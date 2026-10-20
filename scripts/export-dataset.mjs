import { readdir, readFile, writeFile, mkdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import vm from "node:vm";
const root = new URL("../", import.meta.url);
const ctx = { globalThis: {} };
for (const f of ["compare.js", "export-lib.js"]) vm.runInNewContext(await readFile(new URL(f, root), "utf8"), ctx);
const X = ctx.globalThis.SimHighlineExport, C = ctx.globalThis.SimHighlineCompare;
const release = JSON.parse(await readFile(new URL("data/release.json", root), "utf8"));
const files = (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json")).sort();
const records = [];
for (const f of files) records.push(...JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records);
const out = new URL("data/export/", root);
await mkdir(out, { recursive: true });
const recRows = records.map(r => X.recordRow(r)), ptRows = records.flatMap(r => X.pointRows(r)), distRows = records.flatMap(r => X.distRows(r)); // not records.map(X.recordRow): map passes the row index as a second argument, which these functions read as the redshift to evaluate at
const head = [`sim-highline dataset v${release.version} (${release.released}); records table, one row per evidence record`, "join with sim-highline-points.csv on record_id; see sim_highline.py"];
const outputs = {
  "sim-highline-records.csv": X.toCsv(recRows, X.RECORD_COLS, head),
  "sim-highline-points.csv": X.toCsv(ptRows, X.POINT_COLS, [`sim-highline dataset v${release.version} (${release.released}); points table, one row per plotted point (parametric records sampled at ${X.NSAMPLE} points over their domain)`]),
  "sim-highline-distributions.csv": X.toCsv(distRows, X.DIST_COLS, [`sim-highline dataset v${release.version} (${release.released}); per-galaxy distributions, one row per non-empty cell of a record's grid (x = stellar mass or similar, y = specific SFR or colour); join with sim-highline-records.csv on record_id`]),
  "sim-highline-records.json": JSON.stringify({ version: release.version, released: release.released, records }) + "\n",
  "sim-highline-citations.bib": X.bibtex(records),
  "sim-highline-conversions.json": await readFile(new URL("data/conversions.json", root), "utf8"),
  "sim-highline-corrections.json": await readFile(new URL("data/compilation-corrections.json", root), "utf8"),
  "sim-highline-rules.json": JSON.stringify({ note: "Comparability rules used by the website and by sim_highline.compatible; generated from compare.js", unset: [null, "unspecified", "heterogeneous"], minBins: C.MIN_BINS, imfDex: C.IMF_DEX, rules: C.RULES }, null, 1) + "\n"
};
const manifest = { version: release.version, released: release.released, doi: release.doi, license: release.license, nRecords: records.length, nPoints: ptRows.length, nDistributionRecords: records.filter(r => r.representation.distribution).length, nDistributionCells: distRows.length, nParametric: records.filter(r => r.representation.type === "parametric").length,
  parametricSampling: `${X.NSAMPLE} points over the record domain at zRepresentative; the published expression is evaluated, nothing else is generated`,
  columns: { records: X.RECORD_COLS, points: X.POINT_COLS, distributions: X.DIST_COLS }, files: {} };
for (const [name, text] of Object.entries(outputs)) {
  await writeFile(new URL(name, out), text);
  manifest.files[name] = { sha256: createHash("sha256").update(text).digest("hex"), bytes: Buffer.byteLength(text) };
}
await writeFile(new URL("sim-highline-manifest.json", out), JSON.stringify(manifest, null, 2) + "\n");
console.log(`Exported v${release.version}: ${records.length} records, ${ptRows.length} points -> data/export/ (${Object.entries(manifest.files).map(([k, v]) => `${k} ${(v.bytes / 1e6).toFixed(1)} MB`).join(", ")})`);
