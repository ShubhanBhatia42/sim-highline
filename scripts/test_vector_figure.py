import math
import sys
import tempfile
from pathlib import Path

try:
    import pymupdf
except ImportError:
    print("vector_figure test skipped: pymupdf not installed")
    raise SystemExit(0)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

X0, X1, Y0, Y1 = 100.0, 400.0, 50.0, 290.0
PX, PDEX = 50.0, 80.0
tx = lambda v: X0 + PX * v
ty = lambda v: Y1 - PDEX * v


def build(path):
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=360)
    sh = page.new_shape()
    sh.draw_rect(pymupdf.Rect(X0, Y0, X1, Y1))
    sh.finish(color=(0, 0, 0), width=1)
    for v in range(0, 7):
        sh.draw_line((tx(v), Y1), (tx(v), Y1 - 6))
        sh.finish(color=(0, 0, 0), width=0.8)
        page.insert_text((tx(v) - 3, Y1 + 16), str(v), fontsize=9)
    for e in range(0, 3):
        sh.draw_line((X0, ty(e)), (X0 + 8, ty(e)))
        sh.finish(color=(0, 0, 0), width=0.8)
        page.insert_text((X0 - 22, ty(e) + 3), "1" + "0" * e if e else "1", fontsize=9)
        for k in range(2, 10):
            yy = ty(e + math.log10(k))
            if yy > Y0:
                sh.draw_line((X0, yy), (X0 + 4, yy))
                sh.finish(color=(0, 0, 0), width=0.5)
    truth = [(0.5 + 0.9 * i, 0.15 + 0.4 * i + 0.05 * (i % 2)) for i in range(7)]
    sh.draw_polyline([pymupdf.Point(tx(x), ty(y)) for x, y in truth])
    sh.finish(color=(0.1, 0.4, 0.8), width=1.5, closePath=False)
    marks = [(1.0, 0.4), (2.5, 1.1), (4.0, 1.7), (5.5, 0.9)]
    for x, y in marks:
        sh.draw_circle(pymupdf.Point(tx(x), ty(y)), 2.5)
        sh.finish(color=None, fill=(0.9, 0.1, 0.1))
    sh.commit()
    doc.save(path)
    return truth, marks


with tempfile.TemporaryDirectory() as tmp:
    pdf = Path(tmp) / "synthetic.pdf"
    truth, marks = build(pdf)
    page = vf.page_of(pdf)
    fr = [f for f in vf.frames(page, min_w=100, min_h=60)]
    assert len(fr) == 1 and abs(fr[0].x0 - X0) < 0.6 and abs(fr[0].y1 - Y1) < 0.6, fr
    frame = fr[0]
    fx, xt = vf.axis_fit(page, frame, "x")
    assert len(xt) >= 6 and all(abs(fx(tx(v)) - v) < 1e-6 for v in range(7)), xt
    ylabels = [(ty(e), float(e)) for e in range(3)]
    fy, yt = vf.axis_fit_log2(page, frame, "y", ylabels)
    assert all(abs(fy(ty(v)) - v) < 1e-6 for v in (0.0, 0.5, 1.3, 2.0)), "log axis calibration"
    cv = [c for c in vf.curves(page, frame, fx, fy, min_items=4) if c["color"] == (0.1, 0.4, 0.8)]
    assert len(cv) == 1 and len(cv[0]["points"]) == len(truth)
    assert all(abs(a - b[0]) < 1e-3 and abs(c - b[1]) < 1e-3 for (a, c), b in zip(cv[0]["points"], truth)), "curve vertices"
    mk = sorted(vf.markers(page, frame, fx, fy, (0.9, 0.1, 0.1), max_size=8.0))
    assert len(mk) == len(marks) and all(abs(a - b[0]) < 0.02 and abs(c - b[1]) < 0.02 for (a, c), b in zip(mk, sorted(marks))), mk
    sha = vf.sha256(pdf)
    assert len(sha) == 64
    rec = vf.record(rid="t.synthetic", source="Test", run="r", relation="sfms", z=1.0, axes={}, points=cv[0]["points"], population="all", warning="w", definitions={}, citation="c", doi="d", url="u",
                    figure="f", panel="p", sha=sha, member="synthetic.pdf", calib="c", calibration="unknown")
    assert rec["provenance"]["tier"] == "digitized-figure" and rec["rankable"] is False and len(rec["representation"]["points"]) == len(truth)
    try:
        vf.record(rid="t.bad", source="Test", run="r", relation="sfms", z=1.0, axes={}, points=[(1, 1), (0, 1)], population="all", warning="w", definitions={}, citation="c", doi="d", url="u",
                  figure="f", panel="p", sha=sha, member="m", calib="c", calibration="unknown")
        raise SystemExit("non-monotone x was accepted")
    except AssertionError:
        pass
print("vector_figure test passed: frame, linear and log calibration, curve vertices, marker centres, record rules")
