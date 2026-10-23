// Applies the corrections listed in data/compilation-corrections.json to the curves taken from the SWIFT/VELOCIraptor comparison-data compilation (data/curves/comparison-data.json).
// Each correction (kind "numeric", "label" or "flag"; a flag changes nothing but the record's warning) names the records it changes, the shift in dex (x and y), any definition fields to set, the evidence, and why. A record that has been corrected carries the correction in provenance.corrections (id, summary and a hash of the points as ingested), so a reader can undo it and see why it was made. Applying twice does nothing.
// Usage: node scripts/apply-compilation-corrections.mjs [--check]   (--check changes nothing and fails if the file and the list disagree)
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = new URL("../", import.meta.url).pathname;
const CURVES = ROOT + "data/curves/comparison-data.json";
const LIST = ROOT + "data/compilation-corrections.json";
const check = process.argv.includes("--check");

const round = v => Math.round(v * 1e6) / 1e6;
const sha = x => crypto.createHash("sha256").update(JSON.stringify(x)).digest("hex");
const doc = JSON.parse(fs.readFileSync(CURVES, "utf8"));
const list = JSON.parse(fs.readFileSync(LIST, "utf8"));
const byId = new Map(doc.records.map(r => [r.id, r]));

function setPath(obj, path, value) {
  const keys = path.split(".");
  let o = obj;
  for (const k of keys.slice(0, -1)) o = o[k] ??= {};
  o[keys.at(-1)] = value;
}

const problems = [];
let applied = 0;
const listed = new Set();
for (const c of list.corrections) {
  if (!c.id || !c.summary || !Array.isArray(c.evidence) || !c.evidence.length) problems.push(`${c.id}: needs id, summary and evidence`);
  for (const rid of c.records) {
    listed.add(`${c.id}|${rid}`);
    const r = byId.get(rid);
    if (!r) { problems.push(`${c.id}: no record ${rid}`); continue; }
    const marks = (r.provenance.corrections ??= []);
    if (marks.some(m => m.id === c.id)) continue;
    if (check) { problems.push(`${rid}: correction ${c.id} is listed but not applied`); continue; }
    const before = sha(r.representation.points ?? r.representation);
    const dx = c.dxDex ?? 0, dy = c.dyDex ?? 0;
    if ((dx || dy) && r.representation.type === "points") {
      for (const p of r.representation.points) {
        if (dx) p.x = round(p.x + dx);
        if (dy) for (const k of ["y", "yLow", "yHigh"]) if (typeof p[k] === "number") p[k] = round(p[k] + dy);
      }
      if (r.domain && dx) { r.domain.xMin = round(r.domain.xMin + dx); r.domain.xMax = round(r.domain.xMax + dx); }
    } else if (dx || dy) problems.push(`${rid}: shifts only apply to points records`);
    for (const [path, value] of Object.entries(c.set ?? {})) setPath(r, path, value);
    r.selection ??= {};
    r.selection.warning = [r.selection.warning, `${c.kind === "flag" ? "Checked by sim-highline against the paper, not changed" : "Corrected by sim-highline"}: ${c.summary}`].filter(Boolean).join(" ");
    marks.push({ id: c.id, summary: c.summary, dxDex: dx || undefined, dyDex: dy || undefined, pointsBefore: before });
    applied++;
  }
}
for (const r of doc.records) for (const m of r.provenance.corrections ?? []) if (!listed.has(`${m.id}|${r.id}`)) problems.push(`${r.id}: carries correction ${m.id} that is not in the list`);

if (problems.length) { console.error("compilation corrections:\n  " + problems.join("\n  ")); process.exit(1); }
if (!check && applied) fs.writeFileSync(CURVES, JSON.stringify(doc, null, 2) + "\n");
console.log(`compilation corrections: ${list.corrections.length} listed, ${applied} record(s) changed now, ${[...listed].length} record-corrections in place`);
