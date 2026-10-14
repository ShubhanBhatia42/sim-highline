import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
const root = new URL("../dist/", import.meta.url);
const manifest = JSON.parse(await readFile(new URL("../data/export/sim-highline-manifest.json", import.meta.url), "utf8"));
const release = JSON.parse(await readFile(new URL("../data/release.json", import.meta.url), "utf8"));
const PAGES = ["index", "studies", "study-definitions", "study-harmonization", "study-sfh", "study-joint", "retune", "data", "methods", "sources"];
const html = {};
for (const page of [...PAGES, "findings"]) {
  const h = html[page] = await readFile(new URL(`site/${page}.html`, root), "utf8");
  assert(!/\{\{|__CSS__/.test(h), `${page}: unreplaced placeholder`);
  assert(h.includes(`${manifest.version}`), `${page}: version missing`);
  for (const m of h.matchAll(/(?:href|src)="((?:\.\.\/|)[^":#]+)(?:#[^"]*)?"/g)) {
    const link = m[1];
    if (/^https?:|^mailto:/.test(link)) continue;
    await access(new URL(link, new URL(`site/${page}.html`, root))).catch(() => assert.fail(`${page}: broken link ${link}`));
  }
  assert(/<title>[^<]{10,}<\/title>/.test(h) && /name="description"/.test(h), `${page}: title or description missing`);
  assert((h.match(/<h1>/g) || []).length === 1, `${page}: exactly one h1`);
  // in-page anchors must exist
  for (const m of h.matchAll(/href="#([^"]+)"/g)) assert(h.includes(`id="${m[1]}"`), `${page}: anchor #${m[1]} has no target`);
  assert(h.includes('<a class="mark" href="index.html" aria-label="sim-highline home">sim-highline</a>'), `${page}: wordmark links home`);
  assert(h.includes("Michroma") === false && h.includes("Jost") === false, `${page}: old fonts must be gone`);
  assert(h.includes('<nav class="menu" aria-label="Main">') && h.includes('href="../highline.html">Explorer</a>') && h.includes('href="methods.html"'), `${page}: main navigation missing`);
  assert(h.includes(`v${release.version} · doi`), `${page}: version and DOI chip missing`);
  assert(!/concord/i.test(h.replace(/concordance/gi, "")), `${page}: no old project name`);
  assert(/<main id="main"/.test(h) && /class="skip"/.test(h), `${page}: landmark and skip link`);
}
// the old pages are gone and the old findings URL redirects
for (const gone of ["about", "use-cases"]) await access(new URL(`site/${gone}.html`, root)).then(() => assert.fail(`${gone}.html must be removed`), () => {});
assert(/http-equiv="refresh" content="0; url=studies.html"/.test(html.findings) && html.findings.includes('href="studies.html"'), "findings.html must redirect to studies.html");
for (const page of PAGES) assert(!/href="findings\.html"/.test(html[page]) && !/href="(about|use-cases)\.html"/.test(html[page]), `${page}: links to a retired page`);

const index = html.index;
assert(index.includes(manifest.nRecords.toLocaleString("en-US")), "index: record count must match the export manifest");
assert(/<svg viewBox/.test(index) && (index.match(/<path d="M/g) || []).length >= 5, "index: figure must contain curves");
assert(/Not independently reviewed/.test(index), "index must state limits");
assert(/Fig\. 1/.test(index) && /Records by relation/.test(index), "index: figure and data table expected");
for (const id of ["S1", "S2", "S3", "S4"]) assert(index.includes(`<td class="sid">${id}</td>`), `index: study ${id} missing from the table`);
assert(/<tr class="todo"><td class="sid">S4<\/td>[\s\S]*?In preparation/.test(index), "index: S4 row must say in preparation");
assert(!/hero|What you get|What it is not|Start with a question|problem it removes/i.test(index), "index: marketing sections must be gone");

const studies = html.studies;
assert(["study-definitions", "study-harmonization", "study-sfh", "study-joint"].every(s => studies.includes(`href="${s}.html"`)), "studies: every study must be linked");
assert(/pre-registered|Protocol first/i.test(studies) && /Null results are reported/.test(studies), "studies: how studies are registered");
for (const [p, n] of [["study-definitions", 3], ["study-harmonization", 1], ["study-sfh", 3]]) {
  assert((html[p].match(/<figure class="fig/g) || []).length === n, `${p}: ${n} figures expected`);
  for (const s of ["Question", "Data", "Result", "Limits", "Reproduce"]) assert(new RegExp(`<h2 id="[a-z]+-h"><span class="sn">§\\d</span>[^<]*${s}`).test(html[p]), `${p}: section ${s}`);
  assert(/<div class="abstract">/.test(html[p]) && /Status<\/dt>/.test(html[p]), `${p}: abstract and status line`);
}
assert(html["study-harmonization"].includes("PROTOCOL-harmonization.md") && html["study-harmonization"].includes("ANALYSIS-harmonization.md"), "S2 links protocol and analysis");
assert(["PROTOCOL-model-form.md", "ANALYSIS-model-form.md", "POWER-model-form.md"].every(f => html["study-sfh"].includes(f)), "S3 links protocol, analysis and power study");
for (const p of ["study-joint", "retune"]) assert(/In preparation/.test(html[p]) && html[p].includes("<!-- CONTENT -->"), `${p}: stub with a content marker`);

const data = html.data;
assert(/camels-sfrd\.json/.test(data) && /CAMELS galaxy summaries \(in preparation\)/.test(data) && !/camels-galaxies/.test(data), "data: ensembles listed, galaxy summaries unlinked");
assert(data.includes("sim-highline-records.csv") && data.includes("sim_highline.py") && data.includes("sim-highline-citations.bib") && data.includes("CITATION.cff") && data.includes(release.doi), "data: downloads, loader and citation");
assert(data.includes('href="sources.html"') && /id="tiers"/.test(data) && /id="relations"/.test(data), "data: relation table, tiers and the sources page");
const methods = html.methods;
for (const id of ["routes", "extraction", "definitions", "audit", "limits", "ledger", "undocumented"]) assert(methods.includes(`id="${id}"`), `methods: section ${id}`);
assert(/Not independently reviewed/.test(methods) && /Not a leaderboard/.test(methods) && /Thin relations/.test(methods), "methods: limits");

const sources = html.sources;
const profiles = JSON.parse(await readFile(new URL("../data/simulation-profiles.json", import.meta.url), "utf8")).profiles;
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
for (const k of Object.keys(profiles)) assert(sources.includes(`id="${slug(k)}"`), `sources: missing simulation ${k}`);
assert(/Known metadata issues/.test(sources) && /not yet filled/.test(sources), "sources: must state what is unfilled");
assert((sources.match(/<article class="sim"/g) || []).length === Object.keys(profiles).length, "sources: one entry per simulation");
assert(!/class="card"/.test(sources), "sources: no cards");

const app = await readFile(new URL("highline.html", root), "utf8");
assert(app.includes("site/methods.html") && app.includes("site/sources.html") && app.includes("site/retune.html") && app.includes("site/studies.html"), "app must link to the Methods, Sources, Retune and Studies pages");
assert(!/about\.html|use-cases\.html/.test(app), "app: no links to retired pages");
assert(app.includes("Michroma") === false && app.includes("Jost") === false, "app: old fonts must be gone");
console.log(`Site pages valid: ${PAGES.length} pages + redirect, ${manifest.nRecords} records, links and anchors resolve`);
