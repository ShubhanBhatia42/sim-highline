"""Tests of the quenching-shape machinery (scripts/analyze_quenching_shape.py) on synthetic two-code worlds with known structure, and that its saved outputs, if present, are consistent. The synthetic worlds only check that the code does
what the protocol says; they are not a calibration of the estimators for this block layout (protocol section 6)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import numpy as np
except ImportError:
    print("quenching shape test skipped: numpy not installed")
    raise SystemExit(0)
import analyze_joint_reachability as J
import analyze_quenching_shape as Q
import power_joint_reachability as P

ROOT = Path(__file__).resolve().parent.parent
SMALL = dict(nsplit=8, nstarts=3, sens=True, workers=1)


def world(kind="identical", shape_shift=0.0, s4_shift=0.0, seed=21, n_lh=300):
    """The earlier study's synthetic world at one snapshot plus the three shape families (10 bins each) with the same linear-response structure; SIMBA's gv is offset by `shape_shift`."""
    w = P.world("shift" if s4_shift else "identical", seed, n_lh=n_lh, snaps=("090",), shift=s4_shift)
    r = np.random.default_rng(seed + 100)
    new = [(f, "090", b) for f in ("gv", "sfw", "gvwide") for b in range(10)]
    base = r.uniform(-1, 1, len(new))
    R = r.normal(0, 0.25, (len(new), 4))
    off = np.array([shape_shift if f in ("gv", "gvwide") else 0.0 for f, _, _ in new])
    for code, o in (("IllustrisTNG", 0.0 * off), ("SIMBA", off)):
        rr = np.random.default_rng([seed, 7 if code == "IllustrisTNG" else 8])
        for sset, n, fixed in (("LH", n_lh, False), ("CV", 27, True)):
            X = w["suites"][code][sset]["X"]
            Y2 = base[None, :] + o[None, :] + X[:, 2:] @ R.T + rr.normal(0, 0.1, (len(X), len(new)))
            w["suites"][code][sset]["Y"] = np.hstack([w["suites"][code][sset]["Y"], Y2])
    w["meta"]["columns"] = w["meta"]["columns"] + new
    w["counts"] = {c: {(k, "090"): np.full((27, 10), 100.0) for k in ("ngal", "nsf")} for c in J.SUITES}
    return w


import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
_POOL = ProcessPoolExecutor(3, mp_context=mp.get_context("fork"))
_RUN = {"identical": _POOL.submit(Q.run, world("identical"), **SMALL), "gv_shifted": _POOL.submit(Q.run, world(shape_shift=1.5), **SMALL), "s4_shifted": _POOL.submit(Q.run, world(s4_shift=1.5), **SMALL)}

# ---- the paired rule on constructed splits
def fake(between, ctl_t, ctl_s, verdict):
    return {"between_raw": list(between), "control_raw_IllustrisTNG": list(ctl_t), "control_raw_SIMBA": list(ctl_s)}, {"verdict": verdict}

base_sp, base_sm = fake([1.0] * 20, [0.2] * 20, [0.2] * 20, "unresolved")
big_up, sm_up = fake([1.6] * 20, [0.2] * 20, [0.2] * 20, "structural")
big_flat, sm_flat = fake(list(1.0 + np.linspace(-0.08, 0.08, 20)), [0.2] * 20, [0.2] * 20, "unresolved")
big_tiny, sm_tiny = fake([1.02] * 20, [0.2] * 20, [0.2] * 20, "unresolved")
big_mid, sm_mid = fake(list(np.linspace(0.9, 1.4, 20)), [0.2] * 20, [0.2] * 20, "unresolved")
big_weak, sm_weak = fake([1.6] * 20, [0.2] * 20, [0.2] * 20, "removable")
sp = {"base": base_sp, "tiny": big_tiny, "up": big_up, "flat": big_flat, "mid": big_mid, "weak": big_weak}
sm = {"base": base_sm, "tiny": sm_tiny, "up": sm_up, "flat": sm_flat, "mid": sm_mid, "weak": sm_weak}
assert Q.paired(sp, "up", "base", sm)["verdict"] == "adds separation"
# amendment A1: a rise that the same-code controls show equally (more outputs, no more separation) is not separation, however consistent
rise, sm_rise = fake(list(1.04 + 0.01 * np.sin(np.arange(20))), list(0.24 + 0.01 * np.sin(np.arange(20))), list(0.24 + 0.01 * np.sin(np.arange(20))), "unresolved")
sp["rise"], sm["rise"] = rise, sm_rise
sp["base"] = {"between_raw": [1.0] * 20, "control_raw_IllustrisTNG": [0.2] * 20, "control_raw_SIMBA": [0.2] * 20}
rr = Q.paired(sp, "rise", "base", sm)
assert rr["verdict"] == "adds nothing detectable" and rr["between"]["p5"] > 0 and rr["excess"]["p95"] < Q.ADD_MIN, rr
assert Q.paired(sp, "flat", "base", sm)["verdict"] == "adds nothing detectable"
# a tiny but perfectly consistent rise satisfies both conditions of the rule as written; the first listed (adds separation) is reported and the flag says so
tiny = Q.paired(sp, "tiny", "base", sm)
assert tiny["verdict"] == "adds separation" and tiny["both_conditions"] and abs(tiny["excess"]["p50"] - 0.02) < 1e-9
assert Q.paired(sp, "mid", "base", sm)["verdict"] == "unresolved"
assert Q.paired(sp, "weak", "base", sm)["verdict"] == "unresolved"   # the distance rose but the verdict is weaker than the base's: the rule does not call that separation
try:
    Q.paired({**sp, "short": fake([1.0] * 5, [0.2] * 5, [0.2] * 5, "removable")[0]}, "short", "base", {**sm, "short": {"verdict": "removable"}})
    raise AssertionError("paired sets with different numbers of splits must be refused")
except ValueError:
    pass

# ---- merged data: the loader keeps the columns of both ensembles aligned (a real ensemble is checked below if present)
d_syn = world()
keep, blocks, _ = J.eligibility(d_syn)
assert ("gv", "090") in blocks and ("sfw", "090") in blocks and ("gvwide", "090") in blocks and len(blocks) == len(J.FAMILIES) + 3

# ---- identical codes: nothing is structural, the shape adds nothing, the negative control and the numerical checks hold
r0 = _RUN["identical"].result()
assert r0["splits"]["shape"]["verdict"] == "removable", r0["splits"]["shape"]
assert r0["paired"]["Q2"]["verdict"] != "adds separation" and r0["paired"]["Q3"]["verdict"] != "adds separation", (r0["paired"]["Q2"], r0["paired"]["Q3"])
assert r0["validations"]["V1"]["passed"] and r0["validations"]["V2"]["passed"] and r0["validations"]["V3"]["passed"] and r0["validations"]["V4"]["passed"], r0["validations"]
assert set(r0["sets"] if "sets" in r0 else r0["meta"]["sets"]) >= {"shape", "sf2", "sf2+shape", "joint", "joint+shape", "hmf", "S2:gv", "S2:sfw", "S3:wide", "S1:shape", "S1:joint+shape"}
# every set has the same number of splits: split k is the same pair of halves for all of them
assert len({len(s["between"]) if isinstance(s["between"], list) else s["n"] for s in r0["splits"].values()}) == 1

# ---- the green-valley fraction of one code offset by 1.5 noise-free units no parameter can absorb: the shape is structural, gv alone is, sfw alone is not, and it adds separation to the usual two and to the joint set
r1 = _RUN["gv_shifted"].result()
assert r1["splits"]["shape"]["verdict"] == "structural" and r1["splits"]["S2:gv"]["verdict"] == "structural" and r1["splits"]["S2:sfw"]["verdict"] == "removable", {k: r1["splits"][k]["verdict"] for k in ("shape", "S2:gv", "S2:sfw")}
assert r1["splits"]["sf2"]["verdict"] == "removable" and r1["splits"]["sf2+shape"]["verdict"] == "structural"
assert r1["paired"]["Q2"]["verdict"] == "adds separation", r1["paired"]["Q2"]
assert r1["splits"]["joint"]["verdict"] == "removable" and r1["paired"]["Q3"]["verdict"] == "adds separation", (r1["splits"]["joint"]["verdict"], r1["paired"]["Q3"])
assert r1["splits"]["S3:wide"]["verdict"] == "structural"
assert r1["decomposition"]["shape"][0]["family"] == "gv" and r1["decomposition"]["shape"][0]["share"] > 0.8

# ---- the earlier study's family already structural, the shape identical: the shape set is removable, and adding it to the joint set adds nothing (it dilutes)
r2 = _RUN["s4_shifted"].result()
assert r2["splits"]["shape"]["verdict"] == "removable" and r2["splits"]["joint"]["verdict"] == "structural"
assert r2["paired"]["Q3"]["verdict"] == "adds nothing detectable", r2["paired"]["Q3"]
assert r2["paired"]["Q3"]["between"]["p95"] < Q.ADD_MIN

# ---- the V3 rule flags resolution-limited outputs
w3 = world()
for c in J.SUITES:
    w3["counts"][c][("ngal", "090")][:, :4] = 12.0
keep3, blocks3, _ = J.eligibility(w3)
rv = Q.validations(w3, J.build_emulators(w3, keep3)[1], keep3, {b: np.array(v) for b, v in blocks3.items()}, J.noise_scale(J.build_emulators(w3, keep3)[1]),
                   {"shape": [("gv", "090"), ("sfw", "090")], "hmf": [("hmf", "090")]}, [("gv", "090"), ("sfw", "090")], {"hmf": {"verdict": "removable", "between": {"p50": 0}, "control": {"p95": 0}}}, J.build_emulators(w3, keep3)[0], 2, w3["meta"]["columns"])
assert abs(rv["V3"]["share_below_30"] - 4 / 20) < 1e-9 and rv["V3"]["passed"]    # 4 of 20 outputs (20 %): below the 25 % limit
for c in J.SUITES:
    w3["counts"][c][("ngal", "090")][:, :7] = 12.0
rv2 = Q.validations(w3, J.build_emulators(w3, keep3)[1], keep3, {b: np.array(v) for b, v in blocks3.items()}, J.noise_scale(J.build_emulators(w3, keep3)[1]),
                    {"shape": [("gv", "090"), ("sfw", "090")], "hmf": [("hmf", "090")]}, [("gv", "090"), ("sfw", "090")], {"hmf": {"verdict": "removable", "between": {"p50": 0}, "control": {"p95": 0}}}, J.build_emulators(w3, keep3)[0], 2, w3["meta"]["columns"])
assert not rv2["V3"]["passed"]

# ---- the report renders and mentions the three questions
r1b = Q.to_plain({**r1, "version": "x", "parameters": {"seed": Q.SEED, "nsplit": 8}})
r1b["deviations"] = Q.deviations(r1b)
r1b["headline"] = Q.headline(r1b)
doc = Q.render(r1b)
assert all(k in doc for k in ("Q1", "Q2", "Q3", "do not edit by hand", "adds separation")) and doc.count("|") > 120

# ---- the saved outputs, if present, are the rendering of each other and match the data
saved = ROOT / "data" / "analysis" / "quenching-shape.json"
ens = ROOT / "data" / "ensembles" / "camels-distshape.json"
if saved.exists():
    s = json.loads(saved.read_text())
    assert (ROOT / "docs" / "ANALYSIS-quenching-shape.md").read_text() == Q.render(s), "the report is not the rendering of the saved analysis"
    assert s["verdicts"]["Q1"] == s["splits"]["shape"]["verdict"] and s["verdicts"]["Q2"] == s["paired"]["Q2"]["verdict"] and s["verdicts"]["Q3"] == s["paired"]["Q3"]["verdict"]
    assert len({v["n"] for v in s["splits"].values()}) == 1
    if ens.exists():
        g = Q.load()
        keepr, blocksr, _ = J.eligibility(g)
        assert s["meta"]["n_outputs_eligible"] == int(keepr.sum()) and s["meta"]["n_blocks"] == len(blocksr), "analysis output is stale; rerun analyze_quenching_shape.py"
chk = ROOT / "data" / "analysis" / "quenching-shape-checks.json"
if chk.exists():
    import check_quenching_shape as C
    c = json.loads(chk.read_text())
    assert (ROOT / "docs" / "CHECKS-quenching-shape.md").read_text() == C.render(c), "the checks report is not the rendering of its saved numbers"
    assert all(r["min"] <= r["median"] <= r["max"] for d in c["distances"].values() for r in d["rows"].values())
print("quenching shape: OK")
