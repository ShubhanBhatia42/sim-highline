"""Writes the small synthetic catalogues in tests/derive-cli/ (one per format) that the derive tests and docs/DERIVE-CLI.md use. Not a simulation: the numbers are drawn from simple laws with known parameters so that tests can check that they are recovered. Usage: python3 scripts/make_derive_fixtures.py (the files are committed; run it only to change them)."""
import sys
from pathlib import Path

import h5py
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "tests" / "derive-cli"
H, OM = 0.6774, 0.3089
BOX_CKPC_H = 25000.0          # 25 comoving Mpc/h
SHMR = -1.7                   # injected log10(M*/M200c) of the centrals
QUENCHED = 0.3                # injected share of galaxies with SFR = 0
SIZE_KPC = lambda lm: 10 ** (0.2 * (lm - 10) + 0.5)


def galaxies(seed, n, lo=8.0, hi=11.4):
    rng = np.random.default_rng(seed)
    logms = rng.uniform(lo, hi, n)
    logmh = logms - SHMR + rng.normal(0, 0.1, n)
    sfr = np.where(rng.random(n) < QUENCHED, 0.0, 10 ** (0.8 * (logms - 10) + rng.normal(0, 0.2, n)))
    return logms, logmh, sfr


def gz(f, name, data):
    f.create_dataset(name, data=data, compression="gzip", compression_opts=9)


def subfind():
    n = 2000
    logms, logmh, sfr = galaxies(11, n)
    mf = np.zeros((n, 10), dtype="f4"); mf[:, 0], mf[:, 4] = 0.74, 0.0074
    folder = OUT / "subfind" / "groups_099"
    folder.mkdir(parents=True, exist_ok=True)
    for chunk, idx in enumerate(np.array_split(np.arange(n), 2)):
        with h5py.File(folder / f"fof_subhalo_tab_099.{chunk}.hdf5", "w") as f:
            f.create_group("Header").attrs.update({"Redshift": 0.0, "Time": 1.0, "BoxSize": BOX_CKPC_H, "HubbleParam": H, "Omega0": OM, "OmegaLambda": 1 - OM})
            f.create_group("Parameters").attrs.update({"UnitLength_in_cm": 3.085678e21, "UnitMass_in_g": 1.989e43, "UnitVelocity_in_cm_per_s": 1e5})
            s, g = f.create_group("Subhalo"), f.create_group("Group")
            mt = np.zeros((len(idx), 6), dtype="f8"); mt[:, 4] = 10 ** logms[idx] * H / 1e10
            gz(s, "SubhaloMassInRadType", mt)
            gz(s, "SubhaloSFRinRad", sfr[idx].astype("f4"))
            gz(s, "SubhaloFlag", np.ones(len(idx), dtype="i1"))
            hr = np.zeros((len(idx), 6), dtype="f4"); hr[:, 4] = SIZE_KPC(logms[idx]) * H
            gz(s, "SubhaloHalfmassRadType", hr)
            gz(s, "SubhaloBHMass", (10 ** (logms[idx] - 3) * H / 1e10).astype("f4"))
            gz(s, "SubhaloGasMetalFractionsSfrWeighted", mf[idx])
            gz(s, "SubhaloGrNr", idx.astype("i4"))
            gz(s, "SubhaloStarMetallicity", np.full(len(idx), 0.0127, dtype="f4"))
            gz(g, "GroupFirstSub", idx.astype("i4"))
            gz(g, "Group_M_Crit200", (10 ** logmh[idx] * H / 1e10))


def caesar():
    n, z, h, om = 2000, 2.0, 0.68, 0.3
    logms, logmh, sfr = galaxies(12, n, 8.5, 11.4)
    folder = OUT / "caesar"
    folder.mkdir(parents=True, exist_ok=True)
    with h5py.File(folder / "m50n512_040.hdf5", "w") as f:
        sa = f.create_group("simulation_attributes")
        sa.attrs.update({"redshift": z, "hubble_constant": h, "omega_matter": om, "boxsize": 50000.0, "boxsize_units": b"kpccm/h"})
        g, hd = f.create_group("galaxy_data"), f.create_group("halo_data")

        def put(grp, key, data, unit):
            d = grp.create_dataset(key, data=data, compression="gzip", compression_opts=9)
            d.attrs["unit"] = unit.encode()
        put(g, "dicts/masses.stellar", 10 ** logms, "Msun")
        put(g, "sfr", sfr, "Msun/yr")
        g.create_dataset("central", data=np.ones(n, dtype=bool))
        g.create_dataset("parent_halo_index", data=np.arange(n))
        put(g, "dicts/radii.stellar_half_mass", SIZE_KPC(logms) * h * (1 + z), "kpccm/h")   # a physical radius r is stored as r h (1+z) comoving kpc/h
        put(g, "dicts/masses.HI", 10 ** (logms - 1), "Msun")
        put(hd, "dicts/masses.m200c", 10 ** logmh, "Msun")


def soap():
    n, h, om = 2000, 0.681, 0.306
    logms, logmh, sfr = galaxies(13, n, 8.5, 11.6)
    cen = np.random.default_rng(14).random(n) < 0.8
    conv = "Conversion factor to physical CGS (including cosmological corrections)"
    folder = OUT / "soap"
    folder.mkdir(parents=True, exist_ok=True)
    with h5py.File(folder / "halo_properties_0050.hdf5", "w") as f:
        f.create_group("Header").attrs.update({"Redshift": [0.0], "BoxSize": np.array([50.0, 50.0, 50.0])})
        f.create_group("Cosmology").attrs.update({"h": [h], "Omega_m": [om]})
        g = f.create_group("ExclusiveSphere/50kpc")
        g.create_dataset("StellarMass", data=10 ** logms / 1e10, compression="gzip", compression_opts=9).attrs[conv] = [1.98847e43]
        g.create_dataset("StarFormationRate", data=sfr, compression="gzip", compression_opts=9).attrs[conv] = [1.98847e33 / 3.15576e7]
        g.create_dataset("HalfMassRadiusStars", data=SIZE_KPC(logms), compression="gzip", compression_opts=9).attrs[conv] = [3.0856775814913673e21]
        f.create_group("ExclusiveSphere/30kpc")
        f["InputHalos/IsCentral"] = cen.astype(int)
        f.create_dataset("SO/200_crit/TotalMass", data=np.where(cen, 10 ** logmh / 1e10, 0), compression="gzip", compression_opts=9).attrs[conv] = [1.98847e43]


def eagle():
    folder = OUT / "eagle"
    folder.mkdir(parents=True, exist_ok=True)
    rows = ["# synthetic table with the columns of the documented EAGLE database query (docs/DERIVE-CLI.md); not EAGLE data"]
    rows.append("GalaxyID,SnapNum,Redshift,SubGroupNumber,Mass_Star,SFR,Mass_BH,R_halfmass30,Group_M_Crit200")
    gid = 0
    for seed, snap, z, lo in ((15, 28, 0.0, 8.0), (16, 19, 1.0, 8.0)):
        logms, logmh, sfr = galaxies(seed, 1000, lo, 11.4)
        sub = (np.random.default_rng(seed + 100).random(1000) < 0.25).astype(int)
        for k in range(1000):
            gid += 1
            rows.append(f"{gid},{snap},{z},{sub[k]},{10 ** logms[k]:.6g},{sfr[k]:.6g},{10 ** (logms[k] - 3):.6g},{SIZE_KPC(logms[k]):.6g},{10 ** logmh[k]:.6g}")
    (folder / "eagle-export.csv").write_text("\n".join(rows) + "\n")


if __name__ == "__main__":
    for fn in (subfind, caesar, soap, eagle):
        fn()
    print("written to", OUT, sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()), "bytes")
