// Speed budget, measured the way a visitor on a modest phone would meet it: pages are served gzip-compressed (as GitHub Pages does), the network is throttled to a slow 4G connection and the processor to a quarter of this machine's speed.
// Prints the measured numbers and fails if a budget is exceeded. Needs dist/ and Playwright.
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
  { name: "Explorer", url: "/highline.html#r=gsmf&z=0.1", ready: () => !document.getElementById("boot") && document.querySelectorAll("#stage path").length > 5, maxKB: 800, maxMs: 9000 },
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
  const ms = Date.now() - t0, kb = Math.round(Object.values(sizes).reduce((s, v) => s + v, 0) / 1000);
  rows.push(`${b.name}: ${(ms / 1000).toFixed(1)} s to usable, ${kb} kB transferred (budget ${b.maxMs / 1000} s, ${b.maxKB} kB)`);
  if (ms > b.maxMs) failures.push(`${b.name}: ${ms} ms over ${b.maxMs}`);
  if (kb > b.maxKB) failures.push(`${b.name}: ${kb} kB over ${b.maxKB}`);
  await ctx.close();
}
await browser.close(); server.close();
console.log(rows.join("\n"));
if (failures.length) { console.log("OVER BUDGET:\n" + failures.join("\n")); process.exit(1); }
console.log("performance: within budget on slow 4G with a 4x slower processor");
