import json
import subprocess
from datetime import date
from pathlib import Path

repo, url = "/tmp/bt", "https://github.com/kuanweih/paper-2018"
commit = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
FITS = {
    "bh": {8: (8.25, 0.03, 1.10, 0.14), 9: (8.44, 0.08, 1.19, 0.14), 10: (8.76, 0.20, 1.35, 0.13)},
    "bhsigma": {8: (8.35, 0.08, 5.31, 0.36), 9: (8.50, 0.23, 5.95, 0.40), 10: (8.49, 0.54, 6.06, 0.40)},
}
records = []
for rel, rows in FITS.items():
    for z, (alpha, alpha_err, beta, scatter) in rows.items():
        mass = rel == "bh"
        records.append({
            "id": f"huang18.bluetides.{rel}.z{z}", "source": "BlueTides", "run": "BlueTides (400 cMpc/h)", "kind": "simulation", "relation": rel,
            "epoch": {"zRepresentative": float(z), "zNominal": float(z), "zMin": float(z), "zMax": float(z), "mode": "published-epoch", "snapshot": None},
            "axes": {"xDefinition": "log10 total stellar mass" if mass else "log10 stellar velocity dispersion within the half-mass radius", "xUnit": "log10(Msun)" if mass else "log10(km/s)",
                     "yDefinition": "log10 black-hole mass", "yUnit": "log10(Msun)"},
            "domain": {"xMin": 9.5, "xMax": 11.5} if mass else {"xMin": 1.8, "xMax": 2.5},
            "representation": {"type": "parametric", "equation": "log MBH = alpha + beta (x - x0), ODR fit", "expression": "alpha+beta*(x-(%s))" % ("11" if mass else "log10(200)"),
                               "parameters": {"alpha": alpha, "alphaError": alpha_err, "beta": beta}},
            "scatter": {"value": scatter, "unit": "dex", "meaning": "intrinsic scatter of the fit"},
            "selection": {"population": "BlueTides galaxies hosting black holes above the paper's mass thresholds",
                          "warning": "Fit outputs printed in the authors' public notebook (4_BHM_STM_MSigma.ipynb, 'MM (total)' and 'MS (hm)' cells). The plotted x-range is a conservative choice, not the paper's sample limits."},
            "definitions": {"massDefinition": "total-subhalo", "imf": "unspecified", "bhMassMethod": "intrinsic", "sigmaDefinition": "sigma-stellar-within-half-mass-radius", "population": "bh-hosts"},
            "provenance": {"tier": "published-fit", "citation": "Huang, Di Matteo et al. 2018, BlueTides simulation: establishing black hole-galaxy relations at high redshift (arXiv:1801.04951)",
                           "doi": None, "url": "https://arxiv.org/abs/1801.04951", "retrieved": date.today().isoformat(), "compilation": f"{url} @ {commit}", "sourceMember": "4_BHM_STM_MSigma.ipynb"},
            "calibration": "prediction", "rankable": True, "notes": "MP-Gadget lineage (shared with ASTRID); not independent of ASTRID as model evidence."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "bluetides.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Curated {len(records)} BlueTides records")
