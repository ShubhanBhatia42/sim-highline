"""Tests of the catalogue reduction of scripts/ingest_camels_galaxies.py on a synthetic subhalo catalogue with known answers: units, bins, medians, fractions, centrals, thresholds."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import numpy as np
except ImportError:
    print("camels galaxies test skipped: numpy not installed")
    raise SystemExit(0)
import ingest_camels_galaxies as G

h, box, z = 0.6711, 25000.0, 0.0
vol = (box / 1000 / h) ** 3
# 400 subhaloes: stellar masses (1e10 Msun/h) log-uniform over 10^9.1 to 10^11.4 Msun; every fifth is a satellite (not the first subhalo of its group)
rng = np.random.default_rng(3)
n = 400
lm = rng.uniform(9.1, 11.4, n)
ms = 10 ** lm * h / 1e10
mt = np.zeros((n, 6))
mt[:, 4] = ms
mt[:, 0] = ms * 2.0  # gas twice the stars (within the whole subhalo)
mr = np.zeros((n, 6))
mr[:, 4] = ms * 0.8
mr[:, 0] = ms * 0.8  # inside twice the half-mass radius: gas fraction 0.5
sfr = np.where(np.arange(n) % 4 == 0, 0.0, 10 ** (lm - 10.0 + 0.0))  # a quarter quenched (SFR 0), the rest at specific SFR 1e-10 per yr
bh = np.where(lm > 10.0, 10 ** (lm - 3.0) * h / 1e10, 0.0)
group = np.arange(n) // 2  # two subhaloes per group
first = np.arange(n // 2) * 2
m200 = np.repeat(10 ** (lm[first] + 2.0) * h / 1e10, 2)[:n]
a = {"SubhaloMassType": mt, "SubhaloMassInRadType": mr, "SubhaloHalfmassRadType": np.tile([0, 0, 0, 0, 2.0, 0], (n, 1)), "SubhaloSFR": sfr, "SubhaloBHMass": bh,
     "SubhaloGasMetallicitySfrWeighted": np.full(n, 0.0127 * 0.5), "SubhaloStarMetallicity": np.full(n, 0.0127 * 2.0), "SubhaloGrNr": group, "SubhaloLenType": np.tile([0, 0, 0, 0, 100, 0], (n, 1)),
     "GroupFirstSub": first, "Group_M_Crit200": 10 ** (lm[first] + 2.0) * h / 1e10}
v = G.summarize(a, z, h, box)
assert set(v) == set(G.FAMILIES) and all(len(v[k]) == G.FAMILY_BINS[k] for k in v)
# stellar mass function: counts per bin per volume per dex
for k, (lo, hi) in enumerate(zip(G.MSTAR_EDGES[:-1], G.MSTAR_EDGES[1:])):
    cnt = int(((lm >= lo) & (lm < hi)).sum())
    assert abs(v["gsmf"][k] - np.log10(cnt / vol / 0.25)) < 1e-3, (k, cnt, v["gsmf"][k])
# quenched fraction: SFR = 0 is quenched, specific SFR 1e-10 is not (exact per bin)
for k, (lo, hi) in enumerate(zip(G.MSTAR_EDGES[:-1], G.MSTAR_EDGES[1:])):
    sel = (lm >= lo) & (lm < hi)
    assert (v["qf"][k] is None) == (sel.sum() < 5) and (sel.sum() < 5 or abs(v["qf"][k] - np.mean(sfr[sel] == 0)) < 1e-3), (k, v["qf"][k])
# specific SFR of star-forming galaxies is 1e-10 per yr, black holes appear above 1e10, metallicities, sizes (physical kpc: 2.0 ckpc/h at z = 0 over h), gas fraction 0.5
assert all(abs(x + 10.0) < 1e-3 for x in v["sfms"] if x is not None)
assert v["bhocc"][0] == 0.0 and v["bhocc"][-1] == 1.0 and v["bhms"][0] is None and abs(v["bhms"][-1] - (11.4 - 3.0)) < 0.35
assert all(abs(x - np.log10(0.5)) < 1e-3 for x in v["mzr"] if x is not None) and all(abs(x - np.log10(2.0)) < 1e-3 for x in v["zstar"] if x is not None)
assert all(abs(x - np.log10(2.0 / h)) < 1e-3 for x in v["size"] if x is not None)
assert all(abs(x - 0.5) < 1e-6 for x in v["fgas"] if x is not None)
# centrals: M200 is 100 times M*, so the median ratio is -2; the halo mass function counts centrals only
assert all(abs(x + 2.0) < 1e-2 for x in v["shmr"] if x is not None) and sum(1 for x in v["shmr"] if x is not None) >= 5
cen_m200 = np.log10(10 ** (lm[first] + 2.0))
for k, (lo, hi) in enumerate(zip(G.M200_EDGES_HMF[:-1], G.M200_EDGES_HMF[1:])):
    cnt = int(((cen_m200 >= lo) & (cen_m200 < hi)).sum())
    assert (v["hmf"][k] is None) == (cnt == 0) and (cnt == 0 or abs(v["hmf"][k] - np.log10(cnt / vol / 0.5)) < 1e-3), (k, cnt, v["hmf"][k])
# densities: stellar mass and star formation per comoving volume
assert abs(v["rho"][0] - np.log10((10 ** lm).sum() / vol)) < 1e-3 and abs(v["rho"][1] - np.log10(sfr.sum() / vol)) < 1e-3
# a bin with fewer than 5 galaxies gives no median; no star particles means no galaxy
a2 = dict(a)
a2["SubhaloLenType"] = np.zeros((n, 6), dtype=int)
v2 = G.summarize(a2, z, h, box)
assert all(x is None for x in v2["gsmf"]) and all(x is None for x in v2["sfms"])
# redshift: sizes are physical (scale factor 0.5 at z = 1)
v3 = G.summarize(a, 1.0, h, box)
assert all(abs(x - np.log10(0.5 * 2.0 / h)) < 1e-3 for x in v3["size"] if x is not None)
print("camels galaxies: OK")
