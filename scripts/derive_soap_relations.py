import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import h5py
import numpy as np

from derive_subfind_relations import DM, MIN_PER_BIN, relations_from_arrays, update_digest

MSUN_G, KPC_CM, YR_S = 1.98847e33, 3.0856775814913673e21, 3.15576e7
MIN_STAR_PARTICLES = 100
SUITES = {
    "flamingo": {"source": "FLAMINGO", "url": "https://flamingo.strw.leidenuniv.nl/", "citation": "FLAMINGO data release (Helly et al. 2026), SOAP halo catalogue",
                 "calibrated": ("gsmf",), "h": 0.681, "Om": 0.306},
    "colibre": {"source": "COLIBRE", "url": "https://colibre-simulations.org/", "citation": "COLIBRE SOAP halo catalogue", "calibrated": ("gsmf", "size", "bh"), "h": 0.681, "Om": 0.306},
}


def physical(f, path, factor):
    d = f[path]
    conv = d.attrs.get("Conversion factor to physical CGS (including cosmological corrections)")
    if conv is None:
        raise SystemExit(f"{path}: missing CGS conversion attribute; refusing to guess units")
    return d[()].astype(float) * float(np.atleast_1d(conv)[0]) / factor


def first(f, *paths):
    for p in paths:
        if p in f:
            return p
    return None


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from SWIFT/SOAP halo catalogues (FLAMINGO, COLIBRE).")
    ap.add_argument("suite", choices=sorted(SUITES))
    ap.add_argument("run", help="run label, e.g. L1_m8")
    ap.add_argument("mbar", type=float, help="initial baryon particle mass in Msun")
    ap.add_argument("catalogues", nargs="+", help="SOAP halo_properties_NNNN.hdf5 files")
    ap.add_argument("--aperture", default="50kpc")
    args = ap.parse_args()
    suite, records = SUITES[args.suite], []
    for path in args.catalogues:
        sha = hashlib.sha256()
        update_digest(sha, path)
        digest = sha.hexdigest()
        with h5py.File(path, "r") as f:
            header = dict(f["Header"].attrs)
            z = float(np.atleast_1d(header["Redshift"])[0])
            box = float(np.atleast_1d(header["BoxSize"])[0])
            if not 10 < box < 5000:
                raise SystemExit(f"{path}: BoxSize {box} is not in comoving Mpc as expected")
            es = f"ExclusiveSphere/{args.aperture}"
            mstar = physical(f, f"{es}/StellarMass", MSUN_G)
            sfr = physical(f, f"{es}/StarFormationRate", MSUN_G / YR_S)
            central = f["InputHalos/IsCentral"][()] == 1
            m200 = physical(f, "SO/200_crit/TotalMass", MSUN_G)
            rpath = first(f, f"{es}/HalfMassRadiusStars", "BoundSubhalo/HalfMassRadiusStars")
            bpath = first(f, f"{es}/MostMassiveBlackHoleMass", "BoundSubhalo/MostMassiveBlackHoleMass")
            arrays = {"logm": np.log10(np.where(mstar > 0, mstar, np.nan)), "sfr": sfr, "resolved": mstar >= MIN_STAR_PARTICLES * args.mbar, "central": central,
                      "logmh": np.log10(np.where(central & (m200 > 0), m200, np.nan))}
            if rpath:
                arrays["rhalf_kpc"] = physical(f, rpath, KPC_CM)
            if bpath:
                arrays["mbh"] = physical(f, bpath, MSUN_G)
        spec = {"source": suite["source"], "run": args.run, "h": suite["h"], "Om": suite["Om"], "box": box, "snap": None, "z": z, "z_nominal": round(z, 2),
                "massDefinition": f"aperture-{args.aperture.replace('kpc', 'pkpc')}-exclusive", "sizeDefinition": f"stellar-half-mass-3d-{'aperture' if rpath and 'Exclusive' in rpath else 'bound'}",
                "provenance": {"tier": "catalog-derived", "citation": f"{suite['citation']} {Path(path).name}; relations derived by sim-highline", "doi": None, "url": suite["url"],
                               "retrieved": date.today().isoformat(), "sourceMember": Path(path).name, "checksumSha256": digest},
                "warning": (f"Derived by scripts/derive_soap_relations.py with the same cuts as the Subfind/EAGLE pipelines (M* >= {MIN_STAR_PARTICLES} baryon particle masses, {DM} dex bins, "
                            f">= {MIN_PER_BIN} galaxies per median); masses and SFRs in the {args.aperture} exclusive sphere; units from the catalogue's CGS conversion attributes."),
                "metallicityNote": "", "calibratedAtLowZ": suite["calibrated"]}
        records += relations_from_arrays(spec, arrays)
    out = Path(__file__).resolve().parent.parent / "data" / "curves" / f"soap-{args.suite}-{args.run.lower()}.json"
    out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
    print(f"{suite['source']} {args.run}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
