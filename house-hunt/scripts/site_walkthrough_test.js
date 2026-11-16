// Walk-through of the page at one width. Usage (from house-hunt/):
//   python3 scripts/page_data_extras.py && python3 scripts/build_site.py
//   (cd site && python3 -m http.server 8765 &)
//   BASE=http://localhost:8765 OUT=site/screens W=390 node scripts/site_walkthrough_test.js     (then W=1280 and W=320)
// BASE serves site/ (index.html fetches data.json and map_base.json). At W=390 it also opens the built single file
// (site/dist/index.html) as a phone, a desktop, a small phone with reduced motion, with storage that throws, and with its
// outer doctype/html/head/body stripped and re-wrapped, and compares what the built page (slimmed data) shows with what the
// whole data shows on a sample of pages. Screenshots are written at W=390 only.
// The tutorial ("How this works") opens by itself on a first visit: tutorialTests() covers it in fresh contexts; the main
// walk-through stores its flag first, and the built-page runs close it with Skip.
// Structure since round 3: experience -> neighborhood -> BUILDING (its rows, then "Apartments here") ; #unit-… opens the
// building with that apartment open; saving is unlimited ("My list", #list); compare takes the two or three ticked there.
const { chromium } = require('playwright');
const assert = require('assert');
const BASE = process.env.BASE, OUT = process.env.OUT, W = +(process.env.W || 390), VH = W === 320 ? 640 : W >= 1000 ? 900 : 844;
const SCREEN = 844, AIM = 2 * SCREEN; // collapsed pages: aim for two phone screens
// The "About" text is now shown whole, so a page is taller than two screens; what must hold is how soon the way on is reached (the "See the …" button) and these ceilings.
const LIMITS = { experience: 2.9, neighborhood: 2.9, building: 2.6, 'building, many': 3.5, compare: 2.2, list: 2.2 }, LIMIT = Math.round(3.6 * SCREEN), limitOf = kind => Math.round((LIMITS[kind] || 3.6) * SCREEN);
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: VH }, deviceScaleFactor: 1 });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
  // The tutorial opens by itself on a first visit. The walk-through below is a returning visit: the flag is already stored.
  // (tutorialTests() further down opens fresh contexts without it.)
  const TUT_KEY = 'lamia-house-hunt-v1-tutorial', seenTut = () => { try { localStorage.setItem('lamia-house-hunt-v1-tutorial', '1'); } catch (e) {} };
  await ctx.addInitScript(seenTut);
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
      bad: [...document.querySelectorAll('#view *, #foot *, #tray *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && (r.right > window.innerWidth + 1 || r.left < -1) && !e.closest('svg') && !e.closest('.story') && !e.closest('.hhm-chips'); }).slice(0, 5).map(e => e.tagName + '.' + e.className + ' ' + Math.round(e.getBoundingClientRect().right)) }));
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
  // (pass 8) a screenshot of one part of the page (W=390 only), clear of the sticky lines
  const shotEl = async (name, sel) => { if (W !== 390 || !OUT) return; await page.waitForFunction(() => !document.getElementById('toast').classList.contains('on'), null, { timeout: 5000 }).catch(() => {}); await page.locator(sel).first().scrollIntoViewIfNeeded(); await page.evaluate(() => window.scrollBy(0, -130)); await page.waitForTimeout(150); await page.locator(sel).first().screenshot({ path: `${OUT}/${name}.png` }); };
  // height of a page in its default, collapsed state: from under the sticky top line to the end of the footer (the fixed bottom bar is not counted)
  const pageHeight = async (pg) => (pg || page).evaluate(() => { const f = document.getElementById('foot').getBoundingClientRect(), t = document.getElementById('trail'); return Math.round(f.bottom + window.scrollY - (t.hidden ? 0 : t.offsetHeight)); });
  const heights = [];
  const fits = async (kind, tag) => { const h = await pageHeight(), open = await page.evaluate(() => [...document.querySelectorAll('#view details.rowd[open]')].map(d => d.id));
    heights.push({ kind, tag, h, screens: +(h / SCREEN).toFixed(2) });
    if (W === 390) { /* the owner dropped the page-height limit (UI pass 6): the height is measured and printed, never asserted */ assert.strictEqual(open.length, 0, `${kind} ${tag} has a row open by default: ${open}`); }
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
  // the page lists the experiences by how many apartments each shows, most first (chips, tiles, Next)
  const yearsBySize = d => { const cnt = {}; (d.units || []).filter(u => u.unit != null && String(u.unit).trim() !== '' && !/(^|[:_-])plan-/i.test(String(u.id || ''))).forEach(u => { cnt[u.hood_id] = (cnt[u.hood_id] || 0) + 1; }); const n = y => (y.hood_ids || []).reduce((s, id) => s + (cnt[id] || 0), 0); return d.years.map((y, i) => [y, i]).sort((a, b) => (n(b[0]) - n(a[0])) || (a[1] - b[1])).map(x => x[0]); };
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
    chips.forEach((c, i) => { const y = yearsBySize(d)[i], full = String(y.display_label || y.label).replace(/ Year$/, ' Experience'), short = full.replace(/^The\s+/, '').replace(/\s+Experience$/, '');
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
    assert(/\d+\s*apartments? shown|\d+ of \d+\s*apartments? match your filters/.test(cardText), 'the card gives the unit count: ' + cardText);
    assert(/(Typical rent|Rent) \$[\d,]+ · total about \$[\d,]+ with utilities and fees/.test(cardText), 'the map card gives both prices, each named: ' + cardText);
    if (H.rank_in_experience != null) { const of = d.years.find(y => y.id === H.year).hood_ids.length;
      assert((await pg.textContent('.hhm-card .hhm-rank')).trim() === (H.rank_in_experience === 1 ? 'Top pick' : '#' + H.rank_in_experience + ' of ' + of), 'rank within its experience: ' + cardText); }
    assert(/Experience/.test(await pg.textContent('.hhm-card .hhm-yr')), 'the card names the experience');
    await noSideScroll(pg, tag + ' card');
    // zoom and pan stay put when another mark is chosen, and when the page is drawn again (a limit moved)
    { const view = () => pg.evaluate(() => { const v = window.__houseHunt.map().view(); return [v.k, v.cx, v.cy].map(x => +x.toFixed(3)).join(); });
      await pg.waitForTimeout(o.reduced ? 50 : 350); const v1 = await view(); assert(+v1.split(',')[0] > 1.01, 'zoomed in: ' + v1);
      const other = d.neighborhoods.find(h => h.id !== H.id && h.year === H.year && h.lat != null && d.years.some(y => y.hood_ids.includes(h.id)));
      if (other) { await pg.evaluate(id => window.__houseHunt.map().select(id), other.id); assert.strictEqual((await pg.textContent('.hhm-card h3')).trim().indexOf(other.name), 0); assert.strictEqual(await view(), v1, 'another card: same zoom and pan'); await pg.evaluate(id => window.__houseHunt.map().select(id), H.id); }
      await pg.evaluate(() => { const e = document.getElementById('f-total'), v = e.value, fire = () => { e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); }; e.value = String(+e.max - +e.step); fire(); e.value = v; fire(); });
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
  // UI pass 6: the page never shows a floor plan or an apartment without its own identifier, and counts only what it shows.
  // The data is held to the same rule here, so every count below is recomputed from the arrays, as the page does.
  const isPlan = u => !!u && (/(^|[:_-])plan-/i.test(String(u.id || '')) || u.floor_plan === true || u.is_floor_plan === true || /floor[ _-]?plan/i.test(String(u.kind || u.listing_kind || u.unit || '')));
  const RAW = { units: data.units.length };
  data.units = data.units.filter(u => u.unit != null && String(u.unit).trim() !== '' && !isPlan(u));
  ['avoid', 'held', 'awaiting_live_check'].forEach(k => { data[k] = (data[k] || []).filter(u => !isPlan(u)); });
  { const ok = new Set(data.units.map(u => u.id)); data.neighborhoods.forEach(h => { h.unit_ids_raw = h.unit_ids || []; h.unit_ids = (h.unit_ids || []).filter(id => ok.has(id)); });
    const emptied = new Set(data.neighborhoods.filter(h => !h.unit_ids.length && (h.unit_ids_raw.length || (h.avoid_ids || []).length)).map(h => h.id)); data.years.forEach(y => { y.hood_ids = (y.hood_ids || []).filter(id => !emptied.has(id)); });
    console.log('shown after the identifier rule:', data.units.length, 'of', RAW.units, 'apartments;', emptied.size, 'neighborhoods left without one'); }
  { const av = new Set(data.avoid.map(u => u.id)); data.neighborhoods.forEach(h => { h.counts = Object.assign({}, h.counts, { shown: h.unit_ids.length, avoid: (h.avoid_ids || []).filter(id => av.has(id)).length, held: data.held.filter(u => u.hood_id === h.id).length }); }); }
  // the experiences are listed by how much there is to see, most first (the page sorts them the same way); FEW: below this a tile says so
  { const n = y => (y.hood_ids || []).reduce((s, id) => { const h = data.neighborhoods.find(x => x.id === id); return s + (h ? h.unit_ids.length : 0); }, 0); data.years.forEach((y, i) => { y.data_ix = i; y.n_shown = n(y); }); data.years.sort((a, b) => (b.n_shown - a.n_shown) || (a.data_ix - b.data_ix)); }
  const FEW = 5;
  // a building name as the page shows it (cleanName in site/index.html)
  const cleanName = t => { t = String(t == null ? '' : t).split(/\s+[|~]\s+/)[0].trim(); t = t.replace(/\s+[–—-]\s+\d.*$/, ''); if (/,\s*[A-Z]{2}\b(?:\s+\d{5}(?:-\d{4})?)?\s*(?:,|$)|,\s*(?:USA?|United States)\s*$/.test(t)) t = t.split(',')[0]; return t.replace(/\s*#\s*\S+\s*$/, '').trim(); };
  const m10 = v => '$' + (Math.round(v / 10) * 10).toLocaleString('en-US');
  const hoodBy = Object.fromEntries(data.neighborhoods.map(h => [h.id, h])), yearBy = Object.fromEntries(data.years.map(y => [y.id, y]));
  const median = a => { a = a.filter(x => x != null).sort((x, y) => x - y); const m = a.length >> 1; return !a.length ? null : a.length % 2 ? a[m] : (a[m - 1] + a[m]) / 2; };
  const money0 = v => '$' + Math.round(v).toLocaleString('en-US');
  const listed = y => y.hood_ids.map(id => hoodBy[id]).filter(Boolean), unitIds = new Set(data.units.map(u => u.id));
  // UI pass 8: an apartment has two prices. RENT is the rent line of its cost breakdown (what the listing asks); TOTAL is all_in
  // (rent + fees + pet rent + parking where known + estimated utilities). The page shows both wherever a price appears, and the
  // typical (median) rent and total are worked out from the apartments shown, as here.
  const rentOf = u => { const l = (u.all_in_lines || []).find(x => x && /^rent\b/i.test(String(x.line || '')) && x.amount != null); return l ? +l.amount : u.rent && u.rent.basis != null ? +u.rent.basis : u.rent && u.rent.listed != null ? +u.rent.listed : null; };
  const uBy8 = Object.fromEntries(data.units.map(u => [u.id, u])), unitsOfHood = h => (h.unit_ids || []).map(id => uBy8[id]).filter(Boolean), unitsOfYear = y => listed(y).flatMap(unitsOfHood);
  const moneyX = v => '$' + Number(v).toLocaleString('en-US', { maximumFractionDigits: Number(v) % 1 ? 2 : 0, minimumFractionDigits: Number(v) % 1 ? 2 : 0 });
  const span = a => { a = a.filter(x => x != null); return a.length ? [Math.min(...a), Math.max(...a)] : null; };
  const figsOf = us => ({ n: us.length, rent: median(us.map(rentOf)), rr: span(us.map(rentOf)), total: median(us.map(u => u.all_in)), tr: span(us.map(u => u.all_in)) });
  const L_RENT = 'Rent', L_TOTAL = 'Total with utilities and fees', WITH_UF = 'with utilities and fees';
  // a price in running text must say which of the two it is: "$2,345" needs "rent", "total" or "with utilities and fees" close by
  const barePrices = async (sel, pg) => (pg || page).evaluate(sel => { const out = [];
    document.querySelectorAll(sel).forEach(root => { const t = root.innerText.replace(/\s+/g, ' '); const re = /\$\d[\d,]*(?:\.\d\d)?\*?/g; let m;
      while ((m = re.exec(t))) { const near = t.slice(Math.max(0, m.index - 70), m.index + m[0].length + 60).toLowerCase();
        if (!/rent|total|with utilities and fees|toll|pet |parking|fee|a month in|limit|electric|internet|gas|lease|deposit|credit|off |bonus|save|special|\bover\b|difference|queens|\$\d[\d,]*\s*(?:to|–|-)\s*\$/.test(near)) out.push(t.slice(Math.max(0, m.index - 40), m.index + 40)); } });
    return out; }, sel);

  await page.goto(BASE + '/index.html');
  await page.waitForSelector('.life');
  // the drawings are optional: with site/illustrations.json each tile carries its banner, without it nothing is shown
  const illusRes = await page.request.get(BASE + '/illustrations.json'), illus = illusRes.ok();
  if (illus) await page.waitForSelector('a.life .illus svg'); else await page.waitForTimeout(200);
  console.log('illustrations:', illus ? 'present' : 'absent (no art is shown)');
  // ================= The tutorial ("UI pass 7: tutorial" in docs/SITE_NOTES.md) =================
  // a returning visit (the flag is stored): nothing opens by itself
  assert(await page.evaluate(() => document.getElementById('tut').hidden && document.getElementById('tutscrim').hidden), 'no tutorial on a returning visit');
  assert(!(await page.evaluate(() => document.getElementById('sheet').classList.contains('open'))), 'no sheet is open on arrival');
  const tutorialTests = async () => {
    const phone = W < 1000, mk = async (extra, init) => { const cx = await browser.newContext(Object.assign({ viewport: { width: W, height: VH }, deviceScaleFactor: 1 }, phone ? { hasTouch: true, isMobile: true } : {}, extra || {})), pg = await cx.newPage(), errs = []; pg.setDefaultTimeout(10000);
      pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); pg.on('pageerror', e => errs.push('PAGEERROR ' + e.message)); if (init) await pg.addInitScript(init); return { cx, pg, errs }; };
    const isOpen = pg => pg.evaluate(() => !document.getElementById('tut').hidden), count = async pg => (await pg.textContent('#tutCount')).trim();
    const inert = pg => pg.evaluate(() => ['view', 'foot', 'tray'].map(i => !!document.getElementById(i).inert));
    const nExp = data.years.length, NUMW = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'];
    // ---- a first visit: it opens over the first screen ----
    const A = await mk(); let pg = A.pg;
    await pg.goto(BASE + '/index.html'); await pg.waitForSelector('.life'); await pg.waitForSelector('#tutCard', { state: 'visible' });
    assert.strictEqual(await pg.evaluate(() => location.hash.replace(/^#/, '') || 'lives'), 'lives');
    assert.deepStrictEqual(await inert(pg), [true, true, true], 'the page behind is inert while the tutorial is open');
    const shell = await pg.evaluate(() => { const t = document.getElementById('tut'), st = document.getElementById('tutStep'); return { role: t.getAttribute('role'), modal: t.getAttribute('aria-modal'), named: !!document.getElementById(t.getAttribute('aria-labelledby')), h2: [...t.querySelectorAll('h2')].map(h => h.textContent.trim()), h1: t.querySelectorAll('h1').length, live: st.getAttribute('aria-live'), focus: t.contains(document.activeElement) ? document.activeElement.id : null, skip: document.getElementById('tutSkip').getAttribute('aria-label'), next: document.getElementById('tutNext').getAttribute('aria-label'), pup: !!t.querySelector('#tutPup svg'), imgs: t.querySelectorAll('img').length }; });
    assert.deepStrictEqual([shell.role, shell.modal, shell.named, shell.live, shell.h1, shell.imgs, shell.pup], ['dialog', 'true', true, 'polite', 0, 0, true], JSON.stringify(shell));
    assert.deepStrictEqual(shell.h2, ['How this works'], 'one h2, the tutorial title'); assert.strictEqual(shell.focus, 'tutNext', 'focus moves into the tutorial'); assert(shell.skip && shell.next, 'the controls are named');
    const N = +(await count(pg)).split(' of ')[1]; assert(N >= 6 && N <= 8, 'six to eight steps: ' + N); assert.strictEqual(await count(pg), '1 of ' + N);
    assert(await pg.isHidden('#tutBack'), 'no Back on the first step');
    const lum = c => { const v = c.match(/[\d.]+/g).slice(0, 3).map(x => { x = +x / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); }); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; }, ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    const steps = [];
    for (let i = 1; i <= N; i++) {
      assert.strictEqual(await count(pg), i + ' of ' + N);
      const m = await pg.evaluate(() => { const c = document.getElementById('tutCard'), r = c.getBoundingClientRect(), vis = e => e.getClientRects().length && getComputedStyle(e).visibility !== 'hidden';
        const bg = e => { for (let x = e; x; x = x.parentElement) { const b = getComputedStyle(x).backgroundColor; if (b && !/rgba\(0, 0, 0, 0\)|transparent/.test(b)) return b; } return 'rgb(255,255,255)'; };
        const texts = [...c.querySelectorAll('*')].filter(e => vis(e) && !e.closest('svg') && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && !e.classList.contains('sr'));
        return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, vw: innerWidth, vh: innerHeight, scroll: c.scrollHeight - c.clientHeight, title: c.querySelector('#tutStep h3').innerText.trim(), text: c.querySelector('.tut-p').innerText.trim(), art: !!c.querySelector('.tut-art svg, .tut-art .kf, .tut-art .tut-row, .tut-art .tut-apt, .tut-art .tut-chip'), artHidden: c.querySelector('.tut-art').getAttribute('aria-hidden'), artCtl: c.querySelectorAll('.tut-art button, .tut-art a, .tut-art [tabindex]').length,
          small: texts.filter(e => parseFloat(getComputedStyle(e).fontSize) < 14).map(e => e.className + ':' + e.textContent.trim().slice(0, 20) + ' ' + getComputedStyle(e).fontSize),
          cols: texts.filter(e => !e.closest('.tut-art')).map(e => [getComputedStyle(e).color, bg(e), e.textContent.trim().slice(0, 16)]),
          btns: [...c.querySelectorAll('button')].filter(vis).map(b => { const q = b.getBoundingClientRect(); return [b.textContent.trim(), Math.round(q.width), Math.round(q.height)]; }),
          off: [...c.querySelectorAll('.tut-art *')].filter(e => vis(e) && !e.closest('svg') && !e.closest('.kf') && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).display !== 'inline').map(e => e.className + ':' + e.textContent.trim().slice(0, 20)),
          dots: c.querySelectorAll('#tutDots i').length, on: [...c.querySelectorAll('#tutDots i')].findIndex(d => d.classList.contains('on')) }; });
      steps.push(m);
      const tw = m.title.split(/\s+/).length, pw = m.text.split(/\s+/).length;
      assert(tw >= 3 && tw <= 6, `step ${i} title is three to six words: ${m.title}`); assert(pw <= 28, `step ${i} text is at most 28 words (${pw}): ${m.text}`);
      assert(m.art && m.artHidden === 'true' && m.artCtl === 0, `step ${i} has a drawing, hidden from assistive tech, with no control in it`);
      assert(m.top >= 0 && m.bottom <= m.vh + 1 && m.left >= 0 && m.right <= m.vw + 1, `step ${i} card is on screen: ${JSON.stringify([m.top, m.bottom, m.vh])}`);
      assert(m.scroll <= (VH < 700 ? 60 : 1), `step ${i} fits the card without scrolling inside it (${m.scroll}px over)`);
      assert.strictEqual(m.small.length, 0, `step ${i} text under 14px: ${m.small}`); assert.strictEqual(m.off.length, 0, `step ${i} drawing overflows: ${m.off}`);
      m.btns.forEach(b => assert(b[1] >= 44 && b[2] >= 44, `step ${i} button "${b[0]}" is at least 44px: ${b}`));
      m.cols.forEach(c => assert(ratio(c[0], c[1]) >= 4.5, `step ${i} contrast of "${c[2]}" ${c[0]} on ${c[1]}: ${ratio(c[0], c[1]).toFixed(2)}`));
      assert(m.btns.some(b => b[0] === 'Skip'), 'Skip is on every step'); assert.strictEqual(m.dots, N); assert.strictEqual(m.on, i - 1, 'the dot follows the step');
      assert(!/all-in|\bgates?\b|verified|\bunits?\b|crime|neighbourhood|\byears?\b|\bplaces?\b|top three/i.test(m.title + ' ' + m.text), `step ${i} wording: ${m.text}`);
      assert.strictEqual((await pg.textContent('#tutNext')).trim(), i === N ? 'Done' : 'Next');
      if (W === 390 && OUT) { await pg.waitForTimeout(300); await pg.screenshot({ path: `${OUT}/p7-tutorial-${i}.png` }); }
      if (i < N) { await pg.click('#tutNext'); assert(await isOpen(pg)); }
    }
    // the words use the page's own labels, and the count of experiences comes from the data
    const all = steps.map(m => m.title + ' ' + m.text).join(' ');
    assert(steps[0].title.toLowerCase().startsWith(NUMW[nExp] + ' ') && steps[0].text.includes(NUMW[nExp] + ' experiences'), 'the number of experiences is read from the data: ' + steps[0].title);
    assert(!/everything included|all-in/i.test(all), 'the tutorial speaks of rent and total, never "everything included"');
    // (pass 8) one step explains the two prices in the page's own sentence, and its sample shows both; another names the Filter button
    { const st = steps.find(m => /rent/i.test(m.title) && /total/i.test(m.title)); assert(st, 'a step is about rent and total'); assert(/Rent is what the listing asks\. The total adds fees, parking, pet rent and our estimate of electricity, gas and internet\./.test(st.text), st.text);
      const fs = steps.find(m => /^Filter/.test(m.title)); assert(fs && /\bFilter\b/.test(fs.text) && /rent, total, size, the drive/.test(fs.text) && /My list/.test(fs.text), 'a step says the Filter button narrows everything: ' + (fs && fs.text)); }
    ['Show more', 'Map', 'Rent', 'total', 'Filter', 'See how we got this', '(*)', 'Still to confirm', 'Save', 'My list', 'Compare', 'See photos'].forEach(w => assert(all.includes(w), 'the tutorial names "' + w + '"'));
    // Back goes back; Done closes; the page is live again; it is remembered
    await pg.click('#tutBack'); assert.strictEqual(await count(pg), (N - 1) + ' of ' + N); await pg.click('#tutNext'); assert.strictEqual(await count(pg), N + ' of ' + N);
    await pg.click('#tutNext'); assert(!(await isOpen(pg)), 'Done closes the tutorial'); assert(await pg.isHidden('#tutscrim'));
    assert.deepStrictEqual(await inert(pg), [false, false, false], 'the page is live again');
    assert(await pg.evaluate(() => document.getElementById('view').contains(document.activeElement)), 'focus returns to the page');
    assert.strictEqual(await pg.evaluate(k => localStorage.getItem(k), TUT_KEY), '1');
    if (W === 390 && OUT) await pg.screenshot({ path: `${OUT}/p7-tutorial-after.png` });
    await pg.reload(); await pg.waitForSelector('.life'); await pg.waitForTimeout(200); assert(!(await isOpen(pg)), 'it does not reopen after Done');
    // the button under the title is on the first screen without scrolling, and reopens it from step 1
    const tb = await pg.evaluate(() => { const r = document.getElementById('how-top').getBoundingClientRect(); return [r.top, r.bottom, r.width, r.height, innerHeight]; });
    assert(tb[0] > 0 && tb[1] < tb[4] && tb[3] >= 44, '"How this works" sits near the top: ' + tb); assert.strictEqual((await pg.textContent('#how-top')).trim(), 'How this works');
    await pg.click('#how-top'); assert(await isOpen(pg)); assert.strictEqual(await count(pg), '1 of ' + N); await pg.click('#tutNext'); await pg.click('#tutNext'); assert.strictEqual(await count(pg), '3 of ' + N);
    await pg.click('#tutSkip'); assert(!(await isOpen(pg)), 'Skip closes'); assert.strictEqual(await pg.evaluate(() => document.activeElement.id), 'how-top', 'focus returns to the button that opened it');
    await pg.click('#how-top'); assert.strictEqual(await count(pg), '1 of ' + N, 'it starts again from step 1');
    // keyboard: right and left arrows, then Escape
    await pg.keyboard.press('ArrowRight'); await pg.keyboard.press('ArrowRight'); assert.strictEqual(await count(pg), '3 of ' + N); await pg.keyboard.press('ArrowLeft'); assert.strictEqual(await count(pg), '2 of ' + N);
    await pg.keyboard.press('ArrowLeft'); await pg.keyboard.press('ArrowLeft'); assert.strictEqual(await count(pg), '1 of ' + N); assert(await pg.evaluate(() => document.getElementById('tut').contains(document.activeElement)), 'focus stays inside');
    for (let i = 0; i < N + 2; i++) await pg.keyboard.press('ArrowRight'); assert(await isOpen(pg), 'the right arrow stops at the last step'); assert.strictEqual(await count(pg), N + ' of ' + N);
    await pg.keyboard.press('Escape'); assert(!(await isOpen(pg)), 'Escape closes');
    // the footer link opens the same tutorial; a tap outside the card closes it
    await pg.click('#foot [data-act=how-open]'); assert(await isOpen(pg)); assert.strictEqual(await count(pg), '1 of ' + N); assert.strictEqual(await pg.locator('#sheet.open').count(), 0, 'no sheet: the footer link opens the tutorial');
    await pg.mouse.click(4, 4); assert(!(await isOpen(pg)), 'a tap outside closes');
    // a swipe: left is next, right is back
    if (phone) { await pg.click('#how-top'); const y = await pg.evaluate(() => { const r = document.querySelector('#tutStep h3').getBoundingClientRect(); return r.top + 10; });
      const drag = async (x0, x1) => pg.evaluate(([a, b, yy]) => { const c = document.getElementById('tutCard'), t = (x) => new Touch({ identifier: 1, target: c, clientX: x, clientY: yy }); c.dispatchEvent(new TouchEvent('touchstart', { touches: [t(a)], changedTouches: [t(a)], bubbles: true })); c.dispatchEvent(new TouchEvent('touchend', { touches: [], changedTouches: [t(b)], bubbles: true })); }, [x0, x1, y]);
      await drag(W - 60, 60); assert.strictEqual(await count(pg), '2 of ' + N, 'a swipe left goes on'); await drag(60, W - 60); assert.strictEqual(await count(pg), '1 of ' + N, 'a swipe right goes back');
      await drag(60, W - 60); assert.strictEqual(await count(pg), '1 of ' + N); await drag(W / 2, W / 2 - 20); assert.strictEqual(await count(pg), '1 of ' + N, 'a small move is not a swipe'); await pg.click('#tutSkip'); }
    assert.strictEqual(A.errs.length, 0, 'tutorial console errors: ' + A.errs.join(' | ')); await A.cx.close();
    // ---- Skip on a first visit: closed for good ----
    const B = await mk(); pg = B.pg; await pg.goto(BASE + '/index.html'); await pg.waitForSelector('#tutCard', { state: 'visible' }); await pg.click('#tutSkip'); assert(!(await isOpen(pg)));
    await pg.reload(); await pg.waitForSelector('.life'); await pg.waitForTimeout(200); assert(!(await isOpen(pg)), 'it does not reopen after Skip');
    // the page is usable straight away
    await pg.click('a.life >> nth=0'); await pg.waitForSelector('.ph1'); assert.strictEqual(B.errs.length, 0, B.errs.join(' | ')); await B.cx.close();
    // ---- a link straight to an inner page: nothing opens, there or on the way back to the first screen ----
    const C = await mk(); pg = C.pg;
    for (const h of ['#exp-' + slug(data.years[0].id), '#hood-' + slug(listed(data.years[0])[0].id), '#list']) { await pg.goto('about:blank'); await pg.goto(BASE + '/index.html' + h); await pg.waitForSelector('#view .ph1, #view .pg, #mylist, #view .empty'); await pg.waitForTimeout(150); assert(!(await isOpen(pg)), 'no tutorial on a link to ' + h); assert.strictEqual(await pg.evaluate(k => localStorage.getItem(k), TUT_KEY), null); }
    assert.strictEqual(C.errs.length, 0, C.errs.join(' | ')); await C.cx.close();
    // ---- storage that throws: it shows on each load, and always closes ----
    const D = await mk({}, () => { const bad = () => { throw new Error('storage blocked'); }; try { Object.defineProperty(window, 'localStorage', { get: bad, configurable: true }); Object.defineProperty(window, 'sessionStorage', { get: bad, configurable: true }); } catch (e) {} }); pg = D.pg;
    await pg.goto(BASE + '/index.html'); await pg.waitForSelector('#tutCard', { state: 'visible' }); await pg.click('#tutSkip'); assert(!(await isOpen(pg)), 'with storage blocked it still closes'); assert.deepStrictEqual(await inert(pg), [false, false, false]);
    await pg.reload(); await pg.waitForSelector('#tutCard', { state: 'visible' }); await pg.keyboard.press('Escape'); assert(!(await isOpen(pg)));
    await pg.click('#how-top'); for (let i = 0; i < N; i++) await pg.click('#tutNext'); assert(!(await isOpen(pg)), 'Done closes with storage blocked');
    await pg.click('a.life >> nth=0'); await pg.waitForSelector('.ph1'); assert.strictEqual(D.errs.length, 0, D.errs.join(' | ')); await D.cx.close();
    // ---- reduced motion: the card does not animate ----
    const E = await mk({ reducedMotion: 'reduce' }); pg = E.pg; await pg.goto(BASE + '/index.html'); await pg.waitForSelector('#tutCard', { state: 'visible' });
    assert.strictEqual(await pg.evaluate(() => getComputedStyle(document.getElementById('tutCard')).animationName), 'none', 'no animation with reduced motion'); await pg.click('#tutSkip'); await E.cx.close();
    console.log('tutorial:', N, 'steps;', steps.map((m, i) => (i + 1) + '. ' + m.title + ' (' + m.text.split(/\s+/).length + ' words)').join('; '));
  };
  await tutorialTests();
  // on the walked page (a returning visit) both buttons are there and open it
  await page.click('#foot [data-act=how-open]'); await page.waitForSelector('#tutCard', { state: 'visible' }); await page.keyboard.press('Escape'); assert(await page.isHidden('#tutCard'));
  // ---------- the bottom bar: one slim line, "Saved · N", that opens My list ----------
  { const tr = await page.evaluate(() => { const e = document.getElementById('tray'); return { h: e.offsetHeight, text: e.innerText.replace(/\s+/g, ' ').trim(), href: e.querySelector('a').getAttribute('href'), pad: parseFloat(getComputedStyle(document.body).paddingBottom) }; });
    assert(tr.h >= 50 && tr.h <= 58, 'the bar is slim: ' + tr.h + 'px'); assert.strictEqual(tr.text, 'Saved · 0 My list'); assert.strictEqual(tr.href, '#list');
    assert(Math.abs(tr.pad - tr.h - 20) < 1.5, 'the page keeps room for the bar: ' + tr.pad); console.log('bottom bar:', tr.h, 'px');
    await page.click('#tray a'); await page.waitForSelector('.ph1'); assert.strictEqual((await page.textContent('.ph1')).trim(), 'My list'); assert((await page.textContent('#view .empty')).includes('Nothing saved yet')); await shot('ux-00b-my-list-empty');
    await page.goBack(); await page.waitForSelector('.life'); }
  // ---------- first screen: six short cards, the median with the range small beneath, nothing explained ----------
  assert.strictEqual(await page.locator('a.life').count(), data.years.length);
  const tiles = await page.evaluate(() => [...document.querySelectorAll('a.life')].map(a => ({ h: Math.round(a.getBoundingClientRect().height), label: a.querySelector('h3').textContent.trim(), figs: [...a.querySelectorAll('.figs b')].map(b => b.textContent), labels: [...a.querySelectorAll('.figs span')].map(b => b.textContent), kids: [...a.children].map(c => c.tagName + (c.className ? '.' + c.className : '')), mark: a.querySelectorAll('h3 .ymk').length, w: a.clientWidth, art: (i => i ? { h: Math.round(i.getBoundingClientRect().height), w: Math.round(i.getBoundingClientRect().width), svg: i.querySelectorAll('svg').length } : null)(a.querySelector('.illus')), tag: (a.querySelector('.l2') || {}).textContent, rng: [...a.querySelectorAll('.figs .rng')].map(b => b.textContent), text: a.innerText,
    pp: (p => p ? { rl: p.querySelector('.pp-r .pp-l').textContent, r: p.querySelector('.pp-r b').textContent, rr: (p.querySelector('.pp-r .rng') || {}).textContent || '', tl: p.querySelector('.pp-t .pp-l').textContent, t: p.querySelector('.pp-t b').textContent.replace(/\s+/g, ' ').trim(), uf: p.querySelector('.pp-t .uf').textContent, tr: (p.querySelector('.pp-t .rng') || {}).textContent || '', fsR: parseFloat(getComputedStyle(p.querySelector('.pp-r b')).fontSize), fsT: parseFloat(getComputedStyle(p.querySelector('.pp-t b')).fontSize), rentFirst: p.querySelector('.pp-r').getBoundingClientRect().left <= p.querySelector('.pp-t').getBoundingClientRect().left, small: [...p.querySelectorAll('*')].filter(e => e.children.length === 0 && e.textContent.trim()).map(e => parseFloat(getComputedStyle(e).fontSize)).sort((a, b) => a - b)[0], ufLines: Math.round(p.querySelector('.pp-t .uf').getBoundingClientRect().height / parseFloat(getComputedStyle(p.querySelector('.pp-t .uf')).lineHeight)) } : null)(a.querySelector('.pp')) })));
  tiles.forEach((t, i) => { const y = data.years[i];
    assert.strictEqual(t.label, String(y.display_label || y.label).replace(/ Year$/, ' Experience'));
    // (pass 8) both prices on the tile: the typical rent first and larger, the typical total beside it with "about" and "with utilities and fees"; each to $10, each with its range
    { const us = unitsOfYear(y), f = figsOf(us), one = us.length === 1; assert(t.pp, 'the tile carries the pair of prices');
      assert.strictEqual(t.pp.rl, one ? L_RENT : 'Typical rent'); assert.strictEqual(t.pp.r, one ? moneyX(f.rent) : m10(f.rent), 'the typical rent is the median rent of the apartments shown, to $10');
      assert.strictEqual(t.pp.tl, one ? 'Total' : 'Typical total'); assert.strictEqual(t.pp.t, 'about ' + m10(f.total), 'the typical total is the median total, to $10, said with "about"'); assert.strictEqual(t.pp.uf, WITH_UF);
      if (y.medians && y.medians.all_in != null) assert.strictEqual(m10(f.total), m10(y.medians.all_in), 'and it is the stored median');
      assert(t.pp.rentFirst && t.pp.fsR > t.pp.fsT, 'rent comes first and is the larger figure'); assert(t.pp.small >= 12.5, 'nothing in the pair is under 12.5 px: ' + t.pp.small); assert(t.pp.ufLines <= 2, '"with utilities and fees" takes two lines at most: ' + t.pp.ufLines);
      if (us.length >= FEW) { if (m10(f.rr[0]) !== m10(f.rr[1])) assert.strictEqual(t.pp.rr, m10(f.rr[0]) + ' to –' + m10(f.rr[1]), 'the rent range sits beneath'); if (m10(f.tr[0]) !== m10(f.tr[1])) assert.strictEqual(t.pp.tr, m10(f.tr[0]) + ' to –' + m10(f.tr[1]), 'the total range sits beneath'); } else assert(!t.pp.rr && !t.pp.tr, 'no ranges over a handful'); }
    if (y.medians && y.medians.drive_min != null) assert.strictEqual(t.figs[0], Math.round(y.medians.drive_min) + ' min', 'the tile shows the median drive');
    const few = y.n_shown < FEW; if (i) assert(data.years[i - 1].n_shown >= y.n_shown, 'the tiles run from the most apartments to the fewest');
    if (few) { assert.strictEqual(t.rng.length, 0, 'a tile with a handful of apartments shows no range'); assert(t.text.includes('Only ' + y.n_shown + (y.n_shown === 1 ? ' apartment' : ' apartments') + ' right now'), 'it says how few there are: ' + t.text.replace(/\s+/g, ' ')); }
    // a tile is its marker, the label, the tagline, two numbers with their ranges, and the count of places: nothing else
    assert.deepStrictEqual(t.kids, [illus ? 'DIV.illus banner' : null, 'H3', y.tagline ? 'P.l2' : null, 'DIV.pp tile', 'DIV.figs xt', few ? 'P.tnote' : null].filter(Boolean), 'a tile has nothing else: ' + t.kids);
    if (illus) { assert(t.art.h >= 100 && t.art.h <= 132, 'the drawing is a banner of about 110 to 130 px: ' + t.art.h); assert(t.art.svg === 1 && t.art.w >= t.w - 8, 'edge to edge on the tile'); }
    assert.strictEqual(t.mark, 1, 'the marker is on the tile'); if (y.tagline && !CRIME.test(y.tagline)) assert.strictEqual(t.tag, y.tagline, 'the tagline is shown whole');
    assert.strictEqual(t.figs.length, 2); assert.strictEqual(t.figs[1], String(listed(y).reduce((n, h) => n + (h.unit_ids || []).filter(id => unitIds.has(id)).length, 0)), 'the count of places');
    assert.deepStrictEqual(t.labels, [(y.hood_ids.length <= 1 ? '' : 'typical ') + 'to Mom and Dad', t.figs[1] === '1' ? 'apartment' : 'apartments']);
    // (pass 8) the tile is taller by the second price: 400 px with the drawing (it was 336 with one figure)
    if (W === 390) assert(t.h <= (illus ? 400 : 280), 'an experience tile is a short card: ' + t.h + 'px'); });
  assert.deepStrictEqual(await barePrices('a.life'), [], 'no price on a tile without its name');
  { const pn = (await page.textContent('#price-note')).trim(); assert(/Rent is what the listing asks\. The total adds fees, parking, pet rent and our estimate of electricity, gas and internet\./.test(pn), 'the first screen says once what the two prices are: ' + pn); assert(!/everything included/i.test(await page.evaluate(() => document.getElementById('view').innerText)), 'no "everything included" on the first screen'); }
  { const end = await page.evaluate(() => Math.round(document.getElementById('see-map').getBoundingClientRect().bottom + window.scrollY));
    console.log('first screen: the six tiles and "See them on a map" end at', end, 'px =', (end / SCREEN).toFixed(2), 'screens');
    if (W === 390) assert(end <= (illus ? 3.9 : 3.1) * SCREEN, 'tiles and the map button fit in ' + (illus ? '3.9 screens with the drawings' : '3.1 screens') + ' (pass 8: each tile carries two prices): ' + end);
    assert(await page.evaluate(() => document.getElementById('see-map').getBoundingClientRect().top > [...document.querySelectorAll('a.life')].pop().getBoundingClientRect().bottom), 'the map button follows the tiles'); }
  console.log('first screen: tile heights', tiles.map(t => t.h).join(', '), '| page', await pageHeight(), 'px with the map');
  assert.strictEqual(await page.locator('#view .mock, #view .coldopen, #view .confnote, #view .tip').count(), 0, 'no explaining lines on the first screen');
  assert.strictEqual(await page.locator('#view details.howd[open]').count(), 0);
  assert((await page.textContent('#sources')).includes('OpenStreetMap'), 'the sources are still there, behind the link');
  assert(await page.isHidden('#foothow'), '"See how we got this" starts closed');
  await page.click('[data-act=foot-how]'); assert(await page.isVisible('#foothow')); assert.strictEqual(await page.getAttribute('[data-act=foot-how]', 'aria-expanded'), 'true'); await page.click('[data-act=foot-how]');
  await noCrime('first screen');
  await overflow('home'); await small('home');
  await shot('01-home', true); await shot('ux-01-first-screen'); await shotEl('p8-experience-tile', 'a.life');
  await mapFlow(page, data, 'served page', { shot });

  // ---------- headline builders: small pure functions, tested on made-up records ----------
  const hl = await page.evaluate(() => { const HL = window.__houseHunt.HL, u = (o) => Object.assign({ moments: { sun: {} }, rent: {}, parking: {}, dog: {}, amenities: {}, elevator: {}, evidence: {}, confirm: null, disclosures: [], all_in_lines: [], all_in_unknown: [], tour_questions: [] }, o);
    return {
      cost: HL.cost(u({ all_in: 2710, all_in_lines: [{ line: 'rent (as listed)', amount: 2345 }] })), costStar: HL.cost(u({ all_in: 2710, rent: { basis: 2345, asterisk: true } })), costUnknown: HL.cost(u({ all_in: null })),
      // (D5) a fact that is the open question is not stated as a fact
      bldOpen: HL.building(u({ elevator: { value: 'yes' }, amenities: { gym: 'yes' }, confirm: { asterisk: true, what: 'elevator', why: 'w' } })), dogOpen: HL.dog(u({ dog: { allowed: 'yes', weight_limit_lb: 50 }, confirm: { asterisk: true, what: 'dogs allowed', why: 'w' } })),
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
  // (pass 5) small pure helpers: the rent-terms note in plain words or not at all; a point's bold lead-in or first figure; the street-parking answer in three words; short distances
  { const p5 = await page.evaluate(() => { const x = window.__houseHunt, t = s => String(s).replace(/<[^>]+>/g, '|'); return {
      assumed: t(x.payNote('move-in 2026-12-01 assumed (available now); no free period; rent due on the 1st, first month prorated if move-in is mid-month')), free: t(x.payNote('free-period timing not stated on the page (upfront, end of lease or spread): ask')), internal: x.payNote('1 month(s) free from an assumed date; rent assumed due on the 1st'), plain: t(x.payNote('Due at signing.')), none: x.payNote(null),
      lead: x.ptBody({ lead: 'Parking', text: 'is in a garage.' }), colon: x.ptBody({ text: 'For the dog: a run on site.' }), fig: x.ptBody({ text: 'Your parents are about 72 minutes away.' }), money: x.ptBody({ text: 'About $2,950 a month all in.' }), plainPt: x.ptBody({ text: 'Most places list a garage.' }),
      on: x.parkShort({ local: { parking_rules: [{ rule: 'overnight_parking', summary: 'Overnight parking on the street needs a permit.' }, { rule: 'meter_hours', summary: 'x' }] } }), alt: x.parkShort({ local: { parking_rules: [{ rule: 'alternate_side', summary: 'x' }] } }), nonePark: x.parkShort({ local: {} }),
      d: [x.distShort(400), x.distShort(1700), x.distShort(8000), x.distShort(null)] }; });
    assert.deepStrictEqual(p5, { assumed: '||Counting from a Dec 1, 2026 move-in; a first part-month is charged by the day.|', free: '||Ask when the free month applies.|', internal: '', plain: '||Due at signing.|', none: '',
      lead: '<b>Parking</b> is in a garage.', colon: '<b>For the dog:</b> a run on site.', fig: 'Your parents are about <b>72 minutes</b> away.', money: 'About <b>$2,950 a month</b> all in.', plainPt: 'Most places list a garage.',
      on: 'No overnight parking', alt: 'Street-cleaning days', nonePark: null, d: ['5 min walk', '1.1 miles', '5 miles', null] }); }
  assert.deepStrictEqual(hl, { cost: 'rent $2,345 · total about $2,710', costStar: 'rent $2,345* · total about $2,710', costUnknown: 'not published, ask', bldOpen: 'elevator not confirmed, gym', dogOpen: 'dog policy not confirmed, ask',
    trip: 'about 28 min, $15 in tolls', tripFree: 'about 12 min, no tolls', tripUnk: 'about 40 min, tolls not fully known', tripNone: 'drive time not known',
    park: 'garage, $150 a month', parkFree: 'garage, no monthly charge', parkNoFee: 'garage, fee not published, ask', parkUnk: 'not published, ask',
    dog: 'allowed, weight limit not stated', dog50: 'allowed, up to 50 lb', dogNoLimit: 'allowed, no weight limit', dogUnk: 'not stated, ask',
    bld: 'elevator, gym, pool', bldNone: 'details not published',
    queens: 'closer, cheaper, smaller', queensSame: 'about the same', queensUnk: 'not known yet',
    voices: '3 positive, 1 negative · mostly parking', voicesTopic: 'Parking', voicesNone: 'none found yet',
    rules: 'overnight street parking restricted', rulesPlain: '1 rule on record', rulesNone: 'not found, ask',
    described: '1 description', describedCount: '2 descriptions, from Wikipedia', describedAbbr: '2 descriptions, from Wikipedia and niche.com', describedNone: '',
    confirm: '1 thing to confirm · 2 to ask', confirmRent: '1 thing to confirm', confirmAsk: '1 to ask', confirmNone: 'nothing',
    reviews: '4.2 on Google · 149 reviews, and 2 more sites', reviewsOne: '4.0 on Google · 1 review', reviewsTwo: '4.5 on Google · 20 reviews, and 1 more site',
    reviewsNone: 'No reviews found online', reviewsNotYet: 'Not looked up yet', reviewsMissing: 'Not looked up yet',
    firstLong: 'There is a real night out on foot here, with neighbors your age and a dog run that stays busy until late in the evening.', firstMax: 64,
    dump: ['', 'First month free on a 13-month lease', 'NOW OFFERING 1 MONTH FREE', ''],
    questions: 'nothing flagged', first: 'It has 2.5 miles of beach.' });

  // ---------- an experience: headline, the day (clamped), the figures, the top three, then rows ----------
  const star = data.units.find(u => u.rent.asterisk && u.all_in_gross > u.all_in && hoodBy[u.hood_id]) || data.units.find(u => u.rent.asterisk);
  const y1 = star.year, Y1 = yearBy[y1];
  await page.click(`a.life[href="#exp-${slug(y1)}"]`);
  await page.waitForSelector('.ph1');
  assert.strictEqual(await page.getAttribute('.viewsw [data-v=list]', 'aria-pressed'), 'true');
  assert.strictEqual(await page.locator('#sec-hoods a.hood').count(), Math.min(3, listed(Y1).length));
  // (pass 8) the key facts stay in view: four cells in two rows. The typical RENT, then the typical TOTAL ("about", "with utilities and fees"), each to $10 with
  // its range small beneath ("to" for a screen reader, a dash on screen); then minutes to Mom and Dad, and tolls to the dollar. The counts sit on the button below.
  const money10 = v => '$' + (Math.round(v / 10) * 10).toLocaleString('en-US');
  const strip = await page.evaluate(() => [...document.querySelectorAll('.sec.head #keyfacts > .kfc')].map(c => ({ tag: c.tagName, t: (c.querySelector('.kft') || {}).textContent || '', b: c.querySelector('b').textContent.replace(/\s+/g, ' ').trim(), s: c.querySelector('span').textContent, r: c.querySelector('.rng') ? c.querySelector('.rng').textContent : '', fs: [...c.querySelectorAll('.kft, b, span, .rng, .ab')].map(e => parseFloat(getComputedStyle(e).fontSize)), sLines: Math.round(c.querySelector('span').getBoundingClientRect().height / parseFloat(getComputedStyle(c.querySelector('span')).lineHeight)), x: Math.round(c.getBoundingClientRect().left), y: Math.round(c.getBoundingClientRect().top) })));
  assert.strictEqual(strip.length, 4, 'a four-cell strip: rent, total, the drive, tolls'); assert.strictEqual(await page.locator('#view [role=button]').count(), 0, 'no div dressed as a button');
  strip.forEach(c => assert(c.fs.every(f => f >= 13), 'nothing in the strip is under 13 px: ' + c.fs));
  { const us = unitsOfYear(Y1), f = figsOf(us);
    assert.strictEqual(strip[0].t.trim(), 'typical rent'); assert.strictEqual(strip[0].b, money10(f.rent), 'the strip shows the median rent of the apartments shown, to the nearest $10'); assert.strictEqual(strip[0].tag, 'DIV');
    assert.strictEqual(strip[1].t.trim(), 'typical total'); assert.strictEqual(strip[1].b, 'about ' + money10(f.total), 'and the median total, said with "about"'); assert.strictEqual(strip[1].s, WITH_UF); assert.strictEqual(strip[1].tag, 'BUTTON');
    if (Y1.medians.all_in != null) assert.strictEqual(money10(f.total), money10(Y1.medians.all_in), 'the median total is the stored one');
    if (money10(f.rr[0]) !== money10(f.rr[1])) assert.strictEqual(strip[0].r, money10(f.rr[0]) + ' to –' + money10(f.rr[1]), 'the rent range small beneath');
    if (money10(f.tr[0]) !== money10(f.tr[1])) assert.strictEqual(strip[1].r, money10(f.tr[0]) + ' to –' + money10(f.tr[1]), 'the total range small beneath (a dash on screen, "to" for a screen reader)');
    assert(strip[1].sLines <= 2, '"with utilities and fees" takes two lines at most in its cell: ' + strip[1].sLines);
    if (W < 700) assert(strip[0].y === strip[1].y && strip[0].x < strip[1].x && strip[2].y > strip[0].y, 'rent and total side by side, rent first; the drive and tolls beneath'); }
  strip.splice(0, 1); // from here on: [total, drive, tolls]
  strip.forEach(c => assert(c.fs.every(f => f >= 13), 'nothing in the strip is under 13 px: ' + c.fs));
  if (Y1.all_in_range && money10(Y1.all_in_range[0]) !== money10(Y1.all_in_range[1])) assert.strictEqual(strip[0].r, money10(Y1.all_in_range[0]) + ' to –' + money10(Y1.all_in_range[1]), 'with the range small beneath (a dash on screen, "to" for a screen reader)');
  if (Y1.medians.drive_min != null) { assert.strictEqual(strip[1].b, Math.round(Y1.medians.drive_min) + ' min'); assert.strictEqual(strip[1].s, 'drive to Mom and Dad'); assert(!strip[1].r || /^\d+ to –\d+ min$/.test(strip[1].r), strip[1].r); }
  { const tl = Y1.medians.toll_round_trip; if (tl > 0) { assert.strictEqual(strip[2].b, tl < 1 ? 'under $1' : '$' + Math.round(tl), 'tolls to the dollar'); assert.strictEqual(strip[2].s, 'tolls, round trip'); assert.strictEqual(strip[2].tag, 'BUTTON');
      // "NY E-ZPass" is explained on a tap; the sheet holds the focus while it is open
      await page.click('#keyfacts .kfc[data-act="toll-info"]'); await page.waitForSelector('#sheet.open'); const sh = await page.textContent('#sheetBody'); assert(/New York E-ZPass/.test(sh) && /tag/.test(sh), 'the sheet says what an E-ZPass is: ' + sh.slice(0, 120));
      assert(await page.evaluate(() => document.getElementById('view').inert && document.getElementById('tray').inert), 'the page behind the sheet is inert'); await page.keyboard.press('Escape'); await page.waitForFunction(() => !document.getElementById('sheet').classList.contains('open'));
      assert(await page.evaluate(() => !document.getElementById('view').inert && document.activeElement && document.activeElement.getAttribute('data-act') === 'toll-info'), 'Escape closes it and focus returns to the cell'); }
    else if (tl === 0) assert.strictEqual(strip[2].b, 'No tolls'); }
  await page.click('#keyfacts .kfc[data-act="allin-info"]'); await page.waitForSelector('#sheet.open'); { const sb = await page.textContent('#sheetBody'); assert(sb.includes(L_TOTAL) && sb.includes('Rent is what the listing asks. The total adds fees, parking, pet rent and our estimate of electricity, gas and internet.') && /never counted as \$0/.test(sb), 'the total is explained on a tap: ' + sb.slice(0, 200)); } await page.click('#shClose');
  // "About this experience": the text whole, a lead and a short list, under its own title; no host label, no clamp, no "more"
  assert.strictEqual(await page.locator('#view .host, #view .who, #view .clampw, #view [data-act=unclamp]').count(), 0, 'no host box and nothing clamped'); assert(!/your host/i.test(await page.evaluate(() => document.getElementById('view').textContent)), 'no "Your host says"');
  if (Y1.host && Y1.host.intro) { const ab = await page.evaluate(() => { const s = document.getElementById('about'); return { h2: s.querySelector('h2').textContent, lead: (s.querySelector('.lead2') || {}).textContent || '', pts: [...s.querySelectorAll('.pts li, .catchb p')].map(li => li.textContent), icons: s.querySelectorAll('.pts li svg, .catchb svg').length, nCatch: s.querySelectorAll('.catchb').length, nCatchP: s.querySelectorAll('.catchb p').length, catchLabel: (s.querySelector('.catchb .ctl') || {}).textContent || '', bold: s.querySelectorAll('.pts li b, .catchb p b').length, cut: [...s.querySelectorAll('*')].filter(e => e.scrollHeight > e.clientHeight + 2 && getComputedStyle(e).overflow !== 'visible').length }; });
    assert.strictEqual(ab.h2, 'About this experience'); assert.strictEqual(ab.cut, 0, 'nothing in it is cut');
    const apAll = (Y1.about_points || []).map(p => typeof p === 'string' ? { text: p } : p).filter(p => p && p.text), ap = apAll.filter(p => p.icon !== 'warning').concat(apAll.filter(p => p.icon === 'warning')).map(p => p.text), want = (await page.evaluate(x => window.__houseHunt.sentences(x), Y1.host.intro)).concat(ap), got = [ab.lead].concat(ab.pts).join(' ').replace(/\s+/g, ' ').trim();
    if (!want.some(s => CRIME.test(s))) assert.strictEqual(got, want.join(' '), 'the whole text is there, once: the lead, then the points');
    assert(ab.pts.length >= 1 && ab.icons === ab.pts.length - ab.nCatchP + ab.nCatch, 'the rest is a short list, each line with its mark: ' + ab.pts.length);
    // the catch (the point marked "warning") stands apart under its own label, last; figures in the points are in bold so the list can be scanned
    if (apAll.some(p => p.icon === 'warning')) { assert.strictEqual(ab.nCatch, 1, 'one catch box'); assert.strictEqual(ab.catchLabel, 'The catch'); assert.strictEqual(ab.nCatchP, apAll.filter(p => p.icon === 'warning').length); }
    if (apAll.some(p => /\$\d|\d+ (minutes|percent|square feet|places|miles)/.test(p.text))) assert(ab.bold >= 1, 'a figure in a point is in bold'); assert(ab.lead.length >= 60, 'the lead is something to read: ' + ab.lead); }
  // the way on sits right under the key facts, above the About text
  { const b = await page.evaluate(() => { const e = document.getElementById('see-hoods'), k = document.querySelector('.sec.head #keyfacts'), a = document.getElementById('about'), tr = document.getElementById('trail'); return { text: e.textContent.trim(), top: e.getBoundingClientRect().top, bottom: Math.round(e.getBoundingClientRect().bottom + window.scrollY - tr.offsetHeight), strip: k.getBoundingClientRect().bottom, about: a ? a.getBoundingClientRect().top : 1e9 }; });
    assert(b.text.startsWith('See the ' + listed(Y1).length + (listed(Y1).length === 1 ? ' neighborhood' : ' neighborhoods') + ' ↓'), b.text); assert(/\d+ apartments? to see$/.test(b.text), 'the count of places rides on the button: ' + b.text); assert(b.strip <= b.top && b.top < b.about, 'under the strip, above About');
    if (W === 390) assert(b.bottom + 58 <= 0.7 * SCREEN, 'and within the first 0.7 of a screen, the top line included (pass 8: the key facts are two rows, rent and total above the drive and tolls): ' + b.bottom);
    assert(await page.evaluate(() => { const f = document.querySelector('.seerow #filterBtn'), s = document.getElementById('see-hoods'); return !!f && Math.abs(f.getBoundingClientRect().top - s.getBoundingClientRect().top) < 4 && f.getBoundingClientRect().height >= 44 && f.getBoundingClientRect().right <= innerWidth; }), 'the Filter button sits beside "See the neighborhoods"'); console.log('experience: "See the neighborhoods" ends at', b.bottom, 'px');
    await page.click('#see-hoods'); const y = await page.evaluate(() => document.getElementById('sec-hoods').getBoundingClientRect().top); assert(y >= 0 && y < 160, 'it scrolls to the list: ' + Math.round(y)); assert.strictEqual(await page.evaluate(() => document.activeElement && document.activeElement.tagName + '|' + document.activeElement.closest('section').id), 'H2|sec-hoods', 'and focus follows to the list heading'); await page.evaluate(() => window.scrollTo(0, 0)); }
  if (illus) assert(await page.evaluate(() => { const i = document.querySelector('#view .illus.banner'), h = document.querySelector('.ph1'); return !!i && i.querySelectorAll('svg').length === 1 && i.getBoundingClientRect().bottom <= h.getBoundingClientRect().top; }), 'the drawing (the banner crop, about 100 px) sits at the top of the experience page'); else assert.strictEqual(await page.locator('#view .illus').count(), 0);
  // a day in this experience: three titled moments from the walkthrough, and nothing that the About text already said
  // (pass 5) they are in the open, as a storyboard: three cards side by side that scroll sideways, each with its number, icon and title
  if (Y1.host && (Y1.host.walkthrough || []).length) { const dm = await page.evaluate(() => [...document.querySelectorAll('#sec-day .scene')].map(d => ({ t: d.querySelector('h3').textContent.trim(), p: d.querySelector('p:last-of-type').textContent, n: (d.getAttribute('aria-label') || '').split(':')[0], icon: d.querySelectorAll('.sci svg').length, w: d.getBoundingClientRect().width })));
    const st = await page.evaluate(() => { const s = document.querySelector('#sec-day .story'), a = document.getElementById('about'), h = document.getElementById('sec-hoods'); return { scroll: s.scrollWidth > s.clientWidth, tab: s.tabIndex, order: a.getBoundingClientRect().top < s.getBoundingClientRect().top && s.getBoundingClientRect().top < h.getBoundingClientRect().top, h: Math.round(s.getBoundingClientRect().height) }; });
    assert(st.order, 'About, then the day, then the neighborhoods'); assert(dm.length < 2 || st.scroll, 'the cards scroll sideways'); assert.strictEqual(st.tab, 0, 'and the strip of cards can be reached by keyboard'); assert(dm.every((d, i) => d.icon === 1 && d.n === (i + 1) + ' of ' + dm.length), 'each card is numbered and has its icon');
    assert(dm.every(d => d.w <= W * 0.86), 'the next card peeks in: ' + dm.map(d => Math.round(d.w))); if (W === 390) assert(st.h <= 330, 'a compact strip: ' + st.h);
    assert.deepStrictEqual(dm.map(d => d.t), (Y1.day_moments || []).length ? Y1.day_moments.map(m => m.title) : ['A weekday', 'Saturday night', 'Sunday with Mom and Dad'].slice(0, Y1.host.walkthrough.length));
    const about = await page.textContent('#about'), sents = await page.evaluate(x => window.__houseHunt.sentences(x), Y1.host.intro || '');
    for (const s of sents) if (s.length > 30) assert(!(await page.textContent('#sec-day')).includes(s), 'the day repeats nothing from the About text: ' + s);
    const all = await page.evaluate(() => document.getElementById('view').textContent); for (const d of dm) { const s = d.p.slice(0, 60); assert.strictEqual(all.split(s).length - 1, 1, 'each passage appears once on the page: ' + s); }
    // (pass 6) the sideways scroll is obvious and can be worked without a swipe: a count, two arrow buttons of 44 px, dots, the arrow keys, snap; the page itself never scrolls sideways
    if (dm.length > 1) { const sv = () => page.evaluate(() => { const s = document.getElementById('story'), bs = [...document.querySelectorAll('#storynav .snb')], cs = [...s.children], sr = s.getBoundingClientRect();
        return { count: document.getElementById('story-count').textContent.trim(), dots: [...document.querySelectorAll('#sec-day .sdots i')].map(d => d.className === 'on'), btn: bs.map(b => { const r = b.getBoundingClientRect(); return { w: Math.round(r.width), h: Math.round(r.height), off: b.disabled, label: b.getAttribute('aria-label') }; }),
          snap: getComputedStyle(s).scrollSnapType, left: Math.round(s.scrollLeft), peek: cs[1] ? Math.round(sr.right - cs[1].getBoundingClientRect().left) : 0, firstLeft: Math.round(cs[0].getBoundingClientRect().left), pageX: window.scrollX, sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, role: s.getAttribute('aria-roledescription') }; });
      const settle = async want => { await page.waitForFunction(w => document.getElementById('story-count').textContent.trim() === w, want, { timeout: 4000 }); await page.waitForTimeout(450); };
      let s0 = await sv(); assert.strictEqual(s0.count, '1 of ' + dm.length); assert.deepStrictEqual(s0.dots, dm.map((d, i) => i === 0), 'the first dot is on'); assert(s0.btn.length === 2 && s0.btn.every(b => b.w >= 44 && b.h >= 44), 'two arrow buttons of at least 44 px: ' + JSON.stringify(s0.btn));
      assert(s0.btn[0].off && !s0.btn[1].off, 'Previous is off on the first card'); assert.deepStrictEqual(s0.btn.map(b => b.label), ['Previous moment', 'Next moment']); assert(/x mandatory/.test(s0.snap), 'the strip snaps: ' + s0.snap); assert(s0.peek >= 24, 'the next card peeks in by ' + s0.peek + 'px'); assert.strictEqual(s0.role, 'carousel');
      await page.click('#storynav .snb >> nth=1'); await settle('2 of ' + dm.length); let s1 = await sv(); assert(s1.left > 100, 'Next moves the strip: ' + s1.left); assert.deepStrictEqual(s1.dots, dm.map((d, i) => i === 1)); assert(!s1.btn[0].off, 'Previous is live on the second card');
      assert.strictEqual(s1.pageX, 0, 'the page itself did not move sideways'); assert(s1.sw <= s1.cw, 'and has no sideways scroll: ' + s1.sw + ' > ' + s1.cw);
      await page.focus('#story'); for (let i = 2; i < dm.length; i++) { await page.keyboard.press('ArrowRight'); await settle((i + 1) + ' of ' + dm.length); } let s2 = await sv(); assert(s2.btn[1].off, 'Next is off on the last card'); assert.deepStrictEqual(s2.dots, dm.map((d, i) => i === dm.length - 1));
      await page.keyboard.press('ArrowLeft'); await settle((dm.length - 1) + ' of ' + dm.length); await page.keyboard.press('Home'); await settle('1 of ' + dm.length); s2 = await sv(); assert.strictEqual(s2.left, 0, 'Home goes back to the first card'); assert.strictEqual(s2.pageX, 0);
      // a vertical wheel or swipe over the strip still scrolls the page: the strip traps nothing
      { const y0 = await page.evaluate(() => { document.getElementById('story').scrollIntoView({ block: 'center' }); return window.scrollY; }); const bx = await page.locator('#story').boundingBox(); await page.mouse.move(bx.x + bx.width / 2, bx.y + bx.height / 2); await page.mouse.wheel(0, 300); await page.waitForTimeout(250);
        assert((await page.evaluate(() => window.scrollY)) > y0, 'the page scrolls down with the pointer over the strip'); await page.evaluate(() => window.scrollTo(0, 0)); } } }
  { await page.click('[data-act=rows-all]'); const t = await page.evaluate(() => document.getElementById('view').textContent); assert(!/by mail/i.test(t) && !/a 8-minute|a 11-minute|a 18-minute/.test(t) && !/,,/.test(t) && !/typical place is/.test(t), 'no by-mail toll figure and no "a 8-minute" anywhere on the experience, rows open'); await page.click('[data-act=rows-all]'); }
  // the story order of the page: drawing, title, key facts, the way on, About, the day, the neighborhoods, then the rows
  { const ys = await page.evaluate(() => ['.ph1', '#keyfacts', '#see-hoods', '#about', '#sec-day', '#sec-hoods', '#sec-rows'].map(s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().top + window.scrollY) : null; }).filter(v => v != null)); assert.deepStrictEqual(ys, ys.slice().sort((a, b) => a - b), 'in story order: ' + ys);
    const sizes = await page.evaluate(() => [...new Set([...document.querySelectorAll('#view .pg p, #view .pg li, #view .pg small, #view .pg b, #view .pg span, #view .pg h2, #view .pg h3')].filter(e => e.getClientRects().length && e.textContent.trim() && !e.closest('svg') && !e.closest('.rb') && !e.closest('.hhmap')).map(e => parseFloat(getComputedStyle(e).fontSize)))].sort((a, b) => a - b)); assert(sizes[0] >= 12.5, 'nothing on the page is under 12.5 px: ' + sizes); console.log('experience: text sizes in the open', sizes.join(', ')); }
  assert.strictEqual(await page.locator('#view details.rowd[open]').count(), 0, 'no row starts open');
  const nRows = await page.locator('#sec-rows details.rowd').count(); assert(nRows >= 3 && nRows <= 7, 'three to seven rows on an experience: ' + nRows);
  assert((await page.textContent('#r-queens .rl')).trim() === 'Compared to staying in Queens');
  assert.strictEqual(await page.locator('#r-queens button.pt').count(), data.meta.queens_spectrum.filter(s => !/crime/.test(s.measure)).length, 'the scale leaves crime out');
  assert.strictEqual(await headOf('r-cost'), await page.evaluate(id => window.__houseHunt.headline('year', id, 'yearCost'), y1));
  // a neighborhood card: name, rank, one line, three facts
  const card = await page.evaluate(() => { const a = document.querySelector('#sec-hoods a.hood'); return { chips: a.querySelectorAll('.chip').length, kids: [...a.children].map(c => c.className), h: Math.round(a.getBoundingClientRect().height) }; });
  assert(card.chips >= 1 && card.chips <= 2, 'a neighborhood card has the pair of prices and one or two facts: ' + card.chips); assert(card.kids.every(k => /^(hd|hsub|l2|pp card|chips|safest)$/.test(k)) && card.kids.includes('pp card'), 'and nothing else: ' + card.kids);
  // (pass 8) every neighborhood card carries both prices: the typical rent (the median of its apartments' rents) first and larger, the typical total beside it
  { const cards = await page.evaluate(() => [...document.querySelectorAll('#sec-hoods a.hood')].map(a => { const p = a.querySelector('.pp'); return { href: a.getAttribute('href'), rl: p.querySelector('.pp-r .pp-l').textContent, r: p.querySelector('.pp-r b').textContent, tl: p.querySelector('.pp-t .pp-l').textContent, t: p.querySelector('.pp-t b').textContent.replace(/\s+/g, ' ').trim(), uf: p.querySelector('.uf').textContent, fsR: parseFloat(getComputedStyle(p.querySelector('.pp-r b')).fontSize), fsT: parseFloat(getComputedStyle(p.querySelector('.pp-t b')).fontSize) }; }));
    for (const c of cards) { const h = listed(Y1).find(x => '#hood-' + slug(x.id) === c.href), f = figsOf(unitsOfHood(h)), typ = f.n > 1;
      assert.strictEqual(c.rl, typ ? 'Typical rent' : L_RENT); assert.strictEqual(c.r.replace('*', ''), typ ? money10(f.rent) : moneyX(f.rent), 'the card shows the median rent: ' + h.name); assert.strictEqual(c.tl, typ ? 'Typical total' : 'Total'); assert.strictEqual(c.t, 'about ' + money10(f.total)); assert.strictEqual(c.uf, WITH_UF); assert(c.fsR > c.fsT, 'rent is the larger figure'); }
    assert.deepStrictEqual(await barePrices('#sec-hoods a.hood'), [], 'no unnamed price on a neighborhood card'); }
  { const c3 = await page.evaluate(() => [...document.querySelectorAll('#sec-hoods a.hood')].slice(0, 3).map(a => ({ name: a.querySelector('h3').textContent, pick: (a.querySelector('.pick') || {}).textContent || '', line: (a.querySelector('.l2') || {}).textContent || '', lines: a.querySelector('.l2') ? a.querySelector('.l2').clientHeight / parseFloat(getComputedStyle(a.querySelector('.l2')).lineHeight) : 0, small: [...a.querySelectorAll('.chip small')].filter(e => e.scrollWidth > e.clientWidth + 1).length })));
    // the badge goes to the first card, unless that neighborhood rests on one building that still has something to confirm (single_building)
    { const h0 = listed(Y1)[0], b0 = h0 && h0.single_building ? data.units.filter(u => u.hood_id === h0.id) : []; const solo = !!(h0 && h0.single_building && new Set(b0.map(u => u.building_id)).size === 1);
      if (!solo) assert.strictEqual(c3[0].pick, 'Top pick', 'the first card carries the badge'); else assert(c3[0].pick === '' || c3[0].pick === 'Top pick', c3[0].pick); } c3.forEach(c => { assert(c.line.length >= 12 && c.lines <= 2.1 && /[.!?]$/.test(c.line.trim()), 'a top-three card is compact: one sentence, two lines at most: ' + c.name + ': ' + c.lines + ' ' + c.line); assert.strictEqual(c.small, 0, 'no fact label is cut: ' + c.name); }); }
  await noCrime('experience ' + y1); await overflow('year'); await small('year');
  await shot('02-year', true); await shot('ux-02-experience-collapsed'); await shotEl('p8-experience-strip', '.sec.head'); await shotEl('p8-neighborhood-card', '#sec-hoods a.hood'); await page.evaluate(() => window.scrollTo(0, 0));
  await openRow('r-cost'); assert((await page.textContent('#r-cost .allin')).startsWith('Rent is what the listing asks. The total adds fees'), 'one plain sentence says what the two prices are');
  { const cf = await page.evaluate(() => [...document.querySelectorAll('#cost-figs > div')].map(d => d.innerText.replace(/\s+/g, ' ').trim())); assert(cf.length === 2 && /rent/.test(cf[0]) && /^about \$/.test(cf[1]) && /total with utilities and fees/.test(cf[1]), 'the row shows the typical rent and the typical total: ' + cf.join(' | ')); }
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
    assert(sb.t.startsWith('See the ' + nb + (nb === 1 ? ' building' : ' buildings') + ' ↓'), sb.t); assert(sb.t.endsWith(h.counts.shown + (h.counts.shown === 1 ? ' apartment' : ' apartments')), 'the count of apartments rides on the button: ' + sb.t);
    assert(sb.above, '"See the places" is above the About text'); if (W === 390) assert(sb.bottom + 58 <= 0.7 * SCREEN, 'and in the first 0.7 of a screen: ' + sb.bottom);
    // (pass 5) the neighborhood's story order: its experience marker and rank, name, where, three key facts, the way on, About, At a glance, one pull quote, the buildings, then the rows
    const hp = await page.evaluate(() => { const y = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().top + window.scrollY) : null; };
      return { ys: ['#hood-rank', '.ph1', '#hood-where', '#keyfacts', '#see-places', '#about', '#sec-glance', '#pull', '#sec-places', '#sec-rows'].map(y).filter(v => v != null), kick: document.getElementById('hood-rank').textContent.trim(), mark: document.querySelectorAll('#hood-rank svg.ymk').length,
        cells: [...document.querySelectorAll('#keyfacts > .kfc')].map(c => ({ tag: c.tagName, t: (c.querySelector('.kft') || {}).textContent || '', b: c.querySelector('b').textContent.replace(/\s+/g, ' ').trim(), s: c.querySelector('span').textContent, r: (c.querySelector('.rng') || {}).textContent || '', sLines: Math.round(c.querySelector('span').getBoundingClientRect().height / parseFloat(getComputedStyle(c.querySelector('span')).lineHeight)) })),
        glance: [...document.querySelectorAll('#sec-glance .glance li')].map(li => ({ b: li.querySelector('b').textContent, s: li.querySelector('small').textContent, icon: li.querySelectorAll('svg').length, btn: !!li.querySelector('button') })), pull: document.getElementById('pull') ? { q: document.querySelector('#pull blockquote').textContent, src: document.querySelector('#pull figcaption').textContent, fs: parseFloat(getComputedStyle(document.querySelector('#pull blockquote')).fontSize) } : null,
        described: document.getElementById('sec-described') ? document.querySelectorAll('#sec-described .quote').length : 0, fake: document.querySelectorAll('#view [role=button]').length }; });
    assert.deepStrictEqual(hp.ys, hp.ys.slice().sort((a, b) => a - b), 'in story order: ' + hp.ys); assert.strictEqual(hp.mark, 1, 'the experience marker leads the top line'); assert(hp.kick.endsWith(yearBy[h.year].display_label || yearBy[h.year].label), 'which names the experience: ' + hp.kick); assert.strictEqual(hp.fake, 0);
    // (pass 8) four key facts: the rent (typical = the median of the apartments' rents, with its range), the total ("about", "with utilities and fees"), the drive, tolls
    assert.strictEqual(hp.cells.length, 4, 'four key facts: rent, total, the drive, tolls'); const us = data.units.filter(u => u.hood_id === h.id), f8 = figsOf(us), costs = us.map(u => u.all_in).filter(v => v != null).sort((a, b) => a - b);
    assert.strictEqual(hp.cells[0].t.trim(), us.length > 1 ? 'typical rent' : 'rent'); assert.strictEqual(hp.cells[0].b, us.length > 1 ? money10(f8.rent) : moneyX(f8.rent), 'the rent: the median to $10, or the one apartment\'s rent to the dollar');
    assert.strictEqual(hp.cells[1].t.trim(), us.length > 1 ? 'typical total' : 'total'); assert.strictEqual(hp.cells[1].b, 'about ' + money10(f8.total), 'the total, with "about"'); assert.strictEqual(hp.cells[1].s, WITH_UF); assert(hp.cells[1].sLines <= 2, '"with utilities and fees" in two lines at most: ' + hp.cells[1].sLines);
    if (us.length > 1) { if (money10(f8.rr[0]) !== money10(f8.rr[1])) assert.strictEqual(hp.cells[0].r, money10(f8.rr[0]) + ' to –' + money10(f8.rr[1]), 'the rent range reads as a range'); if (money10(costs[0]) !== money10(costs[costs.length - 1])) assert.strictEqual(hp.cells[1].r, money10(costs[0]) + ' to –' + money10(costs[costs.length - 1]), 'the total range reads as a range'); }
    else { assert.strictEqual(hp.cells[0].r, ''); assert.strictEqual(hp.cells[1].r, ''); }
    hp.cells.splice(0, 1); // from here on: [total, drive, tolls]
    if (h.drive_min != null) { assert.strictEqual(hp.cells[1].b, Math.round(h.drive_min) + ' min'); assert.strictEqual(hp.cells[1].s, 'drive to Mom and Dad'); }
    if (h.toll_round_trip > 0) { assert.strictEqual(hp.cells[2].b, h.toll_round_trip < 1 ? 'under $1' : '$' + Math.round(h.toll_round_trip), 'tolls to the dollar'); assert.strictEqual(hp.cells[2].tag, 'BUTTON', 'the toll cell opens the E-ZPass explanation'); } else if (h.toll_round_trip === 0) assert.strictEqual(hp.cells[2].b, 'No tolls');
    // At a glance: icon facts, never sentences; the street-parking fact is last and opens Local rules
    if (!(h.at_a_glance || []).length) { const tr = h.traits || {}, want = (tr.restaurants_800m != null) + (tr.park_walk_min != null) + (tr.dog_park_m != null) + (tr.supermarket_m_c != null) + (h.transit_min != null) + 1; assert.strictEqual(hp.glance.length, want, 'one fact per figure the data has, and street parking: ' + hp.glance.length);
      assert(hp.glance.every(g => g.icon === 1 && g.b.length <= 30 && !/\.$/.test(g.b)), 'short icon facts: ' + hp.glance.map(g => g.b).join(' | ')); const last = hp.glance[hp.glance.length - 1]; assert(last.s === 'street parking' && last.btn && last.b.split(' ').length <= 3, 'street parking in three words or fewer: ' + last.b);
      if (tr.restaurants_800m != null) assert(hp.glance[0].b.startsWith(Math.round(tr.restaurants_800m) + ' restaurant'), hp.glance[0].b); }
    // one outside description is set as a pull quote with its source; the others wait in their row, and none is shown twice
    { const ds = (h.described || []).filter(d => d && (d.quote || d.text || d.excerpt)); if (hp.pull) { assert(ds.some(d => String(d.quote || d.text || d.excerpt).replace(/\s+/g, ' ').trim() === hp.pull.q), 'the pull quote is one of the descriptions, whole'); assert(hp.pull.q.length <= 240 && hp.pull.src.trim().length > 0 && !CRIME.test(hp.pull.q)); assert.strictEqual(hp.described, ds.length - 1, 'the rest are in the row'); }
      else assert.strictEqual(hp.described, ds.length); } }
  // the street-parking fact of a neighborhood with an overnight rule says so, and tapping it opens Local rules
  { const hOn = shownHoods.find(x => (x.local.parking_rules || []).some(r => r.rule === 'overnight_parking' && /\bbanned\b|not allowed|needs (a|the) permit|permit-only|may not park|overnight (parking )?permit|all-night parking restrictions/i.test(r.summary || '')));
    if (hOn) { await go('#hood-' + slug(hOn.id)); assert.strictEqual((await page.textContent('#sec-glance li:last-child b')).trim(), 'No overnight parking'); await page.click('#sec-glance li:last-child button'); await page.waitForFunction(() => document.getElementById('r-rules').open); await shot('p5-after-hood-overnight-rule'); } }
  await go('#hood-' + slug(hRich.id)); await small('hood'); await shot('03-neighborhood', true); await shot('ux-03-neighborhood-collapsed'); await shotEl('p8-neighborhood-strip', '.sec.head'); await shotEl('p8-building-card', '#sec-places article.bcard'); await page.evaluate(() => window.scrollTo(0, 0));
  await openRow('r-voices'); await page.evaluate(() => document.getElementById('r-voices').scrollIntoView({ block: 'start' })); await page.evaluate(() => window.scrollBy(0, -70)); await shot('ux-03b-neighborhood-residents-open');
  // a building card: name, from-price, how many apartments, one line, three facts, and the asterisk only when every apartment there shares it
  await go('#hood-' + slug(hStar.id)); await showAll();
  { const bs = bOf(hStar.id), cards = await page.evaluate(() => [...document.querySelectorAll('#sec-places article.bcard')].map(a => ({ href: a.querySelector('a').getAttribute('href'), name: a.querySelector('h3').textContent, sub: (a.querySelector('.hd small') || {}).textContent || '', chips: [...a.querySelectorAll('.chip b')].map(b => b.textContent), pp: (p => ({ rl: p.querySelector('.pp-r .pp-l').textContent, r: p.querySelector('.pp-r b').textContent, tl: p.querySelector('.pp-t .pp-l').textContent, t: p.querySelector('.pp-t b').textContent.replace(/\s+/g, ' ').trim(), uf: p.querySelector('.uf').textContent, note: ((p.querySelector('.pp-n') || {}).textContent || '').replace(/\u00a0/g, ' '), fsR: parseFloat(getComputedStyle(p.querySelector('.pp-r b')).fontSize), fsT: parseFloat(getComputedStyle(p.querySelector('.pp-t b')).fontSize), below: p.querySelector('.pp-t').getBoundingClientRect().top >= p.querySelector('.pp-r').getBoundingClientRect().top - 1, small: [...p.querySelectorAll('*')].filter(e => e.children.length === 0 && e.textContent.trim()).map(e => parseFloat(getComputedStyle(e).fontSize)).sort((x, y) => x - y)[0] }))(a.querySelector('.pp')), cutChips: [...a.querySelectorAll('.chip b, .chip small')].filter(e => e.scrollWidth > e.clientWidth + 1).length, star: a.querySelectorAll('.confl').length, other: a.querySelectorAll('button, .gtk, .rentl, .host').length })));
    assert.strictEqual(cards.length, bs.length, 'one card per building');
    const offer = await page.evaluate(ids => Object.fromEntries(ids.map(id => [id, window.__houseHunt.offerLine(id)])), bs.flatMap(b => b.units.map(u => u.id)));
    cards.forEach((c, i) => { const us = bs[i].units, from = Math.min(...us.map(u => u.all_in)), rs = u => u.rent.asterisk || u.rent.basis_kind === 'net_effective';
      assert.strictEqual(c.href, '#bldg-' + bSlug(us[0])); assert.strictEqual(c.chips.length, 2, 'the pair of prices, then two facts'); assert.strictEqual(c.cutChips, 0, 'no fact is cut on ' + c.name); assert.strictEqual(c.other, 0, 'nothing else on the card');
      // (pass 8) "Rent from $X" and "about $Y with utilities and fees": both are the figures of ONE apartment, the one with the lowest total, and the card says which
      { const fu = us.slice().sort((a, b) => a.all_in - b.all_in)[0], same = us.every(u => u.all_in === us[0].all_in && rentOf(u) === rentOf(us[0]) && rs(u) === rs(us[0]));
        assert.strictEqual(c.pp.rl, us.length > 1 && !same ? 'Rent from' : L_RENT); assert.strictEqual(c.pp.r, moneyX(rentOf(fu)) + (rs(fu) ? '*' : ''), 'the rent of the apartment with the lowest total, to the dollar, the offer star on the rent: ' + c.pp.r);
        assert.strictEqual(c.pp.tl, 'Total'); assert.strictEqual(c.pp.t, 'about ' + money10(from), 'that same apartment\'s total, to $10, with "about": ' + c.pp.t); assert.strictEqual(c.pp.uf, WITH_UF);
        assert(c.pp.fsR > c.pp.fsT && c.pp.below && c.pp.small >= 12.5, 'rent first and larger; nothing under 12.5 px');
        if (us.length > 1) assert(same ? /^The same for (both|all \d+) apartments here$/.test(c.pp.note) : c.pp.note === 'Both for ' + (fu.unit ? 'Apartment ' + fu.unit : '') + ', the lowest total of the ' + us.length + ' here', 'the card says both figures belong to one apartment: ' + c.pp.note); }
      if (us.length > 1) assert(c.sub.includes(us.length + ' apartments'), 'how many apartments made the list: ' + c.sub);
      const sig = u => (u.confirm.asterisk ? String(u.confirm.what) : '') + '|' + (rs(u) ? 'r' + offer[u.id] : ''), shared = us.every(u => sig(u) === sig(us[0])) && sig(us[0]) !== '|';
      assert.strictEqual(c.star, shared ? 1 : 0, 'one asterisk line when every apartment shares it, none otherwise: ' + c.name); }); }
  // the avoid cards, the phone-call list and the not-re-checked list sit in their own rows
  await go('#hood-' + slug(hAvoid.id)); assert((await headOf('sec-avoid')).startsWith(hAvoid.counts.avoid + (hAvoid.counts.avoid === 1 ? ' apartment ' : ' apartments ')));
  assert(await page.isHidden('.unit.avoid'), 'avoid cards start closed'); await openRow('sec-avoid');
  assert.strictEqual(await page.locator('.unit.avoid').count(), hAvoid.counts.avoid); await overflow('hood avoid open');
  await page.evaluate(() => document.getElementById('sec-avoid').scrollIntoView()); await page.evaluate(() => window.scrollBy(0, -70)); await shot('03b-neighborhood-avoid-card');
  const hHeld = shownHoods.find(h => h.counts.held > 0);
  if (hHeld) { await go('#hood-' + slug(hHeld.id)); await openRow('sec-call');
    assert.strictEqual(await page.locator('#sec-call .callitem').count(), hHeld.counts.held); assert.strictEqual(await page.locator('#sec-call [data-act=save]').count(), 0);
    assert((await page.textContent('#sec-call > summary')).includes('two questions')); await overflow('hood-held');
    await page.evaluate(() => document.getElementById('sec-call').scrollIntoView()); await page.evaluate(() => window.scrollBy(0, -70)); await shot('03c-worth-a-phone-call'); }
  const known = new Set([...data.held, ...data.units, ...data.avoid].map(u => u.id)), hoodIds = new Set(data.neighborhoods.map(h => h.id));
  // (pass 6, owner decision) there is no "not re-checked" list any more: whatever the data still carries under awaiting_live_check is not shown, and no page says "re-checked"
  { const hw = (data.awaiting_live_check || []).map(a => a.hood_id).find(id => hoodIds.has(id) && yearBy[hoodBy[id].year] && hoodBy[id].unit_ids.length) || shownHoods[0].id; await go('#hood-' + slug(hw)); await page.click('[data-act=rows-all]');
    const t = await page.evaluate(() => document.getElementById('view').textContent + document.getElementById('foot').textContent); assert.strictEqual(await page.locator('#sec-wait, #wait-box').count(), 0, 'no "Not re-checked yet" row'); assert(!/re-checked|not seen live|live check/i.test(t), 'no "re-checked" wording on the page'); await page.click('[data-act=rows-all]'); }
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
    await go('#bldg-' + bSlug(u), '.bpage'); await fits(bUnits(u).length > 2 ? 'building, many' : 'building', tag + ' (' + (u.building || u.address) + ')'); await noCrime('building ' + tag); await overflow('building ' + tag);
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
        saves: [...document.querySelectorAll('.savb')].map(b => b.textContent.trim()), host: document.querySelectorAll('#view .host, #view .who, #view .clampw').length, sign: document.querySelectorAll('.bpage .sign').length,
        pp: (p => p ? { rl: p.querySelector('.pp-r .pp-l').textContent, r: p.querySelector('.pp-r b').textContent, tl: p.querySelector('.pp-t .pp-l').textContent, t: p.querySelector('.pp-t b').textContent.replace(/\s+/g, ' ').trim(), uf: p.querySelector('.uf').textContent, note: ((p.querySelector('.pp-n') || {}).textContent || '').replace(/\u00a0/g, ' '), fsR: parseFloat(getComputedStyle(p.querySelector('.pp-r b')).fontSize), fsT: parseFloat(getComputedStyle(p.querySelector('.pp-t b')).fontSize), y: Math.round(p.getBoundingClientRect().top + window.scrollY) } : null)(document.querySelector('.bpage .pp')) }; });
    assert.strictEqual(pg.h1, uRich.building || String(uRich.address).split(',')[0]); assert.strictEqual(pg.strip.length, 3);
    // (pass 8) the header: "Rent from $X" first and larger, "about $Y with utilities and fees" beside it; both the figures of the apartment with the lowest total, and it says so
    { const fu = us.slice().sort((a, b) => a.all_in - b.all_in)[0], same = us.every(u => u.all_in === us[0].all_in && rentOf(u) === rentOf(us[0]) && rs(u) === rs(us[0]));
      assert(pg.pp, 'the pair of prices leads the building header'); assert.strictEqual(pg.pp.rl, us.length > 1 && !same ? 'Rent from' : L_RENT); assert.strictEqual(pg.pp.r, moneyX(rentOf(fu)) + (rs(fu) ? '*' : ''));
      assert.strictEqual(pg.pp.tl, 'Total'); assert.strictEqual(pg.pp.t, 'about ' + money10(fu.all_in)); assert.strictEqual(pg.pp.uf, WITH_UF); assert(pg.pp.fsR > pg.pp.fsT && pg.pp.y < pg.y.strip, 'rent larger; the pair above the strip');
      if (us.length > 1) assert(same ? /^The same for (both|all \d+) apartments here$/.test(pg.pp.note) : pg.pp.note === 'Both for Apartment ' + fu.unit + ', the lowest total of the ' + us.length + ' here', 'both figures belong to one apartment, named: ' + JSON.stringify([pg.pp.note, fu.unit, us.length, same]));
      assert.deepStrictEqual(await barePrices('.bpage'), [], 'no unnamed price in the building header'); }
    assert(/to Mom and Dad|drive/.test(pg.strip[0]) && /parking/.test(pg.strip[1]) && /dogs/.test(pg.strip[2]), 'then minutes, parking, dogs');
    assert.deepStrictEqual(pg.rows.filter(r => r !== 'r-queens'), ['r-day', 'r-parking', 'r-dog', 'r-building', 'r-reviews', 'r-rules'], 'the building\'s rows, A day here first: ' + pg.rows);
    assert.deepStrictEqual(pg.labels.slice(0, 6), ['A day here', 'The car', 'For the dog', 'The building', 'Reviews of the building', 'Local rules']); if (pg.rows.includes('r-queens')) assert.strictEqual(pg.rows[pg.rows.length - 1], 'r-queens');
    assert(pg.rows.length <= 8, 'at most eight rows: ' + pg.rows.length); assert.strictEqual(pg.host, 0, 'no host box'); assert.strictEqual(pg.sign, 0);
    assert(pg.y.strip < pg.y.save && pg.y.save < pg.y.about && pg.y.about < pg.y.rows && pg.y.rows < pg.y.apts && pg.y.apts < pg.y.save2 && pg.y.save2 < pg.y.next, 'in that order: ' + JSON.stringify(pg.y));
    assert.strictEqual(pg.saves.length, 2, '"Save this place" at the top and at the bottom'); assert(pg.saves.every(s => s.startsWith('Save this apartment')), pg.saves.join(' | '));
    assert.strictEqual(pg.about.h2, 'About the building'); // the About text is the building's own copy in buildings[]; a unit's host line is only the last resort
    const bRec = (data.buildings || []).find(b => b.id === uRich.building_id), aboutText = bRec && typeof bRec.about_building === 'string' && bRec.about_building ? bRec.about_building : typeof uRich.about_building === 'string' && uRich.about_building ? uRich.about_building : '';
    if (aboutText && !CRIME.test(aboutText)) { const s0 = aboutText.slice(0, 50); assert(pg.about.text.includes(s0), 'the text is shown'); assert.strictEqual((await page.evaluate(() => document.getElementById('view').textContent)).split(s0).length - 1, 1, 'and only once on the page'); }
    // photos: one clear tap near the top, to the building's own site when one of its apartments has it, else to the listing
    const ph = us.map(u => u.photos).filter(p => p && p.url), want = ph.find(p => p.kind === 'own_site') || ph[0] || null;
    if (want) { const b = await page.evaluate(() => { const a = document.getElementById('see-photos'); return { href: a.getAttribute('href'), target: a.target, rel: a.rel, text: a.textContent.replace(/\s+/g, ' ').trim(), svg: a.querySelectorAll('svg').length }; });
      assert.strictEqual(b.href, want.url); assert.strictEqual(b.target + '|' + b.rel, '_blank|noopener noreferrer'); assert.strictEqual(b.text, 'See photos' + 'opens ' + (want.where || new URL(want.url).hostname.replace(/^www\./, ''))); assert.strictEqual(b.svg, 1); assert(pg.y.photos < pg.y.about, 'before About the building'); }
    else if (!us.some(u => u.links && (u.links.building || u.links.listing))) assert.strictEqual(await page.locator('#see-photos').count(), 0, 'no link, no button'); }
  { const noPh = best.find(u => bUnits(u).every(x => !(x.photos && x.photos.url) && !(x.links && (x.links.listing || x.links.building)))); if (noPh) { await go('#bldg-' + bSlug(noPh), '.bpage'); assert.strictEqual(await page.locator('#see-photos').count(), 0); }
    console.log('buildings with a photos link:', best.filter(u => bUnits(u).some(x => x.photos && x.photos.url)).length, 'of', best.length, '| own site:', best.filter(u => bUnits(u).some(x => x.photos && x.photos.kind === 'own_site')).length); }
  if (await page.locator('#r-building [data-act=contact]').count()) { await go('#bldg-' + bSlug(uRich), '.bpage'); }
  { const withC = best.find(u => u.contact && u.contact.phone); if (withC) { await go('#bldg-' + bSlug(withC), '.bpage'); await openRow('r-building'); await page.click('#r-building [data-act=contact]'); await page.waitForSelector('#sheet.open'); { const cb = ((data.buildings || []).find(b => b.id === withC.building_id) || {}).contact || withC.contact, fwd = !!(cb.phone && /listing-site|forwarding|tracking number/i.test(cb.note || '')), sh = await page.textContent('#sheetBody');
      // a listing site's forwarding number is not called the leasing office, and its pipeline note is not printed
      if (fwd) { assert(sh.includes('Listing-site number (forwards to the office)') && !sh.includes('Leasing office') && !/tracking number/.test(sh), sh.slice(0, 200)); } else assert(sh.includes('Leasing office'), sh.slice(0, 200)); }
    const fw = best.find(u => { const c = ((data.buildings || []).find(b => b.id === u.building_id) || {}).contact; return c && c.phone && /listing-site|forwarding|tracking number/i.test(c.note || ''); });
    if (fw && fw !== withC) { await page.keyboard.press('Escape'); await page.waitForSelector('#sheet:not(.open)'); await go('#bldg-' + bSlug(fw), '.bpage'); await openRow('r-building'); await page.click('#r-building [data-act=contact]'); await page.waitForSelector('#sheet.open'); assert((await page.textContent('#sheetBody')).includes('Listing-site number (forwards to the office)')); }
    await page.waitForTimeout(300); await shot('ux-04c-leasing-office-sheet'); await page.keyboard.press('Escape'); await page.waitForSelector('#sheet:not(.open)'); await page.waitForTimeout(300); } }
  // "A day here": a stack of closed rows, one per moment: icon, title, one-line takeaway, and a chip in three levels where the data can say
  await go('#bldg-' + bSlug(star), '.bpage'); await openRow('r-day');
  { const B0 = bUnits(star)[0], KS = ['wake', 'work', 'after', 'night', 'sat', 'sun'], ms = await page.evaluate(() => [...document.querySelectorAll('#r-day details.mom')].map(d => ({ id: d.id, open: d.open, icon: d.querySelectorAll('summary .mi svg').length, title: d.querySelector('summary .rl').firstChild.textContent.trim(), take: d.querySelector('summary .rh').textContent, chip: (d.querySelector('summary .lvl') || {}).textContent || '', chev: d.querySelectorAll('summary .chev').length })));
    assert.deepStrictEqual(ms.map(m => m.id), KS.map(k => 'm-' + k));
    // crime wording of the night moment is only inside its closed "See how we got this"; "an 8-minute walk", never "a 8-minute"
    { await page.click('#m-night > summary'); const vis = await page.evaluate(() => document.getElementById('m-night').innerText); assert(!CRIME.test(vis), 'no crime line in the open night moment: ' + (CRIME.exec(vis) || [''])[0]); await page.click('#m-night > summary');
      assert.deepStrictEqual(await page.evaluate(() => [8, 11, 18, 5, 80, 1].map(n => window.__houseHunt.aWalk(n))), ['an 8-minute walk', 'an 11-minute walk', 'an 18-minute walk', 'a 5-minute walk', 'an 80-minute walk', 'a 1-minute walk']); } assert.strictEqual((await page.textContent('#mom-count')).trim(), '6 moments', 'it says how many are below');
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
  { const us = bUnits(bTwo), rows = await page.evaluate(() => [...document.querySelectorAll('#sec-apts .apt')].map(a => ({ id: a.querySelector('details').id, open: a.querySelector('details').open, name: a.querySelector('.an').textContent, price: a.querySelector('.apx').innerText.replace(/\s+/g, ' ').trim(), rent: a.querySelector('.apr b').textContent, rentLabel: a.querySelector('.apr small').textContent, total: a.querySelector('.apw').textContent.replace(/\s+/g, ' ').trim(), fsR: parseFloat(getComputedStyle(a.querySelector('.apr b')).fontSize), fsT: parseFloat(getComputedStyle(a.querySelector('.apw b')).fontSize), fsMin: [...a.querySelectorAll('summary *')].filter(e => e.children.length === 0 && e.textContent.trim() && !e.closest('svg')).map(e => parseFloat(getComputedStyle(e).fontSize)).sort((x, y) => x - y)[0], rentAbove: a.querySelector('.apr').getBoundingClientRect().top <= a.querySelector('.apw').getBoundingClientRect().top, meta: a.querySelector('.am').textContent, conf: (a.querySelector('summary .ac:not(.out)') || {}).textContent || '', heart: a.querySelectorAll(':scope > .heartb').length, h: Math.round(a.getBoundingClientRect().height) })));
    assert.strictEqual((await page.textContent('#sec-apts h2')).replace(/\d+$/, '').trim(), us.length > 1 ? 'Apartments here' : 'The apartment'); assert.deepStrictEqual(rows.map(r => r.id), us.map(u => 'apt-' + slug(u.id)), 'its apartments, best first');
    rows.forEach((r, i) => { const u = us[i]; assert(!r.open, 'closed to start'); assert.strictEqual(r.heart, 1, 'its own Save'); if (u.unit) assert(r.name.includes(u.unit));
      // (pass 8) both prices on the row itself: "Rent $2,345" exact, first and larger; then "about $2,670 with utilities and fees" (the total, to $10)
      assert.strictEqual(r.rentLabel, L_RENT); assert.strictEqual(r.rent, moneyX(rentOf(u)) + (rs(u) ? '*' : ''), 'the rent, to the dollar, the offer star on it: ' + r.rent); assert.strictEqual(r.total, 'about ' + money10(u.all_in) + ' ' + WITH_UF, 'the total: ' + r.total);
      assert(r.fsR > r.fsT && r.rentAbove && r.fsMin >= 12.5, 'rent is the larger figure and comes first; nothing under 12.5 px: ' + [r.fsR, r.fsT, r.fsMin]); assert(!/\$[\d,]+\*? a month/.test(r.price) && !/everything included/i.test(r.price), 'no single unnamed figure: ' + r.price);
      assert(r.meta.includes(u.sqft != null ? Math.round(u.sqft) + ' sq ft' : 'size not published') && r.meta.includes(u.floor != null ? 'floor ' + Math.round(u.floor) : 'floor not published') && r.meta.includes(u.confirm.asterisk && /live check|availab/i.test(u.confirm.what || '') ? 'availability to confirm' : u.available === 'now' ? 'available now' : /^\d{4}-\d\d-\d\d/.test(u.available || '') ? 'from ' : 'move-in date: ask'), 'size, floor and date: ' + r.meta);
      assert.strictEqual(!!r.conf, !!(u.confirm.asterisk || rs(u)), 'its own thing to confirm: ' + r.conf); if (u.confirm.asterisk) assert(r.conf.startsWith('* To confirm:')); if (W === 390) assert(r.h <= 250, 'a compact row (name, rent, total, the facts, what to confirm, a line on the offer, a line when a cost is not published): ' + r.h + 'px'); });
    assert.deepStrictEqual(await barePrices('#sec-apts .aptd > summary'), [], 'no unnamed price on an apartment row');
    await shot('ux-05-apartments-here'); await shotEl('p8-apartment-row', '#sec-apts .apt');
    const u = us.find(x => x.confirm.asterisk) || us[0]; await openApt(u); const S0 = aptSel(u);
    assert.strictEqual(await page.locator(S0 + ' .receipt .ln:not(.tot)').count(), u.all_in_lines.length, 'every cost line is in the box'); assert.strictEqual((await page.textContent(S0 + ' .sec-cost > .allin')).trim(), 'Rent is what the listing asks. The total adds fees, parking, pet rent and our estimate of electricity, gas and internet.', 'one sentence at the top of the breakdown says what the two prices are'); assert.strictEqual(await page.locator(S0 + ' .psent').count(), 1, 'once');
    // (pass 8) the "What it costs" headline gives both; the breakdown adds up to the total; a line is marked "estimate" or "not published" as the data says; never $0 for a cost that is not published
    { const hl8 = (await page.textContent(S0 + ' .costhl')).trim(); assert(hl8.startsWith('Rent ' + moneyX(rentOf(u)) + (rs(u) ? '*' : '')) && hl8.endsWith('· about ' + money10(u.all_in) + ' ' + WITH_UF), 'the headline: ' + hl8); }
    assert.strictEqual(await page.locator(S0 + ' .receipt .ln small').count(), 0, 'no basis notes on the lines'); assert(await page.isHidden(S0 + ' .receipt .howb'));
    assert(u.all_in_unknown.length === 0 || (await page.textContent(S0 + ' .receipt')).toLowerCase().includes('not published'), 'an unknown cost reads "not published", never $0');
    assert((await page.textContent(S0 + ' .tour-qs')).includes((u.tour_questions[0] || 'to ask on the tour').slice(0, 30))); if (u.links && u.links.listing) assert.strictEqual(await page.getAttribute(S0 + ' .plinks a >> nth=0', 'href'), u.links.listing);
    assert.strictEqual(await page.evaluate(ss => ss.filter(s => document.querySelector(s).open).length, us.map(aptSel)), 1, 'only the one tapped is open');
    await page.evaluate(s => document.querySelector(s).scrollIntoView(), S0); await page.evaluate(() => window.scrollBy(0, -70)); await shot('ux-05b-apartment-open'); await overflow('apartment open'); await shotEl('p8-apartment-open', '#w-' + S0.slice(1));
    await page.click(S0 + ' .receipt details.howd > summary'); assert(await page.isVisible(S0 + ' .receipt .howb')); await shot('05-receipt-how-open');
    // "Photos of this apartment" only when its own page differs from the building's
    for (const x of us) { const bp = (us.map(y => y.photos).filter(p => p && p.url).find(p => p.kind === 'own_site') || us.map(y => y.photos).filter(p => p && p.url)[0] || {}).url, own = x.photos && x.photos.url, n = await page.locator(aptSel(x) + ' .aphoto').count(); assert.strictEqual(n, own && own !== bp && own !== (x.links && x.links.listing) ? 1 : 0, 'the apartment photo link: ' + x.id); } }
  // the asterisk: what to confirm on the apartment's line, the why behind a tap; disclosures as "Good to know before you call"
  await go('#bldg-' + bSlug(conf), '.bpage');
  { const us = bUnits(conf), nStar = us.filter(u => u.confirm.asterisk || rs(u)).length, t = (await page.textContent('#see-apts')).replace(/\s+/g, ' ').trim();
    assert(t.startsWith('* ' + (us.length > 1 ? 'See the ' + us.length + ' apartments' : 'See the apartment')), 'the asterisk rides on the line that leads to the apartments: ' + t); assert.strictEqual(await page.locator('.bpage .confl').count(), 0, 'no separate boxes at the top');
    assert(t.includes(us.length > 1 ? nStar + ' with something to confirm' : 'to confirm'), t);
    await page.click('#see-apts'); const y = await page.evaluate(() => ({ top: document.getElementById('sec-apts').getBoundingClientRect().top, end: window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2 })); assert(y.top >= 0 && (y.top < 200 || y.end), 'it scrolls to the apartments: ' + Math.round(y.top)); }
  await openApt(conf); assert.strictEqual((await page.textContent(aptSel(conf))).split('Still to confirm').length - 1, 1, '"Still to confirm" is a heading once, not a heading and a box title');
  // (D24) the why is shown only when it is reader-facing: a note that names our own files or steps is not rendered at all
  const INTERNAL = /docs\/|\.csv\b|evidence pass|harvest|\bbatch/i;
  if (conf.confirm.why && !INTERNAL.test(conf.confirm.why)) { assert((await page.textContent(aptSel(conf) + ' .confirm-box')).includes(conf.confirm.why.replace(/\s*\((?:and )?count(?:ed|s)? as \$0\)/gi, '').slice(0, 40)), 'the why is on the page'); assert(await page.isHidden(aptSel(conf) + ' .confirm-box blockquote'), 'but behind "See why"'); }
  else assert.strictEqual(await page.locator(aptSel(conf) + ' .confirm-box blockquote').count(), 0, 'an internal note is not shown');
  if (await page.locator(aptSel(conf) + ' .confirm-box p:has-text("What to ask:")').count()) { const q = (await page.locator(aptSel(conf) + ' .confirm-box p:has-text("What to ask:")').first().textContent()).replace('What to ask: ', ''); assert((await page.textContent(aptSel(conf) + ' .tour-qs')).includes(q), 'the confirmation question is also in the tour questions'); }
  await overflow('unit-confirm'); await shot('08-unit-confirm-asterisk', true);
  const dU = data.units.find(u => whats(u).length >= 2 && !u.confirm.asterisk && hoodBy[u.hood_id]) || data.units.find(u => whats(u).length);
  console.log('places with a disclosure:', data.units.filter(u => whats(u).length).length, 'of', data.units.length);
  if (dU) { await go('#unit-' + slug(dU.id), '.bpage'); const S1 = aptSel(dU); assert(await page.evaluate(s => document.querySelector(s).open, S1), 'a link to a place opens its building with that apartment open');
    const OFFER_W = /special offer|net-effective|free months?\b/i, RENT_Q = /normal month|full monthly rent|advertised rent|after free months|first full payment/i, shownW = whats(dU).filter(w => !(rs(dU) && OFFER_W.test(w)));
    assert.strictEqual(await page.locator(S1 + ' .good-to-know > ul > li').count(), shownW.length, 'every disclosure is listed once (the rent offer is said on the apartment\'s line, not again here)');
    const gtk = await page.textContent(S1 + ' .good-to-know'), tqs = await page.textContent(S1 + ' .tour-qs'); assert(gtk.includes('Good to know before you call'));
    // a disclosure is shown under its reader-facing label when the data gives one ("lease term" reads "lease length"); new kinds (income requirement, furnished apartment) show like the others
    const labelOf = w => { const x = (dU.disclosures || []).find(d => String(d.what || '').trim() === w); return x && typeof x.label === 'string' && x.label ? x.label : w; };
    for (const w of shownW) assert(gtk.toLowerCase().includes(labelOf(w).toLowerCase()), 'disclosure shown: ' + labelOf(w));
    assert(!/why_internal/.test(gtk) && !(dU.disclosures || []).some(d => d.why_internal && d.why_internal !== d.why && d.why_internal.length > 30 && gtk.includes(d.why_internal.slice(0, 40))), 'the internal note of a disclosure is never rendered');
    for (const x of dU.disclosures) if (x.question && !RENT_Q.test(x.question)) assert(tqs.includes(x.question.replace(/\s*\([^)]*\)\s*$/, '')), 'the disclosure question is in the tour questions: ' + x.question);
    if (!dU.confirm.asterisk) assert.strictEqual(await page.locator(S1 + ' .confirm-box, ' + S1 + ' .cstar').count(), 0, 'a disclosure is not an asterisk');
    await page.evaluate(s => document.querySelector(s + ' .good-to-know').scrollIntoView(), S1); await page.evaluate(() => window.scrollBy(0, -70)); await shot('12-unit-good-to-know'); await overflow('unit-disclosures'); }
  const noConf = best.find(u => bUnits(u).every(x => !x.confirm.asterisk && !rs(x)));
  if (noConf) { await go('#bldg-' + bSlug(noConf), '.bpage'); assert.strictEqual(await page.locator('.confirm-box, .cstar, .aptd summary .ac:not(.out)').count(), 0, 'nothing to confirm: no asterisk anywhere'); assert(!(await page.textContent('#see-apts')).includes('*')); }
  // rent with an asterisk: on the price, on the apartment's line, and the terms inside it
  await go('#unit-' + slug(star.id), '.bpage'); { const S2 = aptSel(star); assert((await page.textContent(S2 + ' .apr b')).includes('*'), 'the offer star is on the RENT figure'); assert(!(await page.textContent(S2 + ' .apw')).includes('*'), 'and not on the total');
    // (pass 6) the rent offer is said once: on the apartment's line; its full wording waits behind one tap; nothing else repeats it
    { const line = await page.evaluate(id => window.__houseHunt.offerLine(id), star.id), o = await page.evaluate(([s, line]) => { const d = document.querySelector(s), t = d.innerText; return { lines: [...d.querySelectorAll('summary .ac.offer')].map(e => e.textContent.trim()), hits: t.split(line).length - 1, old: d.querySelectorAll('.confl.rent, .capwarn, .rent-terms .call').length, fold: [...d.querySelectorAll('.rentfold details')].map(x => x.open), label: d.querySelector('.apr small').textContent, term: (d.querySelector('.apr .rt') || {}).textContent || '',
        rentQs: [...d.querySelectorAll('.tour-qs li')].map(li => li.textContent).filter(q => /normal month|full monthly rent|advertised rent|after free months|first full payment/i.test(q)).length, gtk: (d.querySelector('.good-to-know') || { textContent: '' }).textContent, jargon: (m => m ? t.slice(Math.max(0, m.index - 50), m.index + 40) : '')(/net-effective|all-in|\bcap\b|live check/i.exec(t)) }; }, [S2, line]);
      assert.deepStrictEqual(o.lines, [line], 'one line on the offer: ' + o.lines); assert.strictEqual(o.hits, 1, 'and it is said once in the open apartment'); assert.strictEqual(o.old, 0, 'no second rent box, no warning line, no "Needs a call" chip');
      assert.deepStrictEqual(o.fold, [false], 'the full wording is behind one tap, closed'); assert(o.rentQs <= 1, 'one question about the rent, not the same one twice: ' + o.rentQs); assert(!/special offer|net-effective/i.test(o.gtk), 'and not again under Good to know'); assert(!o.jargon, 'no "net-effective", "all-in", "cap" or "live check" in the open apartment: ' + o.jargon);
      assert.strictEqual(o.label, L_RENT); if (star.rent.basis_kind === 'net_effective') assert.strictEqual(o.term, 'with the current offer', 'a rent after an offer says so beside the figure'); assert(/normal month|offer/i.test(line), line);
      if (star.all_in_gross > star.all_in) assert(/^In a normal month the rent is (\$[\d,]+|higher), about \$[\d,]+ with utilities and fees/.test(line), 'the line gives the normal month as rent and as total, each named: ' + line); }
    const co = await page.evaluate(x => window.__houseHunt.cleanText(x), star.rent.offer_text), rt = await page.textContent(S2 + ' .terms'); if (co) assert(rt.includes(co.slice(0, 30)), 'the offer, in the building\'s words'); else assert(!rt.includes('The offer, in the building\'s words')); await shot('04-unit-rent-asterisk', true); }
  // an old link to a place: the building's page, that apartment open and in view, the others closed
  { const u2 = data.units.find(u => hoodBy[u.hood_id] && bUnits(u).length > 1 && bUnits(u)[0].id !== u.id); if (u2) { await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); await page.evaluate(h => { location.hash = h; }, '#unit-' + slug(u2.id)); await page.waitForSelector('.bpage');
      const r = await page.evaluate(([s, all]) => ({ open: all.map(x => document.querySelector(x).open), top: Math.round(document.querySelector(s).getBoundingClientRect().top), h1: document.querySelector('.ph1').textContent.trim(), hash: location.hash }), [aptSel(u2), bUnits(u2).map(aptSel)]);
      assert.deepStrictEqual(r.open, bUnits(u2).map(x => x.id === u2.id), 'only that apartment is open'); assert(r.top >= 0 && r.top < 844 * 0.6, 'and it is in view: ' + r.top); assert.strictEqual(r.h1, cleanName(bUnits(u2)[0].building) || String(u2.address).split(',')[0]); assert.strictEqual(r.hash, '#unit-' + slug(u2.id)); } }
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
  assert.strictEqual(await page.getAttribute('.savb[data-pos=top]', 'aria-pressed'), String(bUnits(star)[0].id === star.id), 'the big Save button stands for the building\'s best-ranked apartment only');
  const two = data.units.find(u => u.year !== y1 && u.evidence.items.length && u.evidence.positive.length && isBest(u)) || data.units.find(u => u.year !== y1 && isBest(u));
  await go('#bldg-' + bSlug(two), '.bpage'); await openRow('r-queens'); assert(await page.locator('#r-love .panel.pause .quote a.srcl').count() >= 1); await overflow('unit2'); await shot('04c-building-with-evidence', true);
  // "Save this place" at the top saves ONE apartment, the building's best-ranked (a heart on each row saves the others); the toast names it; the one at the bottom shows the same state and takes it off again
  { const lab = (await page.textContent('.savb[data-pos=top]')).trim(); assert(lab.startsWith('Save this apartment')); if (bUnits(two).length > 1) assert(/top pick of \d+ here$/.test(lab), 'the button says which apartment it saves: ' + lab); }
  await page.click('.savb[data-pos=top]'); { const want = [star.id].concat([bUnits(two)[0].id]); assert.deepStrictEqual(await saved(), want, 'one tap saves one apartment'); assert((await page.textContent('#toast')).startsWith('Saved ' + (bUnits(two)[0].building || '').slice(0, 12)), 'the toast says what was saved: ' + await page.textContent('#toast'));
    assert.strictEqual(await page.getAttribute('#w-apt-' + slug(bUnits(two)[0].id) + ' > .heartb', 'aria-pressed'), 'true', 'and that apartment\'s own heart shows it');
    assert.deepStrictEqual(await page.evaluate(() => [...document.querySelectorAll('.savb')].map(b => b.getAttribute('aria-pressed') + '|' + b.textContent.trim().slice(0, 5))), ['true|Saved', 'true|Saved'], 'both Save buttons say Saved');
    await page.click('.savb[data-pos=bottom]'); assert.deepStrictEqual(await saved(), [star.id], 'the bottom one takes them off'); await page.click('.savb[data-pos=bottom]'); assert.deepStrictEqual(await saved(), want); }
  const three = data.units.find(u => u.year !== y1 && u.year !== two.year && isBest(u)) || data.units.find(u => u.id !== star.id && u.id !== two.id && isBest(u));
  await go('#bldg-' + bSlug(three), '.bpage'); await heart(three);
  // any number: two more, from other buildings
  const more = best.filter(u => ![star, two, three].some(x => bSlug(x) === bSlug(u))).slice(0, 2); for (const u of more) { await go('#bldg-' + bSlug(u), '.bpage'); await heart(u); }
  const all = await saved(); assert(all.length >= 5, 'more than three can be saved: ' + all.length); assert.strictEqual((await page.evaluate(() => document.getElementById('tray').innerText)).replace(/\s+/g, ' ').trim(), 'Saved · ' + all.length + ' My list');
  await page.click('#tray a'); await page.waitForSelector('#mylist');
  const listIds = () => page.evaluate(() => [...document.querySelectorAll('#mylist .lrow')].map(r => r.getAttribute('data-id')));
  assert.deepStrictEqual(await listIds(), all, 'My list: everything saved, in the order saved, not ranked'); assert.strictEqual((await page.textContent('#list-count')).trim(), all.length + ' apartments saved');
  await fits('list', all.length + ' apartments saved'); await overflow('list');
  // (audit) the facts of a row never run into each other, at any width, and none is under 12 px; with more than three saved nothing is ticked for her
  // (pass 8) My list: each row gives both prices by name, the rent first ("$2,345 rent", "about $2,670 total"); the offer star is on the rent
  { const lp = await page.evaluate(() => [...document.querySelectorAll('#mylist .lrow')].map(r => ({ id: r.getAttribute('data-id'), facts: [...r.querySelectorAll('.lfacts > span')].map(s => s.textContent.replace(/\s+/g, ' ').trim()) })));
    for (const r of lp) { const u = unitBy[r.id]; assert.strictEqual(r.facts[0], moneyX(rentOf(u)) + (rs(u) ? '*' : '') + ' rent', 'the rent leads the row: ' + r.facts[0]); assert.strictEqual(r.facts[1], 'about ' + m10(u.all_in) + ' total', 'then the total: ' + r.facts[1]); }
    assert.deepStrictEqual(await barePrices('#mylist .lrow'), [], 'no unnamed price in My list'); assert.strictEqual(await page.locator('#mylist .lout').count(), 0, 'no filter is on: no note about filters');
    assert(await page.evaluate(() => { const b = document.querySelector('.listbar #filterBtn'); return !!b && b.getBoundingClientRect().height >= 44 && b.getBoundingClientRect().right <= innerWidth; }), 'the Filter button sits beside Sort on My list'); }
  { const lf = await page.evaluate(() => [...document.querySelectorAll('#mylist .lfacts')].map(f => { const r = [...f.children].map(c => c.getBoundingClientRect()); let bad = 0; r.forEach((a, i) => r.forEach((b, j) => { if (i < j && a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1) bad++; })); return { bad, fs: Math.min(...[...f.querySelectorAll('span')].map(s => parseFloat(getComputedStyle(s).fontSize))), wide: [...f.children].some(c => c.scrollWidth > c.clientWidth + 1) }; }));
    assert(lf.every(f => f.bad === 0 && !f.wide && f.fs >= 12), 'no fact overlaps another: ' + JSON.stringify(lf.slice(0, 3))); } await small('list'); await noCrime('list'); await shot('06-my-list', true); await shot('ux-06-my-list');
  // sorting is hers: all-in, minutes, size, move-in date, things to confirm, experience
  { const U = id => unitBy[id], mk = u => u.available === 'now' ? '0000' : /^\d{4}-\d\d-\d\d/.test(u.available || '') ? u.available : '9999', nc = u => (u.confirm.asterisk ? 1 : 0) + (rs(u) ? 1 : 0) + whats(u).length, yi = u => data.years.findIndex(y => y.id === u.year);
    const ord = { rent: (a, b) => rentOf(a) - rentOf(b), all_in: (a, b) => a.all_in - b.all_in, mins: (a, b) => a.moments.sun.drive_min - b.moments.sun.drive_min, sqft: (a, b) => (b.sqft == null ? -1e18 : b.sqft) - (a.sqft == null ? -1e18 : a.sqft), movein: (a, b) => mk(a) < mk(b) ? -1 : mk(a) > mk(b) ? 1 : 0, confirm: (a, b) => nc(a) - nc(b), exp: (a, b) => yi(a) - yi(b) };
    assert.deepStrictEqual(await page.evaluate(() => [...document.querySelectorAll('#listSort option')].map(o => o.value)), ['saved', 'rent', 'all_in', 'mins', 'sqft', 'movein', 'confirm', 'exp']);
    assert.deepStrictEqual(await page.evaluate(() => [...document.querySelectorAll('#listSort option')].slice(1, 3).map(o => o.textContent)), ['Rent, lowest first', 'Total with utilities and fees, lowest first'], 'the two price sorts are named');
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
  await shot('06-compare', true); await shot('ux-06-compare-collapsed'); await shot('p8-compare', true);
  // the trade in plain words is in view; names and prices stay pinned; only what differs is shown, until asked; the Queens comparison starts closed
  assert(await page.isVisible('.pairbox p')); assert.strictEqual(await page.evaluate(() => getComputedStyle(document.querySelector('.cmp-head')).position), 'sticky');
  assert.strictEqual(await page.locator('.cmp-head .colh').count(), 3);
  // (audit) each column head names its apartment on two lines and is never cut to "City…"; the sentence above uses names, never "House 1"; removing is a 44 px target; the best cell says "Best" in words
  { const heads = await page.evaluate(() => [...document.querySelectorAll('.cmp-head .colh')].map(c => ({ b: c.querySelector('a b').textContent, s: c.querySelector('a small').textContent, cut: c.querySelector('a b').scrollWidth > c.querySelector('a b').clientWidth + 1, ws: getComputedStyle(c.querySelector('a b')).whiteSpace, x: Math.round(c.querySelector('.x').getBoundingClientRect().width), fs: parseFloat(getComputedStyle(c.querySelector('a small')).fontSize) })));
    [star, two, three].forEach((u, i) => { assert.strictEqual(heads[i].b, u.unit ? 'Apartment ' + u.unit : (u.building || String(u.address).split(',')[0]), 'the door number leads when there is one'); if (u.unit) assert.strictEqual(heads[i].s, u.building || String(u.address).split(',')[0]); });
    assert(heads.every(h => !h.cut && h.ws !== 'nowrap' && h.x >= 44 && h.fs >= 12.5), 'whole names, a 44 px remove button: ' + JSON.stringify(heads)); assert(!/House \d/.test(await page.textContent('.pairbox')), 'no "House 1" in the sentence');
    const edge = await page.evaluate(() => { const e = document.querySelector('#cmp-rows .cell.edge'); return e ? getComputedStyle(e, '::before').content : null; }); if (edge) assert(/Best/.test(edge), 'the best cell is marked in words, not by colour alone: ' + edge); } assert(await page.isChecked('#ties'), '"Only show what differs" is on by default'); assert(!(await page.evaluate(() => document.getElementById('c-queens').open)), 'the Queens comparison is collapsed');
  const rows1 = await page.locator('#cmp-rows .rowc').count(); await page.click('#ties'); const rows2 = await page.locator('#cmp-rows .rowc').count();
  assert.strictEqual(rows2, 5 + ([star, two, three].some(u => u.confirm.asterisk || (u.disclosures || []).length) ? 1 : 0), 'rent, total, space, parking, the trip and what is to confirm, got ' + rows2); assert(rows1 <= rows2);
  // (pass 8) compare: two money rows, "Rent" then "Total with utilities and fees", each with its own figures, each in the "what differs" logic; the column heads carry the rent, named
  { const three3 = [star, two, three], cr = await page.evaluate(() => [...document.querySelectorAll('#cmp-rows .rowc')].map(r => ({ label: (h => { const k = h.cloneNode(true); k.querySelectorAll('svg, em').forEach(x => x.remove()); return k.textContent.trim(); })(r.querySelector('h4')), cells: [...r.querySelectorAll('.cell')].map(c => { const k = c.cloneNode(true); k.querySelectorAll('small').forEach(x => x.remove()); return k.textContent.trim(); }), small: [...r.querySelectorAll('.cell small')].map(s => s.textContent) })));
    assert.strictEqual(cr[0].label, L_RENT); assert.strictEqual(cr[1].label, L_TOTAL);
    assert.deepStrictEqual(cr[0].cells, three3.map(u => moneyX(rentOf(u)) + (rs(u) ? '*' : '')), 'the rent row: each rent to the dollar'); assert.deepStrictEqual(cr[1].cells, three3.map(u => 'about ' + m10(u.all_in)), 'the total row: each total with "about"');
    const heads = await page.evaluate(() => [...document.querySelectorAll('.cmp-head .colh .pr')].map(p => p.textContent.replace(/\s+/g, ' ').trim())); assert.deepStrictEqual(heads, three3.map(u => moneyX(rentOf(u)) + (rs(u) ? '*' : '') + ' rent'), 'each head names its figure: ' + heads);
    // "what differs": a row whose figures are within $24 of each other is hidden while the switch is on, for rent and for total alike
    await page.click('#ties'); const shownLabels = await page.evaluate(() => [...document.querySelectorAll('#cmp-rows .rowc h4')].map(h => { const k = h.cloneNode(true); k.querySelectorAll('svg, em').forEach(x => x.remove()); return k.textContent.trim(); })); await page.click('#ties');
    const tie = a => Math.max(...a) - Math.min(...a) <= 24; assert.strictEqual(shownLabels.includes(L_RENT), !tie(three3.map(rentOf)), 'the rent row is shown only when the rents differ'); assert.strictEqual(shownLabels.includes(L_TOTAL), !tie(three3.map(u => u.all_in)), 'the total row is shown only when the totals differ');
    await page.click('#ties'); { const money = await page.evaluate(() => [...document.querySelectorAll('#cmp-rows .rowc')].filter(r => /\$\d/.test(r.querySelector('.cols').textContent)).map(r => { const k = r.querySelector('h4').cloneNode(true); k.querySelectorAll('svg, em').forEach(x => x.remove()); return k.textContent.trim(); }));
      assert(money.every(l => [L_RENT, L_TOTAL, 'Parking', 'To Mom and Dad'].includes(l)), 'every row with a dollar figure says what the figure is: ' + money); } await page.click('#ties');
    const pb = (await page.textContent('.pairbox p')).trim(); assert(/rent/i.test(pb) && /With utilities and fees/.test(pb), 'the sentence speaks of the rent and of the total: ' + pb); }
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

  // ---------- (UI pass 8) filters: one sheet, opened by a Filter button on every list page; they apply everywhere at once ----------
  // The test keeps its own reading of each filter, from the data alone, and compares the page's counts with it.
  const N_ALL = data.units.length, bRecOf = u => (data.buildings || []).find(b => b.id === u.building_id);
  const hasReviews = u => { const r = (bRecOf(bUnits(u)[0]) || {}).ratings || bUnits(u)[0].ratings; return !!(r && r.found_any !== false && (r.platforms || []).some(x => x && x.platform && x.rating != null && isFinite(+x.rating))); };
  const parkOf = u => u.parking && u.parking.rank != null ? +u.parking.rank : (u.parking && u.parking.type ? 1.5 : null), moveOf = u => u.available === 'now' ? '' : /^\d{4}-\d\d-\d\d/.test(u.available || '') ? u.available.slice(0, 10) : null;
  const passes = (f, u) => { const mv = moveOf(u);
    if (f.rent != null && rentOf(u) > f.rent) return false; if (f.total != null && u.all_in > f.total) return false; if (f.beds != null && u.beds !== f.beds) return false;
    if (u.sqft == null) { if (f.nosize) return false; } else if (f.sqft != null && u.sqft < f.sqft) return false;
    if (f.mins != null && Math.round(u.moments.sun.drive_min) > f.mins) return false;
    if (f.move != null && (mv == null || (f.move === 'now' ? mv !== '' : mv > f.move))) return false;
    if (f.park === 'covered' && !(parkOf(u) >= 3)) return false; if (f.park === 'at' && !(parkOf(u) >= 1.5)) return false;
    if (f.wd && u.amenities.in_unit_laundry !== 'yes') return false; if (f.clear && u.confirm.asterisk) return false; if (f.rev && !hasReviews(u)) return false;
    if (f.exps && f.exps.length && !f.exps.includes(u.year)) return false; return true; };
  const countOf = f => data.units.filter(u => passes(f, u)).length;
  const FS = () => page.evaluate(() => window.__houseHunt.filters());
  const fitline = async () => (await page.textContent('#fitline')).trim(), waitFit = n => page.waitForFunction(t => document.getElementById('fitline').textContent.trim() === t, 'Shows ' + n + ' of ' + N_ALL + (N_ALL === 1 ? ' apartment' : ' apartments'));
  const setRange = async (k, v, only) => page.evaluate(([k, v, only]) => { const e = document.getElementById('f-' + k); e.value = String(v); e.dispatchEvent(new Event('input', { bubbles: true })); if (!only) e.dispatchEvent(new Event('change', { bubbles: true })); }, [k, v, only || false]);
  const openF = async sel => { await page.click(sel || '#view .fbtn >> nth=0'); await page.waitForSelector('#limsheet.open'); await page.waitForTimeout(260); };
  const closeF = async () => { await page.click('#fShow'); await page.waitForSelector('#limsheet:not(.open)'); await page.waitForTimeout(260); };
  const clearF = async () => { await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); if ((await FS()).on) { await page.click('#fbar .fb-clear'); await page.waitForFunction(() => document.getElementById('fbar').hidden); } };
  const R8 = await FS(); assert.strictEqual(R8.on, 0, 'no filter is on to start'); assert.strictEqual(R8.n, N_ALL);
  await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life');
  // the button: on the first screen beside the heading, within the first screen, 44 px; the footer keeps its link; no bar while nothing is on
  { const b = await page.evaluate(() => { const e = document.getElementById('filterBtn'), r = e.getBoundingClientRect(), h = document.querySelector('#sec-experiences h2').getBoundingClientRect(); return { text: e.textContent.trim(), top: r.top + scrollY, h: r.height, w: r.width, right: r.right, beside: r.top < h.bottom && r.bottom > h.top, pop: e.getAttribute('aria-haspopup'), name: e.getAttribute('aria-label'), foot: document.getElementById('foot-filter').textContent.trim(), bar: document.getElementById('fbar').hidden }; });
    assert.strictEqual(b.text, 'Filter'); assert(b.h >= 44 && b.w >= 44 && b.right <= W, 'a 44 px target on screen: ' + JSON.stringify(b)); assert(b.top < VH, 'on the first screen without scrolling: ' + Math.round(b.top)); assert(b.beside, 'beside "Pick an experience"'); assert.strictEqual(b.pop, 'dialog'); assert(/^Filter/.test(b.name));
    assert.strictEqual(b.foot, 'Filter', 'the footer link stays'); assert(b.bar, 'no bar of filters while none is on'); }
  await openF('#filterBtn');
  // the sheet: a dialog with a title, the page behind inert, focus inside, a scrim; every control labelled; 44 px targets; no safety slider and no crime wording
  { const sh = await page.evaluate(() => { const s = document.getElementById('limsheet'), vis = e => e.getClientRects().length > 0, ctl = [...s.querySelectorAll('input, button, select')].filter(vis);
      const named = e => !!(e.getAttribute('aria-label') || (e.labels && e.labels.length && [...e.labels].some(l => l.textContent.trim())) || e.textContent.trim());
      const size = e => { const t = e.type === 'checkbox' ? e.closest('label') : e.type === 'radio' ? e.nextElementSibling : e, r = t.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; };
      return { role: s.getAttribute('role'), modal: s.getAttribute('aria-modal'), title: (document.getElementById(s.getAttribute('aria-labelledby')) || {}).textContent, inert: ['view', 'foot', 'tray', 'fbar'].map(i => !!document.getElementById(i).inert), focusIn: s.contains(document.activeElement), scrim: !document.getElementById('scrim').hidden,
        ranges: [...s.querySelectorAll('input[type=range]')].map(e => e.id), unnamed: ctl.filter(e => !named(e)).map(e => e.id || e.name || e.tagName), small: ctl.filter(e => { const z = size(e); return z[0] < 44 || z[1] < 44; }).map(e => (e.id || e.name) + ' ' + size(e)), groups: [...s.querySelectorAll('fieldset')].filter(vis).map(f => (f.querySelector('legend') || {}).textContent || ''), nameless: [...s.querySelectorAll('fieldset')].filter(f => !f.querySelector('legend')).length,
        live: [document.getElementById('fitline').getAttribute('role'), document.getElementById('fitline').getAttribute('aria-live')], text: s.innerText, tiny: [...s.querySelectorAll('*')].filter(e => vis(e) && e.children.length === 0 && e.textContent.trim() && parseFloat(getComputedStyle(e).fontSize) < 12.5).map(e => e.textContent.trim().slice(0, 20)),
        rent: (e => [+e.min, +e.max, +e.step, +e.value])(document.getElementById('f-rent')), total: (e => [+e.min, +e.max, +e.step, +e.value])(document.getElementById('f-total')), sw: s.scrollWidth, cw: s.clientWidth }; });
    assert.deepStrictEqual([sh.role, sh.modal, sh.title], ['dialog', 'true', 'Filter']); assert.deepStrictEqual(sh.inert, [true, true, true, true], 'the page behind is inert'); assert(sh.focusIn && sh.scrim, 'focus moves into the sheet; a scrim covers the page');
    assert.deepStrictEqual(sh.ranges, ['f-rent', 'f-total', 'f-sqft', 'f-mins'], 'four sliders: rent, total, size, the drive; no safety slider'); assert.deepStrictEqual(sh.unnamed, [], 'every control has a label'); assert.deepStrictEqual(sh.small, [], 'every control is a 44 px target'); assert.strictEqual(sh.nameless, 0, 'every group has a legend');
    assert(['Bedrooms', 'Parking', 'Only show apartments with', 'Experience'].every(g => sh.groups.includes(g)), 'the groups: ' + sh.groups); assert.deepStrictEqual(sh.live, ['status', 'polite'], 'the count is a live region');
    { const m = CRIME.exec(sh.text) || /safety|safe\b/i.exec(sh.text); assert(!m, 'the sheet names no crime rate: ' + (m && sh.text.slice(Math.max(0, m.index - 40), m.index + 40))); } assert(!/weight/i.test(sh.text), 'no dog-weight filter (dropped: most apartments publish no limit)'); assert.deepStrictEqual(sh.tiny, [], 'nothing under 12.5 px'); assert(sh.sw <= sh.cw, 'the sheet does not scroll sideways');
    assert(sh.text.includes(L_RENT + ', at most') && sh.text.includes(L_TOTAL + ', at most'), 'the two prices are filtered apart, each by name');
    // the ranges come from the data: rent in $50 steps from the lowest to the highest rent; the total up to the $3,000 limit
    const rents = data.units.map(rentOf), cap = data.meta.cap_all_in || 3000; assert.deepStrictEqual(sh.rent, [Math.floor(Math.min(...rents) / 50) * 50, Math.ceil(Math.max(...rents) / 50) * 50, 50, Math.ceil(Math.max(...rents) / 50) * 50]); assert.deepStrictEqual(sh.total.slice(1), [Math.max(cap, Math.ceil(Math.max(...data.units.map(u => u.all_in)) / 50) * 50), 50, Math.max(cap, Math.ceil(Math.max(...data.units.map(u => u.all_in)) / 50) * 50)]);
    assert.strictEqual(await fitline(), 'Shows ' + N_ALL + ' of ' + N_ALL + ' apartments'); assert.strictEqual((await page.textContent('#fShow')).trim(), 'Show ' + N_ALL + ' apartments'); assert(await page.isDisabled('#fClear'), 'nothing to clear yet');
    assert(await page.isVisible('#fs-exps'), 'the experience filter is offered on the first screen'); }
  await shot('p8-filter-sheet'); await page.evaluate(() => { document.getElementById('limsheet').scrollTop = 520; }); await page.waitForTimeout(200); await shot('p8-filter-sheet-2'); await page.evaluate(() => { document.getElementById('limsheet').scrollTop = 1e5; }); await page.waitForTimeout(200); await shot('p8-filter-sheet-3'); await page.evaluate(() => { document.getElementById('limsheet').scrollTop = 0; });
  // a rent that cuts the list roughly in half
  const RMAX = Math.round(median(data.units.map(rentOf)) / 50) * 50, fR = { rent: RMAX }, nR = countOf(fR); assert(nR > 0 && nR < N_ALL, 'the test rent splits the list: ' + nR);
  // while the slider moves, only the sheet follows (its words and the live count); the page behind is not drawn again
  await page.evaluate(() => { document.querySelector('a.life').setAttribute('data-mark8', '1'); }); const tag0 = (await page.textContent('#tagline')).trim();
  await setRange('rent', RMAX, true); await waitFit(nR);
  assert.strictEqual((await page.textContent('#o-rent')).trim(), 'Up to ' + moneyX(RMAX) + ' a month'); assert.strictEqual((await page.textContent('#fShow')).trim(), 'Show ' + nR + ' apartments');
  assert(await page.evaluate(() => !!document.querySelector('a.life[data-mark8]')), 'the page behind was not drawn again while the slider moved'); assert.strictEqual((await page.textContent('#tagline')).trim(), tag0);
  // let go: the filter applies everywhere, at once
  await setRange('rent', RMAX); await page.waitForFunction(() => !document.querySelector('a.life[data-mark8]'));
  assert.strictEqual((await page.textContent('#tagline')).trim(), nR + ' of ' + N_ALL + ' apartments match your filters.'); assert.strictEqual((await FS()).n, nR);
  // the keyboard works the slider: one arrow is one $50 step, and the count follows
  { await page.focus('#f-rent'); await page.keyboard.press('ArrowLeft'); await waitFit(countOf({ rent: RMAX - 50 })); assert.strictEqual((await FS()).f.rent, RMAX - 50, 'an arrow key moves the rent by $50 and applies it'); await page.keyboard.press('ArrowRight'); await waitFit(nR); }
  // Escape closes; focus returns to a Filter button; the page is live again
  await page.keyboard.press('Escape'); await page.waitForSelector('#limsheet:not(.open)');
  assert(await page.evaluate(() => { const a = document.activeElement; return !document.getElementById('view').inert && !!a && a.getAttribute('data-act') === 'filter-open'; }), 'Escape closes the sheet and focus returns to the Filter button');
  // the bar under the top line: the count, one removable chip per filter, "Clear all"; the button and the footer show how many are on
  { const bar = await page.evaluate(() => { const b = document.getElementById('fbar'), r = b.getBoundingClientRect(); return { hidden: b.hidden, pos: getComputedStyle(b).position, top: Math.round(r.top), h: Math.round(r.height), n: b.querySelector('.fb-n').textContent.replace(/\s+/g, ' ').trim(), chips: [...b.querySelectorAll('.fchip')].map(c => ({ t: c.querySelector('span').textContent, name: c.getAttribute('aria-label'), h: Math.round(c.getBoundingClientRect().height) })), clear: (b.querySelector('.fb-clear') || {}).textContent, clearH: Math.round(b.querySelector('.fb-clear').getBoundingClientRect().height), btn: document.getElementById('filterBtn').textContent.trim(), foot: document.getElementById('foot-filter').textContent.trim(), role: b.getAttribute('role'), label: b.getAttribute('aria-label') }; });
    assert(!bar.hidden && bar.pos === 'sticky' && bar.top === 0, 'the bar is pinned at the top of the first screen: ' + JSON.stringify(bar)); assert(bar.h <= 60, 'a slim bar: ' + bar.h + 'px'); assert.strictEqual(bar.n, nR + ' of ' + N_ALL);
    assert.deepStrictEqual(bar.chips.map(c => c.t), ['Rent up to ' + moneyX(RMAX)]); assert.strictEqual(bar.chips[0].name, 'Remove the filter: Rent up to ' + moneyX(RMAX)); assert(bar.chips[0].h >= 44 && bar.clearH >= 44, 'the chip and "Clear all" are 44 px targets'); assert.strictEqual(bar.clear, 'Clear all');
    assert.strictEqual(bar.btn, 'Filter · 1'); assert.strictEqual(bar.foot, 'Filter · 1 on: ' + nR + ' of ' + N_ALL + ' match'); assert(bar.role === 'region' && bar.label, 'the bar is a named region'); }
  // first screen: every tile counts and prices only what matches; an experience with nothing left says so and stays in place
  { const ts = await page.evaluate(() => [...document.querySelectorAll('a.life')].map(a => ({ href: a.getAttribute('href'), none: a.classList.contains('none'), cnt: (a.querySelector('.cnt b') || {}).textContent || '', lab: (a.querySelector('.cnt span') || {}).textContent || '', zero: (a.querySelector('.tzero') || {}).textContent || '', rent: (a.querySelector('.pp-r b') || {}).textContent || '', total: ((a.querySelector('.pp-t b') || {}).textContent || '').replace(/\s+/g, ' ').trim() })));
    assert.strictEqual(ts.length, data.years.length, 'no experience vanishes');
    data.years.forEach((y, i) => { const us = unitsOfYear(y), ok = us.filter(u => passes(fR, u)), t = ts[i];
      if (!ok.length) { assert(t.none && /Nothing here matches your filters/.test(t.zero), 'an experience with nothing left says so: ' + y.id); return; }
      assert.strictEqual(t.cnt, String(ok.length), 'the tile counts what matches: ' + y.id); assert.strictEqual(t.lab, ok.length === us.length ? (us.length === 1 ? 'apartment' : 'apartments') : 'of ' + us.length + ' match');
      const f = figsOf(ok); assert.strictEqual(t.rent, ok.length === 1 ? moneyX(f.rent) : m10(f.rent), 'the typical rent is of the apartments that match: ' + y.id); assert.strictEqual(t.total, 'about ' + m10(f.total)); });
    await overflow('first screen, filtered'); await shot('p8-first-screen-filtered'); }
  // the map: a mark counts only what matches, and its card says "N of M apartments match your filters"
  assert.strictEqual(await page.evaluate(() => window.__houseHunt.mapHoods()), data.neighborhoods.filter(h => h.unit_ids.length && yearBy[h.year] && yearBy[h.year].hood_ids.includes(h.id)).length, 'the map still holds every neighborhood');
  // an experience: the strip is recomputed over what matches and says so; only neighborhoods with a match are listed; the rest are counted in one line
  const yF = data.years.map(y => ({ y, us: unitsOfYear(y), ok: unitsOfYear(y).filter(u => passes(fR, u)) })).filter(x => x.ok.length && x.ok.length < x.us.length).sort((a, b) => b.ok.length - a.ok.length)[0];
  if (yF) { await go('#exp-' + slug(yF.y.id)); if (await page.getAttribute('.viewsw [data-v=list]', 'aria-pressed') !== 'true') await page.click('.viewsw [data-v=list]'); await showAll();
    const f = figsOf(yF.ok), hsAll = listed(yF.y), hsOk = hsAll.filter(h => unitsOfHood(h).some(u => passes(fR, u)));
    const e = await page.evaluate(() => ({ cells: [...document.querySelectorAll('.sec.head #keyfacts > .kfc')].map(c => (c.querySelector('.kft').textContent + '|' + c.querySelector('b').textContent).replace(/\s+/g, ' ').trim()), note: (document.querySelector('.sec.head .fnote') || {}).textContent || '', see: document.getElementById('see-hoods').textContent.replace(/\s+/g, ' ').trim(), hoods: [...document.querySelectorAll('#sec-hoods a.hood')].map(a => a.getAttribute('href')), subs: [...document.querySelectorAll('#sec-hoods a.hood .hsub')].map(s => s.textContent), hid: (document.querySelector('#sec-hoods .fhid span') || {}).textContent || '', head: document.querySelector('#sec-hoods h2').textContent.replace(/\s+/g, ' ').trim(), barTop: Math.round(document.getElementById('fbar').getBoundingClientRect().top), trailH: document.getElementById('trail').offsetHeight, fb: document.querySelectorAll('#view .fbtn').length }));
    assert.strictEqual(e.cells[0], (yF.ok.length > 1 ? 'typical rent|' + money10(f.rent) : 'rent|' + moneyX(f.rent)), 'the rent in the strip is of the apartments that match'); assert.strictEqual(e.cells[1], (yF.ok.length > 1 ? 'typical total' : 'total') + '|about ' + money10(f.total));
    assert.strictEqual(e.note, 'Typical figures are of the ' + yF.ok.length + ' of ' + yF.us.length + ' apartments that match your filters.', 'a small line says the figures are of the apartments that match');
    assert(e.see.startsWith('See the ' + hsOk.length + (hsOk.length === 1 ? ' neighborhood' : ' neighborhoods')) && e.see.endsWith(yF.ok.length + (yF.ok.length === 1 ? ' apartment' : ' apartments') + ' match your filters'), e.see);
    assert.deepStrictEqual(e.hoods, hsOk.map(h => '#hood-' + slug(h.id)), 'only the neighborhoods with a match, in their order'); assert(e.head.startsWith(hsOk.length + (hsOk.length === 1 ? ' neighborhood' : ' neighborhoods')) && e.head.includes(yF.ok.length + (yF.ok.length === 1 ? ' apartment' : ' apartments')), e.head);
    if (hsOk.length < hsAll.length) assert.strictEqual(e.hid, (hsAll.length - hsOk.length) + (hsAll.length - hsOk.length === 1 ? ' more neighborhood here has' : ' more neighborhoods here have') + ' nothing that matches your filters.', 'the others are counted, not silently dropped: ' + e.hid);
    hsOk.forEach((h, i) => { const us = unitsOfHood(h), k = us.filter(u => passes(fR, u)).length; if (k < us.length) assert(e.subs[i].includes(k + ' of ' + us.length + (us.length === 1 ? ' apartment' : ' apartments') + ' match'), 'a card counts what matches: ' + e.subs[i]); });
    assert.strictEqual(e.barTop, e.trailH, 'the bar sits right under the top line'); assert(e.fb >= 2, 'a Filter button near the top and one at the list');
    assert.strictEqual(await headOf('r-cost'), 'typical rent ' + money10(f.rent) + ' · total about ' + money10(f.total)); await overflow('experience, filtered'); }
  // a neighborhood where a building has only some apartments passing: the count and the "from" figures are of those that pass
  const part = (() => { for (const h of shownHoods) for (const b of bOf(h.id)) { const ok = b.units.filter(u => passes(fR, u)); if (ok.length && ok.length < b.units.length) return { h, b, ok }; } return null; })();
  if (part) { const { h, b, ok } = part, usH = unitsOfHood(h), okH = usH.filter(u => passes(fR, u)), bsOk = bOf(h.id).filter(x => x.units.some(u => passes(fR, u)));
    await go('#hood-' + slug(h.id)); await showAll();
    const n = await page.evaluate(href => { const a = [...document.querySelectorAll('#sec-places article.bcard')].find(x => x.querySelector('a').getAttribute('href') === href), p = a.querySelector('.pp');
      return { see: document.getElementById('see-places').textContent.replace(/\s+/g, ' ').trim(), head: document.querySelector('#sec-places h2').textContent.replace(/\s+/g, ' ').trim(), cards: document.querySelectorAll('#sec-places article.bcard').length, sub: a.querySelector('.hd small').textContent, rl: p.querySelector('.pp-r .pp-l').textContent, r: p.querySelector('.pp-r b').textContent, t: p.querySelector('.pp-t b').textContent.replace(/\s+/g, ' ').trim(), note: (p.querySelector('.pp-n') || {}).textContent.replace(/ /g, ' '), strip: [...document.querySelectorAll('.sec.head #keyfacts > .kfc')].map(c => c.querySelector('b').textContent.replace(/\s+/g, ' ').trim()), fnote: (document.querySelector('.sec.head .fnote') || {}).textContent || '', hid: (document.querySelector('#sec-places .fhid span') || {}).textContent || '' }; }, '#bldg-' + bSlug(b.units[0]));
    const fu = ok.slice().sort((x, y) => x.all_in - y.all_in)[0], same = ok.length > 1 && ok.every(u => u.all_in === ok[0].all_in && rentOf(u) === rentOf(ok[0]) && rs(u) === rs(ok[0])), fH = figsOf(okH);
    assert(n.see.startsWith('See the ' + bsOk.length + (bsOk.length === 1 ? ' building' : ' buildings')) && n.see.endsWith(okH.length < usH.length ? okH.length + ' of ' + usH.length + ' apartments match' : usH.length + (usH.length === 1 ? ' apartment' : ' apartments')), n.see);
    assert.strictEqual(n.cards, bsOk.length, 'a building is shown when at least one of its apartments passes'); assert(n.head.startsWith(bsOk.length + (bsOk.length === 1 ? ' building' : ' buildings')) && n.head.includes(okH.length + (okH.length === 1 ? ' apartment' : ' apartments')), n.head);
    assert(n.sub.includes(ok.length + ' of ' + b.units.length + ' apartments match'), 'the card gives the reduced count: ' + n.sub);
    assert.strictEqual(n.r, moneyX(rentOf(fu)) + (rs(fu) ? '*' : ''), 'its rent is the rent of the cheapest apartment that passes'); assert.strictEqual(n.t, 'about ' + money10(fu.all_in), 'and its total is that apartment\'s'); assert.strictEqual(n.rl, ok.length > 1 && !same ? 'Rent from' : L_RENT);
    assert(ok.length > 1 ? (same ? / that match$/.test(n.note) : n.note === 'Both for Apartment ' + fu.unit + ', the lowest total of the ' + ok.length + ' that match') : n.note.startsWith('For Apartment ' + fu.unit), 'the note names the apartment: ' + n.note);
    assert.strictEqual(n.strip[0], okH.length > 1 ? money10(fH.rent) : moneyX(fH.rent), 'the neighborhood strip is recomputed over what matches'); assert.strictEqual(n.strip[1], 'about ' + money10(fH.total)); assert(/that match your filters\.$/.test(n.fnote), n.fnote);
    await overflow('neighborhood, filtered'); await page.evaluate(() => window.scrollTo(0, 0)); await shot('p8-neighborhood-filtered', true); await shot('p8-neighborhood-filtered-top');
    // the building itself: the apartments that match are listed, the others wait behind one line, and each says why when shown
    await go('#bldg-' + bSlug(b.units[0]), '.bpage');
    const bp = await page.evaluate(() => ({ sub: document.getElementById('b-sub').textContent, rows: [...document.querySelectorAll('#sec-apts .aptd')].map(d => d.id), hid: (document.querySelector('#apts-hid span') || {}).textContent || '', r: document.querySelector('.bpage .pp-r b').textContent, t: document.querySelector('.bpage .pp-t b').textContent.replace(/\s+/g, ' ').trim(), note: document.querySelector('.bpage .pp-n').textContent.replace(/ /g, ' ') }));
    assert(bp.sub.includes(ok.length + ' of ' + b.units.length + ' apartments match your filters'), bp.sub); assert.deepStrictEqual(bp.rows, ok.map(u => 'apt-' + slug(u.id)), 'only the apartments that match are listed');
    assert.strictEqual(bp.hid, (b.units.length - ok.length) + (b.units.length - ok.length === 1 ? ' more apartment here does' : ' more apartments here do') + ' not match your filters.'); assert.strictEqual(bp.r, moneyX(rentOf(fu)) + (rs(fu) ? '*' : '')); assert.strictEqual(bp.t, 'about ' + money10(fu.all_in)); assert(/match your filters$|^For Apartment/.test(bp.note), bp.note);
    await page.click('#apts-hid button'); const outs = await page.evaluate(() => [...document.querySelectorAll('#sec-apts .apt')].map(a => ({ id: a.querySelector('details').id, out: (a.querySelector('summary .ac.out') || {}).textContent || '' })));
    assert.deepStrictEqual(outs.map(o => o.id), b.units.map(u => 'apt-' + slug(u.id)), '"Show them" lists every apartment of the building');
    b.units.forEach((u, i) => { if (passes(fR, u)) assert.strictEqual(outs[i].out, ''); else assert.strictEqual(outs[i].out, 'Outside your filters: rent ' + moneyX(rentOf(u)) + ' is over ' + moneyX(RMAX) + '.', 'an apartment outside the filters says why'); });
    // an apartment opened by its own link is shown even when it does not match
    { const uOut = b.units.find(u => !passes(fR, u)); await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); await page.evaluate(h => { location.hash = h; }, '#unit-' + slug(uOut.id)); await page.waitForSelector('.bpage');
      assert(await page.evaluate(s => { const d = document.querySelector(s); return !!d && d.open; }, aptSel(uOut)), 'a link to an apartment outside the filters still opens it'); } }
  // a neighborhood with nothing left: a plain message and a way out, never a blank page
  const hNone8 = shownHoods.find(h => !unitsOfHood(h).some(u => passes(fR, u)));
  if (hNone8) { await go('#hood-' + slug(hNone8.id)); const em = await page.evaluate(() => ({ n: document.querySelectorAll('#view .fempty').length, text: (document.querySelector('#view .fempty') || {}).innerText || '', btns: [...document.querySelectorAll('#view .fempty button')].map(b => b.textContent.trim() + '|' + Math.round(b.getBoundingClientRect().height)), h1: document.querySelector('.ph1').textContent.trim(), cards: document.querySelectorAll('#sec-places article.bcard').length, about: !!document.getElementById('about') || !!document.getElementById('sec-rows') }));
    assert.strictEqual(em.n, 1, 'one message'); assert(em.text.includes('Nothing here matches your filters.') && em.text.includes(unitsOfHood(hNone8).length + (unitsOfHood(hNone8).length === 1 ? ' apartment' : ' apartments') + ' here without them'), em.text); assert(em.btns[0].startsWith('Clear filters|') && em.btns.every(b => +b.split('|')[1] >= 44), 'a "Clear filters" button: ' + em.btns);
    assert.strictEqual(em.cards, 0); assert(em.h1 && em.about, 'the rest of the page is still there'); await overflow('neighborhood, nothing matches'); await page.evaluate(() => window.scrollTo(0, 0)); await shot('p8-empty-state');
    // "Clear filters" there restores the neighborhood at once
    await page.click('#view .fempty [data-act=filter-clear]'); await page.waitForSelector('#sec-places article.bcard'); assert.strictEqual((await FS()).on, 0); assert(await page.evaluate(() => document.getElementById('fbar').hidden), 'the bar goes when nothing is on');
    assert.strictEqual(await page.locator('#sec-places article.bcard').count(), Math.min(3, bOf(hNone8.id).length), 'clearing restores the buildings');
    await openF(); await setRange('rent', RMAX); await closeF(); }
  // the filters hold across navigation and a reload; nothing is added to the address
  { await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); assert.strictEqual((await FS()).f.rent, RMAX, 'kept across pages'); await page.reload(); await page.waitForSelector('.life');
    const s = await FS(); assert.strictEqual(s.f.rent, RMAX, 'kept across a reload'); assert.strictEqual(s.n, nR); assert(!(await page.evaluate(() => document.getElementById('fbar').hidden))); assert(!/rent|filter|\d{4}/i.test(await page.evaluate(() => location.hash + location.search)), 'nothing about the filters is in the address'); }
  // My list is not filtered unless she asks: every saved apartment stays, and one outside the filters says so
  { await page.click('#tray a'); await page.waitForSelector('#mylist'); assert.deepStrictEqual(await listIds(), all, 'My list is unaffected by the filters'); const outIds = all.filter(id => !passes(fR, unitBy[id]));
    const notes = await page.evaluate(() => [...document.querySelectorAll('#mylist .lrow')].filter(r => r.querySelector('.lout')).map(r => [r.getAttribute('data-id'), r.querySelector('.lout').textContent]));
    assert.deepStrictEqual(notes.map(x => x[0]), outIds, 'a saved apartment outside the filters carries a note'); notes.forEach(x => assert.strictEqual(x[1], 'Outside your filters: rent ' + moneyX(rentOf(unitBy[x[0]])) + ' is over ' + moneyX(RMAX) + '.'));
    await overflow('My list, filtered'); await shot('p8-my-list', true);
    if (outIds.length) { await openF('#view .fbtn'); assert(await page.isVisible('#fs-exps'), 'the experience filter is offered on My list'); assert(!(await page.isChecked('#f-mine')), '"apply to My list" is off by default'); await page.check('#f-mine'); await closeF();
      assert.deepStrictEqual(await listIds(), all.filter(id => passes(fR, unitBy[id])), 'with "apply to My list" on, only the saved apartments that match are listed'); assert.strictEqual((await page.textContent('#list-hid span')).trim(), outIds.length + (outIds.length === 1 ? ' saved apartment is' : ' saved apartments are') + ' hidden by your filters.');
      assert.deepStrictEqual(await saved(), all, 'nothing was taken off the list'); await page.click('#list-hid button'); assert.deepStrictEqual(await listIds(), all, '"Show them" brings them back'); assert.strictEqual((await FS()).f.mine, false); } }
  // a second filter; then one is removed by its chip in the bar
  { await openF('#view .fbtn'); await page.click('#fs-beds label:has(input[value="1"])'); await waitFit(countOf({ rent: RMAX, beds: 1 })); await closeF();
    assert.deepStrictEqual(await page.evaluate(() => [...document.querySelectorAll('#fbar .fchip span')].map(s => s.textContent)), ['Rent up to ' + moneyX(RMAX), '1 bedroom']); assert.strictEqual((await page.textContent('#view .fbtn >> nth=0')).trim(), 'Filter · 2');
    await page.click('#fbar .fchip[data-k=rent]'); await page.waitForFunction(() => document.querySelectorAll('#fbar .fchip').length === 1); const s = await FS(); assert.strictEqual(s.n, countOf({ beds: 1 }), 'removing a chip removes that filter only'); assert.strictEqual(s.on, 1);
    assert(await page.evaluate(() => document.getElementById('fbar').contains(document.activeElement)), 'focus stays in the bar'); assert(/of \d+ apartments match your filters\.$/.test((await page.textContent('#toast')).trim()), 'the new count is announced'); }
  // every filter, one at a time, against the test's own reading of the data
  { await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); await openF('#filterBtn'); await page.click('#fClear'); await waitFit(N_ALL);
    const rng = (await FS()).rng, mv = (await FS()).move.map(m => m[0]), sq = Math.min(rng.sqft.max, Math.max(rng.sqft.min + 50, 700)), mn = Math.max(rng.mins.min, Math.min(rng.mins.max - 5, 30)), tot = Math.max(rng.total.min + 50, rng.total.max - 400), y0 = data.years[0].id, y1x = data.years[1] ? data.years[1].id : y0;
    const radio = (k, v) => page.click(`#fs-${k} label:has(input[value="${v}"])`), tick = id => page.click('label[for="' + id + '"]'), expBox = id => page.evaluate(id => { const e = [...document.querySelectorAll('input[data-k="exps"]')].find(x => x.value === id); e.click(); }, id);
    const cases = [
      ['the total', () => setRange('total', tot), { total: tot }, () => setRange('total', rng.total.max)],
      ['studios', () => radio('beds', '0'), { beds: 0 }, () => radio('beds', 'any')],
      ['one-bedrooms', () => radio('beds', '1'), { beds: 1 }, () => radio('beds', 'any')],
      ['size (unpublished sizes stay)', () => setRange('sqft', sq), { sqft: sq }, null],
      ['size, hiding unpublished', () => tick('f-nosize'), { sqft: sq, nosize: true }, async () => { await tick('f-nosize'); await setRange('sqft', rng.sqft.min); }],
      ['the drive', () => setRange('mins', mn), { mins: mn }, () => setRange('mins', rng.mins.max)],
      ...mv.filter(m => m !== 'any').map(m => ['move-in ' + m, () => radio('move', m), { move: m }, () => radio('move', 'any')]),
      ['parking at the building', () => radio('park', 'at'), { park: 'at' }, null], ['garage or covered', () => radio('park', 'covered'), { park: 'covered' }, () => radio('park', 'any')],
      ['washer and dryer', () => tick('f-wd'), { wd: true }, () => tick('f-wd')], ['nothing left to confirm', () => tick('f-clear'), { clear: true }, () => tick('f-clear')], ['reviews online', () => tick('f-rev'), { rev: true }, () => tick('f-rev')],
      ['one experience', () => expBox(y0), { exps: [y0] }, null], ['two experiences', () => expBox(y1x), { exps: [y0, y1x] }, async () => { await expBox(y0); if (y1x !== y0) await expBox(y1x); }]];
    const seen = [];
    for (const [name, on, f, off] of cases) { await on(); const want = countOf(f); await waitFit(want).catch(async () => { throw new Error('filter "' + name + '": the page says "' + (await fitline()) + '", the data says ' + want); }); assert.strictEqual((await FS()).n, want, name); seen.push(name + ' ' + want); if (off) { await off(); await waitFit(N_ALL).catch(async () => { throw new Error('after undoing "' + name + '": ' + (await fitline())); }); } }
    console.log('filters, each alone (apartments left of ' + N_ALL + '):', seen.join(' | '));
    // the move-in choices are only those that change something: no "by" date that every apartment already meets
    for (const m of mv.filter(x => x !== 'any')) { const c = countOf({ move: m }); assert(c > 0 && c < N_ALL, 'the move-in choice ' + m + ' filters something: ' + c); }
    // an impossible mix: the sheet says nothing matches; the first screen keeps its tiles, says so once, and offers "Clear filters"
    await setRange('rent', rng.rent.min); await setRange('sqft', rng.sqft.max); await setRange('mins', rng.mins.min); await tick('f-nosize'); const fX = { rent: rng.rent.min, sqft: rng.sqft.max, mins: rng.mins.min, nosize: true }, nX = countOf(fX); await waitFit(nX);
    if (nX === 0) { assert.strictEqual((await page.textContent('#fShow')).trim(), 'Nothing matches these. Close'); await closeF();
      const z = await page.evaluate(() => ({ tag: document.getElementById('tagline').textContent.trim(), empty: [...document.querySelectorAll('#view .fempty')].map(e => e.innerText), tiles: document.querySelectorAll('a.life').length, none: document.querySelectorAll('a.life.none').length, zero: [...document.querySelectorAll('a.life .tzero')].map(e => e.textContent) }));
      assert.strictEqual(z.tag, '0 of ' + N_ALL + ' apartments match your filters.'); assert.strictEqual(z.empty.length, 1); assert(z.empty[0].includes('Nothing here matches your filters.'), z.empty[0]); assert.strictEqual(z.tiles, data.years.length, 'the experiences stay in place'); assert.strictEqual(z.none, data.years.length); assert(z.zero.every(t => /Nothing here matches your filters/.test(t)));
      await overflow('first screen, nothing matches'); await shot('p8-empty-state-first-screen');
      // an experience with nothing left: the message, not an empty list
      await go('#exp-' + slug(data.years[0].id)); assert((await page.locator('#view .fempty').count()) >= 1, 'the experience says nothing matches'); assert.strictEqual(await page.locator('#sec-hoods a.hood').count(), 0); await overflow('experience, nothing matches'); await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); }
    else await closeF();
    // "Clear all" in the bar restores everything
    await page.click('#fbar .fb-clear'); await page.waitForFunction(() => document.getElementById('fbar').hidden); const s = await FS(); assert.strictEqual(s.on, 0); assert.strictEqual(s.n, N_ALL); assert.strictEqual(await page.locator('.life.none, #view .fempty').count(), 0, 'clearing restores every experience');
    assert((await page.textContent('#tagline')).trim().startsWith(N_ALL + ' apartments to see'), 'and the first line'); assert.strictEqual((await page.textContent('#foot-filter')).trim(), 'Filter'); assert(/^Filters cleared\. All \d+ apartments are back\.$/.test((await page.textContent('#toast')).trim()));
    const tl = await page.evaluate(() => [...document.querySelectorAll('a.life .cnt b')].map(b => b.textContent)); assert.deepStrictEqual(tl, data.years.map(y => String(unitsOfYear(y).length)), 'and every count'); }
  // the experience filter is offered only where experiences are chosen (the first screen, My list)
  { await go('#hood-' + slug(shownHoods[0].id)); await openF('#filterBtn'); assert(await page.isHidden('#fs-exps'), 'no experience filter inside a neighborhood'); await page.mouse.click(8, 8); await page.waitForSelector('#limsheet:not(.open)'); assert(await page.evaluate(() => !document.getElementById('view').inert), 'a tap on the scrim closes the sheet'); }
  // the old "My limits" stored by an earlier visit become filters (total, drive, size, nothing left to confirm)
  { await page.evaluate(() => { const k = 'lamia-house-hunt-v1', o = JSON.parse(localStorage.getItem(k) || '{}'); delete o.f; o.lim = { cost: 2500, mins: 60, sqft: 600, clear: true }; localStorage.setItem(k, JSON.stringify(o)); }); await page.reload(); await page.waitForSelector('#view .ph1, .life'); const s = await FS();
    assert.deepStrictEqual([s.f.total, s.f.mins, s.f.sqft, s.f.clear], [2500, 60, 600, true], 'old limits carry over'); assert.strictEqual(s.n, countOf({ total: 2500, mins: 60, sqft: 600, clear: true })); await clearF(); assert.strictEqual((await FS()).n, N_ALL); }
  // with storage that throws, the filters still work for the visit
  { const cx = await browser.newContext({ viewport: { width: W, height: VH }, deviceScaleFactor: 1 }), pg = await cx.newPage(), errs = []; pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); pg.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
    await pg.addInitScript(() => { const bad = () => { throw new Error('storage blocked'); }; try { Object.defineProperty(window, 'localStorage', { get: bad, configurable: true }); Object.defineProperty(window, 'sessionStorage', { get: bad, configurable: true }); } catch (e) {} });
    await pg.goto(BASE + '/index.html'); await pg.waitForSelector('#tutCard', { state: 'visible' }); await pg.click('#tutSkip'); await pg.click('#filterBtn'); await pg.waitForSelector('#limsheet.open');
    await pg.evaluate(v => { const e = document.getElementById('f-rent'); e.value = String(v); e.dispatchEvent(new Event('input', { bubbles: true })); e.dispatchEvent(new Event('change', { bubbles: true })); }, RMAX);
    await pg.waitForFunction(t => document.getElementById('tagline').textContent.trim() === t, nR + ' of ' + N_ALL + ' apartments match your filters.'); await pg.click('#fShow'); await pg.click('a.life:not(.none) >> nth=0'); await pg.waitForSelector('.ph1');
    assert.strictEqual(await pg.evaluate(() => window.__houseHunt.filters().n), nR, 'the filter holds across pages without storage'); assert(!(await pg.evaluate(() => document.getElementById('fbar').hidden))); assert.strictEqual(errs.length, 0, 'filters with storage blocked: ' + errs.join(' | ')); await cx.close(); }
  await page.click('#tray a'); await page.waitForSelector('#mylist');
  // copy the tour list: it comes from My list, every saved place
  await page.click('#tray a'); await page.waitForSelector('[data-act=copy]'); await page.click('[data-act=copy]');
  await page.waitForFunction(() => document.getElementById('copyStatus').textContent.length > 0); console.log('copy status:', await page.textContent('#copyStatus'));
  const txt = await page.evaluate(() => window.__houseHunt.tourText()); assert(txt.includes(star.tour_questions[0])); for (const id of all) assert(txt.includes(unitBy[id].building || String(unitBy[id].address).split(',')[0]), 'every saved place is in the tour list');
  assert.strictEqual((txt.match(/^\d+\. /gm) || []).length, all.length);
  if ((star.disclosures || []).length) assert(txt.includes('Good to know before you call:'));
  let clip = null; try { clip = await page.evaluate(() => navigator.clipboard.readText()); } catch (e) {} if (clip !== null) assert.strictEqual(clip, txt);

  // ---------- (UI pass 8) the cost breakdown of every apartment: it adds up to the total; a line is marked as the data marks it; a cost that is not published is never $0 ----------
  { const bd = await page.evaluate(async ids => { const out = {};
      for (const [slug, uid, sel] of ids) { if (location.hash !== '#bldg-' + slug) { location.hash = '#bldg-' + slug; await new Promise(r => setTimeout(r, 0)); } const d = document.querySelector(sel); if (!d) { out[uid] = null; continue; }
        out[uid] = { lines: [...d.querySelectorAll('.receipt .ln:not(.tot)')].map(l => ({ name: l.children[0].childNodes[0].textContent.trim(), tag: (l.querySelector('.tg') || {}).textContent || '', amt: l.children[1].textContent.trim(), rent: l.classList.contains('rentln') })), tot: d.querySelector('.receipt .ln.tot').textContent, fn: (d.querySelector('.receipt .fn') || {}).textContent || '', head: d.querySelector('.costhl').textContent, row: d.querySelector('summary .apx').textContent.replace(/\s+/g, ' ').trim(), term: (d.querySelector('summary .apr .rt') || {}).textContent || '', notes: [...d.querySelectorAll('summary .ac.rn')].map(e => e.textContent), cp: (d.querySelector('summary .ac.cp') || {}).textContent || '', sent: d.querySelectorAll('.psent').length }; }
      return out; }, data.units.filter(u => hoodBy[u.hood_id]).map(u => [bSlug(u), u.id, aptSel(u)]));
    const cap = data.meta.cap_all_in || 3000, num = s => +String(s).replace(/[$,]/g, ''); let nUnk = 0, nEst = 0, nCp = 0, n12 = 0, nHigh = 0, nOffer = 0, nTerm = 0;
    for (const u of data.units.filter(x => hoodBy[x.hood_id])) { const r = bd[u.id]; assert(r, 'the apartment has a row: ' + u.id); const L = u.all_in_lines;
      assert.strictEqual(r.lines.length, L.length, 'every cost line is shown: ' + u.id); let sum = 0;
      L.forEach((l, i) => { const x = r.lines[i], unk = l.basis === 'unknown' || l.amount == null;
        if (unk) { nUnk++; assert.strictEqual(x.amt, 'not published', 'a cost that is not published says so: ' + u.id + ' ' + l.line); assert(!/\$/.test(x.amt), 'and is never shown as $0'); }
        else { sum += +l.amount; assert.strictEqual(x.amt, +l.amount === 0 ? 'no charge' : moneyX(l.amount), 'the amount of ' + l.line + ' on ' + u.id); assert.strictEqual(x.tag, l.basis === 'estimate' ? 'estimate' : '', 'a line is marked "estimate" exactly when the data says so: ' + u.id + ' ' + l.line); if (l.basis === 'estimate') nEst++; }
        assert(!/\(est\.?\)/i.test(x.name), 'the mark replaces "(est.)" in the name: ' + x.name); });
      assert(r.lines[0].rent && /^Rent/.test(r.lines[0].name), 'the rent line leads: ' + r.lines[0].name); assert.strictEqual(num(r.lines[0].amt), rentOf(u), 'and its amount is the Rent figure');
      assert.strictEqual(r.tot, L_TOTAL + moneyX(u.all_in), 'the total line is named and exact: ' + r.tot); assert(Math.abs(sum - u.all_in) <= 1, 'the breakdown adds up to the total: ' + sum + ' against ' + u.all_in + ' on ' + u.id);
      assert.strictEqual(r.sent, 1, 'the sentence about the two prices, once');
      const term = /12[- ]month/i.test(L[0].line) ? 'on a 12-month lease' : (/net[- ]effective|offer/i.test(L[0].line) || u.rent.basis_kind === 'net_effective') ? 'with the current offer' : null;
      if (term) { assert.strictEqual(r.term, term, 'the rent says which price it is: ' + u.id); assert(r.head.startsWith('Rent ' + moneyX(rentOf(u)) + (rs(u) ? '*' : '') + ' ' + term + ' · about '), r.head); if (/12/.test(term)) n12++; else nOffer++; } else if (r.term) { nTerm++; assert(/^on an? [\d.]+-month lease$/.test(r.term), 'a listed rent names only a lease length that is not 12 months: ' + r.term); const lm = u.rent.lease_months != null ? u.rent.lease_months : u.cost_check && u.cost_check.lease_term_months; assert(lm != null && Math.round(lm) !== 12, u.id); }
      assert(r.row.startsWith('Rent ' + moneyX(rentOf(u)) + (rs(u) ? '*' : '')) && r.row.endsWith('about ' + m10(u.all_in) + ' ' + WITH_UF), 'both prices on the row: ' + r.row);
      // the 12-month price: the listing's own headline price is said beside it when it differs
      if (/12[- ]month/i.test(L[0].line) && u.rent.listed != null && +u.rent.listed !== rentOf(u)) assert(r.notes.some(x => x.startsWith('The listing shows ' + moneyX(u.rent.listed))), 'the listing\'s own price is given: ' + r.notes);
      // "the 12-month price in this building is much higher than the price shown": directly under the rent, not only in the disclosures
      if ((u.disclosures || []).some(d => /much higher/i.test(d.why || '') || /^lease:sibling/.test(d.code || ''))) { nHigh++; assert(r.notes.some(x => /^The \d+-month price in this building can be much higher than the price shown: ask for it\.$/.test(x)), 'the warning sits under the rent: ' + u.id + ' ' + r.notes); }
      // a cost that is not published could carry the total past the limit: the note is on the total
      const could = (u.all_in_unknown || []).length && ((u.disclosures || []).some(d => /could pass/i.test(d.what || '')) || (u.all_in_likely > cap && u.all_in <= cap));
      if (could) { nCp++; assert(/^Total could pass \$[\d,]+ once .+ (is|are) known$/.test(r.cp), 'the row says the total could pass the limit: ' + r.cp); assert(/The total could pass \$[\d,]+ once/.test(r.fn), 'and so does the breakdown: ' + r.fn); } else assert.strictEqual(r.cp, '');
      if ((u.all_in_unknown || []).length) assert(r.fn.startsWith('Not published, so not in the total:'), r.fn); }
    console.log('cost breakdowns:', Object.keys(bd).length, 'apartments add up;', nUnk, 'lines not published,', nEst, 'estimates,', nCp, 'totals that could pass the limit;', 'rent basis: 12-month', n12 + ', after an offer', nOffer + ', other lease length', nTerm + ';', nHigh, 'with "12-month price much higher"'); }
  // (independent check 4) D5: a fact that is the open question is never stated as a fact; D25: plain sentences; D24: no internal wording on any page
  { const openE = best.find(u => bUnits(u).some(x => x.confirm.asterisk && /elevator/i.test(x.confirm.what || ''))), openD = best.find(u => bUnits(u).some(x => x.confirm.asterisk && /\bdogs?\b/i.test(x.confirm.what || '')));
    if (openE) { await go('#bldg-' + bSlug(openE), '.bpage'); const h = await headOf('r-building'); assert(/^elevator not confirmed/.test(h) && !/(^|, )elevator(,|$)/.test(h), 'the building row does not list an elevator that is still to confirm: ' + h); await openRow('r-building'); const t = await page.textContent('#bld-facts'); assert(/Elevator: not confirmed for this apartment/.test(t) && !/Elevator: yes/.test(t), 'nor do the building facts: ' + t.slice(0, 160)); await shot('p8-open-elevator-row'); }
    if (openD) { await go('#bldg-' + bSlug(openD), '.bpage'); assert.strictEqual(await headOf('r-dog'), 'dog policy not confirmed, ask'); const all = await page.evaluate(() => document.getElementById('view').textContent); assert(!/Dogs allowed[;,.]/.test(all) && !/Dogs: yes/.test(all), 'no "Dogs allowed" where the dog policy is the open question'); assert.strictEqual((await page.textContent('.bpage .kstrip > div:last-child b')).trim(), 'Ask', 'the header does not say "Yes" to dogs'); }
    const say = await page.evaluate(() => { const x = window.__houseHunt; return x.say ? x.say() : null; }); if (say) assert.deepStrictEqual(say, { one: 'A one-bedroom of 784 sq ft on floor 3.', studio: 'A studio of 500 sq ft, floor not published.', garage: 'Garage parking; the fee is not published.', garageFee: 'Garage parking, $150 a month.', lot: 'Parking in an open lot, no monthly charge.', none: 'Parking is not published.' }); }
  // ---------- every view renders, collapsed: no side scroll, within 2.2 screens, no crime in the open ----------
  await page.reload(); await page.waitForSelector('#view .ph1, #view .life'); // a fresh visit: no row is remembered as open
  const t0 = Date.now();
  const res = await page.evaluate(async ([ids, LIMS]) => { let worst = 0, n = 0, tall = [], crime = [], maxH = {}, unresolved = [], cutHeads = [], longHeads = 0, heads = 0, dumps = []; const RE = /\bcrimes?\b|violen|burglar|\bthefts?\b|robber|assault|per 1,000/i;
    for (const h of ids) { const t = performance.now(); location.hash = h; await new Promise(r => setTimeout(r, 0)); worst = Math.max(worst, performance.now() - t); n++;
      if (location.hash !== '#' + h) { unresolved.push(h); continue; } // two ids that give the same plain hash: the page numbers the second one
      if (document.documentElement.scrollWidth > document.documentElement.clientWidth) return 'overflow at ' + h;
      const kind = h.split('-')[0], f = document.getElementById('foot').getBoundingClientRect(), tr = document.getElementById('trail'), ht = Math.round(f.bottom + window.scrollY - (tr.hidden ? 0 : tr.offsetHeight));
      maxH[kind] = Math.max(maxH[kind] || 0, ht); if (ht > (kind === 'bldg' ? Math.round((2.3 + 0.15 * document.querySelectorAll('#sec-apts .apt').length) * 844) : LIMS[kind])) tall.push(h + ' ' + ht); // a building: 2.3 screens and 0.15 for each apartment row (a row carries one line on the rent offer since pass 6)
      if (document.querySelectorAll('#view .host, #view .who, #view .clampw').length || /your host/i.test(document.getElementById('view').textContent)) return 'a host box at ' + h;
      if (kind === 'unit' && !(document.querySelector('.bpage') && document.querySelectorAll('#sec-apts details.aptd[open]').length === 1)) return 'a place link that does not open its building with one apartment open: ' + h;
      if (kind === 'bldg' && document.querySelectorAll('#sec-apts details[open]').length) return 'an apartment open by default at ' + h;
      if (document.querySelectorAll('#view details.rowd[open]').length) return 'a row is open by default at ' + h;
      // a headline is readable in full while its row is closed: never clipped, never ending in an ellipsis, 64 characters at most
      document.querySelectorAll('#view details.rowd > summary .rh').forEach(e => { if (!e.getClientRects().length) return; const s = e.textContent, cs = getComputedStyle(e); heads++; if (s.length > 44) longHeads++;
        if (/…|\.\.\.$/.test(s) || e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1 || cs.textOverflow === 'ellipsis' || cs.whiteSpace === 'nowrap' || s.length > 64) cutHeads.push(h + ' ' + e.closest('details').id + ': ' + s); });
      // text from a listing is never shown as a dump of fields
      { const dv = document.getElementById('view').textContent, im = /docs\/|\.csv\b|evidence pass|harvest row|why_internal|The car sleeps|Where the car sleeps|\bAn one-bedroom/i.exec(kind === 'unit' ? '' : dv); if (im) dumps.push(h + ' (internal or retired wording): ' + dv.slice(Math.max(0, im.index - 40), im.index + 60)); }
      { const dv = document.getElementById('view').textContent, dm = /totalPrice|\bterm \d+:/.exec(dv); if (dm) dumps.push(h + ': ' + dv.slice(Math.max(0, dm.index - 30), dm.index + 50)); }
      const m = RE.exec(document.getElementById('view').innerText); if (m) crime.push(h + ': ' + document.getElementById('view').innerText.slice(Math.max(0, m.index - 40), m.index + 40).replace(/\s+/g, ' ')); }
    return { n, worst: Math.round(worst), maxH, tall, crime, unresolved, cutHeads, longHeads, heads, dumps }; },
    [[...data.years.map(y => 'exp-' + slug(y.id)), ...data.neighborhoods.filter(h => yearBy[h.year] && h.unit_ids.length).map(h => 'hood-' + slug(h.id)), ...pageBldgs.map(b => 'bldg-' + b.slug), ...data.units.filter(u => hoodBy[u.hood_id]).map(u => 'unit-' + slug(u.id))], { exp: limitOf('experience'), hood: limitOf('neighborhood'), bldg: limitOf('building'), unit: 1e9 }]);
  console.log('all views:', JSON.stringify(res).slice(0, 1500), 'in', Date.now() - t0, 'ms');
  assert(typeof res === 'object', String(res)); assert(res.unresolved.length <= 3, 'hashes the page did not open: ' + res.unresolved);
  // (independent check 4, D21) a neighborhood with no apartment shown (only avoid cards) is not a neighborhood of the page: no page of its own, no mark on the map,
  // in no count; its avoid cards sit under its experience's "Looked good, skipped"
  { const avoidOnly = data.neighborhoods.concat(data.neighborhoods_avoid_only || []).filter(h => !(h.unit_ids || []).length && yearBy[h.year]), real = data.neighborhoods.filter(h => (h.unit_ids || []).length && yearBy[h.year]);
    for (const h of avoidOnly.slice(0, 3)) { await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life'); await page.evaluate(x => { location.hash = x; }, '#hood-' + slug(h.id)); await page.waitForTimeout(120);
      assert(await page.evaluate(() => !!document.querySelector('a.life') && !/None to tour|Nothing to tour here yet/.test(document.getElementById('view').innerText)), 'an avoid-only neighborhood has no page of its own: ' + h.id); }
    await page.evaluate(() => { location.hash = '#lives'; }); await page.waitForSelector('.life');
    assert.strictEqual(await page.evaluate(() => window.__houseHunt.mapHoods()), real.length, 'the map marks only neighborhoods with an apartment shown'); assert((await page.textContent('#tagline')).includes('in ' + real.length + ' neighborhood'), 'and the first line counts the same ' + real.length);
    for (const y of data.years) assert.strictEqual(await page.evaluate(id => window.__houseHunt.mapHoods(id), y.id), listed(y).filter(h => h.unit_ids.length).length, 'the map counts the neighborhoods of ' + y.id + ' as its page does');
    const ao = avoidOnly.find(h => (h.avoid_ids || []).some(id => data.avoid.some(a => a.id === id)));
    if (ao) { await go('#exp-' + slug(ao.year)); await openRow('r-others'); const sk = await page.evaluate(() => ({ names: [...document.querySelectorAll('#skipped .othn')].map(e => e.textContent), cards: document.querySelectorAll('#skipped .unit.avoid').length, links: document.querySelectorAll('#skipped a[href^="#hood-"]').length }));
      const mine = avoidOnly.filter(h => h.year === ao.year && (h.avoid_ids || []).some(id => data.avoid.some(a => a.id === id))); assert.strictEqual(sk.names.length, mine.length, 'each skipped neighborhood is named: ' + sk.names); assert.strictEqual(sk.cards, mine.reduce((n, h) => n + h.avoid_ids.filter(id => data.avoid.some(a => a.id === id)).length, 0), 'with its avoid cards'); assert.strictEqual(sk.links, 0, 'and no link to a page it does not have'); await overflow('experience, skipped open'); }
    console.log('neighborhoods:', real.length, 'with apartments;', avoidOnly.length, 'with avoid cards only (no page, not on the map)'); }
  if (res.tall.length) console.log('pages over the old ceilings, collapsed (measured only, not a failure):', res.tall.length, res.tall.slice(0, 4).join(' | '));
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
    y.host = { intro: 'TEST experience host intro.', walkthrough: ['TEST walkthrough one.', 'TEST walkthrough two.'] }; delete y.day_moments; delete y.about_points; delete h.about_points; // the older shape: no points, no moments
    u.host = { line: 'TEST host line for the place.', catch: 'TEST host catch.' }; delete u.about_building; delete u.about_points; { const vb = (d.buildings || []).find(b => b.id === u.building_id); if (vb) { delete vb.about_building; delete vb.about_points; } } /* the last resort: no About text on the building or the unit, so the host line shows */ d.units.filter(x => x.building_id === u.building_id).forEach(x => { x.headlines = { parking: { subhead: 'TEST parking subhead.' }, building: { subhead: 'The building.' }, cost: { subhead: 'TEST cost subhead: ask about the fee.' } }; });
    // (pass 6) a floor plan and an apartment with no identifier of its own are never shown or counted; no description is marked as featured here
    { const c = JSON.parse(JSON.stringify(u)); d.units.push(Object.assign({}, c, { id: 'test:plan-A1', unit: null }), Object.assign({}, c, { id: 'test-no-unit', unit: '' })); h.unit_ids = (h.unit_ids || []).concat(['test:plan-A1', 'test-no-unit']); (h.described || []).forEach(x => { if (x && typeof x === 'object') delete x.featured; }); }
    // fields the writing agent will send: icon points, the day's moments, a text about the building
    const y2 = d.years.find(x => x.id === h2o.year), h2 = d.neighborhoods.find(x => x.id === h2id), u2 = d.units.find(x => x.id === u2id);
    y2.about_points = [{ icon: 'dog', text: 'TEST point one, with a dog.' }, { icon: 'no-such-icon', text: 'TEST point two, unknown icon.' }, { icon: 'moon', text: 'TEST point about violent crime that must not show.' }, 'TEST point three, a plain string.'];
    y2.day_moments = [{ icon: 'coffee', title: 'TEST morning', text: 'TEST moment one.' }, { icon: 'train', title: 'TEST commute', text: 'TEST moment two.' }];
    h2.about_points = [{ icon: 'park', text: 'TEST hood point.' }]; u2.about_building = 'TEST about the building. It has a second sentence. And a third one.'; { const b2 = (d.buildings || []).find(b => b.id === u2.building_id); if (b2) { b2.about_building = u2.about_building; b2.about_points = [{ icon: 'pool', text: 'TEST building point.' }, { icon: 'warning', text: 'TEST building catch.' }]; b2.contact = { phone: '(555) 010-0100', kind: 'leasing office', note: 'listing-site tracking number (TEST forwarding line)', site: 'https://example.com/own' }; } }
    h2.single_building = true; h2.described = [{ quote: 'TEST second description, which is shorter and comes first but is not the one marked, so it waits in its row.', source: 'TEST two' }, { quote: 'TEST description of the park next door, written long so that the pull quote holds thirty-five words in all and can be measured on a phone to see that it never runs past six lines.', source: 'TEST source', url: 'https://example.com/d', about: 'TEST Park', featured: true }];
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify(d) }); });
  await page2.goto(BASE + '/index.html#hood-' + slug(vh.id)); await page2.waitForSelector('.ph1');
  
  // (pass 6) the floor plan and the apartment without an identifier are not counted, listed or linked; with no description marked as featured there is no pull quote
  { const sb = (await page2.textContent('#see-places')).replace(/\s+/g, ' ').trim(), n = vh.unit_ids.length; assert(sb.endsWith(n + (n === 1 ? ' apartment' : ' apartments')), 'the count leaves the floor plan out: ' + sb); assert.strictEqual(await page2.locator('#pull').count(), 0, 'no description is marked, so no pull quote is shown (never picked by length)');
    assert.strictEqual(await page2.evaluate(() => window.__houseHunt.bldgs().filter(b => b.units.some(id => /^test/.test(id))).length), 0, 'neither sits in a building'); }
  // "About <name>": the made-up intro whole, no host box, nothing clamped
  { const ab = await page2.evaluate(() => ({ h2: document.querySelector('#about h2').textContent, text: document.getElementById('about').textContent, host: document.querySelectorAll('#view .host, #view .clampw, #view [data-act=unclamp]').length }));
    assert.strictEqual(ab.h2, 'About ' + (vh.parent_name && vh.short_name ? vh.short_name : vh.name)); assert.strictEqual(ab.host, 0); assert.strictEqual(ab.text.split('This is a long made-up paragraph').length - 1, 3, 'all of it is shown'); }
  // a written subhead under the built headline, lighter and clamped to two lines; a subhead about crime is not shown
  assert((await page2.textContent('#r-rules > summary .rs')).startsWith('TEST subhead written by hand')); assert.strictEqual(await page2.locator('#r-voices > summary .rs').count(), 0, 'a subhead about crime is dropped');
  const subStyle = await page2.evaluate(() => { const rs = document.querySelector('#r-rules .rs'), rh = document.querySelector('#r-rules .rh'), a = getComputedStyle(rs), b = getComputedStyle(rh); return { subW: +a.fontWeight, headW: +b.fontWeight, lines: Math.round(rs.clientHeight / parseFloat(a.lineHeight)) }; });
  assert(subStyle.headW > subStyle.subW && subStyle.lines <= 2, 'headline strong, subhead lighter and at most two lines: ' + JSON.stringify(subStyle));
  // tolls: the E-ZPass figure, with its note when a mail rate is also present
  { const chips = await page2.textContent('.sec.head #keyfacts'); assert(chips.includes('$14') && !chips.includes('13.50') && chips.includes('NY E-ZPass') && !chips.includes('21.25'), 'E-ZPass figure, to the dollar, with its note: ' + chips);
    await page2.click('#keyfacts [data-act="toll-info"]'); await page2.waitForSelector('#sheet.open'); const sh = await page2.textContent('#sheetBody'); assert(sh.includes('$13.50') && !sh.includes('21.25') && !/by mail/i.test(sh) && /out-of-state tag/.test(sh), 'the exact figure is behind the tap; the by-mail figure is not shown anywhere (it rests on fewer apartments and misleads): ' + sh); await page2.click('#shClose'); await page2.waitForSelector('#sheet:not(.open)'); }
  // resident voices in their row
  assert((await headOf('r-voices', page2)).startsWith('3 positive, 2 negative'), 'the balance leads the headline, then what most of it is about: ' + await headOf('r-voices', page2)); await openRow('r-voices', page2);
  assert.strictEqual(await page2.locator('#no-voices').count(), 0); assert.strictEqual(await page2.locator('#sec-voices .vtheme').count(), 3, 'two themes and the survey heading');
  assert.strictEqual(await page2.locator('#sec-voices > .quote.pos').count(), 1, 'one positive shown against the one negative'); assert.strictEqual(await page2.locator('#sec-voices > .quote.neg').count(), 2);
  assert.strictEqual(await page2.locator('#sec-voices details .quote').count(), 2, 'the other positives are folded'); assert.strictEqual(await page2.locator('#sec-voices .quote a.srcl').count(), 4);
  assert((await page2.textContent('#sec-voices')).includes('Would recommend share: 71%.'));
  if (W === 390 && OUT) { await page2.evaluate(() => window.scrollTo(0, 0)); await page2.screenshot({ path: `${OUT}/ux-07-test-data-host-voice-and-subhead.png` }); }
  // experience: a subhead or promise about crime is not rendered; the host walks her through in a row
  await page2.evaluate(h => { location.hash = h; }, '#exp-' + slug(vh.year)); await page2.waitForSelector('#about');
  { const t = await page2.evaluate(() => document.getElementById('view').innerText); assert(!CRIME.test(t), 'no crime clause from the subhead or the promise'); assert(t.includes('TEST subhead: a quiet town and a train to the city.'), 'the rest of the subhead stays: ' + t.slice(0, 200)); }
  assert(!(await page2.locator('#sec-promise').count()) || !(await page2.textContent('#sec-promise')).includes('TEST promise'), 'a promise about crime is not shown'); assert.deepStrictEqual(await page2.evaluate(() => [...document.querySelectorAll('#sec-day .scene p')].map(p => p.textContent)), ['TEST walkthrough one.', 'TEST walkthrough two.'], 'the walkthrough paragraphs are the cards of the day when the data has no day_moments');
  await page2.evaluate(() => { location.hash = '#lives'; }); await page2.waitForSelector('.life'); assert(!CRIME.test(await page2.evaluate(() => document.getElementById('view').innerText)));
  // building: the text under "About the building", the catch as its own marked line, a written subhead on a row
  await page2.evaluate(h => { location.hash = h; }, '#bldg-' + bSlug(vu)); await page2.waitForSelector('.bpage');
  // (pass 6) the apartment's own line and catch are in its row (the line first, the catch as "To ask"), not under "About the building"; with no text about the building there is no About block
  { const a = await page2.evaluate(s => { const d = document.querySelector(s); return { about: document.querySelectorAll('#about').length, line: (d.querySelector('.rb > .aline') || {}).textContent, katch: (d.querySelector('.rb > .acatch') || {}).textContent, cost: (d.querySelector('.costsub') || {}).textContent, all: document.getElementById('view').textContent, floor: document.querySelectorAll('[id*="test-plan"], [id*="test-no-unit"]').length }; }, '#apt-' + slug(vu.id));
    assert.strictEqual(a.about, 0, 'no About block without text about the building'); assert.strictEqual(a.line, 'TEST host line for the place.'); assert.strictEqual(a.katch, 'To ask: TEST host catch.'); assert.strictEqual(a.cost, 'TEST cost subhead: ask about the fee.', 'the cost subhead sits under "What it costs"');
    assert.strictEqual(a.all.split('TEST host line for the place.').length - 1, 1, 'the line is on the page once'); assert.strictEqual(a.floor, 0, 'no row for the floor plan or the apartment without an identifier'); }
  assert.strictEqual((await page2.textContent('#r-parking .rs')).trim(), 'TEST parking subhead.'); assert.strictEqual(await page2.locator('#r-building > summary .rs').count(), 0, 'a subhead that only repeats the headline is left out');
  // about_points: an icon list, a dot for an unknown key, a point about crime left out; day_moments: its own titles; about_building in place of the host line
  await page2.evaluate(h => { location.hash = h; }, '#exp-' + slug(h2o.year)); await page2.waitForSelector('#about .pts');
  { const pts = await page2.evaluate(() => [...document.querySelectorAll('#about .pts li')].map(li => ({ t: li.textContent, stroke: li.querySelectorAll('svg path, svg rect').length, dot: li.querySelectorAll('svg circle[fill=currentColor]').length })));
    assert.deepStrictEqual(pts.map(p => p.t), ['TEST point one, with a dog.', 'TEST point two, unknown icon.', 'TEST point three, a plain string.'], 'the points, the crime one left out'); assert(pts[0].stroke >= 1 && pts[0].dot === 0, 'a drawn icon for a known key'); assert(pts[1].dot === 1 && pts[2].dot === 1, 'a dot for an unknown or missing key');
    assert.strictEqual(await page2.locator('#about .lead2').count(), 1, 'the written lead stays above the points'); 
    assert.deepStrictEqual(await page2.evaluate(() => [...document.querySelectorAll('#sec-day .scene h3')].map(h => h.textContent.trim())), ['TEST morning', 'TEST commute']); assert.deepStrictEqual(await page2.evaluate(() => [...document.querySelectorAll('#sec-day .scene p')].map(h => h.textContent.trim())), ['TEST moment one.', 'TEST moment two.']);
    // a neighborhood that rests on one building says "1 building" on its card
    { const c = await page2.evaluate(hh => { const a = document.querySelector('#view a.hood[href="' + hh + '"]'); return a ? a.querySelector('.hsub').textContent : null; }, '#hood-' + slug(h2id)); if (c != null) assert(/1 building, \d+ apartments?/.test(c), 'the card says 1 building: ' + c); }
    if (W === 390 && OUT) { await page2.evaluate(() => window.scrollTo(0, 0)); await page2.screenshot({ path: `${OUT}/ux-07b-test-data-about-points.png` }); } }
  await page2.evaluate(h => { location.hash = h; }, '#hood-' + slug(h2id)); await page2.waitForSelector('#about .pts'); assert.strictEqual((await page2.textContent('#about .pts')).trim(), 'TEST hood point.');
  // the pull quote: the first description short enough, with its source and what it is about; the other waits in its row
  { const pq = await page2.evaluate(() => ({ q: document.querySelector('#pull blockquote').textContent, cap: document.querySelector('#pull figcaption').textContent, link: document.querySelector('#pull figcaption a').getAttribute('href'), rest: [...document.querySelectorAll('#sec-described .quote')].map(q => q.textContent) }));
    assert(pq.q.startsWith('TEST description of the park') && pq.cap.includes('TEST source') && pq.cap.includes('about TEST Park') && pq.link === 'https://example.com/d', 'the one marked as featured, not the first or the shortest: ' + JSON.stringify(pq)); assert(pq.rest.length === 1 && pq.rest[0].includes('TEST second description'), 'the other description is in the row, once');
    const lines = await page2.evaluate(() => { const b = document.querySelector('#pull blockquote'); return Math.round(b.getBoundingClientRect().height / parseFloat(getComputedStyle(b).lineHeight)); }); if (W === 390) assert(lines <= 6, 'a 35-word pull quote is at most six lines at 390 px: ' + lines); }
  await page2.evaluate(h => { location.hash = h; }, '#bldg-' + bSlug(u2o)); await page2.waitForSelector('.bpage');
  { const a = await page2.textContent('#about'); assert(a.includes('TEST about the building. It has a second sentence.') && a.includes('And a third one.'), a);
    // the building's own points and contact (buildings[] in the data) are what the page shows
    assert(a.includes('TEST building point.') && (await page2.textContent('#about .catchb p')) === 'TEST building catch.', 'building-level points, the warning one as the catch: ' + a);
    await openRow('r-building', page2); assert.strictEqual((await page2.textContent('#r-building [data-act=contact]')).trim(), 'Phone and hours'); await page2.click('#r-building [data-act=contact]'); await page2.waitForSelector('#sheet.open');
    { const sh = await page2.textContent('#sheetBody'); assert(sh.includes('Listing-site number (forwards to the office)') && !sh.includes('TEST forwarding line') && sh.includes('(555) 010-0100'), sh); assert.strictEqual(await page2.getAttribute('#contact-site', 'href'), 'https://example.com/own', 'the building\'s own site leads'); } await page2.click('#shClose'); await page2.waitForSelector('#sheet:not(.open)'); if (u2o.host && u2o.host.line) assert(!a.includes(u2o.host.line.slice(0, 40)), 'about_building replaces the host line'); }
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
    // The built page carries slimmed data (scripts/build_site.py drops what the template never reads). What it shows must be
    // what the whole data shows: every experience, and a sample of neighborhoods and buildings, with everything opened, sheets included.
    { const routes = ['#lives', ...data.years.map(y => '#exp-' + slug(y.id)), ...shownHoods.filter((h, i) => i % 6 === 0).map(h => '#hood-' + slug(h.id)), ...pageBldgs.filter((b, i) => i % 8 === 0).map(b => '#bldg-' + b.slug)];
      const read = async rs => { const out = {}; for (const h of rs) { location.hash = h; await new Promise(r => setTimeout(r, 25));
          for (let k = 0; k < 20; k++) { const m = [...document.querySelectorAll('#view [data-act=more]')].filter(x => x.getAttribute('data-n') !== '3').pop(); if (!m) break; m.click(); }
          document.querySelectorAll('#view details').forEach(d => { d.open = true; }); let s = document.getElementById('view').innerText;
          document.querySelectorAll('#view [data-act=scale],#view [data-act=contact]').forEach(b => { b.click(); document.querySelectorAll('#sheetBody details').forEach(d => { d.open = true; }); s += '\n@@' + document.getElementById('sheetBody').innerText; });
          const c = document.querySelector('[data-act=close-sheet]'); if (c) c.click(); out[h] = s; } return out; };
      const cx = await browser.newContext({ viewport: { width: 390, height: 844 } }); await cx.addInitScript(seenTut); const a = await cx.newPage(), b = await cx.newPage();
      await a.goto(BASE + '/index.html'); await a.waitForSelector('.life'); await b.goto(BASE + '/dist/index.html'); await b.waitForSelector('.life');
      const full = await a.evaluate(read, routes), slim = await b.evaluate(read, routes), diff = routes.filter(r => full[r] !== slim[r]);
      assert.strictEqual(diff.length, 0, 'the slimmed page reads differently from the whole data on: ' + diff.slice(0, 5).join(', '));
      const whole = Buffer.byteLength(JSON.stringify(data)); console.log(`slimmed data: ${dataBytes} bytes in the page against ${whole} whole (${Math.round(100 - 100 * dataBytes / whole)}% less); same text on ${routes.length} sampled pages`);
      await cx.close(); }
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
      // a first visit to the built page: the tutorial is up; Skip closes it (also when storage throws)
      await pg.waitForSelector('#tutCard', { state: 'visible' }); await pg.click('#tutSkip'); assert(await pg.isHidden('#tutCard'), c.tag + ': the tutorial closes');
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
