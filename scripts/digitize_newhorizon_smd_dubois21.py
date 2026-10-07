import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2009.10578"
DOI = "10.1051/0004-6361/202039429"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "stellardensity_cosmo-eps-converted-to.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
xt = vf._tick_positions(page, fr, "x")
xl = [((w[0] + w[2]) / 2, float(w[4])) for w in page.get_text("words") if w[4] in ("0.0", "0.2", "0.4", "0.6", "0.8", "1.0") and (w[1] + w[3]) / 2 > fr.y1]
fl, _ = vf.axis_fit(page, fr, "x", labels=[(min(xt, key=lambda t: abs(t - cx)), v) for cx, v in xl])
yt = vf._tick_positions(page, fr, "y")
yl = [((w[1] + w[3]) / 2, float(w[4][2:])) for w in page.get_text("words") if w[4] in ("105", "106", "107", "108", "109") and (w[0] + w[2]) / 2 < fr.x0]
assert len(yl) == 5
fy, _ = vf.axis_fit(page, fr, "y", labels=[(min(yt, key=lambda t: abs(t - cy)), v) for cy, v in yl])
cs = [c for c in vf.curves(page, fr, lambda p: p, fy, min_items=500) if c["color"] == (0.0, 0.0, 0.0)]
assert len(cs) == 1, len(cs)
c = cs[0]
raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(c["raw"], c["points"]))
pts = []
for x, y in raw:
    if -0.01 <= x <= 10 and 4.9 < y < 9.2 and (not pts or x > pts[-1][0]):
        pts.append((x, y))
near = lambda z: min(pts, key=lambda q: abs(q[0] - z))[1]
assert len(pts) > 100 and 0.1 < pts[0][0] < 0.5 and 8.5 < near(0.5) < 9.1 and 7.9 < near(2.0) < 8.6 and 6.5 < near(4.0) < 7.7, (len(pts), pts[0], near(0.5), near(2), near(4))
rec = vf.record(
    rid="dubois21.newhorizon.smd.total", source="NewHorizon", run="NewHorizon (stellar mass density, Dubois+21)", relation="smd", z=2.0,
    axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 stellar mass density of the zoom volume", "yUnit": "log10(Msun Mpc^-3)"},
    points=pts, population="all stars in the NewHorizon zoom volume", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
    definitions={"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.272}, "densityFrame": "unspecified", "population": "all galaxies in the zoom volume"},
    citation=f"Dubois et al. 2021, A&A 651, A109 (arXiv:{ARXIV}), cosmic stellar mass density", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
    figure="Cosmic SFR density and stellar density as a function of redshift", panel="bottom panel, NewHorizon true stellar density (black line)", sha=sha, member="stellardensity_cosmo-eps-converted-to.pdf", calibration="prediction",
    calib="x: labels 0.0-1.0 of log10(1+z) snapped to ticks, converted exactly to z; y: decade labels 10^5-10^9 snapped to ticks (log10)",
    warning="Total stellar mass density of the NewHorizon zoom (a small, non-volume-complete region) from z about 0.4 to 9, read from the vector path of Dubois et al. 2021; the reconstructed and per-mass-bin curves, the Behroozi+13 comparison and the observational points are not extracted. The paper does not state whether the density is per comoving or physical volume.",
    uncertainty=0.02)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dubois21-newhorizon-smd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print(f"Wrote 1 NewHorizon stellar mass density record ({len(pts)} points) from Dubois+21")
