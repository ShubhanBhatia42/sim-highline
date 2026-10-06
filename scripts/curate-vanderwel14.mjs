import { writeFile } from "node:fs/promises";
import { definitionsFor } from "./definitions.mjs";

const source = "van der Wel et al. 2014";
const provenance = table => ({tier: table === "Table 1" ? "published-fit" : "published-table", citation: `van der Wel et al. 2014, ApJ 788, 28, ${table}`, doi: "10.1088/0004-637X/788/1/28", url: "https://arxiv.org/abs/1404.2844", retrieved: "2026-10-02", table});
const bins = [0.25, 0.75, 1.25, 1.75, 2.25, 2.75];
const epoch = z => ({zRepresentative: z, zMin: +(z - 0.25).toFixed(2), zMax: +(z + 0.25).toFixed(2), mode: "observational-bin", snapshot: null});
const axes = population => ({xDefinition: "log10 stellar mass, Chabrier IMF", xUnit: "log10(Msun)", yDefinition: `log10 major-axis effective radius at rest-frame 5000 A (${population})`, yUnit: "log10(kpc)"});

const table1 = {
  late: {xMin: 9.48, rows: [[0.86,0.02,0.25,0.02,0.16],[0.78,0.01,0.22,0.01,0.16],[0.70,0.01,0.22,0.01,0.17],[0.65,0.01,0.23,0.01,0.18],[0.55,0.01,0.22,0.01,0.19],[0.51,0.01,0.18,0.02,0.19]]},
  early: {xMin: 10.3, rows: [[0.60,0.02,0.75,0.06,0.10],[0.42,0.01,0.71,0.03,0.11],[0.22,0.01,0.76,0.04,0.12],[0.09,0.01,0.76,0.04,0.14],[-0.05,0.02,0.76,0.04,0.14],[-0.06,0.03,0.79,0.07,0.14]]}
};
const tableA3 = {
  0.25: [[9.25,0.21,0.46,0.69],[9.75,0.28,0.54,0.77],[10.25,0.27,0.54,0.82],[10.75,0.49,0.75,0.99]],
  0.75: [[9.25,0.16,0.41,0.64],[9.75,0.25,0.52,0.74],[10.25,0.18,0.52,0.78],[10.75,0.35,0.59,0.84],[11.25,0.66,0.85,1.04]],
  1.25: [[9.75,0.21,0.47,0.68],[10.25,0.15,0.52,0.74],[10.75,0.23,0.57,0.80],[11.25,0.49,0.74,0.94]],
  1.75: [[9.75,0.15,0.42,0.65],[10.25,0.12,0.48,0.69],[10.75,0.09,0.48,0.74],[11.25,0.34,0.64,0.83]],
  2.25: [[10.25,0.10,0.41,0.63],[10.75,0.03,0.45,0.68],[11.25,0.28,0.59,0.83]],
  2.75: [[10.75,0.01,0.43,0.65],[11.25,0.27,0.52,0.75]]
};

const records = [];
for (const [type, {xMin, rows}] of Object.entries(table1)) rows.forEach(([logA, logAError, alpha, alphaError, sigma], i) => {
  const z = bins[i], population = type === "late" ? "late-type (UVJ star-forming)" : "early-type (UVJ quiescent)";
  records.push({
    id: `vanderwel14.size.${type}.z${z}`, source, run: `${type}-type`, kind: "observation", relation: "size", epoch: epoch(z), axes: axes(population),
    domain: {xMin, xMax: 11.5},
    representation: {type: "parametric", equation: "R_eff/kpc = A (M/5e10 Msun)^alpha", expression: "logA+alpha*(x-log10(5e10))", parameters: {logA, logAError, alpha, alphaError}},
    scatter: {value: sigma, unit: "dex", meaning: "intrinsic scatter in log R_eff (Table 1)"},
    selection: {population, warning: "UVJ-based type split with 10% assumed misclassification; fit mass limits >3e9 Msun (late) and >2e10 Msun (early). Section 3.1 states a 7e10 Msun pivot while the Table 1 caption gives 5e10 Msun; the caption is used here."},
    definitions: definitionsFor(source, `size-${type}`), provenance: provenance("Table 1"), calibration: "validation", rankable: true,
    notes: "Transcribed from Table 1. Cosmology (Om, OL, h) = (0.27, 0.73, 0.71)."
  });
});
for (const z of bins) {
  const points = tableA3[z].map(([x, lo, y, hi]) => ({x, y, yLow: lo, yHigh: hi}));
  records.push({
    id: `vanderwel14.size.all.z${z}`, source, run: "early+late", kind: "observation", relation: "size", epoch: epoch(z), axes: axes("all galaxies"),
    domain: {xMin: points[0].x, xMax: points.at(-1).x},
    representation: {type: "points", intervalKind: "scatter", points},
    scatter: {lower: "16th percentile of the size distribution", upper: "84th percentile of the size distribution"},
    selection: {population: "all galaxies (early+late) above the redshift-dependent mass limit", warning: "Medians in 0.5 dex mass bins; percentiles describe the population spread, not the uncertainty of the median."},
    definitions: definitionsFor(source, "size-all"), provenance: provenance("Table A3"), calibration: "validation", rankable: true,
    notes: "Transcribed from Appendix Table A3 (major-axis radii, mass bins)."
  });
}
await writeFile(new URL("../data/curves/vanderwel14.json", import.meta.url), `${JSON.stringify({schemaVersion: "1.0.0", records}, null, 2)}\n`);
console.log(`Curated ${records.length} van der Wel et al. 2014 size records`);
