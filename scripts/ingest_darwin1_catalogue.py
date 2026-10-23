"""The galaxy stellar mass function, the stellar-to-halo mass relation and the black hole mass relation of DARWIN-1 counted from the project's public galaxy/halo catalogues (https://darwin.kasi.re.kr/data_darwin1.html).
Galaxy stellar mass function (11 snapshots, z = 10 to 0.19): a galaxy is a self-bound substructure of the catalogue that has star particles (`sub/nstar` > 0), as defined in Lee et al. 2026 (arXiv:2610.25786); its stellar mass is the catalogue column `sub/mstar`, which the catalogue states in Msun/h (divided by h = 0.674 here). Only `sub/mstar` and `sub/nstar` are read, by HTTP range requests (about 4 MB per snapshot).
Stellar-to-halo mass relation and black hole mass relation (12 snapshots: the 11 and snapshot 164, z = 2.087, the nearest to the z = 2.1 of the paper's black hole figure), read from `halo/mtot`, `sub/halo_index`, `sub/mstar`, `sub/mtot`, `sub/nstar`, `sub/mMBH`, `sub/nMBH`:
 - halo mass is the Friends-of-Friends group mass `halo/mtot` (all particle species; the catalogue has no M200,c, which the paper uses); the central galaxy of a halo is its galaxy (substructure with star particles) of largest stellar mass (the catalogue has no central flag; the finder's own paper, Kim et al. 2023, classifies the most massive galaxy of each halo as the central); only halo-mass bins in which every FoF halo hosts a galaxy are used, so that no median is biased by empty halos;
 - black hole mass is `sub/mMBH`, the total mass of the black hole particles of the substructure, for every galaxy with 100 or more star particles and at least one black hole particle (`sub/nMBH` >= 1), centrals and satellites.
Not derivable from the catalogue: sizes (no radii among the columns), gas-phase or stellar metallicities (no abundances), see data/sources-catalogue.json.
Stage 1 (network, a few minutes): python3 scripts/ingest_darwin1_catalogue.py   writes data/ensembles/darwin1-gsmf.json (counts on a fine mass grid, what was read, and the comparison with the paper's Fig. 7)
Stage 1b (network, about 15 minutes): python3 scripts/ingest_darwin1_catalogue.py --relations [--source DIR]   writes data/ensembles/darwin1-shmr-bh.json (counts on two-dimensional grids, and the comparison with the paper's raster Figs. 10 and 11, DIR = the arXiv source of 2610.25786, fetched when not given)
Stage 2 (offline, run by verify-all.sh): python3 scripts/ingest_darwin1_catalogue.py --records   writes data/curves/darwin-catalogue.json (then node scripts/derive-distributions.mjs adds the medians and bands of the two-dimensional records)
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
sys.path.insert(0, str(HERE))
import distribution_stats as D  # noqa: E402
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
# stellar-to-halo mass relation and black hole mass relation: the same snapshots and snapshot 164 (z = 2.087, nearest to the z = 2.1 of the paper's Fig. 11)
ENS2 = ROOT / "data" / "ensembles" / "darwin1-shmr-bh.json"
SNAPS_REL = sorted(SNAPS + [(164, 2.086860, 2.1)], key=lambda t: t[1])
HALO_LO, HALO_STEP, HALO_N, HALO_COARSE = 6.0, 1 / 6, 54, 2  # log10(M_FoF/Msun) 6 to 15; 2 fine bins make one bin of 1/3 dex
MS_LO, MS_STEP, MS_N = 4.5, 0.05, 160  # log10(M*/Msun) of the central galaxy, 4.5 to 12.5
GX_LO, GX_STEP, GX_N, GX_COARSE = 6.0, 1 / 6, 40, 2  # log10(M*/Msun) of the galaxies of the black hole relation, 6 to 12.67
BH_LO, BH_STEP, BH_N = 4.5, 0.05, 120  # log10(M_BH/Msun), 4.5 to 10.5 (the seed mass is 5e4 Msun = 10^4.70)
FIG_SHMR = {"z3": 81, "z0.19": 1001}  # the two panels of the paper's Fig. 10
FIG_BH = {"z2.1": 164, "z0.19": 1001}  # the two panels of the paper's Fig. 11 (the upper one is labelled z = 2-3, the paper says DARWIN-1 is taken at z = 2.1)
ARXIV = "2610.25786"


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
    n_gsmf = len(recs)
    if ENS2.exists():
        ens2 = json.loads(ENS2.read_text())
        recs += shmr_records(ens2) + bh_records(ens2)
    OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=2) + "\n")
    print(f"wrote {len(recs)} catalogue records to {OUT} ({n_gsmf} mass functions, {len(recs) - n_gsmf} two-dimensional records of the halo-mass and black hole relations; derive-distributions.mjs adds their medians)")


def edges_of(lo, step, n):
    return [round(lo + step * i, 4) for i in range(n + 1)]


def read_rel(snap):
    import fsspec
    import h5py
    url = URL.format(s=snap)
    fs = fsspec.filesystem("http")
    info = fs.info(url)
    sha = hashlib.sha256()
    names = ("halo/mtot", "sub/halo_index", "sub/mstar", "sub/mtot", "sub/nstar", "sub/mMBH", "sub/nMBH")
    with fs.open(url, mode="rb", block_size=4 * 2 ** 20, cache_type="readahead") as f:
        with h5py.File(f, "r") as h:
            a = {k: h[k][()] for k in names}
    for k in names:
        sha.update(np.ascontiguousarray(a[k]).tobytes())
    hm, hi, ms, mt, ns, mb, nb = (a[k] for k in names)
    ms64, mt64 = ms.astype(np.float64), mt.astype(np.float64)
    gal = (ns > 0) & (ms > 0)

    def central(key):  # the galaxy of each halo with the largest `key`, ties to the lower index
        idx = np.nonzero(gal)[0]
        idx = idx[np.lexsort((idx, key[idx], hi[idx]))]
        last = np.ones(len(idx), bool)
        last[:-1] = hi[idx][1:] != hi[idx][:-1]
        return idx[last]
    cen, alt = central(ms64), central(mt64)  # the central is the galaxy of largest stellar mass; the alternative is the galaxy of largest total mass
    ok_h = hm > 0
    hlog = np.log10(hm[ok_h].astype(np.float64) / H)
    xe, ye = edges_of(HALO_LO, HALO_STEP, HALO_N), edges_of(MS_LO, MS_STEP, MS_N)
    hx, cy = np.log10(hm[hi[cen]].astype(np.float64) / H), np.log10(ms64[cen] / H)
    shmr = {"nHalos": int(ok_h.sum()), "nHalosWithGalaxy": int(len(cen)), "nOutsideGrid": int(((cy < ye[0]) | (cy >= ye[-1])).sum()),
            "halos": np.histogram(hlog, bins=xe)[0].astype(int).tolist(), "halosWithGalaxy": np.histogram(hx, bins=xe)[0].astype(int).tolist(), "counts": D.bin_counts(hx, cy, xe, ye).astype(int).tolist()}
    cnt_alt = D.bin_counts(np.log10(hm[hi[alt]].astype(np.float64) / H), np.log10(ms64[alt] / H), xe, ye)
    shmr["altCentral"] = {"definition": "the galaxy of largest total mass (sub/mtot) of the halo", "nHalosDiffering": int((cen != alt).sum()), **alt_difference(np.array(shmr["counts"]), cnt_alt)}
    gx_e, bh_e = edges_of(GX_LO, GX_STEP, GX_N), edges_of(BH_LO, BH_STEP, BH_N)
    xs = np.log10(ms64[gal] / H)
    has = gal & (nb >= 1) & (mb > 0)
    bx, by = np.log10(ms64[has] / H), np.log10(mb[has].astype(np.float64) / H)
    inx = (bx >= gx_e[0]) & (bx < gx_e[-1])
    one = gal & (nb == 1)
    bh = {"nGalaxies": int(gal.sum()), "nWithBH": int(has.sum()), "nWithOneBH": int(one.sum()), "nOutsideGrid": int((inx & ((by < bh_e[0]) | (by >= bh_e[-1]))).sum()), "nBelowGalaxyGrid": int((bx < gx_e[0]).sum()),
          "galaxies": np.histogram(xs, bins=gx_e)[0].astype(int).tolist(), "withBH": np.histogram(bx, bins=gx_e)[0].astype(int).tolist(), "withOneBH": np.histogram(np.log10(ms64[one] / H), bins=gx_e)[0].astype(int).tolist(),
          "bhParticles": np.histogram(bx, bins=gx_e, weights=nb[has].astype(np.float64))[0].round().astype(int).tolist(), "counts": D.bin_counts(bx, by, gx_e, bh_e).astype(int).tolist()}
    rec = {"snapshot": snap, "url": url, "contentLength": int(info.get("size") or 0), "etag": str(info.get("ETag") or info.get("etag") or ""), "nSubstructures": int(len(ms)), "sha256": sha.hexdigest(), "shmr": shmr, "bh": bh}
    gal_fig = {"A": (bx, by), "B": (np.log10(ms64[one] / H), np.log10(mb[one].astype(np.float64) / H))} if snap in FIG_BH.values() else None
    return rec, gal_fig


def coarse_2d(counts, coarse):
    c = np.asarray(counts)
    return c.reshape(-1, coarse, c.shape[1]).sum(axis=1)


def x_range_complete(halos, with_galaxy):
    """First coarse halo-mass bin from which every bin that holds halos has a galaxy in every halo (so that no median is biased by empty halos), the last bin that holds a halo, and the coarse counts of halos and of halos with a galaxy."""
    h, g = np.asarray(halos).reshape(-1, HALO_COARSE).sum(axis=1), np.asarray(with_galaxy).reshape(-1, HALO_COARSE).sum(axis=1)
    full = (h > 0) & (h == g)
    top = int(np.nonzero(h > 0)[0].max())
    k0 = top
    while k0 > 0 and (h[k0 - 1] == 0 or full[k0 - 1]):
        k0 -= 1
    while h[k0] == 0:
        k0 += 1
    return k0, top, h, g


def alt_difference(cnt, cnt_alt):
    """Largest difference of the median, and of the 16th and 84th percentiles, between two choices of central, over the coarse halo-mass bins that hold 10 or more centrals in both."""
    a, b = coarse_2d(cnt, HALO_COARSE), coarse_2d(cnt_alt, HALO_COARSE)
    d = {"xEdges": edges_of(HALO_LO, HALO_STEP * HALO_COARSE, a.shape[0]), "yEdges": edges_of(MS_LO, MS_STEP, MS_N), "thresholds": []}
    sa, sb = D.stats({**d, "counts": a.tolist()}), D.stats({**d, "counts": b.tolist()})
    diffs = [[abs(sa["quantiles"][k][i] - sb["quantiles"][k][i]) for k in (1, 2, 3)] for i in range(a.shape[0]) if sa["quantiles"][2][i] is not None and sb["quantiles"][2][i] is not None]
    return {"binsCompared": len(diffs), "maxAbsDiffMedianDex": round(max(x[1] for x in diffs), 4), "maxAbsDiff16and84Dex": round(max(max(x[0], x[2]) for x in diffs), 4)}


def shmr_curve_for_check(r):
    """The catalogue curve of one snapshot as the saved counts give it: bin centre, number of centrals, median, and whether every halo of the bin hosts a galaxy."""
    k0, top, h, g = x_range_complete(r["shmr"]["halos"], r["shmr"]["halosWithGalaxy"])
    c = coarse_2d(r["shmr"]["counts"], HALO_COARSE)
    st = D.stats({"xEdges": edges_of(HALO_LO, HALO_STEP * HALO_COARSE, c.shape[0]), "yEdges": edges_of(MS_LO, MS_STEP, MS_N), "counts": c.tolist(), "thresholds": []})
    return [(st["xCentres"][i], st["n"][i], st["quantiles"][2][i], bool(i >= k0)) for i in range(c.shape[0]) if st["quantiles"][2][i] is not None]


def trimmed(counts, k0, k1, x_lo, x_step, y_lo, y_step):
    """Counts of the coarse x bins k0 to k1 with the empty rows at both ends of the y axis dropped: (xEdges, yEdges, counts)."""
    c = np.asarray(counts)[k0:k1 + 1]
    rows = np.nonzero(c.sum(axis=0))[0]
    j0, j1 = int(rows.min()), int(rows.max())
    return edges_of(x_lo + k0 * x_step, x_step, k1 - k0 + 1), edges_of(y_lo + j0 * y_step, y_step, j1 - j0 + 1), c[:, j0:j1 + 1].astype(int).tolist()


def base_record(rid, relation, snap, z, zn, ens):
    return {"id": rid, "source": "DARWIN", "run": "DARWIN-1 (65.5 cMpc box)", "kind": "simulation", "relation": relation,
            "epoch": {"zRepresentative": round(z, 4), "zNominal": zn, "zMin": round(z, 4), "zMax": round(z, 4), "mode": "snapshot", "snapshot": snap},
            "calibration": "prediction", "rankable": True}


def provenance_of(snap, s, ens, members, what):
    return {"tier": "catalog-derived", "citation": "DARWIN-1 public galaxy/halo catalogues (DARWIN project, KASI; run described by Lee et al. 2026, arXiv:2610.25786); counts by this project", "doi": None, "url": PAGE, "retrieved": ens["retrieved"],
            "sourceMember": f"Darwin1/{snap:04d}/catalog_{snap:04d}.hdf5 ({members})", "checksumSha256": s["sha256"],
            "extractionMethod": f"scripts/ingest_darwin1_catalogue.py --relations (HTTP range requests of the arrays; counts on a two-dimensional grid in data/ensembles/darwin1-shmr-bh.json); {what}"}


def shmr_records(ens):
    recs = []
    chk = ens["figureCheck"]["shmr"]
    panel_of = {sn: k for k, sn in chk["snapshots"].items()}
    for snap, z, zn in SNAPS_REL:
        s = ens["snapshots"][str(snap)]
        r = s["shmr"]
        k0, top, h, g = x_range_complete(r["halos"], r["halosWithGalaxy"])
        c = coarse_2d(r["counts"], HALO_COARSE)
        if int((c[k0:top + 1].sum(axis=1) >= 10).sum()) < 3:
            continue
        xe, ye, counts = trimmed(c, k0, top, HALO_LO, HALO_STEP * HALO_COARSE, MS_LO, MS_STEP)
        nb = int((c[k0:top + 1].sum(axis=1) >= 10).sum())
        alt = r["altCentral"]
        cmp_note = ""
        if snap in panel_of.values():
            p = chk[panel_of[snap]]
            cmp_note = (f" Compared with the paper's Fig. 10, a raster image (its solid median line for the z = {zn:g} panel read on axes calibrated from the tick marks, at {p['binsCompleteCompared']} bin centres of this curve; internal check only): the paper's median stellar mass is higher than this curve's by "
                        f"{p['completeMin']:.2f} to {p['completeMax']:.2f} dex (median {p['completeMedian']:.2f}); the line is about 0.06 dex thick. The paper's halo mass is M200,c, and the same halos have a lower M200,c than FoF mass, which would lift a rising curve by about this much, but this cause was not tested (the catalogue has no M200,c).")
        rec = base_record(f"darwin1.catalogue.shmr.z{zn:g}", "shmr", snap, z, zn, ens)
        rec.update({
            "axes": {"xDefinition": "log10 mass of the Friends-of-Friends halo (all particles of the group: dark matter, gas, stars and black holes; adaptive linking length), not M200,c", "xUnit": "log10(Msun)", "yDefinition": "log10 stellar mass of the central galaxy (total mass of the star particles bound to it)", "yUnit": "log10(Msun)"},
            "domain": {"xMin": round(xe[0] + HALO_STEP, 4), "xMax": round(xe[-1] - HALO_STEP, 4)},
            "representation": {"type": "distribution", "xEdges": xe, "yEdges": ye, "counts": counts, "weighting": "number"},
            "scatter": {"unit": "dex", "meaning": "the 16th to 84th percentile of the central galaxies in each halo-mass bin"},
            "selection": {"population": "the central galaxy of every Friends-of-Friends halo, in the halo-mass bins in which every halo hosts a galaxy (at least 10 halos per bin)", "warning": (
                f"Counted by this project from the public DARWIN-1 catalogue of snapshot {snap} (z = {z:.3f}). Halo mass is the Friends-of-Friends group mass `halo/mtot` (all particle species of the group, Msun/h divided by h = 0.674), not the M200,c of the paper's Fig. 10: the catalogue has no M200,c, so this relation is not comparable with M200-based ones. "
                f"Stellar mass is the total stellar mass `sub/mstar` bound to the central galaxy. The catalogue has no central flag: the central is the galaxy (substructure with star particles) of largest stellar mass in the halo, as the finder's own paper (Kim et al. 2023, ApJ 951, 137) classifies the most massive galaxy of a halo as the central; Lee et al. 2026 say only 'the central galaxy, as identified by PGalF'. "
                f"Taking the galaxy of largest total mass instead changes the central of {alt['nHalosDiffering']} of {r['nHalosWithGalaxy']} halos with a galaxy and the bin medians by at most {alt['maxAbsDiffMedianDex']:.3f} dex. "
                f"Only bins of 1/3 dex from 10^{xe[0]:.2f} Msun upward, in which every halo hosts a galaxy (no selection on stellar mass), are kept: {nb} bins with 10 or more centrals, {int(c[k0:top + 1].sum())} centrals. Median and 16th to 84th percentile are taken from counts on a 0.05 dex grid of stellar mass. Cosmic variance of one box not included.{cmp_note}")},
            "definitions": {"imf": "kroupa01", "cosmology": {"H0": 67.4, "Om": OM}, "massDefinition": "total-bound-subhalo", "haloMassDefinition": "FoF-total-mass-all-species", "haloMassHistory": "current", "population": "central-galaxies", "galaxyType": "central"},
            "provenance": provenance_of(snap, s, ens, "halo/mtot, sub/halo_index, sub/mstar, sub/nstar", "central = largest stellar mass of the halo"),
            "notes": "Counted from the catalogue, not read from a figure. The paper's own relation (Fig. 10, M200,c on the x axis) is a raster image and is not in the dataset. Per-galaxy distribution: the median and 16 to 84 per cent band shown as a curve are derived from the counts (scripts/derive-distributions.mjs)."})
        recs.append(rec)
    return recs


def bh_records(ens):
    recs = []
    chk = ens["figureCheck"]["bh"]
    panel_of = {sn: k for k, sn in chk["snapshots"].items()}
    first = round((LOGM_MIN - GX_LO) / (GX_STEP * GX_COARSE))  # 10^7 Msun: 100 or more star particles (8.0e4 Msun each)
    for snap, z, zn in SNAPS_REL:
        s = ens["snapshots"][str(snap)]
        r = s["bh"]
        c = coarse_2d(r["counts"], GX_COARSE)
        n_x = c.sum(axis=1)
        if int((n_x[first:] >= 10).sum()) < 3:
            continue
        k1 = int(np.nonzero(n_x[first:] > 0)[0].max()) + first
        xe, ye, counts = trimmed(c, first, k1, GX_LO, GX_STEP * GX_COARSE, BH_LO, BH_STEP)
        nb = int((n_x[first:] >= 10).sum())
        gal = np.asarray(r["galaxies"]).reshape(-1, GX_COARSE).sum(axis=1); hosts = np.asarray(r["withBH"]).reshape(-1, GX_COARSE).sum(axis=1); one = np.asarray(r["withOneBH"]).reshape(-1, GX_COARSE).sum(axis=1); parts = np.asarray(r["bhParticles"]).reshape(-1, GX_COARSE).sum(axis=1)
        lo_sel, hi_sel, top_sel = slice(first, first + 3), slice(first + 7, None), slice(first + 9, None)  # 10^7 to 10^8, above 10^9.33, above 10^10
        f_lo = hosts[lo_sel].sum() / max(gal[lo_sel].sum(), 1); f_hi = hosts[hi_sel].sum() / max(gal[hi_sel].sum(), 1)
        multi_lo = 1 - one[lo_sel].sum() / max(hosts[lo_sel].sum(), 1); multi_top = 1 - one[top_sel].sum() / max(hosts[top_sel].sum(), 1); mean_top = parts[top_sel].sum() / max(hosts[top_sel].sum(), 1)
        cmp_note = ""
        if snap in panel_of.values():
            p = chk[panel_of[snap]]
            a, b = p["A"], p["B"]
            near = sum(1 for x in a["bins"] if x["maxAbsDiffAll"] <= 0.2)
            miss = b["binsWithPaperDotsButNoCatalogueDots"]
            only_one = (f" With only the galaxies that hold exactly one black hole particle, {len(miss)} bins have dots in the figure and no galaxy here (10^{min(miss):.1f} to 10^{max(miss):.1f} Msun), so the figure's population includes galaxies with several black hole particles; "
                        "whether the paper sums their masses or takes the most massive one is not stated, and the sum reproduces the figure.") if miss else ""
            cmp_note = (f" Compared with the paper's Fig. 11, a raster image, {'upper panel, labelled z = 2-3, for which the paper takes DARWIN-1 at z = 2.1' if zn == 2.1 else 'lower panel, z = 0.19'} (internal check only): the figure's grey DARWIN-1 dots and the same galaxies drawn as dots of the same size on the same calibrated axes, "
                        f"bins of 1/3 dex of stellar mass from 10^7 Msun ({a['binsCompared']} bins, pixels hidden under other symbols ignored in both): the 50th percentile of the dot pixels differs by {a['diff50Median']:+.2f} dex at the median over the bins, by at most {a['diff50Max']:.2f} dex, and all of the 5th, 25th, 50th, 75th and 95th percentiles agree within 0.2 dex in {near} of {a['binsCompared']} bins.{only_one}")
        rec = base_record(f"darwin1.catalogue.bh.z{zn:g}", "bh", snap, z, zn, ens)
        rec.update({
            "axes": {"xDefinition": "log10 stellar mass (total mass of the star particles of the self-bound substructure)", "xUnit": "log10(Msun)", "yDefinition": "log10 black hole mass of the galaxy (total mass of all black hole particles of the substructure)", "yUnit": "log10(Msun)"},
            "domain": {"xMin": round(xe[0] + GX_STEP, 4), "xMax": round(xe[-1] - GX_STEP, 4)},
            "representation": {"type": "distribution", "xEdges": xe, "yEdges": ye, "counts": counts, "weighting": "number"},
            "scatter": {"unit": "dex", "meaning": "the 16th to 84th percentile of the black hole masses of the galaxies in each stellar-mass bin"},
            "selection": {"population": "all galaxies with at least 100 star particles and at least one black hole particle, centrals and satellites", "warning": (
                f"Counted by this project from the public DARWIN-1 catalogue of snapshot {snap} (z = {z:.3f}). Population: every galaxy (self-bound substructure with at least 100 star particles, stellar mass `sub/mstar`) that holds at least one black hole particle (`sub/nMBH` >= 1), centrals and satellites alike (the catalogue has no flag for either); "
                f"{int(n_x[first:].sum())} galaxies. Galaxies without a black hole particle are not in the relation: {f_lo:.0%} of the galaxies of 10^7 to 10^8 Msun and {f_hi:.0%} of those above 10^9.3 Msun hold one, so this is the relation of black hole hosts, not of all galaxies. "
                f"Black hole mass is `sub/mMBH`, the total mass of all black hole particles of the substructure (Msun/h divided by h = 0.674): a galaxy with several black hole particles counts their sum ({multi_lo:.0%} of the hosts of 10^7 to 10^8 Msun and {multi_top:.0%} of those above 10^10 Msun have two or more, on average {mean_top:.1f} particles above 10^10 Msun). "
                f"The catalogue does not give the mass of the most massive particle alone; it lies between the sum divided by the number of particles and the sum. Black holes are seeded at 5e4 Msun (Lee et al. 2026), so the median is close to the seed mass (10^4.70 Msun) at the lowest stellar masses. Median and 16th to 84th percentile are taken from counts on a 0.05 dex grid of black hole mass. Cosmic variance of one box not included.{cmp_note}")},
            "definitions": {"imf": "kroupa01", "cosmology": {"H0": 67.4, "Om": OM}, "massDefinition": "total-bound-subhalo", "bhMassMethod": "intrinsic-sum-of-bh-particles", "population": "bh-hosts"},
            "provenance": provenance_of(snap, s, ens, "sub/mstar, sub/nstar, sub/mMBH, sub/nMBH", "black hole mass = sum over the black hole particles of the substructure"),
            "notes": "Counted from the catalogue, not read from a figure. The paper's own relation (Fig. 11) is a raster image and is not in the dataset. Per-galaxy distribution: the median and 16 to 84 per cent band shown as a curve are derived from the counts (scripts/derive-distributions.mjs)."})
        recs.append(rec)
    return recs


def stage1b(source):
    import darwin_raster_check as R
    if source is None:
        import vector_figure as vf
        source = vf.fetch_arxiv(ARXIV)
    figs = {n: Path(source) / "figures" / n for n in ("mstar_mhalo.png", "mbh_mstar.png")}
    with ThreadPoolExecutor(max_workers=4) as pool:
        got = list(pool.map(read_rel, [s for s, _, _ in SNAPS_REL]))
    snaps = {str(g[0]["snapshot"]): {**g[0], "z": z, "zNominal": zn} for g, (_, z, zn) in zip(got, SNAPS_REL)}
    fig_gal = {str(g[0]["snapshot"]): g[1] for g in got if g[1] is not None}
    curves = {k: shmr_curve_for_check(snaps[str(sn)]) for k, sn in FIG_SHMR.items()}
    bh_edges = 7.0 + np.arange(17) / 3  # bins of 1/3 dex in stellar mass, 10^7 to 10^12.33, for the comparison with Fig. 11
    check = {"figures": {n: {"sha256": R.sha256(p), "source": f"arXiv:{ARXIV} source, figures/{n}"} for n, p in figs.items()},
             "shmr": {"snapshots": FIG_SHMR, **R.check_shmr(figs["mstar_mhalo.png"], curves)},
             "bh": {"snapshots": FIG_BH, **R.check_bh(figs["mbh_mstar.png"], {k: fig_gal[str(sn)] for k, sn in FIG_BH.items()}, bh_edges)}}
    ens = {"schemaVersion": "1.0.0", "source": "DARWIN-1 public galaxy/halo catalogues (DARWIN project, KASI), " + PAGE, "retrieved": date.today().isoformat(), "h": H, "Om": OM, "boxCMpc": BOX_CMPC,
           "grids": {"haloLogMin": HALO_LO, "haloStep": HALO_STEP, "haloN": HALO_N, "mstarLogMin": MS_LO, "mstarStep": MS_STEP, "mstarN": MS_N, "galaxyLogMin": GX_LO, "galaxyStep": GX_STEP, "galaxyN": GX_N, "bhLogMin": BH_LO, "bhStep": BH_STEP, "bhN": BH_N},
           "snapshots": snaps, "figureCheck": check}
    ENS2.write_text(json.dumps(ens, separators=(",", ":")) + "\n")
    for k in FIG_SHMR:
        v = check["shmr"][k]
        print(f"Fig. 10 panel {k}: {v['binsCompared']} bins, paper median line minus catalogue median {v['paperMinusCatalogueMin']} to {v['paperMinusCatalogueMax']} dex (median {v['paperMinusCatalogueMedian']})")
    for k in FIG_BH:
        for sc, r in check["bh"][k].items():
            print(f"Fig. 11 panel {k}, scenario {sc}: {r['binsCompared']} bins, median difference of the 50th percentile {r['diff50Median']} dex, {r['diff50WithinHalfDex']} within 0.1 dex, largest {r['diff50Max']}; bins with dots in the paper and none here: {r['binsWithPaperDotsButNoCatalogueDots']}")
    print(f"wrote {ENS2}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", action="store_true", help="offline: build the curve records from the saved counts")
    ap.add_argument("--relations", action="store_true", help="network: count the stellar-to-halo mass relation and the black hole mass relation (stage 1b)")
    ap.add_argument("--source", help="stage 1b: directory of the arXiv source of 2610.25786 (with figures/mstar_mhalo.png and figures/mbh_mstar.png); fetched when not given")
    a = ap.parse_args()
    stage2() if a.records else stage1b(a.source) if a.relations else stage1()
