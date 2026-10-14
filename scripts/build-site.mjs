import { cp, readdir, readFile, writeFile, mkdir } from "node:fs/promises";
import vm from "node:vm";
const root = new URL("../", import.meta.url);
const read = async p => readFile(new URL(p, root), "utf8");
const palette = await read("data/palette.css");
const ctx = { globalThis: {} };
vm.runInNewContext(await read("compare.js"), ctx);
const { evaluator } = ctx.globalThis.SimHighlineCompare;
const files = (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json")).sort();
const all = [];
for (const f of files) all.push(...JSON.parse(await read(`data/curves/${f}`)).records);
const release = JSON.parse(await read("data/release.json"));
const audit = JSON.parse(await read("data/audit-report.json"));
const notes = JSON.parse(await read("data/relation-notes.json")).relations;
const simProf = JSON.parse(await read("data/simulation-profiles.json"));
const obsProf = JSON.parse(await read("data/observation-profiles.json")).sources;
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
<p class="inc"><b>In sim-highline:</b> ${n(rs.length)} records · ${runsOf(rs)} run${runsOf(rs) > 1 ? "s" : ""} · ${relOf(rs).join(", ")} · z ${(+Math.min(...z).toFixed(2))} to ${(+Math.max(...z).toFixed(2))} · ${tiers.map(([t, c]) => `${c} ${t.replace(/-/g, " ")}`).join(", ")} · <a href="../highline.html#r=${relOf(rs)[0]}">open</a></p></article>`;
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
  (og.get(g) || og.set(g, []).get(g)).push(`<tr id="${slug(src)}"><td>${esc(src)}${bad ? ' <span class="flag" title="the citation stored with this record names a different paper than the label">check</span>' : ""}</td><td>${pr ? esc(pr.facility) : '<span class="dim">not yet filled: see the cited paper</span>'}</td><td>${pr ? esc(pr.measures) : ""}</td><td>${relOf(o.rs).join(", ")}</td><td>${(+Math.min(...z).toFixed(2))} to ${(+Math.max(...z).toFixed(2))}</td><td>${uniq(o.rs.map(r => (r.provenance.tier || "").replace(/-/g, " "))).join(", ")}</td><td>${[...o.links].slice(0, 1).map(l => `<a href="${esc(l)}" target="_blank" rel="noopener">${esc(cite.slice(0, 70))}</a>`).join("") || esc(cite.slice(0, 70))}</td></tr>`);
}
for (const g of ["Surveys and measurements", "Compilations", "Empirical models (constrained by data, not measurements)", "Simulation-calibrated theory curves (not observations)", "Not yet profiled"]) if (og.has(g)) obsHtml += `<h3 class="grp">${esc(g)} <span class="yr">${og.get(g).length}</span></h3><div class="tw"><table><thead><tr><th>Source</th><th>Survey / facility</th><th>What it measures</th><th>Relations</th><th>z</th><th>Evidence</th><th>Citation</th></tr></thead><tbody>${og.get(g).join("")}</tbody></table></div>`;
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
  const nice = v => String(v).replace(/\s*\(.*$/, "").replace(/^aperture-/, "").replace(/rhalf/, "R_half").replace(/pkpc/, " pkpc").replace(/-/g, " "), cut = t => t.length > 22 ? t.slice(0, 21) + "…" : t;
  const RN = { gsmf: "stellar mass function", shmr: "stellar-to-halo mass", sfms: "main sequence", uvlf: "UV luminosity function", size: "size", gas: "cold gas fraction", btfr: "baryonic Tully-Fisher" };
  const lo = Math.min(-0.7, ...forestRows.map(g => g.medianRange[0])) - 0.05, hi = Math.max(0.3, ...forestRows.map(g => g.medianRange[1])) + 0.05, FL2 = 300, FW = W - FL2 - 70, RH2 = 40, H2 = forestRows.length * RH2 + 46;
  const fx = v => FL2 + (v - lo) / (hi - lo) * FW;
  let fs = `<svg viewBox="0 0 ${W} ${H2}" role="img" aria-labelledby="fsT fsD"><title id="fsT">Measured shift in the relation when only one definition changes inside a single simulation run</title><desc id="fsD">Dot: median over epochs; bar: range of the per-epoch medians. Zero means the definition does not matter.</desc><g class="axis">`;
  for (let v = Math.ceil(lo * 4) / 4; v <= hi; v += 0.25) fs += `<line x1="${fx(v).toFixed(1)}" x2="${fx(v).toFixed(1)}" y1="6" y2="${H2 - 30}"/><text x="${fx(v).toFixed(1)}" y="${H2 - 12}" text-anchor="middle">${v.toFixed(2)}</text>`;
  fs += `<line x1="${fx(0).toFixed(1)}" x2="${fx(0).toFixed(1)}" y1="6" y2="${H2 - 30}" style="stroke:var(--cream3);stroke-width:1.4"/></g>`;
  forestRows.forEach((g, i) => {
    const y = 20 + i * RH2, c = colorFor(g.source), m = g.median_dy;
    fs += `<text class="al" x="${FL2 - 14}" y="${y - 2}" text-anchor="end" style="font-weight:600">${esc(g.source)} · ${esc(RN[g.relation] || g.relation)}</text><text class="al" x="${FL2 - 14}" y="${y + 14}" text-anchor="end" style="fill:var(--cream3);font-size:12px">${esc(cut(nice(g.from)))} → ${esc(cut(nice(g.to)))}</text><line x1="${fx(g.medianRange[0]).toFixed(1)}" x2="${fx(g.medianRange[1]).toFixed(1)}" y1="${y + 4}" y2="${y + 4}" stroke="${c}" stroke-width="6" stroke-linecap="round" opacity=".5"/><circle cx="${fx(m).toFixed(1)}" cy="${y + 4}" r="6.5" fill="${c}" stroke="var(--bg2)" stroke-width="2"/><text class="al" x="${W - 62}" y="${y + 9}">${m >= 0 ? "+" : "−"}${Math.abs(m).toFixed(2)}</text>`;
  });
  fs += `</svg>`;
  stats.fForest = fs;
  const cls = [["matched", S.byClass.matched, "var(--ink)"], ["differing", S.byClass.differing, "var(--orange)"], ["unknown", S.byClass.unknown, "var(--mustard)"], ["not comparable", S.byClass.mismatch, "var(--line2)"]];
  let x = 0, cb = `<svg viewBox="0 0 ${W} 86" role="img" aria-labelledby="clT"><title id="clT">Cross-simulation record pairs by what the documented definitions allow</title>`;
  for (const [n, v, c] of cls) { const w = v / S.pairs * W; cb += `<rect x="${x.toFixed(1)}" y="8" width="${Math.max(w - 2, 1).toFixed(1)}" height="30" fill="${c}"/><text class="al" x="${(x + 2).toFixed(1)}" y="62">${esc(n)}</text><text class="al" x="${(x + 2).toFixed(1)}" y="80" style="font-weight:600">${Math.round(100 * v / S.pairs)}% · ${v}</text>`; x += w; }
  cb += `</svg>`;
  stats.fClasses = cb;
  stats.fLedger = FL.fills.map(f => { const n = sims.filter(r => (r.provenance.definitionFills || []).includes(f.id)).length; return `<tr><td>${esc(f.evidence.citation)}<br><a href="${esc(f.evidence.url)}" target="_blank" rel="noopener">arXiv:${esc(f.evidence.url.split("/").pop())}</a></td><td>${esc(Object.entries(f.set).map(([k, v]) => `${k} = ${v}`).join("; "))}</td><td>${n}</td><td>${esc(f.evidence.where)}<br><span class="dim">“${esc(f.evidence.quote)}”</span></td></tr>`; }).join("");
  stats.fRead = FL.readWithoutResult.map(r => `<li><b>${esc(r.paper)}</b> (<a href="https://arxiv.org/abs/${esc(r.arxiv)}" target="_blank" rel="noopener">arXiv:${esc(r.arxiv)}</a>): ${esc(r.note)}</li>`).join("");
  stats.fPairs = n(S.pairs); stats.fMatchedPct = pc(S.byClass.matched); stats.fUnknownPct = pc(S.byClass.unknown); stats.fMismatchPct = pc(S.byClass.mismatch); stats.fDifferingPct = pc(S.byClass.differing);
  stats.fRecRecords = UD.summary.recordsWithRecoveredDefinition; stats.fSimRecords = UD.summary.simulationRecords; stats.fUndoc = UD.summary.undocumentedValues; stats.fNotStated = UD.summary.sourceReadNotStated; stats.fNotRead = UD.summary.sourceNotYetRead; stats.fNoPaper = UD.summary.noPaperToRead;
  stats.fTests = S.testsRun; stats.fBelow = S.testsBelow0 || S["testsBelow0.05"]; stats.fExpect = S["expectedBelow0.05UnderNull"]; stats.fBonf = S.bonferroniSignificant;
  stats.fOpenBreakdown = `${UD.summary.sourceReadNotStated} where the paper was read and does not state it${UD.summary.sourceNotYetRead ? `, ${UD.summary.sourceNotYetRead} where it has not yet been read for that key` : "; every paper behind a record has now been read for every open key"}, and ${UD.summary.noPaperToRead} where the source is a data release without a paper`;
  stats.fNFills = FL.fills.length; stats.fSensN = A.sensitivity.pairs.length; stats.fSensG = A.sensitivity.summary.length;
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
  stats.mfE1 = `The spread across ${E1.n_balanced} families is ${E1.sd_low.toFixed(2)} dex at z = 0.5 to 3 and ${E1.sd_high.toFixed(2)} dex at z = 5 to 7.5 (a factor ${(10 ** E1.phi).toFixed(1)}; 90% interval of the log ratio ${f2(E1.phi_ci90[0])} to ${f2(E1.phi_ci90[1])}, Pitman–Morgan p = ${E1.pitman_morgan.p_one_sided.toFixed(3)}): funnel ${stats.mfSuccess} by the rule fixed in advance.`;
  const rr = C.reachability, kk = C.calibration;
  stats.mfE3 = `Retuning four feedback parameters per code over the same factors, IllustrisTNG and SIMBA stay ${rr.full.D_dex.toFixed(2)} dex apart (emulators trained on half of the simulations: the same code against its other half leaves at most ${rr.controls_full.p95.toFixed(2)}, two seeds of these codes differ by ${rr.margin_dex.toFixed(2)}): <b>${rr.verdict}</b>. Tuned to the same observed star formation history they disagree at z = ${kk.z_target[0]} to ${kk.z_target[kk.z_target.length - 1]} (intervals disjoint at ${pct(kk.disjoint_fraction)} of the redshifts): <b>${kk.verdict}</b>.`;
}
const SUN = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="10" cy="10" r="3.6"/><path d="M10 2.5v1.8M10 15.7v1.8M2.5 10h1.8M15.7 10h1.8M4.7 4.7l1.3 1.3M14 14l1.3 1.3M4.7 15.3 6 14M14 6l1.3-1.3"/></svg>', MOON = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M16.5 11.8A6.8 6.8 0 0 1 8.2 3.5a6.8 6.8 0 1 0 8.3 8.3z"/></svg>';
const THEME_JS = `<script>(function(){var b=document.getElementById("theme"),r=document.documentElement,S='${SUN}',M='${MOON}';function now(){return r.dataset.theme||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")}function paint(){var d=now()==="dark";b.innerHTML=d?S:M;b.setAttribute("aria-label",d?"Switch to the light theme":"Switch to the dark theme")}b.onclick=function(){var n=now()==="dark"?"light":"dark";r.dataset.theme=n;try{localStorage.setItem("sh-theme",n)}catch(e){}paint()};paint()})()</script>`;
const NAV = (cur) => `<nav aria-label="Main"><a class="mark" href="index.html" aria-label="sim-highline home">SIM<i>/</i>HIGHLINE</a><span class="sp"></span>${[["about.html", "About"], ["findings.html", "Findings"], ["sources.html", "Simulations &amp; observations"], ["use-cases.html", "Use cases"]].map(([h, t]) => `<a class="l" href="${h}"${h === cur ? ' aria-current="page"' : ""}>${t}</a>`).join("")}<button class="ico" id="theme" type="button" aria-label="Switch theme"></button><a class="btn main" href="../highline.html">Open the app</a></nav>${THEME_JS}`;
await mkdir(new URL("dist/site/", root), { recursive: true });
await cp(new URL("site/src/img/", root), new URL("dist/site/img/", root), { recursive: true });
for (const page of ["index.html", "use-cases.html", "about.html", "sources.html", "findings.html"]) {
  let html = await read(`site/src/${page}`);
  stats.nav = NAV(page);
  html = html.replace("/*__CSS__*/", () => stats.css).replace(/\{\{(\w+)\}\}/g, (m, k) => { if (!(k in stats)) throw new Error(`unknown placeholder ${m} in ${page}`); return String(stats[k]); });
  await writeFile(new URL(`dist/site/${page}`, root), html);
}
console.log(`Built dist/site/{index,use-cases,about,sources,findings}.html (${all.length} records; charts: ${Object.entries(CH).map(([k, c]) => `${k} ${c.curves} sims`).join(", ")}; ${mismatched.length} obs citation mismatches flagged)`);
