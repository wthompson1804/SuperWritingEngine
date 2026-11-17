/* Tests for the recommender of the short page (version 4: choices between made-up apartments, then the version 3
   recommendation from her weights). Plain Node, no packages:  node scripts/test_concierge_pick.js
   The file keeps its version 1 name so scripts/verify_concierge.py runs it unchanged; it now tests ConciergeRec.
   The logic is read straight out of site/concierge.html (the <script id="recommender-logic"> block), so the page and
   the test cannot drift apart. It runs on the page's data (site/concierge_data.json when it carries the recommender
   fields, else site/_concierge_fixture.json; CONCIERGE_DATA=<file> picks one):
     1. every meta.recommender_examples entry, replayed answer by answer, must ask exactly expected_tasks and end with
        exactly expected_mean_weights, expected_priorities, expected_priorities_sentence, expected_top,
        expected_more_like_this, expected_why and expected_gives_up; and its nudge_example, where it has one;
     2. property tests: deterministic; never a set-aside building anywhere; three different neighborhoods; more like
        this never repeats a building on screen; pairs never repeat; 3 to 6 pairs; "either" favours samples where the
        two are close; the nudge brings the promised neighborhood to the top.
   The version 2 match logic is gone from the page (See everything's filter never used it), and so are its tests. */
"use strict";
const fs = require("fs"), path = require("path"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "concierge.html"), "utf8");
const m = /<script id="recommender-logic">([\s\S]*?)<\/script>/.exec(html);
assert(m, 'no <script id="recommender-logic"> block in site/concierge.html');
assert(!/<script id="match-logic">/.test(html), "the version 2 match logic is still in the page");
assert(!/<script id="pick-logic">/.test(html), "the version 1 pick logic is still in the page");
assert(!/\b(document|window|localStorage|navigator)\b/.test(m[1].replace(/\/\*[\s\S]*?\*\//g, "")), "the recommender must not touch the page");
const mod = { exports: {} };
new Function("module", m[1])(mod);
const R = mod.exports;
let n = 0;
function test(name, fn) { fn(); n++; console.log("ok  " + name); }
const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function pickData() {
  if (process.env.CONCIERGE_DATA) return process.env.CONCIERGE_DATA;
  const real = path.join(ROOT, "site", "concierge_data.json"), fx = path.join(ROOT, "site", "_concierge_fixture.json");
  try { if (R.usable(JSON.parse(fs.readFileSync(real, "utf8")))) return real; } catch (e) { /* fall through */ }
  return fx;
}
const file = pickData();
const D = JSON.parse(fs.readFileSync(file, "utf8"));
console.log("data: " + path.relative(ROOT, file) + (D.meta.fixture ? "  [TEST FIXTURE]" : ""));
const M = R.model(D);
assert(M, "the data has no recommender fields (recommender_samples, meta.recommender, buildings[].features)");
const EX = D.meta.recommender_examples || [];

/* ---- small pieces ---- */
test("Neumaier sum, as CPython 3.12+ sum()", () => {
  assert.strictEqual(R.nsum([0.1, 0.2, 0.3]), 0.6);           /* plain += gives 0.6000000000000001 */
  assert.strictEqual(R.nsum([1e100, 1, -1e100]), 1);
  assert.strictEqual(R.nsum([]), 0);
});
test("Python round(): halves to even", () => {
  assert.deepStrictEqual([0.5, 1.5, 2.5, 12.5, 13.5, 2.4, 2.6].map(R.pyRound), [0, 2, 2, 12, 14, 2, 3]);
});
test("no data, no model", () => {
  assert.strictEqual(R.model({ meta: {}, buildings: [{ id: "x" }] }), null);
  assert.strictEqual(R.usable({ meta: { recommender: { features: [] } }, recommender_samples: [], buildings: [] }), false);
});

/* ---- 1. the examples ---- */
const C = R.cj(M);
assert(C, "the data has no meta.recommender.conjoint");
const round6 = (w) => w.map((x) => Number(x.toFixed(6)));
function replay(ex) {
  const A = [], tasks = [];
  for (let i = 0; i < 30; i++) {
    const t = R.cjNext(M, A); if (t === null) break;
    tasks.push(t); A.push({ task_index: t, choice: ex.answers[i] ? ex.answers[i].choice : "either" });
  }
  const w = R.cjWeights(M, A);
  return { A, tasks, w, rec: R.recommend(M, [], { w }) };
}
test("the data has examples", () => assert(EX.length >= 3, "meta.recommender_examples has " + EX.length));
EX.forEach((ex) => {
  const name = ex.persona || "example";
  test("example '" + name + "': the tasks asked, in order (" + ex.expected_tasks.length + ")", () => {
    const p = replay(ex);
    assert.deepStrictEqual(p.tasks, ex.expected_tasks);
    ex.answers.forEach((a, i) => assert.strictEqual(a.task_index, ex.expected_tasks[i]));
    if (ex.expected_tasks_shown) ex.expected_tasks_shown.forEach((rows, i) => assert.deepStrictEqual(C.pool[ex.expected_tasks[i]].map((x) => ({ attribute: C.attr[x[0]].label, a: C.attr[x[0]].levels[x[1]].text, b: C.attr[x[0]].levels[x[2]].text })), rows));
  });
  test("example '" + name + "': weights, priorities and the sentence", () => {
    const p = replay(ex), w6 = round6(p.w);
    assert.deepStrictEqual(Object.fromEntries(M.feats.map((k, i) => [k, w6[i]])), ex.expected_mean_weights);
    const pr = R.priorities(M, w6);
    assert.deepStrictEqual(pr.order, ex.expected_priorities);
    if (ex.expected_priorities_sentence) assert.strictEqual(pr.sentence, ex.expected_priorities_sentence);
  });
  test("example '" + name + "': the three places, more like this, why, gives up", () => {
    const r = replay(ex).rec, by = (f) => Object.fromEntries(r.neighborhoods.map((x) => [x.neighborhood_id, f(x)]));
    assert.deepStrictEqual(r.top, ex.expected_top);
    if (ex.expected_more_like_this) assert.deepStrictEqual(Object.fromEntries(r.neighborhoods.flatMap((x) => x.buildings.map((b) => [b.id, b.more_like_this]))), ex.expected_more_like_this);
    if (ex.expected_why) assert.deepStrictEqual(by((x) => x.why), ex.expected_why);
    if (ex.expected_gives_up) assert.deepStrictEqual(by((x) => x.gives_up), ex.expected_gives_up);
  });
  if (ex.nudge_example) test("example '" + name + "': moving one priority " + ex.nudge_example.direction, () => {
    const n = ex.nudge_example, w6 = M.feats.map((k) => ex.expected_mean_weights[k]), w2 = R.nudge(M, w6, n.feature, n.direction);
    assert.deepStrictEqual(Object.fromEntries(M.feats.map((k, i) => [k, Number(w2[i].toFixed(6))])), n.weights_after);
    assert.strictEqual(R.priorities(M, w2).sentence, n.priorities_sentence_after);
    assert.deepStrictEqual(R.recommend(M, [], { w: w2 }).top, n.expected_top_after);
  });
});

/* ---- 2. properties ---- */
const BY = Object.fromEntries(D.buildings.map((b) => [b.id, b]));
function walk(rule) {
  const A = [];
  for (let i = 0; i < 30; i++) { const t = R.cjNext(M, A); if (t === null) break; A.push({ task_index: t, choice: rule(C.pool[t], i) }); }
  return A;
}
const gapUnder = (wObj) => (task) => R.taskGap(M, M.feats.map((k) => wObj[k] || 0), task);
const RULES = {
  a: () => "a", b: () => "b", either: () => "either", mixed: (t, i) => ["a", "b", "either"][i % 3],
  near: (t) => { const g = gapUnder({ family: 1 })(t); return g > 0 ? "a" : g < 0 ? "b" : "either"; },
  space: (t) => { const g = gapUnder({ room: 1 })(t); return g > 0 ? "a" : g < 0 ? "b" : "either"; },
};
test("the pool: two or three attributes differ, never one apartment better on all of them", () => {
  C.pool.forEach((t, i) => {
    assert(t.length >= 2 && t.length <= 3, "task " + i);
    assert.strictEqual(new Set(t.map((x) => x[0])).size, t.length, "task " + i + " repeats an attribute");
    const better = t.map((x) => Math.sign(C.lv[x[0]][x[1]] - C.lv[x[0]][x[2]]));
    assert(better.includes(1) && better.includes(-1), "task " + i + " is dominated");
  });
});
test("exactly n_tasks choices, never the same task twice, never the same attributes twice in a row", () => {
  for (const k in RULES) {
    const A = walk(RULES[k]);
    assert.strictEqual(A.length, C.n, k);
    assert.strictEqual(new Set(A.map((x) => x.task_index)).size, A.length, k);
    for (let i = 1; i < A.length; i++) {
      const s = (j) => C.pool[A[j].task_index].map((x) => x[0]).sort().join("|");
      assert.notStrictEqual(s(i), s(i - 1), k + ": same attributes twice in a row");
    }
  }
});
test("deterministic: the same answers give the same tasks, weights and places", () => {
  for (const k in RULES) {
    const x = walk(RULES[k]), y = walk(RULES[k]);
    assert(eq(x, y), k);
    assert(eq(R.recommend(M, [], { w: R.cjWeights(M, x) }), R.recommend(M, [], { w: R.cjWeights(M, y) })), k);
  }
});
test("the weights learn: someone who always picks the shorter drive gets Mom and Dad first; space likewise", () => {
  assert.strictEqual(R.priorities(M, R.cjWeights(M, walk(RULES.near))).order[0], "family");
  assert.strictEqual(R.priorities(M, R.cjWeights(M, walk(RULES.space))).order[0], "room");
});
test("weights stay a distribution", () => {
  for (const k in RULES) { const w = R.cjWeights(M, walk(RULES[k])); assert(Math.abs(R.nsum(w) - 1) < 1e-9 && w.every((x) => x >= 0), k); }
});
test("a move swaps one priority with its neighbour, and only that", () => {
  const w = R.cjWeights(M, walk(RULES.mixed)), o = R.priorities(M, w).order;
  for (let i = 0; i < o.length; i++) {
    const up = R.priorities(M, R.nudge(M, w, o[i], "up")).order, down = R.priorities(M, R.nudge(M, w, o[i], "down")).order;
    const want = (j) => { const x = o.slice(); if (j < 0 || j >= x.length) return x; [x[i], x[j]] = [x[j], x[i]]; return x; };
    assert.deepStrictEqual(up, want(i - 1), "up " + o[i]); assert.deepStrictEqual(down, want(i + 1), "down " + o[i]);
  }
  assert.deepStrictEqual(R.cjWeights(M, walk(RULES.mixed), [[o[1], "up"]]), R.nudge(M, w, o[1], "up"));
});
test("three different neighborhoods, each with one to three of its own buildings, best first", () => {
  for (const k in RULES) {
    const r = R.recommend(M, [], { w: R.cjWeights(M, walk(RULES[k])) });
    assert.strictEqual(r.top.length, Math.min(3, M.groups.length), k);
    assert.strictEqual(new Set(r.top.map((t) => t[0])).size, r.top.length, k);
    r.top.forEach((t) => {
      const g = M.groups.find((x) => x.id === t[0]);
      assert(t[1].length >= 1 && t[1].length <= 3 && t[1].every((id) => g.building_ids.includes(id)), k + ": " + t[0]);
      const s = t[1].map((id) => r.scores[id]); for (let i = 1; i < s.length; i++) assert(s[i - 1] >= s[i] - 1e-9, k);
    });
  }
});
test("more like this on a place: three others, never itself", () => {
  const w = R.cjWeights(M, walk(RULES.mixed));
  M.ids.slice(0, 20).forEach((id) => { const m = R.similarTo(M, id, w, 3); assert(m.length === Math.min(3, M.ids.length - 1) && !m.includes(id) && m.every((x) => BY[x]), id); });
});
test("every building in exactly one group, every group named", () => {
  M.groups.forEach((g) => { assert(g.name, g.id); g.building_ids.forEach((id) => assert(BY[id], id)); });
  assert.strictEqual(new Set(M.groups.flatMap((g) => g.building_ids)).size, M.ids.length);
});

console.log(n + " tests passed");
