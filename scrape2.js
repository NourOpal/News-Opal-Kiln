const { chromium } = require('playwright');
const fs = require('fs');
const https = require('https');

const TARGETS = [
  ['9c7f6927', 'https://thehill.com/policy/technology/5655028-meta-lawsuit-teen-suicides/'],
  ['7513e094', 'https://www.ucsf.edu/news/2026/01/431366/psychiatrists-hope-chat-logs-can-reveal-secrets-ai-psychosis'],
  ['01b03760', 'https://www.usnews.com/news/health-news/articles/2026-02-13/tween-screen-addiction-linked-to-mental-health-problems-substance-use'],
];

function downloadImage(url, out) {
  return new Promise((resolve, reject) => {
    https.get(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Accept': 'image/*,*/*;q=0.8',
        'Referer': new URL(url).origin + '/',
      },
    }, (res) => {
      if ([301, 302, 308].includes(res.statusCode)) return downloadImage(res.headers.location, out).then(resolve).catch(reject);
      if (res.statusCode !== 200) return reject(new Error(res.statusCode));
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => {
        const buf = Buffer.concat(chunks);
        if (buf.length < 1000) return reject(new Error('small'));
        fs.writeFileSync(out, buf);
        resolve(buf.length);
      });
    }).on('error', reject);
  });
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-sandbox',
    ],
  });
  const ctx = await browser.newContext({
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    viewport: { width: 1366, height: 800 },
    locale: 'en-US',
    timezoneId: 'America/New_York',
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9',
    },
  });
  await ctx.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });

  const got = [];
  for (const [hash, url] of TARGETS) {
    const page = await ctx.newPage();
    try {
      console.log(`Trying ${url.slice(0, 70)}...`);
      await page.goto(url, { timeout: 45000, waitUntil: 'networkidle' });
      // Wait for Cloudflare challenge
      await page.waitForTimeout(8000);

      let og = await page.evaluate(() => {
        const sel = (s) => document.querySelector(s)?.getAttribute('content');
        return sel('meta[property="og:image"]') || sel('meta[name="og:image"]') || sel('meta[name="twitter:image"]');
      });
      if (og && og.startsWith('//')) og = 'https:' + og;
      if (og && og.startsWith('/')) og = new URL(url).origin + og;

      console.log(`  og:image = ${og ? og.slice(0, 80) : 'none'}`);

      if (og) {
        const ext = (og.split('?')[0].match(/\.([a-z]{3,4})$/i) || [, 'jpg'])[1].toLowerCase();
        try {
          const size = await downloadImage(og, `img/${hash}.${ext}`);
          console.log(`  OK ${hash}.${ext} (${size} bytes)`);
          got.push([url, `img/${hash}.${ext}`]);
          continue;
        } catch (e) {
          console.log(`  og dl failed: ${e.message}`);
        }
      }

      // Take screenshot of just the article header area
      const buf = await page.screenshot({ type: 'jpeg', quality: 80, clip: { x: 0, y: 0, width: 1366, height: 750 } });
      // Verify it's not a blank page (should be at least 20KB for content)
      if (buf.length > 20000) {
        fs.writeFileSync(`img/${hash}.jpg`, buf);
        console.log(`  SHOT ${hash}.jpg (${buf.length} bytes)`);
        got.push([url, `img/${hash}.jpg`]);
      } else {
        console.log(`  Blank/blocked screenshot (${buf.length} bytes)`);
      }
    } catch (e) {
      console.log(`  FAIL: ${e.message.slice(0, 100)}`);
    } finally {
      await page.close();
    }
  }
  await browser.close();
  fs.writeFileSync('/tmp/scrape2-got.txt', got.map(([u, p]) => `${u}\t${p}`).join('\n'));
  console.log(`\nGot ${got.length}/${TARGETS.length}`);
})();
