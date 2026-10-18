"""Per-galaxy distributions of the CAMELS fiducial (cosmic-variance) simulations: for each code (IllustrisTNG, SIMBA, Astrid), each of the 27 seeds and the five snapshots used elsewhere, the counts of
Subfind subhaloes on a grid of log10 stellar mass (0.25 dex from 10^9 to 10^11.5 Msun) by log10 specific star formation rate (0.1 dex from -13.5 to -8.5; zero or lower values are put in the lowest bin) and,
for IllustrisTNG only (the other two catalogues carry no photometry), by the intrinsic g-r colour (0.04 mag from -0.2 to 1.2). Only the needed arrays are read, by HTTP range requests, as in ingest_camels_galaxies.py.
Stage 1 (network): python3 scripts/ingest_camels_distributions.py [--workers 12] [--sets CV]   writes data/ensembles/camels-distributions.json
Stage 2 (offline, run by verify-all.sh): python3 scripts/ingest_camels_distributions.py --records   pools the 27 seeds and writes data/curves/camels-distributions.json (then node scripts/derive-distributions.mjs adds the summaries)."""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import distribution_stats as D  # noqa: E402

ROOT = HERE.parent
BASE = "https://users.flatironinstitute.org/~camels"
SNAPS = {"090": 0.0, "062": 0.95, "042": 2.15, "032": 3.0, "024": 4.0}
SUITES = ("IllustrisTNG", "SIMBA", "Astrid")
X_EDGES = [round(v, 3) for v in np.arange(9.0, 11.5001, 0.25)]
SSFR_EDGES = [round(v, 3) for v in np.arange(-13.5, -8.4999, 0.1)]
COL_EDGES = [round(v, 3) for v in np.arange(-0.2, 1.2001, 0.04)]
ENS = ROOT / "data" / "ensembles" / "camels-distributions.json"
OUT = ROOT / "data" / "curves" / "camels-distributions.json"
ARRAYS = ["SubhaloMassType", "SubhaloLenType", "SubhaloSFR", "SubhaloStellarPhotometrics"]
SOURCE = {"IllustrisTNG": "IllustrisTNG", "SIMBA": "SIMBA", "Astrid": "ASTRID"}
DEFS = {"IllustrisTNG": {"imf": "chabrier03", "imfBasis": "TNG model paper (Pillepich+18); the CAMELS paper does not restate it"},
        "SIMBA": {"imf": "chabrier03", "imfBasis": "Dave+19 (SIMBA); the CAMELS paper does not restate it"},
        "Astrid": {"imf": "chabrier03", "imfBasis": "the ASTRID records already in this dataset; the CAMELS paper does not restate it"}}


def read(url):
    import fsspec
    import h5py
    fs = fsspec.filesystem("http")
    with fs.open(url, mode="rb", block_size=2 ** 20, cache_type="readahead") as f:
        with h5py.File(f, "r") as h:
            hd = h["Header"].attrs
            z, hh, box = float(hd["Redshift"]), float(hd["HubbleParam"]), float(hd["BoxSize"])
            arr, sha = {}, hashlib.sha256()
            for n in ARRAYS:
                arr[n] = h[f"Subhalo/{n}"][:]
                sha.update(np.ascontiguousarray(arr[n]).tobytes())
    return arr, z, hh, box, sha.hexdigest()


def grids(arr, h):
    """Counts on the two grids for one catalogue (pure function of its arrays; tested on synthetic catalogues)."""
    ms = arr["SubhaloMassType"][:, 4] * 1e10 / h
    has = (arr["SubhaloLenType"][:, 4] > 0) & (ms > 0)
    lm = np.log10(np.where(ms > 0, ms, 1.0))
    sfr = arr["SubhaloSFR"]
    ly = np.where((sfr > 0) & (ms > 0), np.log10(np.where(sfr > 0, sfr, 1.0) / np.where(ms > 0, ms, 1.0)), -99.0)
    sel = has & (lm >= X_EDGES[0]) & (lm < X_EDGES[-1])
    ssfr = D.bin_counts(lm[sel], ly[sel], X_EDGES, SSFR_EDGES)
    ph = arr["SubhaloStellarPhotometrics"]
    col = None
    if sel.any() and np.all(np.isfinite(ph[sel])):
        gr = (ph[:, 4] - ph[:, 5])[sel]
        if np.ptp(gr) > 0.05:  # SIMBA and Astrid catalogues carry placeholder photometry (infinite or constant); only real colours are kept
            col = D.bin_counts(lm[sel], gr, X_EDGES, COL_EDGES)
    return ssfr, col, int(sel.sum())


def one(args):
    suite, name, snaps = args
    res = {}
    for s in snaps:
        url = f"{BASE}/Sims/{suite}/CV/{name}/groups_{s}.hdf5"
        for attempt in range(4):
            try:
                arr, z, h, box, sha = read(url)
                g, c, n = grids(arr, h)
                res[s] = {"z": round(z, 4), "h": round(h, 5), "boxCkpcH": box, "nSelected": n, "ssfr": g.astype(int).tolist(), "colour": None if c is None else c.astype(int).tolist(), "arraysSha256": sha}
                break
            except Exception as e:
                if attempt == 3:
                    res[s] = {"error": str(e)[:120]}
                time.sleep(2 ** attempt)
    return suite, name, res


def stage1(workers):
    names = [f"CV_{i}" for i in range(27)]
    jobs = [(s, n, list(SNAPS)) for s in SUITES for n in names]
    out = {"schemaVersion": "1.0.0", "source": "CAMELS first-generation Subfind catalogues (Villaescusa-Navarro et al. 2021, ApJ 915, 71), cosmic-variance set CV", "base": BASE, "retrieved": date.today().isoformat(),
           "snapshots": SNAPS, "xEdges": X_EDGES, "ssfrEdges": SSFR_EDGES, "colourEdges": COL_EDGES,
           "definitions": __doc__.split("Stage 1")[0].strip(), "suites": {}}
    t0, done = time.time(), 0
    with ProcessPoolExecutor(workers) as ex:
        for suite, name, res in ex.map(one, jobs, chunksize=1):
            out["suites"].setdefault(suite, {})[name] = res
            done += 1
            if done % 9 == 0:
                print(f"{done}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    ENS.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    errs = sum(1 for su in out["suites"].values() for r in su.values() for s in r.values() if "error" in s)
    print(f"written {ENS}: {done} simulations, {errs} snapshot errors, {time.time() - t0:.0f}s")


def pooled(ens, suite, snap, key):
    tot, n_sims, sha, vol = None, 0, hashlib.sha256(), 0.0
    for name in sorted(ens["suites"][suite], key=lambda k: int(k.split("_")[1])):
        r = ens["suites"][suite][name].get(snap)
        if not r or "error" in r or r.get(key) is None:
            continue
        g = np.array(r[key], int)
        tot = g if tot is None else tot + g
        n_sims += 1
        sha.update(r["arraysSha256"].encode())
        vol += (r["boxCkpcH"] / 1000.0 / r["h"]) ** 3
    return tot, n_sims, sha.hexdigest(), vol


def stage2():
    ens = json.loads(ENS.read_text())
    recs = []
    for suite in SUITES:
        for snap, z in SNAPS.items():
            for key, rel, edges, ylab, yunit, ydef in (("ssfr", "ssfr", SSFR_EDGES, "log10 specific star formation rate", "log10(yr^-1)", "log10 specific SFR of all galaxies; zero or lower values are in the lowest bin"),
                                                       ("colour", "colour", COL_EDGES, "g-r colour", "mag (AB)", "intrinsic rest-frame g-r (SDSS filters, AB), summed stellar-particle luminosities, no dust attenuation")):
                tot, n_sims, sha, vol = pooled(ens, suite, snap, key)
                if tot is None or tot.sum() == 0:
                    continue
                short = {"IllustrisTNG": "tng", "SIMBA": "simba", "Astrid": "astrid"}[suite]
                rep = {"type": "distribution", "xEdges": X_EDGES, "yEdges": edges, "counts": tot.tolist(), "weighting": "number", "nSims": n_sims, "clipped": {"low": True, "high": True}}
                if rel == "ssfr":
                    rep["thresholds"] = [-11.0, -10.5]
                recs.append({
                    "id": f"camels.{short}.{rel}-dist.cv.z{z:g}", "source": SOURCE[suite], "run": "CAMELS CV, 27 seeds", "kind": "simulation", "relation": rel,
                    "epoch": {"zRepresentative": z, "zMin": z, "zMax": z, "mode": "snapshot", "snapshot": int(snap)},
                    "axes": {"xDefinition": "log10 stellar mass (total mass of the star particles bound to the Subfind subhalo)", "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": yunit},
                    "domain": {"xMin": X_EDGES[0], "xMax": X_EDGES[-1]},
                    "representation": rep,
                    "scatter": {"value": None, "unit": "dex" if rel == "ssfr" else "mag", "meaning": "the 16th to 84th percentile of the pooled galaxies in each stellar-mass bin"},
                    "selection": {"population": "all subhaloes with at least one star particle and stellar mass between 1e9 and 10^11.5 Msun, pooled over the 27 seeds",
                                  "warning": f"Pooled over {n_sims} boxes of 25 Mpc/h (total comoving volume {vol:.0f} Mpc^3); the distribution is of galaxies, not volume-weighted beyond that. Galaxies with zero instantaneous SFR, and those below the lowest sSFR bin, are in the lowest row and count as quenched; near the resolution limit (about 60 to 300 star particles) this probably inflates the quenched share at low mass, most visibly in Astrid (not verified against a resolution test). Stellar mass is the total bound mass, not an aperture mass; SFR is the instantaneous SFR of all gas in the subhalo."},
                    "provenance": {"tier": "catalog-derived", "citation": "Villaescusa-Navarro et al. 2021, ApJ 915, 71 (CAMELS), cosmic-variance set, Subfind catalogues; counts by this project", "doi": "10.3847/1538-4357/abf7ba", "url": "https://arxiv.org/abs/2010.00619",
                                   "retrieved": ens["retrieved"], "sourceMember": f"Sims/{suite}/CV/CV_0..CV_26/groups_{snap}.hdf5 (SubhaloMassType, SubhaloLenType, SubhaloSFR" + (", SubhaloStellarPhotometrics)" if key == "colour" else ")"), "checksumSha256": sha,
                                   "extractionMethod": "scripts/ingest_camels_distributions.py (HTTP range requests of the arrays; counts per seed in data/ensembles/camels-distributions.json)"},
                    "calibration": "prediction", "rankable": True,
                    "notes": "Per-galaxy distribution: the median and 16 to 84 per cent band shown as a curve are derived from the counts (scripts/derive-distributions.mjs).",
                    "definitions": {"massDefinition": "total-bound-subhalo", **DEFS[suite], "cosmology": {"H0": 67.11, "Om": 0.3}, "population": "all", "sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median"} if rel == "ssfr" else
                                   {"massDefinition": "total-bound-subhalo", **DEFS[suite], "cosmology": {"H0": 67.11, "Om": 0.3}, "population": "all", "colourBand": "g-r", "dustTreatment": "none (summed stellar-particle luminosities)"}})
                recs[-1]["scatter"].pop("value")
    OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=2) + "\n")
    print(f"wrote {len(recs)} distribution records to {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--records", action="store_true", help="offline: build the curve records from the saved counts")
    a = ap.parse_args()
    stage2() if a.records else stage1(a.workers)
