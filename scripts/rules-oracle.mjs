import { readFile } from "node:fs/promises";
import vm from "node:vm";
const root = new URL("../", import.meta.url);
const ctx = { globalThis: {} };
vm.runInNewContext(await readFile(new URL("compare.js", root), "utf8"), ctx);
const C = ctx.globalThis.SimHighlineCompare;
const { records } = JSON.parse(await readFile(new URL("data/export/sim-highline-records.json", root), "utf8"));
const pairs = [], step = 37;
for (let i = 0; i < records.length; i += 7) for (let j = i + 1; j < records.length && pairs.length < 4000; j += step) if (records[i].relation === records[j].relation) pairs.push([records[i], records[j]]);
// pairs the sample above need not reach: the Friends-of-Friends halo mass of the DARWIN-1 catalogue against M200-based and BN98 relations, another code's FOF, and itself (scripts/test_rules_parity.py checks the verdicts)
const byId = new Map(records.map(r => [r.id, r]));
for (const [a, b] of [["darwin1.catalogue.shmr.z0.19", "bird22.astrid.shmr.z3"], ["darwin1.catalogue.shmr.z0.19", "darwin1.catalogue.shmr.z0.25"], ["darwin1.catalogue.shmr.z0.19", "vcd.behroozi-et-al-2019-universemachine.bn98-peak.shmr.z0"], ["darwin1.catalogue.bh.z0.19", "darwin1.catalogue.bh.z0.25"]]) if (byId.get(a) && byId.get(b)) pairs.push([byId.get(a), byId.get(b)]);
const verdicts = pairs.map(([a, b]) => { const v = C.compatible(a, b); return { a: a.id, b: b.id, verdict: v.verdict, nb: v.blockers.length, nc: v.caveats.length }; });
const user = { x: [], y: [], lo: [], hi: [] };
for (let x = 8; x <= 11.5; x += 0.37) { user.x.push(x); user.y.push(-1.4 - 0.45 * (x - 8) + 0.1 * Math.sin(x)); user.lo.push(-1.4 - 0.45 * (x - 8) + 0.1 * Math.sin(x) - 0.05); user.hi.push(-1.4 - 0.45 * (x - 8) + 0.1 * Math.sin(x) + 0.05); }
const mine = user.x.map((x, i) => ({ x, y: user.y[i], yLow: user.lo[i], yHigh: user.hi[i] }));
const stats = [];
for (const r of records.filter(r => r.relation === "gsmf" && r.representation.type === "points").slice(0, 60)) {
  const ref = r.representation.points.filter(p => Number.isFinite(p.x) && Number.isFinite(p.y)).sort((p, q) => p.x - q.x).map(p => ({ x: p.x, y: p.y, yLow: p.yLow, yHigh: p.yHigh }));
  const s = C.summarize(C.residuals(mine, ref, "uncertainty", r.representation.intervalKind === "uncertainty" ? "uncertainty" : "unspecified"));
  stats.push({ id: r.id, summary: s });
}
console.log(JSON.stringify({ user, verdicts, stats }));
