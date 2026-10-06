import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
import { dirname } from "node:path";
const root = new URL("../dist/", import.meta.url);
const manifest = JSON.parse(await readFile(new URL("../data/export/sim-highline-manifest.json", import.meta.url), "utf8"));
for (const page of ["index.html", "use-cases.html", "about.html", "sources.html"]) {
  const html = await readFile(new URL(`site/${page}`, root), "utf8");
  assert(!/\{\{|__CSS__/.test(html), `${page}: unreplaced placeholder`);
  assert(html.includes(`${manifest.version}`), `${page}: version missing`);
  for (const m of html.matchAll(/(?:href|src)="((?:\.\.\/|)[^":#]+)(?:#[^"]*)?"/g)) {
    const link = m[1];
    if (/^https?:|^mailto:/.test(link)) continue;
    await access(new URL(link, new URL(`site/${page}`, root))).catch(() => assert.fail(`${page}: broken link ${link}`));
  }
  assert(/<title>[^<]{10,}<\/title>/.test(html) && /name="description"/.test(html), `${page}: title or description missing`);
  assert(/<h1>/.test(html) && (html.match(/<h1>/g) || []).length === 1, `${page}: exactly one h1`);
}
const index = await readFile(new URL("site/index.html", root), "utf8");
assert(index.includes(manifest.nRecords.toLocaleString("en-US")), "index: record count must match the export manifest");
assert(/<svg viewBox/.test(index) && (index.match(/<path d="M/g) || []).length >= 5, "index: hero chart must contain curves");
assert(/What it is not/.test(index), "index must state limits");
const sources = await readFile(new URL("site/sources.html", root), "utf8");
const about = await readFile(new URL("site/about.html", root), "utf8");
const profiles = JSON.parse(await readFile(new URL("../data/simulation-profiles.json", import.meta.url), "utf8")).profiles;
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
for (const k of Object.keys(profiles)) assert(sources.includes(`id="${slug(k)}"`), `sources: missing simulation ${k}`);
assert((about.match(/<svg viewBox/g) || []).length === 4, "about: four charts expected");
assert(/Known metadata issues/.test(sources) && /not yet filled/.test(sources), "sources: must state what is unfilled");
assert((sources.match(/<article class="sim"/g) || []).length === Object.keys(profiles).length, "sources: one card per simulation");
const app = await readFile(new URL("highline.html", root), "utf8");
assert(app.includes("site/about.html") && app.includes("site/sources.html"), "app must link to the About and Sources pages");
console.log(`Marketing pages valid: ${manifest.nRecords} records, links resolve`);
