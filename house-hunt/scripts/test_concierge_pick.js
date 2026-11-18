/* Tests for what the short page (version 5) reads from its data. Plain Node, no packages:  node scripts/test_concierge_pick.js
   The file keeps its version 1 name so scripts/verify_concierge.py runs it unchanged. Version 5 asks nothing, so the page
   no longer carries a recommender (the <script id="recommender-logic"> block is gone, and with it its tests); the page
   shows meta.default_recommendation as the data gives it. This checks the data it shows (site/concierge_data.json when
   it carries meta.funnel and meta.default_recommendation, else site/_concierge_fixture.json; CONCIERGE_DATA=<file>
   picks one):
     - the promise: exactly three neighborhoods, three buildings each, every building in the data and in its
       neighborhood's group, no building twice;
     - each neighborhood's why, gives up and tags are there to show;
     - meta.funnel has the counts the two sentences use, and its rules are plain strings;
     - meta.leanings point at real groups, one per priority;
     - buildings[].similar (the place sheet's More like this) names real other buildings.
   And that the page itself has no recommender left and no version 4 choice screens. */
"use strict";
const fs = require("fs"), path = require("path"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "concierge.html"), "utf8");
let n = 0;
function test(name, fn) { fn(); n++; console.log("ok  " + name); }

function ready(d) { const m = (d && d.meta) || {}; return !!(m.funnel && m.default_recommendation && (m.default_recommendation.neighborhoods || []).length); }
function pickData() {
  if (process.env.CONCIERGE_DATA) return process.env.CONCIERGE_DATA;
  const real = path.join(ROOT, "site", "concierge_data.json"), fx = path.join(ROOT, "site", "_concierge_fixture.json");
  try { if (ready(JSON.parse(fs.readFileSync(real, "utf8")))) return real; } catch (e) { /* fall through */ }
  return fx;
}
const file = pickData();
const D = JSON.parse(fs.readFileSync(file, "utf8"));
console.log("data: " + path.relative(ROOT, file) + (D.meta.fixture ? "  [TEST FIXTURE]" : ""));
const M = D.meta, DR = M.default_recommendation, BY = Object.fromEntries(D.buildings.map((b) => [b.id, b]));
const groups = Object.fromEntries(((M.recommender || {}).groups || []).map((g) => [g.id, g]));
const HB = Object.fromEntries(D.neighborhoods.map((h) => [h.id, h]));

test("the page has no recommender and no choice screens left", () => {
  assert(!/<script id="recommender-logic">/.test(html), "the recommender-logic block is still in the page");
  assert(!/<script id="match-logic">/.test(html) && !/<script id="pick-logic">/.test(html), "an older logic block is still in the page");
  assert(!/function chooseScreen|function confirmScreen|data-act="cj"/.test(html), "the version 4 choices are still in the page");
});
test("the promise: exactly three neighborhoods with exactly three buildings each", () => {
  assert(DR && Array.isArray(DR.neighborhoods), "meta.default_recommendation.neighborhoods");
  assert.strictEqual(DR.neighborhoods.length, 3);
  DR.neighborhoods.forEach((nb) => assert.strictEqual(nb.buildings.length, 3, nb.neighborhood_id));
  assert.strictEqual(new Set(DR.neighborhoods.map((x) => x.neighborhood_id)).size, 3, "a neighborhood twice");
  const all = DR.neighborhoods.flatMap((x) => x.buildings.map((b) => b.id));
  assert.strictEqual(new Set(all).size, 9, "a building twice");
});
test("every building shown is in the data, in its neighborhood's group", () => {
  DR.neighborhoods.forEach((nb) => nb.buildings.forEach((b) => {
    assert(BY[b.id], b.id + " is not in the data");
    const g = groups[nb.neighborhood_id];
    if (g) assert(g.building_ids.includes(b.id), b.id + " is not in " + nb.neighborhood_id);
    else assert.strictEqual(BY[b.id].group_id || BY[b.id].neighborhood_id, nb.neighborhood_id, b.id);
  }));
});
test("each neighborhood has its name, why, and gives up (or none) to show", () => {
  DR.neighborhoods.forEach((nb) => {
    assert(nb.name || (HB[nb.neighborhood_id] || {}).name, nb.neighborhood_id + ": no name");
    assert(typeof nb.why === "string" && nb.why.length > 5, nb.neighborhood_id + ": no why");
    assert(Array.isArray(nb.why_features) && nb.why_features.length >= 1, nb.neighborhood_id + ": no why_features");
    assert(nb.gives_up === null || typeof nb.gives_up === "string", nb.neighborhood_id + ": gives_up");
    assert(!nb.gives_up || nb.gives_up_feature, nb.neighborhood_id + ": gives_up without its feature");
  });
});
test("meta.funnel: the counts for the two sentences, and the rules as plain strings", () => {
  const f = M.funnel;
  assert(Number.isFinite(f.listings_read) && f.listings_read > 0, "listings_read");
  const passed = typeof f.passed_apartments === "object" && f.passed_apartments ? f.passed_apartments.at_or_under_2000 : f.passed_apartments;
  assert(Number.isFinite(passed) && passed > 0, "passed apartments");
  assert(Array.isArray(f.rules) && f.rules.length >= 3 && f.rules.every((r) => typeof r === "string" && r.trim()), "rules");
  assert(!f.rules.some((r) => /\bcrime/i.test(r)), "no crime wording in the rules");
});
test("meta.leanings: one line per priority, each pointing at a real neighborhood", () => {
  const L = M.leanings || [];
  assert(L.length >= 1);
  L.forEach((x) => {
    assert(x.priority_key && x.neighborhood_id, JSON.stringify(x));
    assert(groups[x.neighborhood_id] || HB[x.neighborhood_id], x.neighborhood_id + " is not a neighborhood");
    assert(D.buildings.some((b) => (b.group_id || b.neighborhood_id) === x.neighborhood_id || b.neighborhood_id === x.neighborhood_id), x.neighborhood_id + " has no buildings");
  });
  assert.strictEqual(new Set(L.map((x) => x.priority_key)).size, L.length, "a priority twice");
});
test("buildings[].similar names real other buildings (the place sheet's More like this)", () => {
  D.buildings.forEach((b) => { (b.similar || []).forEach((x) => { assert(BY[x], b.id + " -> " + x); assert.notStrictEqual(x, b.id); }); });
  assert(D.buildings.filter((b) => (b.similar || []).length >= 3).length >= D.buildings.length * 0.9, "most buildings have three similar ones");
});

console.log(n + " tests passed");
