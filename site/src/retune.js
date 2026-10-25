/* The dials page: two feedback models, four dials each. Emulators of the CAMELS galaxy-population summaries (polynomials in the four astrophysical coordinates at the fiducial cosmology) are evaluated in the browser;
   gaps are in the units of the all-at-once study (docs/PROTOCOL-joint-reachability.md): 1 = the standard deviation of the difference between one run of each code. Nothing here is fitted in advance: the buttons search the dials in the page. */
(async function () {
  "use strict";
  const root = document.getElementById("retune");
  if (!root) return;
  const CODES = ["IllustrisTNG", "SIMBA"], SHORT = { IllustrisTNG: "TNG", SIMBA: "SIMBA" }, COL = { IllustrisTNG: "var(--c-illustristng)", SIMBA: "var(--c-simba)" };
  let D;
  try { D = root.dataset.src === "embedded" ? JSON.parse(document.getElementById("rt-data").textContent) : await (await fetch(root.dataset.src)).json(); } catch (e) { root.textContent = "The emulator file could not be loaded."; return; }
  if (D.pending) { root.replaceChildren(Object.assign(document.createElement("p"), { className: "dim", textContent: "The emulators are published when the joint-reachability study has run (protocol committed, analysis pending)." })); return; }
  const PLAIN = { ASN1: "Supernova wind strength", AAGN1: "Black hole feedback strength", ASN2: "Supernova wind speed", AAGN2: "Black hole jet speed" };
  const FRIENDLY = { gsmf: "how many galaxies there are of each mass", qf: "how many have stopped forming stars", sfms: "how fast the star-forming ones make stars", bhms: "how heavy the central black holes are", bhocc: "which galaxies have a central black hole at all",
    mzr: "how metal-rich the gas is", zstar: "how metal-rich the stars are", size: "how big the galaxies are", fgas: "how much gas they still hold", shmr: "how much of each halo has turned into stars", rho: "the total stars and star formation in the box", hmf: "how many halos there are of each mass (barely touched by feedback)" };
  /* what usually drives each property, in one sentence; hedged because the dials of the two codes are not the same physical thing */
  const PHYS = { gsmf: "Stronger winds and black hole feedback usually remove gas before it forms stars, which lowers the number of massive galaxies most.", qf: "Black hole feedback is what usually switches star formation off in massive galaxies, so its strength moves this the most.",
    sfms: "How fast a galaxy makes stars depends on how much gas it keeps, which winds and black hole feedback both control.", bhms: "Black holes grow from the gas that reaches the centre; stronger feedback in either code limits it.",
    bhocc: "Whether a galaxy has a black hole at all is mostly set by the rule that plants the first black holes, not by the feedback dials, which is why almost no dial setting changes it.",
    mzr: "Winds carry metals out of galaxies, so the metal content depends on how much is lost and on the yields each code assumes, which no dial changes.", zstar: "Stars inherit the metals of the gas they formed from, so this follows the gas metallicity with a delay.",
    size: "Winds and feedback change how much gas settles into a disc and how far it spreads, which sets the stellar half-mass radius.", fgas: "Feedback ejects or heats gas; the gas that stays is what is left in the galaxy.", shmr: "How efficiently a halo turns its gas into stars is the net effect of cooling against feedback.",
    rho: "The total stars and star formation in the box add up what all galaxies do, so they move with every dial.", hmf: "Halo masses are set mostly by gravity, which is why this is a control." };
  const VERD = { structural: "stays apart at every dial setting", removable: "can be closed", unresolved: "borderline" };
  const NO = D.outputs.length, SCALE = Float64Array.from(D.scale), FAMS = Object.keys(D.families);
  const JOINT = FAMS.filter(f => D.families[f].joint), LINE = JOINT.filter(f => D.families[f].kind === "line");
  const el = (t, a = {}, ...kids) => { const e = document.createElementNS(a.ns || "http://www.w3.org/1999/xhtml", t); for (const [k, v] of Object.entries(a)) if (k !== "ns") (k.startsWith("on") ? e.addEventListener(k.slice(2), v) : e.setAttribute(k, v)); for (const c of kids.flat()) e.append(c); return e; };
  const svgEl = (t, a = {}, ...kids) => el(t, { ns: "http://www.w3.org/2000/svg", ...a }, ...kids);
  const f2 = (v, d = 2) => (Number.isFinite(v) ? v.toFixed(d) : "–");
  const REDUCED = (() => { try { return matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; } })();
  const ANIM = REDUCED || navigator.webdriver ? 0 : 450;
  /* ---- emulators */
  const EM = {};
  for (const c of CODES) { const q = D.codes[c]; EM[c] = { terms: q.terms, coef: q.coef.map(r => Float64Array.from(r.map(v => (v === null ? NaN : v)))) }; }
  function basis(terms, a) { const t = new Float64Array(terms.length); for (let k = 0; k < terms.length; k++) { let v = 1; for (const j of terms[k]) v *= a[j]; t[k] = v; } return t; }
  function predict(code, a, idx) {
    const { terms, coef } = EM[code], t = basis(terms, a), n = idx ? idx.length : NO, y = new Float64Array(n);
    for (let k = 0; k < terms.length; k++) { const row = coef[k], tk = t[k]; if (tk === 0) continue; if (idx) for (let i = 0; i < n; i++) y[i] += tk * row[idx[i]]; else for (let i = 0; i < n; i++) y[i] += tk * row[i]; }
    return y;
  }
  root.__rt = { predict: (code, a) => Array.from(predict(code, a)) }; // read by scripts/test-parity.mjs: the page's own evaluation of the emulators
  /* ---- sets of outputs with the study's weights: every block the same total weight, mean weight 1 */
  const blockKeys = Object.keys(D.blocks);
  function prep(keys) {
    const idx = [], w = [];
    for (const k of keys) { const o = D.blocks[k]; for (const i of o) { idx.push(i); w.push(1 / o.length); } }
    const m = w.reduce((s, v) => s + v, 0) / w.length;
    return { idx: Int32Array.from(idx), w2: Float64Array.from(w.map((v, i) => v / m / (SCALE[idx[i]] ** 2))), keys };
  }
  const STUCK = JOINT.filter(f => D.analysis && D.analysis.splits["fam:" + f] && D.analysis.splits["fam:" + f].verdict === "structural");
  const SETS = { all: prep(blockKeys.filter(k => k.split("|")[0] !== "hmf")) };
  SETS.matchable = prep(blockKeys.filter(k => { const f = k.split("|")[0]; return f !== "hmf" && !STUCK.includes(f); }));
  for (const f of FAMS) SETS[f] = prep(blockKeys.filter(k => k.split("|")[0] === f));
  function dist(yA, yB, set) { let s = 0; const n = set.idx.length; for (let i = 0; i < n; i++) { const d = yA[i] - yB[i]; s += set.w2[i] * d * d; } return Math.sqrt(s / n); }
  const state = { a: { IllustrisTNG: [0, 0, 0, 0], SIMBA: [0, 0, 0, 0] }, snap: D.snapshots[0].id, overlays: true, controls: false, explain: false, matchSet: JOINT.includes("gsmf") ? "gsmf" : "all", hold: "", story: null, user: null, k: "" };
  function fullDist(set, a = state.a) { return dist(predict("IllustrisTNG", a.IllustrisTNG, set.idx), predict("SIMBA", a.SIMBA, set.idx), set); }
  /* ---- search: projected gradient descent with backtracking from the current point, the default point and random starts */
  function descend(f, dims, base, nstarts = 14, seed = 12345) {
    let rs = seed; const rnd = () => { rs = (rs * 1664525 + 1013904223) >>> 0; return rs / 4294967296; };
    let best = { f: Infinity, a: base };
    const starts = [base.slice(), base.map((v, i) => (dims.includes(i) ? 0 : v))];
    for (let s = 0; s < nstarts; s++) starts.push(base.map((v, i) => (dims.includes(i) ? 2 * rnd() - 1 : v)));
    for (const a0 of starts) {
      const a = a0.slice(); let fa = f(a), step = 0.5;
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
  const flat = () => [...state.a.IllustrisTNG, ...state.a.SIMBA];
  /* match one code to the other (or both), optionally keeping one property as it is */
  function optimise(free, set) {
    const dims = free.flatMap((fr, c) => (fr ? [0, 1, 2, 3].map(j => 4 * c + j) : []));
    const hold = state.hold && SETS[state.hold] ? { set: SETS[state.hold], y0: { IllustrisTNG: predict("IllustrisTNG", state.a.IllustrisTNG, SETS[state.hold].idx), SIMBA: predict("SIMBA", state.a.SIMBA, SETS[state.hold].idx) } } : null;
    const f = a8 => {
      const aT = a8.slice(0, 4), aS = a8.slice(4);
      let v = dist(predict("IllustrisTNG", aT, set.idx), predict("SIMBA", aS, set.idx), set) ** 2;
      if (hold) { if (free[0]) v += 20 * dist(predict("IllustrisTNG", aT, hold.set.idx), hold.y0.IllustrisTNG, hold.set) ** 2; if (free[1]) v += 20 * dist(predict("SIMBA", aS, hold.set.idx), hold.y0.SIMBA, hold.set) ** 2; }
      return v;
    };
    return descend(f, dims, flat());
  }
  /* find the dials of one code that best reproduce a target on some outputs */
  function fitCode(code, tset) {
    const c = CODES.indexOf(code), dims = [0, 1, 2, 3].map(j => 4 * c + j);
    const f = a8 => dist(predict(code, a8.slice(4 * c, 4 * c + 4), tset.idx), tset.y, tset) ** 2;
    const a = descend(f, dims, flat());
    return { a: a.slice(4 * c, 4 * c + 4), gap: Math.sqrt(f(a)) };
  }
  /* a curve on the bins of one property at one epoch; null if fewer than three bins fall inside it */
  function targetFrom(pts, fam, snap) {
    const ids = D.blocks[fam + "|" + snap], meta = D.families[fam];
    if (!ids || pts.length < 2) return null;
    const P = pts.slice().sort((p, q) => p.x - q.x), idx = [], y = [];
    for (const i of ids) {
      const x = meta.x_centres[D.outputs[i].b];
      if (x < P[0].x || x > P[P.length - 1].x) continue;
      let k = 1; while (k < P.length - 1 && P[k].x < x) k++;
      const a = P[k - 1], b = P[k], t = b.x === a.x ? 0 : (x - a.x) / (b.x - a.x);
      idx.push(i); y.push(a.y + t * (b.y - a.y));
    }
    if (idx.length < 3) return null;
    return { idx: Int32Array.from(idx), y: Float64Array.from(y), w2: Float64Array.from(idx.map(i => 1 / (SCALE[i] ** 2))), n: idx.length };
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
  /* how strongly each dial moves the outputs, in noise units, over its whole range with the others at their defaults */
  const SENS = {};
  { const jidx = SETS.all.idx; for (const c of CODES) SENS[c] = [0, 1, 2, 3].map(j => { const up = [0, 0, 0, 0], dn = [0, 0, 0, 0]; up[j] = 1; dn[j] = -1; const yu = predict(c, up, jidx), yd = predict(c, dn, jidx); let s = 0; for (let i = 0; i < jidx.length; i++) { const d = (yu[i] - yd[i]) / SCALE[jidx[i]]; s += d * d; } return Math.sqrt(s / jidx.length); }); }
  const SMAX = Math.max(...CODES.flatMap(c => SENS[c]));
  /* ---- words */
  const nameOf = f => D.family_names[f].toLowerCase().replace(" at fixed m*", "");
  const unitOf = f => ((D.native && D.native[f] && D.native[f].unit) || "dex") === "dex" ? "dex" : "";
  const list = a => (a.length < 2 ? a.join("") : a.slice(0, -1).join(", ") + " and " + a[a.length - 1]);
  const mult = c => D.params.map((p, j) => `${PLAIN[p.id].toLowerCase()} ×${f2(Math.pow(p.base, state.a[c][j]), 2)}`).join(", ");
  const gaps = (a = state.a) => JOINT.map(f => ({ f, d: fullDist(SETS[f], a) }));
  const agreeAt = snap => { const rows = JOINT.filter(f => D.blocks[f + "|" + snap]).map(f => { const ids = D.blocks[f + "|" + snap], set = { idx: Int32Array.from(ids), w2: Float64Array.from(ids.map(i => 1 / (SCALE[i] ** 2))) }; return fullDist(set); }); return { n: rows.length, ok: rows.filter(d => d < D.margin).length }; };
  function sideEffects(prev, skip) {
    const out = [];
    for (const c of CODES) {
      if (prev[c].every((v, j) => Math.abs(v - state.a[c][j]) < 1e-6)) continue;
      for (const f of JOINT) {
        if (f === skip) continue;
        const idx = SETS[f].idx, y0 = predict(c, prev[c], idx), y1 = predict(c, state.a[c], idx);
        let s = 0; for (let i = 0; i < idx.length; i++) s += (y1[i] - y0[i]) ** 2;
        const rms = Math.sqrt(s / idx.length), nu = (D.native && D.native[f] && D.native[f].noise_unit) || 1;
        out.push({ f, c, rms, rel: rms / nu });
      }
    }
    return out.sort((x, y) => y.rel - x.rel).slice(0, 3);
  }
  function story(kind, before, prev, head) {
    const after = gaps(), ok = a => a.filter(x => x.d < D.margin).map(x => x.f), nb = ok(before), na = ok(after);
    const closed = na.filter(f => !nb.includes(f)), lost = nb.filter(f => !na.includes(f)), stuck = after.filter(x => x.d >= D.margin).sort((a, b) => b.d - a.d);
    const only = state.matchSet === "all" ? "" : state.matchSet === "matchable" ? ` (leaving aside ${list(STUCK.map(nameOf))}, which stay apart at every dial setting)` : ` (matching only ${nameOf(state.matchSet)})`;
    const hold = state.hold ? ` while keeping ${nameOf(state.hold)} as it was` : "";
    const h = head || (kind === "S" ? `To look as much like TNG as it can${only}${hold}, SIMBA's dials went to: ${mult("SIMBA")}.` : kind === "T" ? `To look as much like SIMBA as it can${only}${hold}, TNG's dials went to: ${mult("IllustrisTNG")}.` : `Closest the two can get${only}${hold}: TNG with ${mult("IllustrisTNG")}; SIMBA with ${mult("SIMBA")}.`);
    const one = !head && JOINT.includes(state.matchSet) ? `The gap on ${nameOf(state.matchSet)} went from ${f2(before.find(x => x.f === state.matchSet).d, 1)} to ${f2(after.find(x => x.f === state.matchSet).d, 1)}. ` : "";
    const skip = head ? (state.user && state.user.fam) : state.matchSet, se = prev ? sideEffects(prev, skip) : [];
    const side = se.length ? ` Biggest side effects: ${list(se.map(x => `${nameOf(x.f)} in ${SHORT[x.c]} moved by ${f2(x.rms, 2)}${unitOf(x.f) ? " " + unitOf(x.f) : ""}`))}.` : "";
    return [h, one + `Overall they now agree on ${na.length} of ${JOINT.length} things (before: ${nb.length}).` + (closed.length ? ` Brought into line: ${list(closed.map(nameOf))}.` : "") + (lost.length ? ` Knocked out of agreement by the change: ${list(lost.map(nameOf))}.` : "") + side,
      stuck.length ? `Still apart: ${list(stuck.slice(0, 4).map(x => `${nameOf(x.f)} (${f2(x.d, 1)}× run-to-run noise)`))}${stuck.length > 4 ? " and " + (stuck.length - 4) + " more" : ""}.` : "Nothing is left apart."];
  }
  /* ---- interface */
  const ui = {};
  const live = el("p", { class: "sr", "aria-live": "polite", id: "rt-live" });
  const header = el("div", { class: "rt-head" }), stick = el("div", { class: "rt-stick" });
  const legend = el("p", { class: "rt-legend" }, el("i", { style: `background:${COL.IllustrisTNG}` }), "IllustrisTNG ", el("i", { style: `background:${COL.SIMBA}` }), "SIMBA: line, the emulated mean at the dials; narrow band, plus or minus the seed-to-seed scatter of one 25 Mpc/h box; dotted lines, the emulator's own error; wide pale band, the range reached by moving all four dials (5th to 95th percentile); grey lines, published curves of the dataset with different definitions (hover for the source and definitions); black dashed line, your curve.");
  const ctrl = el("div", { class: "rt-ctrl" });
  const panels = el("div", { class: "rt-panels", role: "group", "aria-label": "Observables" });
  const table = el("div", { class: "rt-table" });
  root.replaceChildren(el("div", { class: "rt-wrap" }, stick, el("div", { class: "rt-grid" }, ctrl, el("div", { class: "rt-main" }, header, legend, panels, table, live))));
  for (const c of CODES) {
    const box = el("fieldset", { class: "rt-code" }, el("legend", {}, el("i", { style: `background:${COL[c]}` }), SHORT[c] === "TNG" ? "IllustrisTNG" : "SIMBA"));
    D.params.forEach((p, j) => {
      const out = el("output", { id: `o-${c}-${j}`, "aria-live": "off" }), id = `s-${c}-${j}`, sensText = `Moving this dial across its whole range changes the galaxy properties by ${f2(SENS[c][j], 1)} noise units (rms over all properties)`, sensBar = el("span", { class: "rt-sens", title: sensText, role: "img", "aria-label": sensText }, el("i", { style: `width:${Math.max(2, Math.round(100 * SENS[c][j] / SMAX))}%` }));
      const input = el("input", { type: "range", id, min: -1, max: 1, step: 0.05, value: 0, "aria-describedby": `d-${c}-${j}`, oninput: e => { state.a[c][j] = +e.target.value; state.story = null; state.k = ""; update(); } });
      ui[`${c}${j}`] = { input, out, box: null };
      const dial = el("div", { class: "rt-dial" }, el("label", { for: id }, el("span", { class: "sr" }, (SHORT[c] === "TNG" ? "IllustrisTNG" : "SIMBA") + ": "), PLAIN[p.id] || p.label, el("span", { class: "rt-fac" }, out)), input, el("small", { id: `d-${c}-${j}` }, p.label + " · " + p[SHORT[c] === "TNG" ? "TNG" : "SIMBA"] + " · " + p.range), el("span", { class: "rt-edge", "aria-hidden": "true" }, "near the edge of the simulated range: less certain"), sensBar);
      ui[`${c}${j}`].box = dial;
      box.append(dial);
    });
    ctrl.append(box);
  }
  const snapSel = el("select", { id: "rt-snap", "aria-label": "Redshift", onchange: e => { state.snap = e.target.value; refreshObs(); update(); } }, D.snapshots.map(s => el("option", { value: s.id }, "z = " + f2(s.z))));
  const matchSel = el("select", { id: "rt-match", "aria-label": "Match on (the property to match)", onchange: e => { state.matchSet = e.target.value; update(); } }, JOINT.map(f => el("option", { value: f }, D.family_names[f])), (STUCK.length ? [el("option", { value: "matchable" }, "everything that can be matched, together")] : []), el("option", { value: "all" }, "everything, even what cannot be matched"));
  matchSel.value = state.matchSet;
  const holdSel = el("select", { id: "rt-hold", "aria-label": "While keeping (the property to hold as it is)", onchange: e => { state.hold = e.target.value; update(); } }, el("option", { value: "" }, "nothing in particular"), JOINT.map(f => el("option", { value: f }, D.family_names[f])));
  const ovl = el("input", { type: "checkbox", id: "rt-ov", checked: "", onchange: e => { state.overlays = e.target.checked; update(); } });
  const ctl = el("input", { type: "checkbox", id: "rt-ctl", onchange: e => { state.controls = e.target.checked; update(); } });
  const expl = el("input", { type: "checkbox", id: "rt-expl", onchange: e => { state.explain = e.target.checked; update(); } });
  const toast = t => { live.textContent = ""; setTimeout(() => { live.textContent = t; }, 30); };
  /* what a listener hears: the story of a search when it is new (what moved, what came into line, what was given up), otherwise the one-sentence summary when it changes; the same text is never written twice */
  let lastBig = "", storySaid = null;
  const say = t => { live.textContent = ""; setTimeout(() => { live.textContent = t; }, 30); };
  let tweening = 0;
  /* move the dials to a new setting, smoothly unless the visitor prefers reduced motion; the story is written once the dials have arrived */
  function setA(aT, aS, then) {
    const from = { IllustrisTNG: state.a.IllustrisTNG.slice(), SIMBA: state.a.SIMBA.slice() }, to = { IllustrisTNG: aT ? aT.slice() : from.IllustrisTNG, SIMBA: aS ? aS.slice() : from.SIMBA };
    const done = () => { state.a = { IllustrisTNG: to.IllustrisTNG, SIMBA: to.SIMBA }; if (then) then(); update(); };
    if (!ANIM) { done(); return; }
    const t0 = performance.now(), id = ++tweening;
    const tick = now => { if (id !== tweening) return; const t = Math.min(1, (now - t0) / ANIM), e = t * t * (3 - 2 * t); for (const c of CODES) state.a[c] = from[c].map((v, j) => v + (to[c][j] - v) * e); if (t < 1) { sync(); render(); requestAnimationFrame(tick); } else done(); };
    requestAnimationFrame(tick);
  }
  const run = (kind, free) => { const before = gaps(), prev = { IllustrisTNG: state.a.IllustrisTNG.slice(), SIMBA: state.a.SIMBA.slice() }; state.k = kind; const a = optimise(free, SETS[state.matchSet]); setA(free[0] ? a.slice(0, 4) : null, free[1] ? a.slice(4) : null, () => { state.story = story(kind, before, prev); }); };
  const btn = (t, fn, cls = "", extra = {}) => el("button", { type: "button", class: "rt-btn " + cls, onclick: fn, ...extra }, t);
  const actions = el("div", { class: "rt-actions" },
    el("label", { for: "rt-snap" }, "Redshift"), snapSel,
    el("label", { for: "rt-match" }, "Match on"), matchSel,
    el("label", { for: "rt-hold" }, "While keeping"), holdSel,
    btn("Make SIMBA look like TNG", () => run("S", [false, true])),
    btn("Make TNG look like SIMBA", () => run("T", [true, false])),
    btn("Closest the two can get", () => run("B", [true, true])),
    btn("Reset", () => { tweening++; state.story = null; state.k = ""; state.hold = ""; holdSel.value = ""; state.matchSet = JOINT.includes("gsmf") ? "gsmf" : "all"; matchSel.value = state.matchSet; state.user = null; setA([0, 0, 0, 0], [0, 0, 0, 0]); }, "plain"),
    el("div", { class: "rt-presets", role: "group", "aria-label": "Starting points" },
      btn("Same dials in both", () => { state.story = null; state.k = ""; setA(null, state.a.IllustrisTNG.slice()); }, "plain"),
      btn("Weak feedback", () => { state.story = null; state.k = ""; setA([-0.8, -0.8, -0.8, -0.8], [-0.8, -0.8, -0.8, -0.8]); }, "plain"),
      btn("Strong feedback", () => { state.story = null; state.k = ""; setA([0.8, 0.8, 0.8, 0.8], [0.8, 0.8, 0.8, 0.8]); }, "plain"),
      btn("Show me a surprise", () => surprise(), "plain")),
    btn("Play through redshifts", () => playZ(), "plain", { id: "rt-play" }),
    el("label", { class: "rt-chk" }, ovl, "Published curves"), el("label", { class: "rt-chk" }, ctl, "Halo mass function (control)"), el("label", { class: "rt-chk" }, expl, "Explain each panel"));
  ctrl.append(actions);
  let player = 0;
  function playZ() {
    const b = document.getElementById("rt-play");
    if (player) { clearInterval(player); player = 0; b.textContent = "Play through redshifts"; return; }
    if (REDUCED) { toast("Step through the redshifts with the buttons above the charts (animation is off)."); return; }
    b.textContent = "Stop"; let k = D.snapshots.findIndex(s => s.id === state.snap);
    player = setInterval(() => { k = (k + 1) % D.snapshots.length; state.snap = D.snapshots[k].id; snapSel.value = state.snap; refreshObs(); update(); if (k === D.snapshots.length - 1) { clearInterval(player); player = 0; b.textContent = "Play through redshifts"; } }, 2200);
  }
  /* a random setting of TNG; SIMBA is tuned to match the mass function: what breaks? */
  function surprise() {
    const prev = { IllustrisTNG: state.a.IllustrisTNG.slice(), SIMBA: state.a.SIMBA.slice() }, before = gaps();
    const aT = [0, 0, 0, 0].map(() => +(1.6 * Math.random() - 0.8).toFixed(2));
    state.a.IllustrisTNG = aT; const keep = state.matchSet, keepHold = state.hold; state.matchSet = JOINT.includes("gsmf") ? "gsmf" : "all"; state.hold = "";
    const a = optimise([false, true], SETS[state.matchSet]);
    state.a.IllustrisTNG = prev.IllustrisTNG; matchSel.value = state.matchSet; state.k = "S";
    setA(aT, a.slice(4), () => { state.story = story("S", before, prev, `TNG was set to a random point (${mult("IllustrisTNG")}). SIMBA's dials were then tuned to reproduce its ${nameOf(state.matchSet)}: ${mult("SIMBA")}.`); });
    state.hold = keepHold; void keep;
  }
  /* ---- fit the dials to a curve: your own, or a published observation */
  const fitFam = el("select", { id: "rt-fitfam", "aria-label": "Property your curve describes" }, LINE.map(f => el("option", { value: f }, D.family_names[f])));
  const fitText = el("textarea", { id: "rt-fittext", rows: "4", placeholder: "x,y per line: x is log10 stellar mass (or halo mass), y is log10 of the property as shown in the panel", "aria-label": "Your curve" });
  const fitLin = el("input", { type: "checkbox", id: "rt-fitlin" });
  const fitMsg = el("p", { class: "rt-fitmsg", id: "rt-fitmsg", "aria-live": "polite" });
  const obsSel = el("select", { id: "rt-obs", "aria-label": "or an observed curve (choose a published observation)" });
  function parseCurve(text, lin) {
    const pts = [];
    for (const l of String(text || "").replace(/^﻿/, "").split(/\r?\n/)) { const t = l.trim(); if (!t || t.startsWith("#")) continue; const c = (t.includes(";") ? t.split(";").map(v => v.trim().replace(",", ".")) : t.split(/[,\t ]+/)).map(Number); if (Number.isFinite(c[0]) && Number.isFinite(c[1])) pts.push({ x: c[0], y: lin ? (c[1] > 0 ? Math.log10(c[1]) : NaN) : c[1] }); }
    return pts.filter(p => Number.isFinite(p.y)).sort((a, b) => a.x - b.x);
  }
  function fitTo(label, tset, fam, pts, kind) {
    const before = gaps(), prev = { IllustrisTNG: state.a.IllustrisTNG.slice(), SIMBA: state.a.SIMBA.slice() }, T = fitCode("IllustrisTNG", tset), S = fitCode("SIMBA", tset);
    state.user = { fam, snap: state.snap, pts, name: label }; state.k = "";
    setA(T.a, S.a, () => { state.story = story("B", before, prev, `${kind === "obs" ? "Tuned to the observed curve" : "Tuned to your curve"} (${label}; ${tset.n} bins of ${nameOf(fam)} at z = ${f2(D.snapshots.find(s => s.id === state.snap).z)}). IllustrisTNG gets within a gap of ${f2(T.gap, 1)} with ${mult("IllustrisTNG")}; SIMBA within ${f2(S.gap, 1)} with ${mult("SIMBA")}.${kind === "obs" ? " The observed curve is defined differently from the simulated one (aperture, IMF, population), so a good fit is not a verdict on either code." : ""}`); });
  }
  const fitBtn = btn("Find the dials for my curve", () => {
    const pts = parseCurve(fitText.value, fitLin.checked), fam = fitFam.value, t = targetFrom(pts, fam, state.snap);
    if (!t) { fitMsg.textContent = `Need at least three bins of ${nameOf(fam)} inside your curve at this redshift: x must be log10 ${fam === "shmr" ? "halo" : "stellar"} mass, roughly ${f2(Math.min(...D.families[fam].x_centres), 1)} to ${f2(Math.max(...D.families[fam].x_centres), 1)}.`; return; }
    fitMsg.textContent = ""; fitTo("your curve", t, fam, pts, "own");
  });
  function refreshObs() {
    const fam = fitFam.value, os = (D.overlays || []).filter(o => o.family === fam && o.snapshot === state.snap && o.kind === "observation");
    obsSel.replaceChildren(...(os.length ? os.map((o, i) => el("option", { value: i }, `${o.label} (z = ${f2(o.z, 1)})`)) : [el("option", { value: "" }, "no observed curve for this property at this redshift")]));
    obsGo.disabled = !os.length;
  }
  const obsGo = btn("Tune both to this observation", () => {
    const fam = fitFam.value, os = (D.overlays || []).filter(o => o.family === fam && o.snapshot === state.snap && o.kind === "observation"), o = os[+obsSel.value];
    if (!o) return;
    const pts = o.x.map((x, i) => ({ x, y: o.y[i] })).filter(p => Number.isFinite(p.y)), t = targetFrom(pts, fam, state.snap);
    if (!t) { fitMsg.textContent = "That observed curve covers fewer than three of the simulated mass bins."; return; }
    fitMsg.textContent = ""; fitTo(o.label, t, fam, pts, "obs");
  });
  fitFam.addEventListener("change", () => { refreshObs(); });
  const fit = el("details", { class: "rt-fit" }, el("summary", {}, "Fit the dials to a curve of your own, or to an observation"),
    el("p", { class: "rt-hint" }, "Pick the property, paste a curve (or choose a published observation) and each universe's dials are searched for the setting that reproduces it at the redshift chosen above. Then look at what else changes."),
    el("label", { for: "rt-fitfam" }, "Property"), fitFam, el("label", { for: "rt-fittext" }, "Your curve"), fitText, el("label", { class: "rt-chk" }, fitLin, "y values are linear, not log10"), fitBtn,
    el("label", { for: "rt-obs" }, "or an observed curve"), obsSel, obsGo, fitMsg);
  ctrl.append(fit);
  const outputs = el("div", { class: "rt-actions rt-out" }, btn("Copy link to this setting", () => copyLink(), "plain"), btn("Download the numbers (CSV)", () => csv(), "plain"), btn("Download the figure (PNG)", () => png(), "plain"));
  ctrl.append(outputs);
  function copyLink() {
    const u = location.href.split("#")[0] + "#" + hashString();
    const done = () => toast("Link copied");
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(u).then(done, () => { prompt("Copy this link", u); });
    else { const t = el("textarea", { style: "position:fixed;opacity:0" }); document.body.append(t); t.value = u; t.select(); try { document.execCommand("copy"); done(); } catch (e) { /* ignore */ } t.remove(); }
  }
  function hashString() { return CODES.map(c => state.a[c].map(v => v.toFixed(2)).join(",")).join(";") + "@" + state.snap + "&m=" + state.matchSet + (state.k ? "&k=" + state.k : "") + (state.hold ? "&h=" + state.hold : ""); }
  function csv() {
    const rows = [["property", "redshift", "x", "TNG", "SIMBA", "difference_TNG_minus_SIMBA"].join(",")];
    for (const s of D.snapshots) for (const f of JOINT) {
      const ids = D.blocks[f + "|" + s.id]; if (!ids) continue; const meta = D.families[f], yT = predict("IllustrisTNG", state.a.IllustrisTNG, Int32Array.from(ids)), yS = predict("SIMBA", state.a.SIMBA, Int32Array.from(ids));
      ids.forEach((i, k) => rows.push([f, s.z, meta.kind === "points" ? meta.labels[D.outputs[i].b] : meta.x_centres[D.outputs[i].b], yT[k].toFixed(4), yS[k].toFixed(4), (yT[k] - yS[k]).toFixed(4)].join(",")));
    }
    const head = `# sim-highline v${D.version} dials page. IllustrisTNG dials (x0.25..x4 and x0.5..x2 as coordinates -1..1): ${state.a.IllustrisTNG.map(v => v.toFixed(2)).join(" ")}; SIMBA: ${state.a.SIMBA.map(v => v.toFixed(2)).join(" ")}. Emulated means; units are those of each property (log10 or fraction).\n`;
    const a = el("a", { href: URL.createObjectURL(new Blob([head + rows.join("\n") + "\n"], { type: "text/csv" })), download: "sim-highline-dials.csv" }); document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function png() {
    const figs = [...panels.querySelectorAll("figure.rt-panel")], cols = Math.min(3, Math.max(1, figs.length)), cw = 330, ch = 232, W = cols * cw + 24, rowsN = Math.ceil(figs.length / cols), H = rowsN * ch + 110;
    const P = ["fill", "stroke", "stroke-width", "stroke-dasharray", "opacity", "fill-opacity", "stroke-opacity", "font-family", "font-size", "font-weight", "text-anchor", "display"];
    const bg = getComputedStyle(document.body).backgroundColor, fg = getComputedStyle(document.body).color;
    let g = "";
    figs.forEach((fig, n) => {
      const s = fig.querySelector("svg"), c = s.cloneNode(true), a = s.querySelectorAll("*"), b = c.querySelectorAll("*");
      a.forEach((e, i) => { const cs = getComputedStyle(e); let st = ""; for (const p of P) st += `${p}:${cs.getPropertyValue(p)};`; if (b[i]) b[i].setAttribute("style", st); });
      c.setAttribute("x", 12 + (n % cols) * cw); c.setAttribute("y", 88 + Math.floor(n / cols) * ch + 22); c.setAttribute("width", cw); c.setAttribute("height", ch - 22);
      g += `<text x="${12 + (n % cols) * cw}" y="${88 + Math.floor(n / cols) * ch + 14}" font-family="Georgia,serif" font-size="13" fill="${fg}">${fig.querySelector("b").textContent} (${fig.querySelector(".rt-d").textContent})</text>` + new XMLSerializer().serializeToString(c);
    });
    const esc = t => String(t).replace(/[&<>]/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[m]));
    const big = stick.querySelector(".rt-big").textContent;
    const words = big.match(/.{1,92}(\s|$)/g) || [big];
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><rect width="${W}" height="${H}" fill="${bg}"/><text x="12" y="26" font-family="Georgia,serif" font-size="18" fill="${fg}">${esc(words[0])}</text><text x="12" y="48" font-family="Georgia,serif" font-size="18" fill="${fg}">${esc(words[1] || "")}</text><text x="12" y="70" font-family="monospace" font-size="11" fill="${fg}">TNG: ${esc(mult("IllustrisTNG"))}</text><text x="12" y="84" font-family="monospace" font-size="11" fill="${fg}">SIMBA: ${esc(mult("SIMBA"))}</text>${g}</svg>`;
    const img = new Image(); img.onload = () => { const cv = document.createElement("canvas"); cv.width = W * 2; cv.height = H * 2; const x = cv.getContext("2d"); x.scale(2, 2); x.drawImage(img, 0, 0); cv.toBlob(bl => { const a = el("a", { href: URL.createObjectURL(bl), download: "sim-highline-dials.png" }); document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500); }, "image/png"); };
    img.onerror = () => toast("The figure could not be rendered in this browser"); img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
  }
  function sync() {
    for (const c of CODES) D.params.forEach((p, j) => { const x = state.a[c][j], u = ui[`${c}${j}`]; const t = "×" + f2(Math.pow(p.base, x), 2); if (+u.input.value !== x) u.input.value = x; if (u.out.textContent !== t) u.out.textContent = t; if (u.input.getAttribute("aria-valuetext") !== t) u.input.setAttribute("aria-valuetext", t); u.box.classList.toggle("edge", Math.abs(x) >= 0.9); });
    try { history.replaceState(null, "", "#" + hashString()); } catch (e) { /* no history in some embeds */ }
  }
  /* ---- panels */
  const W = 330, H = 200, L = 46, R = 10, T = 8, B = 34;
  function nice(lo, hi) { const span = hi - lo || 1, raw = span / 4, p = Math.pow(10, Math.floor(Math.log10(raw))), m = raw / p, st = (m < 1.5 ? 1 : m < 3.5 ? 2 : m < 7.5 ? 5 : 10) * p, a = Math.floor(lo / st) * st, b = Math.ceil(hi / st) * st, t = []; for (let v = a; v <= b + 1e-9; v += st) t.push(+v.toFixed(6)); return { a, b, t }; }
  function panel(fam) {
    const key = fam + "|" + state.snap, ids = D.blocks[key];
    if (!ids) return null;
    const meta = D.families[fam], iarr = Int32Array.from(ids), yT = predict("IllustrisTNG", state.a.IllustrisTNG, iarr), yS = predict("SIMBA", state.a.SIMBA, iarr);
    const xs = ids.map(i => meta.x_centres[D.outputs[i].b]);
    const ovs = state.overlays ? (D.overlays || []).filter(o => o.family === fam && o.snapshot === state.snap) : [];
    const ys = [...yT, ...yS, ...ids.flatMap(i => [REACH.IllustrisTNG.lo[i], REACH.IllustrisTNG.hi[i], REACH.SIMBA.lo[i], REACH.SIMBA.hi[i]])];
    const xr = meta.kind === "points" ? [-0.5, ids.length - 0.5] : [Math.min(...xs) - 0.12, Math.max(...xs) + 0.12];
    const finite = ys.filter(Number.isFinite), yr = nice(Math.min(...finite), Math.max(...finite));
    const sx = x => L + (x - xr[0]) / (xr[1] - xr[0]) * (W - L - R), sy = y => H - B - (y - yr.a) / (yr.b - yr.a) * (H - T - B);
    const path = (px, py) => px.map((x, i) => (Number.isFinite(py[i]) ? `${i && Number.isFinite(py[i - 1]) ? "L" : "M"}${sx(x).toFixed(1)},${sy(py[i]).toFixed(1)}` : "")).join("");
    const band = (px, lo, hi) => { const a = px.map((x, i) => `${sx(x).toFixed(1)},${sy(hi[i]).toFixed(1)}`), b = px.map((x, i) => `${sx(x).toFixed(1)},${sy(lo[i]).toFixed(1)}`).reverse(); return `M${a.join("L")}L${b.join("L")}Z`; };
    const unit = (D.native && D.native[fam] && D.native[fam].unit) === "fraction" ? "" : " dex";
    const g = svgEl("svg", { viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `${meta.title} at z = ${f2(D.snapshots.find(s => s.id === state.snap).z)}: IllustrisTNG and SIMBA emulated curves` });
    const axes = svgEl("g", { class: "axis" });
    for (const t of yr.t) axes.append(svgEl("line", { x1: L, x2: W - R, y1: sy(t), y2: sy(t) }), svgEl("text", { x: L - 6, y: sy(t) + 4, "text-anchor": "end" }, String(+t.toPrecision(3))));
    const xt = meta.kind === "points" ? ids.map((_, i) => i) : nice(xr[0], xr[1]).t.filter(t => t >= xr[0] && t <= xr[1]);
    xt.forEach(t => axes.append(svgEl("text", { x: sx(t), y: H - B + 15, "text-anchor": "middle" }, meta.kind === "points" ? meta.labels[t] : String(t))));
    axes.append(svgEl("text", { class: "al", x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle" }, meta.x));
    g.append(axes);
    if (meta.kind === "points") {
      ids.forEach((i, k) => { for (const c of CODES) g.append(svgEl("line", { x1: sx(k), x2: sx(k), y1: sy(REACH[c].lo[i]), y2: sy(REACH[c].hi[i]), stroke: COL[c], "stroke-width": 7, opacity: 0.18, transform: `translate(${c === "SIMBA" ? 6 : -6} 0)` })); });
      ids.forEach((i, k) => { g.append(svgEl("circle", { cx: sx(k) - 6, cy: sy(yT[k]), r: 4.5, fill: COL.IllustrisTNG }, svgEl("title", {}, `${meta.labels[k]}: TNG ${f2(yT[k], 2)}, SIMBA ${f2(yS[k], 2)}`)), svgEl("circle", { cx: sx(k) + 6, cy: sy(yS[k]), r: 4.5, fill: COL.SIMBA }, svgEl("title", {}, `${meta.labels[k]}: TNG ${f2(yT[k], 2)}, SIMBA ${f2(yS[k], 2)}`))); });
    } else {
      const cid = `rtc-${fam}-${state.snap}`, gov = svgEl("g", { "clip-path": `url(#${cid})` });
      g.append(svgEl("defs", {}, svgEl("clipPath", { id: cid }, svgEl("rect", { x: L, y: T, width: W - L - R, height: H - T - B })))), g.append(gov);
      for (const o of ovs) gov.append(svgEl("path", { d: path(o.x.filter((x, k) => Number.isFinite(o.y[k])), o.y.filter(Number.isFinite)), class: "ov " + o.kind, "stroke-dasharray": o.tier === "digitized-figure" ? "2 3" : "", opacity: o.kind === "observation" ? 0.85 : 0.45 }, svgEl("title", {}, `${o.label} (${o.source}, ${o.kind}, ${o.tier}); x: ${o.xDef}; y: ${o.yDef}; mass: ${o.mass || "unspecified"}`)));
      if (state.user && state.user.fam === fam && state.user.snap === state.snap) gov.append(svgEl("path", { d: path(state.user.pts.map(p => p.x), state.user.pts.map(p => p.y)), fill: "none", stroke: "var(--ink)", "stroke-width": 2, "stroke-dasharray": "6 4" }, svgEl("title", {}, state.user.name)));
      for (const c of CODES) g.append(svgEl("path", { d: band(xs, ids.map(i => REACH[c].lo[i]), ids.map(i => REACH[c].hi[i])), fill: COL[c], opacity: 0.1 }));
      for (const [c, y] of [["IllustrisTNG", yT], ["SIMBA", yS]]) {
        g.append(svgEl("path", { d: band(xs, ids.map((i, k) => y[k] - D.codes[c].seed[i]), ids.map((i, k) => y[k] + D.codes[c].seed[i])), fill: COL[c], opacity: 0.22 }), svgEl("path", { d: path(xs, Array.from(y)), fill: "none", stroke: COL[c], "stroke-width": 2.2 }));
        for (const sgn of [-1, 1]) g.append(svgEl("path", { d: path(xs, ids.map((i, k) => y[k] + sgn * D.codes[c].emulator_error[i])), fill: "none", stroke: COL[c], "stroke-width": 0.9, "stroke-dasharray": "1 3" }));
      }
      const bw = (W - L - R) / Math.max(ids.length, 1);
      ids.forEach((i, k) => g.append(svgEl("rect", { x: sx(xs[k]) - bw / 2, y: T, width: bw, height: H - T - B, fill: "transparent" }, svgEl("title", {}, `${meta.x} ${xs[k]}: TNG ${f2(yT[k], 3)}, SIMBA ${f2(yS[k], 3)}, difference ${f2(yT[k] - yS[k], 3)}`))));
    }
    const set = { idx: iarr, w2: Float64Array.from(ids.map(i => 1 / (SCALE[i] ** 2))) }, d = dist(yT, yS, set);
    let ss = 0; for (let k = 0; k < yT.length; k++) ss += (yT[k] - yS[k]) ** 2; const nat = Math.sqrt(ss / yT.length);
    /* the text alternative says what the curves do, not only what the panel is: the values at the ends of the range (or at each category) and how far apart the two codes are */
    const last = yT.length - 1, zNow = f2(D.snapshots.find(s => s.id === state.snap).z);
    g.setAttribute("aria-label", `${meta.title} at z = ${zNow}: ` + (meta.kind === "points"
      ? ids.map((_, k) => `${meta.labels[k]}: IllustrisTNG ${f2(yT[k], 2)}, SIMBA ${f2(yS[k], 2)}`).join("; ")
      : `over ${meta.x} from ${f2(xs[0], 2)} to ${f2(xs[last], 2)}, IllustrisTNG goes from ${f2(yT[0], 2)} to ${f2(yT[last], 2)} and SIMBA from ${f2(yS[0], 2)} to ${f2(yS[last], 2)}`)
      + `. Average difference between the codes ${f2(nat, 2)}${unit}; gap ${f2(d)}.`);
    const nOut = meta.kind === "points" ? 0 : ovs.filter(o => !o.x.some((x, k) => x >= xr[0] && x <= xr[1] && o.y[k] >= yr.a && o.y[k] <= yr.b)).length;
    return el("figure", { class: "rt-panel" + (d >= D.margin ? " far" : ""), "data-family": fam }, el("figcaption", { class: "rt-cap" }, el("b", {}, meta.title), nOut ? el("span", { class: "rt-n" }, `${nOut} published outside the frame`) : "", el("span", { class: "rt-d", title: "gap between the two curves; 1 = as far apart as two runs of the same code that differ only in their random seed. After it: the rms difference in the property's own units." }, `gap ${f2(d)} · ${f2(nat, 2)}${unit}`)), el("p", { class: "rt-sub" }, FRIENDLY[fam] || "", state.explain && PHYS[fam] ? el("span", { class: "rt-phys" }, " " + PHYS[fam]) : ""), g);
  }
  function render() {
    panels.replaceChildren(...FAMS.filter(f => (f !== "hmf" || state.controls)).map(panel).filter(Boolean));
    const A = D.analysis, rows = [];
    for (const f of JOINT) {
      const dcur = fullDist(SETS[f]), an = A && A.point["fam:" + f], sp = A && A.splits["fam:" + f];
      rows.push(el("tr", {}, el("th", { scope: "row" }, D.family_names[f]), el("td", { class: "n" }, f2(dcur)), el("td", { class: "n" }, an ? f2(an.D_fiducial) : "–"), el("td", { class: "n" }, an ? f2(an.D_corrected != null ? an.D_corrected : an.D) : "–"), el("td", {}, sp ? (VERD[sp.verdict] || sp.verdict) : "–")));
    }
    const dall = fullDist(SETS.all), an = A && A.point.all, sp = A && A.splits.all;
    rows.push(el("tr", { class: "tot" }, el("th", { scope: "row" }, "All of them at once"), el("td", { class: "n" }, f2(dall)), el("td", { class: "n" }, an ? f2(an.D_fiducial) : "–"), el("td", { class: "n" }, an ? f2(an.D_corrected != null ? an.D_corrected : an.D) : "–"), el("td", {}, sp ? (VERD[sp.verdict] || sp.verdict) : "–")));
    table.setAttribute("tabindex", "0"); table.setAttribute("role", "region"); table.setAttribute("aria-label", "Distance per observable (scrolls sideways on narrow screens)");
    table.replaceChildren(el("table", {}, el("caption", {}, "Gap between the two codes at the dials above, over all redshifts. 1 = as far apart as two runs of the same code that differ only in random seed; below 1 they agree. The last two columns are the registered study’s result."),
      el("thead", {}, el("tr", {}, ["Property", "now", "default dials", "best any dials", "closable by retuning?"].map(t => el("th", { scope: "col" }, t)))), el("tbody", {}, rows)));
    const gs = gaps(), agree = gs.filter(x => x.d < D.margin), worst = gs.filter(x => x.d >= D.margin).sort((x, y) => y.d - x.d).slice(0, 3);
    const big = `At these dials the two universes agree on ${agree.length} of ${JOINT.length} things about galaxies.` + (worst.length ? ` They are furthest apart on ${list(worst.map(x => nameOf(x.f)))}.` : " Nothing is out of line.");
    const strip = el("div", { class: "rt-strip", role: "group", "aria-label": "Agreement at each redshift" }, el("span", { class: "rt-striplab" }, "Agreement by redshift:"), D.snapshots.map(s => { const a = agreeAt(s.id); return el("button", { type: "button", class: "rt-z" + (s.id === state.snap ? " on" : ""), "data-z": s.id, "aria-label": `z = ${f2(s.z)}: ${a.ok} of ${a.n} properties agree`, "aria-pressed": s.id === state.snap ? "true" : "false", onclick: () => { state.snap = s.id; snapSel.value = s.id; refreshObs(); update(); } }, `z = ${f2(s.z)}`, el("b", {}, ` ${a.ok}/${a.n}`)); }));
    /* on a narrow screen the panels are far below the dials: keep a small live copy of the property being matched in the pinned headline */
    const miniSrc = panels.querySelector(`figure.rt-panel[data-family="${JOINT.includes(state.matchSet) ? state.matchSet : "gsmf"}"]`) || panels.querySelector("figure.rt-panel"), mini = miniSrc ? miniSrc.cloneNode(true) : null;
    if (mini) { mini.className = "rt-mini"; mini.setAttribute("aria-hidden", "true"); mini.removeAttribute("data-family"); mini.removeAttribute("id"); for (const e of mini.querySelectorAll("[id]")) e.setAttribute("id", e.id + "-m"); for (const e of mini.querySelectorAll("[clip-path]")) e.setAttribute("clip-path", e.getAttribute("clip-path").replace(/\)$/, "-m)")); for (const x of mini.querySelectorAll(".rt-expl, .rt-hold")) x.remove(); }
    const hadFocus = document.activeElement && stick.contains(document.activeElement) ? document.activeElement.getAttribute("data-z") : null;
    stick.replaceChildren(el("p", { class: "rt-big" }, big), strip, ...(mini ? [mini] : []));
    if (hadFocus) { const again = stick.querySelector(`.rt-z[data-z="${hadFocus}"]`); if (again) again.focus({ preventScroll: true }); } /* the strip is rebuilt on every change: keep the keyboard where it was */
    header.replaceChildren(
      el("p", { class: "rt-sum" }, `Joint gap ${f2(dall)} (1 = as far apart as two runs of one code that differ only in random seed)${an ? `; the smallest the study found with every dial free: ${f2(an.D_corrected != null ? an.D_corrected : an.D)}; with the default dials: ${f2(an.D_fiducial)}` : ""}.`),
      state.story ? el("div", { class: "rt-story" }, state.story.map(t => el("p", {}, t))) : "");
    if (!tweening || !ANIM) { if (state.story && state.story !== storySaid) { storySaid = state.story; lastBig = big; say(state.story.join(" ")); } else if (big !== lastBig) { lastBig = big; say(big); } }
  }
  function update() { sync(); render(); }
  /* url state: #aT;aS@snap&m=property&k=S|T|B&h=property. A shared link that carries k replays the story from the default dials. */
  try {
    const parts = decodeURIComponent(location.hash.slice(1)).split("&"), m = parts[0].match(/^([^;@]+);([^@]+)@(\d+)$/), q = Object.fromEntries(parts.slice(1).map(s => s.split("=")));
    if (m) {
      const [aT, aS] = [m[1], m[2]].map(s => s.split(",").map(Number));
      if (aT.length === 4 && aS.length === 4 && [...aT, ...aS].every(Number.isFinite)) { state.a.IllustrisTNG = aT.map(v => Math.max(-1, Math.min(1, v))); state.a.SIMBA = aS.map(v => Math.max(-1, Math.min(1, v))); }
      if (D.snapshots.some(s => s.id === m[3])) { state.snap = m[3]; snapSel.value = m[3]; }
      if (q.m && (JOINT.includes(q.m) || q.m === "all" || q.m === "matchable")) { state.matchSet = q.m; matchSel.value = q.m; }
      if (q.h && JOINT.includes(q.h)) { state.hold = q.h; holdSel.value = q.h; }
      if (q.k && "STB".includes(q.k)) { state.k = q.k; const now = { IllustrisTNG: state.a.IllustrisTNG.slice(), SIMBA: state.a.SIMBA.slice() }; state.a = { IllustrisTNG: [0, 0, 0, 0], SIMBA: [0, 0, 0, 0] }; const before = gaps(); state.a = now; state.story = story(q.k, before, { IllustrisTNG: [0, 0, 0, 0], SIMBA: [0, 0, 0, 0] }); }
    }
  } catch (e) { /* ignore a malformed hash */ }
  /* ---- a five-step tour: each step lights one part of the page and says what it is for */
  {
    const go = document.getElementById("rt-tourbtn"); if (!go) { refreshObs(); update(); return; }
    go.hidden = false;
    const STEPS = [
      { sel: ".rt-code", t: "These are the four dials of one universe, in plain words with the code's own name underneath. Drag one: the centre is the setting CAMELS treats as normal, the ends are a factor of two to four weaker and stronger." },
      { sel: ".rt-big", t: `This sentence is the answer so far: on how many of the ${JOINT.length} galaxy properties the two universes agree at these settings, and which are furthest apart. It updates as you turn the dials.` },
      { sel: ".rt-panel", t: "Each panel is one property. Orange is IllustrisTNG, blue is SIMBA, the pale band is how far a universe moves when you turn all four dials. A shaded panel means the two are further apart than two runs of the same universe would be." },
      { sel: ".rt-actions", t: "These buttons search the dials for you. Make SIMBA look like TNG matches the property you choose under Match on, then tells you what that did to everything else. Show me a surprise picks a setting with a striking trade-off." },
      { sel: ".rt-fit", t: "Or bring your own curve, or pick a published observation, and see which dial settings of each universe reproduce it, and what that does to every other property." }
    ];
    let k = -1, spot = null; const card = el("div", { class: "rt-tour", role: "dialog", "aria-label": "Tour of the dials page", "aria-describedby": "rt-tour-t", hidden: "" });
    const txt = el("p", { class: "rt-tour-t", id: "rt-tour-t", "aria-live": "polite" }), cnt = el("span", { class: "rt-tour-n" });
    const back = btn("Back", () => show(k - 1), "rt-tour-b"), next = btn("Next", () => show(k + 1), "rt-tour-b"), close = btn("Close", () => end(), "rt-tour-b");
    card.append(txt, el("div", { class: "rt-tour-r" }, cnt, back, next, close)); document.body.append(card);
    function end() { if (spot) spot.classList.remove("rt-spot"); spot = null; card.hidden = true; k = -1; go.focus(); }
    function show(i) {
      if (i < 0) return; if (i >= STEPS.length) return end();
      k = i; const st = STEPS[i], target = root.querySelector(st.sel) || document.querySelector(st.sel);
      if (spot) spot.classList.remove("rt-spot"); spot = target || null;
      if (spot) { spot.classList.add("rt-spot"); spot.scrollIntoView({ block: "center", behavior: REDUCED ? "auto" : "smooth" }); }
      txt.textContent = st.t; cnt.textContent = `${i + 1} of ${STEPS.length}`; back.disabled = i === 0; next.textContent = i === STEPS.length - 1 ? "Done" : "Next"; card.hidden = false; next.focus({ preventScroll: true });
    }
    go.addEventListener("click", () => { const g = go.closest("details"); if (g) g.open = false; show(0); });
    card.addEventListener("keydown", e => { if (e.key === "Escape") end(); });
  }
  refreshObs();
  update();
})();
