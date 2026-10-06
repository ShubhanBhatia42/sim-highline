import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2002.07226"
DOI = "10.1093/mnras/staa1894"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "ms_sfr_m100n1024.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 100, 100)
assert len(fs) == 2
fx, xt = vf.axis_fit(page, fs[1], "x")


def fy_of(frame):
    ws = sorted(((w[1] + w[3]) / 2, -float(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and 40 < (w[0] + w[2]) / 2 < 60 and frame.y0 - 2 <= (w[1] + w[3]) / 2 <= frame.y1 + 2)
    ticks = vf._tick_positions(page, frame, "y")
    lab = [(min(ticks, key=lambda t: abs(t - cy)), v) for cy, v in ws]
    return vf.axis_fit(page, frame, "y", labels=lab)[0]


RUNS = {(0.0, 0.0, 1.0): ("SIMBA", "m100n1024 (all galaxies, Dave+20)", {"H0": 68.0, "Om": 0.3}, "Dave+20 SIMBA"), (0.86, 0.08, 0.24): ("IllustrisTNG", "TNG100-1 (all galaxies, Dave+20)", {"H0": 67.74, "Om": 0.3089}, "TNG100"), (0.0, 0.5, 0.0): ("EAGLE", "Ref-L100N1504 (all galaxies, Dave+20)", {"H0": 67.77, "Om": 0.307}, "EAGLE")}
records = []
fy0, fy1 = fy_of(fs[0]), fy_of(fs[1])
cs = vf.curves(page, fs[0], fx, fy0, min_items=10)
for col, (src, run, cosmo, nm) in RUNS.items():
    c = [k for k in cs if k["color"] == col and k["width"] == 1.5 and (k["opacity"] in (None, 1.0))]
    assert len(c) == 1, (nm, len(c))
    pts = vf.clip(c[0]["points"], 9.0, 12.5, -6.5, -1.5)
    pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
    ys = {round(x * 2) / 2: y for x, y in pts}
    assert len(pts) >= 15 and -2.3 < ys[9.5] < -1.7 and ys[11.0] < -2.6, (nm, ys.get(9.5), ys.get(11.0))
    records.append(vf.record(
        rid=f"dave20.{src.lower()}.gsmf.{run.split(' ')[0].lower()}.z0", source=src, run=run, relation="gsmf", z=0.0,
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function (axis labelled Mpc^-3; per-dex normalisation and comoving frame not stated in the figure)", "yUnit": "log10(Mpc^-3)"},
        points=pts, population="all galaxies", interval="unspecified",
        definitions={"massDefinition": "unspecified", "imf": "unspecified", "cosmology": cosmo, "densityFrame": "unspecified", "population": "all"},
        citation=f"Dave et al. 2020, MNRAS 497, 146 (arXiv:{ARXIV}), stellar mass function at z=0", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Galaxy stellar mass function (top) and sSFR versus stellar mass (bottom) at z=0", panel="top panel", sha=sha, member="ms_sfr_m100n1024.pdf", calibration="prediction",
        calib="x: numeric tick labels snapped to ticks; y: positive tick words negated (minus glyphs are separate) and paired with ticks",
        warning=f"z=0 stellar mass function of {run} read from the vector paths of Dave et al. 2020. The SIMBA shaded variance over 8 sub-octants and the Wright+17 points are not extracted."))
markers = {}
for d in page.get_drawings():
    if d["type"] == "fs" and d["fill"] is not None and len(d["items"]) == 8:
        col = tuple(round(v, 2) for v in d["fill"])
        r = d["rect"]
        if col in RUNS and 5 < r.width < 7 and fs[1].x0 < r.x0 < fs[1].x1 and fs[1].y0 < r.y0 < fs[1].y1 and not (r.x0 < 150 and r.y0 > 255 + 0 and r.y0 < 0):
            markers.setdefault(col, []).append((fx((r.x0 + r.x1) / 2), fy1((r.y0 + r.y1) / 2) - 9.0))
for col, (src, run, cosmo, nm) in RUNS.items():
    pts = sorted(set((round(x, 3), round(y, 4)) for x, y in markers[col]))
    assert len(pts) >= 5 and all(9.0 < x < 12.2 and -11.5 < y < -9.0 for x, y in pts), (nm, pts)
    if src == "SIMBA":
        assert abs(pts[0][1] + 9.5) < 0.1 and abs(pts[-1][1] + 10.69) < 0.1, pts
    records.append(vf.record(
        rid=f"dave20.{src.lower()}.ssfr.{run.split(' ')[0].lower()}.z0", source=src, run=run, relation="ssfr", z=0.0,
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 median specific star formation rate of galaxies above the sSFR cut", "yUnit": "log10(yr^-1)"},
        points=pts, population="galaxies with sSFR > 10^-1.8 Gyr^-1 (running median)", interval="unspecified", connect=False, scatter=True,
        definitions={"massDefinition": "unspecified", "imf": "unspecified", "cosmology": cosmo, "population": "star-forming (sSFR cut)", "sfrStatistic": "median", "sfrTimescaleMyr": "unspecified"},
        citation=f"Dave et al. 2020, MNRAS 497, 146 (arXiv:{ARXIV}), specific star formation rate versus stellar mass at z=0", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Galaxy stellar mass function (top) and sSFR versus stellar mass (bottom) at z=0", panel="bottom panel", sha=sha, member="ms_sfr_m100n1024.pdf", calibration="prediction",
        calib="x: numeric tick labels snapped to ticks; y: as the top panel; the axis is labelled in Gyr^-1 and converted exactly by subtracting 9 dex",
        warning=f"Running median sSFR of {run} for galaxies above sSFR = 10^-1.8 Gyr^-1 at z=0, marker centres read from the vector paths of Dave et al. 2020 (axis in Gyr^-1, converted to yr^-1). The 1-sigma error bars and the xGASS points are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dave20-gsmf-ssfr.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} GSMF and sSFR records from Dave+20")
