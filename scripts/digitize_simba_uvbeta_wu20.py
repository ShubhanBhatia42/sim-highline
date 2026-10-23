"""SIMBA, UV-continuum slope beta against M_1500 and against stellar mass at z = 6 (Wu et al. 2020, MNRAS 494, 5; arXiv:1911.06330, photometric properties of reionization-epoch galaxies in SIMBA-25 and SIMBA-50), read from three vector figures:
beta-MUV_extinction.pdf (the combined SIMBA-25 and SIMBA-50 relation with no dust, the Salmon et al. 2016, the Calzetti et al. 2000 and the SMC law), beta-MUV.pdf (the Calzetti law with its 1 sigma spread, SIMBA-25 and SIMBA-50 separately)
and beta-Mstar_extinction.pdf (the combined beta-stellar mass relation, four dust laws). The tick labels are text, but their minus signs are separate vector paths, so each label is read as the digits plus the minus path found to its left;
the axes are calibrated on the labelled tick marks. Every axis is checked against numbers printed elsewhere: the observations drawn in the M_1500 panel must reproduce the Bouwens et al. 2014 table (z ~ 6, read by transcribe_uvbeta_bouwens.py), the
Finkelstein et al. 2012 points in the mass panel must reproduce that paper's Table 5 medians (transcribe_uvbetam_finkelstein12.py) and lie inside its mass bins, the legend line styles must match their labels, and the combined curve must lie
between the two boxes where both are drawn. Needs PyMuPDF.
Usage: python3 scripts/digitize_simba_uvbeta_wu20.py [SOURCE_DIR]   (writes data/curves/wu20-simba-uvbeta.json)"""
import json
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1911.06330"
DOI = "10.1093/mnras/staa1044"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
FIG = SRC / "figures"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "wu20-simba-uvbeta.json"
CITE = "Wu et al. 2020, MNRAS 494, 5 (arXiv:1911.06330)"
TEXFILE = SRC / "mnras_template.tex"
SHA_TEX = vf.sha256(TEXFILE)
flat = " ".join(TEXFILE.read_text(errors="ignore").split())
for q in ("We compute $\\beta$ by fitting a power-law slope using the three rest-frame magnitudes at rest-frame 1500 {\\AA}, 2300 {\\AA}, and 2800 {\\AA}",
          "The magnitude at rest-frame 1500 {\\AA}, $\\MUV$, is calculated by the convolving the rest-frame spectra using a boxcar filter centered at 1500 {\\AA} with 400 {\\AA} in width.",
          "assume a \\citet{Chab03} initial mass function",
          "we first calculate the metal column density and the mass-weighted average metallicity along the line of sight to each star particle",
          "We primarily use the \\citet{Calz00} law, but we also consider the extinction law from \\citet{Salm16}",
          "we only use galaxies with $\\MUV\\le-16$ in \\simba-25 and those with $\\MUV\\le-18$ in \\simba-50 when assuming the \\citet{Calz00} extinction law",
          "Errorbars represent $1\\sigma$ spread in $\\beta$ within the galaxy sample.",
          "Without dust attenuation, the $\\beta-\\MUV$ relations are flat",
          "Combined $\\beta-M_*$ relations of \\simba-25 and \\simba-50 at $z=6$."):
    assert " ".join(q.split()) in flat, ("quoted sentence missing", q)
tabs = {}
for r in json.loads((vf.reference_root() / "data" / "curves" / "uvbeta-bouwens12-14.json").read_text())["records"] + json.loads((vf.reference_root() / "data" / "curves" / "uvbetam-finkelstein12.json").read_text())["records"]:
    tabs[r["id"]] = [(p["x"], p["y"]) for p in r["representation"]["points"]]
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


def frame_and_axes(page, xsign_neg, nx, ny):
    dr = page.get_drawings()
    hz = sorted({round(d["rect"].y0, 1) for d in dr if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and d["rect"].height == 0 and d["rect"].width > 300})
    vt = sorted({round(d["rect"].x0, 1) for d in dr if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and d["rect"].width == 0 and d["rect"].height > 200})
    assert len(hz) == 2 and len(vt) == 2
    fr = pymupdf.Rect(vt[0], hz[0], vt[-1], hz[-1])
    minus = [d["rect"] for d in dr if d["type"] == "f" and d["fill"] == (0.0, 0.0, 0.0) and 8 < d["rect"].width < 11 and d["rect"].height < 2]
    xl, yl = [], []
    for w in page.get_text("words"):
        if not w[4].replace(".", "").isdigit():
            continue
        mm = [m for m in minus if w[0] - 16 < m.x0 < w[0] and w[1] - 2 < (m.y0 + m.y1) / 2 < w[3] + 2]
        if w[1] > fr.y1 and fr.x0 - 20 < (w[0] + w[2]) / 2 < fr.x1 + 20 and w[1] < fr.y1 + 12:
            if xsign_neg:
                assert mm, ("x label without minus path", w[4])
                xl.append(((mm[0].x0 + w[2]) / 2, -float(w[4])))
            else:
                assert not mm
                xl.append(((w[0] + w[2]) / 2, float(w[4])))
        elif w[2] <= fr.x0 and fr.y0 - 12 < (w[1] + w[3]) / 2 < fr.y1 + 12:
            assert mm, ("y label without minus path", w[4])
            yl.append(((mm[0].y0 + mm[0].y1) / 2, -float(w[4])))
    assert len(xl) == nx and len(yl) == ny, (xl, yl)
    fx, xt = vf.axis_fit(page, fr, "x", labels=xl)
    fy, yt = vf.axis_fit(page, fr, "y", labels=yl)
    assert len(xt) == nx and len(yt) == ny
    assert max(abs(fx(p) - v) for p, v in xt) < 0.002 and max(abs(fy(p) - v) for p, v in yt) < 0.002
    return fr, fx, fy, {"xTicks": xt, "yTicks": yt}


def lines_of(page, color):
    """Stroked polylines (>= 4 items, all straight) of one colour: dash string -> vertices."""
    out = []
    for d in page.get_drawings():
        if d["type"] == "s" and d["color"] is not None and tuple(round(v, 2) for v in d["color"]) == color and len(d["items"]) >= 4 and all(it[0] == "l" for it in d["items"]):
            out.append(((d.get("dashes") or "").strip(), [d["items"][0][1]] + [it[2] for it in d["items"]]))
    return out


def legend_lines(page, color):
    out = []
    for d in page.get_drawings():
        if d["type"] == "s" and d["color"] is not None and tuple(round(v, 2) for v in d["color"]) == color and d["rect"].height == 0 and abs(d["rect"].width - 22.4) < 0.1:
            out.append(((d.get("dashes") or "").strip(), d["rect"].y0))
    return sorted(out, key=lambda t: t[1])


def legend_words(page, words, right=True):
    out = []
    for w in page.get_text("words"):
        if w[4] in words and (w[0] > 300) == right:
            out.append((w[4], (w[1] + w[3]) / 2))
    return sorted(out, key=lambda t: t[1])


def circles(page, fr, color=(0.0, 0.0, 0.0)):
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if d["type"] == "fs" and d["fill"] is not None and tuple(round(v, 2) for v in d["fill"]) == color and abs(r.width - 8.0) < 0.1 and abs(r.height - 8.0) < 0.1 and len(d["items"]) == 8:
            out.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
    return out


def vbars(page, color):
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if d["type"] == "s" and d["color"] is not None and tuple(round(v, 2) for v in d["color"]) == color and r.width == 0 and r.height > 5:
            out.append((r.x0, r.y0, r.y1))
    return out


def interp(pts, x):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (x - x0) / (x1 - x0) * (y1 - y0)
    return None


GREEN = (0.0, 0.5, 0.0)
DASH = {"nodust": "[ 6 6 ] 0", "salm16": "[ 3 5 1 5 ] 0", "calz00": "[] 0", "smc": "[ 1 3 ] 0"}
LAW = {"nodust": ("intrinsic", "no dust: the extinction-free spectrum (stellar population plus nebular emission)"),
       "calz00": ("attenuated", "Calzetti et al. 2000 law; A_V of each star particle from the metal column density along its line of sight (Milky Way relation), scaled by the dust-to-metal ratio of the sight line"),
       "salm16": ("attenuated", "Salmon et al. 2016 law (the Calzetti law times (lambda / 5500 A)^delta, delta = 0.62 log E(B-V) + 0.26); A_V as for the Calzetti case"),
       "smc": ("attenuated", "SMC extinction law (Gordon et al. 2003); A_V as for the Calzetti case")}
NAME = {"nodust": "no dust", "calz00": "Calzetti00", "salm16": "Salmon16", "smc": "SMC"}
COMMON = {"betaWindow": "power-law fit to the magnitudes at rest-frame 1500, 2300 and 2800 A", "betaMethod": "power law through three synthetic rest-frame magnitudes (the paper: fitting the spectrum directly gives very similar results)",
          "imf": "chabrier03", "cosmology": "unspecified", "aperture": "all star particles of the Caesar galaxy (a 6-D friends-of-friends group); no radius is stated",
          "population": "galaxies with at least 32 star particles; for beta only M_UV <= -16 (SIMBA-25) and M_UV <= -18 (SIMBA-50) with the Calzetti law (the paper does not restate the cut for the other laws)",
          "statistic": "unspecified (the paper says 'relations' and gives the 1 sigma spread; mean or median is not stated)", "stellarPopulation": "FSPS with MIST isochrones and the MILES library, nebular emission from a Cloudy table"}


def rec(rid, run, relation, axes, pts, defs, panel, fname, figure, calib, interval, warning):
    r = vf.record(rid=rid, source="SIMBA", run=run, relation=relation, z=6.0, axes=axes, points=pts, population="galaxies of SIMBA-25 and SIMBA-50 at z = 6", interval=interval, warning=warning, definitions=defs,
                  citation=f"{CITE}, {figure} ({fname})", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure=figure, panel=panel, sha=vf.sha256(FIG / fname), member=f"figures/{fname}", calib=calib, calibration="prediction",
                  retrieved="2026-10-23", strict=True)
    r["provenance"]["sourceTexSha256"] = SHA_TEX
    return r


AXU = {"xDefinition": "absolute UV magnitude M_1500 (rest-frame 1500 A, boxcar filter 400 A wide, dust attenuated with the law of the curve)", "xUnit": "mag (AB)", "yDefinition": "UV-continuum slope beta, f_lambda ~ lambda^beta (power law through the rest-frame magnitudes at 1500, 2300 and 2800 A)", "yUnit": "dimensionless"}
AXM = {"xDefinition": "log10 stellar mass of the galaxy (the paper does not state the aperture)", "xUnit": "log10(Msun)", "yDefinition": AXU["yDefinition"], "yUnit": "dimensionless"}
records = []
curveA = {}

# ================================================================ A. combined beta - M_1500, four dust laws
fname = "beta-MUV_extinction.pdf"
page = pymupdf.open(FIG / fname)[0]
fr, fx, fy, calib = frame_and_axes(page, True, 9, 10)
check(len(calib["xTicks"]) == 9 and len(calib["yTicks"]) == 10, f"{fname}: 9 x labels (M_1500 -23 to -15) and 10 y labels (beta -0.8 to -2.6) on ticks, residual under 0.002")
lg = legend_lines(page, GREEN)
lw = legend_words(page, {"no", "Salmon16", "Calzetti00", "SMC"})
check(len(lg) == 4 and [d for d, _ in lg] == [DASH["nodust"], DASH["salm16"], DASH["calz00"], DASH["smc"]] and [w for w, _ in lw] == ["no", "Salmon16", "Calzetti00", "SMC"] and all(abs(a[1] - b[1]) < 6 for a, b in zip(lg, lw)),
      f"{fname}: the four legend lines (dashed, dash-dot, solid, dotted) sit beside the labels no dust, Salmon16, Calzetti00, SMC")
ls = {d: v for d, v in lines_of(page, GREEN)}
assert set(ls) >= set(DASH.values())
for key, dash in DASH.items():
    v = ls[dash]
    pts = sorted((round(fx(p.x), 3), round(fy(p.y), 4)) for p in v if fr.x0 - 0.5 <= p.x <= fr.x1 + 0.5)
    assert len(pts) >= 6
    curveA[key] = pts
oc = circles(page, fr)
hits = 0
for x, y in oc:
    m, b = fx(x), fy(y)
    if any(abs(m - tm) < 0.012 and abs(b - tb) < 0.012 for tm, tb in tabs["bouwens14.uvbeta.z6"]):
        hits += 1
check(hits == len(tabs["bouwens14.uvbeta.z6"]) == 10, f"{fname}: all {hits} rows of the Bouwens et al. 2014 z ~ 6 table are among the {len(oc)} plotted markers (two are legend markers, three are the Finkelstein et al. 2012 points the caption names) to 0.012 in M_UV and in beta")
check(all(-2.5 < y < -2.2 for _, y in curveA["nodust"]), f"{fname}: the no-dust curve is flat near beta = -2.35 (between -2.5 and -2.2), as the paper says ('without dust attenuation the relations are flat')")
for key in ("nodust", "calz00", "salm16", "smc"):
    law, lawtxt = LAW[key]
    d = dict(COMMON, dustTreatment=law, dustModel=lawtxt, xVariable="M_UV (M_1500)", uvBand="rest-frame 1500 A, boxcar 400 A wide")
    records.append(rec(f"wu20.simba.uvbeta.z6.combined.{key}", f"SIMBA-25 and SIMBA-50 combined, {NAME[key]}", "uvbeta", AXU, [{"x": x, "y": y} for x, y in curveA[key]], d, f"z = 6, {NAME[key]} (combined)", fname,
                       "Combined beta - M_1500 relations at z = 6", calib, "unspecified",
                       f"Combined SIMBA-25 and SIMBA-50 UV slope against M_1500 at z = 6, {NAME[key]}; vertices of the plotted line at the bin centres, no error bars are drawn in this panel. The observations drawn in the panel are not extracted here "
                       "(the Bouwens et al. 2014 table is in the dataset). For the dust laws other than Calzetti the paper does not restate which galaxies enter the relation."))

# ================================================================ B. the two boxes separately, Calzetti law with 1 sigma spread
fname = "beta-MUV.pdf"
page = pymupdf.open(FIG / fname)[0]
fr, fx, fy, calibB = frame_and_axes(page, True, 9, 10)
check(len(calibB["xTicks"]) == 9 and len(calibB["yTicks"]) == 10, f"{fname}: 9 x labels and 10 y labels on ticks, residual under 0.002")
RED, BLUE = (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
lgr, lgb = legend_lines(page, RED), legend_lines(page, BLUE)
lw = legend_words(page, {"m25n1024", "m50n1024"})
allleg = sorted([(d, y, "red") for d, y in lgr] + [(d, y, "blue") for d, y in lgb], key=lambda t: t[1])
check([(d, c) for d, _, c in allleg] == [(DASH["nodust"], "red"), (DASH["nodust"], "blue"), (DASH["calz00"], "red"), (DASH["calz00"], "blue")] and [w for w, _ in lw] == ["m25n1024", "m50n1024", "m25n1024", "m50n1024"],
      f"{fname}: legend order is m25 no dust (red dashed), m50 no dust (blue dashed), m25 Calzetti00 (red solid), m50 Calzetti00 (blue solid)")
solid = {}
for color, nm, run in ((RED, "m25", "SIMBA-25 (25 Mpc/h box)"), (BLUE, "m50", "SIMBA-50 (50 Mpc/h box)")):
    L = {d: v for d, v in lines_of(page, color)}
    v = L[DASH["calz00"]]
    bars = vbars(page, color)
    pts = []
    for p in v:
        cand = [b for b in bars if abs(b[0] - p.x) < 0.3 and b[1] < p.y < b[2]]
        assert len(cand) == 1, (nm, p.x)
        _, top, bot = cand[0]
        pts.append({"x": round(fx(p.x), 3), "y": round(fy(p.y), 4), "yLow": round(fy(bot), 4), "yHigh": round(fy(top), 4)})
    pts.sort(key=lambda q: q["x"])
    solid[nm] = pts
    check(all(q["yLow"] < q["y"] < q["yHigh"] for q in pts) and len(pts) >= 5, f"{fname}: every vertex of the {run} Calzetti line carries a bar that brackets it ({len(pts)} points)")
    d = dict(COMMON, dustTreatment=LAW["calz00"][0], dustModel=LAW["calz00"][1], xVariable="M_UV (M_1500)", uvBand="rest-frame 1500 A, boxcar 400 A wide")
    records.append(rec(f"wu20.simba.uvbeta.z6.{nm}.calz00", f"{run}, Calzetti00", "uvbeta", AXU, pts, d, f"z = 6, {run}, Calzetti00", fname, "Top panel: beta - M_1500 relations of SIMBA-25 and SIMBA-50", calibB, "scatter",
                       f"UV slope against M_1500 at z = 6 in {run} with the Calzetti law; the bars are the 1 sigma spread of beta within the galaxy sample (the paper's caption); only galaxies with M_UV <= {-16 if nm == 'm25' else -18} enter (the paper's cut for the Calzetti law)."))
# the combined Calzetti curve of the other figure lies inside the two boxes' range where both are drawn (two independent PDFs)
inside = 0
for x, y in curveA["calz00"]:
    vals = [interp([(q["x"], q["y"]) for q in solid[k]], x) for k in ("m25", "m50")]
    vals = [v for v in vals if v is not None]
    if vals:
        assert min(vals) - 0.12 <= y <= max(vals) + 0.12, (x, y, vals)
        inside += 1
check(inside >= 4, f"{fname} against the combined figure: the combined Calzetti curve lies within 0.12 of the range spanned by the two boxes at {inside} of its vertices (two independent PDFs)")

# ================================================================ C. combined beta - stellar mass
fname = "beta-Mstar_extinction.pdf"
page = pymupdf.open(FIG / fname)[0]
fr, fx, fy, calibC = frame_and_axes(page, False, 9, 4)
check(len(calibC["xTicks"]) == 9 and len(calibC["yTicks"]) == 4, f"{fname}: 9 x labels (log M* 7.0 to 11.0) and 4 y labels (beta -1.0 to -2.5) on ticks, residual under 0.002")
lg = legend_lines(page, GREEN)
lw = legend_words(page, {"no", "Salmon16", "Calzetti00", "SMC"}, right=False)
check([d for d, _ in lg] == [DASH["nodust"], DASH["salm16"], DASH["calz00"], DASH["smc"]] and [w for w, _ in lw] == ["no", "Salmon16", "Calzetti00", "SMC"] and all(abs(a[1] - b[1]) < 6 for a, b in zip(lg, lw)),
      f"{fname}: the four legend lines sit beside the labels no dust, Salmon16, Calzetti00, SMC")
ls = {d: v for d, v in lines_of(page, GREEN)}
curveC = {}
for key, dash in DASH.items():
    pts = sorted((round(fx(p.x), 3), round(fy(p.y), 4)) for p in ls[dash] if fr.x0 - 0.5 <= p.x <= fr.x1 + 0.5)
    assert len(pts) >= 8
    curveC[key] = pts
bk = vbars(page, (0.0, 0.0, 0.0))
oc = [(x, y) for x, y in circles(page, fr) if any(abs(b[0] - x) < 0.3 and abs((b[2] - b[1]) - 16.0) > 0.5 and b[2] - b[1] < 100 for b in bk)]   # the legend marker has two bars of 16 pt
f12 = tabs["finkelstein12.uvbetam.z6"]
oc = sorted((fx(x), fy(y)) for x, y in oc)
check(len(oc) == 3 and all(abs(b - tb) < 0.015 for (m, b), (_, tb) in zip(oc, f12)) and all(7 + i < m < 8 + i for i, (m, b) in enumerate(oc)),
      f"{fname}: the three Finkelstein et al. 2012 points (log M* = {', '.join(f'{m:.2f}' for m, _ in oc)}) lie inside the mass bins 7-8, 8-9, 9-10 and their beta ({', '.join(f'{b:.2f}' for _, b in oc)}) reproduces Table 5 of that paper at z = 6 ({', '.join(str(t) for _, t in f12)}) to 0.015")
check(all(a[1] <= b[1] + 0.02 for a, b in zip(curveC["nodust"], curveC["salm16"])) and all(a[1] <= b[1] + 0.02 for a, b in zip(curveC["salm16"], curveC["calz00"])) and all(a[1] <= b[1] + 0.02 for a, b in zip(curveC["calz00"], curveC["smc"])),
      f"{fname}: at every mass the curves are ordered no dust < Salmon16 < Calzetti00 < SMC, the order of their extinction (the paper: the SMC law reddens most, Salmon16 least)")
for key in ("nodust", "calz00", "salm16", "smc"):
    law, lawtxt = LAW[key]
    d = dict(COMMON, dustTreatment=law, dustModel=lawtxt, xVariable="stellar mass", massDefinition="unspecified (galaxies from the Caesar 6-D friends-of-friends finder; the mass aperture is not stated)", uvBand="rest-frame 1500 A, boxcar 400 A wide")
    records.append(rec(f"wu20.simba.uvbetam.z6.combined.{key}", f"SIMBA-25 and SIMBA-50 combined, {NAME[key]}", "uvbetam", AXM, [{"x": x, "y": y} for x, y in curveC[key]], d, f"z = 6, {NAME[key]} (combined)", fname,
                       "Combined beta - stellar mass relations at z = 6", calibC, "unspecified",
                       f"Combined SIMBA-25 and SIMBA-50 UV slope against stellar mass at z = 6, {NAME[key]}; vertices of the plotted line, no error bars. The paper does not restate the M_UV cut for this figure, and its caption says the observations "
                       "'indicate much steeper changes of beta with stellar mass'. The Finkelstein et al. 2012 points drawn in the panel are not extracted here (the table is in the dataset)."))
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} records; {len(checks)} checks passed")
for c in checks:
    print("  ", c)
