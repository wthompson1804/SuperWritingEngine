/* Tests for the recommender of the short page (version 3). Plain Node, no packages:  node scripts/test_concierge_pick.js
   The file keeps its version 1 name so scripts/verify_concierge.py runs it unchanged; it now tests ConciergeRec.
   The logic is read straight out of site/concierge.html (the <script id="recommender-logic"> block), so the page and
   the test cannot drift apart. It runs on the page's data (site/concierge_data.json when it carries the version 3
   fields, else site/_concierge_fixture.json; CONCIERGE_DATA=<file> picks one):
     1. every meta.recommender_examples entry, replayed answer by answer, must ask exactly expected_pairs and end with
        exactly expected_top, expected_mean_weights, expected_top_set_probability, expected_more_like_this,
        expected_why, expected_gives_up and expected_what_would_change (each where the example has it);
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
test("the data has examples", () => assert(EX.length >= 3, "meta.recommender_examples has " + EX.length));
EX.forEach((ex) => {
  const name = ex.persona || ex.name || "example";
  test("example '" + name + "': the pairs asked, in order (" + ex.expected_pairs.length + ")", () => {
    const p = R.play(M, ex);
    assert.deepStrictEqual(p.pairs, ex.expected_pairs);
    ex.answers.forEach((a, i) => assert(eq([a.a, a.b], ex.expected_pairs[i]), "answer " + i + " is not about the pair asked"));
  });
  test("example '" + name + "': the top three and their buildings", () => {
    const r = R.play(M, ex).rec;
    assert.deepStrictEqual(r.top, ex.expected_top);
  });
  test("example '" + name + "': weights, probability, more like this, why, gives up, what would change", () => {
    const p = R.play(M, ex), r = p.rec;
    if (ex.expected_mean_weights) assert.deepStrictEqual(Object.fromEntries(M.feats.map((k, i) => [k, r.weights[i]])), ex.expected_mean_weights);
    if (ex.expected_top_set_probability != null) assert.strictEqual(Number(R.holds(M, p.asked).p.toFixed(6)), ex.expected_top_set_probability);
    const by = (f) => Object.fromEntries(r.neighborhoods.map((x) => [x.neighborhood_id, f(x)]));
    if (ex.expected_more_like_this) assert.deepStrictEqual(Object.fromEntries(r.neighborhoods.flatMap((x) => x.buildings.map((b) => [b.id, b.more_like_this]))), ex.expected_more_like_this);
    if (ex.expected_why) assert.deepStrictEqual(by((x) => x.why), ex.expected_why);
    if (ex.expected_gives_up) assert.deepStrictEqual(by((x) => x.gives_up), ex.expected_gives_up);
    if (ex.expected_what_would_change) assert.deepStrictEqual(by((x) => x.what_would_change ? x.what_would_change.text : null), ex.expected_what_would_change);
  });
});

/* ---- 2. properties ---- */
const ids = M.ids, BY = Object.fromEntries(D.buildings.map((b) => [b.id, b]));
function walk(rule, opts) {   /* answer pairs until the model stops, by a rule (a, b, i) -> choice */
  const answers = [];
  for (let i = 0; i < 12; i++) {
    const p = R.nextPair(M, answers, opts); if (!p) break;
    answers.push({ a: p[0], b: p[1], choice: rule(p[0], p[1], i) });
  }
  return answers;
}
const RULES = {
  a: () => "a", b: () => "b", either: () => "either", mixed: (a, b, i) => ["a", "b", "either"][i % 3],
  near: (a, b) => (BY[a].features.family >= BY[b].features.family ? "a" : "b"),
  room: (a, b) => (BY[a].features.room >= BY[b].features.room ? "a" : "b"),
};
test("deterministic: the same answers give the same pairs and the same places", () => {
  for (const k in RULES) {
    const x = walk(RULES[k]), y = walk(RULES[k]);
    assert(eq(x, y), k);
    assert(eq(R.recommend(M, x), R.recommend(M, y)), k);
  }
});
test("between 3 and 6 pairs, never the same pair twice, a < b by id", () => {
  for (const k in RULES) {
    const A = walk(RULES[k]);
    assert(A.length >= M.cfg.min_pairs && A.length <= M.cfg.max_pairs, k + ": " + A.length + " pairs");
    const keys = A.map((x) => [x.a, x.b].sort().join("|"));
    assert.strictEqual(new Set(keys).size, keys.length, k + ": a pair repeated");
    A.forEach((x) => assert(x.a < x.b && x.a !== x.b, k + ": pair order"));
  }
});
test("three different neighborhoods, each with one to three of its own buildings, best first", () => {
  for (const k in RULES) {
    const r = R.recommend(M, walk(RULES[k]));
    assert.strictEqual(r.top.length, Math.min(3, M.groups.length), k);
    assert.strictEqual(new Set(r.top.map((t) => t[0])).size, r.top.length, k + ": a neighborhood twice");
    r.top.forEach((t) => {
      const g = M.groups.find((x) => x.id === t[0]);
      assert(t[1].length >= 1 && t[1].length <= 3 && t[1].every((id) => g.building_ids.includes(id)), k + ": buildings of " + t[0]);
      const s = t[1].map((id) => r.scores[id]); for (let i = 1; i < s.length; i++) assert(s[i - 1] >= s[i] - 1e-9, k + ": order in " + t[0]);
    });
  }
});
test("more like this: at most three, never a building on screen, never one given twice", () => {
  for (const k in RULES) {
    const r = R.recommend(M, walk(RULES[k])), on = new Set(r.top.flatMap((t) => t[1])), seen = new Set();
    r.neighborhoods.forEach((nb) => nb.buildings.forEach((b) => {
      assert(b.more_like_this.length <= 3, k);
      b.more_like_this.forEach((x) => { assert(!on.has(x), k + ": " + x + " is on screen"); assert(!seen.has(x), k + ": " + x + " twice"); assert(x !== b.id); seen.add(x); });
    }));
  }
});
test("a building set aside is never asked, shown, or offered as more like this", () => {
  const first = R.recommend(M, walk(RULES.near));
  const out = [first.top[0][1][0], first.top[1][1][0], ids[0]];
  for (const k in RULES) {
    const A = walk(RULES[k], { removed: out });
    A.forEach((x) => assert(!out.includes(x.a) && !out.includes(x.b), k + ": a set-aside building was asked"));
    const r = R.recommend(M, A, { removed: out });
    r.neighborhoods.forEach((nb) => nb.buildings.forEach((b) => { assert(!out.includes(b.id), k + ": shown"); b.more_like_this.forEach((x) => assert(!out.includes(x), k + ": offered")); }));
    assert(!Object.keys(r.scores).some((id) => out.includes(id)), k + ": scored");
  }
  /* a whole neighborhood set aside drops out */
  const g = first.top[0][0], all = M.groups.find((x) => x.id === g).building_ids;
  const r2 = R.recommend(M, [], { removed: all });
  assert(!r2.top.some((t) => t[0] === g), "an emptied neighborhood is still recommended");
  assert.strictEqual(R.recommend(M, [], { removed: ids }).top.length, 0, "with everything set aside, nothing is recommended");
});
test("with nothing set aside, the removed option changes nothing", () => {
  const A = walk(RULES.mixed);
  assert(eq(R.recommend(M, A, { removed: [] }), R.recommend(M, A)));
  assert(eq(R.nextPair(M, A.slice(0, 2), { removed: [] }), R.nextPair(M, A.slice(0, 2))));
});
test("'either' favours samples where the two places are close; a pick favours the one picked", () => {
  const p = R.nextPair(M, []);
  const gap = (c, signed) => { const pi = R.posterior(M, [{ a: p[0], b: p[1], choice: c }]); let s = 0; pi.forEach((x, i) => { const g = M.U[p[0]][i] - M.U[p[1]][i]; s += x * (signed ? g : Math.abs(g)); }); return s; };
  assert(gap("either") < gap("a") && gap("either") < gap("b"), "mean |gap| " + gap("either") + " " + gap("a") + " " + gap("b"));
  assert(gap("a", true) > 0 && gap("b", true) < 0, "signed gap");
});
test("a choice can be given as the building id", () => {
  const p = R.nextPair(M, []);
  assert(eq(R.recommend(M, [{ a: p[0], b: p[1], choice: p[1] }]), R.recommend(M, [{ a: p[0], b: p[1], choice: "b" }])));
});
test("more choices: up to extra_pairs after she asks, past the stop rule", () => {
  const A = walk(RULES.near), more = [];
  for (let i = 0; i < 6; i++) { const p = R.nextPair(M, A.concat(more), { extraFrom: A.length }); if (!p) break; more.push({ a: p[0], b: p[1], choice: "a" }); }
  assert.strictEqual(more.length, M.cfg.extra_pairs || 3);
  assert.strictEqual(R.nextPair(M, A), null, "the stop rule still holds without the request");
});
test("the nudge brings the promised neighborhood to the top", () => {
  for (const k in RULES) {
    const A = walk(RULES[k]), r = R.recommend(M, A), w = r.neighborhoods[0].what_would_change;
    if (!w) continue;
    const r2 = R.recommend(M, A, { nudge: { feature: w.feature, direction: w.direction, factor: w.factor } });
    assert.strictEqual(r2.top[0][0], w.neighborhood_id, k + ": " + w.text);
    assert(/^If .+ mattered (more|less), .+ would come first\.$/.test(w.text), k);
  }
});
test("the stop rule: the most likely top three holds at stop_prob, or six pairs were asked", () => {
  for (const k in RULES) {
    const A = walk(RULES[k]), h = R.holds(M, A);
    assert(h.stop && (A.length >= M.cfg.max_pairs || Number(h.p.toFixed(9)) >= M.cfg.stop_prob), k);
  }
});
test("every building the model scores is a building in the data, and every group has a name", () => {
  M.groups.forEach((g) => { assert(g.name, g.id); g.building_ids.forEach((id) => assert(BY[id], id)); });
  assert.strictEqual(new Set(M.groups.flatMap((g) => g.building_ids)).size, ids.length, "every building in exactly one group");
});

console.log(n + " tests passed");
