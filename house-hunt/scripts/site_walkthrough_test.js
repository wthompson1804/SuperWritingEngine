const { chromium } = require('playwright');
const assert = require('assert');
const BASE = process.env.BASE, OUT = process.env.OUT, W = +(process.env.W || 390);
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: 844 }, deviceScaleFactor: 1 });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
  const page = await ctx.newPage();
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
  await overflow('home'); await small('home');
  await shot('01-home', true);

  // a year: the one holding Bogota (asterisk unit)
  const star = data.units.find(u => u.rent.asterisk && u.all_in_gross > u.all_in);
  const y1 = star.year;
  await page.click(`a.life[href="#year-${encodeURIComponent(y1)}"]`);
  await page.waitForSelector('.hero h1');
  await overflow('year'); await small('year');
  await shot('02-year', true);
  // year five-point explanation
  await page.click('.ylist button.pt >> nth=0'); await page.waitForSelector('#sheet.open'); await page.click('#shClose');

  // neighborhood with an avoid card
  const hAvoid = data.neighborhoods.find(h => h.counts.avoid > 0 && h.counts.shown > 0 && h.name === 'Jamaica') || data.neighborhoods.find(h => h.counts.avoid > 0 && h.counts.shown > 0);
  await page.goto(BASE + '/index.html#hood-' + encodeURIComponent(hAvoid.id));
  await page.waitForSelector('.unit.avoid');
  assert.strictEqual(await page.locator('.unit.avoid').count(), hAvoid.counts.avoid);
  assert.strictEqual(await page.locator('#sec-places article.unit').count(), hAvoid.counts.shown);
  await overflow('hood'); await small('hood');
  await shot('03-neighborhood', true);
  await page.locator('#sec-avoid').scrollIntoViewIfNeeded();
  await page.evaluate(() => document.getElementById('sec-avoid').scrollIntoView());
  await shot('03b-neighborhood-avoid-card');
  // hood with held list
  const hHeld = data.neighborhoods.find(h => h.counts.held > 0 && h.counts.shown > 0);
  await page.goto(BASE + '/index.html#hood-' + encodeURIComponent(hHeld.id));
  await page.waitForSelector('.callbox');
  assert.strictEqual(await page.locator('.callbox .callitem').count(), hHeld.counts.held);
  assert.strictEqual(await page.locator('.callbox [data-act=hold]').count(), 0);
  await overflow('hood-held');

  // go via UI: home -> year -> hood -> unit (asterisk)
  await page.goto(BASE + '/index.html#lives'); await page.waitForSelector('.life');
  await page.click(`a.life[href="#year-${encodeURIComponent(y1)}"]`);
  await page.click(`a.hood[href="#hood-${encodeURIComponent(star.hood_id)}"]`);
  await page.waitForSelector('#sec-places');
  await page.click(`a.btn[href="#unit-${encodeURIComponent(star.id)}"]`);
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
  await page.goto(BASE + '/index.html#unit-' + encodeURIComponent(two.id));
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
    [...data.years.map(y => 'year-' + encodeURIComponent(y.id)), ...data.neighborhoods.map(h => 'hood-' + encodeURIComponent(h.id)), ...data.units.map(u => 'unit-' + encodeURIComponent(u.id)), 'compare']);
  console.log('all views:', res, 'in', Date.now() - t0, 'ms');
  assert(!String(res).startsWith('overflow'), res);
  console.log('console errors:', errors.length ? errors : 'none');
  assert.strictEqual(errors.length, 0);
  await browser.close();
  console.log('OK width', W);
})().catch(e => { console.error('FAIL', e); process.exit(1); });
