"""Nelson et al. 2018 (arXiv:1707.03395): g-r colour of IllustrisTNG / Illustris galaxies at z=0 from vector figures.

  (1) Fig. 2 (figure2_TNG100-1_*.pdf, g-r panel): the four conditional-KDE contours of the TNG100-1 colour-mass plane -> `colour` polygon records;
  (2) Fig. 1 (figure1_*.pdf): normalised (g-r) PDFs of TNG100-1 and Illustris-1 galaxies in 0.5-dex mass bins -> `colour` distribution records;
  (3) Appendix Fig. (appendix2.pdf): TNG100-1 PDFs for dust models A (none), B, C (one random line of sight), C (all 12), D in three mass bins -> distribution records.
The PDFs are Gaussian-KDE curves normalised to unit integral over the plotted colour range, not histograms of counts: they are stored as pseudo-counts
(N_REF per mass bin, relative within a mass bin only) and the weighting field says so.
Usage: python3 -I digitize_tng_colour_nelson18.py [path-to-unpacked-arxiv-source]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
import vector_figure as vf

OUT = HERE.parent / "data" / "staged" / "nelson18-tng-colour-all.json"  # every record the script makes; the ones in the dataset are promoted by hand into data/curves (see data/staged/README.md)
OUT_POLY = HERE.parent / "data" / "staged" / "polygons_nelson18.json"  # exact polygon (vertex-list) form of the contours, kept for reference; it fails the validator rules
ARXIV = "1707.03395"
DOI = "10.1093/mnras/stx3040"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
FIG = SRC / "figures"
COSMO_TNG = {"H0": 67.74, "Om": 0.3089}
N_REF = 100000  # pseudo-counts per mass bin
YEDGES = [round(-0.2 + 0.01 * k, 2) for k in range(141)]  # (g-r) bin edges, -0.2 .. 1.2
MIN_VERTS = 20  # a contour piece with fewer vertices is a sliver at the plot edge
vf.LABEL_MAX = 60

F1 = FIG / "figure1_Illustris-1_TNG100-1_p07c_cf00dust_res_conv_ns1_rad30pkpc_all.pdf"
F2 = FIG / "figure2_TNG100-1_p07c_cf00dust_res_conv_ns1_rad30pkpc.pdf"
FA2 = FIG / "appendix2.pdf"
BLUE = (0.12, 0.47, 0.71)  # TNG100-1 line colour in Figs. 1 and 2
RED = (0.84, 0.15, 0.16)  # Illustris line colour in Fig. 1
GREY = (0.2, 0.2, 0.2)  # SDSS
# Fig. 2: the four contour opacities nest from the outermost (0.05) to the innermost (1.0); caption levels {0.2, 0.5, 0.75, 0.98}
LEVEL_OF_OPACITY = {0.05: 0.2, 0.2: 0.5, 0.5: 0.75, 1.0: 0.98}
MODELS = {  # appendix2.pdf legend colours -> (key, label, dustTreatment)
    (0.55, 0.34, 0.29): ("modelA", "Model A (no dust)", "intrinsic"),
    (0.58, 0.4, 0.74): ("modelB", "Model B (unresolved birth-cloud dust only)", "attenuated (Model B: unresolved birth-cloud dust only)"),
    (0.84, 0.15, 0.16): ("modelC1", "Model C (resolved dust, one random line of sight per galaxy)", "attenuated (Model C: resolved dust, one random line of sight per galaxy)"),
    (0.17, 0.63, 0.17): ("modelCall", "Model C (resolved dust, all 12 projections per galaxy)", "attenuated (Model C: resolved dust, all 12 projections per galaxy)"),
    (0.12, 0.47, 0.71): ("modelD", "Model D (resolved dust, uniform-scattering geometry)", "attenuated (Model D: resolved dust, uniform-scattering geometry)"),
}


def contour_to_band(rec, step=0.05):
    """Closed or open contour polygon -> vertical-envelope band: x on a regular grid (plus the exact end points), y = mid-point, yLow / yHigh = lowest / highest y of the contour at that x.
    The dataset's validator needs x to increase along a connected record and domain = first/last point, which a polygon cannot satisfy; yLow/yHigh bands are the dataset's own representation of an interval."""
    import copy
    P = [(p["x"], p["y"]) for p in rec["representation"]["points"]]
    xmin, xmax = min(p[0] for p in P), max(p[0] for p in P)
    grid = [xmin] + [round(k * step, 6) for k in range(int(np.ceil(xmin / step - 1e-9)), int(np.floor(xmax / step + 1e-9)) + 1) if xmin + 0.5 * step * 0.2 < k * step < xmax - 0.5 * step * 0.2] + [xmax]
    pts, nconc = [], 0
    for x in grid:
        ys = []
        for a, b in zip(P[:-1], P[1:]):
            if abs(a[0] - b[0]) < 1e-9:
                if abs(a[0] - x) < 1e-9:
                    ys += [a[1], b[1]]
            elif min(a[0], b[0]) - 1e-9 <= x <= max(a[0], b[0]) + 1e-9:
                ys.append(a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))
        assert ys, ("no crossing", rec["id"], x)
        lo, hi = min(ys), max(ys)
        nconc += len([1 for u, v in zip(sorted(ys), sorted(ys)[1:]) if v - u > 1e-3]) > 1
        pts.append({"x": round(x, 3), "y": round(0.5 * (lo + hi), 4), "yLow": round(lo, 4), "yHigh": round(hi, 4)})
    xs = [p["x"] for p in pts]
    assert all(b > a for a, b in zip(xs, xs[1:])), rec["id"]
    out = copy.deepcopy(rec)
    out["id"] = rec["id"].replace("contour", "contourband", 1)
    out["run"] = rec["run"].replace("contour", "contour vertical envelope", 1)
    out["representation"] = {"type": "points", "intervalKind": "scatter", "connect": True, "points": pts}
    out["domain"] = {"xMin": xs[0], "xMax": xs[-1]}
    out["selection"]["warning"] = (
        "STORED AS A VERTICAL ENVELOPE (band), not as the polygon: at each x of a regular 0.05-dex grid, yLow and yHigh are the lowest and highest y where the plotted contour path crosses that x "
        "and y is their mid-point (not a median or a ridge). The path vertices were read exactly, then reduced to this band because the dataset requires x to increase along a connected record. "
        "Concavities of the contour are filled by the band (" + str(nconc) + " of " + str(len(pts)) + " grid x values have a crossing gap), and a path that is a single curve in x has zero width. " + rec["selection"]["warning"])
    out["selection"]["contourRepresentation"] = "vertical envelope: y = mid-point, yLow/yHigh = lowest/highest crossing; 0.05-dex x grid"
    out["notes"] = (out.get("notes", "") + " Reduced from the vertex list to a vertical-envelope band (see selection.warning).").strip()
    return out


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


def poly_area(p):
    p = np.asarray(p)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def calibrated_frames(page):
    out = []
    for f in vf.frames(page):
        fx, xt = vf.axis_fit(page, f, "x")
        fy, yt = vf.axis_fit(page, f, "y")
        out.append((f, fx, fy, xt, yt))
    return out


def title_bin(page, f):
    """(lo, hi) of the 'lo < M* < hi' title inside the top of a frame"""
    ws = [w for w in page.get_text("words") if f.x0 <= (w[0] + w[2]) / 2 <= f.x1 and f.y0 - 2 <= w[1] <= f.y0 + 25]
    nums = [float(w[4]) for w in sorted(ws, key=lambda w: w[0]) if re.fullmatch(r"\d+\.\d", w[4])]
    assert len(set(nums)) == 2, nums  # the title is drawn twice in these files
    return min(nums), max(nums)


def pdf_to_counts(pts):
    """polyline (colour, pdf) -> integer pseudo-counts per 0.01-mag bin: N_REF x integral of the PDF over the bin (exact for the piecewise-linear curve on a fine grid)"""
    p = np.array(sorted(pts))
    xg = np.linspace(-0.2, 1.2, 14001)  # 0.0001-mag grid
    yg = np.interp(xg, p[:, 0], np.clip(p[:, 1], 0.0, None))
    cell = 0.5 * (yg[1:] + yg[:-1]) * (xg[1] - xg[0])
    per_bin = cell.reshape(140, 100).sum(axis=1)
    return per_bin, float(cell.sum())


def dist_record(rid, run, source, z, xedges, counts_cols, integrals, axes_y, definitions, warning, citation, figure, panel, sha, member, calib, population):
    counts = [[int(round(N_REF * v)) for v in col] for col in counts_cols]
    rec = {
        "id": rid, "source": source, "run": run, "kind": "simulation", "relation": "colour",
        "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": axes_y, "yUnit": "mag (AB not stated in the paper)"},
        "domain": {"xMin": xedges[0], "xMax": xedges[-1]},
        "representation": {"type": "distribution", "xEdges": xedges, "yEdges": YEDGES, "counts": counts,
                           "weighting": f"pseudo-counts: Gaussian-KDE PDF (unit integral over the plotted range) x {N_REF} per mass bin; relative within a mass bin only, not galaxy numbers",
                           "intervalKind": "scatter"},
        "scatter": None, "selection": {"population": population, "warning": warning}, "definitions": definitions,
        "provenance": {"tier": "digitized-figure", "citation": citation, "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-18", "figure": figure, "panel": panel,
                       "checksumSha256": sha, "sourceMember": member,
                       "extractionMethod": "vector path vertices from the figure PDF (PyMuPDF get_drawings), transformed through axes calibrated on labelled tick marks; PDF polyline integrated per 0.01-mag bin",
                       "axisCalibrationPixels": calib, "digitizationUncertaintyDex": 0.01},
        "calibration": "prediction", "rankable": False,
        "notes": "Vector-path extraction of a normalised PDF curve (not a count histogram); the curve integrals over the plotted colour range are " + ", ".join(f"{v:.3f}" for v in integrals) + " (bin by bin).",
    }
    return rec


records = []
log = []

# ------------------------------------------------------------------ Fig. 1 PDFs
page1 = vf.page_of(F1)
sha1 = vf.sha256(F1)
fr1 = calibrated_frames(page1)
assert len(fr1) == 6
bins1 = []
pdfs = {"tng": [], "ill": [], "tng_cen": None, "ill_cen": None}
for i, (f, fx, fy, xt, yt) in enumerate(fr1):
    assert [v for _, v in xt] == [-0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0], xt  # the 1.2 label sits on the frame edge
    assert abs(fx(f.x0) + 0.2) < 1e-3 and abs(fx(f.x1) - 1.2) < 1e-3 and abs(fy(f.y1)) < 0.01
    bins1.append(title_bin(page1, f))
    cs = vf.curves(page1, f, fx, fy, min_items=6)
    for key, col in (("tng", BLUE), ("ill", RED)):
        solid = [c for c in cs if near(c["color"], col) and c["dashes"] == "[] 0"]
        dashed = [c for c in cs if near(c["color"], col) and c["dashes"] != "[] 0"]
        assert len(solid) == 1, (i, key, len(solid))
        pdfs[key].append(solid[0]["points"])
        if dashed:
            assert i == 0 and len(dashed) == 1
            pdfs[key + "_cen"] = dashed[0]["points"]
assert bins1 == [(9.0, 9.5), (9.5, 10.0), (10.0, 10.5), (10.5, 11.0), (11.0, 11.5), (11.5, 12.0)], bins1
X1 = [9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0]
cols_tng, ints_tng = zip(*[pdf_to_counts(p) for p in pdfs["tng"]])
for v in ints_tng:
    assert abs(v - 1.0) < 0.01, ints_tng  # calibration check: every PDF integrates to 1 over the plotted (g-r) range
cols_ill, ints_ill = zip(*[pdf_to_counts(p) for p in pdfs["ill"]])
good_ill = [k for k, v in enumerate(ints_ill) if abs(v - 1.0) < 0.01]
assert good_ill == [0, 1, 2, 3, 4], (ints_ill, "the Illustris curve of the 11.5-12 bin is clipped by the panel and is not stored")
cen_tng, int_cen_tng = pdf_to_counts(pdfs["tng_cen"])
cen_ill, int_cen_ill = pdf_to_counts(pdfs["ill_cen"])
assert abs(int_cen_tng - 1) < 0.01 and abs(int_cen_ill - 1) < 0.01
log.append(("Fig1 integrals TNG100", [round(v, 3) for v in ints_tng], "Illustris", [round(v, 3) for v in ints_ill], "centrals", round(int_cen_tng, 3), round(int_cen_ill, 3)))

COMMON_DEF = {"imf": "chabrier03", "massDefinition": "unspecified", "population": "all", "colourBand": "SDSS g-r (SDSS u,g,r,i,z passbands at airmass 1.3, galaxy at z=0)",
              "colourAperture": "30 pkpc (3D radius from the subhalo centre)", "resolutionCut": "10^9 < M* < 10^12 Msun (Fig. 1 caption)"}
WARN1 = ("Normalised (g-r) PDF of {what} at z=0 in {nbin} stellar-mass bins of 0.5 dex, read from the vector paths of Nelson et al. 2018 (MNRAS 475, 624), Fig. 1; no table is published. "
         "The curves are one-dimensional Gaussian-kernel-density PDFs ('half-Scott bandwidth of 0.5 N^-1/5', caption) normalised to unit integral over the plotted range -0.2..1.2 mag, not histograms of counts: "
         "they are stored as pseudo-counts ({n} per mass bin) that are meaningful within a mass bin only, and quantiles or fractions read from them are those of the smoothed PDF. "
         "Dust: Model C ('resolved dust') for all galaxies, centrals and satellites. N_side=1 (12 projections); the paper says the main text uses either all 12 colours per galaxy or one random one depending on the application, and does not say which for Fig. 1 "
         "(the TNG100 curves coincide, to within 0.004 in PDF units, with the appendix 'Model C (all)' curves in the three shared mass bins, which points to all 12; this is an inference). {extra}")

records.append(dist_record(
    "nelson18.tng100.colour-pdf.z0.modelC-all12", "TNG100-1 (per galaxy, all galaxies, Model C, KDE PDF)", "IllustrisTNG", 0, X1, cols_tng, ints_tng,
    "(g-r) colour, SDSS passbands, attenuated (Model C resolved dust), per-bin PDF",
    dict(COMMON_DEF, cosmology=COSMO_TNG, dustTreatment="attenuated (Model C: resolved dust; N_side=1, probably all 12 projections per galaxy)"),
    WARN1.format(what="TNG100-1 galaxies (centrals and satellites, 1e9 < M* < 1e12 Msun)", nbin=6, n=N_REF, extra="The Illustris and SDSS curves of the same panels are stored/not stored separately."),
    "Nelson et al. 2018, MNRAS 475, 624 (arXiv:1707.03395), Fig. 1 (distribution of simulated versus observed (g-r) colours)", "Fig. 1 (fig_colors_1d_histos), blue curves", "six mass-bin panels", sha1,
    f"{F1.name} (blue 4 pt stroked curves, 6 panels)", "x: labelled ticks -0.2..1.0 of each panel; y: labelled ticks of each panel (0-8 or 0-6 or 0-10); every PDF integrates to 1.000 +- 0.001", "all galaxies, 1e9-1e12 Msun, z=0"))
records.append(dist_record(
    "nelson18.illustris1.colour-pdf.z0.modelC-all12", "Illustris-1 (per galaxy, all galaxies, Model C, KDE PDF)", "Illustris", 0, X1[:6], list(cols_ill[:5]), list(ints_ill[:5]),
    "(g-r) colour, SDSS passbands, attenuated (Model C resolved dust), per-bin PDF",
    dict(COMMON_DEF, cosmology="unspecified", dustTreatment="attenuated (Model C: resolved dust; N_side=1, all 12 or one random projection, not stated for Fig. 1)"),
    WARN1.format(what="Illustris-1 galaxies (centrals and satellites)", nbin=5, n=N_REF, extra="Only the five mass bins 9-11.5 are stored: the Illustris curve of the 11.5-12 bin runs off the top of the panel (its integral over the visible part is 0.78) and is dropped. The cosmology of Illustris is not stated in this paper."),
    "Nelson et al. 2018, MNRAS 475, 624 (arXiv:1707.03395), Fig. 1 (distribution of simulated versus observed (g-r) colours)", "Fig. 1 (fig_colors_1d_histos), red curves", "five mass-bin panels", sha1,
    f"{F1.name} (red 2 pt stroked curves, panels 1-5)", "x: labelled ticks -0.2..1.0 of each panel; y: labelled ticks of each panel; every stored PDF integrates to 1.000 +- 0.001", "all galaxies, M* from 1e9 Msun, z=0"))
for key, label, cols, ints, simname, cosmo, srcname in (("tng100", "TNG100-1", cen_tng, int_cen_tng, "TNG100-1", COSMO_TNG, "IllustrisTNG"), ("illustris1", "Illustris-1", cen_ill, int_cen_ill, "Illustris-1", "unspecified", "Illustris")):
    records.append(dist_record(
        f"nelson18.{key}.colour-pdf-centrals.z0.modelC-all12", f"{simname} (per galaxy, centrals only, Model C, KDE PDF)", srcname, 0, [9.0, 9.5], [cols], [ints],
        "(g-r) colour, SDSS passbands, attenuated (Model C resolved dust), per-bin PDF",
        dict(COMMON_DEF, cosmology=cosmo, population="centrals", dustTreatment="attenuated (Model C: resolved dust; N_side=1, all 12 or one random projection, not stated for Fig. 1)"),
        WARN1.format(what=f"{simname} central galaxies", nbin=1, n=N_REF, extra="Dotted line of the lowest-mass panel only (the paper decomposes the simulated result into centrals only for 9 < log M* < 9.5)."),
        "Nelson et al. 2018, MNRAS 475, 624 (arXiv:1707.03395), Fig. 1 (lowest-mass panel, centrals only)", "Fig. 1 (fig_colors_1d_histos), dotted curve, panel 9.0 < M* < 9.5", "9.0 < log M* < 9.5, centrals only", sha1,
        f"{F1.name} (dashed curve, panel 1)", "as the all-galaxy records; the PDF integrates to 1.00", "centrals only, 1e9-10^9.5 Msun, z=0"))

# ------------------------------------------------------------------ Fig. 2 contours (g-r panel)
page2 = vf.page_of(F2)
sha2 = vf.sha256(F2)
fr2 = calibrated_frames(page2)
assert len(fr2) == 4
words2 = [w for w in page2.get_text("words")]
f, fx, fy, xt, yt = fr2[1]
assert [v for _, v in xt] == [9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0] and [v for _, v in yt] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0], (xt, yt)
assert any(w[4] == "(g-r)" and f.x0 - 80 < w[0] < f.x0 and f.y0 < w[1] < f.y1 for w in words2), "panel 2 (top right) is the g-r panel"
assert abs(fx(f.x0) - 9.0) < 1e-3 and abs(fx(f.x1) - 12.0) < 1e-3 and abs(fy(f.y1)) < 1e-3 and abs(fy(f.y0) - 1.0) < 1e-3
cs2 = [c for c in vf.curves(page2, f, fx, fy, min_items=6) if c["width"] == 3.0 and near(c["color"], BLUE)]
assert len(cs2) == 11, len(cs2)
by_level = {}
for c in cs2:
    op = round(c["opacity"], 2)
    assert op in LEVEL_OF_OPACITY, op
    by_level.setdefault(LEVEL_OF_OPACITY[op], []).append(c)
assert sorted(by_level) == [0.2, 0.5, 0.75, 0.98]
def cross(pts, x):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        if (a[0] - x) * (b[0] - x) < 0:
            out.append(a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))
    return out


# nesting check: at several masses the lowest crossing moves monotonically outward (down in colour) as the level decreases
for xq in (9.2, 9.5, 9.75, 10.0):
    low = [min(v for c in by_level[lev] for v in cross(c["points"], xq)) for lev in (0.98, 0.75, 0.5, 0.2)]
    assert all(a > b for a, b in zip(low, low[1:])), (xq, low)
    up = [max(v for c in by_level[lev] for v in cross(c["points"], xq) if v < 0.65) for lev in (0.98, 0.75, 0.5)]
    assert all(a < b for a, b in zip(up, up[1:])), (xq, up)

# level check against the Fig. 1 PDF of the same simulation: contour at fraction L of the peak of the conditional PDF
p = np.array(sorted(pdfs["tng"][1]))  # 9.5 < log M* < 10 bin
xg = np.linspace(-0.2, 1.2, 14001)
yg = np.interp(xg, p[:, 0], p[:, 1])
blue = xg < 0.62
pk = yg[blue].max()
checks = []
for lev, c_list in sorted(by_level.items()):
    cr = sorted(v for c in c_list for v in cross(c["points"], 9.75))
    lower = cr[0]
    pred = xg[blue][yg[blue] >= lev * pk].min()
    checks.append((lev, round(lower, 3), round(float(pred), 3)))
    assert abs(lower - pred) < 0.015, (lev, lower, pred)
log.append(("Fig2 level check (lower edge at log M*=9.75 vs Fig.1 PDF at fraction-of-peak level)", checks))
AXES2 = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "(g-r) colour, SDSS passbands, attenuated (Model C resolved dust)", "yUnit": "mag (AB not stated in the paper)"}
nrec2 = 0
for lev in (0.98, 0.75, 0.5, 0.2):
    loops = [c for c in by_level[lev] if len(c["points"]) >= MIN_VERTS]
    nsmall = len(by_level[lev]) - len(loops)
    loops.sort(key=lambda c: -len(c["points"]))
    for k, c in enumerate(loops):
        pts = [(round(float(x), 3), round(float(y), 4)) for x, y in c["points"]]
        ys = [q[1] for q in pts]
        xs = [q[0] for q in pts]
        closed = abs(pts[0][0] - pts[-1][0]) < 2e-3 and abs(pts[0][1] - pts[-1][1]) < 2e-3
        if closed:
            pop = f"closed island at log M* {min(xs):.2f}-{max(xs):.2f}, g-r {min(ys):.2f}-{max(ys):.2f}"
            slug = "island"
        elif max(ys) < 0.65:
            pop, slug = "blue cloud", "blue"
        elif min(ys) > 0.6:
            pop, slug = "red sequence", "red"
        else:
            pop, slug = "open envelope spanning blue cloud and red sequence (g-r %.2f-%.2f)" % (min(ys), max(ys)), "span"
        rec = vf.record(
            rid=f"nelson18.tng100.colour-contour.z0.modelC.l{int(round(lev * 100)):03d}.{slug}{k + 1}", source="IllustrisTNG",
            run=f"TNG100-1 (per galaxy, KDE contour {lev}, {slug} {k + 1})", relation="colour", z=0, axes=AXES2, points=pts,
            population="all TNG100-1 galaxies, 1e9 < M* < 1e12 Msun (centrals and satellites)",
            warning=(f"Vertices of one contour of the conditional 2-D kernel density estimate of the TNG100-1 colour-mass plane, read from the vector paths of Nelson et al. 2018 (MNRAS 475, 624), Fig. 2 (g-r panel, blue lines); no table is published. "
                     f"The caption states 'Conditional 2D kernel density estimates (KDEs) are shown with contours at {{0.2,0.5,0.75,0.98}}'; it does not say what the numbers are. The four drawn opacities (0.05, 0.2, 0.5, 1.0) nest, and the assignment "
                     f"outermost = 0.2 ... innermost = 0.98 is an inference: it reproduces, to within 0.007 mag at the lower edge in all four levels, the contour edges predicted by taking the level as the fraction of the peak of the conditional PDF "
                     f"(Fig. 1 PDF of the same run, mass bin 9.5-10), and reproduces the alternative reading as enclosed probabilities less well (0.01-0.03 mag off); the reading is not proven. "
                     f"This path is the {pop}. {'Closed loop.' if closed else 'Open path: truncated by the plot edge (log M* = 9 or 12).'} Contour pieces with fewer than {MIN_VERTS} vertices (slivers at the plot edge) are not stored ({nsmall} at this level). "
                     f"Dust: Model C resolved dust (N_side=1); whether Fig. 2 uses all 12 projections or one random one is not stated. The SDSS contours (black) and the u-i, u-r, r-i panels are not extracted."),
            definitions=dict(COMMON_DEF, cosmology=COSMO_TNG, dustTreatment="attenuated (Model C: resolved dust; N_side=1, projection choice not stated for Fig. 2)"),
            citation="Nelson et al. 2018, MNRAS 475, 624 (arXiv:1707.03395), Fig. 2 (distribution of observed versus simulated galaxies in the colour-mass plane, g-r panel)", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Fig. 2 (fig_color_mass_2d_4bands), g-r panel", panel="top right, TNG100-1 (blue) contours", sha=sha2, member=f"{F2.name} (3 pt blue stroked contour paths, opacity {1.0 if lev == 0.98 else {0.75: 0.5, 0.5: 0.2, 0.2: 0.05}[lev]})",
            calib="x: labelled ticks 9.0-12.0 of the g-r panel; y: labelled ticks 0.0-1.0; frame asserted at log M* 9-12 and g-r 0-1", calibration="prediction", interval="scatter", connect=True, strict=False, uncertainty=0.01, retrieved="2026-10-18",
            note="Vector-path extraction of a density contour; the loop is the plotted line.")
        rec["domain"] = {"xMin": min(xs), "xMax": max(xs)}
        rec["selection"].update({"contourLevel": lev, "contourKind": "level of the conditional 2-D KDE as listed in the caption; read as a fraction of the per-mass peak density (inferred, see warning)", "contourClosed": bool(closed), "contourRegion": pop})
        records.append(rec)
        nrec2 += 1
log.append(("Fig2 contour records", nrec2))

# ------------------------------------------------------------------ Appendix: dust models
pagea = vf.page_of(FA2)
shaa = vf.sha256(FA2)
fra = calibrated_frames(pagea)
assert len(fra) == 3
binsA = [title_bin(pagea, fa[0]) for fa in fra]
assert binsA == [(9.5, 10.0), (10.0, 10.5), (10.5, 11.0)], binsA
# legend: line colours listed top to bottom must be SDSS, D, C(all), C, B, A
leg = sorted(((d["rect"].y0, tuple(round(v, 2) for v in d["color"])) for d in pagea.get_drawings() if d["type"] == "s" and len(d["items"]) == 1 and d["width"] >= 2.5 and d["rect"].width > 30 and d["rect"].y0 < 220), key=lambda t: t[0])
assert [c for _, c in leg] == [GREY, BLUE, (0.17, 0.63, 0.17), RED, (0.58, 0.4, 0.74), (0.55, 0.34, 0.29)], leg
words_leg = {w[4] + str(round(w[1])): w for w in pagea.get_text("words") if w[1] < 220 and w[0] > 330}
lab = [w for w in sorted(pagea.get_text("words"), key=lambda w: w[1]) if w[1] < 200 and w[0] > 330 and w[4] in ("SDSS", "Model")]
assert [w[4] for w in lab] == ["SDSS", "Model", "Model", "Model", "Model", "Model"]
legtext = []
for w in lab:
    line = [x[4] for x in sorted(pagea.get_text("words"), key=lambda x: x[0]) if abs(x[1] - w[1]) < 3 and x[0] > 330]
    legtext.append(" ".join(line))
assert legtext == ["SDSS z<0.1", "Model D", "Model C (all)", "Model C", "Model B", "Model A"], legtext
perbin = {k: [] for k in MODELS}
for i, (f, fx, fy, xt, yt) in enumerate(fra):
    assert abs(fx(f.x0) + 0.2) < 1e-3 and abs(fx(f.x1) - 1.2) < 1e-3
    cs = vf.curves(pagea, f, fx, fy, min_items=6)
    sdss = [c for c in cs if near(c["color"], GREY)]
    # the SDSS curve of this panel equals the SDSS curve of the corresponding Fig. 1 panel (identification of the mass bin)
    s1 = np.array(sorted(sdss[0]["points"]))
    f1 = fr1[i + 1]
    c1 = [c for c in vf.curves(page1, f1[0], f1[1], f1[2], min_items=6) if near(c["color"], GREY)][0]
    s2 = np.array(sorted(c1["points"]))
    assert abs(s1[:, 1].max() - s2[:, 1].max()) < 0.02, (i, s1[:, 1].max(), s2[:, 1].max())
    for col in MODELS:
        cc = [c for c in cs if near(c["color"], col)]
        assert len(cc) == 1, (i, col, len(cc))
        counts, integ = pdf_to_counts(cc[0]["points"])
        assert abs(integ - 1.0) < 0.01, (i, col, integ)
        perbin[col].append((counts, integ, cc[0]["points"]))
# consistency: Fig. 1 TNG100 curve == appendix 'Model C (all)' curve in the three shared bins
maxdiff = 0.0
for i in range(3):
    a = np.array(sorted(pdfs["tng"][i + 1]))
    b = np.array(sorted(perbin[(0.17, 0.63, 0.17)][i][2]))
    xg = np.linspace(-0.2, 1.2, 1401)
    maxdiff = max(maxdiff, float(np.abs(np.interp(xg, a[:, 0], a[:, 1]) - np.interp(xg, b[:, 0], b[:, 1])).max()))
assert maxdiff < 0.15, maxdiff
log.append(("Fig1 TNG100 vs appendix Model C (all): max |dPDF| over the three shared bins", round(maxdiff, 3)))
for col, (key, label, dust) in MODELS.items():
    cols = [perbin[col][i][0] for i in range(3)]
    ints = [perbin[col][i][1] for i in range(3)]
    records.append(dist_record(
        f"nelson18.tng100.colour-pdf.z0.{key}", f"TNG100-1 (per galaxy, all galaxies, {label}, KDE PDF)", "IllustrisTNG", 0, [9.5, 10.0, 10.5, 11.0], cols, ints,
        f"(g-r) colour, SDSS passbands, {'intrinsic (no dust)' if key == 'modelA' else 'attenuated'} ({label}), per-bin PDF",
        dict(COMMON_DEF, cosmology=COSMO_TNG, dustTreatment=dust),
        (f"Normalised (g-r) PDF of TNG100-1 galaxies at z=0 in the three 0.5-dex mass bins 9.5-10, 10-10.5, 10.5-11, {label}, read from the vector paths of the dust-model comparison figure of Nelson et al. 2018 (MNRAS 475, 624), Appendix (fig_dust_model_comparison); no table is published. "
         f"The curves are Gaussian-KDE PDFs normalised to unit integral over -0.2..1.2 mag, not histograms of counts: stored as pseudo-counts ({N_REF} per mass bin; relative within a mass bin only). "
         "Caption: Model A 'includes the stellar population synthesis modeling with no dust treatment'; Model B 'includes only the unresolved presence of dense birth clouds'; Model C 'includes the resolved dust column calculations with one random line of sight per galaxy ... or all twelve projections'; Model D 'uses a different dust geometry assumption'. "
         "Galaxies of the full TNG100-1 population (centrals and satellites)."),
        "Nelson et al. 2018, MNRAS 475, 624 (arXiv:1707.03395), Appendix figure: building up the dust model (Models A-D)", "Appendix fig_dust_model_comparison", f"three mass-bin panels, {label}", shaa,
        f"{FA2.name} (3 pt stroked curve, legend colour {col})", "x: labelled ticks -0.2..1.0 of each panel; y: labelled ticks of each panel; every PDF integrates to 1.000 +- 0.001; mass bin identified by the SDSS curve identical to the corresponding Fig. 1 panel",
        "all galaxies, 10^9.5-10^11 Msun, z=0"))

ids = [r["id"] for r in records]
assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
keys = [(r["source"], r["run"], r["relation"], r["epoch"]["zRepresentative"]) for r in records]
assert len(keys) == len(set(keys))
polys = [r for r in records if r["representation"]["type"] == "points"]
final = [contour_to_band(r) if r["representation"]["type"] == "points" else r for r in records]
OUT_POLY.write_text(json.dumps({"schemaVersion": "1.0.0", "records": polys}, indent=2) + "\n")
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": final}, indent=2) + "\n")
for l in log:
    print(l)
print(f"Wrote {len(final)} records to {OUT} ({len(polys)} contours as bands; polygons in {OUT_POLY})")
