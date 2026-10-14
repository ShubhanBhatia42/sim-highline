import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1909.05864"
DOI = "10.1093/mnras/stz3241"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "plots" / "tully_fisher.pdf"
# marker colour -> galaxy, from the legend of the figure
GALAXIES = {(0.12, 0.47, 0.71): "g2.79e12", (1.0, 0.5, 0.05): "g8.26e11", (0.0, 0.75, 0.75): "g7.55e11", (0.55, 0.0, 0.55): "g6.96e11", (0.17, 0.63, 0.17): "g7.08e11"}
near = lambda c, t, tol=0.03: c is not None and all(abs(a - b) < tol for a, b in zip(c, t))

page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page, 200, 200)[0]
words = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
xl = [(cx, int(t[2:])) for t, cx, cy in words if re.fullmatch(r"10\d{2}", t) and cy > fr.y1]
assert len(xl) == 3, xl
fx, _ = vf.axis_fit_log2(page, fr, "x", xl)
fy, _ = vf.axis_fit(page, fr, "y")
legend = lambda r: (r.x0 + r.x1) / 2 < fr.x0 + 80 and (r.y0 + r.y1) / 2 < fr.y0 + 170
got = {"solid": {}, "faint": {}}
for d in page.get_drawings():
    r = d["rect"]
    if d["type"] != "fs" or d["fill"] is None or not (14 < r.width < 26 and 14 < r.height < 26) or not fr.contains(r) or legend(r):
        continue
    for col, name in GALAXIES.items():
        if near(d["fill"], col):
            got["solid" if (d.get("fill_opacity") or 1.0) > 0.9 else "faint"][name] = (fx((r.x0 + r.x1) / 2), fy((r.y0 + r.y1) / 2))
assert all(len(v) == 5 for v in got.values()), {k: sorted(v) for k, v in got.items()}
for name in GALAXIES.values():
    assert abs(got["solid"][name][0] - got["faint"][name][0]) < 0.01, name
SPOT = {"g6.96e11": (10.19, 2.146), "g8.26e11": (10.53, 2.333), "g2.79e12": (11.2, 2.569)}
for name, (xa, ya) in SPOT.items():
    assert abs(got["solid"][name][0] - xa) < 0.03 and abs(got["solid"][name][1] - ya) < 0.01, (name, got["solid"][name])
AX = {"xDefinition": "log10 total stellar mass", "xUnit": "log10(Msun)", "yUnit": "log10(km/s)"}
records = []
for tag, key, ydef, vdef, what in (
        ("v22rd", "solid", "log10 circular velocity at 2.2 disc scale lengths (2.2 R_d)", "circular velocity at 2.2 R_d", "solid coloured points (circular velocity at 2.2 R_d)"),
        ("hi-linewidth", "faint", "log10 edge-on rotation velocity derived from the HI line width", "rotation velocity from the edge-on HI line width (the paper does not say which width, W50 or W20)", "shaded coloured points (rotation velocity from the edge-on HI line width)")):
    names = sorted(got[key], key=lambda n: got[key][n][0])
    pts = [{"x": round(got[key][n][0], 3), "y": round(got[key][n][1], 4)} for n in names]
    assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:]))
    records.append(vf.record(
        rid=f"buck19.nihao-uhd.stfr-{tag}.z0", source="NIHAO zoom suite", run=f"NIHAO-UHD Milky Way-mass discs (per galaxy, {vdef.split(' (')[0]})", relation="stfr", z=0.0, axes={**AX, "yDefinition": ydef}, points=pts,
        population="5 NIHAO-UHD Milky Way-mass galaxies (zoom, not volume complete)", interval="unspecified", connect=False,
        definitions={"imf": "unspecified", "cosmology": {"H0": 67.1, "Om": 0.3175}, "massDefinition": "unspecified", "velocityDefinition": vdef, "population": "zoom-centrals"},
        citation=f"Buck et al. 2019, MNRAS, stz3241 (doi:{DOI}; arXiv:{ARXIV}), NIHAO-UHD Tully-Fisher relation", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="Tully-Fisher relation (left panel)", panel=what, sha=sha, member="plots/tully_fisher.pdf",
        calibration="prediction", uncertainty=0.01, retrieved="2026-10-14", calib="x: labelled decades 10^10 to 10^12 snapped to ticks (log); y: labelled ticks 2.0 to 2.6 snapped to ticks (linear)",
        warning=f"The {what} of the five NIHAO-UHD galaxies g6.96e11, g7.08e11, g7.55e11, g8.26e11 and g2.79e12 (in order of increasing stellar mass), read from the marker paths of Buck et al. 2019; no table exists. "
                "The stellar mass is the total stellar mass of the galaxy as listed in the paper's galaxy table; its aperture is not stated. The paper notes that the simulated velocities lie on the high side of the observed relation. "
                "Five hand-picked Milky Way-mass zoom galaxies, not a population. Observational data and fits are not extracted. The right panel (flat rotation velocity at the HI radius against SPARC) is not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "buck19-nihao-uhd-tf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} NIHAO-UHD stellar Tully-Fisher records from Buck+19 vector paths")
for r in records:
    print(r["id"], [(p["x"], p["y"]) for p in r["representation"]["points"]])
