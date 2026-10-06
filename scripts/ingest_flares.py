import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import h5py
import numpy as np

data_file = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/louisarts_Arts24LRD/data/raw_FLARES_data.hdf5")
weights_file = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/flares/weight_files/weights_grid.txt")
h, om, mbar = 0.6777, 0.307, 1.81e6
radius = 14.0 / h
volume = 4 / 3 * np.pi * radius**3
edges = np.arange(8.2, 11.81, 0.2)
min_mass, min_count = 100 * mbar, 10
retrieved = date.today().isoformat()

lines = weights_file.read_text().strip().splitlines()
weights = np.array([float(l.split(",")[-1]) for l in lines[1:]])
digest = hashlib.sha256(data_file.read_bytes() + weights_file.read_bytes()).hexdigest()


def age_gyr(z):
    ol, th = 1 - om, 977.8 / (100 * h)
    return 2 * th / (3 * np.sqrt(ol)) * np.arcsinh(np.sqrt(ol / om) / (1 + z) ** 1.5)


def weighted_quantiles(y, w, qs):
    order = np.argsort(y)
    y, w = y[order], w[order]
    c = np.cumsum(w) - 0.5 * w
    c /= np.sum(w)
    return np.interp(qs, c, y)


records = []
with h5py.File(data_file, "r") as f:
    regions = sorted(f.keys())
    if len(regions) != len(weights):
        raise SystemExit(f"{len(regions)} regions but {len(weights)} weights")
    for tag in sorted(f[regions[0]].keys()):
        z = float(tag.split("_z")[1].replace("p", "."))
        logm, sfr, w = [], [], []
        for i, r in enumerate(regions):
            g = f[r][tag]["Galaxy"]
            m = g["Mstar_30"][()] * 1e10
            keep = m >= min_mass
            logm.append(np.log10(m[keep]))
            sfr.append(g["SFR_inst_30"][()][keep])
            w.append(np.full(keep.sum(), weights[i]))
        logm, sfr, w = np.concatenate(logm), np.concatenate(sfr), np.concatenate(w)
        hist, err2 = np.zeros(len(edges) - 1), np.zeros(len(edges) - 1)
        counts = np.zeros(len(edges) - 1, dtype=int)
        for i, r in enumerate(regions):
            sel = w == weights[i]
            n_i, _ = np.histogram(logm[sel], bins=edges)
            hist += n_i * weights[i]
            err2 += n_i * weights[i] ** 2
            counts += n_i
        dm = edges[1] - edges[0]
        phi, sig = hist / (volume * dm), np.sqrt(err2) / (volume * dm)
        gsmf = [{"x": round(float(c), 3), "y": round(float(np.log10(p)), 4), "yLow": round(float(np.log10(max(p - s, p * 0.05))), 4), "yHigh": round(float(np.log10(p + s)), 4), "count": int(n)}
                for c, p, s, n in zip((edges[1:] + edges[:-1]) / 2, phi, sig, counts) if n >= 1]
        ssfr = sfr / 10**logm
        sf = (ssfr > 0.2 / (age_gyr(z) * 1e9)) & (sfr > 0)
        sfms = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = sf & (logm >= lo) & (logm < hi)
            if m.sum() >= min_count:
                q16, q50, q84 = weighted_quantiles(np.log10(sfr[m]), w[m], [0.16, 0.5, 0.84])
                sfms.append({"x": round((lo + hi) / 2, 3), "y": round(float(q50), 4), "yLow": round(float(q16), 4), "yHigh": round(float(q84), 4), "count": int(m.sum())})
        common = {"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": om}}
        base = {"source": "FLARES", "run": "40 resimulated regions (EAGLE AGNdT9 model)", "kind": "simulation",
                "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "snapshot", "snapshot": int(tag[:3])},
                "scatter": None, "calibration": "prediction", "rankable": True,
                "provenance": {"tier": "catalog-derived", "citation": "FLARES (Lovell et al. 2021; Vijayan et al. 2021) galaxy properties as redistributed in github.com/louisarts/Arts24LRD (data/raw_FLARES_data.hdf5); region weights from github.com/flaresimulations/flares (weight_files/weights_grid.txt); relations derived by sim-highline",
                               "doi": None, "url": "https://github.com/flaresimulations/flares", "retrieved": retrieved, "checksumSha256": digest,
                               "sourceMember": f"raw_FLARES_data.hdf5:{tag}; weights_grid.txt"},
                "notes": "Composite volume from 40 zoom regions of radius 14 cMpc/h, combined with the official FLARES overdensity weights following the method in the flares repository README."}
        warn = (f"Galaxies with M*(30 pkpc) >= {min_mass:.2g} Msun (100 gas particle masses). Region weights reconstruct a representative volume; "
                "the galaxy table is a third-party extraction of the FLARES master file, so completeness below the published FLARES mass cut is not guaranteed.")
        if len(gsmf) >= 2:
            records.append({**base, "id": f"flares.gsmf.z{z:g}", "relation": "gsmf",
                            "axes": {"xDefinition": "log10 stellar mass (30 pkpc)", "xUnit": "log10(Msun)", "yDefinition": "log10 weighted galaxy number density per dex", "yUnit": "log10(cMpc^-3 dex^-1)"},
                            "domain": {"xMin": gsmf[0]["x"], "xMax": gsmf[-1]["x"]}, "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": gsmf},
                            "selection": {"population": "all", "warning": warn + " Errors are weighted Poisson."},
                            "definitions": {**common, "densityFrame": "comoving", "population": "all"}})
        if len(sfms) >= 2:
            records.append({**base, "id": f"flares.sfms.z{z:g}", "relation": "sfms",
                            "axes": {"xDefinition": "log10 stellar mass (30 pkpc)", "xUnit": "log10(Msun)", "yDefinition": "log10 instantaneous SFR (30 pkpc), weighted median of star-forming galaxies", "yUnit": "log10(Msun/yr)"},
                            "domain": {"xMin": sfms[0]["x"], "xMax": sfms[-1]["x"]}, "representation": {"type": "points", "intervalKind": "scatter", "connect": True, "points": sfms},
                            "selection": {"population": "star-forming", "warning": warn + " Star-forming: sSFR > 0.2/t_age(z), as in the other sim-highline pipelines."},
                            "definitions": {**common, "population": "star-forming", "sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median"}})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "flares.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Ingested {len(records)} FLARES records")
