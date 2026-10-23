"""Dave et al. 2019 (arXiv:1901.10203), Fig. mainseqhist: histograms of the specific SFR of SIMBA m100n1024 galaxies at z=0.1 in three stellar-mass bins
(vector lines through the bin centres) -> one `ssfr` distribution record stored as pseudo-counts (the figure plots fractions per bin; no galaxy numbers).
Usage: python3 -I digitize_simba_ssfr_hist_dave19.py [path-to-unpacked-arxiv-source]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
import vector_figure as vf

OUT = HERE.parent / "data" / "staged" / "dave19-simba-ssfr-hist.json"  # every record the script makes; the ones in the dataset are promoted by hand into data/curves (see data/staged/README.md)
ARXIV = "1901.10203"
DOI = "10.1093/mnras/stz937"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "mainseqhist_z0.pdf"
N_REF = 100000
BLUE, GREEN, RED = (0.0, 0.0, 0.5), (0.0, 0.5, 0.0), (0.86, 0.08, 0.24)
vf.LABEL_MAX = 60


def near(c, t, tol=0.02):
    return all(abs(a - b) < tol for a, b in zip(c, t))


page = vf.page_of(PDF)
sha = vf.sha256(PDF)
f = vf.frames(page)[0]
words = page.get_text("words")
xl = sorted([((w[0] + w[2]) / 2, float(w[4])) for w in words if re.fullmatch(r"\d\.\d", w[4]) and f.y1 < w[1] < f.y1 + 10], key=lambda t: t[0])
assert len(xl) == 8
vals = [-3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0, 0.5]  # the minus signs are not in the text layer: the digit sequence 3.0..0.5..0.0 0.5 runs from -3.0 to +0.5
(p0, _), (p5, _) = xl[6], xl[7]
slope = (p5 - p0) / 0.5
shifts = [p - (p0 + slope * v) for (p, _), v in zip(xl[:6], vals[:6])]
assert max(shifts) - min(shifts) < 0.05, shifts  # all negative labels are offset by the same (minus-sign) width
lab = [(p0, 0.0), (p5, 0.5)] + [(p - s, v) for (p, _), v, s in zip(xl[:6], vals[:6], shifts)]
fx, xt = vf.axis_fit(page, f, "x", labels=lab)
fy, yt = vf.axis_fit(page, f, "y")
assert [v for _, v in xt] == vals[:6] + [0.0, 0.5] or sorted(v for _, v in xt) == sorted(vals), xt
assert sorted(round(v, 1) for _, v in yt) == [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7], yt
# legend: three solid lines top to bottom = 1e9<M*<1e10, 1e10<M*<1e11, M*>1e11
leg = sorted((d["rect"].y0, tuple(round(v, 2) for v in d["color"])) for d in page.get_drawings() if d["type"] == "s" and len(d["items"]) == 1 and d["width"] >= 1.5 and d["rect"].width > 10)
assert [c for _, c in leg] == [BLUE, GREEN, RED], leg
tw = [w[4] for w in words]
assert tw.count("109") == 1 and tw.count("1010") == 2 and tw.count("1011") == 2 and "Simba," in tw and "GSWLC-D2" in tw and "z=0.1" in tw
cs = vf.curves(page, f, fx, fy, min_items=3)
cols = {}
for key, col in (("m9-10", BLUE), ("m10-11", GREEN), ("m11+", RED)):
    sel = [c for c in cs if near(c["color"], col) and c["dashes"] == "[] 0"]
    assert len(sel) == 1, key
    pts = np.array(sel[0]["points"])
    assert abs(pts[:, 1].sum() - 1.0) < 0.002, (key, pts[:, 1].sum())  # fractions per bin sum to one: calibration check
    cols[key] = pts
xs = cols["m9-10"][:, 0]
assert all(np.allclose(c[:, 0], xs, atol=1e-3) for c in cols.values()) and np.allclose(np.diff(xs), 0.2, atol=1e-3)
# the first non-zero bin sits at log sSFR = -2.5 Gyr^-1, the paper's stated floor ("All galaxies with sSFR<10^-2.5 Gyr^-1 are placed in the lowest bin")
for key, c in cols.items():
    nz = np.nonzero(c[:, 1] > 1e-3)[0]
    assert abs(c[nz[0], 0] + 2.5) < 1e-3, (key, c[nz[0], 0])
keep = [k for k in range(len(xs)) if -2.5 - 1e-3 <= xs[k] <= 0.3 + 1e-3]
assert all(abs(c[k, 1]) < 1e-3 for c in cols.values() for k in range(len(xs)) if k not in keep)
yedges = [round(float(xs[k]) - 0.1 - 9.0, 3) for k in keep] + [round(float(xs[keep[-1]]) + 0.1 - 9.0, 3)]  # Gyr^-1 -> yr^-1: subtract 9 dex
counts = [[int(round(N_REF * max(c[k, 1], 0.0))) for k in keep] for c in cols.values()]
# quenched fraction below the paper's z=0 cut sSFR = 10^-1.8 Gyr^-1 (bins with centre <= -1.9), compared with the text
cut = [round(float(sum(c[k, 1] for k in keep if xs[k] <= -1.9 + 1e-6)), 3) for c in cols.values()]
rec = {
    "id": "dave19.simba.ssfr-hist.m100n1024.z0p1", "source": "SIMBA", "run": "m100n1024 (per galaxy, normalised sSFR histogram in three mass bins)", "kind": "simulation", "relation": "ssfr",
    "epoch": {"zRepresentative": 0.1, "zNominal": 0.1, "zMin": 0.1, "zMax": 0.1, "mode": "published-epoch", "snapshot": None},
    "axes": {"xDefinition": "log10 stellar mass (bins 1e9-1e10, 1e10-1e11, >1e11; the last bin is open: 12.0 is a nominal upper edge)", "xUnit": "log10(Msun)",
             "yDefinition": "log10 specific SFR (instantaneous SFR of the gas elements / stellar mass); the lowest bin holds all galaxies with sSFR < 10^-2.5 Gyr^-1 (axis in Gyr^-1, converted by subtracting 9 dex)", "yUnit": "log10(yr^-1)"},
    "domain": {"xMin": 9.0, "xMax": 12.0},
    "representation": {"type": "distribution", "xEdges": [9.0, 10.0, 11.0, 12.0], "yEdges": yedges, "counts": counts,
                       "weighting": f"pseudo-counts: fraction of the galaxies of the mass bin per 0.2-dex sSFR bin (the figure's 'fraction', sums to 1) x {N_REF}; relative within a mass bin only, not galaxy numbers", "intervalKind": "scatter"},
    "scatter": None,
    "selection": {"population": "all SIMBA m100n1024 galaxies in the stellar-mass bin at z=0.1 (centrals and satellites)",
                  "warning": ("Fractions of galaxies per sSFR bin read from the vector lines (through the bin centres) of Dave et al. 2019 (MNRAS 486, 2827), Fig. mainseqhist (solid lines, SIMBA z=0.1); no table is published. "
                              "The caption says 'All galaxies with sSFR<10^-2.5 Gyr^-1 are placed in the lowest bin': the lowest bin (centre log sSFR = -2.5 Gyr^-1 = -11.5 yr^-1) is therefore an underflow bin and its nominal edges are not physical limits. "
                              "The stellar-mass bins are 1e9-1e10, 1e10-1e11 and >1e11 Msun; the upper edge of the last bin is not stated and 12.0 is a nominal value. The dotted GSWLC-D2 observed histograms are not stored. "
                              "The figure plots fractions, not counts; no galaxy numbers are given. The SFR-M* scatter plots of the same paper (mainseq_z0.jpg, mainseq_z2.jpg) are JPEG rasters and cannot be used.")},
    "definitions": {"imf": "unspecified", "cosmology": {"H0": 68, "Om": 0.3}, "massDefinition": "unspecified", "population": "all", "sfrTimescaleMyr": "instantaneous",
                    "sfrStatistic": "per-galaxy", "sfrIndicator": "instantaneous SFRs from the gas elements"},
    "provenance": {"tier": "digitized-figure", "citation": "Dave et al. 2019, MNRAS 486, 2827 (arXiv:1901.10203), sSFR histograms in three stellar-mass bins at z=0.1 (SIMBA, solid lines)", "doi": DOI,
                   "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-18", "figure": "mainseqhist (histogram of sSFR in three bins of stellar mass)", "panel": "SIMBA z=0.1 solid lines", "checksumSha256": sha,
                   "sourceMember": f"{PDF.name} (2 pt solid lines blue, green, red)", "extractionMethod": "vector path vertices from the figure PDF (PyMuPDF get_drawings), transformed through axes calibrated on labelled tick marks",
                   "axisCalibrationPixels": "x: labelled ticks -3.0..0.5 (the minus signs are missing from the text layer; the six negative labels share the same offset to their ticks, asserted); y: labelled ticks 0.0-0.7; each curve sums to 0.9999",
                   "digitizationUncertaintyDex": 0.01},
    "calibration": "prediction", "rankable": False,
    "notes": f"Vector-path extraction. Fraction below sSFR = 10^-1.8 Gyr^-1 (the z=0 star-forming cut of the paper) per mass bin: {cut}.",
}
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print("quenched fraction (sSFR < 10^-1.8 Gyr^-1) per bin 9-10, 10-11, >11:", cut)
print("lowest-bin fractions:", [round(float(c[keep[0], 1]), 3) for c in cols.values()], "nbins", len(keep))
print(f"Wrote 1 record to {OUT}")
