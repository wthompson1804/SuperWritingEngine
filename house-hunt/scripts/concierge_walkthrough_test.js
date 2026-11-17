/* Walk through the short page (version 3) the way Lamia would, on a phone:  node scripts/concierge_walkthrough_test.js
   Build first: python3 scripts/build_concierge.py. Opens site/dist/concierge.html from disk, no network (the font
   stylesheet request is answered with an empty file). Writes site/screens/concierge3-*.png at 2x.
   At 390 x 844 and 360 x 780: every persona in meta.recommender_examples is played through the screen, tapping the
   card (or "Either is fine") the persona chose, and the page must ask exactly the example's pairs and then show
   exactly its top three neighborhoods with their buildings, why, gives up and more like this. Then, on the first
   persona: Back undoes an answer; a place (Life here, the five facts, Save top and bottom); More like this opens and
   its thumbnail opens that place; save three; the bar on every screen; My list; Compare with two and three; Choose
   this one; the tour plan; the "if X mattered less" link and its Undo; Not for me; a few more choices; See everything
   with its filter and map. Then: dark theme, storage blocked, a 320px phone, data with no recommender, and Ask
   against a stand-in for the viewer's Claude.
   Checks on every screen: no console or page errors, no network, no sideways scroll, no rent above meta.rent_limit,
   none of the banned words, no trace of "Ask the concierge" outside a Claude viewer, every target at least 44px, the
   bar never covering the end of the page, and the toast never under the bar. */
"use strict";
const { chromium } = require("playwright");
const path = require("path"), fs = require("fs"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const PAGE = "file://" + path.join(ROOT, "site", "dist", "concierge.html");
const SHOTS = path.join(ROOT, "site", "screens");
const BANNED = /\ball-in\b|\bcap\b|\bunits?\b|\bgate\b|\bwe\b|net-effective|everything included|\bcrimes?\b|\bexperiences?\b/i;
const KEY = "lamia-concierge-v3";
let checks = 0;
const ok = (cond, msg) => { assert(cond, msg); checks++; };
const said = (t) => String(t || "").replace(/\b1 places\b/g, "1 place").replace(/\b1 minutes\b/g, "1 minute");

async function open(browser, extra, init) {
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
  if (init) await page.addInitScript(init);
  await page.goto(PAGE);
  await page.waitForSelector("#app h1");
  return { ctx, page, errs, net };
}
let prefix = "";
async function screen(page, name, full) { await page.waitForTimeout(200); await page.screenshot({ path: path.join(SHOTS, "concierge3-" + prefix + name + ".png"), fullPage: !!full }); }
async function sheetShot(page, name) {
  const h = await page.evaluate(() => { const s = document.getElementById("sheet"); return s ? s.scrollHeight : 0; });
  const vp = page.viewportSize();
  if (h > vp.height) {
    await page.setViewportSize({ width: vp.width, height: Math.min(h, 7000) }); await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(SHOTS, "concierge3-" + prefix + name + ".png") });
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
  ok(r.padOk, label + ": the bar covers the end of the page");
  return r;
}
const state = (page) => page.evaluate((k) => JSON.parse(localStorage.getItem(k) || "null"), KEY);
const act = (page, a, v, scope) => page.click((scope || "#app") + ' [data-act="' + a + '"]' + (v ? '[data-v="' + v + '"]' : ""));
async function toastClear(page) {
  const r = await page.evaluate(() => { const t = document.getElementById("toast"), b = document.getElementById("savebar"); if (!t || !b) return true; return t.getBoundingClientRect().bottom <= b.getBoundingClientRect().top + 0.5; });
  ok(r, "the toast sits above the bar");
}
async function barSays(page, n, label) {
  const t = (await page.locator("#savebar #bar-list").innerText()).replace(/\s+/g, " ").trim();
  ok(/My list · (\d+)/.test(t) && Number(/My list · (\d+)/.exec(t)[1]) === n, label + ": the bar says My list · " + n + " (got " + t + ")");
}
const pairOnScreen = (page) => page.locator("#app [data-pair]").getAttribute("data-pair");
async function tap(page, choice) {
  if (choice === "either") await page.click('#app button[data-act="choose"][data-v="either"]');
  else await page.click('#app .pick[data-v="' + choice + '"]');
}
/* what the results screen shows: [[area, [building ids]]] */
const shownTopFromState = (page) => page.evaluate(() => { const r = window.__conciergeRec(); return r && r.top[0] ? r.top[0][0] : null; });
const shownTop = (page) => page.evaluate(() => [...document.querySelectorAll("#app .area3")].map((s) => [s.getAttribute("data-area"), [...s.querySelectorAll(".bcard")].map((c) => c.getAttribute("data-building"))]));

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const built = path.join(ROOT, "site", "dist", "concierge.html");
  assert(fs.existsSync(built), "site/dist/concierge.html is missing: run python3 scripts/build_concierge.py");
  const D = JSON.parse(/window\.CONCIERGE_DATA=(\{[\s\S]*?\});<\/script>/.exec(fs.readFileSync(built, "utf8"))[1]);
  const LIMIT = D.meta.rent_limit, NB = D.buildings.length, EX = D.meta.recommender_examples || [];
  ok(EX.length >= 3, "the built data has recommender examples");
  const byId = Object.fromEntries(D.buildings.map((b) => [b.id, b]));
  const HB = Object.fromEntries(D.neighborhoods.map((h) => [h.id, h]));
  const browser = await chromium.launch();

  /* play one example through the screen; returns the page on the results screen */
  async function playExample(page, ex, L, shots) {
    await act(page, "start");
    for (let i = 0; i < ex.answers.length; i++) {
      await page.waitForSelector("#app [data-pair]");
      const pr = await pairOnScreen(page);
      ok(pr === ex.expected_pairs[i].join("|"), L + ex.persona + ": pair " + (i + 1) + " is " + pr + ", the example says " + ex.expected_pairs[i].join("|"));
      ok((await page.locator("#app .pick").count()) === 2, "two cards");
      const a = page.locator('#app .pick[data-v="a"]'), b = page.locator('#app .pick[data-v="b"]');
      ok((await a.getAttribute("data-id")) === ex.expected_pairs[i][0] && (await b.getAttribute("data-id")) === ex.expected_pairs[i][1], "the cards are a then b");
      ok((await page.locator(".qtop").innerText()).includes("A few quick choices"), "the progress line");
      ok((await page.locator(".dots i").count()) === i + 1, "one dot per choice made, plus this one");
      if (shots && i === 0) { await everyScreen(page, L + "pick", LIMIT); await screen(page, "02-pick"); await screen(page, "02b-pick-full", true); }
      if (shots && i === 1) await everyScreen(page, L + "pick 2", LIMIT);
      await tap(page, ex.answers[i].choice);
    }
    await page.waitForSelector("#app .area3");
    ok((await page.locator("#app [data-pair]").count()) === 0, L + ex.persona + ": no further pair after the example's " + ex.answers.length);
    const top = await shownTop(page);
    ok(JSON.stringify(top) === JSON.stringify(ex.expected_top), L + ex.persona + ": the top three shown " + JSON.stringify(top) + " is the example's " + JSON.stringify(ex.expected_top));
    for (const [area, ids] of ex.expected_top) {
      const sec = page.locator('#app .area3[data-area="' + area + '"]');
      if (ex.expected_why && ex.expected_why[area]) ok((await sec.locator(".because .t").innerText()) === said(ex.expected_why[area]), L + "why for " + area);
      if (ex.expected_gives_up) ok(ex.expected_gives_up[area] ? (await sec.locator(".gives .t").innerText()) === said(ex.expected_gives_up[area]) : (await sec.locator(".gives").count()) === 0, L + "gives up for " + area);
      ok((await sec.locator(".tags li").count()) === Math.min(2, (HB[area].tags || []).length), "two tags on " + area);
      for (const id of ids) {
        const want = (ex.expected_more_like_this || {})[id];
        if (!want) continue;
        const got = await sec.locator('.bcard[data-building="' + id + '"] .thumb').evaluateAll((els) => els.map((e) => e.getAttribute("data-id")));
        ok(JSON.stringify(got) === JSON.stringify(want), L + "more like this under " + id + ": " + got.join(",") + " / " + want.join(","));
      }
    }
    const first = ex.expected_what_would_change && ex.expected_what_would_change[ex.expected_top[0][0]];
    ok(first ? (await page.locator("#whatif p").innerText()) === said(first) : (await page.locator("#whatif").count()) === 0, L + "the 'if it mattered' line");
    return top;
  }

  /* ================= 390 x 844 and 360 x 780 ================= */
  for (const vp of [{ width: 390, height: 844, p: "" }, { width: 360, height: 780, p: "360-" }]) {
    prefix = vp.p;
    const L = "@" + vp.width + " ";
    /* every persona */
    for (let e = 1; e < EX.length; e++) {
      const { ctx, page, errs, net } = await open(browser, { viewport: { width: vp.width, height: vp.height } });
      await playExample(page, EX[e], L, false);
      await everyScreen(page, L + EX[e].persona + " results", LIMIT);
      if (!vp.p && e === EX.length - 1) await screen(page, "03c-results-" + EX[e].persona.replace(/\W+/g, "-"), true);
      ok(errs.length === 0 && net.length === 0, L + EX[e].persona + ": errors or network " + errs.concat(net).join(" | "));
      await ctx.close();
    }
    /* the first persona, then everything else on the page */
    const { ctx, page, errs, net } = await open(browser, { viewport: { width: vp.width, height: vp.height } });
    await everyScreen(page, L + "welcome", LIMIT);
    ok((await page.locator(".hello .lead").innerText()).trim() === "Pick between a few real places, and I'll suggest where to look.", "the welcome line");
    ok(await page.locator('#app [data-act="all"]').isVisible(), "See everything on the first screen");
    await screen(page, "01-welcome");
    /* Back undoes an answer */
    const ex = EX[0];
    await act(page, "start"); await page.waitForSelector("#app [data-pair]");
    await tap(page, ex.answers[0].choice);
    await page.waitForSelector("#app [data-pair]");
    ok((await pairOnScreen(page)) === ex.expected_pairs[1].join("|"), "the second pair");
    await act(page, "undo");
    ok((await pairOnScreen(page)) === ex.expected_pairs[0].join("|"), "Back puts the first pair back");
    ok(((await state(page)).answers || []).length === 0, "and forgets that answer");
    await act(page, "undo");
    ok((await page.locator(".hello").count()) === 1, "Back from the first pair goes to the welcome");
    const top = await playExample(page, ex, L, true);
    await everyScreen(page, L + "results", LIMIT);
    await screen(page, "03-results"); if (!vp.p) await screen(page, "03b-results-full", true);
    ok((await page.locator("#savebar").count()) === 0, "no bar before anything is saved");
    ok(!/experience/i.test(await page.locator("#app").innerText()), "no experiences on the results");
    /* More like this */
    const withMore = top.flatMap((t) => t[1]).find((id) => ((ex.expected_more_like_this || {})[id] || []).length);
    if (withMore) {
      const btn = page.locator('#app [data-act="more"][data-id="' + withMore + '"]');
      ok((await btn.getAttribute("aria-expanded")) === "false" && !(await page.locator("#ml-" + withMore).isVisible()), "more like this starts closed");
      await btn.click();
      ok((await btn.getAttribute("aria-expanded")) === "true" && (await page.locator("#ml-" + withMore).isVisible()), "a tap opens more like this");
      const onScreen = top.flatMap((t) => t[1]);
      const thumbs = await page.locator("#ml-" + withMore + " .thumb").evaluateAll((els) => els.map((e) => e.getAttribute("data-id")));
      ok(thumbs.length >= 1 && thumbs.length <= 3 && thumbs.every((id) => !onScreen.includes(id)), "thumbnails are other buildings, not ones on screen");
      const tt = await page.locator("#ml-" + withMore + " .thumb").first().innerText();
      ok(/Rent/.test(tt) && /Total/.test(tt), "a thumbnail pairs rent and total");
      await everyScreen(page, L + "more like this", LIMIT);
      await page.locator("#ml-" + withMore).scrollIntoViewIfNeeded(); await screen(page, "04-more-like-this");
      await page.locator("#ml-" + withMore + " .thumb").first().click();
      await page.waitForSelector("#sheet .place");
      ok((await page.locator("#sheet .place").getAttribute("data-building")) === thumbs[0], "a thumbnail opens that place");
      await act(page, "back", null, "#sheet");
    }
    /* a place */
    const firstId = top[0][1][0], fb = byId[firstId];
    await page.click('#app .bcard[data-building="' + firstId + '"] .btn[data-act="open"]');
    await page.waitForSelector("#sheet .place");
    const life = (fb.life_here || []).filter((m) => m.text);
    ok((await page.locator("#sheet .life .moment").count()) === life.length, "Life here, one per moment (" + life.length + ")");
    const labels = await page.locator("#sheet .facts .l").allInnerTexts();
    ok(JSON.stringify(labels) === JSON.stringify(["Rent", "Total with utilities and fees", "Drive to Mom and Dad", "Parking", "Dog"]), "the numbers: " + labels.join(" / "));
    ok((await page.locator('#sheet [data-act="save"]').count()) === 2, "Save at the top and the bottom of a place");
    ok((await page.locator("#sheet img").count()) === 0, "no photos copied, only a link");
    ok(/In your place 1 of 3/.test(await page.locator("#sheet").innerText()), "the place says which of her three it is in");
    await everyScreen(page, L + "place", LIMIT); await screen(page, "05-place");
    if (!vp.p) { for (const d of await page.locator("#sheet details.more").all()) await d.locator("summary").click(); await everyScreen(page, L + "place open", LIMIT); await sheetShot(page, "05b-place-full"); }
    await page.locator('#sheet [data-act="save"]').first().click();
    await toastClear(page); await barSays(page, 1, "after one save");
    ok(await page.locator("#bar-compare").isDisabled(), "Compare waits for a second place");
    await act(page, "back", null, "#sheet");
    /* save two more from the cards */
    const pool = top.flatMap((t) => t[1]).filter((id) => id !== firstId);
    for (const id of pool.slice(0, 2)) { const b = page.locator('#app .bcard [data-act="save"][data-id="' + id + '"]'); await b.scrollIntoViewIfNeeded(); await b.click(); }
    await toastClear(page); await barSays(page, 3, "results");
    await everyScreen(page, L + "results with three saved", LIMIT); await screen(page, "06-results-saved");
    ok((await state(page)).saved.length === 3, "three saved");
    /* the bar on every screen: a choice screen too */
    await act(page, "undo"); await page.waitForSelector("#app [data-pair]"); await barSays(page, 3, "a choice");
    await everyScreen(page, L + "pick with bar", LIMIT); if (!vp.p) await screen(page, "06b-pick-with-bar");
    const clear = await page.evaluate(() => { window.scrollTo(0, document.scrollingElement.scrollHeight); const bar = document.getElementById("savebar");
      const last = [...document.querySelectorAll('#app [data-act="choose"], #app [data-act="undo"]')].pop(); return !bar || last.getBoundingClientRect().bottom <= bar.getBoundingClientRect().top; });
    ok(clear, "with the bar showing, Either and Back scroll clear of it");
    await tap(page, ex.answers[ex.answers.length - 1].choice);
    await page.waitForSelector("#app .area3");
    ok(JSON.stringify(await shownTop(page)) === JSON.stringify(ex.expected_top), "the same answer again gives the same three");
    /* My list and Compare */
    await page.click("#bar-list"); await page.waitForSelector("#sheet .saved");
    ok((await page.locator("#sheet .srow").count()) === 3, "three rows in My list");
    await everyScreen(page, L + "my list", LIMIT); await screen(page, "07-my-list");
    await page.locator("#sheet .srow input[type=checkbox]").nth(0).click();
    await page.locator("#sheet .srow input[type=checkbox]").nth(1).click();
    ok((await page.locator("#bar-compare").innerText()).trim() === "Compare 2", "Compare counts the ticked two");
    await page.click("#bar-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "2", "two columns");
    const allLabels = await page.locator("#cmp .crow .cl").allTextContents();
    ok(allLabels.some((l) => /^Each visit/.test(l)) && !allLabels.includes("Experience"), "compare: per-visit row, no experience row");
    await everyScreen(page, L + "compare 2", LIMIT); await screen(page, "08-compare-2");
    await act(page, "back", null, "#sheet"); await page.waitForSelector("#sheet .saved");
    await page.locator("#sheet .srow input[type=checkbox]").nth(2).click();
    await page.click("#bar-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "3", "three columns");
    await everyScreen(page, L + "compare 3", LIMIT); await sheetShot(page, "09-compare-3");
    const pickId = (await state(page)).ticked[1];
    await page.click('#sheet [data-act="choose-tour"][data-id="' + pickId + '"]');
    await toastClear(page);
    ok((await state(page)).tour.includes(pickId), "Choose this one adds it to the tour plan");
    await page.click('#sheet [data-act="plan"]'); await page.waitForSelector(".stop");
    ok((await page.locator('.stop[data-stop="' + pickId + '"]').count()) === 1, "the tour plan has the chosen place");
    await barSays(page, 3, "tour plan");
    const planText = (await everyScreen(page, L + "plan", LIMIT)).text;
    D.buildings.forEach((b) => { const c = b.contact || {}; if (c.private && c.office_phone) ok(!planText.includes(c.office_phone), "a private number is shown"); });
    await screen(page, "10-plan");
    await act(page, "results"); await page.waitForSelector("#app .area3");
    /* if X mattered less: re-rank, then Undo */
    if (await page.locator("#whatif").count()) {
      const want = await page.locator("#whatif").getAttribute("data-first");
      await page.locator("#whatif").scrollIntoViewIfNeeded(); if (!vp.p) await screen(page, "11-whatif");
      await act(page, "nudge"); await page.waitForSelector("#nudged");
      ok((await shownTop(page))[0][0] === want, "the link puts " + want + " first");
      await everyScreen(page, L + "nudged", LIMIT); await screen(page, "11b-nudged");
      await act(page, "unnudge");
      ok(JSON.stringify(await shownTop(page)) === JSON.stringify(ex.expected_top), "Undo goes back to the first suggestion");
    }
    /* Not for me: the next best takes its place, and it is gone everywhere on the screen */
    const outId = top[0][1][0];
    await page.click('#app [data-act="remove"][data-id="' + outId + '"]');
    const after = await shownTop(page);
    ok(!after.flatMap((t) => t[1]).includes(outId), "a place set aside is not shown");
    ok(!(await page.locator('#app .thumb[data-id="' + outId + '"]').count()), "nor offered as more like this");
    await everyScreen(page, L + "after not for me", LIMIT);
    await act(page, "unremove");
    ok(JSON.stringify(await shownTop(page)) === JSON.stringify(ex.expected_top), "Bring back restores the three");
    /* a few more choices */
    await act(page, "more-choices"); await page.waitForSelector("#app [data-pair]");
    let extra = 0; while (await page.locator("#app [data-pair]").count()) { await tap(page, "either"); extra++; if (extra > 5) break; }
    ok(extra >= 1 && extra <= 3, "a few more choices asks up to three (" + extra + ")");
    await page.waitForSelector("#app .area3");
    /* See everything */
    await act(page, "all"); await barSays(page, 3, "See everything");
    await everyScreen(page, L + "everything", LIMIT);
    ok((await page.locator("#all-list .row").count()) === NB, "every building is listed");
    const box = await page.locator(".filter").boundingBox(); ok(box && box.y < 600, "the filter is near the top of See everything");
    const slider = page.locator("#f-rent"), min = Number(await slider.getAttribute("min")), max = Number(await slider.getAttribute("max"));
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(Math.round((min + (max - min) * 0.45) / 50) * 50));
    const fewer = await page.locator("#all-list .row").count(); ok(fewer < NB && fewer > 0, "the rent filter changes the list");
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(max));
    await page.click('[data-act="f-beds"][data-v="0"]');
    ok((await page.locator("#all-list .row").count()) === D.buildings.filter((b) => b.apartments.some((a) => a.beds === 0)).length, "bedrooms filter");
    await page.click('[data-act="f-beds"][data-v="any"]');
    ok((await page.locator("#all-list .grp-h").first().getAttribute("data-hood")) === (await shownTopFromState(page)), "her first place leads See everything");
    await screen(page, "12-everything");
    await page.click('.tabs [data-v="map"]'); await page.waitForSelector("#map-slot .hhm-svg"); await page.waitForTimeout(300);
    await everyScreen(page, L + "map", LIMIT); await screen(page, "12b-map");
    await page.click('.tabs [data-v="list"]'); await act(page, "all-close");
    await page.keyboard.press("Escape");
    ok(errs.length === 0, L + "console or page errors: " + errs.join(" || "));
    ok(net.length === 0, L + "network requests: " + net.join(", "));
    await ctx.close();
  }
  prefix = "";

  /* ================= storage blocked ================= */
  { const { ctx, page: p, errs } = await open(browser, {}, () => { Object.defineProperty(window, "localStorage", { get() { throw new Error("blocked"); } }); });
    await playExample(p, EX[0], "no storage ", false);
    await p.locator('#app .bcard [data-act="save"]').first().click();
    await p.click("#bar-list"); await p.waitForSelector("#sheet .saved");
    await p.locator('#sheet [data-act="tour"]').first().click(); await p.click('#sheet [data-act="plan"]');
    ok((await p.locator(".stop").count()) === 1, "works with storage blocked");
    ok(errs.length === 0, "errors (no storage): " + errs.join(" || ")); await ctx.close(); }

  /* ================= her choices survive a reload ================= */
  { const { ctx, page: p, errs } = await open(browser);
    const top = await playExample(p, EX[1] || EX[0], "reload ", false);
    await p.reload(); await p.waitForSelector("#app .area3");
    ok(JSON.stringify(await shownTop(p)) === JSON.stringify(top), "the three places come back after a reload");
    ok(errs.length === 0, "errors (reload): " + errs.join(" || ")); await ctx.close(); }

  /* ================= dark theme, and a 320px phone ================= */
  { const { ctx, page: p, errs } = await open(browser, { colorScheme: "dark" });
    await screen(p, "13-dark-welcome");
    await act(p, "start"); await p.waitForSelector("#app [data-pair]"); await screen(p, "13b-dark-pick");
    await act(p, "undo");
    await playExample(p, EX[0], "dark ", false);
    await p.locator('#app .bcard [data-act="save"]').nth(0).click(); await p.locator('#app .bcard [data-act="save"]').nth(1).click();
    await screen(p, "13c-dark-results");
    await p.locator('#app .bcard .btn[data-act="open"]').first().click(); await p.waitForSelector("#sheet .place"); await screen(p, "13d-dark-place");
    await act(p, "back", null, "#sheet");
    await p.click("#bar-compare"); await p.waitForSelector("#cmp"); await screen(p, "13e-dark-compare");
    await everyScreen(p, "dark", LIMIT);
    ok(errs.length === 0, "errors (dark): " + errs.join(" || ")); await ctx.close();
    const small = await open(browser, { viewport: { width: 320, height: 568 } });
    await everyScreen(small.page, "320 welcome", LIMIT); await act(small.page, "start"); await small.page.waitForSelector("#app [data-pair]");
    await everyScreen(small.page, "320 pick", LIMIT); await screen(small.page, "14-320-pick");
    await act(small.page, "undo");
    await playExample(small.page, EX[0], "320 ", false);
    await everyScreen(small.page, "320 results", LIMIT);
    for (let i = 0; i < 3; i++) await small.page.locator('#app .bcard [data-act="save"]').nth(i).click();
    await small.page.click("#bar-compare"); await small.page.waitForSelector("#cmp");
    await everyScreen(small.page, "320 compare 3", LIMIT); await screen(small.page, "14b-320-compare-3");
    ok(small.errs.length === 0, "errors (320): " + small.errs.join(" || ")); await small.ctx.close(); }

  /* ================= data with no recommender: the list still works ================= */
  { const strip = () => { let d; Object.defineProperty(window, "CONCIERGE_DATA", { configurable: true, get() { return d; }, set(v) { if (v) { delete v.recommender_samples; } d = v; } }); };
    const { ctx, page: p, errs } = await open(browser, {}, strip);
    ok((await p.locator('#app [data-act="start"]').count()) === 0, "no Start without the recommender");
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
    await playExample(p, EX[0], "ask ", false);
    await p.waitForSelector("#ask-btn");
    await p.click("#ask-btn"); await p.waitForSelector("#ask-sheet");
    ok((await p.evaluate(() => window.__calls.length)) === 0, "nothing is sent until she taps");
    await p.locator("#ask-sugg button").first().click();
    await p.waitForFunction(() => /places/.test(document.getElementById("ask-a").textContent));
    ok((await p.locator("#ask-a").innerText()) === "<b>3</b> places", "the answer is plain text and the lookup read the page's suggestion");
    ok(JSON.stringify((await p.evaluate(() => window.__calls[0])).tools) === JSON.stringify(["list_buildings", "get_building", "compare", "recommend", "why"]), "five lookups, recommend and why among them");
    const rec = await p.evaluate(() => window.__conciergeLookups.recommend());
    ok(JSON.stringify(rec.places.map((x) => x.neighborhood)) === JSON.stringify(EX[0].expected_top.map((t) => HB[t[0]].name + (HB[t[0]].state ? ", " + HB[t[0]].state : ""))), "recommend gives her three places");
    const why = await p.evaluate((id) => window.__conciergeLookups.why({ id }), EX[0].expected_top[0][1][0]);
    ok(why.recommended && why.its_neighborhood && why.its_neighborhood.place === 1 && why.rank_among_all_buildings >= 1, "why explains a building");
    const lst = await p.evaluate(() => window.__conciergeLookups.list_buildings({ recommended_only: true }));
    ok(lst.count === EX[0].expected_top.flatMap((t) => t[1]).length, "list_buildings can keep to her three places");
    await p.evaluate(() => { window.__decline = true; });
    await p.fill("#ask-q", "Which is the quietest?"); await p.click("#ask-send");
    await p.waitForFunction(() => !document.querySelector("#ask-btn,#ask-sheet"));
    ok(errs.length === 0, "errors (ask): " + errs.join(" || ")); await ctx.close();
    const none = await open(browser, {}, () => { window.claude = { use: async () => null }; });
    await none.page.waitForTimeout(300); ok((await none.page.locator("#ask-btn").count()) === 0, "use() resolving null leaves no trace"); await none.ctx.close(); }

  await browser.close();
  console.log(checks + " checks passed; screenshots in site/screens/concierge3-*.png");
})().catch((e) => { console.error("FAILED: " + (e && e.message || e)); process.exit(1); });
