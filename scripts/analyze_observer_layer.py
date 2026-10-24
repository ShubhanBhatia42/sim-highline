"""What does Gaussian scatter in stellar mass do to the offsets between simulated and observed galaxy stellar mass functions already in the dataset?
For every pair of a simulation curve and an observed curve of relation gsmf that the comparison rules (compare.js, via data/export/sim-highline-rules.json) call comparable, at similar redshift, this
reports the median offset (dex in log10 number density, simulation minus observation, the number the Explorer shows) before and after applying sigma = 0.1, 0.2 and 0.3 dex of scatter to the simulation
(sim_highline.scatter_points), and how many pairs change from an offset larger than the observational uncertainty to a smaller one. It shows how much of an offset a given scatter COULD absorb; it does not show that
the scatter exists in any survey. Writes data/analysis/observer-layer.json and docs/OBSERVER-LAYER.md (the wording is in this file, the numbers come from the data).
Usage: python3 scripts/analyze_observer_layer.py [--check]   (--check recomputes and fails if either saved file differs; no file is written)"""
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sim_highline as sh  # noqa: E402

OUT_JSON = ROOT / "data" / "analysis" / "observer-layer.json"
OUT_DOC = ROOT / "docs" / "OBSERVER-LAYER.md"
SIGMAS = (0.1, 0.2, 0.3)
RELATION = "gsmf"
NDIG = 4
TOL_Z = lambda z: max(0.15, 0.1 * (1 + z))      # the epoch tolerance the Explorer and sim_highline.nearest_epoch use
POP = {"all": "all", "all galaxies": "all"}


def r(v, n=NDIG):
    return None if v is None or (isinstance(v, float) and not math.isfinite(v)) else round(float(v), n)


def load_records():
    df = sh.load(ROOT / "data" / "export")
    rules = sh.rules(ROOT / "data" / "export")
    sel = df[df["relation"] == RELATION]
    recs = {}
    for rid, g in sel.groupby("record_id", sort=True):
        g = g.sort_values("point_index")
        f = g.iloc[0]
        ok = np.isfinite(g["x"].to_numpy(float)) & np.isfinite(g["y"].to_numpy(float))
        g = g[ok]
        if len(g) < 2:
            continue
        xs = g["x"].to_numpy(float)
        order = np.argsort(xs, kind="stable")
        arr = {k: g[c].to_numpy(float)[order] for k, c in (("x", "x"), ("y", "y"), ("lo", "y_low"), ("hi", "y_high"))}
        defs = json.loads(f["definitions_json"])
        recs[rid] = {"id": rid, "relation": RELATION, "kind": f["kind"], "source": f["source"], "run": None if f["run"] != f["run"] else f["run"], "tier": f["tier"], "rankable": bool(f["rankable"]),
                     "selection": {}, "definitions": defs,
                     "epoch": {"zRepresentative": float(f["z"]), "zMin": float(f["z_min"]), "zMax": float(f["z_max"]), "mode": None if f.get("epoch_mode") != f.get("epoch_mode") else f.get("epoch_mode")},
                     "uncertainty": f["interval_kind"] == "uncertainty", "arr": arr}
    return recs, rules, df.attrs.get("version")


def points_of(arr):
    pts = []
    for x, y, lo, hi in zip(arr["x"], arr["y"], arr["lo"], arr["hi"]):
        p = {"x": float(x), "y": float(y)}
        if math.isfinite(lo):
            p["yLow"] = float(lo)
        if math.isfinite(hi):
            p["yHigh"] = float(hi)
        pts.append(p)
    return pts


def arrays_of(pts):
    return {"x": np.array([p["x"] for p in pts]), "y": np.array([p["y"] for p in pts]), "lo": np.array([p.get("yLow", np.nan) for p in pts]), "hi": np.array([p.get("yHigh", np.nan) for p in pts])}


def epoch_gap(a, b):
    ea, eb = a["epoch"], b["epoch"]
    return max(0.0, max(ea["zMin"], eb["zMin"]) - min(ea["zMax"], eb["zMax"]))


def offset(sim_arr, sim_kind, obs, min_bins):
    """Median of (simulation - observation) in log10 density over the bins the website compares, and the median observational 1-sigma at those bins."""
    res = sh.residuals(sim_arr, obs["arr"], sim_kind, "uncertainty" if obs["uncertainty"] else "unspecified")
    s = sh.summarize(res, min_bins)
    if s is None:
        return None
    sr = sh._sigma(obs["arr"]["y"], obs["arr"]["lo"], obs["arr"]["hi"], "uncertainty" if obs["uncertainty"] else "unspecified")
    sig = [sh._interp(obs["arr"]["x"], sr, row[0]) for row in res]
    sig = [v for v in sig if math.isfinite(v)]
    return {"median": s["median"], "n": s["n"], "obsSigma": float(np.median(sig)) if len(sig) == s["n"] else None}


def classify(bef, aft, sig):
    """'larger to smaller' and the other three combinations of 'offset larger than the observational uncertainty' before and after; None when the observed curve has no uncertainty."""
    if sig is None:
        return None
    big_b, big_a = abs(bef) > sig, abs(aft) > sig
    return "largerToSmaller" if big_b and not big_a else "smallerToLarger" if not big_b and big_a else "stayLarger" if big_b else "staySmaller"


def compute():
    recs, rules, version = load_records()
    min_bins = rules["minBins"]
    sims = [x for x in recs.values() if x["kind"] == "simulation"]
    obss = [x for x in recs.values() if x["kind"] == "observation"]
    counts = Counter()
    counts["simulationRecords"], counts["observationRecords"] = len(sims), len(obss)
    counts["pairsTotal"] = len(sims) * len(obss)
    caveat_keys = Counter()
    h0dex = []
    # scattered curves, once per simulation and sigma
    scat, skipped = {}, {}
    for s in sims:
        pts = points_of(s["arr"])
        for sg in SIGMAS:
            try:
                scat[(s["id"], sg)] = sh.scatter_points(pts, sg)
            except ValueError as e:
                skipped[s["id"]] = str(e)
    pairs = []
    for s in sims:
        for o in obss:
            v = sh.compatible(s, o, rules)
            if v["verdict"] == "not-comparable":
                counts["notComparable"] += 1
                continue
            if epoch_gap(s, o) > TOL_Z(s["epoch"]["zRepresentative"]):
                counts["comparableButEpochsFarApart"] += 1
                continue
            ps, po = POP.get(s["definitions"].get("population"), s["definitions"].get("population")), POP.get(o["definitions"].get("population"), o["definitions"].get("population"))
            if ps and po and ps != po and ps not in ("unspecified",) and po not in ("unspecified",):
                counts["populationMismatch"] += 1
                continue
            counts["comparablePairs"] += 1
            hs, ho = (s["definitions"].get("cosmology") or {}).get("H0"), (o["definitions"].get("cosmology") or {}).get("H0")
            if hs and ho:
                h0dex.append(abs(3 * math.log10(hs / ho)))
            if s["id"] in skipped:
                counts["simulationCurveHasGapOver1dex"] += 1
                continue
            sim_kind = "uncertainty" if s["uncertainty"] else "unspecified"
            b = offset(s["arr"], sim_kind, o, min_bins)
            if b is None:
                counts["fewerThanMinBins"] += 1
                continue
            row = {"sim": s["id"], "obs": o["id"], "source": s["source"], "verdict": v["verdict"], "nBins": b["n"], "obsSigma": r(b["obsSigma"]), "before": r(b["median"]), "after": {}, "interior": {}}
            for c in v["caveats"]:
                caveat_keys[c.split(":")[0].split(" ")[0]] += 1
            for sg in SIGMAS:
                sp = scat[(s["id"], sg)]
                a = offset(arrays_of(sp), sim_kind, o, min_bins)
                row["after"][str(sg)] = r(a["median"]) if a else None
                keep = [p for p, q in zip(points_of(s["arr"]), sp) if not q["edge"]]
                ks = [q for q in sp if not q["edge"]]
                if len(keep) >= 2:
                    bi, ai = offset(arrays_of(keep), sim_kind, o, min_bins), offset(arrays_of(ks), sim_kind, o, min_bins)
                    row["interior"][str(sg)] = {"before": r(bi["median"]), "after": r(ai["median"]), "obsSigma": r(bi["obsSigma"]), "nBins": bi["n"]} if bi and ai else None
                else:
                    row["interior"][str(sg)] = None
            pairs.append(row)
    pairs.sort(key=lambda p: (p["sim"], p["obs"]))
    used_sims = sorted({p["sim"] for p in pairs})
    change = {}
    for sg in SIGMAS:
        dy = [q["y"] - p0["y"] for sid in used_sims for p0, q in zip(points_of(recs[sid]["arr"]), scat[(sid, sg)]) if not q["edge"]]
        change[str(sg)] = {"points": len(dy), "p5": r(float(np.percentile(dy, 5))), "median": r(float(np.median(dy))), "p95": r(float(np.percentile(dy, 95)))}
    counts["pairsMeasured"] = len(pairs)
    unconverted = {"h0InDensityDexMedian": r(np.median(h0dex)) if h0dex else None, "h0InDensityDexMax": r(max(h0dex)) if h0dex else None, "note": "|3 log10(H0_sim / H0_obs)|, the size of the Hubble-constant difference in number density that the comparison rules report and nobody converts here (over the comparable pairs before the bin-count filter)"}

    def block(rows, get):
        """Statistics of one variant over the rows that have a number for it."""
        out = {}
        used = [p for p in rows if get(p, None) is not None]
        out["pairs"] = len(used)
        out["medianOffsetBefore"] = r(np.median([get(p, None)[0] for p in used])) if used else None
        out["medianAbsOffsetBefore"] = r(np.median([abs(get(p, None)[0]) for p in used])) if used else None
        out["bySigma"] = {}
        for sg in SIGMAS:
            g = [(p, get(p, sg)) for p in used if get(p, sg) is not None]
            t = Counter()
            absb = [abs(x[0]) for _, x in g]
            absa = [abs(x[1]) for _, x in g]
            for _, (bef, aft, sig) in g:
                t["absOffsetSmaller" if abs(aft) < abs(bef) - 1e-9 else "absOffsetLarger" if abs(aft) > abs(bef) + 1e-9 else "absOffsetUnchanged"] += 1
                k = classify(bef, aft, sig)
                if k is None:
                    t["noObservationalUncertainty"] += 1
                    continue
                t[k] += 1
            out["bySigma"][str(sg)] = {"pairs": len(g), "medianOffsetAfter": r(np.median([x[1] for _, x in g])) if g else None, "medianAbsOffsetAfter": r(np.median(absa)) if g else None, "medianAbsOffsetBeforeSamePairs": r(np.median(absb)) if g else None, "medianOffsetBeforeSamePairsSigned": r(np.median([x[0] for _, x in g])) if g else None,
                                       "medianChange": r(np.median([x[1] - x[0] for _, x in g])) if g else None, **{k: t.get(k, 0) for k in ("largerToSmaller", "smallerToLarger", "stayLarger", "staySmaller", "noObservationalUncertainty", "absOffsetSmaller", "absOffsetLarger", "absOffsetUnchanged")},
                                       "largerBefore": t["largerToSmaller"] + t["stayLarger"], "largerAfter": t["smallerToLarger"] + t["stayLarger"]}
        return out

    main_get = lambda p, sg: (p["before"], p["before"], p["obsSigma"]) if sg is None else (None if p["after"][str(sg)] is None else (p["before"], p["after"][str(sg)], p["obsSigma"]))
    int_get = lambda p, sg: (lambda i: None if i is None else (i["before"], i["before"], i["obsSigma"]))(p["interior"][str(SIGMAS[0])]) if sg is None else (lambda i: None if i is None else (i["before"], i["after"], i["obsSigma"]))(p["interior"][str(sg)])
    result = {"main": block(pairs, main_get), "interiorOnly": block(pairs, int_get)}
    # smallest tested sigma at which the offset is inside the observational uncertainty
    first = Counter()
    for p in pairs:
        if p["obsSigma"] is None:
            continue
        if abs(p["before"]) <= p["obsSigma"]:
            first["alreadyInside"] += 1
            continue
        hit = next((sg for sg in SIGMAS if p["after"][str(sg)] is not None and abs(p["after"][str(sg)]) <= p["obsSigma"]), None)
        first[str(hit) if hit else "none"] += 1
    result["smallestSigmaThatBringsOffsetInside"] = {k: first.get(k, 0) for k in ("alreadyInside", *map(str, SIGMAS), "none")}
    by_src = {}
    for src in sorted({p["source"] for p in pairs}):
        rows = [p for p in pairs if p["source"] == src]
        by_src[src] = {"pairs": len(rows), "simulationRecords": len({p["sim"] for p in rows}), "medianOffsetBefore": r(np.median([p["before"] for p in rows])),
                       **{f"medianOffsetAfter{sg}": r(np.median([p["after"][str(sg)] for p in rows if p["after"][str(sg)] is not None])) for sg in SIGMAS},
                       **{f"{k}{sg}": sum(1 for p in rows if p["after"][str(sg)] is not None and classify(p["before"], p["after"][str(sg)], p["obsSigma"]) == k) for sg in SIGMAS for k in ("largerToSmaller", "smallerToLarger")}}
    result["bySource"] = by_src
    ids = sorted({i for p in pairs for i in (p["sim"], p["obs"])})
    digest = hashlib.sha256(json.dumps([[i, recs[i]["epoch"], recs[i]["definitions"], recs[i]["rankable"], {k: [None if not math.isfinite(v) else round(float(v), 6) for v in a] for k, a in recs[i]["arr"].items()}] for i in sorted(recs)], sort_keys=True).encode()).hexdigest()
    counts["distinctSimulationRecordsInPairs"] = len({p["sim"] for p in pairs})
    counts["distinctObservationRecordsInPairs"] = len({p["obs"] for p in pairs})
    return {"note": "Written by scripts/analyze_observer_layer.py. Offsets are simulation minus observation in log10 number density per dex, the number the Explorer shows. This shows how much of an offset a given scatter could absorb; it does not show that the scatter exists in any survey.",
            "datasetVersion": version, "inputSha256": digest,
            "settings": {"relation": RELATION, "sigmasDex": list(SIGMAS), "pairRule": "sim_highline.compatible (the rules of compare.js) is not 'not-comparable', both records rankable; epochs: gap between the two redshift ranges at most max(0.15, 0.1 (1 + z_sim)); populations equal when both are stated",
                         "minimumSharedBins": min_bins, "classification": "an offset is 'larger' when |median offset| > the median observational 1-sigma (yHigh-y or y-yLow, the larger) over the bins compared; pairs whose observed curve has no uncertainty are not classified",
                         "scatterOptions": sh.OBSERVER_DEFAULTS, "scatterAppliedTo": "the simulation curve only; the observed curve is untouched", "interiorOnly": "the same, after removing the bins where more than edgeFlag of the scattered density comes from the continuation beyond the curve (before and after on the same bins)"},
            "counts": dict(counts), "caveatKinds": dict(sorted(caveat_keys.items())), "unconvertedDifferences": unconverted, "changeInLog10DensityFromScatter": {"note": "scattered minus input, at the points of the simulation curves in the measured pairs, bins flagged edge left out; percentiles, because a few far-tail points of fitted curves (density 1e-20 or less) change by tens of dex and mean nothing", **change}, "results": result, "skippedSimulations": skipped, "pairs": pairs}


# ------------------------------------------------------------------------------------------------------------------------------------------------------------------
TEMPLATE = """# Observer layer: scatter, offsets, completeness and detection floors

*Wording written by hand; every number in the measurement part is written by `scripts/analyze_observer_layer.py` from `data/analysis/observer-layer.json`. Internal checks only: no outside expert has reviewed this.*

## What this is, and what it is not

A simulation catalogue holds true masses and true rates. A survey reports measured ones. The project already converts differences it can document on the simulation side (IMF, aperture, cosmology). This page covers a small
set of operations for the observer side, so a reader can ask "how much of this offset could a given measurement effect absorb?". They are plain arithmetic on the curves; **none is a calibrated model of any survey**, and
none of the numbers below says that any survey has the scatter, offset, limit or floor that is tried.

| operation | JavaScript (`observer-lib.js`) | Python (`sim_highline.py`) |
|---|---|---|
| Gaussian scatter in log stellar mass, constant or mass-dependent | `scatterPoints(points, sigma, opts)` | `scatter_points(points, sigma, **opts)` |
| a systematic offset in the measured mass | `shiftPoints(points, offset)` | `shift_points(points, offset)` |
| a limiting mass (hard cut) | `completenessCut(points, mLim)` | `completeness_cut(points, m_lim)` |
| a smooth completeness (logistic in measured mass) | `completenessWeight(points, m50, width)` | `completeness_weight(points, m50, width)` |
| the three in survey order | `observePoints(points, opts)` | `observe(points, sigma, offset, m_lim, completeness)` |
| a detection floor on a specific star formation rate curve | `ssfrFloorPoints(points, floor)` | `ssfr_floor_points(points, floor)` |
| the same, from per-galaxy counts | `ssfrFloorRow(row, yEdges, floorLog)` | `ssfr_floor_row(row, y_edges, floor_log)` |
| Poisson bands from counts | `poissonBands(points)` | `poisson_bands(points)` |

Points are the records' own format: `{{x, y, yLow, yHigh, count}}` with x = log10 stellar mass and y = log10 number density per dex. Functions return new points and never change their input. Each function's docstring (and the comment above it in `observer-lib.js`) lists its assumptions; the important ones follow.

### Scatter (Eddington bias)

- **Model.** A galaxy of true log mass m is measured at m + e with e Gaussian, standard deviation sigma(m), where sigma depends on the true mass (a single number gives a constant scatter). The measured density is the convolution n_obs(x) = integral of n(m) N(x - m; sigma(m)) dm. Number is conserved because the kernel integrates to one for every m. The effect is largest where the curve is steep (the high-mass end), where scatter moves more galaxies up than down.
- **Grid.** log10 n is interpolated linearly between the points and continued past the first and last point as a straight line with the slope fitted to the nearest three points (the slope above the last point is never positive). The integral is a sum over a uniform grid of 0.005 dex (or sigma/2 if sigma is smaller than 0.01), reaching 8 sigma on either side of each output mass, so the kernel sums to 1 to better than 1e-12. Outputs are at the same masses as the inputs.
- **The continuation is a guess.** Every output carries `edgeShare`, the fraction of its scattered density that came from the continuation, and `edge` when that is above 5 per cent. Near the ends of a curve the result depends on the guess; the measurement below is repeated without those bins.
- **Bands.** The output log density is a weighted average of the input log densities (the weights are the shares of the scattered density that come from the neighbourhood of each input point, and sum to one). Independent input errors then combine as the square root of the sum of squared weights times squared errors, separately for the upper and lower side. A point that has only a count gets Poisson bands first. Not propagated: the uncertainty of sigma, of the continuation slope and of the interpolation, and the correlation between neighbouring outputs (they are reported as if independent). Cosmic variance is whatever the input already carries.
- **A density, not a catalogue.** No noise is added to individual galaxies, and the scatter is assumed Gaussian in log mass and independent of everything else (real mass errors are often skewed, correlated with the SED model and with redshift).

### Offset, completeness, floor

- **Offset.** Measured log mass = true log mass + offset. A density per dex does not change when the axis slides, so only x moves. One offset for all masses; no mass-dependent offset.
- **Limiting mass.** Points below the limit are removed, as a survey that corrects for completeness above its limit and publishes nothing below it. **Smooth completeness** multiplies the density by C = 1/(1 + exp(-(x - m50)/width)), the density an uncorrected catalogue would show; the bands keep their relative size and no new Poisson noise is derived. The logistic is a convenient shape, not a measured completeness. Both act on the measured mass, so they come after scatter and offset.
- **Detection floor for a specific star formation rate (sSFR).** On a curve of medians with a 16 to 84 per cent band, a point whose median is below the floor is removed (the typical galaxy there is not detected, so no median can be measured) and a lower band below the floor is raised to it. This does not recompute the median of the detected galaxies, which is higher than the median of all of them. When per-galaxy counts exist (a record's distribution), `ssfrFloorRow` drops the counts below the floor and returns the detected fraction and the quantiles of the detected galaxies, with the same within-bin rule as `compare.js`. A floor in SFR becomes an sSFR floor of SFR_min - log10 M (`sfrFloorToSsfr`).
- **Not done.** Scatter in SFR, mass-dependent offsets, redshift errors, cosmic variance, dust, and any link between the mass error and the SFR error.

## How it is tested

- `scripts/test-observer.mjs` (JavaScript) and `scripts/test_observer.py` (Python), the same checks in both: a pure power law gains exactly exp((beta sigma ln10)^2 / 2) (tolerance 1e-9 dex); a Gaussian mass function of width s becomes a Gaussian of width sqrt(s^2 + sigma^2) (2e-4 dex, the interpolation of an input sampled every 0.01 dex); a Schechter function is checked against the defining integral by an independent quadrature at every mass from 8.4 to 12 and, below the knee, against the asymptotic series for the Eddington-biased Schechter function (1e-3 dex). The Schechter function has no elementary closed form after scatter, so the quadrature and the series are the references; the power law and the Gaussian are exact. Mass-dependent scatter is checked against quadrature (1e-6 dex).
- Invariants: zero scatter returns the input exactly; the integrated number is conserved to 2e-4 for constant and mass-dependent sigma (a deliberately kinked test density, which is the worst case for the grid sum); bands shrink under averaging and keep their asymmetry; offsets and cuts are exact.
- JavaScript equals Python to 1e-9 on thirteen cases stored in `tests/fixtures/observer-fixture.json`.
- Both tests also run the same checks on a convolution replaced by a no-op and on one with half the scatter, and require them to fail.

## Measurement: how much of an offset could scatter absorb?

**Result in brief.** {brief}

**Question.** For every galaxy stellar mass function pair in the dataset, one from a simulation and one observed, that the comparison rules call comparable at similar redshift: how does the median offset change if the simulation curve is scattered by 0.1, 0.2 or 0.3 dex?

**Pairs.** Relation `gsmf`; the rules of `compare.js` (through `sim_highline.compatible`) must not return "not-comparable" (this already requires both records to be rankable, so digitized figures are out); the two redshift ranges must be at most max(0.15, 0.1 (1 + z)) apart, the tolerance the Explorer uses; and the stated populations must be equal. For this relation the rules of `compare.js` now require that (a quiescent-galaxy mass function is not compared with an all-galaxy one); an earlier version of the rules did not check it, and 76 such pairs had to be removed by hand in the first run of this measurement. The script still checks the populations itself as a safeguard and removes {pop_mismatch} pairs on that test. {n_sim} simulation records and {n_obs} observed records give {n_total} possible pairs; {n_notcomp} are not comparable, {n_far} are comparable but at redshifts too far apart, {n_pop} are removed for population, leaving {n_comp}. {n_gap} of those have a simulation curve with a gap over 1 dex that cannot be scattered, and {n_few} share fewer than {minbins} bins with the observed curve, so **{n_pairs} pairs ({n_ds} simulation records, {n_do} observed records) are measured**. The pairs are not independent: one simulation curve is paired with every survey at its redshift, and neighbouring redshifts share a survey.

**Offset.** Simulation minus observation in log10 number density, the median over the bins the Explorer compares (observed bins inside the simulation's range, never extrapolated, at least {minbins} of them). Positive means the simulation lies above. The definition differences the rules list as caveats (aperture or total mass, cosmology, IMF) are **not** converted here, as in the Explorer; in these pairs the caveats are: {caveats}. For scale, the Hubble-constant difference alone is worth {h0med} dex in number density (median; at most {h0max}) in the comparable pairs and is not converted either.

**"Larger than the observational uncertainty".** The median offset's absolute value exceeds the median, over the bins compared, of the observed 1-sigma (the larger of upper and lower error). {n_nosig} of the measured pairs have an observed curve with no uncertainty and are left out of the counts of changes.

{table_main}

Reading the table: each row applies the scatter to the simulation and recomputes the offset for the same pairs ("without" is the offset as it stands). "Larger to smaller" is the number of pairs whose offset was larger than the observational uncertainty and is smaller after; "smaller to larger" is shown because scatter can also make an offset worse. In the simulation curves of these pairs, 90 per cent of the changes in log density caused by the scatter lie between {chg_lo} and {chg_hi} dex for 0.1 dex of scatter, {chg2_lo} and {chg2_hi} for 0.2 and {chg3_lo} and {chg3_hi} for 0.3 (5th to 95th percentile over all bins, bins flagged as depending on the continuation left out; a few far-tail points of fitted curves change by tens of dex and mean nothing): it raises the curve by little on a shallow slope and by a lot on the steep high-mass end, and lowers it slightly in a few bins where the curve has a bump. It therefore helps where the simulation lies below the observations and hurts where it lies above, and because the offset here is a median over bins, a change confined to the steep end moves it little.

Of the {n_sigpairs} classified pairs, the smallest tested sigma that brings the offset inside the observational uncertainty: {first_text}.

### Without the bins that depend on the continuation

{table_int}

The same, with the bins removed where more than 5 per cent of the scattered density comes from the guessed continuation. Before and after are compared on the same bins; a larger scatter flags more bins, so the pairs (and the baseline) differ from row to row, and pairs left with too few bins drop out.

### By simulation

{table_src}

## What this shows, and what it does not

- It shows how large an offset in number density a Gaussian mass scatter of 0.1, 0.2 or 0.3 dex could remove, pair by pair, with the Explorer's own offsets. A pair whose offset shrinks to within the observational uncertainty is a pair where that much scatter would be enough, not one where it is present.
- It does not show that any of the surveys has such scatter. Published mass functions of the observed side usually come with their own error treatment (some correct for the Eddington bias, some do not), and this project has not read that for each one.
- It does not separate scatter from the other differences left in these pairs (aperture against total stellar mass, cosmology, IMF, cosmic variance, resolution at the low-mass end). An offset that scatter absorbs may equally be absorbed by one of those.
- Applying the scatter to a simulation curve that already includes an observer-side convolution would count it twice. The rankable COLIBRE records state that no Eddington-bias scatter is added (the convolved variant in the same file is not ingested); the records of the other simulations in these pairs contain no sentence about it either way. That is read from the records' own text, not from the papers.
- The result depends on the dataset: it is regenerated whenever curves are added (`python3 scripts/analyze_observer_layer.py`; `scripts/test_observer_layer.py` fails if the saved file is out of date).

## Where an interface would attach (not built)

{attach}
"""

ATTACH = """These are the places in the existing code where a control for the observer layer would connect. None is implemented; `highline/index.html` is untouched by this work. Names, not line numbers, because the page is being edited.

1. **Load the library next to `compare.js` and `export-lib.js`.** `scripts/build-highline.mjs` reads those two files (and `highline/logic.js`) and inlines them into the one-file Explorer; `observer-lib.js` would be read and inlined the same way and exposes `SimHighlineObserver`. `scripts/build-static.mjs` already copies `sim_highline.py` to `dist/`, so the Python half ships without a change. `scripts/coverage.sh` lists the JavaScript files it measures; `observer-lib.js` is added there.
2. **Where a plotted simulation curve is built.** In `highline/index.html`, `rawPoints(r, z)` takes a record's points (`rawPointsNative`) and applies the IMF shift (`imfShift`); `samples(r, z)` then applies the axis transform. The observer layer is a sibling of the IMF shift: it would run on the points `rawPoints` returns, simulations only, before `samples` transforms the axes, with its settings in the page state and the address. The original curve stays as a thin line; the observed-side curve is drawn dashed, as the page does for comparisons that are not definition-matched.
3. **The offset number in the legend and in the Tension view.** `offsetOf(r, a, z, raw)` calls `SimHighlineLogic.medianOffset` on `samples(...)` or `rawPoints(...)`; because it takes points, it works unchanged on scattered points. `renderLegend` would show the offset with and without the setting, and `renderTension` (the same function) would add the column.
4. **The Evidence panel.** `evidenceHtml` lists a record's definitions; it could list the operations applied (`observePoints(...).steps` is one line per operation) and the warning for bins flagged `edge`.
5. **My run.** `state.user` (parsed by `SimHighlineLogic.parseUserCurve`) and `compare_run` in `sim_highline.py` take the user's own curve; the same options (sigma, offset, limiting mass) would apply to it, in the same order.
6. **Specific star formation rate relations.** `ssfrFloorPoints` on the curves the page draws for relation `ssfr`; for records with `representation.distribution`, `ssfrFloorRow` next to `distributionStats` (`compare.js`), which already gives the quantiles the page draws.
7. **Command line and exports.** `sim_highline.main` (`sim-highline compare`) could take `--scatter 0.2 --mass-offset -0.1 --limiting-mass 8.5` and apply them to the user's curve. Exports are not made with any setting, and should stay so.
8. **Site pages.** `scripts/build-site.mjs` fills templates from saved results; a short page on the Methods route could point at this document and at `data/analysis/observer-layer.json`."""


def fmt(v, signed=True):
    return "n/a" if v is None else (f"{v:+.2f}" if signed else f"{v:.2f}")


def table_for(block, own_baseline=False):
    """One row per scatter. In the interior-only variant the set of bins (and so of pairs) differs between rows, so every row carries its own 'without scatter' numbers."""
    rows = ["| scatter applied to the simulation | pairs | median offset without (dex) | median offset with | median absolute offset without | with | larger than the uncertainty without | with | larger to smaller | smaller to larger |", "|---|---|---|---|---|---|---|---|---|---|"]
    for sg, b in block["bySigma"].items():
        rows.append(f"| {float(sg):.1f} dex | {b['pairs']} | {fmt(b['medianOffsetBeforeSamePairsSigned'])} | {fmt(b['medianOffsetAfter'])} | {fmt(b['medianAbsOffsetBeforeSamePairs'], False)} | {fmt(b['medianAbsOffsetAfter'], False)} | {b['largerBefore']} | {b['largerAfter']} | {b['largerToSmaller']} | {b['smallerToLarger']} |")
    return "\n".join(rows)


def render(res):
    c, m = res["counts"], res["results"]["main"]
    srcrows = ["| simulation | pairs | simulation records | median offset, none | after 0.1 dex | after 0.2 dex | after 0.3 dex | larger to smaller at 0.1 / 0.2 / 0.3 | smaller to larger at 0.1 / 0.2 / 0.3 |", "|---|---|---|---|---|---|---|---|---|"]
    for name, b in res["results"]["bySource"].items():
        srcrows.append(f"| {name} | {b['pairs']} | {b['simulationRecords']} | {fmt(b['medianOffsetBefore'])} | " + " | ".join(fmt(b[f"medianOffsetAfter{sg}"]) for sg in SIGMAS)
                       + " | " + " / ".join(str(b[f"largerToSmaller{sg}"]) for sg in SIGMAS) + " | " + " / ".join(str(b[f"smallerToLarger{sg}"]) for sg in SIGMAS) + " |")
    sg1 = m["bySigma"][str(SIGMAS[0])]
    first = res["results"]["smallestSigmaThatBringsOffsetInside"]
    ncl = sum(first.values())
    ft = f"already inside the uncertainty without scatter, {first['alreadyInside']}; inside at 0.1 dex, {first['0.1']}; at 0.2 dex, {first['0.2']}; at 0.3 dex, {first['0.3']}; still outside at 0.3 dex, {first['none']}"
    cav = ", ".join(f"{k} ({v} pairs)" for k, v in sorted(res["caveatKinds"].items(), key=lambda kv: -kv[1])) or "none"
    return TEMPLATE.format(pop_mismatch=c.get("populationMismatch", 0), n_sim=c["simulationRecords"], n_obs=c["observationRecords"], n_total=c["pairsTotal"], n_notcomp=c.get("notComparable", 0), n_far=c.get("comparableButEpochsFarApart", 0),
                           n_pop=c.get("populationMismatch", 0), n_comp=c["comparablePairs"], n_gap=c.get("simulationCurveHasGapOver1dex", 0), n_few=c.get("fewerThanMinBins", 0), minbins=res["settings"]["minimumSharedBins"],
                           n_pairs=c["pairsMeasured"], n_ds=c["distinctSimulationRecordsInPairs"], n_do=c["distinctObservationRecordsInPairs"], caveats=cav, n_nosig=sg1["noObservationalUncertainty"], h0med=f"{res['unconvertedDifferences']['h0InDensityDexMedian']:.2f}", h0max=f"{res['unconvertedDifferences']['h0InDensityDexMax']:.2f}",
                           table_main=table_for(m), table_int=table_for(res["results"]["interiorOnly"]), brief=brief_text(res), **chg_args(res), table_src=table_src(srcrows), n_sigpairs=ncl, first_text=ft, attach=ATTACH.strip())


def chg_args(res):
    ch = res["changeInLog10DensityFromScatter"]
    out = {}
    for k, sg in zip(("", "2", "3"), SIGMAS):
        out[f"chg{k}_lo"], out[f"chg{k}_hi"] = f"{ch[str(sg)]['p5']:+.2f}", f"{ch[str(sg)]['p95']:+.2f}"
    return out


def brief_text(res):
    m = res["results"]["main"]["bySigma"]
    a, b, c = (m[str(sg)] for sg in SIGMAS)
    return (f"Without scatter, {a['largerBefore']} of the {a['largerBefore'] + a['staySmaller'] + a['smallerToLarger']} classified pairs have an offset larger than the observational uncertainty. "
            f"Scatter of 0.1, 0.2 and 0.3 dex moves {a['largerToSmaller']}, {b['largerToSmaller']} and {c['largerToSmaller']} of them to smaller, and moves {a['smallerToLarger']}, {b['smallerToLarger']} and {c['smallerToLarger']} pairs the other way. "
            f"The median offset over all {res['counts']['pairsMeasured']} pairs goes from {fmt(res['results']['main']['medianOffsetBefore'])} dex to {fmt(a['medianOffsetAfter'])}, {fmt(b['medianOffsetAfter'])} and {fmt(c['medianOffsetAfter'])} dex: the simulations lie mostly above the observations, and scatter raises them further. "
            f"At 0.3 dex, {c['largerToSmaller']} of the {a['largerBefore']} large offsets fall inside the uncertainty and {c['smallerToLarger']} pairs that were inside move outside. This measures how much of an offset a given scatter could absorb; it is not evidence that any survey has that scatter.")


def table_src(rows):
    return "\n".join(rows) + "\n\nMedian over the pairs of that simulation, in dex; positive means the simulation lies above the observations. Pairs of one simulation are not independent."


def main():
    res = compute()
    text_json = json.dumps(res, indent=1, ensure_ascii=False) + "\n"
    text_doc = render(res)
    if "--check" in sys.argv:
        bad = [p.name for p, t in ((OUT_JSON, text_json), (OUT_DOC, text_doc)) if not p.exists() or p.read_text() != t]
        if bad:
            print(f"{', '.join(bad)} out of date: run python3 scripts/analyze_observer_layer.py")
            raise SystemExit(1)
        print("observer-layer results are up to date")
        return
    OUT_JSON.write_text(text_json)
    OUT_DOC.write_text(text_doc)
    c = res["counts"]
    print(f"{c['pairsMeasured']} pairs measured ({c['distinctSimulationRecordsInPairs']} simulation records, {c['distinctObservationRecordsInPairs']} observed); wrote {OUT_JSON.relative_to(ROOT)} and {OUT_DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
