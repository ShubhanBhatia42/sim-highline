import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2509.07960"
DOI = "10.1093/mnras/stag740"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
CITE = f"Chaikin et al. 2026, MNRAS 548, stag740 (doi:{DOI}; arXiv:{ARXIV}), COLIBRE galaxy stellar mass functions, star formation and quenching"
URL = f"https://arxiv.org/abs/{ARXIV}"
BASE = {"imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "densityFrame": "comoving"}
RUNS = {(0.82, 0.14, 0.14): "L400m7", (1.0, 0.62, 0.43): "L200m6", (0.77, 0.91, 1.0): "(L025, L050 or L100)m5"}
SOLID, DASHDOT = "[ 2 0 ]", "[ 8 2 2 2 ]"
SEL = {SOLID: ("all stars", "all star particles", "all stellar mass in the simulated volume (the paper's raw simulation value)"),
       DASHDOT: ("50 pkpc, M* >= 1e8", "bound stars within 50 pkpc 3D apertures of galaxies with M* >= 1e8 Msun", "stars within 50 pkpc 3D apertures of galaxies with M* >= 1e8 Msun (the paper's selection that can be compared with observations)")}
records = []

pdf = SRC / "plots" / "SMD.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
top, bot = vf.frames(page, 100, 60)[:2]
assert top.x0 == bot.x0 and top.x1 == bot.x1 and abs(top.y1 - bot.y0) < 0.5, (top, bot)
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
xt = vf._tick_positions(page, bot, "x")
zl = [(min(xt, key=lambda q: abs(q - cx)), math.log10(1 + float(t))) for t, cx, cy in W if t in ("0", "0.2", "0.5", "1", "2", "3", "4", "5", "6", "7", "9", "11", "14", "18") and bot.y1 < cy < bot.y1 + 30]
assert len(zl) == 14, len(zl)
fl, _ = vf.axis_fit(page, bot, "x", labels=zl)
yl = [(cy, int(t[2:])) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < top.x0 and top.y0 - 3 <= cy <= top.y1 + 3]
assert len(yl) == 5, yl
fy, _ = vf.axis_fit_log2(page, top, "y", yl)
ylo, yhi = fy(top.y1), fy(top.y0)
got = {}
for c in vf.curves(page, top, lambda q: q, fy, min_items=8):
    if abs(c["width"] - 2.0) > 0.05 or c["color"] not in RUNS:
        continue
    for dash in (SOLID, DASHDOT):
        if c["dashes"].startswith(dash):
            got[(RUNS[c["color"]], dash)] = c
assert len(got) == 6, sorted(got)
SPOT = {("L200m6", SOLID): ((0.0, 8.3, 8.6), (2.0, 7.8, 8.2), (9.0, 4.6, 5.9))}
AX = {"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 comoving cosmic stellar mass density", "yUnit": "log10(Msun cMpc^-3)"}
for (run, dash), c in sorted(got.items()):
    raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(c["raw"], c["points"]))
    pts = []
    for x, y in raw:
        if -0.01 <= x <= 20 and ylo + 0.02 < y < yhi - 0.02 and (not pts or x > pts[-1][0]):
            pts.append((x, y))
    assert len(pts) >= 10, (run, dash, len(pts))
    near = lambda zz: min(pts, key=lambda q: abs(q[0] - zz))
    for zz, lo, hi in SPOT.get((run, dash), ()):
        x, v = near(zz)
        assert abs(x - zz) < 0.3 and lo < v < hi, (run, dash, zz, x, v)
    tag, mdef, what = SEL[dash]
    slug = run.split()[0].strip("(,").lower() if run != "(L025, L050 or L100)m5" else "m5"
    kind = "all" if dash == SOLID else "50pkpc-m8"
    records.append(vf.record(
        rid=f"chaikin26.colibre.smd.{slug}.{kind}", source="COLIBRE", run=f"{run} ({tag})", relation="smd", z=min(max(2.0, pts[0][0]), pts[-1][0]), z_range=(pts[0][0], pts[-1][0]), axes=AX, points=pts,
        population="all stars in the simulation volume" if dash == SOLID else "stars in galaxies with M* >= 1e8 Msun", interval="unspecified",
        definitions=dict(BASE, massDefinition=mdef, population="all stars in the volume" if dash == SOLID else "galaxies with M* >= 1e8 Msun"),
        citation=CITE + ", cosmic stellar mass density", doi=DOI, url=URL, figure="Evolution of the cosmic stellar mass density (CSMD)", panel=f"{run} {'solid' if dash == SOLID else 'dash-dotted'} line", sha=sha,
        member="plots/SMD.pdf", calibration="prediction", uncertainty=0.02,
        calib="x: labels 0-18 snapped to ticks in log10(1+z) and converted exactly to z; y: decade labels snapped to ticks and validated by the minor-tick pattern (log)",
        warning=f"Cosmic stellar mass density of COLIBRE {run}, {what}, read from the vector paths of Chaikin et al. 2026 (CSMD figure, top panel). "
                "The paper truncates the L400m7 and m5 lines at z < 4 for clarity because they overlap the L200m6 line; the m5 line is drawn from the L025, L050 or L100 box (the legend does not say which at each redshift). "
                "Observational compilation, residual panel and the black outline of each line are not extracted. Parts of the lines below the lowest labelled density are outside the plot and not recorded."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "chaikin26-colibre-smd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} COLIBRE cosmic stellar mass density records from Chaikin+26")
for r in records:
    p = r["representation"]["points"]
    print(r["id"], len(p), "z", p[0]["x"], "->", p[-1]["x"], "log SMD", p[0]["y"], "->", p[-1]["y"])
