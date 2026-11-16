// usage: node scripts/.p5_one.js '#hash' out.png [W] [openAll]
const { chromium } = require('playwright');
(async () => { const W = +(process.argv[4] || 390); const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: W, height: 844 } })).newPage();
  await p.goto('http://localhost:8765/index.html'); await p.waitForSelector('#view .wrap'); await p.evaluate(x => { location.hash = x; }, process.argv[2]); await p.waitForTimeout(400);
  if (process.argv[5]) { await p.evaluate(() => document.querySelectorAll('#view details.rowd').forEach(d => { d.open = true; })); await p.waitForTimeout(200); }
  const h = await p.evaluate(() => document.documentElement.scrollHeight); await p.setViewportSize({ width: W, height: Math.min(h, 9000) }); await p.waitForTimeout(150); await p.screenshot({ path: process.argv[3] }); console.log(h); await b.close(); })();
