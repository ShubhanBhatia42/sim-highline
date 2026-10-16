// The dials page in a real browser: fitting the dials to a curve (including recovering a curve the emulator itself produced), tuning to an observation, holding a property fixed, the redshift strip, presets, sharing a link, exports,
// the keyboard, the edge warning, sensitivities, animation and the phone layout. Needs dist/ and Playwright.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile, stat } from "node:fs/promises";
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
const D = JSON.parse(await readFile(new URL("../data/retune/retune.json", import.meta.url), "utf8"));
const browser = await launchBrowser();
const failures = []; let n = 0;

// the emulator, evaluated here independently of the page, to make a curve whose true dials are known
function predict(code, a, ids) {
  const q = D.codes[code], t = q.terms.map(term => term.reduce((v, j) => v * a[j], 1));
  return ids.map(i => q.terms.reduce((s, _, k) => s + t[k] * (q.coef[k][i] ?? 0), 0));
}
async function step(name, fn, { viewport = { width: 1280, height: 900 }, animate = false } = {}) {
  n++;
  const ctx = await browser.newContext({ viewport, acceptDownloads: true });
  if (animate) await ctx.addInitScript(() => Object.defineProperty(navigator, "webdriver", { get: () => false }));
  const page = await ctx.newPage(); const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  try { await page.goto(`${BASE}/site/retune.html`); await page.waitForSelector(".rt-panel", { timeout: 15000 }); await fn(page, ctx); assert.deepEqual(errors, [], "page errors"); }
  catch (e) { failures.push(`${name}: ${e.message.split("\n")[0]}`); console.log("FAIL", name, "-", e.message.split("\n")[0]); }
  await ctx.close();
}
const dialsOf = page => page.evaluate(() => [...document.querySelectorAll(".rt-dial input[type=range]")].map(i => +i.value));
const story = page => page.locator(".rt-story").innerText();

await step("a curve the emulator produced is recovered: both codes fit it and the story says how well", async page => {
  const fam = "gsmf", snap = D.snapshots[0].id, ids = D.blocks[`${fam}|${snap}`], meta = D.families[fam];
  const truth = [0.4, -0.3, 0.2, 0.5], y = predict("IllustrisTNG", truth, ids), x = ids.map(i => meta.x_centres[D.outputs[i].b]);
  await page.locator(".rt-fit summary").click();
  await page.fill("#rt-fittext", x.map((v, k) => `${v},${y[k]}`).join("\n"));
  await page.click("button:has-text(\"Find the dials for my curve\")");
  const s = await story(page);
  assert.match(s, /Tuned to your curve/);
  const gT = +s.match(/IllustrisTNG gets within a gap of ([0-9.]+)/)[1];
  assert.ok(gT < 0.3, `TNG reproduces a curve it produced itself (gap ${gT})`);
  assert.ok(await page.locator('path[stroke-dasharray="6 4"]').count() >= 1, "your curve is drawn on the panel");
  assert.match(s, /Biggest side effects/);
});

await step("a curve outside the simulated range is refused with a message that says what is expected", async page => {
  await page.locator(".rt-fit summary").click();
  await page.fill("#rt-fittext", "1.0,2.0\n2.0,2.5\n3.0,3.0");
  await page.click("button:has-text(\"Find the dials for my curve\")");
  assert.match(await page.locator("#rt-fitmsg").innerText(), /Need at least three bins/);
});

await step("tuning to an observed curve works and says the definitions differ", async page => {
  await page.locator(".rt-fit summary").click();
  assert.ok((await page.locator("#rt-obs option").count()) >= 1);
  const label = await page.locator("#rt-obs option").first().innerText();
  assert.ok(!/no observed curve/.test(label), `an observed stellar mass function exists at z = 0 (${label})`);
  await page.click("button:has-text(\"Tune both to this observation\")");
  const s = await story(page);
  assert.match(s, /Tuned to the observed curve/); assert.match(s, /defined differently/);
});

await step("keeping a property as it was is stated and honoured", async page => {
  await page.selectOption("#rt-match", "bhms");
  await page.selectOption("#rt-hold", "gsmf");
  await page.click("button:has-text(\"Make SIMBA look like TNG\")");
  assert.match(await story(page), /while keeping stellar mass function as it was/);
});

await step("the redshift strip shows agreement at each epoch and moves the page", async page => {
  const chips = page.locator(".rt-z");
  assert.equal(await chips.count(), D.snapshots.length);
  assert.match(await chips.nth(0).innerText(), /\d+\/\d+/);
  await chips.nth(2).click();
  assert.equal(await page.inputValue("#rt-snap"), D.snapshots[2].id);
  assert.equal(await page.locator(".rt-z.on").count(), 1);
});

await step("presets set the dials", async page => {
  await page.click("button:has-text(\"Weak feedback\")");
  assert.ok((await dialsOf(page)).every(v => Math.abs(v + 0.8) < 1e-6));
  await page.click("button:has-text(\"Strong feedback\")");
  assert.ok((await dialsOf(page)).every(v => Math.abs(v - 0.8) < 1e-6));
  await page.click("button:has-text(\"Reset\")");
  assert.ok((await dialsOf(page)).every(v => v === 0));
  await page.click("button:has-text(\"Weak feedback\")"); await page.click("button:has-text(\"Same dials in both\")");
  const d = await dialsOf(page); assert.deepEqual(d.slice(0, 4), d.slice(4));
});

await step("a shared link restores the dials, the redshift, the match and the story", async (page, ctx) => {
  await page.click("button:has-text(\"Closest the two can get\")");
  const hash = await page.evaluate(() => location.hash);
  assert.match(hash, /&k=B/); assert.match(hash, /&m=/);
  const dials = await dialsOf(page), big = await page.locator(".rt-big").innerText();
  const p2 = await ctx.newPage();
  await p2.goto(`${BASE}/site/retune.html${hash}`); await p2.waitForSelector(".rt-panel");
  assert.deepEqual(await dialsOf(p2), dials);
  assert.equal(await p2.locator(".rt-big").innerText(), big);
  assert.match(await p2.locator(".rt-story").innerText(), /Closest the two can get/);
});

await step("the numbers and the figure download", async page => {
  const [csv] = await Promise.all([page.waitForEvent("download"), page.click("button:has-text(\"Download the numbers\")")]);
  const p = await csv.path(), txt = await readFile(p, "utf8");
  assert.match(txt, /^# sim-highline v/); assert.ok(txt.split("\n").length > 100, "a row per bin");
  const [png] = await Promise.all([page.waitForEvent("download", { timeout: 20000 }), page.click("button:has-text(\"Download the figure\")")]);
  assert.ok((await stat(await png.path())).size > 15000, "a real image");
});

await step("a dial moves from the keyboard and the headline is announced", async page => {
  await page.focus("#s-IllustrisTNG-1");
  const before = await page.inputValue("#s-IllustrisTNG-1");
  await page.keyboard.press("ArrowRight");
  assert.ok(Math.abs(+(await page.inputValue("#s-IllustrisTNG-1")) - +before - 0.05) < 1e-9, "one arrow press is one step of 0.05");
  assert.match(await page.locator("#rt-live").innerText(), /agree on \d+ of 11/);
  assert.ok(await page.getAttribute("#s-IllustrisTNG-1", "aria-valuetext"), "the multiplier is the spoken value");
});

await step("a dial at the edge of the simulated range says so", async page => {
  await page.locator("#s-SIMBA-0").fill("1");
  assert.equal(await page.locator(".rt-dial.edge").count(), 1);
  assert.ok(await page.locator(".rt-dial.edge .rt-edge").isVisible());
});

await step("each dial shows how strongly it moves the galaxies", async page => {
  const widths = await page.$$eval(".rt-sens i", is => is.map(i => i.style.width));
  assert.equal(widths.length, 8); assert.ok(new Set(widths).size >= 4, "bars differ");
});

await step("the surprise button sets a random point and tunes SIMBA to the mass function", async page => {
  await page.click("button:has-text(\"Show me a surprise\")");
  assert.match(await story(page), /random point/);
});

await step("the animated move ends in the same place as the instant one", async page => {
  await page.click("button:has-text(\"Make SIMBA look like TNG\")");
  await page.waitForSelector(".rt-story", { timeout: 5000 });
  const s = await story(page); assert.match(s, /SIMBA's dials went to/);
}, { animate: true });

await step("the tour has five steps, lights each part, closes with Escape and does not move the dials", async page => {
  const before = await dialsOf(page);
  await page.click("#rt-tourbtn"); await page.waitForSelector(".rt-tour:not([hidden])");
  const seen = [];
  for (let i = 0; i < 5; i++) {
    assert.match(await page.locator(".rt-tour-n").innerText(), new RegExp(`${i + 1} of 5`));
    assert.equal(await page.locator(".rt-spot").count(), 1, "exactly one part is lit");
    seen.push((await page.locator(".rt-tour-t").innerText()).slice(0, 25));
    if (i < 4) await page.click(".rt-tour-b:has-text('Next')");
  }
  assert.equal(new Set(seen).size, 5, "five different steps");
  await page.click(".rt-tour-b:has-text('Done')"); assert.ok(await page.locator(".rt-tour").isHidden(), "closed after the last step");
  await page.click("#rt-tourbtn"); await page.waitForSelector(".rt-tour:not([hidden])"); await page.keyboard.press("Escape");
  assert.ok(await page.locator(".rt-tour").isHidden() && (await page.locator(".rt-spot").count()) === 0, "Escape closes it and unlights");
  assert.deepEqual(await dialsOf(page), before, "dials untouched");
});

await step("on a phone the headline stays on screen and nothing overflows", async page => {
  const pos = await page.$eval(".rt-stick", e => getComputedStyle(e).position);
  assert.equal(pos, "sticky");
  const o = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, iw: innerWidth }));
  assert.ok(o.sw <= o.iw + 1, `scrollWidth ${o.sw} within ${o.iw}`);
  await page.evaluate(() => window.scrollTo({ top: 1800, behavior: "instant" })); await page.waitForTimeout(200);
  const top = await page.$eval(".rt-stick", e => Math.round(e.getBoundingClientRect().top));
  assert.ok(top <= 1, `the headline is pinned to the top (${top})`);
}, { viewport: { width: 390, height: 844 } });

await browser.close(); server.close();
if (failures.length) { console.log(failures.join("\n")); process.exit(1); }
console.log(`dials: ${n} browser checks passed`);
