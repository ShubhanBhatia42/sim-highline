import { readFile, readdir } from "node:fs/promises";

const directory = new URL("../data/curves/", import.meta.url);
const files = (await readdir(directory)).filter(file => file.endsWith(".json"));
const allowedRelations = new Set(["sfms","ssfr","gsmf","quenched","mzr","gas","hi-fraction","h2-fraction","shmr","size","jstar","btfr","bh","bhsigma","smd","bhmd","zstar","age","himf","sfrf","uvlf","sfrd","fgas500","metald","dmf","dtg","stfr","hmf"]);
const allowedTiers = new Set(["catalog-derived","official-table","published-table","published-fit","digitized-figure"]);
const ids = new Set();
const evidenceKeys = new Set();
const allowedModes = new Set(["snapshot","published-epoch","observational-bin","analytic-evolution"]);
const errors = [];
let count = 0;

for (const file of files) {
  const payload = JSON.parse(await readFile(new URL(file, directory), "utf8"));
  if (payload.schemaVersion !== "1.0.0") errors.push(`${file}: unsupported schema version`);
  for (const record of payload.records || []) {
    count += 1;
    if (ids.has(record.id)) errors.push(`${record.id}: duplicate id`);
    ids.add(record.id);
    if (!allowedRelations.has(record.relation)) errors.push(`${record.id}: invalid relation`);
    if (!allowedModes.has(record.epoch?.mode)) errors.push(`${record.id}: invalid epoch mode`);
    if (!allowedTiers.has(record.provenance?.tier)) errors.push(`${record.id}: invalid provenance tier`);
    if (!/^https:\/\//.test(record.provenance?.url || "")) errors.push(`${record.id}: HTTPS primary source required`);
    if (record.provenance?.tier === "official-table" && !/^[a-f0-9]{64}$/.test(record.provenance?.checksumSha256 || "")) errors.push(`${record.id}: official table checksum required`);
    if (!(record.epoch?.zMin <= record.epoch?.zRepresentative && record.epoch?.zRepresentative <= record.epoch?.zMax)) errors.push(`${record.id}: representative redshift outside range`);
    const single = record.representation?.type === "points" && record.representation.points?.length === 1;
    if (!(single ? record.domain?.xMin <= record.domain?.xMax : record.domain?.xMin < record.domain?.xMax)) errors.push(`${record.id}: invalid x domain`);
    if (record.provenance?.tier === "digitized-figure" && record.rankable) errors.push(`${record.id}: digitized figures cannot be rankable`);
    if (record.epoch?.mode === "snapshot" && !Number.isInteger(record.epoch.snapshot)) errors.push(`${record.id}: snapshot number required`);
    if (!record.selection || !record.axes || !record.calibration) errors.push(`${record.id}: definition metadata incomplete`);
    if (!record.definitions || typeof record.definitions !== "object") errors.push(`${record.id}: structured definitions required`);
    if (record.representation?.type === "parametric" && typeof record.representation.expression !== "string") errors.push(`${record.id}: parametric expression required`);
    if (record.representation?.type === "points" && !["uncertainty","scatter","unspecified"].includes(record.representation.intervalKind)) errors.push(`${record.id}: intervalKind must state whether intervals are uncertainties or population scatter`);
    const evidenceKey = `${record.source}:${record.run || "none"}:${record.relation}:${record.epoch?.zRepresentative}`;
    if (evidenceKeys.has(evidenceKey)) errors.push(`${record.id}: duplicate source/run/relation/epoch`);
    evidenceKeys.add(evidenceKey);
    if (record.representation?.type === "points") {
      let previous = -Infinity;
      for (const [index, point] of record.representation.points.entries()) {
        if (record.representation.connect !== false && !(point.x > previous)) errors.push(`${record.id}: x values must increase at point ${index}`);
        previous = point.x;
        if (![point.x,point.y].every(Number.isFinite)) errors.push(`${record.id}: non-finite coordinate at point ${index}`);
        if (point.yLow !== undefined && point.yLow > point.y) errors.push(`${record.id}: yLow exceeds y at point ${index}`);
        if (point.yHigh !== undefined && point.yHigh < point.y) errors.push(`${record.id}: yHigh below y at point ${index}`);
      }
      if (record.domain.xMin !== record.representation.points[0]?.x || record.domain.xMax !== record.representation.points.at(-1)?.x) errors.push(`${record.id}: domain must match point extent`);
    }
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exitCode = 1;
} else {
  console.log(`sim-highline curves: ${count} evidence records across ${files.length} files valid`);
}
