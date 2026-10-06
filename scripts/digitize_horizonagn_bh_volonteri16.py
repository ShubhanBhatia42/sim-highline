import json
import math
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1602.01941"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "mbh_mgal_z-eps-converted-to.pdf"
XMAJ = {0: [141.1, 199.7, 258.0, 316.3], 1: [368.9, 427.2, 485.5, 543.8]}
YMAJ = {0: [85.4, 145.1, 205.1], 1: [312.9, 372.6, 432.6]}
PANELS = {(0, 0): 5.0, (1, 0): 3.0, (0, 1): 2.0, (1, 1): 1.0}
GUIDE = math.log10(0.002)

page = pymupdf.open(PDF)[0]
sha = vf.sha256(PDF)
dr = page.get_drawings()
ticks = {(round(a.x, 1) if abs(a.x - b.x) < 0.01 else None, round(a.y, 1) if abs(a.y - b.y) < 0.01 else None)
         for d in dr for it in d["items"] if it[0] == "l" for a, b in [(it[1], it[2])] if 16 < max(abs(a.x - b.x), abs(a.y - b.y)) < 16.6}
for col in (0, 1):
    for x in XMAJ[col]:
        assert (x, None) in ticks, ("x tick", x)
    for row in (0, 1):
        for y in YMAJ[row]:
            assert (None, y) in ticks, ("y tick", y)


def cal(col, row):
    fx = lambda px: 9 + (px - XMAJ[col][0]) / ((XMAJ[col][-1] - XMAJ[col][0]) / 3)
    fy = lambda py: 9 - (py - YMAJ[row][0]) / ((YMAJ[row][2] - YMAJ[row][0]) / 2)
    return fx, fy


def panel_of(pts):
    cx, cy = sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts)
    return (0 if cx < 316.5 else 1, 0 if cy < 259 else 1)


def near(color, target):
    return color is not None and all(abs(c - t) < 0.01 for c, t in zip(color, target))


guides, fits, contours = {}, {}, {}
for d in dr:
    its = d["items"]
    if any(it[0] != "l" for it in its):
        continue
    pts = [its[0][1]] + [it[2] for it in its]
    if near(d["color"], (1.0, 0.65, 0.0)) and len(its) == 1:
        guides[panel_of(pts)] = pts
    elif near(d["color"], (0, 0, 0)) and 3 <= len(its) <= 4 and (abs(pts[-1].x - 316.3) < 0.2 or abs(pts[-1].x - 543.8) < 0.2) and max(q.x for q in pts) - min(q.x for q in pts) > 100:
        fits[panel_of(pts)] = pts
    elif near(d["color"], (0.66, 0.66, 0.66)):
        contours.setdefault(panel_of(pts), []).extend(pts)
assert set(guides) == set(fits) == set(PANELS) == set(contours), (set(guides), set(fits), set(contours))

records = []
for (col, row), z in PANELS.items():
    fx, fy = cal(col, row)
    for p in guides[(col, row)]:
        x, y = fx(p.x), fy(p.y)
        assert abs(y - (x + GUIDE)) < 0.02, ("guide line calibration", z, x, y)
    f = [(fx(p.x), fy(p.y)) for p in fits[(col, row)]]
    slope = (f[-1][1] - f[0][1]) / (f[-1][0] - f[0][0])
    assert all(abs((y - f[0][1]) - slope * (x - f[0][0])) < 0.02 for x, y in f), ("fit not straight", z)
    cx = [fx(p.x) for p in contours[(col, row)]]
    lo, hi = max(min(cx), f[0][0]), min(max(cx), f[-1][0])
    pts = [(x, f[0][1] + slope * (x - f[0][0])) for x in (lo, hi)]
    assert 0.8 < slope < 1.3 and hi - lo > 1.0, (z, slope, lo, hi)
    records.append(vf.record(
        rid=f"volonteri16.horizon-agn.bh.z{z:g}", source="Horizon-AGN", run="Horizon-AGN", relation="bh", z=z,
        axes={"xDefinition": "log10 total galaxy stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 black hole mass (best-fit linear correlation)", "yUnit": "log10(Msun)"},
        points=pts, population="galaxies in haloes above 8e10 Msun with >50 star particles",
        warning=f"Best-fit linear correlation (black line, slope {slope:.3f}) read from Volonteri et al. 2016 (MNRAS 460, 2979), Fig. 12 panel z={z:g}; the paper gives no table. "
                "Recorded as the line's two ends, clipped to the extent of the plotted galaxy contours (themselves cut by the plot's lower limit near M_BH = 10^6.1 Msun); the line is a straight fit, nothing is interpolated. The figure's orange guide line (M_BH = 0.002 M_gal) was used to verify the axis calibration. "
                "The -0.33 dex galaxy-mass shift the paper applies in its z=0 observational comparison does not apply to this figure.",
        definitions={"massDefinition": "stellar mass within region above 178x mean total matter density", "imf": "unspecified", "cosmology": {"H0": 70.4, "Om": 0.272}, "population": "all", "bhMassMethod": "simulation-bh-particle"},
        citation=f"Volonteri et al. 2016, MNRAS 460, 2979, Fig. 12 (arXiv source numbering) panel z={z:g}", doi="10.1093/mnras/stw1123", url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Figure 12", panel=f"{'top' if row == 0 else 'bottom'} {'left' if col == 0 else 'right'} (z={z:g})", sha=sha, member=f"{PDF.name} (black best-fit line)",
        calib="x: major ticks 9-12 (58.4 pt/dex); y: major ticks 7-9 (59.9 pt/dex) by panel; labels are outlines so tick values taken from the render; guide line M_BH=0.002 M_gal asserted",
        uncertainty=0.02, calibration="prediction"))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "volonteri16-horizonagn-bh.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Horizon-AGN BH-galaxy mass records; guide line verified in all panels")
