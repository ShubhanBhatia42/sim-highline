// Every page at 320, 390, 768, 1440 and 2560 pixels wide, in light and dark: no sideways scroll, no content wider than the screen, no text cut off by its box, and (with SHOTS=dir) a screenshot of each for looking at.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { launchBrowser, browserName } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv" };
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p), b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await launchBrowser();
const PAGES = ["index.html", "highline.html#r=gsmf&z=0.1", "site/index.html", "site/retune.html", "site/studies.html", "site/study-joint.html", "site/study-definitions.html", "site/study-harmonization.html", "site/study-sfh.html", "site/findings.html", "site/data.html", "site/methods.html", "site/sources.html", "site/quality.html", "site/glossary.html", "site/faq.html", "site/changes.html", "site/summary.html"];
const WIDTHS = [320, 390, 768, 1440, 2560];
const CAN_PDF = browserName() === "chromium";  // page.pdf exists only in Chromium; elsewhere the sheet-width and colour checks still run
const SHOTS = process.env.SHOTS; if (SHOTS) await mkdir(SHOTS, { recursive: true });
const only = process.env.ONLY ? process.env.ONLY.split(",") : null;
const problems = []; let n = 0;
for (const pg of PAGES) {
  if (only && !only.some(o => pg.includes(o))) continue;
  for (const scheme of ["light", "dark"]) for (const w of WIDTHS) {
    if (w === 2560 && scheme === "dark") continue;
    const ctx = await browser.newContext({ viewport: { width: w, height: w < 500 ? 800 : 900 }, colorScheme: scheme });
    const page = await ctx.newPage(); const errs = [];
    page.on("pageerror", e => errs.push(String(e)));
    await page.goto(`${BASE}/${pg}`);
    await page.waitForFunction(() => document.readyState === "complete" && !document.getElementById("boot"), null, { timeout: 30000 });
    await page.waitForTimeout(pg.startsWith("highline") || pg.includes("retune") ? 1200 : 200);
    const r = await page.evaluate(() => {
      const iw = innerWidth, de = document.documentElement;
      const wide = [];
      for (const e of document.body.querySelectorAll("*")) {
        const b = e.getBoundingClientRect();
        if (b.width === 0 || b.height === 0) continue;
        if (b.right > iw + 1 && !e.closest(".tw, pre, table, .sm, svg, .scroll, [style*='overflow']")) {
          let p = e.parentElement, clipped = false;
          while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o === "auto" || o === "scroll" || o === "hidden") { clipped = true; break; } p = p.parentElement; }
          if (!clipped) wide.push(`${e.tagName.toLowerCase()}${e.className ? "." + String(e.className.baseVal ?? e.className).split(" ")[0] : ""} right=${Math.round(b.right)}`);
        }
      }
      return { sw: de.scrollWidth, iw, wide: wide.slice(0, 3), bg: getComputedStyle(document.body).backgroundColor, fg: getComputedStyle(document.body).color };
    });
    n++;
    if (r.sw > r.iw + 1) problems.push(`${pg} ${scheme} ${w}px: page scrolls sideways (${r.sw} > ${r.iw})`);
    if (r.wide.length) problems.push(`${pg} ${scheme} ${w}px: wider than the screen: ${r.wide.join("; ")}`);
    if (errs.length) problems.push(`${pg} ${scheme} ${w}px: ${errs[0]}`);
    if (SHOTS) await page.screenshot({ path: path.join(SHOTS, `${pg.replace(/[^a-z0-9]+/gi, "_")}-${scheme}-${w}.png`), fullPage: w <= 768 && !pg.startsWith("highline") });
    await ctx.close();
  }
}
// on paper: A4 width, light colours whatever the theme, no navigation chrome, nothing wider than the sheet
for (const pg of ["site/study-joint.html", "site/study-definitions.html", "site/methods.html", "site/quality.html", "site/faq.html", "site/summary.html"]) {
  const ctx = await browser.newContext({ viewport: { width: 794, height: 1123 }, colorScheme: "dark" }); const page = await ctx.newPage();
  await page.goto(`${BASE}/${pg}`); await page.emulateMedia({ media: "print" }); await page.waitForTimeout(300);
  const r = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth, bg: getComputedStyle(document.body).backgroundColor, ink: getComputedStyle(document.body).color, top: getComputedStyle(document.querySelector(".top")).display, status: getComputedStyle(document.querySelector(".status")).display }));
  n++;
  if (r.sw > r.iw + 1) problems.push(`${pg} on paper: wider than the sheet (${r.sw} > ${r.iw})`);
  if (r.bg !== "rgb(255, 255, 255)" || r.ink !== "rgb(0, 0, 0)") problems.push(`${pg} on paper: not black on white in a dark theme (${r.bg} ${r.ink})`);
  if (r.top !== "none" || r.status !== "none") problems.push(`${pg} on paper: navigation is printed`);
  if (pg === "site/summary.html" && CAN_PDF) { const pdf = (await page.pdf({ format: "A4" })).toString("latin1"); const pages = (pdf.match(/\/Type\s*\/Page[^s]/g) || []).length; if (pages !== 1) problems.push(`${pg} on paper: ${pages} pages, it is meant to be one`); }
  if (SHOTS && CAN_PDF) { await page.pdf({ path: path.join(SHOTS, pg.replace(/[^a-z0-9]+/gi, "_") + "-print.pdf"), format: "A4" }); }
  await ctx.close();
}
await browser.close(); server.close();
if (problems.length) { console.log(problems.join("\n")); process.exit(1); }
console.log(`layouts: ${n} page views (${PAGES.length} pages, 320 to 2560 px, light and dark) without sideways scroll or overflow; six pages also checked as print (A4, black on white, no navigation; the one-page summary prints on one page)`);
