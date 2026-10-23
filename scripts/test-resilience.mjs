// What happens when things go wrong: broken data says so in words, a relation's data file that is missing, damaged, wrong or slow says so with a way to try again, no JavaScript says so, a lost connection after loading keeps what is loaded working, and blocked web fonts do not break a page.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv" };
let corrupt = false;
let fault = null, held = []; // fault = { rel, mode: "missing" | "damaged" | "wrong" | "stall" } for the Explorer's per-relation data files
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  const dm = p.match(/^\/highline-data\/([a-z0-9-]+)\.json$/);
  if (fault && dm && dm[1] === fault.rel) {
    if (fault.mode === "missing") { res.writeHead(404, { "content-type": "text/plain" }); res.end("not found"); return; }
    if (fault.mode === "stall") { held.push({ res, p }); return; }
    const b = await readFile(path.join(DIST, fault.mode === "wrong" ? "highline-data/gsmf.json" : p));
    res.writeHead(200, { "content-type": "application/json" }); res.end(fault.mode === "damaged" ? b.subarray(0, Math.floor(b.length / 2)) : b); return;
  }
  try {
    const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p); let b = await readFile(f);
    if (corrupt && p === "/highline.html") b = Buffer.from(b.toString().replace('id="curves-data">', 'id="curves-data">{broken'));
    res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b);
  } catch { // like GitHub Pages: the site's own 404.html for any address that does not exist
    res.writeHead(404, { "content-type": "text/html" }); res.end(await readFile(path.join(DIST, "404.html")));
  }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await launchBrowser();
const failures = []; let n = 0;
async function step(name, fn, ctxOpts = {}) {
  n++; const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, ...ctxOpts });
  try { await fn(ctx); } catch (e) { failures.push(`${name}: ${e.message.split("\n")[0]}`); console.log("FAIL", name, "-", e.message.split("\n")[0]); }
  await ctx.close();
}
const ready = p => p.waitForFunction(() => !document.getElementById("boot") && document.querySelectorAll("#stage path").length > 5, null, { timeout: 30000 });

await step("broken data: the Explorer says it could not start, with a way on", async ctx => {
  corrupt = true; const page = await ctx.newPage();
  try { await page.goto(`${BASE}/highline.html`); await page.waitForSelector("#boot.failed", { timeout: 10000 }); } finally { corrupt = false; }
  const t = await page.locator("#boot").innerText();
  assert.match(t, /could not start/); assert.match(t, /data page/);
  assert.equal(await page.locator("#boot a").count(), 2);
});
const releaseHeld = async () => { for (const h of held.splice(0)) { try { h.res.writeHead(200, { "content-type": "application/json" }); h.res.end(await readFile(path.join(DIST, h.p))); } catch { /* the page gave up on it */ } } };
const dataStep = (name, fn) => step(name, async ctx => { try { await fn(ctx); } finally { fault = null; for (const h of held.splice(0)) { try { h.res.destroy(); } catch { /* gone */ } } } });
await dataStep("a relation's data file is missing: the plot area says so, the other relations still work, Try again brings it back", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1`); await ready(page);
  fault = { rel: "sfms", mode: "missing" };
  await page.click("button[data-r=sfms]");
  await page.waitForSelector("#empty .dstat button", { timeout: 10000 });
  const t = await page.locator("#empty .dstat").innerText();
  assert.match(t, /Star-forming main sequence/); assert.match(t, /could not be loaded/); assert.match(t, /404/);
  assert.equal(await page.locator("#stage path").count(), 0, "no stale curves of the previous relation are left under the message");
  await page.click("button[data-r=gsmf]"); await page.waitForFunction(() => document.querySelectorAll("#stage path").length > 5 && /Stellar mass function/.test(document.getElementById("shTitle").textContent));
  await page.click("button[data-r=sfms]"); await page.waitForSelector("#empty .dstat button");
  fault = null; await page.click("#empty .dstat button");
  await page.waitForFunction(() => document.querySelectorAll("#stage path").length > 5 && /main sequence/i.test(document.getElementById("shTitle").textContent) && document.getElementById("empty").hidden, null, { timeout: 15000 });
});
await dataStep("the first relation's data file is damaged: the opening screen says so and Try again starts the Explorer", async ctx => {
  fault = { rel: "sfms", mode: "damaged" };
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=sfms&z=0`);
  await page.waitForSelector("#boot.failed button", { timeout: 15000 });
  const t = await page.locator("#boot").innerText();
  assert.match(t, /could not be loaded/); assert.match(t, /damaged/);
  fault = null; await page.click("#boot button");
  await ready(page);
  assert.match(await page.locator("#shTitle").innerText(), /main sequence/i);
});
await dataStep("a data file that belongs to another version of the page is refused, not drawn", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1`); await ready(page);
  fault = { rel: "size", mode: "wrong" };
  await page.click("button[data-r=size]");
  await page.waitForSelector("#empty .dstat button", { timeout: 10000 });
  assert.match(await page.locator("#empty .dstat").innerText(), /does not belong to this version of the page/);
  assert.equal(await page.locator("#stage path").count(), 0);
});
await dataStep("a slow data file: the page says it is still loading and offers Try again; Try again fetches it again", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1`); await ready(page);
  fault = { rel: "shmr", mode: "stall" };
  await page.click("button[data-r=shmr]");
  assert.match(await page.locator("#empty .dstat").innerText(), /Loading the data for/);
  await page.waitForFunction(() => /Still loading the data/.test(document.querySelector("#empty .dstat")?.textContent || ""), null, { timeout: 15000 });
  assert.equal(await page.locator("#empty .dstat button").count(), 1);
  fault = null; await page.click("#empty .dstat button");
  await page.waitForFunction(() => document.querySelectorAll("#stage path").length > 5 && /halo/i.test(document.getElementById("shTitle").textContent), null, { timeout: 15000 });
});
await dataStep("the views that read many relations fetch them first, and say so when one cannot be had", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1&m=spread`);
  await page.waitForFunction(() => !document.getElementById("boot") && document.querySelectorAll("#spread table.sp td[data-r]").length > 10, null, { timeout: 60000 });
  const page2 = await ctx.newPage(); fault = { rel: "mzr", mode: "missing" };
  await page2.goto(`${BASE}/highline.html#r=gsmf&z=0.1&m=tension`);
  await page2.waitForSelector("#boot.failed button", { timeout: 30000 });
  assert.match(await page2.locator("#boot").innerText(), /could not be loaded/);
  fault = null; await page2.click("#boot button");
  await page2.waitForFunction(() => !document.getElementById("boot") && document.querySelectorAll("#tension td[data-r]").length > 5, null, { timeout: 60000 });
});
await dataStep("leaving a view while its data are on the way: the data arriving later does not pull the visitor back", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1`); await ready(page);
  fault = { rel: "mzr", mode: "stall" };
  await page.click("#mSpread");
  await page.waitForSelector("#spread .dstat", { timeout: 15000 });
  await page.click("#mPlot");
  await page.waitForFunction(() => document.querySelectorAll("#stage path").length > 5 && state.mode === "plot");
  fault = null; await releaseHeld();
  await page.waitForTimeout(1500);
  assert.equal(await page.evaluate(() => state.mode), "plot", "the late data must not switch the view back to the one that was left");
  assert.equal(await page.locator("#spread.on").count(), 0);
  assert.ok(await page.locator("#stage path").count() > 5);
});
await step("no JavaScript: the Explorer says what it needs", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html`);
  assert.match(await page.locator("noscript").first().innerHTML(), /needs JavaScript/);
}, { javaScriptEnabled: false });
await step("connection lost after loading: what is loaded keeps working, a relation not loaded yet says so and recovers", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1`); await ready(page);
  await ctx.setOffline(true);
  await page.evaluate(() => { location.hash = "#r=gsmf&z=2"; });
  await page.waitForFunction(() => /z = 2/.test(document.getElementById("shTitle").textContent));
  await page.click("#mEvol"); await page.waitForTimeout(500);
  assert.ok(await page.locator("#stage path").count() > 3, "still draws the loaded relation after switching view while offline");
  await page.click("#mPlot");
  await page.evaluate(() => { location.hash = "#r=sfms&z=0"; });
  await page.waitForSelector(".dstat button", { timeout: 15000 });
  assert.match(await page.locator(".dstat").innerText(), /could not be loaded/);
  assert.match(await page.locator("#shTitle").innerText(), /main sequence/i, "the title names the relation that is on its way");
  await ctx.setOffline(false);
  await page.click(".dstat button");
  await page.waitForFunction(() => document.querySelectorAll("#stage path").length > 5 && !document.querySelector(".dstat"), null, { timeout: 15000 });
});
await step("connection lost after loading: the dials page keeps working", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/site/retune.html`); await page.waitForSelector(".rt-panel");
  await ctx.setOffline(true);
  await page.click("button:has-text('Make SIMBA look like TNG')"); await page.waitForSelector(".rt-story", { timeout: 10000 });
  assert.match(await page.locator(".rt-story").innerText(), /SIMBA's dials went to/);
});
await step("web fonts blocked: pages still render with readable fallbacks", async ctx => {
  await ctx.route(/fonts\.(googleapis|gstatic)\.com/, r => r.abort());
  const page = await ctx.newPage(); await page.goto(`${BASE}/site/index.html`); await page.waitForSelector("h1");
  const fam = await page.$eval("body", e => getComputedStyle(e).fontFamily);
  assert.match(fam, /sans-serif|serif|system-ui/i, "a generic fallback family is declared");
  assert.ok((await page.locator("h1").boundingBox()).height > 20);
});
await step("reduced motion asked for: nothing animates or slides on any page", async ctx => {
  for (const pg of ["highline.html#r=gsmf&z=0.1", "site/index.html", "site/retune.html", "site/study-joint.html"]) {
    const page = await ctx.newPage(); await page.goto(`${BASE}/${pg}`); await page.waitForTimeout(1200);
    const r = await page.evaluate(() => { const out = new Set(); for (const e of document.querySelectorAll("*")) { const cs = getComputedStyle(e); const nm = e.tagName.toLowerCase() + "." + String(e.className.baseVal ?? e.className).split(" ")[0];
      if (cs.animationName !== "none" && parseFloat(cs.animationDuration) > 0) out.add("animation on " + nm);
      if (parseFloat(cs.transitionDuration) > 0.01 && /transform|all|opacity|top|left|height|width/.test(cs.transitionProperty)) out.add("transition on " + nm + " (" + cs.transitionProperty + ")"); } return [...out]; });
    assert.deepEqual(r, [], `${pg}: ${r.join("; ")}`); await page.close();
  }
}, { reducedMotion: "reduce" });
await step("the content security policy blocks nothing the pages need", async ctx => {
  const bad = [];
  for (const pg of ["highline.html#r=gsmf&z=0.1", "index.html", "site/index.html", "site/retune.html", "site/study-joint.html", "site/data.html", "site/quality.html", "404.html"]) {
    const page = await ctx.newPage(); page.on("console", m => { if (/content security policy|refused to/i.test(m.text())) bad.push(`${pg}: ${m.text().slice(0, 140)}`); });
    await page.route(/fonts\.(googleapis|gstatic)\.com/, r => r.fulfill({ status: 200, contentType: "text/css", body: "" }));
    await page.goto(`${BASE}/${pg}`); await page.waitForTimeout(1500);
    if (pg.startsWith("highline")) { await page.click("button:has-text('Your run')").catch(() => {}); await page.waitForTimeout(300); }
    if (pg.includes("retune")) { await page.click("button:has-text('Make SIMBA look like TNG')"); await page.waitForTimeout(800); }
    await page.close();
  }
  assert.deepEqual(bad, []);
  const h = (await readFile(path.join(DIST, "site/index.html"), "utf8")); assert.match(h, /http-equiv="Content-Security-Policy"/);
  assert.match(h, /script-src 'self' 'sha256-/); assert.doesNotMatch(h.match(/Content-Security-Policy" content="([^"]+)"/)[1], /unsafe-eval|script-src[^;]*unsafe-inline/);
});
await step("an address that does not exist gets a helpful page whose links lead somewhere", async ctx => {
  const page = await ctx.newPage(); const r = await page.goto(`${BASE}/site/deep/no-such-page.html`);
  assert.equal(r.status(), 404);
  assert.match(await page.locator("h1").innerText(), /does not exist/);
  const hrefs = await page.$$eval("main a", as => as.map(a => a.href));
  assert.ok(hrefs.includes(`${BASE}/highline.html`) && hrefs.includes(`${BASE}/site/retune.html`), `links resolve against the site root: ${hrefs.slice(0, 3)}`);
  for (const h of hrefs.filter(h => h.startsWith(BASE))) assert.equal((await ctx.request.get(h)).status(), 200, h);
});
await browser.close(); server.close();
if (failures.length) { console.log(failures.join("\n")); process.exit(1); }
console.log(`resilience: ${n} checks passed (broken data, a relation's data file missing / damaged / wrong / slow, no JavaScript, offline after load, blocked fonts, reduced motion, content security policy, 404 page)`);
