"""Statistics of a per-galaxy distribution given as counts on a grid: quantiles, fraction below thresholds, the fraction between the two thresholds (for sSFR: the green valley) and the two peak positions.
Mirrors distributionStats in compare.js step for step (tests/fixtures/distribution-fixture.json is evaluated by both and compared by scripts/test-distributions.mjs and scripts/test_distributions.py).
Also the helper the catalogue adapters use to turn per-galaxy arrays into counts. Usage: imported by ingest_camels_distributions.py, derive-distributions.mjs's tests and the adapters."""
import math

import numpy as np

LEVELS = (0.05, 0.16, 0.5, 0.84, 0.95)
MIN_COUNT = 10


def _r6(v):
    return None if v is None else round(float(v) * 1e6) / 1e6


def quantile(row, edges, total, q):
    target = q * total
    cum = 0.0
    for j, c in enumerate(row):
        if c > 0 and cum + c >= target:
            t = (target - cum) / c
            return edges[j] + min(1.0, max(0.0, t)) * (edges[j + 1] - edges[j])
        cum += c
    return edges[-1]


def fraction_below(row, edges, total, thr):
    cum = 0.0
    for j, c in enumerate(row):
        if edges[j + 1] <= thr:
            cum += c
            continue
        if edges[j] < thr:
            cum += c * (thr - edges[j]) / (edges[j + 1] - edges[j])
        break
    return cum / total


def stats(d, levels=LEVELS, min_count=MIN_COUNT):
    """d: {xEdges, yEdges, counts[i][j], thresholds?}; returns the same structure as compare.js distributionStats."""
    thr = sorted(d.get("thresholds") or [])
    nx = len(d["xEdges"]) - 1
    out = {"levels": list(levels), "minCount": min_count, "thresholds": thr, "n": [], "quantiles": [[] for _ in levels], "fracBelow": [[] for _ in thr], "between": [], "bluePeak": [], "redPeak": []}
    ye = d["yEdges"]
    for i in range(nx):
        row = d["counts"][i]
        tot = float(sum(row))
        out["n"].append(int(tot) if float(tot).is_integer() else tot)
        if tot < min_count:
            for k in range(len(levels)):
                out["quantiles"][k].append(None)
            for k in range(len(thr)):
                out["fracBelow"][k].append(None)
            out["between"].append(None); out["bluePeak"].append(None); out["redPeak"].append(None)
            continue
        for k, q in enumerate(levels):
            out["quantiles"][k].append(_r6(quantile(row, ye, tot, q)))
        fb = [fraction_below(row, ye, tot, t) for t in thr]
        for k, v in enumerate(fb):
            out["fracBelow"][k].append(_r6(v))
        out["between"].append(_r6(fb[-1] - fb[0]) if len(thr) >= 2 else None)

        def peak(lo, hi):
            best, bj = -1.0, -1
            for j, c in enumerate(row):
                if ye[j] >= lo and ye[j + 1] <= hi and c > best:
                    best, bj = c, j
            return None if bj < 0 or best <= 0 else _r6((ye[bj] + ye[bj + 1]) / 2)

        out["bluePeak"].append(peak(thr[-1], math.inf) if len(thr) >= 2 else None)
        out["redPeak"].append(peak(-math.inf, thr[0]) if len(thr) >= 2 else None)
    out["xCentres"] = [_r6((d["xEdges"][i] + d["xEdges"][i + 1]) / 2) for i in range(nx)]
    return out


def bin_counts(x, y, x_edges, y_edges, weights=None):
    """Counts of (x, y) pairs on the grid; values outside the y range are put in the first or last y bin (the record states this), values outside the x range are dropped."""
    x = np.asarray(x, float)
    y = np.clip(np.asarray(y, float), y_edges[0] + 1e-9, y_edges[-1] - 1e-9)
    ok = np.isfinite(x) & np.isfinite(y)
    h, _, _ = np.histogram2d(x[ok], y[ok], bins=[x_edges, y_edges], weights=None if weights is None else np.asarray(weights, float)[ok])
    return h
