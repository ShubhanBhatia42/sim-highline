import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1604.06803"
DOI = "10.1093/mnras/stw2586"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = next(SRC.rglob("M_HI_weak_convergence_BR06_evolution.pdf"))
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frame_from_long_lines(page, 100)
fx = lambda p: 7.0 + 5.0 * (p - fr.x0) / (fr.x1 - fr.x0)
fy = lambda p: 7.0 + 4.0 * (fr.y1 - p) / (fr.y1 - fr.y0)
xt, yt = vf._tick_positions(page, fr, "x"), vf._tick_positions(page, fr, "y")
for v in (8, 9, 10, 11):
    assert any(abs(fx(t) - v) < 0.02 for t in xt), ("x major tick", v)
for v in (8, 9, 10):
    assert any(abs(fy(t) - v) < 0.02 for t in yt), ("y major tick", v)
dot = [d for d in page.get_drawings() if d["color"] == (0.0, 0.0, 0.0) and d["dashes"] not in ("[] 0",) and len(d["items"]) <= 3 and d["rect"].width > 200]
assert dot, "dotted M_HI = M* guide line not found"
a, b = dot[0]["items"][0][1], dot[0]["items"][-1][2]
assert abs((fy(b.y) - fy(a.y)) / (fx(b.x) - fx(a.x)) - 1.0) < 0.02 and abs(fy(a.y) - fx(a.x)) < 0.05, "M_HI = M* guide line must have unit slope through the origin of the axes"
ZCOL = {(0.2, 0.13, 0.53): 0.0, (0.27, 0.67, 0.6): 1.0, (0.8, 0.4, 0.47): 4.0}
STYLE = {"[] 0": ("Ref-L100N1504", "Ref-L100N1504 (solid lines and circles)"), "[ 5.6693 2.83465 1.41733 2.83465 ] 0": ("Recal-L025N0752", "Recal-L025N0752 (dot-dashed lines and triangles)")}
close = lambda c, t: c is not None and all(abs(u - v) < 0.02 for u, v in zip(c, t))
records = []
for d in page.get_drawings():
    z = next((z for c, z in ZCOL.items() if close(d["color"], c)), None)
    if z is None or d["type"] != "s" or len(d["items"]) < 4 or d["dashes"] not in STYLE or (d.get("width") or 0) < 1.5:
        continue
    run, what = STYLE[d["dashes"]]
    pts = [(fx(p.x), fy(p.y)) for p in [d["items"][0][1]] + [i[2] for i in d["items"]]]
    assert all(p[0] < q[0] for p, q in zip(pts, pts[1:])) and all(6.5 < y < 11 for _, y in pts), (run, z)
    records.append(vf.record(
        rid=f"crain17.eagle.hi-fraction.{run.split('-')[0].lower()}.z{z:g}", source="EAGLE", run=f"{run} (centrals, median)", relation="hi-fraction", z=z,
        axes={"xDefinition": "log10 stellar mass (3D 30 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": "log10 median HI-to-stellar mass ratio MHI/M* of central galaxies (MHI within 70 pkpc, BR06 neutral-to-molecular split), converted from the plotted log10 MHI", "yUnit": "dex"},
        points=[(x, y - x) for x, y in pts], population="central galaxies", interval="unspecified",
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "massDefinition": "aperture-30pkpc", "population": "centrals", "gasPhase": "HI", "gasMethod": "BR06 (70 pkpc aperture)", "gasStatistic": "median"},
        citation=f"Crain et al. 2017, MNRAS 464, 4204 (arXiv:{ARXIV}), M_HI-M* relation of {what}, z={z:g}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="M_HI-M* relation at z=4, 1 and 0 (weak-convergence test)", panel=f"z={z:g}", sha=sha, member=PDF.name, calibration="prediction",
        calib="outlined text: the frame edges are 7 to 12 (x) and 7 to 11 (y) in the rendered figure; validated by the major ticks falling on integers and by the dotted M_HI = M* guide line having unit slope through the origin",
        warning=f"Median M_HI of central galaxies in bins of d log M* = 0.2 (0.3 for the 25 Mpc run) for {what} at z={z:g}, read from the vector paths of Crain et al. 2017 and converted exactly to MHI/M* by subtracting log M*; no table exists. "
                "The paper draws bins with M* < 100 gas particle masses only as a dotted line in other figures and omits them here; individual galaxies in sparse bins (symbols) are not extracted. "
                "The relation is resolution dependent (Ref-L100N1504 and Recal-L025N0752 disagree at z=0)."))
assert len(records) == 6, len(records)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "crain17-eagle-hi.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE HI-fraction records from Crain+17")
