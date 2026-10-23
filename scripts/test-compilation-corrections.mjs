// Checks that every correction to a compilation curve is listed, reversible and explained: undoing the recorded shifts gives back the points as ingested (hash in the record), and each correction has its evidence.
import assert from "node:assert/strict";
import fs from "node:fs";
import crypto from "node:crypto";

const ROOT = new URL("../", import.meta.url).pathname;
const doc = JSON.parse(fs.readFileSync(ROOT + "data/curves/comparison-data.json", "utf8"));
const list = JSON.parse(fs.readFileSync(ROOT + "data/compilation-corrections.json", "utf8"));
const round = v => Math.round(v * 1e6) / 1e6;
const sha = x => crypto.createHash("sha256").update(JSON.stringify(x)).digest("hex");
let n = 0;
for (const c of list.corrections) {
  assert.ok(c.evidence.length >= (c.kind === "numeric" ? 2 : 1), `${c.id}: a number-changing correction needs at least two pieces of evidence, a label or flag at least one`);
  assert.ok(["numeric", "label", "flag"].includes(c.kind), `${c.id}: kind must be numeric, label or flag`);
  if (c.kind === "flag") assert.ok(!c.set && !c.dxDex && !c.dyDex, `${c.id}: a flag changes nothing`);
  assert.ok(c.records.length, `${c.id}: names records`);
  for (const rid of c.records) {
    const r = doc.records.find(x => x.id === rid);
    assert.ok(r, `${rid} exists`);
    const m = r.provenance.corrections?.find(x => x.id === c.id);
    assert.ok(m, `${rid} carries ${c.id}`);
    assert.match(r.selection.warning, c.kind === "flag" ? /Checked by sim-highline against the paper/ : /Corrected by sim-highline/, `${rid} says so in its warning`);
    if (r.representation.type === "points" && (m.dxDex || m.dyDex)) {
      const undone = r.representation.points.map(p => { const q = { ...p, x: round(p.x - (m.dxDex ?? 0)) }; for (const k of ["y", "yLow", "yHigh"]) if (typeof p[k] === "number") q[k] = round(p[k] - (m.dyDex ?? 0)); return q; });
      const ok = sha(undone) === m.pointsBefore;
      assert.ok(ok, `${rid}: undoing the shift gives back the points as ingested`);
    }
    n++;
  }
}
console.log(`compilation corrections: ${n} record-corrections are listed, explained and reversible`);
