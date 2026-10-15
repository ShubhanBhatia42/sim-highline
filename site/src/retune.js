/* Retune: two feedback models, four dials each. Emulators of the CAMELS galaxy-population summaries (polynomials in the four astrophysical coordinates at the fiducial cosmology) are evaluated in the browser;
   distances are in the units of the joint-reachability study (docs/PROTOCOL-joint-reachability.md): 1 = the standard deviation of the difference between one run of each code. Nothing here is fitted in the page. */
(async function () {
  "use strict";
  const root = document.getElementById("retune");
  if (!root) return;
  const CODES = ["IllustrisTNG", "SIMBA"], SHORT = { IllustrisTNG: "TNG", SIMBA: "SIMBA" }, COL = { IllustrisTNG: "var(--c-illustristng)", SIMBA: "var(--c-simba)" };
  let D;
  try { D = await (await fetch(root.dataset.src)).json(); } catch (e) { root.textContent = "The emulator file could not be loaded."; return; }
  if (D.pending) { root.replaceChildren(Object.assign(document.createElement("p"), { className: "dim", textContent: "The emulators are published when the joint-reachability study has run (protocol committed, analysis pending)." })); return; }
  const NO = D.outputs.length, SCALE = Float64Array.from(D.scale), FAMS = Object.keys(D.families);
  const JOINT = FAMS.filter(f => D.families[f].joint);
  const el = (t, a = {}, ...kids) => { const e = document.createElementNS(a.ns || "http://www.w3.org/1999/xhtml", t); for (const [k, v] of Object.entries(a)) if (k !== "ns") (k.startsWith("on") ? e.addEventListener(k.slice(2), v) : e.setAttribute(k, v)); for (const c of kids.flat()) e.append(c); return e; };
  const svgEl = (t, a = {}, ...kids) => el(t, { ns: "http://www.w3.org/2000/svg", ...a }, ...kids);
  const f2 = (v, d = 2) => (Number.isFinite(v) ? v.toFixed(d) : "–");
  /* ---- emulators */
  const EM = {};
  for (const c of CODES) {
    const q = D.codes[c];
    EM[c] = { terms: q.terms, coef: q.coef.map(r => Float64Array.from(r.map(v => (v === null ? NaN : v)))) };
  }
  function basis(terms, a) { const t = new Float64Array(terms.length); for (let k = 0; k < terms.length; k++) { let v = 1; for (const j of terms[k]) v *= a[j]; t[k] = v; } return t; }
  function predict(code, a, idx) {
    const { terms, coef } = EM[code], t = basis(terms, a), n = idx ? idx.length : NO, y = new Float64Array(n);
    for (let k = 0; k < terms.length; k++) { const row = coef[k], tk = t[k]; if (tk === 0) continue; if (idx) for (let i = 0; i < n; i++) y[i] += tk * row[idx[i]]; else for (let i = 0; i < n; i++) y[i] += tk * row[i]; }
    return y;
  }
  /* ---- sets of outputs with the study's weights: every block the same total weight, mean weight 1 */
  const blockKeys = Object.keys(D.blocks);
  function prep(keys) {
    const idx = [], w = [];
    for (const k of keys) { const o = D.blocks[k]; for (const i of o) { idx.push(i); w.push(1 / o.length); } }
    const m = w.reduce((s, v) => s + v, 0) / w.length;
    return { idx: Int32Array.from(idx), w2: Float64Array.from(w.map((v, i) => v / m / (SCALE[idx[i]] ** 2))), keys };
  }
  const SETS = { all: prep(blockKeys.filter(k => k.split("|")[0] !== "hmf")) };
  for (const f of FAMS) SETS[f] = prep(blockKeys.filter(k => k.split("|")[0] === f));
  const snapKeys = s => blockKeys.filter(k => k.endsWith("|" + s) && k.split("|")[0] !== "hmf");
  function dist(yT, yS, set) { let s = 0; const n = set.idx.length; for (let i = 0; i < n; i++) { const d = yT[i] - yS[i]; s += set.w2[i] * d * d; } return Math.sqrt(s / n); }
  const state = { a: { IllustrisTNG: [0, 0, 0, 0], SIMBA: [0, 0, 0, 0] }, snap: D.snapshots[0].id, overlays: true, controls: false, matchSet: "all" };
  function fullDist(set) { return dist(predict("IllustrisTNG", state.a.IllustrisTNG, set.idx), predict("SIMBA", state.a.SIMBA, set.idx), set); }
  /* ---- search: projected gradient descent with backtracking from the current point and random starts */
  function optimise(free, set, nstarts = 14) {
    const f = a8 => { const aT = a8.slice(0, 4), aS = a8.slice(4); return dist(predict("IllustrisTNG", aT, set.idx), predict("SIMBA", aS, set.idx), set) ** 2; };
    const dims = free.flatMap((fr, c) => (fr ? [0, 1, 2, 3].map(j => 4 * c + j) : []));
    const base = [...state.a.IllustrisTNG, ...state.a.SIMBA];
    let rs = 12345; const rnd = () => { rs = (rs * 1664525 + 1013904223) >>> 0; return rs / 4294967296; };
    let best = { f: Infinity, a: base };
    const starts = [base.slice(), base.map(() => 0)];
    for (let s = 0; s < nstarts; s++) starts.push(base.map((v, i) => (dims.includes(i) ? 2 * rnd() - 1 : v)));
    for (const a0 of starts) {
      const a = a0.slice(); for (let i = 0; i < 8; i++) if (!dims.includes(i)) a[i] = base[i];
      let fa = f(a), step = 0.5;
      for (let it = 0; it < 120; it++) {
        const g = new Float64Array(8);
        for (const i of dims) { const h = 1e-4, p = a.slice(), m = a.slice(); p[i] += h; m[i] -= h; g[i] = (f(p) - f(m)) / (2 * h); }
        let ok = false;
        for (let b = 0; b < 25; b++) {
          const c = a.map((v, i) => (dims.includes(i) ? Math.max(-1, Math.min(1, v - step * g[i])) : v)), fc = f(c);
          if (fc < fa - 1e-12) { for (let i = 0; i < 8; i++) a[i] = c[i]; fa = fc; step *= 1.5; ok = true; break; }
          step *= 0.5;
        }
        if (!ok) break;
      }
      if (fa < best.f) best = { f: fa, a: a.slice() };
    }
    return best.a;
  }
  /* ---- reachable ranges: 5th to 95th percentile of every output over the whole parameter box */
  const REACH = {};
  { let rs = 777; const rnd = () => { rs = (rs * 1664525 + 1013904223) >>> 0; return rs / 4294967296; }; const N = 1200;
    for (const c of CODES) {
      const Y = new Float64Array(N * NO);
      for (let n = 0; n < N; n++) Y.set(predict(c, [0, 1, 2, 3].map(() => 2 * rnd() - 1)), n * NO);
      const lo = new Float64Array(NO), hi = new Float64Array(NO), col = new Float64Array(N);
      for (let o = 0; o < NO; o++) { for (let n = 0; n < N; n++) col[n] = Y[n * NO + o]; const s = Array.from(col).sort((x, y) => x - y); lo[o] = s[Math.floor(0.05 * N)]; hi[o] = s[Math.floor(0.95 * N)]; }
      REACH[c] = { lo, hi };
    } }
  /* ---- interface */
  const ui = {};
  const header = el("div", { class: "rt-head" });
  const legend = el("p", { class: "rt-legend" }, el("i", { style: `background:${COL.IllustrisTNG}` }), "IllustrisTNG ", el("i", { style: `background:${COL.SIMBA}` }), "SIMBA: ", "line, the emulated mean at the dials; narrow band, plus or minus the seed-to-seed scatter of one 25 Mpc/h box; wide pale band, the range reached by moving all four dials (5th to 95th percentile); grey lines, published curves of the dataset with different definitions (hover for the source and definitions).");
  const ctrl = el("div", { class: "rt-ctrl" });
  const panels = el("div", { class: "rt-panels", role: "group", "aria-label": "Observables" });
  const table = el("div", { class: "rt-table" });
  root.replaceChildren(el("div", { class: "rt-grid" }, ctrl, el("div", { class: "rt-main" }, header, legend, panels, table)));
  for (const c of CODES) {
    const box = el("fieldset", { class: "rt-code" }, el("legend", {}, el("i", { style: `background:${COL[c]}` }), c === "IllustrisTNG" ? "IllustrisTNG" : "SIMBA"));
    D.params.forEach((p, j) => {
      const out = el("output", { id: `o-${c}-${j}` }), id = `s-${c}-${j}`;
      const input = el("input", { type: "range", id, min: -1, max: 1, step: 0.01, value: 0, "aria-describedby": `d-${c}-${j}`, oninput: e => { state.a[c][j] = +e.target.value; update(); } });
      ui[`${c}${j}`] = { input, out };
      box.append(el("div", { class: "rt-dial" }, el("label", { for: id }, p.label, el("span", { class: "rt-fac" }, out)), input, el("small", { id: `d-${c}-${j}` }, p[c === "IllustrisTNG" ? "TNG" : "SIMBA"] + " · " + p.range)));
    });
    ctrl.append(box);
  }
  const snapSel = el("select", { id: "rt-snap", "aria-label": "Redshift", onchange: e => { state.snap = e.target.value; update(); } }, D.snapshots.map(s => el("option", { value: s.id }, "z = " + f2(s.z))));
  const matchSel = el("select", { id: "rt-match", "aria-label": "Observables to match", onchange: e => { state.matchSet = e.target.value; update(); } }, el("option", { value: "all" }, "all observables"), JOINT.map(f => el("option", { value: f }, D.family_names[f])));
  const ovl = el("input", { type: "checkbox", id: "rt-ov", checked: "", onchange: e => { state.overlays = e.target.checked; update(); } });
  const ctl = el("input", { type: "checkbox", id: "rt-ctl", onchange: e => { state.controls = e.target.checked; update(); } });
  const setA = (aT, aS) => { if (aT) state.a.IllustrisTNG = aT.slice(); if (aS) state.a.SIMBA = aS.slice(); sync(); update(); };
  const btn = (t, fn, cls = "") => el("button", { type: "button", class: "rt-btn " + cls, onclick: fn }, t);
  const actions = el("div", { class: "rt-actions" },
    el("label", { for: "rt-snap" }, "Redshift"), snapSel,
    el("label", { for: "rt-match" }, "Match"), matchSel,
    btn("Retune SIMBA to the TNG curve", () => { const a = optimise([false, true], SETS[state.matchSet]); setA(null, a.slice(4)); }),
    btn("Retune TNG to the SIMBA curve", () => { const a = optimise([true, false], SETS[state.matchSet]); setA(a.slice(0, 4), null); }),
    btn("Best match, both free", () => { const a = optimise([true, true], SETS[state.matchSet]); setA(a.slice(0, 4), a.slice(4)); }),
    btn("Fiducial", () => setA([0, 0, 0, 0], [0, 0, 0, 0]), "plain"),
    el("label", { class: "rt-chk" }, ovl, "Published curves"), el("label", { class: "rt-chk" }, ctl, "Halo mass function (control)"));
  ctrl.append(actions);
  function sync() {
    for (const c of CODES) D.params.forEach((p, j) => { const x = state.a[c][j], u = ui[`${c}${j}`]; u.input.value = x; u.out.textContent = "×" + f2(Math.pow(p.base, x), 2); });
    try { history.replaceState(null, "", "#" + CODES.map(c => state.a[c].map(v => v.toFixed(2)).join(",")).join(";") + "@" + state.snap); } catch (e) { /* no history in some embeds */ }
  }
  /* ---- panels */
  const W = 330, H = 200, L = 46, R = 10, T = 8, B = 34;
  function nice(lo, hi) { const span = hi - lo || 1, raw = span / 4, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p, st = (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p, a = Math.floor(lo / st) * st, b = Math.ceil(hi / st) * st, t = []; for (let v = a; v <= b + 1e-9; v += st) t.push(+v.toFixed(6)); return { a, b, t }; }
  function panel(fam) {
    const key = fam + "|" + state.snap, ids = D.blocks[key];
    if (!ids) return null;
    const meta = D.families[fam], yT = predict("IllustrisTNG", state.a.IllustrisTNG, Int32Array.from(ids)), yS = predict("SIMBA", state.a.SIMBA, Int32Array.from(ids));
    const xs = ids.map(i => meta.x_centres[D.outputs[i].b]);
    const ovs = state.overlays ? (D.overlays || []).filter(o => o.family === fam && o.snapshot === state.snap) : [];
    let ys = [...yT, ...yS, ...ids.flatMap(i => [REACH.IllustrisTNG.lo[i], REACH.IllustrisTNG.hi[i], REACH.SIMBA.lo[i], REACH.SIMBA.hi[i]])];
    const xr = meta.kind === "points" ? [-0.5, ids.length - 0.5] : [Math.min(...xs) - 0.12, Math.max(...xs) + 0.12];
    const finite = ys.filter(Number.isFinite), yr = nice(Math.min(...finite), Math.max(...finite));
    const sx = x => L + (x - xr[0]) / (xr[1] - xr[0]) * (W - L - R), sy = y => H - B - (y - yr.a) / (yr.b - yr.a) * (H - T - B);
    const path = (px, py) => px.map((x, i) => (Number.isFinite(py[i]) ? `${i && Number.isFinite(py[i - 1]) ? "L" : "M"}${sx(x).toFixed(1)},${sy(py[i]).toFixed(1)}` : "")).join("");
    const band = (px, lo, hi) => { const a = px.map((x, i) => `${sx(x).toFixed(1)},${sy(hi[i]).toFixed(1)}`), b = px.map((x, i) => `${sx(x).toFixed(1)},${sy(lo[i]).toFixed(1)}`).reverse(); return `M${a.join("L")}L${b.join("L")}Z`; };
    const g = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${meta.title} at z = ${f2(D.snapshots.find(s => s.id === state.snap).z)}: IllustrisTNG and SIMBA emulated curves` });
    const axes = svgEl("g", { class: "axis" });
    for (const t of yr.t) axes.append(svgEl("line", { x1: L, x2: W - R, y1: sy(t), y2: sy(t) }), svgEl("text", { x: L - 6, y: sy(t) + 4, "text-anchor": "end" }, String(+t.toPrecision(3))));
    const xt = meta.kind === "points" ? ids.map((_, i) => i) : nice(xr[0], xr[1]).t.filter(t => t >= xr[0] && t <= xr[1]);
    xt.forEach(t => axes.append(svgEl("text", { x: sx(t), y: H - B + 15, "text-anchor": "middle" }, meta.kind === "points" ? meta.labels[t] : String(t))));
    axes.append(svgEl("text", { class: "al", x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle" }, meta.x));
    g.append(axes);
    if (meta.kind === "points") {
      ids.forEach((i, k) => { for (const c of CODES) g.append(svgEl("line", { x1: sx(k), x2: sx(k), y1: sy(REACH[c].lo[i]), y2: sy(REACH[c].hi[i]), stroke: COL[c], "stroke-width": 7, opacity: 0.18, transform: `translate(${c === "SIMBA" ? 6 : -6} 0)` })); });
      ids.forEach((i, k) => { g.append(svgEl("circle", { cx: sx(k) - 6, cy: sy(yT[k]), r: 4.5, fill: COL.IllustrisTNG }), svgEl("circle", { cx: sx(k) + 6, cy: sy(yS[k]), r: 4.5, fill: COL.SIMBA })); });
    } else {
      const cid = `rtc-${fam}-${state.snap}`, gov = svgEl("g", { "clip-path": `url(#${cid})` });
      g.append(svgEl("defs", {}, svgEl("clipPath", { id: cid }, svgEl("rect", { x: L, y: T, width: W - L - R, height: H - T - B })))), g.append(gov);
      for (const o of ovs) gov.append(svgEl("path", { d: path(o.x.filter((x, k) => Number.isFinite(o.y[k])), o.y.filter(Number.isFinite)), class: "ov " + o.kind, "stroke-dasharray": o.tier === "digitized-figure" ? "2 3" : "", opacity: o.kind === "observation" ? 0.85 : 0.45 }, svgEl("title", {}, `${o.label} (${o.source}, ${o.kind}, ${o.tier}); x: ${o.xDef}; y: ${o.yDef}; mass: ${o.mass || "unspecified"}`)));
      for (const c of CODES) g.append(svgEl("path", { d: band(xs, ids.map(i => REACH[c].lo[i]), ids.map(i => REACH[c].hi[i])), fill: COL[c], opacity: 0.1 }));
      for (const [c, y] of [["IllustrisTNG", yT], ["SIMBA", yS]]) {
        g.append(svgEl("path", { d: band(xs, ids.map((i, k) => y[k] - D.codes[c].seed[i]), ids.map((i, k) => y[k] + D.codes[c].seed[i])), fill: COL[c], opacity: 0.22 }), svgEl("path", { d: path(xs, Array.from(y)), fill: "none", stroke: COL[c], "stroke-width": 2.2 }));
      }
    }
    const d = dist(yT, yS, { idx: Int32Array.from(ids), w2: Float64Array.from(ids.map(i => 1 / (SCALE[i] ** 2))) });
    const nOut = meta.kind === "points" ? 0 : ovs.filter(o => !o.x.some((x, k) => x >= xr[0] && x <= xr[1] && o.y[k] >= yr.a && o.y[k] <= yr.b)).length;
    return el("figure", { class: "rt-panel" + (d >= D.margin ? " far" : "") }, el("figcaption", { class: "rt-cap" }, el("b", {}, meta.title), nOut ? el("span", { class: "rt-n" }, `${nOut} published outside the frame`) : "", el("span", { class: "rt-d", title: "distance between the two curves in noise units; 1 = the standard deviation of the difference between one run of each code" }, "D = " + f2(d))), g);
  }
  function render() {
    panels.replaceChildren(...FAMS.filter(f => (f !== "hmf" || state.controls)).map(panel).filter(Boolean));
    const A = D.analysis, rows = [];
    for (const f of JOINT) {
      const dcur = fullDist(SETS[f]), an = A && A.point["fam:" + f], sp = A && A.splits["fam:" + f];
      rows.push(el("tr", {}, el("td", {}, D.family_names[f]), el("td", { class: "n" }, f2(dcur)), el("td", { class: "n" }, an ? f2(an.D_fiducial) : "–"), el("td", { class: "n" }, an ? f2(an.D_corrected != null ? an.D_corrected : an.D) : "–"), el("td", {}, sp ? sp.verdict : "–")));
    }
    const dall = fullDist(SETS.all), an = A && A.point.all, sp = A && A.splits.all;
    rows.push(el("tr", { class: "tot" }, el("td", {}, "All observables"), el("td", { class: "n" }, f2(dall)), el("td", { class: "n" }, an ? f2(an.D_fiducial) : "–"), el("td", { class: "n" }, an ? f2(an.D_corrected != null ? an.D_corrected : an.D) : "–"), el("td", {}, sp ? sp.verdict : "–")));
    table.setAttribute("tabindex", "0"); table.setAttribute("role", "region"); table.setAttribute("aria-label", "Distance per observable (scrolls sideways on narrow screens)");
    table.replaceChildren(el("table", {}, el("caption", {}, "Distance between the two codes, in noise units (1 = the standard deviation of the difference between one run of each), at the dials above and over all redshifts"),
      el("thead", {}, el("tr", {}, ["Observable", "now", "both at fiducial", "best reachable (study, corrected)", "verdict (study)"].map(t => el("th", { scope: "col" }, t)))), el("tbody", {}, rows)));
    header.replaceChildren(el("p", { class: "rt-sum", "aria-live": "polite" }, `Joint distance ${f2(dall)} noise units${an ? `; the study's minimum over both codes' dials is ${f2(an.D_corrected != null ? an.D_corrected : an.D)} (emulator error removed) (${sp ? sp.verdict : "–"}), and ${f2(an.D_fiducial)} at the fiducial parameters` : ""}.`));
  }
  function update() { sync(); render(); }
  /* url state: #aT;aS@snap */
  try { const h = decodeURIComponent(location.hash.slice(1)); const m = h.match(/^([^;@]+);([^@]+)@(\d+)$/); if (m) { const [aT, aS] = [m[1], m[2]].map(s => s.split(",").map(Number)); if (aT.length === 4 && aS.length === 4 && [...aT, ...aS].every(Number.isFinite)) { state.a.IllustrisTNG = aT.map(v => Math.max(-1, Math.min(1, v))); state.a.SIMBA = aS.map(v => Math.max(-1, Math.min(1, v))); } if (D.snapshots.some(s => s.id === m[3])) { state.snap = m[3]; snapSel.value = m[3]; } } } catch (e) { /* ignore a malformed hash */ }
  update();
})();
