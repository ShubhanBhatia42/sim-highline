"""IllustrisTNG, UV-continuum slope beta against M_UV at z = 4, 5 and 6 (Shen et al. 2020, MNRAS 495, 4747; arXiv:2002.10474, the figure 'Predicted UV continuum slope beta versus M_UV relations at z=4-6'; three vector PDFs, UV-beta-0/1/2.pdf).
Per redshift two curves are read from the vector paths: the relation with all dust attenuation (blue circles with 1 sigma dispersion bars) and the relation without the resolved dust attenuation (black line; the paper calls it 'intrinsic'
and notes that the unresolved birth-cloud dust of the MAPPINGS-III library is always present). The tick labels are text, but their minus signs are separate vector paths, so each label is read as the digits plus the minus path found to its left;
the axes are calibrated on the labelled tick marks. Every axis is checked against what the same figure draws and the paper prints: the Bouwens et al. 2014 (red) and 2012 (orange) points plotted in the figure must reproduce the table values
that scripts/transcribe_uvbeta_bouwens.py reads from those papers (to 0.012 in M_UV and in beta), the bars must end on their caps, the blue polyline must pass through the circle centres, and the paper's sentence that the beta without resolved dust
'remains a constant value ~ -2.1 - -2.3' must hold. Needs PyMuPDF.
Usage: python3 scripts/digitize_tng_uvbeta_shen20.py [SOURCE_DIR]   (writes data/curves/shen20-tng-uvbeta.json)"""
import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2002.10474"
DOI = "10.1093/mnras/staa1423"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
FIG = SRC / "figures"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "shen20-tng-uvbeta.json"
CITE = "Shen et al. 2020, MNRAS 495, 4747 (arXiv:2002.10474)"
BLUE, RED, ORANGE = (0.25, 0.41, 0.88), (0.86, 0.08, 0.24), (0.82, 0.41, 0.12)
TEX = next(SRC.glob("paper-arxiv.tex")).read_text(errors="ignore")
SHA_TEX = vf.sha256(next(SRC.glob("paper-arxiv.tex")))
flat = " ".join(TEX.split())
for q in ("we perform a power-law fit on the galaxy UV SED from $1450\\text{\\AA}$ to $3000\\text{\\AA}$ to derive $\\beta$",
          "The wavelength range is selected to cover $1450\\text{\\AA}-1550\\text{\\AA}$ where we measured the rest-frame UV luminosity",
          "Unless specified otherwise, the rest-frame UV magnitude, $M_{\\rm UV}$, in all subsequent analysis in this paper is the dust attenuated magnitude.",
          "we select only star-forming galaxies with $\\log{({\\rm sSFR}/{\\rm yr}^{-1})}>-9.0$",
          "When the resolved dust attenuation is not taken into account (referred to as ``intrinsic''), $\\beta$ remains a constant value $\\sim -2.1-2.3$",
          "we use the term ``without the resolved dust'' because the unresolved dust component in the {\\sc Mappings-\\Rmnum{3}} SED library is always present",
          "$\\Omega_{\\rm m} = 0.3089$, $\\Omega_{\\rm b} = 0.0486$, $\\Omega_{\\Lambda} = 0.6911$, $H_0 = 100\\,h\\,\\kms \\Mpc^{-1} = 67.74\\,\\kms \\Mpc^{-1}$",
          "We combine the median $\\log{(M_{\\rm halo}/{\\rm M}_{\\odot})}$ or the $\\sigma_{\\log{M_{\\rm halo}}}$ using Equation"):
    assert " ".join(q.split()) in flat, ("quoted sentence missing", q)
tab = {}
for r in json.loads((vf.reference_root() / "data" / "curves" / "uvbeta-bouwens12-14.json").read_text())["records"]:
    tab[r["id"]] = [(p["x"], p["y"]) for p in r["representation"]["points"]]
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


def frame_of(page):
    dr = page.get_drawings()
    hz = sorted({(round(d["rect"].x0, 1), round(d["rect"].x1, 1), round(d["rect"].y0, 1)) for d in dr if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and len(d["items"]) == 1 and d["rect"].height == 0 and d["rect"].width > 500})
    vt = sorted({(round(d["rect"].y0, 1), round(d["rect"].y1, 1), round(d["rect"].x0, 1)) for d in dr if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and len(d["items"]) == 1 and d["rect"].width == 0 and d["rect"].height > 500})
    assert len(hz) == 2 and len(vt) == 2
    return pymupdf.Rect(vt[0][2], hz[0][2], vt[-1][2], hz[-1][2])


def calibrate(page, fr):
    """Labels are the digits of the text layer plus the minus drawn as a separate vector path immediately to their left."""
    dr = page.get_drawings()
    minus = [d["rect"] for d in dr if d["type"] == "f" and d["fill"] == (0.0, 0.0, 0.0) and 10 < d["rect"].width < 60 and d["rect"].height < 6]
    xl, yl = [], []
    for w in page.get_text("words"):
        if not w[4].replace(".", "").isdigit():
            continue
        mm = [m for m in minus if w[0] - 30 < m.x0 < w[0] and w[1] < (m.y0 + m.y1) / 2 < w[3]]
        if not mm:
            continue
        m = mm[0]
        if w[1] > fr.y1 - 20 and fr.x0 - 20 < (w[0] + w[2]) / 2 < fr.x1 + 20:
            xl.append(((m.x0 + w[2]) / 2, -float(w[4])))
        elif w[2] <= fr.x0 and fr.y0 - 5 < (m.y0 + m.y1) / 2 < fr.y1 + 5:
            yl.append(((m.y0 + m.y1) / 2, -float(w[4])))
    assert len(xl) == 7 and len(yl) == 5, (xl, yl)
    fx, xt = vf.axis_fit(page, fr, "x", labels=xl)
    fy, yt = vf.axis_fit(page, fr, "y", labels=yl)
    assert len(xt) == 7 and len(yt) == 5
    assert max(abs(fx(p) - v) for p, v in xt) < 0.002 and max(abs(fy(p) - v) for p, v in yt) < 0.002
    return fx, fy, {"xTicks": xt, "yTicks": yt}


def series(page, fr, color):
    """Circles (centres), vertical bars (x -> (y_top, y_bottom)) and caps of one colour, in page coordinates, inside the frame."""
    circ, bars, caps, legend = [], {}, [], []
    for d in page.get_drawings():
        col = tuple(round(v, 2) for v in (d["color"] or ()))
        fil = tuple(round(v, 2) for v in (d["fill"] or ()))
        r = d["rect"]
        if d["type"] == "fs" and fil == color and r.width == 15.0 and r.height == 15.0:
            circ.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
        elif d["type"] == "s" and col == color and r.width == 0 and r.height > 30:
            bars[round(r.x0, 1)] = (r.y0, r.y1)
        elif d["type"] == "s" and col == color and r.width == 0 and 20 < r.height <= 30:
            legend.append(r.x0)
        elif d["type"] == "fs" and fil == color and r.width == 18.0 and r.height == 0:
            caps.append((r.y0, (r.x0 + r.x1) / 2))
    inside = [(x, y) for x, y in circ if fr.x0 <= x <= fr.x1 and fr.y0 <= y <= fr.y1 and not any(abs(x - lx) < 0.3 for lx in legend)]
    return inside, bars, caps


def polyline(page, color):
    out = []
    for d in page.get_drawings():
        col = tuple(round(v, 2) for v in (d["color"] or ()))
        if d["type"] == "s" and col == color and len(d["items"]) >= 15 and all(it[0] == "l" for it in d["items"]):
            out.append([d["items"][0][1]] + [it[2] for it in d["items"]])
    return out


def black_curve(page, fr):
    for d in page.get_drawings():
        if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and len(d["items"]) >= 15 and all(it[0] == "l" for it in d["items"]):
            return [d["items"][0][1]] + [it[2] for it in d["items"]]
    raise AssertionError("black curve not found")


COMMON = {"betaWindow": "power-law fit to the galaxy UV SED from 1450 A to 3000 A", "xVariable": "M_UV", "uvBand": "1450-1550 A (the paper: the range where the rest-frame UV luminosity is measured)",
          "betaMethod": "power-law fit f_lambda ~ lambda^beta to the synthetic SED (no photometry)", "cosmology": {"H0": 67.74, "Om": 0.3089}, "imf": "unspecified",
          "population": "star-forming galaxies, log10(sSFR / yr^-1) > -9.0", "aperture": "integrated flux of the whole galaxy, mock detector 1 physical Mpc away along the +z axis of the simulation box (one viewing direction)",
          "statistic": "unspecified (the caption says 'relations' and '1 sigma dispersion'; mean or median is not stated for this figure)"}
AX = {"xDefinition": "absolute rest-frame UV magnitude M_UV (dust attenuated unless the paper says otherwise)", "xUnit": "mag (AB)", "yDefinition": "UV-continuum slope beta, f_lambda ~ lambda^beta (power-law fit from 1450 to 3000 A)", "yUnit": "dimensionless"}
records = []
for zi, fname in ((4, "UV-beta-0.pdf"), (5, "UV-beta-1.pdf"), (6, "UV-beta-2.pdf")):
    page = pymupdf.open(FIG / fname)[0]
    txt = " ".join(w[4] for w in page.get_text("words"))
    check(f"z = {zi}" in txt, f"{fname} is labelled z = {zi}")
    fr = frame_of(page)
    fx, fy, calib = calibrate(page, fr)
    check(len(calib["xTicks"]) == 7 and len(calib["yTicks"]) == 5, f"{fname}: 7 x labels (M_UV -17 to -23) and 5 y labels (beta -1.6 to -2.4) each on a tick, residual under 0.002")
    # ---- blue circles, bars, caps and polyline
    circ, bars, caps = series(page, fr, BLUE)
    pl = polyline(page, BLUE)
    assert len(pl) == 1
    cap_set = sorted(round(y, 1) for y, _ in caps)
    pts = []
    for x, y in sorted(circ):
        bx = min(bars, key=lambda b: abs(b - x))
        assert abs(bx - x) < 0.3, (fname, x, bx)
        top, bot = bars[bx]
        assert top < y < bot, (fname, x)
        assert any(abs(top - c) < 0.2 for c in cap_set) and any(abs(bot - c) < 0.2 for c in cap_set), (fname, "bar does not end on caps", x)
        pts.append({"x": round(fx(x), 3), "y": round(fy(y), 4), "yLow": round(fy(bot), 4), "yHigh": round(fy(top), 4)})
    check(True, f"{fname}: all {len(circ)} bars end on their two caps")
    onpoly = [min(abs(p.x - x) + abs(p.y - y) for p in pl[0]) for x, y in circ]
    check(max(onpoly) < 0.05, f"{fname}: all {len(circ)} circle centres lie on the vertices of the blue polyline (largest distance {max(onpoly):.3f} pt)")
    xs = [p["x"] for p in pts]
    step = (xs[0] - xs[-1]) / (len(xs) - 1) if xs[0] > xs[-1] else (xs[-1] - xs[0]) / (len(xs) - 1)
    check(abs(step - 8 / 23) < 0.006, f"{fname}: the circles are {step:.4f} mag apart; the paper bins M_UV in 23 bins linearly spaced from -16 to -24 (8/23 = {8 / 23:.4f}), stated for its halo-mass relation and used here as a plausibility check")
    check(all(p["yLow"] < p["y"] < p["yHigh"] for p in pts), f"{fname}: every bar brackets its circle")
    pts.sort(key=lambda p: p["x"])
    # ---- the observations drawn in the same panel reproduce the tables of Bouwens et al. 2014 and 2012
    for color, key, nm in ((RED, f"bouwens14.uvbeta.z{zi}", "Bouwens+14"), (ORANGE, f"bouwens12.uvbeta.z{zi}", "Bouwens+12")):
        oc, _, _ = series(page, fr, color)
        assert oc, (fname, nm)
        hits = 0
        for x, y in oc:
            m, b = fx(x), fy(y)
            near = [(abs(m - tm), abs(b - tb)) for tm, tb in tab[key]]
            assert any(dm < 0.012 and db < 0.012 for dm, db in near), (fname, nm, round(m, 3), round(b, 3), "plotted point not in the table")
            hits += 1
        check(hits >= 5, f"{fname}: {hits} plotted {nm} points inside the frame each reproduce a row of that paper's table to 0.012 in M_UV and in beta (axes checked on independent printed numbers)")
    # ---- the black curve (no resolved dust)
    bc = black_curve(page, fr)
    bpts = sorted(((round(fx(p.x), 3), round(fy(p.y), 4)) for p in bc if fr.x0 <= p.x <= fr.x1))
    check(all(-2.35 <= y <= -2.09 for _, y in bpts), f"{fname}: the curve without resolved dust stays between -2.35 and -2.09 (it spans {min(y for _, y in bpts):.2f} to {max(y for _, y in bpts):.2f}) over M_UV = {bpts[0][0]} to {bpts[-1][0]} (the paper: 'a constant value ~ -2.1 to -2.3', lower at higher redshift)")
    ax = dict(AX)
    run = "IllustrisTNG (TNG50, TNG100 and TNG300 combined after resolution correction)"
    for kind, curve, dust, dmodel, tag, label in (
            ("attenuated", pts, "attenuated", "all dust: resolved dust from Monte Carlo radiative transfer (SKIRT, Model C of Vogelsberger et al. 2020) plus the unresolved birth-cloud dust of the MAPPINGS-III library", "alldust", "relation with all dust attenuation (blue)"),
            ("birthcloud", [{"x": x, "y": y} for x, y in bpts], "birth-cloud dust only (the paper's 'intrinsic': no resolved dust; the unresolved dust of the MAPPINGS-III library is always present)", "no resolved dust; unresolved birth-cloud dust of the MAPPINGS-III library remains", "nodust", "relation without the resolved dust attenuation (black)")):
        d = dict(COMMON, dustTreatment=dust, dustModel=dmodel)
        r = vf.record(rid=f"shen20.tng.uvbeta.z{zi}.{tag}", source="IllustrisTNG", run=f"{run}, {label.split(' (')[0]}", relation="uvbeta", z=float(zi), axes=ax, points=curve,
                      population="star-forming galaxies, log10(sSFR / yr^-1) > -9.0", interval="scatter" if kind == "attenuated" else "unspecified",
                      warning=("UV slope against M_UV for star-forming galaxies of TNG50, TNG100 and TNG300 combined, " + label + (f"; the circles are the plotted bins and the bars are the 1 sigma dispersion; the first circle of the figure (M_UV about -16.2) sits on the frame edge and is not read; " if kind == "attenuated" else "; ")
                               + "the paper's M_UV is the dust-attenuated magnitude unless it says otherwise (not stated separately for this curve). Observational points drawn in the same panel are not extracted here (the tables of those papers are in the dataset)."),
                      definitions=d, citation=f"{CITE}, figure of the predicted beta versus M_UV relations at z = 4-6 ({fname})", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
                      figure="Predicted UV continuum slope beta versus M_UV relations at z = 4-6", panel=f"z = {zi}, {label}", sha=vf.sha256(FIG / fname), member=f"figures/{fname}", calib=calib, calibration="prediction", retrieved="2026-10-23", strict=True)
        r["provenance"]["sourceTexSha256"] = SHA_TEX
        records.append(r)
assert len(records) == 6
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} records; {len(checks)} checks passed")
for c in checks:
    print("  ", c)
