import argparse
import glob
import hashlib
import json
from datetime import date
from pathlib import Path

import h5py
import numpy as np

RUNS = {
    "TNG50-1": {"source": "IllustrisTNG", "run": "TNG50", "box_ckpc_h": 35000.0, "mbar": 8.5e4, "h": 0.6774, "Om": 0.3089, "url": "https://www.tng-project.org/data/", "calibrated": ("gsmf", "shmr", "bh", "size")},
    "TNG100-1": {"source": "IllustrisTNG", "run": "TNG100", "box_ckpc_h": 75000.0, "mbar": 1.4e6, "h": 0.6774, "Om": 0.3089, "url": "https://www.tng-project.org/data/", "calibrated": ("gsmf", "shmr", "bh", "size")},
    "TNG300-1": {"source": "IllustrisTNG", "run": "TNG300", "box_ckpc_h": 205000.0, "mbar": 1.1e7, "h": 0.6774, "Om": 0.3089, "url": "https://www.tng-project.org/data/", "calibrated": ("gsmf", "shmr", "bh", "size")},
    "Illustris-1": {"source": "Illustris", "run": "Illustris-1", "mbar": 1.26e6, "h": 0.704, "Om": 0.2726, "url": "https://www.illustris-project.org/data/", "calibrated": ("gsmf",)},
}
SNAPS_TNG = {99: 0.0, 91: 0.1, 84: 0.2, 67: 0.5, 50: 1.0, 40: 1.5, 33: 2.0, 25: 3.0, 21: 4.0, 17: 5.0, 13: 6.0, 11: 7.0, 8: 8.0}
FIELDS = ["SubhaloFlag", "SubhaloMassInRadType", "SubhaloSFRinRad", "SubhaloHalfmassRadType", "SubhaloBHMass", "SubhaloGasMetalFractionsSfrWeighted", "SubhaloGrNr", "SubhaloStarMetallicity"]
GROUP_FIELDS = ["GroupFirstSub", "Group_M_Crit200"]
MIN_STAR_PARTICLES, MIN_PER_BIN = 100, 10
DM = 0.2


def update_digest(digest, path):
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 24), b""):
            digest.update(chunk)


def load_field_files(groupdir, snap):
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


def load(groupdir, snap):
    files = []
    for pattern in (f"fof_subhalo_tab_{snap:03d}.*.hdf5", f"groups_{snap:03d}.*.hdf5", f"groups_{snap:03d}.hdf5", f"fof_subhalo_tab_{snap:03d}.hdf5"):
        files = sorted((f for f in glob.glob(str(Path(groupdir) / pattern)) if "*" not in pattern or f.split(".")[-2].isdigit()), key=lambda f: int(f.split(".")[-2]) if f.split(".")[-2].isdigit() else 0)
        if files:
            break
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
        mstar = cat["SubhaloMassInRadType"][:, 4] * 1e10 / h
        sfr = cat["SubhaloSFRinRad"]
        flag = cat.get("SubhaloFlag", np.ones_like(mstar, dtype=int)).astype(bool)
        resolved = flag & (mstar >= MIN_STAR_PARTICLES * meta["mbar"])
        logm = np.log10(np.where(mstar > 0, mstar, np.nan))
        central = np.zeros(len(mstar), dtype=bool)
        first = cat["GroupFirstSub"]
        central[first[first >= 0]] = True
        m200 = cat["Group_M_Crit200"] * 1e10 / h
        mf = cat["SubhaloGasMetalFractionsSfrWeighted"]
        ok_oh = (mf[:, 0] > 0) & (mf[:, 4] > 0)
        arrays = {"logm": logm, "sfr": sfr, "resolved": resolved, "central": central,
                  "rhalf_kpc": cat["SubhaloHalfmassRadType"][:, 4] * a / h,
                  "logmh": np.log10(np.where(m200[cat["SubhaloGrNr"]] > 0, m200[cat["SubhaloGrNr"]], np.nan)),
                  "mbh": cat["SubhaloBHMass"] * 1e10 / h,
                  "zstar_solar": cat["SubhaloStarMetallicity"] / 0.0127,
                  "oh": 12 + np.log10(np.where(ok_oh, (mf[:, 4] / 16.0) / np.where(ok_oh, mf[:, 0], 1), np.nan))}
        spec = {"source": meta["source"], "run": meta["run"], "h": h, "Om": meta["Om"], "box": box, "snap": snap, "z": z, "z_nominal": z_nominal,
                "massDefinition": "aperture-2x-stellar-half-mass-radius", "sizeDefinition": "stellar-half-mass-3d-bound",
                "provenance": {"tier": "catalog-derived", "citation": f"{label} Subfind group catalog, snapshot {snap} (Nelson et al. 2019 public data release); relations derived by sim-highline",
                               "doi": None, "url": meta["url"], "retrieved": retrieved, "sourceMember": f"{Path(groupdir).name}/fof_subhalo_tab_{snap:03d}.*.hdf5 ({nfiles} files)", "checksumSha256": digest},
                "warning": (f"Derived by scripts/derive_subfind_relations.py from the public group catalog. Galaxies: SubhaloFlag=1, M* >= {MIN_STAR_PARTICLES} baryon particle masses "
                            f"({MIN_STAR_PARTICLES * meta['mbar']:.2g} Msun); stellar mass and SFR within twice the stellar half-mass radius; bins of {DM} dex with >= {MIN_PER_BIN} galaxies for medians."),
                "metallicityNote": "SFR-weighted, within twice the stellar half-mass radius", "calibratedAtLowZ": meta["calibrated"]}
        records += relations_from_arrays(spec, arrays)
    return records


def relations_from_arrays(spec, A):
    records, z, z_nominal, snap = [], spec["z"], spec["z_nominal"], spec["snap"]
    logm, sfr, resolved, central, box = A["logm"], A["sfr"], A["resolved"], A["central"], spec["box"]
    mstar = 10 ** np.where(np.isfinite(logm), logm, -np.inf)
    ssfr = np.where(mstar > 0, sfr / np.where(mstar > 0, mstar, 1), 0)
    sf_cut = 0.2 / (age_gyr(z, spec["h"], spec["Om"]) * 1e9)
    star_forming = resolved & (ssfr > sf_cut)
    common = {"massDefinition": spec["massDefinition"], "imf": "chabrier03", "cosmology": {"H0": round(100 * spec["h"], 2), "Om": spec["Om"]}}
    edges = np.arange(7.0, 12.6, DM)
    prov, warn = spec["provenance"], spec["warning"]

    def rec(relation, suffix, points, interval, ydef, yunit, xdef, defs, population, extra=""):
        if len(points) < 2:
            return
        records.append({
            "id": f"derived.{spec['source'].lower().replace(' ', '-')}.{spec['run'].lower().replace(' ', '-')}.{relation}.{suffix}.z{z_nominal:g}", "source": spec["source"], "run": spec["run"], "kind": "simulation", "relation": relation,
            "epoch": {"zRepresentative": round(z, 4), "zNominal": z_nominal, "zMin": round(z, 4), "zMax": round(z, 4), "mode": "snapshot", "snapshot": snap},
            "axes": {"xDefinition": xdef, "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": yunit},
            "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
            "representation": {"type": "points", "intervalKind": interval, "connect": True, "points": points},
            "scatter": {"lower": "16th percentile", "upper": "84th percentile"} if interval == "scatter" else None,
            "selection": {"population": population, "warning": (warn + " " + extra).strip()},
            "definitions": {**common, **defs, "population": defs.get("population", population)},
            "provenance": prov, "calibration": "target" if relation in spec.get("calibratedAtLowZ", ()) and z < 0.2 else "prediction", "rankable": True,
            "notes": "Uniform-definition re-derivation; identical cuts are applied to every run and snapshot processed by this script."})

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


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from Subfind group catalogs.")
    ap.add_argument("run", help=f"one of {sorted(RUNS)} or a custom label used with --source/--mbar/--h/--Om")
    ap.add_argument("groups_root", help="directory containing groups_NNN/ subdirectories (or the group files themselves with --flat)")
    ap.add_argument("--flat", action="store_true", help="group files sit directly in groups_root (e.g. CAMELS groups_090.hdf5)")
    ap.add_argument("--source")
    ap.add_argument("--mbar", type=float, help="initial baryon particle mass in Msun (not Msun/h)")
    ap.add_argument("--h", type=float)
    ap.add_argument("--Om", type=float)
    ap.add_argument("--url", default="")
    ap.add_argument("--snaps", help="comma-separated snapshot numbers (default: TNG full-snapshot ladder)")
    args = ap.parse_args()
    if args.run not in RUNS:
        if None in (args.source, args.mbar, args.h, args.Om):
            raise SystemExit("custom runs need --source, --mbar, --h and --Om")
        RUNS[args.run] = {"source": args.source, "run": args.run, "mbar": args.mbar, "h": args.h, "Om": args.Om, "url": args.url, "calibrated": ()}
    snaps = SNAPS_TNG if not args.snaps else {int(s): None for s in args.snaps.split(",")}
    records = []
    for snap, z in snaps.items():
        groupdir = Path(args.groups_root) if args.flat else Path(args.groups_root) / f"groups_{snap:03d}"
        records += derive(args.run, groupdir, {snap: z}, date.today().isoformat())
    out = Path(__file__).resolve().parent.parent / "data" / "curves" / f"subfind-{args.run.lower()}.json"
    out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
    print(f"{args.run}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
