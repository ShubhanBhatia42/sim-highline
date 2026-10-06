"""Load the sim-highline scaling-relation dataset into pandas / numpy.

    import sim_highline
    df = sim_highline.load()                                   # tidy table, one row per plotted point
    sel = sim_highline.select(df, relation="sfms", z=(1, 2), sources=["EAGLE", "IllustrisTNG"], rankable=True)
    one = sim_highline.nearest_epoch(sel, z=1.5)               # one record per source/run, nearest published epoch (nothing is interpolated)
    x, y, lo, hi = sim_highline.curve(df, "schaye15.eagle-refl0100n1504.sfms.z1")
    print(sim_highline.bibtex(sel))

Units are log10, physical and h-free as published; x_unit, y_unit, x_definition, y_definition and the definition columns
(imf, mass_definition, population, ...) say exactly what each curve is. Compare curves only when those agree.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

KEYS = ["kind", "source", "run", "relation"]


def _base(path):
    if path is not None:
        return str(path).rstrip("/")
    for cand in (Path.cwd() / "data" / "export", Path(__file__).resolve().parent / "data" / "export"):
        if (cand / "sim-highline-records.csv").exists():
            return str(cand)
    raise FileNotFoundError("data/export not found; pass the folder or base URL containing sim-highline-records.csv")


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
