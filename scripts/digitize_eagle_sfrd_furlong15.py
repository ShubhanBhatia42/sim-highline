import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1410.3485"
DOI = "10.1093/mnras/stv852"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "madau.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
xt = vf._tick_positions(page, fr, "x")
xw = sorted(((w[0] + w[2]) / 2, vf.number(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and fr.x0 - 2 <= (w[0] + w[2]) / 2 <= fr.x1 + 2 and 0 < (w[1] + w[3]) / 2 - fr.y1 < 15)
assert [v for _, v in xw] == list(range(11)), xw
fl, xtick = vf.axis_fit(page, fr, "x", labels=[(p, math.log10(1 + v)) for p, v in xw])
fz = lambda p: 10 ** fl(p) - 1
yw = [((w[1] + w[3]) / 2, math.log10(float(w[4]))) for w in page.get_text("words") if w[4] in ("0.001", "0.01", "0.1", "1.0")]
assert len(yw) == 4
fy, ytick = vf.axis_fit(page, fr, "y", labels=yw)
cs = [c for c in vf.curves(page, fr, lambda p: p, fy, min_items=50) if c["color"] == (0.0, 0.0, 0.0) and not c["dashes"].startswith("[ ")]
assert len(cs) == 1
pts = [(fz(r.x), y) for r, (_, y) in zip(cs[0]["raw"], cs[0]["points"])]
pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
pk = max(pts, key=lambda p: p[1])
assert -0.05 <= pts[0][0] < 0.3 and pts[-1][0] > 9.5 and 1.5 < pk[0] < 2.8 and -1.35 < pk[1] < -1.1 and pts[-1][1] < -2.0, (pts[0], pts[-1], pk)
rec = vf.record(
    rid="furlong15.eagle.sfrd.refl100n1504", source="EAGLE", run="Ref-L100N1504", relation="sfrd", z=2.0,
    axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic star-formation rate density of the whole box", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
    points=pts, population="all star formation in the box", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
    definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "densityFrame": "comoving", "sfrIndicator": "instantaneous SFR of star-forming gas", "population": "all galaxies"},
    citation=f"Furlong et al. 2015, MNRAS 450, 4486 (arXiv:{ARXIV}), evolution of the cosmic star formation rate density", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
    figure="Evolution of the cosmic star formation rate density", panel="Ref-L100N1504 (solid black line)", sha=sha, member="madau.pdf", calibration="prediction",
    calib="x: axis is log10(1+z); numeric labels snapped to ticks in log10(1+z) and converted back to z; y: decade labels 0.001-1.0 snapped to ticks (log10)",
    warning="Total cosmic SFR density of EAGLE Ref-L100N1504 versus redshift (z 0 to 10), read from the vector paths of Furlong et al. 2015 (x axis is log(1+z), converted to z). The grey dashed '0.2 dex increase' line is an offset of the same curve and is not extracted.")
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "furlong15-eagle-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print("Wrote 1 EAGLE SFR density record from Furlong+15")
