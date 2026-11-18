/* Walk through the short page (version 6) the way Lamia would, on a phone:  node scripts/concierge_walkthrough_test.js
   Build first: python3 scripts/build_concierge.py. Opens site/dist/concierge.html from disk, no network (the font
   stylesheet request is answered with an empty file). Writes site/screens/concierge6-*.png at 2x.
   Version 6 is version 5's content, simplified: Home (the logo, one line, a closed "How these were picked" with the
   funnel sentences and every rule, exactly three neighborhood cards from meta.default_recommendation, each with a
   drawing, its rent and total as a labelled pair, three icon facts, a "Best of 3" sticker on the winner of each fact
   and one "See the 3 apartments" button; then "If one thing matters most to you" with only the leanings outside the
   three); a neighborhood screen (the drawing, its name, one line from the data, exactly its three apartments, each
   with rent and total, three icon facts, the checked mark and Save; Life here as one-line moments that open on a tap;
   Next or Back); the apartment screen (See photos as a link, the five facts, things to confirm, the contact, the rest
   closed); a bar on every screen (Home, Everything, My list with its count); My list with Compare and the tour plan;
   Everything with search, filters, Show more and the map. Then: saved state from earlier versions, storage blocked,
   a thrown error, iPhone 13 and Pixel 7 by tap(), dark theme, a 320px phone, data with no short list, and Ask
   against a stand-in.
   Checks on every screen: no console or page errors, no network, no sideways scroll, no rent above meta.rent_limit,
   none of the banned words, no trace of "Ask the concierge" outside a Claude viewer, every target at least 44px, the
   bar on screen and never covering the end of the page, and the toast never under the bar. */
"use strict";
const { chromium, devices } = require("playwright");
const path = require("path"), fs = require("fs"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const PAGE = "file://" + path.join(ROOT, "site", "dist", "concierge.html");
const SHOTS = path.join(ROOT, "site", "screens");
const BANNED = /\ball-in\b|\bcap\b|\bunits?\b|\bgate\b|\bwe\b|net-effective|everything included|\bcrimes?\b|\bexperiences?\b/i;
const KEY = "lamia-concierge";
let checks = 0;
const ok = (cond, msg) => { assert(cond, msg); checks++; };

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
const shotPath = (name) => path.join(SHOTS, "concierge6-" + prefix + name + ".png");
async function screen(page, name, full) { await page.waitForTimeout(200); await page.screenshot({ path: shotPath(name), fullPage: !!full }); }
async function sheetShot(page, name) {
  const h = await page.evaluate(() => { const s = document.getElementById("sheet"); return s ? s.scrollHeight : 0; });
  const vp = page.viewportSize();
  if (h > vp.height) {
    await page.setViewportSize({ width: vp.width, height: Math.min(h, 7000) }); await page.waitForTimeout(200);
    await page.screenshot({ path: shotPath(name) });
    await page.setViewportSize(vp);
  } else await screen(page, name);
}
async function everyScreen(page, label, limit) {
  const r = await page.evaluate(() => {
    const sheet = document.getElementById("sheet"), bar = document.getElementById("savebar");
    const vis = (e) => { const b = e.getBoundingClientRect(); const st = getComputedStyle(e); return b.width > 0 && b.height > 0 && st.visibility !== "hidden" && (!e.checkVisibility || e.checkVisibility()); };
    const scope = sheet ? sheet.querySelector(".wrap") : document.getElementById("app");
    return {
      sw: Math.max(document.documentElement.scrollWidth, sheet ? sheet.scrollWidth : 0), iw: window.innerWidth,
      text: document.body.innerText,
      rents: [...document.querySelectorAll("[data-rent]")].map((e) => Number(e.getAttribute("data-rent"))),
      ask: !!document.querySelector("#ask-btn,#ask-sheet,[id^=ask-]"),
      bar: !!bar && vis(bar) && bar.querySelectorAll(".tab").length === 3,
      small: [...(sheet ? sheet : document).querySelectorAll("button,a[href],summary,input")].concat(bar ? [...bar.querySelectorAll("button")] : [])
        .filter((e) => vis(e) && !e.closest(".hhm") && !e.closest("label.check") && !e.closest("label.tickl"))
        .filter((e) => { const b = e.getBoundingClientRect(); return b.height < 43.5 || b.width < 43.5; })
        .map((e) => (e.textContent || e.id).trim().slice(0, 30) + " " + Math.round(e.getBoundingClientRect().width) + "x" + Math.round(e.getBoundingClientRect().height)),
      padOk: (() => {
        if (!bar) return true;
        const kids = [...scope.querySelectorAll("*")].filter(vis); if (!kids.length) return true;
        const scroller = sheet || document.scrollingElement;
        const maxScroll = scroller.scrollHeight - scroller.clientHeight;
        const lastBottom = Math.max(...kids.map((e) => e.getBoundingClientRect().bottom)) + (sheet ? sheet.scrollTop : window.scrollY);
        return lastBottom <= maxScroll + (sheet ? sheet.clientHeight : window.innerHeight) - bar.offsetHeight + 1;
      })(),
    };
  });
  ok(r.sw <= r.iw, label + ": the page scrolls sideways (" + r.sw + " > " + r.iw + ")");
  const bad = BANNED.exec(r.text);
  ok(!bad, label + ': banned word "' + (bad && bad[0]) + '" near "' + (bad ? r.text.slice(Math.max(0, bad.index - 40), bad.index + 40).replace(/\n/g, " ") : "") + '"');
  r.rents.forEach((v) => ok(v <= limit, label + ": a rent of " + v + " is above " + limit));
  ok(!r.ask && !/ask the concierge/i.test(r.text), label + ": a trace of the Ask feature");
  ok(r.small.length === 0, label + ": targets under 44px: " + r.small.join(" | "));
  ok(r.bar, label + ": the bar (Home, Everything, My list) is on screen");
  ok(r.padOk, label + ": the bar covers the end of the page");
  return r;
}
const state = (page) => page.evaluate((k) => JSON.parse(localStorage.getItem(k) || "null"), KEY);
async function toastClear(page) {
  const r = await page.evaluate(() => { const t = document.getElementById("toast"), b = document.getElementById("savebar"); if (!t || !b) return true; return t.getBoundingClientRect().bottom <= b.getBoundingClientRect().top + 0.5; });
  ok(r, "the toast sits above the bar");
}
async function barSays(page, n, label) {
  const t = (await page.locator("#savebar #bar-list").innerText()).replace(/\s+/g, " ").trim(), c = (await page.locator("#savebar #bar-list .n").innerText()).trim();
  ok(/My list/.test(t) && c === String(n), label + ": the bar says My list " + n + " (got " + t + ")");
}
const cards = (page) => page.evaluate(() => [...document.querySelectorAll("#app .ncard")].map((c) => c.getAttribute("data-area")));
const aptIds = (page) => page.evaluate(() => [...document.querySelectorAll("#app .acard")].map((c) => c.getAttribute("data-building")));
const num = (t) => Number(String(t).replace(/[^\d.]/g, ""));
async function goHome(page, how) { await page[how || "click"]("#bar-home"); await page.waitForSelector("#app .ncards"); }
async function saveFromHoods(page, n) {
  const saved = [];
  for (let i = 0; saved.length < n && i < 3; i++) {
    await page.click('#app [data-act="hood"][data-v="' + i + '"]'); await page.waitForSelector("#app .acards");
    for (const id of await aptIds(page)) {
      if (saved.length >= n) break;
      await page.click('#app .acard[data-building="' + id + '"] [data-act="save"]'); saved.push(id);
    }
    await goHome(page);
  }
  return saved;
}

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const built = path.join(ROOT, "site", "dist", "concierge.html");
  assert(fs.existsSync(built), "site/dist/concierge.html is missing: run python3 scripts/build_concierge.py");
  const D = JSON.parse(/window\.CONCIERGE_DATA=(\{[\s\S]*?\});<\/script>/.exec(fs.readFileSync(built, "utf8"))[1]);
  const LIMIT = D.meta.rent_limit, NB = D.buildings.length, DR = D.meta.default_recommendation, FUN = D.meta.funnel;
  ok(DR && DR.neighborhoods && DR.neighborhoods.length === 3, "the built data has the short list");
  const WANT = DR.neighborhoods.map((n) => [n.neighborhood_id, n.buildings.map((b) => b.id)]);
  const byId = Object.fromEntries(D.buildings.map((b) => [b.id, b]));
  const HB = Object.fromEntries(D.neighborhoods.map((h) => [h.id, h]));
  const fmt = (x) => Number(x).toLocaleString("en-US");
  const passed = typeof FUN.passed_apartments === "object" ? FUN.passed_apartments.at_or_under_2000 : FUN.passed_apartments;
  const LEANS = (D.meta.leanings || []).filter((x) => x.in_default_three === false);
  const money = (v) => "$" + Math.round(v).toLocaleString("en-US");
  const browser = await chromium.launch();

  async function home(page, L) {
    await page.waitForSelector("#app .ncards");
    ok(/Three neighborhoods picked for you/.test(await page.locator("#res-h").innerText()), L + "the one warm line");
    ok((await page.locator("#app h1.logo").count()) === 1, L + "the logo is the heading");
    ok(JSON.stringify(await cards(page)) === JSON.stringify(WANT.map((t) => t[0])), L + "exactly the data's three neighborhood cards, in order");
    ok(!(await page.locator("#how").evaluate((d) => d.open)), L + "How these were picked is closed");
    ok((await page.locator("#rules li").count()) === FUN.rules.length, L + "every rule is behind the tap");
    for (let i = 0; i < 3; i++) {
      const c = page.locator("#app .ncard").nth(i);
      ok((await c.locator('[data-act="hood"]').count()) === 1 && /^See the 3 apartments/.test((await c.locator('[data-act="hood"]').innerText()).trim()), L + "one button: See the 3 apartments");
      ok((await c.locator(".illus svg").count()) === 1, L + "a drawing on card " + (i + 1));
      ok((await c.locator("[data-fact]").count()) === 4, L + "four facts on card " + (i + 1));
      const mt = (await c.locator(".money").innerText()).replace(/\s+/g, " ");
      const ids = WANT[i][1], rent = Math.min(...ids.map((id) => byId[id].facts.rent_from)), total = Math.min(...ids.map((id) => (byId[id].features_raw || {}).total ?? byId[id].facts.total_from));
      ok(mt.includes("Rent from " + money(rent)) && /Total from with utilities and fees/.test(mt) && mt.includes(money(total)), L + "rent and total as a labelled pair, from the data: " + mt);
      const tags = (DR.neighborhoods[i].tags || []).slice(0, 2);
      ok((await c.locator(".chips li").allInnerTexts()).join("|") === tags.map((t) => t.charAt(0).toUpperCase() + t.slice(1)).join("|"), L + "the tags as chips");
    }
    /* the sticker: on the winner of each fact among the three */
    for (const [fact, dir] of [["total", "low"], ["drive", "low"], ["space", "high"], ["eat", "high"]]) {
      const vals = await page.locator('#app .ncard [data-fact="' + fact + '"]').evaluateAll((els) => els.map((e) => ({ t: (e.querySelector(".tv") || e.querySelector("b")).textContent, best: e.hasAttribute("data-best"), sticker: !!e.querySelector(".sticker") })));
      const ns = vals.map((v) => num(v.t)), t = dir === "low" ? Math.min(...ns) : Math.max(...ns), allSame = ns.every((x) => x === ns[0]);
      vals.forEach((v, j) => ok(v.best === (!allSame && ns[j] === t) && v.sticker === v.best, L + "the Best of 3 sticker on " + fact + " (" + ns.join(", ") + ")"));
    }
    ok((await page.locator("#leanings .lrow").count()) === LEANS.length && (LEANS.length > 0 || (await page.locator("#leanings").count()) === 0), L + "If one thing matters most: only the winners outside the three (" + LEANS.length + ")");
  }
  async function hoodScreen(page, i, L) {
    await page.waitForSelector("#app .acards");
    const A = WANT[i][0], h = HB[A] || {};
    ok(JSON.stringify(await aptIds(page)) === JSON.stringify(WANT[i][1]), L + "neighborhood " + (i + 1) + ": exactly its three apartments, in order");
    ok((await page.locator("#app .hero .illus svg").count()) === 1, L + "the drawing on the neighborhood screen");
    const line = h.good || null;
    if (line) ok((await page.locator("#app .hero .line").innerText()).trim() === line, L + "the one line comes from the data");
    for (const id of WANT[i][1]) {
      const c = page.locator('#app .acard[data-building="' + id + '"]'), b = byId[id];
      const pair = (await c.locator(".pair").innerText()).replace(/\s+/g, " ");
      ok(pair.includes("Rent") && pair.includes("Total with utilities and fees") && pair.includes(money(b.facts.rent_from)) && pair.includes(money(b.facts.total_from)), L + "rent and total on " + id + ": " + pair);
      ok((await c.locator(".minis li").count()) === 3, L + "three icon facts on " + id);
      ok((await c.locator('[data-act="save"]').count()) === 1, L + "Save on " + id);
      const today = (b.apartments || []).every((a) => a.checked && /today/.test(a.checked.status || ""));
      if (today) ok(/Confirmed/.test(await c.locator(".chk").innerText()), L + "the confirmed-today mark on " + id);
      ok((await c.locator(".star").count()) === ((b.apartments || []).some((a) => a.star) ? 1 : 0), L + "a star only where one thing is to confirm (" + id + ")");
      const own = b.neighborhood_id !== A;
      ok((await c.locator(".aname small").count()) === (own ? 1 : 0), L + "its own neighborhood named when not the heading's (" + id + ")");
    }
    const lifeB = WANT[i][1].map((id) => byId[id]).find((b) => (b.life_here || []).some((m) => m.text));
    if (lifeB) {
      const n = lifeB.life_here.filter((m) => m.text).length;
      ok((await page.locator("#life details.mom").count()) === n, L + "Life here: one moment per line (" + n + ")");
      ok((await page.locator("#life details.mom[open]").count()) === 0, L + "the moments start closed");
    }
  }

  /* ================= 390 x 844 and 360 x 780 ================= */
  for (const vp of [{ width: 390, height: 844, p: "" }, { width: 360, height: 780, p: "360-" }]) {
    prefix = vp.p;
    const L = "@" + vp.width + " ";
    const { ctx, page, errs, net } = await open(browser, { viewport: { width: vp.width, height: vp.height } });
    await home(page, L);
    await everyScreen(page, L + "home", LIMIT);
    await screen(page, "01-home"); await screen(page, "01b-home-full", true);
    const tall = await page.evaluate(() => (document.scrollingElement.scrollHeight - document.getElementById("savebar").offsetHeight) / window.innerHeight);
    ok(tall <= 2.6, L + "Home fits on about two phone screens (" + tall.toFixed(2) + ")");
    console.log("  " + L + "home is " + tall.toFixed(2) + " phone screens");
    await page.click("#how summary"); await page.waitForTimeout(100);
    const how = (await page.locator("#how .howbox").innerText()).replace(/\s+/g, " ");
    ok(how.includes(fmt(FUN.listings_read) + " listings") && how.includes(fmt(passed) + " apartments passed every rule"), L + "How these were picked: the real counts (" + how.slice(0, 120) + ")");
    await everyScreen(page, L + "how open", LIMIT); if (!vp.p) { await page.locator("#how").scrollIntoViewIfNeeded(); await screen(page, "01c-how-picked"); }
    await page.click("#how summary");
    /* a leaning opens that neighborhood in Everything */
    if (LEANS.length) {
      await page.locator("#leanings").scrollIntoViewIfNeeded(); if (!vp.p) await screen(page, "02-leanings");
      await page.click('#leanings .lrow[data-id="' + LEANS[0].neighborhood_id + '"]');
      await page.waitForSelector("#all-list");
      const g = page.locator('#all-list .grp-h[data-hood="' + LEANS[0].neighborhood_id + '"]');
      ok((await g.count()) === 1 && await g.evaluate((e) => { const r = e.getBoundingClientRect(); return r.top >= -2 && r.top < window.innerHeight; }), L + "a leaning opens that neighborhood in Everything");
      await goHome(page);
    }
    /* the three neighborhood screens, one after the other with Next */
    await page.click('#app [data-act="hood"][data-v="0"]');
    for (let i = 0; i < 3; i++) {
      await hoodScreen(page, i, L);
      await everyScreen(page, L + "neighborhood " + (i + 1), LIMIT);
      await screen(page, "03-hood-" + (i + 1)); if (!vp.p) await screen(page, "03b-hood-" + (i + 1) + "-full", true);
      if (i === 0) {
        await page.click("#life details.mom >> nth=0 >> summary");
        ok(await page.locator("#life details.mom").first().evaluate((d) => d.open), L + "a tap opens a moment");
        await everyScreen(page, L + "moment open", LIMIT);
        if (!vp.p) { await page.locator("#life").scrollIntoViewIfNeeded(); await screen(page, "03c-life-here-open"); }
      }
      const next = page.locator('#app .hoodnav .btn.main');
      ok((await page.locator("#app .btn.main").count()) === 1, L + "one primary action on neighborhood " + (i + 1));
      if (i < 2) { ok(/^Next: /.test((await next.innerText()).trim()), L + "Next to the following neighborhood"); await next.click(); }
      else { ok(/Back to my three/.test(await next.innerText()), L + "the last one goes back to my three"); }
    }
    await goHome(page);
    /* the apartment screen */
    await page.click('#app [data-act="hood"][data-v="0"]'); await page.waitForSelector("#app .acards");
    const firstId = WANT[0][1][0], fb = byId[firstId];
    await page.click('#app .acard[data-building="' + firstId + '"] .aname'); await page.waitForSelector("#sheet .place");
    const labels = await page.locator("#sheet .facts .l").allInnerTexts();
    ok(JSON.stringify(labels) === JSON.stringify(["Rent", "Total with utilities and fees", "Drive to Mom and Dad", "Parking", "Dog"]), L + "the five facts: " + labels.join(" / "));
    const ph = page.locator("#sheet #photos");
    if (fb.photos_url || fb.listing_url) ok((await ph.getAttribute("href")) === (fb.photos_url || fb.listing_url) && (await ph.getAttribute("target")) === "_blank", L + "See photos is a link out");
    ok((await page.locator("#sheet img").count()) === 0, L + "no photos copied");
    ok((await page.locator('#sheet [data-act="save"]').count()) === 2, L + "Save at the top and the bottom");
    ok((await page.locator("#sheet details.more[open]").count()) === 0 && (await page.locator("#sheet details.more").count()) >= 3, L + "the rest is closed");
    if ((fb.confirm || []).length || (fb.disclosures || []).length) ok((await page.locator("#sheet #confirm li").count()) >= 1, L + "things to confirm");
    const ct = fb.contact || {};
    if ((ct.office_phone && !ct.private) || ct.site) ok((await page.locator("#sheet #contact").count()) === 1, L + "the contact");
    ok(/^Bloomfield|\w/.test(await page.locator("#sheet .kicker").innerText()), L + "the apartment names its neighborhood");
    await everyScreen(page, L + "apartment", LIMIT); await screen(page, "05-apartment");
    if (!vp.p) {
      for (const d of await page.locator("#sheet details.more").all()) await d.locator("summary").first().click();
      const ml = await page.locator("#sheet #more-like .thumb").evaluateAll((els) => els.map((e) => e.getAttribute("data-id")));
      ok(JSON.stringify(ml) === JSON.stringify((fb.similar || []).filter((x) => byId[x] && x !== firstId).slice(0, 3)), "More like this: the data's nearest three");
      await everyScreen(page, L + "apartment all open", LIMIT); await sheetShot(page, "05b-apartment-all-open");
    }
    await page.click('#sheet [data-act="back"]'); await page.waitForSelector("#app .acards");
    await goHome(page);
    /* save three; My list, Compare, tour plan */
    await barSays(page, 0, "before saving");
    const saved = await saveFromHoods(page, 3);
    await toastClear(page); await barSays(page, 3, "home");
    await everyScreen(page, L + "home with three saved", LIMIT); await screen(page, "06-saved");
    await page.click("#bar-list"); await page.waitForSelector("#sheet .saved");
    ok((await page.locator("#sheet .srow").count()) === 3, "three rows in My list");
    ok(!(await page.locator("#sheet #list-compare").isDisabled()) && /Compare 3/.test(await page.locator("#sheet #list-compare").innerText()), "Compare sits in My list, ready for the three saved");
    await everyScreen(page, L + "my list", LIMIT); await screen(page, "07-my-list");
    await page.locator("#sheet .srow input[type=checkbox]").nth(0).click();
    await page.locator("#sheet .srow input[type=checkbox]").nth(1).click();
    await page.click("#sheet #list-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "2", "two columns");
    await everyScreen(page, L + "compare 2", LIMIT); await screen(page, "08-compare-2");
    await page.click('#sheet [data-act="back"]'); await page.waitForSelector("#sheet .saved");
    await page.locator("#sheet .srow input[type=checkbox]").nth(2).click();
    await page.click("#sheet #list-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "3", "three columns");
    await everyScreen(page, L + "compare 3", LIMIT); await sheetShot(page, "09-compare-3");
    const pickId = (await state(page)).ticked[1];
    await page.click('#sheet [data-act="choose-tour"][data-id="' + pickId + '"]');
    await toastClear(page);
    await page.click('#sheet [data-act="plan"]'); await page.waitForSelector(".stop");
    ok((await page.locator('.stop[data-stop="' + pickId + '"]').count()) === 1, "the tour plan has the chosen place");
    const planText = (await everyScreen(page, L + "plan", LIMIT)).text;
    D.buildings.forEach((b) => { const c = b.contact || {}; if (c.private && c.office_phone) ok(!planText.includes(c.office_phone), "a private number is shown"); });
    await screen(page, "10-plan");
    await page.click("#bar-list"); await page.waitForSelector("#sheet .saved");
    ok((await page.locator("#sheet #list-plan").count()) === 1, "the tour plan is reachable from My list");
    await page.click('#sheet [data-act="back"]');
    ok(JSON.stringify((await state(page)).saved) === JSON.stringify(saved), "My list is kept");
    /* Everything */
    await page.click("#bar-all"); await page.waitForSelector("#all-list"); await barSays(page, 3, "Everything");
    await everyScreen(page, L + "everything", LIMIT);
    ok((await page.locator("#all-list .row").count()) === NB, "every building is listed");
    ok(await page.locator("#f-q").isVisible(), "a visible search box");
    const probe = D.buildings.find((b) => b.city) || D.buildings[0];
    const norm = (t) => String(t || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
    for (const q of [probe.city, probe.address, probe.name]) {
      await page.fill("#f-q", q); await page.waitForTimeout(80);
      const ids = await page.locator("#all-list .row").evaluateAll((els) => els.map((e) => e.getAttribute("data-id")));
      const want = D.buildings.filter((b) => { const h = " " + norm([b.name, b.address, b.city, b.state, b.zip, b.postal_code, b.borough, b.neighborhood_name, (HB[b.neighborhood_id] || {}).name, (HB[b.group_id] || {}).name].join(" ")) + " "; return norm(q).split(" ").every((w) => h.includes(" " + w)); }).length;
      ok(ids.includes(probe.id) && ids.length === want, "search '" + q + "' finds it (" + ids.length + " of " + want + ")");
      ok((await page.locator("#f-count").innerText()) === "Showing " + ids.length + " of " + NB + " buildings", "the count follows the search");
    }
    await page.fill("#f-q", probe.city); await page.waitForTimeout(80); await everyScreen(page, L + "search", LIMIT); await screen(page, "12c-everything-search");
    await page.fill("#f-q", "zzzz qqqq"); await page.waitForTimeout(80);
    ok(/Nothing matches/.test(await page.locator("#all-list").innerText()), "no match says so");
    await page.fill("#f-q", ""); await page.waitForTimeout(80);
    ok((await page.locator("#all-list .row").count()) === NB, "clearing the search brings every building back");
    if (!(await page.locator("#filters").evaluate((d) => d.open))) await page.click("#filters summary");
    const slider = page.locator("#f-rent"), min = Number(await slider.getAttribute("min")), max = Number(await slider.getAttribute("max"));
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(Math.round((min + (max - min) * 0.45) / 50) * 50));
    await page.waitForTimeout(80);
    const fewer = await page.locator("#all-list .row").count(); ok(fewer < NB && fewer > 0, "the rent filter changes the list");
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(max));
    await page.waitForTimeout(80);
    ok((await page.locator("#all-list .row").count()) === NB, "back to every building");
    const over = await page.evaluate(() => [...document.querySelectorAll("#all-list .grp")].filter((g) => [...g.querySelectorAll(".row")].filter((r) => r.checkVisibility()).length > 3).length);
    ok(over === 0, "no place shows more than three rows before Show more");
    const moreBtn = page.locator('#all-list [data-act="grp-more"]').first();
    if (await moreBtn.count()) {
      const ctl = await moreBtn.getAttribute("aria-controls"), hidden = await page.locator("#" + ctl.replace(/:/g, "\\:") + " .row").count();
      ok(/^Show \d+ more in /.test(await moreBtn.innerText()) && Number(/\d+/.exec(await moreBtn.innerText())[0]) === hidden, "Show N more says how many");
      await moreBtn.click();
      ok((await moreBtn.getAttribute("aria-expanded")) === "true", "Show more opens the rest");
      await everyScreen(page, L + "show more", LIMIT); await moreBtn.click();
    }
    const states = [...new Set(D.buildings.map((b) => b.state || (HB[b.neighborhood_id] || {}).state).filter(Boolean))].sort();
    if (states.length > 1) {
      await page.click('[data-act="f-state"][data-v="' + states[0] + '"]');
      ok((await page.locator("#all-list .row").count()) === D.buildings.filter((b) => (b.state || (HB[b.neighborhood_id] || {}).state) === states[0]).length, "state filter");
      await page.click('[data-act="f-state"][data-v="any"]');
    }
    await page.click('[data-act="f-beds"][data-v="0"]');
    ok((await page.locator("#all-list .row").count()) === D.buildings.filter((b) => b.apartments.some((a) => a.beds === 0)).length, "bedrooms filter");
    await page.click('[data-act="f-beds"][data-v="any"]');
    ok((await page.locator("#all-list .grp-h").first().getAttribute("data-hood")) === DR.neighborhoods[0].neighborhood_id, "her first neighborhood leads Everything");
    await page.evaluate(() => window.scrollTo(0, 0)); await screen(page, "12-everything");
    await page.click('.tabs [data-v="map"]'); await page.waitForSelector("#map-slot .hhm-svg"); await page.waitForTimeout(300);
    await everyScreen(page, L + "map", LIMIT); await screen(page, "12b-map");
    await page.click('.tabs [data-v="list"]');
    await goHome(page);
    ok(errs.length === 0, L + "console or page errors: " + errs.join(" || "));
    ok(net.length === 0, L + "network requests: " + net.join(", "));
    await ctx.close();
  }
  prefix = "";

  /* ================= keyboard: Tab reaches a card's button, Enter opens it, Escape comes back ================= */
  { const { ctx, page: p, errs } = await open(browser, { hasTouch: false, isMobile: false });
    await p.focus('#app [data-act="hood"][data-v="1"]'); await p.keyboard.press("Enter");
    await p.waitForSelector("#app .acards"); ok(JSON.stringify(await aptIds(p)) === JSON.stringify(WANT[1][1]), "keyboard: Enter opens a neighborhood");
    ok(await p.evaluate(() => document.activeElement && document.activeElement.id === "hood-h"), "keyboard: focus moves to its heading");
    await p.keyboard.press("Escape"); await p.waitForSelector("#app .ncards"); ok(true, "keyboard: Escape goes back home");
    ok(errs.length === 0, "errors (keyboard): " + errs.join(" || ")); await ctx.close(); }

  /* ================= saved state from earlier versions ================= */
  { const keep = D.buildings[0].id;
    const { ctx, page: p, errs } = await open(browser, {}, (k) => { if (!sessionStorage.getItem("seeded")) { sessionStorage.setItem("seeded", "1");
      localStorage.setItem("lamia-concierge-v4", JSON.stringify({ v: 4, step: "results", cj: [0, 1, 2].map((i) => ({ task_index: i, choice: "a" })), moves: [], saved: [k], ticked: [], tour: [k] }));
      localStorage.setItem("lamia-concierge", JSON.stringify({ v: 5, step: "home", saved: [k], ticked: [], tour: [] })); } }, keep);
    await home(p, "old state ");
    const st = await state(p);
    ok(st.v === 6 && st.saved.includes(keep) && st.tour.includes(keep) && !("cj" in st), "old answers ignored; the list and tour plan kept");
    ok(await p.evaluate(() => localStorage.getItem("lamia-concierge-v4") === null), "the old key is removed");
    ok(errs.length === 0, "errors (old state): " + errs.join(" || ")); await ctx.close(); }

  /* ================= storage blocked ================= */
  { const { ctx, page: p, errs } = await open(browser, {}, () => { Object.defineProperty(window, "localStorage", { get() { throw new Error("blocked"); } }); });
    await home(p, "no storage ");
    await saveFromHoods(p, 1);
    await p.click("#bar-list"); await p.waitForSelector("#sheet .saved");
    await p.locator('#sheet [data-act="tour"]').first().click(); await p.click('#sheet [data-act="plan"]');
    ok((await p.locator(".stop").count()) === 1, "works with storage blocked");
    ok(errs.length === 0, "errors (no storage): " + errs.join(" || ")); await ctx.close(); }

  /* ================= an action that throws: a bar with ways on ================= */
  { const { ctx, page: p } = await open(browser);
    await p.evaluate(() => { window.__conciergeThrowOn = "hood"; });
    await p.click('#app [data-act="hood"][data-v="1"]');
    ok(await p.locator("#oops").isVisible() && (await p.locator('#oops [data-oops="results"]').count()) === 1 && (await p.locator('#oops [data-oops="all"]').count()) === 1, "a thrown error shows the Something went wrong bar");
    await screen(p, "16-oops");
    await p.evaluate(() => { window.__conciergeThrowOn = null; });
    await p.click('#oops [data-oops="all"]'); await p.waitForSelector("#all-list");
    ok((await p.locator("#oops").count()) === 0, "Everything recovers");
    await goHome(p);
    ok(JSON.stringify(await cards(p)) === JSON.stringify(WANT.map((t) => t[0])), "and Home is back");
    await ctx.close(); }

  /* ================= real phones: iPhone 13 and Pixel 7, by tap() ================= */
  for (const name of ["iPhone 13", "Pixel 7"]) {
    const ctx = await browser.newContext(Object.assign({}, devices[name]));
    const page = await ctx.newPage(), errs = [], net = [];
    page.on("pageerror", (e) => errs.push(e.message)); page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
    await page.route(/^https?:/, (route) => { const u = route.request().url(); if (/fonts\.googleapis\.com/.test(u)) return route.fulfill({ status: 200, contentType: "text/css", body: "" }); net.push(u); return route.abort(); });
    await page.goto(PAGE); await page.waitForSelector("#app .ncards");
    ok(JSON.stringify(await cards(page)) === JSON.stringify(WANT.map((t) => t[0])), name + ": three neighborhood cards");
    for (let i = 0; i < 3; i++) {
      await page.tap('#app [data-act="hood"][data-v="' + i + '"]'); await page.waitForSelector("#app .acards");
      ok(JSON.stringify(await aptIds(page)) === JSON.stringify(WANT[i][1]), name + ": neighborhood " + (i + 1) + " opens to its three apartments");
      await page.tap("#bar-home"); await page.waitForSelector("#app .ncards");
    }
    await page.tap('#app [data-act="hood"][data-v="0"]'); await page.waitForSelector("#app .acards");
    await page.tap("#app .acard .aname >> nth=0"); await page.waitForSelector("#sheet .place");
    await page.tap('#sheet [data-act="save"] >> nth=0'); await page.tap('#sheet [data-act="back"]');
    await page.tap("#app .acard:nth-child(2) [data-act=\"save\"]");
    await page.tap("#bar-list"); await page.waitForSelector("#sheet .saved");
    await page.tap("#sheet .srow:nth-child(1) .tickl"); await page.tap("#sheet .srow:nth-child(2) .tickl");
    await page.tap("#sheet #list-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "2", name + ": Compare by tap");
    await page.tap('#sheet [data-act="choose-tour"] >> nth=0'); await page.tap('#sheet [data-act="plan"]'); await page.waitForSelector(".stop");
    await page.tap("#bar-all"); await page.waitForSelector("#f-q");
    await page.tap("#f-q"); await page.fill("#f-q", "Stamford"); await page.waitForTimeout(100);
    ok((await page.locator("#all-list .row").count()) >= 1, name + ": search works");
    ok(errs.length === 0 && net.length === 0, name + ": errors or network " + errs.concat(net).join(" | "));
    await page.tap("#bar-home"); await page.waitForSelector("#app .ncards");
    await page.screenshot({ path: path.join(SHOTS, "concierge6-device-" + name.replace(/\W+/g, "-") + ".png") });
    await ctx.close();
  }

  /* ================= dark theme, and a 320px phone ================= */
  { const { ctx, page: p, errs } = await open(browser, { colorScheme: "dark" });
    await home(p, "dark ");
    await screen(p, "13-dark-home"); await screen(p, "13a-dark-home-full", true);
    await everyScreen(p, "dark home", LIMIT);
    await saveFromHoods(p, 2);
    await p.click('#app [data-act="hood"][data-v="0"]'); await p.waitForSelector("#app .acards"); await screen(p, "13b-dark-hood");
    await p.click("#app .acard .aname >> nth=0"); await p.waitForSelector("#sheet .place"); await screen(p, "13c-dark-apartment");
    await everyScreen(p, "dark apartment", LIMIT);
    await p.click("#bar-list"); await p.waitForSelector("#sheet .saved"); await screen(p, "13d-dark-my-list");
    ok(errs.length === 0, "errors (dark): " + errs.join(" || ")); await ctx.close();
    const small = await open(browser, { viewport: { width: 320, height: 568 } });
    await home(small.page, "320 ");
    await everyScreen(small.page, "320 home", LIMIT); await screen(small.page, "14-320-home");
    await small.page.click('#app [data-act="hood"][data-v="2"]'); await small.page.waitForSelector("#app .acards");
    await everyScreen(small.page, "320 neighborhood", LIMIT); await screen(small.page, "14b-320-hood");
    await goHome(small.page);
    await saveFromHoods(small.page, 3);
    await small.page.click("#bar-list"); await small.page.waitForSelector("#sheet .saved");
    for (let i = 0; i < 3; i++) await small.page.locator("#sheet .srow input[type=checkbox]").nth(i).click();
    await small.page.click("#sheet #list-compare"); await small.page.waitForSelector("#cmp");
    await everyScreen(small.page, "320 compare 3", LIMIT); await screen(small.page, "14c-320-compare-3");
    ok(small.errs.length === 0, "errors (320): " + small.errs.join(" || ")); await small.ctx.close(); }

  /* ================= data with no short list: the list still works ================= */
  { const strip = () => { let d; Object.defineProperty(window, "CONCIERGE_DATA", { configurable: true, get() { return d; }, set(v) { if (v && v.meta) { delete v.meta.default_recommendation; } d = v; } }); };
    const { ctx, page: p, errs } = await open(browser, {}, strip);
    await p.click('#app .btn[data-act="all"]'); await p.waitForSelector("#all-list .row");
    ok((await p.locator("#all-list .row").count()) === NB, "fallback: every place is listed");
    await everyScreen(p, "fallback", LIMIT); await screen(p, "15-fallback");
    ok(errs.length === 0, "errors (fallback): " + errs.join(" || ")); await ctx.close(); }

  /* ================= Ask, against a stand-in for the viewer's Claude ================= */
  { const stub = () => {
      window.__calls = [];
      const sample = async (input, options) => {
        window.__calls.push({ input, tools: (options.tools || []).map((t) => t.name) });
        if (window.__decline) throw { code: "not_granted", message: "declined" };
        const r = options.tools ? await options.tools.find((t) => t.name === "recommend").execute({}, {}) : null;
        const text = "<b>" + (r ? r.places.length : "table") + "</b> places";
        options.onText({ text, delta: text }); return { text, truncated: false, modelTierApplied: "quick" };
      };
      sample.limits = async () => ({ maxPromptBytes: 262144, tools: { maxCount: 8 } });
      window.claude = { use: async (n) => (n === "sample" ? sample : null) };
    };
    const { ctx, page: p, errs } = await open(browser, {}, stub);
    await home(p, "ask ");
    await p.waitForSelector("#ask-btn");
    await p.click("#ask-btn"); await p.waitForSelector("#ask-sheet");
    ok((await p.evaluate(() => window.__calls.length)) === 0, "nothing is sent until she taps");
    await p.locator("#ask-sugg button").first().click();
    await p.waitForFunction(() => /places/.test(document.getElementById("ask-a").textContent));
    ok((await p.locator("#ask-a").innerText()) === "<b>3</b> places", "the answer is plain text and the lookup read the page's suggestion");
    ok(JSON.stringify((await p.evaluate(() => window.__calls[0])).tools) === JSON.stringify(["list_buildings", "get_building", "compare", "recommend", "why"]), "five lookups");
    const rec = await p.evaluate(() => window.__conciergeLookups.recommend());
    ok(rec.places.length === 3 && rec.places.every((x, i) => x.why === DR.neighborhoods[i].why) && /listings/.test(rec.how_the_list_was_narrowed), "recommend gives the three places and how the list was narrowed");
    const why = await p.evaluate((id) => window.__conciergeLookups.why({ id }), WANT[0][1][0]);
    ok(why.recommended && why.its_neighborhood && why.its_neighborhood.place === 1, "why explains a building");
    ok((await p.evaluate(() => window.__conciergeLookups.list_buildings({ recommended_only: true }))).count === 9, "list_buildings can keep to the nine");
    await p.evaluate(() => { window.__decline = true; });
    await p.fill("#ask-q", "Which is the quietest?"); await p.click("#ask-send");
    await p.waitForFunction(() => !document.querySelector("#ask-btn,#ask-sheet"));
    ok(errs.length === 0, "errors (ask): " + errs.join(" || ")); await ctx.close();
    const none = await open(browser, {}, () => { window.claude = { use: async () => null }; });
    await none.page.waitForTimeout(300); ok((await none.page.locator("#ask-btn").count()) === 0, "use() resolving null leaves no trace"); await none.ctx.close(); }

  await browser.close();
  console.log(checks + " checks passed; screenshots in site/screens/concierge6-*.png");
})().catch((e) => { console.error("FAILED: " + (e && e.message || e) + "\n" + ((e && e.stack) || "").split("\n").filter((l) => /walkthrough/.test(l)).slice(0, 3).join("\n")); process.exit(1); });
