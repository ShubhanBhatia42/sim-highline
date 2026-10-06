import hashlib
import json
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
bib = sim_highline.bibtex(sim_highline.select(df, sources="EAGLE"))
assert bib.count("@misc") >= 5 and "10.1093/mnras/stu2058" in bib
print(f"sim-highline loader test passed: {len(records)} records, {len(df)} points, v{man['version']}")
