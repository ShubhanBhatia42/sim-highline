"""DARWIN project, first paper (Lee et al. 2026, arXiv:2610.25786, submitted to ApJ): the results of the full-box DARWIN-1 run (65.5 cMpc, 500 pc) and of the DARWIN-2 zoom-in galaxies that are drawn as vector figures, read from the figure files
of the arXiv source: the cosmic star formation rate density (rho_sfr.pdf), the galaxy stellar mass function at z = 5, 3, 1 and 0.25 (gsmf.pdf), the projected half-mass size at z = 4.5, 2 and 0.2 (mgal_size.pdf, DARWIN-1 median and 16th-84th
percentiles, DARWIN-2 galaxies as points), the gas-phase oxygen abundance at z = 4.5 (mgal_OH_highz.pdf) and the gas against star formation surface density of DARWIN-2 galaxies (sfr_gas_vsigma.pdf). The paper's stellar mass-halo mass relation,
local stellar metallicity and black hole mass figures are raster images in the source and are not read (the project does not trace rasters).
The tick labels of these figures are drawn as outlined paths (no text layer), so each axis is calibrated from its tick marks (positions) with the label values read from the rendered figure, and every axis is checked against numbers the paper prints:
the refinement redshifts z = 0.25, 1.5, 4 and 9 (dotted lines of rho_sfr.pdf), the box size and bin width (a bin holding one galaxy has Phi = 1/(L^3 dlogM), and every bin's Poisson error bar must match its count), the resolution limits
500 pc and 62.5 pc (Table 1), the oxygen floor 12 + log(O/H) = 5.67 and Kennicutt (1998) equation 1 (printed with its coefficients). Needs PyMuPDF.
Usage: python3 scripts/digitize_darwin_lee26.py [SOURCE_DIR]   (writes data/curves/darwin-lee26.json)"""
import hashlib
import json
import math
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2610.25786"
DOI = "10.48550/arXiv.2610.25786"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
FIG = SRC / "figures"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "darwin-lee26.json"
CITE = "Lee et al. 2026 (The DARWIN Project; arXiv:2610.25786, submitted to ApJ)"
COSMO = {"H0": 67.4, "Om": 0.315}
L_BOX = 65.536  # cMpc, printed in section 2.2
SHA_TEX = hashlib.sha256((SRC / "main.tex").read_bytes()).hexdigest()
BLACK = (0.0, 0.0, 0.0)
GREY = (0.5, 0.5, 0.51)


# ---------------------------------------------------------------- page helpers
def strokes(page, color=None, items=None, width=None):
    out = []
    for d in page.get_drawings():
        if d["type"] != "s" or d["color"] is None:
            continue
        if color is not None and tuple(round(v, 2) for v in d["color"]) != color:
            continue
        if items is not None and len(d["items"]) != items:
            continue
        if width is not None and abs((d.get("width") or 0) - width) > 0.05:
            continue
        out.append(d)
    return out


def segs(page, color=BLACK, width=None):
    """Single straight black strokes as (x0, y0, x1, y1, width)."""
    r = []
    for d in strokes(page, color, items=1, width=width):
        it = d["items"][0]
        if it[0] == "l":
            r.append((it[1].x, it[1].y, it[2].x, it[2].y, d.get("width") or 0))
    return r


def frames_of(page):
    """Panel frames: rectangles made of four long black strokes of width 1.417 (a shared edge is drawn twice)."""
    hz = sorted({(round(min(a, c), 1), round(b, 1), round(max(a, c), 1)) for a, b, c, d, w in segs(page, width=1.417) if abs(b - d) < 0.05 and abs(c - a) > 150})
    ys = sorted({y for _, y, _ in hz})
    xs = (hz[0][0], hz[0][2])
    return xs, ys


class Axis:
    """pos -> value from two major ticks with known values (linear in the value, or in log10 of it); the other major ticks must be equally spaced and the minor ticks of a log axis must sit at log10(2 .. 9)."""

    def __init__(self, ticks, majors, values, log=False, tol=0.35):
        self.log = log
        top = max(ln for _, ln in ticks)
        ms = []
        for p in sorted(p for p, ln in ticks if ln > 0.75 * top):
            if not ms or p - ms[-1] > 0.3:       # a tick on a shared panel edge is drawn twice
                ms.append(p)
        assert len(ms) == len(values), (len(ms), len(values), [round(m, 1) for m in ms])
        vs = [math.log10(v) if log else v for v in values]
        n = len(ms)
        mp, mv = sum(ms) / n, sum(vs) / n
        slope = sum((p - mp) * (v - mv) for p, v in zip(ms, vs)) / sum((p - mp) ** 2 for p in ms)
        self.a, self.b = slope, mv - slope * mp
        res = max(abs(self.v(p) - v) for p, v in zip(ms, vs)) / abs(slope)
        assert res < tol, ("major ticks are not equally spaced", res)
        self.ms = ms
        self.per_unit = abs(1 / slope)
        if log:
            minors = sorted(p for p, ln in ticks if ln <= 0.75 * top)
            frac = [(self.v(p) % 1.0) for p in minors]
            marks = [math.log10(k) for k in range(2, 10)]
            far = [f for f in frac if min(abs(f - m) for m in marks + [0.0, 1.0]) > 0.012]
            assert not far, ("minor ticks off the log pattern", far[:5])

    def v(self, p):
        return self.a * p + self.b

    def val(self, p):
        """The axis value (the log10 for a log axis)."""
        return self.v(p)


def ticks_on(page, frame, axis, edge=None):
    """Tick marks touching a frame edge: (position along the edge, length)."""
    x0, y0, x1, y1 = frame
    out = []
    for a, b, c, d, w in segs(page):
        if axis == "y" and abs(b - d) < 0.01 and min(abs(a - x0), abs(c - x0)) < 0.6 and y0 - 0.3 <= b <= y1 + 0.3 and 2 < abs(c - a) < 12:
            out.append((b, abs(c - a)))
        if axis == "x" and abs(a - c) < 0.01 and min(abs(b - y1), abs(d - y1)) < 0.6 and x0 - 0.3 <= a <= x1 + 0.3 and 2 < abs(d - b) < 12:
            out.append((a, abs(d - b)))
    return sorted(set((round(p, 3), round(l, 2)) for p, l in out))


def curve_pts(page, frame, color, dashed=None, min_items=1):
    """Stroked polylines of one colour whose vertices lie inside the frame (page coordinates)."""
    x0, y0, x1, y1 = frame
    out = []
    for d in strokes(page, color):
        if len(d["items"]) < min_items or any(it[0] != "l" for it in d["items"]):
            continue
        pts = [d["items"][0][1]] + [it[2] for it in d["items"]]
        if sum(x0 - 0.5 <= p.x <= x1 + 0.5 and y0 - 0.5 <= p.y <= y1 + 0.5 for p in pts) < 0.8 * len(pts):
            continue
        dash = (d.get("dashes") or "").strip()
        is_dashed = dash not in ("[] 0", "")
        if dashed is not None and is_dashed != dashed:
            continue
        out.append([(p.x, p.y) for p in pts])
    return out


def dots(page, frame, size=3.1, fill=BLACK, tol=0.15):
    x0, y0, x1, y1 = frame
    r = []
    for d in page.get_drawings():
        if d["type"] != "f" or d["fill"] is None or tuple(round(v, 2) for v in d["fill"]) != fill:
            continue
        rc = d["rect"]
        if abs(rc.width - size) < tol and abs(rc.height - size) < tol and x0 <= (rc.x0 + rc.x1) / 2 <= x1 and y0 <= (rc.y0 + rc.y1) / 2 <= y1:
            r.append(((rc.x0 + rc.x1) / 2, (rc.y0 + rc.y1) / 2))
    return r


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rec(rid, run, relation, z, axes, points, defs, panel, figure, warning, calib, population, interval="unspecified", connect=True, strict=True, scatter=None, zrange=None, note=None):
    kw = {} if note is None else {"note": note}
    r = vf.record(rid=rid, source="DARWIN", run=run, relation=relation, z=z, axes=axes, points=points, population=population, warning=warning, definitions=defs, citation=f"{CITE}, {figure}", doi=DOI,
                  url=f"https://arxiv.org/abs/{ARXIV}", figure=figure, panel=panel, sha=sha(FIG / FILE[figure]), member=f"figures/{FILE[figure]}", calib=calib, calibration="prediction", interval=interval, connect=connect,
                  strict=strict, z_range=zrange, scatter=scatter, retrieved="2026-10-23", **kw)
    r["provenance"]["sourceTexSha256"] = SHA_TEX
    return r


FILE = {"Fig. 5 (star formation rate density)": "rho_sfr.pdf", "Fig. 7 (galaxy stellar mass functions)": "gsmf.pdf", "Fig. 8 (mass-size relation)": "mgal_size.pdf",
        "Fig. 9 (gas-phase metallicity, z = 4.5)": "mgal_OH_highz.pdf", "Fig. 11 (gas and SFR surface density)": "sfr_gas_vsigma.pdf"}
MASS_AX = {"xDefinition": "log10 total stellar mass", "xUnit": "log10(Msun)"}
records = []
checks = []
OFF = {}


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


# ================================================================ 1. cosmic star formation rate density (DARWIN-1)
F = "Fig. 5 (star formation rate density)"
page = pymupdf.open(FIG / "rho_sfr.pdf")[0]
frame = (86.5, 6.1, 483.3, 261.2)
xt, yt = ticks_on(page, frame, "x"), ticks_on(page, frame, "y")
ax = Axis(xt, None, [1.0, 10.0], log=True)       # 1 + z: the labelled ticks read "1" and "10"
ay = Axis(yt, None, [0.10, 0.01], log=True)       # rho_SFR: the labelled ticks read "0.10" and "0.01"
# the four dotted verticals are the refinement redshifts printed in the text (z = 9, 4, 1.5, 0.25)
dv = sorted(a for a, b, c, d, w in segs(page, width=0.567) if abs(a - c) < 0.01 and abs(d - b) > 200)
zl = [10 ** ax.val(p) - 1 for p in dv]
check(len(zl) == 4 and all(abs(z - t) < 0.03 for z, t in zip(zl, [0.25, 1.5, 4.0, 9.0])), f"rho_sfr dotted lines at z = {[round(z, 3) for z in zl]} (printed: 0.25, 1.5, 4, 9)")
red = curve_pts(page, frame, (0.93, 0.11, 0.14), min_items=50)
assert len(red) == 1
pts = sorted(((10 ** ax.val(x) - 1), ay.val(y)) for x, y in red[0])
pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
zmax = max(pts, key=lambda p: p[1])
check(0.15 < pts[0][0] < 0.3, f"rho_sfr curve starts at z = {pts[0][0]:.3f} (the run's last snapshot, z = 0.19; the reconstruction is from the z = 0.25 snapshot)")
check(1.3 < zmax[0] < 2.1 and 0.085 < 10 ** zmax[1] < 0.115, f"rho_sfr peaks at z = {zmax[0]:.2f}, {10 ** zmax[1]:.3f} Msun/yr/cMpc^3 (text: peak epoch z about 1.5 to 2)")
md14 = lambda z: math.log10(0.015 * (1 + z) ** 2.7 / (1 + ((1 + z) / 2.9) ** 5.6))
dev = max(abs(y - md14(z)) for z, y in pts if 0.3 < z < 6)
check(dev < 0.5, f"rho_sfr within {dev:.2f} dex of Madau & Dickinson (2014) over z = 0.3 to 6 (plausibility, not a printed number)")
records.append(rec("lee26.darwin1.sfrd", "DARWIN-1 (65.5 cMpc box)", "sfrd", 2.0, {"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic star formation rate density of the whole box, from the birth times and initial masses of all stellar particles in 50 Myr bins of proper time", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
                   pts, {"imf": "kroupa01", "cosmology": COSMO, "densityFrame": "comoving", "sfrIndicator": "stellar mass formed per 50 Myr from particle birth times", "sfrIntegrationLimit": "all stellar particles in the simulation volume (bound, unbound and outside halos)", "dustCorrection": "none", "population": "all stars formed in the box"},
                   "DARWIN-1 curve (red)", F, "Cosmic SFR density of the DARWIN-1 box against redshift (z about 0.2 to 14), read from the vector path of the red curve of Lee et al. 2026. The paper reconstructs it from the initial masses and birth times of all stellar particles at the z = 0.25 snapshot in 50 Myr bins (the drawn curve reaches z = 0.2, where the run's latest snapshot, z = 0.19, lies; bound, unbound and diffuse stars all included). The orange symbols (Behroozi et al. 2013, Chabrier IMF) are not extracted. DARWIN-1 uses a Kroupa IMF; the paper notes a Chabrier conversion would lower it by about 0.05 dex. The kinks at the refinement redshifts z = 1.5 and 4 are numerical (the paper says so).",
                   "x: 1+z on a log axis (labelled ticks read as 1 and 10, minor ticks at log10 2 to 9); y: log axis (labelled ticks read as 0.10 and 0.01); the labels are outlined paths, so their values were read from the rendered figure and checked against the four dotted refinement lines (z = 0.25, 1.5, 4, 9)",
                   "all stars formed in the DARWIN-1 box", zrange=(pts[0][0], pts[-1][0]),
                   note="Vector-path extraction; exact to PDF coordinate precision. The paper prints no SFRD values; the axes are checked against the printed refinement redshifts and the printed peak epoch."))

# ================================================================ 2. galaxy stellar mass function (DARWIN-1), four panels
F = "Fig. 7 (galaxy stellar mass functions)"
page = pymupdf.open(FIG / "gsmf.pdf")[0]
xs_, ys_ = frames_of(page)
assert len(ys_) == 5 and abs(xs_[0] - 59.5) < 0.2, ys_
panels = list(zip(ys_[:-1], ys_[1:]))            # top (z = 5) to bottom (z = 0.25)
ZS = [5.0, 3.0, 1.0, 0.25]
bx = Axis(ticks_on(page, (xs_[0], panels[-1][0], xs_[1], panels[-1][1]), "x"), None, [1e9, 1e10, 1e11, 1e12], log=True)
dlog = 22.9 / bx.per_unit  # bin width in dex from the spacing of the markers (22.9 pt on the page); 1/3 dex, verified below
V = L_BOX ** 3
for (ya, yb), z in zip(panels, ZS):
    frame = (xs_[0], ya, xs_[1], yb)
    gy = Axis([t for t in ticks_on(page, frame, "y") if abs(t[0] - yb) > 0.4], None, [1e-1, 1e-2, 1e-3, 1e-4, 1e-5], log=True)   # the lower edge is also the next panel's upper edge
    # markers (vertical strokes of 3.97 pt, width 1.7) and caps (horizontal strokes of 3.96 pt) of the black error bars
    mk, caps = [], []
    for a, b, c, d, w in segs(page, width=1.7):
        if xs_[0] < a < xs_[1] and ya < min(b, d) and max(b, d) < yb + 0.01:
            if abs(a - c) < 0.01 and abs(abs(d - b) - 3.97) < 0.05:
                mk.append((a, (b + d) / 2))
            elif abs(b - d) < 0.01 and abs(abs(c - a) - 3.96) < 0.05:
                caps.append(((a + c) / 2, b))
    mk = sorted({(round(x, 2), round(y, 2)) for x, y in mk})
    pts = []
    for x, y in mk:
        cy = sorted(cy for cx, cy in caps if abs(cx - x) < 0.3)
        up, lo = [c for c in cy if c < y - 0.05], [c for c in cy if c > y + 0.05]
        p = {"x": round(bx.val(x), 3), "y": round(gy.val(y), 4)}
        if up:
            p["yHigh"] = round(gy.val(min(up)), 4)
        if lo:
            p["yLow"] = round(gy.val(max(lo)), 4)
        pts.append(p)
    pts = [p for i, p in enumerate(pts) if i == 0 or p["x"] > pts[i - 1]["x"]]
    # the bins are 0.315 dex wide; the polyline of the curve passes through every marker
    cv = [c for c in curve_pts(page, frame, BLACK, dashed=False, min_items=400)]
    assert len(cv) == 1, len(cv)
    cx_ = sorted(cv[0])
    near = lambda x, y: min(math.hypot(x - u, y - v) for u, v in cx_)
    check(all(near(x, y) < 0.8 for x, y in mk), f"gsmf z={z}: the plotted curve passes through all {len(mk)} markers")
    # printed box size: a bin with N galaxies has Phi = N / (L^3 dlogM); the Poisson error bars must agree with N
    nn = [10 ** p["y"] * V * dlog for p in pts]
    xb = [b - a for a, b in zip([p["x"] for p in pts][:-1], [p["x"] for p in pts][1:])]
    check(all(abs(v / dlog - round(v / dlog)) < 0.03 for v in xb) and abs(dlog - 1 / 3) < 0.01, f"gsmf z={z}: bins {dlog:.3f} dex wide (gaps between populated bins: {sorted(set(round(v / dlog) for v in xb))} bins)")
    bad = []
    for p, n in zip(pts, nn):
        if n < 1.5 or n > 400:
            continue
        up = (10 ** p["yHigh"] - 10 ** p["y"]) / 10 ** p["y"] if "yHigh" in p else None
        if up is not None and abs(up - 1 / math.sqrt(n)) > 0.2 * (1 / math.sqrt(n)) + 0.01:
            bad.append((p["x"], round(n, 1), round(up, 3), round(1 / math.sqrt(n), 3)))
    check(not bad, f"gsmf z={z}: Poisson error bars agree with the counts implied by the box size ({[round(n) for n in nn]})")
    ones = [n for n in nn if n < 3]
    check(all(abs(math.log10(n)) < 0.12 or abs(math.log10(n / 2)) < 0.12 for n in ones), f"gsmf z={z}: the sparsest bins hold 1 or 2 galaxies (N = {[round(n, 2) for n in ones]})")
    records.append(rec(f"lee26.darwin1.gsmf.z{z:g}", "DARWIN-1 (65.5 cMpc box)", "gsmf", z, {**MASS_AX, "yDefinition": "log10 number density per dex of stellar mass (comoving)", "yUnit": "log10(cMpc^-3 dex^-1)"},
                       pts, {"imf": "kroupa01", "cosmology": COSMO, "massDefinition": "unspecified", "densityFrame": "comoving", "population": "all galaxies (PGalF)"}, f"DARWIN-1 binned GSMF at z = {z:g} (black curve with Poisson error bars)", F,
                       f"Galaxy stellar mass function of the DARWIN-1 box at z = {z:g} (the panel label; the text gives z = 0.19 for the run's latest snapshot and does not say whether the z = 0.25 panel is a different snapshot), read from the markers and error-bar caps of the black curve of Lee et al. 2026 (the drawn curve is a smooth line through the {len(pts)} bins; it is not extracted). "
                       "Bins are 0.315 dex wide; error bars are Poisson counting errors, and where the lower bar runs off the axis (one or few galaxies) the lower limit is absent. The paper does not state how the galaxy stellar mass of the GSMF is defined; for the stellar mass-halo mass relation it defines it as the total stellar mass bound to the galaxy as found by PGalF, and it says the massive end depends on the definition. The Schechter fits of McLeod+21, Davidzon+17 and Ilbert+13 are not extracted.",
                       "x: log axis (labelled ticks read as 10^9 to 10^12, equally spaced); y: log axis per panel (labelled ticks read as 10^-1 to 10^-5, minor ticks at log10 2 to 9); labels are outlined paths read from the rendered figure; checked against the printed box size (every bin's Poisson error bar must match the count implied by its value)",
                       "all galaxies of the box", interval="uncertainty", connect=True))

# ================================================================ 3. projected half-mass size (DARWIN-1 median and 16th-84th percentiles; DARWIN-2 galaxies)
F = "Fig. 8 (mass-size relation)"
page = pymupdf.open(FIG / "mgal_size.pdf")[0]
xs_, ys_ = frames_of(page)
assert len(ys_) == 4 and abs(xs_[0] - 70.9) < 0.2, ys_
panels = list(zip(ys_[:-1], ys_[1:]))
ZP = [4.5, 2.0, 0.2]
YLAB = [[1.5, 1.0, 0.5, 0.0, -0.5, -1.0, -1.5]] * 3      # major ticks run from the top edge (1.5, whose label is drawn just inside) to the bottom edge (-1.5)
xax = Axis(ticks_on(page, (xs_[0], panels[-1][0], xs_[1], panels[-1][1]), "x"), None, [6, 7, 8, 9, 10, 11])
size_axes = {**MASS_AX, "yDefinition": "log10 projected stellar half-mass radius R_1/2 (2D, galaxies projected on the XY plane of the box)", "yUnit": "log10(kpc)"}
SIZE_DEFS = {"imf": "kroupa01", "cosmology": COSMO, "massDefinition": "total-galaxy-finder", "population": "all galaxies (PGalF)", "sizeDefinition": "stellar-half-mass-projected"}
for (ya, yb), z, yl in zip(panels, ZP, YLAB):
    frame = (xs_[0], ya, xs_[1], yb)
    yt = ticks_on(page, frame, "y")
    gy = Axis(yt, None, yl)
    # resolution limits printed in Table 1: 500 pc (dotted line) and 62.5 pc (top of the grey band)
    hl = [b for a, b, c, d, w in segs(page, (0.44, 0.44, 0.45)) if abs(b - d) < 0.01 and ya < b < yb and abs(c - a) > 300]
    check(len(hl) == 1 and abs(gy.val(hl[0]) - math.log10(0.5)) < 0.02, f"size z={z}: dotted line at log R = {gy.val(hl[0]):.3f} (DARWIN-1 resolution 500 pc: {math.log10(0.5):.3f})")
    band = [d["rect"] for d in page.get_drawings() if d["type"] == "f" and d["fill"] is not None and abs(d["fill"][0] - 0.84) < 0.04 and d["rect"].width > 300 and ya <= d["rect"].y0 and d["rect"].y1 <= yb + 0.5]
    if band:
        check(abs(gy.val(min(r.y0 for r in band)) - math.log10(0.0625)) < 0.04, f"size z={z}: grey band top at log R = {gy.val(min(r.y0 for r in band)):.3f} (DARWIN-2 resolution 62.5 pc: {math.log10(0.0625):.3f})")
    gr = curve_pts(page, frame, GREY, min_items=5)
    solid = curve_pts(page, frame, GREY, dashed=False, min_items=5)
    dash = sorted(curve_pts(page, frame, GREY, dashed=True, min_items=5), key=lambda c: sum(y for _, y in c))
    assert len(solid) == 1 and len(dash) == 2, (len(solid), len(dash))
    med, hi, lo = sorted(solid[0]), sorted(dash[0]), sorted(dash[1])        # smaller page y = larger radius: dash[0] is the 84th percentile
    assert len(med) == len(hi) == len(lo) and all(abs(a[0] - b[0]) < 0.3 and abs(a[0] - c[0]) < 0.3 for a, b, c in zip(med, hi, lo))
    pts = [{"x": round(xax.val(m[0]), 3), "y": round(gy.val(m[1]), 4), "yLow": round(gy.val(l[1]), 4), "yHigh": round(gy.val(h[1]), 4)} for m, h, l in zip(med, hi, lo)]
    check(all(p["yLow"] <= p["y"] <= p["yHigh"] for p in pts), f"size z={z}: 16th <= median <= 84th at every mass")
    rec_pts = pts
    # the paper's offsets: about 0.3 dex above Miller+25 at z = 4.5 and about 0.1 dex above Nedkova+21 at z = 2
    def overlap_offset(color, label, lo, hi, what):
        cv = [c for c in curve_pts(page, frame, color, min_items=5) if len(c) >= 4 and max(x for x, _ in c) - min(x for x, _ in c) > 60]
        assert len(cv) == 1, (label, len(cv))
        ln = sorted((xax.val(x), gy.val(y)) for x, y in cv[0])
        f = lambda m: next(ln[i][1] + (ln[i + 1][1] - ln[i][1]) * (m - ln[i][0]) / (ln[i + 1][0] - ln[i][0]) for i in range(len(ln) - 1) if ln[i][0] <= m <= ln[i + 1][0])
        offs = [q["y"] - f(q["x"]) for q in pts if ln[0][0] <= q["x"] <= ln[-1][0]]
        off = sum(offs) / len(offs)
        check(lo < off < hi, f"size z={z:g}: DARWIN-1 median is {off:.2f} dex above {label} averaged over the overlap ({what}; the same sign and order as the extracted value)")
        return off
    off_note = ""
    if z == 4.5:
        OFF[4.5] = overlap_offset((0.93, 0.11, 0.14), "Miller+25", 0.2, 0.55, "text: roughly 0.3 dex")
        off_note = f" The text quotes an offset of roughly 0.3 dex above the observed relation of Miller+25; the extracted median lies {OFF[4.5]:.2f} dex above that line averaged over their overlap."
    if z == 2.0:
        OFF[2.0] = overlap_offset((0.0, 0.45, 0.74), "Nedkova+21 (star-forming)", 0.05, 0.3, "text: about 0.1 dex")
        check(OFF[4.5] > OFF[2.0], "size: the offset above the observed relations falls from z = 4.5 to z = 2 (text: the discrepancy decreases toward lower redshift)")
        off_note = f" The text quotes an offset of about 0.1 dex above the star-forming relation of Nedkova+21; the extracted median lies {OFF[2.0]:.2f} dex above that line averaged over their overlap."
    records.append(rec(f"lee26.darwin1.size.z{z:g}", "DARWIN-1 (65.5 cMpc box)", "size", z, size_axes, rec_pts, SIZE_DEFS, f"DARWIN-1 median (solid grey) and 16th-84th percentiles (dashed), z = {z:g}", F,
                       f"Projected stellar half-mass radius against total stellar mass for DARWIN-1 galaxies at z = {z:g}: the median (solid grey) with the 16th and 84th percentiles (dashed grey), read from the vector paths of Lee et al. 2026; the three curves share their mass grid. "
                       "Galaxies are projected on the XY plane of the box. The DARWIN-1 resolution limit is 500 pc (log R = -0.3, dotted line); sizes below a few resolution elements are not reliable (the paper says the low-mass sizes are probably resolution-limited and larger than observed). The observed relations drawn in the figure are not extracted; the observed radii are luminosity-weighted, the simulated ones mass-weighted." + off_note,
                       "x: log M* linear axis (labelled ticks read as 6 to 11); y: log R linear axis (labelled ticks read as -1.5 to 1.5 per panel); labels are outlined paths read from the rendered figure; checked against the printed resolution limits 500 pc and 62.5 pc and the offsets quoted in the text",
                       "all galaxies of the box", interval="scatter", connect=True))
    d2 = dots(page, frame)
    if d2:
        dd = sorted((round(xax.val(x), 3), round(gy.val(y), 4)) for x, y in d2)
        records.append(rec(f"lee26.darwin2.size-galaxies.z{z:g}", "DARWIN-2 (zoom-in galaxies)", "size", z, size_axes, [{"x": x, "y": y} for x, y in dd], SIZE_DEFS, f"DARWIN-2 galaxies (black points), z = {z:g}", F,
                           f"Projected stellar half-mass radius against total stellar mass of the {len(dd)} DARWIN-2 (zoom-in, 62.5 pc) galaxies plotted at z = {z:g} in Lee et al. 2026, read from the centres of the black circles. The zoom-in regions are chosen (24 field regions and a Milky Way analog with its filament), not volume-complete, so the points are context and not a rankable prediction. Points below the grey band (62.5 pc) are at or below the resolution limit.",
                           "x: log M* linear axis (labelled ticks read as 6 to 11); y: log R linear axis; labels are outlined paths read from the rendered figure; checked against the printed resolution limits",
                           "zoom-in regions: 24 field regions and a Milky Way analog with its filament (not volume complete)", interval="unspecified", connect=False, strict=False))

# ================================================================ 4. gas-phase metallicity at z = 4.5
F = "Fig. 9 (gas-phase metallicity, z = 4.5)"
page = pymupdf.open(FIG / "mgal_OH_highz.pdf")[0]
xs_, ys_ = frames_of(page)
assert len(ys_) == 2, ys_
frame = (xs_[0], ys_[0], xs_[1], ys_[1])
mx = Axis(ticks_on(page, frame, "x"), None, [6, 7, 8, 9, 10, 11])
my = Axis(ticks_on(page, frame, "y"), None, [9, 8, 7, 6, 5])
hl = [b for a, b, c, d, w in segs(page, BLACK, width=0.283) if abs(b - d) < 0.01 and abs(c - a) > 300]
floor = [my.val(b) for b in hl if 5.4 < my.val(b) < 6.0]
check(len(floor) >= 1 and abs(floor[0] - 5.67) < 0.04, f"O/H floor line at 12 + log(O/H) = {floor[0]:.3f} (printed: 5.67)")
solid = curve_pts(page, frame, GREY, dashed=False, min_items=5)
dash = sorted(curve_pts(page, frame, GREY, dashed=True, min_items=5), key=lambda c: sum(y for _, y in c))
assert len(solid) == 1 and len(dash) == 2, (len(solid), len(dash))
med, hi, lo = sorted(solid[0]), sorted(dash[0]), sorted(dash[1])
assert len(med) == len(hi) == len(lo)
pts = [{"x": round(mx.val(m[0]), 3), "y": round(my.val(m[1]), 4), "yLow": round(my.val(l[1]), 4), "yHigh": round(my.val(h[1]), 4)} for m, h, l in zip(med, hi, lo)]
check(all(p["yLow"] <= p["y"] <= p["yHigh"] for p in pts) and pts[0]["x"] < 7 and 8.0 < pts[-1]["y"] < 9.0, "mzr: percentile ordering and an increasing median")
mzr_axes = {**MASS_AX, "yDefinition": "12 + log10(O/H) of all gas within a projected aperture of radius 2 proper kpc around the galaxy centre", "yUnit": "dex"}
MZR_DEFS = {"imf": "kroupa01", "cosmology": COSMO, "massDefinition": "unspecified", "population": "all galaxies (PGalF)", "metallicityQuantity": "gas-O/H", "metallicityCalibration": "intrinsic: oxygen over hydrogen abundance of all gas within a projected 2 proper kpc aperture (initial metallicity 1e-3 Zsun, floor 12 + log(O/H) = 5.67)"}
records.append(rec("lee26.darwin1.mzr.z4.5", "DARWIN-1 (65.5 cMpc box)", "mzr", 4.5, mzr_axes, pts, MZR_DEFS, "DARWIN-1 median (solid grey) and 16th-84th percentiles (dashed), z = 4.5", F,
                   "Gas-phase oxygen abundance against total stellar mass for DARWIN-1 galaxies at z = 4.5: median (solid grey) with the 16th and 84th percentiles (dashed grey), read from the vector paths of Lee et al. 2026. Oxygen and hydrogen are summed over all gas within a projected aperture of 2 proper kpc of the galaxy centre, chosen to resemble JWST spectroscopy. The simulations' metallicity floor is 12 + log(O/H) = 5.67 (dotted line). The JWST observations drawn in the figure (Trussler+26, Nakajima+23, Curti+24, Sarkar+25, Chemerynska+24, Hsiao+25) are not extracted.",
                   "x: log M* linear axis (labelled ticks read as 6 to 11); y: linear axis (labelled ticks read as 5 to 9); labels are outlined paths read from the rendered figure; checked against the printed oxygen floor 12 + log(O/H) = 5.67",
                   "all galaxies of the box", interval="scatter", connect=True))
d2 = dots(page, frame)
dd = sorted((round(mx.val(x), 3), round(my.val(y), 4)) for x, y in d2)
check(len(dd) > 200, f"mzr: {len(dd)} DARWIN-2 galaxies")
records.append(rec("lee26.darwin2.mzr-galaxies.z4.5", "DARWIN-2 (zoom-in galaxies)", "mzr", 4.5, mzr_axes, [{"x": x, "y": y} for x, y in dd], MZR_DEFS, "DARWIN-2 galaxies (black points), z = 4.5", F,
                   f"Gas-phase oxygen abundance against total stellar mass of the {len(dd)} DARWIN-2 galaxies plotted at z = 4.5 in Lee et al. 2026, read from the centres of the black circles. The zoom-in regions are chosen, not volume-complete, so the points are context and not a rankable prediction; the low-mass, extremely metal-poor tail is the paper's focus (84 such galaxies at M* of 10^5.5 to 10^8). Points near 12 + log(O/H) = 5.67 are at the metallicity floor.",
                   "x: log M* linear axis; y: linear axis; labels are outlined paths read from the rendered figure; checked against the printed oxygen floor",
                   "zoom-in regions: 24 field regions and a Milky Way analog with its filament (not volume complete)", interval="unspecified", connect=False, strict=False))

# ================================================================ 5. gas against star formation surface density (DARWIN-2 galaxies)
F = "Fig. 11 (gas and SFR surface density)"
page = pymupdf.open(FIG / "sfr_gas_vsigma.pdf")[0]
xs_, ys_ = frames_of(page)
assert len(ys_) == 2, ys_
frame = (xs_[0], ys_[0], xs_[1], ys_[1])
kx = Axis(ticks_on(page, frame, "x"), None, [0, 1, 2, 3, 4])
ky = Axis(ticks_on(page, frame, "y"), None, [2, 1, 0, -1, -2, -3])
# Kennicutt (1998) equation 1, printed with its coefficients: Sigma_SFR = 2.5e-4 Sigma_gas^1.4 (the black line, a polyline of eight vertices)
kl = [d for d in strokes(page, BLACK) if len(d["items"]) == 8 and abs((d.get("width") or 0) - 1.70) < 0.05]
assert len(kl) == 1
pp = [kl[0]["items"][0][1]] + [it[-1] for it in kl[0]["items"]]
lx = [kx.val(p.x) for p in pp if frame[0] < p.x < frame[2] - 0.5 and frame[1] + 0.5 < p.y < frame[3] - 0.5]
ly = [ky.val(p.y) for p in pp if frame[0] < p.x < frame[2] - 0.5 and frame[1] + 0.5 < p.y < frame[3] - 0.5]
mx_, my_ = sum(lx) / len(lx), sum(ly) / len(ly)
sl = sum((a_ - mx_) * (b_ - my_) for a_, b_ in zip(lx, ly)) / sum((a_ - mx_) ** 2 for a_ in lx)
ic = my_ - sl * mx_
check(abs(sl - 1.4) < 0.02 and abs(ic - math.log10(2.5e-4)) < 0.03, f"K-S line: slope {sl:.3f}, intercept {ic:.3f} (printed equation: 1.4 and log 2.5e-4 = {math.log10(2.5e-4):.3f})")
circ = []
for d in page.get_drawings():
    if d["type"] == "f" and d["fill"] is not None and len(d["items"]) == 48 and all(it[0] == "l" for it in d["items"]):
        rc = d["rect"]
        cx, cy = (rc.x0 + rc.x1) / 2, (rc.y0 + rc.y1) / 2
        if frame[0] < cx < frame[2] and frame[1] < cy < frame[3]:
            circ.append((cx, cy, rc.width))
dd = sorted({(round(kx.val(x), 3), round(ky.val(y), 4)) for x, y, w in circ})
check(200 < len(dd) < 300, f"K-S: {len(dd)} DARWIN-2 galaxies")
records.append(rec("lee26.darwin2.ks-galaxies.z0-5", "DARWIN-2 (zoom-in galaxies)", "ks", 3.0, {"xDefinition": "log10 gas surface density: non-ionized hydrogen mass (HI + H2) within 5 stellar half-mass radii, times 1.37 for helium and heavier elements, over the area pi (5 R_star,1/2)^2", "xUnit": "log10(Msun pc^-2)",
                                                                                          "yDefinition": "log10 SFR surface density: mass of stars younger than 20 Myr within 5 stellar half-mass radii over the same area and 20 Myr", "yUnit": "log10(Msun yr^-1 kpc^-2)"},
                   [{"x": x, "y": y} for x, y in dd],
                   {"gasDefinition": "non-ionized hydrogen, M_H - M_HII (HI + H2), within 5 R_star,1/2", "areaScale": "galaxy-integrated: enclosed within 5 stellar half-mass radii over pi (5 R_star,1/2)^2", "sfrIndicator": "mass of stellar particles younger than 20 Myr within 5 R_star,1/2", "sfrTimescaleMyr": 20,
                    "imf": "kroupa01", "coConversion": "not applicable (the molecular fraction is not used: HI and H2 together are the non-ionized hydrogen)", "heliumIncluded": "yes (hydrogen multiplied by 1.37 for helium and heavier elements)", "population": "DARWIN-2 galaxies with M* above 1e8 Msun"},
                   "DARWIN-2 galaxies (circles; colour is Vrot/sigma, size is stellar mass)", F,
                   f"Star formation rate surface density against gas surface density for the {len(dd)} DARWIN-2 (zoom-in, 62.5 pc) galaxies with M* above 10^8 Msun in Lee et al. 2026, read from the centres of the circles over all plotted redshifts (z about 2 to 5). The circles' colour (gas Vrot/sigma) and size (stellar mass) are not extracted. The zoom-in regions are chosen, not volume-complete, so the points are context and not a rankable prediction. "
                   "The paper's Kennicutt (1998) line and its propagated uncertainty bands are not extracted (the dataset holds Kennicutt 1998 as its own record); the line was used to check this figure's axes.",
                   "x: log gas surface density, linear axis (labelled ticks read as 0 to 4); y: linear axis (labelled ticks read as -3 to 2); labels are outlined paths read from the rendered figure; checked against Kennicutt (1998) equation 1 as printed in the paper (slope 1.4, coefficient 2.5e-4)",
                   "DARWIN-2 galaxies above 1e8 Msun", interval="unspecified", connect=False, strict=False, zrange=(2.0, 5.0)))

OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} DARWIN records from Lee et al. 2026; {len(checks)} checks passed:")
for c in checks:
    print("  -", c)
