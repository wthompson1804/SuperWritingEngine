// Walk-through of the page at one width. Usage (from house-hunt/):
//   python3 scripts/page_data_extras.py && python3 scripts/build_site.py
//   (cd site && python3 -m http.server 8765 &)
//   BASE=http://localhost:8765 OUT=site/screens W=390 node scripts/site_walkthrough_test.js     (then W=1280 and W=320)
// BASE serves site/ (index.html fetches data.json and map_base.json). At W=390 it also opens the built single file
// (site/dist/index.html) as a phone, a desktop, a small phone with reduced motion, with storage that throws, and with its
// outer doctype/html/head/body stripped and re-wrapped. Screenshots are written at W=390 only.
const { chromium } = require('playwright');
const assert = require('assert');
const BASE = process.env.BASE, OUT = process.env.OUT, W = +(process.env.W || 390), VH = W === 320 ? 640 : W >= 1000 ? 900 : 844;
const SCREEN = 844, AIM = 2 * SCREEN; // collapsed pages: aim for two phone screens
// The "About" text is now shown whole, so a page is taller than two screens; what must hold is how soon the way on is reached (the "See the …" button) and these ceilings.
const LIMITS = { experience: 3.6, neighborhood: 3.4, building: 2.6, compare: 2.2, list: 2.2 }, LIMIT = Math.round(3.6 * SCREEN), limitOf = kind => Math.round((LIMITS[kind] || 3.6) * SCREEN);
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: VH }, deviceScaleFactor: 1 });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
  const page = await ctx.newPage();
  page.setDefaultTimeout(10000);
  const errors = [];
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text() + ' @' + (m.location().url || '')); });
  page.on('pageerror', e => errors.push('PAGEERROR ' + e.message));
  // plain hashes: the id in lower case, every run of other characters turned into a hyphen (the page's mkSlug)
  const slug = id => String(id).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'x';
  const go = async (h, sel) => { await page.evaluate(x => { location.hash = x; }, h); await page.waitForSelector(sel || '.ph1'); await page.waitForFunction(x => location.hash === x, h); };
  // a list shows three, then more: open everything
  const showAll = async () => { for (let i = 0; i < 20; i++) { const b = page.locator('#view [data-act=more]:not([data-n="3"])').last(); if (!(await b.count())) break; await b.click(); } };
  // a section is a closed row with a headline: open it
  const openRow = async (id, pg) => { pg = pg || page; await pg.waitForSelector('#' + id, { state: 'attached' }); if (!(await pg.evaluate(i => document.getElementById(i).open, id))) await pg.click('#' + id + ' > summary'); await pg.waitForFunction(i => document.getElementById(i).open, id); };
  const headOf = async (id, pg) => (await (pg || page).textContent('#' + id + ' > summary .rh')).trim();
  const overflow = async (tag) => {
    const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
      bad: [...document.querySelectorAll('#view *, #foot *, #tray *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > window.innerWidth + 1 || r.left < -1) && !e.closest('svg'); }).slice(0, 5).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right)) }));
    assert(o.sw <= o.cw, `horizontal overflow on ${tag}: ${o.sw} > ${o.cw} ${o.bad}`);
    assert.strictEqual(o.bad.length, 0, 'something sits off screen on ' + tag + ': ' + o.bad);
  };
  const small = async (tag) => {
    const s = await page.evaluate(() => [...document.querySelectorAll('#view a, #view button, #view summary, #view input, #trail a, #tray a, #foot button')].filter(e => !e.closest('svg') && !e.closest('p.slot-text') && !e.closest('.srcl') && e.getClientRects().length).map(e => { const r = e.getBoundingClientRect(); return { t: (e.className || e.tagName) + ':' + (e.textContent || '').trim().slice(0, 24), w: Math.round(r.width), h: Math.round(r.height) }; }).filter(x => x.h > 0 && x.h < 43.5).slice(0, 8));
    if (s.length) console.log('SMALL targets', tag, JSON.stringify(s));
  };
  const shot = async (name, full) => { if (W !== 390 || !OUT) return; await page.waitForFunction(() => !document.getElementById('toast').classList.contains('on'), null, { timeout: 5000 }).catch(() => {});
    if (full) { const y = await page.evaluate(() => window.scrollY); const h = await page.evaluate(() => document.documentElement.scrollHeight); await page.setViewportSize({ width: W, height: Math.min(h, 6000) }); await page.waitForTimeout(150); await page.screenshot({ path: `${OUT}/${name}.png` }); await page.setViewportSize({ width: W, height: VH }); await page.evaluate(y => window.scrollTo(0, y), y); }
    else await page.screenshot({ path: `${OUT}/${name}.png` }); };
  // height of a page in its default, collapsed state: from under the sticky top line to the end of the footer (the fixed bottom bar is not counted)
  const pageHeight = async (pg) => (pg || page).evaluate(() => { const f = document.getElementById('foot').getBoundingClientRect(), t = document.getElementById('trail'); return Math.round(f.bottom + window.scrollY - (t.hidden ? 0 : t.offsetHeight)); });
  const heights = [];
  const fits = async (kind, tag) => { const h = await pageHeight(), open = await page.evaluate(() => [...document.querySelectorAll('#view details.rowd[open]')].map(d => d.id));
    heights.push({ kind, tag, h, screens: +(h / SCREEN).toFixed(2) });
    if (W === 390) { assert(h <= limitOf(kind), `${kind} ${tag} is ${h}px collapsed, over ${limitOf(kind)}px`); assert.strictEqual(open.length, 0, `${kind} ${tag} has a row open by default: ${open}`); }
    return h; };
  // crime is not shown in the open: nothing visible on a page in its default state names it
  const CRIME = /\bcrimes?\b|violen|burglar|\bthefts?\b|robber|assault|per 1,000/i;
  const noCrime = async (tag) => { const t = await page.evaluate(() => document.getElementById('view').innerText + '\n' + document.getElementById('foot').innerText); const m = CRIME.exec(t); assert(!m, `crime wording in the open on ${tag}: “${m && t.slice(Math.max(0, m.index - 60), m.index + 60).replace(/\s+/g, ' ')}”`); };
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
    await pg.waitForSelector('.life');
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
    if (!o.reduced) await pg.waitForTimeout(350);
    const m = await tapMark(pg, o.touch);
    const name = (await pg.textContent('.hhm-card h3')).trim(), cardText = await pg.textContent('.hhm-card');
    const H = d.neighborhoods.find(h => m.label.indexOf(h.name + (h.state ? ', ' + h.state : '') + '. ') === 0 && name.indexOf(h.name) === 0);
    assert(H, `${tag}: the card (${name}) is the mark that was tapped (${m.label})`);
    assert(/\d+\s*places? shown|\d+ of \d+\s*places fit your limits/.test(cardText), 'the card gives the unit count: ' + cardText);
    if (H.rank_in_experience != null) { const of = d.years.find(y => y.id === H.year).hood_ids.length;
      assert((await pg.textContent('.hhm-card .hhm-rank')).trim() === (H.rank_in_experience === 1 ? 'Top pick' : '#' + H.rank_in_experience + ' of ' + of), 'rank within its experience: ' + cardText); }
    assert(/Experience/.test(await pg.textContent('.hhm-card .hhm-yr')), 'the card names the experience');
    await noSideScroll(pg, tag + ' card');
    // zoom and pan stay put when another mark is chosen, and when the page is drawn again (a limit moved)
    { const view = () => pg.evaluate(() => { const v = window.__houseHunt.map().view(); return [v.k, v.cx, v.cy].map(x => +x.toFixed(3)).join(); });
      await pg.waitForTimeout(o.reduced ? 50 : 350); const v1 = await view(); assert(+v1.split(',')[0] > 1.01, 'zoomed in: ' + v1);
      const other = d.neighborhoods.find(h => h.id !== H.id && h.year === H.year && h.lat != null && d.years.some(y => y.hood_ids.includes(h.id)));
      if (other) { await pg.evaluate(id => window.__houseHunt.map().select(id), other.id); assert.strictEqual((await pg.textContent('.hhm-card h3')).trim().indexOf(other.name), 0); assert.strictEqual(await view(), v1, 'another card: same zoom and pan'); await pg.evaluate(id => window.__houseHunt.map().select(id), H.id); }
      await pg.evaluate(() => { const e = document.getElementById('lim-cost'), v = e.value; e.value = String(+e.max - +e.step); e.dispatchEvent(new Event('input', { bubbles: true })); e.value = v; e.dispatchEvent(new Event('input', { bubbles: true })); });
      await pg.waitForSelector('#hhmap .hhm'); assert.strictEqual(await view(), v1, 'drawn again: same zoom and pan'); assert.strictEqual((await pg.textContent('.hhm-card h3')).trim(), name, 'and the same card');
      // a tap on the Mom and Dad house zooms in on it instead of doing nothing
      await pg.evaluate(() => window.__houseHunt.map().reset()); await pg.waitForTimeout(o.reduced ? 80 : 450);
      const hb = await pg.evaluate(() => { const svg = document.querySelector('.hhm-svg'), tray = document.getElementById('tray').getBoundingClientRect(); const g = svg.querySelector('g[pointer-events="none"] g'); let r = g.getBoundingClientRect(); window.scrollBy(0, r.top - (tray.top / 2)); r = g.getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 }; });
      if (o.touch) await pg.touchscreen.tap(hb.x, hb.y); else await pg.mouse.click(hb.x, hb.y); await pg.waitForTimeout(o.reduced ? 80 : 450);
      const k2 = +(await view()).split(',')[0]; assert(k2 > 2.5, 'the house tap zoomed in: ' + k2); assert.strictEqual((await pg.textContent('.hhm-card h3')).trim(), name, 'and chose no mark under it'); }
    if (o.shot) { await pg.evaluate(() => { const r = document.querySelector('.hhm-stage').getBoundingClientRect(); window.scrollBy(0, r.top + r.height * 0.55); }); await o.shot('map-int-03-selected-card'); }
    await centre(pg, '.hhm-go'); const yBefore = await pg.evaluate(() => window.scrollY);
    await pg.click('.hhm-go'); await pg.waitForSelector('.ph1');
    assert.strictEqual(await pg.evaluate(() => location.hash), '#hood-' + slug(H.id), '"See places" lands on the neighborhood');
    assert.strictEqual((await pg.textContent('.ph1')).trim(), H.name);
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
    await centre(pg, '.hhm-go'); await pg.click('.hhm-go'); await pg.waitForSelector('.ph1');
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
  const hoodBy = Object.fromEntries(data.neighborhoods.map(h => [h.id, h])), yearBy = Object.fromEntries(data.years.map(y => [y.id, y]));
  const median = a => { a = a.filter(x => x != null).sort((x, y) => x - y); const m = a.length >> 1; return !a.length ? null : a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
  const money0 = v => '$' + Math.round(v).toLocaleString('en-US');
  const listed = y => y.hood_ids.map(id => hoodBy[id]).filter(Boolean), unitIds = new Set(data.units.map(u => u.id));

  await page.goto(BASE + '/index.html');
  await page.waitForSelector('.life');
  // the drawings are optional: with site/illustrations.json each tile carries its banner, without it nothing is shown
  const illusRes = await page.request.get(BASE + '/illustrations.json'), illus = illusRes.ok();
  if (illus) await page.waitForSelector('a.life .illus svg'); else await page.waitForTimeout(200);
  console.log('illustrations:', illus ? 'present' : 'absent (no art is shown)');
  // nothing opens by itself on a first visit; "How this works" is a footer link that opens three lines in the sheet
  assert.strictEqual(await page.locator('#tour, #tourscrim, .tour').count(), 0, 'no first-run card');
  assert(!(await page.evaluate(() => document.getElementById('sheet').classList.contains('open'))), 'no sheet is open on arrival');
  await page.click('#foot [data-act=how-open]'); await page.waitForSelector('#sheet.open .howl');
  assert.strictEqual(await page.locator('#sheet .howl li').count(), 3); await shot('ux-00-how-this-works-sheet');
  await page.click('#shClose'); assert(!(await page.evaluate(() => document.getElementById('sheet').classList.contains('open'))));
  // ---------- the bottom bar: one slim line, "Saved · N", that opens My list ----------
  { const tr = await page.evaluate(() => { const e = document.getElementById('tray'); return { h: e.offsetHeight, text: e.innerText.replace(/\s+/g, ' ').trim(), href: e.querySelector('a').getAttribute('href'), pad: parseFloat(getComputedStyle(document.body).paddingBottom) }; });
    assert(tr.h >= 50 && tr.h <= 58, 'the bar is slim: ' + tr.h + 'px'); assert.strictEqual(tr.text, 'Saved · 0 My list'); assert.strictEqual(tr.href, '#list');
    assert(Math.abs(tr.pad - tr.h - 20) < 1.5, 'the page keeps room for the bar: ' + tr.pad); console.log('bottom bar:', tr.h, 'px');
    await page.click('#tray a'); await page.waitForSelector('.ph1'); assert.strictEqual((await page.textContent('.ph1')).trim(), 'My list'); assert((await page.textContent('#view .empty')).includes('Nothing saved yet')); await shot('ux-00b-my-list-empty');
    await page.goBack(); await page.waitForSelector('.life'); }
  // ---------- first screen: six short cards, the median with the range small beneath, nothing explained ----------
  assert.strictEqual(await page.locator('a.life').count(), data.years.length);
  const tiles = await page.evaluate(() => [...document.querySelectorAll('a.life')].map(a => ({ h: Math.round(a.getBoundingClientRect().height), label: a.querySelector('h3').textContent.trim(), figs: [...a.querySelectorAll('.figs b')].map(b => b.textContent), labels: [...a.querySelectorAll('.figs span')].map(b => b.textContent), kids: [...a.children].map(c => c.tagName + (c.className ? '.' + c.className : '')), mark: a.querySelectorAll('h3 .ymk').length, w: a.clientWidth, art: (i => i ? { h: Math.round(i.getBoundingClientRect().height), w: Math.round(i.getBoundingClientRect().width), svg: i.querySelectorAll('svg').length } : null)(a.querySelector('.illus')), tag: (a.querySelector('.l2') || {}).textContent, rng: [...a.querySelectorAll('.figs .rng')].map(b => b.textContent), text: a.innerText })));
  tiles.forEach((t, i) => { const y = data.years[i];
    assert.strictEqual(t.label, String(y.display_label || y.label).replace(/ Year$/, ' Experience'));
    if (y.medians && y.medians.all_in != null) assert.strictEqual(t.figs[0], money0(y.medians.all_in), 'the tile shows the median cost');
    if (y.medians && y.medians.drive_min != null) assert.strictEqual(t.figs[1], Math.round(y.medians.drive_min) + ' min', 'the tile shows the median drive');
    if (y.all_in_range && money0(y.all_in_range[0]) !== money0(y.all_in_range[1])) assert(t.rng.includes(money0(y.all_in_range[0]) + ' to ' + money0(y.all_in_range[1])), 'the range sits under the median: ' + t.rng);
    // a tile is its marker, the label, the tagline, two numbers with their ranges, and the count of places: nothing else
    assert.deepStrictEqual(t.kids, [illus ? 'DIV.illus banner' : null, 'H3', y.tagline ? 'P.l2' : null, 'DIV.figs xt'].filter(Boolean), 'a tile has nothing else: ' + t.kids);
    if (illus) { assert(t.art.h >= 100 && t.art.h <= 132, 'the drawing is a banner of about 110 to 130 px: ' + t.art.h); assert(t.art.svg === 1 && t.art.w >= t.w - 8, 'edge to edge on the tile'); }
    assert.strictEqual(t.mark, 1, 'the marker is on the tile'); if (y.tagline && !CRIME.test(y.tagline)) assert.strictEqual(t.tag, y.tagline, 'the tagline is shown whole');
    assert.strictEqual(t.figs.length, 3); assert.strictEqual(t.figs[2], String(listed(y).reduce((n, h) => n + (h.unit_ids || []).filter(id => unitIds.has(id)).length, 0)), 'the count of places');
    assert.deepStrictEqual(t.labels, ['typical all-in', 'typical to Mom and Dad', t.figs[2] === '1' ? 'place' : 'places']);
    if (W === 390) assert(t.h <= (illus ? 320 : 200), 'an experience tile is a short card: ' + t.h + 'px'); });
  { const end = await page.evaluate(() => Math.round(document.getElementById('see-map').getBoundingClientRect().bottom + window.scrollY));
    console.log('first screen: the six tiles and "See them on a map" end at', end, 'px =', (end / SCREEN).toFixed(2), 'screens');
    if (W === 390) assert(end <= (illus ? 3.3 : 2.5) * SCREEN, 'tiles and the map button fit in ' + (illus ? '3.3 screens with the drawings' : '2.5 screens') + ': ' + end);
    assert(await page.evaluate(() => document.getElementById('see-map').getBoundingClientRect().top > [...document.querySelectorAll('a.life')].pop().getBoundingClientRect().bottom), 'the map button follows the tiles'); }
  console.log('first screen: tile heights', tiles.map(t => t.h).join(', '), '| page', await pageHeight(), 'px with the map');
  assert.strictEqual(await page.locator('#view .mock, #view .coldopen, #view .confnote, #view .tip').count(), 0, 'no explaining lines on the first screen');
  assert.strictEqual(await page.locator('#view details.howd[open]').count(), 0);
  assert((await page.textContent('#sources')).includes('OpenStreetMap'), 'the sources are still there, behind the link');
  assert(await page.isHidden('#foothow'), '"See how we got this" starts closed');
  await page.click('[data-act=foot-how]'); assert(await page.isVisible('#foothow')); assert.strictEqual(await page.getAttribute('[data-act=foot-how]', 'aria-expanded'), 'true'); await page.click('[data-act=foot-how]');
  await noCrime('first screen');
  await overflow('home'); await small('home');
  await shot('01-home', true); await shot('ux-01-first-screen');
  await mapFlow(page, data, 'served page', { shot });

  // ---------- headline builders: small pure functions, tested on made-up records ----------
  const hl = await page.evaluate(() => { const HL = window.__houseHunt.HL, u = (o) => Object.assign({ moments: { sun: {} }, rent: {}, parking: {}, dog: {}, amenities: {}, elevator: {}, evidence: {}, confirm: null, disclosures: [], all_in_lines: [], all_in_unknown: [], tour_questions: [] }, o);
    return {
      cost: HL.cost(u({ all_in: 2710 })), costUnknown: HL.cost(u({ all_in: null })),
      trip: HL.trip({ drive_min: 28.2, toll_round_trip: 15 }), tripFree: HL.trip({ drive_min: 12, toll_round_trip: 0 }), tripUnk: HL.trip({ drive_min: 40, toll_round_trip: null }), tripNone: HL.trip({ drive_min: null }),
      park: HL.parking(u({ parking: { rank: 4, type: 'garage', fee: 150 } })), parkFree: HL.parking(u({ parking: { rank: 4, type: 'garage', fee: 0 } })), parkNoFee: HL.parking(u({ parking: { rank: 4, type: 'garage', fee: null } })), parkUnk: HL.parking(u({ parking: { rank: null, type: '' } })),
      dog: HL.dog(u({ dog: { allowed: 'yes', weight_limit_lb: null } })), dog50: HL.dog(u({ dog: { allowed: 'yes', weight_limit_lb: 50 } })), dogNoLimit: HL.dog(u({ dog: { allowed: 'yes', weight_limit_lb: 'no limit' } })), dogUnk: HL.dog(u({ dog: {} })),
      bld: HL.building(u({ elevator: { value: 'yes' }, amenities: { gym: 'yes', pool: 'pool' } })), bldNone: HL.building(u({})),
      queens: HL.queens({ drive_min: 5, all_in: 4, sqft: 1, parking: 3 }), queensSame: HL.queens({ drive_min: 3, all_in: 3 }), queensUnk: HL.queens({}),
      voices: HL.voices({ local: { voices: [{ excerpt: 'a', sentiment: 'positive', theme: 'parking' }, { excerpt: 'b', sentiment: 'positive', theme: 'parking' }, { excerpt: 'c', sentiment: 'negative', theme: 'noise' }, { excerpt: 'd', sentiment: 'positive', theme: 'safety' }] } }), voicesNone: HL.voices({ local: {} }), voicesTopic: HL.voicesTopic({ local: { voices: [{ excerpt: 'a', theme: 'parking' }, { excerpt: 'b', theme: 'parking' }, { excerpt: 'c', theme: 'noise' }, { excerpt: 'd', theme: 'safety' }, { excerpt: 'e', theme: 'car_crime' }, { excerpt: 'f', theme: 'car_crime' }, { excerpt: 'g', theme: 'car_crime' }] } }),
      rules: HL.rules({ local: { parking_rules: [{ rule: 'overnight_parking', summary: 'Overnight parking on the street needs a permit.' }] } }), rulesPlain: HL.rules({ local: { parking_rules: [{ rule: 'meters', summary: 'Meters run 9 to 6.' }] } }), rulesNone: HL.rules({ local: {} }),
      described: HL.described({ described: [{ quote: 'A leafy village on the Sound with a train to the city and a main street that people walk on weekends.' }] }),
      describedCount: HL.described({ described: [{ quote: 'A leafy village on the Sound with a train to the city and a main street that people walk on weekends, all year.', source: 'Wikipedia' }, { quote: 'It is also a place where the second sentence is the short one, after a very long opening clause. Short.', source: 'Wikipedia' }] }),
      describedAbbr: HL.described({ described: [{ quote: 'East Brunswick is a township in Middlesex County, in the U.S. state of New Jersey.', source: 'Wikipedia' }, { quote: 'x', source: 'niche.com' }] }), describedNone: HL.described({}),
      confirm: HL.confirm(u({ confirm: { asterisk: true, what: 'listing', why: 'w' }, disclosures: [{ what: 'a' }, { what: 'b' }] })), confirmRent: HL.confirm(u({ rent: { asterisk: true } })), confirmAsk: HL.confirm(u({ disclosures: [{ what: 'a' }] })), confirmNone: HL.confirm(u({})),
      reviews: HL.reviews({ platforms: [{ platform: 'Yelp', rating: 3, count: 12 }, { platform: 'Google', rating: 4.24, count: 149 }, { platform: 'Zillow', rating: 5, count: 1 }], searched: true, found_any: true }),
      reviewsOne: HL.reviews({ platforms: [{ platform: 'Google', rating: 4, count: 1 }], searched: true, found_any: true }), reviewsTwo: HL.reviews({ platforms: [{ platform: 'Google', rating: 4.5, count: 20 }, { platform: 'Yelp', rating: 2, count: null }], found_any: true }),
      reviewsNone: HL.reviews({ platforms: [], searched: true, found_any: false }), reviewsNotYet: HL.reviews({ platforms: [], searched: false, found_any: false }), reviewsMissing: HL.reviews(undefined),
      firstLong: HL.first('There is a real night out on foot here, with neighbors your age and a dog run that stays busy until late in the evening.'), firstMax: window.__houseHunt.HL_MAX,
      dump: [window.__houseHunt.cleanText('term 12: price 2805, totalPrice 2805, concession 0'), window.__houseHunt.cleanText('First month free on a 13-month lease | The page does not say whether the listed price is gross or net-effective.'), window.__houseHunt.cleanText('**NOW OFFERING 1 MONTH FREE | lease_term: 12 | {"a":1}'), window.__houseHunt.cleanText(null)],
      questions: HL.questions(0), first: HL.first('It has 2.5 miles of beach. And more.', 80) }; });
  assert.deepStrictEqual(hl, { cost: '$2,710 all-in', costUnknown: 'not published, ask',
    trip: 'about 28 min, $15 in tolls', tripFree: 'about 12 min, no tolls', tripUnk: 'about 40 min, tolls not fully known', tripNone: 'drive time not known',
    park: 'garage, $150 a month', parkFree: 'garage, no monthly charge', parkNoFee: 'garage, fee not published, ask', parkUnk: 'not published, ask',
    dog: 'allowed, weight limit not stated', dog50: 'allowed, up to 50 lb', dogNoLimit: 'allowed, no weight limit', dogUnk: 'not stated, ask',
    bld: 'elevator, gym, pool', bldNone: 'details not published',
    queens: 'closer, cheaper, smaller', queensSame: 'about the same', queensUnk: 'not known yet',
    voices: '3 positive, 1 negative', voicesTopic: 'Parking', voicesNone: 'none found yet',
    rules: 'overnight street parking restricted', rulesPlain: '1 rule on record', rulesNone: 'not found, ask',
    described: '1 description', describedCount: '2 descriptions, from Wikipedia', describedAbbr: '2 descriptions, from Wikipedia and niche.com', describedNone: '',
    confirm: '1 thing to confirm · 2 to ask', confirmRent: '1 thing to confirm', confirmAsk: '1 to ask', confirmNone: 'nothing',
    reviews: '4.2 on Google · 149 reviews, and 2 more sites', reviewsOne: '4.0 on Google · 1 review', reviewsTwo: '4.5 on Google · 20 reviews, and 1 more site',
    reviewsNone: 'No reviews found online', reviewsNotYet: 'Not looked up yet', reviewsMissing: 'Not looked up yet',
    firstLong: 'There is a real night out on foot here.', firstMax: 64,
    dump: ['', 'First month free on a 13-month lease', 'NOW OFFERING 1 MONTH FREE', ''],
    questions: 'nothing flagged', first: 'It has 2.5 miles of beach.' });

  // ---------- an experience: headline, the day (clamped), the figures, the top three, then rows ----------
  const star = data.units.find(u => u.rent.asterisk && u.all_in_gross > u.all_in && hoodBy[u.hood_id]) || data.units.find(u => u.rent.asterisk);
  const y1 = star.year, Y1 = yearBy[y1];
  await page.click(`a.life[href="#exp-${slug(y1)}"]`);
  await page.waitForSelector('.ph1');
  assert.strictEqual(await page.getAttribute('.viewsw [data-v=list]', 'aria-pressed'), 'true');
  assert.strictEqual(await page.locator('#sec-hoods a.hood').count(), Math.min(3, listed(Y1).length));
  // the key facts stay in view: four cells, the median big, the range small beneath
  const strip = await page.evaluate(() => [...document.querySelectorAll('.sec.head .kstrip > div')].map(c => ({ b: c.querySelector('b').textContent, r: c.querySelector('.rng') ? c.querySelector('.rng').textContent : '' })));
  assert.strictEqual(strip.length, 4, 'a four-cell strip');
  if (Y1.medians.all_in != null) assert.strictEqual(strip[0].b, money0(Y1.medians.all_in), 'the strip shows the median, not a range');
  if (Y1.all_in_range && money0(Y1.all_in_range[0]) !== money0(Y1.all_in_range[1])) assert.strictEqual(strip[0].r, money0(Y1.all_in_range[0]) + ' to ' + money0(Y1.all_in_range[1]), 'with the range small beneath');
  // "About this experience": the text whole, a lead and a short list, under its own title; no host label, no clamp, no "more"
  assert.strictEqual(await page.locator('#view .host, #view .who, #view .clampw, #view [data-act=unclamp]').count(), 0, 'no host box and nothing clamped'); assert(!/your host/i.test(await page.evaluate(() => document.getElementById('view').textContent)), 'no "Your host says"');
  if (Y1.host && Y1.host.intro) { const ab = await page.evaluate(() => { const s = document.getElementById('about'); return { h2: s.querySelector('h2').textContent, lead: (s.querySelector('.lead2') || {}).textContent || '', pts: [...s.querySelectorAll('.pts li')].map(li => li.textContent), icons: s.querySelectorAll('.pts li svg').length, cut: [...s.querySelectorAll('*')].filter(e => e.scrollHeight > e.clientHeight + 2 && getComputedStyle(e).overflow !== 'visible').length }; });
    assert.strictEqual(ab.h2, 'About this experience'); assert.strictEqual(ab.cut, 0, 'nothing in it is cut');
    const want = await page.evaluate(x => window.__houseHunt.sentences(x), Y1.host.intro), got = [ab.lead].concat(ab.pts).join(' ').replace(/\s+/g, ' ').trim();
    if (!want.some(s => CRIME.test(s))) assert.strictEqual(got, want.join(' '), 'the whole text is there, once');
    assert(ab.pts.length >= 1 && ab.icons === ab.pts.length, 'the rest is a short list, each line with its mark: ' + ab.pts.length); assert(ab.lead.length >= 60, 'the lead is something to read: ' + ab.lead); }
  // the way on sits right under the key facts, above the About text
  { const b = await page.evaluate(() => { const e = document.getElementById('see-hoods'), k = document.querySelector('.sec.head .kstrip'), a = document.getElementById('about'), tr = document.getElementById('trail'); return { text: e.textContent.trim(), top: e.getBoundingClientRect().top, bottom: Math.round(e.getBoundingClientRect().bottom + window.scrollY - tr.offsetHeight), strip: k.getBoundingClientRect().bottom, about: a ? a.getBoundingClientRect().top : 1e9 }; });
    assert.strictEqual(b.text, 'See the ' + listed(Y1).length + (listed(Y1).length === 1 ? ' neighborhood' : ' neighborhoods') + ' ↓'); assert(b.strip <= b.top && b.top < b.about, 'under the strip, above About');
    if (W === 390) assert(b.bottom <= SCREEN, 'and within the first screen: ' + b.bottom); console.log('experience: "See the neighborhoods" ends at', b.bottom, 'px');
    await page.click('#see-hoods'); const y = await page.evaluate(() => document.getElementById('sec-hoods').getBoundingClientRect().top); assert(y >= 0 && y < 160, 'it scrolls to the list: ' + Math.round(y)); await page.evaluate(() => window.scrollTo(0, 0)); }
  if (illus) assert(await page.evaluate(() => { const i = document.querySelector('#view .illus.tall'), h = document.querySelector('.ph1'); return !!i && i.querySelectorAll('svg').length === 1 && i.getBoundingClientRect().bottom <= h.getBoundingClientRect().top; }), 'the drawing sits at the top of the experience page'); else assert.strictEqual(await page.locator('#view .illus').count(), 0);
  // a day in this experience: three titled moments from the walkthrough, and nothing that the About text already said
  if (Y1.host && (Y1.host.walkthrough || []).length) { await openRow('r-scene'); const dm = await page.evaluate(() => [...document.querySelectorAll('#r-scene .dmom')].map(d => ({ t: d.querySelector('h4').textContent.trim(), p: d.querySelector('p').textContent })));
    assert.deepStrictEqual(dm.map(d => d.t), (Y1.day_moments || []).length ? Y1.day_moments.map(m => m.title) : ['A weekday', 'Saturday night', 'Sunday with Mom and Dad'].slice(0, Y1.host.walkthrough.length));
    const about = await page.textContent('#about'), sents = await page.evaluate(x => window.__houseHunt.sentences(x), Y1.host.intro || '');
    for (const s of sents) if (s.length > 30) assert(!(await page.textContent('#r-scene')).includes(s), 'the day row repeats nothing from the About text: ' + s);
    const all = await page.evaluate(() => document.getElementById('view').textContent); for (const d of dm) { const s = d.p.slice(0, 60); assert.strictEqual(all.split(s).length - 1, 1, 'each passage appears once on the page: ' + s); }
    await page.click('#r-scene > summary'); }
  assert.strictEqual(await page.locator('#view details.rowd[open]').count(), 0, 'no row starts open');
  const nRows = await page.locator('#sec-rows details.rowd').count(); assert(nRows >= 3 && nRows <= 7, 'three to seven rows on an experience: ' + nRows);
  assert((await page.textContent('#r-queens .rl')).trim() === 'Compared to staying in Queens');
  assert.strictEqual(await page.locator('#r-queens button.pt').count(), data.meta.queens_spectrum.filter(s => !/crime/.test(s.measure)).length, 'the scale leaves crime out');
  assert.strictEqual(await headOf('r-cost'), await page.evaluate(id => window.__houseHunt.headline('year', id, 'yearCost'), y1));
  // a neighborhood card: name, rank, one line, three facts
  const card = await page.evaluate(() => { const a = document.querySelector('#sec-hoods a.hood'); return { chips: a.querySelectorAll('.chip').length, kids: [...a.children].map(c => c.className), h: Math.round(a.getBoundingClientRect().height) }; });
  assert(card.chips >= 2 && card.chips <= 3, 'a neighborhood card has two or three facts: ' + card.chips); assert(card.kids.every(k => /^(hd|l2 full|chips|safest)$/.test(k)), 'and nothing else: ' + card.kids);
  { const c3 = await page.evaluate(() => [...document.querySelectorAll('#sec-hoods a.hood')].slice(0, 3).map(a => ({ name: a.querySelector('h4').textContent, pick: (a.querySelector('.pick') || {}).textContent || '', line: (a.querySelector('.l2') || {}).textContent || '', cut: a.querySelector('.l2') ? a.querySelector('.l2').scrollHeight > a.querySelector('.l2').clientHeight + 1 : false, small: [...a.querySelectorAll('.chip small')].filter(e => e.scrollWidth > e.clientWidth + 1).length })));
    assert.strictEqual(c3[0].pick, 'Top pick', 'the first card carries the badge'); c3.forEach(c => { assert(c.line.length >= 40 && !c.cut && !/…$/.test(c.line), 'a top-three card has a whole line to read: ' + c.name + ': ' + c.line); assert.strictEqual(c.small, 0, 'no fact label is cut: ' + c.name); }); }
  await noCrime('experience ' + y1); await overflow('year'); await small('year');
  await shot('02-year', true); await shot('ux-02-experience-collapsed');
  await openRow('r-cost'); assert((await page.textContent('#r-cost .allin')).startsWith('All-in: rent'), 'one plain line says what all-in includes');
  // one control opens and closes every row
  await page.click('[data-act=rows-all]'); assert.strictEqual(await page.locator('#view details.rowd:not([open])').count(), 0); assert.strictEqual((await page.textContent('[data-act=rows-all]')).trim(), 'Close all');
  await page.click('[data-act=rows-all]'); assert.strictEqual(await page.locator('#view details.rowd[open]').count(), 0); await openRow('r-cost');
  assert.strictEqual(await page.locator('#r-cost details.howd[open]').count(), 0, '"See how we got this" stays closed inside the row');
  await page.evaluate(() => document.getElementById('r-cost').scrollIntoView({ block: 'center' })); await shot('ux-02b-experience-costs-open');
  // the open row is remembered for the visit: away and Back
  await openRow('r-queens'); await page.click('#r-queens button.pt >> nth=0'); await page.waitForSelector('#sheet.open');
  assert((await page.textContent('#sheetBody')).includes('Staying in Queens')); assert(!/against/i.test(await page.textContent('#sheetBody')), '"compared to", never "against"'); await page.click('#shClose');
  await page.click('#sec-hoods a.hood >> nth=0'); await page.waitForFunction(() => location.hash.indexOf('#hood-') === 0); await page.goBack(); await page.waitForSelector('#r-queens');
  assert(await page.evaluate(() => document.getElementById('r-queens').open && document.getElementById('r-cost').open), 'Back returns to the page with the same rows open');
  // every experience, collapsed: height, one thing open, no crime, the subhead never about crime
  for (const y of data.years) { await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); await page.click(`a.life[href="#exp-${slug(y.id)}"]`); await page.waitForSelector('.ph1');
    if (await page.getAttribute('.viewsw [data-v=list]', 'aria-pressed').catch(() => 'true') !== 'true') await page.click('.viewsw [data-v=list]');
    await page.evaluate(() => [...document.querySelectorAll('#view details.rowd[open] > summary')].forEach(s => s.click())); await page.waitForTimeout(50);
    await fits('experience', y.id); await noCrime('experience ' + y.id); await overflow('experience ' + y.id); }

  // ---------- neighborhoods ----------
  const shownHoodsAll = data.neighborhoods.filter(h => (h.unit_ids || []).some(id => data.units.some(u => u.id === id)));
  const shownHoods = data.neighborhoods.filter(h => h.counts.shown > 0 && yearBy[h.year] && yearBy[h.year].hood_ids.includes(h.id));
  const richness = h => h.counts.shown + (h.local.voices || []).length + (h.local.parking_rules || []).length + (h.described || []).length + 5 * h.counts.avoid + 5 * h.counts.held;
  // buildings: a neighborhood's places grouped by building_id, in the order of each building's best-ranked place
  const unitBy = Object.fromEntries(data.units.map(u => [u.id, u]));
  const bOf = hid => { const out = [], by = {}; for (const id of hoodBy[hid].unit_ids || []) { const u = unitBy[id]; if (!u) continue; const k = String(u.building_id || u.building || u.id); if (!by[k]) { by[k] = { key: k, units: [] }; out.push(by[k]); } by[k].units.push(u); } return out; };
  const pageBldgs = await page.evaluate(() => window.__houseHunt.bldgs()), bSlug = u => pageBldgs.find(b => b.units.includes(u.id)).slug, bUnits = u => pageBldgs.find(b => b.units.includes(u.id)).units.map(id => unitBy[id]);
  assert.strictEqual(pageBldgs.length, shownHoodsAll.reduce((n, h) => n + bOf(h.id).length, 0), 'one building per building_id in each neighborhood'); assert.strictEqual(pageBldgs.reduce((n, b) => n + b.units.length, 0), data.units.filter(u => hoodBy[u.hood_id]).length, 'every place sits in one building');
  console.log('buildings:', pageBldgs.length, '| with one apartment:', pageBldgs.filter(b => b.units.length === 1).length, '| most apartments in one building:', Math.max(...pageBldgs.map(b => b.units.length)));
  const hRich = shownHoods.slice().sort((a, b) => richness(b) - richness(a))[0], hSparse = shownHoods.slice().sort((a, b) => richness(a) - richness(b))[0];
  const hAvoid = shownHoods.find(h => h.counts.avoid > 0 && h.name === 'Jamaica') || shownHoods.find(h => h.counts.avoid > 0);
  const hStar = shownHoods.find(h => data.units.filter(u => u.hood_id === h.id && u.confirm.asterisk).length >= 2) || hoodBy[star.hood_id];
  for (const [tag, h] of [['rich', hRich], ['sparse', hSparse], ['with avoid cards', hAvoid], ['with asterisks', hStar]]) { if (!h) continue;
    await go('#hood-' + slug(h.id)); await fits('neighborhood', tag + ' (' + h.name + ')'); await noCrime('neighborhood ' + h.name); await overflow('hood ' + tag);
    const nb = bOf(h.id).length;
    assert.strictEqual(await page.locator('#sec-places article.bcard').count(), Math.min(3, nb), 'a neighborhood opens on its top three buildings');
    if (nb > 3) assert((await page.textContent('#sec-places .morectl')).includes('3 of ' + nb + ' buildings shown'));
    assert.strictEqual((await page.textContent('#about h2')).trim(), 'About ' + (h.parent_name && h.short_name ? h.short_name : h.name)); assert.strictEqual(await page.locator('#view .host, #view .clampw').count(), 0);
    const sb = await page.evaluate(() => { const e = document.getElementById('see-places'), tr = document.getElementById('trail'); return { t: e.textContent.trim(), bottom: Math.round(e.getBoundingClientRect().bottom + window.scrollY - tr.offsetHeight), above: e.getBoundingClientRect().top < document.getElementById('about').getBoundingClientRect().top }; });
    assert.strictEqual(sb.t, 'See the ' + h.counts.shown + (h.counts.shown === 1 ? ' place' : ' places') + ' ↓'); assert(sb.above, '"See the places" is above the About text'); if (W === 390) assert(sb.bottom <= SCREEN, 'and in the first screen: ' + sb.bottom); }
  await go('#hood-' + slug(hRich.id)); await small('hood'); await shot('03-neighborhood', true); await shot('ux-03-neighborhood-collapsed');
  await openRow('r-voices'); await page.evaluate(() => document.getElementById('r-voices').scrollIntoView({ block: 'start' })); await page.evaluate(() => window.scrollBy(0, -70)); await shot('ux-03b-neighborhood-residents-open');
  // a building card: name, from-price, how many apartments, one line, three facts, and the asterisk only when every apartment there shares it
  await go('#hood-' + slug(hStar.id)); await showAll();
  { const bs = bOf(hStar.id), cards = await page.evaluate(() => [...document.querySelectorAll('#sec-places article.bcard')].map(a => ({ href: a.querySelector('a').getAttribute('href'), name: a.querySelector('h4').textContent, sub: (a.querySelector('.hd small') || {}).textContent || '', chips: [...a.querySelectorAll('.chip b')].map(b => b.textContent), cutChips: [...a.querySelectorAll('.chip b, .chip small')].filter(e => e.scrollWidth > e.clientWidth + 1).length, star: a.querySelectorAll('.confl').length, other: a.querySelectorAll('button, .gtk, .rentl, .host').length })));
    assert.strictEqual(cards.length, bs.length, 'one card per building');
    cards.forEach((c, i) => { const us = bs[i].units, from = Math.min(...us.map(u => u.all_in)), rs = u => u.rent.asterisk || u.rent.basis_kind === 'net_effective';
      assert.strictEqual(c.href, '#bldg-' + bSlug(us[0])); assert.strictEqual(c.chips.length, 3, 'three facts'); assert.strictEqual(c.cutChips, 0, 'no fact is cut on ' + c.name); assert.strictEqual(c.other, 0, 'nothing else on the card');
      assert.strictEqual(c.chips[0], (us.length > 1 ? 'from ' : '') + money0(from) + (us.some(rs) ? '*' : ''), 'the best all-in price: ' + c.chips[0]);
      if (us.length > 1) assert(c.sub.includes(us.length + ' apartments'), 'how many apartments made the list: ' + c.sub);
      const sig = u => (u.confirm.asterisk ? String(u.confirm.what) : '') + '|' + (rs(u) ? 'r' + (u.rent.basis_kind === 'net_effective') + !!u.rent.needs_call : ''), shared = us.every(u => sig(u) === sig(us[0])) && sig(us[0]) !== '|';
      assert.strictEqual(c.star, shared ? 1 : 0, 'one asterisk line when every apartment shares it, none otherwise: ' + c.name); }); }
  // the avoid cards, the phone-call list and the not-re-checked list sit in their own rows
  await go('#hood-' + slug(hAvoid.id)); assert((await headOf('sec-avoid')).startsWith(hAvoid.counts.avoid + (hAvoid.counts.avoid === 1 ? ' place ' : ' places ')));
  assert(await page.isHidden('.unit.avoid'), 'avoid cards start closed'); await openRow('sec-avoid');
  assert.strictEqual(await page.locator('.unit.avoid').count(), hAvoid.counts.avoid); await overflow('hood avoid open');
  await page.evaluate(() => document.getElementById('sec-avoid').scrollIntoView()); await page.evaluate(() => window.scrollBy(0, -70)); await shot('03b-neighborhood-avoid-card');
  const hHeld = shownHoods.find(h => h.counts.held > 0);
  if (hHeld) { await go('#hood-' + slug(hHeld.id)); await openRow('sec-call');
    assert.strictEqual(await page.locator('#sec-call .callitem').count(), hHeld.counts.held); assert.strictEqual(await page.locator('#sec-call [data-act=save]').count(), 0);
    assert((await page.textContent('#sec-call > summary')).includes('two or more things')); await overflow('hood-held');
    await page.evaluate(() => document.getElementById('sec-call').scrollIntoView()); await page.evaluate(() => window.scrollBy(0, -70)); await shot('03c-worth-a-phone-call'); }
  const known = new Set([...data.held, ...data.units, ...data.avoid].map(u => u.id)), hoodIds = new Set(data.neighborhoods.map(h => h.id));
  const waitOnly = (data.awaiting_live_check || []).filter(a => !known.has(a.id)), waitHood = waitOnly.find(a => hoodIds.has(a.hood_id) && yearBy[hoodBy[a.hood_id].year]);
  console.log('awaiting live check:', (data.awaiting_live_check || []).length, '| not already in held:', waitOnly.length);
  if (waitHood) { await go('#hood-' + slug(waitHood.hood_id)); await openRow('sec-wait');
    assert.strictEqual(await page.locator('#sec-wait .callitem').count(), waitOnly.filter(a => a.hood_id === waitHood.hood_id).length); await overflow('hood-wait'); }
  // local rules and what is here; crime only inside the closed "See how we got this"
  const hRules = shownHoods.find(h => (h.local.parking_rules || []).length >= 3 && (h.local.dog_rules || []).length && h.state !== 'NY') || shownHoods.find(h => (h.local.parking_rules || []).length && (h.local.dog_rules || []).length);
  await go('#hood-' + slug(hRules.id));
  assert.strictEqual(await page.locator('#r-rules .rules li').count(), hRules.local.parking_rules.length + hRules.local.dog_rules.length, 'every local rule is listed');
  assert.strictEqual(await headOf('r-rules'), await page.evaluate(id => window.__houseHunt.headline('hood', id, 'hoodRules'), hRules.id));
  { const n = await page.locator('#sec-rows details.rowd').count(); assert(n >= 4 && n <= 7, 'four to seven rows on a neighborhood: ' + n); }
  await openRow('r-rules'); assert((await page.textContent('#r-rules')).includes(hRules.local.parking_rules[0].summary)); await overflow('hood-rules open');
  await openRow('r-here'); assert(await page.isHidden('#hood-crime'), 'the crime figures stay behind "See how we got this"');
  await page.click('#sec-how details.howd > summary'); assert(await page.isVisible('#hood-crime'));
  if (hRules.safety && hRules.safety.violent_per_1000 != null) assert((await page.textContent('#hood-crime')).includes('violent crimes per 1,000'));
  await shot('09-neighborhood-local-rules', true);
  const hNone = shownHoods.find(h => !(h.local.parking_rules || []).length);
  if (hNone) { await go('#hood-' + slug(hNone.id)); assert((await headOf('r-rules')).includes('not found, ask')); assert((await page.textContent('#r-rules .st')).trim() === 'Ask', 'a missing rule is flagged on the row'); assert((await page.textContent('#no-park-rules')).includes('Local parking rules not found yet'));
    const qs = await page.evaluate(id => window.__houseHunt.tourQs(id), hNone.unit_ids[0]); assert(qs.includes('Where do residents park overnight, and is a permit needed?')); }
  // "Among the safest on the list": the lowest fifth by violent rate among neighborhoods with places, and nothing else about safety
  { const rated = data.neighborhoods.filter(h => h.counts.shown > 0 && h.safety && h.safety.violent_per_1000 != null && (h.unit_ids || []).some(id => data.units.some(u => u.id === id))).sort((a, b) => a.safety.violent_per_1000 - b.safety.violent_per_1000), n = Math.floor(rated.length / 5);
    const safe = rated.slice(0, n).find(h => yearBy[h.year] && yearBy[h.year].hood_ids.includes(h.id)), not = rated.slice(n + 3).find(h => yearBy[h.year] && yearBy[h.year].hood_ids.includes(h.id));
    if (safe) { await go('#hood-' + slug(safe.id)); assert.strictEqual((await page.textContent('.sec.head .safest')).trim(), 'Among the safest on the list'); }
    if (not) { await go('#hood-' + slug(not.id)); assert.strictEqual(await page.locator('.safest').count(), 0); }
    console.log('safest badge:', n, 'of', rated.length, 'rated neighborhoods'); }

  // ---------- buildings ----------
  const whatsOf = u => [...new Set((u.disclosures || []).map(x => String(x.what || '').trim()).filter(w => w && w.toLowerCase() !== String(u.confirm.what || '').toLowerCase()))], whats = whatsOf;
  const rs = u => !!(u.rent.asterisk || u.rent.basis_kind === 'net_effective'), isBest = u => hoodBy[u.hood_id] && bUnits(u)[0].id === u.id, best = data.units.filter(isBest);
  const aptSel = u => '#apt-' + slug(u.id), openApt = async u => { await page.waitForSelector(aptSel(u), { state: 'attached' }); if (!(await page.evaluate(s => document.querySelector(s).open, aptSel(u)))) await page.click(aptSel(u) + ' > summary'); };
  const uRich = best.filter(u => u.confirm.asterisk && u.rent.asterisk && (u.disclosures || []).length).sort((a, b) => (b.evidence.items.length + b.tour_questions.length) - (a.evidence.items.length + a.tour_questions.length))[0] || best.find(u => u.confirm.asterisk) || best[0];
  const uSparse = best.filter(u => !u.confirm.asterisk && !u.rent.asterisk && !u.contact && bUnits(u).length === 1).sort((a, b) => (a.evidence.items.length + a.tour_questions.length) - (b.evidence.items.length + b.tour_questions.length))[0] || best[0];
  const conf = best.find(u => u.confirm.asterisk && !u.rent.asterisk) || best.find(u => u.confirm.asterisk);
  const bOne = best.find(u => bUnits(u).length === 1), bMost = best.slice().sort((a, b) => bUnits(b).length - bUnits(a).length)[0];
  for (const [tag, u] of [['rich', uRich], ['sparse', uSparse], ['with an asterisk', conf], ['one apartment', bOne], [bUnits(bMost).length + ' apartments (the most in the data)', bMost]]) {
    await go('#bldg-' + bSlug(u), '.bpage'); await fits('building', tag + ' (' + (u.building || u.address) + ')'); await noCrime('building ' + tag); await overflow('building ' + tag);
    for (const [id, key] of [['r-parking', 'parking'], ['r-dog', 'dog'], ['r-building', 'building'], ['r-reviews', 'reviews'], ['r-day', 'day']]) assert.strictEqual(await headOf(id), await page.evaluate(([i, k]) => window.__houseHunt.headline('unit', i, k), [u.id, key]), 'the row headline is the builder\'s: ' + id);
    // reviews of the building: what the sites show, most reviews first, each linked; never a judgement of ours
    { const r = u.ratings || {}, ps = (r.platforms || []).filter(x => x && x.platform && x.rating != null), exp = !ps.length || r.found_any === false ? (r.searched ? 'No reviews found online' : 'Not looked up yet') : null;
      const head = await headOf('r-reviews'); if (exp) assert.strictEqual(head, exp); else { const top = ps.slice().sort((a, b) => (b.count == null ? -1 : b.count) - (a.count == null ? -1 : a.count))[0]; assert(head.startsWith(Number(top.rating).toFixed(1) + ' on ' + top.platform), 'the site with the most reviews leads: ' + head); assert.strictEqual(/and (\d+) more sites?$/.test(head) ? +RegExp.$1 : 0, ps.length - 1); }
      assert(head.length <= 64, 'the headline fits: ' + head); assert.strictEqual((await page.textContent('#r-reviews .rl')).trim(), 'Reviews of the building');
      const body = await page.evaluate(() => ({ lis: [...document.querySelectorAll('#bld-reviews li')].map(li => li.textContent), links: [...document.querySelectorAll('#bld-reviews li a')].map(a => a.target + '|' + a.rel), facts: document.querySelectorAll('#bld-facts li').length, text: document.getElementById('bld-reviews').textContent }));
      assert.strictEqual(body.lis.length, exp ? 0 : ps.length); assert(body.facts >= 5, 'the building facts are in their row'); assert(!/★|we think|our rating|recommend/i.test(body.text));
      if (!exp) { assert(body.lis.every(x => /out of 5/.test(x)), 'each line: rating out of 5: ' + body.lis[0]); assert(body.links.every(x => x === '_blank|noopener noreferrer')); } } }
  // the page of a building: title, key facts, Save and photos, About the building, the building's rows, its apartments, Save again, the next building
  await go('#bldg-' + bSlug(uRich), '.bpage'); await small('building'); await shot('04-building', true); await shot('ux-04-building-collapsed');
  { const us = bUnits(uRich), pg = await page.evaluate(() => { const y = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().top + window.scrollY) : null; };
      return { h1: document.querySelector('.ph1').textContent.trim(), strip: [...document.querySelectorAll('.bpage .kstrip > div')].map(c => c.textContent), rows: [...document.querySelectorAll('#sec-rows > details.rowd')].map(d => d.id), labels: [...document.querySelectorAll('#sec-rows > details.rowd > summary .rl')].map(e => e.firstChild.textContent.trim()),
        y: { strip: y('.bpage .kstrip'), save: y('.savb[data-pos=top]'), photos: y('#see-photos'), about: y('#about'), rows: y('#sec-rows'), apts: y('#sec-apts'), save2: y('.savb[data-pos=bottom]'), next: y('.prevnext') }, about: document.getElementById('about') ? { h2: document.querySelector('#about h2').textContent, text: document.getElementById('about').textContent } : null,
        saves: [...document.querySelectorAll('.savb')].map(b => b.textContent.trim()), host: document.querySelectorAll('#view .host, #view .who, #view .clampw').length, sign: document.querySelectorAll('.bpage .sign').length }; });
    assert.strictEqual(pg.h1, uRich.building || String(uRich.address).split(',')[0]); assert.strictEqual(pg.strip.length, 4);
    assert(pg.strip[0].startsWith((us.length > 1 ? 'from ' : '').slice(0, 0) + money0(Math.min(...us.map(u => u.all_in)))) && /all-in/.test(pg.strip[0]), 'the from-price leads the strip: ' + pg.strip[0]); assert(/to Mom and Dad|drive/.test(pg.strip[1]) && /parking/.test(pg.strip[2]) && /dogs/.test(pg.strip[3]), 'then minutes, parking, dogs');
    assert.deepStrictEqual(pg.rows.filter(r => r !== 'r-queens'), ['r-day', 'r-parking', 'r-dog', 'r-building', 'r-reviews', 'r-rules'], 'the building\'s rows, A day here first: ' + pg.rows);
    assert.deepStrictEqual(pg.labels.slice(0, 6), ['A day here', 'The car', 'For the dog', 'The building', 'Reviews of the building', 'Local rules']); if (pg.rows.includes('r-queens')) assert.strictEqual(pg.rows[pg.rows.length - 1], 'r-queens');
    assert(pg.rows.length <= 8, 'at most eight rows: ' + pg.rows.length); assert.strictEqual(pg.host, 0, 'no host box'); assert.strictEqual(pg.sign, 0);
    assert(pg.y.strip < pg.y.save && pg.y.save < pg.y.about && pg.y.about < pg.y.rows && pg.y.rows < pg.y.apts && pg.y.apts < pg.y.save2 && pg.y.save2 < pg.y.next, 'in that order: ' + JSON.stringify(pg.y));
    assert.strictEqual(pg.saves.length, 2, '"Save this place" at the top and at the bottom'); assert(pg.saves.every(s => s.startsWith('Save this place')), pg.saves.join(' | '));
    assert.strictEqual(pg.about.h2, 'About the building'); if (uRich.host && uRich.host.line && !CRIME.test(uRich.host.line)) { const s0 = uRich.host.line.slice(0, 50); assert(pg.about.text.includes(s0), 'the text is shown'); assert.strictEqual((await page.evaluate(() => document.getElementById('view').textContent)).split(s0).length - 1, 1, 'and only once on the page'); }
    // photos: one clear tap near the top, to the building's own site when one of its apartments has it, else to the listing
    const ph = us.map(u => u.photos).filter(p => p && p.url), want = ph.find(p => p.kind === 'own_site') || ph[0] || null;
    if (want) { const b = await page.evaluate(() => { const a = document.getElementById('see-photos'); return { href: a.getAttribute('href'), target: a.target, rel: a.rel, text: a.textContent.replace(/\s+/g, ' ').trim(), svg: a.querySelectorAll('svg').length }; });
      assert.strictEqual(b.href, want.url); assert.strictEqual(b.target + '|' + b.rel, '_blank|noopener noreferrer'); assert.strictEqual(b.text, 'See photos' + 'opens ' + (want.where || new URL(want.url).hostname.replace(/^www\./, ''))); assert.strictEqual(b.svg, 1); assert(pg.y.photos < pg.y.about, 'before About the building'); }
    else if (!us.some(u => u.links && (u.links.building || u.links.listing))) assert.strictEqual(await page.locator('#see-photos').count(), 0, 'no link, no button'); }
  { const noPh = best.find(u => bUnits(u).every(x => !(x.photos && x.photos.url) && !(x.links && (x.links.listing || x.links.building)))); if (noPh) { await go('#bldg-' + bSlug(noPh), '.bpage'); assert.strictEqual(await page.locator('#see-photos').count(), 0); }
    console.log('buildings with a photos link:', best.filter(u => bUnits(u).some(x => x.photos && x.photos.url)).length, 'of', best.length, '| own site:', best.filter(u => bUnits(u).some(x => x.photos && x.photos.kind === 'own_site')).length); }
  if (await page.locator('#r-building [data-act=contact]').count()) { await go('#bldg-' + bSlug(uRich), '.bpage'); }
  { const withC = best.find(u => u.contact && u.contact.phone); if (withC) { await go('#bldg-' + bSlug(withC), '.bpage'); await openRow('r-building'); await page.click('#r-building [data-act=contact]'); await page.waitForSelector('#sheet.open'); assert((await page.textContent('#sheetBody')).includes('Leasing office')); await page.waitForTimeout(300); await shot('ux-04c-leasing-office-sheet'); await page.keyboard.press('Escape'); await page.waitForSelector('#sheet:not(.open)'); await page.waitForTimeout(300); } }
  // "A day here": a stack of closed rows, one per moment: icon, title, one-line takeaway, and a chip in three levels where the data can say
  await go('#bldg-' + bSlug(star), '.bpage'); await openRow('r-day');
  { const B0 = bUnits(star)[0], KS = ['wake', 'work', 'after', 'night', 'sat', 'sun'], ms = await page.evaluate(() => [...document.querySelectorAll('#r-day details.mom')].map(d => ({ id: d.id, open: d.open, icon: d.querySelectorAll('summary .mi svg').length, title: d.querySelector('summary .rl').firstChild.textContent.trim(), take: d.querySelector('summary .rh').textContent, chip: (d.querySelector('summary .lvl') || {}).textContent || '', chev: d.querySelectorAll('summary .chev').length })));
    assert.deepStrictEqual(ms.map(m => m.id), KS.map(k => 'm-' + k)); assert.strictEqual((await page.textContent('#mom-count')).trim(), '6 moments', 'it says how many are below');
    const tints = await page.evaluate(([id, ks]) => ks.map(k => window.__houseHunt.tint(id, k)), [B0.id, KS]);
    ms.forEach((m, i) => { assert(!m.open && m.icon === 1 && m.chev === 1 && m.title && m.take, 'closed, with icon, title, takeaway and caret: ' + JSON.stringify(m)); assert.strictEqual(m.chip, { s: 'Strong', m: 'Mixed', w: 'Weak' }[tints[i]] || '', 'the chip is the level, and absent where the data cannot say: ' + m.id); });
    assert(!CRIME.test(await page.evaluate(() => document.getElementById('r-day').innerText)), 'no crime figure on a moment row');
    for (const k of KS) { await page.click('#m-' + k + ' > summary'); assert((await page.locator('#m-' + k + ' .rb li').count()) >= 3, 'a moment opens to its facts: ' + k); assert.strictEqual(await page.locator('#m-' + k + ' details.howd[open]').count(), 0, 'sources start closed'); }
    await page.evaluate(() => document.getElementById('r-day').scrollIntoView({ block: 'start' })); await page.evaluate(() => window.scrollBy(0, -70)); await shot('ux-04b-day-moments-open');
    for (const k of KS) await page.click('#m-' + k + ' > summary'); await shot('ux-04b2-day-moments-closed');
    // three levels, three colours; Weak is the same numbers on the far side of a second line (twice or half the Strong line)
    const exp = { wake: u => { const v = u.moments.wake.park_walk_min; return v == null ? 'u' : v <= 5 ? 's' : v > 10 ? 'w' : 'm'; }, after: u => { const v = u.moments.after.restaurants_800m; return v == null ? 'u' : v >= 20 ? 's' : v < 10 ? 'w' : 'm'; },
      sat: u => { const b = u.moments.sat.bars_1600m, r = u.moments.sat.restaurants_1600m; return b == null || r == null ? 'u' : b >= 5 && r >= 25 ? 's' : b < 2.5 && r < 12.5 ? 'w' : 'm'; }, sun: u => { const v = u.vs_queens && u.vs_queens.drive_min; return v == null ? 'u' : v >= 3 ? 's' : v <= 1 ? 'w' : 'm'; } };
    const got = await page.evaluate(([ids, ks]) => ids.map(id => ks.map(k => window.__houseHunt.tint(id, k)).join('')), [data.units.map(u => u.id), Object.keys(exp)]), dist = {};
    data.units.forEach((u, i) => { const e = Object.keys(exp).map(k => exp[k](u)).join(''); assert.strictEqual(got[i], e, 'levels of ' + u.id); });
    const all6 = await page.evaluate(([ids, ks]) => ids.map(id => ks.map(k => window.__houseHunt.tint(id, k))), [data.units.map(u => u.id), KS]); all6.forEach(a => a.forEach((x, i) => { dist[KS[i]] = dist[KS[i]] || {}; dist[KS[i]][x] = (dist[KS[i]][x] || 0) + 1; }));
    console.log('moment levels (s strong, m mixed, w weak, u no chip):', JSON.stringify(dist));
    const col = await page.evaluate(() => { const o = {}; for (const c of ['strong', 'mixed', 'weak']) { const e = document.createElement('em'); e.className = 'lvl ' + c; document.body.appendChild(e); o[c] = getComputedStyle(e).backgroundColor; e.remove(); } return o; });
    assert(new Set(Object.values(col)).size === 3, 'three colours: ' + JSON.stringify(col)); const rgb = s => s.match(/\d+/g).map(Number), g = rgb(col.strong), yl = rgb(col.mixed), rd = rgb(col.weak);
    assert(g[1] > g[0] && yl[0] > 240 && yl[2] < 215 && rd[0] > rd[1] && rd[1] > 200, 'green, yellow and a soft (not harsh) red: ' + JSON.stringify(col)); }
  // "Apartments here": one compact row per apartment, closed, each with its own Save; it opens in place to its costs, what to confirm and its listing
  const multi = best.filter(u => bUnits(u).length > 1), bTwo = multi.find(u => bUnits(u).some(x => x.confirm.asterisk) && bUnits(u).some(x => rs(x))) || multi[0] || uRich;
  await go('#bldg-' + bSlug(bTwo), '.bpage');
  { const us = bUnits(bTwo), rows = await page.evaluate(() => [...document.querySelectorAll('#sec-apts .apt')].map(a => ({ id: a.querySelector('details').id, open: a.querySelector('details').open, name: a.querySelector('.an').textContent, price: a.querySelector('.ap').textContent, meta: a.querySelector('.am').textContent, conf: (a.querySelector('summary .ac:not(.out)') || {}).textContent || '', heart: a.querySelectorAll(':scope > .heartb').length, h: Math.round(a.getBoundingClientRect().height) })));
    assert.strictEqual((await page.textContent('#sec-apts h2')).replace(/\d+$/, '').trim(), us.length > 1 ? 'Apartments here' : 'The apartment'); assert.deepStrictEqual(rows.map(r => r.id), us.map(u => 'apt-' + slug(u.id)), 'its apartments, best first');
    rows.forEach((r, i) => { const u = us[i]; assert(!r.open, 'closed to start'); assert.strictEqual(r.heart, 1, 'its own Save'); if (u.unit) assert(r.name.includes(u.unit)); assert(r.price.startsWith(money0(u.all_in)), 'all-in: ' + r.price);
      assert(r.meta.includes(u.sqft != null ? Math.round(u.sqft) + ' sq ft' : 'size: ask') && r.meta.includes(u.floor != null ? 'floor ' + Math.round(u.floor) : 'floor not published') && r.meta.includes(u.available === 'now' ? 'available now' : /^\d{4}-\d\d-\d\d/.test(u.available || '') ? 'from ' : 'move-in date: ask'), 'size, floor and date: ' + r.meta);
      assert.strictEqual(!!r.conf, !!(u.confirm.asterisk || rs(u)), 'its own thing to confirm: ' + r.conf); if (u.confirm.asterisk) assert(r.conf.startsWith('* To confirm:')); if (W === 390) assert(r.h <= 130, 'a compact row: ' + r.h + 'px'); });
    await shot('ux-05-apartments-here');
    const u = us.find(x => x.confirm.asterisk) || us[0]; await openApt(u); const S0 = aptSel(u);
    assert.strictEqual(await page.locator(S0 + ' .receipt .ln:not(.tot)').count(), u.all_in_lines.length, 'every cost line is in the box'); assert((await page.textContent(S0 + ' .allin')).startsWith('All-in: '));
    assert.strictEqual(await page.locator(S0 + ' .receipt .ln small').count(), 0, 'no basis notes on the lines'); assert(await page.isHidden(S0 + ' .receipt .howb'));
    assert(u.all_in_unknown.length === 0 || (await page.textContent(S0 + ' .receipt')).toLowerCase().includes('not published'), 'an unknown cost reads "not published", never $0');
    assert((await page.textContent(S0 + ' .tour-qs')).includes(u.tour_questions[0] || 'to ask on the tour')); if (u.links && u.links.listing) assert.strictEqual(await page.getAttribute(S0 + ' .plinks a >> nth=0', 'href'), u.links.listing);
    assert.strictEqual(await page.evaluate(ss => ss.filter(s => document.querySelector(s).open).length, us.map(aptSel)), 1, 'only the one tapped is open');
    await page.evaluate(s => document.querySelector(s).scrollIntoView(), S0); await page.evaluate(() => window.scrollBy(0, -70)); await shot('ux-05b-apartment-open'); await overflow('apartment open');
    await page.click(S0 + ' .receipt details.howd > summary'); assert(await page.isVisible(S0 + ' .receipt .howb')); await shot('05-receipt-how-open');
    // "Photos of this apartment" only when its own page differs from the building's
    for (const x of us) { const bp = (us.map(y => y.photos).filter(p => p && p.url).find(p => p.kind === 'own_site') || us.map(y => y.photos).filter(p => p && p.url)[0] || {}).url, own = x.photos && x.photos.url, n = await page.locator(aptSel(x) + ' .aphoto').count(); assert.strictEqual(n, own && own !== bp && own !== (x.links && x.links.listing) ? 1 : 0, 'the apartment photo link: ' + x.id); } }
  // the asterisk: what to confirm on the apartment's line, the why behind a tap; disclosures as "Good to know before you call"
  await go('#bldg-' + bSlug(conf), '.bpage');
  { const us = bUnits(conf), nStar = us.filter(u => u.confirm.asterisk || rs(u)).length, t = (await page.textContent('#see-apts')).replace(/\s+/g, ' ').trim();
    assert(t.startsWith('* ' + (us.length > 1 ? 'See the ' + us.length + ' apartments' : 'See the apartment')), 'the asterisk rides on the line that leads to the apartments: ' + t); assert.strictEqual(await page.locator('.bpage .confl').count(), 0, 'no separate boxes at the top');
    assert(t.includes(us.length > 1 ? nStar + ' with something to confirm' : 'to confirm'), t);
    await page.click('#see-apts'); const y = await page.evaluate(() => ({ top: document.getElementById('sec-apts').getBoundingClientRect().top, end: window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2 })); assert(y.top >= 0 && (y.top < 200 || y.end), 'it scrolls to the apartments: ' + Math.round(y.top)); }
  await openApt(conf); assert((await page.textContent(aptSel(conf) + ' .confirm-box h4')).includes('Still to confirm'));
  assert((await page.textContent(aptSel(conf) + ' .confirm-box')).includes(conf.confirm.why.replace(/\s*\((?:and )?count(?:ed|s)? as \$0\)/gi, '').slice(0, 40)), 'the why is on the page'); assert(await page.isHidden(aptSel(conf) + ' .confirm-box blockquote'), 'but behind "See why"');
  if (await page.locator(aptSel(conf) + ' .confirm-box p:has-text("What to ask:")').count()) { const q = (await page.locator(aptSel(conf) + ' .confirm-box p:has-text("What to ask:")').first().textContent()).replace('What to ask: ', ''); assert((await page.textContent(aptSel(conf) + ' .tour-qs')).includes(q), 'the confirmation question is also in the tour questions'); }
  await overflow('unit-confirm'); await shot('08-unit-confirm-asterisk', true);
  const dU = data.units.find(u => whats(u).length >= 2 && !u.confirm.asterisk && hoodBy[u.hood_id]) || data.units.find(u => whats(u).length);
  console.log('places with a disclosure:', data.units.filter(u => whats(u).length).length, 'of', data.units.length);
  if (dU) { await go('#unit-' + slug(dU.id), '.bpage'); const S1 = aptSel(dU); assert(await page.evaluate(s => document.querySelector(s).open, S1), 'a link to a place opens its building with that apartment open');
    assert.strictEqual(await page.locator(S1 + ' .good-to-know > ul > li').count(), whats(dU).length, 'every disclosure is listed once');
    const gtk = await page.textContent(S1 + ' .good-to-know'), tqs = await page.textContent(S1 + ' .tour-qs'); assert(gtk.includes('Good to know before you call'));
    for (const w of whats(dU)) assert(gtk.toLowerCase().includes(w.toLowerCase()), 'disclosure shown: ' + w);
    for (const x of dU.disclosures) if (x.question) assert(tqs.includes(x.question), 'the disclosure question is in the tour questions: ' + x.question);
    if (!dU.confirm.asterisk) assert.strictEqual(await page.locator(S1 + ' .confirm-box, ' + S1 + ' .cstar').count(), 0, 'a disclosure is not an asterisk');
    await page.evaluate(s => document.querySelector(s + ' .good-to-know').scrollIntoView(), S1); await page.evaluate(() => window.scrollBy(0, -70)); await shot('12-unit-good-to-know'); await overflow('unit-disclosures'); }
  const noConf = best.find(u => bUnits(u).every(x => !x.confirm.asterisk && !rs(x)));
  if (noConf) { await go('#bldg-' + bSlug(noConf), '.bpage'); assert.strictEqual(await page.locator('.confirm-box, .cstar, .aptd summary .ac:not(.out)').count(), 0, 'nothing to confirm: no asterisk anywhere'); assert(!(await page.textContent('#see-apts')).includes('*')); }
  // rent with an asterisk: on the price, on the apartment's line, and the terms inside it
  await go('#unit-' + slug(star.id), '.bpage'); { const S2 = aptSel(star); assert((await page.textContent(S2 + ' .ap')).includes('*')); assert((await page.textContent(S2 + ' .confl.rent')).startsWith('* Rent:'));
    const co = await page.evaluate(x => window.__houseHunt.cleanText(x), star.rent.offer_text), rt = await page.textContent(S2 + ' .terms'); if (co) assert(rt.includes(co.slice(0, 30)), 'the offer, in the listing\'s words'); else assert(!rt.includes('in the listing\'s words')); await shot('04-unit-rent-asterisk', true); }
  // an old link to a place: the building's page, that apartment open and in view, the others closed
  { const u2 = data.units.find(u => hoodBy[u.hood_id] && bUnits(u).length > 1 && bUnits(u)[0].id !== u.id); if (u2) { await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); await page.evaluate(h => { location.hash = h; }, '#unit-' + slug(u2.id)); await page.waitForSelector('.bpage');
      const r = await page.evaluate(([s, all]) => ({ open: all.map(x => document.querySelector(x).open), top: Math.round(document.querySelector(s).getBoundingClientRect().top), h1: document.querySelector('.ph1').textContent.trim(), hash: location.hash }), [aptSel(u2), bUnits(u2).map(aptSel)]);
      assert.deepStrictEqual(r.open, bUnits(u2).map(x => x.id === u2.id), 'only that apartment is open'); assert(r.top >= 0 && r.top < 844 * 0.6, 'and it is in view: ' + r.top); assert.strictEqual(r.h1, bUnits(u2)[0].building || String(u2.address).split(',')[0]); assert.strictEqual(r.hash, '#unit-' + slug(u2.id)); } }
  // Next and Previous move between buildings, never between the apartments of one building
  { const h3 = shownHoods.find(h => bOf(h.id).length >= 3 && bOf(h.id)[1].units.length > 1) || shownHoods.find(h => bOf(h.id).length >= 3); if (h3) { const bs = bOf(h3.id);
      await go('#bldg-' + bSlug(bs[1].units[0]), '.bpage'); const ln = await page.evaluate(() => [...document.querySelectorAll('.prevnext a')].map(a => a.querySelector('small').textContent + '|' + a.getAttribute('href')));
      assert.deepStrictEqual(ln, ['Previous building|#bldg-' + bSlug(bs[0].units[0]), 'Next building|#bldg-' + bSlug(bs[2].units[0])]); assert.strictEqual(await page.locator('#view a[href^="#unit-"]').count(), 0, 'no link from a building to one of its own apartments');
      await page.click('.prevnext a >> nth=1'); await page.waitForFunction(h => location.hash === h, '#bldg-' + bSlug(bs[2].units[0])); assert.strictEqual(await page.evaluate(() => window.scrollY), 0, 'the next building opens at its top');
      await go('#bldg-' + bSlug(bs[0].units[0]), '.bpage'); assert.strictEqual(await page.locator('.prevnext a.prev').count(), 0, 'the first building has no Previous');
      await go('#bldg-' + bSlug(bs[bs.length - 1].units[0]), '.bpage'); assert(/Next neighborhood|Back to/.test(await page.textContent('.prevnext a:not(.prev) small')), 'after the last building: the next neighborhood'); } }
  // parking rules that matter for a car on the street, in "The car" and in "Local rules"
  const flagRe = [['overnight_parking', /\bbanned\b|not allowed|needs (a|the) permit|permit-only|may not park|overnight (parking )?permit|all-night parking restrictions/i], ['resident_permit', /out-of-state|out-of-town|registered in|registration[^.]{0,60}(show|address|same)|(licen[cs]e and|valid vehicle|motor vehicle|permanent vehicle) registration/i]];
  const flagged = h => (h.local.parking_rules || []).filter(r => flagRe.some(([k, re]) => r.rule === k && re.test(r.summary)));
  const uStreet = best.filter(u => (u.parking.rank == null || u.parking.rank < 2) && flagged(hoodBy[u.hood_id]).length), uGarage = best.find(u => u.parking.rank >= 2 && flagged(hoodBy[u.hood_id]).length);
  console.log('buildings with street or unknown parking under a flagged parking rule:', uStreet.length);
  if (uStreet.length) { await go('#bldg-' + bSlug(uStreet[0]), '.bpage'); await openRow('r-parking'); assert.strictEqual(await page.locator('#park-rules li').count(), flagged(hoodBy[uStreet[0].hood_id]).length); assert(await page.locator('#park-rules a.srcl').count() >= 1);
    const H0 = hoodBy[uStreet[0].hood_id]; await openRow('r-rules'); assert.strictEqual(await page.locator('#r-rules .rules li').count(), (H0.local.parking_rules || []).length + (H0.local.dog_rules || []).length, 'the town\'s rules are on the building page too'); await overflow('unit-park-rules'); await shot('10-unit-street-parking-rules'); }
  if (uGarage) { await go('#bldg-' + bSlug(uGarage), '.bpage'); assert.strictEqual(await page.locator('#park-rules').count(), 0); }
  const sd = best.find(u => u.dog.weight_limit_lb == null && u.dog.size_note);
  if (sd) { await go('#bldg-' + bSlug(sd), '.bpage'); assert.strictEqual(await headOf('r-dog'), 'allowed, small dogs, no weight given'); assert((await page.textContent('#dog-note')).includes('The page says small dogs; no weight number given')); }
  const noEv = best.find(u => ['none readable', 'rating screen: not_enough_data'].includes(u.evidence.public_evidence) && !u.evidence.items.length && !u.evidence.positive.length && !u.evidence.pause_notes);
  if (noEv) { await go('#bldg-' + bSlug(noEv), '.bpage'); assert((await page.textContent('#r-love .panel.pause')).includes('No public records or readable reviews for this building; ask on the tour')); }
  // keyboard: a row opens with Enter and says so
  { const was = await page.evaluate(() => document.getElementById('r-building').open); await page.focus('#r-building > summary'); await page.keyboard.press('Enter'); assert.strictEqual(await page.evaluate(() => document.getElementById('r-building').open), !was, 'a row opens and closes from the keyboard'); }

  // ---------- via the interface: experience -> neighborhood -> building; save any number; My list; tick two or three; compare ----------
  await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life');
  await page.click(`a.life[href="#exp-${slug(y1)}"]`); await page.waitForSelector('.viewsw'); await showAll();
  await page.click(`a.hood[href="#hood-${slug(star.hood_id)}"]`); await page.waitForSelector('#sec-places'); await showAll();
  await page.click(`a.cardl[href="#bldg-${bSlug(star)}"]`); await page.waitForSelector('.bpage');
  const heart = async u => { await page.click('#w-apt-' + slug(u.id) + ' > .heartb'); }, saved = async () => (await page.evaluate(() => window.__houseHunt.state())).saved;
  await heart(star); assert.deepStrictEqual(await saved(), [star.id]); assert.strictEqual(await page.getAttribute('#w-apt-' + slug(star.id) + ' > .heartb', 'aria-pressed'), 'true');
  assert.strictEqual((await page.evaluate(() => document.getElementById('tray').innerText)).replace(/\s+/g, ' ').trim(), 'Saved · 1 My list'); await shot('04c-saved-toast-and-bar');
  assert.strictEqual(await page.getAttribute('.savb[data-pos=top]', 'aria-pressed'), String(bUnits(star).length === 1), 'the building counts as saved only when all its apartments are');
  const two = data.units.find(u => u.year !== y1 && u.evidence.items.length && u.evidence.positive.length && isBest(u)) || data.units.find(u => u.year !== y1 && isBest(u));
  await go('#bldg-' + bSlug(two), '.bpage'); await openRow('r-queens'); assert(await page.locator('#r-love .panel.pause .quote a.srcl').count() >= 1); await overflow('unit2'); await shot('04c-building-with-evidence', true);
  // "Save this place" at the top saves the building's apartments; the one at the bottom shows the same state and takes them off again
  await page.click('.savb[data-pos=top]'); { const want = [star.id].concat(bUnits(two).map(u => u.id)); assert.deepStrictEqual(await saved(), want);
    assert.deepStrictEqual(await page.evaluate(() => [...document.querySelectorAll('.savb')].map(b => b.getAttribute('aria-pressed') + '|' + b.textContent.trim().slice(0, 5))), ['true|Saved', 'true|Saved'], 'both Save buttons say Saved');
    await page.click('.savb[data-pos=bottom]'); assert.deepStrictEqual(await saved(), [star.id], 'the bottom one takes them off'); await page.click('.savb[data-pos=bottom]'); assert.deepStrictEqual(await saved(), want); }
  const three = data.units.find(u => u.year !== y1 && u.year !== two.year && isBest(u)) || data.units.find(u => u.id !== star.id && u.id !== two.id && isBest(u));
  await go('#bldg-' + bSlug(three), '.bpage'); await heart(three);
  // any number: two more, from other buildings
  const more = best.filter(u => ![star, two, three].some(x => bSlug(x) === bSlug(u))).slice(0, 2); for (const u of more) { await go('#bldg-' + bSlug(u), '.bpage'); await heart(u); }
  const all = await saved(); assert(all.length >= 5, 'more than three can be saved: ' + all.length); assert.strictEqual((await page.evaluate(() => document.getElementById('tray').innerText)).replace(/\s+/g, ' ').trim(), 'Saved · ' + all.length + ' My list');
  await page.click('#tray a'); await page.waitForSelector('#mylist');
  const listIds = () => page.evaluate(() => [...document.querySelectorAll('#mylist .lrow')].map(r => r.getAttribute('data-id')));
  assert.deepStrictEqual(await listIds(), all, 'My list: everything saved, in the order saved, not ranked'); assert.strictEqual((await page.textContent('#list-count')).trim(), all.length + ' places saved');
  await fits('list', all.length + ' places saved'); await overflow('list'); await small('list'); await noCrime('list'); await shot('06-my-list', true); await shot('ux-06-my-list');
  // sorting is hers: all-in, minutes, size, move-in date, things to confirm, experience
  { const U = id => unitBy[id], mk = u => u.available === 'now' ? '0000' : /^\d{4}-\d\d-\d\d/.test(u.available || '') ? u.available : '9999', nc = u => (u.confirm.asterisk ? 1 : 0) + (rs(u) ? 1 : 0) + whats(u).length, yi = u => data.years.findIndex(y => y.id === u.year);
    const ord = { all_in: (a, b) => a.all_in - b.all_in, mins: (a, b) => a.moments.sun.drive_min - b.moments.sun.drive_min, sqft: (a, b) => (b.sqft == null ? -1e18 : b.sqft) - (a.sqft == null ? -1e18 : a.sqft), movein: (a, b) => mk(a) < mk(b) ? -1 : mk(a) > mk(b) ? 1 : 0, confirm: (a, b) => nc(a) - nc(b), exp: (a, b) => yi(a) - yi(b) };
    assert.deepStrictEqual(await page.evaluate(() => [...document.querySelectorAll('#listSort option')].map(o => o.value)), ['saved', 'all_in', 'mins', 'sqft', 'movein', 'confirm', 'exp']);
    for (const k of Object.keys(ord)) { await page.selectOption('#listSort', k); const want = all.map((id, i) => [U(id), i]).sort((x, y) => ord[k](x[0], y[0]) || x[1] - y[1]).map(x => x[0].id); assert.deepStrictEqual(await listIds(), want, 'sorted by ' + k); }
    await page.selectOption('#listSort', 'all_in'); await shot('ux-06a-my-list-sorted-by-all-in'); await page.selectOption('#listSort', 'saved'); }
  // tick any two or three, then compare; a fourth tick is refused; un-tick to swap
  assert.strictEqual(await page.getAttribute('#cmpBtn', 'aria-disabled'), 'true'); assert.strictEqual((await page.textContent('#cmpBtn')).trim(), 'Tick two or three to compare'); await page.click('#cmpBtn', { force: true }); assert.strictEqual(await page.evaluate(() => location.hash), '#list', 'nothing to compare yet');
  const tick = async u => { await page.click(`#mylist .lrow[data-id="${u.id}"] input[type=checkbox]`); };
  await tick(star); assert.strictEqual(await page.getAttribute('#cmpBtn', 'aria-disabled'), 'true', 'one is not enough'); await tick(two); assert.strictEqual((await page.textContent('#cmpBtn')).trim(), 'Compare selected (2)'); await tick(three); assert.strictEqual((await page.textContent('#cmpBtn')).trim(), 'Compare selected (3)');
  await tick(more[0]); assert.strictEqual(await page.isChecked(`#mylist .lrow[data-id="${more[0].id}"] input`), false, 'a fourth tick is refused'); assert.deepStrictEqual((await page.evaluate(() => window.__houseHunt.state())).pick, [star.id, two.id, three.id]);
  await shot('ux-06b-my-list-three-ticked');
  // one tap takes a place off the list, with an undo
  await page.click(`#mylist .lrow[data-id="${more[1].id}"] .lx`); assert.deepStrictEqual(await listIds(), all.filter(id => id !== more[1].id)); assert((await page.textContent('#undo')).includes('Undo')); await shot('ux-06c-my-list-undo');
  await page.click('#undo button'); assert.deepStrictEqual(await listIds(), all, 'Undo puts it back where it was'); assert.strictEqual(await page.locator('#undo').count(), 0);
  await page.reload(); await page.waitForSelector('#mylist'); assert.deepStrictEqual(await listIds(), all, 'the list is kept'); assert.strictEqual((await page.textContent('#cmpBtn')).trim(), 'Compare selected (3)', 'and so are the ticks');
  await page.click('#cmpBtn'); await page.waitForSelector('.pairbox');
  await fits('compare', 'three places'); await overflow('compare'); await small('compare'); await noCrime('compare');
  await shot('06-compare', true); await shot('ux-06-compare-collapsed');
  // the trade in plain words is in view; names and prices stay pinned; only what differs is shown, until asked; the Queens comparison starts closed
  assert(await page.isVisible('.pairbox p')); assert.strictEqual(await page.evaluate(() => getComputedStyle(document.querySelector('.cmp-head')).position), 'sticky');
  assert.strictEqual(await page.locator('.cmp-head .colh').count(), 3); assert(await page.isChecked('#ties'), '"Only show what differs" is on by default'); assert(!(await page.evaluate(() => document.getElementById('c-queens').open)), 'the Queens comparison is collapsed');
  const rows1 = await page.locator('#cmp-rows .rowc').count(); await page.click('#ties'); const rows2 = await page.locator('#cmp-rows .rowc').count();
  assert.strictEqual(rows2, 4 + ([star, two, three].some(u => u.confirm.asterisk || (u.disclosures || []).length) ? 1 : 0), 'money, space, the car, the trip and what is to confirm, got ' + rows2); assert(rows1 <= rows2);
  console.log('compare rows differing/all:', rows1, rows2, '|', await page.textContent('#tiesNote')); await page.click('#ties');
  assert.strictEqual(await page.locator('#cmp-rows .rowc .cell').count(), 3 * rows1, 'the label sits above three equal cells');
  if ([star, two, three].some(u => (u.disclosures || []).length)) assert((await page.textContent('#cmp-rows')).includes('Also ask:'), 'disclosures sit in the Still to confirm row');
  assert.strictEqual((await page.textContent('#c-queens .rl')).trim(), 'Compared to staying in Queens'); assert(!/against/i.test(await page.evaluate(() => document.getElementById('view').textContent)), 'no "against" on the compare page');
  await openRow('c-day'); assert(await page.locator('#day-rows .rowc').count() <= 5);
  await openRow('c-queens'); assert.strictEqual(await page.locator('#sec-scale button.pt').count(), 3 * data.meta.queens_spectrum.filter(s => !/crime/.test(s.measure)).length);
  await page.click('#sec-scale button.pt >> nth=0'); await page.waitForSelector('#sheet.open'); const st = await page.textContent('#sheetBody'); assert(st.includes('Staying in Queens') && st.includes('The bands'));
  await page.waitForTimeout(300); await shot('06b-five-point-explanation'); await page.click('#shClose');
  await page.evaluate(() => document.getElementById('c-queens').scrollIntoView({ block: 'start' })); await page.evaluate(() => window.scrollBy(0, -130)); await shot('ux-06b-compare-queens-open');
  await page.evaluate(() => window.scrollTo(0, 0)); await page.click('[data-act=pair][data-p="0-2"]'); assert.strictEqual(await page.getAttribute('[data-act=pair][data-p="0-2"]', 'aria-pressed'), 'true');
  // un-tick one from the comparison: two stay side by side, and it is still on the list to swap back in
  await page.click('.cmp-head .colh .x >> nth=2'); assert.strictEqual(await page.locator('.cmp-head .colh').count(), 2); assert.deepStrictEqual(await saved(), all, 'still saved'); await shot('06d-compare-two');
  await page.click('#view a[href="#list"]'); await page.waitForSelector('#mylist'); await tick(three); assert.strictEqual((await page.textContent('#cmpBtn')).trim(), 'Compare selected (3)');

  // ---------- limits ----------
  await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life');
  await page.click('[data-act=limits-open]'); await page.waitForSelector('#limsheet.open');
  // the limits are cost, drive, space and the "nothing left to confirm" switch: no safety slider, and no crime wording in the sheet
  assert.strictEqual(await page.locator('#lim-safe, #out-safe').count(), 0, 'no safety slider'); assert.strictEqual(await page.locator('#limsheet input[type=range]').count(), 3);
  { const lt = await page.evaluate(() => document.getElementById('limsheet').innerText), m = CRIME.exec(lt) || /safety|safe\b/i.exec(lt); assert(!m, 'the limits sheet names no crime rate: ' + (m && lt.slice(Math.max(0, m.index - 40), m.index + 40))); }
  const before = await page.textContent('#fitline');
  await page.locator('#lim-cost').fill('2400'); await page.locator('#lim-sqft').fill('700'); await page.locator('#lim-mins').fill('30');
  const after = await page.textContent('#fitline'); assert(before !== after, 'limits changed counts');
  const expect = data.units.filter(u => u.all_in <= 2400 && Math.round(u.moments.sun.drive_min) <= 30 && u.sqft != null && u.sqft >= 700).length;
  assert(after.startsWith(expect + ' of '), `limit count ${after} vs expected ${expect}`);
  console.log('limits:', before, '->', after, '| greyed experiences:', await page.locator('.life.none').count());
  await page.waitForTimeout(300); await shot('07-limits-sheet'); await overflow('limits');
  await page.click('[data-act=limits-close]'); assert((await page.textContent('#foot [data-act=limits-open]')).includes(expect + ' of ' + data.units.length + ' fit')); await shot('07b-home-with-limits', true);
  await page.click('[data-act=limits-open]'); await page.click('[data-act=limits-reset]'); await page.check('#lim-clear');
  const clearN = data.units.filter(u => !u.confirm.asterisk).length;
  assert((await page.textContent('#fitline')).startsWith(clearN + ' of '), 'toggle count ' + (await page.textContent('#fitline')) + ' vs ' + clearN);
  await page.click('[data-act=limits-close]');
  await go('#hood-' + slug(conf.hood_id)); await showAll();
  assert.strictEqual(await page.locator('#sec-places .bcard.out').count(), bOf(conf.hood_id).filter(b => b.units.every(u => u.confirm.asterisk)).length, 'a building is greyed when none of its apartments fits');
  assert((await page.textContent('#sec-places .bcard.out .why')).includes('Still to confirm'));
  await page.reload(); await page.waitForSelector('#sec-places'); assert(await page.isChecked('#lim-clear'), 'the toggle is remembered');
  await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life');
  await page.click('[data-act=limits-open]'); await page.click('[data-act=limits-reset]'); await page.click('[data-act=limits-close]');
  assert.strictEqual(await page.locator('.life.none').count(), 0);
  // copy the tour list: it comes from My list, every saved place
  await page.click('#tray a'); await page.waitForSelector('[data-act=copy]'); await page.click('[data-act=copy]');
  await page.waitForFunction(() => document.getElementById('copyStatus').textContent.length > 0); console.log('copy status:', await page.textContent('#copyStatus'));
  const txt = await page.evaluate(() => window.__houseHunt.tourText()); assert(txt.includes(star.tour_questions[0])); for (const id of all) assert(txt.includes(unitBy[id].building || String(unitBy[id].address).split(',')[0]), 'every saved place is in the tour list');
  assert.strictEqual((txt.match(/^\d+\. /gm) || []).length, all.length);
  if ((star.disclosures || []).length) assert(txt.includes('Good to know before you call:'));
  let clip = null; try { clip = await page.evaluate(() => navigator.clipboard.readText()); } catch (e) {} if (clip !== null) assert.strictEqual(clip, txt);

  // ---------- every view renders, collapsed: no side scroll, within 2.2 screens, no crime in the open ----------
  await page.reload(); await page.waitForSelector('#view .ph1, #view .life'); // a fresh visit: no row is remembered as open
  const t0 = Date.now();
  const res = await page.evaluate(async ([ids, LIMS]) => { let worst = 0, n = 0, tall = [], crime = [], maxH = {}, unresolved = [], cutHeads = [], longHeads = 0, heads = 0, dumps = []; const RE = /\bcrimes?\b|violen|burglar|\bthefts?\b|robber|assault|per 1,000/i;
    for (const h of ids) { const t = performance.now(); location.hash = h; await new Promise(r => setTimeout(r, 0)); worst = Math.max(worst, performance.now() - t); n++;
      if (location.hash !== '#' + h) { unresolved.push(h); continue; } // two ids that give the same plain hash: the page numbers the second one
      if (document.documentElement.scrollWidth > document.documentElement.clientWidth) return 'overflow at ' + h;
      const kind = h.split('-')[0], f = document.getElementById('foot').getBoundingClientRect(), tr = document.getElementById('trail'), ht = Math.round(f.bottom + window.scrollY - (tr.hidden ? 0 : tr.offsetHeight));
      maxH[kind] = Math.max(maxH[kind] || 0, ht); if (ht > LIMS[kind]) tall.push(h + ' ' + ht);
      if (document.querySelectorAll('#view .host, #view .who, #view .clampw').length || /your host/i.test(document.getElementById('view').textContent)) return 'a host box at ' + h;
      if (kind === 'unit' && !(document.querySelector('.bpage') && document.querySelectorAll('#sec-apts details.aptd[open]').length === 1)) return 'a place link that does not open its building with one apartment open: ' + h;
      if (kind === 'bldg' && document.querySelectorAll('#sec-apts details[open]').length) return 'an apartment open by default at ' + h;
      if (document.querySelectorAll('#view details.rowd[open]').length) return 'a row is open by default at ' + h;
      // a headline is readable in full while its row is closed: never clipped, never ending in an ellipsis, 64 characters at most
      document.querySelectorAll('#view details.rowd > summary .rh').forEach(e => { if (!e.getClientRects().length) return; const s = e.textContent, cs = getComputedStyle(e); heads++; if (s.length > 44) longHeads++;
        if (/…|\.\.\.$/.test(s) || e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1 || cs.textOverflow === 'ellipsis' || cs.whiteSpace === 'nowrap' || s.length > 64) cutHeads.push(h + ' ' + e.closest('details').id + ': ' + s); });
      // text from a listing is never shown as a dump of fields
      { const dv = document.getElementById('view').textContent, dm = /totalPrice|\bterm \d+:/.exec(dv); if (dm) dumps.push(h + ': ' + dv.slice(Math.max(0, dm.index - 30), dm.index + 50)); }
      const m = RE.exec(document.getElementById('view').innerText); if (m) crime.push(h + ': ' + document.getElementById('view').innerText.slice(Math.max(0, m.index - 40), m.index + 40).replace(/\s+/g, ' ')); }
    return { n, worst: Math.round(worst), maxH, tall, crime, unresolved, cutHeads, longHeads, heads, dumps }; },
    [[...data.years.map(y => 'exp-' + slug(y.id)), ...data.neighborhoods.filter(h => yearBy[h.year]).map(h => 'hood-' + slug(h.id)), ...pageBldgs.map(b => 'bldg-' + b.slug), ...data.units.filter(u => hoodBy[u.hood_id]).map(u => 'unit-' + slug(u.id))], { exp: limitOf('experience'), hood: limitOf('neighborhood'), bldg: limitOf('building'), unit: 1e9 }]);
  console.log('all views:', JSON.stringify(res).slice(0, 1500), 'in', Date.now() - t0, 'ms');
  assert(typeof res === 'object', String(res)); assert(res.unresolved.length <= 3, 'hashes the page did not open: ' + res.unresolved);
  if (W === 390) assert.strictEqual(res.tall.length, 0, 'pages over their ceiling, collapsed: ' + res.tall.slice(0, 8));
  assert.strictEqual(res.cutHeads.length, 0, 'row headlines that are cut or too long: ' + res.cutHeads.slice(0, 6).join(' | '));
  assert.strictEqual(res.dumps.length, 0, 'pipeline text on a page: ' + res.dumps.slice(0, 3).join(' | '));
  console.log('row headlines:', res.heads, 'on', res.n, 'pages, none cut;', res.longHeads, 'longer than 44 characters (two lines)');
  { const bad = await page.evaluate(us => us.map(u => [u.id, window.__houseHunt.cleanText(u.t)]).filter(x => /totalPrice|term \d+:|_|\bUTC\b|gross or net/.test(x[1]) || window.__houseHunt.looksDump(x[1])), data.units.concat(data.avoid, data.held).filter(u => u.rent && u.rent.offer_text).map(u => ({ id: u.id, t: u.rent.offer_text })));
    assert.strictEqual(bad.length, 0, 'an offer text that still reads like pipeline text: ' + JSON.stringify(bad.slice(0, 3))); }
  // where a neighborhood is: the state for Connecticut, the borough for New York City, the county elsewhere; a part of Jersey City by its short name
  { const where = await page.evaluate(hs => hs.map(h => [window.__houseHunt.hoodTitle(h), window.__houseHunt.hoodWhere(h)]), data.neighborhoods.map(h => ({ name: h.name, area: h.area, state: h.state, parent_name: h.parent_name, short_name: h.short_name })));
    data.neighborhoods.forEach((h, i) => { const [ti, wh] = where[i];
      assert(!/Planning Region/i.test(wh), 'no planning region under a name: ' + wh);
      if (h.parent_name && h.short_name) { assert.strictEqual(ti, h.short_name); assert.strictEqual(wh, h.parent_name + ', ' + h.state); }
      else { assert.strictEqual(ti, h.name); if (h.state === 'CT') assert.strictEqual(wh, 'Connecticut'); else if (h.state === 'NY' && /^(Brooklyn|Queens|Manhattan|Bronx|Staten Island)$/.test(h.area)) assert.strictEqual(wh, h.area + ', New York City'); else assert.strictEqual(wh, [h.area, h.state].filter(Boolean).join(', ')); } });
    const ct = shownHoods.find(h => h.state === 'CT'), jc = shownHoods.find(h => h.parent_name && h.short_name), nyc = shownHoods.find(h => h.state === 'NY' && h.area === 'Queens');
    if (ct) { await go('#hood-' + slug(ct.id)); assert.strictEqual((await page.textContent('#hood-where')).split(' · ')[0].trim(), 'Connecticut'); }
    if (nyc) { await go('#hood-' + slug(nyc.id)); assert.strictEqual((await page.textContent('#hood-where')).split(' · ')[0].trim(), 'Queens, New York City'); }
    if (jc) { await go('#hood-' + slug(jc.id)); assert.strictEqual((await page.textContent('.ph1')).trim(), jc.short_name); assert.strictEqual((await page.textContent('#hood-where')).split(' · ')[0].trim(), 'Jersey City, NJ'); await shot('ux-03e-jersey-city-part'); } }
  assert.strictEqual(res.crime.length, 0, 'crime wording in the open: ' + res.crime.slice(0, 5).join(' | '));
  console.log('collapsed heights (px, screens of ' + SCREEN + '):'); heights.forEach(x => console.log('  ' + x.kind.padEnd(13) + String(x.h).padStart(5) + '  ' + x.screens.toFixed(2) + (x.h > AIM ? '  over 2 screens' : '') + '  ' + x.tag));

  // ---------- made-up test values (in this test only) for fields the data does not carry yet ----------
  const page2 = await ctx.newPage(); page2.setDefaultTimeout(10000);
  page2.on('console', m => { if (m.type() === 'error') errors.push('test-data page: ' + m.text()); }); page2.on('pageerror', e => errors.push('test-data PAGEERROR ' + e.message));
  const vh = shownHoods.find(h => h.counts.shown > 0), vu = bUnits(data.units.find(u => u.hood_id === vh.id))[0];
  const h2o = shownHoods.find(h => h.year !== vh.year), h2id = h2o.id, u2o = best.find(u => u.hood_id === h2id), u2id = u2o.id;
  await page2.route('**/data.json', async route => { const d = JSON.parse(JSON.stringify(data)); const h = d.neighborhoods.find(x => x.id === vh.id), y = d.years.find(x => x.id === vh.year), u = d.units.find(x => x.id === vu.id);
    h.local.voices = [
      { excerpt: 'TEST quote, positive, noise.', theme: 'noise', sentiment: 'positive', context: 'renter', source: 'example forum', date: '2026-05-02', url: 'https://example.com/a' },
      { excerpt: 'TEST quote, positive two, noise.', theme: 'noise', sentiment: 'positive', context: '', source: 'example forum', date: '2026-08-11', url: 'https://example.com/b' },
      { excerpt: 'TEST quote, positive three, noise.', theme: 'noise', sentiment: 'positive', context: '', source: 'example forum', date: '2025-01-11', url: 'https://example.com/c' },
      { excerpt: 'TEST quote, negative, noise.', theme: 'noise', sentiment: 'negative', context: 'owner', source: 'example forum', date: '2026-03-09', url: 'https://example.com/d' },
      { excerpt: 'TEST quote, negative, parking, with a very long unbroken address https://example.com/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.', theme: 'parking', sentiment: 'negative', context: '', source: 'example forum', date: '', url: '' }];
    h.local.survey = [{ measure: 'would_recommend_share', value: '71%', source: 'example survey', as_of: '2026-06-30', url: 'https://example.com/s' }];
    h.toll_round_trip = 13.5; h.toll_round_trip_mail = 21.25; // both an E-ZPass and a mail-rate figure
    h.host = { intro: 'TEST host intro. ' + 'This is a long made-up paragraph in the voice of the host so that it runs well past four lines on a phone and needs the more button to be read in full. '.repeat(3) };
    h.headlines = { local_rules: { subhead: 'TEST subhead written by hand: ask the building about the overnight permit before you bring the car, and ask again in writing.' }, residents_say: { subhead: 'TEST subhead about violent crime that must not show.' } };
    y.tagline = 'TEST subhead: a quiet town, the lowest crime on the list and a train to the city.'; y.subhead = y.tagline; y.prose = Object.assign({}, y.prose, { promise: 'TEST promise about very low crime, 0.3 violent per 1,000.' });
    y.host = { intro: 'TEST experience host intro.', walkthrough: ['TEST walkthrough one.', 'TEST walkthrough two.'] };
    u.host = { line: 'TEST host line for the place.', catch: 'TEST host catch.' }; u.headlines = { parking: { subhead: 'TEST parking subhead.' } };
    // fields the writing agent will send: icon points, the day's moments, a text about the building
    const y2 = d.years.find(x => x.id !== vh.year), h2 = d.neighborhoods.find(x => x.id === h2id), u2 = d.units.find(x => x.id === u2id);
    y2.about_points = [{ icon: 'dog', text: 'TEST point one, with a dog.' }, { icon: 'no-such-icon', text: 'TEST point two, unknown icon.' }, { icon: 'moon', text: 'TEST point about violent crime that must not show.' }, 'TEST point three, a plain string.'];
    y2.day_moments = [{ icon: 'coffee', title: 'TEST morning', text: 'TEST moment one.' }, { icon: 'train', title: 'TEST commute', text: 'TEST moment two.' }];
    h2.about_points = [{ icon: 'park', text: 'TEST hood point.' }]; u2.about_building = 'TEST about the building. It has a second sentence. And a third one.';
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(d) }); });
  await page2.goto(BASE + '/index.html#hood-' + slug(vh.id)); await page2.waitForSelector('.ph1');
  
  // "About <name>": the made-up intro whole, no host box, nothing clamped
  { const ab = await page2.evaluate(() => ({ h2: document.querySelector('#about h2').textContent, text: document.getElementById('about').textContent, host: document.querySelectorAll('#view .host, #view .clampw, #view [data-act=unclamp]').length }));
    assert.strictEqual(ab.h2, 'About ' + (vh.parent_name && vh.short_name ? vh.short_name : vh.name)); assert.strictEqual(ab.host, 0); assert.strictEqual(ab.text.split('This is a long made-up paragraph').length - 1, 3, 'all of it is shown'); }
  // a written subhead under the built headline, lighter and clamped to two lines; a subhead about crime is not shown
  assert((await page2.textContent('#r-rules > summary .rs')).startsWith('TEST subhead written by hand')); assert.strictEqual(await page2.locator('#r-voices > summary .rs').count(), 0, 'a subhead about crime is dropped');
  const subStyle = await page2.evaluate(() => { const rs = document.querySelector('#r-rules .rs'), rh = document.querySelector('#r-rules .rh'), a = getComputedStyle(rs), b = getComputedStyle(rh); return { subW: +a.fontWeight, headW: +b.fontWeight, lines: Math.round(rs.clientHeight / parseFloat(a.lineHeight)) }; });
  assert(subStyle.headW > subStyle.subW && subStyle.lines <= 2, 'headline strong, subhead lighter and at most two lines: ' + JSON.stringify(subStyle));
  // tolls: the E-ZPass figure, with its note when a mail rate is also present
  { const chips = await page2.textContent('.sec.head .kstrip'); assert(chips.includes('$13.50') && chips.includes('NY E-ZPass') && !chips.includes('21.25'), 'E-ZPass figure with its note: ' + chips); }
  // resident voices in their row
  assert.strictEqual(await headOf('r-voices', page2), '3 positive, 2 negative'); await openRow('r-voices', page2);
  assert.strictEqual(await page2.locator('#no-voices').count(), 0); assert.strictEqual(await page2.locator('#sec-voices .vtheme').count(), 3, 'two themes and the survey heading');
  assert.strictEqual(await page2.locator('#sec-voices > .quote.pos').count(), 1, 'one positive shown against the one negative'); assert.strictEqual(await page2.locator('#sec-voices > .quote.neg').count(), 2);
  assert.strictEqual(await page2.locator('#sec-voices details .quote').count(), 2, 'the other positives are folded'); assert.strictEqual(await page2.locator('#sec-voices .quote a.srcl').count(), 4);
  assert((await page2.textContent('#sec-voices')).includes('Would recommend share: 71%.'));
  if (W === 390 && OUT) { await page2.evaluate(() => window.scrollTo(0, 0)); await page2.screenshot({ path: `${OUT}/ux-07-test-data-host-voice-and-subhead.png` }); }
  // experience: a subhead or promise about crime is not rendered; the host walks her through in a row
  await page2.evaluate(h => { location.hash = h; }, '#exp-' + slug(vh.year)); await page2.waitForSelector('#about');
  { const t = await page2.evaluate(() => document.getElementById('view').innerText); assert(!CRIME.test(t), 'no crime clause from the subhead or the promise'); assert(t.includes('TEST subhead: a quiet town and a train to the city.'), 'the rest of the subhead stays: ' + t.slice(0, 200)); }
  assert(!(await page2.locator('#sec-promise').count()) || !(await page2.textContent('#sec-promise')).includes('TEST promise'), 'a promise about crime is not shown'); assert.strictEqual(await headOf('r-scene', page2), 'TEST walkthrough one.');
  await page2.evaluate(() => { location.hash = '#lives'; }); await page2.waitForSelector('.life'); assert(!CRIME.test(await page2.evaluate(() => document.getElementById('view').innerText)));
  // building: the text under "About the building", the catch as its own marked line, a written subhead on a row
  await page2.evaluate(h => { location.hash = h; }, '#bldg-' + bSlug(vu)); await page2.waitForSelector('.bpage');
  { const a = await page2.evaluate(() => ({ t: document.getElementById('about').textContent, warn: document.querySelectorAll('#about .pi.warn').length })); assert(a.t.includes('TEST host line for the place.') && a.t.includes('The catch: TEST host catch.') && a.warn === 1, a.t); }
  assert.strictEqual((await page2.textContent('#r-parking .rs')).trim(), 'TEST parking subhead.');
  // about_points: an icon list, a dot for an unknown key, a point about crime left out; day_moments: its own titles; about_building in place of the host line
  await page2.evaluate(h => { location.hash = h; }, '#exp-' + slug(h2o.year)); await page2.waitForSelector('#about .pts');
  { const pts = await page2.evaluate(() => [...document.querySelectorAll('#about .pts li')].map(li => ({ t: li.textContent, stroke: li.querySelectorAll('svg path, svg rect').length, dot: li.querySelectorAll('svg circle[fill=currentColor]').length })));
    assert.deepStrictEqual(pts.map(p => p.t), ['TEST point one, with a dog.', 'TEST point two, unknown icon.', 'TEST point three, a plain string.'], 'the points, the crime one left out'); assert(pts[0].stroke >= 1 && pts[0].dot === 0, 'a drawn icon for a known key'); assert(pts[1].dot === 1 && pts[2].dot === 1, 'a dot for an unknown or missing key');
    assert.strictEqual(await page2.locator('#about .lead2').count(), 0, 'points replace the split text'); await openRow('r-scene', page2);
    assert.deepStrictEqual(await page2.evaluate(() => [...document.querySelectorAll('#r-scene .dmom h4')].map(h => h.textContent.trim())), ['TEST morning', 'TEST commute']); assert.strictEqual(await headOf('r-scene', page2), 'TEST moment one.');
    if (W === 390 && OUT) { await page2.evaluate(() => window.scrollTo(0, 0)); await page2.screenshot({ path: `${OUT}/ux-07b-test-data-about-points.png` }); } }
  await page2.evaluate(h => { location.hash = h; }, '#hood-' + slug(h2id)); await page2.waitForSelector('#about .pts'); assert.strictEqual((await page2.textContent('#about .pts')).trim(), 'TEST hood point.');
  await page2.evaluate(h => { location.hash = h; }, '#bldg-' + bSlug(u2o)); await page2.waitForSelector('.bpage');
  { const a = await page2.textContent('#about'); assert(a.includes('TEST about the building. It has a second sentence.') && a.includes('And a third one.'), a); if (u2o.host && u2o.host.line) assert(!a.includes(u2o.host.line.slice(0, 40)), 'about_building replaces the host line'); }
  const vo = await page2.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth); assert(vo <= 0, 'test-data overflow ' + vo);
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
