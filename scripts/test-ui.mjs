// Browser tests for the built app and site (needs dist/: run scripts/verify-all.sh or the build scripts first, and `npm install` + `npx playwright install chromium`).
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv", ".py": "text/plain", ".bib": "text/plain" };
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p); const b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await chromium.launch();
const failures = [];
let n = 0;
const step = async (name, fn) => { n++; try { await fn(); } catch (e) { failures.push(`${name}: ${e.message.split("\n")[0]}`); console.log("FAIL", name, "-", e.message.split("\n")[0]); } };

async function open(url, { w = 1280, h = 800, scheme = "light", storage } = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
  if (storage) await ctx.addInitScript(s => { try { localStorage.setItem("sh-theme", s); } catch (e) {} }, storage);
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  page.on("console", m => { if (m.type() === "error" && !/fonts\.(googleapis|gstatic)|ERR_(NAME|INTERNET|CONNECTION)|Failed to load resource/.test(m.text())) errors.push(m.text()); });
  await page.goto(BASE + url, { waitUntil: "load" });
  return { page, ctx, errors };
}
const settle = page => page.waitForFunction(() => !document.getElementById("boot"), null, { timeout: 8000 });

await step("app loads with a title, curves, and no errors", async () => {
  const { page, ctx, errors } = await open("/highline.html#r=gsmf&z=6");
  await settle(page);
  assert.equal(await page.textContent("#shTitle"), "Stellar mass function at z = 6");
  assert((await page.locator("#stage path.curve").count()) >= 3, "expected at least three curves");
  assert((await page.locator("#presets button[data-r]").count()) >= 19, "relation rail incomplete");
  assert.deepEqual(errors, []);
  await ctx.close();
});

await step("every relation renders at several epochs without errors", async () => {
  const { page, ctx, errors } = await open("/highline.html");
  await settle(page);
  const res = await page.evaluate(() => {
    const bad = [];
    for (const k of [...document.querySelectorAll("#presets button[data-r]")].map(b => b.dataset.r)) {
      selectRelation(k);
      const st = stops(k);
      for (const i of [0, Math.floor(st.length / 2), st.length - 1]) { state.z = st[i]; renderAll(false); }
      for (const m of ["evol", "plot"]) setMode(m);
      if (!document.getElementById("shTitle").textContent) bad.push(k);
    }
    return bad;
  });
  assert.deepEqual(res, []);
  assert.deepEqual(errors, []);
  await ctx.close();
});

await step("Coverage and Tension are opaque tables with the chart hidden", async () => {
  const { page, ctx } = await open("/highline.html#r=gsmf&z=6");
  await settle(page);
  for (const [btn, sel] of [["#mTension", "#tension"], ["#mAtlas", "#atlas"]]) {
    await page.click(btn);
    const r = await page.evaluate(s => ({ plot: getComputedStyle(document.getElementById("plot")).display, bg: getComputedStyle(document.querySelector(s)).backgroundColor, table: !!document.querySelector(s + " table"), footer: getComputedStyle(document.querySelector("footer")).display }), sel);
    assert.equal(r.plot, "none", `${btn}: chart must be hidden`);
    assert(!/rgba\(0, 0, 0, 0\)/.test(r.bg), `${btn}: table background must be opaque`);
    assert(r.table, `${btn}: table missing`);
    assert.equal(r.footer, "none", `${btn}: slider footer must be hidden`);
  }
  await page.click("#mPlot");
  assert.notEqual(await page.evaluate(() => getComputedStyle(document.getElementById("plot")).display), "none");
  await ctx.close();
});

await step("editing the URL hash updates the view", async () => {
  const { page, ctx } = await open("/highline.html#r=gsmf&z=6");
  await settle(page);
  await page.evaluate(() => { location.hash = "#r=sfms&z=0"; });
  await page.waitForFunction(() => /main sequence/i.test(document.getElementById("shTitle").textContent));
  await ctx.close();
});

await step("theme toggle switches and persists", async () => {
  const { page, ctx } = await open("/highline.html", { scheme: "light" });
  await settle(page);
  await page.click("#bTheme");
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), "dark");
  await page.reload(); await settle(page);
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), "dark");
  await ctx.close();
});

await step("embed mode keeps a tall chart and hides the chrome", async () => {
  const { page, ctx } = await open("/highline.html#r=sfrd&embed=1");
  await settle(page);
  const r = await page.evaluate(() => ({ h: document.getElementById("stage").getBoundingClientRect().height, rail: getComputedStyle(document.getElementById("presets")).display }));
  assert(r.h >= 300, `chart height ${r.h}`);
  assert.equal(r.rail, "none");
  await ctx.close();
});

await step("phone layout: no horizontal overflow, selector instead of rail, tall chart", async () => {
  const { page, ctx } = await open("/highline.html#r=gsmf&z=6", { w: 375, h: 812 });
  await settle(page);
  const r = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, rail: getComputedStyle(document.getElementById("presets")).display, sel: getComputedStyle(document.querySelector(".relsel")).display, h: document.getElementById("stage").getBoundingClientRect().height }));
  assert(r.sw <= 376, `horizontal overflow ${r.sw}px`);
  assert.equal(r.rail, "none"); assert.equal(r.sel, "block");
  assert(r.h >= 300, `chart height ${r.h}`);
  await ctx.close();
});

await step("hovering a legend row emphasises one curve and dims the rest", async () => {
  const { page, ctx } = await open("/highline.html#r=gsmf&z=0");
  await settle(page);
  if (!(await page.evaluate(() => state.legendOpen))) await page.click("#legTog");
  const row = page.locator("#legend [data-s]").nth(1);
  await row.hover();
  const r = await page.evaluate(() => ({ lo: document.querySelectorAll("#stage path.curve.lo").length, hi: document.querySelectorAll("#stage path.curve.hi").length }));
  assert(r.lo + r.hi >= 3, "hover did not change curve emphasis");
  await ctx.close();
});

for (const w of [375, 1280]) for (const f of ["index", "about", "sources", "use-cases"]) await step(`site ${f} at ${w}px: one h1, no horizontal overflow`, async () => {
  const { page, ctx, errors } = await open(`/site/${f}.html`, { w, h: 800 });
  const r = await page.evaluate(() => ({ h1: document.querySelectorAll("h1").length, sw: document.documentElement.scrollWidth, iw: innerWidth }));
  assert.equal(r.h1, 1); assert(r.sw <= r.iw + 1, `overflow ${r.sw} > ${r.iw}`);
  assert.deepEqual(errors, []);
  await ctx.close();
});

await step("links between the site and the app resolve", async () => {
  const { page, ctx } = await open("/site/index.html");
  await page.click("nav a.btn.main");
  await page.waitForURL(/highline\.html/);
  await settle(page);
  await page.click("a.mark");
  await page.waitForURL(/site\/index\.html/);
  await ctx.close();
  const root = await open("/");
  await root.page.waitForURL(/site\/index\.html/);
  await root.ctx.close();
});

// accessibility (axe): serious and critical violations fail the run
const KNOWN = new Set((process.env.AXE_ALLOW || "").split(",").filter(Boolean));
const axeRun = async (name, url, opts) => step(`accessibility: ${name}`, async () => {
  const { page, ctx } = await open(url, opts);
  if (url.startsWith("/highline")) await settle(page);
  const r = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa"]).analyze();
  const bad = r.violations.filter(v => ["serious", "critical"].includes(v.impact) && !KNOWN.has(v.id));
  await ctx.close();
  assert.equal(bad.length, 0, bad.map(v => `${v.id} (${v.impact}, ${v.nodes.length} nodes: ${v.nodes.slice(0, 2).map(x => x.target.join(" ")).join(" | ")})`).join("; "));
});
await axeRun("app, relation view, light", "/highline.html#r=gsmf&z=6");
await axeRun("app, relation view, dark", "/highline.html#r=gsmf&z=6", { scheme: "dark" });
await axeRun("app, tension view", "/highline.html#m=tension&tz=0");
await axeRun("app, coverage view", "/highline.html#m=atlas");
await axeRun("app, evidence panel", "/highline.html#r=gsmf&z=0&sel=chaikin26.colibre.l400m7.gsmf.z0");
for (const f of ["index", "about", "sources", "use-cases"]) { await axeRun(`site ${f}, light`, `/site/${f}.html`); await axeRun(`site ${f}, dark`, `/site/${f}.html`, { scheme: "dark" }); }

await browser.close(); server.close();
if (failures.length) { console.log(`\n${failures.length} of ${n} UI checks failed`); process.exit(1); }
console.log(`UI tests passed: ${n} checks (app, views, themes, embed, phone layout, site, links, accessibility)`);
