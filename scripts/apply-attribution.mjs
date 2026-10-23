// Writes provenance.attribution into the records listed in data/attribution.json: where the numbers come from when that is not simply the paper the record cites (a curve produced in another paper, a table that belongs to one of several papers in a release, a curve computed by a compilation's maintainers, values from a web page).
// The sentence shown to readers is built from data/attribution.json "kinds". For records whose warning described their source wrongly, the entry's note is added to the warning once. Idempotent. Usage: node scripts/apply-attribution.mjs [--check]
import fs from "node:fs";
import { readdirSync } from "node:fs";

const ROOT = new URL("../", import.meta.url).pathname;
const check = process.argv.includes("--check");
const A = JSON.parse(fs.readFileSync(ROOT + "data/attribution.json", "utf8"));
const files = readdirSync(ROOT + "data/curves").filter(f => f.endsWith(".json")).sort();
const byId = new Map(), docs = new Map();
for (const f of files) { const d = JSON.parse(fs.readFileSync(ROOT + "data/curves/" + f, "utf8")); docs.set(f, d); for (const r of d.records) byId.set(r.id, [f, r]); }
const problems = [], changed = new Set();
const sentence = e => {
  const t = A.kinds[e.kind];
  if (!t) { problems.push(`${e.recordId}: unknown kind ${e.kind}`); return ""; }
  if (t.includes("{primary}") && !e.primarySource) return t.replace("{primary}", `a paper that could not be settled${e.candidates?.length ? " (candidates: " + e.candidates.join("; ") + ")" : ""}`);
  return t.replace("{primary}", e.primarySource);
};
const seen = new Set();
for (const e of A.entries) {
  if (seen.has(e.recordId)) problems.push(`${e.recordId}: listed twice`);
  seen.add(e.recordId);
  const hit = byId.get(e.recordId);
  if (!hit) { problems.push(`${e.recordId}: no such record`); continue; }
  const [f, r] = hit;
  const want = { kind: e.kind, statement: sentence(e), ...(e.primarySource ? { primarySource: e.primarySource } : {}), confidence: e.confidence, evidence: e.evidence, ...(e.candidates ? { candidates: e.candidates } : {}) };
  if (JSON.stringify(r.provenance.attribution) !== JSON.stringify(want)) {
    if (check) { problems.push(`${e.recordId}: attribution is not applied (run node scripts/apply-attribution.mjs)`); continue; }
    r.provenance.attribution = want; changed.add(f);
  }
  if (e.note && !check && !(r.selection.warning || "").includes("Attribution note (sim-highline)")) {
    r.selection.warning = [r.selection.warning, `Attribution note (sim-highline): ${e.note}.`.replace(/\.\.$/, ".")].filter(Boolean).join(" "); changed.add(f);
  }
}
for (const [id, [, r]] of byId) if (r.provenance.attribution && !seen.has(id)) problems.push(`${id}: carries an attribution that is not in the list`);
if (problems.length) { console.error("attribution:\n  " + problems.join("\n  ")); process.exit(1); }
if (!check) for (const f of changed) fs.writeFileSync(ROOT + "data/curves/" + f, JSON.stringify(docs.get(f), null, 2) + "\n");
console.log(`attribution: ${A.entries.length} records listed, ${changed.size} file(s) changed now`);
