import { copyFile, readdir, readFile, writeFile, mkdir } from "node:fs/promises";
import vm from "node:vm";
import { jointStats } from "./site-joint.mjs";
import { shapeStats } from "./site-shape.mjs";
import { withCsp } from "./csp.mjs";
const root = new URL("../", import.meta.url);
const read = async p => readFile(new URL(p, root), "utf8");
const palette = await read("data/palette.css");
const ctx = { globalThis: {} };
vm.runInNewContext(await read("compare.js"), ctx);
const { evaluator, RULES, KEY_LABEL } = ctx.globalThis.SimHighlineCompare;
const files = (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json")).sort();
const all = [];
for (const f of files) all.push(...JSON.parse(await read(`data/curves/${f}`)).records);
const release = JSON.parse(await read("data/release.json"));
const audit = JSON.parse(await read("data/audit-report.json"));
const notes = JSON.parse(await read("data/relation-notes.json")).relations;
const simProf = JSON.parse(await read("data/simulation-profiles.json"));
const obsProf = JSON.parse(await read("data/observation-profiles.json")).sources;
const manifest = JSON.parse(await read("data/export/sim-highline-manifest.json"));
const cov = JSON.parse(await read("data/coverage-report.json"));
const camels = JSON.parse(await read("data/ensembles/camels-sfrd.json"));
const sims = all.filter(r => r.kind === "simulation"), obs = all.filter(r => r.kind !== "simulation");
const uniq = a => [...new Set(a)];
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
const n = v => v.toLocaleString("en-US");
const hi = sims.filter(r => r.epoch.zRepresentative >= 6);
const stats = {
  version: release.version, released: release.released, records: n(all.length), simRecords: n(sims.length), obsRecords: n(obs.length),
  suites: uniq(sims.map(r => r.source)).length, obsSources: uniq(obs.map(r => r.source)).length,
  relations: Object.keys(notes).filter(k => !["mzrz", "mzrraw"].includes(k)).length,
  citations: uniq(all.map(r => r.provenance?.doi || r.provenance?.url)).length, zMax: Math.max(...sims.map(r => r.epoch.zRepresentative)),
  massDefs: uniq(sims.map(r => r.definitions?.massDefinition).filter(m => m && m !== "unspecified")).length,
  zHighRecords: n(hi.length), zHighSuites: uniq(hi.map(r => r.source)).length,
  digitizedShare: `${Math.round(100 * sims.filter(r => r.provenance.tier === "digitized-figure").length / sims.length)}%`,
  rankableShare: `${Math.round(100 * sims.filter(r => r.rankable).length / sims.length)}%`,
  auditNote: `The audit script checks every record (epoch order, provenance, plausible ranges, band consistency, duplicate data, cross-source agreement) and currently reports ${audit.errors} errors and ${audit.warnings} warnings; accepted exceptions are listed with a reason each. That checks consistency, not that every curve is the right one.`
};
const cslug = n => n.toLowerCase().replace(/[^a-z0-9]+/g, "");
const KNOWN = new Set(["simba", "astrid", "illustristng", "illustris", "eagle", "colibre", "flamingo", "fire2", "firebox", "nihaozoomsuite", "romulus25", "flares", "bluetides", "magneticumpathfinder", "thesan1", "thesanzoom", "sphinx20", "horizonagn", "newhorizon"]);
const colorFor = s => `var(--c-${KNOWN.has(cslug(s)) ? cslug(s) : "other"})`;
const ZOOM = new Set(["FIRE-2", "NIHAO zoom suite", "NewHorizon", "Romulus25", "THESAN-zoom"]);
const VARIANT = /variation|low[- ]?res|double|single|per galaxy|hybrid|noAGN|full SUBFIND|2 R_half|rTNG|secondary|individual|Recal-|central|quenched|L025|L050|m5|m7|Box0|Box2b|Box3|Box4|\bfit\b/i;
const FID = { FLAMINGO: /^L1_m9(?! variation)/, "Magneticum Pathfinder": /^Box2\/hr/, Illustris: /^Illustris-1$/, SPHINX20: /100-myr/ };
const interp = (p, x) => { for (let i = 1; i < p.length; i++) if (p[i - 1].x <= x && x <= p[i].x) return p[i - 1].y + (p[i].y - p[i - 1].y) * (x - p[i - 1].x) / (p[i].x - p[i - 1].x || 1); return null; };
const median = a => { const s = [...a].sort((x, y) => x - y), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const ticks = (a, b) => { const span = b - a, step = span > 8 ? 2 : span > 3 ? 1 : 0.5, o = []; for (let v = Math.ceil(a / step) * step; v <= b + 1e-9; v += step) o.push(+v.toFixed(3)); return o; };

function chart(spec) {
  const { rel, z, tol = 0.3, xref, xlab, ylab, id, filterSim = () => true, filterObs = () => true } = spec;
  const cand = sims.filter(r => !ZOOM.has(r.source) && r.relation === rel && r.representation.type === "points" && r.representation.connect !== false && Math.abs(r.epoch.zRepresentative - z) <= tol && filterSim(r));
  const pick = new Map();
  const score = r => [FID[r.source]?.test(r.run || "") ? 0 : 1, VARIANT.test(r.run || "") ? 1 : 0, -r.representation.points.length, Math.abs(r.epoch.zRepresentative - z)];
  const lt = (a, b) => { for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return a[i] < b[i]; return false; };
  for (const r of cand) { const c = pick.get(r.source); if (!c || lt(score(r), score(c))) pick.set(r.source, r); }
  const curves = [...pick.values()].sort((a, b) => a.source.localeCompare(b.source));
  const refs = [];
  for (const r of obs.filter(r => r.relation === rel && filterObs(r) && ((r.epoch.zMin - 0.05 <= z && z <= r.epoch.zMax + 0.05) || Math.abs(r.epoch.zRepresentative - z) <= tol))) {
    if (r.representation.type === "points") refs.push({ r, pts: r.representation.points.map(p => ({ x: p.x, y: p.y })), dots: r.representation.connect === false });
    else { const f = evaluator(r); if (!f) continue; const { xMin, xMax } = r.domain, pts = []; for (let i = 0; i <= 40; i++) { const x = xMin + (xMax - xMin) * i / 40, y = f(x, z); if (Number.isFinite(y)) pts.push({ x, y }); } if (pts.length > 2) refs.push({ r, pts, dots: false }); }
  }
  const sp = curves.flatMap(r => r.representation.points), xs = sp.map(p => p.x);
  const x0 = Math.floor(Math.min(...xs) * 2) / 2, x1 = Math.ceil(Math.max(...xs) * 2) / 2;
  const inr = refs.flatMap(o => o.pts).filter(p => p.x >= x0 && p.x <= x1), ys = [...sp.map(p => p.y), ...inr.map(p => p.y)].sort((a, b) => a - b);
  const y0 = Math.floor(ys[Math.floor(.01 * ys.length)]), y1 = Math.ceil(ys[Math.min(ys.length - 1, Math.floor(.995 * ys.length))]);
  const W = 760, H = 380, L = 62, R = 18, T = 14, B = 50;
  const sx = x => L + (x - x0) / (x1 - x0) * (W - L - R), sy = y => H - B - (y - y0) / (y1 - y0) * (H - T - B);
  const P = a => "M" + a.map(p => `${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join("L");
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(`${ylab} versus ${xlab} at z≈${z}: ${curves.length} simulations`)}"><g class="axis">`;
  for (const t of ticks(x0, x1)) svg += `<line x1="${sx(t)}" x2="${sx(t)}" y1="${T}" y2="${H - B}" opacity=".5"/><text x="${sx(t)}" y="${H - B + 18}" text-anchor="middle">${t}</text>`;
  for (const t of ticks(y0, y1)) svg += `<line x1="${L}" x2="${W - R}" y1="${sy(t)}" y2="${sy(t)}" opacity=".5"/><text x="${L - 8}" y="${sy(t) + 4}" text-anchor="end">${t}</text>`;
  svg += `</g><text class="al" x="${(L + W - R) / 2}" y="${H - 10}" text-anchor="middle">${esc(xlab)}</text><text class="al" transform="translate(16 ${(T + H - B) / 2}) rotate(-90)" text-anchor="middle">${esc(ylab)}</text><defs><clipPath id="c${id}"><rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}"/></clipPath></defs><g clip-path="url(#c${id})" fill="none" stroke-linecap="round" stroke-linejoin="round">`;
  for (const o of refs) svg += o.dots ? o.pts.map(p => `<circle cx="${sx(p.x).toFixed(1)}" cy="${sy(p.y).toFixed(1)}" r="1.8" fill="var(--cream3)" opacity=".55"/>`).join("") : `<path d="${P(o.pts)}" stroke="var(--cream3)" stroke-width="1.3" stroke-dasharray="3 4"/>`;
  for (const r of curves) svg += `<path d="${P(r.representation.points)}" stroke="${colorFor(r.source)}" stroke-width="2.4"${r.provenance.tier === "digitized-figure" ? ' stroke-dasharray="2 3"' : r.provenance.tier === "published-fit" ? ' stroke-dasharray="7 4"' : ""}/>`;
  svg += "</g></svg>";
  const key = curves.map(r => `<span><i style="background:${colorFor(r.source)}"></i>${esc(r.source)}</span>`).join("") + (refs.length ? `<span><i style="background:var(--cream3)"></i>observations (${uniq(refs.map(o => o.r.source)).length})</span>` : "");
  const sv = curves.map(r => interp(r.representation.points, xref)).filter(v => v != null);
  const ov = refs.filter(o => !o.dots).map(o => interp(o.pts, xref)).filter(v => v != null);
  const spread = sv.length >= 3 ? Math.max(...sv) - Math.min(...sv) : null, off = sv.length >= 3 && ov.length ? median(sv) - median(ov) : null;
  return { svg, key, curves: curves.length, nSims: sv.length, spread, off, nObs: ov.length, xref };
}

const CH = {
  gsmf: chart({ id: "g", rel: "gsmf", z: 6, xref: 9, xlab: "log M★ [M☉]", ylab: "log Φ [cMpc⁻³ dex⁻¹]" }),
  sfms: chart({ id: "s", rel: "sfms", z: 2, xref: 10, xlab: "log M★ [M☉]", ylab: "log SFR [M☉ yr⁻¹]" }),
  mzr: chart({ id: "m", rel: "mzr", z: 0, xref: 9.5, xlab: "log M★ [M☉]", ylab: "12 + log(O/H)", filterSim: r => r.definitions?.metallicityQuantity === "gas-O/H", filterObs: r => r.definitions?.metallicityQuantity === "gas-O/H" || /O\/H/.test(r.axes?.yDefinition || "") }),
  bh: chart({ id: "b", rel: "bh", z: 0, xref: 10.5, xlab: "log M★ [M☉]", ylab: "log M● [M☉]" })
};
const dex = v => Math.abs(v).toFixed(1);
const cap = (c, what, unit) => `${c.nSims} simulations reach ${what}${unit ? ` ${unit}` : ""} and span <b>${c.spread != null ? dex(c.spread) : "?"} dex</b>${c.off != null ? `; the median simulation ${Math.abs(c.off) < 0.05 ? "lies within 0.1 dex of" : `lies ${dex(c.off)} dex ${c.off >= 0 ? "above" : "below"}`} the median of the ${c.nObs} observational curve${c.nObs > 1 ? "s" : ""} shown` : ""}. Definitions differ between sources (mass aperture, IMF, SFR timescale, metallicity calibration), so part of any offset is not physics.`;
stats.hero = CH.gsmf.svg; stats.heroKey = CH.gsmf.key;
stats.heroCaption = `Stellar mass function at z ≈ 6 from ${CH.gsmf.curves} simulations (one fiducial run each; zoom samples, which are not volume complete, are left out), straight from the dataset. ${cap(CH.gsmf, "log M★ = 9")} Dotted lines are digitized from figures; solid lines are tables or catalogues.`;
for (const [k, c] of Object.entries(CH)) { stats[`${k}Svg`] = c.svg; stats[`${k}Key`] = c.key; }
stats.gsmfCap = cap(CH.gsmf, "log M★ = 9");
stats.sfmsCap = cap(CH.sfms, "log M★ = 10");
stats.mzrCap = cap(CH.mzr, "log M★ = 9.5");
stats.bhCap = cap(CH.bh, "log M★ = 10.5");
stats.gsmfN = CH.gsmf.curves; stats.sfmsN = CH.sfms.curves; stats.mzrN = CH.mzr.curves; stats.bhN = CH.bh.curves;

/* ---------- simulations and observations page ---------- */
const METHOD_ORDER = ["SPH", "moving mesh", "moving mesh + radiation", "meshless", "AMR", "AMR + radiation"];
const METHOD_BLURB = {
  "SPH": "Smoothed particle hydrodynamics follows the gas with Lagrangian particles whose properties are smoothed over neighbours. It conserves mass by construction and follows collapse well; shocks and fluid instabilities need care. Codes here: Gadget-3 family, MP-Gadget, Gasoline, ChaNGa, SWIFT (SPHENIX).",
  "moving mesh": "AREPO solves the equations on a Voronoi mesh whose cells move with the flow, combining Galilean-invariant finite-volume accuracy with the adaptivity of particles.",
  "meshless": "GIZMO's meshless finite-mass (MFM) method uses particles as cell centres with a Riemann-solver flux between them, keeping mass conservation and improving shock and mixing treatment over classical SPH.",
  "AMR": "Adaptive mesh refinement (RAMSES) uses an Eulerian grid that is refined where the mass or the local Jeans length demands it, which resolves dense gas well and handles shocks and instabilities."
};
const relOf = rs => uniq(rs.map(r => r.relation)).sort();
function runsOf(rs) { return uniq(rs.map(r => r.run)).length; }
let simHtml = "";
const profs = Object.values(simProf.profiles);
const groups = new Map();
for (const p of profs) { const cls = p.method === "AMR + radiation" ? "AMR" : p.method === "moving mesh + radiation" ? "moving mesh" : p.method; (groups.get(cls) || groups.set(cls, []).get(cls)).push(p); }
const link = (c, a) => `<a href="https://arxiv.org/abs/${esc(a)}" target="_blank" rel="noopener">${esc(c)}</a>`;
for (const cls of METHOD_ORDER.filter(c => groups.has(c))) {
  simHtml += `<h3 class="grp">${esc(cls)}</h3><p class="blurb">${esc(METHOD_BLURB[cls] || "")}</p><div class="cards">`;
  for (const p of groups.get(cls).sort((a, b) => a.source.localeCompare(b.source))) {
    const rs = sims.filter(r => r.source === p.source), z = rs.map(r => r.epoch.zRepresentative), tiers = Object.entries(rs.reduce((m, r) => (m[r.provenance.tier] = (m[r.provenance.tier] || 0) + 1, m), {})).sort((a, b) => b[1] - a[1]);
    const cp = simProf.codePapers[p.codeRef];
    simHtml += `<article class="sim" id="${slug(p.source)}"><h4>${esc(p.source)} <span class="yr">${p.introduced}${p.introducedNote ? ` (${esc(p.introducedNote)})` : ""}</span></h4>
<dl><dt>Code</dt><dd>${esc(p.code)}${cp ? ` · ${link(cp.cite, cp.arxiv)}` : ""}</dd><dt>Method</dt><dd>${esc(p.methodDetail)}</dd><dt>Set-up</dt><dd>${esc(p.setup)}</dd><dt>Physics</dt><dd>${esc(p.physics)}</dd><dt>Purpose</dt><dd>${esc(p.purpose)}</dd><dt>Team</dt><dd>${esc(p.team)}</dd>${p.publicData ? `<dt>Data</dt><dd>${esc(p.publicData)}</dd>` : ""}<dt>Papers</dt><dd>${p.papers.map(x => link(x.cite, x.arxiv)).join(" · ")}</dd></dl>
<p class="inc"><b>In sim-highline:</b> ${n(rs.length)} records · ${runsOf(rs)} run${runsOf(rs) > 1 ? "s" : ""} · ${relOf(rs).join(", ")} · z ${(+Math.min(...z).toFixed(2))} to ${(+Math.max(...z).toFixed(2))} · ${tiers.map(([t, c]) => `${c} ${t.replace("catalog-derived", "catalogue-derived").replace(/-/g, " ")}`).join(", ")} · <a href="../highline.html#r=${relOf(rs)[0]}">open</a></p></article>`;
  }
  simHtml += "</div>";
}
const codes = Object.values(simProf.codePapers).map(c => link(c.cite, c.arxiv)).join(" · ");
const fold = t => String(t).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const SKIP = new Set(["survey", "herschel", "chandra", "xmm", "groups", "stacks", "stacked", "compilation", "sdss", "gama", "jwst", "deep", "local", "dwarfs", "data"]);
function mismatch(label, cite) {
  if (!/ et al/.test(label)) return false;
  const L = fold(label), C = fold(cite).replace(/[^a-z]/g, ""), toks = L.replace(/\(.*?\)/g, " ").split(/[^a-z]+/).filter(t => t.length >= 4 && t !== "et" && !SKIP.has(t));
  if (toks.length && !toks.some(t => C.includes(t))) return true;
  const bib = cite.match(/\[\d{4}[^\]\s]*([A-Za-z])\]/), first = fold(label.trim()).replace(/^[^a-z]*/, "")[0];
  return !!(bib && first && bib[1].toLowerCase() !== first);
}
const byObs = new Map();
for (const r of obs) { const o = byObs.get(r.source) || byObs.set(r.source, { rs: [], cites: new Set(), links: new Set() }).get(r.source); o.rs.push(r); o.cites.add((r.provenance.citation || "").replace(/\s*\[[^\]]*\]/g, "")); if (r.provenance.doi) o.links.add("https://doi.org/" + r.provenance.doi); else if (r.provenance.url) o.links.add(r.provenance.url); }
const mismatched = [];
let obsHtml = "";
const KIND = k => /survey/.test(k) ? "Surveys and measurements" : /compilation|review/.test(k) ? "Compilations" : /simulation/.test(k) ? "Simulation-calibrated theory curves (not observations)" : /model/.test(k) ? "Empirical models (constrained by data, not measurements)" : "Not yet profiled";
const og = new Map();
for (const [src, o] of [...byObs].sort((a, b) => a[0].localeCompare(b[0]))) {
  const pr = obsProf[src], g = pr ? KIND(pr.kind) : "Not yet profiled";
  const z = o.rs.flatMap(r => [r.epoch.zMin, r.epoch.zMax]), cite = [...o.cites][0] || "";
  const rawCite = [...o.rs.map(r => r.provenance.citation || "")][0] || "", bad = mismatch(src, rawCite);
  if (bad) mismatched.push({ src, cite: rawCite });
  (og.get(g) || og.set(g, []).get(g)).push(`<tr id="${slug(src)}"><td>${esc(src)}${bad ? ' <span class="flag" title="the citation stored with this record names a different paper than the label">check</span>' : ""}</td><td>${pr ? esc(pr.facility) : '<span class="dim">not yet filled: see the cited paper</span>'}</td><td>${pr ? esc(pr.measures) : ""}</td><td class="id">${relOf(o.rs).join(", ")}</td><td class="mono">${(+Math.min(...z).toFixed(2)) === (+Math.max(...z).toFixed(2)) ? (+Math.min(...z).toFixed(2)) : `${(+Math.min(...z).toFixed(2))} to ${(+Math.max(...z).toFixed(2))}`}</td><td>${uniq(o.rs.map(r => (r.provenance.tier || "").replace(/-/g, " "))).join(", ")}</td><td>${[...o.links].slice(0, 1).map(l => `<a href="${esc(l)}" target="_blank" rel="noopener">${esc(cite.slice(0, 70))}</a>`).join("") || esc(cite.slice(0, 70))}</td></tr>`);
}
for (const g of ["Surveys and measurements", "Compilations", "Empirical models (constrained by data, not measurements)", "Simulation-calibrated theory curves (not observations)", "Not yet profiled"]) if (og.has(g)) obsHtml += `<h3 class="grp">${esc(g)} <span class="yr">${og.get(g).length}</span></h3><div class="tw" role="region" aria-label="${esc(g)}" tabindex="0"><table class="long dense obs"><thead><tr><th>Source</th><th>Survey / facility</th><th>What it measures</th><th>Relations</th><th>z</th><th>Evidence</th><th>Citation</th></tr></thead><tbody>${og.get(g).join("")}</tbody></table></div>`;
stats.simHtml = simHtml; stats.obsHtml = obsHtml; stats.codeLinks = codes;
const nSuites = (rel) => new Set(all.filter((r) => r.kind === "simulation" && r.relation === rel).map((r) => r.source)).size;
stats.nUvlf = nSuites("uvlf"); stats.nSfrd = nSuites("sfrd");
stats.nProfiled = Object.keys(obsProf).length; stats.nObsSources = byObs.size;
stats.mismatchHtml = mismatched.length ? `<ul class="tick">${mismatched.map(m => `<li><b>${esc(m.src)}</b>: the record's citation reads "${esc(m.cite.slice(0, 110))}".</li>`).join("")}</ul>` : "<p>None found by the automatic check.</p>";
stats.mismatchCount = mismatched.length;
stats.quickstart = (await read("site/src/quickstart-output.txt")).trimEnd().replace(/&/g, "&amp;").replace(/</g, "&lt;");
stats.css = (await read("site/src/site.css")).replace("/*__PALETTE__*/", () => palette);
// ---- findings page ----
{
  const vmCtx = { globalThis: {} }; (await import("node:vm")).runInNewContext(await read("compare.js"), vmCtx);
  const RULES = vmCtx.globalThis.SimHighlineCompare.RULES, UNSET = new Set([undefined, null, "unspecified", "heterogeneous"]);
  const A = JSON.parse(await read("data/analysis/definition-budget.json")), FL = JSON.parse(await read("data/definition-fills.json")), UD = JSON.parse(await read("data/undocumented-definitions.json"));
  const CA = JSON.parse(await read("data/analysis/conversions-audit.json"));
  const S = A.summary, pc = v => `${Math.round(100 * v / S.pairs)}%`;
  const fillSet = new Map(FL.fills.map(f => [f.id, Object.keys(f.set).length]));
  const per = new Map();
  for (const r of sims) {
    const rule = RULES[r.relation]; if (!rule) continue;
    const e = per.get(r.source) || per.set(r.source, { slots: 0, un: 0, rec: 0 }).get(r.source);
    for (const k of [...rule.hard, ...rule.soft].filter(k => k !== "cosmology")) {
      e.slots++;
      if (UNSET.has(r.definitions[k])) e.un++;
    }
    for (const id of r.provenance.definitionFills || []) for (const k of Object.keys(FL.fills.find(f => f.id === id).set)) if (!UNSET.has(r.definitions[k]) && [...rule.hard, ...rule.soft].includes(k)) e.rec++;
  }
  const rows = [...per].map(([src, e]) => ({ src, ...e, doc: e.slots - e.un - e.rec })).filter(e => e.slots >= 8).sort((a, b) => (b.un / b.slots) - (a.un / a.slots));
  const W = 860, LBL = 150, BAR = W - LBL - 90, RH = 26, H1 = rows.length * RH + 34;
  let cov = `<svg viewBox="0 0 ${W} ${H1}" role="img" aria-labelledby="covT covD"><title id="covT">Documentation of the definitions each comparison needs, by simulation</title><desc id="covD">Stacked bars: stated in the original table or figure, recovered from the source paper, still undocumented.</desc><defs><pattern id="hat" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--bg2)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--cream3)" stroke-width="2"/></pattern></defs>`;
  rows.forEach((e, i) => {
    const y = 8 + i * RH, w = v => v / e.slots * BAR;
    cov += `<text class="al" x="${LBL - 10}" y="${y + 15}" text-anchor="end">${esc(e.src.length > 22 ? e.src.slice(0, 21) + "…" : e.src)}</text><rect x="${LBL}" y="${y + 3}" width="${w(e.doc).toFixed(1)}" height="16" fill="var(--ink)" opacity=".85"/><rect x="${(LBL + w(e.doc)).toFixed(1)}" y="${y + 3}" width="${w(e.rec).toFixed(1)}" height="16" fill="var(--orange)"/><rect x="${(LBL + w(e.doc) + w(e.rec)).toFixed(1)}" y="${y + 3}" width="${w(e.un).toFixed(1)}" height="16" fill="url(#hat)" stroke="var(--line2)"/><text class="al" x="${LBL + BAR + 8}" y="${y + 15}">${Math.round(100 * e.un / e.slots)}% open</text>`;
  });
  cov += `</svg>`;
  stats.fCoverage = cov;
  const forestRows = A.sensitivity.summary.filter(g => g.relation !== "quenched");
  const nice = v => String(v).replace(/\s*\(.*$/, "").replace(/^aperture-/, "").replace(/rhalf/, "R_half").replace(/pkpc/, " pkpc").replace(/-/g, " "), cut = t => t.length > 19 ? t.slice(0, 18) + "…" : t;
  const RN = { gsmf: "stellar mass function", shmr: "stellar-to-halo mass", sfms: "main sequence", uvlf: "UV luminosity function", size: "size", gas: "cold gas fraction", btfr: "baryonic Tully-Fisher" };
  const lo = Math.min(-0.7, ...forestRows.map(g => g.medianRange[0])) - 0.05, hi = Math.max(0.3, ...forestRows.map(g => g.medianRange[1])) + 0.05, FL2 = 300, FW = W - FL2 - 70, RH2 = 36, H2 = forestRows.length * RH2 + 46;
  const fx = v => FL2 + (v - lo) / (hi - lo) * FW;
  let fs = `<svg viewBox="0 0 ${W} ${H2}" role="img" aria-labelledby="fsT fsD"><title id="fsT">Measured shift in the relation when only one definition changes inside a single simulation run</title><desc id="fsD">Dot: median over epochs; bar: range of the per-epoch medians. Zero means the definition does not matter.</desc><g class="axis">`;
  for (let v = Math.ceil(lo * 4) / 4; v <= hi; v += 0.25) fs += `<line x1="${fx(v).toFixed(1)}" x2="${fx(v).toFixed(1)}" y1="6" y2="${H2 - 30}"/><text x="${fx(v).toFixed(1)}" y="${H2 - 12}" text-anchor="middle">${v.toFixed(2)}</text>`;
  fs += `<line x1="${fx(0).toFixed(1)}" x2="${fx(0).toFixed(1)}" y1="6" y2="${H2 - 30}" style="stroke:var(--cream3);stroke-width:1.4"/></g>`;
  forestRows.forEach((g, i) => {
    const y = 20 + i * RH2, c = colorFor(g.source), m = g.median_dy;
    fs += `<text class="al" x="${FL2 - 14}" y="${y - 2}" text-anchor="end" style="font-weight:600">${esc(g.source)} · ${esc(RN[g.relation] || g.relation)}</text><text class="al" x="${FL2 - 14}" y="${y + 14}" text-anchor="end" style="fill:var(--cream3);font-size:12px">${esc(cut(nice(g.from)))} → ${esc(cut(nice(g.to)))}</text><line x1="${fx(g.medianRange[0]).toFixed(1)}" x2="${fx(g.medianRange[1]).toFixed(1)}" y1="${y + 4}" y2="${y + 4}" stroke="${c}" stroke-width="6" stroke-linecap="round" opacity=".5"/><circle cx="${fx(m).toFixed(1)}" cy="${y + 4}" r="6.5" fill="${c}" stroke="var(--bg2)" stroke-width="2"/><text class="al" x="${W - 62}" y="${y + 9}">${Math.abs(m) < 0.005 ? "0.00" : (m >= 0 ? "+" : "−") + Math.abs(m).toFixed(2)}</text>`;
  });
  fs += `</svg>`;
  stats.fForest = fs;
  const cls = [["matched", S.byClass.matched, "var(--ink)"], ["differing", S.byClass.differing, "var(--orange)"], ["unknown", S.byClass.unknown, "var(--mustard)"], ["not comparable", S.byClass.mismatch, "var(--line2)"]];
  let x = 0, lastX = -1e9, lastRow = 1, cb = `<svg viewBox="0 0 ${W} 124" role="img" aria-labelledby="clT"><title id="clT">Cross-simulation record pairs by what the documented definitions allow</title>`;
  for (const [n, v, c] of cls) {
    const w = v / S.pairs * W, row = x - lastX < 130 ? 1 - lastRow : 0, dy = row * 38; lastX = x; lastRow = row;
    cb += `<rect x="${x.toFixed(1)}" y="8" width="${Math.max(w - 2, 1).toFixed(1)}" height="30" fill="${c}"/>${row ? `<line x1="${(x + 2).toFixed(1)}" x2="${(x + 2).toFixed(1)}" y1="38" y2="${62 + dy - 14}" stroke="var(--line2)"/>` : ""}<text class="al" x="${(x + 2 + (row ? 6 : 0)).toFixed(1)}" y="${62 + dy}">${esc(n)}</text><text class="al" x="${(x + 2 + (row ? 6 : 0)).toFixed(1)}" y="${80 + dy}" style="font-weight:600">${Math.round(100 * v / S.pairs)}% · ${v}</text>`; x += w;
  }
  cb += `</svg>`;
  stats.fClasses = cb;
  stats.fLedger = FL.fills.map(f => { const n = sims.filter(r => (r.provenance.definitionFills || []).includes(f.id)).length; return `<tr><td>${esc(f.evidence.citation)}<br><a href="${esc(f.evidence.url)}" target="_blank" rel="noopener">arXiv:${esc(f.evidence.url.split("/").pop())}</a></td><td>${esc(Object.entries(f.set).map(([k, v]) => `${k} = ${v}`).join("; "))}</td><td class="n">${n}</td><td>${esc(f.evidence.where)}<br><span class="dim">“${esc(f.evidence.quote)}”</span></td></tr>`; }).join("");
  stats.fRead = FL.readWithoutResult.map(r => `<li><b>${esc(r.paper)}</b> (<a href="https://arxiv.org/abs/${esc(r.arxiv)}" target="_blank" rel="noopener">arXiv:${esc(r.arxiv)}</a>): ${esc(r.note)}</li>`).join("");
  stats.fPairs = n(S.pairs); stats.fMatchedPct = pc(S.byClass.matched); stats.fUnknownPct = pc(S.byClass.unknown); stats.fMismatchPct = pc(S.byClass.mismatch); stats.fDifferingPct = pc(S.byClass.differing);
  stats.fRecRecords = UD.summary.recordsWithRecoveredDefinition; stats.fSimRecords = UD.summary.simulationRecords; stats.fUndoc = UD.summary.undocumentedValues; stats.fNotStated = UD.summary.sourceReadNotStated; stats.fNotRead = UD.summary.sourceNotYetRead; stats.fNoPaper = UD.summary.noPaperToRead;
  stats.fTests = S.testsRun; stats.fBelow = S.testsBelow0 || S["testsBelow0.05"]; stats.fExpect = S["expectedBelow0.05UnderNull"]; stats.fBonf = S.bonferroniSignificant;
  stats.fOpenBreakdown = `${UD.summary.sourceReadNotStated} where the paper was read and does not state it${UD.summary.sourceNotYetRead ? `, ${UD.summary.sourceNotYetRead} where it has not yet been read for that key` : "; every paper behind a record has now been read for every open key"}, and ${UD.summary.noPaperToRead} where the source is a data release without a paper`;
  {
    const dexOf = x => Math.log10(x), sgn = v => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(3), C = CA.compilation, off = CA.onScreenImfOffsetsDex;
    stats.cvRows = Object.values(CA.exactReexpressions).map(v => `<tr><td>${esc(v.label)}</td><td>${n(v.records)}</td><td>${esc(Object.keys(v.bySource).slice(0, 4).join(", "))}</td></tr>`).join("");
    stats.cvHRecords = n(CA.ownHConversion.records); stats.cvHSources = esc(CA.ownHConversion.sources.join(", ")); stats.cvH = esc(CA.ownHConversion.h.join(", "));
    stats.cvCompRepo = esc(C.repo); stats.cvCompN = n(C.records); stats.cvCompH = n(C.hCorrected); stats.cvCompImf = n(C.imfConverted); stats.cvCompNone = n(C.noConversion); stats.cvCompUntraced = n(C.notTraced); stats.cvCompCommit = esc((C.commit || "").slice(0, 7));
    stats.cvKro = C.factors.kroupa_to_chabrier_mass; stats.cvSal = C.factors.salpeter_to_chabrier_mass; stats.cvKroDex = sgn(dexOf(C.factors.kroupa_to_chabrier_mass)); stats.cvSalDex = sgn(dexOf(C.factors.salpeter_to_chabrier_mass));
    stats.cvImfList = Object.entries(C.imfConvertedDatasets).map(([k, v]) => `${esc(k)} (from ${esc(v.from)}, ${v.records} curve${v.records === 1 ? "" : "s"})`).join("; ");
    stats.cvOnKro = sgn(off.chabrier03 - off.kroupa01); stats.cvOnSal = sgn(off.chabrier03 - off.salpeter55);
    {
      const V = JSON.parse(await read("data/analysis/compilation-verification.json")), K = JSON.parse(await read("data/compilation-corrections.json")).corrections;
      const tally = {}; for (const row of V.curves) tally[row.result] = (tally[row.result] || 0) + row.records.length;
      const ids = kind => new Set(K.filter(c => c.kind === kind).flatMap(c => c.records));
      const numeric = ids("numeric"), label = ids("label"), flag = ids("flag");
      stats.cvChecked = n(Object.values(tally).reduce((a, b) => a + b, 0)); stats.cvAgree = n(tally.agrees || 0); stats.cvFit = n(tally["fit-only"] || 0); stats.cvDisagree = n(tally.disagrees || 0); stats.cvNoCheck = n(tally["not-verifiable"] || 0);
      stats.cvNumeric = n(numeric.size); stats.cvLabel = n([...label].filter(r => !numeric.has(r)).length); stats.cvFlag = n([...flag].filter(r => !numeric.has(r) && !label.has(r)).length);
    }
    stats.cvCorrN = n(CA.correctionsLogged); stats.cvFillRecords = n(CA.definitionFills.records); stats.cvFillRules = n(CA.definitionFills.rules);
  }
  stats.fNFills = FL.fills.length; stats.fSensN = A.sensitivity.pairs.length; stats.fSensG = A.sensitivity.summary.length;
  // definition changes inside single runs, one row per group (all from data/analysis/definition-budget.json)
  const f3 = (v, d = 3) => (v >= 0 ? "+" : "−") + Math.abs(v).toFixed(d), KEYN = { massDefinition: "stellar mass", haloMassDefinition: "halo mass", sfrTimescaleMyr: "SFR timescale (Myr)", dustCorrection: "dust treatment", sizeDefinition: "size", gasDefinition: "gas" };
  const short = (t, k = 42) => { const f = nice(t); return f.length > k ? `<span title="${esc(String(t))}">${esc(f.slice(0, k - 1))}…</span>` : esc(f); };
  const zr = g => g.zRange[0] === g.zRange[1] ? `${g.zRange[0]}` : `${g.zRange[0]}–${g.zRange[1]}`;
  stats.fSensRows = A.sensitivity.summary.map(g => `<tr><td>${esc(g.source)}</td><td class="id">${esc(g.relation)}</td><td class="nw">${esc(KEYN[g.key] || g.key)}</td><td>${short(g.from)} → ${short(g.to)}</td><td class="n">${zr(g)}</td><td class="n">${f3(g.median_dy)}</td><td class="n">${g.epochs > 1 ? `${f3(g.medianRange[0])} to ${f3(g.medianRange[1])}` : "–"}</td><td class="n">${g.max_abs_dy.toFixed(2)}</td></tr>`).join("");
  const byMed = [...A.sensitivity.summary].sort((a, b) => Math.abs(b.median_dy) - Math.abs(a.median_dy))[0], byMax = [...A.sensitivity.summary].sort((a, b) => b.max_abs_dy - a.max_abs_dy)[0];
  const lab = g => `${g.source}, ${RN[g.relation] || g.relation}, ${(KEYN[g.key] || g.key).replace(" (Myr)", "")}`;
  stats.fSensTop = `${f3(byMed.median_dy, 2)} dex (${lab(byMed)})`; stats.fSensTopLocal = `${byMax.max_abs_dy.toFixed(2)} dex (${lab(byMax)})`;
  stats.fSensMedAbs = n(A.sensitivity.summary.filter(g => Math.abs(g.median_dy) < 0.1).length);
  stats.fP6 = A.allRecords.find(r => r.relation === "gsmf" && r.z === 6).p_permutation.toFixed(2);
}
// ---- harmonization result on the findings page (numbers and the verdict come from data/analysis/harmonization.json; nothing here is written by hand)
{
  const Hm = JSON.parse(await read("data/analysis/harmonization.json")), e1 = Hm.E1, v = Hm.verdicts, W = 860, HT = 250, L = 56, R = 20, T = 14, B = 44;
  const lv = Hm.levels.filter(x => x.sd_raw_dex != null && x.sd_harmonized_dex != null), ymax = Math.ceil(Math.max(...lv.map(x => Math.max(x.sd_raw_dex, x.sd_harmonized_dex))) * 20) / 20;
  const px = x => L + (-2 - x) / 2.5 * (W - L - R), py = y => T + (1 - y / ymax) * (HT - T - B);
  let svg = `<svg viewBox="0 0 ${W} ${HT}" role="img" aria-labelledby="hzT hzD"><title id="hzT">Spread of the stellar mass at fixed abundance across simulations, before and after harmonizing definitions</title><desc id="hzD">Standard deviation across simulation suites of the stellar mass at which the mass function reaches a given abundance, raw and harmonized.</desc><g class="axis">`;
  for (let y = 0; y <= ymax + 1e-9; y += 0.1) svg += `<line x1="${L}" x2="${W - R}" y1="${py(y).toFixed(1)}" y2="${py(y).toFixed(1)}"/><text x="${L - 8}" y="${(py(y) + 4).toFixed(1)}" text-anchor="end">${y.toFixed(1)}</text>`;
  for (let x = -2; x >= -4.5; x -= 0.5) svg += `<text x="${px(x).toFixed(1)}" y="${HT - 22}" text-anchor="middle">${x.toFixed(1)}</text>`;
  svg += `<text x="${((L + W - R) / 2).toFixed(0)}" y="${HT - 4}" text-anchor="middle">log abundance, Φ (cMpc⁻³ dex⁻¹)</text><text x="14" y="${((T + HT - B) / 2).toFixed(0)}" transform="rotate(-90 14 ${((T + HT - B) / 2).toFixed(0)})" text-anchor="middle">SD across suites (dex)</text></g>`;
  for (const [key, col, dash] of [["sd_raw_dex", "var(--ink)", ""], ["sd_harmonized_dex", "var(--orange)", ""]]) {
    svg += `<polyline fill="none" stroke="${col}" stroke-width="2.4" ${dash} points="${lv.map(x => `${px(x.phi).toFixed(1)},${py(x[key]).toFixed(1)}`).join(" ")}"/>` + lv.map(x => `<circle cx="${px(x.phi).toFixed(1)}" cy="${py(x[key]).toFixed(1)}" r="3.4" fill="${col}"/>`).join("");
  }
  svg += `</svg>`;
  const pct = x => `${Math.round(100 * x)}%`, f2 = x => (x >= -0.005 ? "" : "−") + Math.abs(x).toFixed(2), ci = c => `${f2(c[0])} to ${f2(c[1])}`;
  stats.hSvg = svg;
  stats.hSuites = Hm.suites.length;
  stats.hVerdict = v.E1.supported ? "detected" : "not detected";
  stats.hR = f2(e1.R.all); stats.hCI = ci(e1.ci95.all); stats.hP = e1.permutation.p_value.toFixed(2);
  const on = Hm.operators, p80 = v.E4.smallest_lambda_detected_in_80_percent;
  stats.hOps = ["imf only", "scatter only", "aperture only"].map(k => `<tr><td>${esc(k.replace(" only", ""))}</td><td>${f2(on[k].R)}</td><td>${ci(on[k].ci95)}</td></tr>`).join("");
  stats.hPower = p80 === null ? `Injecting aperture effects of the measured size (and up to twice that) into the same suites is not detected in 80% of draws by the same rule (largest detection rate ${pct(Math.max(...Hm.E4.map(r => r.detection_rate)))}), so a non-detection of aperture effects here is uninformative about whether they exist.` : `An injected effect of ${p80} times the measured aperture maps is detected in at least 80% of draws.`;
}
// ---- model-form result on the findings page (everything, including the verdict words, comes from data/analysis/model-form.json)
if (await read("data/analysis/model-form.json").then(() => true, () => false)) {
  const M = JSON.parse(await read("data/analysis/model-form.json")), P = M.published, C = M.camels, E1 = P.E1, V = M.verdicts, W = 860, HT = 280, L = 58, R = 20, T = 16, B = 46;
  const f2 = (x, d = 2) => (x >= -0.5 * 10 ** -d ? "" : "−") + Math.abs(x).toFixed(d);
  const frame = (xr, yr, xt, yt, xl, yl) => {
    const px = x => L + (x - xr[0]) / (xr[1] - xr[0]) * (W - L - R), py = y => T + (1 - (y - yr[0]) / (yr[1] - yr[0])) * (HT - T - B);
    let g = `<g class="axis">`;
    for (const y of yt) g += `<line x1="${L}" x2="${W - R}" y1="${py(y).toFixed(1)}" y2="${py(y).toFixed(1)}"/><text x="${L - 8}" y="${(py(y) + 4).toFixed(1)}" text-anchor="end">${f2(y, y % 1 ? 1 : 0)}</text>`;
    for (const x of xt) g += `<text x="${px(x).toFixed(1)}" y="${HT - 24}" text-anchor="middle">${x}</text>`;
    g += `<text x="${((L + W - R) / 2).toFixed(0)}" y="${HT - 5}" text-anchor="middle">${xl}</text><text x="14" y="${((T + HT - B) / 2).toFixed(0)}" transform="rotate(-90 14 ${((T + HT - B) / 2).toFixed(0)})" text-anchor="middle">${yl}</text></g>`;
    return { px, py, g };
  };
  const path = (pts, px, py) => pts.map(([x, y], i) => `${i ? "L" : "M"}${px(x).toFixed(1)},${py(y).toFixed(1)}`).join("");
  const band = (lo, hi, px, py) => `M${lo.map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join("L")}L${hi.slice().reverse().map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join("L")}Z`;
  const svgOf = (id, title, desc, inner) => `<svg viewBox="0 0 ${W} ${HT}" role="img" aria-labelledby="${id}T ${id}D"><title id="${id}T">${esc(title)}</title><desc id="${id}D">${esc(desc)}</desc>${inner}</svg>`;
  // funnel
  {
    const sp = E1.spread, ok = sp.z.map((z, i) => [z, sp.sd[i], sp.sd_p16[i], sp.sd_p84[i], sp.n[i]]).filter(r => r[1] != null && r[2] != null);
    const ymax = Math.ceil(Math.max(...ok.map(r => r[3])) * 10) / 10, { px, py, g } = frame([0, 8], [0, ymax], [0, 1, 2, 3, 4, 5, 6, 7, 8], Array.from({ length: Math.floor(ymax / 0.2) + 1 }, (_, i) => +(i * 0.2).toFixed(1)), "redshift", "spread between simulations (dex)");
    const bd = M.parameters.bands_published;
    let s = g;
    for (const k of ["low", "high"]) s += `<rect x="${px(bd[k][0]).toFixed(1)}" y="${T}" width="${(px(bd[k][1]) - px(bd[k][0])).toFixed(1)}" height="${HT - T - B}" fill="var(--line2)" opacity=".3"/>`;
    s += `<path d="${band(ok.map(r => [r[0], r[2]]), ok.map(r => [r[0], r[3]]), px, py)}" fill="var(--orange)" opacity=".22"/><path d="${path(ok.map(r => [r[0], r[1]]), px, py)}" fill="none" stroke="var(--orange)" stroke-width="2.6"/>`;
    s += `<text class="al" x="${px(1.75).toFixed(1)}" y="${T + 14}" text-anchor="middle" style="font-size:12px">low band</text><text class="al" x="${px(6.25).toFixed(1)}" y="${T + 14}" text-anchor="middle" style="font-size:12px">high band</text>`;
    stats.mfFunnel = svgOf("mfF", "Spread of the cosmic star formation rate density between simulations against redshift", "Standard deviation across simulation families of log10 SFRD at each redshift, with its bootstrap band; the two shaded bands are the ones compared.", s);
  }
  // CAMELS
  {
    const z = C.meta.grid, cd = C.codes, sd = (a) => a.map((v, i) => [z[i], v]).filter(r => r[1] != null && r[0] <= 8.1);
    const T1 = sd(cd.IllustrisTNG.parametric.sd), S1 = sd(cd.SIMBA.parametric.sd), N1 = sd(cd.IllustrisTNG.seed_noise), N2 = sd(cd.SIMBA.seed_noise), D = C.structural_fiducial.delta.map((v, i) => [z[i], v == null ? null : Math.abs(v)]).filter(r => r[1] != null && r[0] <= 8.1);
    const ymax = Math.ceil(Math.max(...T1.map(r => r[1]), ...S1.map(r => r[1]), ...D.map(r => r[1])) * 5) / 5, { px, py, g } = frame([0, 8], [0, ymax], [0, 1, 2, 3, 4, 5, 6, 7, 8], Array.from({ length: Math.floor(ymax / 0.2) + 1 }, (_, i) => +(i * 0.2).toFixed(1)), "redshift", "dex");
    let s = g;
    for (const [pts, col, w, dash] of [[N1, "var(--orange)", 1.4, "4 3"], [N2, "var(--ink)", 1.4, "4 3"], [T1, "var(--orange)", 2.6, ""], [S1, "var(--ink)", 2.6, ""], [D, "var(--mustard)", 2.6, ""]]) s += `<path d="${path(pts, px, py)}" fill="none" stroke="${col}" stroke-width="${w}" ${dash ? `stroke-dasharray="${dash}"` : ""}/>`;
    stats.mfCamels = svgOf("mfC", "What feedback parameters and what model form do to the star formation history in CAMELS", "Parametric spread of IllustrisTNG (orange) and SIMBA (dark), their seed noise (dashed) and the absolute difference between the codes at the fiducial parameters (yellow), against redshift.", s);
  }
  // calibration
  {
    const k = C.calibration, zt = k.z_target, zo = k.z_obs, rows = [["IllustrisTNG", "var(--orange)"], ["SIMBA", "var(--ink)"]];
    const all = rows.flatMap(([c]) => [...k.codes[c].predictive.p5, ...k.codes[c].predictive.p95, ...k.codes[c].fit_to_observed.p5, ...k.codes[c].fit_to_observed.p95]), lo = Math.floor(Math.min(...all, ...k.target) * 2) / 2, hi = Math.ceil(Math.max(...all, ...k.target) * 2) / 2;
    const { px, py, g } = frame([0, 8], [lo, hi], [0, 1, 2, 3, 4, 5, 6, 7, 8], Array.from({ length: Math.round((hi - lo) / 0.5) + 1 }, (_, i) => +(lo + 0.5 * i).toFixed(1)), "redshift", "log10 SFR density (Msun/yr/cMpc³)");
    let s = g + `<path d="${path(zo.map((z, i) => [z, k.target[i]]), px, py)}" fill="none" stroke="var(--cream3)" stroke-width="2" stroke-dasharray="2 4"/>`;
    for (const [c, col] of rows) {
      const q = k.codes[c], a = q.fit_to_observed, b = q.predictive;
      s += `<path d="${band(zo.map((z, i) => [z, a.p5[i]]), zo.map((z, i) => [z, a.p95[i]]), px, py)}" fill="${col}" opacity=".18"/><path d="${band(zt.map((z, i) => [z, b.p5[i]]), zt.map((z, i) => [z, b.p95[i]]), px, py)}" fill="${col}" opacity=".3"/>`;
      s += `<path d="${path(zo.map((z, i) => [z, a.median[i]]), px, py)}" fill="none" stroke="${col}" stroke-width="2.2"/><path d="${path(zt.map((z, i) => [z, b.median[i]]), px, py)}" fill="none" stroke="${col}" stroke-width="2.2"/>`;
    }
    stats.mfCalib = svgOf("mfK", "Two simulation codes tuned to the same observed star formation history, and what each predicts beyond it", "Posterior predictive median and 90 percent interval of the cosmic star formation rate density for IllustrisTNG (orange) and SIMBA (dark) conditioned on the observed values at redshift 3 and below (dotted), at the redshifts used and beyond.", s);
  }
  const pct = x => `${Math.round(100 * x)}%`;
  stats.mfSuccess = V.E1.success ? "detected" : "not detected";
  stats.mfFactor = (10 ** E1.phi).toFixed(1); stats.mfSdLow = E1.sd_low.toFixed(2); stats.mfSdHigh = E1.sd_high.toFixed(2); stats.mfNFam = E1.n_balanced; stats.mfNFamAll = E1.n_families;
  stats.mfDfid = C.reachability.full.D_fiducial_dex.toFixed(2); stats.mfD = C.reachability.full.D_dex.toFixed(2); stats.mfMargin = C.reachability.margin_dex.toFixed(2);
  stats.mfReach = C.reachability.verdict; stats.mfCalVerdict = C.calibration.verdict;
  const flips = Object.entries(P.sensitivity.S6_leave_one_family_out).filter(([, x]) => x.phi != null && x.phi < 0);
  stats.mfE1 = `The spread across ${E1.n_balanced} families is ${E1.sd_low.toFixed(2)} dex at z = 0.5 to 3 and ${E1.sd_high.toFixed(2)} dex at z = 5 to 7.5 (a factor ${(10 ** E1.phi).toFixed(1)}; 90% interval of the log ratio ${f2(E1.phi_ci90[0])} to ${f2(E1.phi_ci90[1])}, Pitman–Morgan p = ${E1.pitman_morgan.p_one_sided.toFixed(3)}): funnel ${stats.mfSuccess} by the rule fixed in advance.` +
    (flips.length ? ` It does not survive leaving one family out: without ${flips.map(([f]) => esc(f)).join(" or ")} the sign reverses (log ratio ${f2(flips[0][1].phi)}).` + (flips.some(([f]) => f === "FLAMINGO") ? " FLAMINGO's flagship-resolution run is the lowest curve above z = 5, and the same code's run at eight times the mass resolution lies roughly a dex higher at z = 6 to 7, so resolution within one code moves the early star formation history as much as the choice of code (a reading added after the result, not part of the test)." : "") : "");
  const E2n = P.E2.pooled.numerical, E2p = P.E2.pooled.parametric;
  stats.mfE2 = E2n && E2n.low && E2n.high ? `Within one code, the authors' own resolution and box changes (${E2n.low.n_variants} variants of ${E2n.low.n_families} families) move the star formation history by ${E2n.low.rms_dex.toFixed(2)} dex rms at z = 0.5 to 3 and ${E2n.high.rms_dex.toFixed(2)} dex at z = 5 to 7.5, against ${E1.sd_low.toFixed(2)} and ${E1.sd_high.toFixed(2)} dex between the codes; their parameter variants (IllustrisTNG, ${E2p.low.n_variants} runs) move it by ${E2p.low.rms_dex.toFixed(2)} and ${E2p.high.rms_dex.toFixed(2)}. The sizes are the authors' choices, so only the order of magnitude carries information.` : "";
  const rr = C.reachability, kk = C.calibration, edge = [...rr.full.a_tng, ...rr.full.a_simba].filter(x => Math.abs(x) > 0.95).length;
  stats.mfE3 = `At their fiducial parameters IllustrisTNG and SIMBA differ by ${rr.full.D_fiducial_dex.toFixed(2)} dex rms. Retuning four feedback parameters per code over the same factors brings them to ${rr.full.D_dex.toFixed(2)} dex (emulators trained on half of the simulations: ${rr.between_full.p5.toFixed(2)} to ${rr.between_full.p95.toFixed(2)}; the same code against its other half leaves at most ${rr.controls_full.p95.toFixed(2)}, and two seeds of these codes differ by ${rr.margin_dex.toFixed(2)}): <b>${rr.verdict}</b> by the rule fixed in advance. The best-matching pair sits at the edge of the CAMELS range in ${edge} of its 8 coordinates, where the emulator is least constrained, and with the ranges cut to a quarter the codes stay ${rr.shrunk["0.25"].toFixed(2)} dex apart. Tuned to the same observed star formation history their predictions overlap at z = ${kk.z_target[0]} to ${kk.z_target[kk.z_target.length - 1]} (the 90% intervals are disjoint at ${pct(kk.disjoint_fraction)} of the redshifts; the medians drift apart by ${Math.max(...kk.median_difference.map(Math.abs)).toFixed(2)} dex by z = ${kk.z_target[kk.z_target.length - 1]}): <b>${kk.verdict}</b>.`;
  const val = V.validations, badV = [["V1", val.V1], ["V2", val.V2], ["V3", val.V3], ["V4 IllustrisTNG", val.V4.IllustrisTNG], ["V4 SIMBA", val.V4.SIMBA], ["V5", val.V5]].filter(([, ok]) => ok === false).map(([n]) => n);
  stats.mfVal = badV.length ? `Not every validation holds: ${badV.join(", ")}${badV.includes("V4 SIMBA") ? ` (the SIMBA emulator's cross-validation error is ${C.codes.SIMBA.v4.max_cv_over_seed.toFixed(2)} times the seed noise at its worst redshift, against a limit of 1.5)` : ""}; the analysis page says which conclusions to read with that qualification.` : "All five validations hold.";
}
// ---- derived values for the data page and the front page (all from the records, data/coverage-report.json and the export manifest)
const zfmt = v => String(+v.toFixed(2)), zr = (a, b) => a === b ? zfmt(a) : `${zfmt(a)} – ${zfmt(b)}`;
stats.repo = release.repo; stats.doi = release.doi; stats.points = n(manifest.nPoints); stats.relCodes = cov.totals.relations; stats.year = release.released.slice(0, 4);
stats.zMin = zfmt(Math.min(...sims.map(r => r.epoch.zRepresentative))); stats.zMaxAll = zfmt(Math.max(...Object.values(cov.byRelation).flatMap(v => v.epochs)));
stats.rankableAll = n(all.filter(r => r.rankable).length);
stats.thirdParty = n(all.filter(r => /^third-party/.test(r.provenance.terms || "")).length);
stats.bibtex = esc(`@dataset{bhatia${release.released.slice(0, 4)}simhighline,
  author    = {${release.author.split(" ").slice(1).join(" ")}, ${release.author.split(" ")[0]}},
  title     = {${release.title}},
  year      = {${release.released.slice(0, 4)}},
  version   = {${release.version}},
  publisher = {Zenodo},
  doi       = {${release.doi}},
  url       = {https://doi.org/${release.doi}}
}`);
const camelsSims = Object.values(camels.suites).reduce((t, c) => t + Object.keys(c.LH).length + Object.keys(c.CV).length, 0);
stats.camelsN = n(camelsSims); stats.camelsPerCode = n(camelsSims / Object.keys(camels.suites).length); stats.camelsLH = n(Object.keys(Object.values(camels.suites)[0].LH).length); stats.camelsCV = n(Object.keys(Object.values(camels.suites)[0].CV).length);
stats.camelsBox = camels.boxMpcPerH; stats.camelsBins = camels.zCentres.length;
{
  const relRows = Object.entries(cov.byRelation).map(([k, v]) => {
    const rs = all.filter(r => r.relation === k);
    return { k, records: v.records, rankable: v.rankable, sims: uniq(rs.filter(r => r.kind === "simulation").map(r => r.source)), obs: uniq(rs.filter(r => r.kind !== "simulation").map(r => r.source)), z0: Math.min(...v.epochs), z1: Math.max(...v.epochs) };
  }).sort((a, b) => b.records - a.records || a.k.localeCompare(b.k));
  const nameCell = r => { const t = notes[r.k]?.title; return `${t ? `<a href="../highline.html#r=${esc(r.k)}">${esc(t)}</a> ` : ""}<span class="dim mono">${esc(r.k)}</span>`; };
  const tr = r => `<tr><td>${nameCell(r)}</td><td class="n">${n(r.records)}</td><td class="n">${r.sims.length}</td><td class="n">${r.obs.length}</td><td class="n">${n(r.rankable)}</td><td class="n">${zr(r.z0, r.z1)}</td></tr>`;
  const head = `<thead><tr><th>Relation</th><th class="n">Records</th><th class="n" title="distinct simulations with a curve of this relation">Simulations</th><th class="n" title="distinct observational and empirical sources">Observations</th><th class="n">Rankable</th><th class="n">z-range</th></tr></thead>`;
  const totalRow = `<tfoot><tr><td>All ${cov.totals.relations} relation codes <span class="dim">(the Explorer groups them into ${stats.relations} relations)</span></td><td class="n">${stats.records}</td><td class="n">${stats.suites}</td><td class="n">${stats.obsSources}</td><td class="n">${stats.rankableAll}</td><td class="n">${stats.zMin} – ${stats.zMaxAll}</td></tr></tfoot>`;
  const TOP = 10, top = relRows.slice(0, TOP), rest = relRows.slice(TOP);
  const restRow = rest.length ? `<tr><td>${rest.length} further relations <span class="dim">(<a href="data.html#relations">all</a>)</span></td><td class="n">${n(rest.reduce((t, r) => t + r.records, 0))}</td><td class="n">${uniq(rest.flatMap(r => r.sims)).length}</td><td class="n">${uniq(rest.flatMap(r => r.obs)).length}</td><td class="n">${n(rest.reduce((t, r) => t + r.rankable, 0))}</td><td class="n">${zr(Math.min(...rest.map(r => r.z0)), Math.max(...rest.map(r => r.z1)))}</td></tr>` : "";
  stats.dataTableCompact = `<table>${head}<tbody>${top.map(tr).join("")}${restRow}</tbody>${totalRow}</table>`;
  stats.dataTableFull = `<table class="long dense">${head}<tbody>${relRows.map(tr).join("")}</tbody>${totalRow}</table>`;
  stats.relOutside = n(relRows.filter(r => !notes[r.k]).length);
  const thin = relRows.filter(r => notes[r.k] && !["mzrz", "mzrraw"].includes(r.k) && r.sims.length <= 3 && r.sims.length > 0).sort((a, b) => a.sims.length - b.sims.length || a.k.localeCompare(b.k));
  stats.thinList = thin.map(r => `${esc(notes[r.k].title)} (${r.sims.length})`).join("; ");
  stats.thinN = thin.length;
}
{
  const TIER_INFO = [
    ["official-table", "Table released by the collaboration; the SHA-256 of the file is stored."],
    ["catalog-derived", "Computed by a sim-highline script from a public catalogue with fixed cuts and a fixed seed."],
    ["published-table", "Values transcribed from a table in the paper, spot-checked against numbers the paper quotes."],
    ["published-fit", "A published fitting function, fit line or parametric relation, evaluated and not refitted."],
    ["digitized-figure", "Read from the vector paths of a published figure. Never rankable."]
  ];
  const cnt = t => ({ all: all.filter(r => r.provenance.tier === t).length, sim: sims.filter(r => r.provenance.tier === t).length, obs: obs.filter(r => r.provenance.tier === t).length, rk: all.filter(r => r.provenance.tier === t && r.rankable).length });
  const rows = TIER_INFO.map(([t, m]) => { const c = cnt(t); return `<tr><td class="mono">${t}</td><td>${esc(m)}</td><td class="n">${n(c.all)}</td><td class="n">${n(c.sim)}</td><td class="n">${n(c.obs)}</td><td class="n">${n(c.rk)}</td></tr>`; }).join("");
  const unknown = uniq(all.map(r => r.provenance.tier)).filter(t => !TIER_INFO.some(([k]) => k === t));
  if (unknown.length) throw new Error(`tiers without a description: ${unknown.join(", ")}`);
  stats.tierRows = rows;
  stats.tierTotal = `<tr><td colspan="2">All records</td><td class="n">${stats.records}</td><td class="n">${stats.simRecords}</td><td class="n">${stats.obsRecords}</td><td class="n">${stats.rankableAll}</td></tr>`;
  const FILEINFO = {
    "sim-highline-records.csv": "One row per curve: source, run, relation, epoch, evidence tier, rankable flag, structured definitions, citation, DOI, checksum.",
    "sim-highline-points.csv": "One row per plotted point: x, y, band, counts; keyed by record_id.",
    "sim-highline-records.json": "Everything above as nested JSON, with the full provenance block.",
    "sim-highline-citations.bib": "BibTeX for every paper and data release behind a record.",
    "sim-highline-rules.json": "The comparison rules: hard and soft definition keys per relation."
  };
  const size = b => b > 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.round(b / 1e3)} kB`;
  stats.fileRows = Object.entries(manifest.files).map(([f, m]) => `<tr><td class="mono"><a href="../data/export/${esc(f)}">${esc(f)}</a></td><td>${esc(FILEINFO[f] || "")}</td><td class="n">${size(m.bytes)}</td><td class="mono"><span title="${m.sha256}">${m.sha256.slice(0, 10)}…</span></td></tr>`).join("");
  stats.columnList = (manifest.columns.records || []).map(c => `<code>${esc(c)}</code>`).join(", ");
}

// ---- joint reachability (S4): generated from data/analysis/joint-reachability.json when it exists
const JR = await read("data/analysis/joint-reachability.json").then(t => JSON.parse(t), () => null);
const RT = await read("data/retune/retune.json").then(t => JSON.parse(t), () => null);
Object.assign(stats, Object.fromEntries(Object.entries(jointStats(JR, undefined, RT && !RT.pending ? RT.native : null)).map(([k, v]) => [k, typeof v === "string" ? v.replace(/(\d) %/g, "$1%") : v]))); // the saved analysis text writes '28 %'; the pages write '28%'
{
  const V = RT && !RT.pending ? RT.validation : null, FN = RT && RT.family_names ? RT.family_names : {};
  stats.rtValRows = V ? Object.entries(V).filter(([k]) => k !== "n_test").map(([f, r]) => `<tr><td>${esc(FN[f] || f)}</td><td>${r.unit === "dex" ? "dex" : "fraction"}</td>${["IllustrisTNG", "SIMBA"].map(c => `<td class="n">${r[c].cv_rmse_median.toFixed(3)}</td><td class="n">${r[c].ratio_median.toFixed(2)}</td>`).join("")}</tr>`).join("") : "";
  stats.rtValN = V ? `${V.n_test.IllustrisTNG} (IllustrisTNG) and ${V.n_test.SIMBA} (SIMBA)` : "";
}
// ---- checks made after the registered run: generated from the exploratory outputs when they exist
{
  const j = async f => read(f).then(t => JSON.parse(t), () => null);
  const RB = await j("data/analysis/joint-robustness.json"), T3 = await j("data/analysis/third-code.json"), TO = await j("data/analysis/tune-to-observations.json"), MC = await j("data/analysis/minimiser-check.json");
  const f1 = v => v.toFixed(1), f2 = v => v.toFixed(2), repo = "https://github.com/ShubhanBhatia42/sim-highline/blob/main/docs/";
  const rows = [];
  if (RB) {
    rows.push(["A second, independently written search for the same distance", `${f2(RB.reimplementation.all)} against the registered ${f2(RB.registered.all)}`, "ROBUSTNESS-joint-reachability.md"]);
    rows.push(["A different kind of emulator (kernel ridge instead of polynomials)", `${f2(RB.emulator.all)}`, "ROBUSTNESS-joint-reachability.md"]);
    const W = Object.entries(RB.weightings).filter(([k]) => k !== "block").map(([, v]) => v);
    rows.push(["Other weightings and subsets of the outputs", `${f1(Math.min(...W))} to ${f1(Math.max(...W))}`, "CHOICES-joint-reachability.md"]);
  }
  if (T3) {
    const p = T3.pairs, short = k => k.replace("IllustrisTNG", "TNG").replace("|", " – ");
    rows.push([`A third code, Astrid, on the ${T3.n_outputs} outputs all three codes have`, Object.keys(p).map(k => `${short(k)} ${f1(p[k].all.D)}`).join(", ") + `; black hole occupation separates SIMBA from both others (TNG – SIMBA ${f1(p["IllustrisTNG|SIMBA"].bhocc.D)}, SIMBA – Astrid ${f1(p["SIMBA|Astrid"].bhocc.D)}, TNG – Astrid ${f2(p["IllustrisTNG|Astrid"].bhocc.D)})`, "ANALYSIS-third-code.md"]);
  }
  if (TO) {
    const better = r => Math.min(r.IllustrisTNG.gap, r.SIMBA.gap), TITLE = { gsmf: "stellar mass function", qf: "quenched fraction", sfms: "specific star formation rate", bhms: "black hole mass", zstar: "stellar metallicity", mzr: "gas metallicity", size: "size", fgas: "gas fraction", shmr: "stellar-to-halo mass ratio" };
    const fams = [...new Set(TO.rows.map(r => r.family))], far = fams.map(f => { const rs = TO.rows.filter(r => r.family === f), out = rs.filter(r => better(r) > 1); return out.length ? `${TITLE[f] || f} (${out.length} of ${rs.length} curve${rs.length > 1 ? "s" : ""}, the better code ${f1(Math.min(...out.map(better))) === f1(Math.max(...out.map(better))) ? f1(Math.min(...out.map(better))) : `${f1(Math.min(...out.map(better)))} to ${f1(Math.max(...out.map(better)))}`} noise units away)` : null; }).filter(Boolean);
    const near = TO.rows.filter(r => better(r) <= 1).length;
    rows.push([`Each code tuned to ${TO.n} observed curves`, `at least one code gets within one noise unit of ${near} of them (mostly mass functions and quenched fractions, about 0.2 dex or less, which four dials can fit easily); neither does for ${far.join("; ")}. Few bins per curve, and observed and simulated curves are defined differently, so this is not a test of either code`, "ANALYSIS-tune-to-observations.md"]);
  }
  if (MC) {
    const c = MC.codes, g = (code, k) => c[code].sets[k].rms_noise_units.toFixed(2), near = "nearest the minimising setting", far = "random simulations";
    rows.push([`Emulators at the minimum: the ${MC.k} simulations nearest each code's minimising setting, held out and predicted`, `held-out error ${g("IllustrisTNG", near)} (TNG) and ${g("SIMBA", near)} (SIMBA) noise units, against ${g("IllustrisTNG", far)} and ${g("SIMBA", far)} for random simulations: no worse in that corner. The nearest simulations are not at the minimum (${c.IllustrisTNG.sets[near].mean_distance_in_dial_coordinates.toFixed(2)} and ${c.SIMBA.sets[near].mean_distance_in_dial_coordinates.toFixed(2)} away in dial coordinates), and no simulation has been run there`, "ANALYSIS-minimiser-check.md"]);
  }
  stats.jrAfterRows = rows.map(([a, b, d]) => `<tr><td>${esc(a)}</td><td>${esc(b)}</td><td><a href="${repo}${d}">${d.replace(/\.md$/, "")}</a></td></tr>`).join("");
}
// ---- quenching shape (the fifth study): generated from data/analysis/quenching-shape.json (and the checks made after the run)
{
  const QSR = await read("data/analysis/quenching-shape.json").then(t => JSON.parse(t), () => null), QSC = await read("data/analysis/quenching-shape-checks.json").then(t => JSON.parse(t), () => null);
  Object.assign(stats, shapeStats(QSR, QSC));
}
stats.repo = stats.repo || "https://github.com/ShubhanBhatia42/sim-highline";
stats.siteUrl = "shubhanbhatia42.github.io/sim-highline";

// ---- which definitions must agree for each relation (compare.js RULES, with the plain names of the keys); only relations that have records
{
  const T = Object.fromEntries([...(await read("highline/index.html")).matchAll(/\n  "?([A-Za-z0-9-]+)"?:\{t:"([^"]+)"/g)].map(m => [m[1], m[2]]));
  const have = new Set(all.map(r => r.relation)), name = k => esc(KEY_LABEL[k] || k);
  stats.ruleRows = Object.entries(RULES).filter(([k]) => have.has(k)).map(([k, r]) => `<tr><td>${esc(T[k] || k)}</td><td>${r.hard.map(name).join("; ") || "–"}</td><td>${r.soft.map(name).join("; ") || "–"}</td></tr>`).join("");
  stats.ruleCount = String(Object.keys(RULES).filter(k => have.has(k)).length);
}

// ---- data quality: generated from data/analysis/data-quality.json (scripts/analyze_data_quality.py)
{
  const Q = JSON.parse(await read("data/analysis/data-quality.json")), f3 = v => (v == null ? "–" : v.toFixed(3));
  const TIERNAME = { "official-table": "the authors' table", "published-table": "a table in the paper", "published-fit": "a published fit", "catalog-derived": "computed by this project from a catalogue", "digitized-figure": "read from a figure" };
  stats.qTierRows = Q.tiers.map(t => `<tr><td>${esc(t.kind)}</td><td>${esc(TIERNAME[t.tier] || t.tier)}</td><td class="n">${t.records}</td><td class="n">${t.rankable}</td></tr>`).join("");
  const d = Q.digitized, u = d.declared_uncertainty_dex;
  stats.qDigitized = `${d.n} of the ${d.n_simulation_curves} simulation curves (${(100 * d.share_of_simulation_curves).toFixed(0)}%) were read from published figures, and ${d.rankable} of them are used for ranking. They are read from the vector paths in the figure files with the axes calibrated on the printed tick marks, not by eye from an image; the reading error the scripts declare is a median ${u.median} dex and at most ${u.max} dex. That is the error of reading the figure. Whether the figure itself is right only its authors can say.`;
  const e = Q.extraction_checks;
  stats.qExtractN = String(e.n); stats.qExtractShare = (100 * e.n / Math.max(1, d.n)).toFixed(1);
  stats.qExtractRows = e.pairs.map(p => `<tr><td>${esc(p.label)}</td><td class="n">${p.n}</td><td class="n">${f3(p.median_abs)}</td><td class="n">${f3(p.max_abs)}</td></tr>`).join("") || `<tr><td colspan="4">none</td></tr>`;
  stats.qExtractSummary = e.n ? `The ${e.n === 1 ? "pair that exists differs" : "pairs differ"} by a median of ${Math.min(...e.pairs.map(p => p.median_abs)).toFixed(3)}${e.n > 1 ? " to " + Math.max(...e.pairs.map(p => p.median_abs)).toFixed(3) : ""} in the curve's units.` : "No such pair exists.";
  { const rd = Q.redigitization, rt = Q.released_tables;
    stats.qRedigText = rd ? `A second reader re-digitized a random sample by a different method (a 400 dpi raster of each figure, axes recalibrated from the tick marks, the curve traced by colour; the original extraction's vector paths were not read). ${rd.checked} curves from ${rd.papers} papers could be checked, out of ${rd.attempted} tried; ${rd.pass} are within tolerance and ${rd.fail} are not. On logarithmic axes the median difference is ${rd.logYMedianDex.toFixed(4)} dex. Each failure was inspected and none could be attributed to a stored curve, but the check could not see a wrong panel or run, and ${rd.notCheckable} curves could not be checked at all. One reader made it.` : "";
    stats.qReleasedText = rt ? `For the ${rt.papers} papers behind the figure-read simulation curves we looked for released numbers. Fully available as a table: ${(rt.categories["table-in-eprint"] || 0) + (rt.categories["table-in-paper"] || 0) + (rt.categories["table-released-full"] || 0)} paper(s); partly: ${(rt.categories["table-released-partial"] || 0) + (rt.categories["table-partial"] || 0) + (rt.categories["table-released-unverified"] || 0)}; only the simulation's catalogues are public (the plotted numbers would be recomputed): ${rt.categories["catalog-public-recompute"] || 0}; available on request or announced: ${(rt.categories["on-request"] || 0) + (rt.categories["announced-not-released"] || 0)} (${(rt.recordsByCategory["on-request"] || 0) + (rt.recordsByCategory["announced-not-released"] || 0)} curves); nothing found: ${rt.categories["none-found"] || 0}.${rt.exactMatch != null ? ` Of the ${rt.exactMatch} curves for which a table matching the plotted numbers exactly was found, ${rt.replaced.length} have been replaced by the table's numbers and ${rt.stillFigureRead.length} ${rt.stillFigureRead.length === 1 ? "is" : "are"} still the figure read${rt.duplicates && rt.duplicates.length ? `; ${rt.duplicates.length} more figure-read curve${rt.duplicates.length === 1 ? " duplicates" : "s duplicate"} numbers already in the dataset as an official table` : ""}.` : ""}` : ""; }
  stats.qPaperN = String(Q.paper_disagreements.n);
  const th = Q.thin;
  stats.qThinHead = th.epochs.map(z => `<th class="n">z = ${z}</th>`).join("");
  stats.qThinRows = Object.entries(th.cells).map(([rel, row]) => `<tr><td>${esc(rel)}</td>${th.epochs.map(z => { const n = row[String(z)]; return `<td class="n${n === 0 ? " none" : n < 3 ? " thin" : ""}">${n}</td>`; }).join("")}</tr>`).join("");
  stats.qThinCells = String(Object.values(th.cells).reduce((s, r) => s + Object.values(r).filter(n => n > 0 && n < 3).length, 0));
  stats.qTerms = `${Q.terms.records_with_terms} records carry explicit third-party terms. ${Q.terms.permission_not_requested} of them are values this project binned from a repository with no licence file; permission has not yet been requested, and they should be treated as not cleared for reuse until it is.`;
}

// ---- where the dataset has been used (data/used-in.json, filled from the "used in" issue form); honest when empty
{
  const U = JSON.parse(await read("data/used-in.json")), form = `${release.repo}/issues/new?template=used-in.yml`;
  stats.usedIn = U.length
    ? `<p>${U.length} use${U.length > 1 ? "s" : ""} reported to us:</p><ul class="flat">${U.map(u => `<li>${u.url ? `<a href="${esc(u.url)}">${esc(u.what)}</a>` : esc(u.what)}${u.who ? ` (${esc(u.who)})` : ""}: ${esc(u.how)}</li>`).join("")}</ul><p>Used it? <a href="${form}">Tell us</a> and it will be listed here.</p>`
    : `<p>Nobody has told us yet. If you used the data or a page in a paper, a talk, a course or code, <a href="${form}">tell us in two lines</a> and, with your agreement, it is listed here. Until then this list is empty, and the project's usefulness is unproven.</p>`;
}
// ---- the dated registration trail (data/registration-trail.json, from scripts/make_registration_trail.py)
{
  const TR = JSON.parse(await read("data/registration-trail.json")), NAMES = { harmonization: "Can matching definitions close the gap?", "model-form": "What can retuning change in cosmic star formation?", "joint-reachability": "Can two universes agree on everything at once?", "quenching-shape": "Does the shape of star formation tell the codes apart?" };
  const d = x => x.slice(0, 10), link = c => `<a href="${release.repo}/commit/${c.hash}"><code>${c.short}</code></a>`;
  stats.trailRows = Object.entries(TR).map(([k, t]) => { const p = t.protocol_commits, r = t.result_first_commit; return `<tr><td>${esc(NAMES[k] || k)}</td><td>${d(p[0].date)} ${link(p[0])}</td><td>${p.length > 1 ? p.slice(1).map(c => `${d(c.date)} ${link(c)}`).join(", ") : "none"}</td><td>${r ? `${d(r.date)} ${link(r)}` : "–"}</td></tr>`; }).join("");
}

// ---- studies (one list feeds the front page and the studies page)
const STUDIES = [
  { id: "S1", href: "study-definitions.html", title: "How much is just definitions?", q: "How much of the disagreement between simulations is just definitions?", status: "Result", head: `${stats.fMatchedPct} of ${stats.fPairs} cross-simulation pairs fully matched`,
    abs: `${stats.fPairs} cross-simulation curve pairs are classified from their documented definitions alone: ${stats.fMatchedPct} are fully matched and ${stats.fUnknownPct} cannot be classified because a source does not state what it measured. ${stats.fBonf} of ${stats.fTests} epoch tests survive correction. Descriptive; no protocol.` },
  { id: "S2", href: "study-harmonization.html", title: "Can matching definitions close the gap?", q: "Can documented definitions close the gap between simulated z ≈ 0 mass functions?", status: "Pre-registered · result", head: `R = ${stats.hR} (95% CI ${stats.hCI}), p = ${stats.hP}: ${stats.hVerdict}`,
    abs: `Express ${stats.hSuites} suites' z ≈ 0 stellar mass functions in one IMF, without added scatter and in a 30 pkpc aperture, and ask what fraction R of the spread across suites disappears. R = ${stats.hR} (95% interval ${stats.hCI}; permutation p = ${stats.hP}): ${stats.hVerdict} by the rule fixed in advance.` },
  { id: "S3", href: "study-sfh.html", title: "What can retuning change in cosmic star formation?", q: "Do simulations disagree more in the early Universe, and can retuning remove the difference between two codes?", status: "Pre-registered · result", head: `Funnel ${stats.mfSuccess}, factor ${stats.mfFactor}; retuning: ${stats.mfDfid} to ${stats.mfD} dex (${stats.mfReach})`,
    abs: `Published curves of ${stats.mfNFamAll} model families, the authors' own variants and ${stats.camelsN} CAMELS simulations of IllustrisTNG and SIMBA. Across the ${stats.mfNFam} families defined in both redshift bands the spread is ${stats.mfSdLow} dex at z = 0.5 to 3 and ${stats.mfSdHigh} dex at z = 5 to 7.5 (funnel ${stats.mfSuccess}). Retuning four feedback parameters per code brings the two codes from ${stats.mfDfid} to ${stats.mfD} dex rms (${stats.mfReach}).` },
  { id: "S4", href: "study-joint.html", title: "Can two universes agree on everything at once?", q: "Can retuning make two feedback models agree on every galaxy observable at once?", status: stats.jrStatus, head: JR ? stats.jrHead : "—", todo: !JR, abs: stats.jrAbsShort },
  { id: "S5", href: "study-shape.html", title: "Does the shape of star formation tell the codes apart?", q: "Does the share of galaxies in the green valley, and the width of the star-forming sequence, separate the two codes beyond the quenched fraction and the main sequence?", status: stats.qsTodo ? "Pre-registered · pending" : stats.qsStatus, head: stats.qsTodo ? "—" : stats.qsHead, todo: !!stats.qsTodo, abs: stats.qsTodo ? "" : stats.qsAbs }
];
// plain-language result of each study, in one sentence and a short paragraph; numbers come from the same stats as the abstracts
stats.plainDefsOne = `Only ${stats.fMatchedPct} of ${stats.fPairs} pairs of curves from different simulations measure the same thing in the same way.`;
stats.plainDefs = `Many differences between simulated curves are not physics. The papers measured slightly different things: another mass aperture, another way of counting stars, another galaxy selection. Going only by what each source documents, ${stats.fMatchedPct} of the ${stats.fPairs} pairs of curves are measured alike. ${stats.fUnknownPct} cannot be judged, because a source does not say what it measured. So a gap you see between two curves may not be physics.`;
stats.plainHarmOne = `Putting ${stats.hSuites} simulations' stellar mass functions on the same footing did not measurably shrink the disagreement between them.`;
stats.plainHarm = `We put every simulation's stellar mass function on the same footing: the same way of counting stars and the same aperture. Then we asked how much of the disagreement between them goes away. The best guess is ${stats.hR} of it (1 would be all of it). But the 95% range, ${stats.hCI}, includes zero. By the rule we wrote down before looking, the answer is "${stats.hVerdict}". The data cannot say whether matching definitions explains part of the gap.`;
stats.plainSfhOne = `We could not show that simulations disagree more about the early Universe than the later one (the spread is ${stats.mfFactor} times larger, but our test did not pass); retuning four dials per code brings two codes from ${stats.mfDfid} to ${stats.mfD} dex apart.`;
stats.plainSfh = `Models of the cosmic star formation rate differ by ${stats.mfSdLow} dex at redshift 0.5 to 3, and by ${stats.mfSdHigh} dex at redshift 5 to 7.5. Our rule, fixed in advance, did not count this as a real widening: the result was "${stats.mfSuccess}". For two codes, IllustrisTNG and SIMBA, turning their four feedback dials shrinks the difference from ${stats.mfDfid} to ${stats.mfD} dex, so by our rule it is ${stats.mfReach} by retuning. Two cautions: the best match sits at the edge of the dials' range, and one of the checks on the emulators fails narrowly.`;
stats.plainJointOne = JR ? `After the best possible retuning of each code's four dials, IllustrisTNG and SIMBA are still ${Number(stats.jrD).toFixed(1)} noise units apart over all properties at once.` : "Pending.";
stats.plainJoint = JR ? (() => { const N = RT && !RT.pending && RT.native ? RT.native : null, bh = N && N.bhocc ? N.bhocc.alone.toFixed(2) : null, mz = N && N.mzr ? N.mzr.alone.toFixed(2) : null; return `One noise unit is how much two runs of the same code differ by chance. TNG and SIMBA stay ${Number(stats.jrD).toFixed(1)} units apart after retuning, which is far more than chance. Two properties stay apart at every dial setting we tried: the share of galaxies with a black hole${bh ? ` (about ${bh} apart even at the best settings)` : ""}, and the gas metallicity${mz ? ` (${mz} dex apart at best: beyond run-to-run scatter, but small in absolute terms)` : ""}. Six properties can be matched: the stellar mass function, the quenched fraction, black hole mass, galaxy size, gas fraction, and the total stars and star formation. Three are borderline. The best settings sit at the edge of the dials' range, where the emulators are least tested. This is about these two codes at CAMELS resolution, not simulations in general.`; })() : "";
const studyRows = (withAbs) => STUDIES.map(s => `<tr${s.todo ? ' class="todo"' : ""}><td class="ttl" data-l="Study"><a href="${s.href}">${esc(s.title)}</a></td><td data-l="${withAbs ? "Abstract" : "Question"}">${esc(withAbs ? s.abs : s.q)}</td><td class="st" data-l="Status">${esc(s.status)}</td><td class="hd" data-l="Headline">${esc(s.head)}</td></tr>`).join("");
stats.studiesCompact = `<table class="studies stack"><thead><tr><th>Study</th><th>Question</th><th>Status</th><th>Headline</th></tr></thead><tbody>${studyRows(false)}</tbody></table>`;
stats.studiesFull = `<table class="studies stack"><thead><tr><th>Study</th><th>Abstract</th><th>Status</th><th>Headline</th></tr></thead><tbody>${studyRows(true)}</tbody></table>`;

// ---- shared page parts: head, header (wordmark, section nav, version chip, status bar), footer
const SUN = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="10" cy="10" r="3.4"/><path d="M10 2.5v1.8M10 15.7v1.8M2.5 10h1.8M15.7 10h1.8M4.7 4.7l1.3 1.3M14 14l1.3 1.3M4.7 15.3 6 14M14 6l1.3-1.3"/></svg>', MOON = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><path d="M16.5 11.8A6.8 6.8 0 0 1 8.2 3.5a6.8 6.8 0 1 0 8.3 8.3z"/></svg>';
const THEME_JS = `<script>(function(){["reportlink","feedbacklink","tellus"].forEach(function(id){var a=document.getElementById(id);if(!a)return;a.addEventListener("click",function(){var u=a.href.split("&page=")[0];a.href=u+"&title="+encodeURIComponent("["+(id==="reportlink"?"site":"feedback")+"] "+document.title.slice(0,60))+"&page="+encodeURIComponent(document.title)+"&link="+encodeURIComponent(location.href)})});var L=document.querySelectorAll(".idx a[href^='#']");if(L.length&&window.IntersectionObserver){var m={};L.forEach(function(a){m[a.getAttribute("href").slice(1)]=a});var o=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){L.forEach(function(a){a.removeAttribute("aria-current")});m[e.target.id].setAttribute("aria-current","location")}})},{rootMargin:"0px 0px -70% 0px"});Object.keys(m).forEach(function(i){var s=document.getElementById(i);if(s)o.observe(s)})}document.querySelectorAll(".chart").forEach(function(c){if(c.scrollWidth>c.clientWidth+1){c.tabIndex=0;c.setAttribute("role","group");c.setAttribute("aria-label","Chart, scrolls sideways")}});var b=document.getElementById("theme"),r=document.documentElement,S='${SUN}',M='${MOON}';function now(){return r.dataset.theme||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")}function paint(){var d=now()==="dark";b.innerHTML=d?S:M;b.setAttribute("aria-label",d?"Switch to the light theme":"Switch to the dark theme")}b.onclick=function(){var n=now()==="dark"?"light":"dark";r.dataset.theme=n;try{localStorage.setItem("sh-theme",n)}catch(e){}paint()};paint()})()</script>`;
const FONTS = "https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap";
const FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%230c1016'/%3E%3Cpath d='M5 24H13V17H19V9H27' fill='none' stroke='%23ffffff' stroke-width='2.4' stroke-linejoin='miter'/%3E%3C/svg%3E";
const SITE_URL = "https://shubhanbhatia42.github.io/sim-highline";
const OG = { "study-joint.html": "og-study-joint.png", "retune.html": "og-retune.png" };
const HEAD = (title, desc, img = "og-default.png") => `<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="${FONTS}" rel="stylesheet">
<link rel="icon" href="${FAVICON}">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0b0e12" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website"><meta property="og:site_name" content="sim-highline"><meta property="og:title" content="${title}"><meta property="og:description" content="${desc}"><meta property="og:image" content="${SITE_URL}/site/${img}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="${esc(title)}: a chart from the page beside its title"><meta name="twitter:card" content="summary_large_image">
<script>try{var t=localStorage.getItem("sh-theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}</script>
<style>${stats.css}</style>`;
const MENU = [["../highline.html", "Explorer", null], ["retune.html", "Dials", "retune"], ["studies.html", "Studies", "studies"], ["data.html", "Data", "data"], ["methods.html", "Methods", "methods"]];
const SECTION = page => /^study-/.test(page) || page === "studies.html" ? "studies" : page === "retune.html" ? "retune" : ["data.html", "sources.html"].includes(page) ? "data" : page === "methods.html" ? "methods" : null;
const HEADER = page => `<a class="skip" href="#main">Skip to the content</a>
<header class="top"><div class="wrap bar"><a class="mark" href="index.html" aria-label="sim-highline home">sim-highline</a><nav class="menu" aria-label="Main">${MENU.map(([h, t, k]) => `<a href="${h}"${k && k === SECTION(page) ? ' aria-current="page"' : ""}>${t}</a>`).join("")}</nav><span class="sp"></span><a class="chip" href="https://doi.org/${release.doi}" title="dataset v${release.version}, doi:${release.doi}">v${release.version} · doi</a><button class="ico" id="theme" type="button" aria-label="Switch theme"></button></div>
<div class="status"><div class="wrap"><span><b>${stats.records}</b> records</span><span><b>${stats.suites}</b> simulations</span><span><b>${stats.obsSources}</b> observational and empirical sources</span><span><b>${stats.relations}</b> relations</span><span>z <b>${stats.zMin}–${stats.zMax}</b></span><span class="opt">released <b>${release.released}</b></span></div></div></header>`;
const [first, ...lastParts] = release.author.split(" ");
stats.citeText = `${esc(lastParts.join(" "))}, ${esc(first[0])}. (${stats.year}). ${esc(release.title)} (v${release.version}). Zenodo. https://doi.org/${release.doi}`;
const FOOTER = () => `<footer class="foot"><div class="wrap">
<p>Cite as: ${esc(lastParts.join(" "))}, ${esc(first[0])}. (${stats.year}). <em>${esc(release.title)}</em> (v${release.version}). Zenodo. <a href="https://doi.org/${release.doi}">doi:${release.doi}</a>. Cite the original papers as well: every record carries its citation and DOI.</p>
<p>Code ${esc(release.license.code)}; data ${esc(release.license.data.replace("CC-BY-4.0", "CC BY 4.0"))}, third-party inputs keep their own terms (<a href="${release.repo}/blob/main/docs/SOURCE-TERMS.md">SOURCE-TERMS.md</a>). Maintained by ${esc(release.author)}.</p>
<p class="tell"><b>Was something confusing, wrong or missing?</b> <a id="tellus" href="${release.repo}/issues/new?template=feedback.yml">Tell us in two sentences</a>. This needs a GitHub account; without one, write to the maintainer at the address in <a href="${release.repo}/blob/main/CITATION.cff">CITATION.cff</a>.</p>
<p class="links"><a href="../highline.html">Explorer</a><a href="retune.html">Dials</a><a href="studies.html">Studies</a><a href="data.html">Data</a><a href="methods.html">Methods</a><a href="glossary.html">Glossary</a><a href="faq.html">FAQ</a><a href="quality.html">Data quality</a><a href="changes.html">What is new</a><a id="reportlink" href="${release.repo}/issues/new?template=bug.yml">Report a problem</a><a id="feedbacklink" href="${release.repo}/issues/new?template=feedback.yml">Give feedback</a><a href="${release.repo}">Repository</a><a href="${release.repo}/blob/main/CHANGELOG.md">Changelog</a><a href="${release.repo}/blob/main/CITATION.cff">CITATION.cff</a><a href="${release.repo}/blob/main/LICENSE">LICENSE</a><a href="${release.repo}/blob/main/LICENSE-DATA.md">LICENSE-DATA</a></p>
</div></footer>${THEME_JS}`;

// structured metadata so that dataset search understands what this is (schema.org Dataset), from the release and the export manifest
const MIME = { ".csv": "text/csv", ".json": "application/json", ".bib": "application/x-bibtex", ".py": "text/x-python" };
const DATASET_LD = `\n<script type="application/ld+json">${JSON.stringify({
  "@context": "https://schema.org", "@type": "Dataset", name: release.title, description: "Galaxy scaling relations from cosmological simulations and observations: " + stats.records + " curves from " + stats.suites + " simulations and " + stats.obsSources + " observational and empirical sources, each with its definitions (mass aperture, IMF, population), source and a note on whether it can be compared fairly with the others.",
  url: `${SITE_URL}/site/data.html`, sameAs: `https://doi.org/${release.doi}`, identifier: `https://doi.org/${release.doi}`, version: release.version, datePublished: release.released, license: "https://creativecommons.org/licenses/by/4.0/", isAccessibleForFree: true,
  creator: { "@type": "Person", name: release.author }, keywords: ["galaxy formation", "cosmological simulations", "scaling relations", "stellar mass function", "star formation", "black holes", "IllustrisTNG", "SIMBA", "CAMELS"],
  citation: `https://doi.org/${release.doi}`, isBasedOn: release.repo,
  distribution: Object.entries(manifest.files).filter(([f]) => /\.(csv|json|bib)$/.test(f)).map(([f, m]) => ({ "@type": "DataDownload", name: f, contentUrl: `${SITE_URL}/data/export/${f}`, encodingFormat: MIME[f.slice(f.lastIndexOf("."))] || "application/octet-stream", contentSize: `${m.bytes} B`, sha256: m.sha256 }))
}).replace(/</g, "\\u003c")}</script>`;
await mkdir(new URL("dist/site/", root), { recursive: true });
const PAGES = ["index.html", "studies.html", "study-definitions.html", "study-harmonization.html", "study-sfh.html", "study-joint.html", "study-shape.html", "retune.html", "data.html", "methods.html", "sources.html", "findings.html", "glossary.html", "faq.html", "changes.html", "quality.html", "summary.html"];
for (const page of PAGES) {
  let html = await read(`site/src/${page}`);
  const title = (html.match(/<title>([^<]*)<\/title>/) || [])[1], desc = (html.match(/<meta name="description" content="([^"]*)"/) || [])[1];
  if (!title || !desc) throw new Error(`${page}: <title> and <meta name="description"> are required`);
  stats.head = HEAD(title, desc, OG[page]) + (page === "index.html" || page === "data.html" ? DATASET_LD : ""); stats.header = HEADER(page); stats.footer = FOOTER();
  html = html.replace(/\{\{(\w+)\}\}/g, (m, k) => { if (!(k in stats)) throw new Error(`unknown placeholder ${m} in ${page}`); return String(stats[k]); });
  await writeFile(new URL(`dist/site/${page}`, root), page === "findings.html" ? html : withCsp(html));
}
// the page the host serves for an address that does not exist (GitHub Pages serves 404.html from the site root); links are relative to site/ and the base is set from where the site is mounted
{
  const title = "Page not found · sim-highline", desc = "This address does not exist on sim-highline. Here is where to go instead.";
  stats.head = HEAD(title, desc); stats.header = HEADER("404.html"); stats.footer = FOOTER();
  const body = `<main id="main" class="wrap page" tabindex="-1"><div class="doc"><div class="c">
<div class="title"><p class="lab kicker">404 · not found</p><h1>That page does not exist</h1>
<p class="standfirst">The address may be old or mistyped. Pages move; the data does not. Here is where people usually mean to go.</p></div>
<ul class="flat">
<li><a href="../highline.html"><b>Explorer</b></a>: look up a relation and see every published simulation and observation on one plot.</li>
<li><a href="retune.html"><b>Dials</b></a>: turn the feedback dials of two simulated universes and watch the galaxies change.</li>
<li><a href="studies.html"><b>Studies</b></a>: the five questions asked of the data, with the rules written before the answers.</li>
<li><a href="data.html"><b>Data</b></a>: download the curves as CSV or JSON, or load them in Python.</li>
<li><a href="faq.html"><b>Questions</b></a> · <a href="glossary.html">glossary</a> · <a href="quality.html">how much to trust the data</a></li>
</ul>
<p>Looking for something that used to be here? <a href="${release.repo}/issues/new?title=Broken%20link">Tell us</a>, or search the <a href="${release.repo}">repository</a>.</p>
</div></div></main>`;
  const page = `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>${title}</title>\n<meta name="description" content="${desc}">\n<meta name="robots" content="noindex">\n<base href="/site/">\n<script>(function(){var h=location.hostname,p=location.pathname.split("/")[1]||"";var r=/\\.github\\.io$/.test(h)&&p?"/"+p+"/":"/";document.querySelector("base").href=location.origin+r+"site/"})()</script>\n${stats.head}\n</head>\n<body>\n${stats.header}\n${body}\n${stats.footer}\n</body>\n</html>\n`;
  await writeFile(new URL("dist/404.html", root), withCsp(page));
}
// supporting files that pages load (scripts, data, images placed next to the templates) are published beside them
for (const f of await readdir(new URL("site/src/", root))) if (/\.(js|json|svg|png|webp|woff2)$/.test(f)) await copyFile(new URL(`site/src/${f}`, root), new URL(`dist/site/${f}`, root));
console.log(`Built dist/site/{${PAGES.map(p => p.replace(".html", "")).join(",")}}.html (${all.length} records; charts: ${Object.entries(CH).map(([k, c]) => `${k} ${c.curves} sims`).join(", ")}; ${mismatched.length} obs citation mismatches flagged)`);
