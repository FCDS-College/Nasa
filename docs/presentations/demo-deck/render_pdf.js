// Renders the demo deck to flame-in-freefall-demo.pdf, one 1920x1080 page per slide.
// Usage (from the repository root): node docs/presentations/demo-deck/render_pdf.js
// Needs Playwright with Chromium, and network access to fonts.googleapis.com for the typefaces.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const dir = __dirname;
const deck = JSON.parse(fs.readFileSync(path.join(dir, 'deck.json'), 'utf8'));
const assets = JSON.parse(fs.readFileSync(path.join(dir, 'assets.json'), 'utf8'));

// The published deck refers to its screenshots by artifact asset URL; locally they live in images/.
let slides = deck.order
  .map((id) => fs.readFileSync(path.join(dir, 'slides', `${id}.html`), 'utf8'))
  .join('\n');
for (const [blob, file] of Object.entries(assets)) slides = slides.split(blob).join(file);

const fonts = Object.values(deck.faces)
  .filter((f) => f.href)
  .map((f) => `<link rel="stylesheet" href="${f.href}">`)
  .join('\n');

const html = `<!doctype html>
<html><head><meta charset="utf-8">
<base href="file://${dir}/">
${fonts}
<link rel="stylesheet" href="deck.css">
<style>
  @page { size: 1920px 1080px; margin: 0 }
  * { margin: 0; animation: none !important }
  body { font: 32px/1.2 sans-serif }
  body > section { width: 1920px; height: 1080px; overflow: hidden; position: relative; isolation: isolate; break-after: page }
  aside { display: none }
  h1 { font-size: 96px; font-weight: 600 } h2 { font-size: 64px; font-weight: 600 } h3 { font-size: 44px; font-weight: 600 }
</style>
</head><body>
${slides}
</body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const tmp = path.join(dir, '.render.html');
  fs.writeFileSync(tmp, html);
  try {
    await page.goto(`file://${tmp}`, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    // The slide format paints backdrops listed before the first flow child underneath it.
    await page.evaluate(() => {
      for (const s of document.querySelectorAll('body > section')) {
        let flow = false;
        for (const c of s.children) {
          if (getComputedStyle(c).position !== 'absolute') flow = true;
          else if (!flow) c.style.zIndex = '-1';
        }
      }
    });
    const out = path.join(dir, 'flame-in-freefall-demo.pdf');
    await page.pdf({ path: out, width: '1920px', height: '1080px', printBackground: true });
    console.log(`wrote ${path.relative(process.cwd(), out)} (${deck.order.length} slides)`);
  } finally {
    fs.unlinkSync(tmp);
    await browser.close();
  }
})();
