import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1606.03086"
DOI = "10.1093/mnras/stw2265"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "rvsmvariousz-eps-converted-to.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
xm, ym = {}, {}
for d in page.get_drawings():
    for it in d["items"]:
        if it[0] != "l":
            continue
        a, b = it[1], it[2]
        if abs(a.x - b.x) < 0.05 and abs(a.y - b.y) < 12 and abs(max(a.y, b.y) - fr.y1) < 1.5:
            xm[round(a.x, 1)] = max(xm.get(round(a.x, 1), 0), abs(a.y - b.y))
        if abs(a.y - b.y) < 0.05 and abs(a.x - b.x) < 12 and abs(min(a.x, b.x) - fr.x0) < 1.5:
            ym[round(a.y, 1)] = max(ym.get(round(a.y, 1), 0), abs(a.x - b.x))
xmaj = sorted(k for k, v in xm.items() if v > 5)
ymaj = sorted(k for k, v in ym.items() if v > 7)
assert len(xmaj) == 6 and len(ymaj) == 3, (xmaj, ymaj)
fx, _ = vf.axis_fit(page, fr, "x", labels=list(zip(xmaj, [8, 9, 10, 11, 12, 13])))
fy, _ = vf.axis_fit(page, fr, "y", labels=list(zip(ymaj, [2, 1, 0])))
COL = {(0.0, 0.0, 0.0): 0.0, (1.0, 0.54, 0.0): 0.5, (0.85, 0.8, 0.0): 1.0, (0.41, 0.78, 0.55): 2.0, (0.54, 0.46, 1.0): 3.0, (0.82, 0.0, 1.0): 4.0}
got = {COL[c["color"]]: c for c in vf.curves(page, fr, fx, fy, min_items=8) if c["color"] in COL}
assert sorted(got) == sorted(COL.values()), sorted(got)
near = lambda pts, x: min(pts, key=lambda q: abs(q[0] - x))[1]
records = []
for z, c in sorted(got.items()):
    pts = sorted((round(x, 3), round(y, 4)) for x, y in c["points"] if 7.5 <= x <= 13)
    pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0]]
    assert len(pts) >= 10, (z, len(pts))
    if z == 0.0:
        assert 0.45 < near(pts, 10.0) < 0.7 and 1.3 < near(pts, 12.0) < 1.6, (near(pts, 10), near(pts, 12))
    if z == 4.0:
        assert 0.05 < near(pts, 9.0) < 0.4, near(pts, 9)
    records.append(vf.record(
        rid=f"dubois16.horizon-agn.size.z{z:g}", source="Horizon-AGN", run="Horizon-AGN (size-mass, Dubois+16)", relation="size", z=z,
        axes={"xDefinition": "log10 total stellar mass of the galaxy (galaxy finder)", "xUnit": "log10(Msun)", "yDefinition": "log10 effective radius r_eff of the galaxy", "yUnit": "log10(kpc)"},
        points=pts, population="all galaxies with at least 50 star particles (M* >= 1e8 Msun)", interval="unspecified",
        definitions={"massDefinition": "total-galaxy-finder", "imf": "unspecified", "cosmology": "unspecified", "population": "all", "sizeDefinition": "effective radius r_eff (definition as in the paper)"},
        citation=f"Dubois et al. 2016, MNRAS 463, 3948 (arXiv:{ARXIV}), size-mass relation of Horizon-AGN galaxies at different redshifts", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Size-mass relation for galaxies in Horizon-AGN at different redshifts", panel=f"z={z:g} curve", sha=sha, member="rvsmvariousz-eps-converted-to.pdf", calibration="prediction",
        calib="x and y: major ticks (longer strokes) assigned the labels read from the rendered figure (the labels are glyph paths): x 10^8 to 10^13 Msun, y 1, 10, 100 kpc, both logarithmic",
        warning=f"Median (as plotted) effective radius of Horizon-AGN galaxies at z={z:g}, read from the vector path of Dubois et al. 2016. The paper does not state in the figure caption whether r_eff is physical or comoving, nor the statistic; the IMF and cosmology are not stated near the figure.", uncertainty=0.02))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dubois16-horizonagn-size.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Horizon-AGN size-mass records from Dubois+16")
