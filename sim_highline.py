"""Load the sim-highline scaling-relation dataset into pandas / numpy.

    import sim_highline
    df = sim_highline.load()                                   # tidy table, one row per plotted point
    sel = sim_highline.select(df, relation="sfms", z=(1, 2), sources=["EAGLE", "IllustrisTNG"], rankable=True)
    one = sim_highline.nearest_epoch(sel, z=1.5)               # one record per source/run, nearest published epoch (nothing is interpolated)
    x, y, lo, hi = sim_highline.curve(df, "schaye15.eagle-refl0100n1504.sfms.z1")
    print(sim_highline.bibtex(sel))
    me = sim_highline.compare_run(x, y, "gsmf", z=0.1, definitions={"imf": "chabrier03", "massDefinition": "aperture-50pkpc", "densityFrame": "comoving"})
    # one row per published curve at that epoch: definition verdict (same rules as the website) and median offset of your run

Units are log10, physical and h-free as published; x_unit, y_unit, x_definition, y_definition and the definition columns
(imf, mass_definition, population, ...) say exactly what each curve is. Compare curves only when those agree.
"""
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

KEYS = ["kind", "source", "run", "relation"]


def _base(path):
    if path is not None:
        return str(path).rstrip("/")
    here = Path(__file__).resolve().parent
    for cand in (Path.cwd() / "data" / "export", here / "sim_highline_data", here / "data" / "export"):
        if (cand / "sim-highline-records.csv").exists():
            return str(cand)
    raise FileNotFoundError("data not found; install the wheel (data included), run from a checkout, or pass the folder or base URL containing sim-highline-records.csv")


def load(path=None, points=True):
    """Records joined to points (default) or the records table alone (points=False). `path` is a folder or base URL."""
    base = _base(path)
    rec = pd.read_csv(f"{base}/sim-highline-records.csv", comment="#", dtype={"z": float})
    for c in ("connect", "rankable"):
        rec[c] = rec[c].astype(bool)
    if not points:
        return rec
    pts = pd.read_csv(f"{base}/sim-highline-points.csv", comment="#")
    df = rec.merge(pts, on="record_id", how="inner", validate="one_to_many")
    df.attrs.update(version=manifest(base)["version"], base=base)
    return df


def load_distributions(path=None):
    """Per-galaxy distributions: one row per non-empty grid cell (x_low, x_high, y_low, y_high, count), joined to the identifying columns of its record (source, run, relation, z). Use `grid(df, record_id)` for the counts as a matrix."""
    base = _base(path)
    d = pd.read_csv(f"{base}/sim-highline-distributions.csv", comment="#")
    rec = pd.read_csv(f"{base}/sim-highline-records.csv", comment="#", usecols=["record_id", "kind", "source", "run", "relation", "z", "x_definition", "y_definition", "x_unit", "y_unit"])
    return d.merge(rec, on="record_id", how="inner", validate="many_to_one")


def grid(dist, record_id):
    """Counts of one distribution record as a matrix [x bin][y bin] with its edges: (counts, x_edges, y_edges)."""
    d = dist[dist["record_id"] == record_id]
    if d.empty:
        raise KeyError(f"no distribution for {record_id}")
    xe = np.unique(np.concatenate([d["x_low"].to_numpy(), d["x_high"].to_numpy()]))
    ye = np.unique(np.concatenate([d["y_low"].to_numpy(), d["y_high"].to_numpy()]))
    m = np.zeros((len(xe) - 1, len(ye) - 1))
    for r in d.itertuples():
        m[np.searchsorted(xe, r.x_low), np.searchsorted(ye, r.y_low)] = r.count
    return m, xe, ye


def load_conversions(path=None):
    """Measured conversions between definitions in the CAMELS simulations (see docs/CONVERSIONS.md): a dict with suites -> redshift -> pairs/gsmf. Use `measured_shift` for one number with its spread."""
    base = _base(path)
    if "://" in base:
        import urllib.request
        with urllib.request.urlopen(f"{base}/sim-highline-conversions.json") as f:
            return json.load(f)
    return json.loads((Path(base) / "sim-highline-conversions.json").read_text())


def measured_shift(pair, code, x, z=0.0, conv=None):
    """What changing a definition does to a quantity, measured in the CAMELS catalogues of one code: `pair` such as 'mass.total-to-rad2' (stars within twice the stellar half-mass radius against all bound stars),
    `code` one of IllustrisTNG, SIMBA, Astrid, `x` the log10 stellar mass (log10 M200crit for 'halo.*') of the galaxy, `z` one of 0, 0.95, 2.15. Returns median, p16, p84 (galaxies) and se (spread of the median across the 27 boxes) in dex,
    linearly interpolated between the bin centres; raises ValueError outside the measured range rather than extrapolating."""
    conv = conv or load_conversions()
    key = f"z{z:g}"
    try:
        rows = conv["suites"][code][key]["pairs"][pair]
    except KeyError as e:
        raise KeyError(f"no measurement for {pair!r} in {code} at z={z:g}") from e
    xs = np.array([r["x"] for r in rows])
    if not (xs.min() <= x <= xs.max()):
        raise ValueError(f"x={x} is outside the measured range {xs.min():.2f} to {xs.max():.2f}")
    out = {k: float(np.interp(x, xs, [r[k] for r in rows])) for k in ("median", "p16", "p84")}
    i = int(min(max(np.searchsorted(xs, x) - 1, 0), len(xs) - 2))      # the two bins around x
    se = [rows[i]["seedSe"], rows[i + 1]["seedSe"]]
    out["se"] = None if None in se else float(np.interp(x, xs[i:i + 2], se))
    return out


def corrections(path=None):
    """The corrections made to curves taken from third-party compilations (why, by how much, which records); see data/compilation-corrections.json."""
    base = _base(path)
    if "://" in base:
        import urllib.request
        with urllib.request.urlopen(f"{base}/sim-highline-corrections.json") as f:
            return json.load(f)["corrections"]
    return json.loads((Path(base) / "sim-highline-corrections.json").read_text())["corrections"]


def manifest(path=None):
    base = _base(path)
    if "://" in base:
        import urllib.request
        with urllib.request.urlopen(f"{base}/sim-highline-manifest.json") as f:
            return json.load(f)
    return json.loads((Path(base) / "sim-highline-manifest.json").read_text())


def select(df, relation=None, z=None, sources=None, runs=None, kind=None, tier=None, rankable=None, calibration=None, mass_class=None, population=None):
    """Filter records. `z` is a value (record epoch range must contain it) or a (lo, hi) range (epoch must fall inside). Lists/strings accepted for the others."""
    m = pd.Series(True, index=df.index)
    for col, val in (("relation", relation), ("source", sources), ("run", runs), ("kind", kind), ("tier", tier), ("calibration", calibration), ("mass_class", mass_class), ("population", population)):
        if val is not None:
            m &= df[col].isin([val] if isinstance(val, str) else list(val))
    if rankable is not None:
        m &= df["rankable"] == rankable
    if z is not None:
        if np.isscalar(z):
            m &= (df["z_min"] <= z + 1e-9) & (df["z_max"] >= z - 1e-9)
        else:
            m &= (df["z"] >= z[0] - 1e-9) & (df["z"] <= z[1] + 1e-9)
    return df[m]


def open_terms(df):
    """Keep only rows whose records carry no third-party terms (the CC BY 4.0 part of the dataset). Records with a `terms` value come from sources with their own licence or none; see docs/SOURCE-TERMS.md."""
    return df[df["terms"].isna() | df["terms"].astype(str).str.contains("CC-BY-4.0")]


def nearest_epoch(df, z, tol=None):
    """Per source/run series keep only the record closest to z, dropping series with no epoch within tol (default max(0.15, 0.1 (1+z)), as the website does)."""
    tol = max(0.15, 0.1 * (1 + z)) if tol is None else tol
    d = np.where((df["z_min"] <= z) & (df["z_max"] >= z), 0.0, np.minimum((df["z_min"] - z).abs(), (df["z_max"] - z).abs()))
    df = df.assign(_dz=d)
    df = df[df["_dz"] <= tol]
    best = df.groupby(KEYS + ["x_definition", "y_definition"] + ["population_note"], dropna=False)["_dz"].transform("min")
    # series with several records of equal distance (definition variants) are kept whole
    return df[df["_dz"] == best].drop(columns="_dz")


def curve(df, record_id):
    """numpy arrays (x, y, y_low, y_high) of one record; the band arrays are NaN where the source gives none."""
    r = df[df["record_id"] == record_id].sort_values("point_index")
    if r.empty:
        raise KeyError(record_id)
    return tuple(r[c].to_numpy(float) for c in ("x", "y", "y_low", "y_high"))


def bibtex(df):
    """BibTeX @misc entries (paper-level note, DOI, URL) for the records in df, from sim-highline-citations.bib."""
    base = df.attrs.get("base") or _base(None)
    if "://" in base:
        import urllib.request
        text = urllib.request.urlopen(f"{base}/sim-highline-citations.bib").read().decode()
    else:
        text = (Path(base) / "sim-highline-citations.bib").read_text()
    dois = set(df["doi"].dropna()) | set(df.loc[df["doi"].isna(), "url"].dropna())
    keys = {re.sub(r"[^A-Za-z0-9]+", "_", d).strip("_") for d in dois}
    out = []
    for entry in text.strip().split("\n\n"):
        key = entry.split("{", 1)[1].split(",", 1)[0]
        if key in keys:
            out.append(entry)
    return "\n\n".join(out) + "\n"


def rules(path=None):
    """The comparability rules the website uses (hard and soft definition keys per relation), generated from compare.js."""
    base = _base(path)
    if "://" in base:
        import urllib.request
        with urllib.request.urlopen(f"{base}/sim-highline-rules.json") as f:
            return json.load(f)
    return json.loads((Path(base) / "sim-highline-rules.json").read_text())


def _unset(v):
    return v is None or v in ("unspecified", "heterogeneous")


def _same(a, b):
    return json.dumps(a) == json.dumps(b)


def compatible(a, b, rule_table=None):
    """Definition compatibility of two records (dicts with relation, source, rankable, definitions, epoch), identical to the website.
    Returns {"verdict": "comparable" | "comparable-with-caveats" | "not-comparable", "blockers": [...], "caveats": [...]}."""
    R = rule_table or rules()
    rule = R["rules"].get(a["relation"], {"hard": [], "soft": []})
    blockers, caveats = [], []
    if a["relation"] != b["relation"]:
        return {"verdict": "not-comparable", "blockers": ["different relations"], "caveats": caveats}
    for r in (a, b):
        if not r.get("rankable"):
            blockers.append(f"{r['source']}: {(r.get('selection') or {}).get('warning') or 'record marked context only'}")
    da, db = a.get("definitions") or {}, b.get("definitions") or {}
    if not a.get("definitions") or not b.get("definitions"):
        blockers.append("structured definitions missing")
    for key in rule["hard"]:
        if _unset(da.get(key)) or _unset(db.get(key)):
            blockers.append(f"{key} not documented")
        elif not _same(da.get(key), db.get(key)):
            blockers.append(f"{key}: {da.get(key)} vs {db.get(key)}")
    imf = R["imfDex"]
    for key in rule["soft"]:
        if key == "imf" and da.get("imf") in imf and db.get("imf") in imf:
            if da["imf"] != db["imf"]:
                caveats.append(f"imf: {da['imf']} vs {db['imf']}: {abs(imf[da['imf']] - imf[db['imf']]):.3f} dex in stellar mass if not converted")
            continue
        if key == "cosmology":
            ca, cb = da.get("cosmology"), db.get("cosmology")
            if ca and cb and not _same(ca, cb):
                h = lambda c: c.get("H0") if isinstance(c, dict) else None
                ra = math.log10(h(ca) / h(cb)) if h(ca) and h(cb) else float("nan")
                caveats.append(f"H0 {h(ca)} vs {h(cb)}: up to {abs((3 if a['relation'] == 'gsmf' else 2) * ra):.3f} dex if not converted")
            continue
        if _unset(da.get(key)) or _unset(db.get(key)):
            caveats.append(f"{key} not documented for {a['source'] if _unset(da.get(key)) else b['source']}")
        elif not _same(da.get(key), db.get(key)):
            caveats.append(f"{key}: {da.get(key)} vs {db.get(key)}")
    ea, eb = a.get("epoch") or {}, b.get("epoch") or {}
    analytic = ea.get("mode") == "analytic-evolution" or eb.get("mode") == "analytic-evolution"
    dz = abs((ea.get("zRepresentative") or 0) - (eb.get("zRepresentative") or 0))
    if not analytic and dz > 0.5:
        caveats.append(f"epoch: z={ea.get('zRepresentative')} vs z={eb.get('zRepresentative')}; evolution within the bin is not modelled")
    return {"verdict": "not-comparable" if blockers else "comparable-with-caveats" if caveats else "comparable", "blockers": blockers, "caveats": caveats}


def _interp(xs, ys, x):
    for i in range(1, len(xs)):
        if xs[i - 1] <= x <= xs[i]:
            t = 0.0 if xs[i] == xs[i - 1] else (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return float("nan")


def _sigma(y, lo, hi, kind):
    if kind != "uncertainty":
        return np.full(len(y), np.nan)
    up = np.where(np.isfinite(hi), hi - y, 0.0)
    dn = np.where(np.isfinite(lo), y - lo, 0.0)
    s = np.maximum(up, dn)
    return np.where(s == 0, np.nan, s)


def residuals(sim, ref, sim_kind="unspecified", ref_kind="unspecified"):
    """Residual table of curve `sim` against `ref` (each a dict of arrays x, y, lo, hi), as the website computes them: evaluated at the x of the shorter curve, never extrapolated."""
    sx, sy = np.asarray(sim["x"], float), np.asarray(sim["y"], float)
    rx, ry = np.asarray(ref["x"], float), np.asarray(ref["y"], float)
    ss = _sigma(sy, np.asarray(sim["lo"], float), np.asarray(sim["hi"], float), sim_kind)
    sr = _sigma(ry, np.asarray(ref["lo"], float), np.asarray(ref["hi"], float), ref_kind)
    out = []
    if len(rx) < len(sx):
        for i, x in enumerate(rx):
            y = _interp(sx, sy, x)
            if not math.isfinite(y):
                continue
            s_sim = _interp(sx, ss, x)
            s_ref = sr[i]
            sig = math.hypot(s_ref if math.isfinite(s_ref) else 0.0, s_sim if math.isfinite(s_sim) else 0.0)
            out.append((x, y - ry[i], sig if math.isfinite(s_ref) and sig > 0 else float("nan"), math.isfinite(s_sim)))
    else:
        for i, x in enumerate(sx):
            y = _interp(rx, ry, x)
            if not math.isfinite(y):
                continue
            s_ref = _interp(rx, sr, x)
            s_sim = ss[i]
            sig = math.hypot(s_ref if math.isfinite(s_ref) else 0.0, s_sim if math.isfinite(s_sim) else 0.0)
            out.append((x, sy[i] - y, sig if math.isfinite(s_ref) and sig > 0 else float("nan"), math.isfinite(s_sim)))
    return out


def summarize(res, min_bins=3):
    if len(res) < min_bins:
        return None
    d = np.array([r[1] for r in res])
    sig = np.array([r[2] for r in res])
    weighted = np.isfinite(sig)
    return {"n": len(d), "median": float(np.median(d)), "mean": float(d.mean()), "rms": float(np.sqrt((d ** 2).mean())),
            "mean_abs_sigma": float((np.abs(d) / sig).mean()) if weighted.all() else float("nan")}


def compare_run(x, y, relation, z, definitions=None, y_low=None, y_high=None, sigma=None, linear=False, df=None, rankable_only=False, include_observations=True, name="your run"):
    """Compare your own curve with every published curve of one relation at one epoch, as the website's My run tab does.

    x, y: your points (log10 as plotted, or plain values with linear=True); optional y_low/y_high or a symmetric 1-sigma `sigma`.
    definitions: what your numbers mean, keyed like the dataset's definition columns (imf, massDefinition, densityFrame, population, ...).
    Undeclared keys can never be matched, so with no definitions no curve is called comparable.
    Returns a DataFrame, one row per published curve: verdict, blockers, caveats, median/mean/rms offset (yours minus the curve, in y units), n shared bins.
    Nothing is interpolated beyond the range of either curve."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    lo = np.full(len(y), np.nan) if y_low is None else np.asarray(y_low, float)
    hi = np.full(len(y), np.nan) if y_high is None else np.asarray(y_high, float)
    if sigma is not None:
        sg = np.asarray(sigma, float)
        lo, hi = y - sg, y + sg
    if linear:
        keep = (x > 0) & (y > 0)
        x, y, lo, hi = x[keep], y[keep], lo[keep], hi[keep]
        lg = lambda v: np.where(v > 0, np.log10(np.where(v > 0, v, 1.0)), np.nan)
        x, y, lo, hi = np.log10(x), np.log10(y), lg(lo), lg(hi)
    order = np.argsort(x)
    mine = {"x": x[order], "y": y[order], "lo": lo[order], "hi": hi[order]}
    my_kind = "uncertainty" if np.isfinite(mine["lo"]).any() and np.isfinite(mine["hi"]).any() else "unspecified"
    df = load() if df is None else df
    R = rules(df.attrs.get("base"))
    sel = select(df, relation=relation)
    if not include_observations:
        sel = sel[sel["kind"] == "simulation"]
    if rankable_only:
        sel = sel[sel["rankable"]]
    sel = nearest_epoch(sel, z)
    me = {"relation": relation, "source": name, "rankable": True, "selection": {}, "epoch": {"zRepresentative": z, "zMin": z, "zMax": z},
          "definitions": {k: v for k, v in (definitions or {}).items() if v not in (None, "unspecified")}}
    rows = []
    for rid, g in sel.groupby("record_id", sort=False):
        g = g.sort_values("point_index")
        first = g.iloc[0]
        rec = {"relation": relation, "source": first["source"], "rankable": bool(first["rankable"]), "selection": {},
               "definitions": json.loads(first["definitions_json"]),
               "epoch": {"zRepresentative": float(first["z"]), "zMin": float(first["z_min"]), "zMax": float(first["z_max"]), "mode": None if pd.isna(first.get("epoch_mode")) else first["epoch_mode"]}}
        v = compatible(me, rec, R)
        ref = {"x": g["x"].to_numpy(float), "y": g["y"].to_numpy(float), "lo": g["y_low"].to_numpy(float), "hi": g["y_high"].to_numpy(float)}
        m = np.isfinite(ref["x"]) & np.isfinite(ref["y"])
        ref = {k: a[m] for k, a in ref.items()}
        sm = summarize(residuals(mine, ref, my_kind, "uncertainty" if first["interval_kind"] == "uncertainty" else "unspecified"), R["minBins"]) if len(ref["x"]) else None
        rows.append({"record_id": rid, "kind": first["kind"], "source": first["source"], "run": first["run"], "tier": first["tier"], "z": float(first["z"]),
                     "verdict": v["verdict"], "blockers": "; ".join(v["blockers"]), "caveats": "; ".join(v["caveats"]),
                     "median_dy": sm["median"] if sm else np.nan, "mean_dy": sm["mean"] if sm else np.nan, "rms_dy": sm["rms"] if sm else np.nan,
                     "n_bins": sm["n"] if sm else 0, "mean_abs_sigma": sm["mean_abs_sigma"] if sm else np.nan})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.assign(_has=out["n_bins"] > 0, _a=out["median_dy"].abs()).sort_values(["_has", "_a"], ascending=[False, True]).drop(columns=["_has", "_a"]).reset_index(drop=True)


# ---------------------------------------------------------------------------------------------------------------------
# Observer layer: what a survey does to a simulated catalogue that the simulation does not do itself.
# Mirrors observer-lib.js step for step (camelCase names there); scripts/test_observer.py and scripts/test-observer.mjs
# compare the two on one fixture. Not a calibrated model of any survey. Docs: docs/OBSERVER-LAYER.md.
# "points" are the project's record format: a list of dicts {x, y, yLow?, yHigh?, count?}, x = log10(stellar mass / Msun),
# y = log10 of a number density per dex. Every function returns new points and never changes its input.
# ---------------------------------------------------------------------------------------------------------------------
OBSERVER_DEFAULTS = {"step": 0.005, "nsig": 8, "edgeFit": 3, "edgeFlag": 0.05, "maxGap": 1.0, "sigmaMin": 0.001, "sigmaProbe": 0.05, "sigmaMargin": 3.0}


def _finite(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def _clean_points(points, max_gap):
    p = sorted((q for q in points if _finite(q.get("x")) and _finite(q.get("y"))), key=lambda q: q["x"])
    if len(p) < 2:
        raise ValueError("need at least two points with finite x and y")
    for a, b in zip(p, p[1:]):
        if b["x"] == a["x"]:
            raise ValueError(f"duplicate x = {b['x']}")
        if b["x"] - a["x"] > max_gap:
            raise ValueError(f"gap of {b['x'] - a['x']:.3f} dex between x = {a['x']} and {b['x']} is larger than maxGap = {max_gap}; split the curve at the gap")
    return p


def _spec_function(spec, field, what):
    """A scatter or a floor may be a number, a function of log10 mass, or a table {'x': [...], field: [...]} read by linear interpolation and held constant outside."""
    if isinstance(spec, (int, float)) and not isinstance(spec, bool):
        if not math.isfinite(spec):
            raise ValueError(f"{what} must be finite")
        return lambda m: np.full(np.shape(m), float(spec))
    if callable(spec):
        return lambda m: np.array([spec(float(v)) for v in np.atleast_1d(m)], float).reshape(np.shape(m))
    if isinstance(spec, dict) and len(spec.get("x", [])) and len(spec.get("x", [])) == len(spec.get(field, [])):
        tx, tv = np.asarray(spec["x"], float), np.asarray(spec[field], float)
        return lambda m: np.interp(m, tx, tv)
    raise ValueError(f"{what} must be a number, a function of log10 mass or a table {{'x': [...], '{field}': [...]}}")


def poisson_bands(points):
    """Poisson bands for points that carry a count and no band: for N counts the 1-sigma interval of the density is n(1 +- 1/sqrt(N)), written in log10;
    the lower bound is NaN when N <= 1 because the logarithm is then undefined. Points that already have a band are left alone."""
    out = []
    for p in points:
        q = dict(p)
        if not (_finite(p.get("yLow")) or _finite(p.get("yHigh"))) and _finite(p.get("count")) and p["count"] > 0:
            e = 1.0 / math.sqrt(p["count"])
            q["yHigh"] = p["y"] + math.log10(1 + e)
            q["yLow"] = p["y"] + math.log10(1 - e) if e < 1 else float("nan")
        out.append(q)
    return out


def scatter_points(points, sigma, **opts):
    """Gaussian scatter in log10 stellar mass applied to a stellar mass function given as points. Same algorithm as scatterPoints in observer-lib.js.

    Model: each galaxy of true log mass m is observed at m + e, e ~ Normal(0, sigma(m)^2), sigma a function of the TRUE mass (a number gives a constant scatter). The observed density per dex
    at x is  n_obs(x) = integral n(m) N(x - m; sigma(m)) dm;  the kernel integrates to one for every m, so number is conserved.
    Discretisation: log10 n is interpolated linearly in x between the points and continued beyond the first and last point as a straight line with the slope of a least-squares fit to the nearest
    `edgeFit` points (the slope above the last point is never positive). The integral is a sum over a uniform grid of spacing h = min(step, sigma_min_found / 2) centred on each output x and reaching
    `nsig` sigma either way (defaults 0.005 dex and 8, so the kernel sums to 1 to better than 1e-12); sigma_min_found is the smallest sigma met when sigma is read every `sigmaProbe` dex over the data
    range +- `sigmaMargin` dex. sigma below `sigmaMin` (0.001 dex) is raised to it. sigma == 0 returns the input. Output x are the input x.
    sigma: number, function of log10 mass, or table {'x': [...], 'sigma': [...]}.
    Assumptions: the density is smooth between points; the scatter is Gaussian in log mass and independent of everything else; the continuation beyond the data is a guess, so every output carries
    edgeShare (the fraction of the scattered density that came from the continuation) and edge = edgeShare > edgeFlag.
    Uncertainty: y_out = sum_j a_j y_j with a_j the share of the scattered density that comes from the interval around input point j (the shares sum to one), so independent input errors give
    s_out = sqrt(sum a_j^2 s_j^2), separately for the upper and the lower error. Points with only a count get Poisson bands first. Not propagated: the uncertainty of sigma, of the continuation slope
    and of the interpolation, and the correlation between neighbouring outputs. count_out = count * n_out / n_in. A density is transformed, not a catalogue: no noise is added to galaxies."""
    o = {**OBSERVER_DEFAULTS, **opts}
    if isinstance(sigma, (int, float)) and sigma < 0:
        raise ValueError("sigma must be >= 0")
    base = _clean_points(points, o["maxGap"])
    if isinstance(sigma, (int, float)) and sigma == 0:
        return [{**p, "edgeShare": 0.0, "edge": False} for p in base]
    sig = _spec_function(sigma, "sigma", "sigma")
    src = base if o.get("poisson") is False else poisson_bands(base)
    xs = np.array([p["x"] for p in src], float)
    ys = np.array([p["y"] for p in src], float)
    N = len(xs)
    kfit = max(2, min(o["edgeFit"], N))

    def slope(a, b):
        mx, my = a.mean(), b.mean()
        return float(((a - mx) * (b - my)).sum() / ((a - mx) ** 2).sum())

    s_lo = slope(xs[:kfit], ys[:kfit])
    s_hi = min(0.0, slope(xs[N - kfit:], ys[N - kfit:]))
    probe = []
    m = xs[0] - o["sigmaMargin"]
    while m <= xs[-1] + o["sigmaMargin"] + 1e-9:
        probe.append(m)
        m += o["sigmaProbe"]
    sp = np.maximum(sig(np.array(probe)), o["sigmaMin"])
    if not np.isfinite(sp).all():
        raise ValueError("sigma returned a non-finite value")
    h = min(o["step"], float(sp.min()) / 2)
    K = int(math.ceil(o["nsig"] * float(sp.max()) / h))

    def band(key, sign):
        e = np.array([sign * (p[key] - p["y"]) if _finite(p.get(key)) else np.nan for p in src])
        ok = np.isfinite(e)
        if not ok.any():
            return None
        return np.where(ok, e, np.interp(xs, xs[ok], e[ok]))

    up, dn = band("yHigh", 1), band("yLow", -1)
    ks = np.arange(-K, K + 1)
    out = []
    for p in src:
        d = ks * h
        m = p["x"] + d
        s = np.maximum(sig(m), o["sigmaMin"])
        keep = np.abs(d) <= o["nsig"] * s
        d, m, s = d[keep], m[keep], s[keep]
        w = h * np.exp(-0.5 * (d / s) ** 2) / (s * math.sqrt(2 * math.pi))
        below, above = m < xs[0], m > xs[-1]
        j = np.clip(np.searchsorted(xs, m, side="right") - 1, 0, N - 2)
        t = np.clip((m - xs[j]) / (xs[j + 1] - xs[j]), 0.0, 1.0)
        y = ys[j] + t * (ys[j + 1] - ys[j])
        y = np.where(below, ys[0] + s_lo * (m - xs[0]), y)
        y = np.where(above, ys[-1] + s_hi * (m - xs[-1]), y)
        f = w * np.power(10.0, y)
        num = float(f.sum())
        ext = float(f[below | above].sum())
        A = np.zeros(N)
        outside = below | above
        wj = np.where(outside, 1.0, 1 - t)
        wj1 = np.where(outside, 0.0, t)
        jj = np.where(below, 0, np.where(above, N - 1, j))
        np.add.at(A, jj, f * wj)
        np.add.at(A, np.minimum(jj + 1, N - 1), f * wj1)
        a = A / num
        q = {"x": p["x"], "y": math.log10(num)}
        if up is not None:
            q["yHigh"] = q["y"] + float(np.sqrt((a * a * up * up).sum()))
        if dn is not None:
            q["yLow"] = q["y"] - float(np.sqrt((a * a * dn * dn).sum()))
        if _finite(p.get("count")):
            q["count"] = p["count"] * num / 10.0 ** p["y"]
        q["edgeShare"] = ext / num
        q["edge"] = q["edgeShare"] > o["edgeFlag"]
        out.append(q)
    return out


def shift_points(points, offset):
    """A systematic offset in the measured mass: observed log mass = true log mass + offset (dex). A density per dex does not change when the mass axis is translated, so x moves and y, the bands and
    the counts stay. Assumes the same offset at every mass (no mass-dependent offset, no change of slope). Apply after scatter."""
    if not _finite(offset):
        raise ValueError("offset must be a finite number of dex")
    return [{**p, "x": p["x"] + offset} for p in points]


def completeness_cut(points, m_lim):
    """Hard limiting mass: points with x < m_lim are removed (a survey that corrects for completeness above its limit and publishes nothing below it)."""
    if not _finite(m_lim):
        raise ValueError("m_lim must be a finite log10 mass")
    return [dict(p) for p in points if p["x"] >= m_lim]


def completeness_fraction(x, m50, width):
    """Smooth completeness C(x) = 1 / (1 + exp(-(x - m50) / width)): a logistic in observed log mass, half complete at m50, scale `width` dex (10 to 90 per cent in 4.4 width). A convenient shape, not a measured curve."""
    if not width > 0:
        raise ValueError("width must be > 0")
    return 1.0 / (1.0 + math.exp(-(x - m50) / width))


def completeness_weight(points, m50, width):
    """The density an UNCORRECTED catalogue would show: C times the true density, so y gets + log10 C; the bands get the same shift (their relative size is kept; no new Poisson noise is derived) and count is multiplied by C.
    Acts on the observed mass, so apply after scatter and offset."""
    out = []
    for p in points:
        c = completeness_fraction(p["x"], m50, width)
        l = math.log10(c)
        q = {**p, "y": p["y"] + l, "completeness": c}
        if _finite(p.get("yLow")):
            q["yLow"] = p["yLow"] + l
        if _finite(p.get("yHigh")):
            q["yHigh"] = p["yHigh"] + l
        if _finite(p.get("count")):
            q["count"] = p["count"] * c
        out.append(q)
    return out


def observe(points, sigma=None, offset=0.0, m_lim=None, completeness=None, **opts):
    """Scatter, then the systematic offset, then completeness on the measured mass (the order a survey applies them). completeness = (m50, width) for the smooth version; m_lim for the hard cut.
    Returns (points, steps), steps being one line per operation applied."""
    steps = []
    p = [dict(q) for q in points]
    if sigma is not None and sigma != 0:
        p = scatter_points(p, sigma, **opts)
        steps.append(f"Gaussian scatter {sigma} dex in log mass" if isinstance(sigma, (int, float)) else "Gaussian scatter, mass-dependent")
    if offset:
        p = shift_points(p, offset)
        steps.append(f"mass offset {offset:+g} dex")
    if completeness is not None:
        p = completeness_weight(p, completeness[0], completeness[1])
        steps.append(f"smooth completeness, half at log M = {completeness[0]}, scale {completeness[1]} dex")
    if m_lim is not None:
        p = completeness_cut(p, m_lim)
        steps.append(f"limiting mass log M = {m_lim}")
    return p, steps


def ssfr_floor_points(points, floor):
    """Detection floor for a specific star formation rate (sSFR) curve: y is log10 sSFR per year, with a 16 to 84 per cent band (yLow, yHigh). A point whose MEDIAN is below floor(x) is removed (the typical galaxy
    there is undetected, so no median can be measured); for the others the lower band is raised to the floor and the point is marked clipped = True. This does not recompute the median of the detected galaxies,
    which is higher than the median of all of them (ssfr_floor_row does that when the counts are known). floor: number, function of x, or table {'x': [...], 'floor': [...]}, in log10 per year."""
    f = _spec_function(floor, "floor", "floor")
    out = []
    for p in points:
        fl = float(f(np.array([p["x"]]))[0])
        if not math.isfinite(fl):
            raise ValueError("floor returned a non-finite value")
        if p["y"] < fl:
            continue
        q = dict(p)
        if _finite(p.get("yLow")) and p["yLow"] < fl:
            q["yLow"] = fl
            q["clipped"] = True
        out.append(q)
    return out


def _row_quantile(row, edges, total, q):
    target = q * total
    cum = 0.0
    for j, c in enumerate(row):
        if c > 0 and cum + c >= target:
            t = (target - cum) / c
            return edges[j] + min(1.0, max(0.0, t)) * (edges[j + 1] - edges[j])
        cum += c
    return edges[-1]


def ssfr_floor_row(row, y_edges, floor_log, levels=(0.16, 0.5, 0.84)):
    """For one row of per-galaxy counts over sSFR edges (a record's representation.distribution): drop the counts below the floor (the bin that holds the floor keeps its upper share, galaxies being spread evenly
    within a bin, as in compare.js) and return the detected fraction and the quantiles of the detected galaxies (linear within a bin, the rule of compare.js distQuantile)."""
    if len(row) + 1 != len(y_edges):
        raise ValueError("y_edges must have one more entry than row")
    kept = []
    for c, lo, hi in zip(row, y_edges[:-1], y_edges[1:]):
        kept.append(0.0 if hi <= floor_log else c if lo >= floor_log else c * (hi - floor_log) / (hi - lo))
    total, det = float(sum(row)), float(sum(kept))
    return {"total": total, "detected": det, "fractionDetected": det / total if total > 0 else float("nan"), "levels": list(levels),
            "quantiles": [_row_quantile(kept, y_edges, det, q) if det > 0 else float("nan") for q in levels]}


def sfr_floor_to_ssfr(sfr_min_log, log_m):
    """A floor in SFR (log10 Msun/yr) is an sSFR floor of sfr_min_log - log10 M at mass log10 M."""
    return sfr_min_log - log_m


def read_curve(path_or_text):
    """Read a curve from a file or text: comma, semicolon (with decimal commas), tab or space separated rows; a byte-order mark; comment lines starting with #; an optional header; a units row; missing values.
    Returns x, y and a 1-sigma error array (NaN where there is none)."""
    p = Path(str(path_or_text))
    text = p.read_text(encoding="utf-8-sig") if len(str(path_or_text)) < 400 and p.exists() else str(path_or_text).lstrip("﻿")
    rows = [l.strip() for l in re.split(r"\r\n|\r|\n", text) if l.strip() and not l.strip().startswith("#")]
    cells = lambda l: [c.strip().replace(",", ".") for c in l.split(";")] if ";" in l else [c for c in re.split(r"[,\t ]+", l) if c]
    num = lambda c: float(c) if re.fullmatch(r"[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?", c or "") else float("nan")
    head = None
    if rows and math.isnan(num(cells(rows[0])[0])):
        head = [re.sub(r"[^a-z]", "", h.lower()) for h in cells(rows.pop(0))]
    pick = lambda names, default: next((i for i, h in enumerate(head or []) if h in names), default)
    ix, iy, ie = pick(("x", "logm", "mass", "mstar", "logmstar", "z", "redshift"), 0), pick(("y", "logphi", "phi", "value", "sfr", "ssfr", "logsfr"), 1), pick(("err", "sigma", "yerr", "error", "dy"), 2 if head is None else -1)
    xs, ys, es = [], [], []
    for l in rows:
        c = [num(v) for v in cells(l)]
        if len(c) <= max(ix, iy) or math.isnan(c[ix]) or math.isnan(c[iy]):
            continue
        xs.append(c[ix]); ys.append(c[iy]); es.append(c[ie] if 0 <= ie < len(c) else float("nan"))
    return np.array(xs), np.array(ys), np.array(es)


def describe(res, relation, z):
    """One plain sentence about a compare_run table, as the website writes it."""
    if res.empty:
        return f"No published curve of {relation} near z = {z:g}."
    fair = res[(res["verdict"] != "not-comparable") & (res["n_bins"] > 0)]
    ok = fair[fair["verdict"] == "comparable"]
    if not len(fair):
        return f"None of the {len(res)} published curves at this epoch is comparable with the definitions you declared (or shares enough x range), so there is no fair offset to report."
    use = (ok if len(ok) else fair)["median_dy"]
    best = fair.sort_values("rms_dy").iloc[0]
    thin = " With fewer than three curves, treat this as indicative only." if len(use) < 3 else ""
    return (f"Your run is {use.median():+.2f} from the {'comparable' if len(ok) else 'comparable-with-caveats'} curves (median; range {use.min():+.2f} to {use.max():+.2f}, {len(use)} curve{'s' if len(use) > 1 else ''}), in the y units of the relation. "
            f"The closest is {best['source']} {best['run'] or ''} (rms {best['rms_dy']:.2f} over {int(best['n_bins'])} shared points).{thin}").replace("  ", " ")


def main(argv=None):
    """Command line: sim-highline compare my.csv --relation gsmf --z 0.1 --define imf=chabrier03 --define densityFrame=comoving"""
    import argparse
    ap = argparse.ArgumentParser(prog="sim-highline", description="Compare your own curve with every published curve of a relation, as the website does.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compare", help="compare a curve file with the published curves at one epoch")
    c.add_argument("file", help="CSV or text file: x, y and an optional 1-sigma error per row (log10 values unless --linear)")
    c.add_argument("--relation", required=True, help="relation code, for example gsmf, sfms, mzr, size, shmr, bh")
    c.add_argument("--z", type=float, required=True, help="redshift of your curve")
    c.add_argument("--define", action="append", default=[], metavar="KEY=VALUE", help="what your numbers mean, for example imf=chabrier03; repeat for each definition")
    c.add_argument("--linear", action="store_true", help="the values are linear, not log10")
    c.add_argument("--rankable-only", action="store_true", help="leave out curves that are context only")
    c.add_argument("--name", default="your run")
    c.add_argument("--csv", help="write the full table to this CSV file")
    c.add_argument("--top", type=int, default=15, help="rows to print")
    a = ap.parse_args(argv)
    x, y, e = read_curve(a.file)
    if len(x) < 3:
        raise SystemExit(f"{a.file}: fewer than three numeric rows were read")
    defs = dict(d.split("=", 1) for d in a.define)
    res = compare_run(x, y, a.relation, a.z, definitions=defs, sigma=e if np.isfinite(e).any() else None, linear=a.linear, rankable_only=a.rankable_only, name=a.name)
    print(f"{len(x)} points read from {a.file}; relation {a.relation}, z = {a.z:g}; definitions: {defs or 'none declared, so nothing can be called comparable'}")
    print(describe(res, a.relation, a.z))
    if not res.empty:
        with pd.option_context("display.width", 200, "display.max_columns", 20, "display.max_colwidth", 38):
            print(res[["source", "run", "tier", "verdict", "median_dy", "rms_dy", "n_bins"]].head(a.top).to_string(index=False, float_format=lambda v: f"{v:+.2f}" if abs(v) < 100 else f"{v:.0f}"))
        if a.csv:
            res.to_csv(a.csv, index=False)
            print(f"full table written to {a.csv}")


if __name__ == "__main__":
    main()
