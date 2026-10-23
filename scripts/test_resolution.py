"""Tests of the resolution study (scripts/analyze_resolution.py) on synthetic records with known shifts, and that its saved output, if present, is consistent with the dataset. The synthetic cases check that the code does what
docs/PROTOCOL-resolution.md says (pairs that must be built and pairs that must be refused, shifts that must be recovered, labels that must come out); they say nothing about any real model."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import numpy as np
except ImportError:
    print("resolution test skipped: numpy not installed")
    raise SystemExit(0)
import analyze_resolution as R

ROOT = Path(__file__).resolve().parent.parent
AX = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 number density", "yUnit": "log10(Mpc^-3 dex^-1)"}
SNAPS = {"090": 0.0, "062": 0.95, "042": 2.15, "032": 3.0, "024": 4.0}


def rec(i, run, relation, z, xs, ys, tier="official-table", u=None, defs=None, axes=None):
    return {"id": i, "source": "X", "run": run, "kind": "simulation", "relation": relation, "epoch": {"zRepresentative": z}, "axes": axes or AX, "definitions": defs if defs is not None else {"imf": "chabrier03"},
            "provenance": {"tier": tier, **({"digitizationUncertaintyDex": u} if u is not None else {})}, "representation": {"type": "points", "points": [{"x": float(a), "y": float(b)} for a, b in zip(xs, ys)]}}


def reference(s=0.1):
    out = {("gsmf", sn): {b: s for b in range(10)} for sn in ("090", "062", "042", "032")}
    out.update({("qf", "090"): {b: s for b in range(10)}})
    out.update({("rho", sn): {0: s, 1: s} for sn in SNAPS})
    centres = {f: [9.125 + 0.25 * i for i in range(10)] for f in ("gsmf", "qf")}
    return R.Reference(out, centres, SNAPS, 0.065)


SAVED = {"point": {"fam:gsmf": {"D": 0.6, "D_fiducial": 0.9}, "fam:rho": {"D": 0.2, "D_fiducial": 1.4}, "fam:qf": {"D": 0.2, "D_fiducial": 0.5}}}
X = np.arange(9.0, 11.6, 0.25)
FX = lambda x: -1.0 - 0.8 * (x - 9.0)


def ladder(shifts, z=0.0, prefix="chaikin26.colibre.l025m{}.gsmf.z{:g}", rungs=("7", "6", "5"), xs=X, **kw):
    """Records of one ladder: the coarsest follows FX, each finer rung adds the next shift."""
    recs, y = {}, FX(xs)
    for k, r in enumerate(rungs):
        if k:
            y = y + shifts[k - 1]
        i = prefix.format(r, z)
        recs[i] = rec(i, f"m{r} (L025)", "gsmf", z, xs, y, **kw)
    return recs


def units_of(recs, ref=None, supp=None):
    res = R.run(recs=recs, ref=ref or reference(), saved=SAVED, supp={})
    return res, {(u["rung_a"], u["rung_b"], u["relation"]): u for u in res["units"]}


# ---- a constant shift is recovered, in dex and in noise units; labels follow the rules of section 4
res, u = units_of(ladder([0.05, 0.3]))
a, b = u[("7", "6", "gsmf")], u[("6", "5", "gsmf")]
assert abs(a["rms_dex"] - 0.05) < 1e-9 and abs(a["mean_dex"] - 0.05) < 1e-9 and abs(b["rms_dex"] - 0.3) < 1e-9, (a, b)
assert a["basis"] == "reference" and abs(a["R"] - 0.5) < 1e-9 and a["label"] == "converged", a                    # 0.05 dex / 0.1 noise = 0.5 < 1
assert abs(b["R"] - 3.0) < 1e-9 and abs(b["Rc"] - 3.0) < 1e-9 and b["label"] == "resolution-dependent", b       # tables carry no digitization noise
sp = u[("7", "5", "gsmf")]
assert sp["kind"] == "span" and abs(sp["rms_dex"] - 0.35) < 1e-9, sp
assert u[("7", "6", "gsmf")]["tier"] == "A" and u[("7", "6", "gsmf")]["parameters"] == "recalibrated"
# either side of the margin (noise 0.1): 0.095 dex is converged, 0.105 dex is resolution-dependent
res1, u1 = units_of(ladder([0.095, 0.105]))
assert u1[("7", "6", "gsmf")]["label"] == "converged" and u1[("6", "5", "gsmf")]["label"] == "resolution-dependent"
# zero shift is zero; a mean shift keeps its sign (finer minus coarser)
res0, u0 = units_of(ladder([0.0, -0.2]))
assert u0[("7", "6", "gsmf")]["rms_dex"] == 0.0 and u0[("7", "6", "gsmf")]["R"] == 0.0
assert u0[("6", "5", "gsmf")]["mean_dex"] < 0 and abs(u0[("6", "5", "gsmf")]["mean_dex"] + 0.2) < 1e-9

# ---- digitization noise is removed in quadrature: shift 0.04, two digitized curves of 0.02 dex each, noise 0.01
recs = ladder([0.04, 0.04], tier="digitized-figure", u=0.02)
res, u = units_of(recs, reference(0.01))
a = u[("7", "6", "gsmf")]
assert abs(a["R"] - 4.0) < 1e-9 and abs(a["Rc"] - np.sqrt(16 - 8)) < 1e-9, a
# R_c can fall below the margin while R does not: the label is then cannot tell (digitization decides)
res, u = units_of(ladder([0.025, 0.025], tier="digitized-figure", u=0.02), reference(0.02))
a = u[("7", "6", "gsmf")]
assert a["R"] > 1.0 and a["Rc"] < 1.0 and a["label"] == "cannot tell" and a["qualifier"], a

# ---- the finer curve on a different grid is interpolated (linear function recovered exactly); no extrapolation outside the common range
xs_f = np.arange(9.5, 11.01, 0.1)
recs = ladder([0.07], rungs=("7", "6"))
fine_id = "chaikin26.colibre.l025m6.gsmf.z0"
recs[fine_id] = rec(fine_id, "m6 (L025)", "gsmf", 0.0, xs_f, FX(xs_f) + 0.07)
res, u = units_of(recs)
a = u[("7", "6", "gsmf")]
assert abs(a["rms_dex"] - 0.07) < 1e-9 and abs(a["max_abs_dex"] - 0.07) < 1e-9, a
ep = a["epochs"][0]
assert abs(ep["range"][0] - 9.5) < 1e-9 and abs(ep["range"][1] - 11.0) < 1e-9, ep["range"]

# ---- too few points in the common range: built, not evaluated, cannot tell
recs2 = ladder([0.1], rungs=("7", "6"))
recs2["chaikin26.colibre.l025m6.gsmf.z0"] = rec("chaikin26.colibre.l025m6.gsmf.z0", "m6 (L025)", "gsmf", 0.0, [11.4, 11.5, 11.6], [0.0] * 3)   # common range 11.4 to 11.5: one point of the coarser, two of the finer
res, u = units_of(recs2)
assert u[("7", "6", "gsmf")]["label"] == "cannot tell" and u[("7", "6", "gsmf")]["qualifier"] == "too few points", u[("7", "6", "gsmf")]

# ---- the inclusion rule: what must be refused (with the reason) and what must be built
good = ladder([0.1, 0.1])
built, refused = R.enumerate_pairs(good)
assert len(built) == 3 and not refused and {p["kind"] for p in built} == {"adjacent", "span"}, (len(built), refused)
far = ladder([0.1, 0.1], z=0.0)
far["chaikin26.colibre.l025m6.gsmf.z0"] = rec("chaikin26.colibre.l025m6.gsmf.z0", "m6 (L025)", "gsmf", 0.2, X, FX(X))        # epoch 0.2 away from the others
b2, r2 = R.enumerate_pairs(far)
assert any("not comparable" in r["reason"] for r in r2) and len(b2) == 1, (len(b2), r2)                                        # only the 7 > 5 span pair (both at z = 0) survives
other_defs = ladder([0.1, 0.1])
other_defs["chaikin26.colibre.l025m6.gsmf.z0"] = rec("chaikin26.colibre.l025m6.gsmf.z0", "m6 (L025)", "gsmf", 0.0, X, FX(X), defs={"imf": "kroupa01"})
b3, r3 = R.enumerate_pairs(other_defs)
assert sorted(r["reason"] for r in r3) == ["definitions differ"] * 2 and len(b3) == 1
other_axes = ladder([0.1, 0.1])
other_axes["chaikin26.colibre.l025m6.gsmf.z0"] = rec("chaikin26.colibre.l025m6.gsmf.z0", "m6 (L025)", "gsmf", 0.0, X, FX(X), axes={**AX, "xDefinition": "log10 stellar mass (30 pkpc)"})
assert sorted(r["reason"] for r in R.enumerate_pairs(other_axes)[1]) == ["axes differ"] * 2
# the one allowed free-text exception (THESAN dust correction), and only in that ladder
th = {}
for t, txt in (("1", "dust attenuated (Vogelsberger+20 scaling)"), ("2", "dust attenuated (same dust scaling)")):
    th[f"kannan22.thesan.uvlf.t{t}.z6"] = rec(f"kannan22.thesan.uvlf.t{t}.z6", f"THESAN-{t}", "uvlf", 6.0, X, FX(X), defs={"imf": "chabrier03", "dustCorrection": txt})
assert len(R.enumerate_pairs(th)[0]) == 1
co = ladder([0.1], rungs=("7", "6"), defs={"imf": "chabrier03", "dustCorrection": "a"})
co["chaikin26.colibre.l025m6.gsmf.z0"] = rec("chaikin26.colibre.l025m6.gsmf.z0", "m6 (L025)", "gsmf", 0.0, X, FX(X), defs={"imf": "chabrier03", "dustCorrection": "b"})
assert not R.enumerate_pairs(co)[0], "the dustCorrection exception must not apply outside the THESAN ladder"
# rungs two apart are not an adjacent pair in a three-rung ladder, and records of different ladders are never paired
sk = {k: v for k, v in ladder([0.1, 0.1]).items() if not k.endswith("m6.gsmf.z0")}
bsk, _ = R.enumerate_pairs(sk)
assert [p["kind"] for p in bsk] == ["span"]
mixed = {**ladder([0.1], rungs=("7", "6")), **{"pillepich18.tng-l25n512.fiducial.sfrd": rec("pillepich18.tng-l25n512.fiducial.sfrd", "L25n512", "sfrd", 2.0, X, FX(X))}}
assert len(R.enumerate_pairs(mixed)[0]) == 1

# ---- two epochs near one snapshot: only the closest is a reference epoch-curve; the other falls to the yardstick (counted only if no epoch has a reference)
recs = {}
for z in (0.0, 0.1):
    recs.update(ladder([0.2], z=z, rungs=("7", "6")))
res, u = units_of(recs)
a = u[("7", "6", "gsmf")]
refs = [e for e in a["epochs"] if e["reference"]]
assert len(a["epochs"]) == 2 and len(refs) == 1 and refs[0]["z"] == 0.0 and a["n_curves_counted"] == 1, a["epochs"]
# an epoch whose snapshot is not eligible (z = 4 here has no gsmf block) is evaluated with the yardstick, and the label says so
res, u = units_of(ladder([0.2], z=4.0, rungs=("7", "6")))
a = u[("7", "6", "gsmf")]
assert a["basis"] == "yardstick" and abs(a["R"] - 0.2 / 0.065) < 1e-9, a
# a relation without a counterpart uses the yardstick
fe = {}
for r, y in (("7", 0.0), ("6", 0.1)):
    i = f"chaikin26.colibre.l025m{r}.gsmf.z0"
    fe[i] = rec(i, f"m{r} (L025)", "uvlf", 0.0, X, FX(X) + y)
res, u = units_of(fe)
assert u[("7", "6", "uvlf")]["basis"] == "yardstick" and u[("7", "6", "uvlf")]["family"] is None

# ---- tier B: a small shift may be 'converged' with the qualifier; a large one is never 'resolution-dependent'
def tier_b(dy):
    d = {}
    for t, off in (("300", 0.0), ("50", dy)):
        i = f"donnari21.tng{t}.quenched-cent.z0.1"
        d[i] = rec(i, f"TNG{t}-1", "quenched", 0.1, X, 0.3 + off + 0.0 * X, axes={**AX, "yUnit": "fraction"})
    return units_of(d)[1][("300", "50", "quenched")]
a = tier_b(0.5)
assert a["tier"] == "B" and a["y_kind"] == "fraction" and a["label"] == "cannot tell" and "box" in a["qualifier"] and a["R"] > 1, a
a = tier_b(0.02)
assert a["label"] == "converged" and "box" in a["qualifier"], a
big = R.label({"R": 9.0, "Rc": 9.0}, "B")
assert big[0] == "cannot tell" and R.label({"R": 9.0, "Rc": 9.0}, "A")[0] == "resolution-dependent"

# ---- redshift-x relations (sfrd) are evaluated at the snapshot redshifts inside the common range
zs = np.arange(0.025, 6.31, 0.05)
sf = {}
for n, dy in (("128", 0.0), ("256", 0.2), ("512", 0.2)):
    i = f"pillepich18.tng-l25n{n}.fiducial.sfrd"
    sf[i] = rec(i, f"L25n{n}", "sfrd", 2.0, zs, -1.0 + 0.0 * zs + dy, axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 sfrd", "yUnit": "log10(Msun yr^-1 cMpc^-3)"})
res, u = units_of(sf)
a = u[("128", "256", "sfrd")]
assert a["basis"] == "reference" and abs(a["R"] - 2.0) < 1e-9 and a["family"] == "rho" and a["parameters"] == "unchanged", a
assert a["epochs"][0]["reference"]["n_ref"] == 4          # z = 0.95, 2.15, 3 and 4 (z = 0 lies outside the curves)
assert u[("256", "512", "sfrd")]["R"] == 0.0 and u[("256", "512", "sfrd")]["label"] == "converged"
# P2 reads the distance at the fiducial parameters for 'unchanged' ladders and the retuned distance for the others
row = next(r for r in res["P2"]["rows"] if r["rungs"] == "128>256")
assert row["compared_with"] == "D_fiducial" and abs(row["ratio"] - 2.0 / 1.4) < 1e-9 and abs(row["ratio_D"] - 2.0 / 0.2) < 1e-9, row
res_c, uc = units_of(ladder([0.3, 0.3]))
rowc = next(r for r in res_c["P2"]["rows"] if r["relation"] == "gsmf" and r["rungs"] == "7>6")
assert rowc["compared_with"] == "D" and abs(rowc["ratio"] - 3.0 / 0.6) < 1e-9, rowc
assert res_c["P2"]["n_ratio_at_least_1"] == res_c["P2"]["n"] == 2 and res["P1"]["total"]["resolution-dependent"] == 1

# ---- the step ratio: a ladder whose second step is half the first
res, u = units_of(ladder([0.2, 0.1]))
st = [s for s in res["steps"] if s["ladder"] == "colibre-l025-gsmf"]
assert len(st) == 1 and abs(st[0]["ratio"] - 0.5) < 1e-9, st

# ---- the machinery is deterministic
r1 = R.to_plain(R.run(recs=ladder([0.2, 0.1]), ref=reference(), saved=SAVED, supp={}))
r2 = R.to_plain(R.run(recs=ladder([0.2, 0.1]), ref=reference(), saved=SAVED, supp={}))
assert json.dumps(r1, sort_keys=True) == json.dumps(r2, sort_keys=True)

# ---- the reference is the joint-reachability study's own noise scale (check C1)
ref, check, saved = R.build_reference()
assert all(v["match"] for v in check.values()), check
assert 0.05 < ref.y0 < 0.08 and ref.outputs[("gsmf", "090")] and ref.snapshot_for(1.0)[0] == "062"
assert ref.snapshot_for(2.0)[0] == "042" and ref.snapshot_for(0.1)[0] == "090" and ref.snapshot_for(10.0)[0] is None

# ---- the dataset: the ladders of the protocol exist with the counts it lists (structure only), and the saved output, if present, is not stale
recs = R.load_records()
built, refused = R.enumerate_pairs(recs)
cnt = {}
for p in built:
    if p["kind"] == "adjacent":
        cnt[p["ladder"]] = cnt.get(p["ladder"], 0) + 1
expected = {"tng-l25n": 2, "illustris-l25n": 2, "colibre-l025-gsmf": 18, "flamingo-l1": 22, "thesan": 6, "colibre-boxes": 7, "colibre-quenched": 12, "colibre-mzr": 12, "illustris-sparre15": 8, "tng-donnari21": 6, "tng-mzr": 6, "magneticum": 130}
for k, v in expected.items():
    assert cnt.get(k) == v, (k, cnt.get(k), v)
assert sum(v for k, v in cnt.items() if k.startswith("eagle")) == 24
saved_path = ROOT / "data" / "analysis" / "resolution.json"
if saved_path.exists():
    s = json.loads(saved_path.read_text())
    assert s["checks"]["C1"]["passed"] and s["checks"]["C2"]["passed"], s["checks"]
    for l in s["ladders"]:
        assert l["n_epoch_pairs_built"] == sum(1 for p in built if p["ladder"] == l["name"]), f"analysis output is stale for {l['name']}; rerun analyze_resolution.py"
    assert len(s["units"]) == len({(p["ladder"], p["kind"], p["rung_a"], p["rung_b"], p["tok_a"], p["tok_b"], p["relation"], p["stem"]) for p in built})
    assert all(u["label"] in ("converged", "resolution-dependent", "cannot tell") for u in s["units"] + s["supplementary"]["units"])
    assert all(u["tier"] == "A" or u["label"] != "resolution-dependent" for u in s["units"]), "a tier B unit can never be called resolution-dependent"
    assert s["P1"]["n_units"] == sum(1 for u in s["units"] if u["tier"] == "A" and u["kind"] == "adjacent")
print(f"resolution: OK (synthetic ladders, inclusion rule, labels, reference, {len(built)} epoch-pairs enumerated" + (", saved output consistent" if saved_path.exists() else ", no saved output yet") + ")")
