import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1501.01311"
DOI = "10.1093/mnras/stv725"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "Figs" / "rhostar_calibrated.pdf"
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
assert len(xmaj) == 10 and len(ymaj) == 5, (xmaj, ymaj)
fl, _ = vf.axis_fit(page, fr, "x", labels=[(q, math.log10(1 + z)) for q, z in zip(xmaj, range(10))], snap=0.5)
fy, _ = vf.axis_fit(page, fr, "y", labels=[(q, v) for q, v in zip(ymaj, [8.5, 8.0, 7.5, 7.0, 6.5])], snap=0.5)
RUNS = {(0.2, 0.13, 0.53): ("Ref", "Ref-L050N0752 (calibration model, Crain+15)"), (0.53, 0.8, 0.93): ("FBZ", "FBZ-L050N0752 (calibration model, Crain+15)"), (0.27, 0.67, 0.6): ("FBsigma", "FBsigma-L050N0752 (calibration model, Crain+15)"), (0.8, 0.4, 0.47): ("FBconst", "FBconst-L050N0752 (calibration model, Crain+15)")}
SPOT = {"Ref": ((0.0, 8.2, 8.45), (2.0, 7.5, 7.95), (4.0, 6.7, 7.25)), "FBconst": ((0.0, 8.25, 8.5), (4.0, 7.2, 7.8))}
records = []
cs = [c for c in vf.curves(page, fr, lambda q: q, fy, min_items=20) if c["color"] in RUNS and abs(c["width"] - 3.69) < 0.05]
assert len(cs) == 4, len(cs)
for c in cs:
    slug, run = RUNS[c["color"]]
    raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(c["raw"], c["points"]))
    pts = []
    for x, y in raw:
        if -0.01 <= x <= 9.2 and 6.4 < y < 8.6 and (not pts or x > pts[-1][0]):
            pts.append((x, y))
    near = lambda z: min(pts, key=lambda q: abs(q[0] - z))[1]
    assert len(pts) >= 20 and pts[0][0] < 0.2, (slug, len(pts), pts[0])
    for zz, lo, hi in SPOT.get(slug, ()):
        assert lo < near(zz) < hi, (slug, zz, near(zz))
    records.append(vf.record(
        rid=f"crain15.eagle.{slug.lower()}-l050n0752.smd", source="EAGLE", run=run, relation="smd", z=2.0,
        axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 comoving stellar mass density of the simulated volume", "yUnit": "log10(Msun cMpc^-3)"},
        points=pts, population="all stars in the 50 cMpc simulation volume", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "densityFrame": "comoving", "population": "all galaxies in the volume"},
        citation=f"Crain et al. 2015, MNRAS 450, 1937 (arXiv:{ARXIV}), evolution of the comoving stellar mass density of the calibrated models", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Evolution of the comoving stellar mass density of the calibrated EAGLE models (L050N0752)", panel=f"{slug} curve", sha=sha, member="Figs/rhostar_calibrated.pdf", calibration="prediction",
        calib="x: major ticks z=0..9 assigned in order (verified: positions follow log10(1+z)) and converted exactly to z; y: five major ticks 8.5 to 6.5 assigned in order down the axis; labels are glyph paths so no text was read",
        warning=f"Comoving stellar mass density of the {slug} calibration model of Crain et al. 2015 (50 cMpc, 752^3 particles), read from the vector path; the paper notes only the Ref model is broadly consistent with observations at z below about 2 and that FBconst forms too much stellar mass early. These are calibration variants, not the production runs of Schaye+15; the survey data points are not extracted.", uncertainty=0.02))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "crain15-eagle-smd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE stellar mass density records from Crain+15")
