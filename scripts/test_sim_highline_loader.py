import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("sim-highline loader test skipped: pandas/numpy not installed")
    raise SystemExit(0)
import sim_highline

EXP = ROOT / "data" / "export"
man = json.loads((EXP / "sim-highline-manifest.json").read_text())
records = [r for f in sorted((ROOT / "data" / "curves").glob("*.json")) for r in json.loads(f.read_text())["records"]]
assert man["nRecords"] == len(records), (man["nRecords"], len(records))
for name, meta in man["files"].items():
    assert hashlib.sha256((EXP / name).read_bytes()).hexdigest() == meta["sha256"], name
df = sim_highline.load()
assert df["record_id"].nunique() == len(records) and len(df) == man["nPoints"]
assert df.groupby("record_id").size().min() >= 1
assert df.attrs["version"] == man["version"] == json.loads((ROOT / "data" / "release.json").read_text())["version"]

step = max(1, len(records) // 40)
for r in records[::step]:
    x, y, lo, hi = sim_highline.curve(df, r["id"])
    if r["representation"]["type"] == "points":
        pts = r["representation"]["points"]
        assert np.allclose(x, [p["x"] for p in pts]) and np.allclose(y, [p["y"] for p in pts]), r["id"]
        assert np.allclose(lo, [p.get("yLow", np.nan) for p in pts], equal_nan=True), r["id"]
    else:
        assert 2 <= len(x) <= 40 and np.isfinite(y).all(), r["id"]
        assert abs(x[0] - r["domain"]["xMin"]) < 1e-9 and abs(x[-1] - r["domain"]["xMax"]) < 1e-9, r["id"]

sel = sim_highline.select(df, relation="sfms", kind="simulation")
assert set(sel["relation"]) == {"sfms"} and set(sel["kind"]) == {"simulation"}
one = sim_highline.nearest_epoch(sel, z=2.0)
assert len(one) and ((one["z_min"] <= 2.0 + 0.25) & (one["z_max"] >= 2.0 - 0.25)).all()
assert one.groupby(sim_highline.KEYS + ["x_definition", "y_definition", "population_note"], dropna=False)["record_id"].nunique().max() == 1
assert not sim_highline.nearest_epoch(sel, z=50.0).shape[0]
rk = sim_highline.select(df, rankable=True)
assert rk["tier"].ne("digitized-figure").all()
third = df[df["terms"].astype(str).str.contains("GPL|no licence", na=False)]
assert third.record_id.nunique() >= 200, third.record_id.nunique()
opened = sim_highline.open_terms(df)
assert not opened.record_id.isin(third.record_id).any() and len(opened) > 0.5 * len(df)
bib = sim_highline.bibtex(sim_highline.select(df, sources="EAGLE"))
assert bib.count("@misc") >= 5 and "10.1093/mnras/stu2058" in bib
dist = sim_highline.load_distributions()
assert len(dist) > 1000 and set(["x_low", "y_high", "count", "source", "relation", "z"]) <= set(dist.columns)
_rid = dist["record_id"].iloc[0]
_m, _xe, _ye = sim_highline.grid(dist, _rid)
assert _m.shape == (len(_xe) - 1, len(_ye) - 1) and _m.sum() == dist[dist["record_id"] == _rid]["count"].sum()
conv = sim_highline.load_conversions()
s = sim_highline.measured_shift("mass.total-to-rad2", "IllustrisTNG", 10.0, 0.0, conv)
assert -0.2 < s["p16"] < s["median"] < s["p84"] < 0.0 and s["se"] is not None and s["se"] < 0.01, s
half = sim_highline.measured_shift("mass.total-to-rad1", "SIMBA", 9.8, 0.0, conv)
assert abs(half["median"] - math.log10(0.5)) < 0.012, half   # the stellar half-mass aperture holds half the stars by definition
for bad in (lambda: sim_highline.measured_shift("mass.total-to-rad2", "SIMBA", 14.0, 0.0, conv), lambda: sim_highline.measured_shift("nope", "SIMBA", 10.0, 0.0, conv)):
    try:
        bad()
        raise AssertionError("should have raised")
    except (ValueError, KeyError):
        pass
cor = sim_highline.corrections()
assert cor and cor[0]["id"] == "grazian15-h70" and len(cor[0]["records"]) == 4
print(f"sim-highline loader test passed: {len(records)} records, {len(df)} points, v{man['version']}")
