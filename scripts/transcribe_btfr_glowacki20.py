import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2003.03402"
DOI = "10.1093/mnras/staa2616"
src = vf.fetch_arxiv(ARXIV) / "main.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
lab = tex.index("\\label{tab:btfr_fits}")
tb = tex[tex.rindex("\\begin{tabular}", 0, lab):lab]
SAMPLES = {"Full sample, 100": ("combined 100 Mpc/h box and high-resolution box", 100.0, "m100n1024 + hires (combined)", "combined"), "\\simba\\--100, 140": ("100 Mpc/h box only", 140.0, "m100n1024", "box100"), "High resolution sample, 100": ("high-resolution box only (8x better mass resolution)", 100.0, "hires", "hires")}
VEL = {"2R_{e}": "V_2Re (velocity at twice the effective radius)", "max": "V_max (peak of the rotation curve)", "flat": "V_flat (flat part of the rotation curve)", "polyex": "V_polyex (polyex model velocity)"}
tb = "\n".join(l for l in tb.splitlines() if not l.lstrip().startswith("%"))
rows, cur = {}, None
for line in tb.split("\\\\"):
    line = line.replace("\\hline", "").strip()
    hdr = re.search(r"(Full sample[^&]*|\\simba\\--100[^&]*|High resolution sample[^&]*|Hi-res[^&]*):", line)
    if hdr:
        cur = next((k for k in SAMPLES if hdr.group(0).startswith(k)), None)
    m = re.match(r"\$V_\{\\rm\{([^}]+(?:\{e\})?)\}\}\$\s*&\s*([\d.]+)\$\\pm\$[\d.]+\s*&\s*(-?[\d.]+)\$\\pm\$[\d.]+\s*&\s*([\d.]+)\$\\pm\$[\d.]+\s*&\s*([\d.]+)\$\\pm\$[\d.]+", line)
    if m and cur:
        rows[(cur, m.group(1))] = tuple(float(m.group(i)) for i in range(2, 6))
assert len(rows) == 12 and rows[("Full sample, 100", "flat")][:2] == (3.65, 2.21) and rows[("\\simba\\--100, 140", "polyex")][:2] == (3.76, 1.64) and rows[("High resolution sample, 100", "max")][:2] == (5.07, -1.11), rows
records = []
for (k, v), (m, b, b200, scat) in rows.items():
    assert abs(m * math.log10(200) + b - b200) < 0.03, (k, v, m, b, b200)
    label, vlo, run, slug = SAMPLES[k]
    lo, hi = math.log10(vlo), math.log10(300.0)
    records.append({
        "id": f"glowacki20.simba.btfr.{slug}.{v.replace('_', '').replace('{', '').replace('}', '').lower()}.z0", "source": "SIMBA", "run": f"{run}, {VEL[v].split(' ')[0]} fit", "kind": "simulation", "relation": "btfr",
        "epoch": {"zRepresentative": 0.0, "zNominal": 0.0, "zMin": 0.0, "zMax": 0.0, "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": f"log10 rotation velocity, {VEL[v]}", "xUnit": "log10(km/s)", "yDefinition": "log10 baryonic mass M_bar", "yUnit": "log10(Msun)"},
        "domain": {"xMin": round(lo, 4), "xMax": round(hi, 4)},
        "representation": {"type": "parametric", "equation": "log10 M_bar = m log10 V + b (orthogonal maximum-likelihood fit)", "expression": "m*x+b", "parameters": {"m": m, "b": b, "log10b200": b200, "scatterOrthogonalDex": scat}},
        "scatter": None,
        "selection": {"population": f"SIMBA galaxies at z=0 with sSFR and HI-mass cuts and M*>5.8e8 Msun (see paper), {label}", "warning": f"Linear fit of Glowacki et al. 2020 over {vlo:g} < V < 300 km/s using the {VEL[v]}; the stellar mass-to-light adjustment to Upsilon*=0.5 follows the SPARC comparison section. Velocity definitions differ between the four fits, so compare like with like. The figure itself (individual galaxies) is not extracted."},
        "definitions": {"imf": "unspecified", "cosmology": {"H0": 68.0, "Om": 0.3}, "massDefinition": "baryonic mass as defined in the paper", "population": "rotation-supported galaxies (sSFR and HI cuts)", "velocityDefinition": VEL[v]},
        "provenance": {"tier": "published-fit", "citation": f"Glowacki et al. 2020, MNRAS 498, 3687 (arXiv:{ARXIV}), BTFR best-fit parameters", "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": vf.RETRIEVED, "checksumSha256": sha,
                       "sourceMember": "main.tex table:btfr_fits (arXiv source, transcribed)", "extractionMethod": "transcribed from the arXiv LaTeX table; m, b and b200 cross-checked in the script (m log10(200) + b = log10 b200 within 0.03 dex)"},
        "calibration": "prediction", "rankable": False,
        "notes": "Transcribed from the paper's table and spot-checked against quoted values in the script. Not rankable: the sample is a selection of rotators and the velocity definition is not the observational one."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "glowacki20-simba-btfr.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} SIMBA BTFR fit records from Glowacki+20")
