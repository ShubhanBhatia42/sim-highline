import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2306.04024"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "Images" / "SMF_2_Panel.pdf"
RUNS = {(0.07, 0.47, 0.2): ("l1_m9", "L1_m9", 1000.0), (0.2, 0.13, 0.53): ("l2p8_m9", "L2p8_m9", 2800.0),
        (0.87, 0.8, 0.47): ("l1_m10", "L1_m10", 1000.0), (0.8, 0.4, 0.47): ("l1_m8", "L1_m8", 1000.0)}


def near(c, t):
    return c is not None and all(abs(a - b) < 0.01 for a, b in zip(c, t))


page = vf.page_of(PDF)
sha = vf.sha256(PDF)
frame = vf.frames(page)[0]
words = page.get_text("words")
ylab = [((w[1] + w[3]) / 2, -float(m.group(1))) for w in words for m in [re.fullmatch(r"10−(\d)", w[4])] if m and w[0] < frame.x0]
xw = sorted(((w[0] + w[2]) / 2, w[4]) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[1] > frame.y1 and w[0] < frame.x1 and w[0] > frame.x0 - 20)
assert [t for _, t in xw] == ["108", "109", "1010", "1011", "1012", "1013"], xw
xlab = [(p, float(t[2:])) for p, t in xw]
assert len({round(b[0] - a[0], 0) for a, b in zip(xlab, xlab[1:])}) <= 2
fx, xt = vf.axis_fit(page, frame, "x", labels=xlab)
fy, yt = vf.axis_fit(page, frame, "y", labels=ylab)
assert [v for _, v in xt] == [8, 9, 10, 11, 12, 13] and [v for _, v in yt] == [-2, -3, -4, -5, -6, -7, -8], (xt, yt)
xlo, xhi = fx(frame.x0), fx(frame.x1)
ylo, yhi = fy(frame.y1), fy(frame.y0)
records = []
seen = set()
for cu in vf.curves(page, frame, fx, fy, min_items=8):
    c = next((RUNS[k] for k in RUNS if near(cu["color"], k)), None)
    if c is None or cu["dashes"] != "[] 0" or cu["width"] != 1.5:
        continue
    key, run, box = c
    pts = [(x, y) for x, y in cu["points"] if xlo <= x <= xhi and ylo <= y <= yhi]
    assert key not in seen and len(pts) >= 10 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), key
    seen.add(key)
    records.append(vf.record(
        rid=f"schaye23.flamingo-{key}.gsmf.z0", source="FLAMINGO", run=run, relation="gsmf", z=0.0,
        axes={"xDefinition": "log10 stellar mass (3D 50 pkpc aperture, with 0.3 dex lognormal mock scatter)", "xUnit": "log10(Msun)",
              "yDefinition": "log10 galaxy stellar mass function, dn/dlog10(M*)", "yUnit": "log10(Mpc^-3 dex^-1)"},
        points=pts, population="all galaxies",
        warning="Solid segment only of the curve in Schaye et al. 2023 (MNRAS 526, 4978) Fig. 8 left-top panel, above the resolution-dependent lower mass limit for calibration; "
                f"the dotted low-mass part is omitted. {run}: box {box:g} cMpc, fiducial galaxy formation model and cosmology. The curves include the 0.3 dex random lognormal stellar-mass scatter "
                "expected in observed data, so they are not raw catalogue values. The paper gives no table.",
        definitions={"massDefinition": "aperture-50pkpc", "imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "densityFrame": "comoving", "population": "all"},
        citation="Schaye et al. 2023, MNRAS 526, 4978, Fig. 8 (arXiv source numbering) left-top panel", doi="10.1093/mnras/stad2419", url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Figure 8", panel="left-top (resolutions and box sizes, z=0)", sha=sha, member=f"Images/{PDF.name} (solid {run} line, 1.5 pt stroke)",
        calib="x: labelled decades 10^8-10^13 (uniform spacing asserted); y: labelled decades 10^-2..10^-8; both snapped to tick marks", calibration="target"))
assert seen == {v[0] for v in RUNS.values()}, seen
LIMIT = {"l1_m8": 8.67, "l1_m9": 9.92, "l2p8_m9": 9.92, "l1_m10": 11.17}
for r in records:
    assert abs(r["domain"]["xMin"] - LIMIT[r["id"].split(".")[1].split("-")[1]]) < 0.05, (r["id"], r["domain"])
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "schaye23-flamingo-gsmf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FLAMINGO GSMF records from Schaye+23 vector paths")
