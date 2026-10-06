import json
import subprocess
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

rng = np.random.default_rng(5)
n, nh = 4000, 4000
logms = rng.uniform(9.5, 12, n)
here = Path(__file__).resolve().parent
for z in (0.0, 2.0):
  with tempfile.TemporaryDirectory() as tmp:
      cat = Path(tmp) / "m100n1024_151.hdf5"
      with h5py.File(cat, "w") as f:
          sa = f.create_group("simulation_attributes")
          sa.attrs.update({"redshift": z, "hubble_constant": 0.68, "omega_matter": 0.3, "boxsize": 100000.0, "boxsize_units": b"kpccm/h"})
          g, hd = f.create_group("galaxy_data"), f.create_group("halo_data")
          def put(grp, key, data, unit=None):
              d = grp.create_dataset(key, data=data)
              if unit:
                  d.attrs["unit"] = unit.encode()
          put(g, "dicts/masses.stellar", 10**logms, "Msun")
          put(g, "sfr", 10 ** (logms - 10), "Msun/yr")
          put(g, "central", np.ones(n, dtype=bool))
          put(g, "parent_halo_index", np.arange(n))
          put(g, "dicts/radii.stellar_half_mass", np.full(n, 2.0 * 0.68 * (1 + z)), "kpccm/h")
          put(g, "dicts/masses.HI", 10 ** (logms - 1), "Msun")
          put(hd, "dicts/masses.m200c", 10 ** (logms + 2), "Msun")
      subprocess.run([sys.executable, str(here / "derive_caesar_relations.py"), "m100n1024", str(cat), "--source", "SYNTHETIC"], check=True, capture_output=True)
  out = here.parent / "data" / "curves" / "caesar-synthetic-m100n1024.json"
  records = json.loads(out.read_text())["records"]
  out.unlink()
  by = {r["relation"]: r for r in records}
  box = 100 / 0.68
  assert abs(sum(10 ** p["y"] * 0.2 for p in by["gsmf"]["representation"]["points"]) * box**3 - sum(p["count"] for p in by["gsmf"]["representation"]["points"])) < 1, f"box must stay comoving cMpc at z={z}"
  assert all(abs(p["y"] - np.log10(2.0)) < 1e-3 for p in by["size"]["representation"]["points"]), "kpccm/h radii must become physical kpc"
  assert all(abs(p["y"] + 2) < 0.05 for p in by["shmr"]["representation"]["points"]), "halo masses must be matched through parent_halo_index"
  assert all(abs(p["y"] + 1) < 1e-3 for p in by["hi-fraction"]["representation"]["points"]), "HI fractions must be HI/M*"
print(f"CAESAR pipeline tests passed on a synthetic catalogue: {sorted(by)}")
