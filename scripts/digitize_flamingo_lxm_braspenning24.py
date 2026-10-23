"""Braspenning et al. 2024 (arXiv:2312.08277, MNRAS 533, 2656): FLAMINGO median X-ray luminosity - halo mass relation (L_X,500c E(z)^-2, 0.5-2.0 keV, within R500c vs M500c),
read from the vector paths of the top-right panel of figures/4diffpanel_scaling_relations_Redshift_2.00WithoutRecentAGNHeating_redshifts.pdf
(4 runs x z = 0, 1, 2). The redshift of each line is identified from the figure's colour bar (a raster strip whose pixel colours at z = 0, 1, 2 equal the three line colours).
Checks: log axes calibrated on the major ticks (decade labels asserted from the text layer); fiducial L1_m9 z=0 line fitted with the paper's eq. powerlaw_fit over 10^13.5-10^15 Msun
reproduces the tabulated alpha = 1.75, beta = 42.24 (Table slope_and_norm); the same fiducial line read from the second figure (2diffpanel ..., model variations) agrees.
The Y-M panel of the same figure is NOT stored: the paper quotes no Y number to check it against (see NOTES).
Run: python3 -I digitize_flamingo_lxm_braspenning24.py [path-to-unpacked-arxiv-source]
"""
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))      
import vector_figure as vf  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "staged" / "braspenning24-flamingo-lxm.json"  # withheld: only partly verified (see data/staged/README.md)
ARXIV = "2312.08277"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
F4 = SRC / "figures" / "4diffpanel_scaling_relations_Redshift_2.00WithoutRecentAGNHeating_redshifts.pdf"
F2 = SRC / "figures" / "2diffpanel_scaling_relations_WithoutRecentAGNHeating_models_diffpans.pdf"
page4, page2 = vf.page_of(F4), vf.page_of(F2)
SHA4, SHA2 = vf.sha256(F4), vf.sha256(F2)

# ---- colour bar -> redshift
doc = pymupdf.open(F4)
img = doc[0].get_images()[0]
im = Image.open(io.BytesIO(doc.extract_image(img[0])["image"])).convert("RGB")
w = im.size[0]
col_at = lambda z: tuple(round(v / 255, 2) for v in im.getpixel((int(round(z / 2 * (w - 1))), im.size[1] // 2)))
ZCOL = {0.0: col_at(0.0), 1.0: col_at(1.0), 2.0: col_at(2.0)}
assert len(set(ZCOL.values())) == 3 and ZCOL[0.0] == (1.0, 0.56, 0.12) and ZCOL[2.0] == (0.5, 0.0, 0.0)
bbox = doc[0].get_image_info()[0]["bbox"]
lab = {x[4]: (x[0] + x[2]) / 2 for x in doc[0].get_text("words")}
assert abs((lab["0.25"] - bbox[0]) / (bbox[2] - bbox[0]) - 0.25 / 2) < 0.005        # the colour bar spans z = 0 ... 2 linearly (tick label 0.25 sits at 1/8 of the bar)

DASH = {"[] 0": "L1_m9", "[ 5.55 2.4 ] 0": "L2p8_m9", "[ 9.6 2.4 1.5 2.4 ] 0": "L1_m10", "[ 1.5 2.475 ] 0": "L1_m8"}


def calibrate(page, frame):
    words = {x[4] for x in page.get_text("words")}
    assert {"1013", "1014", "1015", "1041", "1042", "1043", "1044", "1045"} <= words
    xs, ys = set(), set()
    lens = {}
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if abs(a.x - b.x) < 0.05 and abs(max(a.y, b.y) - frame.y1) < 1 and frame.x0 - 1 <= a.x <= frame.x1 + 1:
                lens.setdefault(("x", round(a.x, 2)), round(abs(a.y - b.y), 1))
            if abs(a.y - b.y) < 0.05 and abs(min(a.x, b.x) - frame.x0) < 1 and frame.y0 - 1 <= a.y <= frame.y1 + 1:
                lens.setdefault(("y", round(a.y, 2)), round(abs(a.x - b.x), 1))
    for axis, store in (("x", xs), ("y", ys)):
        L = [(p, l) for (ax, p), l in lens.items() if ax == axis and l < 100]
        top = max(l for _, l in L)
        store.update(p for p, l in L if abs(l - top) < 0.15)
    return sorted(xs), sorted(ys)


def panel_axes(page, frame, xexp0, yexp_top, ny):
    xs, ys = calibrate(page, frame)
    return xs, ys


frames4 = vf.frames(page4)
frame = frames4[1]                                                  # top right: L_X,500c E(z)^-2 versus M500c
xs, ys = calibrate(page4, frame)
assert len(xs) == 3 and len(ys) == 5, (xs, ys)
kx, cx = np.polyfit(xs, [13, 14, 15], 1)
ky, cy = np.polyfit(ys, [45, 44, 43, 42, 41], 1)
assert np.allclose(kx * np.array(xs) + cx, [13, 14, 15], atol=0.005) and np.allclose(ky * np.array(ys) + cy, [45, 44, 43, 42, 41], atol=0.005)
fx = lambda p: kx * p + cx
fy = lambda p: ky * p + cy
assert abs(fx(frame.x0) - 13) < 0.03                                # frame left edge is 10^13 Msun (minimum halo mass of the selection)


def lines(page, frame, fxx, fyy):
    out = {}
    for c in vf.curves(page, frame, fxx, fyy, min_items=4):
        for z, col in ZCOL.items():
            if c["color"] == col and c["dashes"] in DASH and abs(c["width"] - 1.5) < 0.01:
                pts = [(x, y) for x, y in c["points"] if 13 - 0.01 <= x <= 15.5 and 40.5 <= y <= 45.5]
                out[(DASH[c["dashes"]], z)] = pts
    return out


L4 = lines(page4, frame, fx, fy)
assert len(L4) == 12, sorted(L4)
for k, p in L4.items():
    assert len(p) >= 8 and all(a[0] < b[0] for a, b in zip(p, p[1:])), (k, len(p))

# ---- check 1: paper's power-law fit (eq. powerlaw_fit) of the fiducial z=0 line against the tabulated alpha, beta
p = np.array(L4[("L1_m9", 0.0)])
m = (p[:, 0] >= 13.5) & (p[:, 0] <= 15.0)
# The paper does not define m_500c in eq. powerlaw_fit. A pivot of 10^13.5 Msun (the lower end of the fit range, m = M500c / 10^13.5) is the only choice among 10^13, 10^13.5, 10^14
# that reproduces the tabulated beta (42.24) to 0.03 dex; it is INFERRED, so this check is partial (flagged in the records and NOTES.md).
alpha, beta = np.polyfit(p[m, 0] - 13.5, p[m, 1], 1)
assert abs(alpha - 1.75) < 0.05 and abs(beta - 42.24) < 0.06, (alpha, beta)
alt = {piv: float(np.polyfit(p[m, 0] - piv, p[m, 1], 1)[1]) for piv in (13.0, 14.0)}
assert all(abs(v - 42.24) > 0.5 for v in alt.values()), alt
FIT = (float(alpha), float(beta), int(m.sum()))
assert "L1\\textunderscore m9 & 0.55 & 7.05 & 1.75 & 42.24" in (SRC / "main.tex").read_text(errors="replace")

# ---- check 2: the same fiducial line in the second figure (left panel of the model-variation figure)
fr2 = vf.frames(page2)[0]
xs2, ys2 = calibrate(page2, fr2)
assert len(xs2) == 3 and len(ys2) == 5
k2x, c2x = np.polyfit(xs2, [13, 14, 15], 1)
k2y, c2y = np.polyfit(ys2, [45, 44, 43, 42, 41], 1)
cs2 = [c for c in vf.curves(page2, fr2, lambda q: k2x * q + c2x, lambda q: k2y * q + c2y, min_items=4) if c["dashes"] == "[] 0" and abs(c["width"] - 1.5) < 0.01]
best = None
for c in cs2:
    q = np.array([(x, y) for x, y in c["points"] if 13.5 <= x <= 15 and 40.5 <= y <= 45.5])
    if len(q) < 8:
        continue
    d = np.interp(p[m, 0], q[:, 0], q[:, 1], left=np.nan, right=np.nan) - p[m, 1]
    d = d[~np.isnan(d)]
    if len(d) >= 8 and (best is None or np.max(np.abs(d)) < best[0]):
        best = (float(np.max(np.abs(d))), len(d))
assert best is not None and best[0] < 0.03, best
CROSS = best

# ---- records
CITE = "Braspenning et al. 2024, MNRAS 533, 2656 (arXiv:2312.08277), Fig. 'scaling_relations_evolution' (top right)"
SEL = ("all haloes with M500c > 10^13 Msun from the FLAMINGO halo catalogues (VELOCIraptor + SOAP); median L_X in mass bins; gas excluding star-forming particles, particles heated by AGN in the last 15 Myr and particles with T < 10^5 K")
recs = []
RUNINFO = {"L1_m9": "L1_m9 (1 Gpc box, fiducial resolution, fiducial model)", "L2p8_m9": "L2p8_m9 (2.8 Gpc box, fiducial resolution, fiducial model)", "L1_m10": "L1_m10 (1 Gpc box, low resolution)", "L1_m8": "L1_m8 (1 Gpc box, high resolution)"}
for (run, z), pts in sorted(L4.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    pp = [{"x": round(x, 3), "y": round(y, 4)} for x, y in pts]
    scaled = z > 0
    recs.append({
        "id": f"braspenning24.flamingo-{run.lower().replace('_', '-')}.lxm.z{int(z)}", "source": "FLAMINGO", "run": run, "kind": "simulation", "relation": "lxm",
        "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": "log10 M500c (spherical overdensity, 500 times the critical density)", "xUnit": "log10(Msun)",
                 "yDefinition": "log10 median X-ray luminosity L_X,500c E(z)^-2 (0.5-2.0 keV band, within R500c, core included) as plotted" + ("; at z=0 E(z)=1 so this is the physical luminosity" if not scaled else "; E(z)^-2 scaled, i.e. NOT the physical luminosity (multiply by E(z)^2)"),
                 "yUnit": "log10(erg s^-1)"},
        "domain": {"xMin": pp[0]["x"], "xMax": pp[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "unspecified", "connect": True, "points": pp}, "scatter": None,
        "selection": {"population": "all haloes with M500c > 10^13 Msun (groups and clusters)",
                      "warning": f"Median relation read from the vector paths of the top-right panel of the paper's Fig. on the evolution of the scaling relations; run {RUNINFO[run]}, z = {z:g} (identified from the colour bar). {SEL}. "
                                 "The paper gives the power-law fit only for the z=0 fiducial run (Table slope_and_norm: alpha = 1.75, beta = 42.24 for log L = alpha log M500c + beta between 10^13.5 and 10^15 Msun); no table of the curves. "
                                 "The 16th-84th percentile band (z=0 only) is not extracted. Luminosity: ROSAT-band emissivity from Cloudy tables summed over particles inside R500c."},
        "definitions": {"xrayBand": "0.5-2.0 keV (ROSAT band)", "coreTreatment": "with core", "haloMassDefinition": "M500crit", "luminosityAperture": "within R500c (3D, spherical)",
                        "luminosityScaling": "E(z)^-2 applied (E(z)=H(z)/H0)" if scaled else "E(z)^-2 (=1 at z=0)", "statistic": "median",
                        "cosmology": {"H0": 68.1, "Om": 0.306}, "cosmologyNote": "FLAMINGO D3A cosmology as in Schaye+23 (as used by the repository's FLAMINGO records); not restated numerically in Braspenning+24",
                        "sampleSelection": SEL, "massDefinition": "not applicable (halo mass M500c)", "population": "all"},
        "provenance": {"tier": "digitized-figure", "citation": CITE, "doi": "10.1093/mnras/stae1436", "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-18",
                       "figure": "Fig. scaling_relations_evolution (4 panels; top right: L_X-M500c)", "panel": "top right", "checksumSha256": SHA4,
                       "sourceMember": f"figures/{F4.name} ({run}, line style {[k for k, v in DASH.items() if v == run][0]}, colour of z = {z:g})",
                       "extractionMethod": "vector path vertices from the figure PDF (PyMuPDF get_drawings), log axes calibrated on the major ticks (decade labels 10^13-10^15 Msun and 10^41-10^45 erg/s asserted from the text layer)",
                       "axisCalibrationPixels": "x: 3 major ticks fitted to 13, 14, 15; y: 5 major ticks fitted to 45 ... 41; frame left edge = 10^13 Msun", "digitizationUncertaintyDex": 0.01},
        "calibration": "prediction", "rankable": False,
        "notes": (f"PARTIAL verification (fiducial L1_m9, z=0): fit of log L = alpha (log M500c - 13.5) + beta over 10^13.5-10^15 Msun to the digitized vertices gives alpha = {FIT[0]:.3f}, beta = {FIT[1]:.2f} against the paper's table 1.75, 42.24; the paper does not define m_500c, the 10^13.5 Msun pivot is inferred (10^13 or 10^14 give beta off by ~0.8); "
                  f"the same line read from the model-variation figure differs by <= {CROSS[0]:.3f} dex. Redshift of the line from the colour bar (pixel colours at z = 0, 1, 2 equal the line colours exactly).")})
# DOI check is done by hand (Crossref) and recorded in NOTES.md
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=1) + "\n")
print(f"wrote {len(recs)} records; fit alpha, beta, n = {FIT}; cross-figure max diff {CROSS}")
