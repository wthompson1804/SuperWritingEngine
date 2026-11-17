/* Tests for the match logic of the short page (version 2). Plain Node, no packages:  node scripts/test_concierge_pick.js
   The file keeps its version 1 name so scripts/verify_concierge.py runs it unchanged; it now tests ConciergeMatch.
   The logic is read straight out of site/concierge.html (the <script id="match-logic"> block), so the page and the test
   cannot drift apart. Runs on made-up buildings, then on the page's data file (site/concierge_data.json when it has
   `questions`, else site/_concierge_fixture.json; CONCIERGE_DATA=<file> picks one): every entry of meta.matching_examples must give exactly the order
   and the failing set the data says. */
"use strict";
const fs = require("fs"), path = require("path"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "concierge.html"), "utf8");
const m = /<script id="match-logic">([\s\S]*?)<\/script>/.exec(html);
assert(m, 'no <script id="match-logic"> block in site/concierge.html');
assert(!/<script id="pick-logic">/.test(html), "the version 1 pick logic is still in the page");
assert(!/\b(document|window|localStorage|navigator)\b/.test(m[1].replace(/\/\*[\s\S]*?\*\//g, "")), "the match logic must not touch the page");
const mod = { exports: {} };
new Function("module", m[1])(mod);
const M = mod.exports;
let n = 0;
function test(name, fn) { fn(); n++; console.log("ok  " + name); }
const ids = (list) => list.map((r) => r.b.id);

/* ---- made-up data ---- */
function mk(id, rank, scores, fit, extra) { return Object.assign({ id, experience_id: "E", neighborhood_id: "h", rank_score: rank, scores: scores || {}, fit: fit || {}, apartments: [] }, extra || {}); }
const QS = [
  { id: "visits", kind: "single", must_have: false, answers: [{ id: "weekly", label: "Every week", weights: { parents: 20 }, per_month: 4 }, { id: "monthly", label: "Once a month", weights: { parents: 4 } }] },
  { id: "drive", kind: "single", must_have: true, answers: [{ id: "d30", label: "Half an hour", filter: { field: "drive_min", op: "<=", value: 30 }, weights: {} }, { id: "dany", label: "Any", filter: null, weights: {} }] },
  { id: "room", kind: "single", must_have: true, answers: [{ id: "bed", label: "A separate bedroom", filter: { field: "has_one_bedroom", op: "==", value: true }, weights: { home: 10 } }, { id: "either", label: "Either", weights: {} }] },
  { id: "sat", kind: "single", must_have: false, answers: [{ id: "walk", label: "Walk out", weights: { going_out: 20 } }, { id: "home", label: "Stay in", weights: { home: 10 } }] },
  { id: "pri", kind: "pick_two", must_have: false, answers: [{ id: "p_par", label: "Mom and Dad", weights: { parents: 10 } }, { id: "p_out", label: "Going out", weights: { going_out: 10 } }, { id: "p_room", label: "Room", weights: { home: 10 } }] },
];
const BS = [
  mk("a", 50, { parents: 1, going_out: 0.2, home: 0.1 }, { drive_min: 12, has_one_bedroom: false }, { fit_chips: { weekly: "12 minutes to Mom and Dad", d30: "12 minutes to Mom and Dad", walk: "3 restaurants" }, fit_misses: { bed: "Studios only here", walk: "Only 3 restaurants within a 10-minute walk" } }),
  mk("b", 52, { parents: 0.2, going_out: 1, home: 0.5 }, { drive_min: 50, has_one_bedroom: true }, { fit_chips: { walk: "40 restaurants within a 10-minute walk", bed: "A separate bedroom" }, fit_misses: { d30: "50 minutes to Mom and Dad, more than your 30", weekly: "50 minutes each way" } }),
  mk("c", 40, { parents: 0.5, going_out: 0.5, home: 1 }, { drive_min: null, has_one_bedroom: true }),
  mk("d", 40, { parents: 0.5, going_out: 0.5, home: 1 }, { drive_min: 25, has_one_bedroom: true }),
];
const CFG = M.config({ meta: { matching: { priority_multiplier: 2, confirmed_bonus: 8 } } });
const FLOOR = M.config({ meta: { matching: { pick_floor: 10, confirmed_bonus: 8 } } });

test("no answers: rank order, ties by id, nothing fails", () => {
  const r = M.match(BS, QS, {}, CFG);
  assert.deepStrictEqual(ids(r.fits), ["b", "a", "c", "d"]); assert.strictEqual(r.fails.length, 0);
});
test("weights add weight x score", () => {
  const s = M.score(BS[0], QS, { visits: "weekly" }, CFG);
  assert.strictEqual(s, 50 + 20 * 1);
});
test("a pick doubles the single-question weights on its key and adds its own weight", () => {
  assert.strictEqual(M.score(BS[0], QS, { visits: "weekly", pri: ["p_par"] }, CFG), 50 + (20 * 2 + 10) * 1);
  assert.strictEqual(M.score(BS[0], QS, { pri: ["p_par"] }, CFG), 50 + 10 * 1, "a key no other answer weighted counts the pick's own weight");
  const t = M.score(BS[1], QS, { visits: "weekly", sat: "walk", pri: ["p_out", "p_room"] }, CFG);
  assert.ok(Math.abs(t - (52 + 20 * 0.2 + (20 * 2 + 10) * 1 + 10 * 0.5)) < 1e-6);
  assert.strictEqual(M.score(BS[0], QS, { pri: ["p_par", "p_out", "p_room"] }, CFG), M.score(BS[0], QS, { pri: ["p_par", "p_out"] }, CFG), "only two picks count");
});
test("the pick_floor form, when the data publishes it instead", () => {
  const Q2 = QS.map((q) => q.kind === "pick_two" ? Object.assign({}, q, { answers: q.answers.map((a) => Object.assign({}, a, { weights: Object.fromEntries(Object.keys(a.weights).map((k) => [k, 2])) })) }) : q);
  assert.strictEqual(M.score(BS[0], Q2, { visits: "weekly", pri: ["p_par"] }, FLOOR), 50 + 40 * 1);
  assert.strictEqual(M.score(BS[0], Q2, { visits: "monthly", pri: ["p_par"] }, FLOOR), 50 + 20 * 1, "4 is raised to the floor, then doubled");
});
test("a filter on a question that is not a must-have does not screen", () => {
  const q2 = [{ id: "x", kind: "single", must_have: false, answers: [{ id: "x1", label: "X", filter: { field: "drive_min", op: "<=", value: 1 }, weights: {} }] }];
  assert.strictEqual(M.match(BS, q2, { x: "x1" }, CFG).fails.length, 0);
});
test("must-have filters move places to the failing group, with reasons; an unknown field passes", () => {
  const r = M.match(BS, QS, { drive: "d30" }, CFG);
  assert.deepStrictEqual(ids(r.fits).sort(), ["a", "c", "d"]);
  assert.deepStrictEqual(ids(r.fails), ["b"]);
  assert.deepStrictEqual(M.reasons(r.fails[0].b, r.fails[0].failed), [{ text: "50 minutes to Mom and Dad, more than your 30", said: "Half an hour" }]);
  const r2 = M.match(BS, QS, { drive: "d30", room: "bed" }, CFG);
  assert.deepStrictEqual(ids(r2.fits), ["c", "d"]);
  assert.deepStrictEqual(M.reasons(r2.fails.find((x) => x.b.id === "a").b, r2.fails.find((x) => x.b.id === "a").failed).map((x) => x.text), ["Studios only here"]);
});
test("a failed filter with no miss text still gets a plain reason", () => {
  const r = M.match([mk("z", 1, {}, { drive_min: 99 })], QS, { drive: "d30" }, CFG);
  assert.deepStrictEqual(M.reasons(r.fails[0].b, r.fails[0].failed), [{ text: "Does not match", said: "Half an hour" }]);
});
test("countFits agrees with match", () => {
  [{}, { drive: "d30" }, { drive: "d30", room: "bed" }, { room: "bed" }].forEach((a) => assert.strictEqual(M.countFits(BS, QS, a, CFG), M.match(BS, QS, a, CFG).fits.length));
});
test("confirmed today adds the bonus", () => {
  const b = mk("x", 10, {}, {}, { apartments: [{ checked: { status: "confirmed_today" } }] });
  assert.strictEqual(M.score(b, QS, {}, CFG), 18);
  assert.strictEqual(M.score(mk("y", 10, {}, {}, { apartments: [{ checked: { status: "last_seen" } }] }), QS, {}, CFG), 10);
});
test("chips: her answers only, not the ones it misses, her priorities first, at most three, no repeats", () => {
  assert.deepStrictEqual(M.chips(BS[0], QS, { visits: "weekly", drive: "d30", sat: "walk" }), ["12 minutes to Mom and Dad"]);
  const b = Object.assign({}, BS[0], { fit_chips: { weekly: "W", walk: "R", either: "E", p_out: "R" }, fit_misses: {} });
  assert.deepStrictEqual(M.chips(b, QS, { visits: "weekly", room: "either", sat: "walk", pri: ["p_out"] }), ["R", "W", "E"]);
  assert.deepStrictEqual(M.chips(BS[1], QS, { room: "bed", sat: "walk", pri: ["p_out"] }), ["40 restaurants within a 10-minute walk", "A separate bedroom"]);
  assert.deepStrictEqual(M.chips(BS[1], QS, {}), []);
});
test("miss: at most one, only for a preference, priority first", () => {
  assert.strictEqual(M.miss(BS[0], QS, { sat: "walk", room: "bed" }), "Only 3 restaurants within a 10-minute walk");
  const b = Object.assign({}, BS[1], { fit_misses: { weekly: "50 minutes each way", p_room: "A small studio" } });
  assert.strictEqual(M.miss(b, QS, { visits: "weekly", pri: ["p_room"] }), "A small studio", "a missed priority comes first");
  assert.strictEqual(M.miss(BS[1], QS, { drive: "d30" }), null, "a must-have miss is a failure, not an amber chip");
  assert.strictEqual(M.miss(BS[1], QS, { visits: "weekly" }), "50 minutes each way");
});
test("visits a month", () => {
  assert.strictEqual(M.perMonth(QS[0].answers[0]), 4);
  assert.strictEqual(M.perMonth(QS[0].answers[1]), 1);
  assert.strictEqual(M.perMonth({ id: "visits_twice", label: "Twice a month" }), 2);
  assert.strictEqual(M.perMonth({ id: "visits_rarely", label: "Now and then", visits_per_month: null }), null);
  assert.strictEqual(M.perMonth({ id: "v", label: "x", visits_per_month: 4 }), 4);
});
test("without questions the version 1 either/or questions are used, skippable", () => {
  const q = M.questionsOf({ either_or: [{ id: "x", question: "This or that?", a: { label: "A", weight: { home: 30 } }, b: { label: "B", weight: { parents: 30 } } }] });
  assert.strictEqual(q.length, 1); assert.strictEqual(q[0].must_have, false); assert.deepStrictEqual(q[0].answers.map((a) => a.id), ["x:a", "x:b"]);
  assert.deepStrictEqual(M.questionsOf({}), []);
});
test("pick_two answers are a list; an unknown answer id is ignored", () => {
  assert.strictEqual(M.score(BS[0], QS, { pri: ["nope"] }, CFG), 50);
  assert.strictEqual(M.score(BS[0], QS, { visits: "nope" }, CFG), 50);
});

/* ---- the page's data ---- */
const realPath = path.join(ROOT, "site", "concierge_data.json"), fixPath = path.join(ROOT, "site", "_concierge_fixture.json");
let dataPath = null;
for (const p of (process.env.CONCIERGE_DATA ? [path.resolve(process.env.CONCIERGE_DATA)] : [realPath, fixPath])) { if (fs.existsSync(p)) { const d = JSON.parse(fs.readFileSync(p, "utf8")); if (Array.isArray(d.questions) && d.questions.length) { dataPath = p; break; } } }
if (dataPath) {
  const D = JSON.parse(fs.readFileSync(dataPath, "utf8"));
  const B = M.prepare(D), Q = M.questionsOf(D), C = M.config(D);
  const ex = (D.meta && D.meta.matching_examples) || [];
  test("the data (" + path.basename(dataPath) + ") has matching examples", () => assert.ok(ex.length >= 1, "meta.matching_examples is empty"));
  ex.forEach((e, i) => test("example " + (i + 1) + ": " + (e.name || ""), () => {
    const r = M.match(B, Q, e.answers || {}, C);
    const want = e.expected_fits || e.order || e.expected_order || [];
    assert.deepStrictEqual(ids(r.fits), want, "order");
    const wf = e.expected_doesnt_fit || e.failing || e.expected_failing;
    if (wf) assert.deepStrictEqual(ids(r.fails), wf, "the non-fitting group, in order");
    const sc = e.expected_scores;
    if (sc) r.fits.concat(r.fails).forEach((x) => assert.ok(Math.abs(x.s - sc[x.b.id]) < 0.0015, x.b.id + " score " + x.s + " vs " + sc[x.b.id]));
  }));
  test("every filter names a field that buildings[].fit carries", () => {
    const fields = new Set(); B.forEach((b) => Object.keys(b.fit || {}).forEach((k) => fields.add(k)));
    Q.forEach((q) => q.answers.forEach((a) => { if (a.filter) assert.ok(fields.has(a.filter.field), q.id + "/" + a.id + " filters on " + a.filter.field); }));
  });
  test("chips and misses are keyed by real answer ids", () => {
    const aids = new Set(); Q.forEach((q) => q.answers.forEach((a) => aids.add(a.id)));
    B.forEach((b) => ["fit_chips", "fit_misses"].forEach((k) => Object.keys(b[k] || {}).forEach((id) => assert.ok(aids.has(id), b.id + " " + k + " has " + id))));
  });
} else console.log("note: no data file with questions; only the made-up tests ran");
console.log(n + " tests passed");
