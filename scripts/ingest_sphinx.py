import csv
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import numpy as np

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/sphinx")
url = "https://github.com/HarleyKatz/SPHINX-20-data"
commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
table = root / "data" / "all_basic_data.csv"
rows = list(csv.DictReader(table.open()))
digest = hashlib.sha256(table.read_bytes()).hexdigest()
DM, MIN_N = 0.25, 8
retrieved = date.today().isoformat()
selection_note = ("SPHINX20 public data release sample (Katz et al. 2023): haloes selected for the release, not a volume-complete census, "
                  "so medians at fixed mass are biased toward the selection (bright, star-forming systems).")


def binned(x, y, edges):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = (x >= lo) & (x < hi) & np.isfinite(y)
        if sel.sum() >= MIN_N:
            p16, p50, p84 = np.percentile(y[sel], [16, 50, 84])
            out.append({"x": round((lo + hi) / 2, 3), "y": round(float(p50), 4), "yLow": round(float(p16), 4), "yHigh": round(float(p84), 4), "count": int(sel.sum())})
    return out


def record(rel, suffix, z, points, xdef, xunit, ydef, yunit, defs, member, extra=""):
    return {"id": f"katz23.sphinx20.{rel}.{suffix}.z{z:g}", "source": "SPHINX20", "run": suffix, "kind": "simulation", "relation": rel,
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
            "axes": {"xDefinition": xdef, "xUnit": xunit, "yDefinition": ydef, "yUnit": yunit},
            "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "scatter", "connect": True, "points": points},
            "scatter": {"lower": "16th percentile", "upper": "84th percentile"},
            "selection": {"population": "SPHINX20 data-release galaxies", "warning": (selection_note + " " + extra).strip()},
            "definitions": defs,
            "provenance": {"tier": "catalog-derived", "citation": "SPHINX20 public data release (Katz et al. 2023; Rosdahl et al. 2018, 2022); medians derived by sim-highline",
                           "doi": None, "url": url, "retrieved": retrieved, "compilation": f"{url} @ {commit}", "sourceMember": member, "checksumSha256": digest},
            "calibration": "prediction", "rankable": True,
            "notes": "RAMSES-RT radiation-hydrodynamics of reionization in a 20 cMpc box; binned medians computed by sim-highline from the public per-galaxy table."}


records = []
for z in sorted({float(r["redshift"]) for r in rows}):
    sub = [r for r in rows if float(r["redshift"]) == z]
    logm = np.array([float(r["stellar_mass"]) for r in sub])
    edges = np.arange(6.0, 11.01, DM)
    for tag, col in (("SFR 10 Myr", "sfr_10"), ("SFR 100 Myr", "sfr_100")):
        sfr = np.array([float(r[col]) for r in sub])
        pts = binned(logm, np.log10(np.where(sfr > 0, sfr, np.nan)), edges)
        if len(pts) >= 2:
            records.append(record("sfms", tag.lower().replace(" ", "-"), z, pts, "log10 stellar mass (integral of SFH)", "log10(Msun)", f"log10 SFR averaged over {tag[4:]}", "log10(Msun/yr)",
                                  {"massDefinition": "integral-of-SFH", "imf": "unspecified", "population": "star-forming", "sfrTimescaleMyr": int(tag.split()[1]), "sfrStatistic": "median"},
                                  "data/all_basic_data.csv", "Galaxies without star formation in the window are excluded from the median."))
    zst = np.array([float(r["mean_stellar_metallicity_mass"]) for r in sub])
    pts = binned(logm, zst, edges)
    if len(pts) >= 2:
        records.append(record("zstar", "mass-weighted", z, pts, "log10 stellar mass", "log10(Msun)", "log10 mass-weighted stellar metallicity (Zsun)", "dex",
                              {"massDefinition": "integral-of-SFH", "imf": "unspecified", "metallicityQuantity": "stellar-Z", "metallicityCalibration": "intrinsic mass-weighted (solar value per release)", "population": "release-sample"},
                              "data/all_basic_data.csv"))
    mvir = np.array([float(r["mvir"]) for r in sub])
    pts = binned(mvir, logm - mvir, np.arange(8.0, 12.01, DM))
    if len(pts) >= 2:
        records.append(record("shmr", "virial", z, pts, "log10 halo virial mass", "log10(Msun)", "log10 stellar-to-halo mass ratio", "dex",
                              {"imf": "unspecified", "haloMassDefinition": "Mvir (release definition)", "haloMassHistory": "current", "population": "release-sample"},
                              "data/all_basic_data.csv", "Halo mass definition as provided in the release table (virial)."))
    morph = root / "data" / "galaxy_sizes" / f"morph_z{z:g}_1500A.json"
    if morph.exists():
        sizes = json.loads(morph.read_text())
        ids = [r["halo_id"] for r in sub]
        rh = np.array([np.median([v["half"] for v in sizes[i].values()]) if i in sizes else np.nan for i in ids])
        pts = binned(logm, np.log10(np.where(rh > 0, rh, np.nan)), edges)
        if len(pts) >= 2:
            records.append(record("size", "uv-1500A", z, pts, "log10 stellar mass", "log10(Msun)", "log10 circularised half-light radius at 1500 A (median over 10 sightlines)", "log10(kpc)",
                                  {"massDefinition": "integral-of-SFH", "imf": "unspecified", "sizeDefinition": "uv-half-light-1500A-circularised", "population": "release-sample"},
                                  f"data/galaxy_sizes/{morph.name}", "Sizes from the release's PHOTUTILS segmentation of mock 1500 A images."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "sphinx20.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Ingested {len(records)} SPHINX20 records")
