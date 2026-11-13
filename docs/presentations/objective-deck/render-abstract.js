// Renders abstract.html to ../flame-in-freefall-abstract.pdf (A4).
// Usage: node docs/presentations/objective-deck/render-abstract.js "$PWD/docs/presentations/objective-deck"
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + path.join(dir, 'abstract.html'), { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: path.join(dir, '..', 'flame-in-freefall-abstract.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
  await b.close();
})();
