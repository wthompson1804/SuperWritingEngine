/* Walk through the short page (version 2) the way Lamia would, on a phone:  node scripts/concierge_walkthrough_test.js
   Build first: python3 scripts/build_concierge.py. Opens site/dist/concierge.html from disk, no network (the font
   stylesheet request is answered with an empty file). Writes site/screens/concierge2-*.png at 2x.
   Runs at 390 x 844 and 360 x 780: every question answered; only the must-haves answered; must-haves that leave few
   (and none); a place with Life here and its sources; save three; the bar "My list · 3" on every screen; My list;
   Compare with two and with three columns; Choose this one; the tour plan. Then See everything, storage blocked, the
   dark theme, a 320px phone, the version 1 fallback when the data has no questions, and Ask against a stand-in.
   Checks on every screen: no console or page errors, no network, no sideways scroll, no rent above meta.rent_limit,
   none of the banned words, no trace of "Ask the concierge" outside a Claude viewer, every target at least 44px, the
   bar never covering the end of the page, and the toast never under the bar. */
"use strict";
const { chromium } = require("playwright");
const path = require("path"), fs = require("fs"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const PAGE = "file://" + path.join(ROOT, "site", "dist", "concierge.html");
const SHOTS = path.join(ROOT, "site", "screens");
const BANNED = /\ball-in\b|\bcap\b|\bunits?\b|\bgate\b|\bwe\b|net-effective|everything included|\bcrimes?\b/i;
const KEY = "lamia-concierge-v2";
let checks = 0;
const ok = (cond, msg) => { assert(cond, msg); checks++; };

/* the match logic, straight out of the page */
const html = fs.readFileSync(path.join(ROOT, "site", "concierge.html"), "utf8");
const mod = { exports: {} };
new Function("module", /<script id="match-logic">([\s\S]*?)<\/script>/.exec(html)[1])(mod);
const M = mod.exports;

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
let prefix = "";
async function screen(page, name, full) { await page.waitForTimeout(240); await page.screenshot({ path: path.join(SHOTS, "concierge2-" + prefix + name + ".png"), fullPage: !!full }); }
async function sheetShot(page, name) {
  /* a full-length picture of the open sheet: let the page grow to the sheet's height for the shot */
  const h = await page.evaluate(() => { const s = document.getElementById("sheet"); return s ? s.scrollHeight : 0; });
  const vp = page.viewportSize();
  if (h > vp.height) {
    await page.setViewportSize({ width: vp.width, height: Math.min(h, 6000) });
    await page.waitForTimeout(200);
    await page.screenshot({ path: path.join(SHOTS, "concierge2-" + prefix + name + ".png") });
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
      barTop: bar ? bar.getBoundingClientRect().top : null,
      padOk: (() => {   /* the end of the page can scroll clear of the bar */
        if (!bar) return true;
        const kids = [...scope.querySelectorAll("*")].filter(vis); if (!kids.length) return true;
        const scroller = sheet || document.scrollingElement;
        const maxScroll = scroller.scrollHeight - scroller.clientHeight;
        const lastBottom = Math.max(...kids.map((e) => e.getBoundingClientRect().bottom)) + (sheet ? sheet.scrollTop : window.scrollY);
        const visibleBottomAtEnd = maxScroll + (sheet ? sheet.clientHeight : window.innerHeight);
        return lastBottom <= visibleBottomAtEnd - bar.offsetHeight + 1;
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

(async () => {
  fs.mkdirSync(SHOTS, { recursive: true });
  const built = path.join(ROOT, "site", "dist", "concierge.html");
  assert(fs.existsSync(built), "site/dist/concierge.html is missing: run python3 scripts/build_concierge.py");
  const D = JSON.parse(/window\.CONCIERGE_DATA=(\{[\s\S]*?\});<\/script>/.exec(fs.readFileSync(built, "utf8"))[1]);
  const LIMIT = D.meta.rent_limit, QS = M.questionsOf(D), CFG = M.config(D), B = M.prepare(D), NB = D.buildings.length;
  ok(Array.isArray(D.questions) && D.questions.length, "the built data has questions (else only the fallback is tested)");
  const byId = Object.fromEntries(D.buildings.map((b) => [b.id, b]));
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
  const nice = (d) => { const m = /^(\d{4})-(\d\d)-(\d\d)/.exec(d || ""); return m ? MONTHS[+m[2] - 1] + " " + +m[3] : null; };
  const isToday = (a) => a.checked && (a.checked.status === "confirmed_today" || a.checked.status === "price_changed_today");
  const expectChecked = (b) => {
    const ap = b.apartments.filter((a) => a.checked && a.checked.status); if (!ap.length) return null;
    const n = ap.filter(isToday).length;
    if (n === b.apartments.length) return "Confirmed on the building's site today";
    if (n > 0) return "Some apartments confirmed today";
    const d = ap.map((a) => a.checked.date).filter(Boolean).sort().pop();
    return (nice(d) ? "Last seen " + nice(d) + ". " : "Not re-read today. ") + "Ask if it is still offered.";
  };
  const browser = await chromium.launch();

  /* answer the questions on screen. pickFor(q, counts) returns an answer id, an array (pick_two) or null (skip). */
  async function answerAll(page, pickFor, opts) {
    opts = opts || {};
    const answers = {};
    for (let i = 0; i < QS.length; i++) {
      const q = QS[i];
      await page.waitForSelector("#q-h");
      await page.mouse.move(1, 1); await page.waitForTimeout(30);
      ok((await page.locator(".qtop").innerText()).includes("Question " + (i + 1) + " of " + QS.length), "progress line on question " + (i + 1));
      ok((await page.locator('.prog[role="progressbar"]').getAttribute("aria-valuenow")) === String(i), "progress bar value");
      const want = M.countFits(B, QS, answers, CFG);
      const fc = await page.locator("#fitcount").innerText();
      ok(new RegExp("^" + want + "\\s+of " + NB + " places fit so far").test(fc.replace(/\n/g, " ")), q.id + ": live count says " + fc + ", want " + want);
      ok((await page.locator('#app [data-act="q-skip"]').count()) === (q.must_have ? 0 : 1), q.id + ": Skip this one only on questions that are not must-haves");
      const counts = {};
      if (q.kind !== "pick_two") {
        for (const a of q.answers) {
          const c = M.countFits(B, QS, Object.assign({}, answers, { [q.id]: a.id }), CFG); counts[a.id] = c;
          const btn = page.locator('#app [data-act="qa"][data-v="' + a.id + '"]');
          ok((await btn.locator(".none").count()) === (c === 0 ? 1 : 0), q.id + "/" + a.id + ": 'None fit' label iff it leaves none (" + c + ")");
          if (!opts.fast) {
            await btn.hover();
            const t = (await page.locator("#fitcount").innerText()).replace(/\n/g, " ");
            ok(new RegExp("^" + c + "\\s+of " + NB).test(t), q.id + "/" + a.id + ": hover shows " + c + " (got " + t + ")");
          }
        }
        if (!opts.fast) { await page.mouse.move(2, 2); await page.locator("#app h1").hover(); }
      }
      if (opts.shot && opts.shot[q.id]) await screen(page, opts.shot[q.id]);
      const choice = pickFor(q, counts);
      if (choice == null) { await act(page, "q-skip"); continue; }
      if (q.kind === "pick_two") {
        ok(await page.locator('#app [data-act="pick-done"]').isDisabled(), "Continue waits for a pick");
        for (const id of choice) await act(page, "pick", id);
        if (choice.length === 2) {   /* a third tap is refused */
          const third = q.answers.find((a) => !choice.includes(a.id));
          await act(page, "pick", third.id);
          ok((await page.locator('#app .pchip[aria-pressed="true"]').count()) === 2, "at most two chips");
          await toastClear(page);
        }
        if (opts.shot && opts.shot[q.id + ":picked"]) await screen(page, opts.shot[q.id + ":picked"]);
        await everyScreen(page, "question " + q.id, LIMIT);
        await act(page, "pick-done");
        answers[q.id] = choice;
      } else {
        await everyScreen(page, "question " + q.id, LIMIT);
        await act(page, "qa", choice);
        answers[q.id] = choice;
      }
    }
    return answers;
  }
  async function checkMatches(page, answers, label) {
    await page.waitForSelector("#app .kicker");
    const R = M.match(B, QS, answers, CFG);
    const got = await page.locator("#mlist > li.mcard").evaluateAll((els) => els.map((e) => e.getAttribute("data-building")));
    ok(JSON.stringify(got) === JSON.stringify(R.fits.map((r) => r.b.id)), label + ": the matches are in the match function's order");
    const failIds = await page.locator("#misfit .frow-x").evaluateAll((els) => els.map((e) => e.getAttribute("data-building")));
    ok(JSON.stringify(failIds) === JSON.stringify(R.fails.map((r) => r.b.id)), label + ": the places that do not fit are all in the collapsed group");
    ok(!got.some((id) => failIds.includes(id)), label + ": no failing place in the main list");
    if (R.fails.length) {
      ok((await page.locator("#misfit summary").innerText()).includes("(" + R.fails.length + ")"), label + ": the group says how many");
      for (const r of R.fails) ok((await page.locator('#misfit .frow-x[data-building="' + r.b.id + '"] .why').count()) === r.failed.length, label + ": a reason per missed must-have on " + r.b.id);
    }
    const best = await page.locator("#mlist > li .bestflag").count();
    ok(best === Math.min(3, R.fits.length), label + ": the top three are marked Best fit (" + best + ")");
    for (const r of R.fits) {
      const card = page.locator('#mlist > li[data-building="' + r.b.id + '"]');
      const chips = await card.locator(".chips li").count(), miss = await card.locator(".missc").count();
      ok(chips <= 3 && miss <= 1, label + ": at most three chips and one amber chip");
      ok(chips === M.chips(r.b, QS, answers, 3).length, label + ": the chips are the ones the data gives for her answers");
      const pair = await card.locator(".pair").innerText();
      ok(/Rent/.test(pair) && /Total with utilities and fees/.test(pair), label + ": rent and total together");
      const want = expectChecked(byId[r.b.id]), gotc = await card.locator(".chk").allInnerTexts();
      ok(want ? gotc.length === 1 && gotc[0].replace(/^\S+\s/, "") === want : gotc.length === 0, label + ": checked line on " + r.b.id);
      ok((await card.locator('[data-act="save"]').count()) === 1, label + ": a Save button on each card");
      if (r.b.experience_line) ok((await card.locator(".xline").innerText()) === r.b.experience_line, label + ": the experience line on the card");
      ok((await card.locator(".badge").count()) === 1, label + ": an experience badge on the card");
    }
    return R;
  }

  /* ================= 390 x 844 and 360 x 780: the main walk ================= */
  for (const vp of [{ width: 390, height: 844, p: "" }, { width: 360, height: 780, p: "360-" }]) {
    prefix = vp.p;
    const { ctx, page, errs, net } = await open(browser, { viewport: { width: vp.width, height: vp.height } });
    const L = "@" + vp.width + " ";
    await everyScreen(page, L + "welcome", LIMIT);
    await screen(page, "01-welcome");
    ok(await page.locator('#app [data-act="all"]').isVisible(), "See everything on the first screen");
    ok(await page.locator('#app [data-act="stories"]').isVisible(), "the quiet link to the stories");
    if (!vp.p) {   /* the stories stay reachable from the welcome screen */
      await act(page, "stories"); await page.waitForSelector("#story-card");
      await everyScreen(page, L + "story", LIMIT); await screen(page, "02-story");
      await act(page, "story-next", null, "#sheet"); await screen(page, "02b-story-next");
      await page.keyboard.press("Escape"); ok((await page.locator("#sheet").count()) === 0, "Escape closes the story");
    }
    await act(page, "start");
    /* the example the data gives first, else the first answer of every question */
    const ex = (D.meta.matching_examples || [])[0];
    const plan = ex ? ex.answers : {};
    const answers = await answerAll(page, (q) => {
      if (plan[q.id] !== undefined) return plan[q.id];
      return q.kind === "pick_two" ? q.answers.slice(0, 2).map((a) => a.id) : q.answers[0].id;
    }, { fast: !!vp.p, shot: vp.p ? { [QS[0].id]: "03-question" } : { [QS[0].id]: "03-question-first", [(QS.find((q) => q.must_have) || QS[0]).id]: "03b-question-must-have", [(QS.find((q) => q.kind === "pick_two") || QS[0]).id + ":picked"]: "03c-question-pick-two" } });
    if (ex) ok(JSON.stringify(M.match(B, QS, answers, CFG).fits.map((r) => r.b.id)) === JSON.stringify(ex.expected_fits || ex.order), "the walk reproduces the data's first example");
    const R = await checkMatches(page, answers, L + "all answered");
    await everyScreen(page, L + "matches", LIMIT);
    await screen(page, "04-matches"); if (!vp.p) await screen(page, "04-matches-full", true);
    if (R.fails.length) { await page.click("#misfit summary"); await everyScreen(page, L + "misfit open", LIMIT); if (!vp.p) { await page.locator("#misfit").scrollIntoViewIfNeeded(); await screen(page, "04b-matches-misfit"); } }
    ok((await page.locator("#savebar").count()) === 0, "no bar before anything is saved");

    /* open the best fit */
    const first = R.fits[0] ? R.fits[0].b : R.fails[0].b;
    await page.click('#app [data-act="open"][data-id="' + first.id + '"]');
    await page.waitForSelector("#sheet .place");
    ok((await page.locator("#sheet .xbadge").count()) === 1, "the experience badge on the place");
    if (first.experience_line) ok((await page.locator("#sheet .xbadge small").innerText()) === first.experience_line, "experience_line on the place");
    const life = (first.life_here || []).filter((m) => m.text);
    ok((await page.locator("#sheet .life .moment").count()) === life.length, "one Life here section per moment in the data (" + life.length + ")");
    if (life.length) {
      ok((await page.locator("#sheet .life h2").innerText()) === "Life here", "Life here heading");
      const named = life.flatMap((m) => (m.places || []).map((p) => p.name)).filter((n) => life.some((m) => m.text.includes(n)));
      if (named.length) ok((await page.locator("#sheet .moment p b").allInnerTexts()).includes(named[0]), "place names are bold");
      const nSrc = await page.locator("#sheet details.src").count();
      ok(nSrc === life.filter((m) => (m.sources || []).some((s) => /^https?:/.test(s.url || ""))).length, "a Sources disclosure per sourced moment");
      if (nSrc) {
        await page.locator("#sheet details.src summary").first().click();
        const a = page.locator("#sheet details.src[open] a").first();
        ok((await a.getAttribute("target")) === "_blank" && /^https?:/.test(await a.getAttribute("href")), "sources are links that open a new tab");
      }
    }
    const labels = await page.locator("#sheet .facts .l").allInnerTexts();
    ok(JSON.stringify(labels) === JSON.stringify(["Rent", "Total with utilities and fees", "Drive to Mom and Dad", "Parking", "Dog"]), "the five facts: " + labels.join(" / "));
    ok((await page.locator("#sheet .pos").count()) >= 2, "position markers");
    ok((await page.locator('#sheet [data-act="save"]').count()) === 2, "Save at the top and the bottom of a place");
    ok((await page.locator("#sheet img").count()) === 0, "no photos copied, only a link");
    const photo = page.locator('#sheet a:has-text("See photos")');
    if (await photo.count()) ok((await photo.getAttribute("target")) === "_blank", "See photos opens a new tab");
    await everyScreen(page, L + "place", LIMIT);
    await screen(page, "05-place");
    if (!vp.p) { for (const d of await page.locator("#sheet details.more").all()) await d.locator("summary").click(); await everyScreen(page, L + "place, all open", LIMIT); await sheetShot(page, "05b-place-full"); }
    /* the badge opens that experience's story */
    if (!vp.p && await page.locator('#sheet [data-act="story"]').count()) {
      await page.click('#sheet [data-act="story"]'); await page.waitForSelector("#story-card"); await everyScreen(page, L + "story from badge", LIMIT);
      await screen(page, "05c-story-from-badge"); await act(page, "back", null, "#sheet"); await page.waitForSelector("#sheet .place");
    }
    /* save it from the top */
    await page.locator('#sheet [data-act="save"]').first().click();
    await toastClear(page);
    await barSays(page, 1, "after one save");
    ok(await page.locator("#bar-compare").isDisabled(), "Compare waits for a second place");
    await everyScreen(page, L + "place saved", LIMIT);
    await screen(page, "05d-place-saved");
    await act(page, "back", null, "#sheet");
    /* save two more from the cards */
    const pool = R.fits.concat(R.fails).map((r) => r.b.id).filter((id) => id !== first.id);
    for (const id of pool.slice(0, 2)) {
      const btn = page.locator('[data-act="save"][data-id="' + id + '"]').first();
      if (!(await btn.isVisible())) await page.click("#misfit summary");
      await btn.scrollIntoViewIfNeeded(); await btn.click();
    }
    await toastClear(page);
    await barSays(page, 3, "matches");
    ok(!(await page.locator("#bar-compare").isDisabled()), "Compare is ready with three saved");
    await everyScreen(page, L + "matches with three saved", LIMIT);
    await screen(page, "06-matches-saved");
    let st = await state(page); ok(st.saved.length === 3, "three saved");
    /* the bar is on every screen */
    await page.click('#app [data-act="open"][data-id="' + pool[0] + '"]'); await barSays(page, 3, "a place"); await act(page, "back", null, "#sheet");
    await act(page, "all"); await barSays(page, 3, "See everything"); await everyScreen(page, L + "everything", LIMIT); await act(page, "all-close");
    await act(page, "redo"); await barSays(page, 3, "a question"); await everyScreen(page, L + "question with bar", LIMIT); if (!vp.p) await screen(page, "06b-question-with-bar");
    for (let i = 0; i < QS.length; i++) {   /* her answers are remembered: Continue / the pressed answer moves on */
      const q = QS[i];
      if (q.kind === "pick_two") { if (answers[q.id]) await act(page, "pick-done"); else await act(page, "q-skip"); }
      else if (answers[q.id]) await act(page, "qa", answers[q.id]); else await act(page, "q-skip");
    }
    await checkMatches(page, answers, L + "after changing nothing");

    /* My list */
    await page.click("#bar-list"); await page.waitForSelector("#sheet .saved");
    ok((await page.locator("#sheet .srow").count()) === 3, "three rows in My list");
    ok((await page.locator('#sheet .srow [data-act="unsave"]').count()) === 3 && (await page.locator('#sheet .srow [data-act="tour"]').count()) === 3, "Remove and Add to tour plan on each row");
    await everyScreen(page, L + "my list", LIMIT); await screen(page, "07-my-list");
    await page.locator("#sheet .srow input[type=checkbox]").nth(0).click();
    await page.locator("#sheet .srow input[type=checkbox]").nth(1).click();
    ok((await page.locator("#bar-compare").innerText()).trim() === "Compare 2", "Compare counts the ticked two");
    await screen(page, "07b-my-list-ticked");
    await page.click("#bar-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "2", "two columns");
    await everyScreen(page, L + "compare 2", LIMIT);
    const rowsLabels = (await page.locator("#cmp > .crow .cl").allTextContents());
    ok(rowsLabels[0] === "Rent" || !rowsLabels.includes("Rent"), "rent first when it differs");
    const allLabels = await page.locator("#cmp .crow .cl").allTextContents();
    const visitQ = QS.find((q) => q.id === "visits"), pm = visitQ ? M.perMonth(M.chosen(visitQ, answers)[0]) : null;
    ok(allLabels.some((l) => pm ? /^A month of visits/.test(l) : /^Each visit/.test(l)), "the visits row follows her answer (" + pm + " a month)");
    if (pm) {
      const ids2 = (await state(page)).ticked, b0 = byId[ids2[0]], mins = pm * b0.facts.drive_min * 2;
      const cell = await page.evaluate(() => { const r = [...document.querySelectorAll("#cmp .crow")].find((x) => /^A month of visits/.test(x.querySelector(".cl").textContent)); return r ? r.querySelector(".cells > div").textContent : "(no row)"; });
      const r5 = Math.round(mins / 5) * 5, h = Math.floor(r5 / 60), m = r5 % 60;
      const want = h ? h + " h" + (m ? " " + (m < 10 ? "0" : "") + m : "") : r5 + " min";
      ok(cell.includes("about " + want), "monthly visit time: " + cell.replace(/\n/g, " ") + " (want about " + want + ")");
    }
    ok((await page.locator("#cmp .cells .best").count()) >= 1, "the better value is marked");
    const sameRows = await page.locator("#same .crow").count();
    if (sameRows) ok(/Same for all \(\d+\)/.test(await page.locator("#same summary").innerText()), "identical rows are collapsed under Same for all");
    for (const row of await page.locator("#cmp > .crow").all()) {   /* no row in the open part is identical across all columns */
      const cells = await row.locator(".cells > div").allInnerTexts();
      ok(new Set(cells.map((c) => c.replace(/^[^:]*:\s*/, ""))).size > 1 || cells.length < 2, "a row that differs is in the open part");
    }
    await screen(page, "08-compare-2"); if (!vp.p) await sheetShot(page, "08b-compare-2-full");
    await act(page, "back", null, "#sheet");   /* back to My list */
    await page.waitForSelector("#sheet .saved");
    await page.locator("#sheet .srow input[type=checkbox]").nth(2).click();
    await page.click("#bar-compare"); await page.waitForSelector("#cmp");
    ok((await page.locator("#cmp").getAttribute("data-cols")) === "3", "three columns");
    const r3 = await everyScreen(page, L + "compare 3", LIMIT);
    ok(r3.sw <= vp.width, "three columns fit at " + vp.width + "px");
    const widths = await page.locator("#cmp .chead > div").evaluateAll((els) => els.map((e) => e.getBoundingClientRect().right));
    ok(Math.max(...widths) <= vp.width - 15, "the third column is on screen (" + Math.round(Math.max(...widths)) + ")");
    await screen(page, "09-compare-3"); await sheetShot(page, "09b-compare-3-full");
    if (sameRows || await page.locator("#same").count()) { await page.click("#same summary"); await everyScreen(page, L + "same for all open", LIMIT); }
    /* Choose this one */
    const pickId = (await state(page)).ticked[1];
    await page.click('#sheet [data-act="choose"][data-id="' + pickId + '"]');
    await toastClear(page);
    ok((await state(page)).tour.includes(pickId), "Choose this one adds it to the tour plan");
    ok((await page.locator('#sheet [data-act="untour"][data-id="' + pickId + '"]').count()) === 1, "the column says it is on the tour");
    await screen(page, "09c-compare-chosen");
    await page.click('#sheet [data-act="plan"]');
    await page.waitForSelector(".stop");
    ok((await page.locator(".stop").count()) === 1 && (await page.locator('.stop[data-stop="' + pickId + '"]').count()) === 1, "the tour plan has the chosen place");
    await barSays(page, 3, "tour plan");
    const stopB = byId[pickId], wantC = expectChecked(stopB);
    const firstQ = (await page.locator(".stop ol li").allInnerTexts())[0];
    if (wantC && /^(Last seen|Not re-read)/.test(wantC)) ok(firstQ === "Is this apartment still offered, and at what rent?", "a last-seen place asks first whether it is still offered");
    const planText = (await everyScreen(page, L + "plan", LIMIT)).text;
    D.buildings.forEach((b) => { const c = b.contact || {}; if (c.private && c.office_phone) ok(!planText.includes(c.office_phone), "a private number is shown"); });
    await screen(page, "10-plan"); if (!vp.p) await screen(page, "10b-plan-full", true);
    /* a fourth save, then a fourth tick is refused */
    await act(page, "matches");
    const fourth = pool[2];
    const fb = page.locator('[data-act="save"][data-id="' + fourth + '"]').first();
    if (!(await fb.isVisible())) await page.click("#misfit summary");
    await fb.scrollIntoViewIfNeeded(); await fb.click();
    await barSays(page, 4, "four saved");
    await page.click("#bar-list"); await page.waitForSelector("#sheet .saved");
    await page.locator("#sheet .srow input[type=checkbox]").nth(3).click();
    ok((await page.locator("#sheet .srow input:checked").count()) === 3, "a fourth tick is refused");
    ok(/Compare up to three/.test(await page.locator("#tickmsg").innerText()), "and it says why");
    await toastClear(page);
    await everyScreen(page, L + "fourth tick", LIMIT); await screen(page, "07c-my-list-fourth");
    /* untick all: with four saved and none ticked, Compare waits */
    while (await page.locator("#sheet .srow input:checked").count()) await page.locator("#sheet .srow input:checked").first().click();
    ok(await page.locator("#bar-compare").isDisabled(), "with four saved and none ticked Compare waits for ticks");
    await page.locator('#sheet [data-act="unsave"]').first().click();
    ok((await page.locator("#sheet .srow").count()) === 3, "Remove takes it off My list");
    await barSays(page, 3, "after Remove");
    await page.keyboard.press("Escape");
    ok((await page.locator("#sheet").count()) === 0, "Escape closes My list");
    ok(errs.length === 0, L + "console or page errors: " + errs.join(" || "));
    ok(net.length === 0, L + "network requests: " + net.join(", "));
    await ctx.close();
  }
  prefix = "";

  /* ================= only the must-haves: skip every question that can be skipped ================= */
  { const { ctx, page: p, errs: e2 } = await open(browser);
    await act(p, "start");
    const a = await answerAll(p, (q) => q.must_have ? q.answers[q.answers.length - 1].id : null, { fast: true });
    QS.filter((q) => !q.must_have).forEach((q) => ok(a[q.id] === undefined, "skipped " + q.id));
    const R = await checkMatches(p, a, "skip all");
    await everyScreen(p, "skip all matches", LIMIT); await screen(p, "11-skip-all-matches");
    if (R.fits.length >= 2) {   /* compare shows per-visit figures when she skipped the visits question */
      await p.locator('#mlist [data-act="save"]').nth(0).click(); await p.locator('#mlist [data-act="save"]').nth(1).click();
      await p.click("#bar-compare"); await p.waitForSelector("#cmp");
      const lab = await p.locator("#cmp .crow .cl").allTextContents();
      ok(lab.some((l) => /^Each visit/.test(l)) && !lab.some((l) => /^A month of visits/.test(l)), "per-visit figures when the visits question was skipped");
      await everyScreen(p, "skip all compare", LIMIT); await screen(p, "11b-skip-all-compare");
    }
    ok(e2.length === 0, "errors (skip all): " + e2.join(" || ")); await ctx.close(); }

  /* ================= must-haves that leave few, then none ================= */
  { const { ctx, page: p, errs: e3 } = await open(browser);
    await act(p, "start");
    /* the tightest answer that still leaves something, on every must-have */
    const a = await answerAll(p, (q, counts) => {
      if (!q.must_have) return null;
      const live = q.answers.filter((x) => counts[x.id] > 0).sort((x, y) => counts[x.id] - counts[y.id]);
      return (live[0] || q.answers[0]).id;
    }, { fast: true, shot: { [QS.filter((q) => q.must_have).slice(-1)[0].id]: "12-question-few-left" } });
    const R = await checkMatches(p, a, "few");
    ok(R.fits.length >= 1 && R.fits.length <= 5, "tight must-haves leave few (" + R.fits.length + ")");
    ok((await p.locator("#misfit .frow-x").count()) === NB - R.fits.length, "the rest are in the collapsed group");
    await p.click("#misfit summary");
    await everyScreen(p, "few", LIMIT); await screen(p, "12b-few-matches", true);
    /* now a must-have answer that leaves none */
    await act(p, "redo");
    let none = null;
    for (let i = 0; i < QS.length; i++) {
      const q = QS[i];
      await p.waitForSelector("#q-h");
      if (q.must_have && !none) {
        for (const x of q.answers) { if ((await p.locator('#app [data-act="qa"][data-v="' + x.id + '"] .none').count())) { none = x.id; break; } }
        if (!none && q.answers[0].filter) { await act(p, "qa", q.answers[0].id); continue; }   /* the tightest, to get there */
        if (none) { await screen(p, "12c-question-none-fit"); await act(p, "qa", none); continue; }
      }
      if (q.kind === "pick_two") await act(p, "q-skip");
      else if (a[q.id]) await act(p, "qa", a[q.id]); else await act(p, "q-skip");
    }
    if (none) {
      ok(/Nothing fits all of that/.test(await p.locator("#app h1").innerText()), "a plain screen when nothing fits");
      ok(await p.locator("#misfit").evaluate((d) => d.open), "the places that do not fit are open when nothing fits");
      await everyScreen(p, "none", LIMIT); await screen(p, "12d-none-fit");
    } else console.log("note: no answer here leaves none, so the empty screen was not reached");
    ok(e3.length === 0, "errors (few): " + e3.join(" || ")); await ctx.close(); }

  /* ================= See everything (filters, map) ================= */
  { const { ctx, page, errs } = await open(browser);
    await act(page, "all");
    await everyScreen(page, "everything", LIMIT);
    const box = await page.locator(".filter").boundingBox();
    ok(box && box.y < 500, "the filter is on the first screen of See everything");
    const total = await page.locator("#all-list .row").count();
    ok(total === NB, "every building is listed (" + total + ")");
    const slider = page.locator("#f-rent"), min = Number(await slider.getAttribute("min")), max = Number(await slider.getAttribute("max"));
    const mid = Math.round((min + (max - min) * 0.45) / 50) * 50;
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(mid));
    const fewer = await page.locator("#all-list .row").count();
    ok(fewer < total && fewer > 0, "the rent filter changes the list");
    await slider.evaluate((el, v) => { el.value = v; el.dispatchEvent(new Event("input", { bubbles: true })); }, String(max));
    await page.click('[data-act="f-beds"][data-v="0"]');
    ok((await page.locator("#all-list .row").count()) === D.buildings.filter((b) => b.apartments.some((a) => a.beds === 0)).length, "bedrooms filter");
    await page.click('[data-act="f-beds"][data-v="any"]');
    await page.click('#all-list .row >> nth=0'); await page.waitForSelector("#sheet .place");
    await page.locator('#sheet [data-act="save"]').last().click();
    await barSays(page, 1, "saved from See everything");
    await page.keyboard.press("Escape");
    ok(await page.locator("#all-list .row .tag.k").first().isVisible(), "the list marks a saved place");
    await screen(page, "13-everything");
    await page.click('.tabs [data-v="map"]'); await page.waitForSelector("#map-slot .hhm-svg"); await page.waitForTimeout(300);
    await everyScreen(page, "map", LIMIT); await screen(page, "13b-map");
    await page.click('.tabs [data-v="list"]'); await act(page, "all-close");
    ok(errs.length === 0, "errors (everything): " + errs.join(" || ")); await ctx.close(); }

  /* ================= storage unavailable ================= */
  { const { ctx, page: p, errs: e4 } = await open(browser, {}, () => { Object.defineProperty(window, "localStorage", { get() { throw new Error("blocked"); } }); });
    await act(p, "start");
    await answerAll(p, (q) => q.kind === "pick_two" ? null : q.answers[q.answers.length - 1].id, { fast: true });
    await p.locator('#mlist [data-act="save"]').first().click();
    await p.click("#bar-list"); await p.waitForSelector("#sheet .saved");
    await p.locator('#sheet [data-act="tour"]').first().click(); await p.click('#sheet [data-act="plan"]');
    ok((await p.locator(".stop").count()) === 1, "works with storage blocked");
    ok(e4.length === 0, "errors (no storage): " + e4.join(" || ")); await ctx.close(); }

  /* ================= dark theme, and a 320px phone ================= */
  { const { ctx, page: p, errs: e5 } = await open(browser, { colorScheme: "dark" });
    await screen(p, "14-dark-welcome");
    await act(p, "start"); await screen(p, "14b-dark-question");
    await answerAll(p, (q) => q.kind === "pick_two" ? q.answers.slice(0, 2).map((a) => a.id) : q.answers[q.answers.length - 1].id, { fast: true });
    await p.locator('#mlist [data-act="save"]').nth(0).click(); await p.locator('#mlist [data-act="save"]').nth(1).click();
    await screen(p, "14c-dark-matches");
    await p.locator('#mlist [data-act="open"]').first().click(); await p.waitForSelector("#sheet .place"); await screen(p, "14d-dark-place");
    await act(p, "back", null, "#sheet");
    await p.click("#bar-compare"); await p.waitForSelector("#cmp"); await screen(p, "14e-dark-compare");
    await everyScreen(p, "dark", LIMIT);
    ok(e5.length === 0, "errors (dark): " + e5.join(" || ")); await ctx.close();
    const small = await open(browser, { viewport: { width: 320, height: 568 } });
    await everyScreen(small.page, "320 welcome", LIMIT); await act(small.page, "start"); await everyScreen(small.page, "320 question", LIMIT);
    await answerAll(small.page, (q) => q.kind === "pick_two" ? q.answers.slice(0, 2).map((a) => a.id) : q.answers[q.answers.length - 1].id, { fast: true });
    await everyScreen(small.page, "320 matches", LIMIT);
    for (let i = 0; i < 3; i++) await small.page.locator('#mlist [data-act="save"]').nth(i).click();
    await small.page.click("#bar-compare"); await small.page.waitForSelector("#cmp");
    await everyScreen(small.page, "320 compare 3", LIMIT); await screen(small.page, "15-320-compare-3");
    ok(small.errs.length === 0, "errors (320): " + small.errs.join(" || ")); await small.ctx.close(); }

  /* ================= the data without questions: the version 1 either/or questions, then matches ================= */
  { const strip = () => { let d; Object.defineProperty(window, "CONCIERGE_DATA", { configurable: true, get() { return d; }, set(v) { if (v) { delete v.questions; } d = v; } }); };
    const { ctx, page: p, errs: e6 } = await open(browser, {}, strip);
    const EO = (D.either_or || []).slice(0, 3);
    await act(p, "start");
    for (let i = 0; i < EO.length; i++) { await p.waitForSelector("#q-h"); ok((await p.locator("#q-h").innerText()) === EO[i].question, "fallback question " + (i + 1)); await act(p, "qa", EO[i].id + ":a"); }
    await p.waitForSelector("#mlist");
    ok((await p.locator("#mlist > li").count()) === NB, "fallback: every place is a match");
    await everyScreen(p, "fallback", LIMIT); await screen(p, "16-fallback-matches");
    ok(e6.length === 0, "errors (fallback): " + e6.join(" || ")); await ctx.close(); }

  /* ================= Ask, against a stand-in for the viewer's Claude ================= */
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
    const { ctx, page: p, errs: e7 } = await open(browser, {}, stub);
    await p.waitForSelector("#ask-btn");
    await p.click("#ask-btn"); await p.waitForSelector("#ask-sheet");
    ok((await p.evaluate(() => window.__calls.length)) === 0, "nothing is sent until she taps");
    await p.locator("#ask-sugg button").first().click();
    await p.waitForFunction(() => /buildings/.test(document.getElementById("ask-a").textContent));
    const garages = D.buildings.filter((b) => b.facts.parking && b.facts.parking.kind === "garage").length;
    ok((await p.locator("#ask-a").innerText()) === "<b>" + garages + "</b> buildings", "the answer is plain text and the lookup read the page's data");
    const call = await p.evaluate(() => window.__calls[0]);
    ok(JSON.stringify(call.tools) === JSON.stringify(["list_buildings", "get_building", "compare"]), "three lookups");
    const withLife = D.buildings.find((b) => (b.life_here || []).length) || D.buildings[0];
    const one = await p.evaluate((id) => window.__conciergeLookups.get_building({ id }), withLife.id);
    ok(one.name === withLife.name && Array.isArray(one.life_here) && one.life_here.length === (withLife.life_here || []).length && one.fit, "get_building carries fit and life_here");
    const lst = await p.evaluate(() => window.__conciergeLookups.list_buildings({}));
    ok(lst.count === NB && "fits_her_answers" in lst.buildings[0], "list_buildings says whether each fits");
    await p.evaluate(() => { window.__decline = true; });
    await p.fill("#ask-q", "Which is the quietest?"); await p.click("#ask-send");
    await p.waitForFunction(() => !document.querySelector("#ask-btn,#ask-sheet"));
    await p.click('#app [data-act="start"]');
    ok((await p.locator("#ask-btn,#ask-sheet").count()) === 0, "after a decline the feature is gone");
    ok(e7.length === 0, "errors (ask): " + e7.join(" || ")); await ctx.close();
    const none = await open(browser, {}, () => { window.claude = { use: async () => null }; });
    await none.page.waitForTimeout(300); ok((await none.page.locator("#ask-btn").count()) === 0, "use() resolving null leaves no trace"); await none.ctx.close(); }

  await browser.close();
  console.log(checks + " checks passed; screenshots in site/screens/concierge2-*.png");
})().catch((e) => { console.error("FAILED: " + (e && e.message || e)); process.exit(1); });
