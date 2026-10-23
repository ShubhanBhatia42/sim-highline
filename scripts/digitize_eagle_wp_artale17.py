"""Artale et al. 2017 (arXiv:1611.05064, MNRAS 470, 1771): EAGLE (Ref-L100N1504) z=0.1 projected galaxy correlation function, stellar-mass threshold
M* > 10^8.66 h^-2 Msun, read from the vector paths of Wp-1halo2halo-Ms-gt-9.0-z0.1-JN-2.eps (bottom panel of Fig. xi_mstar).
The y axis of that panel is log10(w_p/r_p); it is converted exactly to log10 w_p by adding log10 r_p (stated in the record).
Calibration check: the red reference line of the panel is the paper's eq. (wp_ref) with r0 = 5.33 h^-1 Mpc, gamma = 1.8 (quoted in the paper); it must be reproduced.
Run: python3 -I digitize_eagle_wp_artale17.py [path-to-unpacked-arxiv-source]
"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.special import gamma as gam

sys.path.insert(0, str(Path(__file__).resolve().parent))      
import vector_figure as vf  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "wp-artale17.json"
ARXIV = "1611.05064"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
EPS = SRC / "Wp-1halo2halo-Ms-gt-9.0-z0.1-JN-2.eps"
tmp = Path(tempfile.mkdtemp(prefix="a17_"))
subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dEPSCrop", "-sDEVICE=pdfwrite", f"-sOutputFile={tmp/'f.pdf'}", str(EPS)], check=True)
page = vf.page_of(tmp / "f.pdf")
sha = vf.sha256(EPS)
fr = vf.frames(page)[0]
# axis labels are outlined text: calibrate by hand on the major ticks (6.0 pt long; x: -1.5 ... 1.0 step 0.5; y: 5 ... -2 step 1, top to bottom), checked against the red reference line
majx = sorted(set(round(it[1].x, 2) for d in page.get_drawings() for it in d["items"] if it[0] == "l" and abs(it[1].x - it[2].x) < 0.05 and abs(max(it[1].y, it[2].y) - fr.y1) < 1 and abs(abs(it[1].y - it[2].y) - 6.0) < 0.1))
majy = sorted(set(round(it[1].y, 2) for d in page.get_drawings() for it in d["items"] if it[0] == "l" and abs(it[1].y - it[2].y) < 0.05 and abs(min(it[1].x, it[2].x) - fr.x0) < 1 and abs(abs(it[1].x - it[2].x) - 6.0) < 0.1))
assert len(majx) == 6 and len(majy) == 8, (majx, majy)
kx, cx = np.polyfit(majx, [-1.5 + 0.5 * i for i in range(6)], 1)
ky, cy = np.polyfit(majy, [5.0 - i for i in range(8)], 1)
assert np.allclose(kx * np.array(majx) + cx, [-1.5 + 0.5 * i for i in range(6)], atol=0.002) and np.allclose(ky * np.array(majy) + cy, [5.0 - i for i in range(8)], atol=0.002)
fx = lambda p: kx * p + cx          # log10 r_p [h^-1 Mpc]
fy = lambda p: ky * p + cy          # log10 (w_p / r_p)

# calibration check against the reference line (red, eq. wp_ref of the paper: r0 = 5.33, gamma = 1.8)
R0, G = 5.33, 1.8


def wref_over_rp(x):
    return math.log10((R0 / 10 ** x) ** G * math.sqrt(math.pi) * gam((G - 1) / 2) / gam(G / 2))


red = [c for c in vf.curves(page, fr, fx, fy, min_items=8) if c["color"] == (1.0, 0.0, 0.0)]
assert len(red) == 1
rd = np.array([wref_over_rp(x) - y for x, y in red[0]["points"] if -1.45 <= x <= 1.0])
assert len(rd) >= 20 and np.max(np.abs(rd)) < 0.005, np.max(np.abs(rd))
CAL = (len(rd), float(np.max(np.abs(rd))))

green = [c for c in vf.curves(page, fr, fx, fy, min_items=8) if c["color"] == (0.0, 0.5, 0.0) and abs(c["width"] - 1.5) < 0.01]
assert len(green) == 1
pts = [(x, y) for x, y in green[0]["points"] if -1.5 <= x <= 1.0 + 1e-3 and -2 <= y <= 5]
assert len(pts) == 17
# jackknife error bars: short vertical green strokes at each data x
bars = {}
for d in page.get_drawings():
    col = tuple(round(v, 2) for v in d["color"]) if d["color"] else None
    if col != (0.0, 0.5, 0.0) or len(d["items"]) > 3:
        continue
    for it in d["items"]:
        if it[0] == "l" and abs(it[1].x - it[2].x) < 0.05 and abs(it[1].y - it[2].y) > 1.0:
            bars.setdefault(round(fx(it[1].x), 2), []).append((fy(it[1].y), fy(it[2].y)))
points = []
nb = 0
for x, y in pts:
    p = {"x": round(x, 3), "y": round(y + x, 4)}                       # log w_p = log(w_p/r_p) + log r_p
    key = [k for k in bars if abs(k - x) < 0.03]
    if key:
        ys = [v for seg in bars[key[0]] for v in seg]
        lo, hi = min(ys), max(ys)
        if lo < y < hi:
            p["yLow"], p["yHigh"] = round(lo + x, 4), round(hi + x, 4)
            nb += 1
    points.append(p)
assert all(a["x"] < b["x"] for a, b in zip(points, points[1:]))

sel = ("EAGLE galaxies at z=0.1 with M* > 10^8.66 h^-2 Msun (stellar mass within a 3D spherical aperture of 30 kpc), simulation Ref-L100N1504 "
       "(L = 67.77 h^-1 Mpc); w_p integrated to pi_max ~ 34 Mpc/h")
rec = {
    "id": "artale17.eagle.wp.mstar-gt-8p66.z0p1", "source": "EAGLE", "run": "Ref-L100N1504, M* > 10^8.66 h^-2 Msun", "kind": "simulation", "relation": "wp",
    "epoch": {"zRepresentative": 0.1, "zNominal": 0.1, "zMin": 0.1, "zMax": 0.1, "mode": "published-epoch", "snapshot": None},
    "axes": {"xDefinition": "log10 projected separation r_p", "xUnit": "log10(h^-1 Mpc)",
             "yDefinition": "log10 projected correlation function w_p(r_p) (the figure plots log10(w_p/r_p); w_p is recovered by adding log10 r_p)", "yUnit": "log10(h^-1 Mpc)"},
    "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
    "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": points},
    "scatter": None,
    "selection": {"population": "all EAGLE galaxies with M* > 10^8.66 h^-2 Msun",
                  "warning": "Curve read from the vector paths of the bottom panel (log10(w_p/r_p) versus log10 r_p) of the figure of Artale et al. 2017 (MNRAS 470, 1771) that compares the z=0.1 EAGLE projected correlation function with the Zehavi+11 power-law fit; "
                             "w_p = (w_p/r_p) r_p exactly. The plotted line joins 17 binned values; vertical error bars are the jackknife errors of the paper (JN), read from the vector strokes where drawn. "
                             "The paper states that the EAGLE selection differs in detail from the SDSS samples and that the 100 Mpc box suppresses clustering beyond ~5 h^-1 Mpc. The paper gives no table of these values."},
    "definitions": {"sampleSelection": sel, "piMax": 34, "lengthUnit": "h^-1 Mpc", "projection": "w_p(r_p) = 2 int_0^pi_max xi(r_p, pi) d(pi) with the redshift-space xi(r_p, pi) (paper eq. wp_rp), averaged over three orthogonal projection directions",
                    "massDefinition": "aperture-30pkpc", "massThreshold": "M* > 10^8.66 h^-2 Msun", "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "population": "all"},
    "provenance": {"tier": "digitized-figure", "citation": "Artale et al. 2017, MNRAS 470, 1771 (arXiv:1611.05064), figure of the z=0.1 EAGLE two-point function (bottom panel, w_p)", "doi": "10.1093/mnras/stx1263",
                   "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-18", "figure": "Fig. 'xi_mstar' (file Wp-1halo2halo-Ms-gt-9.0-z0.1-JN-2.eps)", "panel": "bottom panel",
                   "checksumSha256": sha, "sourceMember": EPS.name,
                   "extractionMethod": "vector path vertices from the figure (EPS converted with ghostscript, PyMuPDF get_drawings); axes calibrated by hand on the 6 pt major ticks (outlined labels)",
                   "axisCalibrationPixels": "x ticks -1.5 ... 1.0 (step 0.5) and y ticks 5 ... -2 (step 1) fitted linearly; validated by the red reference curve: eq. (wp_ref) with r0=5.33, gamma=1.8 reproduced at 26 vertices to <0.005 dex",
                   "digitizationUncertaintyDex": 0.01},
    "calibration": "prediction", "rankable": False,
    "notes": "Vector-path extraction; exact to PDF coordinate precision. Cosmology of EAGLE: Planck 2013 (Omega_b=0.0482, Omega_dark=0.2588, Omega_Lambda=0.693, h=0.677) as quoted in the paper; sum Omega_m = 0.307."}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=1) + "\n")
print("wrote 1 record,", len(points), "points,", nb, "with error bars; red-line calibration check", CAL)
