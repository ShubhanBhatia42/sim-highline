// Tests of observer-lib.js (Gaussian mass scatter, mass offset, completeness, sSFR detection floor): closed forms and an independent quadrature, invariants, equality with the Python
// implementation on tests/fixtures/observer-fixture.json (written by scripts/test_observer.py), and a check that the battery fails if the convolution is a no-op.
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const LN10 = Math.LN10;
const deq = (a, b, m) => assert.equal(JSON.stringify(a), JSON.stringify(b), m);   // the library runs in its own realm, so compare by value
const file = fileURLToPath(new URL("../observer-lib.js", import.meta.url));
const ctx = { globalThis: {} };
vm.runInNewContext(await readFile(file, "utf8"), ctx, { filename: file });   // a filename, so coverage tools attribute the lines to observer-lib.js
const O = ctx.globalThis.SimHighlineObserver;
const cfile = fileURLToPath(new URL("../compare.js", import.meta.url)), efile = fileURLToPath(new URL("../export-lib.js", import.meta.url));
vm.runInNewContext(await readFile(cfile, "utf8"), ctx, { filename: cfile });      // export-lib.js reads compare.js's evaluator from the same context
vm.runInNewContext(await readFile(efile, "utf8"), ctx, { filename: efile });
const C = ctx.globalThis.SimHighlineCompare;

const arange = (a, b, s) => { const out = []; for (let i = 0; a + i * s <= b + 1e-9; i++) out.push(Math.round((a + i * s) * 1e6) / 1e6); return out; };
const ptsFrom = (f, xs, band) => xs.map(x => ({ x, y: f(x), ...(band ? { yLow: f(x) - band, yHigh: f(x) + band } : {}) }));
const schechterY = (x, alpha, xs, phi) => { const u = x - xs; return Math.log10(LN10 * phi * 10 ** ((alpha + 1) * u) * Math.exp(-(10 ** u))); };
const schechterN = (x, alpha, xs, phi) => { const u = x - xs; return u > 2.8 ? 0 : LN10 * phi * 10 ** ((alpha + 1) * u) * Math.exp(-(10 ** u)); };
const simpson = (f, a, b, n) => { const h = (b - a) / n; let s = f(a) + f(b); for (let i = 1; i < n; i++) s += f(a + i * h) * (i % 2 ? 4 : 2); return s * h / 3; };
const trapz = (ys, xs) => { let s = 0; for (let i = 1; i < xs.length; i++) s += 0.5 * (ys[i] + ys[i - 1]) * (xs[i] - xs[i - 1]); return s; };
const interpTable = (t, m) => O.interp1(t.x, t.sigma, m);

// the defining integral, by composite Simpson on the exact function (a different discretisation from the library's, and no interpolation of the input)
const convolveExact = (n, sigmaAt, x, width) => simpson(m => n(m) * Math.exp(-0.5 * ((x - m) / sigmaAt(m)) ** 2) / (sigmaAt(m) * Math.sqrt(2 * Math.PI)), x - width, x + width, 8000);

function checks(sp) {
  let n = 0;
  // 1a. power law: exact factor exp((beta sigma ln10)^2 / 2), edges included
  const beta = -1.4, sig = 0.3;
  const pl = ptsFrom(x => beta * x + 3, arange(8, 11, 0.25));
  const want = Math.log10(Math.exp(0.5 * (beta * sig * LN10) ** 2));
  assert(want > 0.2);
  sp(pl, sig).forEach((a, i) => assert(Math.abs(a.y - pl[i].y - want) < 1e-9, `power law at ${a.x}`));
  n++;
  // 1b. Gaussian mass function of width s, scatter sigma: Gaussian of width sqrt(s^2 + sigma^2), amplitude A s / sqrt(s^2 + sigma^2); tolerance 2e-4 dex = the linear-in-log interpolation at 0.01 dex spacing
  const c = 10.5, s = 0.45, A = 2e-3;
  const ln = ptsFrom(x => Math.log10(A * Math.exp(-0.5 * ((x - c) / s) ** 2)), arange(7.5, 13.5, 0.01));
  for (const sg of [0.1, 0.2, 0.3]) {
    const se = Math.hypot(s, sg);
    let worst = 0;
    for (const q of sp(ln, sg)) if (q.x >= 8.4 && q.x <= 12.6) worst = Math.max(worst, Math.abs(q.y - Math.log10(A * s / se * Math.exp(-0.5 * ((q.x - c) / se) ** 2))));
    assert(worst < 2e-4, `Gaussian mass function, sigma ${sg}: ${worst}`);
  }
  n++;
  // 1c. Schechter: asymptotic series where u = log(M/M*) <= -1, and the defining integral at every mass; tolerance 1e-3 dex (interpolation of the input)
  const alpha = -1.2, xs0 = 10.7, phi = 1e-3;
  const sc = ptsFrom(x => schechterY(x, alpha, xs0, phi), arange(7, 13, 0.01));
  for (const sg of [0.1, 0.2, 0.3]) {
    const b = alpha + 1, s2 = (sg * LN10) ** 2;
    for (const q of sp(sc, sg)) {
      if (q.x < 8.4 || q.x > 12) continue;
      const u = q.x - xs0;
      if (u <= -1) {
        let ser = 0, prev = Infinity, fact = 1;
        for (let k = 0; k < 60; k++) {
          if (k > 0) fact *= k;
          const term = (k % 2 ? -1 : 1) / fact * 10 ** ((b + k) * u) * Math.exp((b + k) ** 2 * s2 / 2);
          if (Math.abs(term) > prev) break;
          ser += term; prev = Math.abs(term);
        }
        ser *= LN10 * phi;
        assert(Math.abs(q.y - Math.log10(ser)) < 1e-3, `series sigma ${sg} x ${q.x}`);
      }
      const ref = convolveExact(m => schechterN(m, alpha, xs0, phi), () => sg, q.x, 9 * sg);
      assert(Math.abs(q.y - Math.log10(ref)) < 1e-3, `quadrature sigma ${sg} x ${q.x}: ${q.y} vs ${Math.log10(ref)}`);
    }
  }
  const o3 = sp(sc, 0.3);
  assert(o3.find(q => q.x === 11.5).y - sc.find(q => q.x === 11.5).y > 0.2, "the Eddington bias above the knee must exceed the interpolation tolerance");
  n++;
  // 1d. mass-dependent scatter against quadrature; a constant table equals the number
  const tab = { x: [8, 12], sigma: [0.4, 0.15] };
  const pl2 = ptsFrom(x => -1 * x + 2, arange(7, 13, 0.25));
  for (const q of sp(pl2, tab)) {
    if (q.x < 9 || q.x > 11) continue;
    const ref = convolveExact(m => 10 ** (-1 * m + 2), m => interpTable(tab, m), q.x, 4);
    assert(Math.abs(q.y - Math.log10(ref)) < 1e-6, `mass-dependent sigma at ${q.x}`);
  }
  const a = sp(pl2, { x: [0, 20], sigma: [0.2, 0.2] }), b2 = sp(pl2, 0.2);
  assert(Math.max(...a.map((p, i) => Math.abs(p.y - b2[i].y))) < 1e-12);
  n++;
  // 2a. zero scatter returns the input exactly; a tiny scatter is continuous
  const pt = ptsFrom(x => schechterY(x, alpha, xs0, phi), arange(8, 12, 0.3), 0.05);
  const z = sp(pt, 0);
  deq(z.map(p => [p.x, p.y, p.yLow, p.yHigh]), pt.map(p => [p.x, p.y, p.yLow, p.yHigh]));
  assert(Math.max(...sp(pl, 0.002).map((p, i) => Math.abs(p.y - pl[i].y))) < 1e-3);
  n++;
  // 2b. number conserved (tent density, integral 2 / (a ln10)), for constant and mass-dependent sigma; tolerance 2e-4 (7e-5 of it is the grid sum across the kink of the tent)
  const a_ = 2.5, c0 = 10;
  const tent = ptsFrom(x => -a_ * Math.abs(x - c0), arange(c0 - 6, c0 + 6, 0.01));
  const total = 2 / (a_ * LN10);
  for (const spec of [0.1, 0.3, { x: [4, 16], sigma: [0.35, 0.1] }]) {
    const out = sp(tent, spec);
    const got = trapz(out.map(q => 10 ** q.y), out.map(q => q.x));
    assert(Math.abs(got / total - 1) < 2e-4, `number not conserved for ${JSON.stringify(spec)}: ${got} vs ${total}`);
  }
  n++;
  // 2c. bands
  const bd = ptsFrom(x => beta * x + 3, arange(8, 11, 0.25), 0.05);
  const ob = sp(bd, 0.3);
  assert(ob.filter(q => q.x >= 8.9 && q.x <= 10.1).every(q => q.yHigh - q.y > 0 && q.yHigh - q.y < 0.05 && q.y - q.yLow > 0 && q.y - q.yLow < 0.05));
  assert(sp(pl, 0.3).every(q => q.yHigh === undefined));
  const oa = sp(pl.map(p => ({ ...p, yHigh: p.y + 0.1, yLow: p.y - 0.02 })), 0.3);
  assert(oa.every(q => q.yHigh - q.y > 3 * (q.y - q.yLow)));
  n++;
  // 2d. edge flags
  const oe = sp(pl, 0.3);
  assert(oe[0].edge && oe[oe.length - 1].edge && !oe[oe.length >> 1].edge && oe.every(q => q.edgeShare >= 0 && q.edgeShare <= 1));
  n++;
  return n;
}

function otherChecks() {
  let n = 0;
  const pt = ptsFrom(x => -1 - 0.5 * (x - 8), arange(8, 11, 0.5), 0.05);
  pt[0].count = 400;
  const sh_ = O.shiftPoints(pt, -0.2);
  assert(sh_.every((a, i) => Math.abs(a.x - (pt[i].x - 0.2)) < 1e-12 && a.y === pt[i].y && a.yLow === pt[i].yLow));
  assert(O.shiftPoints(sh_, 0.2).every((a, i) => Math.abs(a.x - pt[i].x) < 1e-12));
  assert.throws(() => O.shiftPoints(pt, NaN));
  n++;
  const cut = O.completenessCut(pt, 9);
  deq(cut.map(p => p.x), [9, 9.5, 10, 10.5, 11]);
  deq(O.completenessCut(cut, 9), cut);
  n++;
  const w = O.completenessWeight(pt, 9.5, 0.2), mid = w.find(p => p.x === 9.5), ref = pt.find(p => p.x === 9.5);
  assert(Math.abs(mid.y - (ref.y - Math.log10(2))) < 1e-12 && Math.abs(mid.yHigh - mid.y - 0.05) < 1e-12);
  assert(Math.abs(w[w.length - 1].completeness - 1) < 1e-3 && Math.abs(w[0].count - 400 * w[0].completeness) < 1e-9);
  assert.throws(() => O.completenessFraction(9, 9, 0));
  n++;
  const pb = O.poissonBands([{ x: 9, y: 0, count: 100 }, { x: 10, y: 0, count: 1 }, { x: 11, y: 0, count: 50, yLow: -0.3, yHigh: 0.3 }]);
  assert(Math.abs(pb[0].yHigh - Math.log10(1.1)) < 1e-12 && Math.abs(pb[0].yLow - Math.log10(0.9)) < 1e-12);
  assert(Number.isNaN(pb[1].yLow) && pb[2].yLow === -0.3);
  n++;
  const sc = ptsFrom(x => schechterY(x, -1.2, 10.7, 1e-3), arange(8, 12, 0.25));
  const ob = O.observePoints(sc, { sigma: 0.2, offset: -0.1, completeness: { m50: 9, width: 0.2 }, mLim: 8.5 });
  deq(ob.steps.map(s => s.split(" ")[0]), ["Gaussian", "mass", "smooth", "limiting"]);
  const manual = O.completenessCut(O.completenessWeight(O.shiftPoints(O.scatterPoints(sc, 0.2), -0.1), 9, 0.2), 8.5);
  assert(ob.points.length === manual.length && ob.points.every((p, i) => p.x === manual[i].x && Math.abs(p.y - manual[i].y) < 1e-12) && Math.min(...ob.points.map(p => p.x)) >= 8.5);
  n++;
  const ss = [{ x: 9, y: -9.5, yLow: -10.5, yHigh: -9 }, { x: 10, y: -10.5, yLow: -12, yHigh: -9.8 }, { x: 11, y: -12, yLow: -13, yHigh: -10.9 }];
  const f = O.ssfrFloorPoints(ss, -11);
  deq(f.map(p => p.x), [9, 10]);
  assert(f[0].clipped === undefined && f[1].yLow === -11 && f[1].clipped === true);
  const ft = O.ssfrFloorPoints(ss, { x: [9, 11], floor: [-10, -12.5] });
  deq(ft.map(p => p.x), [9, 10, 11]);
  assert(ft[1].yLow === -11.25);
  deq(O.ssfrFloorPoints(ss, { x: [9, 11], floor: [-10, -11] }).map(p => p.x), [9, 10]);
  assert(O.sfrFloorToSsfr(-1, 10) === -11);
  n++;
  return n;
}

function badInputs() {
  for (const f of [() => O.scatterPoints([{ x: 9, y: 0 }], 0.2), () => O.scatterPoints([{ x: 9, y: 0 }, { x: 9, y: 1 }], 0.2), () => O.scatterPoints([{ x: 8, y: 0 }, { x: 10, y: 1 }], 0.2),
    () => O.scatterPoints([{ x: 8, y: 0 }, { x: 8.5, y: 1 }], -0.1), () => O.scatterPoints([{ x: 8, y: 0 }, { x: 8.5, y: 1 }], "wide")]) assert.throws(f);
}

// parity with the Python results
const fx = JSON.parse(await readFile(new URL("../tests/fixtures/observer-fixture.json", import.meta.url), "utf8"));
const norm = v => Array.isArray(v) ? v.map(norm) : v && typeof v === "object" ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, norm(x)])) : typeof v === "number" && !Number.isFinite(v) ? null : v;
function same(a, b, path) {
  if (Array.isArray(a)) { assert(Array.isArray(b) && a.length === b.length, `${path}: length ${a.length} vs ${b && b.length}`); a.forEach((x, i) => same(x, b[i], `${path}[${i}]`)); }
  else if (a && typeof a === "object") { assert(b && typeof b === "object", path); deq(Object.keys(a).sort(), Object.keys(b).sort(), `${path}: keys`); for (const k of Object.keys(a)) same(a[k], b[k], `${path}.${k}`); }
  else if (typeof a === "number") { assert(typeof b === "number" && Math.abs(a - b) <= fx.tolerance * Math.max(1, Math.abs(a)), `${path}: ${a} vs ${b}`); }
  else assert.equal(a, b, path);
}
function runCase(lib, c) {
  const p = c.points, a = c.params;
  switch (c.op) {
    case "scatter": return lib.scatterPoints(p, a.sigma, a.opts);
    case "shift": return lib.shiftPoints(p, a.offset);
    case "cut": return lib.completenessCut(p, a.mLim);
    case "weight": return lib.completenessWeight(p, a.m50, a.width);
    case "poisson": return lib.poissonBands(p);
    case "observe": return lib.observePoints(p, a);
    case "floorPoints": return lib.ssfrFloorPoints(p, a.floor);
    case "floorRow": return lib.ssfrFloorRow(a.row, a.yEdges, a.floorLog);
  }
  throw new Error(c.op);
}
function parity(lib) { for (const c of fx.cases) same(norm(JSON.parse(JSON.stringify(runCase(lib, c)))), c.expected, c.name); }

// the same quantile rule as compare.js: with the floor below every bin the quantiles of a fixture row are compare.js's
{
  const dfx = JSON.parse(await readFile(new URL("../tests/fixtures/distribution-fixture.json", import.meta.url), "utf8")), st = C.distributionStats(dfx.input);
  const i = st.n.findIndex(t => t >= 10), r = O.ssfrFloorRow(dfx.input.counts[i], dfx.input.yEdges, dfx.input.yEdges[0] - 1, [.16, .5, .84]);
  assert(r.fractionDetected === 1 && [1, 2, 3].every((k, j) => Math.abs(r.quantiles[j] - st.quantiles[k][i]) < 1e-6));
  const rr = O.ssfrFloorRow([10, 10, 10, 10], [-13, -12, -11, -10, -9], -11.5);
  assert(rr.detected === 25 && Math.abs(rr.fractionDetected - 0.625) < 1e-12 && rr.quantiles[1] > -11);
}

const n1 = checks(O.scatterPoints), n2 = otherChecks();
badInputs();
parity(O);

// the battery must fail for a no-op convolution and for half the scatter; the parity must fail too
const noop = { ...O, scatterPoints: (p) => p.slice().sort((a, b) => a.x - b.x).map(q => ({ ...q, edgeShare: 0, edge: false })) };
const half = { ...O, scatterPoints: (p, s, o) => O.scatterPoints(p, typeof s === "number" ? s / 2 : s, o) };
for (const [name, broken] of [["no-op", noop.scatterPoints], ["half the scatter", half.scatterPoints]]) assert.throws(() => checks(broken), undefined, `the checks did not fail for a ${name} convolution`);
assert.throws(() => parity(noop), undefined, "the parity test did not fail for a no-op convolution");

// the saved measurement (data/analysis/observer-layer.json, written by the Python script) is reproduced for a sample of its pairs from the curves, with compare.js for the offsets and observer-lib.js for the scatter
{
  const saved = JSON.parse(await readFile(new URL("../data/analysis/observer-layer.json", import.meta.url), "utf8")), recs = {};
  for (const f of (await readdir(new URL("../data/curves/", import.meta.url))).filter(f => f.endsWith(".json")))
    for (const r of JSON.parse(await readFile(new URL(`../data/curves/${f}`, import.meta.url), "utf8")).records) recs[r.id] = r;
  const X = ctx.globalThis.SimHighlineExport;
  const pts = r => (r.representation.type === "parametric" ? X.sampled(r) : r.representation.points).filter(p => Number.isFinite(p.x) && Number.isFinite(p.y)).sort((a, b) => a.x - b.x);
  const kind = r => r.representation.intervalKind === "uncertainty" ? "uncertainty" : "unspecified";
  let worst = 0, checked = 0;
  for (let i = 0; i < saved.pairs.length; i += 9) {
    const p = saved.pairs[i], s = recs[p.sim], o = recs[p.obs], sp = pts(s), op = pts(o);
    const off = A => { const st = C.summarize(C.residuals(A, op, kind(s), kind(o))); assert(st, `${p.sim} against ${p.obs}: no summary`); return st.median; };
    worst = Math.max(worst, Math.abs(off(sp) - p.before));
    for (const sg of saved.settings.sigmasDex) worst = Math.max(worst, Math.abs(off(O.scatterPoints(sp, sg)) - p.after[String(sg)]));
    checked++;
  }
  assert(checked >= 50 && worst < 1e-4, `the saved measurement is not reproduced from the curves (largest difference ${worst}); run python3 scripts/analyze_observer_layer.py`);
  var savedNote = `${checked} saved pairs reproduced from the curves to ${worst.toExponential(1)} dex`;
}

console.log(`observer tests passed: ${n1 + n2} check groups, analytic and quadrature agreement, invariants, ${fx.cases.length} fixture cases equal to the Python results, and a no-op convolution is caught; ${savedNote}`);
