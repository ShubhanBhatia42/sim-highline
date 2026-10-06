import { readdir, readFile, writeFile } from "node:fs/promises";
const root = new URL("../", import.meta.url);
const files = (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json"));
const all = [];
for (const f of files) for (const r of JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records) all.push({ ...r, _file: f });
const sims = JSON.parse(await readFile(new URL("data/simulations.json", root), "utf8")).simulations;
const known = JSON.parse(await readFile(new URL("data/audit-known.json", root), "utf8")).accepted;
const issues = [];
const flag = (sev, code, r, msg) => { const k = known.find(k => k.code === code && r.id.startsWith(k.idPrefix)); issues.push({ sev: k ? "known" : sev, code, id: r.id, file: r._file, relation: r.relation, source: r.source, msg, reason: k?.reason }); };
const RANGE = {
  gsmf: { y: [-11, 2], x: [3, 13.7] }, sfms: { y: [-7, 4.5], x: [3, 13.7] }, ssfr: { y: [-14, -6], x: [3, 13] }, mzr: { y: [-5, 10], x: [3, 13] },
  zstar: { y: [-4, 10], x: [3, 13.7] }, size: { y: [-1.5, 3], x: [3, 13] }, shmr: { y: [-6, 0.1], x: [6, 16.5] }, bh: { y: [3, 11.5], x: [3, 13] },
  bhsigma: { y: [3, 11.5], x: [0.8, 3.2] }, quenched: { y: [-0.05, 1.05], x: [3, 13] }, jstar: { y: [-1, 6], x: [4, 13.7] }, btfr: { y: [4, 13], x: [0.5, 3.2] },
  stfr: { y: [0.5, 3.2], x: [3, 13] }, gas: { y: [-4, 3], x: [3, 13] }, smd: { y: [3, 10], x: [0, 15] }, uvlf: { y: [-9, 1], x: [-25, -5] }, sfrd: { y: [-6, 0], x: [0, 20] }, metald: { y: [-6, 3], x: [0, 15] }
};
const mono = (pts, key = "x") => pts.every((p, i) => i === 0 || p[key] >= pts[i - 1][key]);
for (const r of all) {
  const rep = r.representation, ep = r.epoch, d = r.definitions || {};
  if (!(ep.zMin <= ep.zRepresentative + 1e-9 && ep.zRepresentative <= ep.zMax + 1e-9)) flag("error", "epoch-order", r, `zMin ${ep.zMin} zRep ${ep.zRepresentative} zMax ${ep.zMax}`);
  if (r.kind === "simulation") {
    const s = sims.find(s => (s.label || s.id) && [s.id].includes(idOf(r.source)));
    const sim = simFor(r.source);
    if (sim && sim.redshiftRange && sim.redshiftRange[1] != null && (ep.zRepresentative < sim.redshiftRange[0] - 0.15 || ep.zRepresentative > sim.redshiftRange[1] + 0.15)) flag("warn", "epoch-outside-sim-range", r, `z ${ep.zRepresentative} outside ${sim.id} range ${sim.redshiftRange}`);
    if (!d.imf) flag("warn", "no-imf", r, "definitions.imf missing");
    if (!d.cosmology && r.provenance?.tier !== "catalog-derived") flag("info", "no-cosmology", r, "definitions.cosmology missing");
    if (!d.massDefinition && ["gsmf", "sfms", "ssfr", "size", "mzr", "zstar", "bh", "quenched", "gas", "jstar"].includes(r.relation)) flag("info", "no-mass-definition", r, "massDefinition missing");
  }
  if (!r.provenance?.url || !r.provenance?.citation) flag("error", "no-provenance", r, "missing url/citation");
  if (r.provenance?.tier === "official-table" && !r.provenance?.checksumSha256) flag("error", "official-no-checksum", r, "official-table needs SHA-256");
  if (r.provenance?.tier === "digitized-figure" && r.rankable) flag("error", "digitized-rankable", r, "digitized figures cannot be rankable");
  const rg = RANGE[r.relation];
  if (rep.type === "points") {
    const pts = rep.points;
    if (pts.some(p => !Number.isFinite(p.x) || !Number.isFinite(p.y))) flag("error", "non-finite", r, "non-finite point");
    if (rg) {
      const bx = pts.filter(p => p.x < rg.x[0] || p.x > rg.x[1]).length, by = pts.filter(p => p.y < rg.y[0] || p.y > rg.y[1]).length;
      if (bx) flag("warn", "x-out-of-range", r, `${bx}/${pts.length} points outside plausible x ${rg.x}`);
      if (by) flag("warn", "y-out-of-range", r, `${by}/${pts.length} points outside plausible y ${rg.y}`);
    }
    if (rep.connect !== false && !mono(pts)) flag("error", "x-not-monotone", r, "connected curve has non-monotone x");
    const bad = pts.filter(p => p.yLow != null && p.yHigh != null && (p.yLow > p.y + 1e-6 || p.yHigh < p.y - 1e-6)).length;
    if (bad) flag("warn", "band-excludes-median", r, `${bad} points with y outside [yLow,yHigh]`);
    if (r.relation === "gsmf" && rep.connect !== false && pts.length > 5) {
      const hi = pts.filter(p => p.x > 10.8);
      if (hi.length > 2 && hi[hi.length - 1].y > hi[0].y + 0.3) flag("warn", "gsmf-rises-at-high-mass", r, "log phi increases above 10^10.8");
    }
    if (r.relation === "quenched" && rep.connect !== false && pts.length > 5) {
      const lo = pts.filter(p => p.x < 9.8), hi = pts.filter(p => p.x > 10.8);
      if (lo.length && hi.length && Math.max(...hi.map(p => p.y)) < Math.min(...lo.map(p => p.y))) flag("warn", "quenched-decreases", r, "quenched fraction lower at high mass than low mass");
    }
    const key = JSON.stringify(pts.slice(0, 4).map(p => [p.x, p.y]));
    (globalThis.__dup ??= new Map()).set(key, [...(globalThis.__dup.get(key) || []), r.id]);
  }
}
for (const ids of globalThis.__dup.values()) if (ids.length > 1) for (const id of ids) flag("warn", "duplicate-data", all.find(r => r.id === id), `same first points as ${ids.filter(i => i !== id).join(", ")}`);
// cross-source agreement: same suite+relation+epoch+run-family from different provenance
const interp = (pts, x) => { for (let i = 1; i < pts.length; i++) if (pts[i - 1].x <= x && x <= pts[i].x) { const t = (x - pts[i - 1].x) / (pts[i].x - pts[i - 1].x || 1); return pts[i - 1].y + t * (pts[i].y - pts[i - 1].y); } return null; };
const groups = new Map();
for (const r of all) if (r.kind === "simulation" && r.representation.type === "points" && r.representation.connect !== false) { const k = `${r.source}|${r.relation}|${r.epoch.zRepresentative.toFixed(1)}`; (groups.get(k) || groups.set(k, []).get(k)).push(r); }
const agree = [];
for (const [k, rs] of groups) for (let i = 0; i < rs.length; i++) for (let j = i + 1; j < rs.length; j++) {
  const a = rs[i], b = rs[j];
  if (a.provenance.citation === b.provenance.citation) continue;
  const ra = a.run || "", rb = b.run || "";
  const fam = s => s.replace(/\(.*?\)/g, "").trim().split(/\s+/)[0];
  if (fam(ra) !== fam(rb)) continue;
  const same = k => JSON.stringify([a.axes[k], b.axes[k]]);
  const da = a.definitions || {}, db = b.definitions || {};
  if (a.axes.yUnit !== b.axes.yUnit || a.axes.xUnit !== b.axes.xUnit || da.population !== db.population || da.metallicityQuantity !== db.metallicityQuantity || da.massDefinition !== db.massDefinition || da.quenchingCriterion !== db.quenchingCriterion || da.sizeDefinition !== db.sizeDefinition || ra !== rb && /\b(cent|sat|active|passive|ap\d+|SF|Q)\b/i.test(ra + rb) || /variation/.test(ra + rb)) continue;
  const xs = a.representation.points.map(p => p.x).filter(x => interp(b.representation.points, x) != null);
  if (xs.length < 3) continue;
  const d = xs.map(x => interp(a.representation.points, x) - interp(b.representation.points, x)).sort((u, v) => u - v);
  const med = d[Math.floor(d.length / 2)];
  agree.push({ a: a.id, b: b.id, relation: a.relation, n: xs.length, medianOffset: +med.toFixed(3), maxAbs: +Math.max(...d.map(Math.abs)).toFixed(3) });
  if (Math.abs(med) > 0.3) flag("warn", "cross-source-offset", a, `median offset ${med.toFixed(2)} vs ${b.id} over ${xs.length} points`);
}
function idOf(name) { return name; }
function simFor(name) {
  const map = { "IllustrisTNG": ["tng100", "tng50", "tng300"], "Illustris": ["illustris"], "EAGLE": ["eagle"], "COLIBRE": ["colibre"], "FLAMINGO": ["flamingo"], "SIMBA": ["simba"], "Horizon-AGN": ["horizon"], "NewHorizon": ["newhorizon"], "Romulus25": ["romulus25"], "ASTRID": ["astrid"], "BlueTides": ["bluetides"], "FIRE-2": ["fire2"], "FIREbox": ["firebox"], "FLARES": ["flares"], "NIHAO zoom suite": ["nihao"], "Magneticum Pathfinder": ["magneticum"], "SPHINX20": ["sphinx20"], "THESAN-1": ["thesan"], "THESAN-zoom": ["thesan-zoom"] };
  const ids = map[name] || [];
  const ss = ids.map(i => sims.find(s => s.id === i)).filter(Boolean);
  if (!ss.length) return null;
  return { id: ss.map(s => s.id).join("/"), redshiftRange: [Math.min(...ss.map(s => s.redshiftRange?.[0] ?? 0)), ss.some(s => s.redshiftRange?.[1] == null) ? null : Math.max(...ss.map(s => s.redshiftRange[1]))] };
}
const bySev = s => issues.filter(i => i.sev === s).length;
const nKnown = bySev("known");
const byCode = {};
for (const i of issues) byCode[`${i.sev}:${i.code}`] = (byCode[`${i.sev}:${i.code}`] || 0) + 1;
const defs = {};
for (const r of all) if (r.kind === "simulation") { const k = r.relation; (defs[k] ??= { yDef: new Set(), yUnit: new Set(), mass: new Set() }); defs[k].yUnit.add(r.axes.yUnit); defs[k].mass.add(r.definitions?.massDefinition || "-"); }
const report = { total: all.length, known: nKnown, errors: bySev("error"), warnings: bySev("warn"), info: bySev("info"), byCode, yUnitsByRelation: Object.fromEntries(Object.entries(defs).map(([k, v]) => [k, { yUnit: [...v.yUnit], massDefinitions: [...v.mass] }])), crossSource: agree, issues };
await writeFile(new URL("data/audit-report.json", root), JSON.stringify(report, null, 1) + "\n");
console.log(`Audit: ${all.length} records, ${report.errors} errors, ${report.warnings} warnings, ${nKnown} known (accepted), ${report.info} info`);
console.log(byCode);
if (report.errors) { for (const i of issues.filter(i => i.sev === "error").slice(0, 20)) console.log("ERROR", i.id, i.code, i.msg); process.exitCode = 1; }
