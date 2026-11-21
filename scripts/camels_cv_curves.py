"""Curves of the CAMELS fiducial simulations (the cosmic-variance set CV: 27 boxes of 25 Mpc/h with the fiducial parameters of IllustrisTNG, SIMBA and Astrid) for six relations, from the per-box summaries saved by
scripts/ingest_camels_galaxies.py in data/ensembles/camels-galaxies.json (IllustrisTNG, SIMBA) and data/ensembles/camels-galaxies-astrid.json (Astrid). Offline; no download.

Each curve is, bin by bin, the mean over the boxes of the per-box statistic (the median of the galaxies in the bin, or for the quenched fraction the fraction) at one snapshot (z = 0, 0.95, 2.15, 3, 4); a bin is kept when at least
14 of the 27 boxes have a value for it (a box has none where it holds fewer than 5 galaxies). The band is one standard deviation between the boxes: the cosmic variance of a box of this size, not the scatter of galaxies.
All three codes are measured by the same code from the same kind of catalogue with the same definitions, so the curves of one relation can be read against each other; they are the small-box CAMELS versions of the models, not
the production runs of the same names, and they are given their own source names (CAMELS-TNG, CAMELS-SIMBA, CAMELS-Astrid) so that they never stand in for those runs.

Left out on purpose: the stellar mass function (the pre-registered harmonization study takes one curve per simulation source from every stellar mass function record), the star formation rate density (the model-form study),
the specific star formation rate (the distribution records of the same boxes already give it, with a different population), the halo mass function and the black hole occupation.
Writes data/curves/camels-cv-curves.json. Usage: python3 scripts/camels_cv_curves.py"""
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ENS = {"IllustrisTNG": ROOT / "data" / "ensembles" / "camels-galaxies.json", "SIMBA": ROOT / "data" / "ensembles" / "camels-galaxies.json", "Astrid": ROOT / "data" / "ensembles" / "camels-galaxies-astrid.json"}
OUT = ROOT / "data" / "curves" / "camels-cv-curves.json"
SNAPS = {"090": 0.0, "062": 0.95, "042": 2.15, "032": 3.0, "024": 4.0}
SOURCE = {"IllustrisTNG": "CAMELS-TNG", "SIMBA": "CAMELS-SIMBA", "Astrid": "CAMELS-Astrid"}
SHORT = {"IllustrisTNG": "tng", "SIMBA": "simba", "Astrid": "astrid"}
IMF_BASIS = {"IllustrisTNG": "TNG model paper (Pillepich+18); the CAMELS paper does not restate it", "SIMBA": "Dave+19 (SIMBA); the CAMELS paper does not restate it",
             "Astrid": "the ASTRID records already in this dataset; the CAMELS paper does not restate it"}
MIN_BOXES = 14
XM = "log10 stellar mass (total mass of the star particles bound to the Subfind subhalo)"
GALAXIES = "all subhaloes with at least one star particle and a stellar mass between 10^9 and 10^11.5 Msun"
# family -> (relation, x axis, y definition, y unit, population value, extra definitions, what the bin statistic is, the population sentence)
FAMILIES = {
    "bhms": ("bh", "mstar", "log10 black hole mass of the galaxy (total mass of the black hole particles of the subhalo), median over the galaxies that have a black hole", "log10(Msun)", "bh-hosts",
             {"bhMassMethod": "intrinsic-sum-of-bh-particles"}, "median", f"{GALAXIES} that have a black hole"),
    "shmr": ("shmr", "m200", "log10 (total bound stellar mass of the central galaxy / M200c of its halo)", "dex", "centrals", {"haloMassDefinition": "M200crit", "haloMassHistory": "current"}, "median",
             "central subhaloes (the first subhalo of each Friends-of-Friends group) with at least one star particle, halo mass M200c between 10^11 and 10^13 Msun"),
    "size": ("size", "mstar", "log10 3D stellar half-mass radius of all bound stars (physical kpc)", "log10(kpc)", "all", {"sizeDefinition": "stellar-half-mass-3d-bound"}, "median", GALAXIES),
    "zstar": ("zstar", "mstar", "log10 mass-weighted stellar metallicity / Zsun (Zsun = 0.0127)", "dex", "all",
              {"metallicityQuantity": "stellar-Z", "metallicityCalibration": "intrinsic mass-weighted (Zsun=0.0127)"}, "median", GALAXIES),
    "mzr": ("mzr", "mstar", "log10 SFR-weighted metal mass fraction of the gas / Zsun (Zsun = 0.0127)", "dex", "all galaxies with non-zero SFR",
            {"metallicityQuantity": "gas-metal-mass-fraction", "metallicityCalibration": "intrinsic-simulation (star-forming gas, SFR-weighted; Zsun = 0.0127)"}, "median", f"{GALAXIES} and a non-zero star formation rate"),
    "qf": ("quenched", "mstar", "fraction of galaxies classified as quenched (specific SFR below 1e-11 per yr; zero star formation counts as quenched)", "fraction", "all", {"quenchingCriterion": "ssfr<1e-11"}, "fraction", GALAXIES),
}
RELATION_NOTE = {"bh": "bhms", "shmr": "shmr", "size": "size", "zstar": "zstar", "mzr": "mzr", "quenched": "qf"}


def centres(edges):
    return [round((a + b) / 2, 4) for a, b in zip(edges[:-1], edges[1:])]


def build():
    recs = []
    cache = {}
    for suite, path in ENS.items():
        ens = cache.setdefault(path, json.loads(path.read_text()))
        boxes = ens["suites"][suite]["CV"]
        names = sorted(boxes, key=lambda k: int(k.split("_")[1]))
        assert len(names) == 27, (suite, len(names))
        for snap, z in SNAPS.items():
            used = [n for n in names if boxes[n].get("snaps", {}).get(snap, {}).get("values")]
            sha = hashlib.sha256()
            for n in used:
                sha.update(boxes[n]["snaps"][snap]["arrays_sha256"].encode())
            for fam, (rel, xk, ydef, yunit, pop, extra, stat, popsent) in FAMILIES.items():
                edges = ens["m200ShmrEdges"] if xk == "m200" else ens["mstarEdges"]
                xs = centres(edges)
                rows = np.array([[np.nan if v is None else v for v in boxes[n]["snaps"][snap]["values"][fam]] for n in used], float)
                assert rows.shape[1] == len(xs), (suite, fam, rows.shape, len(xs))
                pts = []
                for j, x in enumerate(xs):
                    col = rows[:, j][~np.isnan(rows[:, j])]
                    if len(col) < MIN_BOXES:
                        continue
                    m, s = float(col.mean()), float(col.std(ddof=1))
                    lo, hi = m - s, m + s
                    if yunit == "fraction":
                        lo, hi = max(0.0, lo), min(1.0, hi)
                    pts.append({"x": x, "y": round(m, 4), "yLow": round(lo, 4), "yHigh": round(hi, 4)})
                if len(pts) < 3:
                    continue
                xdef = ("log10 M200c of the host halo (Friends-of-Friends group, 200 times the critical density)" if xk == "m200" else XM)
                recs.append({
                    "id": f"camels-cv.{SHORT[suite]}.{rel}.z{z:g}", "source": SOURCE[suite], "run": "CAMELS CV, 27 seeds", "kind": "simulation", "relation": rel,
                    "epoch": {"zRepresentative": z, "zMin": z, "zMax": z, "mode": "snapshot", "snapshot": int(snap)},
                    "axes": {"xDefinition": xdef, "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": yunit},
                    "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
                    "representation": {"type": "points", "intervalKind": "scatter", "connect": True, "points": pts},
                    "scatter": {"lower": "mean minus one standard deviation between the boxes", "upper": "mean plus one standard deviation between the boxes"},
                    "selection": {"population": f"{popsent}; per bin the {'fraction' if stat == 'fraction' else 'median'} over the galaxies of one box, then the mean over the boxes",
                                  "warning": (f"Mean over {len(used)} boxes of 25 Mpc/h of the per-box {'fraction' if stat == 'fraction' else 'median'} in each bin; a bin is kept where at least {MIN_BOXES} boxes have a value (a box has none where it holds fewer than 5 galaxies in the bin). "
                                              "The band is one standard deviation between the boxes (the cosmic variance of a box this size), not the scatter of galaxies. The lowest stellar-mass bin holds galaxies of about 60 star particles, so resolution may affect it (not tested). "
                                              "A box of 25 Mpc/h holds no galaxy above about 10^11.5 Msun. This is the small-box CAMELS version of the model, not the production run of the same name.")},
                    "definitions": {"massDefinition": "total-bound-subhalo", "imf": "chabrier03", "imfBasis": IMF_BASIS[suite], "cosmology": {"H0": 67.11, "Om": 0.3}, "population": pop, **extra},
                    "provenance": {"tier": "catalog-derived", "citation": "Villaescusa-Navarro et al. 2021, ApJ 915, 71 (CAMELS), cosmic-variance set, Subfind catalogues; per-box summaries and their mean by this project", "doi": "10.3847/1538-4357/abf7ba", "url": "https://arxiv.org/abs/2010.00619",
                                   "retrieved": ens.get("retrieved", "2026-10-18"), "sourceMember": f"Sims/{suite}/CV/CV_0..CV_26/groups_{snap}.hdf5 (SubhaloMassType, SubhaloHalfmassRadType, SubhaloSFR, SubhaloBHMass, SubhaloGasMetallicitySfrWeighted, SubhaloStarMetallicity, Group_M_Crit200)",
                                   "checksumSha256": sha.hexdigest(),
                                   "extractionMethod": "scripts/ingest_camels_galaxies.py (HTTP range requests of the arrays; per-box values in the saved ensemble file), then scripts/camels_cv_curves.py (mean and standard deviation over the boxes, offline); the tests recompute every point from the per-box values"},
                    "calibration": "prediction", "rankable": True,
                    "notes": "Same definitions and the same code for the three CAMELS codes, so the three CAMELS-* curves of a relation can be read against each other; the redshift range of the box set is z = 0 to 4 (five snapshots)."})
    return recs


if __name__ == "__main__":
    recs = build()
    OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(recs)} records to {OUT} ({len({r['source'] for r in recs})} sources, {len({r['relation'] for r in recs})} relations)")
