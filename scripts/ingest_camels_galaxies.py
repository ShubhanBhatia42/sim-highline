"""Galaxy-population summaries of the CAMELS IllustrisTNG and SIMBA simulations at several redshifts, reduced from the public Subfind catalogues (groups_NNN.hdf5) without downloading them: only the arrays needed
are read by HTTP range requests (about 1 MB of a 15 to 50 MB file), and the arrays' bytes are hashed.

For every simulation of the Latin-hypercube set LH (1000 per code, six parameters) and the cosmic-variance set CV (27 per code, fiducial parameters, 27 seeds), and at the snapshots z = 0, 0.95, 2.15, 3 and 4, one number
per bin of each of the following (all galaxies are Subfind subhaloes with at least one star particle; M* is the total bound stellar mass; bins of 0.25 dex in M* from 10^9 to 10^11.5 Msun, about 60 star particles at
the bottom; a bin needs at least 5 galaxies for a median and at least 1 for a count):
  gsmf   log10 of the number of galaxies per comoving cMpc^3 per dex
  qf     fraction with specific star formation rate below 1e-11 per yr (zero star formation counts as quenched)
  sfms   median log10 specific SFR of galaxies with SFR > 0
  bhms   median log10 black hole mass of galaxies with a black hole
  bhocc  fraction of galaxies with a black hole
  mzr    median log10 of the SFR-weighted gas metallicity over 0.0127, galaxies with SFR > 0
  zstar  median log10 of the stellar metallicity over 0.0127
  size   median log10 stellar half-mass radius (physical kpc)
  fgas   median gas fraction inside twice the stellar half-mass radius, Mgas / (Mgas + M*)
  shmr   centrals only, bins of 0.25 dex in M200c from 10^11 to 10^13 Msun: median log10 (M* / M200c)
  hmf    centrals only, bins of 0.5 dex in M200c from 10^10.5 to 10^13.5 Msun: log10 of the number per cMpc^3 per dex
  rho    scalars: log10 of the stellar mass density in subhaloes and of the instantaneous SFR density
Writes data/ensembles/camels-galaxies.json. Usage: python3 scripts/ingest_camels_galaxies.py [--limit N] [--workers W] [--snaps 090,062,...] [--out PATH]. Needs fsspec, aiohttp and h5py."""
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
SNAPS = {"090": 0.0, "062": 0.95, "042": 2.15, "032": 3.0, "024": 4.0}
ZSUN = 0.0127
SSFR_Q = 1e-11
MSTAR_EDGES = np.round(np.arange(9.0, 11.5001, 0.25), 3)  # 10 bins
M200_EDGES_SHMR = np.round(np.arange(11.0, 13.0001, 0.25), 3)  # 8 bins
M200_EDGES_HMF = np.round(np.arange(10.5, 13.5001, 0.5), 3)  # 6 bins
MIN_MEDIAN, MIN_COUNT = 5, 1
FAMILIES = ["gsmf", "qf", "sfms", "bhms", "bhocc", "mzr", "zstar", "size", "fgas", "shmr", "hmf", "rho"]
FAMILY_BINS = {k: len(MSTAR_EDGES) - 1 for k in ("gsmf", "qf", "sfms", "bhms", "bhocc", "mzr", "zstar", "size", "fgas")}
FAMILY_BINS.update({"shmr": len(M200_EDGES_SHMR) - 1, "hmf": len(M200_EDGES_HMF) - 1, "rho": 2})
ARRAYS = {"Subhalo": ["SubhaloMassType", "SubhaloMassInRadType", "SubhaloHalfmassRadType", "SubhaloSFR", "SubhaloBHMass", "SubhaloGasMetallicitySfrWeighted", "SubhaloStarMetallicity", "SubhaloGrNr", "SubhaloLenType"],
          "Group": ["GroupFirstSub", "Group_M_Crit200"]}


def _med(x, minn=MIN_MEDIAN):
    return float(np.log10(np.median(x))) if len(x) >= minn and np.median(x) > 0 else None


def _r(v, d=3):
    return None if v is None or not np.isfinite(v) else round(float(v), d)


def summarize(a, z, h, box_ckpc_h):
    """The summaries of one catalogue. `a` holds the arrays named in ARRAYS (Subhalo and Group fields under their own names, Header values as z, h, box). Pure function of its inputs, tested on synthetic catalogues."""
    vol = (box_ckpc_h / 1000.0 / h) ** 3  # comoving Mpc^3
    scale = 1.0 / (1.0 + z)
    mt, mr = a["SubhaloMassType"] * 1e10 / h, a["SubhaloMassInRadType"] * 1e10 / h
    ms = mt[:, 4]
    has = (a["SubhaloLenType"][:, 4] > 0) & (ms > 0)
    sfr = a["SubhaloSFR"]
    ssfr = np.where(ms > 0, sfr / np.where(ms > 0, ms, 1.0), 0.0)
    bh = a["SubhaloBHMass"] * 1e10 / h
    rhalf = a["SubhaloHalfmassRadType"][:, 4] * scale / h  # physical kpc
    zg, zs = a["SubhaloGasMetallicitySfrWeighted"], a["SubhaloStarMetallicity"]
    gas_in = mr[:, 0]
    fgas = np.where(gas_in + mr[:, 4] > 0, gas_in / np.where(gas_in + mr[:, 4] > 0, gas_in + mr[:, 4], 1.0), np.nan)
    first = a["GroupFirstSub"]
    cen = np.zeros(len(ms), bool)
    cen[first[first >= 0]] = True
    m200 = a["Group_M_Crit200"][a["SubhaloGrNr"]] * 1e10 / h
    lm = np.log10(np.where(ms > 0, ms, 1.0))
    out = {k: [] for k in FAMILIES}
    for lo, hi in zip(MSTAR_EDGES[:-1], MSTAR_EDGES[1:]):
        s = has & (lm >= lo) & (lm < hi)
        n = int(s.sum())
        out["gsmf"].append(_r(np.log10(n / vol / 0.25)) if n >= MIN_COUNT else None)
        out["qf"].append(_r(float(np.mean(ssfr[s] < SSFR_Q))) if n >= MIN_MEDIAN else None)
        sf = s & (sfr > 0)
        out["sfms"].append(_r(_med(ssfr[sf])) if sf.sum() >= MIN_MEDIAN else None)
        b = s & (bh > 0)
        out["bhms"].append(_r(_med(bh[b])) if b.sum() >= MIN_MEDIAN else None)
        out["bhocc"].append(_r(float(np.mean(bh[s] > 0))) if n >= MIN_MEDIAN else None)
        g = sf & (zg > 0)
        out["mzr"].append(_r(_med(zg[g] / ZSUN)) if g.sum() >= MIN_MEDIAN else None)
        st = s & (zs > 0)
        out["zstar"].append(_r(_med(zs[st] / ZSUN)) if st.sum() >= MIN_MEDIAN else None)
        r_ = s & (rhalf > 0)
        out["size"].append(_r(_med(rhalf[r_])) if r_.sum() >= MIN_MEDIAN else None)
        f_ = s & np.isfinite(fgas)
        out["fgas"].append(_r(float(np.median(fgas[f_]))) if f_.sum() >= MIN_MEDIAN else None)
    lm200 = np.log10(np.where(m200 > 0, m200, 1.0))
    for lo, hi in zip(M200_EDGES_SHMR[:-1], M200_EDGES_SHMR[1:]):
        s = cen & has & (lm200 >= lo) & (lm200 < hi)
        out["shmr"].append(_r(float(np.log10(np.median(ms[s] / m200[s])))) if s.sum() >= MIN_MEDIAN else None)
    for lo, hi in zip(M200_EDGES_HMF[:-1], M200_EDGES_HMF[1:]):
        n = int((cen & (lm200 >= lo) & (lm200 < hi)).sum())
        out["hmf"].append(_r(np.log10(n / vol / 0.5)) if n >= MIN_COUNT else None)
    out["rho"] = [_r(np.log10(ms[has].sum() / vol)) if has.any() else None, _r(np.log10(sfr.sum() / vol)) if sfr.sum() > 0 else None]
    return out


def read_snapshot(url):
    """Header values and the needed arrays of one catalogue by range requests; returns (arrays, z, h, box, sha256 of the arrays' bytes, file size)."""
    import fsspec
    import h5py
    fs = fsspec.filesystem("http")
    size = int(fs.info(url)["size"])
    with fs.open(url, mode="rb", block_size=2 ** 20, cache_type="readahead") as f:
        with h5py.File(f, "r") as h:
            hd = h["Header"].attrs
            z, hh, box = float(hd["Redshift"]), float(hd["HubbleParam"]), float(hd["BoxSize"])
            arr, sha = {}, hashlib.sha256()
            for grp, names in ARRAYS.items():
                for n in names:
                    arr[n] = h[f"{grp}/{n}"][:]
                    sha.update(np.ascontiguousarray(arr[n]).tobytes())
    return arr, z, hh, box, sha.hexdigest(), size


def one(args):
    suite, sset, name, snaps = args
    res = {}
    for s in snaps:
        url = f"{BASE}/Sims/{suite}/{sset}/{name}/groups_{s}.hdf5"
        for attempt in range(4):
            try:
                arr, z, h, box, sha, size = read_snapshot(url)
                res[s] = {"z": round(z, 4), "n_subhalos": int(len(arr["SubhaloSFR"])), "values": summarize(arr, z, h, box), "arrays_sha256": sha, "file_bytes": size}
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
    ap.add_argument("--out", default=str(ROOT / "data" / "ensembles" / "camels-galaxies.json"))
    args = ap.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ingest_camels_sfrd as I
    snaps = args.snaps.split(",")
    jobs, params = [], {}
    for suite in ("IllustrisTNG", "SIMBA"):
        for sset in ("LH", "CV"):
            p = I.parameters(suite, sset)
            params[(suite, sset)] = p
            names = sorted(p, key=lambda k: int(k.split("_")[1]))[: args.limit]
            jobs += [(suite, sset, n, snaps) for n in names]
    out = {"schemaVersion": "1.0.0", "source": "CAMELS first-generation Subfind catalogues (Villaescusa-Navarro et al. 2021, ApJ 915, 71)", "base": BASE, "snapshots": {s: SNAPS[s] for s in snaps},
           "mstarEdges": [float(v) for v in MSTAR_EDGES], "m200ShmrEdges": [float(v) for v in M200_EDGES_SHMR], "m200HmfEdges": [float(v) for v in M200_EDGES_HMF], "families": FAMILIES, "familyBins": FAMILY_BINS,
           "definitions": __doc__.split("Writes")[0].split("\n\n", 1)[1].strip(), "parameterRanges": {}, "suites": {}}
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
