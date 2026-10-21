"""Schreiber et al. 2015 (arXiv:1409.5433) main-sequence fit, Eq. 7 (tex label EQ:sfrms), as one analytic-evolution record.
Parameters are parsed from the arXiv source; the transcribed expression is then checked against the six grey 'best fit' curves
of the paper's own Fig. 8 (sfrms_cmp.eps, converted with gs to s15_sfrms_cmp.pdf), digitised from the vector paths with the axes calibrated
on the major tick marks. Writes records_schreiber15.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_figure import fetch_arxiv  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
import re
from pathlib import Path
TEX = (fetch_arxiv("1409.5433") / "paper.tex").read_text()
mm = re.search(r"with \$m_0 = ([\d.]+) \\pm ([\d.]+)\$, \$a_0 = ([\d.]+) \\pm ([\d.]+)\$, \$a_1 = ([\d.]+) \\pm ([\d.]+)\$, \$m_1 = ([\d.]+) \\pm ([\d.]+)\$ and \$a_2 = ([\d.]+) \\pm ([\d.]+)\$", TEX)
v = [float(g) for g in mm.groups()]
PAR = dict(m0=v[0], a0=v[2], a1=v[4], m1=v[6], a2=v[8], m0Error=v[1], a0Error=v[3], a1Error=v[5], m1Error=v[7], a2Error=v[9])
assert (PAR["m0"], PAR["a0"], PAR["a1"], PAR["m1"], PAR["a2"]) == (0.5, 1.5, 0.3, 0.36, 2.5)

import json, sys
import numpy as np
import pymupdf
from scipy.optimize import minimize_scalar
import subprocess
PDF = Path("/tmp/vector_figure_src/s15_sfrms_cmp.pdf")   # gs-converted copy of sfrms_cmp.eps in the arXiv source
if not PDF.exists():
    subprocess.run(["gs", "-q", "-dBATCH", "-dNOPAUSE", "-dEPSCrop", "-sDEVICE=pdfwrite", f"-sOutputFile={PDF}", str(fetch_arxiv("1409.5433") / "sfrms_cmp.eps")], check=True)
p = pymupdf.open(PDF)[0]; dr = p.get_drawings()
# --- axis calibration from major ticks (black, stroked 0.85 pt, length ~3.9 pt)
xt = sorted({round(it[1].x, 1) for d in dr for it in d["items"] if it[0] == "l" and d["fill"] is None and d["color"] == (0, 0, 0) and abs(it[1].y - 215.1) < .2 and abs(it[2].y - 211.2) < .2})
yt = sorted({round(it[1].y, 1) for d in dr for it in d["items"] if it[0] == "l" and d["fill"] is None and d["color"] == (0, 0, 0) and abs(it[1].x - 62.9) < .2 and abs(it[2].x - 66.4) < .2}, reverse=True)
assert len(xt) == 5 and len(yt) == 6, (xt, yt)
xv = [9.5, 10.0, 10.5, 11.0, 11.5]; yv = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]   # labels read from the rendered figure
fx = np.polyfit(xt, xv, 1); fy = np.polyfit(yt, yv, 1)
assert np.abs(np.polyval(fx, xt) - xv).max() < 0.002 and np.abs(np.polyval(fy, yt) - yv).max() < 0.002   # ticks equally spaced: 0.5 dex per tick
X = lambda px: np.polyval(fx, px); Y = lambda py: np.polyval(fy, py)
# --- grey best-fit curves
grey = [d for d in dr if d["color"] and abs(d["color"][0] - .67) < .01 and len(d["items"]) > 20 and d["fill"] is None]
cur = []
for d in grey:
    pts = [(X(it[1].x), Y(it[1].y)) for it in d["items"] if it[0] == "l"] + [(X(d["items"][-1][2].x), Y(d["items"][-1][2].y))]
    cur.append(np.array(pts))
cur.sort(key=lambda c: c[0, 1])
print("grey curves:", len(cur), [(round(c[:, 0].min(), 2), round(c[:, 0].max(), 2)) for c in cur])
def sfr(x, z, m0=PAR["m0"], a0=PAR["a0"], a1=PAR["a1"], m1=PAR["m1"], a2=PAR["a2"]):
    r = np.log10(1 + z); m = x - 9
    return m - m0 + a0 * r - a1 * np.maximum(0, m - m1 - a2 * r) ** 2
legend = [(0.3, 0.7), (0.7, 1.2), (1.2, 1.8), (1.8, 2.5), (2.5, 3.5), (3.5, 5.0)]
res = {}
for c, (lo, hi) in zip(cur, legend):
    zbest = minimize_scalar(lambda z: np.mean((sfr(c[:, 0], z) - c[:, 1]) ** 2), bounds=(0.05, 6), method="bounded").x
    zc = (lo + hi) / 2; rms_c = np.sqrt(np.mean((sfr(c[:, 0], zc) - c[:, 1]) ** 2))
    res[f"{lo}-{hi}"] = dict(zBestFitToGreyCurve=round(float(zbest), 3), binCentre=zc, rmsAtBinCentre=round(float(rms_c), 4), maxAbsAtBinCentre=round(float(np.abs(sfr(c[:, 0], zc) - c[:, 1]).max()), 4))
print(json.dumps(res, indent=1))
assert all(r["rmsAtBinCentre"] < 0.03 and r["maxAbsAtBinCentre"] < 0.06 for r in res.values()), res
# --- filled circles (stacked SFR points) vs formula at the bin centre
mk = {}
for d in dr:
    if d["fill"] and d["fill"] != (0, 0, 0) and len(d["items"]) > 20 and d["rect"].width < 8 and d["rect"].width > 3 and d["rect"].x0 > 70 and d["rect"].y0 > 25 and not (60 < d["rect"].x0 < 100 and d["rect"].y0 < 80 and d["rect"].x0 < 80 and False):
        mk.setdefault(tuple(round(v, 2) for v in d["fill"]), []).append((X(d["rect"].x0 + d["rect"].width / 2), Y(d["rect"].y0 + d["rect"].height / 2)))
for col, pts in mk.items(): print(col, [(round(a, 2), round(b, 2)) for a, b in pts])
allx = [a for pts in mk.values() for a, b in pts if a > 9.7 and b < 2.9 or (a > 9.7 and b < 2.9)]
# markers of the legend sit at x~9.78 (y>2.3); the stacks span log M* 9.74 ... 11.21
stack_x = [a for pts in mk.values() for a, b in pts if not (abs(a - 9.78) < 0.02 and b > 2.3)]
lo, hi = round(min(stack_x), 2), round(max(stack_x), 2)
print("stack mass range", lo, hi)
OUT = ROOT / "data" / "curves" / "sfms-schreiber15.json"
rec = {
    "id": "schreiber15.goods-candels-cosmos.sfms.evolution", "source": "Schreiber et al. 2015 (Herschel stacking)", "run": None,
    "kind": "observation", "relation": "sfms",
    "epoch": {"zRepresentative": 2.0, "zMin": 0.3, "zMax": 5.0, "mode": "analytic-evolution", "snapshot": None},
    "axes": {"xDefinition": "log10 stellar mass (FAST, Bruzual & Charlot 2003, Salpeter IMF, delayed-exponential SFHs)", "xUnit": "log10(Msun)",
             "yDefinition": "log10 of the mode of the SFR distribution of star-forming galaxies, SFR = SFR_UV (uncorrected, Daddi+04) + SFR_IR (Kennicutt98), Salpeter IMF, from mean Herschel stacks corrected to the mode (about -0.1 dex)", "yUnit": "log10(Msun/yr)"},
    "domain": {"xMin": lo, "xMax": hi},
    "representation": {
        "type": "parametric",
        "equation": "log10 SFR_MS = m - m0 + a0 r - a1 [max(0, m - m1 - a2 r)]^2, m = log10(M*/1e9 Msun), r = log10(1+z) (Eq. 7)",
        "expression": "(x-9)-m0+a0*Math.log10(1+z)-a1*Math.pow(Math.max(0,(x-9)-m1-a2*Math.log10(1+z)),2)", "parameters": PAR},
    "scatter": {"value": 0.3, "unit": "dex", "meaning": "non-varying dispersion of log SFR at fixed mass and redshift from scatter stacking (0.30 +-0.06 Herschel; 0.33 +-0.03 COSMOS UltraVISTA), not an uncertainty of the curve"},
    "selection": {"population": "mass-complete star-forming galaxies selected with the UVJ criterion (U-V>1.3, V-J<1.6, U-V>0.88(V-J)+0.49 = quiescent), GOODS-N/S, UDS, COSMOS CANDELS H-band and GOODS-N/COSMOS UltraVISTA Ks-band catalogues",
                  "warning": f"The fit was made to the filled circles of Fig. 8 (stacked mass/redshift bins with 0.3<z<5.0 in six redshift bins); the stacks span log M* = {lo} to {hi}, so the expression is an extrapolation outside this mass range and outside 0.3<z<5.0. The paper's text says the catalogue is mass-complete above 2e10 Msun and extends to z=4. Abstract: flattening at log M* > 10.5. Quiescent galaxies, not AGN, are excluded."},
    "provenance": {"tier": "published-fit", "citation": "Schreiber et al. 2015, A&A 575, A74 (arXiv:1409.5433), Eq. 7", "doi": None, "url": "https://arxiv.org/abs/1409.5433", "retrieved": "2026-10-18"},
    "calibration": "validation", "rankable": True,
    "notes": "Analytic redshift evolution (variable z in the expression). Verification: parameters parsed from the arXiv source; the expression, evaluated at the legend bin centres, reproduces the six grey best-fit curves of the paper's Fig. 8 with rms 0.007-0.016 dex and maximum 0.04 dex (digitisation of vector paths, axes calibrated on tick marks).",
    "definitions": {"massDefinition": "sed-total", "imf": "salpeter55", "cosmology": {"H0": 70, "Om": 0.3}, "population": "star-forming",
                    "sfrIndicator": "UV (uncorrected, 1500 A) + IR (Herschel stacks, CE01 templates), L_IR from 24-500 micron stacks", "sfrTimescaleMyr": 100,
                    "sfrTimescaleBasis": "'assume that the SFR remained constant over the last 100 Myr'", "sfrStatistic": "mode",
                    "sfrStatisticBasis": "'in all the following we refer to the SFR of the main sequence as the mode of the distribution'"}}
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print("wrote", OUT)
