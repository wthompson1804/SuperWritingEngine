// usage: node shoot.js <prefix> <outdir> [open]   (run with NODE_PATH or from house-hunt/)
const { chromium } = require('playwright');
const prefix = process.argv[2], out = process.argv[3], doOpen = process.argv[4] === 'open', W = +(process.env.W || 390);
const slug = id => String(id).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'x';
const years = ['enclave', 'middle', 'new_water', 'pre_car', 'settled', 'space'];
const hoods = (process.env.HOODS || 'ct:stamford,nj:newark,ct:beacon-falls,ct:brookfield,nj:jersey-city-west-side,nj:jersey-city-mcginley-square,ny:bay-ridge,ct:bridgeport,nj:hackensack,ct:hamden,nj:jersey-city-downtown').split(',');
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: W, height: 844 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage(); const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.addInitScript(() => { try { localStorage.setItem('hh-tour-seen', '1'); } catch (e) {} });
  await page.goto('http://localhost:8765/index.html'); await page.waitForSelector('#view .wrap');
  const res = [];
  const full = async (name) => { const h = await page.evaluate(() => document.documentElement.scrollHeight); await page.setViewportSize({ width: W, height: Math.min(h, 9000) }); await page.waitForTimeout(120); await page.screenshot({ path: `${out}/${name}.png` }); await page.setViewportSize({ width: W, height: 844 }); };
  for (const [kind, ids] of [['year', years], ['hood', hoods]]) for (const id of ids) {
    await page.evaluate(x => { location.hash = x; }, '#' + kind + '-' + slug(id)); await page.waitForTimeout(250);
    const dlg = await page.$('.tourcard [data-act], #tour button'); 
    const m = await page.evaluate(() => { const f = document.getElementById('foot').getBoundingClientRect(), t = document.getElementById('trail'); const y = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().bottom + window.scrollY) : null; };
      return { h: Math.round(f.bottom + window.scrollY - (t.hidden ? 0 : t.offsetHeight)), see: y('.seeb'), h1: (document.querySelector('.ph1') || {}).textContent }; });
    res.push([kind, id, m.h, (m.h / 844).toFixed(2), 'see@' + m.see, m.h1]);
    await page.screenshot({ path: `${out}/${prefix}-${kind}-${slug(id)}-fold.png` });
    await full(`${prefix}-${kind}-${slug(id)}`);
    if (doOpen) { await page.evaluate(() => document.querySelectorAll('#view details.rowd').forEach(d => { d.open = true; })); await page.waitForTimeout(150); await full(`${prefix}-${kind}-${slug(id)}-open`); await page.evaluate(() => document.querySelectorAll('#view details.rowd').forEach(d => { d.open = false; })); }
  }
  console.log(res.map(r => r.join(' | ')).join('\n')); if (errs.length) console.log('ERRORS', errs);
  await b.close();
})();
