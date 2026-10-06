import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
const root = new URL("../", import.meta.url);
const sim = JSON.parse(await readFile(new URL("data/simulation-profiles.json", root), "utf8"));
const obsP = JSON.parse(await readFile(new URL("data/observation-profiles.json", root), "utf8")).sources;
const files = (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json"));
const recs = [];
for (const f of files) recs.push(...JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records);
const simSources = new Set(recs.filter(r => r.kind === "simulation").map(r => r.source)), obsSources = new Set(recs.filter(r => r.kind !== "simulation").map(r => r.source));
for (const s of simSources) assert(sim.profiles[s], `no simulation profile for ${s}`);
for (const k of Object.keys(sim.profiles)) assert(simSources.has(k), `profile for unknown simulation ${k}`);
const ID = /^(\d{4}\.\d{4,5}|[a-z-]+\/\d{7})$/;
for (const [k, p] of Object.entries(sim.profiles)) {
  for (const f of ["code", "method", "methodDetail", "setup", "physics", "purpose", "team", "introduced"]) assert(p[f], `${k}: missing ${f}`);
  assert(p.introduced >= 2013 && p.introduced <= 2026, `${k}: implausible year`);
  assert(p.papers.length >= 1 && p.papers.every(x => ID.test(x.arxiv) && x.cite), `${k}: papers need arXiv ids`);
  assert(sim.codePapers[p.codeRef] && ID.test(sim.codePapers[p.codeRef].arxiv), `${k}: code paper missing`);
  assert(["SPH", "moving mesh", "moving mesh + radiation", "meshless", "AMR", "AMR + radiation"].includes(p.method), `${k}: unknown method class ${p.method}`);
}
for (const k of Object.keys(obsP)) { assert(obsSources.has(k), `observation profile for unknown source ${k}`); assert(obsP[k].facility && obsP[k].measures && obsP[k].kind, `${k}: incomplete profile`); }
console.log(`Profiles valid: ${Object.keys(sim.profiles).length} simulations, ${Object.keys(obsP).length} of ${obsSources.size} observational sources profiled`);
