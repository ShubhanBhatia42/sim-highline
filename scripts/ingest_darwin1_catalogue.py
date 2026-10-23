"""The galaxy stellar mass function of DARWIN-1 counted from the project's public galaxy/halo catalogues (https://darwin.kasi.re.kr/data_darwin1.html), at eleven snapshots from z = 10 to z = 0.19.
A galaxy is a self-bound substructure of the catalogue that has star particles (`sub/nstar` > 0), as defined in Lee et al. 2026 (arXiv:2610.25786); its stellar mass is the catalogue column `sub/mstar`, which the catalogue states in Msun/h (divided by h = 0.674 here). Only `sub/mstar` and `sub/nstar` are read, by HTTP range requests (about 4 MB per snapshot).
Stage 1 (network, a few minutes): python3 scripts/ingest_darwin1_catalogue.py   writes data/ensembles/darwin1-gsmf.json (counts on a fine mass grid, what was read, and the comparison with the paper's Fig. 7)
Stage 2 (offline, run by verify-all.sh): python3 scripts/ingest_darwin1_catalogue.py --records   writes data/curves/darwin-catalogue.json
The comparison with the paper (stage 1) is the evidence that the column and the volume are read correctly: it counts the galaxies in the bins of the digitized curves of Fig. 7 (data/curves/darwin-lee26.json) and compares them with the counts those curves imply (a bin with n galaxies in the volume V has number density n/(V dM))."""
import argparse
import hashlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
URL = "https://archive.kasi.re.kr/darwin/coconas/Darwin/Darwin1/{s:04d}/catalog_{s:04d}.hdf5"
PAGE = "https://darwin.kasi.re.kr/data_darwin1.html"
# (snapshot, redshift of the snapshot as listed on the data page, nominal redshift)
SNAPS = [(1001, 0.190438, 0.19), (944, 0.251684, 0.25), (786, 0.500319, 0.5), (475, 1.002068, 1), (178, 1.990001, 2), (81, 3.002028, 3), (54, 3.991432, 4), (46, 5.015389, 5), (40, 5.931068, 6), (29, 7.986427, 8), (20, 10.113751, 10)]
H, OM, BOX_CMPC = 0.674, 0.315, 65.536  # Lee et al. 2026: H0 = 67.4 km/s/Mpc, Omega_m = 0.315, (65.536 cMpc)^3
FINE_LO, FINE_STEP, FINE_N = 6.0, 1 / 12, 84  # log10(M*/Msun) grid of the saved counts; 4 fine bins make one bin of 1/3 dex
COARSE = 4
LOGM_MIN = 7.0  # 100 or more star particles (one star particle is 5.4e4 Msun/h = 8.0e4 Msun)
ENS = ROOT / "data" / "ensembles" / "darwin1-gsmf.json"
OUT = ROOT / "data" / "curves" / "darwin-catalogue.json"
LEE = ROOT / "data" / "curves" / "darwin-lee26.json"
# the panels of Fig. 7 and the snapshot each is compared with
PANELS = {"z5": 46, "z3": 81, "z1": 475, "z0.25": 944}


def read(snap):
    import fsspec
    import h5py
    url = URL.format(s=snap)
    fs = fsspec.filesystem("http")
    info = fs.info(url)
    sha = hashlib.sha256()
    with fs.open(url, mode="rb", block_size=4 * 2 ** 20, cache_type="readahead") as f:
        with h5py.File(f, "r") as h:
            ms, ns = h["sub/mstar"][()], h["sub/nstar"][()]
            for a in (ms, ns):
                sha.update(np.ascontiguousarray(a).tobytes())
            pos_max = None
            if snap == SNAPS[0][0]:  # the size of the box, once: the largest coordinate (cMpc/h) of any substructure
                pos = h["sub/pos"][()]
                pos_max = float(np.nanmax(pos))
    has = (ns > 0) & (ms > 0)
    logm = np.log10(ms[has].astype(np.float64) / H)
    edges = FINE_LO + FINE_STEP * np.arange(FINE_N + 1)
    counts, _ = np.histogram(logm, bins=edges)
    return {"snapshot": snap, "url": url, "contentLength": int(info.get("size") or 0), "etag": str(info.get("ETag") or info.get("etag") or ""),
            "nSubstructures": int(len(ms)), "nWithStars": int(has.sum()), "nOutsideGrid": int(has.sum() - counts.sum()), "starParticleMassMsunPerH": float(np.min(ms[has])), "posMaxCMpcH": pos_max, "sha256": sha.hexdigest(), "counts": counts.astype(int).tolist()}


def coarse_counts(counts):
    c = np.asarray(counts)
    return c.reshape(-1, COARSE).sum(axis=1)  # FINE_N is a multiple of COARSE; coarse bin k covers 6 + k/3 to 6 + (k+1)/3


def figure_check(snaps):
    """Counts in the bins of each Fig. 7 panel (the digitized curves) against the counts the curves imply."""
    recs = {r["id"].split("gsmf.")[-1]: r for r in json.loads(LEE.read_text())["records"] if r["id"].startswith("lee26.darwin1.gsmf.")}
    vol = BOX_CMPC ** 3
    out = {}
    for key, snap in PANELS.items():
        cc = coarse_counts(snaps[str(snap)]["counts"])
        rows = []
        for p in recs[key]["representation"]["points"]:
            k = int(round((p["x"] - 1 / 6 - FINE_LO) * 3))
            implied = 10 ** p["y"] * vol / 3
            rows.append({"logM": p["x"], "implied": round(implied, 1), "catalogue": int(cc[k]), "dlog10": round(float(np.log10(cc[k] / implied)), 4) if cc[k] > 0 else None})
        low = [r for r in rows if r["implied"] >= 100]
        out[key] = {"snapshot": snap, "binsWith100OrMoreGalaxies": len(low), "maxAbsDlog10Over100": round(max((abs(r["dlog10"]) for r in low), default=0.0), 4),
                    "binsWithin10Percent": sum(1 for r in rows if r["dlog10"] is not None and abs(10 ** r["dlog10"] - 1) <= 0.10), "bins": rows}
    return out


def stage1():
    with ThreadPoolExecutor(max_workers=4) as pool:
        got = list(pool.map(read, [s for s, _, _ in SNAPS]))
    snaps = {str(g["snapshot"]): {**g, "z": z, "zNominal": zn} for g, (_, z, zn) in zip(got, SNAPS)}
    ens = {"schemaVersion": "1.0.0", "source": "DARWIN-1 public galaxy/halo catalogues (DARWIN project, KASI), " + PAGE, "retrieved": date.today().isoformat(), "h": H, "Om": OM, "boxCMpc": BOX_CMPC,
           "grid": {"logMin": FINE_LO, "step": FINE_STEP, "n": FINE_N}, "snapshots": snaps}
    ens["figureCheck"] = figure_check(snaps)
    ENS.write_text(json.dumps(ens, indent=1) + "\n")
    for k, v in ens["figureCheck"].items():
        print(f"Fig. 7 panel {k} (snapshot {v['snapshot']}): {v['binsWithin10Percent']} of {len(v['bins'])} bins within 10 %, largest difference over bins with 100 or more galaxies {v['maxAbsDlog10Over100']} dex")
    print(f"wrote {ENS}; box: largest substructure coordinate {snaps[str(SNAPS[0][0])]['posMaxCMpcH']:.3f} cMpc/h (the paper's box, {BOX_CMPC} cMpc, is {BOX_CMPC * H:.3f} cMpc/h)")


def stage2():
    ens = json.loads(ENS.read_text())
    vol, dm = BOX_CMPC ** 3, 1 / 3
    recs = []
    for snap, z, zn in SNAPS:
        s = ens["snapshots"][str(snap)]
        cc = coarse_counts(s["counts"])
        pts = []
        for k, n in enumerate(cc):
            lo = FINE_LO + k * dm
            if lo < LOGM_MIN - 1e-9 or n < 1:
                continue
            pts.append({"x": round(lo + dm / 2, 4), "y": round(float(np.log10(n / vol / dm)), 4), "yLow": round(float(np.log10(max(n - np.sqrt(n), 0.5) / vol / dm)), 4), "yHigh": round(float(np.log10((n + np.sqrt(n)) / vol / dm)), 4), "count": int(n)})
        if len(pts) < 2:
            continue
        panel = next((v for k, v in ens["figureCheck"].items() if v["snapshot"] == snap), None)
        cmp_note = ""
        if panel:
            cmp_note = (f" Compared with the paper's Fig. 7 panel at z = {zn:g} (the digitized curve lee26.darwin1.gsmf.z{zn:g}), {panel['binsWithin10Percent']} of {len(panel['bins'])} bins have the same galaxy count within 10 %"
                        f"; the largest difference in a bin of 100 or more galaxies is {panel['maxAbsDlog10Over100']:.3f} dex.")
        recs.append({
            "id": f"darwin1.catalogue.gsmf.z{zn:g}", "source": "DARWIN", "run": "DARWIN-1 (65.5 cMpc box)", "kind": "simulation", "relation": "gsmf",
            "epoch": {"zRepresentative": round(z, 4), "zNominal": zn, "zMin": round(z, 4), "zMax": round(z, 4), "mode": "snapshot", "snapshot": snap},
            "axes": {"xDefinition": "log10 stellar mass (total mass of the star particles of the self-bound substructure)", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy number density per dex of stellar mass (comoving, Poisson errors)", "yUnit": "log10(cMpc^-3 dex^-1)"},
            "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": pts}, "scatter": None,
            "selection": {"population": "all substructures with at least 100 star particles", "warning": (
                f"Counted by this project from the public DARWIN-1 galaxy catalogue of snapshot {snap} (z = {z:.3f}): every self-bound substructure with star particles, stellar mass `sub/mstar` (the catalogue gives it in Msun/h; divided by h = 0.674), bins of 1/3 dex from 10^7 Msun (100 or more star particles of 8.0e4 Msun each), "
                f"over the comoving volume (65.536 cMpc)^3. Poisson errors only; cosmic variance of one box not included. The catalogue page documents the columns but not how substructures are found; the match of these counts with the paper's own figure is the evidence that the column and the volume are read correctly.{cmp_note}")},
            "definitions": {"imf": "kroupa01", "cosmology": {"H0": 67.4, "Om": OM}, "massDefinition": "total-bound-subhalo", "densityFrame": "comoving", "population": "all"},
            "provenance": {"tier": "catalog-derived", "citation": "DARWIN-1 public galaxy/halo catalogues (DARWIN project, KASI; run described by Lee et al. 2026, arXiv:2610.25786); counts by this project", "doi": None, "url": PAGE, "retrieved": ens["retrieved"],
                           "sourceMember": f"Darwin1/{snap:04d}/catalog_{snap:04d}.hdf5 (sub/mstar, sub/nstar)", "checksumSha256": s["sha256"],
                           "extractionMethod": "scripts/ingest_darwin1_catalogue.py (HTTP range requests of the two arrays; counts on a fine grid in data/ensembles/darwin1-gsmf.json)"},
            "calibration": "prediction", "rankable": True,
            "notes": "Counted from the catalogue, not read from a figure. The paper's own mass function (Fig. 7, four redshifts) is in the dataset as digitized curves."})
    OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=2) + "\n")
    print(f"wrote {len(recs)} catalogue records to {OUT}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", action="store_true", help="offline: build the curve records from the saved counts")
    a = ap.parse_args()
    stage2() if a.records else stage1()
