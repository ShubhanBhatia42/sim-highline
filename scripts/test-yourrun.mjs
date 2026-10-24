// "Check your own run" in a real browser: what was understood, warnings, the plain verdict, fill-in-like presets, the two lists, a shareable link that restores the run, the PNG and CSV exports, the template, the example for several relations,
// and the whole flow from the keyboard. Needs dist/ and Playwright.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv" };
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p); const b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch (e) { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await launchBrowser();
const failures = []; let n = 0;
const settle = page => page.waitForFunction(() => !document.getElementById("boot"), null, { timeout: 15000 });
async function step(name, fn) {
  n++;
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage(); const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  try { await fn(page, ctx); assert.deepEqual(errors, [], "page errors"); } catch (e) { failures.push(`${name}: ${e.message.split("\n")[0]}`); console.log("FAIL", name, "-", e.message.split("\n")[0]); }
  await ctx.close();
}
const open = async (page, hash) => { await page.goto(`${BASE}/highline.html#${hash}`); await settle(page); await page.waitForTimeout(300); };

await step("messy pasted input is understood and the user is told what was read", async page => {
  await open(page, "r=gsmf&z=0.1&pn=mine");
  await page.fill("#uText", "# my run\nlogM;logPhi;err\n8,0;-0,67;0,05\n8,5;-0,92;0,05\n9,0;-1,22;0,05\n9,5;-1,48;0,06\n10,0;-1,70;0,07\n10,5;-2,10;0,10\n11,0;-3,05;0,20\n");
  await page.click("#uPlot");
  const t = await page.locator("#uInfo").innerText();
  assert.match(t, /7 points read/); assert.match(t, /error column used/);
  assert.equal(await page.locator("#stage .userdot").count(), 7);
});

await step("log values with the linear box ticked, and linear values without it, are caught", async page => {
  await open(page, "r=gsmf&z=0.1&pn=mine");
  await page.fill("#uText", "8.0,2.1e-1\n8.5,1.2e-1\n9.0,6.0e-2\n9.5,3.3e-2\n10.0,2.0e-2\n10.5,8.0e-3");
  await page.click("#uPlot");
  assert.match(await page.locator("#uInfo").innerText(), /look linear/i);
});

await step("with no definitions declared the verdict says so, then declaring them yields a plain sentence and two lists", async page => {
  await open(page, "r=gsmf&z=0.1&pn=mine");
  await page.click("#uEx");
  assert.match(await page.locator("#mineTab .sumline").innerText(), /Say what your numbers mean/);
  assert.equal(await page.locator("#mineTab tr.grp").count() >= 1, true, "a group heading is shown");
  // fill in like a published simulation
  const opts = await page.locator("#uLike option").count();
  assert.ok(opts > 3, "published simulations offered to copy definitions from");
  for (let i = 1; i < Math.min(opts, 12); i++) {
    await page.selectOption("#uLike", { index: i });
    if (/Your run is/.test(await page.locator("#mineTab .sumline").innerText())) break;
  }
  const s = await page.locator("#mineTab .sumline").innerText();
  assert.ok(/Your run is|No published curve at this epoch is comparable/.test(s), `a sentence about the offset or why there is none: ${s.slice(0, 80)}`);
  assert.ok((await page.locator("#mineTab .why").count()) >= 1, "reasons are written under curves that are not comparable");
});

await step("the link restores the run and the definitions", async page => {
  await open(page, "r=gsmf&z=0.1&pn=mine");
  await page.click("#uEx");
  await page.selectOption("#uLike", { index: 1 });
  const hash = await page.evaluate(() => mineShareHash());
  assert.ok(hash.includes("run="));
  const name = await page.inputValue("#uName");
  const p2 = await page.context().newPage();
  await p2.goto(`${BASE}/highline.html#${hash}`);
  await settle(p2); await p2.waitForTimeout(400);
  assert.ok((await p2.locator("#stage .userdot").count()) >= 5, "the shared run is drawn");
  assert.equal(await p2.inputValue("#uName"), name);
});

await step("the figure, the comparison and the template download", async page => {
  await open(page, "r=gsmf&z=0.1&pn=mine");
  await page.click("#uEx");
  const [png] = await Promise.all([page.waitForEvent("download", { timeout: 15000 }), page.click("#uPng")]);
  assert.match(png.suggestedFilename(), /^sim-highline-yourrun-gsmf-z.*\.png$/);
  const { size } = await (async () => { const p = await png.path(); const { statSync } = await import("node:fs"); return statSync(p); })();
  assert.ok(size > 8000, `figure is a real image (${size} bytes)`);
  const [csv] = await Promise.all([page.waitForEvent("download"), page.click("#uCsv")]);
  assert.match(csv.suggestedFilename(), /\.csv$/);
  const [tpl] = await Promise.all([page.waitForEvent("download"), page.click("#uTpl")]);
  assert.equal(tpl.suggestedFilename(), "sim-highline-template.csv");
});

await step("the example plots at least five points for every relation in the app", async page => {
  await page.goto(`${BASE}/highline.html#r=gsmf`); await settle(page);
  const rels = await page.evaluate(() => Object.keys(REL));
  assert.ok(rels.length >= 20, `${rels.length} relations`);
  const bad = [];
  for (const rel of rels) {
    await page.goto(`${BASE}/highline.html#r=${rel}&pn=mine`); await page.reload(); await settle(page); await page.waitForTimeout(200);
    if (!(await page.locator("#uEx").count())) { bad.push(`${rel}: no panel`); continue; }
    await page.click("#uEx"); await page.waitForTimeout(120);
    const dots = await page.locator("#stage .userdot").count();
    if (dots < 5) bad.push(`${rel}: ${dots} points`);
  }
  assert.deepEqual(bad, [], "relations where the example fails: " + bad.join("; "));
});

await step("a residual plot appears when a curve is comparable", async page => {
  await open(page, "r=sfms&z=1&pn=mine");
  await page.click("#uEx");
  const n = await page.locator("#uLike option").count();
  let found = false;
  for (let i = 1; i < n && !found; i++) { await page.selectOption("#uLike", { index: i }); found = (await page.locator("#mineTab .v.ok").count()) > 0; }
  assert.ok(found, "some published simulation's definitions make at least one curve comparable");
  assert.equal(await page.locator("#mineTab figure.resid svg").count(), 1, "residual plot");
  assert.ok((await page.locator("#mineTab figure.resid path").count()) >= 1);
});

await step("the whole flow works from the keyboard", async page => {
  await open(page, "r=gsmf&z=0.1");
  await page.focus("#bMine"); await page.keyboard.press("Enter");
  await page.waitForSelector("#uEx");
  await page.focus("#uEx"); await page.keyboard.press("Enter");
  assert.ok((await page.locator("#stage .userdot").count()) >= 5);
  await page.focus("#uCsv");
  const [d] = await Promise.all([page.waitForEvent("download"), page.keyboard.press("Enter")]);
  assert.match(d.suggestedFilename(), /\.csv$/);
  const first = page.locator("#mineTab tr[data-id]").first();
  await first.focus(); await page.keyboard.press("Enter");
  await page.waitForSelector("#panel.open");
  assert.match(await page.locator("#pbody").innerText(), /How sure are we/);
});

await step("what would make more curves fair: the panel's claim is true when that answer is declared, and nothing is applied for the user", async page => {
  for (const [rel, key] of [["gsmf", "densityFrame"], ["sfms", "population"], ["mzr", "metallicityQuantity"]]) {
    const ctx2 = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true }), page = await ctx2.newPage();  // a fresh browser context per relation: definitions declared for one must not carry over to the next
    await open(page, `r=${rel}&z=0.1&pn=mine`);
    await page.click("#uEx");
    if (rel === "gsmf") { await page.selectOption('select[data-def="population"]', "all"); await page.waitForTimeout(200); }  // a mass function needs its population declared as well; no single answer would make a curve fair while two hard keys are open
    const fairCount = () => page.evaluate(() => { let n = 0; for (const tr of document.querySelectorAll("#mineTab tbody tr")) { if (tr.classList.contains("grp")) { if (n || !/^Fair/.test(tr.textContent)) break; continue; } n++; } return /^Fair/.test(document.querySelector("#mineTab tbody tr.grp")?.textContent || "") ? n : 0; });
    const before = await fairCount();
    await page.waitForTimeout(250);
    if (!(await page.locator("#whatif").evaluate(d => d.open))) await page.click("#whatif summary");  // it stays open once opened
    await page.waitForFunction(() => /Nothing here is applied/.test(document.getElementById("whatif")?.innerText || ""), null, { timeout: 5000 });
    const text = await page.locator("#whatif").innerText();
    assert.match(text, /Nothing here is applied for you/, `says it applies nothing (${rel}: ${JSON.stringify(text.slice(0, 200))})`);
    const m = text.match(/If (.+?) is (.+?): (\d+) more curves? becomes? fair/);
    assert.ok(m, `a suggestion is offered for ${rel}: ${text.slice(0, 300)}`);
    const gain = Number(m[3]);
    assert.equal(await fairCount(), before, "opening the panel changes nothing");
    assert.ok(await page.locator(`select[data-def="${key}"]`).count() === 1, "the suggested key has a selector");
    const label = m[2];
    const opt = await page.locator(`select[data-def="${key}"] option`).evaluateAll((os, want) => os.find(o => o.textContent.trim().toLowerCase() === want.toLowerCase())?.value, label);
    assert.ok(opt, `option "${label}" exists for ${key}`);
    await page.selectOption(`select[data-def="${key}"]`, opt);
    await page.waitForTimeout(200);
    { const after = await fairCount(); assert.equal(after - before, gain, `${rel}: declaring ${key} = ${opt} adds exactly the ${gain} curves the panel promised (panel: ${m[0]}; fair before ${before}, after ${after})`); }
    await ctx2.close();
  }
});

await step("what-if: with a declared run the panel speaks of changes to the run, and it stays open across re-renders", async page => {
  await open(page, "r=gsmf&z=0.1&pn=mine");
  await page.click("#uEx");
  const options = await page.locator("#uLike option").evaluateAll(os => os.map(o => o.value).filter(Boolean));
  await page.selectOption("#uLike", options[0]);
  await page.click("#whatif summary");
  assert.match(await page.locator("#whatif").innerText(), /You have declared definitions|No single change/);
  await page.click("#uPlot");
  assert.equal(await page.locator("#whatif").evaluate(d => d.open), true, "stays open after the table is redrawn");
});

await browser.close(); server.close();
if (failures.length) { console.log(failures.join("\n")); process.exit(1); }
console.log(`your run: ${n} browser checks passed`);
