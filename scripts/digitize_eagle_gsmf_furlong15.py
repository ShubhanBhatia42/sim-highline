import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1410.3485"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
ZS = [0.1, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
RUNS = {(0.2, 0.13, 0.53): ("ref", "Ref-L100N1504", 8.5), (0.07, 0.47, 0.2): ("recal", "Recal-L025N0752", 7.7)}
PDF = SRC / "smf9.pdf"
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)
assert len(fr) == 9
fx0, fy0, cal = vf.calibrate(page, fr[0], ysign=-1)
assert [v for _, v in cal["xTicks"]] == [7, 8, 9, 10, 11, 12] and [v for _, v in cal["yTicks"]] == [-1, -2, -3, -4, -5, -6]
words = page.get_text("words")
records = []
for i, (z, r) in enumerate(zip(ZS, fr)):
    fx, fy = vf.shifted(fx0, r.x0 - fr[0].x0), vf.shifted(fy0, r.y0 - fr[0].y0)
    if i % 3 == 0:
        vf.check_labels(page, r, "y", fy, vsign=-1)
    if i >= 6:
        vf.check_labels(page, r, "x", fx)
    label = f"z={z:.1f}"
    assert any(w[4] == label and r.x0 <= w[0] <= r.x1 and r.y0 <= w[1] <= r.y1 for w in words), (i, label)
    for c in vf.curves(page, r, fx, fy):
        if c["color"] not in RUNS or c["dashes"] != "[] 0" or c["width"] != 3.0:
            continue
        key, run, xstart = RUNS[c["color"]]
        pts = [(x, y) for x, y in c["points"]]
        assert abs(pts[0][0] - xstart) < 0.02 and all(-6.01 < y < -0.99 for _, y in pts) and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (z, run)
        records.append(vf.record(
            rid=f"furlong15.eagle-{key}.gsmf.z{z:g}", source="EAGLE", run=run, relation="gsmf", z=z,
            axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy number density per dex, dn/dlog10(M*)", "yUnit": "log10(cMpc^-3 dex^-1)"},
            points=pts, population="all galaxies",
            warning=f"Solid segment only of the curve in Furlong et al. 2015 Fig. 2 panel {i + 1} ({label}): bins with >=100 baryonic particles and >=10 galaxies; the dotted (<100 particles) and dashed (<10 galaxies) segments are omitted. "
                    "Vertices are the plotted 0.2 dex bin centres; the paper gives no table for these curves.",
            definitions={"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "densityFrame": "comoving", "population": "all"},
            citation=f"Furlong et al. 2015, MNRAS 450, 4486, Fig. 2 (arXiv source numbering) panel {i + 1}", doi="10.1093/mnras/stv852", url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Figure 2", panel=f"panel {i + 1} ({label})", sha=sha, member=f"smf9.pdf (solid {run} line, 3 pt stroke)",
            calib="x: page pt from labelled ticks 7-12 (34.93 pt/dex); y: ticks -1..-6 (34.93 pt/dex); panels share axes, offset by frame origin; labels asserted per panel",
            calibration="target" if z == 0.1 else "prediction"))
ref01 = next(r for r in records if r["id"] == "furlong15.eagle-ref.gsmf.z0.1")["representation"]["points"]
q = min(ref01, key=lambda q: abs(q["x"] - 10.0))
r = 10 ** (q["x"] - 11.14)
single = math.log10(math.log(10) * 0.84e-3 * r ** (-1.43 + 1) * math.exp(-r))
assert abs(q["y"] - single) < 0.05, (q, single)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "furlong15-eagle-gsmf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE GSMF records from Furlong+15 vector paths")
