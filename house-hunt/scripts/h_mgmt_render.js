// Headless render helper for the property-management harvest (JS-only price pages).
// usage: node h_mgmt_render.js <jobs.json>
// jobs.json: {"delay_ms": 2500, "wait_ms": 7000, "jobs": [{"url": "...", "out": "/abs/base"}], "capture": "regex", "click": "css"}
// For each job writes <out>.html (rendered DOM), <out>.txt (innerText), <out>.xhr.json (JSON responses whose
// URL matches `capture`), <out>.meta.json (url, final_url, status, retrieved_at). Skips jobs whose meta exists
// unless "refresh": true. Stops the whole run on 403 / 429 or a challenge page (never works around a bot wall).
const { chromium } = require('/opt/node-tools/node_modules/playwright');
const fs = require('fs');
(async () => {
  const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const browser = await chromium.launch({ executablePath: '/usr/bin/google-chrome', proxy: proxy ? { server: proxy } : undefined });
  const ctx = await browser.newContext({ ignoreHTTPSErrors: false, viewport: { width: 1366, height: 2400 } });
  const cap = cfg.capture ? new RegExp(cfg.capture) : null;
  let done = 0;
  for (const job of cfg.jobs) {
    if (!cfg.refresh && fs.existsSync(job.out + '.meta.json')) continue;
    const page = await ctx.newPage();
    const xhr = [];
    page.on('response', async r => {
      try {
        const ct = r.headers()['content-type'] || '';
        if (cap && cap.test(r.url()) && (ct.includes('json') || ct.includes('text'))) {
          const body = await r.text();
          if (body.length < 8 * 1024 * 1024) xhr.push({ url: r.url(), status: r.status(), body });
        }
      } catch (e) { }
    });
    let status = null, err = null;
    try {
      const resp = await page.goto(job.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
      status = resp ? resp.status() : null;
      await page.waitForTimeout(cfg.wait_ms || 7000);
      if (cfg.scroll) { await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await page.waitForTimeout(2500); }
      for (const sel of (cfg.click || [])) {
        const els = await page.$$(sel);
        for (const el of els.slice(0, cfg.max_clicks || 40)) { try { await el.click({ timeout: 2000 }); await page.waitForTimeout(cfg.click_wait_ms || 800); } catch (e) { } }
      }
    } catch (e) { err = String(e).slice(0, 300); }
    const html = await page.content().catch(() => '');
    const text = await page.evaluate(() => document.body ? document.body.innerText : '').catch(() => '');
    const title = await page.title().catch(() => '');
    const meta = { url: job.url, final_url: page.url(), status, err, title, retrieved_at: new Date().toISOString().replace(/\.\d+Z$/, '+00:00'), text_len: text.length, n_xhr: xhr.length };
    const wall = status === 403 || status === 429 || /Just a moment|Access Denied|captcha|Are you a robot|Pardon Our Interruption/i.test(title + ' ' + text.slice(0, 400));
    if (wall && text.length < 3000) {
      meta.wall = true;
      fs.writeFileSync(job.out + '.wall.json', JSON.stringify(meta));
      console.log('BOT WALL, stopping: ' + JSON.stringify(meta));
      await page.close();
      break;
    }
    fs.writeFileSync(job.out + '.html', html.slice(0, 6 * 1024 * 1024));
    fs.writeFileSync(job.out + '.txt', text);
    fs.writeFileSync(job.out + '.xhr.json', JSON.stringify(xhr));
    fs.writeFileSync(job.out + '.meta.json', JSON.stringify(meta));
    done++;
    console.log(`${done} ${status} ${text.length} xhr=${xhr.length} ${job.url}${err ? ' ERR ' + err : ''}`);
    await page.close();
    await new Promise(r => setTimeout(r, cfg.delay_ms || 2500));
  }
  await browser.close();
})();
