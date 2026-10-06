import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

for(const file of ["index.html","styles.css","compare.js","app.js","views.js","data/curve-index.js","data/coverage-report.json"]){
  const source=await readFile(new URL(`../${file}`,import.meta.url));
  const built=await readFile(new URL(`../dist/${file}`,import.meta.url));
  assert(source.equals(built),`${file}: dist output differs from source`);
}

const html=await readFile(new URL("../dist/index.html",import.meta.url),"utf8");
for(const asset of ["styles.css?v=19","data/curve-index.js?v=19","compare.js?v=19","app.js?v=19","views.js?v=19"])assert(html.includes(asset),`${asset}: release cache key missing`);
const app=await readFile(new URL("../dist/app.js",import.meta.url),"utf8");
for(const forbidden of ["sourceBias","deterministic demonstrations","PUBLISHED_CURVES"])assert(!app.includes(forbidden),`${forbidden}: synthetic client path returned`);
for(const forbidden of ["Concordance","populationSelect","comparisonMode","Objects"])assert(!app.includes(forbidden),`${forbidden}: audited placebo or composite-score UI returned`);
for(const required of ["official table","simulation summary","no composite score","digitized-figure"])assert(html.includes(required)||app.includes(required),`${required}: evidence-first language missing`);
for(const required of ["IllustrisTNG TNG100","NIHAO zoom suite","COLIBRE fiducial suite","published figures","catalog route"])assert(app.includes(required),`${required}: simulation coverage map missing`);
for(const relation of ["ssfr","quenched","gas"])assert(app.includes(`${relation}:{`),`${relation}: relation library was narrowed away`);

console.log("Static release parity and cache keys valid");
