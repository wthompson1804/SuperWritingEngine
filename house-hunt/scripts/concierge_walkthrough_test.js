/* Walk through the short page the way Lamia would, on a phone (390 x 844):  node scripts/concierge_walkthrough_test.js
   Build first: python3 scripts/build_concierge.py. Opens site/dist/concierge.html from disk, no network (the font
   stylesheet request is answered with an empty file). Writes site/screens/concierge-*.png at 2x.
   Checks on every screen: no console or page errors, no sideways scroll, no rent above meta.rent_limit, none of the
   banned words in the visible text, and no trace of "Ask the concierge" when the page is not inside a Claude viewer. */
"use strict";
const { chromium } = require("playwright");
const path = require("path"), fs = require("fs"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const PAGE = "file://" + path.join(ROOT, "site", "dist", "concierge.html");
const SHOTS = path.join(ROOT, "site", "screens");
const BANNED = /\ball-in\b|\bcap\b|\bunits?\b|\bgate\b|\bwe\b|net-effective|everything included|\bcrimes?\b/i;
const KEY = "lamia-concierge-v1";
let checks = 0;
const ok = (cond, msg) => { assert(cond, msg); checks++; };

async function open(browser, extra, init) {
  const ctx = await browser.newContext(Object.assign({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, hasTouch: true, isMobile: true }, extra || {}));
  const page = await ctx.newPage(), errs = [], net = [];
  page.setDefaultTimeout(8000);
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
async function screen(page, name, full) { await page.waitForTimeout(260); await page.screenshot({ path: path.join(SHOTS, "concierge-" + name + ".png"), fullPage: !!full }); }
async function everyScreen(page, label, limit) {
  const r = await page.evaluate(() => ({
    sw: document.documentElement.scrollWidth, iw: window.innerWidth, text: document.body.innerText,
    rents: [...document.querySelectorAll("[data-rent]")].map((e) => Number(e.getAttribute("data-rent"))),
    ask: !!document.querySelector("#ask-btn,#ask-sheet,[id^=ask-]"),
    small: [...document.querySelectorAll("button,a[href],summary,input")].filter((e) => { const b = e.getBoundingClientRect(); return b.width > 0 && (b.height < 43.5 || b.width < 43.5) && !e.closest(".hhm") && !e.closest("label.check"); }).map((e) => (e.textContent || e.id).trim().slice(0, 30) + " " + Math.round(e.getBoundingClientRect().width) + "x" + Math.round(e.getBoundingClientRect().height)),
  }));
  ok(r.sw <= r.iw, label + ": the page scrolls sideways (" + r.sw + " > " + r.iw + ")");
  const bad = BANNED.exec(r.text);
  ok(!bad, label + ': banned word "' + (bad && bad[0]) + '" near "' + (bad ? r.text.slice(Math.max(0, bad.index - 40), bad.index + 40).replace(/\n/g, " ") : "") + '"');
  r.rents.forEach((v) => ok(v <= limit, label + ": a rent of " + v + " is above " + limit));
  ok(!r.ask && !/ask the concierge/i.test(r.text), label + ": a trace of the Ask feature");
  ok(r.small.length === 0, label + ": targets under 44px: " + r.small.join(" | "));
  return r;
}
const state = (page) => page.evaluate((k) => JSON.parse(localStorage.getItem(k) || "null"), KEY);
const act = (page, a, v) => page.click('#app [data-act="' + a + '"]' + (v ? '[data-v="' + v + '"]' : ""));

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const built = path.join(ROOT, "site", "dist", "concierge.html");
  assert(fs.existsSync(built), "site/dist/concierge.html is missing: run python3 scripts/build_concierge.py");
  const D = JSON.parse(/window\.CONCIERGE_DATA=(\{[\s\S]*?\});<\/script>/.exec(fs.readFileSync(built, "utf8"))[1]);
  const LIMIT = D.meta.rent_limit, EXPS = D.experiences, EO = (D.either_or || []).slice(0, 3);
  const parkedNames = D.neighborhoods.filter((h) => h.parked_under).map((h) => h.name);
  const browser = await chromium.launch();

  /* ================= the main walk ================= */
  const { page, errs, net } = await open(browser);
  await everyScreen(page, "welcome", LIMIT);
  await screen(page, "01-welcome");
  ok(await page.locator('#app [data-act="all"]').isVisible(), "See everything is on the first screen");

  /* 1. stories */
  await act(page, "start");
  for (let s = 0; s < EXPS.length; s++) {
    const n = EXPS[s].story.length;
    ok((await page.locator(".segs i").count()) === n + 1, "one progress segment per card and one for the answer");
    for (let c = 0; c < n; c++) {
      ok((await page.locator(".story-head").innerText()).includes("Story " + (s + 1) + " of " + EXPS.length), "story header");
      const r = await everyScreen(page, "story " + (s + 1) + " card " + (c + 1), LIMIT);
      if (EXPS[s].story[c].text) ok(r.text.includes(EXPS[s].story[c].text), "the card shows its text");
      if (s === 0 && c === 0) await screen(page, "02-story-first");
      if (s === 0 && c === 1) await screen(page, "02b-story-weekday");
      if (s === 0 && c === n - 1) await screen(page, "02c-story-last");
      if (s === 0 && c === 1) {            /* she controls the pace: nothing moves by itself, tapping the sides and the arrow keys work */
        const before = (await state(page)).ci; await page.waitForTimeout(1500);
        ok((await state(page)).ci === before, "no timed autoplay");
        const box = await page.locator("#story-card").boundingBox();
        await page.mouse.click(box.x + 20, box.y + 200); ok((await state(page)).ci === before - 1, "tap on the left goes back");
        await page.mouse.click(box.x + box.width - 30, box.y + 200); ok((await state(page)).ci === before, "tap on the right goes on");
        await page.keyboard.press("ArrowLeft"); await page.keyboard.press("ArrowRight"); ok((await state(page)).ci === before, "arrow keys move too");
      }
      await act(page, "story-next");
    }
    await everyScreen(page, "answer " + (s + 1), LIMIT);
    ok((await page.locator('#app [data-act="answer"]').count()) === 3, "three answers");
    if (s === 0) await screen(page, "03-answer");
    await act(page, "answer", ["me", "maybe", "no"][s % 3]);
  }
  /* 2. either/or */
  for (let q = 0; q < EO.length; q++) {
    await everyScreen(page, "question " + (q + 1), LIMIT);
    ok((await page.locator('#app .choice').count()) === 2 && (await page.locator('#app [data-act="eo"][data-v="skip"]').isVisible()), "two choices and Skip");
    if (q === 0) await screen(page, "04-either-or");
    await act(page, "eo", ["a", "b", "skip"][q % 3]);
  }
  /* 3. five picks */
  let st = await state(page);
  ok(st.step === "picks" && st.slots.length === 5 && new Set(st.slots).size === 5, "five different picks");
  ok((await page.locator("#pick-count").innerText()).startsWith("1 of 5"), "1 of 5");
  const labels = await page.locator(".bcard .facts .l").allInnerTexts();
  ok(JSON.stringify(labels) === JSON.stringify(["Rent", "Total with utilities and fees", "Drive to Mom and Dad", "Parking", "Dog"]), "the five facts, in order: " + labels.join(" / "));
  ok((await page.locator(".bcard .pos").count()) >= 2, "position markers on the numbers");
  const me = EXPS.filter((e, i) => ["me", "maybe", "no"][i % 3] === "me").map((e) => e.id);
  me.forEach((e) => ok(st.slots.some((id) => D.buildings.find((b) => b.id === id).experience_id === e), "a pick from each That's me experience"));
  await everyScreen(page, "pick 1", LIMIT);
  await screen(page, "05-pick");
  await screen(page, "05-pick-full", true);
  const photo = page.locator('.bcard a:has-text("See photos")').first();
  if (await photo.count()) ok((await photo.getAttribute("target")) === "_blank" && /^https?:/.test(await photo.getAttribute("href")), "See photos opens a new tab");
  ok((await page.locator(".bcard img").count()) === 0, "no photos on the page, only the link");
  for (const d of await page.locator(".bcard details").all()) await d.locator("summary").click();
  await everyScreen(page, "pick 1, details open", LIMIT);
  const pairs = await page.locator(".bcard .apts .pair").allInnerTexts();
  pairs.forEach((t) => ok(/Rent/.test(t) && /Total with utilities and fees/.test(t), "each apartment shows rent and total as a pair"));
  await screen(page, "05b-pick-details", true);

  /* "Not this one" swaps in the next best and a vetoed building never comes back */
  const vetoed = [];
  for (let i = 0; i < 7; i++) {
    const before = await state(page), cur = before.slots[before.pi];
    await act(page, "veto");
    vetoed.push(cur);
    const after = await state(page);
    ok(after.slots.length === 5 && new Set(after.slots).size === 5, "still five after a swap");
    ok(after.slots.every((id) => !vetoed.includes(id)), "a vetoed building came back");
    ok(after.slots[after.pi] !== cur && !before.slots.includes(after.slots[after.pi]), "the card was replaced by a new building");
    before.slots.forEach((id, k) => { if (k !== before.pi) ok(after.slots[k] === id, "the other four stayed put"); });
    ok((await page.locator(".bcard").getAttribute("data-building")) === after.slots[after.pi], "the card on screen is the new one");
    if (i % 2) await act(page, "pick-next");
  }
  await everyScreen(page, "after swaps", LIMIT);
  /* keep one, look at the bar, then keep the rest */
  st = await state(page);
  if (st.pi !== 0) { while ((await state(page)).pi > 0) await act(page, "pick-prev"); }
  await act(page, "keep");
  st = await state(page);
  ok(st.kept.length === 1 && st.step === "picks", "one kept, still choosing");
  ok(await page.locator('#app .bar [data-act="plan"]').isVisible(), "That's enough is offered once something is kept");
  await screen(page, "05c-pick-after-keep");
  await act(page, "pick-prev");
  ok(await page.locator(".bcard .keptflag").isVisible(), "a kept card says so");
  await screen(page, "05d-pick-kept");
  await act(page, "pick-open");
  for (let i = 0; i < 4; i++) { ok((await state(page)).step === "picks", "still picking"); await act(page, "keep"); }
  /* 4. tour plan */
  st = await state(page);
  ok(st.step === "plan" && st.kept.length === 5, "five kept leads to the tour plan");
  ok(st.kept.every((id) => !vetoed.includes(id)), "nothing vetoed is in the plan");
  ok((await page.locator(".stop").count()) === 5, "five stops in the plan");
  const drives = (await page.locator(".area-h span").allInnerTexts()).map((t) => parseInt(t, 10));
  ok(drives.every((v, i) => i === 0 || v >= drives[i - 1]), "areas are ordered by drive time: " + drives.join(", "));
  ok((await page.locator('.stop a[href*="maps"]').count()) >= 1, "addresses link to a map");
  const kb = st.kept.map((id) => D.buildings.find((b) => b.id === id));
  const firstQ = kb.find((b) => b.confirm.length && b.confirm[0].question);
  if (firstQ) { const qs = await page.locator('.stop:has(h3:text-is("' + firstQ.name.replace(/"/g, '\\"') + '")) ol li').allInnerTexts(); ok(qs[0] === firstQ.confirm[0].question, "confirm questions come first"); }
  const planText = (await everyScreen(page, "plan", LIMIT)).text;
  D.buildings.forEach((b) => { const c = b.contact || {}; if (c.private && c.office_phone) ok(!planText.includes(c.office_phone), "a private number is shown"); });
  await screen(page, "06-plan");
  await screen(page, "06-plan-full", true);
  ok(await page.locator('#app [data-act="picks"]').isVisible() && await page.locator('#app [data-act="reset-ask"]').isVisible(), "Change my picks and Start over");

  /* See everything */
  await act(page, "all");
  await everyScreen(page, "everything", LIMIT);
  const box = await page.locator(".filter").boundingBox();
  ok(box && box.y < 500, "the filter is on the first screen of See everything (top at " + Math.round(box.y) + "px)");
  const heads = await page.locator(".grp-h").evaluateAll((els) => els.map((e) => e.firstChild.textContent));
  parkedNames.forEach((nm) => ok(!heads.some((h) => h.replace(/, [A-Z]{2}$/, "") === nm), "a parked neighborhood has its own heading: " + nm));
  if (parkedNames.length) ok((await page.locator(".nearby").count()) > 0 && (await page.locator(".nearby").first().innerText()).toLowerCase() === "also nearby", "Also nearby label");
  const total = await page.locator("#all-list .row").count();
  ok(total === D.buildings.length, "every building is listed (" + total + " of " + D.buildings.length + ")");
  const expHeads = await page.locator(".exp-h h2").allInnerTexts();
  ok(JSON.stringify(expHeads) === JSON.stringify(EXPS.map((e) => e.label)), "grouped by experience");
  await screen(page, "07-everything");
  await screen(page, "07-everything-full", true);
  const slider = page.locator("#f-rent"), min = Number(await slider.getAttribute("min")), max = Number(await slider.getAttribute("max"));
  const mid = Math.round((min + (max - min) * 0.45) / 50) * 50;
  await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(mid));
  const fewer = await page.locator("#all-list .row").count();
  ok(fewer < total && fewer > 0, "the rent filter changes the list (" + total + " -> " + fewer + ")");
  ok((await page.locator("#f-count").innerText()) === "Showing " + fewer + " of " + total + " buildings", "the count line follows");
  (await page.locator("#all-list [data-rent]").evaluateAll((els) => els.map((e) => Number(e.dataset.rent)))).forEach((v) => ok(v <= mid, "a listed rent is above the filter"));
  await screen(page, "07b-everything-filtered");
  await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(max));
  await page.click('[data-act="f-beds"][data-v="0"]');
  const studios = await page.locator("#all-list .row").count();
  ok(studios === D.buildings.filter((b) => b.apartments.some((a) => a.beds === 0)).length, "bedrooms filter");
  await page.click('[data-act="f-beds"][data-v="any"]');
  await page.check("#f-garage");
  ok((await page.locator("#all-list .row").count()) === D.buildings.filter((b) => b.facts.parking && b.facts.parking.kind === "garage").length, "garage filter");
  await page.uncheck("#f-garage");
  ok((await page.locator("#all-list .row").count()) === total, "clearing the filter brings everything back");
  /* open a building from the list and keep it */
  const target = D.buildings.find((b) => !st.kept.includes(b.id));
  await page.click('#all-list .row[data-id="' + target.id + '"]');
  await page.waitForSelector("#sheet .bcard");
  ok((await page.locator("#sheet .facts .l").count()) === 5, "the same card opens from the list");
  await everyScreen(page, "building from the list", LIMIT);
  await screen(page, "08-building-from-list");
  await page.click('#sheet [data-act="keep"]');
  ok((await state(page)).kept.includes(target.id), "kept from the list");
  await page.keyboard.press("Escape");
  ok((await page.locator("#sheet").count()) === 0, "Escape closes the building");
  ok(await page.locator('#all-list .row[data-id="' + target.id + '"] .tag.k').isVisible(), "the list marks it as kept");
  /* the map */
  await page.click('.tabs [data-v="map"]');
  await page.waitForSelector("#map-slot .hhm-svg");
  await page.waitForTimeout(400);
  await everyScreen(page, "map", LIMIT);
  await screen(page, "09-map", true);
  const dot = page.locator("#map-slot .hhm-dot").first();
  if (await dot.count()) { await dot.focus().catch(() => {}); await page.keyboard.press("Enter").catch(() => {}); await page.waitForTimeout(200); await everyScreen(page, "map card", LIMIT); await screen(page, "09b-map-card", true); }
  await page.click('.tabs [data-v="list"]');
  await act(page, "all-close");
  ok((await state(page)).step === "plan" && (await page.locator(".stop").count()) === 6, "back to the plan, now with six");
  /* start over asks first */
  await act(page, "reset-ask"); await page.waitForSelector("#reset-box");
  await screen(page, "06b-start-over");
  await act(page, "reset-no"); ok((await state(page)).kept.length === 6, "No keeps everything");
  await act(page, "reset-ask"); await act(page, "reset-yes");
  st = await state(page); ok(st.step === "welcome" && !st.kept.length && !st.vetoed.length, "Start over clears it");
  ok(errs.length === 0, "console or page errors: " + errs.join(" || "));
  ok(net.length === 0, "network requests: " + net.join(", "));
  await page.context().close();

  /* ================= everything "Not me" ================= */
  { const { ctx, page: p, errs: e2 } = await open(browser);
    await act(p, "start");
    for (let s = 0; s < EXPS.length; s++) { for (let c = 0; c < EXPS[s].story.length; c++) await act(p, "story-next"); await act(p, "answer", "no"); }
    for (let q = 0; q < EO.length; q++) await act(p, "eo", "skip");
    const s2 = await state(p); ok(s2.slots.length === 5, "all Not me: still five");
    ok(/best places overall/.test(await p.locator("#app").innerText()), "all Not me: the page says it picked the best overall");
    await screen(p, "05e-pick-all-not-me");
    /* reload: her place is remembered */
    await p.reload(); await p.waitForSelector(".bcard"); ok((await state(p)).step === "picks", "a reload comes back to the same step");
    /* veto everything: fewer than five, then none, and never an error */
    for (let i = 0; i < D.buildings.length; i++) { const b = p.locator('#app [data-act="veto"]'); if (!(await b.count())) break; await b.click(); }
    ok((await state(p)).vetoed.length === D.buildings.length && /Nothing is left/.test(await p.locator("#app").innerText()), "vetoing everything ends plainly");
    await everyScreen(p, "nothing left", LIMIT);
    ok(e2.length === 0, "errors (all Not me): " + e2.join(" || ")); await ctx.close(); }

  /* ================= storage unavailable ================= */
  { const { ctx, page: p, errs: e3 } = await open(browser, {}, () => { Object.defineProperty(window, "localStorage", { get() { throw new Error("blocked"); } }); });
    await act(p, "start");
    for (let s = 0; s < EXPS.length; s++) { for (let c = 0; c < EXPS[s].story.length; c++) await act(p, "story-next"); await act(p, "answer", "me"); }
    for (let q = 0; q < EO.length; q++) await act(p, "eo", "a");
    await p.waitForSelector(".bcard"); await act(p, "veto"); await act(p, "keep"); await act(p, "plan");
    ok((await p.locator(".stop").count()) === 1, "works with storage blocked");
    ok(e3.length === 0, "errors (no storage): " + e3.join(" || ")); await ctx.close(); }

  /* ================= dark theme, and a small phone ================= */
  { const seed = (k) => { try { localStorage.setItem(k, JSON.stringify({ step: "story", si: 0, ci: 1 })); } catch (e) {} };
    const { ctx, page: p, errs: e4 } = await open(browser, { colorScheme: "dark" });
    await screen(p, "10-dark-welcome");
    await act(p, "start"); await act(p, "story-next"); await screen(p, "10-dark-story");
    for (let s = 0; s < EXPS.length; s++) { const from = s === 0 ? 1 : 0; for (let c = from; c < EXPS[s].story.length; c++) await act(p, "story-next"); if (s === 0) await screen(p, "10-dark-answer"); await act(p, "answer", "me"); }
    for (let q = 0; q < EO.length; q++) await act(p, "eo", "b");
    await screen(p, "10-dark-pick", true);
    await act(p, "keep"); await act(p, "plan"); await screen(p, "10-dark-plan", true);
    await act(p, "all"); await screen(p, "10-dark-everything");
    await everyScreen(p, "dark", LIMIT);
    ok(e4.length === 0, "errors (dark): " + e4.join(" || ")); await ctx.close(); void seed;
    const small = await open(browser, { viewport: { width: 320, height: 568 } });
    await everyScreen(small.page, "320 welcome", LIMIT); await act(small.page, "start"); await everyScreen(small.page, "320 story", LIMIT);
    for (let s = 0; s < EXPS.length; s++) { for (let c = (s === 0 ? 0 : 0); c < EXPS[s].story.length; c++) await act(small.page, "story-next"); await act(small.page, "answer", "maybe"); }
    for (let q = 0; q < EO.length; q++) { await everyScreen(small.page, "320 question", LIMIT); await act(small.page, "eo", "a"); }
    await everyScreen(small.page, "320 pick", LIMIT); await screen(small.page, "11-small-phone-pick", true);
    await act(small.page, "all"); await everyScreen(small.page, "320 everything", LIMIT);
    ok(small.errs.length === 0, "errors (320): " + small.errs.join(" || ")); await small.ctx.close(); }

  /* ================= Ask, against a stand-in for the viewer's Claude =================
     The real thing only runs inside a Claude viewer. This checks the wiring: the button appears only when
     claude.use("sample") resolves, the lookups answer from the page's data, the answer is put on the page as text,
     and a declined permission removes every trace. */
  { const stub = () => {
      window.__calls = [];
      const sample = async (input, options) => {
        window.__calls.push({ input, tools: (options.tools || []).map((t) => t.name), cache: options.cache });
        if (window.__decline) throw { code: "not_granted", message: "declined" };
        const list = options.tools ? await options.tools.find((t) => t.name === "list_buildings").execute({ garage: true }, {}) : null;
        const text = "<b>" + (list ? list.count : "table") + "</b> buildings";
        options.onText({ text, delta: text }); return { text, truncated: false, modelTierApplied: "quick" };
      };
      sample.limits = async () => ({ maxPromptBytes: 262144, tools: window.__noTools ? undefined : { maxCount: 8 } });
      window.claude = { use: async (n) => (n === "sample" ? sample : null) };
    };
    const { ctx, page: p, errs: e5 } = await open(browser, {}, stub);
    await p.waitForSelector("#ask-btn");
    await p.click("#ask-btn"); await p.waitForSelector("#ask-sheet");
    const sug = await p.locator("#ask-sugg button").count(); ok(sug >= 4 && sug <= 5, "four or five suggested questions (" + sug + ")");
    ok((await p.evaluate(() => window.__calls.length)) === 0, "nothing is sent until she taps");
    await screen(p, "12-ask-sheet-stub");
    await p.locator("#ask-sugg button").first().click();
    await p.waitForFunction(() => /buildings/.test(document.getElementById("ask-a").textContent));
    const garages = D.buildings.filter((b) => b.facts.parking && b.facts.parking.kind === "garage").length;
    ok((await p.locator("#ask-a").innerText()) === "<b>" + garages + "</b> buildings", "the answer is shown as plain text and the lookup read the page's data");
    ok((await p.locator("#ask-a b").count()) === 0, "no markup from an answer reaches the page");
    const call = await p.evaluate(() => window.__calls[0]);
    ok(JSON.stringify(call.tools) === JSON.stringify(["list_buildings", "get_building", "compare"]) && call.cache === undefined, "three lookups are offered, and no cache option with tools");
    ok(/two or three plain sentences/.test(call.input) && /That isn't in what I have/.test(call.input) && /ONLY from the building data/.test(call.input), "the instruction is in the input");
    const one = await p.evaluate((id) => window.__conciergeLookups.get_building({ id }), D.buildings[0].id);
    ok(one.name === D.buildings[0].name && one.apartments.length === D.buildings[0].apartments.length, "get_building");
    const cmp = await p.evaluate((ids) => window.__conciergeLookups.compare({ ids }), [D.buildings[0].id, D.buildings[1].name]);
    ok(cmp.buildings.length === 2, "compare takes ids or names");
    await p.evaluate(() => { window.__decline = true; });
    await p.fill("#ask-q", "Which is the quietest?"); await p.click("#ask-send");
    await p.waitForFunction(() => !document.querySelector("#ask-btn,#ask-sheet"));
    await p.click('#app [data-act="start"]');
    ok((await p.locator("#ask-btn,#ask-sheet").count()) === 0, "after a decline the feature is gone for good");
    ok(e5.length === 0, "errors (ask): " + e5.join(" || ")); await ctx.close();
    const nt = await open(browser, {}, "window.__noTools=true;(" + stub.toString() + ")()");
    await nt.page.waitForSelector("#ask-btn"); await nt.page.click("#ask-btn"); await nt.page.locator("#ask-sugg button").first().click();
    await nt.page.waitForFunction(() => window.__calls.length === 1);
    const c2 = await nt.page.evaluate(() => window.__calls[0]);
    ok(c2.tools.length === 0 && c2.input.includes(D.buildings[0].name) && /rent from \| total with utilities and fees from/.test(c2.input), "without tools the prompt carries a table of the buildings");
    ok(nt.errs.length === 0, "errors (ask, no tools): " + nt.errs.join(" || ")); await nt.ctx.close();
    const none = await open(browser, {}, () => { window.claude = { use: async () => null }; });
    await none.page.waitForTimeout(300); ok((await none.page.locator("#ask-btn").count()) === 0, "use() resolving null leaves no trace"); await none.ctx.close(); }

  await browser.close();
  console.log(checks + " checks passed; screenshots in site/screens/concierge-*.png");
})().catch((e) => { console.error("FAILED: " + (e && e.message || e)); process.exit(1); });
