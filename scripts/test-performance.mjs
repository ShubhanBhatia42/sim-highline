// Speed budget, measured the way a visitor on a modest phone would meet it: pages are served gzip-compressed (as GitHub Pages does), the network is throttled to a slow 4G connection and the processor to a quarter of this machine's speed.
// Prints the measured numbers and fails if a budget is exceeded. Needs dist/ and Playwright.
// The Explorer fetches its curves one relation at a time (docs/ARCHITECTURE.md): the first row is a visit that opens the largest relation (the stellar mass function), "then" rows add what opening a second relation costs, and the last Explorer row is the view that reads every relation. Budgets are about 15 per cent above what was measured when the lazy loading went in (first visit 799 kB and 7.4 s before it; 225 kB and 3.3 s after, measured on this machine).
import assert from "node:assert/strict";
import http from "node:http";
import zlib from "node:zlib";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import { launchOptions } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv" };
const sizes = {};
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try {
    const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p), b = await readFile(f), z = zlib.gzipSync(b, { level: 9 });
    sizes[p] = z.length;
    res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream", "content-encoding": "gzip", "content-length": z.length }); res.end(z);
  } catch (e) { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch(launchOptions());
const BUDGET = [
  { name: "Explorer", url: "/highline.html#r=gsmf&z=0.1", ready: () => !document.getElementById("boot") && document.querySelectorAll("#stage path").length > 5, maxKB: 260, maxMs: 5000,
    then: { name: "the mass-size relation", select: "size", ready: () => /Mass.size/.test(document.getElementById("shTitle").textContent) && document.querySelectorAll("#stage path").length > 5, maxKB: 80, maxMs: 3000 } },
  { name: "Explorer, disagreement view (reads every relation)", url: "/highline.html#r=gsmf&z=0.1&m=spread", ready: () => !document.getElementById("boot") && document.querySelectorAll("#spread table.sp td[data-r]").length > 10, maxKB: 880, maxMs: 12000 },
  { name: "Front page", url: "/site/index.html", ready: () => document.querySelector("h1") && document.fonts.status !== "loading", maxKB: 60, maxMs: 3500 },
  { name: "Dials page", url: "/site/retune.html", ready: () => document.querySelectorAll(".rt-panel").length >= 10, maxKB: 150, maxMs: 6000 },
  { name: "A study page", url: "/site/study-joint.html", ready: () => document.querySelector("h1"), maxKB: 60, maxMs: 3500 },
];
const failures = []; const rows = [];
for (const b of BUDGET) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.emulateNetworkConditions", { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  for (const k of Object.keys(sizes)) delete sizes[k];
  const t0 = Date.now();
  await page.goto(BASE + b.url, { waitUntil: "commit" });
  await page.waitForFunction(b.ready, null, { timeout: 60000, polling: 100 });
  const paint = await page.evaluate(() => new Promise(res => { const fcp = performance.getEntriesByName("first-contentful-paint")[0]; let lcp = 0; try { new PerformanceObserver(l => { for (const e of l.getEntries()) lcp = e.startTime; }).observe({ type: "largest-contentful-paint", buffered: true }); } catch (e) { /* not supported */ } setTimeout(() => res({ fcp: fcp ? Math.round(fcp.startTime) : null, lcp: Math.round(lcp) }), 300); }));
  const ms = Date.now() - t0, kb = Math.round(Object.values(sizes).reduce((s, v) => s + v, 0) / 1000);
  rows.push(`${b.name}: ${(ms / 1000).toFixed(1)} s to usable, ${kb} kB transferred (budget ${b.maxMs / 1000} s, ${b.maxKB} kB); first paint ${paint.fcp} ms, largest element ${paint.lcp} ms`);
  if (ms > b.maxMs) failures.push(`${b.name}: ${ms} ms over ${b.maxMs}`);
  if (kb > b.maxKB) failures.push(`${b.name}: ${kb} kB over ${b.maxKB}`);
  if (b.then) {
    for (const k of Object.keys(sizes)) delete sizes[k];
    const t1 = Date.now();
    await page.selectOption("#relSel", b.then.select); // the phone layout has the relation menu, not the side list
    await page.waitForFunction(b.then.ready, null, { timeout: 60000, polling: 100 });
    const ms2 = Date.now() - t1, kb2 = Math.round(Object.values(sizes).reduce((s, v) => s + v, 0) / 1000);
    rows.push(`${b.name}, then ${b.then.name}: ${(ms2 / 1000).toFixed(1)} s to drawn, ${kb2} kB transferred (budget ${b.then.maxMs / 1000} s, ${b.then.maxKB} kB)`);
    if (ms2 > b.then.maxMs) failures.push(`${b.name}, then ${b.then.name}: ${ms2} ms over ${b.then.maxMs}`);
    if (kb2 > b.then.maxKB) failures.push(`${b.name}, then ${b.then.name}: ${kb2} kB over ${b.then.maxKB}`);
    if (kb2 < 1) failures.push(`${b.name}, then ${b.then.name}: nothing was fetched, so the measurement is blind`);
  }
  await ctx.close();
}
await browser.close(); server.close();
console.log(rows.join("\n"));
if (failures.length) { console.log("OVER BUDGET:\n" + failures.join("\n")); process.exit(1); }
console.log("performance: within budget on slow 4G with a 4x slower processor");
