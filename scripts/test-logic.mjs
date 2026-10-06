import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import vm from "node:vm";
const root = new URL("../", import.meta.url);
const ctx = {};
vm.runInNewContext(await readFile(new URL("highline/logic.js", root), "utf8"), ctx);
const L = ctx.SimHighlineLogic;
const rec = (source, run, z, tier = "catalog-derived") => ({ source, run, epoch: { zRepresentative: z }, provenance: { tier } });

assert.equal(L.tol(0), .15);
assert.ok(Math.abs(L.tol(9) - 1) < 1e-12);
assert.equal(L.nearest([], 3), 0);
assert.equal(L.nearest([0, 1, 2, 4], 2.9), 2);
assert.equal(L.nearest([0, 1, 2, 4], 3.1), 4);

const fl = L.primaryUnits([rec("FLAMINGO", "L1_m9", 0), rec("FLAMINGO", "L1_m9 variation Jet", 0), rec("FLAMINGO", "L1_m10", 0), rec("FLAMINGO", "L1_m10", 1)]);
assert.deepEqual([...fl], ["FLAMINGO|L1_m9"], "fiducial pattern wins over more epochs");
const variants = L.primaryUnits([rec("X", "low-res", 0), rec("X", "low-res", 1), rec("X", "main", 0)]);
assert.deepEqual([...variants], ["X|main"], "variant-like runs lose to plain runs");
const epochs = L.primaryUnits([rec("Y", "a", 0), rec("Y", "b", 0), rec("Y", "b", 1)]);
assert.deepEqual([...epochs], ["Y|b"], "more epochs wins among equals");
const tiers = L.primaryUnits([rec("Z", "a", 0, "digitized-figure"), rec("Z", "b", 0, "official-table")]);
assert.deepEqual([...tiers], ["Z|b"], "better evidence tier wins on a tie");
assert.deepEqual([...L.primaryUnits([rec("W", "b", 0), rec("W", "a", 0)])], ["W|a"], "alphabetical last resort");
assert.equal(L.primaryUnits([rec("A", "r", 0), rec("B", "r", 0)]).size, 2, "one unit per source");

const interp = (pts, x) => { for (let i = 0; i < pts.length - 1; i++) if (x >= pts[i].x && x <= pts[i + 1].x) return pts[i].y + (pts[i + 1].y - pts[i].y) * (x - pts[i].x) / (pts[i + 1].x - pts[i].x); return NaN; };
const line = (a, b, xs) => xs.map(x => ({ x, y: a + b * x }));
assert.ok(Math.abs(L.medianOffset(line(0, 1, [1, 2, 3, 4]), line(0.5, 1, [0, 1, 2, 3, 4, 5]), interp) - 0.5) < 1e-12, "constant offset recovered");
assert.equal(L.medianOffset(line(0, 1, [1, 2]), line(0, 1, [0, 5, 6]), interp), null, "fewer than three anchor points");
assert.equal(L.medianOffset(line(0, 1, [8, 9, 10]), line(0, 1, [0, 1, 2]), interp), null, "no overlap gives no offset");
assert.equal(L.medianOffset(line(0, 1, [0, 1, 2, 3, 20]), line(1, 1, [0, 1, 2, 3, 4]), interp), 1, "points outside the simulation range are ignored");

const obs = [{ source: "COSMOS-Web 2025", epoch: { zRepresentative: 1 } }, { source: "COSMOS-Web 2025", epoch: { zRepresentative: 3 } }, { source: "Baldry et al. 2012 (GAMA)", epoch: { zRepresentative: 0.03 } }];
assert.equal(L.pickAnchor(obs, /COSMOS-Web 2025|Baldry/, 0).source, "Baldry et al. 2012 (GAMA)");
assert.equal(L.pickAnchor(obs, /COSMOS-Web 2025|Baldry/, 2.6).epoch.zRepresentative, 3);
assert.equal(L.pickAnchor(obs, /Nothing/, 1), null);

const records = [];
for (const f of (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json"))) for (const r of JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records) if (r.kind === "simulation") records.push(r);
const rels = [...new Set(records.map(r => r.relation))];
for (const rel of rels) {
  const rs = records.filter(r => r.relation === rel), prim = L.primaryUnits(rs);
  for (const s of new Set(rs.map(r => r.source))) assert.equal([...prim].filter(u => u.startsWith(s + "|")).length, 1, `${rel}: ${s} must have exactly one fiducial run`);
}
const btfr = L.primaryUnits(records.filter(r => r.relation === "btfr"));
assert.ok([...btfr].includes("SIMBA|m100n1024 + hires (combined), V_flat fit"), "SIMBA BTFR defaults to the combined V_flat fit");
assert.ok([...L.primaryUnits(records.filter(r => r.relation === "gsmf"))].some(u => u.startsWith("FLAMINGO|L1_m9")), "FLAMINGO fiducial is L1_m9");
const sz = L.primaryUnits(records.filter(r => r.relation === "size"));
assert.ok([...sz].some(u => /^COLIBRE\|.*centrals, star-forming/.test(u)), "COLIBRE size defaults to star-forming centrals");
console.log(`Logic tests passed: ${rels.length} relations, one fiducial run per source in each`);
