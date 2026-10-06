import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

import pymupdf

ARXIV = "1707.03406"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else None
PANELS = {1: 0.0, 2: 0.5, 3: 1.0, 4: 2.0, 5: 3.0, 6: 4.0}
CURVES = {
    (0.84, 0.15, 0.16): ("illustris", "Illustris", "Illustris-1", 70.4, 0.2726, "WMAP-9", "fig. legend: Illustris"),
    (0.12, 0.47, 0.71): ("tng100", "IllustrisTNG", "TNG100-1", 67.74, 0.3089, "Planck 2015", "fig. legend: TNG100"),
    (1.0, 0.5, 0.05): ("rtng300", "IllustrisTNG", "rTNG300-1 (resolution-corrected)", 67.74, 0.3089, "Planck 2015", "fig. legend: rTNG300"),
}
X0, XDEX, Y0, YDEX = 94.0, 143.0, 24.0, 100.2
FRAME = (94.0, 24.0, 766.0, 525.0)


def fetch_figures():
    if SRC:
        return SRC
    out = Path("/tmp/pillepich18_src")
    if not (out / "fig_gsmf_1.pdf").exists():
        req = urllib.request.Request(f"https://arxiv.org/e-print/{ARXIV}", headers={"User-Agent": "Mozilla/5.0"})
        tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen(req).read())).extractall(out)
    return out


def to_data(p):
    return 8 + (p.x - X0) / XDEX, -1 - (p.y - Y0) / YDEX


def check_calibration(page, n):
    ticks = {(round(l[1].x, 1), round(l[1].y, 1), round(l[2].x, 1), round(l[2].y, 1)) for d in page.get_drawings()
             if d["color"] and tuple(round(v, 2) for v in d["color"]) == (0.15, 0.15, 0.15) for l in d["items"] if l[0] == "l"}
    for k in range(5):
        x = X0 + XDEX * k
        assert any(abs(t[0] - x) < 0.2 and t[0] == t[2] and abs(abs(t[3] - t[1]) - 26.9) < 0.2 for t in ticks), (n, "x major tick", k)
        y = Y0 + YDEX * (k + 1) * 1.0 if k < 4 else Y0 + 501.0
        assert any(abs(t[1] - y) < 0.3 and t[1] == t[3] and abs(abs(t[2] - t[0]) - 26.9) < 0.2 for t in ticks), (n, "y major tick", k)
    labels = {w[4] for w in page.get_text("words")}
    assert {"108", "109", "1010", "1011", "1012", "10-6", "10-1"} <= labels, (n, "axis labels")
    rects = [(round(d["rect"].x0, 1), round(d["rect"].y0, 1), round(d["rect"].x1, 1), round(d["rect"].y1, 1)) for d in page.get_drawings()]
    assert FRAME in rects, (n, "frame")


def curves(page):
    out = {}
    for d in page.get_drawings():
        if d.get("width") != 8.0 or d["type"] != "s" or d.get("stroke_opacity") != 0.800000011920929 or len(d["items"]) < 5:
            continue
        col = tuple(round(v, 2) for v in d["color"])
        if col in CURVES and col not in out:
            pts = [d["items"][0][1]] + [it[2] for it in d["items"] if it[0] == "l"]
            out[col] = [to_data(p) for p in pts]
    assert set(out) == set(CURVES), set(CURVES) - set(out)
    return out


figdir = fetch_figures()
records = []
for n, z in PANELS.items():
    pdf = figdir / f"fig_gsmf_{n}.pdf"
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    page = pymupdf.open(pdf)[0]
    check_calibration(page, n)
    text = " ".join(w[4] for w in page.get_text("words"))
    label = "z = 0" if z == 0 else f"z ~ {z:g}"
    assert re.search(re.escape(label) + r"(?! ?\d)(?! \(rTNG300\))", text.replace("z ~ 0 (rTNG300)", "")), (n, label)
    for col, pts in curves(page).items():
        key, source, run, h0, om, cosmo, member = CURVES[col]
        pts = [{"x": round(x, 3), "y": round(y, 3)} for x, y in pts]
        assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])), (n, run)
        assert all(8.0 < p["x"] < 12.7 and -6 < p["y"] < -1 for p in pts), (n, run)
        aperture = "aperture-30pkpc" if z == 0 else "aperture-2rhalf-stars"
        records.append({
            "id": f"pillepich18.{key}.gsmf.z{z:g}", "source": source, "run": run, "kind": "simulation", "relation": "gsmf",
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
            "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function", "yUnit": "log10(Mpc^-3 dex^-1)"},
            "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "unspecified", "connect": True, "points": pts},
            "scatter": None,
            "selection": {"population": "all galaxies", "warning": "Curve vertices read from the vector paths of Pillepich et al. 2018 (MNRAS 475, 648), Fig. 14 (arXiv source numbering) panel "
                          f"{n}; no table exists. Vertices are the plotted bin centres. The paper's z labels are approximate (z~) for z>0. "
                          + ("The z=0 panel uses a 30 pkpc 3D aperture for all runs. " if z == 0 else "Stellar mass within twice the stellar half-mass radius. ")
                          + ("rTNG300 is TNG300 with the paper's resolution correction to stellar masses; not an unmodified catalogue." if "rTNG300" in run else "")},
            "definitions": {"massDefinition": aperture, "imf": "chabrier03", "cosmology": {"H0": h0, "Om": om}, "densityFrame": "comoving", "population": "all"},
            "provenance": {"tier": "digitized-figure", "citation": f"Pillepich et al. 2018, MNRAS 475, 648, Fig. 14 panel {n}", "doi": "10.1093/mnras/stx3112",
                           "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-05", "figure": "Figure 14", "panel": f"panel {n}", "checksumSha256": sha,
                           "sourceMember": f"fig_gsmf_{n}.pdf ({member}, 8 pt stroke, alpha 0.8)",
                           "extractionMethod": "vector path vertices from the figure PDF (PyMuPDF get_drawings), transformed through axes calibrated on major tick marks",
                           "axisCalibrationPixels": f"x=94+143*(logM-8) pt; y=24+100.2*(-1-logPhi) pt; frame, major ticks and axis labels asserted per panel",
                           "digitizationUncertaintyDex": 0.01},
            "calibration": "target" if z == 0 else "prediction", "rankable": False,
            "notes": "Vector-path extraction; exact to PDF coordinate precision, so uncertainty is the plotted line, not marker tracing."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "pillepich18-gsmf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} GSMF records from Pillepich+18 Fig. 14 vector paths")
