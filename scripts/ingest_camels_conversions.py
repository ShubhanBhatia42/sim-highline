"""Measured conversions between definitions, from the CAMELS fiducial (cosmic-variance) Subfind catalogues of IllustrisTNG, SIMBA and Astrid: how much a galaxy's stellar mass, SFR, gas metallicity and stellar metallicity change when the aperture is changed
(all bound particles, within twice the stellar half-mass radius, within the stellar half-mass radius, within the radius of maximum circular velocity), how a central's total Subfind mass compares with M200crit, and the stellar mass function
that results from each stellar-mass definition. Every number is a median or percentile of galaxies in the catalogues, with the spread between the 27 seeds as its error bar. These are conversions for these three codes at 25 Mpc/h, not universal laws.
Stage 1 (network): python3 scripts/ingest_camels_conversions.py [--workers 12]    writes data/ensembles/camels-conversions.json (per-seed counts; arrays are read by HTTP range requests)
Stage 2 (offline, run by verify-all.sh): python3 scripts/ingest_camels_conversions.py --derive    pools the seeds and writes data/conversions.json (the file the Explorer and docs/CONVERSIONS.md read)."""
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
SNAPS = {"090": 0.0, "062": 0.95, "042": 2.15}
SUITES = ("IllustrisTNG", "SIMBA", "Astrid")
X_EDGES = [round(v, 3) for v in np.arange(9.0, 11.5001, 0.25)]       # log10 reference stellar mass
H_EDGES = [round(v, 3) for v in np.arange(10.0, 13.5001, 0.25)]      # log10 M200crit
G_EDGES = [round(v, 3) for v in np.arange(8.5, 12.0001, 0.1)]        # stellar mass function bins
MIN_N = 10                                                           # a seed contributes a bin's median only with this many galaxies
MIN_POOLED = 50                                                      # a bin is published only with this many galaxies in all seeds
ENS = ROOT / "data" / "ensembles" / "camels-conversions.json"
OUT = ROOT / "data" / "conversions.json"

# name: (reference array, [(label, array)], delta edges, what x is)
MASS_DEFS = [("rad2", "SubhaloMassInRadType"), ("rad1", "SubhaloMassInHalfRadType"), ("radmax", "SubhaloMassInMaxRadType")]
SFR_DEFS = [("rad2", "SubhaloSFRinRad"), ("rad1", "SubhaloSFRinHalfRad"), ("radmax", "SubhaloSFRinMaxRad")]
GASZ_DEFS = [("rad1", "SubhaloGasMetallicityHalfRad"), ("radmax", "SubhaloGasMetallicityMaxRad"), ("sfr", "SubhaloGasMetallicitySfr"), ("sfrweighted", "SubhaloGasMetallicitySfrWeighted")]
STARZ_DEFS = [("rad1", "SubhaloStarMetallicityHalfRad"), ("radmax", "SubhaloStarMetallicityMaxRad")]
MASS_D = [round(v, 3) for v in np.arange(-1.5, 0.1001, 0.01)]       # 0.01 dex: finer than the tightest distribution (the half-mass aperture is -0.301 by definition)
LOG_D = [round(v, 3) for v in np.arange(-2.0, 2.0001, 0.02)]
HALO_D = [round(v, 3) for v in np.arange(-1.0, 1.0001, 0.01)]
ARRAYS = ["SubhaloMassType", "SubhaloLenType", "SubhaloSFR", "SubhaloGasMetallicity", "SubhaloStarMetallicity", "SubhaloMass", "SubhaloGrNr"] + [a for _, a in MASS_DEFS + SFR_DEFS + GASZ_DEFS + STARZ_DEFS]
GROUP_ARRAYS = ["Group_M_Crit200", "GroupFirstSub"]


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
            for n in GROUP_ARRAYS:
                arr[n] = h[f"Group/{n}"][:]
                sha.update(np.ascontiguousarray(arr[n]).tobytes())
    return arr, z, hh, box, sha.hexdigest()


def delta_block(x, delta, x_edges, d_edges, ref_pos, def_pos):
    """Counts of (x, delta) on the grid, the per-bin median of delta, the per-bin number of reference galaxies and how many of those have the other quantity equal to zero."""
    ok = ref_pos & def_pos
    grid = D.bin_counts(x[ok], delta[ok], x_edges, d_edges)
    idx = np.digitize(x, x_edges) - 1
    nx = len(x_edges) - 1
    med, nref, nzero = [], [], []
    for i in range(nx):
        s = idx == i
        v = delta[ok & s]
        med.append(round(float(np.median(v)), 5) if v.size >= MIN_N else None)
        nref.append(int((ref_pos & s).sum()))
        nzero.append(int((ref_pos & ~def_pos & s).sum()))
    return {"grid": grid.astype(int).tolist(), "median": med, "nRef": nref, "nZeroOther": nzero}


def conversions(arr, h):
    """All conversion blocks for one catalogue (a pure function of its arrays; tested on synthetic catalogues in test_camels_conversions.py)."""
    ms_all = arr["SubhaloMassType"][:, 4] * 1e10 / h
    has = (arr["SubhaloLenType"][:, 4] > 0) & (ms_all > 0)
    lm = np.log10(np.where(ms_all > 0, ms_all, 1.0))
    sel = has & (lm >= X_EDGES[0]) & (lm < X_EDGES[-1])
    out = {"nSelected": int(sel.sum()), "pairs": {}, "gsmf": {}}

    def ratio(ref, other):
        r, o = np.asarray(ref, float), np.asarray(other, float)
        pos_r, pos_o = (r > 0) & np.isfinite(r), (o > 0) & np.isfinite(o)
        d = np.log10(np.where(pos_o, o, 1.0) / np.where(pos_r, r, 1.0))
        return d, pos_r, pos_o

    for label, name in MASS_DEFS:
        d, pr, po = ratio(arr["SubhaloMassType"][:, 4], arr[name][:, 4])
        out["pairs"][f"mass.total-to-{label}"] = delta_block(lm[sel], d[sel], X_EDGES, MASS_D, pr[sel], po[sel])
    ref_sfr = arr["SubhaloSFR"]
    for label, name in SFR_DEFS:
        d, pr, po = ratio(ref_sfr, arr[name])
        out["pairs"][f"sfr.total-to-{label}"] = delta_block(lm[sel], d[sel], X_EDGES, LOG_D, pr[sel], po[sel])
    for label, name in GASZ_DEFS:
        d, pr, po = ratio(arr["SubhaloGasMetallicity"], arr[name])
        out["pairs"][f"gasz.all-to-{label}"] = delta_block(lm[sel], d[sel], X_EDGES, LOG_D, pr[sel], po[sel])
    for label, name in STARZ_DEFS:
        d, pr, po = ratio(arr["SubhaloStarMetallicity"], arr[name])
        out["pairs"][f"starz.all-to-{label}"] = delta_block(lm[sel], d[sel], X_EDGES, LOG_D, pr[sel], po[sel])
    # centrals: Subfind total subhalo mass against M200crit of the same group
    first = arr["GroupFirstSub"]
    cen = first[first >= 0].astype(int)
    m200 = arr["Group_M_Crit200"][first >= 0] * 1e10 / h
    msub = arr["SubhaloMass"][cen] * 1e10 / h
    d, pr, po = ratio(m200, msub)
    x = np.log10(np.where(pr, m200, 1.0))
    keep = pr & (x >= H_EDGES[0]) & (x < H_EDGES[-1])
    out["pairs"]["halo.m200crit-to-subhalo"] = delta_block(x[keep], d[keep], H_EDGES, HALO_D, pr[keep], po[keep])
    # stellar mass functions from each definition (counts per 0.1 dex bin; volume is applied when pooling)
    for label, vals in (("total", arr["SubhaloMassType"][:, 4]), *((l, arr[n][:, 4]) for l, n in MASS_DEFS)):
        m = np.asarray(vals, float) * 1e10 / h
        ok = has & (m > 0)
        out["gsmf"][label] = np.histogram(np.log10(m[ok]), bins=G_EDGES)[0].astype(int).tolist()
    return out


def one(args):
    suite, name, snaps = args
    res = {}
    for s in snaps:
        url = f"{BASE}/Sims/{suite}/CV/{name}/groups_{s}.hdf5"
        for attempt in range(4):
            try:
                arr, z, h, box, sha = read(url)
                res[s] = {"z": round(z, 4), "h": round(h, 5), "boxCkpcH": box, "arraysSha256": sha, **conversions(arr, h)}
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
           "snapshots": SNAPS, "xEdges": X_EDGES, "haloEdges": H_EDGES, "gsmfEdges": G_EDGES, "deltaEdges": {"mass": MASS_D, "log": LOG_D, "halo": HALO_D}, "suites": {}}
    t0, done = time.time(), 0
    out["pooledGrids"] = {}
    with ProcessPoolExecutor(workers) as ex:
        for suite, name, res in ex.map(one, jobs, chunksize=1):
            for snap, r in res.items():            # the (x, delta) counts are summed over the seeds as they arrive (per-seed medians and counts are kept separately)
                for key, blk in (r.get("pairs") or {}).items():
                    g = np.array(blk.pop("grid"), int)
                    cur = out["pooledGrids"].setdefault(suite, {}).setdefault(snap, {})
                    cur[key] = g if key not in cur else cur[key] + g
            out["suites"].setdefault(suite, {})[name] = res
            done += 1
            if done % 9 == 0:
                print(f"{done}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)
    out["pooledGrids"] = {su: {sn: {k: g.tolist() for k, g in d.items()} for sn, d in v.items()} for su, v in out["pooledGrids"].items()}
    ENS.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    errs = sum(1 for su in out["suites"].values() for r in su.values() for s in r.values() if "error" in s)
    print(f"written {ENS}: {done} simulations, {errs} snapshot errors, {time.time() - t0:.0f}s")


def edges_for(key, ens):
    return ens["deltaEdges"]["halo"] if key.startswith("halo") else ens["deltaEdges"]["mass"] if key.startswith("mass") else ens["deltaEdges"]["log"]


def mass_at_number_density(counts, vol, edges, n_target):
    """log10 M at which the cumulative number density (galaxies above M per Mpc^3) equals n_target, by linear interpolation on the binned cumulative function; None outside the range."""
    c = np.cumsum(np.asarray(counts, float)[::-1])[::-1] / vol          # n(> lower edge of bin i)
    lo = np.asarray(edges[:-1], float)
    keep = c > 0                                                          # empty bins at the high-mass end have no cumulative density in logs
    if keep.sum() < 2 or not (c[keep].min() <= n_target <= c[0]):
        return None
    return float(np.interp(np.log10(n_target), np.log10(c[keep])[::-1], lo[keep][::-1]))


def derive():
    ens = json.loads(ENS.read_text())
    res = {"schemaVersion": "1.0.0", "retrieved": ens["retrieved"], "source": ens["source"],
           "about": "Measured conversions between definitions in the CAMELS fiducial (cosmic-variance) simulations of three codes, 27 seeds each, 25 Mpc/h boxes. Each conversion is the change in log10 of a quantity when its definition changes, as a function of the log10 stellar mass (or M200crit) of the galaxy; median and 16th to 84th percentile of the pooled galaxies, and the standard error of the median across the 27 seeds. Galaxies with a zero value in either definition are left out and counted separately. These describe these codes at this resolution and volume; they are not corrections for other simulations.",
           "xEdges": ens["xEdges"], "haloEdges": ens["haloEdges"], "minPooledGalaxies": MIN_POOLED, "minPerSeedForMedian": MIN_N, "numberDensities": [-2.0, -2.5, -3.0, -3.5], "suites": {}}
    for suite in SUITES:
        res["suites"][suite] = {}
        for snap, z in SNAPS.items():
            seeds = [(n, r[snap]) for n, r in sorted(ens["suites"][suite].items(), key=lambda kv: int(kv[0].split("_")[1])) if snap in r and "error" not in r[snap]]
            if not seeds:
                continue
            block = {"z": z, "nSeeds": len(seeds), "arraysSha256": hashlib.sha256("".join(s["arraysSha256"] for _, s in seeds).encode()).hexdigest(), "pairs": {}, "gsmf": {}}
            for key in seeds[0][1]["pairs"]:
                edges = edges_for(key, ens)
                xe = ens["haloEdges"] if key.startswith("halo") else ens["xEdges"]
                grid = np.array(ens["pooledGrids"][suite][snap][key], int)
                nref = np.sum([s["pairs"][key]["nRef"] for _, s in seeds], axis=0)
                nzero = np.sum([s["pairs"][key]["nZeroOther"] for _, s in seeds], axis=0)
                meds = np.array([[np.nan if v is None else v for v in s["pairs"][key]["median"]] for _, s in seeds])
                rows = []
                for i in range(len(xe) - 1):
                    tot = int(grid[i].sum())
                    if tot < MIN_POOLED:
                        continue
                    ok_i = meds[:, i]
                    m = ok_i[np.isfinite(ok_i)]
                    w = np.array([s["pairs"][key]["nRef"][i] - s["pairs"][key]["nZeroOther"][i] for _, s in seeds], float)[np.isfinite(ok_i)]
                    # the centre is the galaxy-weighted mean of the per-seed medians (exact); the histogram median (0.01 or 0.02 dex bins) is used only where fewer than 5 seeds have enough galaxies
                    centre = round(float(np.average(m, weights=w)), 4) if m.size >= 5 else round(D.quantile(grid[i], edges, tot, 0.5), 4)
                    rows.append({"x": round((xe[i] + xe[i + 1]) / 2, 4), "n": tot, "median": centre, "medianBasis": "seed-medians" if m.size >= 5 else "pooled-histogram", "p16": round(D.quantile(grid[i], edges, tot, 0.16), 4), "p84": round(D.quantile(grid[i], edges, tot, 0.84), 4),
                                 "seedSe": round(float(np.std(m, ddof=1) / np.sqrt(m.size)), 5) if m.size > 2 else None, "nSeedsUsed": int(m.size),
                                 "fractionZeroOther": round(float(nzero[i] / nref[i]), 4) if nref[i] else None})
                block["pairs"][key] = rows
            vols = [(s["boxCkpcH"] / 1000.0 / s["h"]) ** 3 for _, s in seeds]
            counts = {lab: np.sum([s["gsmf"][lab] for _, s in seeds], axis=0) for lab in seeds[0][1]["gsmf"]}
            width = ens["gsmfEdges"][1] - ens["gsmfEdges"][0]
            block["gsmf"] = {"edges": ens["gsmfEdges"], "volumeMpc3": round(sum(vols), 1),
                             "logPhi": {lab: [round(float(np.log10(c / sum(vols) / width)), 4) if c > 0 else None for c in cs] for lab, cs in counts.items()},
                             "counts": {lab: cs.tolist() for lab, cs in counts.items()}}
            shifts = {}
            for lab in counts:
                if lab == "total":
                    continue
                per = {}
                for nd in res["numberDensities"]:
                    vals = []
                    for (_, s), v in zip(seeds, vols):
                        a = mass_at_number_density(s["gsmf"]["total"], v, ens["gsmfEdges"], 10 ** nd)
                        b = mass_at_number_density(s["gsmf"][lab], v, ens["gsmfEdges"], 10 ** nd)
                        if a is not None and b is not None:
                            vals.append(b - a)
                    a = mass_at_number_density(counts["total"], sum(vols), ens["gsmfEdges"], 10 ** nd)
                    b = mass_at_number_density(counts[lab], sum(vols), ens["gsmfEdges"], 10 ** nd)
                    per[f"{nd:g}"] = {"shiftDex": None if a is None or b is None else round(b - a, 4), "seedSe": round(float(np.std(vals, ddof=1) / np.sqrt(len(vals))), 4) if len(vals) > 2 else None, "nSeedsUsed": len(vals)}
                shifts[f"total-to-{lab}"] = per
            block["gsmfShiftAtFixedNumberDensity"] = shifts
            res["suites"][suite][f"z{z:g}"] = block
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(f"wrote {OUT}: {sum(len(v) for v in res['suites'].values())} (code, redshift) blocks")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--derive", action="store_true", help="offline: pool the saved per-seed counts and write data/conversions.json")
    a = ap.parse_args()
    derive() if a.derive else stage1(a.workers)
