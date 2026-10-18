// Per-galaxy distributions: compare.js reproduces, to the last stored digit, the statistics that scripts/distribution_stats.py computed for the shared fixture, every record's summary and points follow from its counts, and the counts add up.
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const ctx = { globalThis: {} };
vm.runInNewContext(await readFile(new URL("compare.js", root), "utf8"), ctx);
const C = ctx.globalThis.SimHighlineCompare;
const fx = JSON.parse(await readFile(new URL("tests/fixtures/distribution-fixture.json", root), "utf8"));
assert.deepEqual(JSON.parse(JSON.stringify(C.distributionStats(fx.input))), fx.expected, "compare.js and distribution_stats.py disagree on the fixture");
let n = 0, galaxies = 0;
for (const f of (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json"))) {
  for (const r of JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records) {
    const d = r.representation.distribution; if (!d) continue; n++;
    const total = d.counts.flat().reduce((a, b) => a + b, 0); galaxies += total;
    assert.equal(d.summary.n.reduce((a, b) => a + b, 0), total, `${r.id}: the bin totals must add up to the counts`);
    assert.deepEqual(JSON.parse(JSON.stringify(C.distributionStats(d))), d.summary, `${r.id}: stored summary is not the summary of its counts`);
    assert.equal(r.representation.points.length, d.summary.n.filter(v => v >= d.summary.minCount).length, `${r.id}: one point per populated bin`);
    for (const p of r.representation.points) assert.ok(p.yLow <= p.y && p.y <= p.yHigh, `${r.id}: median outside its band`);
    for (let i = 0; i < d.summary.fracBelow.length; i++) for (const v of d.summary.fracBelow[i]) assert.ok(v === null || (v >= 0 && v <= 1), `${r.id}: a fraction outside 0 to 1`);
    if (d.thresholds.length >= 2) for (const v of d.summary.between) assert.ok(v === null || (v >= -1e-9 && v <= 1), `${r.id}: green-valley share outside 0 to 1`);
  }
}
assert.ok(n >= 15, `expected the CAMELS distribution records, found ${n}`);
console.log(`distribution tests passed: ${n} records, ${galaxies.toLocaleString()} galaxies, JS equals Python on the fixture`);
