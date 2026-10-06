import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
from astropy.table import Table

retrieved = date.today().isoformat()
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "github-observations.json"
REPOS = {"koprowski": ("/tmp/maciejpkoprowski_COSMOS-Web-GSMF-MS-data", "https://github.com/maciejpkoprowski/COSMOS-Web-GSMF-MS-data"),
         "baker": ("/tmp/Astro-William-Baker_Baker-2025d", "https://github.com/Astro-William-Baker/Baker-2025d")}


def commit(path):
    return subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def prov(key, member, citation, tier="published-table"):
    path, url = REPOS[key]
    return {"tier": tier, "citation": citation, "doi": None, "url": url, "retrieved": retrieved, "compilation": f"{url} @ {commit(path)}",
            "sourceMember": member, "checksumSha256": hashlib.sha256((Path(path) / member).read_bytes()).hexdigest()}


def epoch(lo, hi, rep):
    return {"zRepresentative": round(float(rep), 3), "zMin": float(lo), "zMax": float(hi), "mode": "observational-bin", "snapshot": None}


records = []
path = REPOS["koprowski"][0]
sfr = Table.read(f"{path}/SFR_components.ecsv", format="ascii.basic", comment="#")
for (lo, hi) in sorted({(r["z_min"], r["z_max"]) for r in sfr}):
    rows = [r for r in sfr if r["z_min"] == lo and r["z_max"] == hi and np.isfinite(r["log_SFR"])]
    rows.sort(key=lambda r: r["logM_mean"])
    pts = [{"x": round(float(r["logM_mean"]), 3), "y": round(float(r["log_SFR"]), 3), "yLow": round(float(r["log_SFR"] - r["e_log_SFR"]), 3), "yHigh": round(float(r["log_SFR"] + r["e_log_SFR"]), 3),
            "xLow": float(r["logM_min"]), "xHigh": float(r["logM_max"])} for r in rows]
    if len(pts) < 2:
        continue
    records.append({"id": f"koprowski26.cosmosweb.sfms.z{lo:g}-{hi:g}", "source": "Koprowski et al. (COSMOS-Web MS)", "run": None, "kind": "observation", "relation": "sfms",
                    "epoch": epoch(lo, hi, np.mean([r["z_mean"] for r in rows])),
                    "axes": {"xDefinition": "log10 stellar mass (bin mean)", "xUnit": "log10(Msun)", "yDefinition": "log10 SFR (IR+UV) of stacked mass-complete star-forming galaxies", "yUnit": "log10(Msun/yr)"},
                    "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]}, "representation": {"type": "points", "intervalKind": "uncertainty", "points": pts}, "scatter": None,
                    "selection": {"population": "mass-complete star-forming galaxies (COSMOS-Web v1.1)", "warning": "Stacked far-IR (Herschel, SCUBA-2) plus UV SFRs; bins without a valid IR luminosity use UV only. A stack measures a mean, not a median."},
                    "definitions": {"massDefinition": "sed-total", "imf": "unspecified", "population": "star-forming", "sfrTimescaleMyr": "IR+UV (~100 Myr)", "sfrStatistic": "stacked-mean"},
                    "provenance": prov("koprowski", "SFR_components.ecsv", "Koprowski, Lisiecki, Sawant & Wijesekera, COSMOS-Web mass-complete main sequence to z~8 (data repository)"),
                    "calibration": "validation", "rankable": True, "notes": "Binned measurements as released by the authors."})
fq = Table.read(f"{path}/f_Q_binned_measurements.ecsv", format="ascii.basic", comment="#")
for (lo, hi) in sorted({(r["z_min"], r["z_max"]) for r in fq}):
    rows = sorted([r for r in fq if r["z_min"] == lo and r["z_max"] == hi and r["used_in_global_fit"]], key=lambda r: r["logM_center"])
    pts = [{"x": float(r["logM_center"]), "y": round(float(r["f_Q"]), 4), "yLow": round(float(max(r["f_Q"] - r["f_Q_err"], 0)), 4), "yHigh": round(float(min(r["f_Q"] + r["f_Q_err"], 1)), 4), "count": int(round(r["N_all"]))} for r in rows]
    if len(pts) < 2:
        continue
    records.append({"id": f"koprowski26.cosmosweb.fq.z{lo:g}-{hi:g}", "source": "Koprowski et al. (COSMOS-Web MS)", "run": None, "kind": "observation", "relation": "quenched",
                    "epoch": epoch(lo, hi, rows[0]["z_center"]),
                    "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "quiescent fraction", "yUnit": "fraction"},
                    "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]}, "representation": {"type": "points", "intervalKind": "uncertainty", "points": pts}, "scatter": None,
                    "selection": {"population": "all galaxies above the mass-completeness limit", "warning": "Only bins the authors used in their global fit (mass complete) are kept. Quiescent selection follows the paper, not an sSFR threshold."},
                    "definitions": {"massDefinition": "sed-total", "imf": "unspecified", "quenchingCriterion": "paper colour/SED selection", "population": "all"},
                    "provenance": prov("koprowski", "f_Q_binned_measurements.ecsv", "Koprowski et al., COSMOS-Web quiescent fractions (data repository)"),
                    "calibration": "validation", "rankable": True, "notes": "Binned measurements as released by the authors."})
bpath = REPOS["baker"][0]
for f in sorted(Path(bpath).glob("smf_z=*.fits")):
    lo, hi = (float(v) for v in f.stem.split("=")[1].split("-"))
    t = Table.read(f)
    pts = []
    for r in t:
        phi, lo_e, hi_e = float(r["phi_vals"]), float(r["phi_low"]), float(r["phi_high"])
        if phi <= 0:
            continue
        pts.append({"x": round(float(r["mass_bins_mid"]), 3), "y": round(np.log10(phi), 4), "yLow": round(np.log10(max(phi - lo_e, phi * 0.05)), 4), "yHigh": round(np.log10(phi + hi_e), 4)})
    if len(pts) < 2:
        continue
    records.append({"id": f"baker25.qsmf.z{lo:g}-{hi:g}", "source": "Baker et al. 2025 (quiescent, JWST)", "run": None, "kind": "observation", "relation": "gsmf",
                    "epoch": epoch(lo, hi, (lo + hi) / 2),
                    "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 number density of quiescent galaxies per dex", "yUnit": "log10(Mpc^-3 dex^-1)"},
                    "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]}, "representation": {"type": "points", "intervalKind": "uncertainty", "points": pts}, "scatter": None,
                    "selection": {"population": "massive quiescent galaxies", "warning": "phi_low/phi_high are treated as offsets from phi (they are smaller than phi in every row). Quiescent-only mass function: not comparable with total GSMFs."},
                    "definitions": {"massDefinition": "sed-total", "imf": "unspecified", "densityFrame": "comoving", "population": "quiescent"},
                    "provenance": prov("baker", f.name, "Baker et al. 2025, massive quiescent galaxies at z=2-7 (arXiv:2506.04119; Zenodo 16942039)"),
                    "calibration": "validation", "rankable": True, "notes": "Data released by the authors on GitHub/Zenodo."})
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Ingested {len(records)} records from author GitHub data releases")
