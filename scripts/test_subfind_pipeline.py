import importlib.util
import json
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pipe", here / "derive_subfind_relations.py")
pipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipe)

rng = np.random.default_rng(1)
h, box_ckpc_h = 0.6774, 75000.0
n_halo = 4000
logmh = rng.uniform(10.5, 13.5, n_halo)
logms = logmh - 1.7 + rng.normal(0, 0.15, n_halo)
sfr = np.where(rng.random(n_halo) < 0.7, 10 ** (0.8 * (logms - 10) + rng.normal(0, 0.2, n_halo)), 0.0)
rad = 10 ** (0.2 * (logms - 10) + 0.5)
mf = np.zeros((n_halo, 10))
mf[:, 0], mf[:, 4] = 0.74, 0.0074

with tempfile.TemporaryDirectory() as tmp:
    gdir = Path(tmp) / "groups_099"
    gdir.mkdir()
    for chunk, idx in enumerate(np.array_split(np.arange(n_halo), 3)):
        with h5py.File(gdir / f"fof_subhalo_tab_099.{chunk}.hdf5", "w") as f:
            f.create_group("Header").attrs.update({"Redshift": 0.0, "Time": 1.0, "BoxSize": box_ckpc_h})
            s, g = f.create_group("Subhalo"), f.create_group("Group")
            mt = np.zeros((len(idx), 6)); mt[:, 4] = 10 ** logms[idx] * h / 1e10
            s["SubhaloMassInRadType"] = mt
            s["SubhaloSFRinRad"] = sfr[idx]
            s["SubhaloFlag"] = np.ones(len(idx), dtype=np.int16)
            hr = np.zeros((len(idx), 6)); hr[:, 4] = rad[idx] * h
            s["SubhaloHalfmassRadType"] = hr
            s["SubhaloBHMass"] = 10 ** (logms[idx] - 3) * h / 1e10
            s["SubhaloGasMetalFractionsSfrWeighted"] = mf[idx]
            s["SubhaloGrNr"] = idx.astype(np.int32)
            s["SubhaloStarMetallicity"] = np.full(len(idx), 0.0127)
            g["GroupFirstSub"] = idx.astype(np.int32)
            g["Group_M_Crit200"] = 10 ** logmh[idx] * h / 1e10
    recs = pipe.derive("TNG100-1", gdir, {99: 0.0}, "2026-10-02")

    fdir = Path(tmp) / "fields_099"
    fdir.mkdir()
    chunks = sorted(gdir.glob("*.hdf5"))
    for kind, fields in (("Subhalo", pipe.FIELDS), ("Group", pipe.GROUP_FIELDS)):
        for field in fields:
            parts = []
            for c in chunks:
                with h5py.File(c, "r") as f:
                    if field in f.get(kind, {}):
                        parts.append(f[kind][field][()])
            with h5py.File(fdir / f"fof_subhalo_tab_099.{kind}.{field}.hdf5", "w") as f:
                f.create_group(kind)[field] = np.concatenate(parts)
    recs_fields = pipe.derive("TNG100-1", fdir, {99: 0.0}, "2026-10-02")

by = {r["relation"]: r for r in recs}
by_fields = {r["relation"]: r for r in recs_fields}
assert all(by[k]["representation"]["points"] == by_fields[k]["representation"]["points"] for k in by), "field-subset downloads must reproduce chunked catalogs"
assert set(by) >= {"gsmf", "sfms", "ssfr", "quenched", "size", "shmr", "bh", "mzr", "zstar"}, sorted(by)
assert all(abs(p["y"]) < 1e-6 for p in by["zstar"]["representation"]["points"]), "stellar metallicity must be in solar units"
box = box_ckpc_h / 1000 / h
total = sum(p["count"] for p in by["gsmf"]["representation"]["points"])
expected = int(np.sum(logms >= np.log10(100 * 1.4e6)))
assert abs(total - expected) <= 2, (total, expected)
phi_sum = sum(10 ** p["y"] * 0.2 for p in by["gsmf"]["representation"]["points"]) * box**3
assert abs(phi_sum - total) / total < 1e-3, "GSMF must integrate back to the galaxy count"
shmr = by["shmr"]["representation"]["points"]
assert all(abs(p["y"] + 1.7) < 0.1 for p in shmr), "SHMR median must recover the injected -1.7 dex ratio"
oh = by["mzr"]["representation"]["points"][0]["y"]
assert abs(oh - (12 + np.log10(0.0074 / 16 / 0.74))) < 1e-3, "O/H conversion must use number ratio"
fq = by["quenched"]["representation"]["points"]
assert all(0.2 < p["y"] < 0.4 for p in fq if p["count"] > 100), "quenched fraction must recover the injected 30 per cent"
size = by["size"]["representation"]["points"]
assert all(abs(p["y"] - (0.2 * (p["x"] - 10) + 0.5)) < 0.06 for p in size), "sizes must be converted from ckpc/h to physical kpc"
assert by["gsmf"]["calibration"] == "target" and by["mzr"]["calibration"] == "prediction", "z=0 calibration targets must be labelled"
print(f"Subfind pipeline tests passed on a synthetic catalog: {len(recs)} relations")
