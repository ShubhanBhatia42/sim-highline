import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import h5py
import numpy as np

from derive_subfind_relations import DM, MIN_PER_BIN, relations_from_arrays, update_digest

MIN_STAR_PARTICLES = 100
RUNS = {"m100n1024": 1.82e7, "m50n512": 1.82e7, "m25n512": 2.28e6}
HALO_MASS_KEYS = ("dicts/masses.m200c", "dicts/virial_quantities.m200c", "dicts/masses.m200")
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


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from CAESAR catalogues (SIMBA and other CAESAR-processed runs).")
    ap.add_argument("run", help=f"one of {sorted(RUNS)} or a custom label with --mbar")
    ap.add_argument("catalogues", nargs="+")
    ap.add_argument("--source", default="SIMBA")
    ap.add_argument("--mbar", type=float)
    args = ap.parse_args()
    mbar = args.mbar or RUNS.get(args.run)
    if mbar is None:
        raise SystemExit("unknown run: pass --mbar")
    records = []
    for path in args.catalogues:
        digest = hashlib.sha256()
        update_digest(digest, path)
        with h5py.File(path, "r") as f:
            sa = f["simulation_attributes"].attrs
            z, h = float(sa["redshift"]), float(sa["hubble_constant"])
            a = 1 / (1 + z)
            om = float(sa.get("omega_matter", 0.3))
            box_units = sa["boxsize_units"].decode() if isinstance(sa["boxsize_units"], bytes) else str(sa["boxsize_units"])
            box_kpc = float(np.atleast_1d(sa["boxsize"])[0]) * {"kpccm": 1, "kpccm/h": 1 / h, "kpc": 1 / a, "Mpccm": 1e3, "Mpccm/h": 1e3 / h}.get(box_units.replace(" ", ""), np.nan)
            if not np.isfinite(box_kpc):
                raise SystemExit(f"{path}: box units '{box_units}' not recognised")
            gal, halo = f["galaxy_data"], f["halo_data"]
            mstar = to_physical(gal["dicts/masses.stellar"], a, h, "mass")
            sfr = to_physical(gal["sfr"], a, h, "sfr")
            central = gal["central"][()].astype(bool)
            hkey = next((k for k in HALO_MASS_KEYS if k in halo), None)
            if hkey is None:
                raise SystemExit(f"{path}: none of {HALO_MASS_KEYS} in halo_data; available: {sorted(halo['dicts'].keys())[:40]}")
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
        spec = {"source": args.source, "run": args.run, "h": h, "Om": om, "box": box_kpc / 1e3, "snap": None, "z": z, "z_nominal": round(z, 2),
                "massDefinition": "caesar-6dfof-galaxy-total", "sizeDefinition": "stellar-half-mass-3d-bound", "halo": hkey.split("/")[-1],
                "provenance": {"tier": "catalog-derived", "citation": f"{args.source} {args.run} CAESAR catalogue {Path(path).name}; relations derived by sim-highline", "doi": None,
                               "url": "https://simba.roe.ac.uk/", "retrieved": date.today().isoformat(), "sourceMember": Path(path).name,
                               "checksumSha256": digest.hexdigest()},
                "warning": (f"Derived by scripts/derive_caesar_relations.py with the same cuts as the other pipelines (M* >= {MIN_STAR_PARTICLES} gas particle masses, {DM} dex bins, "
                            f">= {MIN_PER_BIN} per median). CAESAR stellar masses are totals of 6D-FOF galaxy members, not apertures; units read from each dataset's 'unit' attribute."),
                "metallicityNote": "", "calibratedAtLowZ": ("gsmf",)}
        records += relations_from_arrays(spec, arrays)
    out = Path(__file__).resolve().parent.parent / "data" / "curves" / f"caesar-{args.source.lower()}-{args.run.lower()}.json"
    out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
    print(f"{args.source} {args.run}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
