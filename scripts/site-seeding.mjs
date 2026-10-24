// Generated parts of the page that explains the black hole seeding difference between IllustrisTNG and SIMBA (site/src/seeding.html).
// Every number comes from a saved file: data/analysis/joint-reachability.json, data/retune/retune.json, data/analysis/third-code.json and data/ensembles/camels-galaxies.json.
// Every statement about how the codes seed black holes is a quotation kept in data/seeding-sources.json. Returns an object of placeholder values.
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const f1 = v => v.toFixed(1), f2 = v => v.toFixed(2);
const pct = v => `${Math.round(100 * v)}%`, pctDown = v => `${Math.floor(100 * v + 1e-9)}%`, pctUp = v => `${Math.ceil(100 * v - 1e-9)}%`;
const sci = (v, sig = 2) => { const e = Math.floor(Math.log10(v)), m = +(v / 10 ** e).toPrecision(sig); return m === 1 ? `10<sup>${e}</sup>` : `${m}×10<sup>${e}</sup>`; };
const FAMILY = { gsmf: "Stellar mass function", qf: "Quenched fraction", sfms: "Star-forming main sequence", bhms: "Black hole mass, galaxies that have one", bhocc: "Black hole occupation", mzr: "Gas metallicity", zstar: "Stellar metallicity", size: "Stellar half-mass radius", fgas: "Gas fraction", shmr: "Stellar-to-halo mass ratio", rho: "Stellar mass and SFR density" };
const pctile = (a, p) => { const s = [...a].sort((x, y) => x - y); if (!s.length) return null; const k = (s.length - 1) * p, i = Math.floor(k); return s[i] + (s[Math.min(i + 1, s.length - 1)] - s[i]) * (k - i); };
const mean = a => a.reduce((t, v) => t + v, 0) / a.length;

// fraction of galaxies with a black hole by stellar-mass bin at one snapshot: mean of the cosmic-variance runs, and the 5th to 95th percentile over the Latin-hypercube runs
function occupation(CG, snap) {
  const out = {}, nb = CG.familyBins.bhocc;
  out.x = Array.from({ length: nb }, (_, i) => (CG.mstarEdges[i] + CG.mstarEdges[i + 1]) / 2);
  for (const code of ["IllustrisTNG", "SIMBA"]) {
    const col = (set, i) => Object.values(CG.suites[code][set]).map(s => s.snaps?.[snap]?.values?.bhocc?.[i]).filter(v => v != null && Number.isFinite(v));
    out[code] = { cv: out.x.map((_, i) => mean(col("CV", i))), lo: out.x.map((_, i) => pctile(col("LH", i), 0.05)), hi: out.x.map((_, i) => pctile(col("LH", i), 0.95)), nCV: Object.keys(CG.suites[code].CV).length, nLH: Object.keys(CG.suites[code].LH).length };
  }
  return out;
}

function figure(occ, thr) {
  const W = 860, HT = 320, L = 62, R = 20, T = 16, B = 50, x0 = 9, x1 = 11.5;
  const px = x => L + (x - x0) / (x1 - x0) * (W - L - R), py = y => T + (1 - y) * (HT - T - B);
  let s = `<g class="axis">`;
  for (let y = 0; y <= 1.0001; y += 0.2) s += `<line x1="${L}" x2="${W - R}" y1="${py(y).toFixed(1)}" y2="${py(y).toFixed(1)}"/><text x="${L - 8}" y="${(py(y) + 4).toFixed(1)}" text-anchor="end">${y.toFixed(1)}</text>`;
  for (let x = 9; x <= 11.5001; x += 0.5) s += `<text x="${px(x).toFixed(1)}" y="${HT - 28}" text-anchor="middle">${x.toFixed(1)}</text>`;
  s += `<text x="${((L + W - R) / 2).toFixed(0)}" y="${HT - 6}" text-anchor="middle">log stellar mass [M☉]</text><text x="14" y="${((T + HT - B) / 2).toFixed(0)}" transform="rotate(-90 14 ${((T + HT - B) / 2).toFixed(0)})" text-anchor="middle">fraction of galaxies with a black hole</text></g>`;
  const path = pts => pts.map(([x, y], i) => `${i ? "L" : "M"}${px(x).toFixed(1)},${py(y).toFixed(1)}`).join("");
  const band = (xs, lo, hi) => `M${xs.map((x, i) => `${px(x).toFixed(1)},${py(lo[i]).toFixed(1)}`).join("L")}L${xs.map((x, i) => `${px(xs[xs.length - 1 - i]).toFixed(1)},${py(hi[xs.length - 1 - i]).toFixed(1)}`).join("L")}Z`;
  s += `<line x1="${px(thr).toFixed(1)}" x2="${px(thr).toFixed(1)}" y1="${T}" y2="${HT - B}" stroke="var(--cream3)" stroke-width="1.4" stroke-dasharray="5 4"/><text class="al" x="${(px(thr) + 6).toFixed(1)}" y="${T + 14}" style="font-size:12px">SIMBA seeding threshold</text>`;
  for (const [code, col] of [["IllustrisTNG", "var(--orange)"], ["SIMBA", "var(--ink)"]]) {
    const o = occ[code];
    s += `<path d="${band(occ.x, o.lo, o.hi)}" fill="${col}" opacity=".16"/><path d="${path(occ.x.map((x, i) => [x, o.cv[i]]))}" fill="none" stroke="${col}" stroke-width="2.6"/>` + occ.x.map((x, i) => `<circle cx="${px(x).toFixed(1)}" cy="${py(o.cv[i]).toFixed(1)}" r="3" fill="${col}"/>`).join("");
  }
  const lx = px(10.55), ly = py(0.36);
  s += `<text class="al" x="${lx.toFixed(1)}" y="${ly.toFixed(1)}" style="font-size:12.5px;fill:var(--orange)">IllustrisTNG</text><text class="al" x="${lx.toFixed(1)}" y="${(ly + 18).toFixed(1)}" style="font-size:12.5px">SIMBA</text>`;
  return `<svg viewBox="0 0 ${W} ${HT}" role="img" aria-labelledby="seedT seedD"><title id="seedT">Fraction of galaxies that hold a black hole against stellar mass, IllustrisTNG and SIMBA at z = 0</title><desc id="seedD">Lines: the mean of the cosmic-variance runs of each code. Pale bands: 5th to 95th percentile over the Latin-hypercube runs. SIMBA is close to zero below log stellar mass 9.5 and close to one above 9.75; IllustrisTNG is about 0.8 at the bottom and rises slowly.</desc>${s}</svg>`;
}

export function seedingStats({ JR, RT, CG, TC, SRC }) {
  const out = {}, Q = Object.fromEntries(SRC.quotes.map(q => [q.id, q])), RQ = Object.fromEntries(SRC.repository.map(q => [q.id, q])), P = SRC.papers;
  const h = SRC.hubble.h, tng = SRC.parameters.IllustrisTNG, simba = SRC.parameters.SIMBA;
  const link = k => `<a href="https://arxiv.org/abs/${esc(P[k].arxiv)}" target="_blank" rel="noopener">${esc(P[k].cite)}</a>`;
  const quote = (id, extra = "") => { const q = Q[id]; return `<blockquote class="src"><p>${id === "camels-h" ? esc("…") + " " + esc(q.text) + " " + esc("…") : esc(q.text)}</p><footer>${link(q.paper)}, ${esc(q.where)}${extra}</footer></blockquote>`; };
  const rquote = id => { const q = RQ[id]; return `<blockquote class="src"><p>${esc(q.text)}</p><footer><code>${esc(q.file)}</code>, ${esc(q.where)}</footer></blockquote>`; };
  Object.assign(out, { seedQTngCamels: quote("camels-tng"), seedQTngRule: quote("weinberger-rule"), seedQTngFree: quote("weinberger-free"), seedQSimbaCamels: quote("camels-simba"), seedQSimbaRule: quote("dave-rule"), seedQBhMass: quote("camels-bhmass"), seedQDials: quote("camels-dials"), seedQProtocol: rquote("protocol-seeding"), seedQInputs: rquote("protocol-inputs"), seedQMore: rquote("analysis-more-than-form"), seedQRes: rquote("resolution-rule"), seedQH: quote("camels-h") });
  // the two settings of each rule, from the registry
  const tngMass = tng.seedMass / h, simbaMass = simba.seedMass / h;
  out.seedTngSeed = `${sci(tng.seedMass, 1)} h<sup>−1</sup> M<sub>☉</sub>`; out.seedTngSeedAbs = `${sci(tngMass)} M<sub>☉</sub>`;
  out.seedSimbaSeed = `${sci(simba.seedMass, 1)} h<sup>−1</sup> M<sub>☉</sub>`; out.seedSimbaSeedAbs = `${sci(simbaMass)} M<sub>☉</sub>`;
  out.seedTngHalo = `${sci(tng.haloMassThreshold, 1)} h<sup>−1</sup> M<sub>☉</sub>`; out.seedSimbaStar = `10<sup>${simba.stellarMassThresholdLog10}</sup> M<sub>☉</sub>`;
  out.seedRatio = String(Math.round(tng.seedMass / simba.seedMass)); out.seedH = String(h);
  // what the catalogues show
  const occ = occupation(CG, "090"), T = occ.IllustrisTNG, S = occ.SIMBA, thr = simba.stellarMassThresholdLog10;
  const hiIdx = occ.x.map((x, i) => i).filter(i => occ.x[i] > thr + 0.2); // bins whose centre lies clearly above the SIMBA threshold
  out.seedFig = figure(occ, thr);
  out.seedLowTng = pct(T.cv[0]); out.seedLowSimba = pct(S.cv[0]); out.seedLow2Tng = pct(T.cv[1]); out.seedLow2Simba = pct(S.cv[1]);
  out.seedHiSimba = pctDown(Math.min(...hiIdx.map(i => S.cv[i]))); out.seedHiTngLo = pctDown(Math.min(...hiIdx.map(i => T.cv[i]))); out.seedHiTngHi = pctUp(Math.max(...hiIdx.map(i => T.cv[i])));
  out.seedHiFrom = String(+(occ.x[hiIdx[0]] - 0.125).toFixed(2));
  out.seedBand = T.lo[0] > S.hi[0] ? `The pale bands show how far moving the dials, the cosmology and the random seed shifts each curve. In the lowest mass bin the 5th percentile over IllustrisTNG runs (${pct(T.lo[0])}) lies above the 95th percentile over SIMBA runs (${pct(S.hi[0])}), so no setting in these simulations closes that gap.` : `The pale bands show how far moving the dials, the cosmology and the random seed shifts each curve. In the lowest mass bin they overlap: IllustrisTNG runs span ${pct(T.lo[0])} to ${pct(T.hi[0])} and SIMBA runs ${pct(S.lo[0])} to ${pct(S.hi[0])}.`;
  out.seedBinW = String(+(CG.mstarEdges[1] - CG.mstarEdges[0]).toFixed(2));
  out.seedFigCap = `Fraction of galaxies that hold a black hole, by stellar mass, at z = 0. Lines: the mean of the ${T.nCV} cosmic-variance runs of each code at the fiducial parameters. Pale bands: 5th to 95th percentile over the ${T.nLH.toLocaleString("en-US")} Latin-hypercube runs of each code, which vary the four dials, the two cosmological parameters and the random seed together. Galaxies are Subfind subhaloes with at least one star particle. Dashed line: the stellar-mass threshold the CAMELS paper gives for SIMBA.`;
  // the study
  const SA = JR.splits.all.between, sens = JR.sensitivity, P0 = JR.point, fam = f => P0["fam:" + f], dc = x => x.D_corrected ?? x.D;
  out.seedJoint = f1(SA.p50); out.seedJointLo = f1(SA.p5); out.seedJointHi = f1(SA.p95);
  out.seedNoOcc = f1(sens.S7a_no_bhocc.D); out.seedNoBoth = f1(sens.S7b_no_bhocc_no_bhms.D); out.seedNoLow = f1(sens.S8_no_two_lowest_mass_bins.D);
  out.seedOccAlone = f1(dc(fam("bhocc"))); out.seedOccAloneRaw = f1(fam("bhocc").D); out.seedOccFid = f1(fam("bhocc").D_fiducial); out.seedMassAlone = f1(dc(fam("bhms")));
  out.seedMzrAlone = f1(dc(fam("mzr")));
  const N = RT && !RT.pending ? RT.native : null;
  out.seedOccNative = N && N.bhocc ? `In the property's own unit, the codes' occupation curves differ by ${f2(N.bhocc.fiducial)} (rms over the mass bins, fraction of galaxies) at the default dials and by ${f2(N.bhocc.alone)} at the dial setting that brings them closest; one noise unit is ${f2(N.bhocc.noise_unit)}.` : "";
  const share = {}; for (const b of JR.decomposition) share[b.family] = (share[b.family] || 0) + b.share;
  out.seedOccShare = pct(share.bhocc || 0); out.seedMzrShare = pct(share.mzr || 0);
  const seedFams = new Set(SRC.seedingFamilies.families);
  out.seedFamRows = JR.meta.families.filter(f => f !== "hmf" && JR.splits["fam:" + f]).map(f => ({ f, d: dc(fam(f)), v: JR.splits["fam:" + f].verdict, s: share[f] || 0 })).sort((a, b) => b.d - a.d)
    .map(r => `<tr><td>${esc(FAMILY[r.f] || r.f)}</td><td>${esc(r.v)}</td><td class="n">${f1(r.d)}</td><td class="n">${pct(r.s)}</td><td>${seedFams.has(r.f) ? "yes" : "no"}</td></tr>`).join("");
  const nameOf = f => FAMILY[f].toLowerCase();
  out.seedStructural = JR.meta.families.filter(f => JR.splits["fam:" + f]?.verdict === "structural").map(nameOf).join(" and ");
  out.seedRemovable = String(JR.meta.families.filter(f => f !== "hmf" && JR.splits["fam:" + f]?.verdict === "removable").length);
  out.seedNFam = String(JR.meta.families.filter(f => f !== "hmf" && JR.splits["fam:" + f]).length);
  out.seedUnresolved = String(JR.meta.families.filter(f => f !== "hmf" && JR.splits["fam:" + f]?.verdict === "unresolved").length);
  if (TC) {
    const p = TC.pairs, k = (a, b) => p[`${a}|${b}`];
    out.seedThird = `On the ${TC.n_outputs} outputs that all three codes provide (exploratory, after the registered run), the black hole occupation distance is ${f1(k("IllustrisTNG", "SIMBA").bhocc.D)} between IllustrisTNG and SIMBA, ${f1(k("SIMBA", "Astrid").bhocc.D)} between SIMBA and Astrid, and ${f1(k("IllustrisTNG", "Astrid").bhocc.D)} between IllustrisTNG and Astrid. Taken alone, occupation separates SIMBA from the other two. Astrid's own seeding rule is not described in the sources this page quotes, so nothing is said about why.`;
  } else out.seedThird = "";
  // papers read
  out.seedPapers = Object.values(P).map(p => `<li><a href="https://arxiv.org/abs/${esc(p.arxiv)}" target="_blank" rel="noopener">${esc(p.cite)}</a>, arXiv:${esc(p.arxiv)}. ${esc(p.why)} SHA-256 of the source archive read: <code class="hx">${esc(p.eprintSha256)}</code>.</li>`).join("");
  out.seedRetrieved = SRC.retrieved;
  out.seedNQuotes = String(SRC.quotes.length + SRC.repository.length);
  // plain-words box
  out.plainSeedOne = `The two codes put their first black holes into galaxies by different rules, and none of the four feedback dials changes that rule.`;
  out.plainSeed = `In both codes the black holes are put in by a rule: when a halo or a galaxy passes a size threshold, the code places one. IllustrisTNG plants a heavy one (${out.seedTngSeed}) in a halo above ${out.seedTngHalo}. SIMBA plants a light one (${out.seedSimbaSeed}) in a galaxy above about ${out.seedSimbaStar} of stars. In the saved catalogues, at z = 0, ${out.seedLowTng} of IllustrisTNG galaxies in the lowest mass bin hold a black hole and ${out.seedLowSimba} of SIMBA galaxies do. Fitted one property at a time, retuning the four dials can close ${out.seedRemovable} of the ${out.seedNFam} properties studied, but not this one. This page explains one of our own results. No outside expert has reviewed the result or this explanation.`;
  return out;
}
