import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    import numpy as np
    import pandas as pd
except ImportError:
    print("rules parity test skipped: pandas/numpy not installed")
    raise SystemExit(0)
if shutil.which("node") is None:
    print("rules parity test skipped: node not installed")
    raise SystemExit(0)
import sim_highline

oracle = json.loads(subprocess.run(["node", str(ROOT / "scripts/rules-oracle.mjs")], capture_output=True, text=True, check=True).stdout)
records = {r["id"]: r for r in json.loads((ROOT / "data/export/sim-highline-records.json").read_text())["records"]}
R = sim_highline.rules()
bad = []
for v in oracle["verdicts"]:
    got = sim_highline.compatible(records[v["a"]], records[v["b"]], R)
    if (got["verdict"], len(got["blockers"]), len(got["caveats"])) != (v["verdict"], v["nb"], v["nc"]):
        bad.append((v, got["verdict"], len(got["blockers"]), len(got["caveats"])))
assert not bad, f"{len(bad)} of {len(oracle['verdicts'])} pairs disagree with the website rules, first: {bad[0]}"
kinds = {v["verdict"] for v in oracle["verdicts"]}
assert {"comparable", "comparable-with-caveats", "not-comparable"} <= kinds, f"oracle sample did not exercise every verdict: {kinds}"

# population classes: a quiescent, centrals-only or zoom-sample mass function is not one of all galaxies; spelling variants of "all" are one population (the same cases as scripts/test-compare.mjs)
cases = {"all": "all", "all galaxies": "all", "all galaxies (PGalF)": "all", "All galaxies": "all", "quiescent": "quiescent", "passive": "quiescent", "all galaxies, passive": "quiescent", "star-forming": "star-forming",
         "all galaxies, star-forming": "star-forming", "centrals": "centrals", "satellites": "satellites", "all galaxies of the zoom sample, as drawn": "zoom", "something else": "something else",
         "star-forming-centrals": "centrals star-forming", "zoom-centrals": "centrals zoom", "isolated-zoom-centrals": "centrals isolated zoom", "star-forming galaxies, sSFR > 0.2 / t_H(z)": "star-forming galaxies, sSFR > 0.2 / t_H(z)"}
for text, want in cases.items():
    assert sim_highline.population_class(text) == want, (text, sim_highline.population_class(text), want)


def _gsmf(population, source):
    return {"relation": "gsmf", "source": source, "rankable": True, "epoch": {"zRepresentative": 1}, "definitions": {"densityFrame": "comoving", "imf": "chabrier03", "massDefinition": "total", "cosmology": {"H0": 70, "Om": 0.3}, "population": population}}


assert sim_highline.compatible(_gsmf("all", "A"), _gsmf("all galaxies", "B"), R)["verdict"] == "comparable"
for other in ("quiescent", "centrals", "all galaxies of the zoom sample, as drawn", "star-forming"):
    got = sim_highline.compatible(_gsmf("all", "A"), _gsmf(other, "B"), R)
    assert got["verdict"] == "not-comparable" and any(b.startswith("population") for b in got["blockers"]), (other, got)

u = oracle["user"]
n = 0
for s in oracle["stats"]:
    r = records[s["id"]]
    ref_pts = sorted((p for p in r["representation"]["points"] if all(isinstance(p.get(k), (int, float)) for k in ("x", "y"))), key=lambda p: p["x"])
    ref = {"x": [p["x"] for p in ref_pts], "y": [p["y"] for p in ref_pts], "lo": [p.get("yLow", float("nan")) for p in ref_pts], "hi": [p.get("yHigh", float("nan")) for p in ref_pts]}
    got = sim_highline.summarize(sim_highline.residuals({"x": u["x"], "y": u["y"], "lo": u["lo"], "hi": u["hi"]}, ref, "uncertainty", "uncertainty" if r["representation"].get("intervalKind") == "uncertainty" else "unspecified"))
    want = s["summary"]
    assert (got is None) == (want is None), (s["id"], got, want)
    if got:
        n += 1
        for k_py, k_js in (("n", "n"), ("median", "median"), ("mean", "mean"), ("rms", "rms")):
            assert math.isclose(got[k_py], want[k_js], rel_tol=1e-9, abs_tol=1e-9), (s["id"], k_py, got[k_py], want[k_js])
        if want["meanAbsSigma"] is not None and math.isfinite(want["meanAbsSigma"]):
            assert math.isclose(got["mean_abs_sigma"], want["meanAbsSigma"], rel_tol=1e-9), (s["id"], "sigma")
assert n >= 15, n

x = np.arange(8, 11.6, 0.5)
out = sim_highline.compare_run(x, -1.5 - 0.4 * (x - 8), "gsmf", z=0.0, definitions={"imf": "chabrier03", "massDefinition": "aperture-50pkpc", "densityFrame": "comoving"}, sigma=np.full(len(x), 0.05))
assert len(out) >= 8 and out["n_bins"].max() >= 5 and set(out["verdict"]) <= {"comparable", "comparable-with-caveats", "not-comparable"}
none = sim_highline.compare_run(x, -1.5 - 0.4 * (x - 8), "gsmf", z=0.0)
assert (none["verdict"] == "comparable").sum() == 0, "undeclared definitions must never be called comparable"
print(f"rules parity OK: {len(oracle['verdicts'])} pairs, {n} residual summaries identical to the website")
