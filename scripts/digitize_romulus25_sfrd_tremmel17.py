import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1607.02151"
DOI = "10.1093/mnras/stx1160"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "plots" / "cosmic_SFH_R25_corrected.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
xm, ym = {}, {}
for d in page.get_drawings():
    for it in d["items"]:
        if it[0] != "l":
            continue
        a, b = it[1], it[2]
        if abs(a.x - b.x) < 0.05 and abs(a.y - b.y) < 14 and (abs(max(a.y, b.y) - fr.y1) < 1.5 or abs(min(a.y, b.y) - fr.y1) < 1.5):
            xm[round(a.x, 1)] = max(xm.get(round(a.x, 1), 0), abs(a.y - b.y))
        if abs(a.y - b.y) < 0.05 and abs(a.x - b.x) < 14 and (abs(min(a.x, b.x) - fr.x0) < 1.5 or abs(max(a.x, b.x) - fr.x0) < 1.5):
            ym[round(a.y, 1)] = max(ym.get(round(a.y, 1), 0), abs(a.x - b.x))
xmaj = sorted(k for k, v in xm.items() if v > 0.8 * max(xm.values()))
ymaj = sorted(k for k, v in ym.items() if v > 0.8 * max(ym.values()))
assert len(xmaj) == 11 and len(ymaj) == 3, (xmaj, ymaj)
fl, _ = vf.axis_fit(page, fr, "x", labels=[(q, math.log10(1 + z)) for q, z in zip(xmaj, range(11))], snap=0.5)
fy, _ = vf.axis_fit(page, fr, "y", labels=[(q, v) for q, v in zip(ymaj, [-1.0, -2.0, -3.0])], snap=0.5)
cs = [c for c in vf.curves(page, fr, lambda q: q, fy, min_items=15) if c["color"] == (0.0, 0.0, 1.0) and abs(c["width"] - 1.9) < 0.05]
assert len(cs) == 1, len(cs)
c = cs[0]
raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(c["raw"], c["points"]))
pts = []
for x, y in raw:
    if -0.01 <= x <= 11 and -3 < y < -0.3 and (not pts or x > pts[-1][0]):
        pts.append((x, y))
near = lambda z: min(pts, key=lambda q: abs(q[0] - z))[1]
assert len(pts) >= 15 and pts[0][0] < 0.1 and -1.45 < near(0.0) < -1.2 and -0.95 < near(2.0) < -0.7 and -1.7 < near(6.0) < -1.2, (len(pts), near(0), near(2), near(6))
rec = vf.record(
    rid="tremmel17.romulus25.sfrd.total", source="Romulus25", run="Romulus25 (cosmic SFH, Tremmel+17)", relation="sfrd", z=2.0,
    axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 cosmic star formation rate density of the 25 Mpc box", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
    points=pts, population="all star formation in the Romulus25 volume", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
    definitions={"imf": "kroupa01", "cosmology": {"H0": 67.0, "Om": 0.3086}, "densityFrame": "comoving", "sfrIndicator": "instantaneous SFR", "population": "all galaxies in the volume"},
    citation=f"Tremmel et al. 2017, MNRAS 470, 1121 (arXiv:{ARXIV}), cosmic star formation history of Romulus25", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
    figure="Cosmic star formation history (corrected version of the figure)", panel="blue Romulus25 line", sha=sha, member="plots/cosmic_SFH_R25_corrected.pdf", calibration="prediction",
    calib="x: major ticks z=0..10 assigned in order (verified: positions follow log10(1+z)) and converted exactly to z; y: three major ticks 10^-1, 10^-2, 10^-3 assigned in order down the axis; labels are glyph paths so no text was read",
    warning="Total cosmic SFR density of the Romulus25 volume (25 Mpc per side), read from the vector path of Tremmel et al. 2017. The paper notes the overproduction of stars at low redshift comes from a handful of high-SFR systems in a small volume; the Behroozi+13, Duncan+14 and Kistler+13 comparison data are not extracted.", uncertainty=0.02)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "tremmel17-romulus25-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print(f"Wrote 1 Romulus25 SFR density record ({len(pts)} points) from Tremmel+17")
