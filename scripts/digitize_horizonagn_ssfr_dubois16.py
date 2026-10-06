import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1606.03086"
DOI = "10.1093/mnras/stw2265"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "ssfrvsmgal-eps-converted-to.pdf"
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
xmaj = sorted(k for k, v in xm.items() if v > 1.5 * min(xm.values()) and v > 5)
ymaj = sorted(k for k, v in ym.items() if v > 1.5 * min(v2 for v2 in ym.values() if v2 > 0.5) and v > 7)
assert len(xmaj) == 5 and len(ymaj) == 3, (xmaj, ymaj)
fx, _ = vf.axis_fit(page, fr, "x", labels=list(zip(xmaj, [9, 10, 11, 12, 13])))
fy, _ = vf.axis_fit(page, fr, "y", labels=list(zip(ymaj, [-1.0, -2.0, -3.0])))
cs = [c for c in vf.curves(page, fr, fx, fy, min_items=5) if c["color"] == (0.0, 0.0, 0.0) and len(c["points"]) in (11, 14) and (len(c["points"]) == 14) == bool(c["dashes"].startswith("[ "))]
solid = [c for c in cs if len(c["points"]) == 11]
dashed = [c for c in cs if len(c["points"]) == 14]
assert len(solid) == 1 and len(dashed) == 1, (len(solid), len(dashed))
records = []
for c, run, name in ((solid[0], "Horizon-AGN (mean sSFR, Dubois+16)", "Horizon-AGN"), (dashed[0], "Horizon-noAGN (mean sSFR, Dubois+16)", "Horizon-noAGN")):
    pts = sorted((round(x, 3), round(y - 9.0, 4)) for x, y in c["points"])
    assert all(9.0 <= x <= 13.6 for x, _ in pts) and len(pts) >= 11, name
    if name == "Horizon-AGN":
        assert -10.3 < pts[0][1] < -9.9 and pts[-1][1] < -10.4, (pts[0], pts[-1])
    else:
        assert all(-10.4 < y < -9.9 for _, y in pts), pts
    records.append(vf.record(
        rid=f"dubois16.{name.lower()}.ssfr.z0.3", source="Horizon-AGN", run=run, relation="ssfr", z=0.3,
        axes={"xDefinition": "log10 total stellar mass of the galaxy (galaxy finder)", "xUnit": "log10(Msun)", "yDefinition": "log10 mean specific star formation rate (axis in Gyr^-1, converted to yr^-1)", "yUnit": "log10(yr^-1)"},
        points=pts, population=f"all galaxies, {name} at z=0.3", interval="unspecified",
        definitions={"massDefinition": "total-galaxy-finder", "imf": "unspecified", "cosmology": "unspecified", "population": "all", "sfrStatistic": "mean", "sfrTimescaleMyr": "unspecified"},
        citation=f"Dubois et al. 2016, MNRAS 463, 3948 (arXiv:{ARXIV}), mean sSFR as a function of stellar mass at z=0.3", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Mean sSFR versus galaxy stellar mass for Horizon-AGN (solid) and Horizon-noAGN (dashed) at z=0.3", panel="solid line" if name == "Horizon-AGN" else "dashed line", sha=sha, member="ssfrvsmgal-eps-converted-to.pdf", calibration="prediction",
        calib="x and y: major ticks (longer strokes) assigned the labels read from the rendered figure (glyph paths): x 9-13 in log10 M, y 0.001, 0.01, 0.1 Gyr^-1 (log); y converted to yr^-1 by subtracting 9 dex",
        warning=f"Mean sSFR of {name} galaxies at z=0.3, read from the vector path of Dubois et al. 2016 (the error bars of the mean and the Karim+11 points are not extracted). AGN feedback creates a population of passive massive galaxies, absent without AGN.", uncertainty=0.02))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dubois16-horizonagn-ssfr.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Horizon-AGN sSFR records from Dubois+16")
