"""SMBH accretion-rate density of Aird et al. 2015 (arXiv:1503.01120, figure f20, vector EPS): solid black line (total AGN accretion
density, scaled up by the paper's arbitrary factor 1500, divided back here) with its 99 per cent confidence band (grey polygon).

Checks asserted below:
  * axis calibration: x is log10(1+z), the six top ticks (z = 0, 0.5, 1, 2, 5, 9) fall on one straight line (max residual < 0.05 pt); y is log10, the four
    major ticks (1, 0.1, 0.01, 0.001) are equally spaced (80.17 pt).
  * the figure-f19 luminosity-density curve ('All', same EPS family) converted with eta = 0.1 as (1-eta) L/(eta c^2) reproduces the f20 curve/1500 to < 0.006 dex (a uniform 0.005 dex offset, i.e. constants)
    at z = 0, 0.5, 1, 1.76, 2.5, 3, 4: this fixes the convention of the plotted quantity (the version without (1-eta) is 0.046 dex higher and fails).
  * quoted numbers: peak of the luminosity density z = 1.76 +- 0.05 (f19 quadratic peak 1.776, f20 peak 1.762) and relic mass density 4.20e5 Msun/Mpc^3
    (time integral of the digitized curve, H0=70, Om=0.3: 4.28e5, +2.0%, asserted within 4%).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pymupdf
from scipy import integrate

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

OUT = Path(os.environ.get("B_OUT_DIR") or Path(__file__).resolve().parent.parent / "data" / "curves") / "aird15-bhad.json"
ARXIV = "1503.01120"
SRC = vf.fetch_arxiv(ARXIV)
TEX = SRC / "ms.tex"
WORK = Path(os.environ.get("B_WORK_DIR") or "/tmp/vector_figure_src/aird15_pdf")
WORK.mkdir(parents=True, exist_ok=True)
C, MSUN, YR = 2.998e10, 1.989e33, 3.156e7


def to_pdf(name):
    eps, pdf = SRC / f"{name}.eps", WORK / f"{name}.pdf"
    if not pdf.exists():
        subprocess.run(["epstopdf", str(eps), f"--outfile={pdf}"], check=True)
    return eps, pdf


def quote(path, text):
    for i, line in enumerate(Path(path).read_text(errors="replace").splitlines(), 1):
        if text in line:
            return {"file": Path(path).name, "line": i, "text": text}
    raise AssertionError(f"quote not found: {text!r}")


def path_vertices(d):
    return [d["items"][0][1]] + [it[-1] for it in d["items"]]


# ---------------------------------------------------------------- f20 calibration
EPS20, PDF20 = to_pdf("f20")
page20 = vf.page_of(PDF20)
ds = page20.get_drawings()
top = sorted({round(d["rect"].x0, 2) for d in ds if d["rect"].width < 0.05 and d["rect"].height > 2 and abs(d["rect"].y0 - 23.3) < 0.5 and d["rect"].height < 6})
ZLAB = [0.0, 0.5, 1.0, 2.0, 5.0, 9.0]
tick_pts = [(t, np.log10(1 + z)) for t, z in zip([78.3, 148.38, 198.06, 268.13, 387.88, 476.13], ZLAB)]
assert all(any(abs(t - p) < 0.1 for p in top) for t, _ in tick_pts), top
A = np.polyfit([t for t, _ in tick_pts], [v for _, v in tick_pts], 1)
assert max(abs(np.polyval(A, t) - v) * 397.85 for t, v in tick_pts) < 0.05
fx = lambda px: 10 ** np.polyval(A, px) - 1
major = sorted({round(d["rect"].y0, 2) for d in ds if d["rect"].height < 0.05 and 8 < d["rect"].width < 9 and abs(d["rect"].x0 - 78.3) < 0.5})
assert len(major) == 4 and np.ptp(np.diff(major)) < 0.1, major  # 1.0, 0.1, 0.01, 0.001 (labels checked below)
labels = {w[4]: (w[1] + w[3]) / 2 for w in page20.get_text("words") if w[4] in ("0.001", "0.010", "0.100", "1.000")}
assert all(abs(labels[k] - t) < 4.5 for k, t in zip(("1.000", "0.100", "0.010", "0.001"), major)), (labels, major)
fy = lambda py: -3.0 + (major[3] - py) / (major[1] - major[0])

solid = next(d for d in ds if d["color"] == (0.0, 0.0, 0.0) and d["type"] == "s" and len(d["items"]) == 149)
verts = path_vertices(solid)
z = np.array([fx(q.x) for q in verts])
y = np.array([fy(q.y) for q in verts]) - np.log10(1500.0)
assert np.all(np.diff(z) > 0) and z[0] < 1e-3
poly = next(d for d in ds if d["type"] == "f" and len(d["items"]) == 299)
pv = path_vertices(poly)
px = np.array([q.x for q in pv])
py = np.array([fy(q.y) for q in pv]) - np.log10(1500.0)
k = int(px.argmax())
up = sorted(zip(px[: k + 1], py[: k + 1]))
lo = sorted(zip(px[k + 1:], py[k + 1:]))
zup = fx(np.array([p[0] for p in up]))
zlo = fx(np.array([p[0] for p in lo]))
yhigh = np.interp(z, zup, [p[1] for p in up])
ylow = np.interp(z, zlo, [p[1] for p in lo])
# the polygon's two edges are the max and min envelope; sort them
yhi, ylo = np.maximum(yhigh, ylow), np.minimum(yhigh, ylow)
print("band viol", float((ylo - y).max()), float((y - yhi).max()), int(np.argmax(ylo - y)), int(np.argmax(y - yhi)), len(z))
assert np.all(ylo <= y + 0.005) and np.all(y <= yhi + 0.005), "curve outside its own band"

# ---------------------------------------------------------------- f19 cross-check of the plotted quantity
EPS19, PDF19 = to_pdf("f19")
d19 = vf.page_of(PDF19).get_drawings()
c19 = d19[42]
assert c19["color"] == (0.0, 0.0, 0.0) and len(c19["items"]) == 49
sx19 = (263.0 - 78.4) / 0.6
v19 = path_vertices(c19)
z19 = np.array([10 ** ((q.x - 78.4) / sx19) - 1 for q in v19])
l19 = np.array([42 - (q.y - 23.59) / 83.995 for q in v19])
conv = {}
for zz in (0.0, 0.5, 1.0, 1.76, 2.5, 3.0, 4.0):
    b = np.log10(10 ** np.interp(zz, z19, l19) / (0.1 * C ** 2) / MSUN * YR) + np.log10(0.9)
    conv[zz] = round(float(b - np.interp(zz, z, y)), 4)
assert max(abs(v) for v in conv.values()) < 0.01, conv
i = int(l19.argmax())
sl = slice(max(i - 4, 0), i + 5)
c2 = np.polyfit(z19[sl], l19[sl], 2)
peak19 = float(-c2[1] / (2 * c2[0]))
i = int(y.argmax())
sl = slice(max(i - 4, 0), i + 5)
c2 = np.polyfit(z[sl], y[sl], 2)
peak20 = float(-c2[1] / (2 * c2[0]))
assert abs(peak19 - 1.76) < 0.05 and abs(peak20 - 1.76) < 0.05, (peak19, peak20)
H0S = 70e5 / 3.0857e24
rho0 = integrate.quad(lambda zz: 10 ** np.interp(zz, z, y) / ((1 + zz) * H0S * np.sqrt(0.3 * (1 + zz) ** 3 + 0.7)) / YR, z[0], z[-1], limit=400)[0] / 1e5
assert abs(rho0 / 4.20 - 1) < 0.04, rho0

Q = {
    "scaling": quote(TEX, "Our estimate of the SMBH accretion density (solid black line) is scaled up by an arbitrary factor of 1500."),
    "conversion": quote(TEX, "converted to $\\mathcal{M}_\\odot$ yr$^{-1}$ Mpc$^{-3}$ using the same bolometric corrections and radiative efficiency assumptions described above"),
    "eta": quote(TEX, "Adopting a radiative efficiency of $\\eta=0.1$,"),
    "bolcorr": quote(TEX, "We adopt the luminosity-dependent bolometric corrections from \\citet{Hopkins07b}."),
    "peak": quote(TEX, "We find a clear peak in the luminosity density at $z=1.76\\pm0.05$"),
    "relic": quote(TEX, "we estimate a relic SMBH mass density of $4.20^{+0.29}_{-0.14} \\times 10^5"),
    "cosmology": quote(TEX, "We adopt a flat cosmology with $\\Omega_\\Lambda=0.7$ and $h=0.7$ throughout this paper."),
    "band": quote(TEX, "Shaded regions indicate the 99 per cent confidence interval in our model parameters"),
    "xlfdef": quote(TEX, "XLF of AGNs across the full range of absorption ($20<\\log \\nh<26$)"),
    "extrapolation": quote(TEX, "The dashed black line and grey hatching indicate where we are substantially extrapolating our model outside the coverage of our data."),
}
pts = [{"x": round(float(a), 3), "y": round(float(b), 4), "yLow": round(float(lo_), 4), "yHigh": round(float(hi_), 4)} for a, b, lo_, hi_ in zip(z, y, ylo, yhi)]
assert all(p["yLow"] <= p["y"] <= p["yHigh"] for p in pts)
rec = {
    "id": "aird15.bhad.total", "source": "Aird et al. 2015", "run": "Aird et al. 2015 (XLAF model, total AGN)", "kind": "observation", "relation": "bhad",
    "epoch": {"zRepresentative": 2.0, "zNominal": 2.0, "zMin": pts[0]["x"], "zMax": pts[-1]["x"], "mode": "observational-bin", "snapshot": None},
    "axes": {"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 comoving SMBH accretion-rate density of all AGN (the plotted curve divided by the paper's factor 1500)", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
    "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
    "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": pts},
    "scatter": None,
    "selection": {"population": "all AGN: unabsorbed, absorbed and Compton-thick (20 < log N_H < 26)",
                  "warning": "Model curve from the paper's X-ray luminosity and absorption function fitted to hard- and soft-band samples; the band is the paper's 99 per cent confidence interval of the model parameters and, in the paper's words, may under-represent the uncertainties in the bolometric correction and radiative efficiency. Only the solid part of the curve (inside the coverage of the data, z < 5) is stored; the dashed extrapolation to higher z is not. The plotted quantity was shown multiplied by 1500; it is divided back here (exact)."},
    "definitions": {"luminosityBand": "bolometric, from the 2-10 keV XLF with the luminosity-dependent bolometric corrections of Hopkins+07", "luminosityBandQuote": Q["bolcorr"]["text"],
                    "radiativeEfficiency": 0.1, "radiativeEfficiencyQuote": Q["eta"]["text"],
                    "bhadDefinition": "(1-eta) L_bol-density/(eta c^2): the convention is not written in the text; it was established numerically (the f20 curve/1500 equals the f19 luminosity density times (1-eta)/(eta c^2) to 0.005-0.006 dex (uniform offset) for eta=0.1, whereas the version without (1-eta) is 0.046 dex higher)",
                    "obscurationCorrection": "total XLF over the full absorption range incl. Compton-thick: " + Q["xlfdef"]["text"], "densityFrame": "comoving", "cosmology": {"H0": 70, "Om": 0.3},
                    "cosmologyQuote": Q["cosmology"]["text"]},
    "provenance": {"tier": "digitized-figure", "citation": f"Aird et al. 2015, MNRAS (arXiv:{ARXIV}), total SMBH accretion density (figure f20)", "doi": None, "url": f"https://arxiv.org/abs/{ARXIV}",
                   "retrieved": "2026-10-18", "figure": "Total SFR density compared to our estimate of the total SMBH accretion density", "panel": "solid black line with grey 99 per cent band",
                   "checksumSha256": vf.sha256(PDF20, source=EPS20), "sourceMember": "f20.eps", "sourceArchiveSha256": "45b0e18bf875248337307cd42cb3cdb222cbe7c2fc2eed6162e8240323f332c5",
                   "extractionMethod": "vector path vertices of the EPS (converted with epstopdf, PyMuPDF get_drawings), transformed through axes calibrated on the drawn ticks; band from the grey fill polygon",
                   "axisCalibrationPixels": "x: log10(1+z) linear in the six top ticks z=0,0.5,1,2,5,9 (residual <0.05 pt); y: log decades 1, 0.1, 0.01, 0.001 at 23.26, 103.46, 183.63, 263.80 pt",
                   "digitizationUncertaintyDex": 0.01,
                   "verification": {"fig19ConversionDiffDex": conv, "peakRedshiftF19": round(peak19, 3), "peakRedshiftF20": round(peak20, 3), "quotedPeak": "1.76 +- 0.05",
                                    "relicMassDensity_1e5": {"integratedFromCurve": round(float(rho0), 3), "quoted": 4.20}}, "quotes": Q},
    "calibration": "target", "rankable": False, "notes": "Vector-path extraction; checks in provenance.verification."}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print("Wrote 1 record,", len(pts), "points; peaks", round(peak19, 3), round(peak20, 3), "rho0", round(float(rho0), 3), "conv", conv)
