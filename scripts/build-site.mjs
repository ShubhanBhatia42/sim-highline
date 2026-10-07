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
const SUN = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="10" cy="10" r="3.6"/><path d="M10 2.5v1.8M10 15.7v1.8M2.5 10h1.8M15.7 10h1.8M4.7 4.7l1.3 1.3M14 14l1.3 1.3M4.7 15.3 6 14M14 6l1.3-1.3"/></svg>', MOON = '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"><path d="M16.5 11.8A6.8 6.8 0 0 1 8.2 3.5a6.8 6.8 0 1 0 8.3 8.3z"/></svg>';
const THEME_JS = `<script>(function(){var b=document.getElementById("theme"),r=document.documentElement,S='${SUN}',M='${MOON}';function now(){return r.dataset.theme||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light")}function paint(){var d=now()==="dark";b.innerHTML=d?S:M;b.setAttribute("aria-label",d?"Switch to the light theme":"Switch to the dark theme")}b.onclick=function(){var n=now()==="dark"?"light":"dark";r.dataset.theme=n;try{localStorage.setItem("sh-theme",n)}catch(e){}paint()};paint()})()</script>`;
const NAV = (cur) => `<nav aria-label="Main"><a class="mark" href="index.html" aria-label="sim-highline home">SIM<i>/</i>HIGHLINE</a><span class="sp"></span>${[["about.html", "About"], ["sources.html", "Simulations &amp; observations"], ["use-cases.html", "Use cases"]].map(([h, t]) => `<a class="l" href="${h}"${h === cur ? ' aria-current="page"' : ""}>${t}</a>`).join("")}<button class="ico" id="theme" type="button" aria-label="Switch theme"></button><a class="btn main" href="../highline.html">Open the app</a></nav>${THEME_JS}`;
await mkdir(new URL("dist/site/", root), { recursive: true });
await cp(new URL("site/src/img/", root), new URL("dist/site/img/", root), { recursive: true });
for (const page of ["index.html", "use-cases.html", "about.html", "sources.html"]) {
  let html = await read(`site/src/${page}`);
  stats.nav = NAV(page);
  html = html.replace("/*__CSS__*/", () => stats.css).replace(/\{\{(\w+)\}\}/g, (m, k) => { if (!(k in stats)) throw new Error(`unknown placeholder ${m} in ${page}`); return String(stats[k]); });
  await writeFile(new URL(`dist/site/${page}`, root), html);
}
console.log(`Built dist/site/{index,use-cases,about,sources}.html (${all.length} records; charts: ${Object.entries(CH).map(([k, c]) => `${k} ${c.curves} sims`).join(", ")}; ${mismatched.length} obs citation mismatches flagged)`);
