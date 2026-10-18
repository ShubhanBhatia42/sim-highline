"""Tests of the per-galaxy distribution machinery: the Python statistics equal the fixture that compare.js also reproduces; a mixture of two populations with a known green-valley share is recovered from binned counts; the CAMELS grid function handles zero SFR, out-of-range values and placeholder photometry."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import distribution_stats as D  # noqa: E402
import ingest_camels_distributions as I  # noqa: E402

ROOT = HERE.parent
fx = json.loads((ROOT / "tests" / "fixtures" / "distribution-fixture.json").read_text())
assert D.stats(fx["input"]) == fx["expected"], "Python statistics differ from the fixture"

# injection and recovery: 30% of galaxies in a red population (mean -12.2), 12% in the valley (uniform -11..-10.5), the rest blue (mean -10.1)
rng = np.random.default_rng(7)
n = 60000
u = rng.random(n)
y = np.where(u < 0.30, rng.normal(-12.2, 0.4, n), np.where(u < 0.42, rng.uniform(-11.0, -10.5, n), rng.normal(-10.1, 0.3, n)))
xe, ye = [9.0, 9.25], [round(-13.5 + 0.1 * k, 1) for k in range(51)]
counts = D.bin_counts(np.full(n, 9.1), y, xe, ye)
st = D.stats({"xEdges": xe, "yEdges": ye, "counts": counts.astype(int).tolist(), "thresholds": [-11.0, -10.5]})
true_red = float(np.mean(y < -11.0)); true_gv = float(np.mean((y >= -11.0) & (y < -10.5)))
assert abs(st["fracBelow"][0][0] - true_red) < 0.01, (st["fracBelow"][0][0], true_red)
assert abs(st["between"][0] - true_gv) < 0.01, (st["between"][0], true_gv)
assert abs(st["redPeak"][0] - (-12.2)) < 0.25 and abs(st["bluePeak"][0] - (-10.1)) < 0.25, (st["redPeak"], st["bluePeak"])
assert abs(st["quantiles"][2][0] - float(np.median(np.clip(y, -13.5, -8.5)))) < 0.06

# the CAMELS grid function on a synthetic catalogue
m = 5000
h = 0.6711
mstar = 10 ** rng.uniform(8.5, 11.8, m)  # Msun
mt = np.zeros((m, 6)); mt[:, 4] = mstar * h / 1e10
ln = np.zeros((m, 6), int); ln[:, 4] = np.where(mstar > 10 ** 8.8, 100, 0)
sfr = np.where(rng.random(m) < 0.3, 0.0, 10 ** rng.normal(-10.2, 0.4, m) * mstar)
ph = np.full((m, 8), np.inf)
g, c, nsel = I.grids({"SubhaloMassType": mt, "SubhaloLenType": ln, "SubhaloSFR": sfr, "SubhaloStellarPhotometrics": ph}, h)
sel = (ln[:, 4] > 0) & (mstar >= 10 ** 9.0) & (mstar < 10 ** 11.5)
assert nsel == int(sel.sum()) and g.shape == (len(I.X_EDGES) - 1, len(I.SSFR_EDGES) - 1) and int(g.sum()) == nsel
assert c is None, "placeholder (infinite) photometry must not produce colour counts"
assert int(g[:, 0].sum()) >= int(((sfr == 0) & sel).sum()), "zero-SFR galaxies belong in the lowest row"
ph2 = np.column_stack([np.zeros(m)] * 4 + [rng.normal(-20, 1, m), rng.normal(-20.5, 1, m), np.zeros(m), np.zeros(m)])
g2, c2, _ = I.grids({"SubhaloMassType": mt, "SubhaloLenType": ln, "SubhaloSFR": sfr, "SubhaloStellarPhotometrics": ph2}, h)
assert c2 is not None and int(c2.sum()) == nsel
print("distribution tests passed: fixture equal, injected green-valley share recovered to 1%, zero SFR and placeholder photometry handled")
