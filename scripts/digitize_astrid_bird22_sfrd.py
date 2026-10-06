import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2111.01160"
DOI = "10.1093/mnras/stac648"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "plots" / "sfrd.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
fx, xt = vf.axis_fit(page, fr, "x")
ws = sorted(((w[1] + w[3]) / 2, -vf.number(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and 30 < (w[0] + w[2]) / 2 < fr.x0 and fr.y0 <= (w[1] + w[3]) / 2 <= fr.y1)
ticks = vf._tick_positions(page, fr, "y")
assert len(ws) == len(ticks) == 8
fy, yt = vf.axis_fit(page, fr, "y", labels=[(t, v) for t, (_, v) in zip(ticks, ws)])
cs = [c for c in vf.curves(page, fr, fx, fy, min_items=100) if c["color"] == (0.0, 0.0, 0.0) and not c["dashes"].startswith("[ ")]
assert len(cs) == 1
pts = cs[0]["points"]
pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0]]
ys = {round(x): y for x, y in pts}
assert 2.4 < pts[0][0] < 3.0 and pts[-1][0] > 11.8 and -1.2 < ys[3] < -0.9 and -2.2 < ys[6] < -1.8 and -3.4 < ys[10] < -3.0, (pts[0], pts[-1], ys[3], ys[6], ys[10])
rec = vf.record(
    rid="bird22.astrid.sfrd.total", source="ASTRID", run="ASTRID (250 Mpc/h)", relation="sfrd", z=7.0,
    axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic star-formation rate density of the whole box", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
    points=pts, population="all star formation in the box", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
    definitions={"imf": "unspecified", "cosmology": {"H0": 67.74, "Om": 0.3089}, "densityFrame": "comoving", "sfrIndicator": "instantaneous SFR of star-forming gas", "population": "all galaxies"},
    citation=f"Bird et al. 2022, MNRAS 512, 3703 (arXiv:{ARXIV}), star formation rate density over time", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
    figure="Star Formation Rate Density over time", panel="whole simulation box (solid black line)", sha=sha, member="plots/sfrd.pdf", calibration="prediction",
    calib="x: numeric tick labels snapped to tick marks; y: positive tick words negated (the minus signs are drawn as paths) and paired with the tick marks in order",
    warning="Total cosmic SFR density of the ASTRID box versus redshift (z about 2.7 to 12), read from the vector paths of Bird et al. 2022. The grey dashed line (halos with SFR above 0.3 Msun/yr only) is not extracted. The cosmology and IMF follow the existing ASTRID records and have not been re-verified against the paper's parameter table.")
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "bird22-astrid-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print("Wrote 1 ASTRID SFR density record from Bird+22")
