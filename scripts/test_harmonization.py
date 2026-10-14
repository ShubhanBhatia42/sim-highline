import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import numpy as np
except ImportError:
    print("harmonization test skipped: numpy not installed")
    raise SystemExit(0)
import analyze_harmonization as H

PHI = H.PHI


def schechter(x, xs=10.7, alpha=-1.2, logphi=-2.5):
    return logphi + np.log10(np.log(10)) + (alpha + 1) * (x - xs) - 10 ** (x - xs) / np.log(10)


def curve(xs=10.7, alpha=-1.2, logphi=-2.5, x0=7.5, x1=12.6, step=0.05):
    x = np.arange(x0, x1, step)
    return list(zip(x.tolist(), schechter(x, xs, alpha, logphi).tolist()))


def remap(pts, f, df):
    """The same population with every mass M replaced by M + f(M): a known aperture-like map, Jacobian included."""
    return [(x + f(x), y - np.log10(1 + df(x))) for x, y in pts]


# ---- the coordinate: m(phi) on a curve with an analytic answer
pts = curve()
m = H.mass_at(pts, PHI)
grid = np.arange(7.5, 12.6, 1e-4)
for phi, got in zip(PHI, m):
    above = grid[schechter(grid) >= phi]
    assert abs(got - above.max()) < 2e-3, (phi, got, above.max())
assert np.isnan(H.mass_at([(8.0, -1.0), (9.0, -1.5), (10.0, -2.0)], [-3.0])[0]), "a curve that never reaches the level is undefined"
assert np.isnan(H.mass_at([(8.0, -1.0), (9.5, -3.0)], [-2.0])[0]), "points further apart than MAX_GAP are not interpolated"

# ---- the library: galaxy-level remaps measured by rank-preserving matching recover a known map, Jacobian included
f = lambda x: 0.06 * (x - 10.0) + 0.02
pts = curve(x0=9.0)
rm = H.estimate_remap(pts, remap(pts, f, lambda x: 0.06))
g = np.linspace(rm.lo, rm.hi, 60)
assert np.max(np.abs(rm.f(g) - f(g))) < 2e-3 and np.max(np.abs(rm.df(g) - 0.06)) < 2e-3, "linear map recovered"
f2 = lambda x: 0.06 * np.tanh((x - 10.8) / 1.2)
df2 = lambda x: 0.06 / 1.2 / np.cosh((x - 10.8) / 1.2) ** 2
b2 = remap(pts, f2, df2)
rm2 = H.estimate_remap(pts, b2)
g = np.linspace(rm2.lo, rm2.hi, 60)
assert np.max(np.abs(rm2.f(g) - f2(g))) < 0.01, "a curved map is recovered to 0.01 dex (a cubic cannot follow a sharper bend: the limit is stated in the analysis)"
assert H.estimate_remap(curve(x0=9.0, x1=9.8), curve(x0=11.0, x1=12.0)) is None, "curves that share under 0.4 dex have no map"
# the map is a property of the aperture, not of the curve it was measured on: measured on suite X, it undoes the aperture of suite Y
Y = curve(xs=10.9, alpha=-1.1, x0=9.0)
lib = H.Library({"X": {"30": pts, "100": b2}})
back = lib.apply(remap(Y, f2, df2), "100", "30")
bx, by = np.array([p[0] for p in back]), np.array([p[1] for p in back])
assert len(back) > 30 and np.max(np.abs(by - np.interp(bx, [p[0] for p in Y], [p[1] for p in Y]))) < 0.03, "the map measured on X undoes the aperture on Y (mass and density)"
mb, my = H.mass_at(back, PHI), H.mass_at(Y, PHI)
assert np.isfinite(mb).sum() >= 8 and np.nanmax(np.abs(mb - my)) < 0.02, np.nanmax(np.abs(mb - my))
assert lib.apply(pts, "unknown", "30") is None and lib.apply(pts, "30", "30") is pts, "no map, no correction; identity is free"
assert H.Library({"X": {"30": pts, "100": b2}}).apply([(5.0, -1.0), (6.0, -2.0)], "100", "30") == [], "points outside every map are dropped"
# a differential, fixed-abundance shift is not transferable between curves with different slopes; the galaxy-level remap is: the contrast that motivated amendment A2
d_x = H.mass_at(remap(pts, f2, df2), PHI) - H.mass_at(pts, PHI)
d_y = H.mass_at(remap(Y, f2, df2), PHI) - H.mass_at(Y, PHI)
assert np.nanmax(np.abs(d_x - d_y)) > 0.02, "the same aperture shifts different curves by different amounts at fixed abundance"

# ---- composition through the reference class
three = {"X": {"30": pts, "50": remap(pts, lambda x: 0.04, lambda x: 0.0), "100": remap(pts, lambda x: 0.10, lambda x: 0.0)}}
l3 = H.Library(three)
comp = l3.apply(three["X"]["50"], "50", "100")
c100 = three["X"]["100"]
assert comp and np.max(np.abs(np.array([p[1] for p in comp]) - np.interp([p[0] for p in comp], [p[0] for p in c100], [p[1] for p in c100]))) < 5e-3, "50 -> 100 composed through 30 pkpc reproduces the 100 pkpc curve"

# ---- operators are exact where they are defined to be
assert abs(H.imf_shift("salpeter55") + 0.235) < 1e-12 and abs(H.imf_shift("kroupa01") + 0.025) < 1e-12 and H.imf_shift("chabrier03") == 0 and H.imf_shift("unspecified") == 0
assert abs(H.imf_shift("salpeter55", 0.05) - (-0.185)) < 1e-12 and H.imf_shift("chabrier03", 0.05) == 0
hz = H.Harmonizer(lib)
sal = hz.transform(Y, "salpeter55", None)
assert np.allclose([p[0] for p in sal], np.array([p[0] for p in Y]) - 0.235, atol=1e-12) and [p[1] for p in sal] == [p[1] for p in Y], "IMF moves masses and nothing else"
assert hz.transform(Y, "chabrier03", None) == Y and hz.transform(Y, "chabrier03", "unknown") == Y, "an unknown aperture is not corrected"
both = hz.transform(remap(Y, f2, df2), "chabrier03", "100")
assert len(both) == len(back) and np.allclose([p[0] for p in both], bx), "the aperture operator is lib.apply"
assert H.Harmonizer(lib, ("imf",)).transform(remap(Y, f2, df2), "salpeter55", "100")[0][0] == remap(Y, f2, df2)[0][0] - 0.235, "operators left out are not applied"

# ---- scatter: forward and inverse, recovery on a smooth curve to within the validation gate of the protocol; the stated scatter is read from the record text
smooth = curve(x0=8.0, x1=12.8, step=0.1)
for sigma in (0.1, 0.3):
    conv = H.convolve_scatter(smooth, sigma)
    back, lo = H.deconvolve_scatter(conv, sigma)
    m0, mc, mb = H.mass_at(smooth, PHI), H.mass_at(conv, PHI), np.where(H.mass_at(conv, PHI) >= lo, H.mass_at(back, PHI), np.nan)
    ok = np.isfinite(mb) & np.isfinite(m0) & np.isfinite(mc)
    assert ok.sum() >= 6 and np.max(np.abs(mb - m0)[ok]) < H.GATE_DEX and np.median((mc - m0)[ok]) > 0.01 * sigma / 0.1, (sigma, np.max(np.abs(mb - m0)[ok]))
assert H.scatter_sigma({"selection": {"warning": "The curves include the 0.3 dex random lognormal stellar-mass scatter expected in observed data"}}) == 0.3
assert H.scatter_sigma({"selection": {"warning": "no scatter here"}}) == 0.0 and H.scatter_sigma({}) == 0.0

# ---- variance and reduction
rng = np.random.default_rng(1)
base = np.array([m + s for s in rng.normal(0, 0.12, 14)])
assert abs(H.reduction(base, base)) < 1e-12, "a harmonization that changes nothing removes nothing"
shift = rng.normal(0, 0.3, (14, 1)) * np.ones((1, len(PHI)))
obs = base + shift
assert abs(H.reduction(obs, base) - (1 - H.level_variance(base).mean() / H.level_variance(obs).mean())) < 1e-12
assert H.reduction(obs, base) > 0.3, "undoing injected shifts removes variance"
short = obs.copy()
short[3:, :] = np.nan
assert np.isnan(H.level_variance(short)).all(), "fewer than four suites at a level means no variance there"
boot = H.bootstrap_reduction(obs, base, np.random.default_rng(2), 400)
assert np.percentile(boot, 2.5) > 0, "a real reduction is detected by the cluster bootstrap"


# ---- the null: with no definitional effect in the data, the permutation test rejects about 5 % of the time; with the maps injected it detects them
def dataset(r):
    return {f"S{i}": curve(xs=10.7 + r.normal(0, 0.04), alpha=-1.2 + r.normal(0, 0.02), logphi=-2.5 + r.normal(0, 0.04), x0=9.0) for i in range(12)}


class Fake:
    def __init__(self, name, pts, cls):
        self.name, self.pts, self.imf, self.cls, self.sigma = name, pts, "chabrier03", cls, 0.0
        self.native = H.m_of(pts)

    def label(self):
        return (self.imf, self.cls, self.sigma)


mk = lambda d: {"30": pts, "50": remap(pts, f, lambda x: 0.06), "100": remap(pts, lambda x: 0.12 * (x - 10.5), lambda x: 0.12), "total": remap(pts, lambda x: 0.1 * np.tanh(x - 10.5), lambda x: 0.1 / np.cosh(x - 10.5) ** 2)}
tlib = H.Library({"X": mk(0), "Y": mk(1)})
r0 = np.random.default_rng(3)
classes = ["30", "50", "100", "total"]
reject, detect = 0, 0
nsim = 60
for k in range(nsim):
    cs = dataset(r0)
    labels_cls = [classes[i] for i in r0.integers(0, 4, 12)]
    # no effect: the curves are what they are, the labels say they used some aperture
    res = H.estimand_e1([Fake(n, c, cl) for (n, c), cl in zip(cs.items(), labels_cls)], H.Harmonizer(tlib), np.random.default_rng(10 + k), nboot=150, nperm=150)
    reject += int(res["ci95"]["all"][0] > 0 and res["permutation"]["p_value"] < 0.05)
    # effect: the same curves seen through the labelled apertures (the forward map, Jacobian included); the harmonizer then undoes exactly that
    seen = []
    for (n, c), cl in zip(cs.items(), labels_cls):
        seen.append(Fake(n, c if cl == "30" else H.forward(c, tlib.remaps("30", cl)[0][1], 1.0), cl))
    r = H.estimand_e1(seen, H.Harmonizer(tlib), np.random.default_rng(500 + k), nboot=150, nperm=150)
    detect += int(r["ci95"]["all"][0] > 0 and r["permutation"]["p_value"] < 0.05)
assert reject / nsim <= 0.15, f"false positive rate too high: {reject}/{nsim}"
assert detect / nsim >= 0.6, f"injected effects are not detected: {detect}/{nsim}"

# ---- E4 reports what it was told: no effect at lambda 0, a recoverable one at lambda 1 (a small run on the synthetic library)
e4 = H.estimand_e4([Fake(n, c, "30") for n, c in dataset(np.random.default_rng(4)).items()], tlib.curves, np.random.default_rng(5), lambdas=(0.0, 1.0), ndraw=12, nboot=40)
assert e4[0]["detection_rate"] <= 0.25 and e4[1]["R_true_mean"] > 0.05 and abs(e4[1]["R_recovered_mean"] - e4[1]["R_true_mean"]) < 0.35 * e4[1]["R_true_mean"] + 0.05, e4

# ---- E3 on synthetic maps: a universal map is recognised, a suite with a different map is not
same = {sn: {"30": pts, "total": remap(pts, lambda x: -0.08 * (x - 10.0), lambda x: -0.08)} for sn in "ABC"}
t = next(r for r in H.estimand_e3(H.Library(same)) if r["pair"] == "total -> 30")
assert t["universal"] and all(fo["skill"] > 0 for fo in t["folds"]), t
odd = dict(same)
odd["C"] = {"30": pts, "total": remap(pts, lambda x: 0.0, lambda x: 0.0)}
t = next(r for r in H.estimand_e3(H.Library(odd)) if r["pair"] == "total -> 30")
assert not t["universal"], t
assert all(not r.get("leave_one_out_with_three_or_more") or r["n_suites"] >= 3 for r in H.estimand_e3(H.Library(same))), "universality is claimed only with three or more suites"

# ---- the website's fiducial rule, ported: identical to the JavaScript on the real records
recs = H.adb.load()
sims = [r for r in recs if r["kind"] == "simulation" and r["relation"] == "gsmf" and not H.ID_SUBLIBRARY.search(r["id"])]
mine = sorted(H.primary_units(sims))
if shutil.which("node"):
    payload = json.dumps([{"source": r["source"], "run": r.get("run"), "epoch": {"zRepresentative": r["epoch"]["zRepresentative"]}, "provenance": {"tier": r["provenance"].get("tier")}} for r in sims])
    theirs = json.loads(subprocess.run(["node", str(ROOT / "scripts" / "fiducial-oracle.mjs")], input=payload, capture_output=True, text=True, check=True).stdout)
    assert mine == theirs, (set(mine) ^ set(theirs))
    parity = "identical to the website's"
else:
    parity = "not compared with the website's (node not installed)"

# ---- the real inputs: the library is what the protocol says, selection is deterministic, the gate passes
byid = {r["id"]: r for r in recs}
for s, cs in H.LIBRARY.items():
    for cls, rid in cs.items():
        assert rid in byid and H.CLASS_OF[byid[rid]["definitions"]["massDefinition"]] == cls and byid[rid]["definitions"]["population"] == "all", (s, cls, rid)
a, _ = H.choose_suites(recs)
b, _ = H.choose_suites(recs)
assert {k: v["id"] for k, v in a.items()} == {k: v["id"] for k, v in b.items()} and len(a) >= 6
assert not any(H.ID_SUBLIBRARY.search(v["id"]) for v in a.values())
assert H.validate_scatter()["passed"]
assert {k for k, v in a.items() if H.scatter_sigma(v) > 0} == {"FLAMINGO"}

# ---- the saved analysis is not stale: its headline number is recomputed from the records
saved = json.loads((ROOT / "data" / "analysis" / "harmonization.json").read_text())
curves = H.library_curves(recs)
suites = [H.Suite(n, r) for n, r in sorted(a.items())]
assert [s["record"] for s in saved["suites"]] == [s.rec["id"] for s in suites], "analysis output is stale; rerun analyze_harmonization.py"
fresh = H.r_point(H.Harmonizer(H.Library(curves), tuple(saved["operators_used"])), suites)
assert abs(fresh - saved["E1"]["R"]["all"]) < 1e-3, ("analysis output is stale; rerun analyze_harmonization.py", fresh, saved["E1"]["R"]["all"])
assert saved["version"] == json.loads((ROOT / "data" / "release.json").read_text())["version"]
assert "do not edit by hand" in (ROOT / "docs" / "ANALYSIS-harmonization.md").read_text()
print(f"harmonization: OK (fiducial rule {parity}; false positives {reject}/{nsim}, detections {detect}/{nsim} on synthetic data)")
