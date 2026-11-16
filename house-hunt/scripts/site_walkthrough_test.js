const { chromium } = require('playwright');
const assert = require('assert');
const BASE = process.env.BASE, OUT = process.env.OUT, W = +(process.env.W || 390);
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: 844 }, deviceScaleFactor: 1 });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
  const page = await ctx.newPage();
  page.setDefaultTimeout(10000);
  // plain hashes: the id in lower case, every run of other characters turned into a hyphen (the page's mkSlug)
  const slug = id => String(id).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'x';
  // a list shows three, then more: open everything
  const showAll = async () => { for (let i = 0; i < 20; i++) { const b = page.locator('#view [data-act=more]:not([data-n="3"])').last(); if (!(await b.count())) break; await b.click(); } };
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text() + ' @' + (m.location().url || '')); });
  page.on('pageerror', e => errors.push('PAGEERROR ' + e.message));
  const overflow = async (tag) => {
    const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
      bad: [...document.querySelectorAll('#view *, #foot *, #tray *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > window.innerWidth + 1 || r.left < -1) && !e.closest('svg'); }).slice(0, 5).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right)) }));
    assert(o.sw <= o.cw, `horizontal overflow on ${tag}: ${o.sw} > ${o.cw} ${o.bad}`);
    if (o.bad.length) console.log('WARN offscreen', tag, o.bad);
  };
  const small = async (tag) => {
    const s = await page.evaluate(() => [...document.querySelectorAll('#view a, #view button, #view summary, #view input, #trail a, #tray a')].filter(e => !e.closest('svg') && !e.closest('p.slot-text')).map(e => { const r = e.getBoundingClientRect(); return { t: (e.className || e.tagName) + ':' + (e.textContent || '').trim().slice(0, 24), w: Math.round(r.width), h: Math.round(r.height) }; }).filter(x => x.h > 0 && x.h < 43.5).slice(0, 8));
    if (s.length) console.log('SMALL targets', tag, JSON.stringify(s));
  };
  const shot = async (name, full) => { if (W !== 390) return; await page.waitForFunction(() => !document.getElementById('toast').classList.contains('on'), null, { timeout: 5000 }).catch(() => {});
    if (full) { const y = await page.evaluate(() => window.scrollY); const h = await page.evaluate(() => document.documentElement.scrollHeight); await page.setViewportSize({ width: W, height: h }); await page.waitForTimeout(150); await page.screenshot({ path: `${OUT}/${name}.png` }); await page.setViewportSize({ width: W, height: 844 }); await page.evaluate(y => window.scrollTo(0, y), y); }
    else await page.screenshot({ path: `${OUT}/${name}.png` }); };
  const data = await (await page.request.get(BASE + '/data.json')).json();

  await page.goto(BASE + '/index.html');
  await page.waitForSelector('.life');
  // first-run tour
  await page.waitForSelector('#tour:not([hidden])');
  await page.click('[data-act=tour-next]'); await page.click('[data-act=tour-next]'); await page.click('[data-act=tour-next]');
  assert(await page.isHidden('#tour'));
  assert.strictEqual(await page.locator('.life').count(), data.years.length);
  const nStar = data.units.filter(u => u.confirm && u.confirm.asterisk).length;
  assert.strictEqual(nStar, data.meta.counts.shown_with_asterisk);
  assert.strictEqual(+(await page.getAttribute('#view .confnote', 'data-conf-count')), nStar, 'home states how many places carry an asterisk');
  assert((await page.textContent('#view .confnote')).includes(nStar + ' of the ' + data.units.length + ' places'));
  assert((await page.textContent('#sources')).includes('OpenStreetMap data of 14 Nov 2026'));
  await overflow('home'); await small('home');
  await shot('01-home', true);

  // a year: the one holding Bogota (asterisk unit)
  const star = data.units.find(u => u.rent.asterisk && u.all_in_gross > u.all_in);
  const y1 = star.year;
  await page.click(`a.life[href="#exp-${slug(y1)}"]`);
  await page.waitForSelector('.hero h1');
  assert.strictEqual(+(await page.getAttribute('#sec-hoods .confnote', 'data-conf-count')), data.units.filter(u => u.year === y1 && u.confirm.asterisk).length, 'year states its asterisk count');
  await overflow('year'); await small('year');
  await shot('02-year', true);
  // year five-point explanation
  await page.click('.ylist button.pt >> nth=0'); await page.waitForSelector('#sheet.open'); await page.click('#shClose');

  // neighborhood with an avoid card
  const hAvoid = data.neighborhoods.find(h => h.counts.avoid > 0 && h.counts.shown > 0 && h.name === 'Jamaica') || data.neighborhoods.find(h => h.counts.avoid > 0 && h.counts.shown > 0);
  await page.goto(BASE + '/index.html#hood-' + slug(hAvoid.id));
  await page.waitForSelector('.unit.avoid');
  assert.strictEqual(await page.locator('.unit.avoid').count(), hAvoid.counts.avoid);
  // top three first, then "Show more places"
  assert.strictEqual(await page.locator('#sec-places article.unit').count(), Math.min(3, hAvoid.counts.shown), 'a neighborhood opens on its top three places');
  if (hAvoid.counts.shown > 3) assert((await page.textContent('#sec-places .morectl')).includes('3 of ' + hAvoid.counts.shown + ' places shown'));
  await showAll();
  assert.strictEqual(await page.locator('#sec-places article.unit').count(), hAvoid.counts.shown);
  await overflow('hood'); await small('hood');
  await shot('03-neighborhood', true);
  await page.locator('#sec-avoid').scrollIntoViewIfNeeded();
  await page.evaluate(() => document.getElementById('sec-avoid').scrollIntoView());
  await shot('03b-neighborhood-avoid-card');
  // hood with held list
  const hHeld = data.neighborhoods.find(h => h.counts.held > 0 && h.counts.shown > 0);
  await page.goto(BASE + '/index.html#hood-' + slug(hHeld.id));
  await page.waitForSelector('#sec-call .callbox');
  assert.strictEqual(await page.locator('#sec-call .callitem').count(), hHeld.counts.held);
  assert.strictEqual(await page.locator('.callbox [data-act=hold]').count(), 0);
  assert((await page.textContent('#sec-call')).includes('two or more things'));
  await overflow('hood-held');
  await page.evaluate(() => document.getElementById('sec-call').scrollIntoView());
  await shot('03c-worth-a-phone-call');
  // places waiting for a live re-check that are not already in the phone-call list: "Not re-checked yet"
  const known = new Set([...data.held, ...data.units, ...data.avoid].map(u => u.id)), hoodIds = new Set(data.neighborhoods.map(h => h.id));
  const waitOnly = (data.awaiting_live_check || []).filter(a => !known.has(a.id));
  const waitHood = waitOnly.find(a => hoodIds.has(a.hood_id));
  console.log('awaiting live check:', (data.awaiting_live_check || []).length, '| not already in held:', waitOnly.length, '| of those in a listed neighborhood:', waitOnly.filter(a => hoodIds.has(a.hood_id)).length);
  if (waitHood) {
    await page.goto(BASE + '/index.html#hood-' + slug(waitHood.hood_id));
    await page.waitForSelector('#sec-wait .callitem');
    assert.strictEqual(await page.locator('#sec-wait .callitem').count(), waitOnly.filter(a => a.hood_id === waitHood.hood_id).length);
    assert((await page.textContent('#sec-wait h3')).includes('Not re-checked yet'));
    await overflow('hood-wait');
    await page.evaluate(() => document.getElementById('sec-wait').scrollIntoView());
    await shot('03d-not-re-checked-yet');
  }

  // neighborhood with local rules: summaries with source links under "For the car" and "For the dog"
  const hRules = data.neighborhoods.find(h => h.counts.shown > 0 && (h.local.parking_rules || []).length >= 3 && (h.local.dog_rules || []).length && h.state !== 'NY') || data.neighborhoods.find(h => h.counts.shown > 0 && (h.local.parking_rules || []).length && (h.local.dog_rules || []).length);
  await page.goto(BASE + '/index.html#hood-' + slug(hRules.id));
  await page.waitForSelector('.amen .rules');
  assert.strictEqual(await page.locator('.amen .rules li').count(), hRules.local.parking_rules.length + hRules.local.dog_rules.length, 'every local rule is listed');
  assert.strictEqual(await page.locator('.amen .rules li a.srcl').count(), [...hRules.local.parking_rules, ...hRules.local.dog_rules].filter(r => /^https?:/.test(r.url)).length, 'every rule with a URL links to it');
  assert((await page.textContent('.amen')).includes(hRules.local.parking_rules[0].summary));
  assert.strictEqual(await page.locator('#no-park-rules').count(), 0);
  if (!(hRules.local.voices || []).length && await page.locator('#no-voices').count()) assert((await page.textContent('#no-voices')).includes('No resident comments found yet'));
  assert((await page.textContent('#view')).includes('How we got this'));
  await overflow('hood-rules'); await small('hood-rules');
  await shot('09-neighborhood-local-rules', true);
  // its Saturday-night and wake-up sheets quote the rules
  const uRules = data.units.find(u => u.hood_id === hRules.id);
  await page.goto(BASE + '/index.html#unit-' + slug(uRules.id)); await page.waitForSelector('.tile[data-k=sat]');
  for (const [k, key, kinds] of [['sat', 'parking_rules', ['overnight_parking', 'resident_permit', 'guest_parking', 'municipal_lot_overnight']], ['wake', 'dog_rules', ['leash_law', 'parks_and_beaches', 'dog_park', 'waste']]]) {
    await page.click(`.tile[data-k=${k}]`); await page.waitForSelector('#sheet.open');
    const want = hRules.local[key].filter(r => kinds.includes(r.rule)), body = await page.textContent('#sheetBody');
    for (const r of want) assert(body.includes(r.summary), k + ' sheet quotes the rule ' + r.rule);
    assert(body.includes('How we got this'));
    if (k === 'sat') { await page.waitForTimeout(300); await shot('09b-saturday-sheet-local-rules'); }
    await overflow('sheet-' + k);
    await page.keyboard.press('Escape'); await page.waitForSelector('#sheet:not(.open)');
  }
  // neighborhood with no local rules: says so, and its places get the parking question
  const hNone = data.neighborhoods.find(h => h.counts.shown > 0 && !(h.local.parking_rules || []).length);
  if (hNone) {
    await page.goto(BASE + '/index.html#hood-' + slug(hNone.id)); await page.waitForSelector('#no-park-rules');
    assert((await page.textContent('#no-park-rules')).includes('Local parking rules not found yet'));
    const qs = await page.evaluate(id => window.__houseHunt.tourQs(id), hNone.unit_ids[0]);
    assert(qs.includes('Where do residents park overnight, and is a permit needed?'));
    await overflow('hood-no-rules');
  }
  // a parking rule that bans overnight street parking or ties the permit to registration shows on a unit with street or unknown parking
  const flagRe = [['overnight_parking', /\bbanned\b|not allowed|needs (a|the) permit|permit-only|may not park|overnight (parking )?permit|all-night parking restrictions/i], ['resident_permit', /out-of-state|out-of-town|registered in|registration[^.]{0,60}(show|address|same)|(licen[cs]e and|valid vehicle|motor vehicle|permanent vehicle) registration/i]];
  const flagged = h => (h.local.parking_rules || []).filter(r => flagRe.some(([k, re]) => r.rule === k && re.test(r.summary)));
  const hoodBy = Object.fromEntries(data.neighborhoods.map(h => [h.id, h]));
  const uStreet = data.units.filter(u => (u.parking.rank == null || u.parking.rank < 2) && flagged(hoodBy[u.hood_id]).length);
  const uGarage = data.units.find(u => u.parking.rank >= 2 && flagged(hoodBy[u.hood_id]).length);
  console.log('units with street or unknown parking under a flagged parking rule:', uStreet.length);
  if (uStreet.length) {
    await page.goto(BASE + '/index.html#unit-' + slug(uStreet[0].id)); await page.waitForSelector('#park-rules');
    assert.strictEqual(await page.locator('#park-rules li').count(), flagged(hoodBy[uStreet[0].hood_id]).length);
    assert(await page.locator('#park-rules a.srcl').count() >= 1);
    await overflow('unit-park-rules');
    await page.evaluate(() => { const r = document.getElementById('park-rules').getBoundingClientRect(); window.scrollBy(0, r.top - 70); });
    await shot('10-unit-street-parking-rules');
  }
  if (uGarage) { await page.goto(BASE + '/index.html#unit-' + slug(uGarage.id)); await page.waitForSelector('#tour-qs'); assert.strictEqual(await page.locator('#park-rules').count(), 0); }

  // a unit with a confirmation asterisk, reached from its card
  const conf = data.units.find(u => u.confirm.asterisk && !u.rent.asterisk) || data.units.find(u => u.confirm.asterisk);
  await page.goto(BASE + '/index.html#hood-' + slug(conf.hood_id)); await page.waitForSelector('#sec-places'); await showAll();
  assert.strictEqual(await page.locator('#sec-places article.unit:has(.confl)').count(), data.units.filter(u => u.hood_id === conf.hood_id && u.confirm.asterisk).length, 'each asterisk place shows it on its card');
  await page.click(`a.btn[href="#unit-${slug(conf.id)}"]`);
  await page.waitForSelector('#confirm-box');
  assert((await page.textContent('#confirm-box')).includes(conf.confirm.why));
  assert((await page.textContent('.unit h4')).includes('*'));
  assert((await page.textContent('#confirm-box h4')).includes('Still to confirm'));
  if (await page.locator('#confirm-box p:has-text("What to ask:")').count()) {
    const confQ = (await page.locator('#confirm-box p:has-text("What to ask:")').first().textContent()).replace('What to ask: ', '');
    assert((await page.textContent('#tour-qs')).includes(confQ), 'the confirmation question is also in the tour questions'); }
  await overflow('unit-confirm'); await small('unit-confirm');
  await shot('08-unit-confirm-asterisk', true);
  const noConf = data.units.find(u => !u.confirm.asterisk);
  if (noConf) { await page.goto(BASE + '/index.html#unit-' + slug(noConf.id)); await page.waitForSelector('#tour-qs'); assert.strictEqual(await page.locator('#confirm-box, .unit .confl, .cstar').count(), 0); }
  // small dogs with no weight number: a plain note, not in "Gives us pause"
  const sd = data.units.find(u => u.dog.weight_limit_lb == null && u.dog.size_note);
  if (sd) { await page.goto(BASE + '/index.html#unit-' + slug(sd.id)); await page.waitForSelector('#dog-note');
    assert((await page.textContent('#dog-note')).includes('The page says small dogs; no weight number given'));
    assert(!((await page.locator('.panel.pause').count()) && (await page.textContent('.panel.pause')).includes('small dogs'))); }
  // a building with nothing readable in public records or reviews says so
  const noEv = data.units.find(u => ['none readable', 'rating screen: not_enough_data'].includes(u.evidence.public_evidence) && !u.evidence.items.length && !u.evidence.positive.length && !u.evidence.pause_notes);
  if (noEv) { await page.goto(BASE + '/index.html#unit-' + slug(noEv.id)); await page.waitForSelector('.panel.pause');
    assert((await page.textContent('.panel.pause')).includes('No public records or readable reviews for this building; ask on the tour'));
    await overflow('unit-no-evidence');
    await page.evaluate(() => { const r = document.querySelector('.panel.pause').getBoundingClientRect(); window.scrollBy(0, r.top - 200); });
    await shot('11-unit-no-public-evidence'); }
  console.log('no public evidence:', data.units.filter(u => ['none readable', 'rating screen: not_enough_data'].includes(u.evidence.public_evidence) && !u.evidence.items.length && !u.evidence.positive.length && !u.evidence.pause_notes).length, 'units | small-dog note:', data.units.filter(u => u.dog.weight_limit_lb == null && u.dog.size_note).length);

  // go via UI: home -> year -> hood -> unit (asterisk)
  await page.goto(BASE + '/index.html#lives'); await page.waitForSelector('.life');
  await page.click(`a.life[href="#exp-${slug(y1)}"]`);
  await page.waitForSelector('.viewsw');
  if (await page.getAttribute('.viewsw [data-v=list]', 'aria-pressed') !== 'true') await page.click('.viewsw [data-v=list]');
  await showAll();
  await page.click(`a.hood[href="#hood-${slug(star.hood_id)}"]`);
  await page.waitForSelector('#sec-places'); await showAll();
  await page.click(`a.btn[href="#unit-${slug(star.id)}"]`);
  await page.waitForSelector('#rent-terms');
  assert((await page.textContent('.sign strong')).includes('*'));
  assert((await page.textContent('#rent-terms')).includes(star.rent.offer_text.slice(0, 30)));
  await overflow('unit'); await small('unit');
  await shot('04-unit-rent-asterisk', true);
  await page.click('details.receipt summary');
  assert((await page.textContent('details.receipt')).includes('Not counted yet') || star.all_in_unknown.length === 0);
  await page.locator('details.receipt').scrollIntoViewIfNeeded();
  await page.evaluate(() => { const r = document.querySelector('details.receipt').getBoundingClientRect(); window.scrollBy(0, r.top - 70); });
  await shot('05-receipt-open');
  await overflow('receipt');
  // tile sheets: all six
  for (const k of ['wake', 'work', 'after', 'night', 'sat', 'sun']) {
    await page.click(`.tile[data-k=${k}]`); await page.waitForSelector('#sheet.open');
    assert((await page.locator('#sheetBody li').count()) >= 3);
    if (k === 'night') { await page.waitForTimeout(300); await shot('04b-tile-sheet-night'); assert(await page.locator('#sheetBody a.srcl').count() >= 1, 'night sheet has a source link'); }
    await page.keyboard.press('Escape'); await page.waitForSelector('#sheet:not(.open)');
  }
  // hold it
  await page.click('.unit > [data-act=hold]');
  // second unit in a different year, with evidence
  const two = data.units.find(u => u.year !== y1 && u.evidence.items.length && u.evidence.positive.length) || data.units.find(u => u.year !== y1);
  await page.goto(BASE + '/index.html#unit-' + slug(two.id));
  await page.waitForSelector('.unit > [data-act=hold]');
  assert(await page.locator('.panel.pause .quote a.srcl').count() >= 1);
  await overflow('unit2');
  await shot('04c-unit-with-evidence', true);
  await page.click('.unit > [data-act=hold]');
  assert.strictEqual(await page.locator('.slot.full').count(), 2);
  await page.click('#goBtn');
  await page.waitForSelector('.pairbox');
  await overflow('compare'); await small('compare');
  await shot('06-compare', true);
  const rows1 = await page.locator('#cmp-rows .rowc').count();
  await page.click('#ties');
  const rows2 = await page.locator('#cmp-rows .rowc').count();
  assert.strictEqual(rows2, 10, 'all ten rows when ties shown, got ' + rows2);
  assert(rows1 <= rows2);
  console.log('compare rows hidden-ties/all:', rows1, rows2, await page.textContent('#tiesNote'));
  await page.click('#ties');
  // five-point
  assert.strictEqual(await page.locator('#sec-scale button.pt').count(), 18);
  await page.click('#sec-scale button.pt >> nth=0'); await page.waitForSelector('#sheet.open');
  const st = await page.textContent('#sheetBody');
  assert(st.includes('Staying in Queens') && st.includes('The bands'));
  await page.waitForTimeout(300); await shot('06b-five-point-explanation');
  await page.click('#shClose');
  // third hold then pair buttons
  // limits
  await page.goto(BASE + '/index.html#lives'); await page.waitForSelector('.life');
  await page.click('[data-act=limits-open]'); await page.waitForSelector('#limsheet.open');
  const before = await page.textContent('#fitline');
  await page.locator('#lim-cost').fill('2400'); await page.locator('#lim-safe').fill('3'); await page.locator('#lim-sqft').fill('700'); await page.locator('#lim-mins').fill('30');
  const after = await page.textContent('#fitline');
  assert(before !== after, 'limits changed counts');
  const expect = data.units.filter(u => u.all_in <= 2400 && Math.round(u.moments.sun.drive_min) <= 30 && u.moments.night.violent_vs_jamaica != null && u.moments.night.violent_vs_jamaica < 0.5 && u.sqft != null && u.sqft >= 700).length;
  assert(after.startsWith(expect + ' of '), `limit count ${after} vs expected ${expect}`);
  console.log('limits:', before, '->', after, '| greyed years:', await page.locator('.life.none').count());
  await page.waitForTimeout(300); await shot('07-limits-sheet');
  await overflow('limits');
  await page.click('[data-act=limits-close]');
  await shot('07b-home-with-limits', true);
  // the new limit: only places with nothing left to confirm
  await page.click('[data-act=limits-open]'); await page.click('[data-act=limits-reset]');
  await page.check('#lim-clear');
  const clearN = data.units.filter(u => !u.confirm.asterisk).length;
  assert((await page.textContent('#fitline')).startsWith(clearN + ' of '), 'toggle count ' + (await page.textContent('#fitline')) + ' vs ' + clearN);
  await page.waitForTimeout(300); await shot('07c-limits-nothing-left-to-confirm');
  await page.click('[data-act=limits-close]');
  await page.goto(BASE + '/index.html#hood-' + slug(conf.hood_id)); await page.waitForSelector('#sec-places'); await showAll();
  assert.strictEqual(await page.locator('#sec-places .unit.out').count(), data.units.filter(u => u.hood_id === conf.hood_id && u.confirm.asterisk).length);
  assert((await page.textContent('#sec-places .unit.out .why')).includes('Still to confirm'));
  await page.reload(); await page.waitForSelector('#sec-places');
  assert(await page.isChecked('#lim-clear'), 'the toggle is remembered');
  await page.goto(BASE + '/index.html#lives'); await page.waitForSelector('.life');
  await page.click('[data-act=limits-open]'); await page.click('[data-act=limits-reset]'); await page.click('[data-act=limits-close]');
  assert.strictEqual(await page.locator('.life.none').count(), 0);
  // copy tour list
  await page.click('#goBtn'); await page.waitForSelector('[data-act=copy]');
  await page.click('[data-act=copy]');
  await page.waitForFunction(() => document.getElementById('copyStatus').textContent.length > 0);
  console.log('copy status:', await page.textContent('#copyStatus'));
  const txt = await page.evaluate(() => window.__houseHunt.tourText());
  assert(txt.includes(star.tour_questions[0]) && txt.includes('House 2'));
  let clip = null; try { clip = await page.evaluate(() => navigator.clipboard.readText()); } catch (e) {}
  if (clip !== null) assert.strictEqual(clip, txt);
  // every hood and unit renders without error (performance + robustness)
  const t0 = Date.now();
  const res = await page.evaluate(async (ids) => { let worst = 0, n = 0; for (const h of ids) { const t = performance.now(); location.hash = h; await new Promise(r => setTimeout(r, 0)); worst = Math.max(worst, performance.now() - t); n++; if (document.documentElement.scrollWidth > document.documentElement.clientWidth) return 'overflow at ' + h; } return n + ' views, worst ' + Math.round(worst) + ' ms'; },
    [...data.years.map(y => 'exp-' + slug(y.id)), ...data.neighborhoods.map(h => 'hood-' + slug(h.id)), ...data.units.map(u => 'unit-' + slug(u.id)), 'compare']);
  console.log('all views:', res, 'in', Date.now() - t0, 'ms');
  assert(!String(res).startsWith('overflow'), res);
  // resident voices: empty now, so feed one neighborhood made-up test quotes (in this test only) to check the layout that will fill in later
  const page2 = await ctx.newPage();
  page2.on('console', m => { if (m.type() === 'error') errors.push('voices page: ' + m.text()); }); page2.on('pageerror', e => errors.push('voices PAGEERROR ' + e.message));
  const vh = data.neighborhoods.find(h => h.counts.shown > 0);
  await page2.route('**/data.json', async route => { const d = JSON.parse(JSON.stringify(data)); const h = d.neighborhoods.find(x => x.id === vh.id);
    h.local.voices = [
      { excerpt: 'TEST quote, positive, noise.', theme: 'noise', sentiment: 'positive', context: 'renter', source: 'example forum', date: '2026-05-02', url: 'https://example.com/a' },
      { excerpt: 'TEST quote, positive two, noise.', theme: 'noise', sentiment: 'positive', context: '', source: 'example forum', date: '2026-08-11', url: 'https://example.com/b' },
      { excerpt: 'TEST quote, positive three, noise.', theme: 'noise', sentiment: 'positive', context: '', source: 'example forum', date: '2025-01-11', url: 'https://example.com/c' },
      { excerpt: 'TEST quote, negative, noise.', theme: 'noise', sentiment: 'negative', context: 'owner', source: 'example forum', date: '2026-03-09', url: 'https://example.com/d' },
      { excerpt: 'TEST quote, negative, parking, with a very long unbroken address https://example.com/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.', theme: 'parking', sentiment: 'negative', context: '', source: 'example forum', date: '', url: '' }];
    h.local.survey = [{ measure: 'would_recommend_share', value: '71%', source: 'example survey', as_of: '2026-06-30', url: 'https://example.com/s' }];
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(d) }); });
  await page2.goto(BASE + '/index.html#hood-' + slug(vh.id)); await page2.waitForSelector('#sec-voices .quote');
  assert.strictEqual(await page2.locator('#no-voices').count(), 0);
  assert.strictEqual(await page2.locator('#sec-voices .vtheme').count(), 3, 'two themes and the survey heading');
  assert.strictEqual(await page2.locator('#sec-voices > .quote.pos').count(), 1, 'one positive shown against the one negative');
  assert.strictEqual(await page2.locator('#sec-voices > .quote.neg').count(), 2);
  assert.strictEqual(await page2.locator('#sec-voices details .quote').count(), 2, 'the other positives are folded');
  assert.strictEqual(await page2.locator('#sec-voices .quote a.srcl').count(), 4);
  assert((await page2.textContent('#sec-voices')).includes('Would recommend share: 71%.'));
  const vo = await page2.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth); assert(vo <= 0, 'voices overflow ' + vo);
  await page2.close();
  console.log('console errors:', errors.length ? errors : 'none');
  assert.strictEqual(errors.length, 0);
  await browser.close();
  console.log('OK width', W);
})().catch(e => { console.error('FAIL', e); process.exit(1); });
