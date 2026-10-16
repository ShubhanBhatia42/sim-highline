// Share-preview images (1200 x 630) made from the real charts: each card is a title beside a screenshot of the page's own chart. Run after the site is built; writes site/src/og-*.png, which the site build publishes and links from every page.
//   node scripts/build-static.mjs && node scripts/build-highline.mjs && node scripts/build-site.mjs && node scripts/make-og-images.mjs && node scripts/build-site.mjs
import http from "node:http";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { launchOptions } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname, OUT = new URL("../site/src/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css" };
const server = http.createServer(async (req, res) => { const p = decodeURIComponent(new URL(req.url, "http://x").pathname); try { const f = path.join(DIST, p), b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end(); } });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch(launchOptions());
const CARDS = [
  { name: "default", url: "site/index.html", sel: "figure svg", title: "sim-highline", sub: "Every published simulation and observation of a galaxy relation on one plot, with the definitions that decide whether the comparison is fair." },
  { name: "explorer", url: "highline.html#r=gsmf&z=0.1", sel: "#stage", wait: 1200, title: "Explorer", sub: "Look up a relation at any epoch: simulations against observations, each labelled with where it came from." },
  { name: "retune", url: "site/retune.html", sel: ".rt-panel svg", wait: 1500, title: "Turn the physics dials", sub: "Two simulated universes, four feedback dials each. Can one be made to look like the other?" },
  { name: "study-joint", url: "site/study-joint.html", sel: "figure svg", title: "Can retuning make two codes agree?", sub: "After the best possible retuning, IllustrisTNG and SIMBA stay far apart on some properties. The rules were written first." },
];
const shot = async (url, sel, wait) => {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 2, colorScheme: "light" }); const page = await ctx.newPage();
  await page.goto(`${BASE}/${url}`); await page.waitForFunction(() => !document.getElementById("boot")); await page.waitForTimeout(wait || 300);
  const buf = await page.locator(sel).first().screenshot(); await ctx.close(); return buf;
};
const ctx = await browser.newContext({ viewport: { width: 1200, height: 630 } }); const page = await ctx.newPage();
for (const c of CARDS) {
  const img = (await shot(c.url, c.sel, c.wait)).toString("base64");
  await page.setContent(`<!doctype html><meta charset=utf-8><style>
    *{box-sizing:border-box}body{margin:0;width:1200px;height:630px;background:#fff;color:#0c1016;display:grid;grid-template-columns:470px 1fr;font-family:"Source Serif 4",Charter,Georgia,serif}
    .t{padding:56px 40px 48px 56px;display:flex;flex-direction:column;justify-content:space-between;border-right:2px solid #0c1016}
    .k{font:500 17px "IBM Plex Mono",ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:#3d4653}
    h1{font-weight:600;font-size:${c.title.length > 24 ? 50 : 66}px;line-height:1.05;margin:0 0 22px;text-wrap:balance}
    p{margin:0;font-size:25px;line-height:1.4;color:#3d4653}
    .f{font:500 17px "IBM Plex Mono",ui-monospace,monospace;color:#5f6977}
    .c{display:grid;place-items:center;padding:36px;background:#f4f5f7}.c img{max-width:100%;max-height:100%;border:1px solid #c2c9d2;background:#fff}
  </style><div class=t><div class=k>sim-highline</div><div><h1>${c.title}</h1><p>${c.sub}</p></div><div class=f>shubhanbhatia42.github.io/sim-highline</div></div><div class=c><img src="data:image/png;base64,${img}"></div>`);
  await page.waitForTimeout(250);
  await writeFile(path.join(OUT, `og-${c.name}.png`), await page.screenshot({ type: "png" }));
  console.log("wrote site/src/og-" + c.name + ".png");
}
await browser.close(); server.close();
