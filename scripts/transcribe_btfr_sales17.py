import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1602.02155"
src = vf.fetch_arxiv(ARXIV)
tex = (src / "ms.tex").read_text(errors="ignore")
sha = vf.sha256(src / "ms.tex")
tb = tex[tex.index("\\label{TabBestFitPar}") - 700:tex.index("\\label{TabBestFitPar}")]
rows = {}
for line in tb.split("\\\\"):
    m = re.search(r"V_\{\\rm (max|out)\}\$\s*&\s*\$([\d.]+)\s*\\times\s*10\^(\d+)\$\s*&\s*(-?[\d.]+)\s*&\s*(-?[\d.]+)", line)
    if m:
        rows[m.group(1)] = (float(m.group(2)) * 10 ** int(m.group(3)), float(m.group(4)), float(m.group(5)))
assert rows == {"max": (7.1e8, 3.08, -2.43), "out": (1.25e9, 2.5, -2.0)}, rows
pdf = src / "figs" / "btf_rhbar_massive.pdf"
page = vf.page_of(pdf)
pdfsha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
xt, yt = vf._tick_positions(page, fr, "x"), vf._tick_positions(page, fr, "y")
fx = vf.axis_fit(page, fr, "x", labels=[(min(xt, key=lambda t: abs(t - cx)), math.log10(float(t))) for t, cx, cy in W if t in ("30", "50", "100", "150", "200") and cy > fr.y1])[0]
fy = vf.axis_fit(page, fr, "y", labels=[(min(yt, key=lambda t: abs(t - cy)), float(t[2:])) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < fr.x0])[0]
curves = vf.curves(page, fr, fx, fy, min_items=15)
CURVE = {"max": lambda c: c["color"] == (0.0, 0.5, 0.0) and c["width"] == 2.0, "out": lambda c: c["color"] == (0.0, 0.0, 0.0) and c["width"] == 6.0 and c["dashes"] == "[ 6 6 ] 0"}
LAB = {"max": ("V_max", "maximum circular velocity V_max of the halo (the green curve in the paper's Fig. 6)"), "out": ("V_out", "V_out of the paper's table (the thick dashed fit in Fig. 6, drawn against the circular velocity at twice the baryonic half-mass radius)")}
records = []
for k, (m0, a, g) in rows.items():
    c = [x for x in curves if CURVE[k](x)]
    assert len(c) == 1, (k, len(c))
    pts = c[0]["points"]
    err = max(abs(math.log10(m0 * (10 ** x / 50) ** a * math.exp(-((10 ** x / 50) ** g))) - y) for x, y in pts)
    assert err < 0.05, (k, err)
    xlo, xhi = round(min(x for x, _ in pts), 3), round(max(x for x, _ in pts), 3)
    records.append({
        "id": f"sales17.eagle-apostle.btfr.{k}.z0", "source": "EAGLE", "run": f"APOSTLE + EAGLE galaxies, {LAB[k][0]} fit (Sales+17)", "kind": "simulation", "relation": "btfr",
        "epoch": {"zRepresentative": 0.0, "zNominal": 0.0, "zMin": 0.0, "zMax": 0.0, "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": f"log10 rotation velocity, {LAB[k][1]}", "xUnit": "log10(km/s)", "yDefinition": "log10 baryonic mass M_bar (stars plus 1.4 M_HI within r_gal)", "yUnit": "log10(Msun)"},
        "domain": {"xMin": xlo, "xMax": xhi},
        "representation": {"type": "parametric", "equation": "M_bar/Msun = m0 nu^alpha exp(-nu^gamma), nu = V / (50 km/s)", "expression": "log10(m0*Math.pow(Math.pow(10,x)/50,alpha)*Math.exp(-Math.pow(Math.pow(10,x)/50,gamma)))", "parameters": {"m0": m0, "alpha": a, "gamma": g}},
        "scatter": None,
        "selection": {"population": "simulated galaxies of the EAGLE Ref-L100N1504 volume and the APOSTLE zoom volumes (Local Group analogues) at z=0, all morphologies", "warning": f"Fit of Sales et al. 2017 with a slope that steepens towards low velocity ({LAB[k][0]}). The domain is the extent of the drawn curve in the paper's figure; the formula reproduces that curve to {err:.3f} dex at every vertex (checked in the script). M_bar uses gas = 1.4 M_HI (HI from the Rahmati+13 prescription). APOSTLE is a zoom sample, not volume complete."},
        "definitions": {"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "massDefinition": "baryonic, stars plus 1.4 M_HI within r_gal", "population": "all galaxies (EAGLE Ref-L100N1504 and APOSTLE)", "velocityDefinition": LAB[k][1]},
        "provenance": {"tier": "published-fit", "citation": f"Sales et al. 2017, MNRAS 464, 2419 (arXiv:{ARXIV}), best-fit BTF parameters table", "doi": "10.1093/mnras/stw2461", "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": vf.RETRIEVED, "checksumSha256": sha,
                       "sourceMember": "ms.tex table:TabBestFitPar (arXiv source, transcribed); domain from figs/btf_rhbar_massive.pdf", "extractionMethod": "transcribed from the arXiv LaTeX table; each fit evaluated against the vector path of the curve drawn in the paper's figure (max deviation under 0.05 dex) and the domain read from that path", "figureSha256": pdfsha},
        "calibration": "prediction", "rankable": False,
        "notes": "APOSTLE is a zoom suite and the sample mixes it with EAGLE, so the record is not rankable. The IMF and cosmology follow the EAGLE runs."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "sales17-eagle-apostle-btfr.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} BTFR fits from Sales+17")
