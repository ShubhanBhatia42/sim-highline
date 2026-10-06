import json
import subprocess
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

C = "Conversion factor to physical CGS (including cosmological corrections)"
rng = np.random.default_rng(3)
n = 5000
logms = rng.uniform(9, 12, n)
central = rng.random(n) < 0.7
here = Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as tmp:
    cat = Path(tmp) / "halo_properties_0077.hdf5"
    with h5py.File(cat, "w") as f:
        f.create_group("Header").attrs.update({"Redshift": [0.0], "BoxSize": np.array([100.0, 100, 100])})
        g = f.create_group("ExclusiveSphere/50kpc")
        g.create_dataset("StellarMass", data=10**logms / 1e10).attrs[C] = [1.98847e43]
        g.create_dataset("StarFormationRate", data=10 ** (logms - 10)).attrs[C] = [1.98847e33 / 3.15576e7]
        g.create_dataset("HalfMassRadiusStars", data=np.full(n, 3.0)).attrs[C] = [3.0856775814913673e21]
        f["InputHalos/IsCentral"] = central.astype(int)
        f.create_dataset("SO/200_crit/TotalMass", data=np.where(central, 10 ** (logms + 1.8) / 1e10, 0)).attrs[C] = [1.98847e43]
    subprocess.run([sys.executable, str(here / "derive_soap_relations.py"), "flamingo", "SYNTHETIC", "1e6", str(cat)], check=True, capture_output=True)
out = here.parent / "data" / "curves" / "soap-flamingo-synthetic.json"
records = json.loads(out.read_text())["records"]
out.unlink()
by = {r["relation"]: r for r in records}
assert sum(p["count"] for p in by["gsmf"]["representation"]["points"]) == n, "GSMF must count every resolved galaxy"
assert all(abs(p["y"] + 1.8) < 0.05 for p in by["shmr"]["representation"]["points"]), "SO/200_crit masses must give the injected ratio"
assert all(abs(p["y"] + 10) < 0.05 for p in by["ssfr"]["representation"]["points"]), "SFR units must come from the CGS conversion attribute"
assert all(abs(p["y"] - np.log10(3.0)) < 1e-3 for p in by["size"]["representation"]["points"]), "radii must be converted to physical kpc"
print(f"SOAP pipeline tests passed on a synthetic catalogue: {sorted(by)}")
