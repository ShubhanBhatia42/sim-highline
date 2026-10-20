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
