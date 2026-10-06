import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1605.09379"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PS = SRC / "cosmicsfh.ps"
PDF = SRC / "pdf" / "cosmicsfh_bb.pdf"
if not PDF.exists():
    bb = re.search(r"%%BoundingBox:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)", PS.read_text(errors="ignore")[:4000])
    x0, y0, x1, y1 = (int(v) for v in bb.groups())
    PDF.parent.mkdir(exist_ok=True)
    subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", f"-sOutputFile={PDF}", f"-dDEVICEWIDTHPOINTS={x1 - x0}", f"-dDEVICEHEIGHTPOINTS={y1 - y0}",
                    "-c", f"<</Install {{{-x0} {-y0} translate}}>> setpagedevice", "-f", str(PS)], check=True)
page = vf.page_of(PDF)
sha = vf.sha256(PS)
fr = vf.frame_from_long_lines(page, 100)
xm, ym = {}, {}
for d in page.get_drawings():
    for it in d["items"]:
        if it[0] != "l":
            continue
        a, b = it[1], it[2]
        if abs(a.x - b.x) < 0.05 and abs(a.y - b.y) < 12 and abs(max(a.y, b.y) - fr.y1) < 1.5:
            xm[round(a.x, 1)] = max(xm.get(round(a.x, 1), 0), abs(a.y - b.y))
        if abs(a.y - b.y) < 0.05 and abs(a.x - b.x) < 12 and abs(min(a.x, b.x) - fr.x0) < 1.5:
            ym[round(a.y, 1)] = max(ym.get(round(a.y, 1), 0), abs(a.x - b.x))
xmaj = sorted(k for k, v in xm.items() if v > 1.5 * min(xm.values()) and v > 4)
ymaj = sorted(k for k, v in ym.items() if v > 1.5 * min(v2 for v2 in ym.values() if v2 > 0.5) and v > 5)
assert len(xmaj) == 5 and len(ymaj) == 4, (xmaj, ymaj)
XV, YV = [0.0, 0.2, 0.4, 0.6, 0.8], [-1.0, -1.5, -2.0, -2.5]
fx, _ = vf.axis_fit(page, fr, "x", labels=list(zip(xmaj, XV)))
fy, _ = vf.axis_fit(page, fr, "y", labels=list(zip(ymaj, YV)))
red = [d for d in page.get_drawings() if d["type"] == "s" and d["color"] and d["color"][0] > 0.9 and d["color"][1] < 0.3 and d["color"][2] < 0.3 and (d.get("width") or 0) > 3]
assert len(red) >= 30, len(red)
pts = []
for d in red:
    for it in d["items"]:
        for q in (it[1], it[2]) if it[0] == "l" else ():
            pts.append((10 ** fx(q.x) - 1, fy(q.y)))
pts = sorted(set((round(x, 3), round(y, 4)) for x, y in pts))
out = []
for x, y in pts:
    if -0.01 <= x <= 6.0 and -2.5 < y < -0.6 and (not out or x > out[-1][0]):
        out.append((x, y))
near = lambda z: min(out, key=lambda q: abs(q[0] - z))[1]
assert len(out) > 20 and out[0][0] < 0.1 and out[-1][0] > 5.5 and -1.95 < out[0][1] < -1.75 and -1.0 < near(3.0) < -0.85 and -1.55 < out[-1][1] < -1.35, (len(out), out[0], out[-1], near(3.0))
rec = vf.record(
    rid="kaviraj17.horizon-agn.sfrd", source="Horizon-AGN", run="Horizon-AGN (SFR density, Kaviraj+17)", relation="sfrd", z=3.0,
    axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 cosmic star formation rate density", "yUnit": "log10(Msun yr^-1 Mpc^-3)"},
    points=out, population="all star formation in the box", interval="unspecified", z_range=(out[0][0], out[-1][0]),
    definitions={"imf": "unspecified", "cosmology": "unspecified", "densityFrame": "unspecified", "sfrIndicator": "unspecified", "population": "all galaxies"},
    citation=f"Kaviraj et al. 2017, MNRAS (doi 10.1093/mnras/stx126), cosmic star formation history", doi="10.1093/mnras/stx126", url=f"https://arxiv.org/abs/{ARXIV}",
    figure="Predicted cosmic star formation history compared with Hopkins & Beacom 2006", panel="red curve", sha=sha, member="cosmicsfh.ps (converted to PDF with the PostScript bounding box)", calibration="prediction",
    calib="x and y: major ticks (longer strokes) assigned the labels read from the rendered figure (the labels are glyph paths): x 0.0-0.8 in log10(1+z), y -1.0 to -2.5; x converted exactly to z",
    warning="Cosmic star formation history of Horizon-AGN (z 0 to 6), read from the PostScript vector paths of Kaviraj et al. 2017. The grey band is the observational range of Hopkins 2006 and is not extracted. IMF, cosmology and the density frame are not stated in the figure.",
    uncertainty=0.02)
outp = Path(__file__).resolve().parent.parent / "data" / "curves" / "kaviraj17-horizonagn-sfrd.json"
outp.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print(f"Wrote 1 Horizon-AGN SFR density record ({len(out)} points) from Kaviraj+17")
