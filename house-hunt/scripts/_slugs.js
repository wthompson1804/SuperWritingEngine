const { chromium } = require('playwright');
(async () => { const b = await chromium.launch(), p = await b.newPage(); await p.goto('http://localhost:8765/index.html'); await p.waitForSelector('.life');
  const r = await p.evaluate(() => { const bs = window.__houseHunt.bldgs(); const one = bs.filter(x => x.units.length === 1), many = bs.filter(x => x.units.length > 2);
    return { tresser: bs.filter(x => /tresser|b_4c467fb1c9/.test(x.slug + x.id)).map(x => x.slug), one: one.slice(0, 4).map(x => x.slug + ' | ' + x.units[0]), many: many.slice(0, 4).map(x => x.slug + ' ' + x.units.length + ' | ' + x.units.slice(0, 4).join(',')) }; });
  console.log(JSON.stringify(r, null, 1)); await b.close(); })();
