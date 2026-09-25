// Renders index.html by calling seek(t) and taking screenshots.
//   node scripts/render.mjs preview        one frame per beat (28) → out/preview/
//   node scripts/render.mjs full           60 fps × 4 subframes      → out/frames/
//   node scripts/render.mjs at 3.25 7.1    arbitrary times           → out/at/
import { createRequire } from 'node:module';
import { mkdirSync, writeFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); }
catch { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const URL = pathToFileURL(resolve(ROOT, 'index.html')).href + '?render=1';
const FPS = 60, SUB = 4, WORKERS = +(process.env.WORKERS || 4);
const [mode = 'preview', ...rest] = process.argv.slice(2);

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1440 }, deviceScaleFactor: 1 });
  await page.goto(URL);
  await page.waitForFunction(() => window.READY === true);
  return page;
}
async function shoot(page, t, file) {
  await page.evaluate(t => window.seek(t), t);
  await page.screenshot({ path: file, clip: { x: 0, y: 0, width: 1440, height: 1440 } });
}

const browser = await chromium.launch();
try {
  if (mode === 'preview' || mode === 'at') {
    const dir = resolve(ROOT, mode === 'at' ? 'out/at' : 'out/preview');
    mkdirSync(dir, { recursive: true });
    // Preview: each beat, 0.32 s in (the state has landed, springs mostly settled).
    const times = mode === 'at' ? rest.map(Number) : Array.from({ length: 28 }, (_, i) => i * 0.5 + 0.32);
    const page = await openPage(browser);
    for (const [i, t] of times.entries()) {
      const name = mode === 'at' ? `t${t.toFixed(3)}.png` : `beat${String(i + 1).padStart(2, '0')}.png`;
      await shoot(page, t, resolve(dir, name));
    }
    console.log(`${times.length} frames → ${dir}`);
  } else if (mode === 'full') {
    const dir = resolve(ROOT, 'out/frames');
    mkdirSync(dir, { recursive: true });
    const sounds = await (await openPage(browser)).evaluate(() => ({ duration: window.DURATION, sounds: window.SOUNDS }));
    writeFileSync(resolve(ROOT, 'out/sounds.json'), JSON.stringify(sounds, null, 1));
    const total = Math.round(sounds.duration * FPS) * SUB;   // t = 14 is t = 0, so it is not rendered twice
    const started = Date.now();
    let done = 0;
    await Promise.all(Array.from({ length: WORKERS }, async (_, w) => {
      const page = await openPage(browser);
      for (let n = w; n < total; n += WORKERS) {
        await shoot(page, n / (FPS * SUB), resolve(dir, `s${String(n).padStart(5, '0')}.png`));
        if (++done % 240 === 0) console.log(`${done}/${total}  ${((Date.now() - started) / 1000).toFixed(0)}s`);
      }
    }));
    console.log(`${total} subframes → ${dir}`);
  } else {
    throw new Error(`unknown mode ${mode}`);
  }
} finally {
  await browser.close();
}
