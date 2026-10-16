// Re-renders the product SVG icons (assets/images/products/*.svg) into the
// transparent PNGs used by scripts/image_cards.py. Only needed when a product
// icon is added or changed; the PNGs are committed so CI doesn't need this.
//
//   npm i -g playwright   (or any Playwright install with Chromium)
//   node scripts/card_kit/render_icons.js
//
// The light background rectangle is stripped so the icon sits on a card tile.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const srcDir = path.join(root, 'assets', 'images', 'products');
const outDir = path.join(__dirname, 'icons');

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 600, height: 450 } });
  let n = 0;
  for (const f of fs.readdirSync(srcDir).filter(f => f.endsWith('.svg')).sort()) {
    let svg = fs.readFileSync(path.join(srcDir, f), 'utf8');
    svg = svg.replace(/<rect width="400" height="300" fill="url\(#bg\)"\/>/, '');
    svg = svg.replace('width="400" height="300"', 'width="600" height="450"');
    await page.setContent('<html><body style="margin:0;background:transparent">' + svg + '</body></html>');
    await page.screenshot({ path: path.join(outDir, f.replace('.svg', '.png')), omitBackground: true });
    n++;
  }
  await browser.close();
  console.log('rendered', n, 'icons to', outDir);
})();
