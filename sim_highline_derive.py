"""Derive the standard scaling relations from a simulation catalogue, with the definitions the dataset uses.

The library behind `sim-highline derive` and the four scripts in scripts/ (derive_subfind_relations.py, derive_caesar_relations.py,
derive_soap_relations.py, derive_eagle_relations.py, which are thin wrappers around the functions here):

    import sim_highline_derive as sd
    payload = sd.derive_run("subfind", ["groups_099/"], source="MySim", run="L50", imf="chabrier03", baryon_particle_mass=1.4e6)
    # raises sd.UnderSpecified (a ValueError) listing every definition it cannot know; never fills one in

The cuts are the same for every run and format: galaxies with at least 100 baryon particle masses of stars, bins of 0.2 dex, at least 10 galaxies
for a median, comoving volumes for number densities. Reading catalogues needs h5py (pip install "sim-highline[derive]").
"""
import glob
import hashlib
import json
import math
import re
from datetime import date
from pathlib import Path

import numpy as np

DM = 0.2
MIN_STAR_PARTICLES, MIN_PER_BIN = 100, 10
MSUN_G, KPC_CM, YR_S = 1.98847e33, 3.0856775814913673e21, 3.15576e7
SCHEMA_VERSION = "1.0.0"

# --- per-galaxy distributions: counts on a grid (mirrors distributionStats in compare.js step for step; tests/fixtures/distribution-fixture.json is evaluated by both) ---
LEVELS = (0.05, 0.16, 0.5, 0.84, 0.95)
MIN_COUNT = 10


def _r6(v):
    return None if v is None else round(float(v) * 1e6) / 1e6


def dist_quantile(row, edges, total, q):
    target = q * total
    cum = 0.0
    for j, c in enumerate(row):
        if c > 0 and cum + c >= target:
            t = (target - cum) / c
            return edges[j] + min(1.0, max(0.0, t)) * (edges[j + 1] - edges[j])
        cum += c
    return edges[-1]


def dist_fraction_below(row, edges, total, thr):
    cum = 0.0
    for j, c in enumerate(row):
        if edges[j + 1] <= thr:
            cum += c
            continue
        if edges[j] < thr:
            cum += c * (thr - edges[j]) / (edges[j + 1] - edges[j])
        break
    return cum / total


def dist_stats(d, levels=LEVELS, min_count=MIN_COUNT):
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
            out["quantiles"][k].append(_r6(dist_quantile(row, ye, tot, q)))
        fb = [dist_fraction_below(row, ye, tot, t) for t in thr]
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


# --- the shared core: per-galaxy arrays in, records out ---
def _h5py():
    try:
        import h5py
    except ImportError as e:
        raise SystemExit('reading HDF5 catalogues needs h5py: pip install "sim-highline[derive]"') from e
    return h5py


def update_digest(digest, path):
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            digest.update(chunk)


def binned_median(x, y, edges, min_count=MIN_PER_BIN):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (x >= lo) & (x < hi) & np.isfinite(y)
        n = int(sel.sum())
        if n < min_count:
            continue
        p16, p50, p84 = np.percentile(y[sel], [16, 50, 84])
        out.append({"x": round((lo + hi) / 2, 3), "y": round(float(p50), 4), "yLow": round(float(p16), 4), "yHigh": round(float(p84), 4), "count": n})
    return out


def age_gyr(z, h, om):
    ol, th = 1 - om, 977.8 / (100 * h)
    return 2 * th / (3 * np.sqrt(ol)) * np.arcsinh(np.sqrt(ol / om) / (1 + z) ** 1.5)


def distribution_record_form(rep):
    """A distribution representation in the stored form (points = median and 16 to 84 per cent band of each mass bin, plus the grid and its summary), as scripts/derive-distributions.mjs writes it."""
    d = {"xEdges": rep["xEdges"], "yEdges": rep["yEdges"], "counts": rep["counts"], "weighting": rep.get("weighting", "number")}
    for k in ("thresholds", "clipped"):
        if rep.get(k):
            d[k] = rep[k]
    stats = dist_stats(d)
    k16, k50, k84 = (stats["levels"].index(q) for q in (0.16, 0.5, 0.84))
    pts = [{"x": stats["xCentres"][i], "y": stats["quantiles"][k50][i], "yLow": stats["quantiles"][k16][i], "yHigh": stats["quantiles"][k84][i], "count": stats["n"][i]}
           for i in range(len(stats["n"])) if stats["quantiles"][k50][i] is not None]
    return {"type": "points", "connect": True, "intervalKind": "scatter", "points": pts, "distribution": {**d, "summary": stats}}


def relations_from_arrays(spec, A):
    records, z, z_nominal, snap = [], spec["z"], spec["z_nominal"], spec["snap"]
    logm, sfr, resolved, central, box = A["logm"], A["sfr"], A["resolved"], A["central"], spec["box"]
    mstar = 10 ** np.where(np.isfinite(logm), logm, -np.inf)
    ssfr = np.where(mstar > 0, sfr / np.where(mstar > 0, mstar, 1), 0)
    sf_cut = 0.2 / (age_gyr(z, spec["h"], spec["Om"]) * 1e9)
    star_forming = resolved & (ssfr > sf_cut)
    common = {"massDefinition": spec["massDefinition"], "imf": spec.get("imf", "chabrier03"), "cosmology": {"H0": round(100 * spec["h"], 2), "Om": spec["Om"]}}
    edges = np.arange(7.0, 12.6, DM)
    prov, warn = spec["provenance"], spec["warning"]
    id_prefix = spec.get("idPrefix") or f"derived.{spec['source'].lower().replace(' ', '-')}.{spec['run'].lower().replace(' ', '-')}"

    def rec(relation, suffix, points, interval, ydef, yunit, xdef, defs, population, extra="", representation=None, run=None):
        if representation is None and len(points) < 2:
            return
        if representation is not None and spec.get("storedDistribution"):
            representation = distribution_record_form(representation)
            if len(representation["points"]) < 2:
                return
            points, interval = representation["points"], "scatter"
        records.append({
            "id": f"{id_prefix}.{relation}.{suffix}.z{z_nominal:g}", "source": spec["source"], "run": run or spec["run"], "kind": "simulation", "relation": relation,
            "epoch": {"zRepresentative": round(z, 4), "zNominal": z_nominal, "zMin": round(z, 4), "zMax": round(z, 4), "mode": "snapshot", "snapshot": snap},
            "axes": {"xDefinition": xdef, "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": yunit},
            "domain": {"xMin": representation["xEdges"][0], "xMax": representation["xEdges"][-1]} if representation and representation["type"] == "distribution" else {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
            "representation": representation or {"type": "points", "intervalKind": interval, "connect": True, "points": points},
            "scatter": {"lower": "16th percentile", "upper": "84th percentile"} if interval == "scatter" else None,
            "selection": {"population": population, "warning": (warn + " " + extra).strip()},
            "definitions": {**common, **defs, "population": defs.get("population", population)},
            "provenance": prov, "calibration": "target" if relation in spec.get("calibratedAtLowZ", ()) and z < 0.2 else spec.get("calibrationDefault", "prediction"), "rankable": True,
            "notes": spec.get("notes", "Uniform-definition re-derivation; identical cuts are applied to every run and snapshot processed by this script.")})

    sel = resolved & np.isfinite(logm)
    counts, _ = np.histogram(logm[sel], bins=edges)
    gsmf = []
    for lo, n in zip(edges[:-1], counts):
        if n < 1:
            continue
        phi = n / box**3 / DM
        gsmf.append({"x": round(lo + DM / 2, 3), "y": round(float(np.log10(phi)), 4), "yLow": round(float(np.log10(max(n - np.sqrt(n), 0.5) / box**3 / DM)), 4),
                     "yHigh": round(float(np.log10((n + np.sqrt(n)) / box**3 / DM)), 4), "count": int(n)})
    rec("gsmf", "all", gsmf, "uncertainty", "log10 galaxy number density per dex (Poisson errors)", "log10(cMpc^-3 dex^-1)", "log10 stellar mass",
        {"densityFrame": "comoving"}, "all", "Poisson errors only; cosmic variance of the box not included.")
    sf = star_forming & (sfr > 0)
    rec("sfms", "sf", binned_median(logm[sf], np.log10(np.where(sf, sfr, np.nan)[sf]), edges), "scatter", "log10 instantaneous SFR, median of star-forming galaxies", "log10(Msun/yr)",
        "log10 stellar mass", {"sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median"}, "star-forming", f"Star-forming: sSFR > 0.2/t_age(z) = {sf_cut:.3g} /yr.")
    rec("ssfr", "all", binned_median(logm[sel], np.log10(np.maximum(ssfr[sel], 1e-14)), edges), "scatter", "log10 specific SFR, median of all galaxies (floored at 1e-14 /yr)", "log10(yr^-1)",
        "log10 stellar mass", {"sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median"}, "all")
    # the whole distribution, not only its median: counts of galaxies on a stellar-mass by sSFR grid (zero or very low sSFR in the lowest row), from which the quenched share, the green valley and the peaks follow
    if spec.get("distribution", True):
        xe, ye = [round(float(v), 3) for v in np.arange(8.0, 12.5001, 0.25)], [round(float(v), 3) for v in np.arange(-13.5, -8.4999, 0.1)]
        ly = np.where(ssfr > 0, np.log10(np.where(ssfr > 0, ssfr, 1.0)), -99.0)
        counts = bin_counts(logm[sel], ly[sel], xe, ye)
        if counts.sum() >= 10:
            rec("ssfr", "dist", [], "scatter", "log10 specific SFR of all galaxies; zero or lower values are in the lowest bin", "log10(yr^-1)", "log10 stellar mass",
                {"sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median"}, "all", "Per-galaxy distribution: counts on a grid; the curve is derived from them.",
                representation={"type": "distribution", "xEdges": xe, "yEdges": ye, "counts": counts.astype(int).tolist(), "weighting": "number", "clipped": {"low": True, "high": True}, "thresholds": [-11.0, -10.5]},
                run=spec.get("distributionRun"))
    fq = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = sel & (logm >= lo) & (logm < hi)
        n = int(m.sum())
        if n >= MIN_PER_BIN:
            f = float(np.mean(ssfr[m] < 1e-11))
            err = np.sqrt(max(f * (1 - f), 1 / n) / n)
            fq.append({"x": round((lo + hi) / 2, 3), "y": round(f, 4), "yLow": round(max(f - err, 0), 4), "yHigh": round(min(f + err, 1), 4), "count": n})
    rec("quenched", "ssfr1e-11", fq, "uncertainty", "fraction of galaxies with sSFR < 1e-11 /yr (binomial errors)", "fraction", "log10 stellar mass",
        {"quenchingCriterion": "ssfr<1e-11"}, "all")
    rh = A.get("rhalf_kpc")
    if rh is not None:
        rec("size", "all", binned_median(logm[sel], np.log10(np.where(rh > 0, rh, np.nan))[sel], edges), "scatter", "log10 3D stellar half-mass radius", "log10(kpc)",
            "log10 stellar mass", {"sizeDefinition": spec["sizeDefinition"]}, "all")
    cen = sel & central
    mh = A["logmh"]
    rec("shmr", "centrals", binned_median(mh[cen], (logm - mh)[cen], np.arange(10.0, 15.2, DM)), "scatter", "log10 stellar-to-halo mass ratio of centrals", "dex", "log10 halo mass M200crit",
        {"haloMassDefinition": {"m200c": "M200crit", "m200": "M200crit"}.get(spec.get("halo", "m200c"), "M200crit"), "haloMassHistory": "current"}, "centrals")
    bh = A.get("mbh")
    if bh is not None:
        cb = cen & (bh > 0)
        rec("bh", "centrals", binned_median(logm[cb], np.log10(np.where(cb, bh, np.nan))[cb], edges), "scatter", "log10 black-hole mass, median of centrals", "log10(Msun)",
            "log10 stellar mass", {"bhMassMethod": "intrinsic"}, "centrals")
    for key, rel in (("mHI", "hi-fraction"), ("mH2", "h2-fraction")):
        mg = A.get(key)
        if mg is not None:
            frac = np.log10(np.maximum(mg, 0) / np.where(mstar > 0, mstar, np.nan))
            rec(rel, "all", binned_median(logm[sel], np.where(np.isfinite(frac), frac, -4.0)[sel], edges), "scatter",
                f"log10 median {key[1:]}-to-stellar mass ratio (galaxies without {key[1:]} floored at -4)", "dex", "log10 stellar mass",
                {"gasDefinition": key[1:], "gasStatistic": "median-of-log"}, "all")
    zs = A.get("zstar_solar")
    if zs is not None:
        ok = sel & (zs > 0)
        rec("zstar", "all", binned_median(logm[ok], np.log10(np.where(ok, zs, np.nan))[ok], edges), "scatter", "log10 mass-weighted stellar metallicity / Zsun (Zsun = 0.0127)", "dex", "log10 stellar mass",
            {"metallicityQuantity": "stellar-Z", "metallicityCalibration": "intrinsic mass-weighted (Zsun=0.0127)"}, "all")
    oh = A.get("oh")
    if oh is not None:
        ok = sf & np.isfinite(oh)
        rec("mzr", "sf", binned_median(logm[ok], oh[ok], edges), "scatter", f"12+log(O/H), {spec['metallicityNote']}", "dex", "log10 stellar mass",
            {"metallicityQuantity": "gas-O/H", "metallicityCalibration": "intrinsic-simulation (SFR-weighted)"}, "star-forming")
    return records


# --- Subfind group catalogues (Illustris, IllustrisTNG, CAMELS) ---
RUNS = {
    "TNG50-1": {"source": "IllustrisTNG", "run": "TNG50", "box_ckpc_h": 35000.0, "mbar": 8.5e4, "h": 0.6774, "Om": 0.3089, "url": "https://www.tng-project.org/data/", "calibrated": ("gsmf", "shmr", "bh", "size")},
    "TNG100-1": {"source": "IllustrisTNG", "run": "TNG100", "box_ckpc_h": 75000.0, "mbar": 1.4e6, "h": 0.6774, "Om": 0.3089, "url": "https://www.tng-project.org/data/", "calibrated": ("gsmf", "shmr", "bh", "size")},
    "TNG300-1": {"source": "IllustrisTNG", "run": "TNG300", "box_ckpc_h": 205000.0, "mbar": 1.1e7, "h": 0.6774, "Om": 0.3089, "url": "https://www.tng-project.org/data/", "calibrated": ("gsmf", "shmr", "bh", "size")},
    "Illustris-1": {"source": "Illustris", "run": "Illustris-1", "mbar": 1.26e6, "h": 0.704, "Om": 0.2726, "url": "https://www.illustris-project.org/data/", "calibrated": ("gsmf",)},
}
SNAPS_TNG = {99: 0.0, 91: 0.1, 84: 0.2, 67: 0.5, 50: 1.0, 40: 1.5, 33: 2.0, 25: 3.0, 21: 4.0, 17: 5.0, 13: 6.0, 11: 7.0, 8: 8.0}
FIELDS = ["SubhaloFlag", "SubhaloMassInRadType", "SubhaloSFRinRad", "SubhaloHalfmassRadType", "SubhaloBHMass", "SubhaloGasMetalFractionsSfrWeighted", "SubhaloGrNr", "SubhaloStarMetallicity"]
GROUP_FIELDS = ["GroupFirstSub", "Group_M_Crit200"]


def load_field_files(groupdir, snap):
    h5py = _h5py()
    found = sorted(Path(groupdir).glob(f"fof_subhalo_tab_{snap:03d}.*.*.hdf5"))
    if not found:
        return None
    cat, digest = {}, hashlib.sha256()
    for name in found:
        kind, field = name.name.split(".")[1:3]
        if field not in FIELDS + GROUP_FIELDS:
            continue
        with h5py.File(name, "r") as f:
            cat[field] = f[kind][field][()]
        update_digest(digest, name)
    missing = [k for k in FIELDS + GROUP_FIELDS if k not in cat]
    if missing:
        raise SystemExit(f"{groupdir}: field files missing {missing}")
    return {}, cat, digest.hexdigest(), len(found)


def subfind_files(groupdir, snap):
    """The files of one snapshot's group catalogue, in chunk order (empty list when there are none)."""
    files = []
    for pattern in (f"fof_subhalo_tab_{snap:03d}.*.hdf5", f"groups_{snap:03d}.*.hdf5", f"groups_{snap:03d}.hdf5", f"fof_subhalo_tab_{snap:03d}.hdf5"):
        files = sorted((f for f in glob.glob(str(Path(groupdir) / pattern)) if "*" not in pattern or f.split(".")[-2].isdigit()), key=lambda f: int(f.split(".")[-2]) if f.split(".")[-2].isdigit() else 0)
        if files:
            break
    return files


def load(groupdir, snap):
    h5py = _h5py()
    files = subfind_files(groupdir, snap)
    if not files:
        return None
    sub, grp, digest = {k: [] for k in FIELDS}, {k: [] for k in GROUP_FIELDS}, hashlib.sha256()
    with h5py.File(files[0], "r") as f:
        header = dict(f["Header"].attrs)
    for name in files:
        with h5py.File(name, "r") as f:
            update_digest(digest, name)
            for k in FIELDS:
                if "Subhalo" in f and k in f["Subhalo"]:
                    sub[k].append(f["Subhalo"][k][()])
            for k in GROUP_FIELDS:
                if "Group" in f and k in f["Group"]:
                    grp[k].append(f["Group"][k][()])
    cat = {k: np.concatenate(v) for k, v in sub.items() if v}
    cat.update({k: np.concatenate(v) for k, v in grp.items() if v})
    return header, cat, digest.hexdigest(), len(files)


def subfind_arrays(cat, h, a, mbar):
    """Per-galaxy arrays from Subfind fields in the Illustris/TNG convention (masses 1e10 Msun/h, comoving lengths kpc/h). Fields a catalogue lacks are left out and their relations are not derived."""
    mstar = cat["SubhaloMassInRadType"][:, 4] * 1e10 / h
    flag = cat.get("SubhaloFlag", np.ones_like(mstar, dtype=int)).astype(bool)
    logm = np.log10(np.where(mstar > 0, mstar, np.nan))
    central = np.zeros(len(mstar), dtype=bool)
    first = cat["GroupFirstSub"]
    central[first[first >= 0]] = True
    m200 = cat["Group_M_Crit200"] * 1e10 / h
    arrays = {"logm": logm, "sfr": cat["SubhaloSFRinRad"], "resolved": flag & (mstar >= MIN_STAR_PARTICLES * mbar), "central": central,
              "logmh": np.log10(np.where(m200[cat["SubhaloGrNr"]] > 0, m200[cat["SubhaloGrNr"]], np.nan))}
    if "SubhaloHalfmassRadType" in cat:
        arrays["rhalf_kpc"] = cat["SubhaloHalfmassRadType"][:, 4] * a / h
    if "SubhaloBHMass" in cat:
        arrays["mbh"] = cat["SubhaloBHMass"] * 1e10 / h
    if "SubhaloStarMetallicity" in cat:
        arrays["zstar_solar"] = cat["SubhaloStarMetallicity"] / 0.0127
    if "SubhaloGasMetalFractionsSfrWeighted" in cat:
        mf = cat["SubhaloGasMetalFractionsSfrWeighted"]
        ok_oh = (mf[:, 0] > 0) & (mf[:, 4] > 0)
        arrays["oh"] = 12 + np.log10(np.where(ok_oh, (mf[:, 4] / 16.0) / np.where(ok_oh, mf[:, 0], 1), np.nan))
    return arrays


def derive(label, groupdir, snaps, retrieved):
    meta, records = RUNS[label], []
    h = meta["h"]
    for snap, z_nominal in snaps.items():
        loaded = load(groupdir, snap) or load_field_files(groupdir, snap)
        if loaded is None:
            continue
        header, cat, digest, nfiles = loaded
        if "Redshift" not in header:
            if snap not in SNAPS_TNG or "box_ckpc_h" not in meta:
                raise SystemExit(f"{label} snap {snap}: field files carry no header; redshift and box size unknown")
            header = {"Redshift": SNAPS_TNG[snap], "Time": 1 / (1 + SNAPS_TNG[snap]), "BoxSize": meta["box_ckpc_h"]}
        z, a = float(header["Redshift"]), float(header["Time"])
        z_nominal = round(z, 2) if z_nominal is None else z_nominal
        box = float(header.get("BoxSize", 0)) / 1000 / h
        if box <= 0:
            raise SystemExit(f"{label} snap {snap}: BoxSize missing from group catalog header")
        arrays = subfind_arrays(cat, h, a, meta["mbar"])
        spec = {"source": meta["source"], "run": meta["run"], "h": h, "Om": meta["Om"], "box": box, "snap": snap, "z": z, "z_nominal": z_nominal,
                "massDefinition": "aperture-2x-stellar-half-mass-radius", "sizeDefinition": "stellar-half-mass-3d-bound",
                "provenance": {"tier": "catalog-derived", "citation": f"{label} Subfind group catalog, snapshot {snap} (Nelson et al. 2019 public data release); relations derived by sim-highline",
                               "doi": None, "url": meta["url"], "retrieved": retrieved, "sourceMember": f"{Path(groupdir).name}/fof_subhalo_tab_{snap:03d}.*.hdf5 ({nfiles} files)", "checksumSha256": digest},
                "warning": (f"Derived by scripts/derive_subfind_relations.py from the public group catalog. Galaxies: SubhaloFlag=1, M* >= {MIN_STAR_PARTICLES} baryon particle masses "
                            f"({MIN_STAR_PARTICLES * meta['mbar']:.2g} Msun); stellar mass and SFR within twice the stellar half-mass radius; bins of {DM} dex with >= {MIN_PER_BIN} galaxies for medians."),
                "metallicityNote": "SFR-weighted, within twice the stellar half-mass radius", "calibratedAtLowZ": meta["calibrated"]}
        records += relations_from_arrays(spec, arrays)
    return records


# --- CAESAR catalogues (SIMBA and other CAESAR-processed runs) ---
CAESAR_RUNS = {"m100n1024": 1.82e7, "m50n512": 1.82e7, "m25n512": 2.28e6}
CAESAR_HALO_MASS_KEYS = ("dicts/masses.m200c", "dicts/virial_quantities.m200c", "dicts/masses.m200")
LENGTH = {"kpc": 1.0, "Mpc": 1e3}


def to_physical(ds, a, h, kind):
    unit = ds.attrs.get("unit", b"").decode() if isinstance(ds.attrs.get("unit", b""), bytes) else str(ds.attrs.get("unit", ""))
    values = ds[()].astype(float)
    u = unit.replace(" ", "")
    if kind == "mass":
        if u in ("Msun", "Msun/h"):
            return values / (h if u.endswith("/h") else 1)
    if kind == "sfr":
        if u in ("Msun/yr",):
            return values
    if kind == "length":
        for base, factor in LENGTH.items():
            for suffix, scale in (("", 1.0), ("cm", a), ("/h", 1 / h), ("cm/h", a / h)):
                if u == base + suffix:
                    return values * factor * scale
    raise SystemExit(f"{ds.name}: unit '{unit}' not recognised for {kind}; refusing to guess")


def caesar_read(path, mbar, halo_keys=CAESAR_HALO_MASS_KEYS, h=None):
    """What a CAESAR catalogue holds: redshift, h, Omega_m (None when the file has none), box in comoving kpc, the per-galaxy arrays and the halo-mass key used.
    `h` overrides the file's hubble_constant when given (the units in the file are converted with that value)."""
    h5py = _h5py()
    digest = hashlib.sha256()
    update_digest(digest, path)
    with h5py.File(path, "r") as f:
        sa = f["simulation_attributes"].attrs
        z = float(sa["redshift"])
        h = float(sa["hubble_constant"]) if h is None else h
        a = 1 / (1 + z)
        om = float(sa["omega_matter"]) if "omega_matter" in sa else None
        box_units = sa["boxsize_units"].decode() if isinstance(sa["boxsize_units"], bytes) else str(sa["boxsize_units"])
        box_kpc = float(np.atleast_1d(sa["boxsize"])[0]) * {"kpccm": 1, "kpccm/h": 1 / h, "kpc": 1 / a, "Mpccm": 1e3, "Mpccm/h": 1e3 / h}.get(box_units.replace(" ", ""), np.nan)
        if not np.isfinite(box_kpc):
            raise SystemExit(f"{path}: box units '{box_units}' not recognised")
        gal, halo = f["galaxy_data"], f["halo_data"]
        mstar = to_physical(gal["dicts/masses.stellar"], a, h, "mass")
        sfr = to_physical(gal["sfr"], a, h, "sfr")
        central = gal["central"][()].astype(bool)
        hkey = next((k for k in halo_keys if k in halo), None)
        if hkey is None:
            raise SystemExit(f"{path}: none of {halo_keys} in halo_data; available: {sorted(halo['dicts'].keys())[:40]}")
        mhalo = to_physical(halo[hkey], a, h, "mass")[gal["parent_halo_index"][()]]
        arrays = {"logm": np.log10(np.where(mstar > 0, mstar, np.nan)), "sfr": sfr, "resolved": mstar >= MIN_STAR_PARTICLES * mbar, "central": central,
                  "logmh": np.log10(np.where(central & (mhalo > 0), mhalo, np.nan))}
        if "dicts/radii.stellar_half_mass" in gal:
            arrays["rhalf_kpc"] = to_physical(gal["dicts/radii.stellar_half_mass"], a, h, "length")
        if "dicts/masses.bh" in gal:
            arrays["mbh"] = to_physical(gal["dicts/masses.bh"], a, h, "mass")
        for key in ("HI", "H2"):
            if f"dicts/masses.{key}" in gal:
                arrays[f"m{key}"] = to_physical(gal[f"dicts/masses.{key}"], a, h, "mass")
    return {"z": z, "h": h, "Om": om, "box_kpc": box_kpc, "arrays": arrays, "hkey": hkey, "digest": digest.hexdigest()}


def caesar_records(run, paths, source, mbar, retrieved=None):
    records = []
    for path in paths:
        c = caesar_read(path, mbar)
        spec = {"source": source, "run": run, "h": c["h"], "Om": 0.3 if c["Om"] is None else c["Om"], "box": c["box_kpc"] / 1e3, "snap": None, "z": c["z"], "z_nominal": round(c["z"], 2),
                "massDefinition": "caesar-6dfof-galaxy-total", "sizeDefinition": "stellar-half-mass-3d-bound", "halo": c["hkey"].split("/")[-1],
                "provenance": {"tier": "catalog-derived", "citation": f"{source} {run} CAESAR catalogue {Path(path).name}; relations derived by sim-highline", "doi": None,
                               "url": "https://simba.roe.ac.uk/", "retrieved": retrieved or date.today().isoformat(), "sourceMember": Path(path).name,
                               "checksumSha256": c["digest"]},
                "warning": (f"Derived by scripts/derive_caesar_relations.py with the same cuts as the other pipelines (M* >= {MIN_STAR_PARTICLES} gas particle masses, {DM} dex bins, "
                            f">= {MIN_PER_BIN} per median). CAESAR stellar masses are totals of 6D-FOF galaxy members, not apertures; units read from each dataset's 'unit' attribute."),
                "metallicityNote": "", "calibratedAtLowZ": ("gsmf",)}
        records += relations_from_arrays(spec, c["arrays"])
    return records


# --- SWIFT/SOAP halo catalogues (FLAMINGO, COLIBRE) ---
SOAP_SUITES = {
    "flamingo": {"source": "FLAMINGO", "url": "https://flamingo.strw.leidenuniv.nl/", "citation": "FLAMINGO data release (Helly et al. 2026), SOAP halo catalogue",
                 "calibrated": ("gsmf",), "h": 0.681, "Om": 0.306},
    "colibre": {"source": "COLIBRE", "url": "https://colibre-simulations.org/", "citation": "COLIBRE SOAP halo catalogue", "calibrated": ("gsmf", "size", "bh"), "h": 0.681, "Om": 0.306},
}


def soap_physical(f, path, factor):
    d = f[path]
    conv = d.attrs.get("Conversion factor to physical CGS (including cosmological corrections)")
    if conv is None:
        raise SystemExit(f"{path}: missing CGS conversion attribute; refusing to guess units")
    return d[()].astype(float) * float(np.atleast_1d(conv)[0]) / factor


def _first(f, *paths):
    for p in paths:
        if p in f:
            return p
    return None


def soap_read(path, aperture, mbar, box_mpc=None):
    """What a SOAP halo catalogue holds: redshift, box (comoving Mpc), the per-galaxy arrays in physical units from the file's own CGS conversion attributes,
    and the h and Omega_m of its Cosmology group (None when the file has none). `box_mpc` states the box when the header's number is not plausibly Mpc."""
    h5py = _h5py()
    sha = hashlib.sha256()
    update_digest(sha, path)
    with h5py.File(path, "r") as f:
        header = dict(f["Header"].attrs)
        z = float(np.atleast_1d(header["Redshift"])[0])
        box = float(np.atleast_1d(header["BoxSize"])[0]) if box_mpc is None else float(box_mpc)
        if box_mpc is None and not 10 < box < 5000:
            raise SystemExit(f"{path}: BoxSize {box} is not in comoving Mpc as expected")
        es = f"ExclusiveSphere/{aperture}"
        mstar = soap_physical(f, f"{es}/StellarMass", MSUN_G)
        sfr = soap_physical(f, f"{es}/StarFormationRate", MSUN_G / YR_S)
        central = f["InputHalos/IsCentral"][()] == 1
        m200 = soap_physical(f, "SO/200_crit/TotalMass", MSUN_G)
        rpath = _first(f, f"{es}/HalfMassRadiusStars", "BoundSubhalo/HalfMassRadiusStars")
        bpath = _first(f, f"{es}/MostMassiveBlackHoleMass", "BoundSubhalo/MostMassiveBlackHoleMass")
        arrays = {"logm": np.log10(np.where(mstar > 0, mstar, np.nan)), "sfr": sfr, "resolved": mstar >= MIN_STAR_PARTICLES * mbar, "central": central,
                  "logmh": np.log10(np.where(central & (m200 > 0), m200, np.nan))}
        if rpath:
            arrays["rhalf_kpc"] = soap_physical(f, rpath, KPC_CM)
        if bpath:
            arrays["mbh"] = soap_physical(f, bpath, MSUN_G)
        cosmo = dict(f["Cosmology"].attrs) if "Cosmology" in f else {}
        h_file = float(np.atleast_1d(cosmo["h"])[0]) if "h" in cosmo else None
        om_file = float(np.atleast_1d(cosmo["Omega_m"])[0]) if "Omega_m" in cosmo else None
        apertures = sorted(f["ExclusiveSphere"].keys()) if "ExclusiveSphere" in f else []
    return {"z": z, "box": box, "arrays": arrays, "rpath": rpath, "digest": sha.hexdigest(), "h": h_file, "Om": om_file, "apertures": apertures}


def soap_records(suite, run, mbar, paths, aperture="50kpc", retrieved=None):
    meta, records = SOAP_SUITES[suite], []
    for path in paths:
        c = soap_read(path, aperture, mbar)
        spec = {"source": meta["source"], "run": run, "h": meta["h"], "Om": meta["Om"], "box": c["box"], "snap": None, "z": c["z"], "z_nominal": round(c["z"], 2),
                "massDefinition": f"aperture-{aperture.replace('kpc', 'pkpc')}-exclusive", "sizeDefinition": f"stellar-half-mass-3d-{'aperture' if c['rpath'] and 'Exclusive' in c['rpath'] else 'bound'}",
                "provenance": {"tier": "catalog-derived", "citation": f"{meta['citation']} {Path(path).name}; relations derived by sim-highline", "doi": None, "url": meta["url"],
                               "retrieved": retrieved or date.today().isoformat(), "sourceMember": Path(path).name, "checksumSha256": c["digest"]},
                "warning": (f"Derived by scripts/derive_soap_relations.py with the same cuts as the Subfind/EAGLE pipelines (M* >= {MIN_STAR_PARTICLES} baryon particle masses, {DM} dex bins, "
                            f">= {MIN_PER_BIN} galaxies per median); masses and SFRs in the {aperture} exclusive sphere; units from the catalogue's CGS conversion attributes."),
                "metallicityNote": "", "calibratedAtLowZ": meta["calibrated"]}
        records += relations_from_arrays(spec, c["arrays"])
    return records


# --- the EAGLE public SQL database ---
EAGLE_RUNS = {"RefL0100N1504": {"run": "Ref-L100N1504", "box": 100.0, "mbar": 1.81e6}, "RecalL0025N0752": {"run": "Recal-L025N0752", "box": 25.0, "mbar": 2.26e5}}
EAGLE_SNAPS = [28, 27, 23, 19, 15, 12, 10, 8, 6, 5, 4]
EAGLE_QUERY = """
SELECT SH.GalaxyID, SH.SnapNum, SH.Redshift, SH.SubGroupNumber,
       AP.Mass_Star, AP.SFR, AP.Mass_BH, SZ.R_halfmass30, FOF.Group_M_Crit200
FROM {sim}_SubHalo AS SH
JOIN {sim}_Aperture AS AP ON AP.GalaxyID = SH.GalaxyID AND AP.ApertureSize = 30
LEFT JOIN {sim}_Sizes AS SZ ON SZ.GalaxyID = SH.GalaxyID
JOIN {sim}_FOF AS FOF ON FOF.GroupID = SH.GroupID
WHERE SH.SnapNum = {snap} AND AP.Mass_Star >= {mmin}
"""


def eagle_arrays(rows):
    mstar = np.asarray(rows["Mass_Star"], dtype=float)
    return {"logm": np.log10(mstar), "sfr": np.asarray(rows["SFR"], dtype=float), "resolved": np.ones(len(mstar), dtype=bool),
            "central": np.asarray(rows["SubGroupNumber"]) == 0,
            "rhalf_kpc": np.asarray(rows["R_halfmass30"], dtype=float),
            "logmh": np.log10(np.where(np.asarray(rows["Group_M_Crit200"], dtype=float) > 0, rows["Group_M_Crit200"], np.nan)),
            "mbh": np.asarray(rows["Mass_BH"], dtype=float)}


def eagle_records(sim, execute, retrieved=None):
    """`execute(query)` returns the rows of one snapshot (a structured array or dict of columns), or nothing for a missing snapshot."""
    meta, records = EAGLE_RUNS[sim], []
    for snap in EAGLE_SNAPS:
        query = EAGLE_QUERY.format(sim=sim, snap=snap, mmin=MIN_STAR_PARTICLES * meta["mbar"])
        rows = execute(query)
        if rows is None or len(rows) == 0:
            continue
        z = float(rows["Redshift"][0])
        spec = {"source": "EAGLE", "run": meta["run"], "h": 0.6777, "Om": 0.307, "box": meta["box"], "snap": snap, "z": z, "z_nominal": round(z, 2),
                "massDefinition": "aperture-30pkpc", "sizeDefinition": "stellar-half-mass-3d-30pkpc",
                "provenance": {"tier": "catalog-derived", "citation": f"EAGLE {sim} public database, snapshot {snap} (McAlpine et al. 2016); relations derived by sim-highline",
                               "doi": None, "url": "https://virgodb.dur.ac.uk/", "retrieved": retrieved or date.today().isoformat(),
                               "sourceMember": "SQL: " + " ".join(query.split()), "checksumSha256": hashlib.sha256(np.asarray(rows).tobytes()).hexdigest()},
                "warning": (f"Derived by scripts/derive_eagle_relations.py from the public EAGLE database: 30 pkpc apertures for mass, SFR and BH mass; M* >= {MIN_STAR_PARTICLES} baryon particle masses; "
                            f"bins of {DM} dex with >= {MIN_PER_BIN} galaxies for medians. Same cuts as the Subfind pipeline used for TNG/Illustris except the aperture."),
                "metallicityNote": "", "calibratedAtLowZ": ("gsmf", "size", "bh")}
        records += relations_from_arrays(spec, eagle_arrays(rows))
    return records


def write_records(records, out):
    Path(out).write_text(json.dumps({"schemaVersion": SCHEMA_VERSION, "records": records}, indent=2) + "\n")


# =====================================================================================================================
# `sim-highline derive`: from a catalogue you hold to records in the project's format.
# The rule: a definition is taken from what you state or from what the file itself says, never assumed. Where the two
# disagree, or neither says, nothing is written and every such item is listed with the option that would settle it.
# =====================================================================================================================
FORMATS = ("subfind", "caesar", "soap", "eagle")
IMFS = ("chabrier03", "kroupa01", "salpeter55")
DOCS_URL = "https://github.com/ShubhanBhatia42/sim-highline/blob/main/docs/DERIVE-CLI.md"
RELATIONS_DERIVED = ("gsmf", "sfms", "ssfr", "quenched", "size", "shmr", "bh", "zstar", "mzr", "hi-fraction", "h2-fraction")
# what each format can hold beyond the core (stellar mass, SFR, centrals, halo mass): the relation, the array it needs, and what to say when it is absent
OPTIONAL = {
    "subfind": (("size", "rhalf_kpc", "SubhaloHalfmassRadType"), ("bh", "mbh", "SubhaloBHMass"), ("zstar", "zstar_solar", "SubhaloStarMetallicity"), ("mzr", "oh", "SubhaloGasMetalFractionsSfrWeighted")),
    "caesar": (("size", "rhalf_kpc", "dicts/radii.stellar_half_mass"), ("bh", "mbh", "dicts/masses.bh"), ("hi-fraction", "mHI", "dicts/masses.HI"), ("h2-fraction", "mH2", "dicts/masses.H2")),
    "soap": (("size", "rhalf_kpc", "HalfMassRadiusStars"), ("bh", "mbh", "MostMassiveBlackHoleMass")),
    "eagle": (("size", "rhalf_kpc", "R_halfmass30"), ("bh", "mbh", "Mass_BH")),
}
SUBFIND_CORE = ("SubhaloMassInRadType", "SubhaloSFRinRad", "SubhaloGrNr", "GroupFirstSub", "Group_M_Crit200")
EAGLE_CORE = ("Redshift", "SnapNum", "SubGroupNumber", "Mass_Star", "SFR", "Group_M_Crit200")


class UnderSpecified(ValueError):
    """Raised, with every problem at once, when a definition cannot be known (nothing stated, nothing in the file) or the file and the statement disagree. `problems` is the list."""

    def __init__(self, problems):
        self.problems = list(problems)
        n = len(self.problems)
        super().__init__(f"refusing to guess: {n} thing{'s' if n != 1 else ''} the tool cannot know or that conflict\n"
                         + "\n".join(f"  {i}. {p}" for i, p in enumerate(self.problems, 1)) + "\nNothing was written.")


class Derived(dict):
    """The payload ({"schemaVersion", "records"}) with a plain-language `report` (list of lines) and the `facts` (where each definition came from)."""
    report = ()
    facts = ()


def slug(text):
    return re.sub(r"[^a-z0-9.-]+", "-", str(text).lower()).strip("-.")


def _num(x):
    return float(np.atleast_1d(x)[0])


def _close(a, b, tol=1e-3):
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-12)


def _pick(problems, facts, name, flag, stated, in_file, where, tol=1e-3, fmt="{:g}"):
    """One value from the statement and/or the file. Both and different: a problem. Neither: a problem. Returns the value (the file's on a conflict, so that the rest can go on)."""
    if stated is not None and in_file is not None and not _close(stated, in_file, tol):
        problems.append(f"{name}: you stated {fmt.format(stated)} ({flag}) but {where} says {fmt.format(in_file)}. Fix whichever is wrong; the tool will not choose between them.")
        return in_file
    if stated is not None:
        facts.append(f"{name} = {fmt.format(stated)} (stated by you with {flag}" + (f"; {where} agrees" if in_file is not None else "") + ")")
        return stated
    if in_file is not None:
        facts.append(f"{name} = {fmt.format(in_file)} (read from {where})")
        return in_file
    problems.append(f"{name}: {where} does not record it and you did not state it. Add {flag}.")
    return None


def _snapshot_from_name(path):
    m = re.search(r"(\d+)(?!.*\d)", Path(path).stem)
    return int(m.group(1)) if m else None


def _attr_float(attrs, key):
    return _num(attrs[key]) if key in attrs else None


def _subfind_snapshots(path):
    """{snapshot: folder} for a folder of group-catalogue files (one level of groups_NNN subfolders is searched too) or one such file."""
    path = Path(path)
    pats = (r"fof_subhalo_tab_(\d+)\.\d+\.hdf5", r"groups_(\d+)\.\d+\.hdf5", r"groups_(\d+)\.hdf5", r"fof_subhalo_tab_(\d+)\.hdf5")
    found = {}

    def scan(folder, only=None):
        for f in sorted(folder.glob("*.hdf5")):
            for p in pats:
                m = re.fullmatch(p, f.name)
                if m and (only is None or f == only):
                    found.setdefault(int(m.group(1)), folder)
    if path.is_file():
        scan(path.parent, only=path)
    else:
        scan(path)
        if not found:
            for sub in sorted(d for d in path.glob("groups_*") if d.is_dir()):
                scan(sub)
    return found


def _attested_units(first_file):
    """(UnitLength_in_cm, UnitMass_in_g) when the catalogue carries them in Header, Parameters or Config; else None."""
    h5py = _h5py()
    with h5py.File(first_file, "r") as f:
        for grp in ("Header", "Parameters", "Config"):
            if grp in f and "UnitLength_in_cm" in f[grp].attrs and "UnitMass_in_g" in f[grp].attrs:
                return _num(f[grp].attrs["UnitLength_in_cm"]), _num(f[grp].attrs["UnitMass_in_g"])
    return None


def _prep_subfind(catalogs, st, problems, facts):
    epochs = []
    if st["units"] not in (None, "illustris"):
        problems.append(f"units: '{st['units']}' is not a units convention this format knows; the only one is 'illustris' (masses in 1e10 Msun/h, comoving lengths in kpc/h, SFR in Msun/yr).")
    for c in catalogs:
        snaps = _subfind_snapshots(c)
        if not snaps:
            problems.append(f"catalog: no Subfind group-catalogue files in {c} (looked for fof_subhalo_tab_NNN.*.hdf5, groups_NNN.*.hdf5, groups_NNN.hdf5 and fof_subhalo_tab_NNN.hdf5).")
            continue
        for snap, folder in sorted(snaps.items()):
            where = f"the catalogue {Path(folder).name} (snapshot {snap})"
            header, cat, digest, nfiles = load(folder, snap)
            lacking = [k for k in SUBFIND_CORE if k not in cat]
            if lacking:
                problems.append(f"{where} lacks the fields {lacking}. They give the stellar mass within twice the stellar half-mass radius, the SFR, which subhaloes are centrals and the halo mass; derive cannot do without them.")
                continue
            if "Redshift" not in header:
                problems.append(f"{where} has no Redshift in its Header (a download of single fields has no header); derive needs the full group-catalogue files.")
                continue
            z = _num(header["Redshift"])
            a = _num(header["Time"]) if "Time" in header else 1 / (1 + z)
            attested = _attested_units(subfind_files(folder, snap)[0])
            if attested is not None:
                if not (_close(attested[0], KPC_CM) and _close(attested[1], 1e10 * MSUN_G)):
                    problems.append(f"units: {where} says UnitLength_in_cm = {attested[0]:g} and UnitMass_in_g = {attested[1]:g}; this format reads lengths in kpc/h and masses in 1e10 Msun/h, which are 3.085678e21 and 1.989e43.")
                unit_fact = "units: lengths ckpc/h, masses 1e10 Msun/h (checked against the unit attributes in the file)"
            elif st["units"] == "illustris":
                unit_fact = "units: lengths ckpc/h, masses 1e10 Msun/h (stated by you with --units illustris; the file carries no unit attributes to check)"
            else:
                problems.append(f"units: {where} carries no UnitLength_in_cm and UnitMass_in_g, so it cannot show that lengths are comoving kpc/h and masses 1e10 Msun/h. If they are (the Illustris and IllustrisTNG convention), add --units illustris.")
                unit_fact = None
            local = []
            h = _pick(problems, local, "h", "--h", st["h"], _attr_float(header, "HubbleParam"), where, fmt="{:.4g}")
            om = _pick(problems, local, "omega_m", "--omega-m", st["omega_m"], _attr_float(header, "Omega0"), where, fmt="{:.4g}")
            ol = _attr_float(header, "OmegaLambda")
            if om is not None and ol is not None and abs(om + ol - 1) > 1e-3:
                problems.append(f"{where} has Omega0 + OmegaLambda = {om + ol:.4g}; the star-forming cut uses a flat cosmology, so a non-flat run is not supported.")
            box_file = _attr_float(header, "BoxSize")
            box = _pick(problems, local, "box (comoving Mpc)", "--box-mpc", st["box_mpc"], None if box_file is None or h is None else box_file / 1000 / h, f"{where} (BoxSize in ckpc/h divided by h)", fmt="{:.6g}")
            if None in (h, om, box):
                continue
            flag = cat.get("SubhaloFlag")
            local += [unit_fact] if unit_fact else []
            local.append("mass: stellar mass within twice the stellar half-mass radius (SubhaloMassInRadType), SFR from SubhaloSFRinRad (the field's own definitions)")
            local.append("SubhaloFlag: " + ("subhaloes flagged as not of cosmological origin are excluded" if flag is not None else "absent from the catalogue, so no subhalo is excluded as spurious"))
            epochs.append({"z": z, "snap": snap, "h": h, "Om": om, "box": box, "arrays": subfind_arrays(cat, h, a, st["mbar"]), "digest": digest, "nfiles": nfiles,
                           "member": f"{Path(folder).name}/ ({nfiles} files of snapshot {snap})", "name": Path(folder).name, "facts": local,
                           "mass_definition": "aperture-2rhalf-stars", "size_definition": "stellar-half-mass-3d-bound", "halo": "m200c",
                           "metallicity_note": "SFR-weighted, within twice the stellar half-mass radius",
                           "warning": (f"Subhaloes with SubhaloFlag = 0 excluded; " if flag is not None else "No SubhaloFlag in the catalogue, so spurious subhaloes are not excluded; ")
                           + "stellar mass and SFR within twice the stellar half-mass radius."})
    return epochs


def _prep_caesar(catalogs, st, problems, facts):
    h5py = _h5py()
    epochs = []
    for c in catalogs:
        path = Path(c)
        if not path.is_file():
            problems.append(f"catalog: {path} is not a file; give the CAESAR .hdf5 catalogue itself.")
            continue
        where = f"the catalogue {path.name}"
        with h5py.File(path, "r") as f:
            if "simulation_attributes" not in f or "galaxy_data" not in f or "halo_data" not in f:
                problems.append(f"{where} does not look like a CAESAR catalogue (no simulation_attributes, galaxy_data and halo_data).")
                continue
            sa = f["simulation_attributes"].attrs
            z = _attr_float(sa, "redshift")
            h_file, om_file = _attr_float(sa, "hubble_constant"), _attr_float(sa, "omega_matter")
            halo_keys = [k for k in CAESAR_HALO_MASS_KEYS[:2] if k in f["halo_data"]]
        if z is None:
            problems.append(f"{where} has no redshift in simulation_attributes.")
            continue
        local = []
        h = _pick(problems, local, "h", "--h", st["h"], h_file, where, fmt="{:.4g}")
        om = _pick(problems, local, "omega_m", "--omega-m", st["omega_m"], om_file, where, fmt="{:.4g}")
        if not halo_keys:
            problems.append(f"{where} has no M200crit halo mass (looked for dicts/masses.m200c and dicts/virial_quantities.m200c in halo_data); a mean-density m200 is not accepted because the halo-mass relation would then not be M200crit.")
        snap = _snapshot_from_name(path) if st["snapshot"] is None else st["snapshot"]
        if snap is None:
            problems.append(f"snapshot: no number in the file name {path.name}; add --snapshot N (only with one catalogue).")
        if None in (h, om) or not halo_keys or snap is None:
            continue
        try:
            r = caesar_read(path, st["mbar"], halo_keys=tuple(halo_keys), h=h)
        except SystemExit as e:
            problems.append(str(e))
            continue
        box = _pick(problems, local, "box (comoving Mpc)", "--box-mpc", st["box_mpc"], r["box_kpc"] / 1e3, f"{where} (boxsize with its stated units)", fmt="{:.6g}")
        local.append("units: every quantity is converted from the 'unit' attribute of its dataset; an unrecognised unit stops the run")
        local.append("mass: total stellar mass of the CAESAR galaxy (6D-FOF members), not an aperture")
        epochs.append({"z": z, "snap": snap, "h": h, "Om": om, "box": box, "arrays": r["arrays"], "digest": r["digest"], "member": path.name, "name": path.name, "facts": local,
                       "mass_definition": "caesar-6dfof-galaxy-total", "size_definition": "stellar-half-mass-3d-bound", "halo": r["hkey"].split("/")[-1], "metallicity_note": "",
                       "warning": "CAESAR stellar masses are totals of 6D-FOF galaxy members, not apertures; units read from each dataset's 'unit' attribute."})
    return epochs


def _prep_soap(catalogs, st, problems, facts):
    h5py = _h5py()
    epochs = []
    ap = st["aperture"]
    if ap is None:
        problems.append("aperture: the mass aperture is a choice made when the catalogue was built and the tool cannot guess it. Add --aperture, for example 50kpc (the name of a group under ExclusiveSphere in the file).")
    elif not re.fullmatch(r"\d+p?kpc", ap):
        problems.append(f"aperture: '{ap}' is not of the form 50kpc.")
        ap = None
    else:
        ap = ap.replace("pkpc", "kpc")
    for c in catalogs:
        path = Path(c)
        if not path.is_file():
            problems.append(f"catalog: {path} is not a file; give the SOAP halo_properties_NNNN.hdf5 file itself.")
            continue
        where = f"the catalogue {path.name}"
        with h5py.File(path, "r") as f:
            if "Header" not in f or "ExclusiveSphere" not in f:
                problems.append(f"{where} does not look like a SOAP halo catalogue (no Header and ExclusiveSphere).")
                continue
            available = sorted(f["ExclusiveSphere"].keys())
        if ap is not None and ap not in available:
            problems.append(f"aperture: {where} has no ExclusiveSphere/{ap}; it has {available}.")
            continue
        if ap is None:
            continue
        try:
            r = soap_read(path, ap, st["mbar"], box_mpc=st["box_mpc"])
        except SystemExit as e:
            msg = str(e)
            problems.append(msg + (" State the box with --box-mpc (comoving Mpc)." if "BoxSize" in msg else ""))
            continue
        local = []
        h = _pick(problems, local, "h", "--h", st["h"], r["h"], f"the Cosmology group of {where}", fmt="{:.4g}")
        om = _pick(problems, local, "omega_m", "--omega-m", st["omega_m"], r["Om"], f"the Cosmology group of {where}", fmt="{:.4g}")
        snap = _snapshot_from_name(path) if st["snapshot"] is None else st["snapshot"]
        if snap is None:
            problems.append(f"snapshot: no number in the file name {path.name}; add --snapshot N (only with one catalogue).")
        if None in (h, om) or snap is None:
            continue
        local.append(f"box = {r['box']:.6g} comoving Mpc (" + ("stated by you with --box-mpc" if st["box_mpc"] is not None else "read from the Header; it is plausibly comoving Mpc") + ")")
        local.append(f"mass: stellar mass in the {ap} exclusive sphere (ExclusiveSphere/{ap}); units from the file's own CGS conversion attributes (a dataset without one stops the run)")
        epochs.append({"z": r["z"], "snap": snap, "h": h, "Om": om, "box": r["box"], "arrays": r["arrays"], "digest": r["digest"], "member": path.name, "name": path.name, "facts": local,
                       "mass_definition": f"aperture-{ap.replace('kpc', 'pkpc')}", "halo": "m200c", "metallicity_note": "",
                       "size_definition": f"stellar-half-mass-3d-{'aperture' if r['rpath'] and 'Exclusive' in r['rpath'] else 'bound'}",
                       "warning": f"Masses and SFRs in the {ap} exclusive sphere (the particles bound to the subhalo within that radius); M200crit from SO/200_crit."})
    return epochs


def _prep_eagle(catalogs, st, problems, facts):
    import pandas as pd
    epochs = []
    if st["units"] != "eagle-database":
        problems.append("units: a table of numbers does not say what its columns are in. If they are as the EAGLE database gives them (Msun, Msun/yr, proper kpc), add --units eagle-database.")
    if st["aperture"] not in (None, "30pkpc", "30kpc"):
        problems.append(f"aperture: this format reads the 30 pkpc aperture quantities (the R_halfmass30 column is a 30 pkpc radius); '{st['aperture']}' is not supported.")
    elif st["aperture"] is None:
        problems.append("aperture: the table does not say which aperture Mass_Star, SFR and Mass_BH were taken in. Add --aperture 30pkpc if they come from the 30 pkpc aperture (ApertureSize = 30) as in the documented query.")
    for c in catalogs:
        path = Path(c)
        if not path.is_file():
            problems.append(f"catalog: {path} is not a file; give the table exported from the EAGLE database (CSV).")
            continue
        where = f"the table {path.name}"
        df = pd.read_csv(path, comment="#")
        lacking = [k for k in EAGLE_CORE if k not in df.columns]
        if lacking:
            problems.append(f"{where} lacks the columns {lacking}; the documented query (docs/DERIVE-CLI.md) lists them.")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        local = []
        h = _pick(problems, local, "h", "--h", st["h"], None, "the table (it holds no cosmology)", fmt="{:.4g}")
        om = _pick(problems, local, "omega_m", "--omega-m", st["omega_m"], None, "the table (it holds no cosmology)", fmt="{:.4g}")
        box = _pick(problems, local, "box (comoving Mpc)", "--box-mpc", st["box_mpc"], None, "the table (it holds no box size)", fmt="{:.6g}")
        if None in (h, om, box):
            continue
        cut = MIN_STAR_PARTICLES * st["mbar"]
        local += ["units: as the EAGLE database gives them (stated by you with --units eagle-database)", "mass: stellar mass in the 30 pkpc aperture (stated by you with --aperture 30pkpc)"]
        for snap, d in sorted(df.groupby("SnapNum"), key=lambda kv: kv[0]):
            if d["Mass_Star"].min() > 2 * cut:
                problems.append(f"{where}, snapshot {snap}: the smallest Mass_Star is {d['Mass_Star'].min():.3g} Msun, more than twice the resolution cut ({cut:.3g} Msun = 100 baryon particle masses), so the table is not complete down to the cut and the mass function would be wrong. Export every galaxy above the cut.")
                continue
            zs = d["Redshift"].to_numpy(float)
            if np.ptp(zs) > 1e-6:
                problems.append(f"{where}, snapshot {snap}: Redshift is not one value ({zs.min():g} to {zs.max():g}).")
                continue
            rows = {k: d[k].to_numpy() for k in d.columns}
            ms = rows["Mass_Star"].astype(float)
            arrays = {"logm": np.log10(np.where(ms > 0, ms, np.nan)), "sfr": rows["SFR"].astype(float), "resolved": ms >= cut, "central": rows["SubGroupNumber"] == 0,
                      "logmh": np.log10(np.where(rows["Group_M_Crit200"].astype(float) > 0, rows["Group_M_Crit200"].astype(float), np.nan))}
            if "R_halfmass30" in rows:
                arrays["rhalf_kpc"] = rows["R_halfmass30"].astype(float)
            if "Mass_BH" in rows:
                arrays["mbh"] = rows["Mass_BH"].astype(float)
            epochs.append({"z": float(zs[0]), "snap": int(snap), "h": h, "Om": om, "box": box, "arrays": arrays, "digest": digest, "member": f"{path.name} (SnapNum = {int(snap)})", "name": path.name, "facts": local,
                           "mass_definition": "aperture-30pkpc", "size_definition": "stellar-half-mass-3d-30pkpc", "halo": "m200c", "metallicity_note": "",
                           "warning": "Masses, SFRs and black-hole masses in the 30 pkpc aperture; sizes are the 30 pkpc half-mass radii; the table must hold every galaxy above the resolution cut."})
    return epochs


_PREP = {"subfind": _prep_subfind, "caesar": _prep_caesar, "soap": _prep_soap, "eagle": _prep_eagle}


def validate_records(records):
    """The structural checks that scripts/validate-curves.mjs makes on a record file, for the records this tool writes. Returns a list of problems (empty when valid)."""
    errors, ids, keys = [], set(), set()
    for r in records:
        i = r.get("id", "?")
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]+", i):
            errors.append(f"{i}: id must match ^[a-z0-9][a-z0-9._-]+$")
        if i in ids:
            errors.append(f"{i}: duplicate id")
        ids.add(i)
        key = (r["source"], r.get("run") or "none", r["relation"], r["epoch"]["zRepresentative"])
        if key in keys:
            errors.append(f"{i}: duplicate source/run/relation/epoch")
        keys.add(key)
        e = r["epoch"]
        if not (e["zMin"] <= e["zRepresentative"] <= e["zMax"]):
            errors.append(f"{i}: representative redshift outside range")
        if e["mode"] == "snapshot" and not isinstance(e.get("snapshot"), int):
            errors.append(f"{i}: snapshot number required")
        if not re.match(r"https://", r["provenance"].get("url", "")):
            errors.append(f"{i}: HTTPS primary source required")
        if r["provenance"]["tier"] == "digitized-figure" and r["rankable"]:
            errors.append(f"{i}: digitized figures cannot be rankable")
        rep = r["representation"]
        if rep["type"] != "points":
            errors.append(f"{i}: representation type {rep['type']} is not the stored form")
            continue
        prev = -math.inf
        for k, p in enumerate(rep["points"]):
            if not (all(isinstance(p.get(c), (int, float)) and math.isfinite(p[c]) for c in ("x", "y"))):
                errors.append(f"{i}: non-finite coordinate at point {k}")
                continue
            if rep.get("connect") is not False and not p["x"] > prev:
                errors.append(f"{i}: x values must increase at point {k}")
            prev = p["x"]
            if "yLow" in p and p["yLow"] > p["y"] or "yHigh" in p and p["yHigh"] < p["y"]:
                errors.append(f"{i}: interval does not contain y at point {k}")
        if len(rep["points"]) < 2 or r["domain"]["xMin"] != rep["points"][0]["x"] or r["domain"]["xMax"] != rep["points"][-1]["x"]:
            errors.append(f"{i}: domain must match the point extent (and there must be two points)")
    return errors


def derive_run(fmt, catalogs, *, source=None, run=None, imf=None, baryon_particle_mass=None, h=None, omega_m=None, box_mpc=None, units=None, aperture=None,
               snapshot=None, url=None, calibrated_on=(), distributions=False, retrieved=None):
    """Records of the standard relations from a catalogue you hold. `fmt` is one of FORMATS; `catalogs` a path or a list of paths (a folder or file per snapshot for subfind, a file per snapshot for caesar and soap, an exported table for eagle).
    Stated here: source and run (names), imf, baryon_particle_mass (initial baryon particle mass in Msun, sets the 100-particle cut), and where the catalogue does not say them h, omega_m, box_mpc (comoving Mpc), units, aperture, snapshot.
    Raises UnderSpecified, listing every missing or conflicting definition, instead of assuming one. Returns a Derived payload (a dict with "schemaVersion" and "records", plus .report and .facts)."""
    problems, facts = [], []
    if fmt not in FORMATS:
        raise UnderSpecified([f"format: '{fmt}' is not one of {', '.join(FORMATS)}."])
    paths = [Path(c) for c in ([catalogs] if isinstance(catalogs, (str, Path)) else list(catalogs or []))]
    if not paths:
        problems.append("catalog: no catalogue given. Add --catalog PATH (repeat it for several snapshots).")
    problems += [f"catalog: {p} does not exist." for p in paths if not p.exists()]
    if not source or not run:
        problems.append("source and run: the name of your simulation and of this run are yours to give. Add --source and --run (they appear in every record and in the comparison).")
    if imf is None:
        problems.append(f"imf: no catalogue format records the initial mass function the stellar masses assume. Add --imf ({', '.join(IMFS)}).")
    elif imf not in IMFS:
        problems.append(f"imf: '{imf}' is not one of {', '.join(IMFS)}, the three the comparison rules can convert between; a different IMF is not supported.")
    if baryon_particle_mass is None or not baryon_particle_mass > 0:
        problems.append("baryon particle mass: the resolution cut (stellar mass of at least 100 baryon particle masses) needs the initial baryon particle mass in Msun (not Msun/h). Add --baryon-particle-mass.")
    for name, val, lo, hi, flag in (("h", h, 0.3, 1.5, "--h"), ("omega_m", omega_m, 0.05, 0.95, "--omega-m"), ("box (comoving Mpc)", box_mpc, 0.0, math.inf, "--box-mpc")):
        if val is not None and not lo < val < hi:
            problems.append(f"{name}: {val} is not plausible for {flag}" + (" (h is H0 / 100, for example 0.6774, not 67.74)" if name == "h" else "") + ".")
    bad = [r for r in calibrated_on if r not in RELATIONS_DERIVED]
    if bad:
        problems.append(f"calibrated-on: {bad} are not relations this tool derives ({', '.join(RELATIONS_DERIVED)}).")
    if snapshot is not None and len(paths) > 1:
        problems.append("snapshot: --snapshot names one snapshot, so it can be used with one catalogue only.")
    st = {"imf": imf, "mbar": baryon_particle_mass if baryon_particle_mass and baryon_particle_mass > 0 else 1.0, "h": h, "omega_m": omega_m, "box_mpc": box_mpc, "units": units, "aperture": aperture, "snapshot": snapshot}
    epochs = []
    if paths and all(p.exists() for p in paths):
        try:
            epochs = _PREP[fmt](paths, st, problems, facts)
        except (KeyError, OSError, ValueError, IndexError) as ex:
            problems.append(f"catalog: could not be read as a {fmt} catalogue ({type(ex).__name__}: {ex}). Check that --catalog is a {fmt} catalogue of the layout this format reads (docs/DERIVE-CLI.md lists it).")
    if not problems and not epochs:
        problems.append("catalog: nothing could be read from the catalogue(s).")
    seen = {}
    for ep in epochs:
        key = round(ep["z"], 4)
        if key in seen:
            problems.append(f"catalog: {ep['name']} and {seen[key]} are at the same redshift ({ep['z']:.4g}); give one catalogue per snapshot.")
        seen[key] = ep["name"]
    for k in ("h", "Om"):
        vals = sorted({round(ep[k], 6) for ep in epochs})
        if len(vals) > 1:
            problems.append(f"{k}: the catalogues disagree ({vals}); one run has one cosmology.")
    if problems:
        raise UnderSpecified(problems)
    retrieved = retrieved or date.today().isoformat()
    records, report = [], []
    for ep in sorted(epochs, key=lambda e: e["z"]):
        z = ep["z"]
        spec = {"source": source, "run": run, "idPrefix": f"derived.{slug(source)}.{slug(run)}", "h": ep["h"], "Om": ep["Om"], "box": ep["box"], "snap": ep["snap"], "z": z, "z_nominal": round(z, 2),
                "imf": imf, "massDefinition": ep["mass_definition"], "sizeDefinition": ep["size_definition"], "halo": ep["halo"], "metallicityNote": ep["metallicity_note"],
                "calibratedAtLowZ": tuple(calibrated_on), "calibrationDefault": "unknown", "distribution": bool(distributions), "storedDistribution": True,
                "distributionRun": f"{run} (per-galaxy distribution)",
                "provenance": {"tier": "catalog-derived", "citation": f"{source} {run}: catalogue {ep['name']} supplied by the user (format {fmt}), not a public release; relations derived by sim-highline derive",
                               "doi": None, "url": url or DOCS_URL, "retrieved": retrieved, "sourceMember": ep["member"], "checksumSha256": ep["digest"]},
                "warning": (f"Derived by sim-highline derive (format {fmt}) from a catalogue supplied by the user. Galaxies: stellar mass of at least {MIN_STAR_PARTICLES} baryon particle masses "
                            f"({MIN_STAR_PARTICLES * st['mbar']:.2g} Msun, as stated); {ep['warning']} Bins of {DM} dex with at least {MIN_PER_BIN} galaxies for medians."),
                "notes": "Derived with the same cuts and definitions as the dataset's own catalogue-derived records. Where each value came from: " + "; ".join(facts_of(st, ep, imf, calibrated_on)) + "."}
        made = relations_from_arrays(spec, ep["arrays"])
        records += made
        have = {r["relation"] for r in made}
        n_res = int(np.sum(ep["arrays"]["resolved"] & np.isfinite(ep["arrays"]["logm"])))
        line = f"z = {z:.4g} (snapshot {ep['snap']}), {ep['name']}: {n_res} galaxies above the cut; relations written: {', '.join(r for r in RELATIONS_DERIVED if r in have)}"
        skipped = []
        for rel, key, field in OPTIONAL[fmt]:
            if rel not in have:
                skipped.append(f"{rel} ({field} not in the catalogue)" if key not in ep["arrays"] else f"{rel} (fewer than two bins with {MIN_PER_BIN} galaxies)")
        for rel in ("gsmf", "sfms", "ssfr", "quenched", "shmr"):
            if rel not in have:
                skipped.append(f"{rel} (fewer than two bins with enough galaxies)")
        report.append(line + (f"; not derived: {', '.join(skipped)}" if skipped else ""))
    errors = validate_records(records)
    if errors:
        raise RuntimeError("the records this tool built do not pass its own validation (a bug, please report it): " + "; ".join(errors[:5]))
    out = Derived({"schemaVersion": SCHEMA_VERSION, "records": records})
    out.report, out.facts = report, list(dict.fromkeys(f for ep in epochs for f in facts_of(st, ep, imf, calibrated_on)))
    return out


def facts_of(st, ep, imf, calibrated_on):
    f = [f"imf = {imf} (stated by you with --imf)", f"baryon particle mass = {st['mbar']:.3g} Msun (stated by you)"]
    f += [x for x in ep["facts"] if x]
    f.append("calibration: " + (f"{', '.join(calibrated_on)} stated by you as tuned to at z < 0.2; every other relation, and every epoch above z = 0.2, is marked unknown" if calibrated_on else "not stated, so every record is marked unknown"))
    return f


def write_payload(payload, out):
    Path(out).write_text(json.dumps({"schemaVersion": payload["schemaVersion"], "records": payload["records"]}, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def add_derive_arguments(p):
    p.add_argument("--format", required=True, choices=FORMATS, dest="fmt", help="subfind (Illustris/TNG-style group catalogue), caesar (SIMBA), soap (FLAMINGO/COLIBRE halo catalogue) or eagle (a table exported from the EAGLE database)")
    p.add_argument("--catalog", required=True, action="append", metavar="PATH", help="the catalogue: a folder or file (repeat for several snapshots)")
    p.add_argument("--out", required=True, metavar="run.json", help="where to write the records")
    p.add_argument("--source", help="name of your simulation or suite (required)")
    p.add_argument("--run", help="name of this run (required)")
    p.add_argument("--imf", help="initial mass function the stellar masses assume: " + ", ".join(IMFS) + " (required)")
    p.add_argument("--baryon-particle-mass", type=float, metavar="MSUN", help="initial baryon particle mass in Msun, not Msun/h (required)")
    p.add_argument("--h", type=float, help="H0/100, only if the catalogue does not record it")
    p.add_argument("--omega-m", type=float, help="matter density, only if the catalogue does not record it")
    p.add_argument("--box-mpc", type=float, help="box side in comoving Mpc (not Mpc/h), only if the catalogue does not record it")
    p.add_argument("--units", help="the units convention of a catalogue that does not carry its units: illustris (subfind), eagle-database (eagle)")
    p.add_argument("--aperture", help="mass aperture: 50kpc (a group under ExclusiveSphere in a SOAP file) or 30pkpc (eagle)")
    p.add_argument("--snapshot", type=int, help="snapshot number, when the file name has none (one catalogue only)")
    p.add_argument("--calibrated-on", default="", metavar="RELATIONS", help="comma-separated relations your run was tuned to at z < 0.2 (default: none stated, every record is marked unknown)")
    p.add_argument("--url", help="https address describing the catalogue (default: the page describing this tool, which is not where the data are)")
    p.add_argument("--distributions", action="store_true", help="also write the per-galaxy specific-SFR distribution as its own record")
    p.add_argument("--compare", action="store_true", help="after writing, compare the records with the dataset as `sim-highline compare` does")
    p.add_argument("--top", type=int, default=5, help="rows per list with --compare")


def run_derive_cli(a):
    """Entry point for the derive subcommand (called by sim_highline.main). Returns the exit code: 0 written, 2 refused."""
    import sys
    try:
        payload = derive_run(a.fmt, a.catalog, source=a.source, run=a.run, imf=a.imf, baryon_particle_mass=a.baryon_particle_mass, h=a.h, omega_m=a.omega_m, box_mpc=a.box_mpc,
                             units=a.units, aperture=a.aperture, snapshot=a.snapshot, url=a.url, calibrated_on=tuple(x for x in a.calibrated_on.split(",") if x), distributions=a.distributions)
    except UnderSpecified as e:
        print(f"sim-highline derive: {e}", file=sys.stderr)
        return 2
    write_payload(payload, a.out)
    print(f"sim-highline derive: {len(payload['records'])} records written to {a.out}")
    for line in payload.report:
        print("  " + line)
    print("definitions used (each says whether you stated it or the file did):")
    for f in payload.facts:
        print("  " + f)
    if a.compare:
        import sim_highline
        print()
        sim_highline.compare_records_cli(payload["records"], top=a.top)
    return 0
