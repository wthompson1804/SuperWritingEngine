/* Walk through the short page (version 4) the way Lamia would, on a phone:  node scripts/concierge_walkthrough_test.js
   Build first: python3 scripts/build_concierge.py. Opens site/dist/concierge.html from disk, no network (the font
   stylesheet request is answered with an empty file). Writes site/screens/concierge41-*.png at 2x.
   At 390 x 844 and 360 x 780: every persona in meta.recommender_examples is played through the screen (eight choices
   between made-up apartments, tapping what the persona chose) and the page must show exactly the example's tasks, in
   the example's words, then its priorities and sentence on "Here's what you told me", then its three neighborhoods with
   their places, why and gives up, number 1 open and 2 and 3 closed. Then, on the first persona: Back undoes a choice;
   a place row opens the place sheet (Life here, the numbers, Save top and bottom, More like this at the bottom); save
   three; the bar on every screen; "Not quite" moves a priority and the places follow (the data's nudge example);
   My list; Compare with two and three; Choose this one; the tour plan; See everything with its filters, Show more and
   the map. Then: storage blocked, a reload, dark theme, a 320px phone, data with no recommender, and Ask against a
   stand-in for the viewer's Claude.
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
const KEY = "lamia-concierge-v4";
let checks = 0;
const ok = (cond, msg) => { assert(cond, msg); checks++; };
const said = (t) => String(t || "");   /* the page shows the model's sentences as they are */

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
async function screen(page, name, full) { await page.waitForTimeout(200); await page.screenshot({ path: path.join(SHOTS, "concierge41-" + prefix + name + ".png"), fullPage: !!full }); }
async function sheetShot(page, name) {
  const h = await page.evaluate(() => { const s = document.getElementById("sheet"); return s ? s.scrollHeight : 0; });
  const vp = page.viewportSize();
  if (h > vp.height) {
    await page.setViewportSize({ width: vp.width, height: Math.min(h, 7000) }); await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(SHOTS, "concierge41-" + prefix + name + ".png") });
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
const taskOnScreen = (page) => page.locator("#app [data-cand]").getAttribute("data-cand").then(Number);
async function tap(page, choice) {
  if (choice === "either") await page.click('#app button[data-act="cj"][data-v="either"]');
  else await page.click('#app .ct-pick[data-v="' + choice + '"], #app .apt[data-v="' + choice + '"]');
}
const shownTopFromState = (page) => page.evaluate(() => { const r = window.__conciergeRec(); return r && r.top[0] ? r.top[0][0] : null; });
/* what the results show: [[area, [building ids]]] */
const shownTop = (page) => page.evaluate(() => [...document.querySelectorAll("#app .hcard")].map((s) => [s.getAttribute("data-area"), [...s.querySelectorAll(".prow")].map((c) => c.getAttribute("data-id"))]));
/* save n places from the results: open each row (opening closed neighborhoods as needed) and Save in the sheet */
async function saveFromResults(page, n) {
  const ids = (await shownTop(page)).flatMap((t) => t[1]).slice(0, n);
  for (const id of ids) {
    const row = page.locator('#app .prow[data-id="' + id + '"]');
    if (!(await row.isVisible())) { const card = page.locator('#app .hcard:has(.prow[data-id="' + id + '"]) .hhead'); await card.click(); }
    await row.scrollIntoViewIfNeeded(); await row.click(); await page.waitForSelector("#sheet .place");
    await page.locator('#sheet [data-act="save"]').first().click();
    await page.click('#sheet [data-act="back"]');
  }
  return ids;
}

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
    const n = ex.answers.length;
    for (let i = 0; i < n; i++) {
      await page.waitForSelector("#app [data-cand]");
      const t = await taskOnScreen(page);
      ok(t === ex.expected_tasks[i], L + ex.persona + ": task " + (i + 1) + " is " + t + ", the example says " + ex.expected_tasks[i]);
      ok((await page.locator("#cj-step").innerText()).trim() === (i + 1) + " of " + n, "progress " + (i + 1) + " of " + n);
      if (ex.expected_tasks_shown) {   /* only the attributes that differ, in the task's order, with the example's words */
        const rows = await page.evaluate(() => [...document.querySelectorAll("#app .ct-row")].map((r) => { const c = r.querySelectorAll(".ct-c");
          return { attribute: r.getAttribute("data-label"), a: c[0].getAttribute("data-level"), b: c[1].getAttribute("data-level") }; }));
        const want = ex.expected_tasks_shown[i], wantRows = Array.isArray(want) ? want : want.rows;
        ok(JSON.stringify(rows) === JSON.stringify(wantRows), L + "task " + (i + 1) + " shows " + JSON.stringify(rows));
        if (!Array.isArray(want)) {
          const hl = await page.locator("#app .ct-pick .ap-hl").allTextContents();
          ok(JSON.stringify(hl) === JSON.stringify([want.headline_a, want.headline_b]), L + "task " + (i + 1) + " headlines " + hl.join(" / "));
        }
        ok((await page.locator("#app .same").count()) === 1, "a quiet Same for both line");
        const marks = await page.evaluate(() => [...document.querySelectorAll("#app .ct-row")].map((r) => [...r.querySelectorAll(".ct-c")].map((c) => c.classList.contains("up") ? "up" : "dn")));
        ok(marks.every((m) => m.length === 2 && m[0] !== m[1]), "each row: one side marked better, the other worse");
        ok(marks.some((m) => m[0] === "up") && marks.some((m) => m[0] === "dn"), "a trade-off: A better on one, worse on another");
        ok((await page.locator("#app .ct-pick .ap-hl").count()) === 2, "a headline on each side");
      }
      if (shots && i === 0) { await everyScreen(page, L + "choice", LIMIT); await screen(page, "02-choice"); }
      if (shots && i === 3) await screen(page, "02b-choice-4");
      await tap(page, ex.answers[i].choice);
    }
    await page.waitForSelector("#prio");
    ok((await page.locator("#app [data-cand]").count()) === 0, "no ninth choice");
    ok((await page.locator("#cf-h").innerText()).trim() === ex.expected_priorities_sentence, L + ex.persona + ": the sentence " + (await page.locator("#cf-h").innerText()));
    const order = await page.locator("#prio li").evaluateAll((els) => els.map((e) => e.getAttribute("data-feature")));
    ok(JSON.stringify(order) === JSON.stringify(ex.expected_priorities), L + ex.persona + ": the priorities in order");
    if (shots) { await everyScreen(page, L + "confirm", LIMIT); await screen(page, "03-confirm"); }
    await act(page, "confirm-yes");
    await page.waitForSelector("#app .hlist");
    const top = await shownTop(page);
    ok(JSON.stringify(top) === JSON.stringify(ex.expected_top), L + ex.persona + ": the three shown " + JSON.stringify(top));
    ok((await page.locator("#res-h").innerText()).trim() === ex.expected_priorities_sentence, "the results open with what she cares about");
    const exp = await page.locator("#app .hhead").evaluateAll((els) => els.map((e) => e.getAttribute("aria-expanded")));
    ok(JSON.stringify(exp) === JSON.stringify(["true", "false", "false"]), "exactly three neighborhoods: number 1 open, 2 and 3 closed");
    ok(top.length === 3 && top.every((t) => t[1].length === 3), L + ex.persona + ": exactly three buildings in each of the three");
    for (const [area] of ex.expected_top) {
      const card = page.locator('#app .hcard[data-area="' + area + '"]');
      if (ex.expected_why && ex.expected_why[area]) ok((await card.locator(".because .t").textContent()) === ex.expected_why[area], L + "why for " + area);
      if (ex.expected_gives_up) ok(ex.expected_gives_up[area] ? (await card.locator(".gives .t").textContent()) === ex.expected_gives_up[area] : (await card.locator(".gives").count()) === 0, L + "gives up for " + area);
    }
    ok(!(await page.locator('#app #whatif, #app [data-act="more"], #app [data-act="remove"], #app .thumb').count()), "no what-would-change, more like this or Not for me on the results");
    return top;
  }

  /* ================= 390 x 844 and 360 x 780 ================= */
  for (const vp of [{ width: 390, height: 844, p: "" }, { width: 360, height: 780, p: "360-" }]) {
    prefix = vp.p;
    const L = "@" + vp.width + " ";
    for (let e = 1; e < EX.length; e++) {   /* every persona, through the screen */
      const { ctx, page, errs, net } = await open(browser, { viewport: { width: vp.width, height: vp.height } });
      await playExample(page, EX[e], L, false);
      await everyScreen(page, L + EX[e].persona + " results", LIMIT);
      ok(errs.length === 0 && net.length === 0, L + EX[e].persona + ": errors or network " + errs.concat(net).join(" | "));
      await ctx.close();
    }
    const { ctx, page, errs, net } = await open(browser, { viewport: { width: vp.width, height: vp.height } });
    await everyScreen(page, L + "welcome", LIMIT);
    ok(await page.locator('#app [data-act="all"]').isVisible(), "See everything on the first screen");
    const intro = await page.locator(".hello").innerText();
    ok(/eight quick choices/i.test(intro) && /imaginary apartments/i.test(intro) && /trade-off/i.test(intro) && /teach the page/i.test(intro) &&
       /three neighborhoods/i.test(intro) && /three best buildings/i.test(intro) && /browse, search and filter/i.test(intro), "the first screen says what will happen and what is promised");
    ok((await page.locator("#app .btn").count()) === 1 && (await page.locator('#app .btn[data-act="start"]').count()) === 1, "one Start button");
    await screen(page, "01-welcome");
    const ex = EX[0];
    /* Back undoes an answer */
    await act(page, "start"); await page.waitForSelector("#app [data-cand]");
    await tap(page, ex.answers[0].choice); await page.waitForSelector("#app [data-cand]");
    ok((await taskOnScreen(page)) === ex.expected_tasks[1], "the second task");
    await act(page, "undo");
    ok((await taskOnScreen(page)) === ex.expected_tasks[0], "Back puts the first task back");
    ok(((await state(page)).cj || []).length === 0, "and forgets that answer");
    await act(page, "undo");
    ok((await page.locator(".hello").count()) === 1, "Back from the first task goes to the welcome");
    const top = await playExample(page, ex, L, true);
    await everyScreen(page, L + "results", LIMIT);
    await screen(page, "04-results"); await screen(page, "04b-results-full", true);
    /* number 2 opens on tap */
    await page.click('#app .hhead[data-v="1"]');
    ok((await page.locator('#app .hhead[data-v="1"]').getAttribute("aria-expanded")) === "true" && await page.locator("#hb-1").isVisible(), "a tap opens number 2");
    await everyScreen(page, L + "results, two open", LIMIT); if (!vp.p) await screen(page, "04c-results-two-open", true);
    await page.click('#app .hhead[data-v="1"]');
    /* a place row, and the place sheet with More like this at the bottom */
    const firstId = top[0][1][0], fb = byId[firstId];
    const rowText = await page.locator('#app .prow[data-id="' + firstId + '"]').innerText();
    ok(/Rent/.test(rowText) && /Total with utilities and fees/.test(rowText), "a place row pairs rent and total");
    await page.click('#app .prow[data-id="' + firstId + '"]'); await page.waitForSelector("#sheet .place");
    ok((await page.locator("#sheet .life .moment").count()) === (fb.life_here || []).filter((m) => m.text).length, "Life here");
    const labels = await page.locator("#sheet .facts .l").allInnerTexts();
    ok(JSON.stringify(labels) === JSON.stringify(["Rent", "Total with utilities and fees", "Drive to Mom and Dad", "Parking", "Dog"]), "the numbers: " + labels.join(" / "));
    ok((await page.locator('#sheet [data-act="save"]').count()) === 2, "Save at the top and the bottom of a place");
    ok((await page.locator("#sheet img").count()) === 0, "no photos copied");
    ok(/In your place 1 of 3/.test(await page.locator("#sheet").innerText()), "the place says which of her three it is in");
    const ml = await page.locator("#sheet #more-like .thumb").evaluateAll((els) => els.map((e) => e.getAttribute("data-id")));
    ok(ml.length === 3 && !ml.includes(firstId), "More like this at the bottom of a place: three others");
    await everyScreen(page, L + "place", LIMIT); await screen(page, "05-place");
    if (!vp.p) { for (const d of await page.locator("#sheet details.more").all()) await d.locator("summary").click(); await sheetShot(page, "05b-place-full"); }
    await page.locator("#sheet #more-like .thumb").first().click();
    ok((await page.locator("#sheet .place").getAttribute("data-building")) === ml[0], "a More like this row opens that place");
    await act(page, "back", null, "#sheet"); await act(page, "back", null, "#sheet");
    /* save three */
    ok((await page.locator("#savebar").count()) === 0, "no bar before anything is saved");
    await saveFromResults(page, 3);
    await toastClear(page); await barSays(page, 3, "results");
    await everyScreen(page, L + "results with three saved", LIMIT); await screen(page, "06-results-saved");
    /* Not quite: move one priority up, carry on, the places follow */
    await act(page, "restart"); await page.waitForSelector("#app [data-cand]"); await barSays(page, 3, "a choice");
    ok(((await state(page)).cj || []).length === 0, "Change my answers starts the choices again");
    await everyScreen(page, L + "choice with bar", LIMIT);
    const clear = await page.evaluate(() => { window.scrollTo(0, document.scrollingElement.scrollHeight); const bar = document.getElementById("savebar");
      const last = [...document.querySelectorAll('#app [data-act="cj"], #app [data-act="undo"]')].pop(); return !bar || last.getBoundingClientRect().bottom <= bar.getBoundingClientRect().top; });
    ok(clear, "with the bar showing, the last button scrolls clear of it");
    for (const a of ex.answers) { await page.waitForSelector("#app [data-cand]"); await tap(page, a.choice); }
    await page.waitForSelector("#prio");
    await act(page, "confirm-fix");
    ok((await page.locator("#prio .mv").count()) === 12, "a move up and down on every priority");
    if (ex.nudge_example) {
      const n = ex.nudge_example;
      await page.click('#app .mv[data-id="' + n.feature + '"][data-v="' + n.direction + '"]');
      ok((await page.locator("#cf-h").innerText()).trim() === n.priorities_sentence_after, "the sentence follows the move");
      await everyScreen(page, L + "fixing", LIMIT); await screen(page, "03b-confirm-not-quite");
      await act(page, "confirm-yes"); await page.waitForSelector("#app .hlist");
      ok(JSON.stringify(await shownTop(page)) === JSON.stringify(n.expected_top_after), "the three places follow the move");
      await page.evaluate(() => window.scrollTo(0, 0));
      await act(page, "restart"); for (const a of ex.answers) { await page.waitForSelector("#app [data-cand]"); await tap(page, a.choice); }
      await page.waitForSelector("#prio"); await act(page, "confirm-yes"); await page.waitForSelector("#app .hlist");
      ok(JSON.stringify(await shownTop(page)) === JSON.stringify(ex.expected_top), "answering again without the move gives the first three");
    } else { await act(page, "confirm-yes"); await page.waitForSelector("#app .hlist"); }
    /* My list, Compare, tour plan */
    await page.click("#bar-list"); await page.waitForSelector("#sheet .saved");
    ok((await page.locator("#sheet .srow").count()) === 3, "three rows in My list");
    await everyScreen(page, L + "my list", LIMIT); await screen(page, "07-my-list");
    await page.locator("#sheet .srow input[type=checkbox]").nth(0).click();
    await page.locator("#sheet .srow input[type=checkbox]").nth(1).click();
    await page.click("#bar-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "2", "two columns");
    await everyScreen(page, L + "compare 2", LIMIT); await screen(page, "08-compare-2");
    await act(page, "back", null, "#sheet"); await page.waitForSelector("#sheet .saved");
    await page.locator("#sheet .srow input[type=checkbox]").nth(2).click();
    await page.click("#bar-compare"); await page.waitForSelector("#cmp");
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
    await act(page, "results"); await page.waitForSelector("#app .hlist");
    /* See everything */
    await act(page, "all"); await barSays(page, 3, "See everything");
    await everyScreen(page, L + "everything", LIMIT);
    ok((await page.locator("#all-list .row").count()) === NB, "every building is listed");
    /* search: by name, street and town, instant */
    ok(await page.locator("#f-q").isVisible(), "a visible search box");
    const probe = D.buildings.find((b) => b.city) || D.buildings[0];
    const norm = (t) => String(t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
    for (const q of [probe.city, probe.address, probe.name]) {
      await page.fill("#f-q", q); await page.waitForTimeout(80);
      const ids = await page.locator("#all-list .row").evaluateAll((els) => els.map((e) => e.getAttribute("data-id")));
      const want = D.buildings.filter((b) => { const h = " " + norm([b.name, b.address, b.city, b.state, b.zip, b.postal_code, b.neighborhood_name, (HB[b.neighborhood_id] || {}).name, (HB[b.group_id] || {}).name].join(" ")) + " "; return norm(q).split(" ").every((w) => h.includes(" " + w)); }).length;
      ok(ids.includes(probe.id) && ids.length === want, "search '" + q + "' finds it (" + ids.length + " of " + want + ")");
      ok((await page.locator("#f-count").innerText()) === "Showing " + ids.length + " of " + NB + " buildings", "the count follows the search");
    }
    if (!vp.p || true) { await page.fill("#f-q", probe.city); await page.waitForTimeout(80); await everyScreen(page, L + "search", LIMIT); await screen(page, "12c-browse-search"); }
    await page.fill("#f-q", "zzzz qqqq"); await page.waitForTimeout(80);
    ok(/Nothing matches/.test(await page.locator("#all-list").innerText()), "no match says so");
    await page.fill("#f-q", ""); await page.waitForTimeout(80);
    ok((await page.locator("#all-list .row").count()) === NB, "clearing the search brings every building back");
    const box = await page.locator(".filter").boundingBox(); ok(box && box.y < 600, "the filter is near the top of See everything");
    const slider = page.locator("#f-rent"), min = Number(await slider.getAttribute("min")), max = Number(await slider.getAttribute("max"));
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(Math.round((min + (max - min) * 0.45) / 50) * 50));
    await page.waitForTimeout(80);
    const fewer = await page.locator("#all-list .row").count(); ok(fewer < NB && fewer > 0, "the rent filter changes the list");
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(max));
    await page.waitForTimeout(80);
    ok((await page.locator("#all-list .row").count()) === NB, "back to every building");
    /* at most three rows show per place until "Show N more" */
    const over = await page.evaluate(() => [...document.querySelectorAll("#all-list .grp")].filter((g) => [...g.querySelectorAll(".row")].filter((r) => r.checkVisibility()).length > 3).length);
    ok(over === 0, "no place shows more than three rows before Show more");
    const moreBtn = page.locator('#all-list [data-act="grp-more"]').first();
    if (await moreBtn.count()) {
      const ctl = await moreBtn.getAttribute("aria-controls"), hidden = await page.locator("#" + ctl.replace(/:/g, "\\:") + " .row").count();
      ok(/^Show \d+ more in /.test(await moreBtn.innerText()) && Number(/\d+/.exec(await moreBtn.innerText())[0]) === hidden, "Show N more says how many");
      await moreBtn.click();
      ok((await moreBtn.getAttribute("aria-expanded")) === "true" && (await page.locator("#" + ctl.replace(/:/g, "\\:")).isVisible()), "Show more opens the rest");
      await everyScreen(page, L + "show more", LIMIT);
      await moreBtn.click();
    }
    /* the state filter */
    const states = [...new Set(D.buildings.map((b) => b.state || (HB[b.neighborhood_id] || {}).state).filter(Boolean))].sort();
    if (states.length > 1) {
      await page.click('[data-act="f-state"][data-v="' + states[0] + '"]');
      ok((await page.locator("#all-list .row").count()) === D.buildings.filter((b) => (b.state || (HB[b.neighborhood_id] || {}).state) === states[0]).length, "state filter");
      await page.click('[data-act="f-state"][data-v="any"]');
    }
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
    await saveFromResults(p, 1);
    await p.click("#bar-list"); await p.waitForSelector("#sheet .saved");
    await p.locator('#sheet [data-act="tour"]').first().click(); await p.click('#sheet [data-act="plan"]');
    ok((await p.locator(".stop").count()) === 1, "works with storage blocked");
    ok(errs.length === 0, "errors (no storage): " + errs.join(" || ")); await ctx.close(); }

  /* ================= her choices survive a reload ================= */
  { const { ctx, page: p, errs } = await open(browser);
    const top = await playExample(p, EX[1] || EX[0], "reload ", false);
    await p.reload(); await p.waitForSelector("#app .hlist");
    ok(JSON.stringify(await shownTop(p)) === JSON.stringify(top), "the three places come back after a reload");
    ok(errs.length === 0, "errors (reload): " + errs.join(" || ")); await ctx.close(); }

  /* ================= dark theme, and a 320px phone ================= */
  { const { ctx, page: p, errs } = await open(browser, { colorScheme: "dark" });
    await screen(p, "13-dark-welcome");
    await act(p, "start"); await p.waitForSelector("#app [data-cand]"); await screen(p, "13b-dark-choice");
    await act(p, "undo");
    await playExample(p, EX[0], "dark ", false);
    await saveFromResults(p, 2);
    await screen(p, "13c-dark-results");
    await p.locator('#app .prow').first().click(); await p.waitForSelector("#sheet .place"); await screen(p, "13d-dark-place");
    await act(p, "back", null, "#sheet");
    await p.click("#bar-compare"); await p.waitForSelector("#cmp"); await screen(p, "13e-dark-compare");
    await everyScreen(p, "dark", LIMIT);
    ok(errs.length === 0, "errors (dark): " + errs.join(" || ")); await ctx.close();
    const small = await open(browser, { viewport: { width: 320, height: 568 } });
    await everyScreen(small.page, "320 welcome", LIMIT); await act(small.page, "start"); await small.page.waitForSelector("#app [data-cand]");
    await everyScreen(small.page, "320 choice", LIMIT); await screen(small.page, "14-320-choice");
    await act(small.page, "undo");
    await playExample(small.page, EX[0], "320 ", false);
    await everyScreen(small.page, "320 results", LIMIT);
    await saveFromResults(small.page, 3);
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
  console.log(checks + " checks passed; screenshots in site/screens/concierge41-*.png");
})().catch((e) => { console.error("FAILED: " + (e && e.message || e)); process.exit(1); });
