"""FLAMINGO calibration (Kugel et al. 2023, MNRAS 526, 6103; arXiv:2306.05492): the best-fitting calibration simulations that the paper's Fig. 8 draws in red against the two observables the model was fitted to,
the z = 0 galaxy stellar mass function (left column) and the cluster gas fraction inside R500c at z = 0.1 (right column), for the high-, intermediate- and low-resolution runs (m8 in a (100 Mpc)^3 volume, m9 in (200 Mpc)^3, m10 in (400 Mpc)^3).
Read from the vector paths of Fiducial_models.pdf of the arXiv source (the red dotted path is the full curve, the red solid path the part inside the fitted mass range). The emulator curves (blue, purple) and the observations are not stored.
Each of the six panels is calibrated from its own tick labels (the minus signs of the stellar mass function axis are drawn as filled bars and are checked), and checked against numbers the paper prints: the 10-particle lines against the particle masses of
Table 1, the edges of the grey excluded ranges against Table 3 (mass ranges used for fitting), the median bin spacing of the simulated curves against the stated binning (40 bins from 1e8 to 2e13 Msun for m8, 25 bins from 1e9 to 2e12 Msun for m9 and m10;
20 bins in M500c from 1e13 to 1e15 Msun for the gas fractions, whose vertices must lie inside that range) and the X-ray gas fractions drawn as data against the compilation of Table 5 (shifted by the best-fitting hydrostatic bias of Table 6). Needs PyMuPDF.
Usage: python3 scripts/digitize_flamingo_kugel23.py [SOURCE_DIR]   (writes data/curves/flamingo-kugel23.json)"""
import hashlib
import json
import math
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2306.05492"
DOI = "10.1093/mnras/stad2540"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
FIG = SRC / "Images" / "Fiducial_models.pdf"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "flamingo-kugel23.json"
CITE = "Kugel et al. 2023, MNRAS 526, 6103 (FLAMINGO calibration; arXiv:2306.05492)"
OMEGA_B, OMEGA_M, H0 = 0.0486, 0.306, 68.1       # section 2: the '3x2pt + all' cosmology of the DES Y3 analysis
LOG_FB = math.log10(OMEGA_B / OMEGA_M)
RED, GREY, XRAY = (0.8, 0.26, 0.08), (0.5, 0.5, 0.5), (0.34, 0.4, 0.7)
SHA_TEX = hashlib.sha256((SRC / "mnras_template.tex").read_bytes()).hexdigest()
SHA_FIG = hashlib.sha256(FIG.read_bytes()).hexdigest()
# Table 1: particle mass of the baryons (Msun); Table 3: fitted mass ranges (log10 Msun): (SMF lower, SMF upper, f_gas lower, f_gas upper)
RES = {"m8": {"box": 100, "mg": 1.34e8, "range": (8.67, 11.50, 13.50, 13.73), "bins": (40, 8.0, math.log10(2e13))},
       "m9": {"box": 200, "mg": 1.07e9, "range": (9.92, 11.50, 13.50, 14.36), "bins": (25, 9.0, math.log10(2e12))},
       "m10": {"box": 400, "mg": 8.56e9, "range": (11.17, 11.50, 13.50, 14.53), "bins": (25, 9.0, math.log10(2e12))}}
# Table 5: X-ray gas fractions (median of the compilation in bins of the hydrostatic mass) and Table 6: best-fitting hydrostatic bias b_HSE
XRAY_TAB = [(13.89, 0.083), (14.06, 0.094), (14.23, 0.105), (14.40, 0.115), (14.57, 0.130), (14.74, 0.130), (14.91, 0.139)]
B_HSE = 0.743
ROWS = {"m8": (11.3, 142.4), "m9": (176.4, 307.5), "m10": (341.6, 472.6)}
COLS = {"smf": (35.2, 243.8), "fgas": (286.7, 495.4)}
page = pymupdf.open(FIG)[0]
words = page.get_text("words")
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


def rgb(c):
    return tuple(round(v, 2) for v in c)


def labels(frame, axis, sign=1):
    """Numeric tick labels directly beside one frame: below it (x) or to its left (y), as (page position, value)."""
    out = []
    for w in words:
        v = vf.number(w[4])
        if v is None:
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if axis == "x" and 2 < cy - frame.y1 < 14 and frame.x0 - 3 <= cx <= frame.x1 + 3:
            out.append((cx, v))
        if axis == "y" and 0 < frame.x0 - cx < 14 and frame.y0 - 3 <= cy <= frame.y1 + 3:
            out.append((cy, v * sign))
    return out


def minus_bars(frame):
    return [d["rect"] for d in page.get_drawings() if d["type"] == "f" and d["fill"] is not None and rgb(d["fill"]) == (0.0, 0.0, 0.0) and len(d["items"]) == 4 and 3 < d["rect"].width < 6 and d["rect"].height < 1.0
            and 0 < frame.x0 - d["rect"].x1 < 20 and frame.y0 - 3 <= (d["rect"].y0 + d["rect"].y1) / 2 <= frame.y1 + 3]


def red_path(frame):
    """The longest red path inside the frame (the dotted one, which holds every bin) and the solid one (the fitted range): lists of page points."""
    best = []
    for d in page.get_drawings():
        if d["type"] != "s" or d["color"] is None or rgb(d["color"]) != RED or abs((d.get("width") or 0) - 1.5) > 0.05 or len(d["items"]) < 4 or any(it[0] != "l" for it in d["items"]):
            continue
        pts = [d["items"][0][1]] + [it[2] for it in d["items"]]
        if sum(frame.x0 - 0.5 <= p.x <= frame.x1 + 0.5 and frame.y0 - 0.5 <= p.y <= frame.y1 + 0.5 for p in pts) < 0.9 * len(pts):
            continue
        best.append(((d.get("dashes") or "").strip() not in ("[] 0", ""), pts))
    dotted = [p for dashed, p in best if dashed]
    assert len(dotted) == 1, ("red dotted path", len(dotted))
    return dotted[0]


def vertical_lines(frame, dashes):
    out = []
    for d in page.get_drawings():
        if d["type"] == "s" and d["color"] is not None and rgb(d["color"]) == (0.0, 0.0, 0.0) and abs((d.get("width") or 0) - 1.5) < 0.05 and len(d["items"]) == 1 and d["items"][0][0] == "l" and (d.get("dashes") or "").replace(" ", "") == dashes:
            a, b = d["items"][0][1], d["items"][0][2]
            if abs(a.x - b.x) < 0.01 and frame.x0 < a.x < frame.x1 and abs(abs(a.y - b.y) - (frame.y1 - frame.y0)) < 1 and abs(min(a.y, b.y) - frame.y0) < 1:
                out.append(a.x)
    return out


def grey_edges(frame):
    """Left and right edge (page x) of the grey excluded ranges of a panel."""
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if d["type"] == "f" and d["fill"] is not None and rgb(d["fill"]) == GREY and len(d["items"]) == 4 and abs(r.y0 - frame.y0) < 0.5 and frame.x0 - 0.5 <= r.x0 < frame.x1 and r.x1 <= frame.x1 + 6:
            out.append((r.x0, min(r.x1, frame.x1)))
    return sorted(out)


def xray_points(frame, fx, fy):
    """Centres of the X-ray data markers inside the frame that carry an error bar, leaving out the handle of the legend entry 'X-ray data'."""
    bars = []
    for d in page.get_drawings():
        if d["type"] == "s" and d["color"] is not None and rgb(d["color"]) == XRAY and len(d["items"]) == 1 and abs(d["items"][0][1].x - d["items"][0][2].x) < 0.01 and abs(d["items"][0][1].y - d["items"][0][2].y) > 1:
            bars.append((d["items"][0][1].x, min(d["items"][0][1].y, d["items"][0][2].y), max(d["items"][0][1].y, d["items"][0][2].y)))
    out = []
    for d in page.get_drawings():
        if d["type"] in ("f", "fs") and d["fill"] is not None and rgb(d["fill"]) == XRAY and len(d["items"]) >= 8:
            r = d["rect"]
            cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            if frame.x0 < cx < frame.x1 and frame.y0 < cy < frame.y1 and any(abs(b[0] - cx) < 0.2 and b[1] - 0.2 <= cy <= b[2] + 0.2 for b in bars) \
                    and not any(w[4] == "X-ray" and frame.x0 < w[0] < frame.x1 and w[0] - 40 < cx < w[0] and abs((w[1] + w[3]) / 2 - cy) < 6 for w in words):
                out.append((fx(cx), fy(cy)))
    return sorted(out)


records = []
AX_SMF = {"xDefinition": "log10 stellar mass within a 3D aperture of 50 kpc (a lognormal mass error, 0.07 dex at z = 0, is added to every simulated mass before counting)", "xUnit": "log10(Msun)",
          "yDefinition": "log10 number density per dex of stellar mass (the axis reads Mpc^-3; the boxes are given in comoving Mpc)", "yUnit": "log10(cMpc^-3 dex^-1)"}
AX_FG = {"xDefinition": "log10 M500c (mass inside R500c, the radius enclosing 500 times the critical density)", "xUnit": "log10(Msun)",
         "yDefinition": "log10 gas fraction inside R500c (gas mass over M500c) normalised by the cosmic baryon fraction Omega_b/Omega_m = 0.0486/0.306 of the simulation", "yUnit": "dex"}
COSMO = {"H0": H0, "Om": OMEGA_M}
for name, (y0, y1) in ROWS.items():
    res = RES[name]
    fl, fr = pymupdf.Rect(COLS["smf"][0], y0, COLS["smf"][1], y1), pymupdf.Rect(COLS["fgas"][0], y0, COLS["fgas"][1], y1)
    # ------------------------------------------------ stellar mass function, left panel
    fxs, xcal = vf.axis_fit(page, fl, "x", labels=labels(fl, "x"))
    ylab = labels(fl, "y", -1)
    check(len(minus_bars(fl)) == len(ylab) == 8, f"{name} SMF: the {len(ylab)} y labels (5.0 to 1.5) each carry a minus sign drawn as a filled bar")
    fys, ycal = vf.axis_fit(page, fl, "y", labels=ylab)
    pts_page = red_path(fl)
    lo, hi = res["range"][:2]
    pl = vertical_lines(fl, "[1.52.475]0")
    check(len(pl) == 1 and abs(fxs(pl[0]) - math.log10(10 * res["mg"])) < 0.01, f"{name} SMF: the '10 particles' line is at log M* = {fxs(pl[0]):.4f}, Table 1: 10 x {res['mg']:.3g} Msun = {math.log10(10 * res['mg']):.4f}")
    ge = grey_edges(fl)
    check(len(ge) == 2 and abs(fxs(ge[0][1]) - lo) < 0.02 and abs(fxs(ge[1][0]) - hi) < 0.1,
          f"{name} SMF: the grey excluded ranges end at log M* = {fxs(ge[0][1]):.3f} and start at {fxs(ge[1][0]):.3f} (Table 3: fitted from {lo} to {hi}; the table is rounded and its limits move with the bias factors, so the upper edge is checked to 0.1 dex)")
    nb, b0, b1 = res["bins"]
    dlog = (b1 - b0) / nb
    xs = [fxs(p.x) for p in pts_page]
    steps = [b - a for a, b in zip(xs, xs[1:])]
    med = sorted(steps)[len(steps) // 2]
    dlog2 = (b1 - b0) / (nb - 1)     # the same range cut into nb edges (nb - 1 intervals) is the other reading of 'nb logarithmically spaced bins'
    check(min(abs(med / dlog - 1), abs(med / dlog2 - 1)) < 0.03, f"{name} SMF: the median spacing of the {len(xs)} vertices of the simulated curve is {med:.4f} dex; the stated {nb} logarithmic bins from {10 ** b0:.0e} to 2e{round(b1 - math.log10(2))} Msun are {dlog:.4f} dex wide "
                                                                  f"(or {dlog2:.4f} dex if the {nb} are edges); empty bins are dropped and a vertex is not always at its bin centre")
    limit = math.log10(10 * res["mg"])
    pts = [{"x": round(fxs(p.x), 3), "y": round(fys(p.y), 4)} for p in pts_page if fxs(p.x) >= limit - 0.005]
    check(len(pts) >= 6, f"{name} SMF: {len(pts)} vertices at or above the 10-particle limit")
    base = f"FLAMINGO calibration run, {name} ({res['box']} Mpc)^3, best-fitting subgrid parameters"
    d_smf = {"imf": "chabrier03", "cosmology": COSMO, "massDefinition": "aperture-50pkpc, 3D, with a lognormal mass error added", "densityFrame": "comoving",
             "population": "galaxies of the calibration volume (VELOCIraptor subhaloes)"}
    r = vf.record(rid=f"kugel23.flamingo.gsmf.{name}.z0", source="FLAMINGO", run=base, relation="gsmf", z=0.0, axes=AX_SMF, points=pts,
                  population="galaxies of the calibration volume (VELOCIraptor subhaloes)",
                  warning=f"Galaxy stellar mass function at z = 0 of the FLAMINGO {name} calibration simulation run with the best-fitting subgrid parameters in a ({res['box']} Mpc)^3 volume ({res['mg']:.3g} Msun baryonic particles), read from the red path of Fig. 8 of Kugel et al. 2023 and cut at the 10-particle limit "
                          f"(M* = {limit:.2f}; fainter bins are drawn dotted and grey). The simulated masses are 3D 50 kpc aperture masses to which a random lognormal error of 0.07 dex (z = 0) is added, as the paper does to mimic observational errors (an Eddington-like bias), so the high-mass end is steeper-looking than the plain aperture masses give. "
                          f"The model was fitted to this curve between log M* = {lo} and {hi}, so it is not a prediction there. The paper does not say whether satellites and subhaloes without stars enter the count. The box is small, so the highest-mass bins hold few galaxies. The paper says the Chabrier (2003) IMF is used for the stars.",
                  definitions=d_smf, citation=f"{CITE}, Fig. 8, left column", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="Fig. 8 (best-fitting models against the SMF and the gas fractions)", panel=f"{name} stellar mass function, red path",
                  sha=SHA_FIG, member="Images/Fiducial_models.pdf",
                  calib="x: linear axis in log M* (labelled ticks 8 to 12); y: linear axis in log number density (labelled ticks 1.5 to 5.0 with drawn minus signs); each panel calibrated on its own labels and checked against the 10-particle line, the stated binning and the Table 3 mass range",
                  calibration="target", retrieved="2026-10-24", interval="unspecified", connect=True,
                  note="Vector-path extraction; exact to PDF coordinate precision.")
    r["provenance"]["sourceTexSha256"] = SHA_TEX
    records.append(r)

    # ------------------------------------------------ gas fraction inside R500c, right panel
    fxg, _ = vf.axis_fit(page, fr, "x", labels=labels(fr, "x"))
    fyg, _ = vf.axis_fit(page, fr, "y", labels=labels(fr, "y"))
    gl = grey_edges(fr)
    up = res["range"][3]
    check(len(gl) == 1 and abs(fxg(gl[0][0]) - up) < 0.02, f"{name} f_gas: the grey excluded range starts at log M500c = {fxg(gl[0][0]):.3f} (Table 3: fitted up to {up})")
    xp = xray_points(fr, fxg, fyg)
    ok = []
    for tx, ty in XRAY_TAB:
        near = min(xp, key=lambda p: abs(p[0] - (tx - math.log10(B_HSE))))
        ok.append((near[0] - (tx - math.log10(B_HSE)), near[1] - ty))
    check(len(xp) == 8 and max(abs(a) for a, _ in ok) < 0.01 and max(abs(b) for _, b in ok) < 0.002,
          f"{name} f_gas: the 7 X-ray data points of Table 5 are drawn within {max(abs(a) for a, _ in ok):.4f} dex in mass (after the best-fitting hydrostatic bias b = 0.743, log b = {math.log10(B_HSE):.3f}) and {max(abs(b) for _, b in ok):.4f} in f_gas")
    gpts = red_path(fr)
    gx = [fxg(p.x) for p in gpts]
    check(len(gx) >= 6 and 13.0 <= min(gx) and max(gx) <= 15.0, f"{name} f_gas: the {len(gx)} vertices of the simulated curve lie between log M500c = {min(gx):.3f} and {max(gx):.3f}, inside the stated binning range of 1e13 to 1e15 Msun")
    out = [{"x": round(fxg(p.x), 3), "y": round(math.log10(fyg(p.y)) - LOG_FB, 4)} for p in gpts]
    d_fg = {"imf": "chabrier03", "cosmology": COSMO, "apertureDefinition": "R500crit", "fgasNormalisation": "Omega_b/Omega_m of the simulation (0.0486/0.306 = 0.159)",
            "massMethod": "simulation: gas mass inside R500c over M500c (VELOCIraptor haloes; the paper does not say which gas phases are counted)", "population": "haloes of the calibration volume (bins hold at least ten haloes)"}
    r = vf.record(rid=f"kugel23.flamingo.fgas500.{name}.z0p1", source="FLAMINGO", run=base, relation="fgas500", z=0.1, axes=AX_FG, points=out, population="haloes of the calibration volume (bins hold at least ten haloes)",
                  warning=f"Median gas fraction inside R500c at z = 0.1 against M500c of the FLAMINGO {name} calibration simulation run with the best-fitting subgrid parameters in a ({res['box']} Mpc)^3 volume, read from the red path of Fig. 8 of Kugel et al. 2023 (adaptive bins of at least ten haloes between 1e13 and 1e15 Msun; "
                          f"the statistic is not stated: the paper takes the median and the 16th-84th percentiles of each bin for the fit) and divided by Omega_b/Omega_m = 0.0486/0.306. The model was fitted to X-ray gas fractions at z = 0.1 up to M500c = 10^{up} Msun and to weak lensing at z = 0.3, so this curve is a calibration target, not a prediction, and the observations "
                          "it was fitted to carry a hydrostatic mass bias that the paper fits (b = 0.743). The small box holds few clusters, so the highest bins are noisy.",
                  definitions=d_fg, citation=f"{CITE}, Fig. 8, right column", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="Fig. 8 (best-fitting models against the SMF and the gas fractions)", panel=f"{name} gas fraction, red path",
                  sha=SHA_FIG, member="Images/Fiducial_models.pdf",
                  calib="x: linear axis in log M500c (labelled ticks 13.0 to 15.0); y: linear axis in f_gas (labelled ticks 0.00 to 0.14); each panel calibrated on its own labels and checked against the Table 5 X-ray data drawn in the panel (shifted by the Table 6 bias), the stated binning and the Table 3 mass range; "
                        "f_gas is divided by Omega_b/Omega_m = 0.0486/0.306 (section 2)",
                  calibration="target", retrieved="2026-10-24", interval="unspecified", connect=True,
                  note="Vector-path extraction; exact to PDF coordinate precision.")
    r["provenance"]["sourceTexSha256"] = SHA_TEX
    records.append(r)

OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} records ({len(checks)} checks passed)")
for c in checks:
    print("  ok:", c)
