/* Walk through the short page (version 7, "zoom out to neighborhoods") the way Lamia would, on a phone:
     node scripts/concierge_walkthrough_test.js
   Build first: python3 scripts/build_concierge.py. Opens site/dist/concierge.html from disk, no network (the font
   stylesheet request is answered with an empty file). Writes site/screens/concierge7-*.png at 2x.
   What is compared with site/neighborhoods_data.json, field by field:
     - Home: the logo, "Neighborhoods for you", a closed "How this was ranked" (its counts and weights from meta),
       the first ten neighborhood cards in rank order (rank, name, state, up to two tags, typical rent, drive, one
       chip per why fact, the low-confidence mark only where the data says low, one button), then Show more by ten;
     - every neighborhood screen (all of them, by Next): the why and know-this sentences word for word, its top
       buildings (at most three, none with a rent above the limit: name, rent, total only where the data has one,
       apartments count, known and to-ask chips, rating only where present, a phone only for an office or a company)
       and its buildings to avoid (at most two: name, reason, source name, nothing else), and "All N buildings here";
     - building screens: what is known, what to ask, rent, the listing link, "Checked against its listing" and the
       fuller sheet only for verified buildings, Save;
     - Everything: every neighborhood in rank order, search, the state, drive and typical-rent filters, the map;
     - My list: saved buildings, Remove, Clear, kept across a reload and from version 6's saved state.
   Then: a 360x780 phone, iPhone 13 by tap(), dark theme, storage blocked, a thrown error.
   Checks on every screen: no console or page errors, no network, no sideways scroll, no rent above meta.rent_limit,
   none of the banned words, every target at least 44px, the bar on screen and never covering the end of the page. */
"use strict";
const { chromium, devices } = require("playwright");
const path = require("path"), fs = require("fs"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const PAGE = "file://" + path.join(ROOT, "site", "dist", "concierge.html");
const SHOTS = path.join(ROOT, "site", "screens");
const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, "site", "neighborhoods_data.json"), "utf8"));
const META = DATA.meta, LIMIT = META.rent_limit;
const N = DATA.neighborhoods.slice().sort((a, b) => a.rank - b.rank);
const BANNED = /\ball-in\b|\bcap\b|\bunits?\b|\bgates?\b|\bwe\b|net-effective|everything included|\bcrimes?\b/i;
/* street and building names are proper names ("Vails Gate Heights Dr"): they are taken out before the word check */
const NAMES = [...new Set(N.flatMap((h) => h.all_buildings.concat(h.top_buildings, h.avoid_buildings).flatMap((b) => [b.name, b.address])).filter((s) => typeof s === "string" && BANNED.test(s)))];
const KEY = "lamia-concierge";
const PUBLIC = /^(leasing office|management company)$/i;
let checks = 0;
const ok = (cond, msg) => { assert(cond, msg); checks++; };
const same = (a, b, msg) => ok(JSON.stringify(a) === JSON.stringify(b), msg + "\n  page: " + JSON.stringify(a) + "\n  data: " + JSON.stringify(b));
const money = (v) => "$" + Math.round(v).toLocaleString("en-US");
const rentText = (r) => money(r[0]) + (r[1] !== r[0] ? " to " + money(r[1]) : "");
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const nm = (b) => (b.name || b.address || "").trim();
const isLow = (h) => /^low/i.test(String(typeof h.confidence === "string" ? h.confidence : (h.confidence || {}).level || ""));
const publicPhone = (b) => !!(b.contact && !b.contact.private && PUBLIC.test(b.contact.kind || "") && (b.contact.phone || b.contact.office_phone));

async function open(browser, extra, init, initArg) {
  const ctx = await browser.newContext(Object.assign({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true }, extra || {}));
  const page = await ctx.newPage(), errs = [], net = [];
  page.setDefaultTimeout(10000);
  page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
  page.on("pageerror", (e) => errs.push("PAGEERROR " + e.message));
  await page.route(/^https?:/, (route) => {
    const u = route.request().url();
    if (/fonts\.googleapis\.com/.test(u)) return route.fulfill({ status: 200, contentType: "text/css", body: "" });
    net.push(u); return route.abort();
  });
  if (init) await page.addInitScript(init, initArg);
  await page.goto(PAGE);
  await page.waitForSelector("#app h1");
  return { ctx, page, errs, net };
}
let prefix = "";
const shotPath = (name) => path.join(SHOTS, "concierge7-" + prefix + name + ".png");
async function screen(page, name) { await page.waitForTimeout(150); await page.screenshot({ path: shotPath(name) }); }
async function fullShot(page, name) {
  const vp = page.viewportSize(), h = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.evaluate(() => window.scrollTo(0, 0));
  if (h > vp.height) { await page.setViewportSize({ width: vp.width, height: Math.min(h, 6000) }); await page.waitForTimeout(150); await page.screenshot({ path: shotPath(name) }); await page.setViewportSize(vp); }
  else await screen(page, name);
}
async function everyScreen(page, label) {
  const r = await page.evaluate(() => {
    const bar = document.getElementById("savebar"), scope = document.getElementById("app");
    const vis = (e) => { const b = e.getBoundingClientRect(); const st = getComputedStyle(e); return b.width > 0 && b.height > 0 && st.visibility !== "hidden" && (!e.checkVisibility || e.checkVisibility()); };
    return {
      sw: document.documentElement.scrollWidth, iw: window.innerWidth,
      text: document.body.innerText,
      rents: [...document.querySelectorAll("[data-rent]")].map((e) => Number(e.getAttribute("data-rent"))),
      bar: !!bar && vis(bar) && bar.querySelectorAll(".tab").length === 3 && ["Home", "Everything", "My list"].every((t, i) => bar.querySelectorAll(".tab")[i].textContent.indexOf(t) >= 0),
      small: [...document.querySelectorAll("button,a[href],summary,input")].filter(vis)
        .filter((e) => { const b = e.getBoundingClientRect(); return b.height < 43.5 || b.width < 43.5; })
        .map((e) => (e.textContent || e.id).trim().slice(0, 30) + " " + Math.round(e.getBoundingClientRect().width) + "x" + Math.round(e.getBoundingClientRect().height)),
      padOk: (() => {
        if (!bar) return true;
        const kids = [...scope.querySelectorAll("*")].filter(vis); if (!kids.length) return true;
        const sc = document.scrollingElement, maxScroll = sc.scrollHeight - sc.clientHeight;
        const lastBottom = Math.max(...kids.map((e) => e.getBoundingClientRect().bottom)) + window.scrollY;
        return lastBottom <= maxScroll + window.innerHeight - bar.offsetHeight + 1;
      })(),
    };
  });
  ok(r.sw <= r.iw, label + ": the page scrolls sideways (" + r.sw + " > " + r.iw + ")");
  let text = r.text; NAMES.forEach((s) => { text = text.split(s).join(" "); });
  const bad = BANNED.exec(text);
  ok(!bad, label + ': banned word "' + (bad && bad[0]) + '" near "' + (bad ? text.slice(Math.max(0, bad.index - 40), bad.index + 40).replace(/\n/g, " ") : "") + '"');
  r.rents.forEach((v) => ok(v <= LIMIT, label + ": a rent of " + v + " is above " + LIMIT));
  ok(r.small.length === 0, label + ": targets under 44px: " + r.small.join(" | "));
  ok(r.bar, label + ": the bar (Home, Everything, My list) is on screen");
  ok(r.padOk, label + ": the bar covers the end of the page");
  return r;
}
const state = (page) => page.evaluate((k) => JSON.parse(localStorage.getItem(k) || "null"), KEY);
async function barSays(page, n, label) { ok((await page.locator("#savebar #bar-list .n").innerText()).trim() === String(n), label + ": the bar says My list " + n); }
const cardsDom = (page) => page.evaluate(() => [...document.querySelectorAll("#ncards .ncard")].map((c) => ({
  id: c.getAttribute("data-hood"), rank: c.querySelector(".num").textContent.replace(/\D/g, ""), title: c.querySelector("h2").innerText.replace(/\s+/g, " "),
  tags: [...c.querySelectorAll(".tags li")].map((e) => e.textContent), figs: c.querySelector(".figs").innerText.replace(/\s+/g, " "),
  chips: [...c.querySelectorAll(".wchips li")].map((e) => e.getAttribute("data-measure")), chipText: [...c.querySelectorAll(".wchips li")].map((e) => e.textContent.trim()),
  low: !!c.querySelector('[data-conf="low"]'), buttons: [...c.querySelectorAll("button,a")].map((e) => e.textContent.replace(/\s+/g, " ").trim()),
  drawing: !!c.querySelector(".illus svg"),
})));
const hoodDom = (page) => page.evaluate(() => {
  const T = (e) => (e ? e.textContent.replace(/\s+/g, " ").trim() : null), q = (s, r) => (r || document).querySelector(s), qa = (s, r) => [...(r || document).querySelectorAll(s)];
  return {
    id: q("#app article").getAttribute("data-hood"), h1: T(q("#app h1")), kicker: T(q(".hero .kicker")), whyH: T(q("#why-h")),
    why: qa("#why li .t").map(T), know: qa("#know li .t").map(T), low: !!q('#why [data-conf="low"]'), note: T(q("#supply-note")),
    life: qa("#life details.mom .mt b").map(T),
    tops: qa("#tops .bcard").map((c) => ({
      id: c.getAttribute("data-building"), name: T(q(".bname b", c)).replace(/\s*›$/, ""), checked: /Checked against its listing/.test(T(q(".bname", c))),
      rent: T(q(".pair [data-rent]", c)), rentTop: Number(q(".pair [data-rent]", c).getAttribute("data-rent")), total: T(q(".pair [data-total]", c)), pairLabels: qa(".pair span", c).map(T),
      count: q("[data-count]", c) ? Number(q("[data-count]", c).getAttribute("data-count")) : null,
      known: qa(".kq li.k", c).map((e) => T(e).replace(/^✓\s*/, "")), ask: qa(".kq li.q", c).map((e) => e.getAttribute("data-q")),
      rating: q("[data-rating]", c) ? Number(q("[data-rating]", c).getAttribute("data-rating")) : null, tel: qa('a[href^="tel:"]', c).length,
      listing: (q(".links a.link", c) || {}).href || null, save: qa('[data-act="save"]', c).length,
    })),
    avoid: qa("#avoid .avoid").map((c) => ({ id: c.getAttribute("data-building"), name: T(q("h3", c)).replace(/^Avoid:\s*/, ""), reason: T(q(".reason", c)), src: T(q(".src", c)), kids: c.children.length, rent: !!q("[data-rent]", c), tel: qa('a[href^="tel:"]', c).length, x: T(q(".x", c)) })),
    avoidStyle: q("#avoid .avoid") ? getComputedStyle(q("#avoid .avoid")).borderTopStyle : null, topStyle: q("#tops .bcard") ? getComputedStyle(q("#tops .bcard")).borderTopStyle : null,
    allLabel: T(q("#allb-t")), next: T(q("#next-hood")), prev: T(q("#prev-hood")),
  };
});
function checkHood(d, h, i, L) {
  ok(d.id === h.id && d.h1 === h.name, L + "is the screen of " + h.name + " (got " + d.h1 + ")");
  ok(d.kicker === "Number " + h.rank + " of " + N.length && d.whyH === "Why it ranks #" + h.rank, L + "says its rank");
  same(d.why, h.why.slice(0, 3).map((w) => w.text.replace(/\s+/g, " ").trim()), L + "why sentences");
  same(d.know, h.know_this.slice(0, 2).map((w) => w.text.replace(/\s+/g, " ").trim()), L + "know-this sentences");
  ok(d.low === isLow(h), L + "the low-confidence mark is " + (isLow(h) ? "missing" : "shown without cause"));
  ok(d.note === (typeof h.supply_note === "string" && h.supply_note.trim() ? h.supply_note.trim() : null), L + "supply note");
  same(d.life, (h.life_here || []).filter((m) => m && m.fact).map((m) => (m.place || "Around here").replace(/\s+/g, " ").trim()), L + "Life here moments");
  const tops = h.top_buildings.slice(0, 3), avs = h.avoid_buildings.slice(0, 2);
  ok(d.tops.length <= 3 && d.avoid.length <= 2, L + "at most three top buildings and two to avoid");
  same(d.tops.map((b) => b.id), tops.map((b) => b.id), L + "top buildings");
  d.tops.forEach((c, k) => {
    const b = tops[k], B = L + nm(b) + ": ", v = b.verified && b.verified.on_page, t = v && b.verified.total_with_utilities_and_fees;
    ok(c.name === nm(b).replace(/\s+/g, " "), B + "name (got " + c.name + ")");
    ok(c.rent === rentText(b.rent_range) && c.rentTop === b.rent_range[1] && c.rentTop <= LIMIT, B + "rent " + c.rent);
    ok(c.total === (t ? rentText(t) : null), B + "total with utilities and fees " + c.total);
    same(c.pairLabels, t ? ["Rent", "Total with utilities and fees"] : ["Rent"], B + "the rent labels");
    ok(c.count === b.apartments, B + "apartments at the limit or less");
    same(c.known, b.known, B + "known chips"); same(c.ask, b.to_ask, B + "to-ask chips");
    ok(c.rating === (b.rating && typeof b.rating.value === "number" ? b.rating.value : null), B + "rating only where the data has one");
    ok(c.checked === !!v, B + "Checked against its listing");
    ok(c.tel === (publicPhone(b) ? 1 : 0), B + "a phone only for an office or a company");
    ok(c.listing === (b.listing_url ? new URL(b.listing_url).href : null), B + "listing link"); ok(c.save === 1, B + "one Save");
  });
  same(d.avoid.map((b) => b.id), avs.map((b) => b.id), L + "buildings to avoid");
  d.avoid.forEach((c, k) => {
    const b = avs[k], B = L + "avoid " + nm(b) + ": ";
    ok(c.name === nm(b).replace(/\s+/g, " ") && c.reason === b.reason.replace(/\s+/g, " ").trim(), B + "name and reason");
    ok(c.src.indexOf("Source: " + b.source.name) === 0, B + "source name (got " + c.src + ")");
    ok(c.kids === 4 && !c.rent && c.tel === 0 && c.x === "✕", B + "shows only the cross, the name, the reason and the source");
  });
  if (d.avoid.length && d.tops.length) ok(d.avoidStyle === "dashed" && d.topStyle === "solid", L + "avoid cards look different from top buildings");
  ok(d.allLabel === "All " + h.all_buildings.length + (h.all_buildings.length === 1 ? " building" : " buildings") + " here", L + "All N buildings here (got " + d.allLabel + ")");
  ok(d.next === (N[i + 1] ? "Next: " + N[i + 1].name + " ›" : null) && d.prev === (N[i - 1] ? "‹ Previous: " + N[i - 1].name : null), L + "next and previous");
}
const bldDom = (page) => page.evaluate(() => {
  const T = (e) => (e ? e.textContent.replace(/\s+/g, " ").trim() : null), q = (s) => document.querySelector(s), qa = (s) => [...document.querySelectorAll(s)];
  return { id: q("#app article").getAttribute("data-building"), h1: T(q("#app h1")), kicker: T(q(".place .kicker")), checked: !!q("#checked"), photos: (q("#photos") || {}).href || null,
    facts: qa("#facts .frow").map((r) => [T(r.querySelector(".l")), T(r.querySelector(".v"))]), known: qa("#known li .t").map(T), ask: qa("#toask li .t").map(T), tel: qa('a[href^="tel:"]').map(T), rich: !!q("#d-apts"), saves: qa('[data-act="save"]').length, rating: !!q("[data-rating]") };
});
function checkBld(d, b, h, L) {
  const v = !!(b.verified && b.verified.on_page);
  ok(d.id === b.id && d.h1 === nm(b).replace(/\s+/g, " ") && d.kicker === h.name, L + "is the screen of " + nm(b));
  ok(d.checked === v, L + "Checked against its listing only when verified");
  ok(!d.rich || v, L + "the fuller sheet only for a verified building");
  ok(d.photos === (b.listing_url ? new URL(b.listing_url).href : null), L + "the listing link");
  ok(d.facts[0][0] === "Rent" && d.facts[0][1] === rentText(b.rent_range) + "a month", L + "rent first (got " + d.facts[0].join(" ") + ")");
  const t = v && b.verified.total_with_utilities_and_fees, tot = d.facts.find((f) => f[0] === "Total with utilities and fees");
  ok(!!tot === !!t && (!t || tot[1] === rentText(t) + "a month"), L + "the total, labelled, only where the data has one");
  const cnt = d.facts.find((f) => f[0] === "Apartments at " + money(LIMIT) + " or less");
  ok(cnt && cnt[1] === String(b.apartments), L + "apartments at the limit or less");
  same(d.known, b.known, L + "what is known");
  same(d.ask.slice(0, b.to_ask.length), b.to_ask, L + "what to ask");
  ok(d.tel.length === (publicPhone(b) ? 1 : 0), L + "a phone only for an office or a company (got " + d.tel.join(",") + ")");
  ok(d.rating === !!(b.rating && typeof b.rating.value === "number"), L + "rating only where present");
  ok(d.saves === 2, L + "Save at the top and the bottom");
}
const rowsDom = (page, sel) => page.evaluate((s) => [...document.querySelectorAll(s + " .row")].map((r) => r.getAttribute("data-id")), sel || "#all-list");
async function setRange(page, id, v) { await page.evaluate(([i, val]) => { const e = document.getElementById(i); e.value = String(val); e.dispatchEvent(new Event("input", { bubbles: true })); }, [id, v]); await page.waitForTimeout(80); }
async function toHood(page, id, how) { await page[how || "click"]("#bar-all"); await page.waitForSelector("#all-list"); await page[how || "click"]('#all-list .row[data-id="' + id + '"]'); await page.waitForSelector('#app article[data-hood="' + id + '"]'); }

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const browser = await chromium.launch();
  const firstVerified = N.map((h) => [h, h.top_buildings.find((b) => b.verified && b.verified.on_page)]).find((x) => x[1]);
  const firstPlain = N.map((h) => [h, h.top_buildings.find((b) => !(b.verified && b.verified.on_page))]).find((x) => x[1]);

  for (const size of [{ width: 390, height: 844, p: "" }, { width: 360, height: 780, p: "360-" }]) {
    prefix = size.p; const W = size.width + ": ";
    const { ctx, page, errs, net } = await open(browser, { viewport: { width: size.width, height: size.height } });

    /* ================= home ================= */
    ok((await page.locator("#app h1.logo").getAttribute("aria-label")) === "Lamia's House Hunt, the short version", W + "the logo");
    ok((await page.locator(".hello .say").innerText()).trim() === "Neighborhoods for you", W + "Neighborhoods for you");
    ok(!(await page.locator("#how").evaluate((e) => e.open)) && (await page.locator("#how summary").innerText()).trim().indexOf("How this was ranked") === 0, W + "How this was ranked is one closed tap");
    let cards = await cardsDom(page);
    same(cards.map((c) => c.id), N.slice(0, 10).map((h) => h.id), W + "home shows the first ten in rank order");
    cards.forEach((c, i) => {
      const h = N[i], L = W + "card " + h.name + ": ";
      ok(c.rank === String(h.rank) && c.title.indexOf(h.name) >= 0 && c.title.indexOf(h.state) >= 0, L + "rank, name and state (got " + c.title + ")");
      same(c.tags, h.tags.slice(0, 2).map(cap), L + "tags");
      ok(c.figs.indexOf(money(h.typical_rent) + " typical rent") === 0 && c.figs.indexOf(Math.round(h.drive_min) + " min drive to Mom and Dad") > 0, L + "typical rent and drive (got " + c.figs + ")");
      same(c.chips, h.why.slice(0, 3).map((w) => w.measure), L + "one chip per why fact");
      ok(c.chipText.every((t) => t.length > 3 && t.length <= 30), L + "chips are short: " + c.chipText.join(" | "));
      ok(c.low === isLow(h), L + "low-confidence mark"); ok(c.drawing, L + "a drawing");
      ok(c.buttons.length === 1 && /^See this neighborhood/.test(c.buttons[0]), L + "one button");
    });
    ok((await page.locator("#show-more").innerText()).trim() === "Show " + Math.min(10, N.length - 10) + " more" && (await page.locator("#shown-count").innerText()).trim() === "Showing 10 of " + N.length, W + "Show more");
    await everyScreen(page, W + "home");
    await screen(page, "01-home"); await fullShot(page, "01b-home-full");
    await page.click("#how summary");
    const how = await page.locator(".howbox").innerText();
    ok(how.indexOf(META.counts.listings_used.toLocaleString("en-US") + " apartment listings") >= 0 && how.indexOf(META.counts.eligible + " neighborhoods are ranked") >= 0, W + "how: the counts from meta");
    const wts = await page.evaluate(() => [...document.querySelectorAll("#weights li")].map((l) => [l.getAttribute("data-measure"), Number(l.querySelector("b").textContent), (l.querySelector("small") || {}).textContent || ""]));
    same(wts.map((w) => [w[0], w[1]]), Object.keys(META.measures).sort((a, b) => META.measures[b].weight - META.measures[a].weight).map((k) => [k, META.measures[k].weight]), W + "how: measures and weights");
    wts.forEach((w) => { const c = META.coverage[w[0]]; ok(w[2] === (c.neighborhoods_with_measure === c.of ? "Known for all " + c.of : "Known for " + c.neighborhoods_with_measure + " of " + c.of), W + "how: coverage of " + w[0]); });
    await everyScreen(page, W + "how this was ranked"); await screen(page, "02-how");
    await page.click("#how summary");
    await page.click("#show-more");
    cards = await cardsDom(page);
    same(cards.map((c) => c.id), N.slice(0, 20).map((h) => h.id), W + "Show more adds the next ten in rank order");
    await everyScreen(page, W + "home, twenty shown");

    /* ================= every neighborhood screen, by Next ================= */
    await page.click('#ncards .ncard[data-hood="' + N[0].id + '"] [data-act="hood"]');
    const sweep = size.p ? 12 : N.length;
    for (let i = 0; i < sweep; i++) {
      const h = N[i], L = W + "#" + h.rank + " " + h.name + ": ";
      await page.waitForSelector('#app article[data-hood="' + h.id + '"]');
      checkHood(await hoodDom(page), h, i, L);
      await everyScreen(page, L.slice(0, -2));
      if (i < 3) { await page.click("#allb-t"); await page.waitForSelector("#allb-list");
        same(await rowsDom(page, "#allb-list"), h.all_buildings.slice(0, 20).map((b) => b.id), L + "all buildings, the first twenty");
        await everyScreen(page, L + "all buildings open"); await fullShot(page, "03-hood-" + (i + 1)); await page.click("#allb-t"); }
      if (i + 1 < sweep) await page.click("#next-hood");
    }
    if (!size.p) { await page.click("#prev-hood"); await page.waitForSelector('#app article[data-hood="' + N[N.length - 2].id + '"]'); ok(true, "Previous goes back one"); }
    /* a neighborhood with the most to show, for the eye */
    const rich = N.slice().sort((a, b) => (b.avoid_buildings.length + b.life_here.length + b.know_this.length) - (a.avoid_buildings.length + a.life_here.length + a.know_this.length))[0];
    await toHood(page, rich.id); await page.click("#life details.mom summary").catch(() => {}); await fullShot(page, "04-hood-full");

    /* ================= building screens ================= */
    for (const [h, b, name] of [[firstPlain[0], firstPlain[1], "05-building"], [firstVerified[0], firstVerified[1], "05b-building-checked"]]) {
      await toHood(page, h.id);
      await page.click('.bcard[data-building="' + b.id + '"] .bname'); await page.waitForSelector('#app article[data-building="' + b.id + '"]');
      checkBld(await bldDom(page), b, h, W + "building " + nm(b) + ": ");
      await everyScreen(page, W + "building " + nm(b)); await screen(page, name); await fullShot(page, name + "-full");
      if (b === firstVerified[1]) { ok((await bldDom(page)).rich, W + "a verified building opens the fuller sheet"); await page.click("#d-apts summary"); await everyScreen(page, W + "building, apartments open"); }
      await page.click('[data-act="back"]'); await page.waitForSelector('#app article[data-hood="' + h.id + '"]');
      ok(true, "Back returns to the neighborhood");
    }
    if (!size.p) {
      /* every top building with a contact, and every top building of the first eight neighborhoods */
      const want = [];
      N.forEach((h, i) => h.top_buildings.slice(0, 3).forEach((b) => { if (i < 8 || b.contact) want.push([h, b]); }));
      let lastHood = null;
      for (const [h, b] of want) {
        if (lastHood !== h.id) { await toHood(page, h.id); lastHood = h.id; }
        await page.click('.bcard[data-building="' + b.id + '"] .bname'); await page.waitForSelector('#app article[data-building="' + b.id + '"]');
        checkBld(await bldDom(page), b, h, "building " + h.name + " / " + nm(b) + ": ");
        await everyScreen(page, "building " + nm(b));
        await page.click('[data-act="back"]'); await page.waitForSelector('#app article[data-hood="' + h.id + '"]');
      }
      /* a building to avoid, opened from the full list: its reason, and no Save */
      const av = N.find((h) => h.avoid_buildings.length && h.all_buildings.slice(0, 20).some((b) => b.id === h.avoid_buildings[0].id));
      if (av) {
        await toHood(page, av.id); await page.click("#allb-t"); await page.click('#allb-list .row[data-id="' + av.avoid_buildings[0].id + '"]'); await page.waitForSelector('#app article[data-role="avoid"]');
        ok((await page.locator(".place .avoid .reason").innerText()).trim() === av.avoid_buildings[0].reason.trim() && (await page.locator('[data-act="save"]').count()) === 0, "an avoid building's screen gives its reason and has no Save");
        await everyScreen(page, "avoid building screen"); await screen(page, "06-avoid-building");
      }
    }

    /* ================= Save and My list ================= */
    await page.click("#bar-list"); await page.waitForSelector("#app h1");
    ok((await page.locator("#app h1").innerText()).trim() === "Nothing saved yet", W + "My list starts empty"); await everyScreen(page, W + "My list, empty"); await barSays(page, 0, W + "start");
    await page.click('#app [data-act="home"]'); await page.waitForSelector("#ncards");
    const [sh, sb] = firstPlain, [vh, vb] = firstVerified;
    await toHood(page, sh.id);
    await page.click('.bcard[data-building="' + sb.id + '"] [data-act="save"]');
    ok((await page.locator('.bcard[data-building="' + sb.id + '"] [data-act="save"]').getAttribute("aria-pressed")) === "true" && (await page.locator("#toast").innerText()) === "Saved to My list.", W + "Save on a card");
    ok(await page.evaluate(() => document.getElementById("toast").getBoundingClientRect().bottom <= document.getElementById("savebar").getBoundingClientRect().top + 0.5), W + "the toast sits above the bar");
    await barSays(page, 1, W + "after one save"); await screen(page, "07-saved");
    await toHood(page, vh.id); await page.click('.bcard[data-building="' + vb.id + '"] .bname'); await page.waitForSelector(".place");
    await page.click('.place .btn[data-act="save"]'); await barSays(page, 2, W + "after two saves");
    same(await state(page), { v: 7, saved: [sb.id, vb.id] }, W + "what is kept on the phone");
    await page.click("#bar-list"); await page.waitForSelector("#saved");
    const rows = await page.evaluate(() => [...document.querySelectorAll("#saved .srow")].map((r) => [r.getAttribute("data-building"), r.querySelector("h2").textContent, r.querySelector(".in").textContent, r.querySelector("[data-rent]").textContent]));
    same(rows.map((r) => [r[0], r[1], r[3]]), [[sb.id, nm(sb), rentText(sb.rent_range)], [vb.id, nm(vb), rentText(vb.rent_range)]], W + "My list rows");
    ok(rows[0][2].indexOf(sh.name + ", number " + sh.rank) === 0, W + "a saved building names its neighborhood");
    ok((await page.locator("#app h1").innerText()).trim() === "2 saved buildings", W + "My list heading");
    await everyScreen(page, W + "My list"); await screen(page, "08-my-list");
    await page.reload(); await page.waitForSelector("#app h1"); await barSays(page, 2, W + "after a reload");
    await page.click("#bar-list"); await page.waitForSelector("#saved");
    await page.click('#saved .srow[data-building="' + vb.id + '"] [data-act="open"]'); await page.waitForSelector('#app article[data-building="' + vb.id + '"]');
    ok((await page.locator('.top [data-act="save"]').getAttribute("aria-pressed")) === "true", W + "the saved building opens from My list, marked saved");
    await page.click('[data-act="back"]'); await page.waitForSelector("#saved");
    await page.click('#saved .srow[data-building="' + sb.id + '"] [data-act="unsave"]'); await barSays(page, 1, W + "after Remove");
    await page.click("#clear"); await page.waitForSelector("#clear-confirm"); await everyScreen(page, W + "My list, clear?"); await page.click('[data-act="clear-no"]'); await barSays(page, 1, W + "Keep it");
    await page.click("#clear"); await page.click('[data-act="clear-yes"]'); await barSays(page, 0, W + "after Clear");
    same(await state(page), { v: 7, saved: [] }, W + "the phone's copy is empty");

    /* ================= Everything ================= */
    await page.click("#bar-all"); await page.waitForSelector("#all-list");
    ok((await page.locator("#bar-all").getAttribute("aria-current")) === "page", W + "the bar marks Everything");
    same(await rowsDom(page), N.map((h) => h.id), W + "Everything lists every neighborhood in rank order");
    const r0 = await page.locator("#all-list .row").first().innerText();
    ok([String(N[0].rank), N[0].name, N[0].state, money(N[0].typical_rent), Math.round(N[0].drive_min) + " min drive"].every((s) => r0.indexOf(s) >= 0), W + "a row has rank, name, state, typical rent and drive (got " + r0.replace(/\n/g, " ") + ")");
    ok((await page.locator("#all-count").innerText()).trim() === "All " + N.length + " neighborhoods", W + "the count");
    await everyScreen(page, W + "Everything"); await screen(page, "12-everything");
    const target = N[Math.min(17, N.length - 1)], word = target.name.split(/[^A-Za-z]+/).filter((w) => w.length > 3)[0] || target.name;
    await page.fill("#f-q", word); await page.waitForTimeout(120);
    const found = await rowsDom(page);
    const norm = (t) => " " + String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim() + " ";
    const NAME = { NY: "New York", NJ: "New Jersey", CT: "Connecticut", PA: "Pennsylvania" };
    same(found, N.filter((h) => norm([h.name, h.area, h.state, NAME[h.state], (h.tags_true || h.tags).join(" ")].join(" ")).indexOf(" " + norm(word).trim()) >= 0).map((h) => h.id), W + 'search "' + word + '"');
    ok(found.indexOf(target.id) >= 0 && found.length < N.length, W + "search finds " + target.name);
    await everyScreen(page, W + "Everything, searched"); await screen(page, "12c-everything-search");
    await page.fill("#f-q", "zzzz"); await page.waitForSelector("#all-empty"); await everyScreen(page, W + "Everything, nothing matches");
    await page.click('[data-act="f-reset"]'); await page.waitForSelector("#all-list"); same(await rowsDom(page), N.map((h) => h.id), W + "Clear search and filters");
    await page.click("#filter summary");
    const st = N.map((h) => h.state).sort((a, b) => N.filter((h) => h.state === b).length - N.filter((h) => h.state === a).length)[0];
    await page.click('[data-act="f-state"][data-v="' + st + '"]');
    same(await rowsDom(page), N.filter((h) => h.state === st).map((h) => h.id), W + "state filter " + st);
    const drives = N.map((h) => h.drive_min).sort((a, b) => a - b), dCut = Math.ceil(drives[Math.floor(drives.length / 3)] / 5) * 5;
    await setRange(page, "f-drive", dCut);
    same(await rowsDom(page), N.filter((h) => h.state === st && h.drive_min <= dCut).map((h) => h.id), W + "state and longest drive " + dCut);
    ok((await page.locator("#f-drive-out").innerText()).trim() === dCut + " min", W + "the drive filter says its value");
    await page.click('[data-act="f-state"][data-v="any"]');
    const rents = N.map((h) => h.typical_rent).sort((a, b) => a - b), rCut = Math.ceil(rents[Math.floor(rents.length / 2)] / 25) * 25;
    await setRange(page, "f-rent", rCut);
    const expect = N.filter((h) => h.drive_min <= dCut && h.typical_rent <= rCut).map((h) => h.id);
    same(await rowsDom(page), expect, W + "longest drive and highest typical rent " + rCut);
    ok((await page.locator("#all-count").innerText()).trim() === expect.length + " of " + N.length + " neighborhoods" && (await page.locator("#fsum").innerText()).indexOf("up to " + money(rCut)) >= 0, W + "the count and the filter summary follow");
    await everyScreen(page, W + "Everything, filtered"); await screen(page, "12d-everything-filtered");
    /* the map */
    await page.click("#mode-map"); await page.waitForSelector("#map svg");
    ok((await page.locator("#map svg circle").count()) === expect.length, W + "the map shows the filtered neighborhoods as dots");
    await page.click('[data-act="f-state"][data-v="any"]'); await setRange(page, "f-drive", 9999); await setRange(page, "f-rent", 99999);
    ok((await page.locator("#map svg circle").count()) === N.length, W + "the map shows every neighborhood");
    await page.click("#filter summary");
    const dot = await page.locator("#map svg circle").last().boundingBox();   /* drawn last: rank 1 */
    await page.mouse.click(dot.x + dot.width / 2, dot.y + dot.height / 2); await page.waitForSelector("#map-card .row");
    const picked = await page.locator("#map-card .row").getAttribute("data-id");
    const p1 = N[0], near = N.filter((h) => Math.abs(h.lat - p1.lat) < 0.05 && Math.abs(h.lon - p1.lon) < 0.05).map((h) => h.id);
    ok(near.indexOf(picked) >= 0, W + "tapping a dot shows that neighborhood (got " + picked + ")");
    await everyScreen(page, W + "Everything, map"); await fullShot(page, "12b-map");
    await page.click("#map-card .row"); await page.waitForSelector('#app article[data-hood="' + picked + '"]'); ok(true, "the map's card opens the neighborhood");
    await page.click('[data-act="back"]'); await page.waitForSelector("#map svg"); ok(true, "Back returns to the map");
    await page.click("#bar-home"); await page.waitForSelector("#ncards");
    ok((await page.locator("#bar-home").getAttribute("aria-current")) === "page", W + "the bar marks Home");
    await page.keyboard.press("Tab"); ok(true, "keyboard reaches the page");

    ok(errs.length === 0, W + "console errors: " + errs.join(" | "));
    ok(net.length === 0, W + "network requests: " + net.join(", "));
    await ctx.close();
  }
  prefix = "";

  /* ================= iPhone 13, by tap ================= */
  { const dev = devices["iPhone 13"]; const { ctx, page: p, errs, net } = await open(browser, Object.assign({}, dev));
    const h = N[0], b = h.top_buildings[0];
    await everyScreen(p, "iPhone 13 home");
    await p.tap('#ncards .ncard[data-hood="' + h.id + '"] [data-act="hood"]'); await p.waitForSelector('#app article[data-hood="' + h.id + '"]');
    checkHood(await hoodDom(p), h, 0, "iPhone 13 " + h.name + ": "); await everyScreen(p, "iPhone 13 neighborhood");
    await p.screenshot({ path: shotPath("device-iPhone-13") });
    if (b) {
      await p.tap('.bcard[data-building="' + b.id + '"] .bname'); await p.waitForSelector('#app article[data-building="' + b.id + '"]');
      checkBld(await bldDom(p), b, h, "iPhone 13 building: "); await everyScreen(p, "iPhone 13 building");
      await p.tap('.top [data-act="save"]'); await barSays(p, 1, "iPhone 13 save");
      await p.tap('[data-act="back"]'); await p.waitForSelector("#tops");
    }
    await p.tap("#next-hood"); await p.waitForSelector('#app article[data-hood="' + N[1].id + '"]');
    await p.tap("#bar-list"); await p.waitForSelector(b ? "#saved" : "#app h1"); await everyScreen(p, "iPhone 13 My list");
    await p.tap("#bar-all"); await p.waitForSelector("#all-list"); await p.tap("#mode-map"); await p.waitForSelector("#map svg"); await everyScreen(p, "iPhone 13 map");
    await p.tap("#bar-home"); await p.waitForSelector("#ncards"); await p.tap("#show-more");
    ok((await p.locator("#ncards .ncard").count()) === Math.min(20, N.length), "iPhone 13: Show more by tap");
    ok(errs.length === 0 && net.length === 0, "iPhone 13: errors or network: " + errs.concat(net).join(" | "));
    await ctx.close(); }

  /* ================= dark ================= */
  { prefix = "dark-"; const { ctx, page: p, errs } = await open(browser, { colorScheme: "dark" });
    const lum = await p.evaluate(() => { const m = getComputedStyle(document.body).backgroundColor.match(/\d+/g).map(Number); return (m[0] + m[1] + m[2]) / 3; });
    ok(lum < 60, "dark: the page is dark (" + lum + ")");
    const contrast = await p.evaluate(() => { const c = document.querySelector(".ncard"), a = getComputedStyle(c).backgroundColor.match(/\d+/g).map(Number), b = getComputedStyle(c.querySelector("h2")).color.match(/\d+/g).map(Number); return Math.abs((a[0] + a[1] + a[2]) - (b[0] + b[1] + b[2])) / 3; });
    ok(contrast > 120, "dark: card text stands out from the card");
    await everyScreen(p, "dark home"); await screen(p, "01-home");
    const h = N.find((x) => x.avoid_buildings.length && x.know_this.length) || N[0];
    await toHood(p, h.id); checkHood(await hoodDom(p), h, N.indexOf(h), "dark " + h.name + ": "); await everyScreen(p, "dark neighborhood"); await fullShot(p, "03-hood");
    if (h.top_buildings[0]) { await p.click(".bcard .bname"); await p.waitForSelector(".place"); await everyScreen(p, "dark building"); await fullShot(p, "05-building"); }
    await p.click("#bar-all"); await p.waitForSelector("#all-list"); await p.click("#mode-map"); await p.waitForSelector("#map svg"); await screen(p, "12b-map");
    ok(errs.length === 0, "dark: console errors: " + errs.join(" | ")); await ctx.close(); prefix = ""; }

  /* ================= storage blocked: everything still works, in memory ================= */
  { const { ctx, page: p, errs } = await open(browser, {}, () => { Object.defineProperty(window, "localStorage", { get() { throw new Error("blocked"); } }); });
    ok((await p.locator("#ncards .ncard").count()) === 10, "storage blocked: home still shows ten");
    await p.click("#ncards .ncard [data-act=hood]"); await p.waitForSelector("#tops");
    if (N[0].top_buildings.length) { await p.click('.bcard [data-act="save"]'); await barSays(p, 1, "storage blocked: save");
      await p.click("#bar-list"); await p.waitForSelector("#saved"); ok((await p.locator("#saved .srow").count()) === 1, "storage blocked: My list works in memory"); }
    await everyScreen(p, "storage blocked");
    ok(errs.length === 0, "storage blocked: console errors: " + errs.join(" | ")); await ctx.close(); }

  /* ================= version 6's saved state: its list is kept where the building is still here ================= */
  { const keep = firstVerified[1].id;
    const { ctx, page: p, errs } = await open(browser, {}, ([k, id]) => { if (!sessionStorage.getItem("seeded")) { sessionStorage.setItem("seeded", "1");
      localStorage.setItem(k, JSON.stringify({ v: 6, step: "plan", saved: [id, "b_gone", 7], ticked: [id], tour: [id] })); localStorage.setItem("lamia-concierge-v4", JSON.stringify({ saved: ["b_gone_too"] })); } }, [KEY, keep]);
    await barSays(p, 1, "old state"); same(await state(p), { v: 7, saved: [keep] }, "old state becomes version 7 with the buildings still here");
    ok((await p.evaluate(() => localStorage.getItem("lamia-concierge-v4"))) === null, "the older key is cleared");
    ok((await p.locator("#ncards .ncard").count()) === 10, "old state: opens on Home");
    ok(errs.length === 0, "old state: console errors: " + errs.join(" | ")); await ctx.close(); }
  { const { ctx, page: p, errs } = await open(browser, {}, (k) => { localStorage.setItem(k, "{not json"); }, KEY);
    ok((await p.locator("#ncards .ncard").count()) === 10, "broken saved state: the page still opens"); ok(errs.length === 0, "broken saved state: errors"); await ctx.close(); }

  /* ================= an action that throws: a bar with two ways on ================= */
  { const { ctx, page: p, errs } = await open(browser);
    await p.evaluate(() => { window.__conciergeThrowOn = "hood"; });
    await p.click("#ncards .ncard [data-act=hood]"); await p.waitForSelector("#oops");
    ok(await p.locator("#oops").isVisible() && (await p.locator('#oops [data-oops="home"]').count()) === 1 && (await p.locator('#oops [data-oops="all"]').count()) === 1, "a thrown error shows the Something went wrong bar");
    ok(await p.evaluate(() => [...document.querySelectorAll("#oops button")].every((b) => b.getBoundingClientRect().height >= 44)), "its buttons are 44px");
    await screen(p, "16-oops");
    await p.evaluate(() => { window.__conciergeThrowOn = null; });
    await p.click('#oops [data-oops="all"]'); await p.waitForSelector("#all-list");
    ok((await p.locator("#oops").count()) === 0, "See everything recovers");
    await p.evaluate(() => { window.__conciergeThrowOn = "home"; }); await p.click("#bar-home"); await p.waitForSelector("#oops");
    await p.evaluate(() => { window.__conciergeThrowOn = null; }); await p.click('#oops [data-oops="home"]'); await p.waitForSelector("#ncards");
    ok((await p.locator("#oops").count()) === 0, "Back to Home recovers");
    ok(errs.length === 0, "thrown error: console errors: " + errs.join(" | ")); await ctx.close(); }

  await browser.close();
  console.log("concierge walk-through (version 7): " + checks + " checks passed; screenshots in site/screens/concierge7-*.png");
})().catch((e) => { console.error("FAIL: " + (e && e.message || e)); process.exit(1); });
