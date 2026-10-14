import json
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2509.07960"
DOI = "10.1093/mnras/stag740"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
CITE = f"Chaikin et al. 2026, MNRAS 548, stag740 (doi:{DOI}; arXiv:{ARXIV}), COLIBRE galaxy stellar mass functions, star formation and quenching"
URL = f"https://arxiv.org/abs/{ARXIV}"
RUNS = {(0.82, 0.14, 0.14): ("L400m7", "m7"), (1.0, 0.62, 0.43): ("L200m6", "m6"), (0.77, 0.91, 1.0): ("(L025, L050 or L100)m5", "m5")}
ZS = [0.1, 1.0, 2.0, 3.0, 5.0, 7.0]
near = lambda c, t: c is not None and all(abs(a - b) < 0.02 for a, b in zip(c, t))
cx = lambda w: (w[0] + w[2]) / 2
cy = lambda w: (w[1] + w[3]) / 2

pdf = SRC / "plots" / "qf.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
frames = vf.frames(page, 100, 60)[:6]
assert len(frames) == 6 and frames[0].x1 == frames[1].x0 and frames[0].y1 == frames[3].y0, frames
words = page.get_text("words")
drawings = page.get_drawings()


def xlabels(fr):
    return [(cx(w), float(m.group(1))) for w in words for m in [re.fullmatch(r"10(\d{1,2})", w[4])] if m and fr.y1 < cy(w) < fr.y1 + 30 and fr.x0 - 3 <= cx(w) < fr.x1 - 3]


def ylabels(fr):
    return [(cy(w), float(w[4])) for w in words if re.fullmatch(r"[01]\.\d", w[4]) and cx(w) < frames[0].x0 and fr.y0 + 4 < cy(w) < fr.y1]


def panel_z(fr):
    zs = [w for w in words if w[4] == "z" and fr.x0 < cx(w) < fr.x0 + 60 and fr.y0 < cy(w) < fr.y0 + 40]
    assert len(zs) == 1, fr
    row = sorted((w for w in words if abs(cy(w) - cy(zs[0])) < 2 and cx(w) > cx(zs[0]) and cx(w) < fr.x0 + 100), key=cx)
    assert row[0][4] == "=", row
    return float(row[1][4])


def inside(d, fr):
    r = d["rect"]
    return fr.contains(pymupdf.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))


def verts(d):
    return [d["items"][0][1]] + [it[-1] for it in d["items"]]


AX = {"xDefinition": "log10 stellar mass (bound stars within a 3D 50 pkpc aperture)", "xUnit": "log10(Msun)",
      "yDefinition": "fraction of galaxies in the stellar mass bin that are quenched (sSFR < 0.2 / t_H(z)); band is the 68 per cent Clopper-Pearson interval", "yUnit": "fraction"}
DEF = {"imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "massDefinition": "aperture-50pkpc", "population": "all",
       "quenchingCriterion": "ssfr<0.2/tH(z)", "sfrTimescaleMyr": "instantaneous (gas SFR within 50 pkpc)"}
SPOT = {("m7", 0.1): ((9.5, 0.12, 0.28), (11.5, 0.75, 0.95)), ("m7", 7.0): ((11.0, 0.1, 0.3),)}
records = []
for k, fr in enumerate(frames):
    z = panel_z(fr)
    assert z == ZS[k], (k, z)
    bot = frames[3 + k % 3]
    fx, xt = vf.axis_fit_log2(page, fr, "x", xlabels(bot))
    fy, yt = vf.axis_fit(page, fr, "y", labels=[(min(vf._tick_positions(page, fr, "y"), key=lambda t: abs(t - p)), v) for p, v in ylabels(frames[0] if k < 3 else frames[3])])
    for col, (run, slug) in RUNS.items():
        solid = [d for d in drawings if d["type"] == "s" and near(d["color"], col) and abs((d.get("width") or 0) - 2.0) < 0.01 and d["dashes"].startswith("[ 2 0 ]") and inside(d, fr)]
        band = [d for d in drawings if d["type"] == "f" and near(d["fill"], col) and d.get("fill_opacity") is not None and inside(d, fr)]
        assert len(solid) == 1 and len(band) == 1, (z, run, len(solid), len(band))
        line, poly = verts(solid[0]), verts(band[0])
        assert len(poly) == 2 * len(line) + 1 and (abs(solid[0]["rect"].x0 - band[0]["rect"].x0) < 0.05 and abs(solid[0]["rect"].x1 - band[0]["rect"].x1) < 0.05), (z, run, len(line), len(poly))
        pts = []
        for p in line:
            ys = [q.y for q in poly if abs(q.x - p.x) < 0.01]
            assert len(ys) >= 2, (z, run, p.x)
            pts.append({"x": round(fx(p.x), 3), "y": round(fy(p.y), 4) + 0.0, "yLow": round(fy(max(ys)), 4) + 0.0, "yHigh": round(fy(min(ys)), 4) + 0.0})
        pts.sort(key=lambda q: q["x"])
        assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and all(q["yLow"] - 1e-4 <= q["y"] <= q["yHigh"] + 1e-4 and -0.01 <= q["y"] <= 1.01 for q in pts), (z, run)
        for xa, lo, hi in SPOT.get((slug, z), ()):
            q = min(pts, key=lambda t: abs(t["x"] - xa))
            assert abs(q["x"] - xa) < 0.3 and lo < q["y"] < hi, (slug, z, xa, q)
        records.append(vf.record(
            rid=f"chaikin26.colibre.quenched.{slug}.z{z:g}", source="COLIBRE", run=run, relation="quenched", z=z, axes=AX, points=pts, population="all galaxies", interval="uncertainty", definitions=dict(DEF),
            citation=CITE + f", quenched fraction, z={z:g}", doi=DOI, url=URL, figure="Evolution of the galaxy quenched fraction", panel=f"z={z:g}, {run} solid line", sha=sha, member="plots/qf.pdf", calibration="prediction", uncertainty=0.01,
            calib="x: labelled decades 10^7 to 10^12 of the bottom frame of the panel column; y: labelled ticks 0.0 to 1.0 of the left frame of the panel row; both validated against the drawn ticks",
            warning=f"Quenched fraction of COLIBRE {run} at z={z:g} (sSFR < 0.2 / t_H(z); the threshold moves with redshift, unlike the fixed 1e-11 / yr used elsewhere), read from the vector paths of Chaikin et al. 2026 (quenched fraction figure). "
                    "Solid segment only: the paper draws the line dotted below about 1e9 Msun, where the rise in the quenched fraction may be a resolution artefact, and where fewer than 10 galaxies fall in a bin, and those parts are not extracted. "
                    "yLow and yHigh are the plotted 68 per cent Clopper-Pearson interval. Stellar mass and SFR are measured within 50 pkpc 3D apertures of bound particles (SFR instantaneous). "
                    "The legend names the m5 line (L025, L050 or L100)m5 without saying which box is used in each panel; the paper's mass function caption uses the largest box available, which by the redshift ranges of the data release would be L025 at z=0.1, L050 at z=1-3 and L100 at z=5-7, but that is an inference. "
                    "Observational and semi-empirical overlays are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "chaikin26-colibre-quenched.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} COLIBRE quenched-fraction records from Chaikin+26")
for r in records:
    p = r["representation"]["points"]
    print(r["id"], len(p), "logM", p[0]["x"], "->", p[-1]["x"], "qf", p[0]["y"], "->", p[-1]["y"])
