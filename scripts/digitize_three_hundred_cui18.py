"""The Three Hundred project (Cui et al. 2018, MNRAS 480, 2898; arXiv:1809.04622): 324 re-simulated cluster regions run with two SPH codes (GADGET-MUSIC and GADGET-X). Two results of the paper are drawn as vector figures and are read from
the figure files of the arXiv source: the gas fraction inside R500 against M500 (Fig. 5, left panel; median and 16th-84th percentiles of the comprehensive sample in 0.2 dex bins) and the Y500-M500 relation (Fig. 10; the same binned medians) with the
best-fitting power laws of Table 7, which are stored as published fits. The stellar fraction panel of Fig. 5 (no matching relation in the dataset), the stellar-to-halo mass relation of the central galaxies (Fig. 6) and the satellite mass
function (Fig. 7, counts per cluster, not a number density) are not read.
Both figures are matplotlib vector files with a text layer. Their axes are calibrated from tick marks (a log axis from labelled decades, validated by the minor ticks at log10(2 .. 9)) and every calibration is checked against numbers the paper prints:
the Planck (2014) line of Fig. 10 (A = -4.19, B = 1.79, drawn and printed in the legend), the two fitted lines (Table 7), the self-similar slope 5/3 named in the caption, the mass limit of the complete sample (Table A1: M500 = 4.60e14 h^-1 Msun, the vertical
dashed lines of both figures) and the cosmic baryon fraction Omega_b/Omega_m = 0.048/0.307 (Table 1, the horizontal dashed line of Fig. 5). Masses are plotted in h^-1 Msun and converted with the paper's h = 0.678. Needs PyMuPDF.
Usage: python3 scripts/digitize_three_hundred_cui18.py [SOURCE_DIR]   (writes data/curves/three-hundred-cui18.json)"""
import hashlib
import json
import math
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1809.04622"
DOI = "10.1093/mnras/sty2111"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PLOTS = SRC / "plots"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "three-hundred-cui18.json"
CITE = "Cui et al. 2018, MNRAS 480, 2898 (The Three Hundred project; arXiv:1809.04622)"
H, OMEGA_B, OMEGA_M = 0.678, 0.048, 0.307          # Table 1
LOG_H = math.log10(H)
M500_COMPLETE = 4.60e14                             # h^-1 Msun, Table A1 (z = 0)
FIT = {"planck": (-4.19, 1.79), "music": (-4.26, 1.62), "gadgetx": (-4.18, 1.63)}   # legend of Fig. 10 and Table 7 (A, B of d_A^2 Y500 = 10^A (M500 / 6e14 Msun)^B)
SHA_TEX = hashlib.sha256((SRC / "paper.tex").read_bytes()).hexdigest()
INSET = False
BLACK, RED, BLUE = (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rgb(c):
    return tuple(round(v, 2) for v in c)


def drawings(page, inset=False):
    """The drawings of a page; for a figure with an inset (drawn last, over a white box, with its own copy of the data clipped to its frame) only those before the inset."""
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if inset and d["type"] == "f" and d["fill"] is not None and rgb(d["fill"]) == (1.0, 1.0, 1.0) and 200 < r.width < 260 and 150 < r.height < 175:
            break
        out.append(d)
    return out


def long_strokes(page, width, min_len=100.0):
    """Horizontal and vertical single black strokes of the given width and at least min_len long: ([(x, y0, y1)], [(y, x0, x1)])."""
    vs, hs = [], []
    for d in drawings(page, INSET):
        if d["type"] != "s" or d["color"] is None or rgb(d["color"]) != BLACK or abs((d.get("width") or 0) - width) > 0.05 or len(d["items"]) != 1 or d["items"][0][0] != "l":
            continue
        a, b = d["items"][0][1], d["items"][0][2]
        if abs(a.x - b.x) < 0.01 and abs(a.y - b.y) > min_len:
            vs.append((a.x, min(a.y, b.y), max(a.y, b.y)))
        if abs(a.y - b.y) < 0.01 and abs(a.x - b.x) > min_len:
            hs.append((a.y, min(a.x, b.x), max(a.x, b.x)))
    return vs, hs


def left_frame(page, panels):
    """Frame of the left (or only) panel from the black axis strokes of width 0.8 (a figure with an inset also has the inset's strokes inside the frame, so the outermost ones are taken)."""
    vs, hs = long_strokes(page, 0.8)
    xs = sorted({round(x, 1) for x, _, _ in vs})
    ys = sorted({round(y, 1) for y, _, _ in hs})
    assert len(xs) >= 2 and len(ys) >= 2, (xs, ys)
    return pymupdf.Rect(xs[0], ys[0], xs[1] if panels == 2 else xs[-1], ys[-1])


def major_ticks(page, frame, axis, length):
    """Positions of the major tick marks (strokes of about `length` points) on the lower (x) or left (y) frame edge."""
    out = set()
    for d in drawings(page, INSET):
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if axis == "x" and abs(a.x - b.x) < 0.01 and abs(abs(a.y - b.y) - length) < 0.3 and abs(min(a.y, b.y) - frame.y1) < 0.6 and frame.x0 - 0.5 <= a.x <= frame.x1 + 0.5:
                out.add(round(a.x, 2))
            if axis == "y" and abs(a.y - b.y) < 0.01 and abs(abs(a.x - b.x) - length) < 0.3 and abs(max(a.x, b.x) - frame.x0) < 0.6 and frame.y0 - 0.5 <= a.y <= frame.y1 + 0.5:
                out.add(round(a.y, 2))
    return sorted(out)


def nearest(vals, v):
    return min(vals, key=lambda t: abs(t - v))


def stars_centre(d):
    pts = [d["items"][0][1]] + [it[2] for it in d["items"]]
    pts = pts[:-1] if abs(pts[0].x - pts[-1].x) < 0.01 and abs(pts[0].y - pts[-1].y) < 0.01 else pts
    return sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts)


def run_markers(page, frame, color, skip):
    """Centres of the filled marker paths of one colour inside the frame, leaving out the handles in the first 40 points of the legend box `skip` (a data point may lie under the legend, which is drawn first): circles and squares by their bounding box, 10-vertex stars by the mean of their vertices."""
    out = []
    for d in drawings(page, INSET):
        if d["type"] != "fs" or d["fill"] is None or rgb(d["fill"]) != color:
            continue
        r = d["rect"]
        kinds = {it[0] for it in d["items"]}
        if kinds == {"l"} and len(d["items"]) == 10 and 8 < r.width < 14:
            cx, cy = stars_centre(d)
        elif (kinds == {"c"} or (kinds == {"re"} and len(d["items"]) == 1)) and 5.5 < r.width < 8.5 and abs(r.width - r.height) < 0.3:
            cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        else:
            continue
        if not (frame.x0 < cx < frame.x1 and frame.y0 < cy < frame.y1) or (skip.contains(pymupdf.Point(cx, cy)) and cx < skip.x0 + 40):
            continue
        out.append((cx, cy))
    return sorted(out)


def bars(page, color, width):
    """Vertical error bars of one colour: (x, top, bottom) in page coordinates."""
    out = []
    for d in drawings(page, INSET):
        if d["type"] != "s" or d["color"] is None or rgb(d["color"]) != color or abs((d.get("width") or 0) - width) > 0.05 or len(d["items"]) != 1 or d["items"][0][0] != "l":
            continue
        a, b = d["items"][0][1], d["items"][0][2]
        if abs(a.x - b.x) < 0.01 and abs(a.y - b.y) > 2:
            out.append((a.x, min(a.y, b.y), max(a.y, b.y)))
    return out


def legend_box(page):
    for d in drawings(page, INSET):
        if d["type"] == "fs" and d["color"] is not None and rgb(d["color"]) == (0.8, 0.8, 0.8) and len(d["items"]) == 8:
            return d["rect"]
    raise AssertionError("legend box not found")


def points_of(page, frame, color, width, fx, fy, skip, up_is_high=True):
    """Median markers with their 16th-84th percentile bars as data points (page -> data); a bar end beyond the frame is outside the drawn axes and is left out."""
    mk = run_markers(page, frame, color, skip)
    bs = bars(page, color, width)
    pts = []
    for cx, cy in mk:
        cand = [b for b in bs if abs(b[0] - cx) < 0.15 and b[1] - 0.2 <= cy <= b[2] + 0.2]
        assert len(cand) == 1, (cx, cy, cand)
        x, top, bot = cand[0]
        p = {"x": fx(cx), "y": fy(cy)}
        if top > frame.y0 + 0.2:
            p["yHigh"] = fy(top)
        if bot < frame.y1 - 0.2:
            p["yLow"] = fy(bot)
        pts.append(p)
    return pts, mk


def cite_record(rid, run, relation, axes, pts, defs, population, warning, figure, panel, pdf, calib, calibration="prediction", rankable=False, interval="scatter", extra=None):
    r = vf.record(rid=rid, source="The Three Hundred", run=run, relation=relation, z=0.0, axes=axes, points=pts, population=population, warning=warning, definitions=defs, citation=f"{CITE}, {figure}", doi=DOI,
                  url=f"https://arxiv.org/abs/{ARXIV}", figure=figure, panel=panel, sha=sha(PLOTS / pdf), member=f"plots/{pdf}", calib=calib, calibration=calibration, interval=interval, connect=True,
                  retrieved="2026-10-24", scatter={"lower": "16th percentile", "upper": "84th percentile"}, **(extra or {}))
    r["provenance"]["sourceTexSha256"] = SHA_TEX
    return r


records = []

# ================================================================ Fig. 10: Y500-M500
F10 = "Fig. 10 (Y500-M500 relation)"
page = pymupdf.open(PLOTS / "YM_relation-full.pdf")[0]
INSET = True
frame = left_frame(page, 1)
xt = major_ticks(page, frame, "x", 3.5)
yt = major_ticks(page, frame, "y", 3.5)
words = page.get_text("words")
xl = []
for w in words:
    if w[4] in ("1013", "1014", "1015") and (w[1] + w[3]) / 2 > frame.y1:
        xl.append((nearest(xt, (w[0] + w[2]) / 2), float(w[4][2:])))
check(sorted(e for _, e in xl) == [13.0, 14.0, 15.0], f"Fig. 10: x tick labels read 10^13, 10^14, 10^15 (exponents {sorted(e for _, e in xl)})")
fx, xcal = vf.axis_fit_log2(page, frame, "x", xl)
# y labels: a '10', a digit word and a minus sign drawn as a filled bar, beside each major tick
minus = [d["rect"] for d in drawings(page, INSET) if d["type"] == "f" and d["fill"] is not None and rgb(d["fill"]) == BLACK and len(d["items"]) == 4 and 6 < d["rect"].width < 9 and d["rect"].height < 1.5 and d["rect"].x1 < frame.x0]
yl = []
for t in yt:
    dig = [w for w in words if w[4].isdigit() and len(w[4]) == 1 and w[2] < frame.x0 and abs((w[1] + w[3]) / 2 - t) < 14 and w[0] > 75]
    assert len(dig) == 1, (t, dig)
    mn = [m for m in minus if abs((m.y0 + m.y1) / 2 - t) < 14 and m.x1 <= dig[0][0] + 0.5]
    assert len(mn) == 1, (t, "minus sign", mn)
    yl.append((t, -float(dig[0][4])))
check(sorted(e for _, e in yl) == [-7.0, -6.0, -5.0, -4.0, -3.0], f"Fig. 10: y tick labels read 10^-7 to 10^-3 (each exponent has a minus sign beside it): {sorted(e for _, e in yl)}")
fy, ycal = vf.axis_fit_log2(page, frame, "y", yl)
check(True, "Fig. 10: both axes are log axes whose minor ticks sit at log10(2 .. 9) (asserted by the calibration)")


def lin_in_frame(page, frame, color, width, dashes=None):
    for d in drawings(page, INSET):
        if d["type"] == "s" and d["color"] is not None and rgb(d["color"]) == color and abs((d.get("width") or 0) - width) < 0.05 and len(d["items"]) > 20 and (dashes is None or (d.get("dashes") or "").replace(" ", "") == dashes.replace(" ", "")):
            pts = [d["items"][0][1]] + [it[2] for it in d["items"]]
            ins = [p for p in pts if frame.x0 <= p.x <= frame.x1 and frame.y0 <= p.y <= frame.y1]
            return [(fx(p.x), fy(p.y)) for p in ins]
    raise AssertionError(("line not found", color, width))


def line_dev(pts, A, B):
    """Largest distance in dex between a drawn line (x in log10 h^-1 Msun) and d_A^2 Y500 = 10^A (M500 / 6e14 Msun)^B."""
    return max(abs(y - (A + B * ((x - LOG_H) - math.log10(6e14)))) for x, y in pts)


planck = lin_in_frame(page, frame, (0.5, 0.0, 0.0), 2.0)
check(line_dev(planck, *FIT["planck"]) < 0.01, f"Fig. 10: the Planck (2014) line lies within {line_dev(planck, *FIT['planck']):.4f} dex of A = -4.19, B = 1.79 (legend and text) with M500 converted by h = 0.678 (fixes both axes and the conversion)")
fit_m = lin_in_frame(page, frame, (0.75, 0.0, 0.75), 4.0)
fit_x = lin_in_frame(page, frame, (0.0, 0.93, 0.0), 2.0)
check(line_dev(fit_m, *FIT["music"]) < 0.01, f"Fig. 10: the GADGET-MUSIC fit line lies within {line_dev(fit_m, *FIT['music']):.4f} dex of A = -4.26, B = 1.62 (Table 7)")
check(line_dev(fit_x, *FIT["gadgetx"]) < 0.01, f"Fig. 10: the GADGET-X fit line lies within {line_dev(fit_x, *FIT['gadgetx']):.4f} dex of A = -4.18, B = 1.63 (Table 7)")
ss = lin_in_frame(page, frame, BLACK, 5.0)
slope = (ss[-1][1] - ss[0][1]) / (ss[-1][0] - ss[0][0])
check(abs(slope - 5 / 3) < 0.01, f"Fig. 10: the thick self-similar line has slope {slope:.4f} (caption: Y500 proportional to M500^(5/3))")
nag = lin_in_frame(page, frame, BLACK, 2.0, "[12.8 3.2 2 3.2] 0")
nag_off = sum(y - (-4.16 + 1.51 * ((x - LOG_H) - math.log10(6e14))) for x, y in nag) / len(nag)
vl = [d for d in drawings(page, INSET) if d["type"] == "s" and d["color"] is not None and rgb(d["color"]) == BLACK and abs((d.get("width") or 0) - 1.5) < 0.05 and len(d["items"]) == 1 and abs(d["items"][0][1].x - d["items"][0][2].x) < 0.01 and d["items"][0][1].x > frame.x0 + 100
      and abs(d["items"][0][1].y - d["items"][0][2].y) > 300]
check(len(vl) == 1 and abs(fx(vl[0]["items"][0][1].x) - math.log10(M500_COMPLETE)) < 0.005, f"Fig. 10: the vertical dashed line is at log M500 = {fx(vl[0]['items'][0][1].x):.4f} h^-1 Msun (Table A1: complete above 4.60e14 h^-1 Msun, log = {math.log10(M500_COMPLETE):.4f})")
legend = legend_box(page)
runs = {}
for name, color, width in (("gadgetx", BLUE, 1.5), ("music", RED, 1.5)):
    pts, mk = points_of(page, frame, color, width, fx, fy, legend)
    xs = [p["x"] for p in pts]
    check(len(pts) == 12 and all(abs((b - a) - 0.2) < 0.01 for a, b in zip(xs, xs[1:])), f"Fig. 10: {name} has {len(pts)} bins spaced by 0.2 dex (x = {xs[0]:.3f} to {xs[-1]:.3f} in log h^-1 Msun)")
    check(all(p["y"] > p.get("yLow", -99) and p["y"] < p.get("yHigh", 99) for p in pts), f"Fig. 10: every {name} median lies inside its 16th-84th percentile bar")
    runs[name] = pts
dx = [a["x"] - b["x"] for a, b in zip(runs["music"], runs["gadgetx"])]
check(max(dx) - min(dx) < 0.005 and abs(dx[0] - 0.04) < 0.005, f"Fig. 10: the GADGET-X symbols are drawn {dx[0]:.3f} dex left of the GADGET-MUSIC ones in every bin (a constant display offset, kept as drawn); the GADGET-MUSIC bins are centred on 13.1, 13.3, ... (x = {runs['music'][0]['x']:.3f})")

AX_X = {"xDefinition": "log10 M500 (mass inside R500, the radius enclosing 500 times the critical density; plotted in h^-1 Msun and converted with h = 0.678)", "xUnit": "log10(Msun)"}
AX_Y = {"yDefinition": "log10 d_A^2 Y500 (integrated Compton parameter inside R500, E(z) = 1 at z = 0)", "yUnit": "log10(Mpc^2)"}
DEF_YM = {"haloMassDefinition": "M500crit", "massMethod": "halo mass inside R500 from the AHF halo finder (all particles; simulation, not an observational proxy)", "cosmology": {"H0": 67.8, "Om": 0.307},
          "sampleSelection": "comprehensive sample: all uncontaminated haloes of the 324 re-simulated regions; mass-complete only above M500 = 4.60e14 h^-1 Msun, the fit is weighted by the completeness below it",
          "population": "all haloes of the comprehensive sample", "szScaling": "none (z = 0 only, 'for which E(z) = 1')", "szAperture": "projected (cylindrical) aperture of radius R500, x-y projection",
          "szDefinition": "d_A^2 Y500, the Compton y parameter of the SPH gas particles (with the simulation's smoothing kernel) integrated over the aperture"}
IMF = {"music": "salpeter55", "gadgetx": "chabrier03"}   # Table 2 (IMF row)
RUN = {"music": "GADGET-MUSIC (324 regions, comprehensive sample)", "gadgetx": "GADGET-X (324 regions, comprehensive sample)"}
CODE = {"music": "GADGET-MUSIC (classic entropy-conserving SPH, no AGN; Salpeter IMF; Table 2)", "gadgetx": "GADGET-X (SPH with thermal diffusion and artificial viscosity, AGN feedback; Chabrier IMF; Table 2)"}
CALIB_YM = ("x: log axis (labelled decades 10^13 to 10^15 from the text layer; minor ticks at log10 2 to 9); y: log axis (labelled decades 10^-7 to 10^-3, minus signs drawn as filled bars); both validated by the drawn Planck (2014) line "
            "(A = -4.19, B = 1.79 printed in the legend), the two Table 7 fit lines, the 5/3 self-similar line and the vertical line at the Table A1 completeness limit; the masses are drawn in h^-1 Msun and converted with h = 0.678")
for name in ("gadgetx", "music"):
    A, B = FIT[name]
    pts = [{"x": round(p["x"] - LOG_H, 3), "y": round(p["y"], 4), **{k: round(p[k], 4) for k in ("yLow", "yHigh") if k in p}} for p in sorted(runs[name], key=lambda p: p["x"])]
    # published power-law fit (Table 7)
    records.append({
        "id": f"cui18.three-hundred.ysz.{name}.fit", "source": "The Three Hundred", "run": RUN[name] + ", power-law fit", "kind": "simulation", "relation": "ysz",
        "epoch": {"zRepresentative": 0.0, "zNominal": 0.0, "zMin": 0.0, "zMax": 0.0, "mode": "published-epoch", "snapshot": None},
        "axes": {**AX_X, **AX_Y}, "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "parametric", "equation": f"d_A^2 Y500 = 10^{A} (M500 / 6e14 Msun)^{B} Mpc^2  (Table 7 of Cui+18, eq. 7; the normalising mass has no h)", "expression": "logA+alpha*(x-logM0)",
                           "parameters": {"logA": A, "alpha": B, "logM0": round(math.log10(6e14), 5)}},
        "scatter": None,
        "selection": {"population": "all haloes of the comprehensive sample",
                      "warning": f"Power-law fit of {CODE[name]} to the binned d_A^2 Y500 - M500 data of the comprehensive sample (the fit uses the individual clusters, so it is not a line through the plotted medians; the paper says the fit lines are offset from the medians). Parameters as printed in Table 7: A = {A} +/- 0.07, B = {B} (+/- {0.31 if name == 'music' else 0.29}). "
                                 "The domain is the span of the plotted mass bins (the paper says the relation extends down to M500 = 1e13 h^-1 Msun and gives no fitted range). z = 0 only."},
        "definitions": {**DEF_YM, "imf": IMF[name]},
        "provenance": {"tier": "published-fit", "citation": f"{CITE}, Table 7 (fitted parameters of the Y500-M500 relation) and Fig. 10", "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-24",
                       "checksumSha256": sha(PLOTS / "YM_relation-full.pdf"), "sourceMember": "paper.tex (Table 7) and plots/YM_relation-full.pdf (fit line checked against the printed parameters)", "sourceTexSha256": SHA_TEX,
                       "extractionMethod": "parameters transcribed from the LaTeX table; the drawn fit line of the figure was read from its vector path and agrees with them (see the script)"},
        "calibration": "prediction", "rankable": True, "notes": "Published fit, not the simulation's plotted medians."})
    records.append(cite_record(
        f"cui18.three-hundred.ysz.{name}.medians", RUN[name] + ", binned medians", "ysz", {**AX_X, **AX_Y}, pts, {**DEF_YM, "imf": IMF[name]}, "all haloes of the comprehensive sample",
        f"Median d_A^2 Y500 in 0.2 dex bins of M500 for {CODE[name]}, read from the markers and error bars of Fig. 10 (error bars are the 16th and 84th percentiles; a bar end below the lower axis limit is not drawn and is left out). "
        "Below M500 = 4.60e14 h^-1 Msun (log 14.66) the sample is not mass complete and its haloes lie in denser environments than a complete sample (the paper). " + ("The GADGET-X symbols are drawn 0.04 dex left of the GADGET-MUSIC bin centres; x is stored as drawn. " if name == "gadgetx" else "")
        + "The Nagarajan et al. (2018) line is not used: as drawn it lies %.3f dex from the A = -4.16, B = 1.51 of its legend with the same axes, which the paper does not explain." % nag_off,
        F10, f"{name} markers and error bars", "YM_relation-full.pdf", CALIB_YM, extra={"note": "Vector-path extraction; exact to PDF coordinate precision."}))

# ================================================================ Fig. 5, left panel: gas fraction inside R500
F5 = "Fig. 5 (baryonic fractions, gas panel)"
page = pymupdf.open(PLOTS / "Baryonic-fractions-hydro-full.pdf")[0]
INSET = False
frame = left_frame(page, 2)
fx, xcal = vf.axis_fit(page, frame, "x")
check([round(v, 1) for _, v in xcal] == [13.0, 13.5, 14.0, 14.5, 15.0], f"Fig. 5: x axis calibrated on the labelled ticks 13.0 to 15.0 (log M500 in h^-1 Msun): {[v for _, v in xcal]}")
yt = major_ticks(page, frame, "y", 3.5)
check(len(yt) == 1, f"Fig. 5: one labelled decade on the y axis ('10^-1' at y = {yt})")
w1 = [w for w in page.get_text("words") if w[4] == "1" and w[2] < frame.x0 and abs((w[1] + w[3]) / 2 - yt[0]) < 14]
mb = [d["rect"] for d in drawings(page, INSET) if d["type"] == "f" and d["fill"] is not None and rgb(d["fill"]) == BLACK and len(d["items"]) == 4 and 5 < d["rect"].width < 9 and d["rect"].height < 1.5 and d["rect"].x1 < frame.x0
      and abs((d["rect"].y0 + d["rect"].y1) / 2 - yt[0]) < 14]
check(len(w1) == 1 and len(mb) == 1 and mb[0].x1 <= w1[0][0] + 0.5, "Fig. 5: the label beside the tick reads 10^-1 (the digit 1 with a minus bar before it)")
fy, ycal, per_dex = vf.axis_fit_log1(page, frame, "y", (yt[0], -1))
hl = [d for d in drawings(page, INSET) if d["type"] == "s" and d["color"] is not None and rgb(d["color"]) == BLACK and abs((d.get("width") or 0) - 4.0) < 0.05 and len(d["items"]) == 1 and abs(d["items"][0][1].y - d["items"][0][2].y) < 0.01
      and abs(d["items"][0][1].x - d["items"][0][2].x) > 200]
check(len(hl) == 1 and abs(fy(hl[0]["items"][0][1].y) - math.log10(OMEGA_B / OMEGA_M)) < 0.005,
      f"Fig. 5: the thick horizontal dashed line is at log f = {fy(hl[0]['items'][0][1].y):.4f}, the cosmic baryon fraction Omega_b/Omega_m = 0.048/0.307 (Table 1; log = {math.log10(OMEGA_B / OMEGA_M):.4f}); the y axis has {per_dex:.1f} points per dex")
vl = [d for d in drawings(page, INSET) if d["type"] == "s" and d["color"] is not None and rgb(d["color"]) == BLACK and abs((d.get("width") or 0) - 2.0) < 0.05 and len(d["items"]) == 1 and abs(d["items"][0][1].x - d["items"][0][2].x) < 0.01
      and abs(d["items"][0][1].y - d["items"][0][2].y) > 200 and frame.x0 + 1 < d["items"][0][1].x < frame.x1 - 1]
check(len(vl) == 1 and abs(fx(vl[0]["items"][0][1].x) - math.log10(M500_COMPLETE)) < 0.005, f"Fig. 5: the vertical dashed line is at log M500 = {fx(vl[0]['items'][0][1].x):.4f} h^-1 Msun (Table A1: complete above 4.60e14 h^-1 Msun, log = {math.log10(M500_COMPLETE):.4f})")
legend = legend_box(page)
LOGFB = math.log10(OMEGA_B / OMEGA_M)
AX_FG = {"xDefinition": "log10 M500 (mass inside R500, the radius enclosing 500 times the critical density; plotted in h^-1 Msun and converted with h = 0.678)", "xUnit": "log10(Msun)",
         "yDefinition": "log10 gas fraction within R500 (gas mass over M500) normalised by the cosmic baryon fraction Omega_b/Omega_m = 0.048/0.307 of the simulation", "yUnit": "dex"}
DEF_FG = {"apertureDefinition": "R500crit", "fgasNormalisation": "Omega_b/Omega_m of the simulation (0.048/0.307 = 0.156)", "massMethod": "simulation: gas particles inside R500 over the halo M500 (AHF)", "cosmology": {"H0": 67.8, "Om": 0.307},
          "population": "all haloes of the comprehensive sample"}
CALIB_FG = ("x: linear axis in log M500 (labelled ticks 13.0 to 15.0); y: log axis with one labelled decade (10^-1) and the minor ticks at log10 2 to 9 fixing the scale; checked against the drawn cosmic baryon fraction line (0.048/0.307, Table 1) and the vertical line at the Table A1 "
            "completeness limit (4.60e14 h^-1 Msun); the gas fraction is divided by Omega_b/Omega_m = 0.048/0.307 and the masses converted with h = 0.678")
for name, color, label in (("music", RED, "GADGET-MUSIC"), ("gadgetx", BLUE, "GADGET-X")):
    pts, mk = points_of(page, frame, color, 2.0, fx, fy, legend)
    xs = [p["x"] for p in pts]
    check(len(pts) == 10 and all(abs((b - a) - 0.2) < 0.01 for a, b in zip(xs, xs[1:])) and abs(xs[0] - 13.1) < 0.01 and abs(xs[-1] - 14.9) < 0.01,
          f"Fig. 5: {label} has {len(pts)} bins of 0.2 dex centred on 13.1 ... 14.9 (x = {xs[0]:.3f} to {xs[-1]:.3f} in log h^-1 Msun)")
    check(all(p["y"] > p["yLow"] and p["y"] < p["yHigh"] for p in pts), f"Fig. 5: every {label} median lies inside its 16th-84th percentile bar")
    # the thin connecting line passes through every marker
    conn = [d for d in drawings(page, INSET) if d["type"] == "s" and d["color"] is not None and rgb(d["color"]) == color and abs((d.get("width") or 0) - 2.0) < 0.05 and len(d["items"]) == 9 and d["rect"].x1 < frame.x1 + 1]
    check(len(conn) == 1 and all(min(math.hypot(cx - v.x, cy - v.y) for v in [conn[0]["items"][0][1]] + [it[2] for it in conn[0]["items"]]) < 0.1 for cx, cy in mk), f"Fig. 5: the {label} line passes through all {len(mk)} markers")
    out = [{"x": round(p["x"] - LOG_H, 3), "y": round(p["y"] - LOGFB, 4), "yLow": round(p["yLow"] - LOGFB, 4), "yHigh": round(p["yHigh"] - LOGFB, 4)} for p in pts]
    records.append(cite_record(
        f"cui18.three-hundred.fgas500.{name}", RUN[name] + ", binned medians", "fgas500", AX_FG, out, {**DEF_FG, "imf": IMF[name]}, "all haloes of the comprehensive sample",
        f"Median gas fraction inside R500 in 0.2 dex bins of M500 for {CODE[name]}, from the markers and error bars of the left panel of Fig. 5 (16th-84th percentiles), divided by Omega_b/Omega_m = 0.048/0.307. "
        "Below M500 = 4.60e14 h^-1 Msun (log 14.66, the dashed vertical line) the sample is not mass complete and its haloes lie in denser environments than a complete sample (the paper). The paper does not say which gas phases enter the gas mass.",
        F5, f"{label} medians and 16th-84th percentile bars, left panel", "Baryonic-fractions-hydro-full.pdf", CALIB_FG, extra={"note": "Vector-path extraction; exact to PDF coordinate precision. The right panel (stellar fraction) is not read."}))

OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} records ({len(checks)} checks passed)")
for c in checks:
    print("  ok:", c)
