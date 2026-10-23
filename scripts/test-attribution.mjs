// Attribution: every entry names an existing record, carries evidence (a quote and where it is), is exported in the records table and credited in the BibTeX file.
import assert from "node:assert/strict";
import fs from "node:fs";
import { spawnSync } from "node:child_process";

const ROOT = new URL("../", import.meta.url).pathname;
const A = JSON.parse(fs.readFileSync(ROOT + "data/attribution.json", "utf8"));
const r = spawnSync("node", [ROOT + "scripts/apply-attribution.mjs", "--check"], { encoding: "utf8" });
assert.equal(r.status, 0, r.stderr + r.stdout);
for (const e of A.entries) {
  assert.ok(A.kinds[e.kind], `${e.recordId}: kind ${e.kind} has a sentence`);
  assert.ok(["stated", "inferred"].includes(e.confidence), `${e.recordId}: confidence`);
  assert.ok(e.evidence?.quote && e.evidence?.where, `${e.recordId}: evidence quote and place`);
  if (A.kinds[e.kind].includes("{primary}")) assert.ok(e.primarySource || e.candidates?.length, `${e.recordId}: this kind needs a primary source or the candidates`);
}
const csv = fs.readFileSync(ROOT + "data/export/sim-highline-records.csv", "utf8").split("\n").find(l => l.startsWith("record_id"));
assert.ok(csv.includes("attribution_kind") && csv.includes("primary_source"), "the records table has the attribution columns");
const bib = fs.readFileSync(ROOT + "data/export/sim-highline-citations.bib", "utf8");
assert.match(bib, /primary source of curves reproduced in other records/, "the primary sources are credited in the BibTeX file");
assert.match(bib, /Garcia et al\. 2025/, "Garcia et al. 2025 is credited for the SIMBA curves in the COLIBRE MZR comparison");
console.log(`attribution: ${A.entries.length} records, evidence for each, credited in the records table and the BibTeX file`);
