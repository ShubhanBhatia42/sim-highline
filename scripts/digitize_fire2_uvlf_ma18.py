import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1706.06605"
DOI = "10.1093/mnras/sty1024"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "plot" / "lfall.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page, 100, 100)[0]
ticks = vf._tick_positions(page, fr, "y")
ws = sorted(((w[1] + w[3]) / 2, vf.number(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and 55 < (w[0] + w[2]) / 2 < fr.x0 and fr.y0 <= (w[1] + w[3]) / 2 <= fr.y1)
labs = [(min(ticks, key=lambda t: abs(t - cy - (6.0 if v < 0 else 0.0))), v) for cy, v in ws]
fy, yt = vf.axis_fit(page, fr, "y", labels=labs)
fx, xt = vf.axis_fit(page, fr, "x")
COLS = {(0.0, 0.0, 0.0): (6.0, 9), (0.0, 0.0, 1.0): (8.0, 7), (1.0, 0.0, 0.0): (10.0, 7), (0.0, 0.5, 0.0): (12.0, 6)}
records = []
for col, (z, n) in COLS.items():
    pts = []
    for d in page.get_drawings():
        if d["color"] is None or any(abs(a - b) > 0.02 for a, b in zip(d["color"], col)) or d["fill"] is None:
            continue
        r = d["rect"]
        if not (5 < r.width < 16 and 5 < r.height < 16) or not (fr.x0 <= r.x0 <= fr.x1 and fr.y0 <= r.y0 <= fr.y1) or (r.x0 < 130 and r.y0 > 270):
            continue
        pts.append((fx((r.x0 + r.x1) / 2), fy((r.y0 + r.y1) / 2)))
    pts = sorted(set((round(x, 3), round(y, 4)) for x, y in pts))
    assert len(pts) == n, (z, len(pts))
    assert all(-23.5 < x < -8 and -5 < y < 1 for x, y in pts) and all(a[1] < b[1] for a, b in zip(pts, pts[1:])), (z, pts)
    records.append(vf.record(
        rid=f"ma18.fire2.uvlf.z{z:g}", source="FIRE-2", run="FIRE-2 high-z zoom sample (volume-weighted)", relation="uvlf", z=z,
        axes={"xDefinition": "absolute magnitude at rest-frame 1500 A (intrinsic, no dust attenuation)", "xUnit": "mag (AB)", "yDefinition": "log10 luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"},
        points=pts, population="central galaxies of the zoom-in sample, weighted to the halo mass function", interval="unspecified", connect=False, scatter=True,
        definitions={"imf": "kroupa01", "cosmology": {"H0": 68, "Om": 0.31}, "densityFrame": "comoving", "uvBand": "rest-frame 1500 A", "dustCorrection": "none (intrinsic)", "population": "centrals"},
        citation=f"Ma et al. 2018, MNRAS 478, 1694 (arXiv:{ARXIV}), predicted luminosity functions at 1500 A, z={z:g}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Predicted luminosity functions at rest-frame 1500 A, B and J band", panel=f"left panel (1500 A), z={z:g}", sha=sha, member="plot/lfall.pdf", calibration="prediction",
        calib="x: numeric tick labels snapped to ticks (axis runs from -8 to -24); y: labels paired with ticks (signed-label boxes sit about 6 pt low)",
        warning="Open symbols are the luminosity function derived from the weighted FIRE-2 zoom-in sample (the paper's dashed model lines are not extracted). Magnitudes are intrinsic: no dust attenuation, BPASS v2 binary models with a Kroupa IMF. Marker centres read from the vector paths.",
        strict=False))
    records[-1]["epoch"]["mode"] = "published-epoch"
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ma18-fire2-uvlf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIRE-2 UV luminosity function records from Ma+18")
