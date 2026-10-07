// Regenerates the screenshots used on the landing page and in the README (site/src/img/*.png) from the built dist/.
// Run after the build: node scripts/make-screenshots.mjs   (needs `npm install` and `npx playwright install chromium`).
import http from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const DIST = new URL("../dist/", import.meta.url).pathname, OUT = new URL("../site/src/img/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv" };
const server = http.createServer(async (req, res) => { const p = decodeURIComponent(new URL(req.url, "http://x").pathname); try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p); const b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end(); } });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();
async function shot(name, url, { scheme = "light", w = 1440, h = 900, prep } = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  await page.goto(BASE + url, { waitUntil: "load" });
  await page.waitForFunction(() => !document.getElementById("boot"), null, { timeout: 8000 });
  if (prep) await prep(page);
  await page.waitForTimeout(900);
  await page.screenshot({ path: path.join(OUT, name + ".png") });
  await ctx.close();
  console.log("wrote", name + ".png");
}
const openLegend = async page => { if (!(await page.evaluate(() => state.legendOpen))) await page.click("#legTog"); };
for (const scheme of ["light", "dark"]) await shot(`app-${scheme}`, "/highline.html#r=gsmf&z=6", { scheme, prep: openLegend });
await shot("tension-light", "/highline.html#m=tension&tz=0");
await shot("app-phone-light", "/highline.html#r=gsmf&z=6", { w: 390, h: 844 });
await browser.close(); server.close();
