"""Tests of the joint-reachability machinery (scripts/analyze_joint_reachability.py) on synthetic two-code worlds with known structure, and that its saved outputs, if present, are not stale."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import numpy as np
except ImportError:
    print("joint reachability test skipped: numpy not installed")
    raise SystemExit(0)
import analyze_joint_reachability as J
import analyze_model_form as A
import power_joint_reachability as P

ROOT = Path(__file__).resolve().parent.parent
SMALL = dict(nsplit=6, nsmall=4, npath=3, nstarts=3, sens=False, workers=2)


def go(kind, shift=0.0, seed=11):
    return J.run(data=P.world(kind, seed, n_lh=300, snaps=("090",), shift=shift), **SMALL)


# ---- noise scale, sets and weights
d0 = P.world("identical", 3, n_lh=300, snaps=("090",))
keep, blocks, det = J.eligibility(d0)
assert keep.sum() == len(d0["meta"]["columns"]) and len(blocks) == len(J.FAMILIES)
idx_by_block = {b: np.array(v) for b, v in blocks.items()}
emus, info = J.build_emulators(d0, keep)
scale = J.noise_scale(info)
assert np.all(scale[keep] >= J.FLOOR) and 0.1 < np.median(scale[keep]) < 0.4, np.median(scale[keep])  # seed scatter 0.1 per code: sqrt(2) x 0.1 plus emulator error
idx, c = J.make_set(idx_by_block, [b for b in blocks if b[0] != "hmf"], scale)
w = (c * scale[idx]) ** 2  # the weights w_k: mean 1, equal total per block
assert abs(w.mean() - 1.0) < 1e-9
tot = {b: sum(w[i] for i, j in enumerate(idx) if j in set(idx_by_block[b])) for b in blocks if b[0] != "hmf"}
assert max(tot.values()) - min(tot.values()) < 1e-9
# an output missing in too many simulations is not eligible, and a block with fewer than 3 eligible outputs is dropped
d1 = P.world("identical", 3, n_lh=300, snaps=("090",))
cols = d1["meta"]["columns"]
jbad = [j for j, (f, s, b) in enumerate(cols) if f == "gsmf"]
for suite in J.SUITES:
    d1["suites"][suite]["LH"]["Y"][: 60, jbad[:8]] = np.nan  # 20 % missing in 8 of the 10 outputs
k1, b1, _ = J.eligibility(d1)
assert not k1[jbad[:8]].any() and ("gsmf", "090") not in b1

# ---- identical codes: everything is removable and the controls are at the noise floor
r0 = go("identical")
assert r0["splits"]["all"]["verdict"] == "removable", r0["splits"]["all"]
assert all(r0["splits"]["fam:" + f]["verdict"] == "removable" for f in J.JOINT_FAMILIES), {f: r0["splits"]["fam:" + f]["verdict"] for f in J.JOINT_FAMILIES}
assert r0["splits"]["all"]["control"]["p95"] < 0.6 and r0["point"]["all"]["D"] < 0.5
assert r0["validations"]["V2"]["passed"] and r0["validations"]["V1"]["passed"] and r0["validations"]["V5"]["passed"]
assert r0["J3"]["mechanism"] is None

# ---- one family shifted by an amount no parameter can absorb: that family is structural alone, so is the joint distance, and it is classed irreducible
r1 = go("shift", shift=1.5)
st = [f for f in J.JOINT_FAMILIES if r1["splits"]["fam:" + f]["verdict"] == "structural"]
assert st == ["bhocc"], st
assert r1["splits"]["all"]["verdict"] == "structural" and r1["J3"]["mechanism"] == "irreducible"
assert r1["greedy_path"][0]["family"] == "bhocc", r1["greedy_path"][:3]  # the shifted family is the first to be added
assert r1["splits"]["path:1"]["verdict"] == "structural"
r1b = go("shift", shift=0.15)
assert r1b["splits"]["all"]["verdict"] == "removable", r1b["splits"]["all"]  # a small shift is within the margin

# ---- every family reachable alone but by different parameter pairs: no family is structural alone, the joint distance is, the ratio is far above the same-code null, and it is classed a conflict
r2 = go("conflict")
assert not any(r2["splits"]["fam:" + f]["verdict"] == "structural" for f in J.JOINT_FAMILIES), {f: r2["splits"]["fam:" + f]["verdict"] for f in J.JOINT_FAMILIES}
assert r2["splits"]["all"]["verdict"] == "structural", r2["splits"]["all"]
assert r2["J3"]["above_null"] is True and r2["J3"]["ratio_point"] > 10 and r2["J3"]["ratio_between"]["p5"] > 5 * r2["J3"]["ratio_control"]["p95"], r2["J3"]
assert r2["J3"]["mechanism"] == "conflict", r2["J3"]
assert r2["point"]["all"]["D"] > 5 * r2["point"]["fam:gsmf"]["D"]
# identical codes: the ratio of the squared distances is above 1 by construction (extra parameters absorb noise) but not above the same-code null
assert r0["J3"]["above_null"] is False, r0["J3"]
assert r0["J3"]["ratio_between"]["p50"] > 1.0 and r0["J3"]["ratio_control"]["p50"] > 1.0
# the squared joint distance is never smaller than the weighted mean of the family distances (point estimate and every split)
assert r2["J3"]["ratio_point"] >= 1.0 - 1e-6 and r1["J3"]["ratio_point"] >= 1.0 - 1e-6 and r0["J3"]["ratio_point"] >= 1.0 - 1e-6

# ---- the emulator-error correction: the corrected distance of identical codes is below the raw one and the correction never goes below zero; the variance estimate is half the squared half-sample difference
assert J.corrected(1.0, 0.36, 0.0) == 0.8 and J.corrected(0.3, 1.0) == 0.0
assert r0["splits"]["all"]["between"]["p50"] <= r0["splits"]["all"]["between_raw"]["p50"] + 1e-12
assert r0["point"]["all"]["D_corrected"] <= r0["point"]["all"]["D"] + 1e-12
ia, ib = A.split_halves(300, np.random.default_rng(2))
ea, eb = A.fit_emulator(d0["suites"]["SIMBA"]["LH"]["X"][ia], d0["suites"]["SIMBA"]["LH"]["Y"][ia]), A.fit_emulator(d0["suites"]["SIMBA"]["LH"]["X"][ib], d0["suites"]["SIMBA"]["LH"]["Y"][ib])
idx_all, c_all = J.make_set(idx_by_block, [b for b in blocks if b[0] != "hmf"], scale)
v_fid, v_corner = J.emu_var(ea, eb, np.zeros(4), idx_all, c_all), J.emu_var(ea, eb, np.ones(4), idx_all, c_all)
assert 0 < v_fid < v_corner, (v_fid, v_corner)  # the emulators are noisier at the corner of the box than at the fiducial point

# ---- decomposition: the shares add to 1 and the shifted family carries most of the distance
dec = r1["decomposition"]
assert abs(sum(x["share"] for x in dec) - 1.0) < 1e-9 and dec[0]["family"] == "bhocc" and dec[0]["share"] > 0.5, dec[:2]

# ---- the report renders and the headline mentions the verdicts
r1.update({"version": "x", "parameters": {"seed": J.SEED}})
r1["verdicts"], r1["deviations"] = J.verdicts(r1), J.deviations(r1)
doc = J.render(r1)
assert "J1" in doc and "do not edit by hand" in doc and doc.count("|") > 150 and "irreducible" in doc

# ---- the saved analysis, if present, is not stale
saved = ROOT / "data" / "analysis" / "joint-reachability.json"
gal = ROOT / "data" / "ensembles" / "camels-galaxies.json"
if saved.exists() and gal.exists():
    s = json.loads(saved.read_text())
    assert s["version"] == json.loads((ROOT / "data" / "release.json").read_text())["version"], "analysis output is stale; rerun analyze_joint_reachability.py"
    g = J.load_galaxies()
    keepr, blocksr, _ = J.eligibility(g)
    assert s["meta"]["n_outputs_eligible"] == int(keepr.sum()) and s["meta"]["n_blocks"] == len(blocksr), "analysis output is stale; rerun analyze_joint_reachability.py"
print("joint reachability: OK")
