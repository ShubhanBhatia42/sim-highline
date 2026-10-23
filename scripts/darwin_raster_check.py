"""Checks of the DARWIN-1 catalogue relations against the two raster figures of Lee et al. 2026 (arXiv:2610.25786): Fig. 10 (stellar mass against halo mass, files figures/mstar_mhalo.png) and Fig. 11 (black hole mass against stellar mass, figures/mbh_mstar.png).
Used by scripts/ingest_darwin1_catalogue.py (stage 1b). A raster figure is never digitized into records; it is only a yardstick, and the axes are calibrated from the major tick marks (decades read from the rendered figure: the labelled ticks run 10^9 to 10^15 and 10^12 to 10^6 in Fig. 10, 10^7 to 10^12 and 10^10 to 10^6 in Fig. 11).
Stellar mass against halo mass: the figure draws the median of the DARWIN-1 galaxies as a solid dark-grey line; it is found as the long connected pieces of that colour (the dashed 16th and 84th percentile lines are short pieces and are dropped; where another line crosses it the line is interrupted) and read at the bin centres of the catalogue curve. The dataset's axis is the stellar-to-halo mass ratio, so the line is turned into a ratio (stellar mass minus halo mass at the column where it is read) and compared with the catalogue's median ratio.
Black hole mass against stellar mass: the figure draws every DARWIN-1 galaxy as a light-grey dot of radius 3 pixels (the area of the isolated dots is 26 to 28 pixels). The same dots are drawn from the catalogue galaxies on the same calibrated axes, the pixels the figure hides under other symbols are hidden in both, and the 5th, 25th, 50th, 75th and 95th percentile of the occupied dot pixels in each stellar-mass bin are compared (the same overlap bias is in both, so the comparison is like for like; it is not a comparison of medians of galaxies)."""
import hashlib
from pathlib import Path

import numpy as np
import pymupdf
from scipy import ndimage as ndi

LINE_RGB, DOT_RGB = (102, 102, 101), (163, 163, 162)  # the DARWIN-1 median line and the DARWIN-1 dots (colours of the legend entries)
DOT_RADIUS = 3


def load(path):
    pix = pymupdf.Pixmap(str(path))
    if pix.alpha:
        pix = pymupdf.Pixmap(pix, 0)
    pix = pymupdf.Pixmap(pymupdf.csRGB, pix) if pix.n != 3 else pix
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, 3).astype(int)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _runs(a):
    a = np.asarray(a)
    if len(a) == 0:
        return []
    cut = np.nonzero(np.diff(a) != 1)[0]
    s = np.concatenate([[0], cut + 1]); e = np.concatenate([cut, [len(a) - 1]])
    return [(int(a[i]), int(a[j])) for i, j in zip(s, e)]


def _centres(a):
    return [(lo + hi) / 2 for lo, hi in _runs(a)]


def frames(rgb):
    """Rows and columns of the black frame lines: panel rows are between consecutive horizontal frame lines."""
    black = rgb.sum(axis=2) < 120
    h, w = black.shape
    rows = _runs(np.nonzero(black.sum(axis=1) > 0.5 * w)[0]); cols = _runs(np.nonzero(black.sum(axis=0) > 0.3 * h)[0])
    assert len(rows) == 3 and len(cols) == 2, (rows, cols)
    return black, rows, cols


def progression(centres, first_value_index=0, tol=3.0, lo=100.0, hi=300.0):
    """Major ticks: the equally spaced subset of detected tick centres, starting at the first one; the step is the median of the plausible neighbouring differences."""
    c = sorted(centres)
    step = float(np.median([b - a for a, b in zip(c, c[1:]) if lo <= b - a <= hi]))
    ticks = [c[first_value_index]]
    while True:
        nxt = [v for v in c if abs(v - (ticks[-1] + step)) <= tol]
        if not nxt:
            return ticks, step
        ticks.append(nxt[0])


def calibrate(rgb, x_first_decade, x_n, y_first_decade, y_n, x_depth=8, y_depth=20):
    """Pixel-to-data maps from the major ticks: x from the bottom frame (ticks point up into the plot), y per panel from the left frame (ticks point right)."""
    black, rows, cols = frames(rgb)
    xt = _centres(np.nonzero(black[rows[2][0] - x_depth, cols[0][1] + 1:cols[1][0]])[0] + cols[0][1] + 1)
    xticks, xstep = progression(xt)
    assert len(xticks) >= x_n, ("x major ticks", xticks)
    xticks = xticks[:x_n]
    panels = []
    for top, bot in ((rows[0][1] + 1, rows[1][0] - 1), (rows[1][1] + 1, rows[2][0] - 1)):
        yt = _centres(np.nonzero(black[top:bot, cols[0][1] + 1 + y_depth])[0] + top)
        yticks, ystep = progression(yt)
        assert len(yticks) >= y_n, ("y major ticks", yticks)
        panels.append({"rows": (top, bot), "y0": yticks[0], "ydec": y_first_decade, "ystep": ystep, "nTicks": len(yticks[:y_n])})
    return {"x0": xticks[0], "xdec": x_first_decade, "xstep": xstep, "xticks": xticks, "cols": (cols[0][1] + 1, cols[1][0] - 1), "panels": panels}


def px_x(cal, logx):
    return cal["x0"] + (np.asarray(logx) - cal["xdec"]) * cal["xstep"]


def px_y(cal, k, logy):
    p = cal["panels"][k]
    return p["y0"] + (p["ydec"] - np.asarray(logy)) * p["ystep"]


def data_x(cal, px):
    return cal["xdec"] + (np.asarray(px) - cal["x0"]) / cal["xstep"]


def data_y(cal, k, py):
    p = cal["panels"][k]
    return p["ydec"] - (np.asarray(py) - p["y0"]) / p["ystep"]


def shmr_median_lines(png):
    """The median line of each panel of Fig. 10 as pixel columns and rows, and the calibration."""
    rgb = load(png)
    cal = calibrate(rgb, 9, 6, 12, 7)
    mask = np.abs(rgb - np.array(LINE_RGB)).max(axis=2) <= 16
    out = []
    for k, p in enumerate(cal["panels"]):
        m = np.zeros_like(mask)
        m[p["rows"][0]:p["rows"][1], cal["cols"][0]:cal["cols"][1]] = mask[p["rows"][0]:p["rows"][1], cal["cols"][0]:cal["cols"][1]]
        if k == 1:  # the legend sample line of the lower panel (a horizontal run of this colour more than 150 pixels long)
            sample_rows = np.nonzero(m[:, int(px_x(cal, 11.5)):int(px_x(cal, 12.5))].sum(axis=1) > 150)[0]
            for r0, r1 in _runs(sample_rows):
                m[r0 - 2:r1 + 3, int(px_x(cal, 11.5)):int(px_x(cal, 12.9))] = False
        lab, n = ndi.label(m, structure=np.ones((3, 3)))
        cols, rows_ = [], []
        for i in range(1, n + 1):
            ys, xs = np.nonzero(lab == i)
            if xs.max() - xs.min() < 60:
                continue
            for c in range(xs.min(), xs.max() + 1):
                yy = ys[xs == c]
                if len(yy) and yy.max() - yy.min() <= 14:
                    cols.append(c); rows_.append(float(yy.mean()))
        out.append((np.array(cols), np.array(rows_)))
    return cal, out


def check_shmr(png, curves, tol_dex=0.012):
    """curves: {"z3": [(logMhalo bin centre, n centrals, median log10(M*/Mhalo), complete), ...], "z0.19": [...]}; the panels are z = 3 (upper) and z = 0.19 (lower).
    Returns for each panel the table of the paper's median line (as log10 ratio) minus the catalogue median at the bin centres where the line was found."""
    cal, lines = shmr_median_lines(png)
    res = {}
    for k, key in enumerate(("z3", "z0.19")):
        cols, rows_ = lines[k]
        lx, ly = data_x(cal, cols), data_y(cal, k, rows_)
        bins = []
        for xc, n, med, complete in curves[key]:
            near = np.abs(lx - xc) < tol_dex
            if not near.any():
                continue
            paper = float((ly[near] - lx[near]).mean())
            bins.append({"logMhalo": round(xc, 3), "n": int(n), "complete": bool(complete), "catalogue": round(med, 3), "paper": round(paper, 3), "paperMinusCatalogue": round(paper - med, 3)})
        d = np.array([b["paperMinusCatalogue"] for b in bins]); dc = np.array([b["paperMinusCatalogue"] for b in bins if b["complete"]])
        res[key] = {"binsCompared": len(bins), "binsCompleteCompared": int(len(dc)), "paperMinusCatalogueMedian": round(float(np.median(d)), 3) if len(d) else None, "paperMinusCatalogueMin": round(float(d.min()), 3) if len(d) else None, "paperMinusCatalogueMax": round(float(d.max()), 3) if len(d) else None,
                    "completeMedian": round(float(np.median(dc)), 3) if len(dc) else None, "completeMin": round(float(dc.min()), 3) if len(dc) else None, "completeMax": round(float(dc.max()), 3) if len(dc) else None, "bins": bins}
    res["calibration"] = {"xTicksPx": cal["xticks"], "xPixelsPerDecade": round(cal["xstep"], 2), "yPixelsPerDecade": [round(p["ystep"], 2) for p in cal["panels"]]}
    return res


def _percentiles(mask, cal, k, lo, hi, qs=(0.05, 0.25, 0.5, 0.75, 0.95), min_pixels=400):
    p = cal["panels"][k]
    c0, c1 = int(round(px_x(cal, lo))), int(round(px_x(cal, hi)))
    sub = mask[p["rows"][0]:p["rows"][1], c0:c1]
    w = sub.sum(axis=1); ys = np.nonzero(w)[0]
    if sub.sum() < min_pixels or len(ys) < 20:
        return None
    logy = data_y(cal, k, ys + p["rows"][0]); o = np.argsort(logy); cw = np.cumsum(w[ys][o]) / w[ys].sum()
    return [float(np.interp(q, cw, logy[o])) for q in qs] + [int(sub.sum())]


def check_bh(png, galaxies, edges):
    """galaxies: {"z2.1": {"A": (logMstar, logMBH), "B": (...)}, "z0.19": {...}}: scenario A is every galaxy with at least one black hole particle (mass summed), B only those with exactly one.
    The panels are z = 2 to 3 (upper; the catalogue snapshot nearest the paper's z = 2.1) and z = 0.19 (lower)."""
    rgb = load(png)
    cal = calibrate(rgb, 8, 5, 10, 5)  # the left frame is 10^7; the first major tick inside the frame is 10^8
    assert abs(cal["x0"] - cal["xstep"] - cal["cols"][0]) < 8, "the left frame must be 10^7"
    dist = np.abs(rgb - np.array(DOT_RGB)).max(axis=2)
    gray = ndi.binary_opening(dist <= 6, structure=np.ones((3, 3), bool))  # the solid grey of the dots; the opening removes the one-pixel anti-aliased edges of text and lines
    white = rgb.min(axis=2) >= 245
    other = (dist > 40) & ~white  # symbols, lines and text drawn over the dots
    yy, xx = np.mgrid[-DOT_RADIUS:DOT_RADIUS + 1, -DOT_RADIUS:DOT_RADIUS + 1]
    disc = (xx ** 2 + yy ** 2) <= DOT_RADIUS ** 2
    res = {}
    for k, key in enumerate(("z2.1", "z0.19")):
        paper = [_percentiles(gray, cal, k, lo, hi) for lo, hi in zip(edges[:-1], edges[1:])]
        res[key] = {}
        for scen, (x, y) in galaxies[key].items():
            canvas = np.zeros(gray.shape, bool)
            px = np.round(px_x(cal, x)).astype(int); py = np.round(px_y(cal, k, y)).astype(int)
            top, bot = cal["panels"][k]["rows"]
            ok = (px >= cal["cols"][0] + DOT_RADIUS) & (px < cal["cols"][1] - DOT_RADIUS) & (py >= top + DOT_RADIUS) & (py < bot - DOT_RADIUS)
            for cx, cy in zip(px[ok], py[ok]):
                canvas[cy - DOT_RADIUS:cy + DOT_RADIUS + 1, cx - DOT_RADIUS:cx + DOT_RADIUS + 1] |= disc
            canvas = ndi.binary_opening(canvas & ~other, structure=np.ones((3, 3), bool))  # the same treatment as the figure's mask
            bins, missing = [], []
            for (lo, hi), pp in zip(zip(edges[:-1], edges[1:]), paper):
                if pp is None:
                    continue
                cc = _percentiles(canvas, cal, k, lo, hi)
                if cc is None:
                    missing.append(round((lo + hi) / 2, 3)); continue
                bins.append({"logMstar": round((lo + hi) / 2, 3), "paper": [round(v, 2) for v in pp[:5]], "catalogue": [round(v, 2) for v in cc[:5]], "diff50": round(cc[2] - pp[2], 3), "maxAbsDiffAll": round(max(abs(a - b) for a, b in zip(cc[:5], pp[:5])), 3)})
            d50 = np.array([b["diff50"] for b in bins])
            res[key][scen] = {"nGalaxiesInWindow": int(ok.sum()), "binsCompared": len(bins), "binsWithPaperDotsButNoCatalogueDots": missing,
                              "diff50Median": round(float(np.median(d50)), 3) if len(d50) else None, "diff50WithinHalfDex": int((np.abs(d50) <= 0.1).sum()) if len(d50) else 0, "diff50Max": round(float(np.abs(d50).max()), 3) if len(d50) else None, "bins": bins}
    res["calibration"] = {"xTicksPx": cal["xticks"], "xPixelsPerDecade": round(cal["xstep"], 2), "yPixelsPerDecade": [round(p["ystep"], 2) for p in cal["panels"]]}
    return res
