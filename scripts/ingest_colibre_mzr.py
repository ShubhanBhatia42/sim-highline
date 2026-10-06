import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/colibre_mzr_sharda26")
commit = sys.argv[2] if len(sys.argv) > 2 else "b685ae661ef4637697bb2d50af7d61e3fed18e6f"
output = Path(__file__).resolve().parent.parent / "data" / "curves" / "colibre-mzr.json"
repo_url = "https://github.com/psharda/colibre_mzr_sharda26"
paper = {"citation": "Sharda et al. 2026, COLIBRE gas-phase MZR (data repository)", "url": "https://arxiv.org/abs/2606.25995", "doi": None}
retrieved = date.today().isoformat()
min_count, reslimit_count = 20, 10
axes = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "gas-phase 12+log(O/H), median of star-forming galaxies", "yUnit": "dex"}
mzr_defs = {"metallicityQuantity": "gas-O/H", "metallicityCalibration": "intrinsic-simulation", "imf": "chabrier03", "population": "star-forming"}
warning = ("Median mass-weighted ISM oxygen abundance of star-forming galaxies as computed for Sharda et al. 2026 "
           "(ISM: nH > 0.1 cm^-3, T < 10^4.5 K). Bins kept only with >= 20 galaxies and M* >= 10 baryonic particle masses, "
           "matching the paper's resolution criterion. Definitions for non-COLIBRE runs follow the paper's re-analysis, not the original simulation papers.")

GRIDS = [
    ("COLIBRE", "m5 (L025)", "plot_mzr_sims_data_m5_{z}.npz", 2.3e5, "prediction"),
    ("COLIBRE", "m6", "plot_mzr_sims_data_m6_{z}.npz", 1.84e6, "prediction"),
    ("COLIBRE", "m7", "plot_mzr_sims_data_m7_{z}.npz", 1.47e7, "prediction"),
    ("EAGLE", "m5 (L025N0752)", "plot_mzr_sims_data_eagle_m5_{z}.npz", 2.26e5, "prediction"),
    ("EAGLE", "m6 (L100N1504)", "plot_mzr_sims_data_eagle_m6_{z}.npz", 1.81e6, "prediction"),
    ("IllustrisTNG", "TNG50", "plot_mzr_sims_data_tng_50_{z}.npz", 8.5e4, "prediction"),
    ("IllustrisTNG", "TNG100", "plot_mzr_sims_data_tng_100_{z}.npz", 1.4e6, "prediction"),
    ("IllustrisTNG", "TNG300", "plot_mzr_sims_data_tng_300_{z}.npz", 1.1e7, "prediction"),
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def record(source, run, kind, z, points, member, digest, interval, extra_warning="", calibration="prediction", rep=None):
    slug = "".join(c if c.isalnum() else "-" for c in f"{source}-{run}".lower()).strip("-")
    return {
        "id": f"sharda26.{slug}.mzr.z{z:g}", "source": source, "run": run, "kind": kind, "relation": "mzr",
        "epoch": {"zRepresentative": float(z), "zNominal": float(z), "zMin": float(z), "zMax": float(z), "mode": "published-epoch", "snapshot": None},
        "axes": axes,
        "domain": {"xMin": rep["domain"][0], "xMax": rep["domain"][1]} if rep else {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
        "representation": rep["representation"] if rep else {"type": "points", "intervalKind": interval, "connect": True, "points": points},
        "scatter": None,
        "selection": {"population": "star-forming galaxies", "warning": (warning + " " + extra_warning).strip()},
        "definitions": dict(mzr_defs),
        "provenance": {"tier": "published-table" if not rep else "published-fit", **paper, "retrieved": retrieved,
                       "compilation": f"{repo_url} @ {commit}", "sourceMember": member, **({"checksumSha256": digest} if digest else {})},
        "calibration": calibration, "rankable": True,
        "notes": "Re-analysis data released with Sharda et al. 2026 (GPL-2.0 repository)."
    }

def grid_records():
    out = []
    for source, run, pattern, particle_mass, calibration in GRIDS:
        for z in (0, 1, 2, 3, 5, 8, 10):
            path = root / "simulated_data" / pattern.format(z=z)
            if not path.exists():
                continue
            data = np.load(path)
            keep = (data["counts"] >= min_count) & (10 ** data["bin_centers"] >= reslimit_count * particle_mass) & np.isfinite(data["medians"])
            points = []
            for i in np.flatnonzero(keep):
                point = {"x": round(float(data["bin_centers"][i]), 4), "y": round(float(data["medians"][i]), 4), "count": int(data["counts"][i])}
                if "p16" in data.files and np.isfinite(data["p16"][i]) and np.isfinite(data["p84"][i]):
                    point["yLow"], point["yHigh"] = round(float(data["p16"][i]), 4), round(float(data["p84"][i]), 4)
                points.append(point)
            if len(points) >= 2:
                out.append(record(source, run, "simulation", z, points, f"simulated_data/{path.name}", sha(path), "scatter" if "p16" in data.files else "unspecified", calibration=calibration))
    for z in range(0, 9):
        mass, metal = root / "simulated_data" / f"SIMBA_z={z}_mass.npy", root / "simulated_data" / f"SIMBA_z={z}_metallicity.npy"
        if mass.exists() and metal.exists():
            x, y = np.load(mass), np.load(metal)
            points = [{"x": round(float(a), 4), "y": round(float(b), 4)} for a, b in zip(x, y) if np.isfinite(a) and np.isfinite(b)]
            out.append(record("SIMBA", "m100n1024 (Garcia et al. 2025)", "simulation", z, points, f"simulated_data/{mass.name}", sha(mass) + "", "unspecified",
                              "SIMBA medians supplied to Sharda et al. by A. Garcia; selection and aperture follow Garcia et al. 2025, not re-derived."))
    firebox = root / "simulated_data" / "FIREbox_z=0_mzr.csv"
    rows = [line.split(",") for line in firebox.read_text().strip().splitlines()[1:]]
    points = [{"x": round(float(a), 4), "y": round(float(b), 4)} for a, b in rows]
    out.append(record("FIREbox", "FIREbox", "simulation", 0, points, "simulated_data/FIREbox_z=0_mzr.csv", sha(firebox), "unspecified",
                      "FIREbox z=0 relation as tabulated in the Sharda et al. repository; original analysis choices not re-derived."))
    for z in (3, 5, 8, 10):
        hi = {3: 10, 5: 9, 8: 9, 10: 8}[z]
        out.append(record("THESAN-zoom", "best-fit relation", "simulation", z, None, "plotting_scripts.ipynb (Figure 5 cell)", None, "unspecified",
                          "Best-fit relation valid for 3 < z < 12 as transcribed in the Sharda et al. notebook; the plotted mass range per redshift follows that notebook.",
                          rep={"domain": (6, hi), "representation": {"type": "parametric", "equation": "12+log(O/H) = Z0 - alpha log10(1+z) - (gamma/beta) log10(1 + (M/M0)^-beta)",
                               "expression": "Z0-alpha*log10(1+zfix)-(gamma/beta)*log10(1+Math.pow(10,-beta*(x-logM0)))",
                               "parameters": {"Z0": 8.98, "alpha": 0.28, "beta": 0.55, "logM0": 10.74, "gamma": 0.39, "zfix": z}}}))
    for z, a, b, lo, hi in ((5, 0.343, -4.033, 6.4, 9.85), (8, 0.373, -4.269, 6.34, 9.278), (10, 0.388, -4.391, 6.34, 8.50)):
        out.append(record("FIRE-2", "high-z zooms (Marszewski et al. 2024)", "simulation", z, None, "plotting_scripts.ipynb (Figure 5 cell)", None, "unspecified",
                          "Linear fit as transcribed in the Sharda et al. notebook; mass range restricted to where FIRE-2 has more than 5 galaxies.",
                          rep={"domain": (lo, hi), "representation": {"type": "parametric", "equation": "12+log(O/H) = 9.0 + a log10(M*) + b",
                               "expression": "9.0+a*x+b", "parameters": {"a": a, "b": b}}}))
    return out

import csv

def obs_record(rid, source, z_lo, z_hi, z_rep, points, member, path, tier, interval, population, warning, calibration_label, citation, url, ydef):
    return {
        "id": rid, "source": source, "run": None, "kind": "observation", "relation": "mzr",
        "epoch": {"zRepresentative": round(z_rep, 3), "zMin": z_lo, "zMax": z_hi, "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": "dex"},
        "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
        "representation": {"type": "points", "intervalKind": interval, "points": points},
        "scatter": None, "selection": {"population": population, "warning": warning},
        "definitions": {"metallicityQuantity": "gas-O/H", "metallicityCalibration": calibration_label, "imf": "unspecified", "population": "star-forming", "massDefinition": "sed-total"},
        "provenance": {"tier": tier, "citation": f"{citation} (table as compiled in the Sharda et al. 2026 repository)", "doi": None, "url": url,
                       "retrieved": retrieved, "compilation": f"{repo_url} @ {commit}", "sourceMember": member, "checksumSha256": sha(path)},
        "calibration": "validation", "rankable": True,
        "notes": "sim-highline-derived binned medians from individual-galaxy measurements; the binning is ours, not the authors'." if tier == "catalog-derived" else "Published stacked measurements; sim-highline groups stacks by redshift only."
    }

def read_rows(name):
    path = root / "observed_data" / name
    return path, list(csv.DictReader(path.read_text(encoding="utf-8-sig").replace("\r", "").strip().splitlines()))

def binned(name, source, tag, zcol, mcol, ohcol, zbins, mass_edges, keep, citation, url, calibration_label, population, extra=""):
    path, rows = read_rows(name)
    rng = np.random.default_rng(20261002)
    out = []
    for z_lo, z_hi in zbins:
        sample = [r for r in rows if r[zcol] and r[ohcol] and r[mcol] and z_lo <= float(r[zcol]) < z_hi and keep(r)]
        points = []
        for m_lo, m_hi in zip(mass_edges[:-1], mass_edges[1:]):
            oh = np.array([float(r[ohcol]) for r in sample if m_lo <= mcol_value(r, mcol) < m_hi])
            if len(oh) < 5:
                continue
            boots, med = np.median(rng.choice(oh, size=(2000, len(oh))), axis=1), float(np.median(oh))
            points.append({"x": round((m_lo + m_hi) / 2, 3), "y": round(med, 3), "yLow": round(float(min(np.percentile(boots, 16), med)), 3),
                           "yHigh": round(float(max(np.percentile(boots, 84), med)), 3), "count": int(len(oh))})
        if len(points) < 2:
            continue
        z_rep = float(np.median([float(r[zcol]) for r in sample]))
        out.append(obs_record(f"{tag}.mzr.z{z_lo:g}-{z_hi:g}.binned", source, z_lo, z_hi, z_rep, points, f"observed_data/{name}", path, "catalog-derived", "uncertainty", population,
                              f"Binned by sim-highline from {len(sample)} galaxies in {z_lo} <= z < {z_hi}; bins need >= 5 galaxies; intervals are bootstrap 16-84% on the median (seed 20261002). {extra}".strip(),
                              calibration_label, citation, url, "gas-phase 12+log(O/H), median of individual galaxies in mass bins"))
    return out

def mcol_value(r, mcol):
    return float(np.log10(float(r[mcol]))) if mcol == "Mass" else float(r[mcol])

def stacks(name, source, tag, group, zcol, citation, url, calibration_label, population, z_fixed=None):
    path, rows = read_rows(name)
    out = []
    for key in sorted({group(r) for r in rows}):
        members = sorted([r for r in rows if group(r) == key], key=lambda r: float(r["logMstar"]))
        zs = [float(r[zcol]) if zcol else z_fixed for r in members]
        points = [{"x": float(r["logMstar"]), "y": float(r["OH"])} for r in members]
        if len(points) < 2 or any(b["x"] <= a["x"] for a, b in zip(points, points[1:])):
            continue
        out.append(obs_record(f"{tag}.mzr.{key}.stacks", source, round(min(zs), 3), round(max(zs), 3), float(np.median(zs)), points, f"observed_data/{name}", path, "published-table", "unspecified", population,
                              "Published stacked spectra; sim-highline only groups stacks by redshift.", calibration_label, citation, url, "gas-phase 12+log(O/H) of stacked spectra"))
    return out

COMPILATION = [
    ("isobe2026_jades_darkhorse_oasis_z1-10.csv", "z", "logMstar", "OH"), ("sarkar2025_archival_z=4-10.csv", "z", "logMstar", "logOH"),
    ("stanton2026_z=2-8_excels.csv", "z_spec", "logMstar_val", "OH_strong_val"), ("sanders2025_aurora_z=1-7.csv", "z_spec", "logMstar", "O_H"),
    ("henry2021_z=1-2_candels_wisp_tab5.csv", "z", "logMstar", "OH"), ("revalski2024_mudf_muse_z1-2.csv", "z", "logMstar", "OH"),
    ("li2023_a2744_smacs_z2-3.csv", "z", "logMstar", "OH"), ("langeroodi2023_archival_z=8.csv", "z_spec", "logM_star", "O_H"),
    ("pollock2025_archival_z=9-10.csv", "z", "logMstar", "OH"), ("hsiao2025_sapphires_z5-6.csv", "z", "logMstar", "OH"),
    ("hsiao2026_z6_glimpsed.csv", "z", "logMstar", "OH"), ("chemerynska2024_uncover_z=6-8.csv", "z", "logMstar", "OH"),
    ("raptis2025_z=2-4_cecilia.csv", "z", "logMstar", "OH"), ("cataldi2025_z=2-4_marta_tab2.csv", "z", "logMstar", "OH"),
    ("rowland2025_z=6-7_rebels.csv", "z", "Mstar", "OH_strong"), ("faisst2026_z=5_alpine_cristal_jwst2.csv", "z", "Mstar", "OH"),
]


def compilation_records():
    galaxies, members = [], []
    for name, zc, mc, oc in COMPILATION:
        path, rows = read_rows(name)
        n = 0
        for r in rows:
            try:
                z, m, oh = float(r[zc]), float(r[mc]), float(r[oc])
            except (ValueError, KeyError, TypeError):
                continue
            if np.isfinite(z) and np.isfinite(m) and np.isfinite(oh) and 6 < m < 12.5 and 6.5 < oh < 9.5:
                galaxies.append((z, m, oh, name.split("_")[0]))
                n += 1
        members.append(f"{name.split('_')[0]} ({n})")
    rng = np.random.default_rng(20261003)
    out = []
    digest = hashlib.sha256("".join(sorted(members)).encode()).hexdigest()
    for z_lo, z_hi in ((1, 2), (2, 3), (3, 4.5), (4.5, 6), (6, 8), (8, 10.5)):
        sample = [g for g in galaxies if z_lo <= g[0] < z_hi]
        points = []
        for m_lo in np.arange(6.5, 11.01, 0.5):
            oh = np.array([g[2] for g in sample if m_lo <= g[1] < m_lo + 0.5])
            if len(oh) < 5:
                continue
            boots, med = np.median(rng.choice(oh, size=(2000, len(oh))), axis=1), float(np.median(oh))
            points.append({"x": round(m_lo + 0.25, 3), "y": round(med, 3), "yLow": round(float(min(np.percentile(boots, 16), med)), 3), "yHigh": round(float(max(np.percentile(boots, 84), med)), 3), "count": int(len(oh))})
        if len(points) < 2:
            continue
        papers = sorted({g[3] for g in sample})
        rec = obs_record(f"sharda26.compilation.mzr.z{z_lo:g}-{z_hi:g}", "JWST+ground MZR compilation (Sharda+26 repository)", z_lo, z_hi, float(np.median([g[0] for g in sample])), points,
                         "observed_data/ (16 individual-galaxy tables)", root / "observed_data" / COMPILATION[0][0], "catalog-derived", "uncertainty", "star-forming galaxies from 16 spectroscopic programmes",
                         f"Binned by sim-highline from {len(sample)} galaxies drawn from: {', '.join(papers)}. Each galaxy weighted equally; abundances mix direct-Te and strong-line calibrations, and selection functions differ per programme. Bootstrap 16-84% on the median (seed 20261003).",
                         "mixed (direct Te and strong-line, per source paper)", "Individual-galaxy tables compiled in the Sharda et al. 2026 repository", repo_url, "gas-phase 12+log(O/H), median of individual galaxies in 0.5 dex mass bins")
        rec["provenance"]["checksumSha256"] = digest
        rec["provenance"]["sourceMember"] = "; ".join(members)
        out.append(rec)
    return out


def observed_records():
    out = []
    out += binned("curti2024_z=3-10_jades.csv", "Curti et al. 2024 (JADES)", "curti24.jades", "Redshift", "logMstar", "OH", [(3, 6), (6, 10)], list(np.arange(6.5, 9.51, 0.5)),
                  lambda r: not r["AGN"].strip(), "Curti et al. 2024 [journal reference not yet verified]", repo_url, "strong-line (Curti+20 calibrations)",
                  "JADES NIRSpec star-forming galaxies, candidate AGN excluded", "Flux-limited JWST selection; not mass complete.")
    out += binned("nakajima2023_z=4-8_ero_glass_ceers.csv", "Nakajima et al. 2023 (ERO/GLASS/CEERS)", "nakajima23", "zspec", "logMstar", "logOH", [(3.8, 6), (6, 9.5)], list(np.arange(6.5, 10.01, 0.5)),
                  lambda r: not r["l_logMstar"].strip(), "Nakajima et al. 2023 [journal reference not yet verified]", repo_url, "direct Te and strong-line mix (Nakajima+22 calibrations)",
                  "JWST NIRSpec emitters at z = 4-9", "Mixed Te and strong-line abundances; lensing-magnified sources included.")
    out += binned("lewis2024_legac_z0.7.csv", "Lewis et al. 2024 (LEGA-C)", "lewis24.legac", "z", "logMstar", "OH", [(0.59, 0.84)], list(np.arange(9.75, 11.26, 0.25)),
                  lambda r: True, "Lewis et al. 2024 (LEGA-C MZR, arXiv:2304.12343)", "https://arxiv.org/abs/2304.12343", "strong-line (Curti+20 calibrations)",
                  "LEGA-C massive star-forming galaxies")
    out += binned("gillmann2021_kross_kges_z=0.6-1.8.csv", "Gillman et al. 2021 (KROSS+KGES)", "gillman21", "z", "Mass", "OH", [(0.7, 1.3)], list(np.arange(9.0, 11.01, 0.25)),
                  lambda r: True, "Gillman et al. 2021 [journal reference not yet verified]", repo_url, "[NII]/Halpha (N2)",
                  "KMOS Halpha-selected star-forming galaxies", "Redshift window follows the Sharda et al. notebook.")
    out += stacks("steidel2014_kbss_z2.3.csv", "Steidel et al. 2014 (KBSS)", "steidel14.kbss", lambda r: "all", "z", "Steidel et al. 2014 [journal reference not yet verified]", repo_url,
                  "N2/O3N2 (Steidel+14 calibration)", "KBSS-MOSFIRE star-forming galaxies")
    out += stacks("he2026_z1-3_ngdeep_stacked.csv", "He et al. 2026 (NGDEEP)", "he26.ngdeep", lambda r: r["ID"][:2], "z", "He et al. 2026 (NGDEEP stacks)", repo_url,
                  "strong-line (see paper)", "NGDEEP grism-selected galaxies")
    out += stacks("lam2026_jades_stacked_z1-7.csv", "Lam et al. 2026 (JADES stacks)", "lam26.jades", lambda r: r["ID"][:2], "z", "Lam et al. 2026 (JADES stacks)", repo_url,
                  "strong-line (see paper)", "JADES stacked spectra")
    return out

records = grid_records() + observed_records() + compilation_records()
output.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Ingested {len(records)} Sharda+26 MZR records")
