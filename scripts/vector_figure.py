import hashlib
import io
import re
import tarfile
import urllib.request
from pathlib import Path

import pymupdf

RETRIEVED = "2026-10-05"
TICK_MAX = 40
LABEL_MAX = 40
SCRATCH = Path("/tmp/vector_figure_src")


def fetch_arxiv(arxiv_id):
    out = SCRATCH / arxiv_id
    if not out.exists():
        req = urllib.request.Request(f"https://arxiv.org/e-print/{arxiv_id}", headers={"User-Agent": "Mozilla/5.0"})
        tarfile.open(fileobj=io.BytesIO(urllib.request.urlopen(req).read())).extractall(out)
    return out


def sha256(path, source=None):
    """SHA-256 of the original source file. A figure converted locally from .eps/.ps (not byte-reproducible) is hashed via its original; pass source= to name it."""
    p = Path(path)
    if source is None and p.parent.name == "pdf":
        for ext in (".eps", ".ps"):
            hits = [h for h in p.parent.parent.rglob(p.stem + ext)]
            if hits:
                source = hits[0]
                break
    return hashlib.sha256(Path(source or p).read_bytes()).hexdigest()


def page_of(path, n=0):
    return pymupdf.open(path)[n]


def frames(page, min_w=100, min_h=60):
    seen, out = set(), []
    for d in page.get_drawings():
        r = d["rect"]
        if r.width < min_w or r.height < min_h or len(d["items"]) > 5:
            continue
        if r.width > 0.95 * page.rect.width and r.height > 0.95 * page.rect.height:
            continue
        if (d["fill"] is None and d["color"] is not None) or (d["fill"] is not None and d["color"] is None and len(d["items"]) == 1 and d["items"][0][0] == "re"):
            key = tuple(round(v, 0) for v in (r.x0, r.y0, r.x1, r.y1))
            if key not in seen:
                seen.add(key)
                out.append(r)
    return sorted(out, key=lambda r: (round(r.y0 / 20), r.x0))


def number(s):
    s = s.replace("−", "-")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def _tick_positions(page, frame, axis):
    pos = set()
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if axis == "x" and abs(a.x - b.x) < 0.05 and abs(abs(a.y - b.y)) < TICK_MAX and frame.x0 - 1 <= a.x <= frame.x1 + 1 \
                    and (abs(min(a.y, b.y) - frame.y1) < 1 or abs(max(a.y, b.y) - frame.y1) < 1 or abs(min(a.y, b.y) - frame.y0) < 1 or abs(max(a.y, b.y) - frame.y0) < 1):
                pos.add(round(a.x, 2))
            if axis == "y" and abs(a.y - b.y) < 0.05 and abs(abs(a.x - b.x)) < TICK_MAX and frame.y0 - 1 <= a.y <= frame.y1 + 1 \
                    and (abs(min(a.x, b.x) - frame.x0) < 1 or abs(max(a.x, b.x) - frame.x0) < 1 or abs(min(a.x, b.x) - frame.x1) < 1 or abs(max(a.x, b.x) - frame.x1) < 1):
                pos.add(round(a.y, 2))
    return sorted(pos)


def axis_fit(page, frame, axis, labels=None, log=False, snap=3.0, tol=0.02, vsign=1):
    """Linear (or log10) map from page coords to data, fitted on numeric tick labels snapped to tick marks.
    labels: optional explicit [(page_pos, value)]; otherwise numeric words found outside the frame edge."""
    ticks = _tick_positions(page, frame, axis)
    pairs = []
    for w in page.get_text("words"):
        v = number(w[4])
        if v is None:
            continue
        v *= vsign
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if axis == "x" and frame.x0 - 2 <= cx <= frame.x1 + 2 and (0 < cy - frame.y1 < LABEL_MAX or 0 < frame.y0 - cy < LABEL_MAX):
            pairs.append((cx, v))
        if axis == "y" and frame.y0 - 2 <= cy <= frame.y1 + 2 and (0 < frame.x0 - cx < LABEL_MAX or 0 < cx - frame.x1 < LABEL_MAX):
            pairs.append((cy, v))
    if labels is not None:
        pairs = labels
    snapped = []
    for p, v in pairs:
        near = min(ticks, key=lambda t: abs(t - p), default=None)
        if near is not None and abs(near - p) <= snap:
            snapped.append((near, v))
    pts = sorted(set(snapped))
    best = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if pts[j][1] == pts[i][1] or pts[j][0] == pts[i][0]:
                continue
            m = (pts[j][1] - pts[i][1]) / (pts[j][0] - pts[i][0])
            c = pts[i][1] - m * pts[i][0]
            inl = [(p, v) for p, v in pts if abs(c + m * p - v) < tol * abs(pts[-1][1] - pts[0][1] or 1.0)]
            if best is None or len(inl) > len(best[0]):
                best = (inl, m, c)
    assert best is not None and len(best[0]) >= 3, (axis, "fewer than 3 labelled ticks agree", pts)
    inl = sorted(set(best[0]))
    n = len(inl)
    mp, mv = sum(p for p, _ in inl) / n, sum(v for _, v in inl) / n
    slope = sum((p - mp) * (v - mv) for p, v in inl) / sum((p - mp) ** 2 for p, _ in inl)
    icpt = mv - slope * mp
    return (lambda p: icpt + slope * p), inl


def calibrate(page, frame, fx=None, fy=None, xsign=1, ysign=1, **kw):
    xt = yt = None
    if fx is None:
        fx, xt = axis_fit(page, frame, "x", vsign=xsign, **kw)
    if fy is None:
        fy, yt = axis_fit(page, frame, "y", vsign=ysign, **kw)
    return fx, fy, {"xTicks": xt, "yTicks": yt}


def curves(page, frame, fx, fy, min_items=4):
    """Stroked polylines whose vertices lie inside the frame, with transformed vertices."""
    out = []
    for d in page.get_drawings():
        if d["type"] not in ("s", "fs") or d["color"] is None or len(d["items"]) < min_items:
            continue
        if any(it[0] not in ("l", "c") for it in d["items"]):
            continue
        pts = [d["items"][0][1]] + [it[-1] for it in d["items"]]
        inside = sum(frame.x0 - 0.5 <= p.x <= frame.x1 + 0.5 and frame.y0 - 0.5 <= p.y <= frame.y1 + 0.5 for p in pts)
        if inside < 0.5 * len(pts):
            continue
        out.append({"color": tuple(round(v, 2) for v in d["color"]), "width": d.get("width"), "dashes": d.get("dashes"),
                    "opacity": d.get("stroke_opacity"), "points": [(fx(p.x), fy(p.y)) for p in pts], "raw": pts})
    return out


def clip(points, xmin, xmax, ymin, ymax):
    return [(x, y) for x, y in points if xmin <= x <= xmax and ymin <= y <= ymax]


def record(*, rid, source, run, relation, z, axes, points, population, warning, definitions, citation, doi, url, figure, panel, sha, member, calib, calibration,
           uncertainty=0.01, tier="digitized-figure", rankable=False, note="Vector-path extraction; exact to PDF coordinate precision, so uncertainty is the plotted line, not marker tracing.",
           interval="unspecified", scatter=None, z_nominal=None, retrieved=RETRIEVED, connect=True, strict=True, z_range=None):
    pts = [{"x": round(x, 3), "y": round(y, 4)} if not isinstance(p, dict) else p for p in points for x, y in [(p["x"], p["y"]) if isinstance(p, dict) else p]]
    assert not strict or all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])), (rid, "x not strictly increasing")
    return {
        "id": rid, "source": source, "run": run, "kind": "simulation", "relation": relation,
        "epoch": {"zRepresentative": z, "zNominal": z if z_nominal is None else z_nominal, "zMin": z if z_range is None else z_range[0], "zMax": z if z_range is None else z_range[1], "mode": "published-epoch", "snapshot": None},
        "axes": axes, "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": interval, "connect": connect, "points": pts},
        "scatter": scatter, "selection": {"population": population, "warning": warning}, "definitions": definitions,
        "provenance": {"tier": tier, "citation": citation, "doi": doi, "url": url, "retrieved": retrieved, "figure": figure, "panel": panel, "checksumSha256": sha,
                       "sourceMember": member, "extractionMethod": "vector path vertices from the figure PDF (PyMuPDF get_drawings), transformed through axes calibrated on labelled tick marks",
                       "axisCalibrationPixels": calib, "digitizationUncertaintyDex": uncertainty},
        "calibration": calibration, "rankable": rankable, "notes": note}


def shifted(f, delta):
    return lambda p: f(p - delta)


def check_labels(page, frame, axis, f, vsign=1, tol=0.02):
    """Assert numeric labels beside this frame edge sit where f predicts (for panels calibrated by translation)."""
    n = 0
    for w in page.get_text("words"):
        v = number(w[4])
        if v is None:
            continue
        v *= vsign
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if axis == "y" and frame.y0 + 2 <= cy <= frame.y1 - 2 and 0 < frame.x0 - cx < LABEL_MAX:
            assert abs(f(cy) - v) < 0.05 * max(1.0, abs(v)), (axis, "label mismatch", v, f(cy))
            n += 1
        if axis == "x" and frame.x0 + 2 <= cx <= frame.x1 - 2 and 0 < cy - frame.y1 < LABEL_MAX:
            assert abs(f(cx) - v) < 0.05 * max(1.0, abs(v)), (axis, "label mismatch", v, f(cx))
            n += 1
    assert n >= 2, (axis, "no labels to verify")


def markers(page, frame, fx, fy, color, max_size=30.0, min_size=0.5, fill=True):
    """Centres of small filled (or stroked) marker paths of one colour inside the frame, in data coordinates."""
    out = []
    for d in page.get_drawings():
        c = d["fill"] if fill else d["color"]
        if c is None or any(abs(a - b) > 0.02 for a, b in zip(c, color)):
            continue
        r = d["rect"]
        if not (min_size <= r.width <= max_size and min_size <= r.height <= max_size):
            continue
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if frame.x0 <= cx <= frame.x1 and frame.y0 <= cy <= frame.y1:
            out.append((fx(cx), fy(cy)))
    return out


def axis_fit_shifted(page, frame, axis, labels, maxshift=6.0, tol=0.3):
    """Linear map when label centres are offset from their tick marks by a constant: fit the labels, then find the shift that puts them on ticks.
    If the full label set fails, retries leaving out one label at a time (glyph bounding boxes of signed labels can be off-centre); at least 4 labels must remain."""
    ticks = _tick_positions(page, frame, axis)
    allpts = sorted(labels)
    assert len(allpts) >= 3 and ticks, (axis, "need labels and ticks")

    def attempt(pts):
        n = len(pts)
        mp, mv = sum(p for p, _ in pts) / n, sum(v for _, v in pts) / n
        b = sum((p - mp) * (v - mv) for p, v in pts) / sum((p - mp) ** 2 for p, _ in pts)
        a = mv - b * mp
        if any(abs(a + b * p - v) > 0.02 * abs(pts[-1][1] - pts[0][1]) + 1e-9 for p, v in pts):
            return None
        best, d = None, -maxshift
        while d <= maxshift:
            cost = sum(min(abs(t - (p - d)) for t in ticks) for p, _ in pts) / n
            if best is None or cost < best[0]:
                best = (cost, d)
            d += 0.05
        return best[0], best[1], a, b, pts

    tries = [attempt(allpts)]
    if len(allpts) >= 5:
        tries += [attempt(allpts[:i] + allpts[i + 1:]) for i in range(len(allpts))]
    ok = [t for t in tries if t is not None and t[0] < tol]
    assert ok, (axis, "labels do not sit on ticks after any shift", [round(t[0], 2) for t in tries if t])
    cost, d, a, b, pts = ok[0] if tries[0] is not None and tries[0][0] < tol else min(ok, key=lambda t: t[0])
    return (lambda t: a + b * (t + d)), [(p - d, v) for p, v in pts]


def axis_fit_log2(page, frame, axis, labels, snap=4.0, tol=0.4, min_frac=0.8):
    """log10 axis from two (or more) decade labels [(page_pos, exponent)], validated by the minor-tick pattern at log10(2..9) inside the frame.
    Each label may sit nearly as close to a minor tick as to its major tick, so the candidate ticks (up to 3 per label) are tried and the combination matching the tick pattern best is kept."""
    import itertools
    import math
    ticks = _tick_positions(page, frame, axis)
    lo, hi = (frame.y0, frame.y1) if axis == "y" else (frame.x0, frame.x1)
    cands = []
    for p, e in labels:
        near = sorted((t for t in ticks if abs(t - p) <= snap), key=lambda t: abs(t - p))[:3]
        assert near, (axis, "decade label not near a tick", p)
        cands.append([(t, float(e)) for t in near])
    best = None
    for combo in itertools.product(*cands):
        pts = sorted(set(combo))
        if len(pts) < 2:
            continue
        (t1, e1), (t2, e2) = pts[0], pts[-1]
        if t2 == t1 or e2 == e1:
            continue
        slope = (e2 - e1) / (t2 - t1)
        if any(abs(e1 + slope * (t - t1) - e) > 0.02 for t, e in pts):
            continue
        vlo, vhi = sorted((e1 + slope * (lo - t1), e1 + slope * (hi - t1)))
        exp = [(v - e1) / slope + t1 for e in range(math.floor(vlo), math.ceil(vhi) + 1) for k in range(2, 10) for v in [e + math.log10(k)] if vlo + 0.02 <= v <= vhi - 0.02]
        if not exp:
            continue
        hit = sum(1 for q in exp if any(abs(t - q) < tol for t in ticks))
        score = hit / len(exp)
        if best is None or score > best[0]:
            best = (score, len(exp), pts, (lambda e1=e1, slope=slope, t1=t1: (lambda q: e1 + slope * (q - t1)))())
    assert best is not None, (axis, "no consistent decade labels")
    assert best[0] >= min_frac, (axis, "minor-tick pattern does not match a log axis", round(best[0], 2), best[1])
    return best[3], best[2]


def axis_fit_log1(page, frame, axis, label, snap=4.0, tol=0.4, min_frac=0.9):
    """log10 axis with a single labelled decade (label = (page_pos, exponent)): the scale is the one for which the minor-tick pattern at log10(2..9) matches the drawn ticks."""
    import math
    ticks = _tick_positions(page, frame, axis)
    p, e0 = label
    t0 = min(ticks, key=lambda t: abs(t - p))
    assert abs(t0 - p) <= snap, (axis, "decade label not near a tick", p, t0)
    lo, hi = (frame.y0, frame.y1) if axis == "y" else (frame.x0, frame.x1)
    sign = -1.0 if axis == "y" else 1.0
    best = []
    s = 25.0
    while s <= 500.0:
        exp = []
        for e in range(-4, 5):
            for k in range(1, 10):
                pos = t0 + sign * s * (e + math.log10(k))
                if lo + 1.0 < pos < hi - 1.0:
                    exp.append(pos)
        if exp:
            hit = sum(1 for q in exp if any(abs(t - q) < tol for t in ticks))
            best.append((hit / len(exp), len(exp), s))
        s += 0.1
    best.sort(reverse=True)
    frac, n, s = best[0]
    assert frac >= min_frac and n >= 6, (axis, "no log scale matches the ticks", best[:3])
    second = next((b for b in best if abs(b[2] - s) > 3.0), (0, 0, 0))
    assert second[0] < frac - 0.1, (axis, "ambiguous scale", best[:3], second)
    return (lambda q: e0 + sign * (q - t0) / s), [(t0, e0)], s

def _long_axis_lines(page, min_len):
    xs, ys = [], []
    for d in page.get_drawings():
        if d["color"] is not None and max(d["color"]) > 0.15:
            continue
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if abs(a.y - b.y) < 0.01 and abs(a.x - b.x) > min_len:
                ys.append(a.y)
            if abs(a.x - b.x) < 0.01 and abs(a.y - b.y) > min_len:
                xs.append(a.x)
    return xs, ys


def frame_from_long_lines(page, min_len=100.0):
    """Plot frame for single-panel figures whose axes are long black strokes (IDL): bounding box of the long horizontal and vertical black lines."""
    xs, ys = _long_axis_lines(page, min_len)
    assert len(set(round(v, 1) for v in xs)) >= 2 and len(set(round(v, 1) for v in ys)) >= 2, "axis lines not found"
    return pymupdf.Rect(min(xs), min(ys), max(xs), max(ys))


def grid_from_long_lines(page, min_len=100.0):
    """Panels of a regular grid drawn with long black strokes (IDL !p.multi): list of rows, each a list of Rects, top to bottom, left to right."""
    xs, ys = _long_axis_lines(page, min_len)

    def uniq(v):
        out = []
        for t in sorted(v):
            if not out or t - out[-1] > 1.0:
                out.append(t)
        return out
    ux, uy = uniq(xs), uniq(ys)
    assert len(ux) >= 2 and len(uy) >= 2, "axis lines not found"
    return [[pymupdf.Rect(ux[i], uy[j], ux[i + 1], uy[j + 1]) for i in range(len(ux) - 1)] for j in range(len(uy) - 1)]
