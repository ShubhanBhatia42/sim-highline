import json
from pathlib import Path

import numpy as np

SUITES = {
    "core": ("Core suite (z=0)", 0.0, "M200mean", "log10 M200m (200x mean matter density, dark matter only, Rockstar)", "log10 M*,90 (sphere enclosing 90% of stellar mass within 20 kpc)", "spherical-90pc-of-20kpc",
             "Table 1", "Primary hosts chosen by z=0 halo mass at fixed mass scales; isolated except the ELVIS on FIRE pairs. Mixed cosmologies (AGORA, Planck and others).", """
m09 2.60e9 1.5e4
m10q 8.23e9 4.8e6
m10v 1.08e10 3.1e5
m11b 4.65e10 4.5e7
m11i 7.77e10 9.2e8
m11q 1.63e11 3.7e8
m11e 1.68e11 1.4e9
m11h 2.07e11 3.6e9
m11d 3.23e11 3.9e9
m12z 9.25e11 2.0e10
m12w 1.08e12 5.7e10
m12r 1.10e12 1.7e10
m12i 1.18e12 6.3e10
m12c 1.35e12 5.8e10
m12b 1.43e12 8.5e10
m12m 1.58e12 1.1e11
m12f 1.71e12 7.9e10
Juliet 1.10e12 3.8e10
Romeo 1.32e12 6.6e10
Louise 1.15e12 2.6e10
Thelma 1.43e12 7.1e10
Remus 1.22e12 4.6e10
Romulus 2.08e12 9.1e10"""),
    "massive": ("Massive Halo suite (z=1)", 1.0, "Mvir-BryanNorman", "log10 Mvir (Bryan & Norman 1998)", "log10 M* within 0.1 Rvir", "sphere-0.1Rvir",
                "Table 2", "No AGN feedback: these galaxies are known to be overly massive with ultradense nuclei, which is why they were only run to z=1.", """
A1 3.92e12 2.75e11
A2 7.75e12 4.10e11
A4 4.54e12 2.34e11
A8 1.27e13 5.36e11"""),
    "highz": ("High Redshift suite (z=5)", 5.0, "Mvir-BryanNorman", "log10 Mvir (Bryan & Norman 1998)", "log10 M* within Rvir", "sphere-Rvir",
              "Table 3", "Haloes chosen across Mvir ~1e9-1e12 Msun at z=5 from 11 and 43 Mpc boxes; reionization at z~10 in this model is likely too early.", """
z5m12b 8.7e11 2.6e10
z5m12c 7.9e11 1.8e10
z5m12d 5.7e11 1.2e10
z5m12e 5.0e11 1.4e10
z5m12a 4.5e11 5.4e9
z5m11f 3.1e11 4.7e9
z5m11e 2.5e11 2.5e9
z5m11g 2.0e11 1.9e9
z5m11d 1.4e11 1.6e9
z5m11h 1.0e11 1.6e9
z5m11c 7.6e10 9.5e8
z5m11i 5.2e10 2.8e8
z5m11b 4.0e10 1.7e8
z5m11a 4.2e10 1.2e8
z5m10f 3.3e10 1.6e8
z5m10e 2.6e10 3.9e7
z5m10d 1.9e10 4.8e7
z5m10c 1.3e10 5.6e7
z5m10b 1.2e10 3.4e7
z5m10a 6.6e9 1.5e7
z5m09b 3.9e9 2.8e6
z5m09a 2.4e9 1.6e6"""),
}
COUNTS = {"core": 23, "massive": 4, "highz": 22}
records = []
for key, (run, z, hdef, xdef, ydef, mdef, table, warn, text) in SUITES.items():
    rows = [r.split() for r in text.strip().splitlines()]
    assert len(rows) == COUNTS[key] and len({r[0] for r in rows}) == len(rows), key
    mh, ms = (np.array([float(r[i]) for r in rows]) for i in (1, 2))
    pts = sorted(({"x": round(float(np.log10(a)), 4), "y": round(float(np.log10(b / a)), 4)} for a, b in zip(mh, ms)), key=lambda p: p["x"])
    records.append({
        "id": f"wetzel23.fire2.shmr.{key}.z{z:g}", "source": "FIRE-2", "run": run, "kind": "simulation", "relation": "shmr",
        "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": xdef, "xUnit": "log10(Msun)", "yDefinition": f"{ydef} minus halo mass", "yUnit": "dex"},
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "unspecified", "connect": False, "points": pts}, "scatter": None,
        "selection": {"population": "primary zoom hosts", "warning": f"Individual primary galaxies of the FIRE-2 public data release. {warn} Halo masses are dark-matter-only where stated by the paper."},
        "definitions": {"imf": "kroupa01", "massDefinition": mdef, "haloMassDefinition": hdef, "haloMassHistory": "current", "population": "primary-zoom-hosts"},
        "provenance": {"tier": "published-table", "citation": f"Wetzel et al. 2023, ApJS 265, 44 (FIRE-2 public data release), {table}", "doi": "10.3847/1538-4365/acb99a",
                       "url": "https://arxiv.org/abs/2202.06969", "retrieved": "2026-10-05", "sourceMember": f"{table}, transcribed from the arXiv PDF"},
        "calibration": "prediction", "rankable": False,
        "notes": "FIRE-2 data are CC-BY-4.0; cite Wetzel et al. 2023 and the per-simulation papers listed in the table."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "fire2-wetzel23.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"FIRE-2: {sum(COUNTS.values())} galaxies in {len(records)} records")
