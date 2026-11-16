const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(); const p = await (await b.newContext({ viewport: { width: 390, height: 844 } })).newPage();
  await p.goto('http://localhost:8765/index.html'); await p.waitForSelector('#view .wrap');
  for (const h of ['#exp-enclave', '#hood-ct-stamford']) { await p.evaluate(x => { location.hash = x; }, h); await p.waitForTimeout(300);
    console.log(h, JSON.stringify(await p.evaluate(() => { const o = {}; [...document.querySelectorAll('#view .pg *')].filter(e => e.getClientRects().length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && !e.closest('svg') && !e.closest('.rb')).forEach(e => { const f = parseFloat(getComputedStyle(e).fontSize); (o[f] = o[f] || new Set()).add(e.tagName + '.' + e.className); }); return Object.fromEntries(Object.entries(o).map(([k, v]) => [k, [...v].slice(0, 8)])); }))); }
  await b.close(); })();
