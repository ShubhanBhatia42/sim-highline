import json
import math
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1610.06375"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDFDIR = SRC / "pdf"
PDF = PDFDIR / "fig4.pdf"
if not PDF.exists():
    import subprocess
    PDFDIR.mkdir(exist_ok=True)
    subprocess.run(["epstopdf", str(next(SRC.rglob("fig4.eps"))), f"--outfile={PDF}"], check=True)
XM = {0: [64.3, 151.4, 189.1, 276.5], 1: [339.6, 427.0, 464.4, 551.8]}
YM = {0: [23.4, 235.6], 1: [298.7, 510.9]}
XDEX, YDEX = 124.6, 26.525
VAL = {(0, 0): ("all-baryons", 3.11), (1, 0): ("stars+neutral-gas", 3.97), (0, 1): ("stars", 5.04), (1, 1): ("neutral-gas", 3.61)}
page = pymupdf.open(PDF)[0]
sha = vf.sha256(PDF)
dr = page.get_drawings()
ticks = {(round(a.x, 1) if abs(a.x - b.x) < 0.01 else None, round(a.y, 1) if abs(a.y - b.y) < 0.01 else None)
         for d in dr for it in d["items"] if it[0] == "l" for a, b in [(it[1], it[2])] if 9.5 < max(abs(a.x - b.x), abs(a.y - b.y)) < 10.1}
for col in (0, 1):
    for x, v in zip(XM[col], (10, 50, 100, 500)):
        assert (x, None) in ticks, ("x major tick", x)
        assert abs((x - XM[col][0]) / XDEX - math.log10(v / 10)) < 0.01, ("log x spacing", col, v)
ys = [y for (_, y) in ticks if y is not None]
for row in (0, 1):
    for k in range(9):
        assert any(abs(y - (YM[row][0] + k * YDEX)) < 0.4 for y in ys), ("y major tick", row, k)


def fx(col, px):
    return 1 + (px - XM[col][0]) / XDEX


def fy(row, py):
    return 12 - (py - YM[row][0]) / YDEX


def cell(cx, cy):
    return (0 if cx < 320 else 1, 0 if cy < 270 else 1)


fits, dotted = {}, None
for d in dr:
    its = d["items"]
    if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and len(its) == 2 and all(i[0] == "l" for i in its):
        a, b = its[0][1], its[1][2]
        if abs(a.x - b.x) < 0.01 or abs(a.y - b.y) < 0.01 or (abs(a.x - b.x) < 20 and abs(a.y - b.y) < 20):
            continue
        c = cell((a.x + b.x) / 2, (a.y + b.y) / 2)
        col, row = c
        slope = (fy(row, b.y) - fy(row, a.y)) / (fx(col, b.x) - fx(col, a.x))
        if d["dashes"] == "[] 0":
            fits[c] = (slope, [(fx(col, p.x), fy(row, p.y)) for p in (a, b)])
        else:
            dotted = (c, slope, fy(row, a.y), fx(col, a.x))
assert set(fits) == set(VAL)
for c, (sl, _) in fits.items():
    assert abs(sl - VAL[c][1]) < 0.05, ("fit slope vs paper", c, sl, VAL[c][1])
assert dotted is not None and abs(dotted[1] - 3.0) < 0.02
# virial relation M_b = (Ob/Om) V^3/(10 G H0): at V=10 km/s with H0=67.1, G=4.30091e-6 kpc (km/s)^2/Msun
assert abs(dotted[2] - math.log10((0.0486 / 0.3089) * 10.0 ** 3 / (10 * 4.30091e-6 * 0.0671))) < 0.05, ("dotted virial line offset", dotted[2])
records = []
markers = {c: [] for c in VAL}
for d in dr:
    r = d["rect"]
    if d["type"] == "f" and d["fill"] == (0.0, 0.0, 0.0) and 5.0 < r.width < 6.0 and 5.0 < r.height < 6.0 and len(d["items"]) == 13:
        c = cell((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
        markers[c].append((fx(c[0], (r.x0 + r.x1) / 2), fy(c[1], (r.y0 + r.y1) / 2)))
assert all(len(v) >= 60 for v in markers.values()), {k: len(v) for k, v in markers.items()}
DEF = {"imf": "chabrier03", "cosmology": {"H0": 67.1, "Om": 0.3175}}
for c, (name, bstated) in VAL.items():
    if name == "neutral-gas":
        continue
    pts = sorted(markers[c])
    fit = fits[c][1]
    rel = "stfr" if name == "stars" else "btfr"
    if rel == "stfr":
        pts, fit = sorted((y, x) for x, y in pts), [(y, x) for x, y in fit]
        axes = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 circular velocity at the HI radius (R_HI, enclosing 90% of HI flux)", "yUnit": "log10(km/s)"}
        mdef = "stellar mass"
    else:
        axes = {"xDefinition": "log10 circular velocity at the HI radius (R_HI, enclosing 90% of HI flux)", "xUnit": "log10(km/s)",
                "yDefinition": f"log10 {'total baryonic mass within the virial radius' if name == 'all-baryons' else 'stars plus neutral gas mass'}", "yUnit": "log10(Msun)"}
        mdef = "all-baryons-within-virial-radius" if name == "all-baryons" else "stars-plus-neutral-gas"
    defs = {**DEF, "massDefinition": mdef, "velocityDefinition": "circular velocity at R_HI", "population": "zoom-centrals"}
    common = dict(source="NIHAO zoom suite", relation=rel, z=0.0, axes=axes, definitions=defs, citation="Dutton et al. 2017 (NIHAO XII), MNRAS 467, 4937, Fig. 4 (arXiv source numbering), "
                  f"{name} panel", doi="10.1093/mnras/stx458", url=f"https://arxiv.org/abs/{ARXIV}", figure="Figure 4", panel=name, sha=sha, member=f"{PDF.name} (converted from fig4.eps)",
                  calib="manual: major ticks (log x: V=10, 50, 100, 500 km/s at 124.6 pt/dex; y: 12 to 4, 26.5 pt/dex), verified by the fit-line slopes against the paper's stated b and the virial-relation dotted line",
                  calibration="unknown")
    records.append(vf.record(
        rid=f"dutton17.nihao.{rel}-{name.replace('+', '-')}.galaxies.z0", run=f"NIHAO zoom sample (per galaxy, {name})", points=pts, population="individual zoom galaxies (not volume complete)",
        warning=f"Marker centres of the simulated galaxies (black filled circles) read from the vector paths of Dutton et al. 2017 Fig. 4 ({name} panel); no table is published. "
                "Zoom selections are not volume complete. The paper's text labels are outlined, so the axes were calibrated from tick marks and verified against the stated fit slopes.",
        interval="scatter", connect=False, strict=False, scatter={"fitSlopeMeasured": round(fits[c][0], 3), "fitSlopeStatedInFigure": bstated}, **common))
    records.append(vf.record(
        rid=f"dutton17.nihao.{rel}-{name.replace('+', '-')}.fit.z0", run=f"NIHAO zoom sample (power-law fit, {name})", points=fit, population="power-law fit to the plotted zoom galaxies",
        warning=f"Black fit line of Dutton et al. 2017 Fig. 4 ({name} panel), the two ends of the plotted line; the figure states b = {bstated} for M proportional to V_HI^b (read from the render) and the measured slope is {fits[c][0]:.3f}. "
                "The plotted line spans the whole axis range, well beyond the galaxy data. Fit to a zoom selection, not volume complete.", **common))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dutton17-nihao-tf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} NIHAO Tully-Fisher records; fit slopes {[round(v[0], 3) for v in fits.values()]} match the stated b")
