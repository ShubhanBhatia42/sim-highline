import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1410.3485"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
RUNS = {(0.2, 0.13, 0.53): ("ref", "Ref-L100N1504"), (0.07, 0.47, 0.2): ("recal", "Recal-L025N0752")}
ZS = [0.1, 1.0, 2.0]
THRESHOLD = {0.1: 0.01, 1.0: 0.1, 2.0: 0.1}

ssfr = vf.page_of(SRC / "ssfr.pdf")
sfr = vf.frames(ssfr)
assert len(sfr) == 3
lab = [((w[1] + w[3]) / 2, math.log10(float(w[4]))) for w in ssfr.get_text("words") if w[4] in ("0.01", "0.1", "1.0") and w[0] < 60]
fys, _ = vf.axis_fit(ssfr, sfr[0], "y", labels=lab)
lines = {}
for d in ssfr.get_drawings():
    its = d["items"]
    if d["color"] == (0.0, 0.0, 0.0) and d["dashes"] == "[ 1 3 ] 0" and len(its) <= 3 and all(i[0] == "l" for i in its) \
            and abs(its[0][1].y - its[0][2].y) < 0.01 and abs(its[0][1].x - its[0][2].x) > 50:
        i = next(k for k, r in enumerate(sfr) if r.x0 - 1 <= its[0][1].x <= r.x1)
        lines[i] = 10 ** fys(its[0][1].y)
for i, z in enumerate(ZS):
    assert abs(lines[i] / THRESHOLD[z] - 1) < 0.02, (z, lines[i])

PDF = SRC / "passive.pdf"
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)
assert len(fr) == 3
fx0, fy, cal = vf.calibrate(page, fr[0])
assert [v for _, v in cal["xTicks"]] == [7, 8, 9, 10, 11, 12] and [v for _, v in cal["yTicks"]] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
words = page.get_text("words")
records = []
for i, (z, r) in enumerate(zip(ZS, fr)):
    fx = vf.shifted(fx0, r.x0 - fr[0].x0)
    if i:
        vf.check_labels(page, r, "x", fx)
    label = f"z={z:.1f}"
    assert any(w[4] == label and r.x0 <= w[0] <= r.x1 for w in words), label
    crit = "ssfr<1e-11" if THRESHOLD[z] == 0.01 else "ssfr<1e-10"
    for c in vf.curves(page, r, fx, fy, min_items=6):
        if c["color"] not in RUNS or c["dashes"] != "[] 0" or c["width"] != 2.0:
            continue
        key, run = RUNS[c["color"]]
        pts = c["points"]
        assert all(-0.01 <= y <= 1.01 for _, y in pts) and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (z, run)
        records.append(vf.record(
            rid=f"furlong15.eagle-{key}.quenched.z{z:g}", source="EAGLE", run=run, relation="quenched", z=z,
            axes={"xDefinition": "log10 stellar mass (3D 30 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": "passive fraction (sSFR below the limit given in the definitions)", "yUnit": "fraction"},
            points=pts, population="all galaxies",
            warning=f"Solid segment only of the curve in Furlong et al. 2015 Fig. 6 ({label} panel): bins with >=30 star-forming particles at the sSFR limit; the dotted low-mass segment (an acknowledged numerical artefact below 10^9 Msun) is omitted. "
                    f"Passive means sSFR below the dotted limit of the sSFR figure, read here as {lines[i] * 1e-9:.1e} /yr. The paper gives no table.",
            definitions={"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "population": "all", "quenchingCriterion": crit,
                         "sfrTimescaleMyr": "instantaneous (gas SFR within 30 pkpc)"},
            citation="Furlong et al. 2015, MNRAS 450, 4486, Fig. 6 (arXiv source numbering)", doi="10.1093/mnras/stv852", url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Figure 6", panel=f"panel {i + 1} ({label})", sha=sha, member=f"{PDF.name} (solid {run} line, 2 pt stroke); threshold from ssfr.pdf dotted line",
            calib="x: labelled ticks 7-12; y: labelled ticks 0-1; panels share axes (offset by frame origin; labels asserted); threshold: log axis from labels 0.01/0.1/1.0 Gyr^-1",
            calibration="prediction"))
assert len(records) == 6, len(records)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "furlong15-eagle-passive.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE passive-fraction records; sSFR limits read: {[f'{v:.3g}' for v in lines.values()]} /Gyr")
