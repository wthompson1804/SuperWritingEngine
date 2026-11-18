/* Tests for what the short page (version 7, "zoom out to neighborhoods") reads from its data. Plain Node, no packages:
     node scripts/test_concierge_pick.js
   The file keeps its version 1 name so scripts/verify_concierge.py runs it unchanged. Version 7 shows the ranked
   neighborhoods of site/neighborhoods_data.json (CONCIERGE_DATA=<file> picks another) as the data gives them, so this
   checks the data the page shows, and that the template still reads it the way the page promises:
     - the ranking: ranks 1..N with no gap, each neighborhood with a name, a state, a typical rent at or under the
       limit and a drive under the limit;
     - at most three why facts and two know-this facts, each a sentence; at most two tags;
     - at most three top buildings, none with a rent above the limit, each with a name or an address;
     - at most two buildings to avoid, each with its reason and the name of its source, none also a top building;
     - every top and avoid building is in its neighborhood's all_buildings; no building sits in two neighborhoods;
     - a phone number only ever with a leasing office or a management company;
     - meta has the measures, weights, coverage and counts the "How this was ranked" box uses;
     - verified buildings find their fuller sheet in site/concierge_data.json (counted, and at least one must);
     - the template has its four slots, no older screens, and none of the words the page must not say. */
"use strict";
const fs = require("fs"), path = require("path"), assert = require("assert");
const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "site", "concierge.html"), "utf8");
let n = 0;
function test(name, fn) { fn(); n++; console.log("ok  " + name); }
const isNum = (x) => typeof x === "number" && isFinite(x);
const str = (x) => typeof x === "string" && x.trim().length > 0;

const file = process.env.CONCIERGE_DATA || path.join(ROOT, "site", "neighborhoods_data.json");
const D = JSON.parse(fs.readFileSync(file, "utf8"));
console.log("data: " + path.relative(ROOT, file));
const M = D.meta || {}, H = D.neighborhoods, LIMIT = M.rent_limit;
const tops = (h) => h.top_buildings || [], avoids = (h) => h.avoid_buildings || [];

test("meta carries the limit and the list is there", () => {
  assert(isNum(LIMIT) && LIMIT === 2000, "meta.rent_limit is " + LIMIT + ", the page promises $2,000");
  assert(Array.isArray(H) && H.length >= 10, "fewer than ten neighborhoods");
  assert(isNum(M.max_drive_min) && isNum(M.min_buildings), "meta.max_drive_min and meta.min_buildings");
});
test("ranks run 1..N with no gap and no repeat", () => {
  const r = H.map((h) => h.rank).sort((a, b) => a - b);
  r.forEach((v, i) => assert(v === i + 1, "rank " + (i + 1) + " is missing or repeated (found " + v + ")"));
  assert(new Set(H.map((h) => h.id)).size === H.length, "a neighborhood id is repeated");
  if (isNum((M.counts || {}).eligible)) assert(M.counts.eligible === H.length, "meta.counts.eligible is not the number of neighborhoods");
});
test("each neighborhood has what its card shows", () => {
  H.forEach((h) => {
    const L = h.name + ": ";
    assert(str(h.id) && str(h.name) && str(h.state), L + "id, name, state");
    assert(isNum(h.typical_rent) && h.typical_rent <= LIMIT, L + "typical rent " + h.typical_rent);
    assert(isNum(h.drive_min) && h.drive_min < M.max_drive_min, L + "drive " + h.drive_min);
    assert(Array.isArray(h.tags) && h.tags.length <= 2 && h.tags.every(str), L + "at most two tags");
    assert(isNum(h.lat) && isNum(h.lon), L + "a place on the map");
  });
});
test("why facts (up to three) and know-this facts (up to two) are sentences with a measure and an icon", () => {
  H.forEach((h) => {
    assert(Array.isArray(h.why) && h.why.length <= 3, h.name + ": " + (h.why || []).length + " why facts");
    assert(Array.isArray(h.know_this) && h.know_this.length <= 2, h.name + ": " + (h.know_this || []).length + " know-this facts");
    h.why.concat(h.know_this).forEach((w) => assert(str(w.text) && /[.!?]$/.test(w.text.trim()) && str(w.measure) && str(w.icon), h.name + ": a fact without text, measure or icon"));
    const both = h.why.map((w) => w.measure).filter((m) => h.know_this.some((k) => k.measure === m));
    assert(both.length === 0, h.name + ": " + both.join(",") + " is both a why and a know-this");
  });
});
test("top buildings: at most three, none above the limit, each with a name or an address", () => {
  H.forEach((h) => {
    assert(Array.isArray(h.top_buildings) && tops(h).length <= 3, h.name + ": " + tops(h).length + " top buildings");
    tops(h).forEach((b) => {
      const L = h.name + " / " + (b.name || b.address || b.id) + ": ";
      assert(str(b.id) && (str(b.name) || str(b.address)), L + "id and name");
      assert(Array.isArray(b.rent_range) && isNum(b.rent_range[0]) && isNum(b.rent_range[1]) && b.rent_range[0] <= b.rent_range[1], L + "rent range");
      assert(b.rent_range[1] <= LIMIT, L + "rent " + b.rent_range[1] + " is above " + LIMIT);
      assert(Array.isArray(b.known) && Array.isArray(b.to_ask) && b.known.concat(b.to_ask).every(str), L + "known and to-ask chips");
      assert(isNum(b.apartments) && b.apartments >= 1, L + "apartments count");
      if (b.rating) assert(isNum(b.rating.value) && b.rating.value >= 0 && b.rating.value <= 5, L + "rating");
      const t = b.verified && b.verified.total_with_utilities_and_fees;
      if (t) assert(isNum(t[0]) && isNum(t[1]) && t[0] >= b.rent_range[0], L + "the total is below the rent");
    });
  });
});
test("buildings to avoid: at most two, each with its reason and source, none also a top building", () => {
  H.forEach((h) => {
    assert(Array.isArray(h.avoid_buildings) && avoids(h).length <= 2, h.name + ": " + avoids(h).length + " to avoid");
    const topIds = new Set(tops(h).map((b) => b.id));
    avoids(h).forEach((b) => {
      const L = h.name + " / " + (b.name || b.id) + ": ";
      assert(str(b.id) && (str(b.name) || str(b.address)), L + "id and name");
      assert(str(b.reason) && /[.!?]$/.test(b.reason.trim()), L + "a one-sentence reason");
      assert(b.source && str(b.source.name), L + "the name of its source");
      assert(!topIds.has(b.id), L + "also a top building");
    });
  });
});
test("every top and avoid building is in all_buildings, and no building sits in two neighborhoods", () => {
  const seen = new Map();
  H.forEach((h) => {
    assert(Array.isArray(h.all_buildings), h.name + ": all_buildings");
    const ids = new Set(h.all_buildings.map((b) => b.id));
    tops(h).concat(avoids(h)).forEach((b) => assert(ids.has(b.id), h.name + ": " + b.id + " is not in all_buildings"));
    h.all_buildings.forEach((b) => {
      assert(str(b.id) && (str(b.name) || str(b.address)), h.name + ": a listed building without id or name");
      assert(!seen.has(b.id), b.id + " is in " + seen.get(b.id) + " and " + h.name); seen.set(b.id, h.name);
      if (Array.isArray(b.rent_range) && isNum(b.rent_range[1])) assert(b.rent_range[1] <= LIMIT, h.name + " / " + b.name + ": rent " + b.rent_range[1]);
    });
  });
});
test("a phone number only with a leasing office or a management company", () => {
  H.forEach((h) => tops(h).concat(avoids(h)).forEach((b) => {
    const c = b.contact;
    if (c && c.phone) assert(/^(leasing office|management company)$/i.test(c.kind || ""), h.name + " / " + b.name + ": a phone with contact kind " + c.kind);
  }));
  assert(/var PUBLIC_KIND = \/\^\(leasing office\|management company\)\$\/i/.test(html), "the page no longer limits contacts to offices and companies");
});
test("meta has what How this was ranked uses", () => {
  const ms = M.measures || {}, cov = M.coverage || {}, keys = Object.keys(ms);
  assert(keys.length >= 5, "meta.measures");
  keys.forEach((k) => {
    assert(isNum(ms[k].weight) && ms[k].weight > 0 && str(ms[k].label), "measure " + k + ": weight and label");
    assert(cov[k] && isNum(cov[k].neighborhoods_with_measure) && isNum(cov[k].of) && cov[k].neighborhoods_with_measure <= cov[k].of, "coverage of " + k);
  });
  ["listings_used", "listings_at_2000_or_less", "eligible", "no_neighborhood_record", "cut_drive", "cut_by_the_jamaica_rule", "too_little_supply"].forEach((k) => assert(isNum((M.counts || {})[k]), "meta.counts." + k));
});
test("verified buildings find their fuller sheet", () => {
  const cpath = path.join(ROOT, "site", "concierge_data.json");
  if (!fs.existsSync(cpath)) { console.log("    (no site/concierge_data.json: verified buildings get the simple screen)"); return; }
  const have = new Set(JSON.parse(fs.readFileSync(cpath, "utf8")).buildings.map((b) => b.id));
  let v = 0, hit = 0;
  H.forEach((h) => tops(h).forEach((b) => { if (b.verified && b.verified.on_page) { v++; if (have.has(b.id)) hit++; } }));
  console.log("    " + hit + " of " + v + " verified top buildings have a fuller sheet");
  assert(v === 0 || hit > 0, "no verified top building has a fuller sheet");
});
test("the template: four slots, version 7 only, none of the words the page must not say", () => {
  ["<!--CONCIERGE_DATA_SLOT-->", "<!--CONCIERGE_PLACES_SLOT-->", "<!--CONCIERGE_ILLUS_SLOT-->", "<!--CONCIERGE_MAP_SLOT-->"].forEach((s) => assert(html.split(s).length === 2, s + " must be in the template exactly once"));
  assert(!/default_recommendation|function plan\(|initAsk|recommender-logic/.test(html), "a version 6 screen is still in the template");
  assert(/function fresh\(\) \{ return \{ v: 7,/.test(html), "the saved state is not version 7");
  const shown = html.replace(/<style>[\s\S]*?<\/style>/, "");
  const bad = /\bcrimes?\b|net-effective|\ball-in\b|\bgates?\b|\bunits?\b/i.exec(shown);
  assert(!bad, 'the template says "' + (bad && bad[0]) + '"');
  assert(/Neighborhoods for you/.test(html) && /How this was ranked/.test(html) && /See this neighborhood/.test(html) && /Top buildings/.test(html) && /Checked against its listing/.test(html), "a promised label is missing");
});
test("the built page, when there, carries no photo addresses and no scoring tables", () => {
  const built = path.join(ROOT, "site", "dist", "concierge.html");
  if (!fs.existsSync(built)) { console.log("    (not built yet)"); return; }
  const t = fs.readFileSync(built, "utf8");
  assert(!/"photo_url"|"evidence_points"|"sensitivity"/.test(t), "the built page still inlines a field it never shows");
});
console.log("\n" + n + " tests passed");
