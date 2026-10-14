"""Validation V1 of docs/PROTOCOL-model-form.md: do the CAMELS star formation logs, read with the volume used in scripts/ingest_camels_sfrd.py, account for the stellar mass of the z = 0 catalogues?

For 12 randomly chosen IllustrisTNG LH simulations (seed fixed) the stellar mass in all subhalos of groups_090.hdf5 (z = 0) is divided by the time integral of the logged star formation rate (the
`formedMassMsun` field of data/ensembles/camels-sfrd.json). The ratio is the fraction of the mass that was formed and still sits in subhalos: one minus the mass-loss fraction of the stellar populations
(about 0.3 to 0.45 for a Chabrier IMF over a Hubble time) times the share of stars inside subhalos, so about 0.5 to 0.7. Writes data/ensembles/camels-closure.json."""
import io
import json
import sys
import urllib.request
from pathlib import Path

import h5py
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://users.flatironinstitute.org/~camels"
SEED = 20261015


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "sim-highline-validate"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main():
    data = json.loads((ROOT / "data" / "ensembles" / "camels-sfrd.json").read_text())
    sims = data["suites"]["IllustrisTNG"]["LH"]
    rng = np.random.default_rng(SEED)
    names = sorted(rng.choice(sorted(sims), size=12, replace=False).tolist(), key=lambda k: int(k.split("_")[1]))
    rows = []
    for name in names:
        raw = fetch(f"{BASE}/Sims/IllustrisTNG/LH/{name}/groups_090.hdf5")
        with h5py.File(io.BytesIO(raw), "r") as f:
            h = float(f["Header"].attrs["HubbleParam"])
            mstar = float(f["Subhalo"]["SubhaloMassType"][:, 4].sum()) * 1e10 / h
            z = float(f["Header"].attrs["Redshift"])
        formed = sims[name]["formedMassMsun"]
        rows.append({"sim": name, "redshift": round(z, 4), "stellar_mass_in_subhalos_Msun": float(f"{mstar:.4e}"), "formed_mass_Msun": formed, "ratio": round(mstar / formed, 3)})
        print(name, rows[-1]["ratio"])
    ratios = [r["ratio"] for r in rows]
    out = {"description": __doc__.split("\n\n")[0], "seed": SEED, "rows": rows, "ratio_min": min(ratios), "ratio_max": max(ratios), "ratio_median": float(np.median(ratios)), "range_required": [0.45, 0.75],
           "passed": bool(all(0.45 <= r <= 0.75 for r in ratios))}
    (ROOT / "data" / "ensembles" / "camels-closure.json").write_text(json.dumps(out, indent=1) + "\n")
    print("V1:", "passed" if out["passed"] else "FAILED", f"(range {min(ratios):.2f} to {max(ratios):.2f})")


if __name__ == "__main__":
    main()
