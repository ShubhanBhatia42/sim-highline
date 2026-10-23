"""Donnari et al. 2019 (arXiv:1812.07584): density contours of the SFR-M* plane of IllustrisTNG galaxies (vector paths).

Each contour level (20, 50, 70, 90, 99 per cent of the galaxies, as stated in the figure captions) of each panel is stored as its own
`sfms` record: one record per closed or open loop, vertices in the order drawn (connect: true). The 2-D histogram under the contours is a
raster image and is not extracted.
Usage: python3 -I digitize_tng_sfms_contours_donnari19.py [path-to-unpacked-arxiv-source]
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np
import vector_figure as vf

OUT = HERE.parent / "data" / "staged" / "m2-donnari19-sfms-contour-bands.json"  # every record the script makes; the ones in the dataset are promoted by hand into data/curves (see data/staged/README.md)
OUT_POLY = HERE.parent / "data" / "staged" / "polygons_donnari19.json"  # exact polygon (vertex-list) form of the contours, kept for reference; it fails the validator rules
ARXIV = "1812.07584"
DOI = "10.1093/mnras/stz712"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
COSMO = {"H0": 67.74, "Om": 0.3089}
LEVELS = [99, 90, 70, 50, 20]  # outermost to innermost; line colours are viridis, G channel increases with decreasing enclosed fraction
AREA_MIN = {99: 0.05, 90: 0.02, 70: 0.02, 50: 0.02, 20: 0.02}  # dex^2 of the polygon (a loop is dropped below this; a cell of the 200x200 histogram is 5.7e-4 dex^2; the 99% level is noisy, so its islands need 0.05)
BAND_PANELS = {"TNG300_z0", "TNG300_z2", "TNG300_z0_200Myr", "TNG300_z2_200Myr"}  # unresolved-band loops are stored for the four main-text panels only
BAND_TOP = -3.5  # loops entirely below this log SFR are the unresolved (SFR = 0 -> random 1e-5..1e-4) band
# file stem, simulation run, z, SFR timescale (Myr or "instantaneous"), SFR_min stated in the text (log Msun/yr), where it is stated, figure label
PANELS = [
    ("TNG300_z0", "TNG300-1", 0, "instantaneous", -3.0, "Appendix A: 'lowest SFR measurable values ... ~ -3 for TNG300' (instantaneous)", "Fig. SFR-MSTAR (top left)"),
    ("TNG300_z2", "TNG300-1", 2, "instantaneous", -3.0, "Appendix A: 'lowest SFR measurable values ... ~ -3 for TNG300' (instantaneous)", "Fig. SFR-MSTAR (top right)"),
    ("TNG300_z0_200Myr", "TNG300-1", 0, 200, -1.9, "Appendix A: TNG300 SFR_min -1.9 for 200 Myr", "Fig. SFR-MSTAR (bottom left) = Fig. SFR-MSTAR_timescales (200 Myr, TNG300)"),
    ("TNG300_z2_200Myr", "TNG300-1", 2, 200, -1.9, "Appendix A: TNG300 SFR_min -1.9 for 200 Myr (z=0 value; text gives no z=2 value)", "Fig. SFR-MSTAR (bottom right)"),
    ("TNG300_z0_10Myr", "TNG300-1", 0, 10, -0.6, "Appendix A: TNG300 SFR_min -0.6 for 10 Myr", "Fig. SFR-MSTAR_timescales (10 Myr, TNG300)"),
    ("TNG300_z0_50Myr", "TNG300-1", 0, 50, -1.3, "Appendix A: TNG300 SFR_min -1.3 for 50 Myr", "Fig. SFR-MSTAR_timescales (50 Myr, TNG300)"),
    ("TNG300_z0_1000Myr", "TNG300-1", 0, 1000, -2.6, "Appendix A: TNG300 SFR_min -2.6 for 1000 Myr", "Fig. SFR-MSTAR_timescales (1000 Myr, TNG300)"),
    ("TNG100_z0_10Myr", "TNG100-1", 0, 10, -1.15, "Appendix A: TNG100 SFR_min -1.15 for 10 Myr", "Fig. SFR-MSTAR_timescales (10 Myr, TNG100)"),
    ("TNG100_z0_50Myr", "TNG100-1", 0, 50, -1.85, "Appendix A: TNG100 SFR_min -1.85 for 50 Myr", "Fig. SFR-MSTAR_timescales (50 Myr, TNG100)"),
    ("TNG100_z0_200Myr", "TNG100-1", 0, 200, -2.46, "Appendix A: TNG100 SFR_min -2.46 for 200 Myr", "Fig. SFR-MSTAR_timescales (200 Myr, TNG100)"),
    ("TNG100_z0_1000Myr", "TNG100-1", 0, 1000, -3.15, "Appendix A: TNG100 SFR_min -3.15 for 1000 Myr", "Fig. SFR-MSTAR_timescales (1000 Myr, TNG100)"),
]
# Main-sequence normalisation of TNG300 (Table tab:table_ms, linear fit log SFR = alpha log M* + beta, 200 Myr, 2 R_h, UVJ-selected star forming)
MS_TABLE = {0: (0.80, -8.15), 2: (0.77, -6.83)}


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


def poly_area(p):
    p = np.asarray(p)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def load_panel(path):
    page = vf.page_of(path)
    fr = vf.frames(page)
    assert len(fr) == 1, fr
    f = fr[0]
    fx, xt = vf.axis_fit(page, f, "x")
    assert [v for _, v in xt] == [9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0], xt
    # the minus signs of the y labels are not in the text layer: the labels read 5,4,3,2,1,0,1,2 from bottom to top and are the values -5..2
    words = [w for w in page.get_text("words") if re.fullmatch(r"\d", w[4]) and w[2] < f.x0 and f.y0 - 3 <= (w[1] + w[3]) / 2 <= f.y1 + 3]
    words.sort(key=lambda w: -(w[1] + w[3]) / 2)
    assert [w[4] for w in words] == ["5", "4", "3", "2", "1", "0", "1", "2"], [w[4] for w in words]
    ylab = [((w[1] + w[3]) / 2, float(v)) for w, v in zip(words, range(-5, 3))]
    fy, yt = vf.axis_fit(page, f, "y", labels=ylab)
    assert sorted(v for _, v in yt) == [float(v) for v in range(-5, 3)], yt
    assert abs(fx(f.x0) - 9.0) < 1e-3 and abs(fx(f.x1) - 12.0) < 1e-3 and abs(fy(f.y1) + 5.1) < 0.01 and abs(fy(f.y0) - 2.5) < 0.01
    return page, f, fx, fy


def cross(pts, x):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        if (a[0] - x) * (b[0] - x) < 0:
            out.append(a[1] + (x - a[0]) / (b[0] - a[0]) * (b[1] - a[1]))
    return out


records = []
summary = []
pdf_sha = {}
for stem, run, z, tscale, smin, smin_src, figlabel in PANELS:
    pdf = SRC / f"{stem}.pdf"
    page, f, fx, fy = load_panel(pdf)
    sha = vf.sha256(pdf)
    words = [w[4] for w in page.get_text("words")]
    assert run.split("-")[0] in words and f"z={z}" in words, (stem, words[:60])
    if tscale == "instantaneous":
        # the z=2 panel carries no timescale label in the file; it is the top-right panel of Fig. SFR-MSTAR (caption: top panels = instantaneous gas SFR)
        assert ("Instantaneous" in words) if z == 0 else ("Timescale" not in words and "Instantaneous" not in words), stem
    elif z == 0:
        assert "Myr" in words and str(tscale) in words, (stem, tscale)
    else:  # z=2 200 Myr: unlabelled in the file; bottom-right panel of Fig. SFR-MSTAR (caption: bottom panels = last 200 Myr)
        assert "Myr" not in words and "Instantaneous" not in words, stem
    # dashed horizontal resolution line vs the SFR_min stated in the text
    lines = [d for d in page.get_drawings() if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and d.get("dashes") not in (None, "[] 0") and d["rect"].width > 200]
    assert len(lines) == 1, (stem, len(lines))
    yres = fy(lines[0]["rect"].y0)
    assert abs(yres - smin) < 0.4, (stem, yres, smin)
    curves = [c for c in vf.curves(page, f, fx, fy, min_items=2) if c["width"] == 3.0]
    colours = sorted({c["color"] for c in curves}, key=lambda c: c[1])  # G channel increases along viridis
    assert len(colours) == 5, (stem, colours)
    per_level = {}
    for lev, col in zip(LEVELS, colours):
        loops = [c for c in curves if c["color"] == col]
        keep = [c for c in loops if poly_area(c["points"]) >= AREA_MIN[lev]]
        per_level[lev] = (col, keep, len(loops) - len(keep))
    # nesting: total polygon area must shrink with the enclosed fraction
    tot = [sum(poly_area(c["points"]) for c in per_level[lev][1]) for lev in LEVELS]
    assert all(a > b for a, b in zip(tot, tot[1:])), (stem, tot)
    # unresolved band: loops entirely below BAND_TOP must lie in log SFR in [-5, -3.85] (authors place SFR=0 galaxies at 1e-5..1e-4), none may straddle
    nmain = nband = 0
    for lev in LEVELS:
        col, keep, nsmall = per_level[lev]
        resolved, band = [], []
        for c in keep:
            ys = [p[1] for p in c["points"]]
            xs = [p[0] for p in c["points"]]
            assert min(xs) >= 9.0 - 1e-3 and max(xs) <= 12.0 + 1e-3
            if max(ys) < BAND_TOP:
                assert min(ys) >= -5.01 and max(ys) <= -3.85, (stem, lev, min(ys), max(ys))
                band.append(c)
            else:
                assert min(ys) > BAND_TOP, (stem, lev, "loop straddles the unresolved band", min(ys), max(ys))
                resolved.append(c)
        for region, group in (("main", resolved), ("band", band if stem in BAND_PANELS else [])):
            group.sort(key=lambda c: -poly_area(c["points"]))
            for k, c in enumerate(group):
                pts = [(round(float(x), 3), round(float(y), 4)) for x, y in c["points"]]
                closed = abs(pts[0][0] - pts[-1][0]) < 2e-3 and abs(pts[0][1] - pts[-1][1]) < 2e-3
                suffix = region + ("" if k == 0 else str(k + 1))
                tkey = "inst" if tscale == "instantaneous" else f"{tscale}myr"
                simid = run.split("-")[0].lower()
                xs = [p[0] for p in pts]
                regtxt = ("Resolved-SFR part of the plane." if region == "main" else
                          "Unresolved band: galaxies with SFR = 0 in the simulation, to which the authors assigned a random value in 1e-5..1e-4 Msun/yr for display, so the y values of this loop are not simulated SFRs; "
                          "the loop shows where in stellar mass those zero-SFR galaxies lie.")
                rec = vf.record(
                    rid=f"donnari19.{simid}.sfms-contour.z{z}.{tkey}.f{lev}.{suffix}", source="IllustrisTNG",
                    run=f"{run} (per galaxy, {lev}% density contour, {suffix} loop, SFR {tscale if tscale == 'instantaneous' else str(tscale) + ' Myr'})",
                    relation="sfms", z=z,
                    axes={"xDefinition": "log10 stellar mass (sum of star particles within 2 R_star,h)", "xUnit": "log10(Msun)",
                          "yDefinition": ("log10 SFR (sum of instantaneous SFRs of star-forming gas cells within 2 R_star,h)" if tscale == "instantaneous"
                                          else f"log10 SFR (stars formed in the last {tscale} Myr within 2 R_star,h)"), "yUnit": "log10(Msun/yr)"},
                    points=pts, population="all subhaloes (centrals and satellites) with M* > 1e9 Msun",
                    warning=(f"Vertices of the {lev}% density contour of Donnari et al. 2019 (MNRAS 485, 4817), {figlabel}, {run.split('-')[0]} z={z}; no table is published. "
                             f"The caption states that 'the solid contours encompass 20, 50, 70, 90, and 99 %' of the galaxies; the five line colours nest, so this loop is assigned {lev}% by nesting order (outermost 99%, innermost 20%); the paper gives no colour key. "
                             f"Contours are drawn on a 200x200-bin histogram of log SFR x log M*; the colour-scale histogram is a raster image and is not extracted. {regtxt} "
                             f"{'Closed loop.' if closed else 'Open path: truncated by the plot edge (log M* = 9 or the SFR axis limits).'} "
                             f"Loops with polygon area < {AREA_MIN[lev]} dex^2 are not stored ({nsmall} at this level in this panel){'; loops in the unresolved band are not stored for this appendix panel' if stem not in BAND_PANELS else ''}. "
                             f"One record per loop: a level can have several loops (main sequence, high-mass quenched tail, unresolved band); the loop name is main/band, numbered by decreasing area. "
                             f"SFR resolution limit drawn at log SFR = {yres:.1f} (dashed line); the text gives SFR_min = {smin} for this timescale/run."),
                    definitions={"massDefinition": "aperture-2rhalf-stars", "imf": "chabrier03", "cosmology": COSMO, "population": "all", "sfrTimescaleMyr": tscale,
                                 "sfrStatistic": "per-galaxy", "sfrAperture": "2 x R_star,h (3D stellar half-mass radius)", "resolutionCut": "M* > 1e9 Msun; unresolved SFR set to 1e-5..1e-4 Msun/yr by the authors"},
                    citation=f"Donnari et al. 2019, MNRAS 485, 4817 (arXiv:{ARXIV}), SFR-M* plane of TNG galaxies with density contours, {figlabel}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
                    figure=figlabel, panel=f"{run.split('-')[0]} z={z}, SFR {tscale}", sha=sha, member=f"{pdf.name} (3 pt stroked contour paths, colour {tuple(round(v, 2) for v in col)})",
                    calib="x: labelled ticks 9.0-12.0 snapped to ticks; y: labelled ticks -5..2 (minus signs absent from the text layer, values assigned bottom to top from the digit sequence 5,4,3,2,1,0,1,2) snapped to ticks; frame asserted at log M* 9.0-12.0 and log SFR -5.1 to 2.5",
                    calibration="prediction", interval="scatter", connect=True, strict=False, uncertainty=0.01, retrieved="2026-10-18",
                    note="Vector-path extraction of a density contour; the loop is the plotted line, not a table. Not a per-galaxy marker set.")
                rec["domain"] = {"xMin": min(xs), "xMax": max(xs)}
                rec["selection"].update({"contourLevel": lev / 100, "contourKind": "enclosed fraction of the galaxies in the panel (caption)", "contourClosed": bool(closed),
                                         "contourRegion": "unresolved-SFR band (random 1e-5..1e-4)" if region == "band" else "resolved SFR"})
                records.append(rec)
                if region == "main":
                    nmain += 1
                else:
                    nband += 1
    # main-sequence normalisation check (200 Myr panels): mid-point of the innermost contour crossing vs the paper's Table (alpha, beta), 0.25 dex tolerance
    if tscale == 200 and run.startswith("TNG300"):
        a, b = MS_TABLE[z]
        checks = []
        for lev in (20, 50):
            for xq in (9.2, 9.5):
                cr = sorted(v for c in per_level[lev][1] for v in cross(c["points"], xq) if v > BAND_TOP)
                if len(cr) == 2:
                    mid = 0.5 * (cr[0] + cr[1])
                    checks.append((lev, xq, round(mid, 3), round(a * xq + b, 3)))
                    assert abs(mid - (a * xq + b)) < 0.25, (stem, lev, xq, mid, a * xq + b)
                    break
        assert len(checks) >= 2, (stem, checks)
        summary.append((stem, "MS check", checks))
    summary.append((stem, "levels", {lev: (len(per_level[lev][1]), per_level[lev][2]) for lev in LEVELS}, "records main/band", nmain, nband, "SFRmin line", round(yres, 2)))

ids = [r["id"] for r in records]
assert len(ids) == len(set(ids))
keys = [(r["source"], r["run"], r["relation"], r["epoch"]["zRepresentative"]) for r in records]
assert len(keys) == len(set(keys))
bands = [contour_to_band(r) for r in records]
OUT_POLY.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": bands}, indent=2) + "\n")
for s in summary:
    print(s)
print(f"Wrote {len(bands)} contour band records to {OUT} (and the polygons to {OUT_POLY})")
