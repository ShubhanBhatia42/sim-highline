// The ten questions a simulation researcher brings (docs/QUESTIONS.md), each walked in a real browser against dist/. Every journey must reach its answer in at most four clicks
// and in under 30 seconds, and the time to the first useful result is printed. Needs dist/ (run the build scripts first) and Playwright.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv", ".py": "text/plain", ".bib": "text/plain" };
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p); const b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch (e) { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await launchBrowser();
const rows = [];
const failures = [];

async function journey(n, question, fn) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  const t0 = Date.now();
  let clicks = 0;
  const click = async (sel) => { clicks++; await page.click(sel); };
  try {
    const answer = await fn({ page, click, base: BASE });
    const ms = Date.now() - t0;
    assert.deepEqual(errors, [], "page errors");
    assert.ok(clicks <= 4, `${clicks} clicks`);
    assert.ok(ms < 30000, `${ms} ms`);
    rows.push([n, question, clicks, ms, answer]);
  } catch (e) { failures.push(`${n} ${question}: ${e.message.split("\n")[0]}`); rows.push([n, question, clicks, Date.now() - t0, "FAILED"]); }
  await ctx.close();
}
const settle = async page => { await page.waitForFunction(() => !document.getElementById("boot"), null, { timeout: 15000 }); await page.waitForTimeout(400); };

await journey(1, "What do simulations predict for a relation at an epoch?", async ({ page, base }) => {
  await page.goto(`${base}/highline.html#r=gsmf&z=0.1`); await settle(page);
  const n = await page.locator("#stage path").count();
  assert.ok(n >= 10, "curves drawn");
  assert.ok((await page.locator("#legend").innerText()).length > 50, "legend lists the sources");
  return `${n} curve paths`;
});
await journey(2, "How does my own run compare with the others?", async ({ page, click, base }) => {
  await page.goto(`${base}/highline.html#r=gsmf&z=0.1`); await settle(page);
  await click("#bMine"); await click("#uEx");
  assert.ok((await page.locator("#stage .userdot").count()) >= 5);
  const rowsN = await page.locator("#mineTab tr[data-id]").count();
  assert.ok(rowsN >= 5);
  return `${rowsN} comparison rows`;
});
await journey(3, "Is a comparison fair (same IMF, aperture, population)?", async ({ page, click, base }) => {
  await page.goto(`${base}/highline.html#r=gsmf&z=0.1&pn=mine`); await settle(page);
  await click("#uEx");
  for (const k of ["densityFrame", "imf", "massDefinition"]) { const o = await page.locator(`[data-def="${k}"] option`).count(); if (o > 1) await page.selectOption(`[data-def="${k}"]`, { index: 1 }); }
  const glyphs = await page.locator("#mineTab .v").allInnerTexts();
  assert.ok(glyphs.some(g => ["✓", "~", "✕", "✗"].includes(g)), "verdict marks shown");
  const why = await page.locator("#mineTab tr[data-id]").first().getAttribute("title");
  return `verdict marks ${[...new Set(glyphs)].join(" ")}; reasons on hover ${why ? "yes" : "no"}`;
});
await journey(4, "Where does a curve come from, and how was it obtained?", async ({ page, click, base }) => {
  await page.goto(`${base}/highline.html#r=gsmf&z=0.1&pn=mine`); await settle(page);
  await click("#uEx");
  await click("#mineTab tr[data-id]");
  await page.waitForSelector("#panel.open");
  const txt = await page.locator("#pbody").innerText();
  assert.ok(txt.length > 80, "evidence panel has content");
  assert.ok(/How sure are we\?/.test(txt), "plain statement of how sure we are");
  assert.ok((await page.locator('#pbody a[href*="issues/new"]').count()) === 1, "a link that reports a problem with this curve");
  return `evidence panel ${txt.length} characters, with how-sure note and report link`;
});
await journey(5, "Where do simulations disagree most?", async ({ page, click, base }) => {
  await page.goto(`${base}/highline.html#r=gsmf&z=0.1`); await settle(page);
  await click("#mSpread"); await page.waitForTimeout(600);
  const t = await page.locator("body").innerText();
  assert.ok(/spread/i.test(t));
  return "spread view";
});
await journey(6, "How do simulations compare with observations?", async ({ page, click, base }) => {
  await page.goto(`${base}/highline.html#r=gsmf&z=0.1`); await settle(page);
  await click("#mTension"); await page.waitForTimeout(600);
  assert.ok(/tension|observ/i.test(await page.locator("body").innerText()));
  return "tension view";
});
await journey(7, "How does a relation change with redshift?", async ({ page, click, base }) => {
  await page.goto(`${base}/highline.html#r=sfms&z=1`); await settle(page);
  await click("#mEvol"); await page.waitForTimeout(600);
  assert.ok((await page.locator("#stage path").count()) >= 5);
  return "evolution view";
});
await journey(8, "How do I cite this and get the BibTeX?", async ({ page, click, base }) => {
  await page.goto(`${base}/highline.html#r=gsmf&z=0.1`); await settle(page);
  await click("#bData");
  await page.waitForSelector("#panel.open");
  assert.ok(/bibtex/i.test(await page.locator("#pbody").innerText()));
  return "Get data panel with BibTeX";
});
await journey(9, "What happens to my galaxies if feedback is stronger?", async ({ page, click, base }) => {
  await page.goto(`${base}/site/retune.html`);
  await page.waitForSelector(".rt-panel", { timeout: 15000 });
  await page.getByRole("button", { name: /make simba look like tng/i }).click(); // one click: dials move and the story is written
  assert.ok(/agree on \d+ of 11/.test(await page.locator(".rt-big").innerText()));
  return "dials page answers in words";
});
await journey(10, "Can I load the data in a notebook?", async ({ page, base }) => {
  await page.goto(`${base}/site/data.html`);
  const t = await page.locator("body").innerText();
  assert.ok(/sim_highline|pip install|CSV/.test(t));
  return "data page lists files and loader";
});

// the "Try this" links on the front page: each lands on what its words promise, in one click
await journey(11, "Front page 'Try this' links each land where they say", async ({ page, base }) => {
  await page.goto(`${base}/site/index.html`);
  const links = await page.$$eval(".try a", as => as.map(a => ({ t: a.textContent, h: a.getAttribute("href") })));
  assert.equal(links.length, 5, "five try-this links");
  const out = [];
  for (const l of links) {
    await page.goto(new URL(l.h, `${base}/site/index.html`).href);
    if (l.h.includes("retune")) {
      await page.waitForSelector(".rt-panel"); const dials = await page.$$eval(".rt-dial input[type=range]", i => i.map(x => +x.value));
      assert.ok(Math.abs(dials[0] - 0.5) < 1e-6 && Math.abs(dials[4] - 0.5) < 1e-6 && dials[1] === 0, "both supernova wind dials at x2");
      out.push("dials");
    } else {
      await settle(page); const title = await page.textContent("#shTitle");
      if (l.h.includes("pn=mine")) assert.ok(await page.locator(".panel.open").count() === 1, "your-run panel open");
      else assert.match(title, /at z = (8|0)/, title);
      assert.ok(await page.locator("#stage path").count() >= 3, "something is drawn");
      out.push(title.slice(0, 22));
    }
  }
  return out.join(" | ");
});
await journey(12, "Copy the citation and the BibTeX from the data page", async ({ page, base }) => {
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"], { origin: base });
  await page.goto(`${base}/site/data.html#cite`);
  await page.click("button[data-copy=cite-text]"); await page.waitForFunction(() => /Copied|Selected/.test(document.querySelector(".cpmsg").textContent));
  const t = await page.evaluate(() => navigator.clipboard.readText());
  assert.match(t, /Bhatia, S\. \(\d{4}\)\. sim-highline/); assert.match(t, /doi\.org\/10\.5281\/zenodo/);
  await page.click("button[data-copy=cite-bib]"); await page.waitForTimeout(300);
  assert.match(await page.evaluate(() => navigator.clipboard.readText()), /^@/);
  return "citation and BibTeX copied";
});
await journey(13, "A returning visitor is told what changed; a first-time visitor is not", async ({ page, base }) => {
  await page.goto(`${base}/site/index.html`);
  assert.ok(!(await page.locator("#whatsnew").isVisible()), "nothing for a first visit");
  await page.evaluate(() => localStorage.setItem("sh-last-version", "0.0.1")); await page.reload();
  assert.ok(await page.locator("#whatsnew").isVisible(), "a returning visitor sees the note");
  await page.click("#whatsnewX"); await page.reload();
  assert.ok(!(await page.locator("#whatsnew").isVisible()), "dismissed for good until the next version");
  return "what's-new note shown once";
});
await journey(14, "Feedback links on every page open a prefilled issue", async ({ page, base }) => {
  for (const pg of ["site/index.html", "site/retune.html", "site/study-joint.html", "site/quality.html"]) {
    await page.goto(`${base}/${pg}#some=setting`);
    const href = await page.evaluate(() => { const a = document.getElementById("tellus"); a.addEventListener("click", e => e.preventDefault()); a.click(); return a.href; });
    const u = new URL(href);
    assert.match(u.pathname, /\/issues\/new$/); assert.equal(u.searchParams.get("template"), "feedback.yml");
    assert.match(u.searchParams.get("title"), /^\[feedback\] .{5}/); assert.ok(u.searchParams.get("page").length > 5);
    const link = u.searchParams.get("link"); assert.ok(link.endsWith("#some=setting") || (pg.includes("retune") && /#.*@\d+&m=/.test(link)), `the address with its settings is passed on (${pg}: ${link}); the dials page may have replaced the hash with its own state`);
  }
  return "prefilled with the page and the address";
});
console.log("journey | question | clicks | ms | answer");
for (const r of rows) console.log(`${String(r[0]).padStart(2)} | ${r[1]} | ${r[2]} | ${r[3]} | ${r[4]}`);
await browser.close(); server.close();
if (failures.length) { console.log("FAILED:\n" + failures.join("\n")); process.exit(1); }
console.log(`journeys: ${rows.length} of ${rows.length} reach their answer in at most four clicks`);
