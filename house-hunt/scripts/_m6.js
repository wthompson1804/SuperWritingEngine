// scratch measuring helper for UI pass 6 (not part of the test suite)
const { chromium } = require('playwright');
(async () => {
  const W = +(process.env.W || 390), OUT = process.env.OUT, pages = (process.env.PAGES || '').split(',').filter(Boolean), SHOT = process.env.SHOT;
  const b = await chromium.launch(), ctx = await b.newContext({ viewport: { width: W, height: 844 }, deviceScaleFactor: 1 }), p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(process.env.BASE + '/index.html'); await p.waitForSelector('.life');
  if (process.env.SAVE) await p.evaluate(ids => { localStorage.setItem('lamia-house-hunt-v1', JSON.stringify({ saved: ids.split(',') })); }, process.env.SAVE);
  const all = await p.evaluate(() => ({ exp: [...document.querySelectorAll('a.life')].map(a => a.getAttribute('href')) }));
  const H = async () => p.evaluate(() => { const f = document.getElementById('foot').getBoundingClientRect(), t = document.getElementById('trail'); return Math.round(f.bottom + window.scrollY - (t.hidden ? 0 : t.offsetHeight)); });
  const list = pages.length ? pages : all.exp;
  for (const h of list) { await p.evaluate(x => { location.hash = x; }, h); await p.waitForFunction(x => location.hash === x, h); await p.waitForTimeout(250);
    if (process.env.CLICK) for (const s of process.env.CLICK.split('|')) { await p.click(s).catch(e => console.log('noclick', s)); await p.waitForTimeout(200); }
    const ht = await H(); const see = await p.evaluate(() => { const s = document.querySelector('.seeb'); return s ? Math.round(s.getBoundingClientRect().bottom + scrollY) : null; });
    console.log(h.padEnd(48), ht, (ht / 844).toFixed(2), 'see@' + see);
    if (OUT && SHOT) { const full = await p.evaluate(() => document.documentElement.scrollHeight); await p.setViewportSize({ width: W, height: Math.min(full, 7000) }); await p.waitForTimeout(200); await p.screenshot({ path: `${OUT}/${SHOT}${h.replace(/[^a-z0-9]+/gi, '-')}.png` }); await p.setViewportSize({ width: W, height: 844 }); } }
  if (errs.length) console.log('ERRORS', errs.slice(0, 5));
  await b.close();
})();
