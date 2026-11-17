/* Tests for the pick logic of the short page. Plain Node, no packages:  node scripts/test_concierge_pick.js
   The logic is read straight out of site/concierge.html (the <script id="pick-logic"> block), so the page and the test
   can never drift apart. Runs on made-up buildings and then on the page's data file when one exists
   (site/concierge_data.json, else site/_concierge_fixture.json). */
"use strict";
const fs = require("fs"), path = require("path"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "concierge.html"), "utf8");
const m = /<script id="pick-logic">([\s\S]*?)<\/script>/.exec(html);
assert(m, 'no <script id="pick-logic"> block in site/concierge.html');
assert(!/\b(document|window|localStorage|navigator)\b/.test(m[1].replace(/\/\*[\s\S]*?\*\//g, "")), "the pick logic must not touch the page");
const mod = { exports: {} };
new Function("module", m[1])(mod);
const P = mod.exports;
let n = 0;
function test(name, fn) { fn(); n++; console.log("ok  " + name); }
const ids = (list) => list.map((b) => b.id);

/* ---- made-up data: 3 experiences, areas of different sizes ---- */
function mk(id, exp, hood, rank, scores) { return { id, experience_id: exp, neighborhood_id: hood, rank_score: rank, scores: scores || {} }; }
const data = {
  neighborhoods: [{ id: "h1" }, { id: "h2" }, { id: "h3" }, { id: "h4", parked_under: "h1" }, { id: "h5" }, { id: "h6" }],
  buildings: [
    mk("a1", "A", "h1", 90, { parents: 1 }), mk("a2", "A", "h1", 88, { parents: 0.9 }), mk("a3", "A", "h4", 86), mk("a4", "A", "h1", 85),
    mk("b1", "B", "h2", 70, { going_out: 1 }), mk("b2", "B", "h2", 60), mk("b3", "B", "h3", 55, { going_out: 0.2 }),
    mk("c1", "C", "h5", 40, { green: 1 }), mk("c2", "C", "h6", 30), mk("c3", "C", "h6", 30),
  ],
};
const B = P.prepare(data);
const perArea = (list) => list.reduce((o, b) => ((o[b.area_id] = (o[b.area_id] || 0) + 1), o), {});

test("prepare: a parked neighborhood counts as its host", () => {
  assert.strictEqual(B.find((b) => b.id === "a3").area_id, "h1");
  assert.strictEqual(B.find((b) => b.id === "b1").area_id, "h2");
  assert.strictEqual(data.buildings[2].area_id, undefined, "the data itself is not changed");
});
test("returns five, in score order, with no duplicates", () => {
  const r = P.pickFive(B, {}, [], [], []);
  assert.strictEqual(r.length, 5);
  assert.strictEqual(new Set(ids(r)).size, 5);
  assert.deepStrictEqual(ids(r), ["a1", "a2", "b1", "b2", "b3"]);
});
test("at most two per area, parked ones included", () => {
  const r = P.pickFive(B, { A: "me" }, [], [], []);
  Object.values(perArea(r)).forEach((c) => assert(c <= 2));
  assert(!ids(r).includes("a3") && !ids(r).includes("a4"), "a3 (parked under h1) and a4 are the third and fourth in h1");
});
test("answers re-weight: That's me 1.0, Maybe 0.6, Not me 0.25, none 0.6", () => {
  const b = B[0];
  assert.strictEqual(P.score(b, { A: "me" }, []), 90);
  assert.strictEqual(P.score(b, { A: "maybe" }, []), 54);
  assert.strictEqual(P.score(b, { A: "no" }, []), 22.5);
  assert.strictEqual(P.score(b, {}, []), 54);
});
test("either/or adds the weight delta times the building's score", () => {
  assert.strictEqual(P.score(B[0], { A: "me" }, [{ label: "x", weight: { parents: 10 } }]), 100);
  assert.strictEqual(P.score(B[1], { A: "me" }, [{ parents: 10 }]), 97);
  assert.strictEqual(P.score(B[2], { A: "me" }, [{ weight: { parents: 10, nothing: 5 } }]), 86);
  const without = ids(P.pickFive(B, { A: "no", B: "no", C: "no" }, [], [], []));
  const withGreen = ids(P.pickFive(B, { A: "no", B: "no", C: "no" }, [{ weight: { green: 50 } }], [], []));
  assert(!without.includes("c1") && withGreen[0] === "c1", "a strong either/or answer moves a building up");
});
test("at least one from each That's me experience", () => {
  const r = P.pickFive(B, { A: "no", B: "no", C: "me" }, [], [], []);
  assert(r.some((b) => b.experience_id === "C"));
  const r2 = P.pickFive(B, { A: "me", B: "me", C: "me" }, [], [], []);
  ["A", "B", "C"].forEach((e) => assert(r2.some((b) => b.experience_id === e), "missing " + e));
  const lowC = B.map((b) => (b.experience_id === "C" ? Object.assign({}, b, { rank_score: 1 }) : b));
  assert(P.pickFive(lowC, { A: "me", B: "me", C: "me" }, [], [], []).some((b) => b.experience_id === "C"), "even when it scores far lower");
});
test("Not me moves an experience down and never removes it", () => {
  const r = P.pickFive(B, { A: "no" }, [], [], []);
  assert.deepStrictEqual(ids(r).slice(0, 3), ["b1", "b2", "b3"]);
  const all = P.pickFive(B, { A: "no", B: "no", C: "no" }, [], [], [], 10);
  assert.strictEqual(all.length, 10, "every building is still reachable");
});
test("everything Not me: still five, the best overall", () => {
  const r = P.pickFive(B, { A: "no", B: "no", C: "no" }, [], [], []);
  assert.strictEqual(r.length, 5);
  assert.deepStrictEqual(ids(r), ids(P.pickFive(B, {}, [], [], [])));
  assert.strictEqual(P.allNotMe(["A", "B", "C"], { A: "no", B: "no", C: "no" }), true);
  assert.strictEqual(P.allNotMe(["A", "B", "C"], { A: "no", B: "no" }), false);
  assert.strictEqual(P.allNotMe([], {}), false);
});
test("a vetoed building is never returned", () => {
  let vetoed = [];
  for (let i = 0; i < 12; i++) {
    const r = P.pickFive(B, { A: "me" }, [], vetoed, []);
    r.forEach((b) => assert(!vetoed.includes(b.id), b.id + " came back"));
    if (!r.length) break;
    vetoed = vetoed.concat(r[0].id);
  }
  assert.strictEqual(P.pickFive(B, {}, [], ids(B), []).length, 0);
  assert.strictEqual(P.pickFive(B, {}, [], ids(B).slice(0, 7), []).length, 3, "fewer than five when fewer are left");
  assert(!ids(P.pickFive(B, {}, [], ["a1"], ["a1"])).includes("a1"), "a veto wins over a keep");
});
test("kept ones stay, first and in the order kept", () => {
  const r = P.pickFive(B, { A: "me" }, [], ["a1"], ["c3", "b3"]);
  assert.deepStrictEqual(ids(r).slice(0, 2), ["c3", "b3"]);
  assert.strictEqual(r.length, 5);
  const many = ["a1", "a2", "a3", "a4", "b1", "b2"];
  assert.deepStrictEqual(ids(P.pickFive(B, {}, [], [], many, many.length)), many, "more than five kept: all stay");
  assert.deepStrictEqual(ids(P.pickFive(B, {}, [], [], ["a1", "a2"])).filter((x) => x === "a3" || x === "a4"), [], "kept ones count toward two per area");
});
test("swapping one out leaves the other four alone", () => {
  const first = ids(P.pickFive(B, { B: "me" }, [], [], []));
  const others = first.slice(1);
  const next = ids(P.pickFive(B, { B: "me" }, [], [first[0]], others));
  assert.deepStrictEqual(next.slice(0, 4), others);
  assert(!first.includes(next[4]));
});
test("ties go to the lower id, whatever order the buildings come in", () => {
  const r1 = ids(P.pickFive(B, { A: "no", B: "no", C: "me" }, [], ["c1"], []));
  const r2 = ids(P.pickFive(B.slice().reverse(), { A: "no", B: "no", C: "me" }, [], ["c1"], []));
  assert.deepStrictEqual(r1, r2);
  assert(r1.indexOf("c2") < r1.indexOf("c3"));
  for (let i = 0; i < 5; i++) assert.deepStrictEqual(ids(P.pickFive(B, { A: "me" }, [], [], [])), ids(P.pickFive(B, { A: "me" }, [], [], [])));
});
test("when two per area cannot fill five, the best of the rest fill in", () => {
  const one = [mk("x1", "A", "h", 9), mk("x2", "A", "h", 8), mk("x3", "A", "h", 7), mk("x4", "A", "h", 6), mk("x5", "A", "h", 5), mk("x6", "A", "h", 4)];
  assert.deepStrictEqual(ids(P.pickFive(one, {}, [], [], [])), ["x1", "x2", "x3", "x4", "x5"]);
});
test("missing fields do not break it", () => {
  const odd = [{ id: "p" }, { id: "q", rank_score: null, scores: null, experience_id: null }, { id: "r", rank_score: 3 }];
  assert.deepStrictEqual(ids(P.pickFive(odd, null, null, null, null)), ["r", "p", "q"]);
  assert.deepStrictEqual(P.pickFive([], {}, [], [], []), []);
});

/* ---- the page's own data ---- */
const real = path.join(ROOT, "site", "concierge_data.json"), fixture = path.join(ROOT, "site", "_concierge_fixture.json");
const file = fs.existsSync(real) ? real : fs.existsSync(fixture) ? fixture : null;
if (!file) console.log("--  no data file yet (site/concierge_data.json): the checks on real data were skipped");
else {
  const D = JSON.parse(fs.readFileSync(file, "utf8")), RB = P.prepare(D), exps = (D.experiences || []).map((e) => e.id);
  const want = Math.min(5, RB.length);
  const combos = [{}];
  ["me", "maybe", "no"].forEach((v) => { const a = {}; exps.forEach((e) => (a[e] = v)); combos.push(a); });
  exps.forEach((e) => { const a = {}; exps.forEach((x) => (a[x] = x === e ? "me" : "no")); combos.push(a); });
  const sides = [[]].concat((D.either_or || []).map((q) => [q.a]), (D.either_or || []).map((q) => [q.b]), [(D.either_or || []).map((q) => q.a)]);
  test(path.basename(file) + ": five every time, variety holds, That's me is represented (" + RB.length + " buildings)", () => {
    combos.forEach((a) => sides.forEach((s) => {
      const r = P.pickFive(RB, a, s, [], []);
      assert.strictEqual(r.length, want);
      assert.strictEqual(new Set(ids(r)).size, r.length);
      const areas = new Set(RB.map((b) => b.area_id));
      if (areas.size * P.PER_AREA >= want) Object.values(perArea(r)).forEach((c) => assert(c <= P.PER_AREA, "more than two in one area"));
      exps.filter((e) => a[e] === "me").slice(0, want).forEach((e) => { if (RB.some((b) => b.experience_id === e)) assert(r.some((b) => b.experience_id === e), "no building from " + e); });
      assert.deepStrictEqual(ids(r), ids(P.pickFive(RB.slice().reverse(), a, s, [], [])), "same answer whatever the order");
    }));
  });
  test(path.basename(file) + ": vetoing through the whole list never brings one back", () => {
    const vetoed = [], seen = new Set();
    let slots = ids(P.pickFive(RB, combos[1], [], [], []));
    for (let guard = 0; guard < RB.length + 5 && slots.length; guard++) {
      slots.forEach((id) => { assert(!vetoed.includes(id)); seen.add(id); });
      const out = slots[0], others = slots.slice(1);
      vetoed.push(out);
      const r = ids(P.pickFive(RB, combos[1], [], vetoed, others));
      assert(!r.includes(out));
      slots = r;
    }
    assert.strictEqual(seen.size, RB.length, "every building gets its turn");
  });
  test(path.basename(file) + ": parked neighborhoods point at a real, unparked host", () => {
    const H = {}; (D.neighborhoods || []).forEach((h) => (H[h.id] = h));
    (D.neighborhoods || []).forEach((h) => { if (h.parked_under) { assert(H[h.parked_under], h.id + " is parked under a neighborhood that is not in the data"); assert(!H[h.parked_under].parked_under, h.id + " is parked under a parked neighborhood"); } });
  });
}
console.log("\n" + n + " tests passed");
