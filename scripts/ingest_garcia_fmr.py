import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

from derive_subfind_relations import DM, MIN_PER_BIN, age_gyr, binned_median

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/does_the_fmr_evolve_simulations_2")
url = "https://github.com/AlexGarcia623/does_the_fmr_evolve_simulations_2"
commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
ZSUN = 0.0127
SIMS = {
    "TNG": {"source": "IllustrisTNG", "run": "TNG100-1 (Garcia+ SF centrals)", "mbar": 1.4e6, "h": 0.6774, "Om": 0.3089, "mmin": 1e8, "sizes": True,
            "snaps": {99: 0, 50: 1, 33: 2, 25: 3, 21: 4, 17: 5, 13: 6, 11: 7, 8: 8, 6: 9, 4: 10}, "calibrated": ("size",),
            "fields": "SubhaloMassType (all bound), SubhaloSFR, SubhaloGasMetallicitySfr, SubhaloStarMetallicity, SubhaloHalfmassRadType"},
    "EAGLE": {"source": "EAGLE", "run": "Ref-L100N1504 (Garcia+ SF centrals)", "mbar": 1.81e6, "h": 0.6777, "Om": 0.307, "mmin": 1e8, "sizes": True,
              "snaps": {28: 0, 19: 1, 15: 2, 12: 3, 10: 4, 8: 5, 6: 6, 5: 7, 4: 8, 3: 9, 2: 10}, "calibrated": ("size",),
              "fields": "SubHalo table MassType_Star (all bound), StarFormationRate, SF_Metallicity, Stars_Metallicity, HalfMassRad_Star"},
    "SIMBA": {"source": "SIMBA", "run": "m100n1024 (Garcia+ SF centrals)", "mbar": 1.82e7, "h": 0.68, "Om": 0.3, "mmin": 1e9, "sizes": False, "skipped": "Zstar and R_star arrays in the release do not match the other arrays in length and are not used",
              "snaps": {151: 0, 105: 1, 79: 2, 62: 3, 51: 4, 42: 5, 36: 6, 30: 7, 26: 8}, "calibrated": (),
              "fields": "CAESAR masses.stellar (6D-FOF galaxy total), sfr, metallicities.sfr_weighted, metallicities.stellar"},
    "ORIGINAL": {"source": "Illustris", "run": "Illustris-1 (Garcia+ SF centrals)", "mbar": 1.26e6, "h": 0.704, "Om": 0.2726, "mmin": 1e8, "sizes": True,
                 "snaps": {135: 0, 86: 1, 68: 2, 60: 3, 54: 4, 49: 5, 45: 6, 41: 7, 38: 8, 35: 9, 32: 10}, "calibrated": (),
                 "fields": "SubhaloMassType (all bound), SubhaloSFR, SubhaloGasMetallicitySfr, SubhaloStarMetallicity, SubhaloHalfmassRadType"},
}
FILES = ("Stellar_Mass", "SFR", "Zgas", "Zstar", "R_star")
retrieved = date.today().isoformat()
edges = np.arange(7.0, 12.6, DM)
records = []
for key, sim in SIMS.items():
    mass_def = "caesar-6dfof-galaxy-total" if key == "SIMBA" else "total-bound-subhalo"
    common = {"massDefinition": mass_def, "imf": "chabrier03", "cosmology": {"H0": round(100 * sim["h"], 2), "Om": sim["Om"]}}
    for snap, z in sim["snaps"].items():
        d = root / "Data" / key / f"snap{snap}"
        if not d.exists():
            continue
        files = FILES if sim["sizes"] else FILES[:3]
        arr = {f: np.load(d / f"{f}.npy") for f in files}
        if len({len(v) for v in arr.values()}) != 1:
            raise SystemExit(f"{d}: arrays have different lengths {[(f, len(v)) for f, v in arr.items()]}")
        for f in ("Zstar", "R_star"):
            arr.setdefault(f, np.full(len(arr["Stellar_Mass"]), np.nan))
        digest = hashlib.sha256(b"".join((d / f"{f}.npy").read_bytes() for f in files)).hexdigest()
        mcut = max(100 * sim["mbar"], sim["mmin"])
        ok = arr["Stellar_Mass"] >= mcut
        logm = np.log10(arr["Stellar_Mass"][ok])
        sfr, zg, zs, rs = (arr[f][ok] for f in ("SFR", "Zgas", "Zstar", "R_star"))
        sf_cut = 0.2 / (age_gyr(z, sim["h"], sim["Om"]) * 1e9)
        sf = sfr / 10**logm > sf_cut
        warn = (f"Per-galaxy catalogue released with Garcia et al. (FMR paper II): centrals with SFR > 0 and M* > {sim['mmin']:.0e} Msun, fields {sim['fields']}. "
                f"sim-highline keeps M* >= {mcut:.2g} Msun (100 baryon particle masses), bins of {DM} dex with >= {MIN_PER_BIN} galaxies, and star-forming sSFR > 0.2/t_age(z). "
                "Satellites and quenched galaxies are not in the released sample. Redshifts are the authors' nominal integer labels for each snapshot." + (f" {sim['skipped']}." if sim.get("skipped") else ""))
        prov = {"tier": "catalog-derived", "citation": "Garcia et al. 2024c, Does the FMR evolve with redshift? II (per-galaxy data released in the paper repository); medians derived by sim-highline",
                "doi": None, "url": url, "retrieved": retrieved, "compilation": f"{url} @ {commit}", "sourceMember": f"Data/{key}/snap{snap}/*.npy", "checksumSha256": digest}

        def add(rel, suffix, points, ydef, yunit, defs, calibrated=False):
            if len(points) < 2:
                return
            records.append({
                "id": f"garcia24.{sim['source'].lower()}.{rel}.{suffix}.z{z}", "source": sim["source"], "run": sim["run"], "kind": "simulation", "relation": rel,
                "epoch": {"zRepresentative": float(z), "zNominal": float(z), "zMin": float(z), "zMax": float(z), "mode": "snapshot", "snapshot": snap},
                "axes": {"xDefinition": f"log10 stellar mass ({mass_def})", "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": yunit},
                "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
                "representation": {"type": "points", "intervalKind": "scatter", "connect": True, "points": points},
                "scatter": {"lower": "16th percentile", "upper": "84th percentile"},
                "selection": {"population": "star-forming centrals", "warning": warn},
                "definitions": {**common, **defs, "population": "star-forming-centrals"},
                "provenance": prov, "calibration": "target" if calibrated and z == 0 else "prediction", "rankable": True,
                "notes": "Uniform cuts applied identically to TNG100, EAGLE, SIMBA and Illustris from one released dataset; the repository carries no licence file, so cite the paper and repository."})

        m = sf & (sfr > 0)
        add("sfms", "sf-centrals", binned_median(logm[m], np.log10(sfr[m]), edges), "log10 instantaneous SFR, median of star-forming centrals", "log10(Msun/yr)",
            {"sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median"})
        m = sf & (zg > 0)
        add("mzr", "zgas-sf-centrals", binned_median(logm[m], np.log10(zg[m] / ZSUN), edges), "log10 metal mass fraction of star-forming gas / Zsun (Zsun = 0.0127)", "dex",
            {"metallicityQuantity": "gas-metal-mass-fraction", "metallicityCalibration": "intrinsic-simulation (star-forming gas, mass-weighted)"})
        m = sf & (zs > 0)
        add("zstar", "sf-centrals", binned_median(logm[m], np.log10(zs[m] / ZSUN), edges), "log10 mass-weighted stellar metallicity / Zsun (Zsun = 0.0127)", "dex",
            {"metallicityQuantity": "stellar-Z", "metallicityCalibration": "intrinsic mass-weighted (Zsun=0.0127)"})
        if sim["sizes"]:
            m = sf & (rs > 0)
            add("size", "sf-centrals", binned_median(logm[m], np.log10(rs[m]), edges), "log10 3D stellar half-mass radius of all bound stars (physical kpc)", "log10(kpc)",
                {"sizeDefinition": "stellar-half-mass-3d-bound"}, calibrated="size" in sim["calibrated"])
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "garcia-fmr.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Ingested {len(records)} records from the Garcia et al. per-galaxy catalogues")
