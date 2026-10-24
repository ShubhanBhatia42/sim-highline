// Browser tests for the built app and site (needs dist/: run scripts/verify-all.sh or the build scripts first, and `npm install` + `npx playwright install chromium`).
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";
import AxeBuilder from "@axe-core/playwright";

const DIST = new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv", ".py": "text/plain", ".bib": "text/plain" };
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p); const b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await launchBrowser();
const failures = [];
let n = 0;
const step = async (name, fn) => { n++; try { await fn(); } catch (e) { const why = e.message.split("\n").slice(0, 8).join(" | ").slice(0, 600); failures.push(`${name}: ${why}`); console.log("FAIL", name, "-", why); } };

async function open(url, { w = 1280, h = 800, scheme = "light", storage } = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
  if (storage) await ctx.addInitScript(s => { try { localStorage.setItem("sh-theme", s); } catch (e) {} }, storage);
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", e => errors.push(String(e)));
  // Firefox reports Playwright's own page.evaluate as a blocked eval under the page's content security policy; the site has no eval (test-resilience checks the policy in Chromium, which does not exempt the page's own code).
  page.on("console", m => { if (m.type() === "error" && !/fonts\.(googleapis|gstatic)|ERR_(NAME|INTERNET|CONNECTION)|Failed to load resource|blocked a JavaScript eval/.test(m.text())) errors.push(m.text()); });
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

await step("the emission-line luminosity function draws its observations and its simulation, and names the line in the legend", async () => {
  for (const [z, prefix] of [["0.84", "sobral13.hizels.elf"], ["5.3", "covelopaz25.fresco-congress.elf"], ["5", "katz23.sphinx20.elf"], ["5", "covelopaz25.fresco-congress.elf"]]) {
    const { page, ctx, errors } = await open(`/highline.html#r=elf&z=${z}`);
    await settle(page);
    assert.equal(await page.textContent("#shTitle"), `Emission-line luminosity function at z = ${z}`);
    assert((await page.locator(`#stage path[data-id^="${prefix}"]`).count()) >= 1, `no ${prefix} curve at z = ${z}`);
    assert.deepEqual(errors, []);
    await ctx.close();
  }
  const { page, ctx } = await open("/highline.html#r=elf&z=0.84");
  await settle(page);
  assert((await page.locator('#presets button[data-r="elf"]').count()) === 1, "the relation rail must list the emission-line luminosity function");
  await ctx.close();
});

await step("every published expression is drawn under the page's content security policy (no eval)", async () => {
  // Playwright's page.evaluate is exempt from the page's policy, so this cannot try new Function itself: it checks the mechanism instead (the policy has no 'unsafe-eval'; every parametric record has a precompiled function; nothing the page itself tried to compile failed)
  const { page, ctx } = await open("/highline.html#r=sfms&z=0.1");
  await settle(page);
  const res = await page.evaluate(() => {
    const par = ALL.filter(r => r.representation.type === "parametric");
    const key = r => Object.entries(r.representation.parameters || {}).filter(([, v]) => typeof v === "number").map(([k]) => k).join(",") + "|" + r.representation.expression;
    return { n: par.length, missing: par.filter(r => typeof window.SIMHIGHLINE_EXPR[key(r)] !== "function").map(r => r.id), failedToCompile: [...evalCache.values()].filter(v => v === null).length, compiled: evalCache.size, csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]').content };
  });
  assert(!/unsafe-eval/.test(res.csp), "the policy must not allow eval");
  assert(res.n >= 100, `${res.n} parametric records`);
  assert.deepEqual(res.missing, [], "parametric records without a precompiled expression: " + res.missing.slice(0, 5).join(", "));
  assert(res.compiled > 0, "the page evaluated no expression at all");
  assert.equal(res.failedToCompile, 0, "expressions the page failed to compile");
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

await step("notes show measured definition effects and the figure pack describes the plot", async () => {
  const { page, ctx } = await open("/highline.html#r=gsmf&z=0");
  await page.click("#bAbout");
  assert.ok((await page.locator("#pbody").innerText()).includes("MEASURED DEFINITION EFFECTS"), "gsmf notes list measured effects");
  await page.click("#bData");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#fPack")]);
  assert.match(dl.suggestedFilename(), /_pack\.md$/);
  const text = await page.evaluate(() => methodsPack().methods);
  assert.ok(text.includes("compiled from the sim-highline dataset") && text.includes("No curve was interpolated"), "methods text states provenance and the no-interpolation rule");
  await ctx.close();
});

await step("first visit: a short guide appears once, can be dismissed, and stays dismissed", async () => {
  const { page, ctx } = await open("/highline.html");
  assert.ok(await page.locator("#hello").isVisible(), "guide shown on a first visit");
  assert.match(await page.locator("#hello").innerText(), /Pick a relation/);
  await page.click("#helloOk");
  assert.ok(!(await page.locator("#hello").isVisible()), "dismissed");
  await page.reload(); await page.waitForFunction(() => !document.getElementById("boot")); await page.waitForTimeout(300);
  assert.ok(!(await page.locator("#hello").isVisible()), "stays dismissed after a reload");
  await ctx.close();
  const e = await open("/highline.html#embed=1&r=gsmf&z=0.1"); await e.page.waitForTimeout(300);
  assert.ok(!(await e.page.locator("#hello").isVisible()), "not shown in an embed");
  await e.ctx.close();
  const s = await open("/highline.html#r=sfms&z=0&m=spread"); await s.page.waitForTimeout(300);
  assert.ok(await s.page.locator("#spread td[data-r]").first().isVisible(), "other views are not nested inside the plot");
  await s.ctx.close();
});

await step("address bar: rapid changes stay under the browsers' replaceState limit, and the last one wins", async () => {
  const { page, ctx } = await open("/highline.html#r=gsmf&z=0");
  const out = await page.evaluate(async () => {
    let calls = 0, errors = 0;
    const t0 = performance.now();
    const orig = history.replaceState.bind(history);
    history.replaceState = (...a) => { calls++; return orig(...a); };
    addEventListener("error", () => errors++);
    const z = document.getElementById("z"), max = Number(z.max);
    for (let i = 0; i < 400; i++) { z.value = String(i % (max + 1)); z.dispatchEvent(new Event("input", { bubbles: true })); await new Promise(r => setTimeout(r, 2)); }
    z.value = String(max); z.dispatchEvent(new Event("input", { bubbles: true }));
    await new Promise(r => setTimeout(r, 400));
    return { calls, errors, hash: location.hash, secs: (performance.now() - t0) / 1000 };
  });
  assert.ok(out.calls <= out.secs / 0.15 + 3, `${out.calls} address-bar writes in ${out.secs.toFixed(1)} s for 401 slider moves (at most one per 150 ms; Safari and Firefox allow 100 per 10 s)`);
  assert.equal(out.errors, 0, "no page errors");
  assert.ok(/z=/.test(out.hash), "the address still carries the redshift");
  const z = Number(new URLSearchParams(out.hash.slice(1)).get("z"));
  assert.ok(Number.isFinite(z), "redshift in the address is a number");
  await ctx.close();
});
await step("distribution view: panels per source, quantile lines, thresholds, tables, a click opens the record", async () => {
  const { page, ctx, errors } = await open("/highline.html#r=ssfr&z=0&m=dist");
  await settle(page);
  assert.ok(await page.locator("#dist.on").count() === 1, "the distribution view is shown");
  assert.ok(await page.locator("#dist .dpanel").count() >= 3, "a heat map for each code");
  assert.ok(await page.locator("#dist .dpanel svg rect").count() > 300, "cells are drawn");
  assert.ok(await page.locator("#dist .dtab").count() >= 2, "the tables of quenched and green-valley shares");
  const q = await page.locator("#dist .dtab").first().innerText();
  assert.match(q, /\d+%/, "percentages in the table");
  assert.equal(await page.locator("#mDist[aria-pressed=true]").count(), 1, "the button shows it is pressed");
  assert.ok((await page.evaluate(() => location.hash)).includes("m=dist"), "the address carries the view");
  await page.locator("#dist .dpanel").first().click();
  await page.waitForSelector("#panel.open");
  assert.equal(await page.locator("#dist.on").count(), 0, "opening a record leaves the distribution view");
  assert.deepEqual(errors, []);
  await ctx.close();
});

await step("links carry the dataset version, and a link from another version shows a notice", async () => {
  const cur = await open("/highline.html#r=gsmf&z=2");
  await settle(cur.page);
  const version = await cur.page.evaluate(() => SIMHIGHLINE_RELEASE.version);
  assert.ok(await cur.page.locator("#verbanner[hidden]").count() === 1, "no notice without a version in the address");
  const pinned = await cur.page.evaluate(() => window.__sh.withVersion("#r=gsmf&z=2"));
  assert.equal(new URLSearchParams(pinned).get("dv"), version, "copied links carry the version");
  assert.equal(new URLSearchParams(pinned).get("r"), "gsmf", "and keep the rest of the state");
  assert.deepEqual(cur.errors, []);
  await cur.ctx.close();
  const same = await open(`/highline.html#r=gsmf&z=2&dv=${version}`);
  await settle(same.page);
  assert.ok(await same.page.locator("#verbanner[hidden]").count() === 1, "no notice when the version matches");
  await same.ctx.close();
  const old = await open("/highline.html#r=gsmf&z=2&dv=0.0.1");
  await settle(old.page);
  assert.ok(await old.page.locator("#verbanner:not([hidden])").count() === 1, "a notice for a link from another version");
  const t = await old.page.locator("#verbannerText").innerText();
  assert.ok(t.includes("0.0.1") && t.includes(version), "the notice names both versions: " + t);
  await old.page.locator("#verbannerX").click();
  assert.ok(await old.page.locator("#verbanner[hidden]").count() === 1, "the notice can be dismissed");
  assert.deepEqual(old.errors, []);
  await old.ctx.close();
});

await step("spread map and command palette", async () => {
  const { page, ctx } = await open("/highline.html#m=spread");
  assert.ok(await page.locator("#spread td[data-r]").count() >= 20, "spread map has cells");
  const first = await page.locator("#spread td[data-r] b").first().innerText();
  assert.ok(Number(first) > 0 && Number(first) < 3, "spread values are plausible dex");
  await page.locator("#spread td[data-r]").first().click();
  await page.waitForFunction(() => !location.hash.includes("m=spread"), null, { timeout: 2000 }).catch(() => {});  // the address bar is written at most every 150 ms
  assert.ok(!(await page.evaluate(() => location.hash)).includes("m=spread"), "clicking a cell opens the relation");
  await page.keyboard.press("/");
  assert.ok(await page.locator("#pal.on").count() === 1, "palette opens with /");
  await page.fill("#palQ", "tension");
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => location.hash.includes("m=tension"), null, { timeout: 2000 }).catch(() => {});
  assert.ok((await page.evaluate(() => location.hash)).includes("m=tension"), "palette runs the first match");
  await page.keyboard.press("Control+k");
  await page.fill("#palQ", "pillepich");
  assert.ok(await page.locator("#palL li[data-i]").count() >= 1, "palette finds records by citation");
  await page.keyboard.press("Escape");
  assert.equal(await page.locator("#pal.on").count(), 0);
  await ctx.close();
});

await step("your run: plot, declare definitions, compare, export", async () => {
  const { page, ctx } = await open("/highline.html#r=gsmf&z=0");
  await page.click("#bMine");
  await page.fill("#uName", "my run");
  await page.fill("#uText", "x,y,err\n8,-1.5,0.05\n8.5,-1.7,0.05\n9,-1.9,0.05\n9.5,-2.1,0.06\n10,-2.3,0.07\n10.5,-2.7,0.1\n11,-3.5,0.2");
  await page.click("#uPlot");
  assert.equal(await page.locator("#stage .userdot").count(), 7, "seven user points drawn");
  assert.ok(await page.locator("#mineTab tr[data-id]").count() >= 5, "comparison rows listed");
  assert.equal(await page.locator("#mineTab .v.ok").count(), 0, "nothing comparable before definitions are declared");
  for (const [k, v] of [["densityFrame", "comoving"], ["imf", "chabrier03"], ["massDefinition", "aperture-30pkpc"]]) await page.selectOption(`[data-def="${k}"]`, v);
  const glyphs = await page.locator("#mineTab .v").allInnerTexts();
  assert.ok(glyphs.some(g => g === "~" || g === "\u2713"), "declaring definitions makes at least one curve comparable");
  const [dl] = await Promise.all([page.waitForEvent("download"), page.click("#uCsv")]);
  assert.match(dl.suggestedFilename(), /^sim-highline-yourrun-gsmf-z/);
  await page.reload(); await settle(page);
  await page.click("#bMine");
  assert.equal(await page.inputValue("#uName"), "my run", "run persists in this browser");
  await page.click("#uClear");
  assert.equal(await page.locator("#stage .userdot").count(), 0);
  await ctx.close();
});

await step("your run: opens from a link, and the example plots and compares without any data of one's own", async () => {
  const { page, ctx, errors } = await open("/highline.html#r=gsmf&z=0.1&pn=mine");
  await settle(page);
  assert.equal(await page.locator("#uText").count(), 1, "the panel opens from the link");
  await page.click("#uEx");
  assert.ok((await page.locator("#stage .userdot").count()) >= 5, "example points drawn");
  assert.match(await page.inputValue("#uName"), /^example: /);
  assert.match(await page.locator("#mineTab .sumline").innerText(), /Say what your numbers mean/, "before definitions are declared the summary asks for them");
  const sel = (k) => page.locator(`[data-def="${k}"]`);
  for (const k of ["densityFrame", "imf", "massDefinition"]) { const opts = await sel(k).locator("option").allInnerTexts(); if (opts.length > 1) await sel(k).selectOption({ index: 1 }); }
  const verdicts = await page.locator("#mineTab .v").allInnerTexts();
  assert.ok(verdicts.length >= 5, "comparison rows listed");
  if (verdicts.includes("\\u2713")) assert.equal(await page.locator("#mineTab .sumline").count(), 1, "a summary line appears once a curve is comparable");
  assert.deepEqual(errors, []);
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

const SITE = ["index", "studies", "study-definitions", "study-harmonization", "study-sfh", "study-joint", "study-shape", "retune", "data", "methods", "sources", "glossary", "faq", "changes", "quality"];
for (const w of [375, 1280]) for (const f of SITE) await step(`site ${f} at ${w}px: one h1, no horizontal overflow`, async () => {
  const { page, ctx, errors } = await open(`/site/${f}.html`, { w, h: 800 });
  const r = await page.evaluate(() => ({ h1: document.querySelectorAll("h1").length, sw: document.documentElement.scrollWidth, iw: innerWidth }));
  assert.equal(r.h1, 1); assert(r.sw <= r.iw + 1, `overflow ${r.sw} > ${r.iw}`);
  assert.deepEqual(errors, []);
  await ctx.close();
});

await step("site theme toggle switches and persists, text contrast stays at least 4.5", async () => {
  const { page, ctx } = await open("/site/study-sfh.html", { scheme: "light" });
  const lum = c => { const [r, g, b] = c.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const probe = () => page.evaluate(() => { const g = s => getComputedStyle(document.querySelector(s)); return { theme: document.documentElement.dataset.theme || null, bg: g("body").backgroundColor, ink: g("p").color, lab: g(".idx .lab").color, link: g("main a").color, status: g(".status").color, statusBg: g(".status").backgroundColor }; });
  const light = await probe();
  await page.click("#theme");
  assert.equal(await page.evaluate(() => document.documentElement.dataset.theme), "dark");
  await page.reload();
  const dark = await probe();
  assert.equal(dark.theme, "dark");
  assert.notEqual(light.bg, dark.bg);
  for (const [name, t] of [["light", light], ["dark", dark]]) for (const k of ["ink", "lab", "link"]) assert(ratio(t[k], t.bg) >= 4.5, `${name} ${k} contrast ${ratio(t[k], t.bg).toFixed(2)}`);
  for (const [name, t] of [["light", light], ["dark", dark]]) assert(ratio(t.status, t.statusBg) >= 4.5, `${name} status bar contrast ${ratio(t.status, t.statusBg).toFixed(2)}`);
  await ctx.close();
});

await step("Retune: emulators evaluate in the browser and the match agrees with the all-at-once study", async () => {
  const { page, ctx, errors } = await open("/site/retune.html");
  await page.waitForSelector(".rt-panel");
  assert.ok((await page.locator(".rt-panel").count()) >= 10, "panels for every family");
  const dist = async () => parseFloat(((await page.locator(".rt-sum").innerText()).match(/Joint gap ([0-9.]+)/) || [])[1]);
  const fid = await dist();
  assert.ok(Math.abs(fid - 6.35) < 0.05, `joint distance at the fiducial parameters ${fid} (study: 6.35)`);
  await page.selectOption("#rt-match", "all");
  await page.getByRole("button", { name: /closest the two can get/i }).click();
  await page.waitForFunction(() => !/Joint gap 6\.3/.test(document.querySelector(".rt-sum").innerText));
  const best = await dist();
  assert.ok(best > 4.5 && best < 5.3, `best match ${best} (study: 4.85)`);
  assert.match(page.url(), /#-?\d/, "dial state in the address");
  const story = await page.locator(".rt-story").innerText();
  assert.match(story, /Closest the two can get/);
  assert.match(story, /agree on \d+ of 11 things/);
  assert.match(story, /Still apart: .*black hole/s, "the stubborn properties are named in words");
  assert.match(await page.locator(".rt-big").innerText(), /agree on \d+ of 11 things about galaxies/);
  await page.getByRole("button", { name: /^reset$/i }).click();
  assert.equal(await page.locator(".rt-story").count(), 0, "reset clears the story");
  assert.ok(Math.abs((await dist()) - fid) < 0.01);
  assert.deepEqual(errors, []);
  await ctx.close();
  const h = await open("/site/retune.html#-0.88,1.00,-0.46,0.40;-1.00,-1.00,-1.00,-0.71@042");
  await h.page.waitForSelector(".rt-panel");
  const d2 = parseFloat(((await h.page.locator(".rt-sum").innerText()).match(/Joint gap ([0-9.]+)/) || [])[1]);
  assert.ok(Math.abs(d2 - 4.85) < 0.05, `restored state ${d2}`);
  await h.ctx.close();
});

await step("links between the site and the app resolve", async () => {
  const { page, ctx } = await open("/site/index.html");
  await page.click('nav.menu a[href="../highline.html"]');
  await page.waitForURL(/highline\.html/);
  await settle(page);
  await page.click('.sitenav a[href="site/retune.html"]');
  await page.waitForURL(/site\/retune\.html/);
  await page.click('nav.menu a[href="../highline.html"]');
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
for (const f of SITE) { await axeRun(`site ${f}, light`, `/site/${f}.html`); await axeRun(`site ${f}, dark`, `/site/${f}.html`, { scheme: "dark" }); }
for (const f of ["index", "study-definitions", "study-sfh", "data", "methods", "sources"]) await axeRun(`site ${f}, phone, light`, `/site/${f}.html`, { w: 375, h: 800 });
await axeRun("app, phone", "/highline.html#r=gsmf&z=6", { w: 375, h: 812 });

await browser.close(); server.close();
if (failures.length) { console.log(`\n${failures.length} of ${n} UI checks failed`); process.exit(1); }
console.log(`UI tests passed: ${n} checks (app, views, themes, embed, phone layout, site, links, accessibility)`);
