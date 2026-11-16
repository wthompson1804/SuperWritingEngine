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
  // ================= Map (docs/MAP_COMPONENT.md, "Map integration" in docs/SITE_NOTES.md) =================
  // The most isolated tappable mark that is on screen, clear of the map's own buttons, the sticky trail and the bottom bar.
  const pickMark = async (pg) => pg.evaluate(() => {
    const svg = document.querySelector('.hhm-svg'), tray = document.getElementById('tray').getBoundingClientRect(), trail = document.getElementById('trail').getBoundingClientRect();
    const top0 = trail.height ? trail.bottom + 6 : 6; window.scrollBy(0, svg.getBoundingClientRect().top - top0);
    const r = svg.getBoundingClientRect(), bottom = Math.min(r.bottom, tray.top) - 12;
    const all = [...svg.querySelectorAll('.hhm-dot:not(.dim)')].map(g => { const q = g.getBoundingClientRect(); return { x: q.x + q.width / 2, y: q.y + q.height / 2, label: g.getAttribute('aria-label') }; });
    const home = svg.querySelector('g[pointer-events="none"]').getBoundingClientRect();
    const ok = all.filter(a => a.y > r.top + 64 && a.y < bottom && a.x > r.left + 14 && a.x < r.right - 66 && !(a.x > home.left - 8 && a.x < home.right + 8 && a.y > home.top - 8 && a.y < home.bottom + 8));
    ok.forEach(a => { a.gap = Math.min(...all.filter(o => o !== a).map(o => Math.hypot(o.x - a.x, o.y - a.y)), 999); });
    ok.sort((a, b) => b.gap - a.gap); return ok[0] || null; });
  const tapMark = async (pg, touch) => { let m = null;
    for (let i = 0; i < 4; i++) { m = await pickMark(pg); assert(m, 'a mark is on screen to tap');
      if (touch) await pg.touchscreen.tap(m.x, m.y); else await pg.mouse.click(m.x, m.y);
      try { await pg.waitForSelector('.hhm-card .hhm-go', { timeout: 1500 }); return m; } catch (e) { await pg.waitForTimeout(400); } }
    throw new Error('no card opened after tapping a mark: ' + JSON.stringify(m)); };
  const noSideScroll = async (pg, tag) => { const o = await pg.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]); assert(o[0] <= o[1], `horizontal page scroll on ${tag}: ${o[0]} > ${o[1]}`); };
  const centre = async (pg, sel) => pg.evaluate(s => { const e = document.querySelector(s), r = e.getBoundingClientRect(), tray = document.getElementById('tray').getBoundingClientRect(); window.scrollBy(0, r.top + r.height / 2 - tray.top / 2); }, sel);
  // First screen map -> New York City -> a mark -> card -> "See places" -> the neighborhood -> Back; then an experience: List -> Map -> a mark -> Back -> List.
  const mapFlow = async (pg, d, tag, o) => { o = o || {};
    const w = pg.viewportSize().width, hoodByName = n => d.neighborhoods.filter(h => (h.name + (h.state ? ', ' + h.state : '')) === n);
    await pg.waitForSelector('.life'); if (await pg.isVisible('#tour')) await pg.click('[data-act=tour-skip]');
    await pg.evaluate(() => { location.hash = '#lives'; }); await pg.waitForSelector('#hhmap .hhm');
    // tiles stay the way in; the map sits below them behind a jump control
    assert(await pg.evaluate(() => document.querySelector('.life').getBoundingClientRect().top < document.getElementById('sec-map').getBoundingClientRect().top), 'the experience tiles come before the map');
    await pg.click('[data-act=scrollto][data-to=sec-map]');
    assert.strictEqual(await pg.locator('.hhm-chip').count(), d.years.length);
    assert.strictEqual(await pg.locator('.hhm-chip[aria-pressed=true]').count(), 0, 'the overview starts with every experience shown');
    const chips = await pg.evaluate(() => [...document.querySelectorAll('.hhm-chip')].map(c => { const r = c.getBoundingClientRect(), t = [...c.querySelectorAll('.hhm-full,.hhm-short')].find(e => e.offsetParent !== null), p = c.querySelector('path'), tr = t.getBoundingClientRect();
      return { top: Math.round(r.top), text: t.textContent, fill: p.getAttribute('fill'), d: p.getAttribute('d'), clipped: tr.right > r.right + 0.5 || tr.left < r.left - 0.5 || c.scrollWidth > c.clientWidth + 1 }; }));
    const rows = new Set(chips.map(c => c.top)).size;
    if (w >= 360) assert(rows <= 2, `${tag}: six chips take ${rows} rows`); else console.log(`${tag}: chips take ${rows} rows at ${w}px`);
    chips.forEach((c, i) => { const y = d.years[i], full = String(y.display_label || y.label).replace(/ Year$/, ' Experience'), short = full.replace(/^The\s+/, '').replace(/\s+Experience$/, '');
      assert(!/Year\b/.test(c.text), 'chip says experience, not year: ' + c.text);
      assert.strictEqual(c.text, w < 520 ? short : full, 'chip label'); assert(!c.clipped, `${tag}: chip text is clipped: ${c.text}`); });
    // one colour and shape per experience: the tile marker is the chip's (and so the map's)
    const tiles = await pg.evaluate(() => [...document.querySelectorAll('a.life h3 .ymk path')].map(p => ({ fill: p.getAttribute('fill') })));
    assert.strictEqual(tiles.length, d.years.length, 'every experience tile carries its marker');
    tiles.forEach((t, i) => assert.strictEqual(t.fill, chips[i].fill, 'tile marker colour matches the map legend'));
    assert.strictEqual(new Set(chips.map(c => c.fill)).size, d.years.length); assert.strictEqual(new Set(chips.map(c => c.d)).size, d.years.length, 'six different shapes');
    assert.strictEqual(await pg.evaluate(() => [...document.querySelectorAll('a.life h3 .ymk')].map(s => s.getAttribute('data-shape')).join()), await pg.evaluate(() => window.__houseHunt.marks().map(m => m.shape).join()));
    assert.strictEqual(await pg.locator('.hhm-dot').count(), await pg.evaluate(() => window.__houseHunt.mapHoods()), 'one mark per listed neighborhood');
    await noSideScroll(pg, tag + ' first screen');
    if (o.shot) { await pg.evaluate(() => { const r = document.getElementById('sec-map').getBoundingClientRect(); window.scrollBy(0, r.top - 8); }); await o.shot('map-int-01-first-screen-map'); }
    await centre(pg, '[data-region=nyc]'); await pg.click('[data-region=nyc]'); await pg.waitForTimeout(o.reduced ? 80 : 450);
    assert(await pg.isVisible('.hhm-reset'), 'zoomed: "Whole map" is offered');
    const m = await tapMark(pg, o.touch);
    const name = (await pg.textContent('.hhm-card h3')).trim(), cardText = await pg.textContent('.hhm-card');
    const H = d.neighborhoods.find(h => m.label.indexOf(h.name + (h.state ? ', ' + h.state : '') + '. ') === 0 && name.indexOf(h.name) === 0);
    assert(H, `${tag}: the card (${name}) is the mark that was tapped (${m.label})`);
    assert(/\d+\s*places? shown|\d+ of \d+\s*places fit your limits/.test(cardText), 'the card gives the unit count: ' + cardText);
    if (H.rank_in_experience != null) { const of = d.years.find(y => y.id === H.year).hood_ids.length;
      assert((await pg.textContent('.hhm-card .hhm-rank')).trim() === (H.rank_in_experience === 1 ? 'Top pick' : '#' + H.rank_in_experience + ' of ' + of), 'rank within its experience: ' + cardText); }
    assert(/Experience/.test(await pg.textContent('.hhm-card .hhm-yr')), 'the card names the experience');
    await noSideScroll(pg, tag + ' card');
    if (o.shot) { await pg.evaluate(() => { const r = document.querySelector('.hhm-stage').getBoundingClientRect(); window.scrollBy(0, r.top + r.height * 0.55); }); await o.shot('map-int-03-selected-card'); }
    await centre(pg, '.hhm-go'); const yBefore = await pg.evaluate(() => window.scrollY);
    await pg.click('.hhm-go'); await pg.waitForSelector('#sec-places, .hero h1');
    assert.strictEqual(await pg.evaluate(() => location.hash), '#hood-' + slug(H.id), '"See places" lands on the neighborhood');
    assert.strictEqual((await pg.textContent('.hero h1')).trim(), H.name);
    assert.strictEqual(await pg.locator('.hhm').count(), 0, 'the map is gone with its view'); assert.strictEqual(await pg.evaluate(() => window.__houseHunt.map()), null, 'and was destroyed');
    assert(await pg.locator('#trail .path .ymk').count() >= 1, 'the breadcrumb carries the experience marker');
    // Back: the first screen again, at the same spot, with the same card open
    await pg.goBack(); await pg.waitForSelector('#hhmap .hhm');
    assert.strictEqual(await pg.evaluate(() => location.hash), '#lives');
    assert.strictEqual((await pg.textContent('.hhm-card h3')).trim(), name, 'Back reopens the card that was open');
    assert(Math.abs((await pg.evaluate(() => window.scrollY)) - yBefore) < 4, 'Back returns to the same scroll position');
    // inside an experience: list by default, top three then more; Map is the switch beside it
    const Y = d.years.find(y => y.id === H.year) || d.years[0], nH = Y.hood_ids.length;
    await pg.evaluate(h => { location.hash = h; }, '#exp-' + slug(Y.id)); await pg.waitForSelector('.viewsw');
    if (!o.keepPref) assert.strictEqual(await pg.getAttribute('.viewsw [data-v=list]', 'aria-pressed'), 'true', 'the list is the default');
    else if (await pg.getAttribute('.viewsw [data-v=list]', 'aria-pressed') !== 'true') await pg.click('.viewsw [data-v=list]');
    assert.strictEqual(await pg.locator('#sec-hoods a.hood').count(), Math.min(3, nH), 'top three neighborhoods first');
    if (nH > 3) assert((await pg.textContent('#sec-hoods .morectl')).includes('3 of ' + nH + ' neighborhoods shown'));
    assert.strictEqual(await pg.locator('#sec-hoods a.hood small .ymk').count(), Math.min(3, nH), 'each neighborhood card carries the experience marker');
    assert.strictEqual(await pg.locator('#hhmap').count(), 0);
    await centre(pg, '.viewsw'); await pg.click('.viewsw [data-v=map]'); await pg.waitForSelector('#hhmap .hhm'); await pg.waitForTimeout(o.reduced ? 80 : 450);
    assert.strictEqual(await pg.getAttribute('.viewsw [data-v=map]', 'aria-pressed'), 'true');
    assert.strictEqual(await pg.locator('#sec-hoods a.hood').count(), 0);
    assert.strictEqual(await pg.getAttribute('.hhm-chip[aria-pressed=true]', 'data-year'), Y.id, 'the map opens filtered on this experience');
    assert.strictEqual(await pg.locator('.hhm-dot:not(.dim)').count(), await pg.evaluate(id => window.__houseHunt.mapHoods(id), Y.id), 'every neighborhood of the experience is a live mark');
    await noSideScroll(pg, tag + ' experience map');
    if (o.shot) { await pg.evaluate(() => { const r = document.querySelector('.viewsw').getBoundingClientRect(); window.scrollBy(0, r.top - 66); }); await o.shot('map-int-02-experience-map'); }
    const m2 = await tapMark(pg, o.touch), H2 = d.neighborhoods.find(h => h.year === Y.id && m2.label.indexOf(h.name + (h.state ? ', ' + h.state : '') + '. ') === 0);
    assert(H2, 'the tapped mark belongs to this experience: ' + m2.label);
    await centre(pg, '.hhm-go'); await pg.click('.hhm-go'); await pg.waitForSelector('.hero h1');
    assert.strictEqual(await pg.evaluate(() => location.hash), '#hood-' + slug(H2.id));
    await pg.goBack(); await pg.waitForSelector('.viewsw');
    assert.strictEqual(await pg.evaluate(() => location.hash), '#exp-' + slug(Y.id), 'Back from the neighborhood returns to the experience');
    assert.strictEqual(await pg.getAttribute('.viewsw [data-v=map]', 'aria-pressed'), 'true', 'still on Map after Back');
    assert.strictEqual((await pg.textContent('.hhm-card h3')).trim().indexOf(H2.name), 0, 'with the same card open');
    if (o.storage !== false) { await pg.reload(); await pg.waitForSelector('#hhmap .hhm'); assert.strictEqual(await pg.getAttribute('.viewsw [data-v=map]', 'aria-pressed'), 'true', 'Map is remembered after a reload'); }
    await centre(pg, '.viewsw'); await pg.click('.viewsw [data-v=list]');
    assert.strictEqual(await pg.locator('#sec-hoods a.hood').count(), Math.min(3, nH), 'back to the list: top three again');
    assert.strictEqual(await pg.locator('.hhm').count(), 0); assert.strictEqual(await pg.evaluate(() => window.__houseHunt.map()), null);
    if (o.shot) { await pg.evaluate(() => { const r = document.querySelector('.viewsw').getBoundingClientRect(); window.scrollBy(0, r.top - 66); }); await o.shot('map-int-04-experience-list'); }
    await pg.goBack(); await pg.waitForSelector('.life'); assert.strictEqual(await pg.evaluate(() => location.hash), '#lives', 'Back from the experience is the first screen');
    await noSideScroll(pg, tag + ' end');
    console.log(`map flow OK: ${tag} (${w}px) | ${name} -> #hood-${slug(H.id)} | ${Y.id}: ${H2.name}`);
  };
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
  await mapFlow(page, data, 'served page', { shot });

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
  // disclosures: "Good to know before you call" on the card and the place page, lighter than the asterisk, and in the tour questions
  const whats = u => [...new Set((u.disclosures || []).map(x => String(x.what || '').trim()).filter(w => w && w.toLowerCase() !== String(u.confirm.what || '').toLowerCase()))];
  const dU = data.units.find(u => whats(u).length >= 2 && !u.confirm.asterisk) || data.units.find(u => whats(u).length);
  console.log('places with a disclosure:', data.units.filter(u => whats(u).length).length, 'of', data.units.length);
  if (dU) {
    await page.goto(BASE + '/index.html#unit-' + slug(dU.id)); await page.waitForSelector('#good-to-know');
    assert.strictEqual(await page.locator('#good-to-know li').count(), whats(dU).length, 'every disclosure is listed once');
    const gtk = await page.textContent('#good-to-know'), tqs = await page.textContent('#tour-qs');
    assert(gtk.includes('Good to know before you call') && gtk.includes('Things to ask, not problems'));
    for (const w of whats(dU)) assert(gtk.toLowerCase().includes(w.toLowerCase()), 'disclosure shown: ' + w);
    for (const x of dU.disclosures) if (x.question) assert(tqs.includes(x.question), 'the disclosure question is in the tour questions: ' + x.question);
    if (!dU.confirm.asterisk) assert.strictEqual(await page.locator('#confirm-box, .cstar').count(), 0, 'a disclosure is not an asterisk');
    assert(await page.evaluate(() => { const b = getComputedStyle(document.getElementById('good-to-know')); return b.borderTopStyle === 'solid' && b.backgroundColor === 'rgb(255, 255, 255)'; }), 'the box is plain, not a warning');
    await overflow('unit-disclosures');
    await page.evaluate(() => { const r = document.getElementById('good-to-know').getBoundingClientRect(); window.scrollBy(0, r.top - 120); });
    await shot('12-unit-good-to-know');
    await page.goto(BASE + '/index.html#hood-' + slug(dU.hood_id)); await page.waitForSelector('#sec-places'); await showAll();
    const cardGtk = await page.locator(`#sec-places article.unit:has(a[href="#unit-${slug(dU.id)}"]) .gtk`).textContent();
    assert(cardGtk.startsWith('Good to know before you call:') && cardGtk.includes(whats(dU)[0]), 'the card carries the compact line: ' + cardGtk);
  }
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
  assert((await page.textContent('details.receipt')).toLowerCase().includes('not published') || star.all_in_unknown.length === 0, 'an unknown cost line reads "not published", never $0');
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
  // ten day-part rows, plus "Still to confirm" when either place has an asterisk or a disclosure
  const hasDisc = u => (u.disclosures || []).length > 0, extra = [star, two].some(u => u.confirm.asterisk || hasDisc(u)) ? 1 : 0;
  assert.strictEqual(rows2, 10 + extra, 'ten rows plus the confirm row when ties shown, got ' + rows2);
  if ([star, two].some(hasDisc)) { const t = await page.textContent('#cmp-rows'); assert(t.includes('Still to confirm') && t.includes('Good to know before you call'), 'disclosures sit in the Still to confirm row'); }
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
    h.toll_round_trip = 13.5; h.toll_round_trip_mail = 21.25; // made-up: both an E-ZPass and a mail-rate figure
    h.local.survey = [{ measure: 'would_recommend_share', value: '71%', source: 'example survey', as_of: '2026-06-30', url: 'https://example.com/s' }];
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(d) }); });
  await page2.goto(BASE + '/index.html#hood-' + slug(vh.id)); await page2.waitForSelector('#sec-voices .quote');
  assert.strictEqual(await page2.locator('#no-voices').count(), 0);
  { const facts = await page2.textContent('.hero .facts'); assert(facts.includes('$13.50 in tolls a visit with a New York E-ZPass') && !facts.includes('21.25'), 'E-ZPass figure with its note when a mail rate is also present: ' + facts); }
  { const real = await page.evaluate(() => document.body.textContent.includes('with a New York E-ZPass')); if (real) console.log('note: the current data already carries a mail-rate toll'); }
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
  // ---- the built single file (scripts/build_site.py), as it is published: phone, desktop, small phone with reduced motion,
  //      storage that throws, and the page with its outer doctype/html/head/body stripped and re-wrapped ----
  if (W === 390 && !process.env.NO_BUILT) {
    const fs = require('fs'), path = require('path'), os = require('os'), { pathToFileURL } = require('url');
    const built = process.env.BUILT || path.join(__dirname, '..', 'site', 'dist', 'index.html');
    const html = fs.readFileSync(built, 'utf8'), bytes = Buffer.byteLength(html);
    const part = re => { const m = html.match(re); return m ? Buffer.byteLength(m[0]) : 0; };
    const dataBytes = part(/<script>window\.HOUSE_HUNT_DATA=[\s\S]*?<\/script>/), baseBytes = part(/<script>window\.HOUSE_HUNT_MAP_BASE=[\s\S]*?<\/script>/);
    console.log(`built page: ${bytes} bytes (${(bytes / 1048576).toFixed(2)} MB) = data ${dataBytes} + map base ${baseBytes} + template ${bytes - dataBytes - baseBytes}`);
    assert(baseBytes > 1000, 'the built page carries the map base');
    if (bytes >= 4 * 1000 * 1000) console.log('WARN built page is over 4 MB');
    const wrapped = path.join(os.tmpdir(), 'house-hunt-rewrapped.html');
    fs.writeFileSync(wrapped, '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>skeleton</title></head><body>' +
      html.replace(/<!doctype[^>]*>/i, '').replace(/<\/?(html|head|body)\b[^>]*>/gi, '') + '</body></html>');
    const throwing = () => { const bad = () => { throw new Error('storage blocked'); }; try { Object.defineProperty(window, 'localStorage', { get: bad, configurable: true }); Object.defineProperty(window, 'sessionStorage', { get: bad, configurable: true }); } catch (e) {} };
    const configs = [
      { tag: 'built, phone touch', file: built, ctx: { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true }, o: { touch: true } },
      { tag: 'built, desktop', file: built, ctx: { viewport: { width: 1280, height: 900 } }, o: {} },
      { tag: 'built, small phone, reduced motion', file: built, ctx: { viewport: { width: 320, height: 640 }, hasTouch: true, isMobile: true, reducedMotion: 'reduce' }, o: { touch: true, reduced: true } },
      { tag: 'built, storage throws', file: built, ctx: { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true }, init: throwing, o: { touch: true, storage: false } },
      { tag: 'built, stripped and re-wrapped', file: wrapped, ctx: { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true }, o: { touch: true } },
      { tag: 'built, stripped and re-wrapped, desktop', file: wrapped, ctx: { viewport: { width: 1280, height: 900 } }, o: {} }];
    for (const c of configs) {
      const cx = await browser.newContext(c.ctx), pg = await cx.newPage(), errs = []; pg.setDefaultTimeout(10000);
      pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); pg.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
      if (c.init) await pg.addInitScript(c.init);
      await pg.goto(pathToFileURL(c.file).href); await pg.waitForSelector('.life');
      if (c.init) assert(await pg.evaluate(() => { try { window.localStorage.getItem('x'); return false; } catch (e) { return true; } }), 'storage really throws in this run');
      const d = await pg.evaluate(() => window.HOUSE_HUNT_DATA);
      await mapFlow(pg, d, c.tag, c.o);
      // every experience opens as a map without error
      await pg.evaluate(() => { location.hash = '#exp-' + location.hash.length; });
      for (const y of d.years) { await pg.evaluate(h => { location.hash = h; }, '#exp-' + slug(y.id)); await pg.waitForSelector('.viewsw'); if (await pg.getAttribute('.viewsw [data-v=map]', 'aria-pressed') !== 'true') await pg.click('.viewsw [data-v=map]'); await pg.waitForSelector('#hhmap .hhm-chip[aria-pressed=true]'); await noSideScroll(pg, c.tag + ' ' + y.id); }
      await pg.click('.viewsw [data-v=list]');
      assert.strictEqual(errs.length, 0, c.tag + ' console errors: ' + errs.join(' | '));
      await cx.close();
    }
    fs.unlinkSync(wrapped);
  }
  await browser.close();
  console.log('OK width', W);
})().catch(e => { console.error('FAIL', e); process.exit(1); });
