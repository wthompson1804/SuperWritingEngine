/* Walk-through test for site/map_component.html (the standalone map demo). No server needed.
   Run:  node scripts/map_component_test.js          (screenshots go to site/screens/map_*.png)
   Checks at 390x844 (touch) and 1280x900 (mouse): no console errors, no sideways page scroll, every mark inside
   the frame, zoom to a region, tap a mark in Manhattan and in Jersey City, a tap 18 px off a mark still opens it,
   "See places" calls onSelectHood, year chip, drive-time toggle, keyboard, pinch, reduced motion, card wording. */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const ROOT = path.resolve(__dirname, '..');
const URL = 'file://' + path.join(ROOT, 'site', 'map_component.html');
const OUT = process.env.OUT || path.join(ROOT, 'site', 'screens');
fs.mkdirSync(OUT, { recursive: true });
let fails = 0;
function ok(cond, msg) { if (cond) console.log('  ok   ' + msg); else { fails++; console.log('  FAIL ' + msg); } }

async function run(name, vp, touch) {
  console.log(`\n== ${name} ${vp.width}x${vp.height} ==`);
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: vp, hasTouch: touch, isMobile: touch, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  const errors = [];
  /* the web fonts are the page's own Google Fonts; offline they fail to load and the fallbacks are used */
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.(googleapis|gstatic)|ERR_(FAILED|INTERNET|NAME|CONNECTION|TUNNEL|PROXY)/.test(m.text() + (m.location().url || ''))) errors.push(m.text()); });
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  await page.goto(URL); await page.waitForTimeout(500);
  const M = page.locator('#map-overview');
  const shot = (n, loc) => (loc || M).screenshot({ path: path.join(OUT, `map_${name}_${n}.png`) });
  const noScroll = async (w) => ok(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth), 'no sideways page scroll ' + w);
  const tapAt = async (x, y) => touch ? page.touchscreen.tap(x, y) : page.mouse.click(x, y);
  const centre = async (label) => page.evaluate((label) => {
    const g = [...document.querySelectorAll('#map-overview .hhm-dot')].find(e => e.getAttribute('aria-label').startsWith(label));
    if (!g) return null; const r = g.querySelector('.m').getBoundingClientRect(); return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  }, label);
  const cardName = async () => page.evaluate(() => { const h = document.querySelector('#map-overview .hhm-card h3'); return h ? h.firstChild.textContent : null; });
  const data = await page.evaluate(() => JSON.parse(document.getElementById('hhm-demo-data').textContent));

  await noScroll('at load');
  await shot('01_overview');
  await page.screenshot({ path: path.join(OUT, `map_${name}_00_page.png`) });
  const frame = await page.evaluate(() => {
    const s = document.querySelector('#map-overview .hhm-svg').getBoundingClientRect();
    let out = 0, n = 0; document.querySelectorAll('#map-overview .hhm-dot .m').forEach(e => { n++; const r = e.getBoundingClientRect(); if (r.left < s.left || r.right > s.right || r.top < s.top || r.bottom > s.bottom) out++; });
    return { n, out };
  });
  ok(frame.n === data.neighborhoods.length && frame.out === 0, `${frame.n} marks, ${frame.out} outside the frame at the widest view`);

  /* zoom to the city, tap a Manhattan mark (a crowded tap zooms first, so allow a few taps) */
  await M.locator('[data-region="nyc"]').click(); await page.waitForTimeout(500);
  await shot('02_nyc', M.locator('.hhm-stage'));
  const manh = data.neighborhoods.find(h => /Harlem|Inwood|Washington Heights|Manhattanville|Hamilton Heights|Upper|Chelsea|Village|Midtown/.test(h.name) && h.lat > 40.7 && h.lon > -74.02 && h.lon < -73.9);
  ok(!!manh, 'a Manhattan neighborhood is in the data: ' + (manh && manh.name));
  if (manh) {
    let taps = 0;
    for (; taps < 5 && (await cardName()) !== manh.name; taps++) { const c = await centre(manh.name); await tapAt(c.x, c.y); await page.waitForTimeout(450); }
    ok((await cardName()) === manh.name, `tap opens "${manh.name}" (taps: ${taps})`);
    await shot('03_manhattan_card');
    await noScroll('with the card open');
  }
  /* Jersey City / Hudson waterfront */
  await M.locator('[data-region="hudson"]').click(); await page.waitForTimeout(500);
  const jc = data.neighborhoods.find(h => /Jersey City|Hoboken|Weehawken|Union City|West New York|Bayonne/.test(h.name));
  ok(!!jc, 'a Hudson-waterfront neighborhood is in the data: ' + (jc && jc.name));
  if (jc) {
    let c = await centre(jc.name), taps = 0;
    /* 18 px off the mark: the tap target is 44 px across */
    for (; taps < 5 && (await cardName()) !== jc.name; taps++) { c = await centre(jc.name); await tapAt(c.x + 18, c.y); await page.waitForTimeout(450); }
    ok((await cardName()) === jc.name, `a tap 18 px beside the mark opens "${jc.name}" (taps: ${taps})`);
    await shot('04_hudson_card');
    await M.locator('.hhm-go').click();
    ok((await page.locator('#log-overview').textContent()).includes(jc.id), 'See places calls onSelectHood("' + jc.id + '")');
  }
  if (!touch) { /* drag pans when zoomed */
    await page.evaluate(() => document.querySelector('#map-overview .hhm-svg').scrollIntoView({ block: 'center' }));
    const b = await M.locator('.hhm-svg').boundingBox(); const before = await centre(jc.name);
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2 + 60); await page.mouse.down(); await page.mouse.move(b.x + b.width / 2 - 60, b.y + b.height / 2 + 30, { steps: 5 }); await page.mouse.up();
    const after = await centre(jc.name); ok(Math.abs((after.x - before.x) + 60) < 3, 'mouse drag pans the zoomed map');
  }
  await M.locator('.hhm-reset').click(); await page.waitForTimeout(450);
  ok(await M.locator('.hhm-reset').isHidden(), 'reset returns to the widest view');

  /* card wording for unknown and zero tolls and unknown crime */
  const words = async (id) => page.evaluate((id) => { window.demoMaps[0].select(id); return document.querySelector('#map-overview .hhm-card').innerText; }, id);
  const unk = data.neighborhoods.find(h => h.toll_round_trip == null), zero = data.neighborhoods.find(h => h.toll_round_trip === 0), pos = data.neighborhoods.find(h => h.toll_round_trip > 0), nocr = data.neighborhoods.find(h => h.safety.violent_per_1000 == null);
  if (unk) { const t = await words(unk.id); ok(/Tolls not fully known/i.test(t) && !/\$0/.test(t), 'missing toll reads "Tolls not fully known", never $0'); }
  if (zero) { const t = await words(zero.id); ok(/No tolls/.test(t) && !/\$0/.test(t), 'a toll of zero reads "No tolls"'); }
  if (pos) { const t = await words(pos.id); ok(t.includes('$') && /Jamaica 9\.8|not known yet/.test(t), 'a known toll shows dollars; crime line against Jamaica 9.8'); await shot('05_card_with_toll_and_crime', M.locator('.hhm-card')); }
  if (nocr) { const t = await words(nocr.id); ok(/Crime rates not known yet/.test(t), 'missing crime rates are said to be not known'); }
  await page.evaluate(() => window.demoMaps[0].select(null));

  /* year chip */
  const y = data.years.find(y => data.neighborhoods.filter(h => h.year === y.id).length > 2) || data.years[0];
  await M.locator(`.hhm-chip[data-year="${y.id}"]`).click(); await page.waitForTimeout(250);
  const lit = await M.locator('.hhm-dot:not(.dim)').count();
  ok(lit === data.neighborhoods.filter(h => h.year === y.id).length && (await M.locator(`.hhm-chip[data-year="${y.id}"]`).getAttribute('aria-pressed')) === 'true', `year chip "${y.label}" leaves ${lit} marks lit and dims the rest`);
  await shot('06_year_filter');
  await M.locator(`.hhm-chip[data-year="${y.id}"]`).click();
  ok((await M.locator('.hhm-dot.dim').count()) === 0, 'tapping the chip again shows every year');

  /* drive-time colours */
  await M.locator('[data-mode="drive"]').click(); await page.waitForTimeout(250);
  const leg = await M.locator('.hhm-legend').innerText();
  ok(/30 min or less/.test(leg) && /31 to 60/.test(leg) && /61 to 90/.test(leg) && /91 to 120/.test(leg), 'drive-time legend has the four bands');
  const fills = await page.evaluate(() => [...new Set([...document.querySelectorAll('#map-overview .hhm-dot .m')].map(e => e.getAttribute('fill')))]);
  ok(fills.length <= 6 && fills.length >= 2, 'marks take the band colours: ' + fills.join(' '));
  await shot('07_drive_bands'); await noScroll('in drive-time colours');
  await M.locator('[data-mode="year"]').click();

  /* keyboard */
  await M.locator('.hhm-chip').last().focus(); await page.keyboard.press('Tab');
  let f = await page.evaluate(() => document.activeElement.getAttribute('aria-label'));
  ok(/minutes by car|not known/.test(f || ''), 'Tab reaches a mark: ' + f);
  await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowUp'); await page.waitForTimeout(200);
  const f2 = await page.evaluate(() => document.activeElement.getAttribute('aria-label'));
  ok(f2 && f2 !== f, 'arrow keys move to another mark: ' + f2);
  ok(await page.evaluate(() => document.querySelector('#map-overview .hhm-ring:not(.w)').getAttribute('visibility') === 'visible'), 'focus ring is drawn');
  await page.keyboard.press('Enter'); await page.waitForTimeout(200);
  ok(f2.startsWith(await cardName()), 'Enter opens the focused mark');
  await shot('08_keyboard');
  ok(await page.evaluate(() => document.activeElement.classList.contains('hhm-go')), 'after Enter the focus is on the card\'s See places button');
  await page.keyboard.press('Escape');
  ok((await cardName()) === null && (await page.evaluate(() => document.activeElement.getAttribute('aria-label'))) === f2, 'Escape closes the card and returns to the mark');
  await page.keyboard.press('0'); await page.waitForTimeout(400);

  if (touch) { /* pinch with two fingers */
    await M.locator('.hhm-stage').scrollIntoViewIfNeeded();
    const b = await M.locator('.hhm-svg').boundingBox(), cx = b.x + b.width / 2, cy = b.y + b.height / 2;
    const cdp = await ctx.newCDPSession(page);
    const pts = (d) => [{ x: cx - d, y: cy, id: 1 }, { x: cx + d, y: cy, id: 2 }];
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: pts(30) });
    for (const d of [45, 60, 80, 100]) await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: pts(d) });
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    await page.waitForTimeout(200);
    ok(await M.locator('.hhm-reset').isVisible(), 'two-finger pinch zooms in');
    await shot('09_after_pinch', M.locator('.hhm-stage'));
    await M.locator('.hhm-reset').click(); await page.waitForTimeout(400);
  }
  /* second instance: started inside a year, drive-time colours */
  await page.locator('#map-year').scrollIntoViewIfNeeded();
  await shot('10_inside_a_year', page.locator('#map-year'));
  ok(errors.length === 0, 'no console errors' + (errors.length ? ': ' + errors.join(' | ') : ''));
  await browser.close();
}

async function reduced() {
  console.log('\n== reduced motion ==');
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  const page = await ctx.newPage(); await page.goto(URL); await page.waitForTimeout(300);
  const moved = await page.evaluate(() => { const g = document.querySelector('#map-overview .hhm-geo'), a = g.getAttribute('transform'); document.querySelector('#map-overview [data-region="nyc"]').click(); return a !== g.getAttribute('transform'); });
  ok(moved, 'with reduced motion the zoom is immediate, with no animation frames');
  await browser.close();
}

(async () => {
  await run('phone', { width: 390, height: 844 }, true);
  await run('desktop', { width: 1280, height: 900 }, false);
  await reduced();
  console.log(fails ? `\n${fails} check(s) failed` : '\nall checks passed');
  process.exit(fails ? 1 : 0);
})();
