import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import numpy as np
except ImportError:
    print("model-form test skipped: numpy not installed")
    raise SystemExit(0)
import analyze_model_form as A
import modelform_stats as ms

# ---- special functions against known values
assert abs(ms.betainc(2, 3, 0.4) - 0.5248) < 1e-9
assert abs(ms.t_sf(2.015048, 5) - 0.05) < 1e-6 and abs(ms.t_sf(2.570582, 5) - 0.025) < 1e-6 and abs(ms.t_sf(-2.015048, 5) - 0.95) < 1e-6
assert abs(ms.t_ppf(0.95, 5) - 2.015048) < 1e-4 and abs(ms.t_ppf(0.975, 10) - 2.228139) < 1e-4
assert abs(ms.f_sf(5.19, 4, 5) - 0.05) < 1e-3

# ---- the Pitman-Morgan test is calibrated and has power
rng = np.random.default_rng(1)
rej0 = rej1 = 0
for _ in range(2000):
    z = rng.standard_normal((8, 2))
    x, y0 = z[:, 0], 0.5 * z[:, 0] + np.sqrt(0.75) * z[:, 1]
    rej0 += ms.pitman_morgan(x, y0)[2] < 0.05
    rej1 += ms.pitman_morgan(x, 3.0 * y0)[2] < 0.05
assert 0.02 < rej0 / 2000 < 0.08 and rej1 / 2000 > 0.8, (rej0 / 2000, rej1 / 2000)

# ---- Gaussian process draws have the stated amplitude and correlation
g = np.arange(0.0, 8.0, 0.25)
d = ms.gp_draws(g, np.full(len(g), 0.3), 1.5, rng, 4000)
assert abs(d.std() - 0.3) < 0.02 and abs(np.corrcoef(d[:, 10], d[:, 14])[0, 1] - np.exp(-0.5 * (1.0 / 1.5) ** 2)) < 0.05

# ---- the emulator recovers a known quadratic response (with a missing value) and respects weights
X = rng.uniform(-1, 1, (800, 6))
F = ms.quad_features(X)
true = rng.normal(0, 0.2, (F.shape[1], 5))
Y = F @ true + rng.normal(0, 0.02, (800, 5))
Y[3, 2] = np.nan
emu = ms.Emulator(2, 1e-6).fit(X, Y)
Xt = rng.uniform(-1, 1, (200, 6))
assert np.sqrt(np.mean((emu.predict(Xt) - ms.quad_features(Xt) @ true) ** 2)) < 0.01
wemu = ms.Emulator(2, 1e-6).fit(X, Y, np.exp(-0.5 * (X[:, 0] ** 2 + X[:, 1] ** 2) / 0.25))
assert np.sqrt(np.mean((wemu.predict(Xt[:50] * np.array([0.3, 0.3, 1, 1, 1, 1])) - ms.quad_features(Xt[:50] * np.array([0.3, 0.3, 1, 1, 1, 1])) @ true) ** 2)) < 0.02

# ---- the family curves, windows and variances
grid = A.Z_PUB
rec = {"representation": {"points": [{"x": float(z), "y": float(-1.0 - 0.1 * z)} for z in np.arange(0.0, 6.01, 0.05)]}}
v = A.on_grid(rec, grid)
assert np.allclose(v[grid <= 5.8], -1.0 - 0.1 * grid[grid <= 5.8], atol=1e-6) and np.isnan(v[grid >= 6.0]).all(), "windowed value of a straight line is the line; undefined past the curve"
Y = np.vstack([np.linspace(0, 1, 10) * s for s in (1.0, 2.0, 3.0, 4.0, 5.0)])
assert np.allclose(A.col_var(Y, 5), np.var(np.array([1, 2, 3, 4, 5.0])[:, None] * np.linspace(0, 1, 10)[None, :], axis=0, ddof=1))
assert np.isnan(A.col_var(Y[:4], 5)).all(), "fewer than five families at a redshift: no spread"

# ---- the funnel statistic: null, a known funnel, and the slope
sel = (grid >= 0.5) & (grid <= 7.5)
gs = grid[sel]


def synth(n, ratio, ell, r, tau_low=0.15):
    amp = tau_low * ratio ** np.clip((gs - 1.75) / (6.25 - 1.75), 0, 1)
    Y = np.full((n, len(grid)), np.nan)
    Y[:, sel] = ms.gp_draws(gs, amp, ell, r, n)
    return Y


rng = np.random.default_rng(7)
Y = synth(4000, 4.0, 1.0, rng)  # many families: the statistic converges on its target
amp = 0.15 * 4.0 ** np.clip((grid - 1.75) / 4.5, 0, 1)
target = 0.5 * np.log10(np.mean(amp[A.band_mask(grid, A.BANDS["high"])] ** 2) / np.mean(amp[A.band_mask(grid, A.BANDS["low"])] ** 2))
phi = A.funnel_phi(Y, grid)
assert abs(phi - target) < 0.03, (phi, target)
slope = A.loglinear_slope(grid, A.spread_curve(Y))
assert 0.05 < slope < 0.2, slope
succ0 = succ1 = 0
for k in range(30):
    r0 = A.pub_funnel(synth(7, 1.0, 1.5, rng), grid, rng, nboot=200)
    r1 = A.pub_funnel(synth(7, 5.0, 1.5, rng), grid, rng, nboot=200)
    succ0 += int(r0["phi_ci90"][0] > 0 and r0["pitman_morgan"]["p_one_sided"] < 0.05)
    succ1 += int(r1["phi_ci90"][0] > 0 and r1["pitman_morgan"]["p_one_sided"] < 0.05)
assert succ0 <= 4 and succ1 >= 18, (succ0, succ1)

# ---- the tier RMS and the closure on constructed curves
recs = {}
for i, off in enumerate((0.0, 0.3, -0.2)):
    recs[f"c{i}"] = {"representation": {"points": [{"x": float(z), "y": float(-1.2 + off + 0.05 * z)} for z in np.arange(0.0, 9.01, 0.05)]}, "definitions": {"cosmology": {"H0": 70.0, "Om": 0.3}}, "relation": "sfrd"}
variants = {"variants": [{"id": "c1", "family": "F", "base": "c0", "class": "parametric"}, {"id": "c2", "family": "F", "base": "c0", "class": "parametric"}]}
t = A.tier_rms(recs, variants, grid, by_family=False)["parametric"]["low"]
assert abs(t["rms_dex"] - np.sqrt((0.3 ** 2 + 0.2 ** 2) / 2)) < 1e-6 and t["n_variants"] == 2
# closure: constant SFR density 0.01 Msun/yr/cMpc^3 from z = 10 to 0 forms rho = 0.01 * (age difference); a stellar density that is 60 % of that has R_eff = 0.4
zz = np.arange(0.0, 10.01, 0.05)
from analyze_model_form import lcdm_dt_dz
formed = float(np.sum(0.5 * (0.01 * lcdm_dt_dz(zz, 0.7, 0.3))[1:] * np.diff(zz) + 0.5 * (0.01 * lcdm_dt_dz(zz, 0.7, 0.3))[:-1] * np.diff(zz)))
srec = {"representation": {"points": [{"x": float(z), "y": -2.0} for z in zz]}, "definitions": {"cosmology": {"H0": 70.0, "Om": 0.3}}}
mrec = {"representation": {"points": [{"x": float(z), "y": float(np.log10(0.6 * 0.01 * np.sum(0.5 * (lcdm_dt_dz(zz[zz >= z], 0.7, 0.3)[1:] + lcdm_dt_dz(zz[zz >= z], 0.7, 0.3)[:-1]) * np.diff(zz[zz >= z])) if z < 10 else 1))} for z in zz[:-1]]}, "definitions": {"cosmology": {"H0": 70.0, "Om": 0.3}}}
ct = A.closure_table({"s": srec, "m": mrec}, [("synthetic", "s", "m")], zs=(0.0, 1.0, 2.0))[0]["R_eff"]
assert all(abs(v["R_eff"] - 0.4) < 0.01 for v in ct.values()), ct
assert abs(A.imf_shift("salpeter55") + 0.235) < 1e-12 and A.imf_shift("chabrier03") == 0 and A.imf_shift("unspecified") == 0

# ---- CAMELS machinery on a synthetic two-code ensemble with a known structure
nz = len(A.CAMELS_Z)
zc = A.CAMELS_Z
shapes = np.array([np.exp(-0.5 * ((zc - c) / 2.5) ** 2) for c in (1.0, 3.0, 5.0, 7.0)])  # four response shapes, per unit coordinate


def synth_code(offset, resp, n, r, noise=0.05):
    X = np.column_stack([r.uniform(-1, 1, (n, 2)), r.uniform(-1, 1, (n, 4))])
    Y = offset[None, :] + 0.1 * X[:, :1] + X[:, 2:] @ (resp[:, None] * shapes) + 0.02 * X[:, 2:3] * X[:, 3:4] + r.normal(0, noise, (n, nz))
    return X, Y


r = np.random.default_rng(11)
resp = np.array([0.25, 0.2, 0.15, 0.1])
base_off = -1.5 - 0.1 * zc
Xt, Yt = synth_code(base_off, resp, 1000, r)
Xs, Ys = synth_code(base_off + 0.02, resp * np.array([1.0, 1.1, 0.9, 1.0]), 1000, r)  # a second code that is the first plus a reachable offset
emu_t, emu_s = A.fit_emulator(Xt, Yt), A.fit_emulator(Xs, Ys)
Xv, Yv = synth_code(base_off, resp, 300, r, noise=0.0)
cvr, ncv = A.cv_errors(Xt, Yt)
assert np.nanmax(cvr) < 0.075 and ncv > 100, "cross-validation error near the noise floor 0.05"
assert np.nanmax(np.abs(emu_t.predict(Xv) - Yv)[(np.abs(Xv[:, 0]) < 0.5) & (np.abs(Xv[:, 1]) < 0.5)]) < 0.05
sd, p16, p84 = A.parametric_spread(emu_t, np.random.default_rng(3))
expected = np.sqrt(((resp[:, None] * shapes) ** 2).sum(axis=0) / 3.0)  # uniform on [-1,1] has variance 1/3
assert np.max(np.abs(sd - expected)) < 0.02, np.max(np.abs(sd - expected))
zsel = np.ones(nz, bool)
d_same, _ = A.reachability(emu_t, emu_s, zsel, np.random.default_rng(5), nstarts=8)
assert d_same < 0.03, d_same  # a small offset is reachable
Xo, Yo = synth_code(base_off + 1.0, resp, 1000, r)  # an offset of 1 dex is not reachable with responses of at most 0.25 per coordinate
emu_o = A.fit_emulator(Xo, Yo)
d_far, _ = A.reachability(emu_t, emu_o, zsel, np.random.default_rng(5), nstarts=8)
import itertools
grid_d = np.linspace(-2, 2, 17)  # the difference of the two codes' coordinates reaches [-2, 2] in each
best_possible = min(np.sqrt(np.mean((-1.0 + np.array(dl) @ (resp[:, None] * shapes)) ** 2)) for dl in itertools.product(grid_d, repeat=4))
assert d_far > 0.2 and abs(d_far - best_possible) < 0.02, (d_far, best_possible)  # the optimiser finds the best reachable difference found by brute force
d_small, _ = A.reachability(emu_t, emu_o, zsel, np.random.default_rng(5), lam=0.25, nstarts=8)
assert d_small > d_far, "a smaller prior range reaches less"
# controls: two emulators of the same code on disjoint halves are at the noise
ia, ib = A.split_halves(len(Xt), np.random.default_rng(1))
d_ctl, _ = A.reachability(A.fit_emulator(Xt[ia], Yt[ia]), A.fit_emulator(Xt[ib], Yt[ib]), zsel, np.random.default_rng(5), nstarts=4)
assert d_ctl < 0.03, d_ctl
# calibration: data generated from a known point; the posterior brackets it
a_true = np.array([0.5, -0.3, 0.2, 0.6])
truth = A.predict_astro(emu_t, a_true[None, :])[0]
zi = np.array([int(np.argmin(np.abs(zc - z))) for z in (0.1, 0.9, 1.7, 2.5)])
post, ess, _ = A.calibrate(emu_t, zi, truth[zi], np.full(len(zi), 0.03), np.random.default_rng(2), nprior=200000, chunk=50000)
assert ess > 50 and np.all(np.abs(np.median(post, axis=0)) < 1.0)
lo, med, hi = A.weighted_summary(emu_t, post, np.array([int(np.argmin(np.abs(zc - z))) for z in (4.1, 6.1)]))
tt = truth[[int(np.argmin(np.abs(zc - z))) for z in (4.1, 6.1)]]
assert np.all(lo - 0.05 <= tt) and np.all(tt <= hi + 0.05), (lo, tt, hi)

# ---- the reachability search does not depend on its starts and beats a random search, also with strong curvature
def curved(seed, quad, off):
    rr = np.random.default_rng(seed)
    pc = ms.quad_features(np.zeros((1, 6))).shape[1]
    coef = np.zeros((pc, nz))
    for j in range(4):
        coef[3 + j] = 0.12 * np.cumsum(rr.normal(0, 1, nz)) / np.sqrt(nz)
    k = 7
    for a in range(6):
        for b in range(a, 6):
            if a >= 2 and b >= 2:
                coef[k] = rr.normal(0, quad, nz)
            k += 1
    coef[0] = -1.5 - 0.1 * zc + off
    e = ms.Emulator(2, 0)
    e.coef = coef
    return e


ec_t, ec_s = curved(1, 0.4, 0.0), curved(2, 0.4, 0.8)
d4, _ = A.reachability(ec_t, ec_s, zsel, np.random.default_rng(1), nstarts=4)
d30, _ = A.reachability(ec_t, ec_s, zsel, np.random.default_rng(2), nstarts=30)
rs = np.random.default_rng(9)
best_rs = min(np.sqrt(np.mean((A.predict_astro(ec_t, rs.uniform(-1, 1, (20000, 4))) - A.predict_astro(ec_s, rs.uniform(-1, 1, (20000, 4)))) ** 2, axis=1)).min() for _ in range(10))
assert abs(d4 - d30) < 1e-4 and d30 <= best_rs, (d4, d30, best_rs)

# ---- the data: variants table is consistent with the records, families are eligible, CAMELS file (if present) has the stated schema
recs_all = A.load_sfrd()
variants = A.load_variants()
for v in variants["variants"]:
    assert v["id"] in recs_all and v["base"] in recs_all and v["class"] in variants["classes"], v
    assert recs_all[v["id"]]["source"] == recs_all[v["base"]]["source"] or v["family"] in ("THESAN-1",), v
fids = A.eligible_fiducials(recs_all, variants)
assert len(fids) == 9 and "SIMBA" not in fids and all(recs_all[f]["definitions"]["densityFrame"] == "comoving" for f in fids.values())
assert not (set(fids.values()) & {v["id"] for v in variants["variants"]}), "a fiducial is never a variant"
camels = ROOT / "data" / "ensembles" / "camels-sfrd.json"
if camels.exists():
    cd = A.load_camels()
    for suite in ("IllustrisTNG", "SIMBA"):
        assert len(cd["suites"][suite]["LH"]) == 1000 and len(cd["suites"][suite]["CV"]) == 27, suite
        names, X, Yc = A.camels_arrays(cd, suite, "LH")
        assert X.shape == (1000, 6) and Yc.shape == (1000, len(A.CAMELS_Z)) and np.all(np.abs(X) <= 1.0 + 1e-9), (suite, X.shape, np.abs(X).max())
        assert np.isfinite(Yc[:, A.CAMELS_Z <= 4.0]).mean() > 0.98
    assert abs(cd["h"] - 0.6711) < 1e-9 and abs(cd["volumeCMpc3"] - (25 / 0.6711) ** 3) < 1

# ---- end to end on a synthetic twin of the data: same records, same coverage, curves generated with a known funnel; CAMELS-like ensembles with a known structural offset
import copy
import time

t0 = time.time()
rng_w = np.random.default_rng(2026)
FUN_RATIO = 5.0
fam_of = {d["fiducial"]: f for f, d in variants["families"].items()}
base_of = {}
for v in variants["variants"]:
    base_of[v["id"]] = v
fam_off = {}
twin = {}
amp_fun = lambda z: 0.15 * FUN_RATIO ** np.clip((z - 1.75) / 4.5, 0, 1)
for rid, rec in recs_all.items():
    z, _ = A.curve_arrays(rec)
    fam = fam_of.get(rid) or (base_of[rid]["family"] if rid in base_of else rec["source"])
    if fam not in fam_off:
        fam_off[fam] = ms.gp_draws(np.arange(0, 20.01, 0.05), amp_fun(np.arange(0, 20.01, 0.05)), 1.5, rng_w, 1)[0]
    y = -1.5 - 0.15 * z + np.interp(z, np.arange(0, 20.01, 0.05), fam_off[fam])
    if rid in base_of:
        cls = base_of[rid]["class"]
        y = y + {"numerical": 0.04, "parametric": 0.2, "calibration": 0.06, "cosmology": 0.05}.get(cls, 0.1) * np.sin(0.7 * z + hash(rid) % 7)
    r2 = copy.deepcopy(rec)
    r2["representation"]["points"] = [{"x": float(a), "y": float(b)} for a, b in zip(z, y)]
    twin[rid] = r2
zc_all = np.round(np.arange(0.1, 13.95, 0.2), 1)
nz_all = len(zc_all)


def twin_camels(offset_high):
    lo = np.array([A.to_x({"Om": 0.3, "s8": 0.8, "ASN1": 1, "AAGN1": 1, "ASN2": 1, "AAGN2": 1})])
    suites = {}
    for code, off, k in (("IllustrisTNG", 0.0, 1), ("SIMBA", offset_high, 2)):
        rr = np.random.default_rng(100 + k)
        shp = np.array([np.exp(-0.5 * ((zc_all - c) / 2.5) ** 2) for c in (1.0, 3.0, 5.0, 7.0)])
        resp = np.array([0.25, 0.2, 0.15, 0.1]) * (1.0 if k == 1 else 1.1)

        def sims(n, prefix, fixed):
            out = {}
            for i in range(n):
                p = {"Om": 0.3, "s8": 0.8, "ASN1": 1.0, "AAGN1": 1.0, "ASN2": 1.0, "AAGN2": 1.0} if fixed else {"Om": float(rr.uniform(0.1, 0.5)), "s8": float(rr.uniform(0.6, 1.0)), "ASN1": float(4 ** rr.uniform(-1, 1)), "AAGN1": float(4 ** rr.uniform(-1, 1)), "ASN2": float(2 ** rr.uniform(-1, 1)), "AAGN2": float(2 ** rr.uniform(-1, 1))}
                x = A.to_x(p)
                y = -1.5 - 0.15 * zc_all + off * (zc_all > 3.25) + 0.1 * x[0] + x[2:] @ (resp[:, None] * shp) + rr.normal(0, 0.1, nz_all)
                out[f"{prefix}_{i}"] = {"params": p, "seed": i, "sfrd": [round(float(v), 4) for v in y], "formedMassMsun": 1e13, "sha256": "x", "bytes": 1}
            return out
        suites[code] = {"LH": sims(1000, "LH", False), "CV": sims(27, "CV", True)}
    return {"zEdges": [round(v, 1) for v in np.arange(0, 14.01, 0.2)], "zCentres": [float(v) for v in zc_all], "suites": suites, "h": 0.6711, "volumeCMpc3": (25 / 0.6711) ** 3}


orig = (A.load_sfrd, A.load_camels)
try:
    A.load_sfrd = lambda: twin
    A.load_camels = lambda path=None: twin_camels(1.5)
    res = A.run(nboot=200, nrand=3, camels_kw=dict(nboot=8, ncontrol=6, nstarts=3))
    A.load_camels = lambda path=None: twin_camels(0.0)
    null_c = A.run_camels(twin, A.SEED, nboot=8, ncontrol=6, nstarts=3)
finally:
    A.load_sfrd, A.load_camels = orig
e1 = res["published"]["E1"]
amp_lo, amp_hi = amp_fun(np.arange(0.5, 3.01, 0.25)).mean(), amp_fun(np.arange(5.0, 7.51, 0.25)).mean()
assert e1["n_balanced"] >= 6 and e1["phi"] > 0.2 and e1["success"], e1["phi"]  # a funnel of 5 across seven or more families is seen
rch = res["camels"]["reachability"]
assert res["verdicts"]["E3"]["verdict"] == "structural" and rch["full"]["D_dex"] > 3 * rch["controls_full"]["p95"], rch
assert rch["high"]["D_dex"] > 0.5 and rch["low"]["D_dex"] < 0.08, {k: rch[k] for k in ("full", "low", "high")}  # an offset of 1.5 dex above z = 3.25 cannot be reached with responses of a few tenths of a dex
assert rch["shrunk"]["0.25"] > rch["shrunk"]["0.5"] > rch["shrunk"]["1.0"], "a smaller parameter range reaches less"
assert res["camels"]["codes"]["IllustrisTNG"]["parametric"]["rms_high"] > 0.1 and res["camels"]["structural_fiducial"]["rms_high"] > 1.0
assert null_c["reachability"]["full"]["D_dex"] < 0.1, "with no offset the codes are reachable from each other"
doc = A.render(res)
import os
if os.environ.get("MODELFORM_DUMP"):  # a synthetic result, for looking at the report and the site charts without the real data
    Path(os.environ["MODELFORM_DUMP"]).write_text(json.dumps(res, default=lambda o: float(o) if isinstance(o, (np.floating,)) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)))
    Path(os.environ["MODELFORM_DUMP"] + ".md").write_text(doc)
assert "do not edit by hand" in doc and "E1" in doc and doc.count("|") > 400
assert time.time() - t0 < 600

# ---- the saved analysis is not stale: its headline numbers are recomputed from the records
saved_path = ROOT / "data" / "analysis" / "model-form.json"
if saved_path.exists():
    saved = json.loads(saved_path.read_text())
    assert saved["version"] == json.loads((ROOT / "data" / "release.json").read_text())["version"], "analysis output is stale; rerun analyze_model_form.py"
    fm = sorted(fids)
    Yp = A.family_matrix(recs_all, variants, [fids[f] for f in fm], A.Z_PUB)
    assert abs(A.funnel_phi(Yp[A.balanced_rows(Yp, A.Z_PUB)], A.Z_PUB) - saved["published"]["E1"]["phi"]) < 1e-6, "analysis output is stale; rerun analyze_model_form.py"
    assert sorted(saved["published"]["families"]) == fm
    assert "do not edit by hand" in (ROOT / "docs" / "ANALYSIS-model-form.md").read_text()
    if camels.exists():
        cdat = A.load_camels()
        _, Xa, Ya = A.camels_arrays(cdat, "IllustrisTNG", "CV")
        sn = A.seed_noise(Ya)
        assert abs(sn[10] - saved["camels"]["codes"]["IllustrisTNG"]["seed_noise"][10]) < 1e-6, "analysis output is stale; rerun analyze_model_form.py"
print("model-form: OK")
