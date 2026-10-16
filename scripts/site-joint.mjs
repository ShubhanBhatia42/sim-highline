// Generated parts of the joint-reachability study page (study S4): every number and verdict word comes from data/analysis/joint-reachability.json.
// When that file does not exist yet the page says the study is pending. Returns an object of placeholder values.
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const f2 = (v, d = 2) => (v == null || !Number.isFinite(v) ? "–" : v.toFixed(d));
const md = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");
const FAMILY = { gsmf: "Stellar mass function", qf: "Quenched fraction", sfms: "Star-forming main sequence", bhms: "Black hole mass at fixed M*", bhocc: "Black hole occupation", mzr: "Gas metallicity at fixed M*",
  zstar: "Stellar metallicity at fixed M*", size: "Stellar half-mass radius", fgas: "Gas fraction at fixed M*", shmr: "Stellar-to-halo mass ratio", rho: "Stellar mass and SFR density", hmf: "Halo mass function (control)" };
const VERDICT = { structural: "structural", removable: "removable", unresolved: "unresolved" };

export function jointStats(R, repo, native) {
  const out = {};
  if (!R) {
    const pend = "Pending: the protocol is committed and the analysis has not been run.";
    Object.assign(out, { jrStatus: "Pre-registered · pending", jrAbs: pend, jrAbsShort: pend, jrHead: "pending", jrJ1: `<p>${pend}</p>`, jrFig1: "", jrFamRows: "", jrJ2: "", jrJ3: "", jrJ4: "", jrFig2: "", jrPathRows: "", jrDropRows: "", jrDecompRows: "", jrReading: `<p>${pend}</p>`, jrNativeRows: "", jrZRows: "", jrRespRows: "", jrValRows: "", jrSensRows: "", jrDev: "<li>none yet</li>", jrElig: "The eligible outputs are counted in the protocol", jrNoise: "not yet computed", jrNote: "", jrVal: "Pending.", jrD: "–", jrDfid: "–", jrVerdict: "pending", jrDials: "" });
    return out;
  }
  const P = R.point, S = R.splits, fams = R.meta.families.filter(f => f !== "hmf"), A = P.all, SA = S.all;
  const dc = x => (x.D_corrected ?? x.D);
  const famRows = fams.filter(f => S["fam:" + f]).map(f => ({ f, d: dc(P["fam:" + f]), d0: P["fam:" + f].D_fiducial, s: S["fam:" + f], nb: P["fam:" + f].n_blocks, red: (S["fam:" + f + "@" + R.meta.reduced_range] || {}).verdict })).sort((a, b) => b.d - a.d);
  const nStruct = famRows.filter(r => r.s.verdict === "structural").length;
  const J3 = R.J3 || {};
  out.jrStatus = "Pre-registered · result";
  out.jrHead = `Joint D = ${f2(A.D, 1)} (${SA.verdict}); ${nStruct} of ${famRows.length} families structural alone`;
  const nm = f => FAMILY[f].replace(" at fixed M*", "").replace(/^./, c => c.toLowerCase());
  const list = a => a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1];
  const cap = t => t.replace(/^./, c => c.toUpperCase());
  const remF = famRows.filter(r => r.s.verdict === "removable").map(r => r.f), strF = famRows.filter(r => r.s.verdict === "structural").map(r => r.f), unrF = famRows.filter(r => r.s.verdict === "unresolved").map(r => r.f);
  out.jrAbs = `For IllustrisTNG and SIMBA in the CAMELS experiment (${A.n_outputs} binned galaxy-population outputs in ${A.n_blocks} blocks, z = 0 to 2.15, both codes read with the same catalogue definitions), retuning four parameters per code leaves the two ${f2(SA.between.p50, 1)} noise units apart on all observables at once (${f2(A.D_fiducial, 1)} at the fiducial parameters; 1 is the scatter between two seeds): ${SA.verdict}. `
    + `Fitted one family at a time, ${strF.length} of ${famRows.length} stay structural (${list(strF.map(nm)) || "none"}), ${remF.length} become removable (${list(remF.map(nm)) || "none"}) and ${unrF.length} are unresolved (${list(unrF.map(nm)) || "none"})`
    + (J3.mechanism ? `; the joint distance is classed ${J3.mechanism}` : "") + ".";
  out.jrAbsShort = `IllustrisTNG against SIMBA over ${A.n_outputs} binned galaxy-population outputs at z = 0 to 2.15: retuning four parameters per code leaves them ${f2(SA.between.p50, 1)} noise units apart at once (margin 1). Alone, ${strF.length} of ${famRows.length} families stay structural (${list(strF.map(nm)) || "none"}) and ${remF.length} can be matched (including ${list(["gsmf", "qf", "rho"].filter(f => remF.includes(f)).map(nm)) || "none of the usual calibration targets"}).`;
  const bare = x => x.replace(/^\*\*J\d - [^*]*\*\*\s*/, "");
  out.jrJ1 = R.headline.slice(0, 1).map(x => `<p>${md(bare(x))}</p>`).join("");
  out.jrJ2 = R.headline[1] ? `<p>${md(bare(R.headline[1]))}</p>` : "";
  out.jrJ3 = R.headline[2] ? `<p>${md(bare(R.headline[2]))}</p>` : "";
  out.jrJ4 = R.headline[3] ? `<p>${md(bare(R.headline[3]))}</p>` : "";
  out.jrVal = R.headline[4] ? md(R.headline[4]) : "";
  // ---- Fig 1: distance by family
  const rowsSvg = (rows, id, title, desc, labelW) => {
    const W = 860, RH = 31, L = labelW, Rm = 170, T = 22, B = 34, H = rows.length * RH + T + B;
    const xmax = Math.max(1.4, ...rows.map(r => r.hi)) * 1.04, x = v => L + v / xmax * (W - L - Rm), xr = W - Rm + 14;
    let g = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-labelledby="${id}T ${id}D"><title id="${id}T">${esc(title)}</title><desc id="${id}D">${esc(desc)}</desc><g class="axis">`;
    const step = xmax > 12 ? 4 : xmax > 6 ? 2 : xmax > 3 ? 1 : 0.5;
    for (let v = 0; v <= xmax + 1e-9; v += step) g += `<line x1="${x(v).toFixed(1)}" x2="${x(v).toFixed(1)}" y1="${T}" y2="${H - B}"/><text x="${x(v).toFixed(1)}" y="${H - B + 15}" text-anchor="middle">${v % 1 ? v.toFixed(1) : v}</text>`;
    g += `<text class="al" x="${((L + W - Rm) / 2).toFixed(0)}" y="${H - 3}" text-anchor="middle">distance between the codes, in noise units</text></g>`;
    g += `<line x1="${x(1).toFixed(1)}" x2="${x(1).toFixed(1)}" y1="${T - 4}" y2="${H - B}" stroke="var(--ink)" stroke-width="1" stroke-dasharray="4 3"/><text x="${x(1).toFixed(1)}" y="${T - 8}" text-anchor="middle" style="font:400 10px var(--mono);fill:var(--ink2)">margin 1</text>`;
    rows.forEach((r, i) => {
      const y = T + i * RH + 4, c = r.verdict === "structural" ? "var(--orange)" : "var(--ink)";
      g += `<text x="${L - 10}" y="${y + 13}" text-anchor="end" style="font:400 12.5px var(--sans);fill:var(--ink)">${esc(r.label)}</text>`;
      if (r.d0 != null) g += `<rect x="${x(0)}" y="${y}" width="${Math.max(0, x(r.d0) - x(0)).toFixed(1)}" height="5" fill="var(--rule-strong)"/>`;
      g += `<rect x="${x(0)}" y="${y + 7}" width="${Math.max(1, x(r.d) - x(0)).toFixed(1)}" height="9" fill="${c}"/>`;
      g += `<g stroke="var(--ink2)" stroke-width="1.2"><line x1="${x(r.lo).toFixed(1)}" x2="${x(r.hi).toFixed(1)}" y1="${y + 21}" y2="${y + 21}"/><line x1="${x(r.lo).toFixed(1)}" x2="${x(r.lo).toFixed(1)}" y1="${y + 18}" y2="${y + 24}"/><line x1="${x(r.hi).toFixed(1)}" x2="${x(r.hi).toFixed(1)}" y1="${y + 18}" y2="${y + 24}"/></g>`;
      g += `<text x="${xr}" y="${y + 17}" style="font:400 11px var(--mono);fill:${r.verdict === "structural" ? "var(--orange)" : "var(--ink2)"}">${f2(r.d, 2)} · ${esc(r.verdict)}</text>`;
    });
    return g + "</svg>";
  };
  const rows1 = [{ label: "All observables", d: dc(A), d0: A.D_fiducial, lo: SA.between.p5, hi: SA.between.p95, verdict: SA.verdict }, ...famRows.map(r => ({ label: FAMILY[r.f], d: r.d, d0: r.d0, lo: r.s.between.p5, hi: r.s.between.p95, verdict: r.s.verdict }))];
  out.jrFig1 = rowsSvg(rows1, "jr1", "Distance between IllustrisTNG and SIMBA after retuning, by observable family", "Bars: minimum distance over both codes' four parameters, all simulations, with the emulators' variance at the minimiser removed (dark; vermilion where structural alone); light bar: distance at the fiducial parameters; grey whisker: 5th to 95th percentile over half-sample emulators.", 210);
  out.jrFamRows = famRows.map(fr => { const s = fr.s; return `<tr><td>${esc(FAMILY[fr.f])}</td><td class="n">${fr.nb}</td><td class="n">${f2(fr.d0)}</td><td class="n">${f2(fr.d)}</td><td class="n">${f2(s.between.p5)} – ${f2(s.between.p95)}</td><td class="n">${f2(s.control.p95)}</td><td>${esc(s.verdict)}</td><td>${esc(fr.red || "–")}</td></tr>`; }).join("")
    + `<tr><td><b>All observables</b></td><td class="n">${A.n_blocks}</td><td class="n">${f2(A.D_fiducial)}</td><td class="n">${f2(dc(A))}</td><td class="n">${f2(SA.between.p5)} – ${f2(SA.between.p95)}</td><td class="n">${f2(SA.control.p95)}</td><td><b>${esc(SA.verdict)}</b></td><td>${esc((S["all@" + R.meta.reduced_range] || {}).verdict || "–")}</td></tr>`;
  out.jrDecompRows = (R.decomposition || []).slice(0, 10).map(x => `<tr><td>${esc(FAMILY[x.family])} at z = ${R.meta.z[x.snapshot]}</td><td class="n">${x.n_outputs}</td><td class="n">${(100 * x.share).toFixed(1)} %</td><td class="n">${f2(x.rms_noise_units)}</td></tr>`).join("");
  // ---- Fig 2: forward selection
  const path = (R.greedy_path || []).map((s, j) => ({ label: `+ ${FAMILY[s.family]}`, d: s.D, d0: null, lo: S[`path:${j + 1}`]?.between.p5 ?? s.D, hi: S[`path:${j + 1}`]?.between.p95 ?? s.D, verdict: S[`path:${j + 1}`]?.verdict ?? "–" }));
  out.jrFig2 = path.length ? rowsSvg(path, "jr2", "Joint distance as observable families are added one at a time", "Each row adds the family that raises the joint distance most; bars are the point estimate on all simulations, whiskers the 5th to 95th percentile over half-sample emulators (50 splits).", 250) : "";
  out.jrPathRows = path.map((p, j) => `<tr><td class="n">${j + 1}</td><td>${esc(p.label.slice(2))}</td><td class="n">${f2(p.d)}</td><td class="n">${f2(p.lo)} – ${f2(p.hi)}</td><td>${esc(p.verdict)}</td></tr>`).join("");
  out.jrDropRows = fams.filter(f => S["drop:" + f]).map(f => `<tr><td>${esc(FAMILY[f])}</td><td class="n">${f2(P["drop:" + f].D)}</td><td class="n">${f2(S["drop:" + f].between.p50)}</td><td>${esc(S["drop:" + f].verdict)}</td></tr>`).join("");
  // ---- redshift
  out.jrZRows = Object.keys(S).filter(k => k.startsWith("z:")).map(k => `<tr><td class="n">${R.meta.z[k.slice(2)]}</td><td class="n">${P[k].n_outputs}</td><td class="n">${f2(P[k].D_fiducial)}</td><td class="n">${f2(P[k].D)}</td><td class="n">${f2(S[k].between.p5)} – ${f2(S[k].between.p95)}</td><td>${esc(S[k].verdict)}</td></tr>`).join("");
  // ---- response: rms over the blocks of a family, per dial, in noise units; with inline bars
  const dials = ["A_SN1", "A_AGN1", "A_SN2", "A_AGN2"];
  const resp = {};
  for (const suite of ["IllustrisTNG", "SIMBA"]) {
    resp[suite] = {};
    for (const [k, v] of Object.entries(R.response[suite])) { const f = k.split("|")[0]; if (f === "hmf") continue; (resp[suite][f] ||= []).push(v); }
  }
  const rms = (a, j) => Math.sqrt(a.reduce((s, v) => s + v[j] ** 2, 0) / a.length);
  const mx = Math.max(...["IllustrisTNG", "SIMBA"].flatMap(su => Object.values(resp[su]).flatMap(a => [0, 1, 2, 3].map(j => rms(a, j)))));
  const bar = v => `<span class="rb"><i style="width:${Math.max(1, Math.round(100 * v / mx))}%"></i><b>${f2(v, 1)}</b></span>`;
  out.jrRespRows = fams.filter(f => resp.IllustrisTNG[f] && resp.SIMBA[f]).map(f => `<tr><td>${esc(FAMILY[f])}</td>${["IllustrisTNG", "SIMBA"].map(su => [0, 1, 2, 3].map(j => `<td class="rc">${bar(rms(resp[su][f], j))}</td>`).join("")).join("")}</tr>`).join("");
  out.jrDials = dials.join(" · ");


  // ---- the distances in the units of the observables (descriptive; from the emulators at the study's minimisers)
  const nu = u => (u === "dex" ? "dex" : "in fraction");
  out.jrNativeRows = native ? fams.filter(f => native[f]).map(f => { const n = native[f]; const d = v => (v == null ? "–" : v.toFixed(2)); return `<tr><td>${esc(FAMILY[f])}</td><td>${nu(n.unit)}</td><td class="n">${d(n.noise_unit)}</td><td class="n">${d(n.fiducial)}</td><td class="n">${d(n.alone)}</td><td class="n">${d(n.joint)}</td></tr>`; }).join("") : "";
  // ---- reading: prose assembled from the result, so that it cannot say something the numbers do not
  const rem = famRows.filter(r => r.s.verdict === "removable"), str = famRows.filter(r => r.s.verdict === "structural"), unr = famRows.filter(r => r.s.verdict === "unresolved");
  const calib = ["gsmf", "qf", "rho"].filter(f => rem.some(r => r.f === f));
  const flip = famRows.filter(r => r.red && r.red !== r.s.verdict);
  const drops = fams.filter(f => P["drop:" + f]).map(f => P["drop:" + f].D);
  const sens = R.sensitivity || {};
  const zs = Object.keys(S).filter(k => k.startsWith("z:")).map(k => ({ z: R.meta.z[k.slice(2)], d: dc(P[k]), n: P[k].n_outputs })).sort((a, b) => a.z - b.z);
  const rise = zs.length > 1 && zs.every((x, i) => i === 0 || x.d > zs[i - 1].d);
  const ratio = J3.ratio_between, nul = J3.ratio_control;
  const para = [];
  para.push(`<p><b>What retuning does.</b> ${rem.length} of the ${famRows.length} families come within the margin of agreement when the four parameters of each code are tuned for that family alone: ${list(rem.map(r => nm(r.f)))}.` + (calib.length ? ` Among them are ${list(calib.map(f => "the " + nm(f)))}, the quantities that galaxy-formation models are usually calibrated on, so agreement on those says little about whether two codes are alike (the same conclusion study <a href="study-sfh.html">S3</a> reached for the cosmic star formation history).` : "") + `</p>`);
  if (str.length) para.push(`<p><b>What it does not.</b> ${cap(list(str.map(r => `${nm(r.f)} (${f2(r.d0, 1)} at the fiducial parameters, ${f2(r.d, 1)} after retuning)`)))} stay${str.length === 1 ? "s" : ""} beyond the margin however the dials are set within the CAMELS ranges, so ${str.length === 1 ? "it is" : "they are"} what separates these two codes by construction rather than by calibration.`
    + (unr.length ? ` ${cap(list(unr.map(r => nm(r.f))))} ${unr.length === 1 ? "is" : "are"} unresolved, at the margin.` : "")
    + (flip.length ? ` With the search kept to 75 % of the parameter range the verdict changes for ${list(flip.map(r => `${nm(r.f)} (${r.s.verdict} to ${r.red})`))}: agreement there leans on the edge of the design, where the emulators are least constrained.` : "") + `</p>`);
  para.push(`<p><b>Not one observable.</b> Leaving out any single family leaves the joint distance between ${f2(Math.min(...drops), 1)} and ${f2(Math.max(...drops), 1)} noise units` + (sens.S7b_no_bhocc_no_bhms ? `; without the black hole occupation and mass, whose difference is a seeding choice that no dial changes, it is ${f2(sens.S7b_no_bhocc_no_bhms.D, 1)} (point estimate, all simulations)` : "") + `. The separation is therefore spread over many observables and not carried by one.</p>`);
  if (ratio && nul) para.push(`<p><b>The cost of one parameter pair.</b> Requiring one parameter pair for all families instead of one per family multiplies the squared distance by ${f2(ratio.p50, 2)} (half-sample median); two halves of one code give ${f2(nul.p50, 2)} (95th percentile ${f2(nul.p95, 2)}), which is what noise and the extra freedom alone produce. ` + (J3.above_null ? "The ratio exceeds the null: the families pull the dials in different directions by more than that." : "By the rule fixed in advance the ratio does not exceed the null, so the data do not show that the families conflict beyond what is expected; what keeps the codes apart is the families that are structural by themselves.") + `</p>`);
  if (zs.length > 2) para.push(`<p><b>Redshift.</b> The retuned distance is ${zs.map(x => `${f2(x.d, 1)} at z = ${x.z} (${x.n} outputs)`).join(", ")}` + (rise ? ", increasing with redshift; at higher redshift fewer and only more massive bins have enough galaxies in the 25 Mpc/h boxes, so the trend is a statement about those bins" : "") + `.</p>`);
  para.push(`<p><b>What tells these codes apart.</b> The observables that separate the two codes are those no retuning removes: here ${list(str.map(r => nm(r.f)))}` + (unr.length ? `, and with less margin ${list(unr.map(r => nm(r.f)))}` : "") + `.` + (calib.length ? ` The conventional calibration targets do not.` : "") + ` The <a href="retune.html">Retune</a> page evaluates the emulators behind these distances in the browser, so any dial setting can be tried against every observable at once.</p>`);
  para.push(`<p><b>What this is not.</b> A statement about two simulation codes at CAMELS resolution and in Subfind subhaloes, not about the Universe: no comparison with observations enters, and an observable that retuning cannot reconcile between two codes is not thereby a better or worse test of either.</p>`);
  out.jrReading = para.join("\n");
  // ---- validations and sensitivity
  const V = R.validations;
  const row = (a, b, c, ok) => `<tr><td>${a}</td><td>${b}</td><td class="nw">${c}</td><td>${ok === null ? "n/a" : ok ? "yes" : "no"}</td></tr>`;
  out.jrValRows = [
    row("V1 emulator cross-validation error over seed noise, share of outputs at most 1.5", `${f2(V.V1.IllustrisTNG["fraction_below_1.5"])} (IllustrisTNG), ${f2(V.V1.SIMBA["fraction_below_1.5"])} (SIMBA)`, "≥ 0.8 each", V.V1.passed),
    row("V2 negative control: the halo mass function is reachable", V.V2.summary ? `${V.V2.verdict} (between ${f2(V.V2.summary.between.p50)}, controls ≤ ${f2(V.V2.summary.control.p95)})` : "not evaluated", "removable", V.V2.passed),
    row("V3 catalogue SFR density minus the star formation log's, median (dex); z = 0.95 and 2.15 (z = 0 is an average over 0 &lt; z &lt; 0.2 and is reported only)", V.V3 ? ["IllustrisTNG", "SIMBA"].map(su => `${su}: ` + Object.values(V.V3[su]).map(x => `z = ${x.z}: ${f2(x.median_difference_dex, 3).replace("-0.000", "0.000")}`).join(", ")).join("; ") : "not evaluated", "|·| ≤ 0.1", V.V3 ? V.V3.passed : null),
    row("V4 stellar mass in subhaloes over the mass formed (median)", V.V4 ? `${f2(V.V4.IllustrisTNG.median_ratio, 3)} and ${f2(V.V4.SIMBA.median_ratio, 3)}` : "not evaluated", "0.45 – 0.75", V.V4 ? V.V4.passed : null),
    row("V5 distance with 4 and 8 random starts", `${f2(V.V5.D_starts_low, 3)} and ${f2(V.V5.D_starts_high, 3)} (${f2(100 * V.V5.relative_change, 1)} %)`, "< 5 %", V.V5.passed)].join("");
  const SENS = { S1_degree2: "Polynomial degree 2 for all outputs", S1_degree3: "Polynomial degree 3 for all outputs", "S2_kernel0.35": "Narrower cosmology weighting (0.35)", "S2_kernel0.8": "Wider cosmology weighting (0.8)",
    S3_no_emulator_error: "Noise scale without the emulators' error", "S4_floor0.01": "Noise floor 0.01", "S4_floor0.05": "Noise floor 0.05", S5_margin2: "Margin 2 instead of 1", "S6_z0_z0.95_only": "Only z = 0 and 0.95",
    S7a_no_bhocc: "Without black hole occupation", S7b_no_bhocc_no_bhms: "Without black hole occupation and mass", S10_no_rho: "Without the stellar mass and SFR densities", S8_no_two_lowest_mass_bins: "Without the two lowest stellar-mass bins of every block" };
  out.jrSensRows = Object.entries(R.sensitivity || {}).map(([k, x]) => `<tr><td>${esc(SENS[k] || k)}</td><td class="n">${f2(x.D)}</td><td>${esc(x.verdict || "")}</td></tr>`).join("");
  out.jrDev = (R.deviations || []).length ? R.deviations.map(d => `<li>${esc(d)}</li>`).join("") : "<li>none</li>";
  out.jrElig = `${R.meta.n_outputs_eligible} of ${R.meta.n_outputs_total} outputs are eligible, in ${R.meta.n_blocks} blocks`;
  out.jrNoise = `median seed noise ${f2(R.noise.IllustrisTNG.median_seed_noise, 3)} (IllustrisTNG) and ${f2(R.noise.SIMBA.median_seed_noise, 3)} (SIMBA)`;
  out.jrD = f2(A.D, 2); out.jrDfid = f2(A.D_fiducial, 2); out.jrVerdict = SA.verdict;
  out.jrNote = `<p class="mono" style="font-size:12.5px">joint distance ${f2(A.D)}<br>at the fiducial parameters ${f2(A.D_fiducial)}<br>same code, uncorrected ≤ ${f2((R.J3 && SA.control_raw ? SA.control_raw.p95 : SA.control.p95))}<br>margin 1</p>`;
  return out;
}
