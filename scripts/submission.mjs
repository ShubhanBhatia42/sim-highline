// Checks a curve table submitted by its authors and turns it into a dataset record.
//   node scripts/submission.mjs check  submissions/<folder> [...]   validate (exit 1 on any error; warnings are printed)
//   node scripts/submission.mjs record submissions/<folder>         print the record that would be added to data/curves/ (a maintainer reviews and merges it)
// A submission folder holds metadata.json (what the numbers are and where they come from) and the CSV it names (columns x, y and optionally yLow, yHigh; header required).
// See docs/SUBMIT-A-CURVE.md and submissions/_template/. Nothing here fetches anything or changes data/curves/.
import { readFile, readdir, writeFile, mkdtemp } from "node:fs/promises";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import vm from "node:vm";

const root = new URL("../", import.meta.url);
const read = async p => readFile(new URL(p, root), "utf8");
const ctx = { globalThis: {} };
vm.runInNewContext(await read("compare.js"), ctx);
const { RULES } = ctx.globalThis.SimHighlineCompare;
const RANGES = JSON.parse(await read("data/plausible-ranges.json")).ranges;
const files = (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json"));
const records = [];
for (const f of files) records.push(...JSON.parse(await read(`data/curves/${f}`)).records);

const TIERS = new Set(["published-table", "published-fit", "official-table", "catalog-derived"]);   // a figure read by eye or by script is not a submission: digitized-figure is not accepted here
const CALIB = new Set(["prediction", "validation", "tuned"]);
const LICENCES = new Set(["CC-BY-4.0", "CC0-1.0"]);
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const unset = v => v == null || v === "unspecified" || v === "heterogeneous";

// the usual axes of a relation are those of the records already in the dataset; a relation with no records needs them spelled out
function usualAxes(relation) {
  const c = new Map();
  for (const r of records) if (r.relation === relation) { const k = JSON.stringify(r.axes); c.set(k, (c.get(k) || 0) + 1); }
  const best = [...c.entries()].sort((a, b) => b[1] - a[1])[0];
  return best ? JSON.parse(best[0]) : null;
}

function parseCsv(text) {
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l && !l.startsWith("#"));
  if (lines.length < 2) throw new Error("the CSV needs a header and at least one row");
  const head = lines[0].split(",").map(s => s.trim());
  if (head[0] !== "x" || head[1] !== "y") throw new Error(`the header must start with x,y (got ${head.join(",")})`);
  const extra = head.slice(2);
  if (extra.some(c => !["yLow", "yHigh"].includes(c))) throw new Error(`only yLow and yHigh may follow x,y (got ${extra.join(",")})`);
  return lines.slice(1).map((l, i) => {
    const cells = l.split(",").map(s => s.trim());
    if (cells.length !== head.length) throw new Error(`row ${i + 1} has ${cells.length} values, the header has ${head.length}`);
    const o = {};
    head.forEach((h, j) => { o[h] = Number(cells[j]); });
    return o;
  });
}

async function build(dir) {
  const errors = [], warnings = [];
  const meta = JSON.parse(await readFile(path.join(dir, "metadata.json"), "utf8"));
  const need = (k, ok = v => v != null && v !== "") => { if (!ok(meta[k])) errors.push(`metadata.${k} is required`); };
  for (const k of ["source", "kind", "relation", "tier", "calibration", "citation", "url", "valuesFrom", "licence", "csv"]) need(k);
  if (meta.kind && !["simulation", "observation"].includes(meta.kind)) errors.push("kind must be simulation or observation");
  if (meta.tier && !TIERS.has(meta.tier)) errors.push(`tier must be one of ${[...TIERS].join(", ")} (curves read from figures are not accepted as submissions)`);
  if (meta.calibration && !CALIB.has(meta.calibration)) errors.push(`calibration must be one of ${[...CALIB].join(", ")}`);
  if (meta.licence && !LICENCES.has(meta.licence)) errors.push(`licence must be one of ${[...LICENCES].join(", ")}: the dataset is CC-BY-4.0`);
  if (meta.url && !/^https:\/\//.test(meta.url)) errors.push("url must be an https address of the paper or data release");
  if (meta.doi && !/^10\.\d{4,9}\/\S+$/.test(meta.doi)) errors.push("doi must look like 10.xxxx/yyyy");
  if (!meta.doi) warnings.push("no doi given: add it if the paper or data release has one");
  if (!meta.contact?.name) errors.push("metadata.contact.name is required (who to ask about these numbers)");
  if (meta.kind === "simulation" && !meta.run) errors.push("metadata.run is required for a simulation (the run or box: it keeps two curves of one simulation apart)");
  const ep = meta.epoch || {};
  const z = ep.zRepresentative ?? ep.z;
  if (!Number.isFinite(z)) errors.push("metadata.epoch needs z (or zRepresentative)");
  const zMin = ep.zMin ?? z, zMax = ep.zMax ?? z;
  if (!(zMin <= z && z <= zMax)) errors.push("epoch: zMin <= z <= zMax is required");
  const mode = ep.mode || (meta.kind === "simulation" ? "snapshot" : "observational-bin");
  if (!["snapshot", "published-epoch", "observational-bin", "analytic-evolution"].includes(mode)) errors.push(`epoch.mode ${mode} is not one of the allowed modes`);
  if (mode === "snapshot" && !Number.isInteger(ep.snapshot)) errors.push("epoch.snapshot (an integer) is required when mode is snapshot");
  const axes = meta.axes || usualAxes(meta.relation);
  if (!axes) errors.push(`no records exist yet for ${meta.relation}: give metadata.axes {xDefinition, xUnit, yDefinition, yUnit}`);
  else for (const k of ["xDefinition", "xUnit", "yDefinition", "yUnit"]) if (!axes[k]) errors.push(`axes.${k} is missing`);
  if (!meta.axes && axes) warnings.push(`axes taken from the records already in the dataset for ${meta.relation}: x = ${axes.xDefinition} [${axes.xUnit}], y = ${axes.yDefinition} [${axes.yUnit}]. Check that your numbers are in these units.`);
  const defs = { ...(meta.definitions || {}) };
  if (meta.population) defs.population ??= meta.population;
  const rule = RULES[meta.relation];
  if (!rule) warnings.push(`no comparability rule exists for ${meta.relation}: the curve will be shown but cannot be judged comparable until one is written`);
  else {
    for (const k of rule.hard) if (!(k in defs)) errors.push(`definitions.${k} is required for ${meta.relation} (state it, or write "unspecified" if the source does not say)`);
    for (const k of rule.soft) if (!(k in defs)) warnings.push(`definitions.${k} is not given; it will count as unspecified`);
    for (const k of Object.keys(defs)) if (unset(defs[k]) && defs[k] !== "unspecified") warnings.push(`definitions.${k} is empty: write "unspecified" if the source does not say`);
  }
  let rows = [], csvText = "";
  try {
    csvText = await readFile(path.join(dir, meta.csv || "curve.csv"), "utf8");
    rows = parseCsv(csvText);
  } catch (e) { errors.push(`CSV: ${e.message}`); }
  let prev = -Infinity;
  rows.forEach((p, i) => {
    if (![p.x, p.y].every(Number.isFinite)) errors.push(`row ${i + 1}: x and y must be numbers`);
    if (!(p.x > prev) && meta.connect !== false) errors.push(`row ${i + 1}: x must increase (set metadata.connect to false for unconnected points)`);
    prev = p.x;
    if (p.yLow !== undefined && p.yLow > p.y) errors.push(`row ${i + 1}: yLow is above y`);
    if (p.yHigh !== undefined && p.yHigh < p.y) errors.push(`row ${i + 1}: yHigh is below y`);
  });
  const rg = RANGES[meta.relation];
  if (rg && rows.length) {
    const bx = rows.filter(p => p.x < rg.x[0] || p.x > rg.x[1]).length, by = rows.filter(p => p.y < rg.y[0] || p.y > rg.y[1]).length;
    if (bx) warnings.push(`${bx} of ${rows.length} x values lie outside the usual range ${rg.x} for ${meta.relation}: check the units (log10? h-free?)`);
    if (by) warnings.push(`${by} of ${rows.length} y values lie outside the usual range ${rg.y} for ${meta.relation}: check the units (log10? h-free?)`);
  }
  if (rows.length && rows.some(p => "yLow" in p) && !meta.intervals) errors.push('say what the yLow/yHigh columns are: metadata.intervals is "uncertainty" or "scatter"');
  const id = meta.id || `sub.${slug(meta.source)}.${slug(meta.run || "main")}.${meta.relation}.z${String(z).replace(".", "p")}`;
  const record = {
    id, source: meta.source, run: meta.run || null, kind: meta.kind, relation: meta.relation,
    epoch: { zRepresentative: z, zMin, zMax, mode, snapshot: mode === "snapshot" ? ep.snapshot : null },
    axes, domain: { xMin: rows[0]?.x, xMax: rows.at(-1)?.x }, scatter: meta.scatter ?? null,
    selection: { population: meta.population || defs.population || "unspecified", ...(meta.warning ? { warning: meta.warning } : {}) },
    definitions: defs,
    provenance: {
      tier: meta.tier, citation: meta.citation, doi: meta.doi ?? null, url: meta.url, retrieved: new Date().toISOString().slice(0, 10),
      valuesFrom: meta.valuesFrom, submittedBy: meta.contact?.name, licence: meta.licence,
      ...(meta.tier === "official-table" ? { checksumSha256: createHash("sha256").update(csvText).digest("hex") } : {}),
    },
    calibration: meta.calibration, rankable: true,
    notes: `Submitted by its authors or a reader as a table (${meta.valuesFrom}); checked by scripts/submission.mjs.${meta.notes ? " " + meta.notes : ""}`,
    representation: { type: "points", intervalKind: meta.intervals || "unspecified", connect: meta.connect !== false, points: rows.map(p => Object.fromEntries(Object.entries(p).filter(([, v]) => v !== undefined))) },
  };
  if (records.some(r => r.id === id)) errors.push(`the id ${id} already exists in the dataset: set metadata.id or change source/run/epoch`);
  return { meta, record, errors, warnings };
}

const [cmd, ...dirs] = process.argv.slice(2);
if (!["check", "record"].includes(cmd) || !dirs.length) { console.error("usage: node scripts/submission.mjs check|record submissions/<folder> [...]"); process.exit(2); }
let failed = false;
for (const dir of dirs) {
  let out;
  try { out = await build(dir); } catch (e) { console.error(`${dir}: ${e.message}`); failed = true; continue; }
  if (cmd === "record") { console.log(JSON.stringify({ schemaVersion: "1.0.0", records: [out.record] }, null, 2)); if (out.errors.length) { console.error(out.errors.join("\n")); failed = true; } continue; }
  // run the dataset's own validator on the record, together with all existing records
  const tmp = path.join(await mkdtemp(path.join(tmpdir(), "sub-")), "record.json");
  await writeFile(tmp, JSON.stringify({ schemaVersion: "1.0.0", records: [out.record] }));
  const v = out.errors.length ? null : spawnSync("node", [new URL("validate-curves.mjs", import.meta.url).pathname, tmp], { encoding: "utf8" });
  if (v && v.status !== 0) out.errors.push(...(v.stderr || v.stdout).trim().split("\n").map(l => `validator: ${l}`));
  for (const w of out.warnings) console.log(`${dir}: warning: ${w}`);
  for (const e of out.errors) console.log(`${dir}: ERROR: ${e}`);
  if (out.errors.length) failed = true;
  else console.log(`${dir}: ok -> ${out.record.id} (${out.record.representation.points.length} points, ${out.warnings.length} warning${out.warnings.length === 1 ? "" : "s"})`);
}
process.exit(failed ? 1 : 0);
