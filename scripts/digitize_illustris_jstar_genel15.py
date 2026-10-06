import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1503.01117"
DOI = "10.1088/2041-8205/804/2/L40"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
EPS = next(SRC.rglob("f1.eps"))
PDF = SRC / "pdf" / "f1.pdf"
if not PDF.exists():
    PDF.parent.mkdir(exist_ok=True)
    subprocess.run(["epstopdf", str(EPS), f"--outfile={PDF}"], check=True)
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
grid = vf.grid_from_long_lines(page, 100)
panels = grid[0][::2]
assert len(panels) == 3, panels
fxs = [vf.axis_fit(page, pn, "x")[0] for pn in panels]
fy, yt = vf.axis_fit(page, panels[0], "y")
assert len(yt) >= 4
assert all(abs(p.y0 - panels[0].y0) < 0.5 and abs(p.y1 - panels[0].y1) < 0.5 for p in panels), "panels share the y axis"
BLACK, CYAN, MAGENTA = (0.0, 0.0, 0.0), (0.0, 0.75, 0.75), (0.75, 0.0, 0.75)
LEG = [("all galaxies", "all galaxies", "all"), ("flat", "extreme axial ratio: flat", "selected on axial ratio (flat)"), ("round", "extreme axial ratio: round", "selected on axial ratio (round)"),
       ("diffuse", "extreme morphology: diffuse", "selected on morphology (diffuse)"), ("concentrated", "extreme morphology: concentrated", "selected on morphology (concentrated)"),
       ("star-forming", "extreme sSFR: star-forming", "selected on specific SFR (star-forming)"), ("quiescent", "extreme sSFR: quiescent", "selected on specific SFR (quiescent)")]
words = page.get_text("words")
for k, names in enumerate((("flat", "round"), ("diffuse", "concentrated"), ("star-forming", "quiescent"))):
    for nm in names:
        w = next(w for w in words if w[4] == nm and panels[k].x0 - 3 < w[0] < panels[k].x1 + 3)
        assert w is not None
close = lambda c, t: c is not None and all(abs(u - v) < 0.02 for u, v in zip(c, t))
lines = {}
for k, pn in enumerate(panels):
    for d in page.get_drawings():
        r = d["rect"]
        if d["type"] != "s" or len(d["items"]) < 8 or abs((d.get("width") or 0) - 3.0) > 0.05 or not (pn.x0 < (r.x0 + r.x1) / 2 < pn.x1):
            continue
        col = next((n for n, c in (("black", BLACK), ("cyan", CYAN), ("magenta", MAGENTA)) if close(d["color"], c)), None)
        if col:
            lines[(k, col)] = [(fxs[k](p.x), fy(p.y)) for p in [d["items"][0][1]] + [i[2] for i in d["items"]]]
assert len(lines) == 9, sorted(lines)
for k in (1, 2):
    assert all(abs(a[0] - b[0]) < 0.02 and abs(a[1] - b[1]) < 0.02 for a, b in zip(lines[(0, "black")], lines[(k, "black")])), "the all-galaxies curve must be the same in every panel"
SEL = {"all galaxies": (0, "black"), "extreme axial ratio: flat": (0, "cyan"), "extreme axial ratio: round": (0, "magenta"), "extreme morphology: diffuse": (1, "cyan"),
       "extreme morphology: concentrated": (1, "magenta"), "extreme sSFR: star-forming": (2, "cyan"), "extreme sSFR: quiescent": (2, "magenta")}
records = []
for _, run, what in LEG:
    pts = lines[SEL[run]]
    assert all(a[0] < b[0] for a, b in zip(pts, pts[1:])) and all(1.5 < y < 4.2 for _, y in pts), run
    tag = "all" if run == "all galaxies" else run.split(": ")[-1]
    records.append(vf.record(
        rid=f"genel15.illustris.jstar.{tag}.z0", source="Illustris", run=f"Illustris-1 ({run})", relation="jstar", z=0.0,
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 logarithmic mean stellar specific angular momentum j* [kpc km/s]", "yUnit": "log10(kpc km/s)"},
        points=pts, population=f"Illustris galaxies, {what}", interval="unspecified",
        definitions={"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.2726}, "massDefinition": "unspecified", "population": "all", "jDefinition": "unspecified (stellar j* of Illustris galaxies)"},
        citation=f"Genel et al. 2015, ApJ 804, L40 (arXiv:{ARXIV}), stellar specific angular momentum versus stellar mass, z=0", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="z=0 relation between stellar specific angular momentum and stellar mass", panel="z=0", sha=sha, member=f"{EPS.name} (converted to PDF)", calibration="prediction",
        calib="x: numeric tick labels of each panel; y: numeric tick labels of the left panel (shared axis, panel extents asserted equal)",
        warning=f"Logarithmic mean j* ({what}) of Illustris galaxies at z=0, read from the vector paths of Genel et al. 2015; no table exists. The paper states the median curves are essentially indistinguishable from the means. "
                "The Fall and Romanowsky 2013 observed relations, the grey full distribution and the visually classified galaxies (squares) are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "genel15-illustris-jstar.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Illustris j*-M* records from Genel+15")
