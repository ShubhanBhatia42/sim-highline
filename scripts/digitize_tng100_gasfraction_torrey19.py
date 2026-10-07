import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1711.05261"
DOI = "10.1093/mnras/stz243"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "interp_gf_relation_L75n1820TNG.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page, 50, 50)[0]
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
xt = vf._tick_positions(page, fr, "x")
yt = vf._tick_positions(page, fr, "y")
xl = [(min(xt, key=lambda q: abs(q - cx)), float(t)) for t, cx, cy in W if t in ("8.0", "8.5", "9.0", "9.5", "10.0", "10.5", "11.0") and cy > fr.y1]
yw = sorted((cy, t) for t, cx, cy in W if t in ("1.0", "0.5", "0.0") and cx < fr.x0)
assert len(xl) == 7 and [t for _, t in yw] == ["1.0", "0.5", "0.0", "0.5", "1.0"], (xl, yw)
yl = [(min(yt, key=lambda q: abs(q - cy)), v) for (cy, _), v in zip(yw, [1.0, 0.5, 0.0, -0.5, -1.0])]
fx, _ = vf.axis_fit(page, fr, "x", labels=xl)
fy, _ = vf.axis_fit(page, fr, "y", labels=yl)
COL = {(0.0, 0.0, 0.0): 0.0, (0.0, 0.47, 0.87): 1.0, (0.0, 0.74, 0.0): 2.0, (1.0, 0.79, 0.0): 4.0}
got = {COL[c["color"]]: c for c in vf.curves(page, fr, fx, fy, min_items=8) if c["color"] in COL and abs(c["width"] - 2.0) < 0.01 and c["dashes"].startswith("[]")}
assert sorted(got) == [0.0, 1.0, 2.0, 4.0], sorted(got)
SPOT = {0.0: (9.0, -0.6, -0.2), 1.0: (9.0, -0.1, 0.3), 2.0: (9.0, 0.1, 0.5), 4.0: (9.0, 0.3, 0.7)}
records = []
for z, c in sorted(got.items()):
    pts = sorted((round(x, 3), round(y, 4)) for x, y in c["points"])
    pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
    assert len(pts) >= 20 and all(8.0 < x < 10.8 and -1.1 < y < 1.1 for x, y in pts), (z, len(pts))
    xa, lo, hi = SPOT[z]
    assert lo < min(pts, key=lambda q: abs(q[0] - xa))[1] < hi, (z, pts[:2])
    records.append(vf.record(
        rid=f"torrey19.tng100.gas.ism.z{z:g}", source="IllustrisTNG", run="TNG100-1 (ISM gas fraction, centrals, Torrey+19)", relation="gas", z=z,
        axes={"xDefinition": "log10 stellar mass within twice the stellar half-mass radius", "xUnit": "log10(Msun)", "yDefinition": "log10 gas-to-stellar mass ratio Mgas/M*, gas above the star-formation density threshold (ISM)", "yUnit": "dex"},
        points=pts, population="central galaxies", interval="unspecified",
        definitions={"gasDefinition": "gas above the star-formation density threshold (ISM)", "massDefinition": "aperture-2rhalf-stars", "imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "population": "centrals", "gasStatistic": "median"},
        citation=f"Torrey et al. 2019, MNRAS (doi 10.1093/mnras/stz243; arXiv:{ARXIV}), gas fraction as a function of stellar mass", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Gas fractions as a function of stellar mass for four redshifts", panel=f"z={z:g} solid line", sha=sha, member="interp_gf_relation_L75n1820TNG.pdf", calibration="prediction",
        calib="x and y: numeric tick labels snapped to ticks (the y labels carry no minus glyph, so signs were assigned in order down the axis, -1.0 to 1.0)",
        warning=f"Median ISM gas-to-stellar mass ratio of TNG100-1 central galaxies at z={z:g}, read from the solid vector line of Torrey et al. 2019 (the dashed power-law fits and their slopes are not extracted). Gas is that above the star-formation density threshold, so it is closer to cold neutral plus molecular gas than to all gas; compare with HI+H2 records only with that in mind.", uncertainty=0.02))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "torrey19-tng100-gas.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} TNG100 gas fraction records from Torrey+19")
