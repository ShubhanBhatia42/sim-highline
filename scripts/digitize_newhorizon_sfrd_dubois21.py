import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2009.10578"
DOI = "10.1051/0004-6361/202039429"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
top = SRC / "sfr_cosmo-eps-converted-to.pdf"
bot = SRC / "stellardensity_cosmo-eps-converted-to.pdf"
page = vf.page_of(top)
pb = vf.page_of(bot)
sha = vf.sha256(top)
fr = vf.frame_from_long_lines(page, 100)
assert fr == vf.frame_from_long_lines(pb, 100)
xt = vf._tick_positions(pb, fr, "x")
xl = [((w[0] + w[2]) / 2, float(w[4])) for w in pb.get_text("words") if w[4] in ("0.0", "0.2", "0.4", "0.6", "0.8", "1.0") and (w[1] + w[3]) / 2 > fr.y1]
fl, _ = vf.axis_fit(pb, fr, "x", labels=[(min(xt, key=lambda t: abs(t - cx)), v) for cx, v in xl])
yt = vf._tick_positions(page, fr, "y")
yl = [((w[1] + w[3]) / 2, math.log10(float(w[4]))) for w in page.get_text("words") if w[4] in ("0.001", "0.010", "0.100", "1.000")]
assert len(yl) == 4
fy, _ = vf.axis_fit(page, fr, "y", labels=[(min(yt, key=lambda t: abs(t - cy)), v) for cy, v in yl])
cs = [c for c in vf.curves(page, fr, lambda p: p, fy, min_items=100) if c["color"] == (0.0, 0.0, 0.0)]
cs = [k for k in cs if len(k["points"]) > 500]
assert len(cs) >= 1, len(cs)
c = max(cs, key=lambda k: len(k["points"]))
raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(c["raw"], c["points"]))
pts = []
for x, y in raw:
    if -0.01 <= x <= 10 and -3.2 < y < 0.2 and (not pts or x > pts[-1][0]):
        pts.append((x, y))
near = lambda z: min(pts, key=lambda q: abs(q[0] - z))[1]
assert len(pts) > 100 and 0.2 < pts[0][0] < 0.6 and -1.3 < near(1.0) < -0.9 and -1.0 < near(2.0) < -0.6 and pts[-1][0] > 4.5, (len(pts), pts[0], pts[-1], near(1), near(2))
rec = vf.record(
    rid="dubois21.newhorizon.sfrd.total", source="NewHorizon", run="NewHorizon (SFR density, Dubois+21)", relation="sfrd", z=2.0,
    axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 cosmic star formation rate density of the zoom volume", "yUnit": "log10(Msun yr^-1 Mpc^-3)"},
    points=pts, population="all star formation in the NewHorizon zoom volume", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
    definitions={"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.272}, "densityFrame": "unspecified", "sfrIndicator": "instantaneous SFR", "population": "all galaxies in the zoom volume"},
    citation=f"Dubois et al. 2021, A&A 651, A109 (arXiv:{ARXIV}), cosmic SFR density", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
    figure="Cosmic SFR density and stellar density as a function of redshift", panel="top panel, NewHorizon total (black line)", sha=sha, member="sfr_cosmo-eps-converted-to.pdf (x axis from stellardensity_cosmo-eps-converted-to.pdf, same frame)", calibration="prediction",
    calib="x: labels 0.0-1.0 of log10(1+z) from the lower panel of the same frame, snapped to ticks, converted exactly to z; y: decade labels 0.001-1.0 snapped to ticks (log10)",
    warning="Total cosmic SFR density of the NewHorizon zoom (a small, non-volume-complete region) from z about 0.4 to 9, read from the vector paths of Dubois et al. 2021; the per-mass-bin curves, the cosmic-variance bar and the observational overlays are not extracted. The paper compares with Chabrier-IMF observations.",
    uncertainty=0.02)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dubois21-newhorizon-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print(f"Wrote 1 NewHorizon SFR density record ({len(pts)} points) from Dubois+21")
