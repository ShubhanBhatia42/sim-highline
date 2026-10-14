"""Validation V1 of docs/PROTOCOL-model-form.md (with amendment A1): do the CAMELS star formation logs, read with the volume used in scripts/ingest_camels_sfrd.py, account for the stellar mass of the z = 0 catalogues?

For 12 randomly chosen IllustrisTNG LH simulations (seed fixed) the stellar mass in all subhalos of groups_090.hdf5 (z = 0) is divided by the time integral of the logged star formation rate (the
`formedMassMsun` field of data/ensembles/camels-sfrd.json). The ratio is the fraction of the mass that was formed and still sits in subhalos: one minus the mass-loss fraction of the stellar populations
(about 0.3 to 0.45 for a Chabrier IMF over a Hubble time) times the share of stars inside subhalos, so about 0.5 to 0.7. That ratio does not depend on the box volume, so A1 adds a volume check: the
comoving volume from the catalogue's own BoxSize and HubbleParam is compared with the volume stored by the ingest, the stored SFRD bins times that volume and the bin durations are integrated and compared with
the stored formed mass, the header redshift is checked to be 0 and the number of simulations in the stored file is checked. Writes data/ensembles/camels-closure.json."""
import io
import json
import sys
import urllib.request
from pathlib import Path

import h5py
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ingest_camels_sfrd as ing

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
    zedges = np.array(data["zEdges"])
    for name in names:
        raw = fetch(f"{BASE}/Sims/IllustrisTNG/LH/{name}/groups_090.hdf5")
        with h5py.File(io.BytesIO(raw), "r") as f:
            h = float(f["Header"].attrs["HubbleParam"])
            mstar = float(f["Subhalo"]["SubhaloMassType"][:, 4].sum()) * 1e10 / h
            z = float(f["Header"].attrs["Redshift"])
            box = float(f["Header"].attrs["BoxSize"])  # ckpc/h
        sim = sims[name]
        formed = sim["formedMassMsun"]
        vol_cat = (box / 1000.0 / h) ** 3
        om = sim["params"]["Om"]
        dt = ing.time_of_a(1.0 / (1.0 + zedges[:-1]), om) - ing.time_of_a(1.0 / (1.0 + zedges[1:]), om)
        s_ = np.array([np.nan if v is None else 10.0 ** v for v in sim["sfrd"]])
        from_bins = float(np.nansum(s_ * data["volumeCMpc3"] * dt))
        rows.append({"sim": name, "redshift": round(z, 4), "stellar_mass_in_subhalos_Msun": float(f"{mstar:.4e}"), "formed_mass_Msun": formed, "ratio": round(mstar / formed, 3), "box_ckpc_h": box, "h_catalogue": h,
                     "volume_catalogue_cMpc3": round(vol_cat, 1), "volume_stored_cMpc3": data["volumeCMpc3"], "volume_ratio": round(data["volumeCMpc3"] / vol_cat, 5), "formed_from_stored_bins_Msun": float(f"{from_bins:.4e}"), "integral_over_formed": round(from_bins / formed, 4)})
        print(name, rows[-1]["ratio"], rows[-1]["volume_ratio"], rows[-1]["integral_over_formed"])
    ratios = [r["ratio"] for r in rows]
    n_lh = {k: len(v["LH"]) for k, v in data["suites"].items()}
    n_cv = {k: len(v["CV"]) for k, v in data["suites"].items()}
    vr = [r["volume_ratio"] for r in rows]
    ir = [r["integral_over_formed"] for r in rows]
    vol = {"volume_ratio": float(np.median(vr)), "volume_ratio_min": min(vr), "volume_ratio_max": max(vr), "integral_over_formed_min": min(ir), "integral_over_formed_max": max(ir), "n_lh": min(n_lh.values()), "n_cv": min(n_cv.values()),
           "max_header_redshift": max(r["redshift"] for r in rows), "required": {"volume_ratio": [0.995, 1.005], "integral_over_formed": [0.95, 1.05], "n_lh": 1000, "n_cv": 27, "max_header_redshift": 0.01}}
    vol["passed"] = bool(all(0.995 <= v <= 1.005 for v in vr) and all(0.95 <= v <= 1.05 for v in ir) and all(v == 1000 for v in n_lh.values()) and all(v == 27 for v in n_cv.values()) and vol["max_header_redshift"] < 0.01)
    out = {"description": __doc__.split("\n\n")[0], "seed": SEED, "rows": rows, "volume_check": vol, "ratio_min": min(ratios), "ratio_max": max(ratios), "ratio_median": float(np.median(ratios)), "range_required": [0.45, 0.75],
           "mass_passed": bool(all(0.45 <= r <= 0.75 for r in ratios))}
    out["passed"] = bool(out["mass_passed"] and vol["passed"])
    (ROOT / "data" / "ensembles" / "camels-closure.json").write_text(json.dumps(out, indent=1) + "\n")
    print("V1:", "passed" if out["passed"] else "FAILED", f"(mass ratio {min(ratios):.2f} to {max(ratios):.2f}; volume {vol['volume_ratio_min']} to {vol['volume_ratio_max']}; integral/formed {vol['integral_over_formed_min']} to {vol['integral_over_formed_max']})")


if __name__ == "__main__":
    main()
