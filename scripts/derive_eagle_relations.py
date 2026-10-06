import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import numpy as np

from derive_subfind_relations import MIN_PER_BIN, DM, relations_from_arrays

RUNS = {"RefL0100N1504": {"run": "Ref-L100N1504", "box": 100.0, "mbar": 1.81e6}, "RecalL0025N0752": {"run": "Recal-L025N0752", "box": 25.0, "mbar": 2.26e5}}
SNAPS = [28, 27, 23, 19, 15, 12, 10, 8, 6, 5, 4]
MIN_STAR_PARTICLES = 100
QUERY = """
SELECT SH.GalaxyID, SH.SnapNum, SH.Redshift, SH.SubGroupNumber,
       AP.Mass_Star, AP.SFR, AP.Mass_BH, SZ.R_halfmass30, FOF.Group_M_Crit200
FROM {sim}_SubHalo AS SH
JOIN {sim}_Aperture AS AP ON AP.GalaxyID = SH.GalaxyID AND AP.ApertureSize = 30
LEFT JOIN {sim}_Sizes AS SZ ON SZ.GalaxyID = SH.GalaxyID
JOIN {sim}_FOF AS FOF ON FOF.GroupID = SH.GroupID
WHERE SH.SnapNum = {snap} AND AP.Mass_Star >= {mmin}
"""


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from the public EAGLE SQL database (McAlpine et al. 2016).")
    ap.add_argument("sim", choices=sorted(RUNS))
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()
    import eagleSqlTools as sql
    con = sql.connect(args.user, password=args.password)
    meta, records = RUNS[args.sim], []
    for snap in SNAPS:
        query = QUERY.format(sim=args.sim, snap=snap, mmin=MIN_STAR_PARTICLES * meta["mbar"])
        rows = sql.execute_query(con, query)
        if rows is None or len(rows) == 0:
            continue
        z = float(rows["Redshift"][0])
        mstar = np.asarray(rows["Mass_Star"], dtype=float)
        arrays = {"logm": np.log10(mstar), "sfr": np.asarray(rows["SFR"], dtype=float), "resolved": np.ones(len(mstar), dtype=bool),
                  "central": np.asarray(rows["SubGroupNumber"]) == 0,
                  "rhalf_kpc": np.asarray(rows["R_halfmass30"], dtype=float),
                  "logmh": np.log10(np.where(np.asarray(rows["Group_M_Crit200"], dtype=float) > 0, rows["Group_M_Crit200"], np.nan)),
                  "mbh": np.asarray(rows["Mass_BH"], dtype=float)}
        spec = {"source": "EAGLE", "run": meta["run"], "h": 0.6777, "Om": 0.307, "box": meta["box"], "snap": snap, "z": z, "z_nominal": round(z, 2),
                "massDefinition": "aperture-30pkpc", "sizeDefinition": "stellar-half-mass-3d-30pkpc",
                "provenance": {"tier": "catalog-derived", "citation": f"EAGLE {args.sim} public database, snapshot {snap} (McAlpine et al. 2016); relations derived by sim-highline",
                               "doi": None, "url": "https://virgodb.dur.ac.uk/", "retrieved": date.today().isoformat(),
                               "sourceMember": "SQL: " + " ".join(query.split()), "checksumSha256": hashlib.sha256(np.asarray(rows).tobytes()).hexdigest()},
                "warning": (f"Derived by scripts/derive_eagle_relations.py from the public EAGLE database: 30 pkpc apertures for mass, SFR and BH mass; M* >= {MIN_STAR_PARTICLES} baryon particle masses; "
                            f"bins of {DM} dex with >= {MIN_PER_BIN} galaxies for medians. Same cuts as the Subfind pipeline used for TNG/Illustris except the aperture."),
                "metallicityNote": "", "calibratedAtLowZ": ("gsmf", "size", "bh")}
        records += relations_from_arrays(spec, arrays)
    out = Path(__file__).resolve().parent.parent / "data" / "curves" / f"eagle-{args.sim.lower()}.json"
    out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
    print(f"EAGLE {args.sim}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
