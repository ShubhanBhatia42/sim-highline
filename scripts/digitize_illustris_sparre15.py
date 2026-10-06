import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1409.0009"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "Fig81_MainSequence_Evolution.pdf"
ZS = [0.0, 1.0, 2.0, 4.0]
RUNS = {"blue": ((0.0, 0.0, 1.0), "Illustris-1", "illustris-1"), "green": ((0.0, 0.5, 0.0), "Illustris-1 low resolution", "illustris-lowres")}
COSMO = {"H0": 70.4, "Om": 0.2726}


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


def numlabels(words, pick):
    out = []
    for w in words:
        s = w[4].replace("−", "-")
        if re.fullmatch(r"-?\d+(\.\d+)?", s) and pick(w) is not None:
            out.append((pick(w), float(s)))
    return sorted(out)


page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)
assert len(fr) == 8
words = page.get_text("words")
drs = page.get_drawings()
fxs = []
for i in range(4):
    bf = fr[4 + i]
    lab = numlabels(words, lambda w, f=bf: (w[0] + w[2]) / 2 if w[1] > f.y1 and f.x0 - 2 <= (w[0] + w[2]) / 2 <= f.x1 + 2 else None)
    fx, xt = vf.axis_fit_shifted(page, bf, "x", lab)
    assert len(xt) >= 4, (i, xt)
    fxs.append(fx)
fys = []
for row in (0, 1):
    lf = fr[4 * row]
    lab = numlabels(words, lambda w, f=lf: (w[1] + w[3]) / 2 if w[0] < f.x0 and f.y0 - 2 <= (w[1] + w[3]) / 2 <= f.y1 + 2 else None)
    lab = [(p, v) for p, v in lab if not (row == 1 and v == -2.0)]
    fy, yt = vf.axis_fit_shifted(page, lf, "y", lab)
    assert len(yt) >= 4, (row, yt)
    fys.append(fy)
RELS = {0: ("sfms", "log10 SFR (instantaneous, gas)", "log10(Msun/yr)"), 1: ("ssfr", "log10 specific SFR (instantaneous, gas)", "log10(1/yr)")}
records = []
for row in (0, 1):
    for i, z in enumerate(ZS):
        frame = fr[4 * row + i]
        fx, fy = fxs[i], fys[row]
        xlo, xhi, ylo, yhi = fx(frame.x0), fx(frame.x1), min(fy(frame.y0), fy(frame.y1)), max(fy(frame.y0), fy(frame.y1))
        for rkey, (color, run, rid) in RUNS.items():
            lines = [c for c in vf.curves(page, frame, fx, fy, min_items=4) if near(c["color"], color) and c["width"] in (3.0, 2.0) and (c["dashes"] == "[] 0") == (rkey == "blue")]
            assert len(lines) == 1, (row, z, rkey, len(lines))
            med = [(x, y) for x, y in lines[0]["points"] if xlo <= x <= xhi]
            bars = []
            for d in drs:
                if d["type"] == "s" and near(d["color"], color) and len(d["items"]) == 1 and abs(d["items"][0][1].x - d["items"][0][2].x) < 0.01 and frame.x0 <= d["items"][0][1].x <= frame.x1:
                    a, b = d["items"][0][1], d["items"][0][2]
                    bars.append((fx(a.x), fy(a.y), fy(b.y)))
            pts = []
            for x, y in med:
                m = [(abs(bx - x), lo, hi) for bx, lo, hi in bars if abs(bx - x) < 0.05 and abs((lo + hi) / 2 - y) < 1.0]
                p = {"x": round(x, 3), "y": round(y, 4)}
                if m:
                    _, lo, hi = min(m)
                    p.update({"yLow": round(min(lo, hi), 4), "yHigh": round(max(lo, hi), 4)})
                pts.append(p)
            assert len(pts) >= 4 and all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])), (row, z, rkey)
            rel, ydef, yunit = RELS[row]
            records.append(vf.record(
                rid=f"sparre15.{rid}.{rel}-median.z{z:g}", source="Illustris", run=f"{run} (median, all galaxies)", relation=rel, z=z,
                axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": ydef + " (median)", "yUnit": yunit},
                points=pts, population="all galaxies in narrow stellar-mass bins", interval="uncertainty",
                warning=f"Median curve and 1-sigma error bars (Gaussian fits to the SFR distributions in narrow mass bins, per the caption) read from the vector paths of Sparre et al. 2015 (MNRAS 447, 3548), Fig. 8.1 ({'SFR' if row == 0 else 'sSFR'} panel, z={z:g}); no table exists. "
                        "Error bars attached where a drawn bar matches the vertex. The Behroozi+13 observational points and the 2D histogram are not extracted.",
                definitions={"massDefinition": "unspecified", "imf": "chabrier03", "cosmology": COSMO, "sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median", "population": "all"},
                citation=f"Sparre et al. 2015, MNRAS 447, 3548, main-sequence evolution figure (Fig81), z={z:g}", doi="10.1093/mnras/stu2713", url=f"https://arxiv.org/abs/{ARXIV}",
                figure="Fig81_MainSequence_Evolution", panel=f"{'top' if row == 0 else 'bottom'} row, z={z:g}", sha=sha, member=f"{PDF.name} ({run} median)",
                calib="x: labelled ticks per column (bottom row); y: labelled ticks of the left panel of each row; asserted", calibration="prediction"))
assert len(records) == 16
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "sparre15-illustris-sfms.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Illustris SFMS and sSFR median records (z=0,1,2,4; two resolutions) from Sparre+15 vector paths")
