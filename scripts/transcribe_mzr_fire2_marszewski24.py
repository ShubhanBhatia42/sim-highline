import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2403.08853"
DOI = "10.3847/2041-8213/ad4cee"
src = vf.fetch_arxiv(ARXIV) / "sample631.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
tb = tex[tex.index("\\begin{tabular}{c c c c c}"):]
tb = tb[:tb.index("\\end{tabular}")]
rows = []
for line in tb.split("\\\\"):
    c = [x.strip() for x in line.replace("\\hline", "").split("&")]
    if len(c) == 5 and re.fullmatch(r"-?[\d.]+", c[1].replace("$", "")):
        rows.append((c[0], [float(x.replace("$", "")) for x in c[1:]]))
assert len(rows) == 3 and rows[0][1] == [0.3717, -4.251, 0.2065, 0.1493] and rows[1][1][2] == 0 and rows[2][1] == [0.3702, -4.241, 0, 0], rows


def AB(p, z):
    a, b, al, be = p
    return a * ((1 + z) / 9) ** al, b * ((1 + z) / 9) ** be


A5, B5 = AB(rows[0][1], 5)
A12, B12 = AB(rows[0][1], 12)
assert abs(A5 - 0.343) < 0.003 and abs(B5 + 4.033) < 0.25 and abs(A12 - 0.402) < 0.003 and abs(B12 + 4.495) < 0.01, (A5, B5, A12, B12)
MODELS = [("Slope and normalization evolution, A(z) and B(z)", "ab", True), ("Normalization evolution, B(z) with fixed slope", "b", False), ("No evolution (fixed slope and normalization)", "none", False)]
records = []
for (label, slug, rank), (_, p) in zip(MODELS, rows):
    a, b, al, be = p
    records.append({
        "id": f"marszewski24.fire2.mzrz.evolution.{slug}", "source": "FIRE-2", "run": f"high-z zooms, redshift-evolving fit ({label})", "kind": "simulation", "relation": "mzr",
        "epoch": {"zRepresentative": 8.0, "zNominal": 8.0, "zMin": 5.0, "zMax": 12.0, "mode": "analytic-evolution", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 gas-phase Z/Zsun (Zsun = 0.02, Anders & Grevesse 1989)", "yUnit": "dex"},
        "domain": {"xMin": 6.0, "xMax": 10.5},
        "representation": {"type": "parametric", "equation": "log(Z/Zsun) = A(z) log(M*/Msun) + B(z); A = a ((1+z)/9)^alpha, B = b ((1+z)/9)^beta", "expression": "a*Math.pow((1+z)/9,alpha)*x+b*Math.pow((1+z)/9,beta)", "parameters": {"a": a, "b": b, "alpha": al, "beta": be}},
        "scatter": None,
        "selection": {"population": "galaxies of the FIRE-2 high-redshift zoom suite at integer redshifts z=5-12, linear fits to medians in five stellar-mass bins", "warning": f"{label}. Fit of Marszewski et al. 2024 to bin medians of the zoom sample (not volume complete) over log M* = 6 to the sample maximum; the domain 6-10.5 is the plotted fit range read from the paper's figure. Metallicity is the mass-weighted mean over gas within 0.2 Rvir; O/H follows from 12+log(O/H) = log(Z/Zsun) + 9.00 (the paper's FIRE-1 calibration, with its systematics)."},
        "definitions": {"metallicityQuantity": "gas-metal-mass-fraction", "metallicityCalibration": "intrinsic-simulation (mass-weighted gas within 0.2 Rvir; Zsun = 0.02)", "imf": "unspecified", "population": "all galaxies of the zoom suite"},
        "provenance": {"tier": "published-fit", "citation": f"Marszewski et al. 2024, ApJL 967, L41 (arXiv:{ARXIV}), best-fit parameters table", "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": vf.RETRIEVED, "checksumSha256": sha,
                       "sourceMember": "sample631.tex table:1 (arXiv source, transcribed)", "extractionMethod": "transcribed from the arXiv LaTeX table; A(5), A(12) and B(12) checked against the per-redshift fits printed on the paper's figure"},
        "calibration": "prediction", "rankable": False,
        "notes": "Zoom samples are not volume complete (see Known caveats)."})
for r in records:
    r["definitions"]["cosmology"] = {"H0": 67.66, "Om": 0.3111}
    r["definitions"]["cosmologyNote"] = "Planck 2020 (flat LCDM), values as in the Planck 2018 release"
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "marszewski24-fire2-mzr-evolution.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIRE-2 MZR evolution fits from Marszewski+24")
