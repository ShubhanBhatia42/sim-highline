import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import yaml

source_file = Path(sys.argv[1] if len(sys.argv) > 1 else "2509.07960.yml")
output = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "colibre-gsmf.json"
url = "https://colibre.strw.leidenuniv.nl/paper_data/2509.07960.yml"
RUNS = {"COLIBRE_L025m5": ("m5 (L025)", 2.3e5), "COLIBRE_L025m6": ("m6 (L025)", 1.84e6), "COLIBRE_L025m7": ("m7 (L025)", 1.47e7), "COLIBRE_L050m5": ("m5 (L050)", 2.3e5), "COLIBRE_L100m5": ("m5 (L100)", 2.3e5), "COLIBRE_L200m6": ("m6 (L200)", 1.84e6), "COLIBRE_L400m7": ("m7 (L400)", 1.47e7), "COLIBRE_L200m7h": ("m7 hybrid AGN (L200)", 1.47e7)}
MIN_PARTICLES = 100

raw = source_file.read_bytes()
data = yaml.safe_load(raw)
digest = hashlib.sha256(raw).hexdigest()
missing = [k for k in RUNS if k not in data]
if len(missing) == len(RUNS):
    raise SystemExit(f"{source_file}: none of {sorted(RUNS)} found; top-level keys are {sorted(data)}")
if missing:
    print(f"not in {source_file.name}: {missing}")
records = []
for key, (run, mpart) in RUNS.items():
    for ztag, block in (data.get(key, {}).get("gsmf_raw") or {}).items():
        z = float(ztag[1:])
        x, y, n = (np.asarray(block.get(k, []), dtype=float) for k in ("log10_bin_centers", "log10_gsmf_values", "bin_counts"))
        keep = (n >= 1) & (x - 0.1 >= np.log10(MIN_PARTICLES * mpart))
        points = []
        for xv, yv, nv in zip(x[keep], y[keep], n[keep]):
            lo, hi = max(nv - np.sqrt(nv), 0.5) / nv, (nv + np.sqrt(nv)) / nv
            points.append({"x": round(float(xv), 3), "y": round(float(yv), 4), "yLow": round(float(yv + np.log10(lo)), 4), "yHigh": round(float(yv + np.log10(hi)), 4), "count": int(nv)})
        if len(points) < 2:
            continue
        records.append({
            "id": f"chaikin26.colibre.{key.split('_')[1].lower()}.gsmf.z{z:g}", "source": "COLIBRE", "run": run, "kind": "simulation", "relation": "gsmf",
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
            "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy number density per dex (raw, no Eddington bias)", "yUnit": "log10(cMpc^-3 dex^-1)"},
            "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": points},
            "scatter": None,
            "selection": {"population": "all galaxies", "warning": f"Chaikin et al. 2026 published GSMF (gsmf_raw, 0.2 dex bins). sim-highline keeps bins whose lower edge exceeds {MIN_PARTICLES} baryonic particle masses and attaches Poisson errors from the published bin counts; box-to-box cosmic variance is not included. The Eddington-bias-convolved variant in the same file is not ingested."},
            "definitions": {"massDefinition": "unspecified", "imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "densityFrame": "comoving", "population": "all"},
            "provenance": {"tier": "official-table", "citation": "Chaikin et al. 2026, MNRAS 548, stag740 (doi:10.1093/mnras/stag740), COLIBRE plot data", "doi": "10.1093/mnras/stag740", "url": url,
                           "retrieved": date.today().isoformat(), "checksumSha256": digest, "sourceMember": f"{key}/gsmf_raw/{ztag}"},
            "calibration": "target" if z <= 0.1 else "prediction", "rankable": True,
            "notes": "COLIBRE is calibrated on the z~0 GSMF; z<=0.1 entries are calibration targets."})
output.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Ingested {len(records)} COLIBRE GSMF records from {source_file}")
