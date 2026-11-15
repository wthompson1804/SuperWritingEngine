// Render one URL in headless Chrome (system google-chrome via Node Playwright),
// print JSON summary to stdout, write rendered HTML to argv[3].
// usage: node render.js <url> <out.html>
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs');
(async () => {
  const [url, out] = process.argv.slice(2);
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', proxy: proxy ? { server: proxy } : undefined });
  const page = await browser.newPage();
  const xhr = [];
  page.on('response', r => { const ct = r.headers()['content-type'] || ''; if (ct.includes('json')) xhr.push(r.status() + ' ' + r.url().slice(0, 160)); });
  let status = null, err = null;
  try {
    const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 45000 });
    status = resp ? resp.status() : null;
    await page.waitForTimeout(8000);
  } catch (e) { err = String(e).slice(0, 300); }
  const html = await page.content().catch(() => '');
  fs.writeFileSync(out, html.slice(0, 2 * 1024 * 1024));
  const text = await page.evaluate(() => document.body ? document.body.innerText : '').catch(() => '');
  const dl = await page.evaluate(() => Array.from(document.querySelectorAll('a[href]')).map(a => a.href).filter(h => /\.csv|\.xlsx|\.zip|download/i.test(h))).catch(() => []);
  const prices = (text.match(/\$\s?\d{1,2},\d{3}/g) || []);
  console.log(JSON.stringify({ url, status, err, final_url: page.url(), title: await page.title().catch(() => ''),
    text_len: text.length, n_prices: prices.length, sample_prices: prices.slice(0, 5), text_head: text.slice(0, 300).replace(/\s+/g, ' '), json_xhr: xhr.slice(0, 15), download_links: [...new Set(dl)].slice(0, 20) }));
  await browser.close();
})();
