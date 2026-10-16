// What happens when things go wrong: broken data says so in words, no JavaScript says so, a lost connection after loading changes nothing, and blocked web fonts do not break a page.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv" };
let corrupt = false;
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
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
await step("no JavaScript: the Explorer says what it needs", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html`);
  assert.match(await page.locator("noscript").first().innerHTML(), /needs JavaScript/);
}, { javaScriptEnabled: false });
await step("connection lost after loading: the Explorer keeps working", async ctx => {
  const page = await ctx.newPage(); await page.goto(`${BASE}/highline.html#r=gsmf&z=0.1`); await ready(page);
  await ctx.setOffline(true);
  await page.evaluate(() => { location.hash = "#r=sfms&z=0"; });
  await page.waitForFunction(() => /main sequence/i.test(document.getElementById("shTitle").textContent));
  await page.click("button:has-text('Evolution')"); await page.waitForTimeout(500);
  assert.ok(await page.locator("#stage path").count() > 3, "still draws after switching view while offline");
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
console.log(`resilience: ${n} checks passed (broken data, no JavaScript, offline after load, blocked fonts, reduced motion, content security policy, 404 page)`);
