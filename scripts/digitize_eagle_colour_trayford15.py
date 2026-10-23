"""Trayford et al. 2015 (arXiv:1504.04374): rest-frame g-r colour distributions of EAGLE galaxies at z=0.1 from vector histograms.

  (1) Appendix Fig. B1 (FigB1a.pdf): histograms of COUNTS per colour bin of Ref-L0100N1504, Ref-L0025N0376 and Recal-L0025N0752 galaxies with
      9.45 < log M* <= 10.05 -> three `colour` distribution records with integer counts (weighting "number");
  (2) Fig. 2 (Fig2_a..d.pdf): histograms normalised to unit integral in four mass bins for the dust models N (none), GI, GD, GD+O -> single-mass-bin
      distribution records stored as pseudo-counts (the figure gives no galaxy numbers).
The Fig. 3 colour-mass diagrams (Fig3a.png, Fig3b.png) are PNG rasters and are not usable.
Usage: python3 -I digitize_eagle_colour_trayford15.py [path-to-unpacked-arxiv-source]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
import vector_figure as vf

OUT = HERE.parent / "data" / "staged" / "trayford15-eagle-colour-all.json"  # every record the script makes; the ones in the dataset are promoted by hand into data/curves (see data/staged/README.md)
ARXIV = "1504.04374"
DOI = "10.1093/mnras/stv1985"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
FIG = SRC / "finalfigs"
COSMO = {"H0": 67.77, "Om": 0.307}  # h = 0.6777, Omega_b + Omega_dark = 0.0482 + 0.2588 (Simulations.tex)
N_REF = 100000
vf.LABEL_MAX = 60
RED = (0.8, 0.4, 0.47)
BLUEC = (0.27, 0.47, 0.67)
MODELS = {"a": ("N", "model N: no dust", "intrinsic"), "b": ("GI", "model GI: galaxy-independent dust", "attenuated (model GI: galaxy-independent dust)"),
          "c": ("GD", "model GD: dust depends on gas fraction and metallicity", "attenuated (model GD: dust optical depth depends on gas fraction and metallicity)"),
          "d": ("GD+O", "model GD+O: GD plus orientation effects (q=0.2)", "attenuated (model GD+O: GD plus orientation effects, fiducial q=0.2)")}
log = []
records = []


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


def steps(raw):
    """a step-histogram path -> (edges, heights); horizontal segments must tile the x range"""
    pts = [(p.x, p.y) for p in raw]
    segs = [(min(a[0], b[0]), max(a[0], b[0]), a[1]) for a, b in zip(pts[:-1], pts[1:]) if abs(a[1] - b[1]) < 1e-6 and abs(a[0] - b[0]) > 1e-6]
    segs.sort()
    for s, t in zip(segs, segs[1:]):
        assert abs(s[1] - t[0]) < 1e-3, ("gap in step path", s, t)
    return segs


def dist_record(rid, run, source, xedges, yedges, counts, weighting, axes_y, definitions, warning, citation, figure, panel, sha, member, calib, population, notes):
    return {
        "id": rid, "source": source, "run": run, "kind": "simulation", "relation": "colour",
        "epoch": {"zRepresentative": 0.1, "zNominal": 0.1, "zMin": 0.1, "zMax": 0.1, "mode": "published-epoch", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": axes_y, "yUnit": "mag (AB)"},
        "domain": {"xMin": xedges[0], "xMax": xedges[-1]},
        "representation": {"type": "distribution", "xEdges": xedges, "yEdges": yedges, "counts": counts, "weighting": weighting, "intervalKind": "scatter"},
        "scatter": None, "selection": {"population": population, "warning": warning}, "definitions": definitions,
        "provenance": {"tier": "digitized-figure", "citation": citation, "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": "2026-10-18", "figure": figure, "panel": panel,
                       "checksumSha256": sha, "sourceMember": member,
                       "extractionMethod": "vector path vertices from the figure PDF (PyMuPDF get_drawings): horizontal segments of the step histogram, transformed through axes calibrated on labelled tick marks",
                       "axisCalibrationPixels": calib, "digitizationUncertaintyDex": 0.01},
        "calibration": "prediction", "rankable": False, "notes": notes,
    }


DEFS = {"imf": "chabrier03", "cosmology": COSMO, "massDefinition": "unspecified", "population": "all",
        "colourBand": "rest-frame SDSS g-r (ugriz photometric system of the paper, AB magnitudes)", "colourAperture": "30 pkpc (3D sphere centred on the subhalo potential minimum)",
        "resolutionCut": "galaxies with at least 100 star particles"}

# ------------------------------------------------------------------ (1) Appendix Fig. B1: counts
pdfB = FIG / "FigB1a.pdf"
pageB = vf.page_of(pdfB)
shaB = vf.sha256(pdfB)
fr = vf.frames(pageB)
assert len(fr) == 1
f = fr[0]
words = pageB.get_text("words")
left = [((w[1] + w[3]) / 2, float(w[4])) for w in words if re.fullmatch(r"\d+", w[4]) and w[2] < f.x0 and f.y0 - 3 <= (w[1] + w[3]) / 2 <= f.y1 + 3]
right = [((w[1] + w[3]) / 2, float(w[4])) for w in words if re.fullmatch(r"\d+", w[4]) and w[0] > f.x1 and f.y0 - 3 <= (w[1] + w[3]) / 2 <= f.y1 + 3]
fx, xt = vf.axis_fit(pageB, f, "x")
fyl, yl = vf.axis_fit(pageB, f, "y", labels=left)
fyr, yr = vf.axis_fit(pageB, f, "y", labels=right)
assert [v for _, v in xt] == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], xt
assert sorted(v for _, v in yl) == [0.0, 200.0, 400.0, 600.0, 800.0, 1000.0, 1200.0] and sorted(v for _, v in yr) == [0.0, 5.0, 10.0, 15.0], (yl, yr)
tw = [w[4] for w in words]
assert "9.45" in tw and "10.05" in tw and "Ref-100" in tw and "Ref-25" in tw and "Recal-25" in tw
# the left (blue, Ref-100) axis is 64 times the right (red, 25 Mpc boxes) axis, as the caption says
for ypix in (f.y0 + 20.0, f.y0 + 100.0, f.y1 - 5.0):
    assert abs(fyl(ypix) / 64.0 - fyr(ypix)) < 0.01 * max(1.0, fyr(ypix)) + 0.02, (ypix, fyl(ypix), fyr(ypix))
curves = vf.curves(pageB, f, fx, fyl, min_items=3)
assert len(curves) == 3
SPEC = {"Ref-100": (BLUEC, "[] 0", fyl, "Ref-L0100N1504", "EAGLE Ref-L0100N1504", "ref100"),
        "Ref-25": (RED, "[ 6 6 ] 0", fyr, "Ref-L0025N0376", "EAGLE Ref-L0025N0376", "ref25"),
        "Recal-25": (RED, "[] 0", fyr, "Recal-L0025N0752", "EAGLE Recal-L0025N0752", "recal25")}
totals = {}
for key, (col, dash, fy, simname, label, slug) in SPEC.items():
    c = [c for c in curves if near(c["color"], col) and c["dashes"] == dash]
    assert len(c) == 1, (key, len(c))
    segs = steps(c[0]["raw"])
    edges = [fx(s[0]) for s in segs] + [fx(segs[-1][1])]
    vals = [fy(s[2]) for s in segs]
    # integrality: counts must be integers (Ref-25 and Recal-25 are 12 pixels per count, a strict test of the axis calibration)
    dev = max(abs(v - round(v)) for v in vals)
    assert dev < (0.05 if fy is fyr else 0.05), (key, dev)
    counts = [int(round(v)) for v in vals]
    assert min(counts) >= 0
    # keep the bins inside the plotted range 0 .. 1.2 mag and assert nothing is lost outside
    keep = [i for i in range(len(counts)) if edges[i] >= -0.1 - 1e-6 and edges[i + 1] <= 1.2 + 1e-6]
    assert all(counts[i] == 0 for i in range(len(counts)) if i not in keep), key
    e = [round(edges[i], 4) for i in keep] + [round(edges[keep[-1] + 1], 4)]
    cnt = [counts[i] for i in keep]
    totals[key] = (sum(cnt), dev)
    records.append(dist_record(
        f"trayford15.eagle-{slug}.colour-counts.z0p1.m9p45-10p05", f"{simname} (per galaxy counts, 9.45 < log M* <= 10.05)", "EAGLE", [9.45, 10.05], e, [cnt],
        "number", "rest-frame (g-r) colour (SDSS g and r bands, AB), dust model not stated for this appendix figure",
        dict(DEFS, dustTreatment="unspecified (appendix figure on colour convergence; the dust model is not named in the appendix text or caption)"),
        (f"Counts per colour bin of the galaxies of {label} with 9.45 < log10(M*/Msun) <= 10.05 at z = 0.1 (rest-frame g-r), read from the step histogram of Trayford et al. 2015 (MNRAS 452, 2879), Appendix Fig. B1 (top panel); no table is published. "
         f"These are galaxy numbers per colour bin (integers, verified): Ref-100 on the left axis, the two 25-Mpc boxes on the right axis (range 1/64 of the left one for the box volume). "
         f"The sum over the bins is {sum(cnt)} galaxies. The bottom panel of the paper's figure (8.7 < log M* <= 9.3) is not in the arXiv source: FigB1b.pdf duplicates the 9.45-10.05 panel. The paper does not state which dust model the histograms use. "
         "Colour bins are about 0.0438 mag wide."),
        "Trayford et al. 2015, MNRAS 452, 2879 (arXiv:1504.04374), Appendix Fig. B1 (colour convergence: Ref-100, Ref-25, Recal-25)", "Fig. B1 (fig:conv), top panel", f"{simname}, 9.45 < log M* <= 10.05", shaB,
        f"{pdfB.name} (step-histogram path, {'solid blue' if key == 'Ref-100' else ('dashed red' if key == 'Ref-25' else 'solid red')})",
        "x: labelled ticks 0.0-1.0; y: labelled ticks of the left axis (0-1200) and right axis (0-15); both fits snapped to ticks; counts are integers to within 0.05; left axis = 64 x right axis asserted",
        "all galaxies with M* in the bin, at least 100 star particles", "Vector-path extraction of a count histogram; integer counts."))
log.append(("B1 counts (sum, max deviation from integers)", totals))
n100, n25 = totals["Ref-100"][0], totals["Ref-25"][0]
log.append(("B1 volume check: Ref-100 total / 64 vs Ref-25 total", round(n100 / 64.0, 1), n25))
assert abs(n100 / 64.0 - n25) < 3 * np.sqrt(n25)  # Poisson-consistent with the volume ratio 4^3 = 64

# ------------------------------------------------------------------ (2) Fig. 2: normalised histograms, four mass bins
ref_by_model = {}
for panelkey, (mkey, mlabel, dust) in MODELS.items():
    pdf = FIG / f"Fig2_{panelkey}.pdf"
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    frs = vf.frames(page)
    assert len(frs) == 4
    fxb, xt = vf.axis_fit(page, frs[-1], "x")
    assert [v for _, v in xt] == [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], xt
    for fr_ in frs:
        assert abs(fr_.x0 - frs[0].x0) < 0.5 and abs(fr_.x1 - frs[0].x1) < 0.5
    words = page.get_text("words")
    for i, fr_ in enumerate(frs):
        fy, yt = vf.axis_fit(page, fr_, "y")
        # mass bin from the title 'lo < log10(M*/Msun) <= hi'
        tw = sorted((w for w in words if fr_.x0 <= w[0] <= fr_.x1 and fr_.y0 <= w[1] < fr_.y0 + 8), key=lambda w: w[0])
        toks = [w[4] for w in tw]
        hi = [float(t[1:]) for t in toks if t.startswith("≤") and len(t) > 1][0]
        lo = [float(toks[j - 1]) for j, t in enumerate(toks) if t == "<" and re.fullmatch(r"\d+(\.\d+)?", toks[j - 1])][0]
        assert (lo, hi) == [(11.2, 11.5), (10.5, 10.8), (9.8, 10.1), (8.7, 9.0)][i], (panelkey, i, lo, hi)
        cands = []
        for c in vf.curves(page, fr_, fxb, fy, min_items=3):
            ys = [p.y for p in c["raw"]]
            if min(ys) < fr_.y0 - 0.5 or max(ys) > fr_.y1 + 0.5:
                continue
            cands.append(c)
        # panel a (model N) draws its histograms dashed; panels b-d draw the model solid (width 2) and repeat model N dashed (width 1)
        if panelkey == "a":
            specs = (("Ref-100", (0.0, 0.0, 0.0), "[ 6 6 ] 0", 1.0), ("Recal-25", RED, "[ 6 6 ] 0", 1.0))
        else:
            specs = (("Ref-100", (0.0, 0.0, 0.0), "[] 0", 2.0), ("Recal-25", RED, "[] 0", 2.0), ("Ref-100 N", (0.0, 0.0, 0.0), "[ 6 6 ] 0", 1.0), ("Recal-25 N", RED, "[ 6 6 ] 0", 1.0))
        for kind, col, dash, width in specs:
            sel = [c for c in cands if near(c["color"], col) and c["dashes"] == dash and c["width"] == width]
            if kind.startswith("Recal") and i != 3:
                assert not sel
                continue
            assert len(sel) == 1, (panelkey, i, kind, len(sel))
            segs = steps(sel[0]["raw"])
            edges = [fxb(s[0]) for s in segs] + [fxb(segs[-1][1])]
            hts = [fy(s[2]) for s in segs]
            integ = sum(h * (edges[k + 1] - edges[k]) for k, h in enumerate(hts))
            assert abs(integ - 1.0) < 0.01, (panelkey, i, kind, integ)  # calibration: unit integral
            ref_by_model[(panelkey, i, kind)] = (edges, hts)
log.append(("Fig2 histograms read", len(ref_by_model), "all integrate to 1.000 +- 0.01"))
# dashed model-N histograms repeated in panels b-d must equal the solid model-N histograms of panel a
maxd = 0.0
for i in range(4):
    for kind in ("Ref-100",) + (("Recal-25",) if i == 3 else ()):
        ea, ha = ref_by_model[("a", i, kind)]
        for pk in "bcd":
            eb, hb = ref_by_model[(pk, i, kind + " N")]
            assert len(ea) == len(eb) and np.allclose(ea, eb, atol=2e-3), (pk, i, kind)
            maxd = max(maxd, float(np.abs(np.array(ha) - np.array(hb)).max()))
assert maxd < 0.02, maxd
log.append(("Fig2 dashed N histograms in b-d vs solid histograms of panel a, max |dheight|", round(maxd, 4)))
BINS = [(11.2, 11.5), (10.5, 10.8), (9.8, 10.1), (8.7, 9.0)]
WARN2 = ("Normalised histogram of the rest-frame g-r colours of {sim} galaxies at z = 0.1 with {lo} < log10(M*/Msun) <= {hi}, {mlabel}, read from the step histogram of Trayford et al. 2015 (MNRAS 452, 2879), Fig. 2 (panel {pk}, mass bin {lo}-{hi}); no table is published. "
         "The paper says 'All models are shown as histograms, normalised to have unit integral': the figure gives no galaxy numbers, so the record stores pseudo-counts (height x bin width x {n}; only the shape within the mass bin is meaningful). "
         "The mass bins of the figure are four non-contiguous 0.3-dex ranges, hence one record per bin. {extra}")
for panelkey, (mkey, mlabel, dust) in MODELS.items():
    sha = vf.sha256(FIG / f"Fig2_{panelkey}.pdf")
    for i, (lo, hi) in enumerate(BINS):
        for kind, simname, slug, label in (("Ref-100", "Ref-L0100N1504", "ref100", "EAGLE Ref-L0100N1504 (fiducial)"), ("Recal-25", "Recal-L0025N0752", "recal25", "EAGLE Recal-L0025N0752")):
            if kind == "Recal-25" and i != 3:
                continue
            edges, hts = ref_by_model[(panelkey, i, kind)]
            keep = [k for k in range(len(hts)) if edges[k] >= -0.1 - 0.05 and edges[k + 1] <= 1.2 + 0.05]
            assert all(abs(hts[k]) < 1e-3 for k in range(len(hts)) if k not in keep), (panelkey, i, kind, "mass outside the plotted range", [(round(edges[k], 3), round(hts[k], 4)) for k in range(len(hts)) if k not in keep and abs(hts[k]) >= 1e-3])
            e = [round(edges[k], 4) for k in keep] + [round(edges[keep[-1] + 1], 4)]
            counts = [int(round(N_REF * hts[k] * (edges[k + 1] - edges[k]))) for k in keep]
            tag = f"m{str(lo).replace('.', 'p')}-{str(hi).replace('.', 'p')}"
            records.append(dist_record(
                f"trayford15.eagle-{slug}.colour-hist.z0p1.{mkey.lower().replace('+', '-')}.{tag}", f"{simname} (per galaxy, normalised histogram, {mkey}, {lo} < log M* <= {hi})", "EAGLE", [lo, hi], e, [counts],
                f"pseudo-counts: unit-integral histogram x {N_REF} per mass bin; relative within the mass bin only, not galaxy numbers",
                f"rest-frame (g-r) colour (SDSS g and r bands, AB), {mlabel}",
                dict(DEFS, dustTreatment=dust),
                WARN2.format(sim=label, lo=lo, hi=hi, mlabel=mlabel, pk=panelkey, n=N_REF,
                             extra=("Recal-25 is shown only in the lowest mass bin of the figure. " if kind == "Recal-25" else "") + "Dashed (model N) and observed GAMA lines of the same panel are not part of this record."),
                "Trayford et al. 2015, MNRAS 452, 2879 (arXiv:1504.04374), Fig. 2 (g-r colour distributions for four dust models in four stellar-mass bins)", f"Fig. 2 (fig:cmddev), panel {panelkey} ({mkey})", f"mass bin {lo}-{hi}", sha,
                f"Fig2_{panelkey}.pdf (2 pt solid {'black' if kind == 'Ref-100' else 'red'} step histogram)",
                "x: labelled ticks 0.0-1.0 of the bottom panel (all four panels share the x axis, frame edges asserted equal); y: labelled ticks of each panel; every histogram integrates to 1.000 +- 0.01",
                "all galaxies with M* in the bin at z=0.1", f"Vector-path extraction of a unit-integral histogram (integral {sum(h * (edges[k + 1] - edges[k]) for k, h in enumerate(hts)):.3f})."))

ids = [r["id"] for r in records]
assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
keys = [(r["source"], r["run"], r["relation"], r["epoch"]["zRepresentative"]) for r in records]
assert len(keys) == len(set(keys))
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
for l in log:
    print(l)
print(f"Wrote {len(records)} records to {OUT}")
