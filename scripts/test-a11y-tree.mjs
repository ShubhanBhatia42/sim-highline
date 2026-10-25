// Reads the built pages the way a screen reader meets them: the accessibility tree that Chromium builds (Playwright's ariaSnapshot), not the HTML.
// It fails when a control has no name, when a heading level is skipped or there is not exactly one h1, when the landmarks are wrong, when two links with the same name go to different places,
// when a data table has no header cells, no row headers or no name, when a link that opens a new tab does not say so, and, on the dials page, when moving a dial announces the wrong things.
//   node scripts/test-a11y-tree.mjs                 the site pages and the dials page (part of npm run test:browser)
//   node scripts/test-a11y-tree.mjs --explorer      also the Explorer (highline.html); these checks describe the fixes listed in docs/ACCESSIBILITY-WALKTHROUGH.md and fail until they are applied
//   node scripts/test-a11y-tree.mjs --dist DIR      test a copy of dist/ (used to try the Explorer patches before they are merged)
// This is a software check of the tree. It does not replace listening to the pages with a screen reader (docs/ACCESSIBILITY-WALKTHROUGH.md lists what a person still has to cover).
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";

/* ---------- the checker: a pure function of the snapshot text, so it can be tested without a browser ---------- */
const CONTROLS = new Set(["link", "button", "textbox", "combobox", "slider", "checkbox", "radio", "spinbutton", "searchbox", "switch", "tab", "menuitem"]);
const LANDMARKS = new Set(["banner", "main", "contentinfo", "navigation", "complementary", "region", "form", "search"]);
export function parseSnapshot(text) {
  const nodes = [];
  for (const raw of text.split("\n")) {
    const m = raw.match(/^(\s*)- (.*)$/); if (!m) continue;
    let body = m[2];
    if (body.startsWith("/")) { if (nodes.length && body.startsWith("/url:")) nodes[nodes.length - 1].url = body.slice(5).trim().replace(/^"|"$/g, ""); continue; }
    if (body.startsWith("'")) { const end = body.lastIndexOf("'"); body = body.slice(1, end).replace(/''/g, "'") + body.slice(end + 1); }
    const r = body.match(/^([\w-]+)(?: "((?:[^"\\]|\\.)*)")?((?: \[[^\]]*\])*)(:.*)?$/); if (!r) continue;
    const level = (r[3].match(/\[level=(\d)\]/) || [])[1];
    nodes.push({ role: r[1], name: r[2] === undefined ? "" : r[2].replace(/\\"/g, '"'), level: level ? +level : null, indent: m[1].length, attrs: r[3], rest: r[4] || "" });
  }
  return nodes;
}
export function audit(text, { page = "", unique = [] } = {}) {
  const nodes = parseSnapshot(text), problems = [], P = s => problems.push(`${page}: ${s}`);
  for (const n of nodes) if (CONTROLS.has(n.role) && !n.name.trim()) P(`${n.role} without a name${n.rest ? ` (value ${n.rest.slice(1).trim()})` : ""}${n.url ? ` -> ${n.url}` : ""}`);
  const heads = nodes.filter(n => n.role === "heading");
  for (const h of heads) if (!h.name.trim()) P(`heading level ${h.level} without a name`);
  for (const h of heads) if (/^\s*§/.test(h.name)) P(`heading "${h.name}" reads the section sign aloud (mark it aria-hidden)`);
  if (heads.filter(h => h.level === 1).length !== 1) P(`${heads.filter(h => h.level === 1).length} h1 headings, expected exactly one`);
  let prev = 0; for (const h of heads) { if (h.level > prev + 1) P(`heading level skipped: h${prev} then h${h.level} "${h.name.slice(0, 50)}"`); prev = h.level; }
  const count = r => nodes.filter(n => n.role === r).length;
  for (const r of ["banner", "main", "contentinfo"]) if (count(r) !== 1) P(`${count(r)} ${r} landmarks, expected one`);
  const navs = nodes.filter(n => n.role === "navigation").map(n => n.name); if (navs.some(x => !x) || new Set(navs).size !== navs.length) P(`navigation landmarks need distinct names (${navs.join(" | ")})`);
  const byName = new Map(); for (const n of nodes) if (n.role === "link" && n.name && n.url && !n.url.startsWith("#")) (byName.get(n.name) || byName.set(n.name, new Set()).get(n.name)).add(n.url);
  for (const [name, urls] of byName) if (urls.size > 1) P(`${urls.size} links named "${name.slice(0, 50)}" go to different places`);
  for (const role of unique) { const seen = new Map(); for (const n of nodes) if (n.role === role && n.name) seen.set(n.name, (seen.get(n.name) || 0) + 1); for (const [name, k] of seen) if (k > 1) P(`${k} ${role}s share the name "${name.slice(0, 50)}"`); }
  return problems;
}
{ // the checker itself must fail on what it is meant to catch
  const bad = [`- banner:`, `  - link "Home":`, `    - /url: a.html`, `- main:`, `  - heading "T" [level=1]`, `  - heading "Deep" [level=3]`, `  - button`, `  - link "Same":`, `    - /url: a.html`, `  - link "Same":`, `    - /url: b.html`, `  - slider: "0"`, `  - heading "§1Start" [level=2]`, `- contentinfo`].join("\n");
  const found = audit(bad, { page: "self" }).join("\n");
  for (const [re, what] of [[/heading level skipped: h1 then h3/, "a skipped heading level"], [/button without a name/, "an unnamed button"], [/slider without a name/, "an unnamed slider"], [/links named "Same" go to different places/, "same name, different targets"], [/section sign/, "a section sign in a heading"]]) assert(re.test(found), `the checker did not catch ${what}:\n${found}`);
  assert.deepEqual(audit([`- banner`, `- main:`, `  - heading "T" [level=1]`, `  - heading "S" [level=2]`, `  - 'link "a: b"':`, `    - /url: x`, `  - button "Go"`, `- contentinfo`].join("\n")), [], "the checker complained about a clean tree");
}

/* ---------- the browser part ---------- */
const args = process.argv.slice(2), WITH_EXPLORER = args.includes("--explorer");
const DIST = args.includes("--dist") ? path.resolve(args[args.indexOf("--dist") + 1]) + "/" : new URL("../dist/", import.meta.url).pathname;
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css", ".csv": "text/csv", ".py": "text/plain", ".bib": "text/plain" };
const server = http.createServer(async (req, res) => {
  const p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  try { const f = path.join(DIST, p.endsWith("/") ? p + "index.html" : p), b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end("not found"); }
});
await new Promise(r => server.listen(0, "127.0.0.1", r));
const BASE = `http://127.0.0.1:${server.address().port}`;
const browser = await launchBrowser();
const problems = []; let checks = 0;
const SITE = ["index", "studies", "study-definitions", "study-harmonization", "study-sfh", "study-joint", "study-shape", "study-resolution", "seeding", "retune", "data", "methods", "sources", "findings", "glossary", "faq", "changes", "quality", "summary"].map(p => `site/${p}.html`).concat(["404.html"]);
const open = async (url, w = 1280) => { const ctx = await browser.newContext({ viewport: { width: w, height: 900 } }), page = await ctx.newPage(); await page.goto(`${BASE}/${url}`); await page.waitForFunction(() => document.readyState === "complete" && !document.getElementById("boot")); return { ctx, page }; };

for (const pg of SITE) {
  const { ctx, page } = await open(pg); await page.waitForTimeout(pg.includes("retune") ? 900 : 200); checks++;
  const tree = await page.locator("html").ariaSnapshot();
  problems.push(...audit(tree, { page: pg, unique: pg.includes("retune") ? ["slider", "combobox", "checkbox", "button"] : [] }));
  const dom = await page.evaluate(() => {
    const out = [], named = t => !!(t.querySelector(":scope > caption") || t.getAttribute("aria-label") || t.getAttribute("aria-labelledby") || (t.closest("[role=region][aria-label]") && t.closest("[role=region][aria-label]").querySelector("table") === t));
    for (const t of document.querySelectorAll("table")) {
      const rows = [...t.querySelectorAll(":scope > tbody > tr")], label = (t.getAttribute("aria-label") || (t.querySelector("caption") || {}).textContent || "table").slice(0, 40);
      if (!t.querySelector("th")) out.push(`table "${label}" has no header cells`);
      if (!named(t)) out.push(`table (${rows.length} rows) has no name: add a caption or aria-label`);
      const noRowHead = rows.filter(r => { const c = r.cells[0]; return c && c.tagName === "TD" && !c.classList.contains("n") && c.colSpan === 1; });
      if (rows.length > 1 && noRowHead.length) out.push(`table "${label}": ${noRowHead.length} of ${rows.length} rows have no row header (first cell "${noRowHead[0].cells[0].textContent.trim().slice(0, 30)}" is a td)`);
    }
    for (const a of document.querySelectorAll('a[target="_blank"]')) if (!/new tab/i.test((a.title || "") + (a.getAttribute("aria-label") || ""))) out.push(`link "${a.textContent.trim().slice(0, 40)}" opens a new tab without saying so`);
    for (const h of document.querySelectorAll("h2")) if (h.querySelector(".sn") && h.querySelector(".sn").getAttribute("aria-hidden") !== "true") out.push(`section number in "${h.textContent.slice(0, 30)}" is not hidden from screen readers`);
    return [...new Set(out)];
  });
  problems.push(...dom.map(d => `${pg}: ${d}`));
  await ctx.close();
}

{ // the dials page: what is said, and where focus goes, when a visitor acts
  const { ctx, page } = await open("site/retune.html"); await page.waitForSelector("#rt-live", { state: "attached" }); await page.waitForTimeout(800); checks++;
  const P = s => problems.push(`site/retune.html: ${s}`);
  await page.evaluate(() => { window.__live = []; new MutationObserver(ms => { for (const m of ms) { const t = m.target.nodeType === 1 ? m.target : m.target.parentElement, live = t && t.closest("[aria-live]:not([aria-live=off]),[role=status],[role=alert]"); if (live && live.textContent.trim()) window.__live.push((live.id || live.className) + ": " + live.textContent.trim().slice(0, 400)); } }).observe(document.body, { subtree: true, childList: true, characterData: true }); });
  const sl = await page.evaluate(() => [...document.querySelectorAll("input[type=range]")].map(i => ({ name: (i.labels[0] || {}).textContent, vt: i.getAttribute("aria-valuetext") })));
  if (sl.length !== 8) P(`expected 8 dials, found ${sl.length}`);
  for (const s of sl) { if (!/^(IllustrisTNG|SIMBA): /.test(s.name || "")) P(`a dial's name does not say which universe it belongs to: "${s.name}"`); if (!/^×\d/.test(s.vt || "")) P(`a dial has no spoken value (aria-valuetext "${s.vt}")`); }
  await page.focus("input[type=range] >> nth=0"); await page.keyboard.press("ArrowRight"); await page.keyboard.press("ArrowRight"); await page.waitForTimeout(500);
  const vt = await page.getAttribute("input[type=range] >> nth=0", "aria-valuetext"); if (vt === "×1.00") P("moving a dial did not change its spoken value");
  const said = await page.evaluate(() => [...new Set(window.__live)]);
  if (said.some(s => /^o-/.test(s))) P(`the value outputs of the dials are live regions and would be read out one by one: ${said.filter(s => /^o-/.test(s)).slice(0, 2).join(" | ")}`);
  if (!said.some(s => /^rt-live: At these dials the two universes agree on/.test(s))) P("moving a dial did not announce the one-sentence summary");
  if (said.filter(s => /^rt-live/.test(s)).length > 2) P(`moving a dial twice announced ${said.filter(s => /^rt-live/.test(s)).length} different messages`);
  await page.evaluate(() => { window.__live = []; });
  await page.click("button:has-text('Make SIMBA look like TNG')"); await page.waitForTimeout(2500);
  const said2 = await page.evaluate(() => [...new Set(window.__live)]);
  if (!said2.some(s => /rt-live: .*Overall they now agree on \d+ of \d+ things/.test(s))) P("the result of a search (what moved, what came into line, what was given up) is not announced");
  if (await page.evaluate(() => document.activeElement.textContent) !== "Make SIMBA look like TNG") P("focus moved away from the button that was pressed");
  const strip = await page.evaluate(() => [...document.querySelectorAll(".rt-z")].map(b => ({ n: b.getAttribute("aria-label"), p: b.getAttribute("aria-pressed") })));
  if (strip.length < 4 || strip.some(b => !/^z = [\d.]+: \d+ of \d+ properties agree$/.test(b.n || "") || !["true", "false"].includes(b.p))) P(`the redshift buttons need a spoken name and a pressed state: ${JSON.stringify(strip.slice(0, 2))}`);
  await page.focus(".rt-z >> nth=1"); await page.keyboard.press("Enter"); await page.waitForTimeout(400);
  const f = await page.evaluate(() => { const e = document.activeElement; return { cls: e.className, pressed: e.getAttribute("aria-pressed") }; });
  if (!/rt-z/.test(f.cls) || f.pressed !== "true") P(`after pressing a redshift button the keyboard is no longer on it (on "${f.cls}")`);
  const labels = await page.evaluate(() => [...document.querySelectorAll(".rt-panels svg[role=img]")].map(s => s.getAttribute("aria-label")));
  if (labels.length < 8 || labels.some(l => !/Average difference between the codes -?[\d.]+/.test(l) || !/IllustrisTNG [^.]*[\d]/.test(l))) P("the charts' text alternatives do not give the curves' values");
  const ids = await page.evaluate(() => { const c = {}; for (const e of document.querySelectorAll("[id]")) c[e.id] = (c[e.id] || 0) + 1; return Object.entries(c).filter(([, v]) => v > 1).map(([k]) => k); });
  if (ids.length) P(`duplicate ids: ${ids.join(", ")}`);
  await page.click("#rt-tourbtn"); await page.waitForTimeout(300);
  const tour = await page.evaluate(() => { const d = document.querySelector(".rt-tour"), t = document.getElementById(d.getAttribute("aria-describedby") || "none"); return { modal: d.getAttribute("role"), desc: t && t.textContent.length > 20, focus: document.activeElement.textContent }; });
  if (tour.modal !== "dialog" || !tour.desc) P("the tour dialog does not carry its text as its description");
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  if (await page.evaluate(() => document.activeElement.id) !== "rt-tourbtn") P("closing the tour with Escape does not return focus to the button that opened it");
  await ctx.close();
}

if (WITH_EXPLORER) { // the Explorer: the fixes listed in docs/ACCESSIBILITY-WALKTHROUGH.md (section "Explorer: patches for the coordinator")
  const { ctx, page } = await open("highline.html#r=gsmf&z=0.1"); await page.waitForFunction(() => document.querySelectorAll("#stage path").length > 3); await page.waitForTimeout(500); checks++;
  const P = s => problems.push(`highline.html: ${s}`);
  const act = () => page.evaluate(() => { const e = document.activeElement; return e && e !== document.body ? `${e.tagName.toLowerCase()}${e.id ? "#" + e.id : ""}[${(e.getAttribute("aria-label") || e.textContent || "").trim().slice(0, 30)}]` : "body"; });
  problems.push(...audit(await page.locator("html").ariaSnapshot(), { page: "highline.html", unique: ["button"] }).filter(p => !/heading level skipped|h1 headings/.test(p)));
  // 1. a closed panel is not in the tab order or the tree
  const hidden = await page.evaluate(() => getComputedStyle(document.getElementById("panel")).visibility);
  if (hidden !== "hidden") P(`the closed details panel is still reachable (visibility ${hidden}): Tab lands on its tabs and close button while it is off screen`);
  // 2. the epoch slider speaks the redshift, not its position
  const zv = await page.getAttribute("#z", "aria-valuetext"); if (!/^z = /.test(zv || "")) P(`the epoch slider's spoken value is "${zv}", expected "z = ..."`);
  // 3. focus survives re-rendering
  await page.focus("#legend .name"); await page.keyboard.press("Enter"); await page.waitForTimeout(400);
  if (!/^button/.test(await act())) P(`focus is lost after toggling a legend entry (now ${await act()})`);
  await page.focus("#presets button[data-r=sfms]"); await page.keyboard.press("Enter"); await page.waitForTimeout(900);
  if (!/^button/.test(await act())) P(`focus is lost after choosing a relation (now ${await act()})`);
  // 4. the details panel takes focus when a visitor opens it, and its content has a name
  await page.focus("#bMine"); await page.keyboard.press("Enter"); await page.waitForTimeout(500);
  if (!/role|tab|Evidence|My run|Your run/.test(await act()) && !(await page.evaluate(() => !!document.activeElement.closest("#panel")))) P(`opening a panel leaves focus on the button (${await act()}), about 130 Tab stops from the panel's content`);
  if (!(await page.getAttribute("#pbody", "aria-labelledby"))) P("the tab panel has no name (aria-labelledby the selected tab)");
  const hs = await page.evaluate(() => [...document.querySelectorAll("#pbody h1,#pbody h2,#pbody h3,#pbody h4")].map(h => +h.tagName[1]));
  if (hs.length && Math.min(...hs) > 3) P(`headings in the panel start at h${Math.min(...hs)}: levels h2 and h3 are skipped`);
  if (await page.locator("#uEx").count()) { await page.focus("#uEx"); await page.keyboard.press("Enter"); await page.waitForTimeout(900); if (await act() === "body") P("focus is lost after 'Try an example'"); }
  const sel = await page.evaluate(() => [...document.querySelectorAll("#pbody select[data-def]")].map(s => (s.labels[0] || {}).textContent.length));
  if (sel.some(n => n > 60)) P("the definition lists' accessible names include their long help text (move it to aria-describedby)");
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  // 5. Get data: unnamed range fields and ambiguous button names
  await page.click("#bData"); await page.waitForTimeout(400);
  const sb = await page.evaluate(() => [...document.querySelectorAll("#pbody input[type=number]")].filter(i => !i.labels.length && !i.getAttribute("aria-label")).length);
  if (sb) P(`${sb} number field(s) in Get data have no name`);
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  // 6. the About dialog holds focus and gives it back
  await page.focus("#infoBtn"); await page.keyboard.press("Enter"); await page.waitForTimeout(300);
  for (let i = 0; i < 16; i++) await page.keyboard.press("Tab");
  if (!(await page.evaluate(() => !!document.activeElement.closest("#about")))) P("Tab leaves the About dialog (aria-modal) for the page behind it");
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  if ((await page.evaluate(() => document.activeElement.id)) !== "infoBtn") P("Escape closes the About dialog but focus does not return to the button that opened it");
  // 7. the search box
  await page.keyboard.press("Control+k"); await page.waitForTimeout(300);
  for (let i = 0; i < 3; i++) await page.keyboard.press("Tab");
  if (!(await page.evaluate(() => !!document.activeElement.closest("#pal")))) P("Tab leaves the search dialog for the page behind it");
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  if (await page.evaluate(() => document.getElementById("pal").classList.contains("on"))) P("Escape does not close the search dialog when focus is outside its input");
  // 8. toasts and the play button
  if (!(await page.evaluate(() => { const t = document.getElementById("toast"); return t.getAttribute("role") === "status" || t.getAttribute("aria-live") === "polite"; })) && !(await page.evaluate(() => !!document.querySelector("#toastLive")))) P("the toast (copied, residuals, errors) is silent for screen readers");
  const pn = await page.getAttribute("#play", "aria-pressed"); if (pn === null) P("the play button does not say whether it is playing (aria-pressed, or a name that changes)");
  // 9. views: switching says what is now shown
  await page.evaluate(() => { window.__live = []; new MutationObserver(ms => { for (const m of ms) { const t = m.target.nodeType === 1 ? m.target : m.target.parentElement, live = t && t.closest("[aria-live]:not([aria-live=off]),[role=status]"); if (live && live.textContent.trim()) window.__live.push(live.textContent.trim().slice(0, 200)); } }).observe(document.body, { subtree: true, childList: true, characterData: true }); });
  await page.click("#mTension"); await page.waitForTimeout(1500);
  if (!(await page.evaluate(() => window.__live.some(s => /observations/i.test(s))))) P("switching to 'Vs observations' announces nothing");
  await ctx.close();
}

await browser.close(); server.close();
if (problems.length) { const u = [...new Set(problems)]; console.log(u.slice(0, 60).join("\n") + (u.length > 60 ? `\n... and ${u.length - 60} more` : "")); console.log(`\na11y-tree: ${u.length} problem(s) in ${checks} checked page(s)`); process.exit(1); }
console.log(`a11y-tree: ${SITE.length} site pages${WITH_EXPLORER ? " and the Explorer" : ""} read as an accessibility tree: every control named, heading levels in order, landmarks unique, link names unambiguous, tables with header cells, row headers and names, new-tab links announced; dials page announces its results and keeps focus`);
