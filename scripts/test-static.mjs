import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";

for (const file of ["data/curve-index.js", "data/coverage-report.json", "sim_highline.py"]) {
  const source = await readFile(new URL(`../${file}`, import.meta.url));
  const built = await readFile(new URL(`../dist/${file}`, import.meta.url));
  assert(source.equals(built), `${file}: dist output differs from source`);
}
for (const retired of ["app.js", "views.js", "styles.css"]) await assert.rejects(access(new URL(`../dist/${retired}`, import.meta.url)), `${retired}: retired workbench file is still shipped`);
await assert.rejects(access(new URL("../dist/data/raw", import.meta.url)), "raw downloads must not ship");

const index = await readFile(new URL("../dist/index.html", import.meta.url), "utf8");
assert(index.includes('url=site/index.html'), "dist/index.html must redirect to the landing page");

const app = await readFile(new URL("../dist/highline.html", import.meta.url), "utf8");
for (const forbidden of ["sourceBias", "deterministic demonstrations", "PUBLISHED_CURVES", "Concordance", "populationSelect", "comparisonMode"]) assert(!app.includes(forbidden), `${forbidden}: synthetic or composite-score path returned`);
for (const required of ["digitized", "rankable", "Nothing is synthesised", "not comparable"]) assert(app.includes(required), `${required}: evidence-first language missing from the app`);

console.log("Static release valid: redirect, parity with sources, retired workbench absent, evidence-first language present");
