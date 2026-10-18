// Per-galaxy distributions: a record's counts on a grid (representation.distribution) are the primary information. This script derives from them, with the same
// function the Explorer uses (compare.js), the summary (quantiles, fractions below thresholds, the fraction between two thresholds, peak positions) and the ordinary
// points that the rest of the project understands (median with a 16 to 84 per cent band per x bin). A record whose representation.type is "distribution" is first
// rewritten into that form. Idempotent. Usage: node scripts/derive-distributions.mjs
import { readFile, readdir, writeFile } from "node:fs/promises";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const ctx = { globalThis: {} };
vm.runInNewContext(await readFile(new URL("compare.js", root), "utf8"), ctx);
const C = ctx.globalThis.SimHighlineCompare;
const DEFAULT_THRESHOLDS = { ssfr: [-11.0, -10.5] };  // the two quenching criteria already used by the quenched-fraction records; between them: the green valley
let changed = 0, made = 0;
for (const file of (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json")).sort()) {
  const url = new URL(`data/curves/${file}`, root), payload = JSON.parse(await readFile(url, "utf8")); let touched = false;
  for (const r of payload.records) {
    const rep = r.representation;
    if (rep.type === "distribution") {
      const { xEdges, yEdges, counts, weighting, thresholds, clipped, nSims, ...rest } = rep;
      r.representation = { type: "points", connect: true, intervalKind: "scatter", points: [], distribution: { xEdges, yEdges, counts, weighting: weighting || "number", ...(thresholds ? { thresholds } : {}), ...(clipped ? { clipped } : {}), ...(nSims ? { nSims } : {}) }, ...Object.fromEntries(Object.entries(rest).filter(([k]) => !["type", "intervalKind", "connect", "points", "distribution"].includes(k))) };
      touched = true;
    }
    const d = r.representation.distribution;
    if (!d) continue;
    made++;
    d.thresholds = d.thresholds || DEFAULT_THRESHOLDS[r.relation] || [];
    const stats = C.distributionStats(d), pts = C.distributionPoints(d, stats);
    if (!pts.length) throw new Error(`${r.id}: no x bin has at least ${stats.minCount} galaxies`);
    const next = { ...d, summary: stats };
    if (JSON.stringify(next) !== JSON.stringify(d) || JSON.stringify(pts) !== JSON.stringify(r.representation.points)) touched = true;
    r.representation.distribution = next; r.representation.points = pts; r.representation.connect = true; r.representation.intervalKind = "scatter";
    r.domain = { xMin: pts[0].x, xMax: pts.at(-1).x };
  }
  if (touched) { await writeFile(url, `${JSON.stringify(payload, null, 2)}\n`); changed++; }
}
console.log(`Distributions derived: ${made} records with counts, ${changed} files rewritten`);
