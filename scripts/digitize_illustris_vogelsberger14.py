import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1405.2921"
DOI = "10.1093/mnras/stu1536"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
CITE = f"Vogelsberger et al. 2014, MNRAS 444, 1518 (arXiv:{ARXIV})"
URL = f"https://arxiv.org/abs/{ARXIV}"
DEF = {"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.2726}, "densityFrame": "comoving", "population": "all"}
records = []


def exp(t):
    return int(t[2:].replace("−", "-"))


def logfit(page, fr, axis, words):
    ticks = vf._tick_positions(page, fr, axis)
    lab = [(min(ticks, key=lambda q: abs(q - pos)), v) for pos, v in words]
    return vf.axis_fit(page, fr, axis, labels=lab)[0]


def words_of(page):
    return [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]


# ---- SFRD ----
pdf = SRC / "figures" / "sfrd.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frame_from_long_lines(page, 100)
W = words_of(page)
zl = [(cx, math.log10(1 + float(t))) for t, cx, cy in W if t in ("0", "1", "2", "3", "4", "5", "6", "8", "10") and cy > fr.y1]
yl = [(cy, float(exp(t))) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < fr.x0]
assert len(zl) == 9 and len(yl) == 5
fl = logfit(page, fr, "x", zl)
fy = logfit(page, fr, "y", yl)
cs = [c for c in vf.curves(page, fr, lambda p: p, fy, min_items=90) if c["color"] == (0.0, 0.0, 0.0) and abs(c["width"] - 7.5) < 0.01]
assert len(cs) == 1
raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(cs[0]["raw"], cs[0]["points"]))
pts = []
for x, y in raw:
    if -0.01 <= x <= 12 and -6 < y < 1 and (not pts or x > pts[-1][0]):
        pts.append((x, y))
near = lambda z: min(pts, key=lambda q: abs(q[0] - z))[1]
assert len(pts) > 80 and pts[0][0] < 0.1 and -1.85 < pts[0][1] < -1.5 and -1.05 < near(2.0) < -0.85 and -2.3 < near(6.0) < -1.7, (len(pts), pts[0], near(2), near(6))
records.append(vf.record(
    rid="vogelsberger14.illustris.sfrd.total", source="Illustris", run="Illustris-1 (SFR density, Vogelsberger+14)", relation="sfrd", z=2.0,
    axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 cosmic star formation rate density (total)", "yUnit": "log10(Msun yr^-1 Mpc^-3)"},
    points=pts, population="all star formation in the box", interval="unspecified", z_range=(pts[0][0], pts[-1][0]), definitions=dict(DEF, sfrIndicator="instantaneous SFR"),
    citation=CITE + ", cosmic star formation rate density", doi=DOI, url=URL, figure="Cosmic star formation rate density", panel="total (thick black line)", sha=sha, member="figures/sfrd.pdf", calibration="prediction",
    calib="x: labels 0-10 snapped to ticks in log10(1+z) and converted exactly to z; y: decade labels snapped to ticks (log10)",
    warning="Total cosmic SFR density of Illustris-1 (z 0 to about 11), read from the vector path of Vogelsberger et al. 2014; the stellar-mass-bin contributions and the observational overlays are not extracted.", uncertainty=0.02))

# ---- Tully-Fisher ----
for name, rel, xdef, ydef, xunit, yunit, swap in (
        ("TF_baryon", "btfr", "log10 circular velocity V_circ of the galaxy (definition as in the paper)", "log10 baryonic mass M_baryon", "log10(km/s)", "log10(Msun)", False),
        ("TF_stellar", "stfr", "log10 stellar mass", "log10 circular velocity V_circ of the galaxy (definition as in the paper)", "log10(Msun)", "log10(km/s)", True)):
    pdf = SRC / "figures" / f"{name}.pdf"
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frame_from_long_lines(page, 100)
    W = words_of(page)
    vw = [t for t, cx, cy in W if t in ("140", "180", "230", "300", "400")]
    assert len(vw) == 5
    if not swap:
        fx = logfit(page, fr, "x", [(cx, math.log10(float(t))) for t, cx, cy in W if t in ("140", "180", "230", "300", "400") and cy > fr.y1])
        fy = logfit(page, fr, "y", [(cy, float(exp(t))) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < fr.x0])
    else:
        fx = logfit(page, fr, "x", [(cx, float(exp(t))) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cy > fr.y1])
        fy = logfit(page, fr, "y", [(cy, math.log10(float(t))) for t, cx, cy in W if t in ("140", "180", "230", "300", "400") and cx < fr.x0])
    mk = []
    for d in page.get_drawings():
        if d["type"] == "fs" and d["fill"] is not None and tuple(round(v, 2) for v in d["fill"]) == (0.0, 0.0, 1.0) and d["rect"].width > 8:
            r = d["rect"]
            mk.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    if len(mk) == 43:
        mk.remove(max(mk, key=lambda q: q[1]))
    assert len(mk) == 42, len(mk)
    pts = sorted((round(fx(x), 4), round(fy(y), 4)) for x, y in mk)
    if rel == "btfr":
        assert all(2.1 < x < 2.65 and 10.5 < y < 11.7 for x, y in pts), pts[:3]
    else:
        assert all(10.2 < x < 11.8 and 2.1 < y < 2.65 for x, y in pts), pts[:3]
    records.append(vf.record(
        rid=f"vogelsberger14.illustris.{rel}.disks.z0", source="Illustris", run="Illustris-1 (42 disc galaxies, Vogelsberger+14)", relation=rel, z=0.0,
        axes={"xDefinition": xdef, "xUnit": xunit, "yDefinition": ydef, "yUnit": yunit},
        points=pts, population="42 well-resolved simulated disc galaxies (B-1 to B-42), a small hand-picked sample", interval="unspecified", connect=False, scatter=True, definitions=dict(DEF, population="disc galaxies (42, selected)", velocityDefinition="circular velocity V_circ as defined in the paper", massDefinition="unspecified"),
        citation=CITE + f", {'baryonic' if rel == 'btfr' else 'stellar'} Tully-Fisher relation", doi=DOI, url=URL, figure="Tully-Fisher relations", panel="blue circles, sample spirals", sha=sha, member=f"figures/{name}.pdf", calibration="prediction",
        calib="log axes: labelled values (velocities 140-400, decades of mass) snapped to ticks; marker centres read from the vector paths",
        warning="Per-galaxy points for the 42 disc galaxies of Illustris-1 shown by the paper (a small sample of well-resolved discs; the paper notes the box holds thousands of Milky Way analogues). The grey Aumer+13 points, the observational trend bands and the legend marker are not extracted.",
        strict=False, uncertainty=0.02))
for r in records[1:]:
    r["rankable"] = False
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "vogelsberger14-illustris.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Illustris records from Vogelsberger+14")
