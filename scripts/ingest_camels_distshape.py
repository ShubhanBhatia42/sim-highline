"""Shape-of-the-star-formation-distribution summaries of the CAMELS IllustrisTNG and SIMBA simulations (the data of docs/PROTOCOL-quenching-shape.md), reduced from the public Subfind catalogues without downloading them: only
three arrays are read by HTTP range requests (SubhaloMassType, SubhaloLenType, SubhaloSFR) and their bytes are hashed.

For every simulation of the Latin-hypercube set LH (1000 per code) and the cosmic-variance set CV (27 per code, fiducial parameters) at z = 0, 0.95 and 2.15, one number per bin of 0.25 dex in stellar mass from 10^9 to 10^11.5 Msun (ten
bins; galaxies are Subfind subhaloes with at least one star particle; M* is the total bound stellar mass; sSFR is the instantaneous SFR of all gas in the subhalo over M*; a galaxy with zero SFR has log sSFR = -infinity and counts as quenched):
  gv      fraction of the bin's galaxies with -11.0 <= log10 sSFR < -10.5 (a bin needs at least 10 galaxies)
  sfw     84th minus 16th percentile (linear interpolation, numpy default) of log10 sSFR among the bin's galaxies with SFR > 0 and log10 sSFR >= -10.5 (at least 10 such galaxies)
  gvwide  the same fraction as gv with the lower threshold at -11.5 (protocol sensitivity S3; computed here from the same arrays, so no second ingest is needed)
  ngal, nsf  counts that are not outputs: galaxies in the bin and galaxies in the bin that enter sfw (used for protocol validation V3)
Writes data/ensembles/camels-distshape.json in the layout of camels-galaxies.json. Usage: python3 scripts/ingest_camels_distshape.py [--limit N] [--workers W] [--snaps 090,062,042] [--out PATH]. Needs fsspec, aiohttp and h5py."""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://users.flatironinstitute.org/~camels"
SNAPS = {"090": 0.0, "062": 0.95, "042": 2.15}
MSTAR_EDGES = np.round(np.arange(9.0, 11.5001, 0.25), 3)  # 10 bins
GV_LO, GV_HI, GV_LO_WIDE = -11.0, -10.5, -11.5
SFW_FLOOR = -10.5
MIN_N = 10
FAMILIES = ["gv", "sfw", "gvwide"]
COUNTS = ["ngal", "nsf"]
ARRAYS = ["SubhaloMassType", "SubhaloLenType", "SubhaloSFR"]


def _r(v, d=4):
    return None if v is None or not np.isfinite(v) else round(float(v), d)


def shape_summaries(a, h):
    """The summaries of one catalogue. `a` holds the arrays named in ARRAYS; `h` is the dimensionless Hubble parameter (masses are in 1e10 Msun/h). Pure function, tested on synthetic catalogues."""
    ms = a["SubhaloMassType"][:, 4] * 1e10 / h
    has = (a["SubhaloLenType"][:, 4] > 0) & (ms > 0)
    sfr = a["SubhaloSFR"]
    with np.errstate(divide="ignore"):
        lssfr = np.where(sfr > 0, np.log10(np.where(sfr > 0, sfr, 1.0) / np.where(ms > 0, ms, 1.0)), -np.inf)
    lm = np.log10(np.where(ms > 0, ms, 1.0))
    out = {k: [] for k in FAMILIES + COUNTS}
    for lo, hi in zip(MSTAR_EDGES[:-1], MSTAR_EDGES[1:]):
        s = has & (lm >= lo) & (lm < hi)
        n = int(s.sum())
        out["ngal"].append(n)
        out["gv"].append(_r(float(np.mean((lssfr[s] >= GV_LO) & (lssfr[s] < GV_HI)))) if n >= MIN_N else None)
        out["gvwide"].append(_r(float(np.mean((lssfr[s] >= GV_LO_WIDE) & (lssfr[s] < GV_HI)))) if n >= MIN_N else None)
        sf = s & (sfr > 0) & (lssfr >= SFW_FLOOR)
        k = int(sf.sum())
        out["nsf"].append(k)
        out["sfw"].append(_r(float(np.percentile(lssfr[sf], 84) - np.percentile(lssfr[sf], 16))) if k >= MIN_N else None)
    return out


def read_snapshot(url):
    """Header values and the three arrays of one catalogue by range requests; returns (arrays, z, h, sha256 of the arrays' bytes, file size)."""
    import fsspec
    import h5py
    fs = fsspec.filesystem("http")
    size = int(fs.info(url)["size"])
    with fs.open(url, mode="rb", block_size=2 ** 20, cache_type="readahead") as f:
        with h5py.File(f, "r") as hf:
            hd = hf["Header"].attrs
            z, hh = float(hd["Redshift"]), float(hd["HubbleParam"])
            arr, sha = {}, hashlib.sha256()
            for n in ARRAYS:
                arr[n] = hf[f"Subhalo/{n}"][:]
                sha.update(np.ascontiguousarray(arr[n]).tobytes())
    return arr, z, hh, sha.hexdigest(), size


def one(args):
    suite, sset, name, snaps = args
    res = {}
    for s in snaps:
        url = f"{BASE}/Sims/{suite}/{sset}/{name}/groups_{s}.hdf5"
        for attempt in range(4):
            try:
                arr, z, h, sha, size = read_snapshot(url)
                res[s] = {"z": round(z, 4), "n_subhalos": int(len(arr["SubhaloSFR"])), "values": shape_summaries(arr, h), "arrays_sha256": sha, "file_bytes": size}
                break
            except Exception as e:  # network hiccups
                if attempt == 3:
                    res[s] = {"error": str(e)[:120]}
                time.sleep(2 ** attempt)
    return suite, sset, name, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--snaps", default=",".join(SNAPS))
    ap.add_argument("--suites", default="IllustrisTNG,SIMBA")
    ap.add_argument("--out", default=str(ROOT / "data" / "ensembles" / "camels-distshape.json"))
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ingest_camels_sfrd as I
    snaps = args.snaps.split(",")
    jobs, params = [], {}
    for suite in args.suites.split(","):
        I.SUITES.setdefault(suite, {"sfr_col": 2, "param_dir": suite})
        for sset in ("LH", "CV"):
            p = I.parameters(suite, sset)
            params[(suite, sset)] = p
            names = sorted(p, key=lambda k: int(k.split("_")[1]))[: args.limit]
            jobs += [(suite, sset, n, snaps) for n in names]
    out = {"schemaVersion": "1.0.0", "source": "CAMELS first-generation Subfind catalogues (Villaescusa-Navarro et al. 2021, ApJ 915, 71)", "base": BASE, "snapshots": {s: SNAPS[s] for s in snaps},
           "mstarEdges": [float(v) for v in MSTAR_EDGES], "families": FAMILIES, "counts": COUNTS, "familyBins": {k: len(MSTAR_EDGES) - 1 for k in FAMILIES + COUNTS},
           "definitions": __doc__.split("Writes")[0].split("\n\n", 1)[1].strip(), "suites": {}}
    t0 = time.time()
    done = 0
    with ProcessPoolExecutor(args.workers) as ex:
        for suite, sset, name, res in ex.map(one, jobs, chunksize=2):
            d = out["suites"].setdefault(suite, {}).setdefault(sset, {})
            d[name] = {**params[(suite, sset)][name], "snaps": res}
            done += 1
            if done % 100 == 0:
                print(f"{done}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    Path(args.out).write_text(json.dumps(out, separators=(",", ":")) + "\n")
    errs = sum(1 for su in out["suites"].values() for ss in su.values() for r in ss.values() for s in r["snaps"].values() if "error" in s)
    print(f"written {args.out}: {done} simulations, {errs} snapshot errors, {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
