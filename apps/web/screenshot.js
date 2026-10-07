const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('http://localhost:3000/chat', { waitUntil: 'networkidle' });
  await page.screenshot({ path: '/home/belal/.gemini/antigravity-ide/brain/d8abe993-048e-41d5-a064-e2a29d940a2b/scratch/screenshot.png' });
  await browser.close();
})();
