import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1706.06605"
DOI = "10.1093/mnras/sty1024"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "plot" / "smd.pdf"
# dash pattern of the black line -> integration limit, as stated in the text of Sec. 6 (solid > 1e6, dashed > 1e4, dotted > 1e8 Msun)
LIMITS = {"[ 7.4 3.2 ]": 4, "[]": 6, "[ 3 4.95 ]": 8}

page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page, 100, 60)[0]
fx, xt = vf.axis_fit(page, fr, "x")
fy, yt = vf.axis_fit(page, fr, "y")
ylo, yhi = fy(fr.y1), fy(fr.y0)
black = lambda c: c is not None and all(abs(v) < 0.02 for v in c)
got = {}
for c in vf.curves(page, fr, fx, fy, min_items=5):
    if black(c["color"]) and c["width"] in (2.0, 3.0) and len(c["raw"]) == 8:
        for dash, lim in LIMITS.items():
            if (c["dashes"] or "").startswith(dash) and (dash != "[]" or c["width"] == 2.0):
                got[lim] = c
assert sorted(got) == [4, 6, 8], sorted(got)
AX = {"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 stellar mass density, model stellar mass function integrated above the mass limit (axis label rho_* in Msun Mpc^-3)", "yUnit": "log10(Msun Mpc^-3)"}
SPOT = {4: (5.0, 6.9, 7.3), 6: (5.0, 6.8, 7.2), 8: (5.0, 6.8, 7.1)}
records = []
for lim, c in sorted(got.items()):
    pts = [(round(x, 3), round(y, 4)) for x, y in c["points"] if ylo + 0.01 < y < yhi - 0.01]
    assert all(abs(x - round(x)) < 0.01 for x, _ in pts) and pts[0][0] == 5.0 and len(pts) >= 5, (lim, pts[:3])
    pts = [(float(round(x)), y) for x, y in pts]
    xa, lo, hi = SPOT[lim]
    y0 = dict(pts)[xa]
    assert lo < y0 < hi, (lim, y0)
    records.append(vf.record(
        rid=f"ma18.fire2.smd.mstar-gt-1e{lim}", source="FIRE-2", run=f"FIRE-2 high-z zoom sample (model, M* > 1e{lim} Msun)", relation="smd", z=7.0, z_range=(pts[0][0], pts[-1][0]), axes=AX, points=pts,
        population=f"central galaxies in the weighted zoom sample, integrated above M* = 1e{lim} Msun", interval="unspecified",
        definitions={"massDefinition": "stars-within-third-Rmax-masked", "imf": "kroupa01", "cosmology": {"H0": 68, "Om": 0.31}, "densityFrame": "comoving", "population": f"central galaxies, M* > 1e{lim} Msun"},
        citation=f"Ma et al. 2018, MNRAS 478, 1694 (arXiv:{ARXIV}), stellar mass density from z=5 to 12", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="Stellar mass density from z=5-12", panel=f"M* > 1e{lim} Msun line", sha=sha, member="plot/smd.pdf",
        calibration="prediction", uncertainty=0.02, retrieved="2026-10-14", calib="x: labelled redshifts 5-12 snapped to ticks (linear); y: labelled ticks 4.0-7.5 snapped to ticks (linear)",
        warning=f"Stellar mass density derived by the authors by integrating their fitted model stellar mass functions above M* = 1e{lim} Msun, read from the vertices of the line in the stellar mass density figure of Ma et al. 2018 (one vertex per integer redshift); no table exists. "
                "It is a model integral, not a direct count in the simulations, and the FIRE-2 zoom sample is not a periodic volume; the axis label gives Mpc^-3 and the frame is taken to be comoving as for the paper's mass functions. "
                "Vertices below the lowest plotted density (4.0) are outside the plot and not recorded. Observational points are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ma18-fire2-smd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIRE-2 stellar mass density records from Ma+18 vector paths")
for r in records:
    p = r["representation"]["points"]
    print(r["id"], len(p), [(q["x"], q["y"]) for q in p])
