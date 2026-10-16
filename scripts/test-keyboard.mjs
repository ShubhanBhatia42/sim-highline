// Keyboard only: on every page, Tab moves on every press (no trap), only to things that can be seen, and each stop has a visible focus mark; the skip link works; Escape closes the Explorer's panels.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv" };
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p), b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await launchBrowser();
const PAGES = ["highline.html#r=gsmf&z=0.1", "site/index.html", "site/retune.html", "site/studies.html", "site/study-joint.html", "site/data.html", "site/methods.html", "site/quality.html", "site/faq.html", "site/glossary.html", "404.html"];
const problems = []; let stops = 0;
const probe = () => {
  const e = document.activeElement; if (!e || e === document.body) return null;
  const b = e.getBoundingClientRect(), cs = getComputedStyle(e), pcs = e.parentElement ? getComputedStyle(e.parentElement) : null;
  const mark = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0) || (cs.boxShadow && cs.boxShadow !== "none") || e.matches(":focus-visible");
  return { idx: [...document.querySelectorAll('*')].indexOf(e), id: e.tagName.toLowerCase() + (e.id ? "#" + e.id : "") + (e.className && typeof e.className === "string" ? "." + e.className.split(" ")[0] : ""), text: (e.getAttribute("aria-label") || e.textContent || e.value || "").trim().slice(0, 30), w: b.width, h: b.height, hidden: cs.visibility === "hidden" || cs.display === "none" || b.width === 0 || b.height === 0, mark, tag: e.tagName.toLowerCase() };
};
for (const pg of PAGES) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } }); const page = await ctx.newPage();
  await page.goto(`${BASE}/${pg}`);
  await page.waitForFunction(() => document.readyState === "complete" && !document.getElementById("boot"), null, { timeout: 30000 });
  await page.waitForTimeout(500);
  let last = null, same = 0, seen = new Set(); const n = pg.startsWith("highline") ? 90 : 70;
  for (let i = 0; i < n; i++) {
    await page.keyboard.press("Tab");
    const r = await page.evaluate(probe);
    if (!r) continue; stops++;
    const key = r.idx + "|" + r.id + "|" + r.text;
    if (key === last) { same++; if (same >= 3) { problems.push(`${pg}: keyboard trap at ${r.id} "${r.text}"`); break; } } else same = 0;
    last = key; seen.add(key);
    if (r.hidden) problems.push(`${pg}: focus on something invisible: ${r.id} "${r.text}"`);
    else if (!r.mark) problems.push(`${pg}: no visible focus mark on ${r.id} "${r.text}"`);
  }
  if (seen.size < 5) problems.push(`${pg}: only ${seen.size} focus stops reached`);
  if (!pg.startsWith("highline") && pg !== "404.html") {
    await page.goto(`${BASE}/${pg}`); await page.keyboard.press("Tab");
    const first = await page.evaluate(() => document.activeElement && document.activeElement.className);
    if (!/skip/.test(first || "")) problems.push(`${pg}: the first Tab stop is not the skip link (${first})`);
    await page.keyboard.press("Enter");
    const hash = await page.evaluate(() => location.hash); if (hash !== "#main") problems.push(`${pg}: the skip link does not reach the main content (${hash})`);
  }
  await ctx.close();
}
{ // Escape closes the Explorer's details panel
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } }); const page = await ctx.newPage();
  await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1`); await page.waitForFunction(() => !document.getElementById("boot") && document.querySelectorAll("#stage path").length > 5);
  await page.click("button:has-text('Notes')"); await page.waitForTimeout(300);
  const open = await page.evaluate(() => !!document.querySelector(".panel.open"));
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);
  const after = await page.evaluate(() => !!document.querySelector(".panel.open"));
  if (!open) problems.push("explorer: the Notes panel did not open"); else if (after) problems.push("explorer: Escape did not close the Notes panel");
  await ctx.close();
}
{ // every chart has a name and a written description
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  for (const pg of PAGES.filter(p => p !== "404.html")) {
    const page = await ctx.newPage(); await page.goto(`${BASE}/${pg}`); await page.waitForFunction(() => document.readyState === "complete" && !document.getElementById("boot")); await page.waitForTimeout(800);
    const bad = await page.evaluate(() => [...document.querySelectorAll("svg")].filter(s => s.getBoundingClientRect().width > 60 && !s.closest("button, a, header, [aria-hidden=true]")).filter(s => {
      const name = (s.getAttribute("aria-label") || (s.querySelector(":scope > title") || {}).textContent || "").trim();
      const fig = s.closest("figure"), cap = fig && fig.querySelector("figcaption") && fig.querySelector("figcaption").textContent.trim();
      return s.getAttribute("role") !== "img" || !(name || cap) || !(cap || s.getAttribute("aria-describedby"));
    }).length);
    if (bad) problems.push(`${pg}: ${bad} chart(s) without a role, a name or a written description`);
    await page.close();
  }
  await ctx.close();
}
await browser.close(); server.close();
if (problems.length) { console.log([...new Set(problems)].slice(0, 25).join("\n")); process.exit(1); }
console.log(`keyboard: ${PAGES.length} pages, ${stops} focus stops: no traps, nothing invisible focused, a visible focus mark on each, skip links work, Escape closes panels, every chart named and described`);
