import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
const ctx = { globalThis: {} };
for (const f of ["compare.js", "export-lib.js"]) vm.runInNewContext(await readFile(new URL(`../${f}`, import.meta.url), "utf8"), ctx);
const X = ctx.globalThis.SimHighlineExport;
const base = (id, extra = {}) => ({ id, kind: "simulation", source: "S", run: "R, with \"comma\"", relation: "sfms", epoch: { zRepresentative: 2, zMin: 2, zMax: 2 }, axes: { xUnit: "log10(Msun)", yUnit: "dex", xDefinition: "x", yDefinition: "y" },
  domain: { xMin: 8, xMax: 10 }, representation: { type: "points", intervalKind: "uncertainty", connect: true, points: [{ x: 8, y: 1, yLow: 0.5, yHigh: 1.5 }, { x: 9, y: 2 }] }, definitions: { imf: "chabrier03", massDefinition: "aperture-30pkpc", cosmology: { H0: 70, Om: 0.3 } },
  provenance: { tier: "digitized-figure", citation: "Doe et al. 2020, Fig. 3, z=2", doi: "10.1/x", url: "https://x", retrieved: "2026-01-01" }, rankable: false, calibration: "unknown", selection: { population: "all" }, ...extra });
const r = base("a");
const rows = X.joined([r]);
assert.equal(rows.length, 2);
assert.equal(rows[0].y_low, 0.5);
assert.equal(rows[1].y_low, undefined);
assert.equal(rows[0].mass_class, "aperture");
assert.equal(rows[0].imf, "chabrier03");
const csv = X.toCsv(rows, X.JOINED_COLS, ["note"]);
const lines = csv.trim().split("\n");
assert.equal(lines[0], "# note");
assert.equal(lines.length, 2 + rows.length);
assert.ok(lines[2].includes('"R, with ""comma"""'), "quoted field");
assert.equal(lines[1].split(",").length, X.JOINED_COLS.length);
const par = base("p", { representation: { type: "parametric", expression: "a0+a1*x", parameters: { a0: 1, a1: 2 } }, domain: { xMin: 0, xMax: 4 }, epoch: { zRepresentative: 3, zMin: 0, zMax: 5 } });
const pr = X.joined([par], 1.5);
assert.equal(pr.length, X.NSAMPLE);
assert.equal(pr[0].x, 0);
assert.equal(pr[pr.length - 1].x, 4);
assert.ok(Math.abs(pr[pr.length - 1].y - 9) < 1e-9);
assert.equal(pr[0].z, 1.5);
assert.equal(pr[0].representation, "sampled-parametric");
assert.equal(X.joined([par])[0].z, 3);
for (const [m, c] of [["aperture-2rhalf-stars", "aperture"], ["total-bound-subhalo", "total-subhalo"], ["sed-total", "sed"], ["integral-of-SFH", "sfh-integral"], ["unspecified", "unspecified"], [undefined, "unspecified"], ["weird", "other"]]) assert.equal(X.massClass({ massDefinition: m }), c, String(m));
const bib = X.bibtex([r, base("b"), base("c", { provenance: { citation: "Other 2021", url: "https://y", tier: "digitized-figure" } })]);
assert.equal((bib.match(/@misc/g) || []).length, 2);
assert.ok(bib.includes("doi = {10.1/x}") && bib.includes("note = {Doe et al. 2020}"));
const rel = JSON.parse(await readFile(new URL("../data/release.json", import.meta.url), "utf8"));
const cff = await readFile(new URL("../CITATION.cff", import.meta.url), "utf8");
assert.equal(cff.match(/^version: (\S+)/m)[1], rel.version, "CITATION.cff version must match data/release.json");
assert.match(cff, /^cff-version: 1\.2\.0$/m, "CITATION.cff must start with cff-version 1.2.0");
assert.equal((cff.match(/^version:/gm) || []).length, 1, "CITATION.cff must have exactly one version");
assert.equal(cff.match(/^date-released: (\S+)/m)[1], rel.released, "CITATION.cff date-released must match data/release.json");
const curveDir = new URL("../data/curves/", import.meta.url);
let thirdParty = 0;
for (const f of (await (await import("node:fs/promises")).readdir(curveDir)).filter(f => f.endsWith(".json"))) for (const r of JSON.parse(await readFile(new URL(f, curveDir), "utf8")).records) { const p = r.provenance; if (/sharda|garcia/i.test([p.citation, p.url, p.sourceMember].join(" "))) { assert.ok(p.terms, `${r.id}: third-party source without provenance.terms`); thirdParty++; } }
assert.ok(thirdParty >= 200, "expected the Sharda and Garcia records to be flagged");
// the shipped files themselves: every sampled-parametric record is exported at its own representative redshift, and its points are the evaluator's values there (a redshift-dependent fit must not be evaluated at a row number: that happened once, see docs/CORRECTIONS.md)
{
  const C = ctx.globalThis.SimHighlineCompare, fs = await import("node:fs/promises");
  const recs = JSON.parse(await readFile(new URL("../data/export/sim-highline-records.json", import.meta.url), "utf8")).records;
  const parse = t => { const rows = []; let row = [], f = "", q = false; for (let i = 0; i < t.length; i++) { const c = t[i]; if (q) { if (c === '"' && t[i + 1] === '"') { f += '"'; i++; } else if (c === '"') q = false; else f += c; } else if (c === '"') q = true; else if (c === ",") { row.push(f); f = ""; } else if (c === "\n") { row.push(f); rows.push(row); row = []; f = ""; } else if (c !== "\r") f += c; } return rows; };
  const csv = t => { const all = parse(t.split("\n").filter(l => !l.startsWith("# ")).join("\n")).filter(r => r.length > 1); return { h: all[0], rows: all.slice(1) }; };
  const rc = csv(await readFile(new URL("../data/export/sim-highline-records.csv", import.meta.url), "utf8")), zi = rc.h.indexOf("z"), ri = rc.h.indexOf("representation");
  const byId = new Map(recs.map(r => [r.id, r]));
  let checked = 0;
  for (const line of rc.rows) {
    const cols = line; if (cols[ri] !== "sampled-parametric") continue;
    const r = byId.get(cols[0]); assert.ok(r, `unknown record ${cols[0]}`);
    assert.equal(Number(cols[zi]), r.epoch.zRepresentative, `${r.id}: exported z ${cols[zi]} is not its representative redshift ${r.epoch.zRepresentative}`);
    checked++;
  }
  assert.ok(checked >= 80, `parametric records checked: ${checked}`);
  const pts = csv(await readFile(new URL("../data/export/sim-highline-points.csv", import.meta.url), "utf8")), pid = pts.h.indexOf("record_id"), px = pts.h.indexOf("x"), py = pts.h.indexOf("y");
  const zdep = recs.filter(r => r.representation.type === "parametric" && Number.isFinite(C.evaluator(r)?.(r.domain.xMin, r.epoch.zRepresentative)) && Math.abs(C.evaluator(r)(r.domain.xMin, r.epoch.zRepresentative) - C.evaluator(r)(r.domain.xMin, r.epoch.zRepresentative + 3)) > 1e-3);
  assert.ok(zdep.length >= 3, "expected redshift-dependent fits (Speagle, Popesso, Marszewski)");
  for (const r of zdep) {
    const ev = C.evaluator(r), rows = pts.rows.filter(c => c[pid] === r.id);
    assert.ok(rows.length >= 10, `${r.id}: points exported`);
    for (const c of rows) assert.ok(Math.abs(Number(c[py]) - ev(Number(c[px]), r.epoch.zRepresentative)) < 2e-6, `${r.id}: point at x=${c[px]} is not the fit at z=${r.epoch.zRepresentative}`);
  }
  void fs;
}
console.log("Export library tests passed");
