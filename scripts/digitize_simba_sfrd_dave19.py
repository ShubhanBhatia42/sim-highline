import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1901.10203"
DOI = "10.1093/mnras/stz937"
H0, OM = 68.0, 0.3
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "madau_t.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
fx, xt = vf.axis_fit(page, fr, "x")
ws = sorted(((w[1] + w[3]) / 2, -float(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and 50 < (w[0] + w[2]) / 2 < 80 and fr.y0 - 2 <= (w[1] + w[3]) / 2 <= fr.y1 + 2)
ticks = vf._tick_positions(page, fr, "y")
fy, yt = vf.axis_fit(page, fr, "y", labels=[(min(ticks, key=lambda t: abs(t - cy)), v) for cy, v in ws])
OL = 1 - OM


def age(z):
    return 2.0 / (3.0 * (H0 / 977.792) * math.sqrt(OL)) * math.asinh(math.sqrt(OL / OM) * (1 + z) ** -1.5)


def z_of_age(t):
    lo, hi = -0.99, 50.0
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if age(mid) > t else (lo, mid)
    return (lo + hi) / 2


top = {int(w[4]): (w[0] + w[2]) / 2 for w in page.get_text("words") if w[4] in ("0", "1", "2", "4", "6") and (w[1] + w[3]) / 2 < fr.y0}
assert set(top) == {0, 1, 2, 4, 6}, top
for z, px in top.items():
    assert abs(fx(px) - age(z)) < 0.2, (z, fx(px), age(z))
cs = [c for c in vf.curves(page, fr, fx, fy, min_items=100) if c["color"] == (0.0, 0.5, 0.0)]
assert len(cs) == 1
raw = [(round(z_of_age(t), 3), y) for t, y in cs[0]["points"] if 0.5 < t < 13.9]
raw.sort()
pts = []
for x, y in raw:
    if not pts or x > pts[-1][0]:
        pts.append((x, y))
assert len(pts) > 300 and pts[0][0] < 0.1 and pts[-1][0] > 5.5, (len(pts), pts[0], pts[-1])
near = lambda z: min(pts, key=lambda q: abs(q[0] - z))[1]
assert -2.15 < pts[0][1] < -1.95 and -1.35 < near(2.0) < -1.1 and -1.5 < near(1.0) < -1.3, (pts[0], near(1.0), near(2.0))
rec = vf.record(
    rid="dave19.simba.sfrd.m100n1024", source="SIMBA", run="m100n1024 (SFR density, Dave+19)", relation="sfrd", z=2.0,
    axes={"xDefinition": "redshift (converted from cosmic time)", "xUnit": "redshift", "yDefinition": "log10 cosmic star formation rate density", "yUnit": "log10(Msun yr^-1 Mpc^-3)"},
    points=pts, population="all star formation in the box", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
    definitions={"imf": "unspecified", "cosmology": {"H0": H0, "Om": OM}, "densityFrame": "unspecified", "sfrIndicator": "instantaneous SFR", "population": "all galaxies"},
    citation=f"Dave et al. 2019, MNRAS 486, 2827 (arXiv:{ARXIV}), star formation rate density versus cosmic time", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
    figure="Star formation rate density evolution versus age of the Universe", panel="Simba curve (green)", sha=sha, member="madau_t.pdf", calibration="prediction",
    calib="x: cosmic time labels snapped to ticks; y: positive tick words negated (minus glyphs are separate) and paired with ticks",
    warning=f"SFR density of the 100 Mpc/h SIMBA run, read from the vector paths of Dave et al. 2019 (about {len(pts)} vertices of the plotted line). The x axis is cosmic time; each time is converted to redshift with the exact flat LCDM age relation (H0={H0:g}, Om={OM:g}, no radiation), validated against the figure's own redshift axis at z=0, 1, 2, 4 and 6 within 0.2 Gyr. The Madau & Dickinson points and fit overlaid in the figure are not extracted. IMF and the density frame (comoving) are not stated in the figure.",
    uncertainty=0.02)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dave19-simba-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print(f"Wrote 1 SIMBA SFR density record ({len(pts)} points) from Dave+19")
