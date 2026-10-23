"""Tests of the reduction of scripts/ingest_camels_distshape.py on a synthetic subhalo catalogue with known answers: bins, thresholds, zero star formation, percentile width, minimum counts."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import numpy as np
except ImportError:
    print("camels distshape test skipped: numpy not installed")
    raise SystemExit(0)
import ingest_camels_distshape as D

h = 0.6711
rng = np.random.default_rng(11)
n = 3000
lm = rng.uniform(9.0, 11.5, n)
ms = 10 ** lm * h / 1e10
# a known mixture, independent of mass: 40 % quenched (SFR = 0 exactly), 20 % in the green valley (log sSFR uniform in [-11, -10.5)), 10 % just below it (log sSFR in [-11.5, -11)), 30 % star forming (log sSFR uniform in [-10.4, -9.4))
kind = rng.choice(4, n, p=[0.4, 0.2, 0.1, 0.3])
ls = np.where(kind == 1, rng.uniform(-11.0, -10.5, n), np.where(kind == 2, rng.uniform(-11.5, -11.0, n), rng.uniform(-10.4, -9.4, n)))
sfr = np.where(kind == 0, 0.0, 10 ** (ls + lm))   # SFR in Msun/yr: the catalogue gives SFR directly, M* in the units above
a = {"SubhaloMassType": np.zeros((n, 6)), "SubhaloLenType": np.tile([0, 0, 0, 0, 100, 0], (n, 1)), "SubhaloSFR": sfr}
a["SubhaloMassType"][:, 4] = ms
v = D.shape_summaries(a, h)
assert set(v) == set(D.FAMILIES + D.COUNTS) and all(len(x) == len(D.MSTAR_EDGES) - 1 for x in v.values())
for k, (lo, hi) in enumerate(zip(D.MSTAR_EDGES[:-1], D.MSTAR_EDGES[1:])):
    s = (lm >= lo) & (lm < hi)
    assert v["ngal"][k] == int(s.sum())
    exp_gv = np.mean(kind[s] == 1)
    exp_wide = np.mean((kind[s] == 1) | (kind[s] == 2))
    assert abs(v["gv"][k] - exp_gv) < 1e-4 and abs(v["gvwide"][k] - exp_wide) < 1e-4, (k, v["gv"][k], exp_gv)
    sf = s & (kind == 3)
    assert v["nsf"][k] == int(sf.sum())
    # star-forming width: 16th to 84th percentile of a uniform spread of 1.0 dex is 0.68 dex (sampling error allowed)
    assert abs(v["sfw"][k] - 0.68) < 0.12, (k, v["sfw"][k])
# zero SFR is never in the green valley and never in the width; the overall fractions are the mixture's
assert abs(np.nanmean([x for x in v["gv"] if x is not None]) - 0.2) < 0.03
# fewer than the minimum count gives a missing value, not zero; exactly the minimum gives a value
sel = np.where((lm >= 10.0) & (lm < 10.25))[0]
keep = np.concatenate([np.where(~((lm >= 10.0) & (lm < 10.25)))[0], sel[:D.MIN_N - 1]])
c = {k: x[keep] for k, x in a.items()}
vc = D.shape_summaries(c, h)
assert vc["gv"][4] is None and vc["sfw"][4] is None and vc["ngal"][4] == D.MIN_N - 1
keep2 = np.concatenate([np.where(~((lm >= 10.0) & (lm < 10.25)))[0], sel[:D.MIN_N]])
vd = D.shape_summaries({k: x[keep2] for k, x in a.items()}, h)
assert vd["gv"][4] is not None and vd["ngal"][4] == D.MIN_N
# a galaxy without star particles is not a galaxy; thresholds are half-open: just above -11.0 is in the green valley, just above -10.5 is not (it is star forming), just below -11.0 is only in the wide window
N = 60
e = {"SubhaloMassType": np.zeros((N, 6)), "SubhaloLenType": np.tile([0, 0, 0, 0, 100, 0], (N, 1)), "SubhaloSFR": np.zeros(N)}
e["SubhaloMassType"][:, 4] = 10 ** 10.1 * h / 1e10
e["SubhaloSFR"][:10] = 10 ** (10.1 - 11.0 + 1e-6)
e["SubhaloSFR"][10:20] = 10 ** (10.1 - 10.5 + 1e-6)
e["SubhaloSFR"][20:30] = 10 ** (10.1 - 11.0 - 1e-6)
e["SubhaloLenType"][30:40, 4] = 0
ve = D.shape_summaries(e, h)
k = 4
assert ve["ngal"][k] == 50, ve["ngal"]
assert abs(ve["gv"][k] - 10 / 50) < 1e-3, ve["gv"][k]
assert abs(ve["gvwide"][k] - 20 / 50) < 1e-3
assert ve["nsf"][k] == 10 and ve["sfw"][k] == 0.0   # only the ten just above -10.5 enter the width, all at one value
print("camels distshape test ok")
