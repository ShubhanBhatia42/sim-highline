"""Parametric versus structural uncertainty in the cosmic star formation history of simulated galaxy formation.

Implements docs/PROTOCOL-model-form.md section by section; every departure is reported as a deviation in the generated docs/ANALYSIS-model-form.md. Two data sources:
  published curves (data/curves, sfrd records; model families and variants in data/model-variants.json) and
  the CAMELS IllustrisTNG and SIMBA ensembles (data/ensembles/camels-sfrd.json, written by scripts/ingest_camels_sfrd.py).
Writes data/analysis/model-form.json and docs/ANALYSIS-model-form.md. Nothing here changes a stored record."""
import itertools
import json
import math
import re
import sys
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import modelform_stats as ms

warnings.filterwarnings("ignore", category=RuntimeWarning, message="(Mean of empty slice|All-NaN slice|Degrees of freedom)")  # columns without enough families are NaN by design
ROOT = Path(__file__).resolve().parent.parent
SEED = 20261015

# ---------------------------------------------------------------- published curves
Z_PUB = np.round(np.arange(0.25, 8.0001, 0.25), 2)
WINDOW = 0.125  # a curve's value at a grid redshift is the mean of log10 SFRD over +-WINDOW (the plotted lines carry spikes from single outputs)
BANDS = {"low": (0.5, 3.0), "high": (5.0, 7.5)}
MIN_FAMILIES = 5
NBOOT = 5000
IMF_DEX = {"kroupa01": 0.0, "chabrier03": -0.025, "salpeter55": 0.21}  # compare.js: dex in stellar mass, the website's offsets


def imf_shift(imf):
    """Dex to add to a rate expressed with this IMF to express it for a Chabrier IMF (the website's offsets; unstated IMFs stay as published)."""
    return IMF_DEX["chabrier03"] - IMF_DEX[imf] if imf in IMF_DEX else 0.0


def load_sfrd():
    recs = {}
    for f in sorted((ROOT / "data" / "curves").glob("*.json")):
        for r in json.loads(f.read_text())["records"]:
            if r["relation"] == "sfrd" and r["kind"] == "simulation":
                recs[r["id"]] = r
    return recs


def load_variants():
    return json.loads((ROOT / "data" / "model-variants.json").read_text())


def curve_arrays(rec):
    pts = sorted((p["x"], p["y"]) for p in rec["representation"]["points"])
    return np.array([p[0] for p in pts]), np.array([p[1] for p in pts])


def on_grid(rec, grid, window=WINDOW, shift=0.0):
    """log10 SFRD of a curve at each grid redshift: the mean over +-window of the linearly interpolated curve, NaN where the window is not wholly inside the curve."""
    z, y = curve_arrays(rec)
    out = np.full(len(grid), np.nan)
    for k, g in enumerate(grid):
        if g - window >= z[0] - 1e-9 and g + window <= z[-1] + 1e-9:
            t = np.linspace(g - window, g + window, 26)
            out[k] = float(np.mean(np.interp(t, z, y))) + shift
    return out


def col_var(Y, min_n=MIN_FAMILIES):
    """Unbiased variance across rows at every column, NaN where fewer than min_n rows are finite."""
    ok = np.isfinite(Y)
    n = ok.sum(axis=0)
    mean = np.nansum(Y, axis=0) / np.maximum(n, 1)
    ss = np.nansum((Y - mean) ** 2, axis=0)
    return np.where(n >= min_n, ss / np.maximum(n - 1, 1), np.nan)


def band_mask(grid, band):
    return (grid >= band[0] - 1e-9) & (grid <= band[1] + 1e-9)


def band_variance(Y, grid, band, min_n=MIN_FAMILIES):
    v = col_var(Y[:, band_mask(grid, band)], min_n)
    return float(np.nanmean(v)) if np.isfinite(v).any() else float("nan")


def funnel_phi(Y, grid, bands=BANDS):
    """Primary statistic: log10 of the ratio of the between-family standard deviations in the high and the low band (variances averaged over the grid points of each band)."""
    vl, vh = band_variance(Y, grid, bands["low"]), band_variance(Y, grid, bands["high"])
    return 0.5 * math.log10(vh / vl) if vl > 0 and vh > 0 else float("nan")


def band_offsets(Y, grid, bands=BANDS):
    """Mean over each band of every family's offset from the family mean at the same redshift (rows complete over both bands)."""
    dev = Y - np.nanmean(Y, axis=0)
    return [np.nanmean(dev[:, band_mask(grid, bands[k])], axis=1) for k in ("low", "high")]


def balanced_rows(Y, grid, bands=BANDS):
    sel = band_mask(grid, bands["low"]) | band_mask(grid, bands["high"])
    return np.isfinite(Y[:, sel]).all(axis=1)


def spread_curve(Y, min_n=MIN_FAMILIES):
    return np.sqrt(col_var(Y, min_n))


def loglinear_slope(grid, s, lo=0.5, hi=7.5):
    """Slope (dex of spread per unit redshift) of log10 S(z) on z over [lo, hi]."""
    sel = (grid >= lo - 1e-9) & (grid <= hi + 1e-9) & np.isfinite(s) & (s > 0)
    if sel.sum() < 6:
        return float("nan")
    return float(np.polyfit(grid[sel], np.log10(s[sel]), 1)[0])


def cluster_bootstrap(Y, stat, rng, nboot=NBOOT):
    """Statistic recomputed on families (rows) resampled with replacement."""
    n = Y.shape[0]
    out = []
    for _ in range(nboot):
        idx = rng.integers(0, n, size=n)
        if len(set(idx.tolist())) < 3:
            continue
        v = stat(Y[idx])
        if np.isfinite(v):
            out.append(v)
    return np.array(out)


def pct(v, q):
    return float(np.percentile(v, q))


def pub_funnel(Y, grid, rng, nboot=NBOOT, bands=BANDS):
    """E1 of the protocol on a matrix of families by grid redshift. Returns the statistic, bootstrap interval, Pitman-Morgan p-value, the spread curve with its bootstrap band, slope and anchor."""
    bal = balanced_rows(Y, grid, bands)
    Yb = Y[bal]
    out = {"n_families": int(Y.shape[0]), "n_balanced": int(bal.sum())}
    if bal.sum() < 5:
        return {**out, "phi": float("nan")}
    phi = funnel_phi(Yb, grid, bands)
    boot = cluster_bootstrap(Yb, lambda M: funnel_phi(M, grid, bands), rng, nboot)
    ul, uh = band_offsets(Yb, grid, bands)
    ratio, tstat, p = ms.pitman_morgan(ul, uh)
    s = spread_curve(Y)
    sboot = []
    for _ in range(min(nboot, 1000)):
        idx = rng.integers(0, Y.shape[0], size=Y.shape[0])
        sboot.append(spread_curve(Y[idx]))
    sboot = np.array(sboot)
    slopes = np.array([loglinear_slope(grid, sb) for sb in sboot])
    slopes = slopes[np.isfinite(slopes)]
    zstar = np.array([grid[np.nanargmin(np.where(np.isfinite(sb), sb, np.inf))] for sb in sboot if np.isfinite(sb).any()])
    return {**out, "phi": float(phi), "phi_ci90": [pct(boot, 5), pct(boot, 95)], "phi_ci95": [pct(boot, 2.5), pct(boot, 97.5)], "boot_fraction_positive": float((boot > 0).mean()), "boot_n": int(boot.size),
            "sd_low": float(math.sqrt(band_variance(Yb, grid, bands["low"]))), "sd_high": float(math.sqrt(band_variance(Yb, grid, bands["high"]))),
            "pitman_morgan": {"variance_ratio": ratio, "t": tstat, "p_one_sided": p, "n": int(bal.sum())},
            "spread": {"z": [float(z) for z in grid], "sd": [None if not np.isfinite(v) else float(v) for v in s], "sd_p16": [None if not np.isfinite(v) else float(v) for v in np.nanpercentile(sboot, 16, axis=0)],
                       "sd_p84": [None if not np.isfinite(v) else float(v) for v in np.nanpercentile(sboot, 84, axis=0)], "n": [int(v) for v in np.isfinite(Y).sum(axis=0)]},
            "slope_dex_per_z": float(loglinear_slope(grid, s)), "slope_ci90": [pct(slopes, 5), pct(slopes, 95)] if slopes.size else None,
            "anchor_z": float(grid[np.nanargmin(np.where(np.isfinite(s), s, np.inf))]), "anchor_z_ci90": [pct(zstar, 5), pct(zstar, 95)] if zstar.size else None}


def family_matrix(recs, variants, fids, grid, imf=False, window=WINDOW):
    """Rows: one fiducial curve per family; columns: grid redshifts."""
    shifts = [imf_shift(recs[f]["definitions"].get("imf")) if imf else 0.0 for f in fids]
    return np.array([on_grid(recs[f], grid, window, s) for f, s in zip(fids, shifts)])


# ---------------------------------------------------------------- the family set (protocol section 3)
def eligible_fiducials(recs, variants, extra=()):
    """One fiducial curve per family: the families of data/model-variants.json (plus `extra` family names), each checked against the rules of section 3."""
    out = {}
    for fam, d in variants["families"].items():
        if fam in ("SIMBA", "Horizon-AGN") and fam not in extra:
            continue
        r = recs[d["fiducial"]]
        defs = r["definitions"]
        assert defs.get("densityFrame") == "comoving" or fam in extra, (fam, "frame")
        out[fam] = d["fiducial"]
    return out


def random_fiducials(recs, variants, rng, both_bands=False):
    """Sensitivity S5: for every family one of its fiducial curve and its numerical variants, chosen at random (S5b: only among curves that reach both bands, so the balanced set keeps all its families)."""
    base = eligible_fiducials(recs, variants)
    out = {}
    for fam, fid in base.items():
        pool = [fid] + [v["id"] for v in variants["variants"] if v["base"] == fid and v["class"] == "numerical" and v["id"] in recs]
        if both_bands:
            pool = [r for r in pool if balanced_rows(family_matrix(recs, variants, [r], Z_PUB), Z_PUB)[0]] or [fid]
        out[fam] = pool[int(rng.integers(0, len(pool)))]
    return out


# ---------------------------------------------------------------- the tiers of published variants (protocol E2)
def tier_rms(recs, variants, grid, bands=BANDS, by_family=True):
    """RMS deviation of the variants of each class from their base run, per band: at every grid redshift the squared difference of the (windowed) log SFRD, averaged over the band and over variants
    (by_family: first within each family, then over families)."""
    rows = {}
    for v in variants["variants"]:
        if v["id"] not in recs or v["base"] not in recs:
            continue
        yv, yb = on_grid(recs[v["id"]], grid), on_grid(recs[v["base"]], grid)
        rows.setdefault(v["class"], []).append((v["family"], v["id"], yv - yb))
    out = {}
    for cls, items in sorted(rows.items()):
        out[cls] = {}
        for bname, band in bands.items():
            m = band_mask(grid, band)
            per = []
            for fam, vid, d in items:
                dd = d[m]
                if np.isfinite(dd).sum() >= max(3, 0.5 * m.sum()):
                    per.append((fam, float(np.nanmean(dd ** 2)), vid))
            if not per:
                out[cls][bname] = None
                continue
            if by_family:
                fams = {}
                for fam, v2, vid in per:
                    fams.setdefault(fam, []).append(v2)
                val = float(np.sqrt(np.mean([np.mean(v) for v in fams.values()])))
            else:
                val = float(np.sqrt(np.mean([v2 for _, v2, _ in per])))
            out[cls][bname] = {"rms_dex": val, "n_variants": len(per), "n_families": len({f for f, _, _ in per}), "variants": [vid for _, _, vid in per]}
    return out


def tier_rms_bootstrap(recs, variants, grid, rng, nboot=2000, bands=BANDS):
    """Percentile intervals of the class RMS values from resampling variants within each class."""
    items = {}
    for v in variants["variants"]:
        if v["id"] in recs and v["base"] in recs:
            items.setdefault(v["class"], []).append(v)
    res = {}
    for cls, vs in items.items():
        res[cls] = {}
        for bname, band in bands.items():
            m = band_mask(grid, band)
            diffs = []
            for v in vs:
                d = (on_grid(recs[v["id"]], grid) - on_grid(recs[v["base"]], grid))[m]
                if np.isfinite(d).sum() >= max(3, 0.5 * m.sum()):
                    diffs.append(float(np.nanmean(d ** 2)))
            if len(diffs) < 2:
                res[cls][bname] = None
                continue
            diffs = np.array(diffs)
            boots = [math.sqrt(diffs[rng.integers(0, len(diffs), len(diffs))].mean()) for _ in range(nboot)]
            res[cls][bname] = [pct(boots, 5), pct(boots, 95)]
    return res


# ---------------------------------------------------------------- closure of the stellar mass budget (protocol V5)
def lcdm_dt_dz(z, h, om):
    """dt/dz in years for a flat LCDM universe (negative sign dropped)."""
    ez = np.sqrt(om * (1 + np.asarray(z)) ** 3 + 1 - om)
    return 977.792e9 / (100.0 * h) / ((1 + np.asarray(z)) * ez)


V5_Z = (0.0, 1.0, 2.0, 3.0)
V5_START_TOLERANCE = 0.06  # a curve that starts at z = 0.046 (EAGLE) or 0.003 (COLIBRE) stands in for z = 0; the integral and the density are taken from the curve's own first point


def closure_table(recs_all, runs, zs=V5_Z):
    """Effective return fraction R_eff(z) = 1 - rho_*(z) / integral of the SFR density above z, for the suites that have both curves of the same run.
    runs: list of (label, sfrd record id, smd record id). A requested redshift below a curve's first point by at most V5_START_TOLERANCE uses that first point; the table lists the redshifts it could not evaluate."""
    rows = []
    for label, sid, mid in runs:
        s, m = recs_all[sid], recs_all[mid]
        zs_s, ys_s = curve_arrays(s)
        zs_m, ys_m = curve_arrays(m)
        cosmo = s["definitions"].get("cosmology") or m["definitions"].get("cosmology") or {"H0": 70.0, "Om": 0.3}
        h, om = cosmo["H0"] / 100.0, cosmo["Om"]
        row = {"run": label, "sfrd": sid, "smd": mid, "z_sfrd": [float(zs_s[0]), float(zs_s[-1])], "z_smd": [float(zs_m[0]), float(zs_m[-1])], "R_eff": {}, "not_evaluated": []}
        for z0 in zs:
            if z0 < zs_s[0] - V5_START_TOLERANCE or z0 < zs_m[0] - V5_START_TOLERANCE or z0 > zs_m[-1] or z0 > zs_s[-1]:
                row["not_evaluated"].append(float(z0))
                continue
            g = np.linspace(max(z0, zs_s[0]), zs_s[-1], 4000)
            integrand = 10.0 ** np.interp(g, zs_s, ys_s) * lcdm_dt_dz(g, h, om)
            formed = float(np.sum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(g)))  # Msun / cMpc^3
            rho = 10.0 ** float(np.interp(z0, zs_m, ys_m))
            row["R_eff"][str(z0)] = {"formed_log10": round(math.log10(formed), 3), "smd_log10": round(math.log10(rho), 3), "R_eff": round(1.0 - rho / formed, 3)}
        rows.append(row)
    return rows


# ---------------------------------------------------------------- observations (protocol E5)
def madau_dickinson(z):
    """log10 of the Madau and Dickinson (2014) fit, Salpeter IMF, converted to Chabrier by dividing by about 1.6 (the record's own statement)."""
    z = np.asarray(z, float)
    return np.log10(0.015 * (1 + z) ** 2.7 / (1 + ((1 + z) / 2.9) ** 5.6)) - math.log10(1.6)


def observational_table(Y, grid, fam_names, zs=(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0), sigma_obs=0.2):
    """Where the Madau and Dickinson curve sits in the ensemble at each redshift: ensemble median, minimum, maximum, the offset in units of the ensemble spread and of the observational error."""
    rows = []
    for z in zs:
        k = int(np.argmin(np.abs(grid - z)))
        col = Y[:, k]
        col = col[np.isfinite(col)]
        if col.size < MIN_FAMILIES:
            continue
        obs = float(madau_dickinson(grid[k]))
        sd = float(col.std(ddof=1))
        rows.append({"z": float(grid[k]), "n": int(col.size), "ensemble_median": float(np.median(col)), "ensemble_min": float(col.min()), "ensemble_max": float(col.max()), "ensemble_sd": sd, "observed": obs,
                     "offset_dex": float(np.median(col) - obs), "offset_in_sd": float((np.median(col) - obs) / sd) if sd > 0 else None, "sd_over_obs_error": float(sd / sigma_obs),
                     "observed_rank": int((col < obs).sum()), "inside_envelope": bool(col.min() <= obs <= col.max())})
    return rows


# ---------------------------------------------------------------- CAMELS (protocol E3, E4)
PARAMS = ["Om", "s8", "ASN1", "AAGN1", "ASN2", "AAGN2"]
CAMELS_Z = np.round(np.arange(0.1, 8.1001, 0.2), 1)
KERNEL_H = 0.5
RIDGE = 1e-3
LOW_C, HIGH_C = (0.1, 3.1), (3.1, 8.1)


def to_x(p):
    """The six parameters as coordinates in [-1, 1]."""
    return np.array([(p["Om"] - 0.3) / 0.2, (p["s8"] - 0.8) / 0.2, math.log(p["ASN1"]) / math.log(4), math.log(p["AAGN1"]) / math.log(4), math.log(p["ASN2"]) / math.log(2), math.log(p["AAGN2"]) / math.log(2)])


def load_camels(path=None):
    return json.loads(Path(path or ROOT / "data" / "ensembles" / "camels-sfrd.json").read_text())


def camels_arrays(data, suite, sset):
    zc = np.array(data["zCentres"])
    cols = [int(np.argmin(np.abs(zc - z))) for z in CAMELS_Z]
    sims = data["suites"][suite][sset]
    names = sorted(sims, key=lambda k: int(k.split("_")[1]))
    X = np.array([to_x(sims[n]["params"]) for n in names])
    Y = np.array([[np.nan if sims[n]["sfrd"][c] is None else sims[n]["sfrd"][c] for c in cols] for n in names], float)
    return names, X, Y


def kernel_weights(X, h=KERNEL_H):
    return np.exp(-0.5 * (X[:, 0] ** 2 + X[:, 1] ** 2) / h ** 2)


def fit_emulator(X, Y, degree=2, ridge=RIDGE, h=KERNEL_H):
    return ms.Emulator(degree, ridge).fit(X, Y, kernel_weights(X, h))


def astro_x(A, cosmo=(0.0, 0.0)):
    """Rows of four astrophysical coordinates as full six-dimensional emulator inputs at a fixed cosmology."""
    A = np.atleast_2d(A)
    X = np.empty((len(A), 2 + A.shape[1]))
    X[:, 0], X[:, 1], X[:, 2:] = cosmo[0], cosmo[1], A
    return X


def predict_astro(emu, A, cosmo=(0.0, 0.0)):
    return emu.predict(astro_x(A, cosmo))


def cv_errors(X, Y, degree=2, ridge=RIDGE, h=KERNEL_H, folds=10, seed=0):
    """Out-of-fold root mean square error per redshift on the simulations within 0.5 of the fiducial cosmology, 10 random folds."""
    n = len(X)
    rng = np.random.default_rng(seed)
    fold = rng.permutation(n) % folds
    pred = np.full(Y.shape, np.nan)
    for f in range(folds):
        tr, te = fold != f, fold == f
        emu = fit_emulator(X[tr], Y[tr], degree, ridge, h)
        pred[te] = emu.predict(X[te])
    near = (np.abs(X[:, 0]) <= 0.5) & (np.abs(X[:, 1]) <= 0.5)
    err = (pred - Y)[near]
    return np.sqrt(np.nanmean(err ** 2, axis=0)), int(near.sum())


def choose_degree(X, Y, ridge=RIDGE, h=KERNEL_H, zmax=6.5):
    """Degree 2 or 3: the one with the smaller mean cross-validation error over z <= zmax (degree 3 only if it improves it by more than 2 %)."""
    sel = CAMELS_Z <= zmax + 1e-9
    e2, _ = cv_errors(X, Y, 2, ridge, h)
    e3, _ = cv_errors(X, Y, 3, ridge, h)
    return (3 if np.nanmean(e3[sel]) < 0.98 * np.nanmean(e2[sel]) else 2), e2, e3


def seed_noise(Ycv):
    return np.nanstd(Ycv, axis=0, ddof=1)


def parametric_spread(emu, rng, n=20000, free_cosmo=False):
    """Standard deviation of the emulated y over the prior of the four astrophysical coordinates (cosmology fixed, or free), per redshift, with the 16th and 84th percentiles of the curve family."""
    A = rng.uniform(-1, 1, size=(n, 4))
    if free_cosmo:
        X = np.column_stack([rng.uniform(-1, 1, size=(n, 2)), A])
    else:
        X = astro_x(A)
    Yp = emu.predict(X)
    return np.nanstd(Yp, axis=0, ddof=1), np.nanpercentile(Yp, 16, axis=0), np.nanpercentile(Yp, 84, axis=0)


def _dist2(Pt, Ps, zsel):
    return np.mean((Pt[zsel] - Ps[zsel]) ** 2)


_EYE4 = np.eye(4)


def _grad_pred(emu, a, eps=1e-5):
    """Prediction and its Jacobian with respect to the four astrophysical coordinates (central differences in one batch)."""
    pts = np.vstack([a, a + eps * _EYE4, a - eps * _EYE4])
    P = predict_astro(emu, pts)
    return P[0], ((P[1:5] - P[5:9]) / (2 * eps)).T  # (nz,), (nz, 4)


def reachability(emu_t, emu_s, zsel, rng, lam=1.0, nstarts=24, iters=150):
    """Minimum over the astrophysical coordinates of both codes (each in [-lam, lam]) of the root mean square difference of their emulated curves over the grid points in zsel.
    Projected gradient descent with backtracking from the fiducial point and from nstarts random starts; returns the distance and the minimising coordinates."""
    zsel = zsel & np.isfinite(emu_t.coef).all(axis=0) & np.isfinite(emu_s.coef).all(axis=0)  # an emulator fitted on half of the simulations can lack a column that the full one has
    starts = [np.zeros(8)] + [rng.uniform(-lam, lam, 8) for _ in range(nstarts)]
    best = (np.inf, None)
    for a0 in starts:
        a = a0.copy()
        pt, Jt = _grad_pred(emu_t, a[:4])
        ps, Js = _grad_pred(emu_s, a[4:])
        f = _dist2(pt, ps, zsel)
        step = 0.5
        for _ in range(iters):
            r = (pt - ps)[zsel]
            g = np.concatenate([2 * (Jt[zsel].T @ r), -2 * (Js[zsel].T @ r)]) / zsel.sum()
            improved = False
            for _ in range(25):
                cand = np.clip(a - step * g, -lam, lam)
                ptc, Jtc = _grad_pred(emu_t, cand[:4])
                psc, Jsc = _grad_pred(emu_s, cand[4:])
                fc = _dist2(ptc, psc, zsel)
                if fc < f - 1e-14:
                    a, pt, Jt, ps, Js, f = cand, ptc, Jtc, psc, Jsc, fc
                    step *= 1.5
                    improved = True
                    break
                step *= 0.5
            if not improved:
                break
        if f < best[0]:
            best = (f, a.copy())
    return float(math.sqrt(best[0])), best[1]


def split_halves(n, rng):
    perm = rng.permutation(n)
    return perm[: n // 2], perm[n // 2:]


def predict_coords(emu, A):
    """Emulator at rows of four (cosmology fixed at the fiducial) or six (cosmology free) coordinates."""
    A = np.atleast_2d(A)
    return emu.predict(A) if A.shape[1] == 6 else predict_astro(emu, A)


def obs_covariance(sig_sys, box, emu_err, common=True):
    """Covariance of the target curve at the calibration redshifts: a systematic of sig_sys dex common to all of them (the normalisation, IMF and dust of the observed fit) or independent at each,
    plus the box and resolution allowance and the emulator error at each."""
    n = len(emu_err)
    return np.diag(box ** 2 + np.asarray(emu_err) ** 2) + sig_sys ** 2 * (np.ones((n, n)) if common else np.eye(n))


MIN_ESS = 5000


def calibrate(emu, z_idx, target, cov, rng, nprior=400000, chunk=100000, free_cosmo=False, min_ess=MIN_ESS, max_rounds=3):
    """Importance sampling of the posterior of the four astrophysical coordinates (six with cosmology free): prior uniform on [-1, 1], Gaussian likelihood of the target at the grid indices z_idx with covariance cov.
    The number of prior draws is multiplied by 4 (at most max_rounds times) while the effective sample size is below min_ess. Returns the posterior draws (resampled by weight), the effective sample size,
    the largest log-likelihood and the number of prior draws used. An emulator column that is undefined at a calibration redshift is an error, not a missing observation."""
    cinv = np.linalg.inv(cov)
    d = 6 if free_cosmo else 4
    for rnd in range(max_rounds + 1):
        As, lls = [], []
        for _ in range(max(1, nprior // chunk)):
            A = rng.uniform(-1, 1, size=(chunk, d))
            P = predict_coords(emu, A)[:, z_idx]
            if not np.isfinite(P).all():
                raise ValueError("emulator undefined at a calibration redshift")
            r = P - target
            lls.append(-0.5 * np.sum((r @ cinv) * r, axis=1))
            As.append(A)
        A, ll = np.vstack(As), np.concatenate(lls)
        w = np.exp(ll - ll.max())
        w /= w.sum()
        ess = float(1.0 / np.sum(w ** 2))
        if ess >= min_ess or rnd == max_rounds:
            break
        nprior *= 4
    idx = rng.choice(len(A), size=20000, p=w)
    return A[idx], ess, float(ll.max()), int(len(A))


def weighted_summary(emu, A, z_idx, noise=None, rng=None):
    """5th, 50th and 95th percentiles of the emulated curve at z_idx over the posterior draws A, optionally with independent Gaussian emulator error (standard deviations `noise` per redshift) added to each draw."""
    P = predict_coords(emu, A)[:, z_idx]
    if noise is not None:
        P = P + rng.normal(size=P.shape) * np.asarray(noise)
    return np.percentile(P, 5, axis=0), np.median(P, axis=0), np.percentile(P, 95, axis=0)


V4_Z_MAX = 6.0  # the emulator-against-CV-mean clause of V4 is stated for z up to 6 (protocol)
DEGREE_Z_MAX = 6.5  # degree choice: mean cross-validation error over z <= 6.5 (A1: set after the design check of section 8, where cross-validation errors were printed)
Z_OBS = [0.1, 0.5, 0.9, 1.3, 1.7, 2.1, 2.5, 2.9]
Z_TGT = [round(4.1 + 0.4 * k, 1) for k in range(10)]
BOX_ALLOWANCE = 0.15  # dex, the small box and low resolution of CAMELS
SIG_OBS = 0.2  # dex, the observational systematic
SPLIT_SEED_STREAM = 34


def emulator_error(info_suite):
    """Cross-validation error in excess of the seed noise, per redshift (zero where it is smaller)."""
    return np.sqrt(np.maximum(0.0, info_suite["cv_rmse"] ** 2 - info_suite["seed_noise"] ** 2))


def build_emulators(arr, degrees=None, ridge=RIDGE, h=KERNEL_H):
    """Emulators and their cross-validation summary per code; degrees: dict of fixed degrees, or None to choose per code (protocol E3)."""
    emus, info = {}, {}
    for suite, d in arr.items():
        if degrees and degrees.get(suite):
            deg, e2, e3 = degrees[suite], None, None
        else:
            deg, e2, e3 = choose_degree(d["X"], d["Y"], ridge, h, zmax=DEGREE_Z_MAX)
        emus[suite] = fit_emulator(d["X"], d["Y"], deg, ridge, h)
        cv, ncv = cv_errors(d["X"], d["Y"], deg, ridge, h, seed=1)  # a fold assignment different from the one that chose the degree
        sn = seed_noise(d["Ycv"])
        info[suite] = {"degree": deg, "cv_rmse": cv, "seed_noise": sn, "cv_mean": np.nanmean(d["Ycv"], axis=0), "cv_se": sn / np.sqrt(np.isfinite(d["Ycv"]).sum(axis=0)), "emulator_at_fiducial": predict_astro(emus[suite], np.zeros((1, 4)))[0],
                       "n_cv_test": ncv, "cv_rmse_degree2_mean": None if e2 is None else float(np.nanmean(e2[CAMELS_Z <= DEGREE_Z_MAX + 1e-9])), "cv_rmse_degree3_mean": None if e3 is None else float(np.nanmean(e3[CAMELS_Z <= DEGREE_Z_MAX + 1e-9]))}
    return emus, info


def calibrate_codes(emus, info, arr, rng, sig_sys=SIG_OBS, common=True, free_cosmo=False):
    """E4 for both codes. Returns the dictionary reported under 'calibration'."""
    zi_obs = np.array([int(np.argmin(np.abs(CAMELS_Z - z))) for z in Z_OBS])
    zi_tgt = np.array([int(np.argmin(np.abs(CAMELS_Z - z))) for z in Z_TGT])
    target = madau_dickinson(CAMELS_Z[zi_obs])
    out = {"z_obs": Z_OBS, "z_target": Z_TGT, "target": [float(v) for v in target], "systematic_dex": sig_sys, "common_systematic": bool(common), "cosmology_free": bool(free_cosmo), "codes": {}}
    res = {}
    for suite in arr:
        err = emulator_error(info[suite])
        cov = obs_covariance(sig_sys, BOX_ALLOWANCE, err[zi_obs], common)
        post, ess, llmax, nused = calibrate(emus[suite], zi_obs, target, cov, rng, free_cosmo=free_cosmo)
        lo, med, hi = weighted_summary(emus[suite], post, zi_tgt, noise=err[zi_tgt], rng=rng)
        lo_o, med_o, hi_o = weighted_summary(emus[suite], post, zi_obs)
        res[suite] = (lo, med, hi)
        r = target - np.median(predict_coords(emus[suite], post)[:, zi_obs], axis=0)
        out["codes"][suite] = {"ess": ess, "n_prior": nused, "chi2_min": float(-2 * llmax), "sigma_obs_total": [float(v) for v in np.sqrt(np.diag(cov))], "residual_median_fit": [float(v) for v in r],
                               "posterior_median_coordinates": [float(v) for v in np.median(post, axis=0)], "posterior_p16_coordinates": [float(v) for v in np.percentile(post, 16, axis=0)], "posterior_p84_coordinates": [float(v) for v in np.percentile(post, 84, axis=0)],
                               "predictive": {"p5": [float(v) for v in lo], "median": [float(v) for v in med], "p95": [float(v) for v in hi]},
                               "fit_to_observed": {"p5": [float(v) for v in lo_o], "median": [float(v) for v in med_o], "p95": [float(v) for v in hi_o]}, "interval_width": [float(h_ - l_) for l_, h_ in zip(lo, hi)]}
    lt, mt, ht = res["IllustrisTNG"]
    ls, ms_, hs = res["SIMBA"]
    disjoint = (ht < ls) | (hs < lt)
    wt, ws = ht - lt, hs - ls
    out["disjoint_fraction"] = float(disjoint.mean())
    out["median_difference"] = [float(v) for v in (mt - ms_)]
    out["verdict"] = "structural" if disjoint.mean() >= 0.5 else ("parametric" if disjoint.sum() == 0 else "mixed")
    lowmask = np.array(Z_TGT) <= 4.9 + 1e-9  # the three lowest targets against the other seven
    out["width_ratio_high_over_low"] = {"IllustrisTNG": float(wt[~lowmask].mean() / wt[lowmask].mean()), "SIMBA": float(ws[~lowmask].mean() / ws[lowmask].mean())}
    return out


def e3_verdict(between, control, margin):
    """A1 rule. structural: the 5th percentile of the between-code distance (half-sized emulators of both codes, random splits) exceeds both the 95th percentile of the same-code controls built the same way and the margin;
    removable: its 95th percentile is below the margin; otherwise unresolved. The margin is the root mean square difference between two seeds of the two codes: sqrt(seed_noise_TNG^2 + seed_noise_SIMBA^2)."""
    if pct(between, 5) > max(pct(control, 95), margin):
        return "structural"
    if pct(between, 95) < margin:
        return "removable"
    return "unresolved"


def reach_splits(arr, degrees, zsets, rng, nsplit, nstarts, bands_splits):
    """Matched-size comparison. In each split both codes' LH sets are divided at random into two halves A and B; between = D(TNG A, SIMBA A); controls = D(TNG A, TNG B) and D(SIMBA A, SIMBA B). All three use emulators
    trained on 500 simulations and the same search effort, so emulation noise enters between and control alike."""
    out = {name: {"between": [], "control_IllustrisTNG": [], "control_SIMBA": []} for name in zsets}
    for k in range(nsplit):
        parts = {}
        for suite, d in arr.items():
            ia, ib = split_halves(len(d["X"]), rng)
            parts[suite] = (fit_emulator(d["X"][ia], d["Y"][ia], degrees[suite]), fit_emulator(d["X"][ib], d["Y"][ib], degrees[suite]))
        for name, zs in zsets.items():
            if name != "full" and k >= bands_splits:
                continue
            out[name]["between"].append(reachability(parts["IllustrisTNG"][0], parts["SIMBA"][0], zs, rng, nstarts=nstarts)[0])
            for suite in arr:
                out[name]["control_" + suite].append(reachability(parts[suite][0], parts[suite][1], zs, rng, nstarts=nstarts)[0])
    return out


def camels_sensitivity(arr, degrees, rng_seed, nstarts):
    """S8 and S9: the emulator and error choices of E3 (point distance) and E4, and cosmology free in E4 and in the parametric spread."""
    out = {}
    cfgs = [("S8_degree2", dict(degrees={s: 2 for s in arr})), ("S8_degree3", dict(degrees={s: 3 for s in arr})), ("S8_kernel0.35", dict(h=0.35)), ("S8_kernel0.8", dict(h=0.8)), ("S8_ridge1e-2", dict(ridge=1e-2)), ("S8_ridge1e-4", dict(ridge=1e-4))]
    for k, (name, kw) in enumerate(cfgs):
        kw = {"degrees": degrees, **kw}
        emus, info = build_emulators(arr, **kw)
        full = np.isfinite(emus["IllustrisTNG"].coef).all(axis=0) & np.isfinite(emus["SIMBA"].coef).all(axis=0)
        d, _ = reachability(emus["IllustrisTNG"], emus["SIMBA"], full, np.random.default_rng([rng_seed, 37, k]), nstarts=nstarts * 2)
        cal = calibrate_codes(emus, info, arr, np.random.default_rng([rng_seed, 38, k]))
        out[name] = {"degree": {s: info[s]["degree"] for s in info}, "D_full_dex": d, "E4_verdict": cal["verdict"], "E4_disjoint_fraction": cal["disjoint_fraction"], "E4_width_ratio": cal["width_ratio_high_over_low"], "ess_min": min(c["ess"] for c in cal["codes"].values())}
    emus, info = build_emulators(arr, degrees=degrees)
    for k, (name, kw) in enumerate([("S8_obs_systematic_0.1", dict(sig_sys=0.1)), ("S8_obs_systematic_0.4", dict(sig_sys=0.4)), ("S8_independent_systematic", dict(common=False))]):
        cal = calibrate_codes(emus, info, arr, np.random.default_rng([rng_seed, 39, k]), **kw)
        out[name] = {"E4_verdict": cal["verdict"], "E4_disjoint_fraction": cal["disjoint_fraction"], "E4_width_ratio": cal["width_ratio_high_over_low"], "ess_min": min(c["ess"] for c in cal["codes"].values())}
    emus9, info9 = build_emulators(arr, degrees={s: 2 for s in arr}, h=100.0)  # uniform weights: cosmology is free, so the emulator must not be concentrated at the fiducial one
    cal = calibrate_codes(emus9, info9, arr, np.random.default_rng([rng_seed, 40]), free_cosmo=True)
    sd = {s: parametric_spread(emus9[s], np.random.default_rng([rng_seed, 41]), free_cosmo=True)[0] for s in arr}
    lo, hi = band_mask(CAMELS_Z, LOW_C), band_mask(CAMELS_Z, HIGH_C)
    out["S9_cosmology_free"] = {"E4_verdict": cal["verdict"], "E4_disjoint_fraction": cal["disjoint_fraction"], "E4_width_ratio": cal["width_ratio_high_over_low"], "ess_min": min(c["ess"] for c in cal["codes"].values()),
                                "parametric_rms": {s: {"low": float(np.sqrt(np.nanmean(sd[s][lo] ** 2))), "high": float(np.sqrt(np.nanmean(sd[s][hi] ** 2)))} for s in arr}}
    return out


def run_camels(recs, rng_seed, nboot=200, ncontrol=200, nstarts=4, fast=False, sensitivity=True):
    """E3 and E4 and the validations V1 to V4 on the CAMELS ensembles, and S8 and S9. Each randomised component has its own stream, so changing one does not move the others."""
    data = load_camels()
    out = {"codes": {}, "meta": {"zEdges": data["zEdges"], "grid": [float(z) for z in CAMELS_Z], "n_lh": 1000, "n_cv": 27, "n_lh_found": {}, "n_cv_found": {}}}
    arr = {}
    for suite in ("IllustrisTNG", "SIMBA"):
        names, X, Y = camels_arrays(data, suite, "LH")
        _, Xc, Yc = camels_arrays(data, suite, "CV")
        arr[suite] = {"X": X, "Y": Y, "Ycv": Yc, "names": names}
        out["meta"]["n_lh_found"][suite], out["meta"]["n_cv_found"][suite] = len(names), len(Yc)
    # emulators, degree, cross-validation (V4)
    emus, info = build_emulators(arr)
    degrees = {s: info[s]["degree"] for s in info}
    ok_z = CAMELS_Z <= V4_Z_MAX + 1e-9
    for suite, d in arr.items():
        inf = info[suite]
        ratio = inf["cv_rmse"] / inf["seed_noise"]
        tol = np.maximum(0.05, 2 * inf["cv_se"])
        diff = np.abs(inf["emulator_at_fiducial"] - inf["cv_mean"])
        inf["nan_fraction_lh"] = [float(np.isnan(d["Y"][:, k]).mean()) for k in range(len(CAMELS_Z))]
        out["codes"][suite] = {"degree": inf["degree"], "cv_rmse_degree2_mean": inf["cv_rmse_degree2_mean"], "cv_rmse_degree3_mean": inf["cv_rmse_degree3_mean"], "nan_fraction_lh": inf["nan_fraction_lh"],
                               "v4": {"max_cv_over_seed": float(np.nanmax(ratio)), "cv_over_seed_by_z": [None if not np.isfinite(v) else float(v) for v in ratio], "n_ratio_undefined": int((~np.isfinite(ratio)).sum()),
                                      "emulator_minus_cv_mean_max_abs_z_le_6": float(np.nanmax(diff[ok_z])), "within_tolerance": bool(np.all((diff <= tol)[ok_z])), "ratio_ok": bool(np.all(ratio[np.isfinite(ratio)] <= 1.5))},
                               "seed_noise": [None if not np.isfinite(v) else float(v) for v in inf["seed_noise"]]}
    # parametric spread
    rng = np.random.default_rng([rng_seed, 31])
    lo, hi = band_mask(CAMELS_Z, LOW_C), band_mask(CAMELS_Z, HIGH_C)
    for suite in arr:
        sd, p16, p84 = parametric_spread(emus[suite], rng)
        sdc, _, _ = parametric_spread(emus[suite], rng, free_cosmo=True)
        out["codes"][suite]["parametric"] = {"sd": [float(v) for v in sd], "p16": [float(v) for v in p16], "p84": [float(v) for v in p84], "sd_cosmology_free": [float(v) for v in sdc],
                                              "rms_low": float(np.sqrt(np.nanmean(sd[lo] ** 2))), "rms_high": float(np.sqrt(np.nanmean(sd[hi] ** 2))), "ratio_high_over_low": float(np.sqrt(np.nanmean(sd[hi] ** 2) / np.nanmean(sd[lo] ** 2)))}
    # structural offset at the fiducial parameters
    t, s = info["IllustrisTNG"], info["SIMBA"]
    delta = t["cv_mean"] - s["cv_mean"]
    se = np.sqrt(t["cv_se"] ** 2 + s["cv_se"] ** 2)  # the CV seeds are shared between the codes, so this independent estimate is conservative
    out["structural_fiducial"] = {"delta": [None if not np.isfinite(v) else float(v) for v in delta], "se": [None if not np.isfinite(v) else float(v) for v in se],
                                  "rms_low": float(np.sqrt(np.nanmean(delta[lo] ** 2))), "rms_high": float(np.sqrt(np.nanmean(delta[hi] ** 2))), "rms_all": float(np.sqrt(np.nanmean(delta ** 2)))}
    # reachability (E3): point distances, full-size bootstrap (reported), matched-size splits (verdict)
    full = np.isfinite(emus["IllustrisTNG"].coef).all(axis=0) & np.isfinite(emus["SIMBA"].coef).all(axis=0)
    zsets = {"full": full, "low": full & lo, "high": full & hi}
    out["reachability"] = {"z_used": [float(z) for z in CAMELS_Z[full]]}
    rr = np.random.default_rng([rng_seed, 32])
    for name, zs in zsets.items():
        d, a = reachability(emus["IllustrisTNG"], emus["SIMBA"], zs, rr, nstarts=nstarts * 2)
        out["reachability"][name] = {"D_dex": d, "a_tng": [float(v) for v in a[:4]], "a_simba": [float(v) for v in a[4:]], "D_fiducial_dex": float(np.sqrt(np.nanmean(delta[zs] ** 2)))}
    out["reachability"]["shrunk"] = {}
    for lam in (0.25, 0.5, 0.75, 1.0):
        d, _ = reachability(emus["IllustrisTNG"], emus["SIMBA"], zsets["full"], rr, lam=lam, nstarts=nstarts)
        out["reachability"]["shrunk"][str(lam)] = d
    if nboot > 0:
        rb = np.random.default_rng([rng_seed, 33])
        boot = []
        for _ in range(nboot):
            e = {}
            for suite, d in arr.items():
                ix = rb.integers(0, len(d["X"]), len(d["X"]))
                e[suite] = fit_emulator(d["X"][ix], d["Y"][ix], degrees[suite])
            boot.append(reachability(e["IllustrisTNG"], e["SIMBA"], zsets["full"], rb, nstarts=nstarts)[0])
        boot = np.array(boot)
        out["reachability"]["bootstrap_full"] = {"n": int(boot.size), "p5": pct(boot, 5), "p50": pct(boot, 50), "p95": pct(boot, 95), "note": "full-size emulators on resampled simulations (duplicate rows make them noisier than the point fit); reported, not used for the verdict"}
    else:
        out["reachability"]["bootstrap_full"] = None
    sp = reach_splits(arr, degrees, zsets, np.random.default_rng([rng_seed, SPLIT_SEED_STREAM]), ncontrol, nstarts, max(20, ncontrol // 2))
    ctl = {name: np.array(v["control_IllustrisTNG"] + v["control_SIMBA"]) for name, v in sp.items()}
    btw = {name: np.array(v["between"]) for name, v in sp.items()}
    margin = float(np.sqrt(np.nanmean(t["seed_noise"][full] ** 2 + s["seed_noise"][full] ** 2)))
    out["reachability"]["margin_dex"] = margin
    out["reachability"]["between_full"] = {"n": int(btw["full"].size), "p5": pct(btw["full"], 5), "p50": pct(btw["full"], 50), "p95": pct(btw["full"], 95)}
    out["reachability"]["controls_full"] = {"n_per_code": ncontrol, "emulator_training_size": 500, "median": pct(ctl["full"], 50), "p95": pct(ctl["full"], 95), "p95_tng": pct(np.array(sp["full"]["control_IllustrisTNG"]), 95), "p95_simba": pct(np.array(sp["full"]["control_SIMBA"]), 95),
                                            "median_tng": pct(np.array(sp["full"]["control_IllustrisTNG"]), 50), "median_simba": pct(np.array(sp["full"]["control_SIMBA"]), 50)}
    out["reachability"]["verdict"] = e3_verdict(btw["full"], ctl["full"], margin)
    out["reachability"]["controls_bands"] = {nm: {"median": pct(ctl[nm], 50), "p95": pct(ctl[nm], 95), "n": int(ctl[nm].size)} for nm in ("low", "high")}
    out["reachability"]["between_bands"] = {nm: {"p5": pct(btw[nm], 5), "p50": pct(btw[nm], 50), "p95": pct(btw[nm], 95), "n": int(btw[nm].size), "verdict": e3_verdict(btw[nm], ctl[nm], float(np.sqrt(np.nanmean(t["seed_noise"][zsets[nm]] ** 2 + s["seed_noise"][zsets[nm]] ** 2))))} for nm in ("low", "high")}
    # calibrate and extrapolate (E4)
    out["calibration"] = calibrate_codes(emus, info, arr, np.random.default_rng([rng_seed, 35]))
    if sensitivity:
        out["sensitivity"] = camels_sensitivity(arr, degrees, rng_seed, nstarts)
    # V2 and V3
    if recs is None:
        out["v2"] = out["v3"] = None
    else:
        tng_f = recs["pillepich18.tng-l25n512.fiducial.sfrd"]
        sel = (CAMELS_Z >= 0.5 - 1e-9) & (CAMELS_Z <= 5.0 + 1e-9)
        base = predict_astro(emus["IllustrisTNG"], np.zeros((1, 4)))[0]
        v2 = {}
        for key, rid, a in (("A_SN1=2", "pillepich18.tng-l25n512.var-stronger-winds-x2.sfrd", [0.5, 0, 0, 0]), ("A_SN2=2", "pillepich18.tng-l25n512.var-faster-winds-x2.sfrd", [0, 0, 1.0, 0])):
            camels_shift = predict_astro(emus["IllustrisTNG"], np.array([a]))[0] - base
            meth = on_grid(recs[rid], CAMELS_Z, 0.1) - on_grid(tng_f, CAMELS_Z, 0.1)
            ok = sel & np.isfinite(meth) & np.isfinite(camels_shift)
            v2[key] = {"rms_difference_dex": float(np.sqrt(np.mean((camels_shift - meth)[ok] ** 2))), "rms_shift_methods_dex": float(np.sqrt(np.mean(meth[ok] ** 2))), "n_z": int(ok.sum()), "camels_shift_mean": float(camels_shift[ok].mean()), "methods_shift_mean": float(meth[ok].mean())}
        out["v2"] = {**v2, "passed": bool(all(v["rms_difference_dex"] <= 0.15 for v in v2.values()))}
        pub = on_grid(recs["dave19.simba.sfrd.m100n1024"], CAMELS_Z, 0.1)
        sel3 = (CAMELS_Z >= 0.5 - 1e-9) & (CAMELS_Z <= 4.0 + 1e-9) & np.isfinite(pub) & np.isfinite(s["cv_mean"])
        out["v3"] = {"mean_difference_dex": float(np.mean((s["cv_mean"] - pub)[sel3])), "max_abs_difference_dex": float(np.max(np.abs((s["cv_mean"] - pub)[sel3]))), "n_z": int(sel3.sum())}
        out["v3"]["passed"] = bool(abs(out["v3"]["mean_difference_dex"]) <= 0.3)
    cp = ROOT / "data" / "ensembles" / "camels-closure.json"
    out["v1"] = json.loads(cp.read_text()) if cp.exists() and recs is not None else None
    out["v4"] = {k: v["v4"] for k, v in out["codes"].items()}
    out["_internal"] = {"emulators": emus, "arrays": arr, "info": info}
    return out


# ---------------------------------------------------------------- the published ensemble (E1, E2, E5, V5 and sensitivities)
def summarize_draws(draws):
    """Median and 95 % range of phi over the S5 draws, the success rate, and both by the number of balanced families (a draw can remove a family from the balanced set by choosing a variant that does not reach both bands)."""
    phis = np.array([d[0] for d in draws])
    nb = np.array([d[2] for d in draws])
    return {"draws": len(draws), "phi_median": float(np.median(phis)), "phi_p2.5": pct(phis, 2.5), "phi_p97.5": pct(phis, 97.5), "fraction_success": float(np.mean([d[1] for d in draws])),
            "by_n_balanced": {str(int(n)): {"draws": int((nb == n).sum()), "phi_median": float(np.median(phis[nb == n])), "fraction_success": float(np.mean([d[1] for d, m in zip(draws, nb == n) if m]))} for n in sorted(set(nb.tolist()))}}


def success(r):
    return bool(r.get("phi_ci90") and r["phi_ci90"][0] > 0 and r["pitman_morgan"]["p_one_sided"] < 0.05)


def run_pub(recs, variants, rng_seed, nboot=NBOOT, nrand=200):
    grid = Z_PUB
    fids = eligible_fiducials(recs, variants)
    fams = sorted(fids)
    Y = family_matrix(recs, variants, [fids[f] for f in fams], grid)
    out = {"families": {f: {"record": fids[f], "z_range": [float(curve_arrays(recs[fids[f]])[0][0]), float(curve_arrays(recs[fids[f]])[0][-1])], "box_note": recs[fids[f]].get("run")} for f in fams}}
    out["E1"] = pub_funnel(Y, grid, np.random.default_rng([rng_seed, 11]), nboot)
    bal = balanced_rows(Y, grid)
    out["E1"]["balanced_families"] = [f for f, b in zip(fams, bal) if b]
    out["E1"]["success"] = success(out["E1"])
    # sensitivities
    sens = {}

    def run_variant(fid_map, grid_=grid, bands=BANDS, imf=False, window=WINDOW, seed=0, n=None):
        n = n or max(200, nboot // 3)
        names = sorted(fid_map)
        M = family_matrix(recs, variants, [fid_map[f] for f in names], grid_, imf=imf, window=window)
        r = pub_funnel(M, grid_, np.random.default_rng([rng_seed, 12, seed]), n, bands)
        return {"n_families": r["n_families"], "n_balanced": r["n_balanced"], "phi": r.get("phi"), "phi_ci90": r.get("phi_ci90"), "pitman_morgan_p": r.get("pitman_morgan", {}).get("p_one_sided"), "success": success(r), "sd_low": r.get("sd_low"), "sd_high": r.get("sd_high"),
                "slope_dex_per_z": r.get("slope_dex_per_z")}
    sens["S1_add_simba_horizon"] = run_variant(eligible_fiducials(recs, variants, extra=("SIMBA", "Horizon-AGN")), seed=1)
    sens["S2_exclude_small_boxes"] = run_variant({f: i for f, i in fids.items() if f not in ("FIREbox", "Romulus25")}, seed=2)
    sens["S3_alternative_bands"] = run_variant(fids, bands={"low": (0.25, 2.0), "high": (4.0, 6.5)}, seed=3)
    sens["S4_chabrier_equivalent"] = run_variant(fids, imf=True, seed=4)
    sens["S7_window_0.0625"] = run_variant(fids, window=0.0625, seed=5)
    sens["S7_window_0.25"] = run_variant(fids, window=0.25, seed=6)
    sens["S6_leave_one_family_out"] = {f: run_variant({g: i for g, i in fids.items() if g != f}, seed=10 + k, n=max(200, nboot // 5)) for k, f in enumerate(fams)}
    rr = np.random.default_rng([rng_seed, 13])
    draws = []
    for k in range(nrand):
        fm = random_fiducials(recs, variants, rr)
        names = sorted(fm)
        M = family_matrix(recs, variants, [fm[f] for f in names], grid)
        r = pub_funnel(M, grid, np.random.default_rng([rng_seed, 14, k]), 300)
        if "phi_ci90" in r:
            draws.append((r["phi"], success(r), r["n_balanced"]))
    sens["S5_random_numerical_fiducial"] = summarize_draws(draws)
    rr2 = np.random.default_rng([rng_seed, 16])
    draws2 = []
    for k in range(nrand):
        fm = random_fiducials(recs, variants, rr2, both_bands=True)
        names = sorted(fm)
        M = family_matrix(recs, variants, [fm[f] for f in names], grid)
        r = pub_funnel(M, grid, np.random.default_rng([rng_seed, 17, k]), 300)
        if "phi_ci90" in r:
            draws2.append((r["phi"], success(r), r["n_balanced"]))
    sens["S5b_random_numerical_fiducial_both_bands"] = summarize_draws(draws2)
    out["sensitivity"] = sens
    # E2
    rb = np.random.default_rng([rng_seed, 15])
    tr = tier_rms(recs, variants, grid, by_family=True)
    trp = tier_rms(recs, variants, grid, by_family=False)
    tb = tier_rms_bootstrap(recs, variants, grid, rb)
    out["E2"] = {"by_family": tr, "pooled": trp, "pooled_interval90": tb, "S_band": {"low": out["E1"].get("sd_low"), "high": out["E1"].get("sd_high")}}
    # V5 and E5
    runs = [("COLIBRE m6 L200", "schaye25.colibre.sfrd.m6-l200", "chaikin26.colibre.smd.l200m6.all"), ("EAGLE Ref-L100N1504", "furlong15.eagle.sfrd.refl100n1504", "vcd.eagle.ref-l100n1504-all-stars.smd.z2.749"),
            ("FIREbox", "feldmann23.firebox.sfrd.all", "feldmann23.firebox.smd.all")]
    allrecs = {**recs}
    for f in sorted((ROOT / "data" / "curves").glob("*.json")):
        for r in json.loads(f.read_text())["records"]:
            if r["relation"] == "smd" and r["kind"] == "simulation":
                allrecs[r["id"]] = r
    ct = closure_table(allrecs, runs)
    out["V5"] = {"runs": ct, "n_evaluated": int(sum(len(r["R_eff"]) for r in ct)), "n_requested": int(len(ct) * len(V5_Z)), "passed": bool(all(0.15 <= v["R_eff"] <= 0.60 for r in ct for v in r["R_eff"].values()))}
    Yc = family_matrix(recs, variants, [fids[f] for f in fams], grid, imf=True)
    out["E5"] = {"table": observational_table(Yc, grid, fams), "sigma_obs": 0.2, "note": "ensemble converted to a Chabrier IMF with the website's offsets; Madau and Dickinson (2014) divided by 1.6"}
    gh = np.array([9.0, 12.0, 16.0])  # the redshifts of the Harikane et al. points (protocol section 2.3); a redshift reached by fewer than 5 families is skipped
    Yh = family_matrix(recs, variants, [fids[f] for f in fams], gh, imf=True)
    hz = harikane_rows()
    rows = []
    for k, z in enumerate(gh):
        col = Yh[:, k][np.isfinite(Yh[:, k])]
        h = next((r for r in hz if abs(r[0] - z) < 0.1), None)
        if h is None or col.size < MIN_FAMILIES:
            continue
        sh = -math.log10(1.6)
        rows.append({"z": float(z), "n": int(col.size), "ensemble_median": float(np.median(col)), "ensemble_min": float(col.min()), "ensemble_max": float(col.max()), "ensemble_sd": float(col.std(ddof=1)),
                     "observed": h[1] + sh, "observed_low": h[2] + sh, "observed_high": h[3] + sh, "offset_dex": float(np.median(col) - (h[1] + sh)), "inside_envelope": bool(col.min() <= h[1] + sh <= col.max())})
    out["E5"]["high_z"] = rows
    return out, Y, fams


def harikane_rows(recs_path=ROOT / "data" / "curves"):
    rows = []
    for f in sorted(recs_path.glob("*.json")):
        for r in json.loads(f.read_text())["records"]:
            if r["id"] == "harikane23.sfrd.dustcorr":
                rows = [(p["x"], p["y"], p["yLow"], p["yHigh"]) for p in r["representation"]["points"]]
    return rows


# ---------------------------------------------------------------- assembly
def run(nboot=NBOOT, nrand=200, camels_kw=None):
    recs = load_sfrd()
    variants = load_variants()
    pub, Y, fams = run_pub(recs, variants, SEED, nboot, nrand)
    cam = run_camels(recs, SEED, **(camels_kw or {}))
    cam.pop("_internal")
    res = {"version": json.loads((ROOT / "data" / "release.json").read_text())["version"], "protocol": "docs/PROTOCOL-model-form.md",
           "parameters": {"seed": SEED, "grid_published": [float(z) for z in Z_PUB], "window": WINDOW, "bands_published": {k: list(v) for k, v in BANDS.items()}, "bands_camels": {"low": list(LOW_C), "high": list(HIGH_C)}, "min_families": MIN_FAMILIES,
                          "bootstrap": nboot, "random_fiducial_draws": nrand, "kernel_bandwidth": KERNEL_H, "ridge": RIDGE},
           "published": pub, "camels": cam}
    res["verdicts"] = verdicts(res)
    res["deviations"] = deviations(res)
    return res


def verdicts(res):
    e1 = res["published"]["E1"]
    c = res["camels"]
    return {"E1": {"success": e1["success"], "phi": e1.get("phi"), "phi_ci90": e1.get("phi_ci90"), "pitman_morgan_p": e1.get("pitman_morgan", {}).get("p_one_sided"), "sd_low": e1.get("sd_low"), "sd_high": e1.get("sd_high"), "n_balanced": e1.get("n_balanced")},
            "E3": {"verdict": c["reachability"]["verdict"], "D_full": c["reachability"]["full"]["D_dex"], "between_p5": c["reachability"]["between_full"]["p5"], "between_p95": c["reachability"]["between_full"]["p95"], "control_p95": c["reachability"]["controls_full"]["p95"], "margin": c["reachability"]["margin_dex"]},
            "E4": {"verdict": c["calibration"]["verdict"], "disjoint_fraction": c["calibration"]["disjoint_fraction"]},
            "validations": {"V1": None if c["v1"] is None else c["v1"]["passed"], "V2": c["v2"]["passed"], "V3": c["v3"]["passed"], "V4": {k: v for k, v in {s: (c["v4"][s]["ratio_ok"] and c["v4"][s]["within_tolerance"]) for s in c["v4"]}.items()}, "V5": res["published"]["V5"]["passed"]}}


def deviations(res):
    """What the code did that the protocol (with amendment A1) does not describe, or could not do."""
    d = []
    c = res["camels"]
    if c["v1"] is None:
        d.append("Validation V1 could not be evaluated: data/ensembles/camels-closure.json is missing (run scripts/validate_camels_closure.py).")
    elif not c["v1"].get("volume_check"):
        d.append("Validation V1 was evaluated without the volume check of amendment A1 (camels-closure.json predates it).")
    for s_, n in c["meta"]["n_lh_found"].items():
        if n != 1000 or c["meta"]["n_cv_found"][s_] != 27:
            d.append(f"{s_}: {n} LH and {c['meta']['n_cv_found'][s_]} CV simulations were found, not 1000 and 27.")
    for s_, k in c["calibration"]["codes"].items():
        if k["ess"] < 5000:
            d.append(f"E4 {s_}: the effective sample size stayed below 5000 ({k['ess']:.0f}) after {k['n_prior']} prior draws.")
    v5 = res["published"]["V5"]
    if v5["n_evaluated"] < v5["n_requested"]:
        miss = [f"{r['run']} z = {', '.join(str(z) for z in r['not_evaluated'])}" for r in v5["runs"] if r["not_evaluated"]]
        d.append(f"V5 was evaluated at {v5['n_evaluated']} of {v5['n_requested']} run-redshift pairs; not evaluated: {'; '.join(miss)}.")
    d.append("Sensitivity S9 (cosmology free) was run for the parametric spread and E4 only: the reachability search over six coordinates per code was dropped (amendment A1).")
    return d


def write_outputs(res):
    out = ROOT / "data" / "analysis" / "model-form.json"
    out.write_text(json.dumps(res, indent=1, default=lambda o: float(o) if isinstance(o, np.floating) else int(o) if isinstance(o, np.integer) else bool(o) if isinstance(o, np.bool_) else str(o)) + "\n")
    (ROOT / "docs" / "ANALYSIS-model-form.md").write_text(render(res))


def _f(v, d=3, sign=False):
    return "n/a" if v is None or (isinstance(v, float) and not np.isfinite(v)) else (f"{v:+.{d}f}" if sign else f"{v:.{d}f}")


def _ci(c, d=2):
    return "n/a" if not c else f"[{c[0]:.{d}f}, {c[1]:.{d}f}]"


def _table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def _yn(b):
    return "yes" if b else "no"


def headline(res):
    """The result in words, assembled by fixed rules from the numbers; nothing is added after the run."""
    v, p, c = res["verdicts"], res["published"], res["camels"]
    e1, out = p["E1"], []
    ratio = 10 ** e1["phi"] if e1.get("phi") is not None else None
    if v["E1"]["success"]:
        out.append(f"**E1 - funnel detected.** Across {e1['n_balanced']} families the standard deviation of the SFRD (dex) grows from {_f(e1['sd_low'])} at z = 0.5 to 3 to {_f(e1['sd_high'])} at z = 5 to 7.5, a factor {ratio:.1f} (phi = {_f(e1['phi'])}, "
                   f"90 % bootstrap interval {_ci(e1['phi_ci90'])}; Pitman-Morgan p = {_f(e1['pitman_morgan']['p_one_sided'], 4)}). The rule fixed in advance is met.")
    else:
        why = []
        if not e1["phi_ci90"][0] > 0:
            why.append(f"the lower end of the bootstrap interval ({_f(e1['phi_ci90'][0])}) is not above 0")
        if not e1["pitman_morgan"]["p_one_sided"] < 0.05:
            why.append(f"the Pitman-Morgan p-value is {_f(e1['pitman_morgan']['p_one_sided'], 3)}, not below 0.05")
        out.append(f"**E1 - no funnel detected.** The spread is {_f(e1['sd_low'])} dex at z = 0.5 to 3 and {_f(e1['sd_high'])} dex at z = 5 to 7.5 across {e1['n_balanced']} families (phi = {_f(e1['phi'])}, 90 % interval {_ci(e1['phi_ci90'])}); by the rule fixed in advance this is not a detection because "
                   + "; ".join(why) + ". With this many families a funnel of a factor three would be detected about two times in three (protocol, section 5).")
    r = c["reachability"]
    rv = r["verdict"]
    out.append(f"**E3 - reachability.** Retuning the four feedback parameters of each code within the CAMELS ranges, IllustrisTNG and SIMBA come no closer than {_f(r['full']['D_dex'])} dex rms in the SFRD over z = {r['z_used'][0]} to {r['z_used'][-1]} "
               f"(emulators on random halves of the simulations, 500 per code: 5th to 95th percentile {_f(r['between_full']['p5'])} to {_f(r['between_full']['p95'])}); the same code against its other half leaves {_f(r['controls_full']['median'])} (median) and at most {_f(r['controls_full']['p95'])} "
               f"(95th percentile), and two seeds of these two codes differ by {_f(r['margin_dex'])} dex rms. At the fiducial parameters they are {_f(r['full']['D_fiducial_dex'])} dex apart. By the rule fixed in advance (amendment A1) the difference is **{rv}**.")
    k = c["calibration"]
    out.append(f"**E4 - calibrate and extrapolate.** Tuned to the same observed SFRD at z <= 3, the two codes' 90 % intervals for the response of the model at z = {k['z_target'][0]} to {k['z_target'][-1]} are disjoint at {100 * k['disjoint_fraction']:.0f} % of the redshifts: **{k['verdict']}** disagreement after calibration. "
               f"Interval widths grow with redshift by a factor {_f(k['width_ratio_high_over_low']['IllustrisTNG'], 1)} (IllustrisTNG) and {_f(k['width_ratio_high_over_low']['SIMBA'], 1)} (SIMBA) from the three lowest targets (z <= 4.9) to the other seven.")
    val = v["validations"]
    bad = [n for n, ok in (("V1", val["V1"]), ("V2", val["V2"]), ("V3", val["V3"]), ("V4 IllustrisTNG", val["V4"]["IllustrisTNG"]), ("V4 SIMBA", val["V4"]["SIMBA"]), ("V5", val["V5"])) if ok is False]
    out.append("**Validations.** " + ("All five hold." if not bad and None not in val.values() else f"Not all hold: {', '.join(bad) if bad else 'some could not be evaluated'}; see the validation table in section 3 and read the corresponding conclusions with that qualification."))
    out.append("**What E3 and E4 can see.** On synthetic twin codes (`scripts/power_model_form.py`, `docs/POWER-model-form.md`) a verdict of structural needs a step between the codes that the four parameters cannot absorb: about 0.6 dex above z = 3.5 when the parameters move the SFRD by a few tenths of a dex, about 1 dex when they move it three times as much; smaller steps are classed removable or parametric (E4 also mixed), and identical codes never came out structural.")
    return out


def reading(res):
    """What follows from the verdicts, by fixed rules."""
    v, c = res["verdicts"], res["camels"]
    out = []
    if v["E3"]["verdict"] == "structural" and v["E4"]["verdict"] in ("structural", "mixed"):
        out.append("The disagreement between the two codes is not removable by retuning their feedback parameters inside the CAMELS ranges: it is a difference of model form, at CAMELS resolution, and it persists when both are calibrated to the same observed star formation history.")
    elif v["E3"]["verdict"] == "removable":
        out.append("Within the CAMELS ranges one code can be retuned to reproduce the other's star formation history to within the scatter between two seeds of the same codes: the difference between these two codes is parametric.")
    else:
        out.append("The experiment does not separate parametric from structural for these two codes: the distance is neither clearly above the larger of the emulation noise and the seed-to-seed scatter, nor clearly below the seed-to-seed scatter.")
    p = c["codes"]
    out.append(f"The four feedback parameters move the SFRD of IllustrisTNG by {_f(p['IllustrisTNG']['parametric']['rms_low'])} dex rms at z < 3 and {_f(p['IllustrisTNG']['parametric']['rms_high'])} dex at z > 3, and that of SIMBA by {_f(p['SIMBA']['parametric']['rms_low'])} and {_f(p['SIMBA']['parametric']['rms_high'])} dex; the seed-to-seed scatter of a 25 Mpc/h box is "
               f"{_f(float(np.nanmedian([x for x in p['IllustrisTNG']['seed_noise'] if x is not None])), 2)} (IllustrisTNG) and {_f(float(np.nanmedian([x for x in p['SIMBA']['seed_noise'] if x is not None])), 2)} (SIMBA) dex at the median redshift.")
    return out


def render(res):
    v, p, c = res["verdicts"], res["published"], res["camels"]
    e1 = p["E1"]
    L = ["# Analysis: parametric versus structural uncertainty in the cosmic star formation history of simulated galaxy formation", "",
         f"Generated by `scripts/analyze_model_form.py` from release {res['version']}; do not edit by hand. The pre-specified protocol is [`PROTOCOL-model-form.md`](PROTOCOL-model-form.md); this page reports what it gave, null results included. Seed {res['parameters']['seed']}.", "", "## Result", ""]
    L += [f"- {x}" for x in headline(res)] + ["", "### What it means", ""] + [f"- {x}" for x in reading(res)]
    L += ["", "R and the other statistics are properties of these simulations at these redshifts and this resolution; sampling noise, box size and everything not modelled stay in them. Section 7 lists the limits.", "",
          "## 1. Published simulations: does the disagreement grow with redshift? (E1)", "",
          "One fiducial curve per model family (`data/model-variants.json`), total cosmic star formation rate density in comoving units, windowed on a grid of 0.25 in z. No IMF conversion (sensitivity S4 applies it).", "",
          _table(["family", "record", "z range of the curve", "in the balanced set"], [[f, f"`{d['record']}`", f"{d['z_range'][0]:.2f} - {d['z_range'][1]:.2f}", _yn(f in e1["balanced_families"])] for f, d in sorted(p["families"].items())]), "",
          _table(["statistic", "value"], [["balanced families", e1["n_balanced"]], ["SD at z = 0.5-3.0 (dex)", _f(e1["sd_low"])], ["SD at z = 5.0-7.5 (dex)", _f(e1["sd_high"])], ["phi = log10 ratio of the SDs", f"{_f(e1['phi'])} (90 % {_ci(e1['phi_ci90'])}, 95 % {_ci(e1['phi_ci95'])})"],
                                    ["share of bootstrap resamples with phi > 0", f"{100 * e1['boot_fraction_positive']:.0f} %"], ["Pitman-Morgan variance ratio, t, one-sided p", f"{_f(e1['pitman_morgan']['variance_ratio'], 2)}, {_f(e1['pitman_morgan']['t'], 2)}, {_f(e1['pitman_morgan']['p_one_sided'], 4)}"],
                                    ["slope of log10 S(z) over z = 0.5-7.5 (dex per unit z)", f"{_f(e1['slope_dex_per_z'], 3)} (90 % {_ci(e1['slope_ci90'], 3)})"], ["redshift of minimum spread (anchor)", f"{e1['anchor_z']:.2f} (90 % {_ci(e1['anchor_z_ci90'], 2)})"],
                                    ["rule met (both conditions)", _yn(e1["success"])]]), "",
          "Spread across all eligible families at each redshift (n families, standard deviation in dex, 16th to 84th percentile of the bootstrap):", ""]
    sp = e1["spread"]
    rows = []
    for k, z in enumerate(sp["z"]):
        if abs(z * 4 - round(z * 4)) < 1e-9 and abs((z * 2) - round(z * 2)) < 1e-9 and sp["sd"][k] is not None:
            rows.append([f"{z:.1f}", sp["n"][k], _f(sp["sd"][k], 2), f"{_f(sp['sd_p16'][k], 2)} - {_f(sp['sd_p84'][k], 2)}"])
    L += [_table(["z", "families", "SD (dex)", "bootstrap 16-84"], rows), "", "Sensitivity analyses (reported, not used to choose):", ""]
    sn = p["sensitivity"]
    srow = lambda k, x: [k, x["n_balanced"], _f(x["phi"]), _ci(x["phi_ci90"]), _f(x["pitman_morgan_p"], 4), _yn(x["success"])]
    L += [_table(["analysis", "balanced families", "phi", "90 % interval", "Pitman-Morgan p", "rule met"],
                 [srow(k, sn[k]) for k in ("S1_add_simba_horizon", "S2_exclude_small_boxes", "S3_alternative_bands", "S4_chabrier_equivalent", "S7_window_0.0625", "S7_window_0.25")] + [srow(f"S6 without {f}", x) for f, x in sn["S6_leave_one_family_out"].items()]), "",
          f"S5: with a random one of each family's fiducial and numerical variants ({sn['S5_random_numerical_fiducial']['draws']} draws) phi has median {_f(sn['S5_random_numerical_fiducial']['phi_median'])} (95 % of draws {_f(sn['S5_random_numerical_fiducial']['phi_p2.5'])} to {_f(sn['S5_random_numerical_fiducial']['phi_p97.5'])}) and the rule is met in {100 * sn['S5_random_numerical_fiducial']['fraction_success']:.0f} % of them. "
          "A draw can remove a family from the balanced set by choosing a variant that does not reach both bands, so the table gives the draws by balanced-set size; S5b restricts the draws to curves that reach both bands.", "",
          _table(["analysis", "balanced families", "draws", "phi median", "rule met"], [[("S5" if k == "S5_random_numerical_fiducial" else "S5b"), n, x["draws"], _f(x["phi_median"]), f"{100 * x['fraction_success']:.0f} %"] for k in ("S5_random_numerical_fiducial", "S5b_random_numerical_fiducial_both_bands") for n, x in sn[k]["by_n_balanced"].items()]), "",
          "## 2. What the authors' own variants do (E2)", "",
          "Root mean square difference in log10 SFRD between each variant and its base run, averaged within families and then over families (pooled over variants in brackets; 90 % interval of the pooled value from resampling variants). Sizes are the authors' choices: read orders of magnitude, not ratios.", ""]
    rows = []
    for cls, d in p["E2"]["by_family"].items():
        for band in ("low", "high"):
            x, pooled, iv = d.get(band), p["E2"]["pooled"][cls].get(band), p["E2"]["pooled_interval90"][cls].get(band)
            if x is None:
                continue
            rows.append([cls, band, x["n_variants"], x["n_families"], _f(x["rms_dex"], 3), f"{_f(pooled['rms_dex'], 3)} {_ci(iv, 3)}" if pooled and iv else "-", _f(p['E2']['S_band'][band], 3)])
    L += [_table(["variant class", "band", "variants", "families", "rms by family (dex)", "pooled rms [90 %]", "between-family SD (dex)"], rows), "",
          "## 3. The designed experiment: IllustrisTNG and SIMBA in CAMELS (E3)", "",
          "Two codes, 25 Mpc/h boxes, 256^3 elements, the same four feedback factors varied over the same ranges in 1000 Latin-hypercube simulations each, 27 cosmic-variance seeds each. All numbers are for CAMELS resolution.", "",
          "**Validations.**", ""]
    v1, v2, v3 = c["v1"], c["v2"], c["v3"]
    L += [_table(["validation", "result", "required", "holds"], [
        ["V1 stellar mass in subhalos / time integral of the SFR (12 IllustrisTNG simulations)", "not evaluated" if v1 is None else f"{_f(v1['ratio_min'], 2)} to {_f(v1['ratio_max'], 2)} (median {_f(v1['ratio_median'], 2)})", "0.45 to 0.75", "n/a" if v1 is None else _yn(v1["passed"])],
        ["V1 volume: stored volume against the catalogue's BoxSize / h; stored SFRD integral against the stored formed mass; all simulations present", "not evaluated" if v1 is None or not v1.get("volume_check") else f"volume ratio {_f(v1['volume_check']['volume_ratio'], 4)}; integral ratio {_f(v1['volume_check']['integral_over_formed_min'], 3)} to {_f(v1['volume_check']['integral_over_formed_max'], 3)}; {v1['volume_check']['n_lh']} LH and {v1['volume_check']['n_cv']} CV", "ratios within 0.5 % (volume) and 5 % (integral), 1000 and 27", "n/a" if v1 is None or not v1.get("volume_check") else _yn(v1["volume_check"]["passed"])],
        ["V2 response of the SFRD to A_SN1 = 2 against the TNG paper's 'stronger winds x2' (rms, dex)", _f(v2["A_SN1=2"]["rms_difference_dex"]), "<= 0.15", _yn(v2["A_SN1=2"]["rms_difference_dex"] <= 0.15)],
        ["V2 response to A_SN2 = 2 against 'faster winds x2' (rms, dex)", _f(v2["A_SN2=2"]["rms_difference_dex"]), "<= 0.15", _yn(v2["A_SN2=2"]["rms_difference_dex"] <= 0.15)],
        ["V3 CAMELS-SIMBA mean CV curve minus the published SIMBA curve, z = 0.5-4 (mean, dex)", _f(v3["mean_difference_dex"], 3, True), "|.| <= 0.3", _yn(v3["passed"])]] +
        [[f"V4 {s}: cross-validation error over seed noise (max over the grid), emulator against CV mean (max, z <= 6)", f"{_f(c['v4'][s]['max_cv_over_seed'], 2)}; {_f(c['v4'][s]['emulator_minus_cv_mean_max_abs_z_le_6'], 3)}", "<= 1.5; <= max(0.05, 2 SE)", _yn(c["v4"][s]["ratio_ok"] and c["v4"][s]["within_tolerance"])] for s in c["v4"]]), "",
          "**Seed noise, parametric spread and structural offset by redshift** (dex; parametric = standard deviation of the emulated SFRD over the four-parameter prior, cosmology fixed):", ""]
    zs = c["meta"]["grid"]
    rows = []
    for zt in (0.1, 0.5, 1.1, 1.9, 2.9, 3.9, 4.9, 5.9, 6.9, 7.9):
        k = int(np.argmin(np.abs(np.array(zs) - zt)))
        if c["structural_fiducial"]["delta"][k] is None:
            continue
        rows.append([f"{zs[k]:.1f}", _f(c["codes"]["IllustrisTNG"]["seed_noise"][k], 2), _f(c["codes"]["IllustrisTNG"]["parametric"]["sd"][k], 2), _f(c["codes"]["SIMBA"]["seed_noise"][k], 2), _f(c["codes"]["SIMBA"]["parametric"]["sd"][k], 2),
                     f"{_f(c['structural_fiducial']['delta'][k], 2, True)} +- {_f(c['structural_fiducial']['se'][k], 2)}"])
    L += [_table(["z", "TNG seed noise", "TNG parametric", "SIMBA seed noise", "SIMBA parametric", "TNG - SIMBA at the fiducial parameters"], rows), "",
          f"Rms over the bands: structural offset at the fiducial parameters {_f(c['structural_fiducial']['rms_low'], 2)} (z < 3.1) and {_f(c['structural_fiducial']['rms_high'], 2)} (z > 3.1) dex; parametric spread of IllustrisTNG {_f(c['codes']['IllustrisTNG']['parametric']['rms_low'], 2)} and {_f(c['codes']['IllustrisTNG']['parametric']['rms_high'], 2)}, of SIMBA {_f(c['codes']['SIMBA']['parametric']['rms_low'], 2)} and {_f(c['codes']['SIMBA']['parametric']['rms_high'], 2)}.", "",
          "**Reachability.** Minimum rms difference of the two emulated curves over the four feedback coordinates of each code:", ""]
    rr = c["reachability"]
    L += [_table(["redshifts", "D at the fiducial parameters (dex)", "D after retuning, all simulations (dex)", "between codes, 500-simulation emulators: 5th / median / 95th", "same-code control (500 v 500): median / 95th"],
                 [["full (" + f"{rr['z_used'][0]} - {rr['z_used'][-1]})", _f(rr["full"]["D_fiducial_dex"]), _f(rr["full"]["D_dex"]), f"{_f(rr['between_full']['p5'])} / {_f(rr['between_full']['p50'])} / {_f(rr['between_full']['p95'])}", f"{_f(rr['controls_full']['median'])} / {_f(rr['controls_full']['p95'])}"],
                  ["low (0.1 - 3.1)", _f(rr["low"]["D_fiducial_dex"]), _f(rr["low"]["D_dex"]), f"{_f(rr['between_bands']['low']['p5'])} / {_f(rr['between_bands']['low']['p50'])} / {_f(rr['between_bands']['low']['p95'])}", f"{_f(rr['controls_bands']['low']['median'])} / {_f(rr['controls_bands']['low']['p95'])}"],
                  ["high (3.1 - 8.1)", _f(rr["high"]["D_fiducial_dex"]), _f(rr["high"]["D_dex"]), f"{_f(rr['between_bands']['high']['p5'])} / {_f(rr['between_bands']['high']['p50'])} / {_f(rr['between_bands']['high']['p95'])}", f"{_f(rr['controls_bands']['high']['median'])} / {_f(rr['controls_bands']['high']['p95'])}"]]), "",
          f"Rule (amendment A1): structural if the 5th percentile of the between-code distance exceeds both the 95th percentile of the controls and the seed margin ({_f(rr['margin_dex'])} dex, the rms difference between two seeds of the two codes); removable if its 95th percentile is below the margin; otherwise unresolved. "
          f"Full range: **{rr['verdict']}**; low band {rr['between_bands']['low']['verdict']}; high band {rr['between_bands']['high']['verdict']}. For reference, resampling all 1000 simulations of each code (full-size emulators, {rr['bootstrap_full']['n']} refits; not used for the verdict) gives D = {_f(rr['bootstrap_full']['p5'])} / {_f(rr['bootstrap_full']['p50'])} / {_f(rr['bootstrap_full']['p95'])} (5th / median / 95th percentile). "
          "Reachable coordinates of the minimising pair (in units of the half-range): IllustrisTNG " + ", ".join(f"{x:+.2f}" for x in rr["full"]["a_tng"]) + "; SIMBA " + ", ".join(f"{x:+.2f}" for x in rr["full"]["a_simba"]) + " (a coordinate of 1 is the edge of the CAMELS range, where the emulator is least constrained).", "",
          "Distance when the parameter ranges are shrunk to a fraction of their log half-width:", "", _table(["fraction of the range", "D (dex)"], [[k, _f(x)] for k, x in rr["shrunk"].items()]), "",
          "## 4. Calibrate on the same observations, then extrapolate (E4)", "",
          f"Both codes are conditioned on the Madau and Dickinson (2014) SFRD (Chabrier) at z = {', '.join(str(z) for z in c['calibration']['z_obs'])}. The error is a systematic of {c['calibration']['systematic_dex']} dex common to all eight points (a normalisation, IMF and dust uncertainty of the observed fit), plus {BOX_ALLOWANCE} dex for CAMELS box size and resolution and the emulator error at each point, independent between points. "
          "The intervals are those of the model's **mean response** after calibration (posterior of the four coordinates, plus the emulator's cross-validation error in excess of the seed noise at each target redshift): they do not include seed-to-seed scatter or the box allowance, which belong to the comparison with the observed fit. Median and 90 % interval of log10 SFRD:", ""]
    k = c["calibration"]
    rows = []
    for i, z in enumerate(k["z_target"]):
        t, s = k["codes"]["IllustrisTNG"]["predictive"], k["codes"]["SIMBA"]["predictive"]
        rows.append([f"{z:.1f}", f"{_f(t['median'][i], 2)} [{_f(t['p5'][i], 2)}, {_f(t['p95'][i], 2)}]", f"{_f(s['median'][i], 2)} [{_f(s['p5'][i], 2)}, {_f(s['p95'][i], 2)}]", _f(k["median_difference"][i], 2, True)])
    L += [_table(["z", "IllustrisTNG", "SIMBA", "difference of medians"], rows), "",
          f"Disjoint intervals at {100 * k['disjoint_fraction']:.0f} % of these redshifts: **{k['verdict']}** (rule: structural at half or more, parametric if never). Effective sample sizes {k['codes']['IllustrisTNG']['ess']:.0f} and {k['codes']['SIMBA']['ess']:.0f}; minimum chi-square {_f(k['codes']['IllustrisTNG']['chi2_min'], 1)} and {_f(k['codes']['SIMBA']['chi2_min'], 1)} for 8 data points. "
          "Posterior median coordinates (A_SN1, A_AGN1, A_SN2, A_AGN2 in units of the half-range): IllustrisTNG " + ", ".join(f"{x:+.2f}" for x in k["codes"]["IllustrisTNG"]["posterior_median_coordinates"]) + "; SIMBA " + ", ".join(f"{x:+.2f}" for x in k["codes"]["SIMBA"]["posterior_median_coordinates"]) + ".", "",
          "Sensitivity (S8, S9): the same quantities when the emulator, the error model or the cosmology are changed (E3 as the point distance D over all simulations, E4 as the verdict and the disjoint share):", "",
          _table(["setting", "degree TNG / SIMBA", "D after retuning (dex)", "E4 verdict", "disjoint share", "min ESS"], [[k_, "-" if "degree" not in x else f"{x['degree']['IllustrisTNG']} / {x['degree']['SIMBA']}", _f(x.get("D_full_dex")), x["E4_verdict"], f"{100 * x['E4_disjoint_fraction']:.0f} %", f"{x['ess_min']:.0f}"] for k_, x in c["sensitivity"].items()]) if c.get("sensitivity") else "",
          "", ("S9 parametric spread with cosmology free (rms, dex; low / high): " + "; ".join(f"{s_} {_f(x['low'], 2)} / {_f(x['high'], 2)}" for s_, x in c["sensitivity"]["S9_cosmology_free"]["parametric_rms"].items()) + ".") if c.get("sensitivity") else "", "",
          "## 5. Observations (E5) and the stellar mass budget (V5)", "",
          "Published fiducial curves (Chabrier-equivalent) against the Madau and Dickinson (2014) fit (Chabrier, error 0.2 dex assumed):", ""]
    rows = [[f"{x['z']:.1f}", x["n"], _f(x["ensemble_median"], 2), f"{_f(x['ensemble_min'], 2)} to {_f(x['ensemble_max'], 2)}", _f(x["observed"], 2), _f(x["offset_dex"], 2, True), _f(x["offset_in_sd"], 2, True) if x["offset_in_sd"] is not None else "-",
             _f(x["sd_over_obs_error"], 2), _yn(x["inside_envelope"])] for x in p["E5"]["table"]]
    L += [_table(["z", "families", "ensemble median", "envelope", "observed", "median - observed", "in units of the spread", "spread / obs. error", "observed inside"], rows), ""]
    if p["E5"].get("high_z"):
        L += ["At z = 9 and beyond (Harikane et al. 2023, dust corrected, converted to Chabrier; their asymmetric 1 sigma errors):", "",
              _table(["z", "families", "ensemble median", "envelope", "observed [1 sigma]", "median - observed", "inside"], [[f"{x['z']:.0f}", x["n"], _f(x["ensemble_median"], 2), f"{_f(x['ensemble_min'], 2)} to {_f(x['ensemble_max'], 2)}",
                                                                                        f"{_f(x['observed'], 2)} [{_f(x['observed_low'], 2)}, {_f(x['observed_high'], 2)}]", _f(x["offset_dex"], 2, True), _yn(x["inside_envelope"])] for x in p["E5"]["high_z"]]), ""]
    L += ["Stellar mass budget: effective return fraction R_eff(z) = 1 - rho_*(z) / integral of the SFRD above z, for runs with both curves (a plausible value for a Chabrier or Kroupa IMF is 0.3 to 0.45; required 0.15 to 0.60):", "",
          _table(["run", "z", "log10 formed", "log10 rho_*", "R_eff"], [[r["run"], z, _f(x["formed_log10"], 2), _f(x["smd_log10"], 2), _f(x["R_eff"], 2)] for r in p["V5"]["runs"] for z, x in r["R_eff"].items()]),
          "", f"Evaluated at {p['V5']['n_evaluated']} of {p['V5']['n_requested']} run-redshift pairs (a curve that starts within 0.06 of z = 0 stands in for z = 0)." + "".join(f" {r['run']}: not evaluated at z = {', '.join(str(z) for z in r['not_evaluated'])}." for r in p["V5"]["runs"] if r["not_evaluated"]), "",
          "## 6. Deviations from the protocol", ""] + ([f"- {d}" for d in res["deviations"]] or ["- none"]) + ["",
          "## 7. Limitations", "",
          "- Nine families, seven balanced: a funnel of modest size would not be detected (power table in the protocol).",
          "- The published curves differ in volume and resolution; cosmic variance and numerical effects are not removed.",
          "- Model families share heritage (Illustris, IllustrisTNG, THESAN; EAGLE, FLAMINGO, COLIBRE); the bootstrap treats them as exchangeable.",
          "- CAMELS boxes are 25 Mpc/h with 256^3 elements: E3 and E4 describe how the models respond at that resolution, not the absolute SFRD of the full-resolution simulations, and star formation above z about 6 is resolution-limited.",
          "- The reachable set depends on the CAMELS parameter ranges, which are not the ranges the code authors would accept; the parameters of the two codes are not the same physical quantities.",
          "- Two codes only: whether the IllustrisTNG-SIMBA distance is typical cannot be said.",
          "- The observed SFRD is a fit with an assumed systematic error, not a likelihood; E4 treats the systematic as common to the eight calibration redshifts and the other errors as independent, and its power is limited (protocol section 5 and `docs/POWER-model-form.md`): steps between the codes smaller than a few tenths of a dex are classed parametric.",
          "- A spread in dex is mechanically larger where the SFRD changes faster with redshift, so a funnel in dex does not by itself say that the models disagree more in timing or physics there; box size, resolution and the number of families that reach each redshift also change with z, and the all-family spread curve S(z) is descriptive for that reason.",
          "- E2: variant classes are confounded with families and boxes (parametric, component and ablation variants are all IllustrisTNG; calibration and implementation variants are FLAMINGO); some variants exist in one band only; the interval ignores family clustering.",
          "- E3: the minimiser seeks the corners of the parameter box, where an emulator trained on a Latin hypercube has the fewest simulations; the controls share that search, which keeps the comparison fair, but D is biased low by the search and high by emulator noise, and the shrunken ranges are the less extrapolated estimates. 63 % of the CAMELS grid points lie above z = 3.1.",
          "- E5: the observed fit is converted to a Chabrier IMF by dividing by 1.6 (0.204 dex), the simulations by the website's offsets (0.235 dex from Salpeter), a difference of 0.03 dex; the observational SFRD is integrated down to a luminosity limit whereas the simulated one is a total.", "",
          "## 8. Reproduce", "", "`python3 scripts/ingest_camels_sfrd.py` rebuilds `data/ensembles/camels-sfrd.json` from the public CAMELS files (about 25 minutes; the hashes of the files read are stored) and `python3 scripts/validate_camels_closure.py` rebuilds V1; "
          "`python3 scripts/analyze_model_form.py` rewrites this file and `data/analysis/model-form.json` from them and from the committed curves; `python3 scripts/test_model_form.py` checks the machinery on synthetic ensembles and that these outputs are not stale.", ""]
    return "\n".join(L)


def main():
    res = run()
    write_outputs(res)
    v = res["verdicts"]
    print(f"model form: E1 phi={v['E1']['phi']:.3f} success={v['E1']['success']}; E3 {v['E3']['verdict']} (D={v['E3']['D_full']:.3f}); E4 {v['E4']['verdict']}")


if __name__ == "__main__":
    main()
