import json
import re
import subprocess
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1605.09379"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PS = SRC / "mf.ps"
PDF = SRC / "pdf" / "mf_bb.pdf"
if not PDF.exists():
    bb = re.search(r"%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", PS.read_text(errors="ignore")[:4000])
    x0, y0, x1, y1 = (int(v) for v in bb.groups())
    PDF.parent.mkdir(exist_ok=True)
    subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", f"-sOutputFile={PDF}", f"-dDEVICEWIDTHPOINTS={x1 - x0}", f"-dDEVICEHEIGHTPOINTS={y1 - y0}",
                    "-c", f"<</Install {{{-x0} {-y0} translate}}>> setpagedevice", "-f", str(PS)], check=True)
ZS = [0.1, 0.4, 0.8, 1.6, 2.7, 4.0, 5.0, 6.0]
COLX, ROWY = [124.8, 350.6], [26.2, 214.0, 401.9, 589.8]
XTICK = [124.81, 184.22, 243.64, 303.05]
YTICK = [26.15, 73.12, 120.09, 167.06, 214.03]
XDEX, YDEX = 59.41, 23.485
GREY, PINK = (0.78, 0.78, 0.78), (0.99, 0.5, 0.87)


def near(c, t, tol=0.02):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


page = pymupdf.open(PDF)[0]
sha = vf.sha256(PDF, source=PS)
dr = page.get_drawings()
ticks_y = {round(a.y, 2) for d in dr if d["color"] == (0.0, 0.0, 0.0) for it in d["items"] if it[0] == "l" for a, b in [(it[1], it[2])]
           if abs(a.y - b.y) < 0.01 and 3 < abs(a.x - b.x) < 6 and abs(min(a.x, b.x) - COLX[0]) < 0.3}
ticks_x = {round(a.x, 2) for d in dr if d["color"] == (0.0, 0.0, 0.0) for it in d["items"] if it[0] == "l" for a, b in [(it[1], it[2])]
           if abs(a.x - b.x) < 0.01 and 3 < abs(a.y - b.y) < 6 and abs(max(a.y, b.y) - (ROWY[3] + 187.9)) < 0.3 and COLX[0] - 1 < a.x < COLX[1]}
assert all(any(abs(t - v) < 0.05 for v in ticks_y) for t in YTICK), ticks_y
assert all(any(abs(t - v) < 0.05 for v in ticks_x) for t in XTICK), ticks_x
assert abs((YTICK[-1] - YTICK[0]) / 4 / 2 - YDEX) < 0.01 and abs((XTICK[-1] - XTICK[0]) / 3 - XDEX) < 0.01


def panel(i):
    return i % 2, i // 2


def to_data(i, p):
    col, row = panel(i)
    return 9 + (p.x - COLX[col]) / XDEX, -(p.y - ROWY[row]) / YDEX


def cell_of(rect):
    cx, cy = (rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2
    col = 0 if cx < COLX[1] else 1
    row = max(r for r in range(4) if cy >= ROWY[r] - 1)
    return row * 2 + col


lines, bands, pinks = {}, {}, {}
for d in dr:
    its = d["items"]
    if not its or any(i[0] != "l" for i in its):
        continue
    pts = [its[0][1]] + [i[2] for i in its]
    r = d["rect"]
    if d["type"] == "s" and near(d["color"], GREY) and abs((d.get("width") or 0) - 5.67) < 0.05 and len(its) >= 2:
        lines[cell_of(r)] = pts
    elif d["type"] == "f" and near(d["fill"], GREY) and len(its) >= 5:
        bands[cell_of(r)] = pts
    elif d["type"] == "s" and near(d["color"], PINK) and d["dashes"].startswith("[ 5.6693") and len(its) >= 2:
        pinks[cell_of(r)] = pts
assert set(lines) == set(bands) == set(pinks) == set(range(8)), (set(lines), set(bands), set(pinks))
DEF = {"imf": "unspecified", "cosmology": {"H0": 70.4, "Om": 0.272}, "massDefinition": "unspecified", "densityFrame": "comoving", "population": "all"}
AX = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function, dN/dlog10(M) (axis label Mpc^-3 dex^-1)", "yUnit": "log10(Mpc^-3 dex^-1)"}
records = []
for i, z in enumerate(ZS):
    col, row = panel(i)
    line = [to_data(i, p) for p in lines[i]]
    poly = [to_data(i, p) for p in bands[i]]
    pts = []
    for x, y in line:
        ys = [py for px, py in poly if abs(px - x) < 0.01]
        assert len(ys) >= 2, (z, x)
        pts.append({"x": round(x, 3), "y": round(y, 4), "yLow": round(min(ys), 4), "yHigh": round(max(ys), 4)})
    assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and all(-8.5 < p["y"] < 0.2 for p in pts), z
    common = dict(source="Horizon-AGN", relation="gsmf", z=z, axes=AX, citation=f"Kaviraj et al. 2017, MNRAS (doi 10.1093/mnras/stx126), Fig. 7 (arXiv source numbering; mf.ps), z={z:g} panel", doi="10.1093/mnras/stx126",
                  url=f"https://arxiv.org/abs/{ARXIV}", figure="Figure 7", panel=f"z={z:g}", sha=sha, member="mf.ps (converted to PDF with the PostScript bounding box)",
                  calib=f"ticks: x 9-12 ({XDEX} pt/dex), y 0 to -8 ({YDEX} pt/dex); asserted against the drawn tick marks; panel offsets from the frame lines", calibration="prediction")
    records.append(vf.record(
        rid=f"kaviraj17.horizon-agn.gsmf.z{z:g}", run="Horizon-AGN", points=pts, population="all galaxies", interval="uncertainty",
        warning=f"Prediction (thick grey line) and Poisson-uncertainty band read from the vector paths of Kaviraj et al. 2017 Fig. 7 (z={z:g} panel); no table exists. "
                "The paper states the band width indicates Poisson uncertainties.", definitions=dict(DEF), **common))
    npts = [{"x": round(x, 3), "y": round(y, 4)} for x, y in (to_data(i, p) for p in pinks[i])]
    assert all(a["x"] < b["x"] for a, b in zip(npts, npts[1:])), z
    records.append(vf.record(
        rid=f"kaviraj17.horizon-noagn.gsmf.z{z:g}", run="Horizon-noAGN", points=npts, population="all galaxies",
        warning=f"Pink dashed Horizon-noAGN prediction (a twin simulation without black-hole feedback) of Kaviraj et al. 2017 Fig. 7 (z={z:g} panel); no table exists. "
                "A different physical model from Horizon-AGN, kept as its own run.", definitions=dict(DEF), **common))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "kaviraj17-horizonagn-gsmf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Horizon-AGN and Horizon-noAGN GSMF records from Kaviraj+17 vector paths")
