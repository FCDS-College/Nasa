// Renders deck.html to ../flame-in-freefall-objective-and-problem.pdf (16:9, 10 slides).
// Usage: node docs/presentations/objective-deck/render.js "$PWD/docs/presentations/objective-deck"
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const dir = process.argv[2];
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await p.goto('file://' + path.join(dir, 'deck.html'), { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: path.join(dir, '..', 'flame-in-freefall-objective-and-problem.pdf'), width: '13.333in', height: '7.5in', printBackground: true, preferCSSPageSize: true });
  // overflow check
  const over = await p.evaluate(() => [...document.querySelectorAll('.slide')].map((s, i) => {
    const r = s.getBoundingClientRect(); let worst = 0;
    s.querySelectorAll('*').forEach(e => { if (e.closest('.footer')) return; const b = e.getBoundingClientRect(); worst = Math.max(worst, b.bottom - r.top); });
    return { i: i + 1, contentBottom: Math.round(worst), slideH: Math.round(r.height) };
  }));
  console.log(JSON.stringify(over));
  await b.close();
})();
