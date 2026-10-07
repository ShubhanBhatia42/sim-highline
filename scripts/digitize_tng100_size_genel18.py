import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1707.05327"
DOI = "10.1093/mnras/stx3078"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "f1.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 100, 100)
assert len(fs) == 4
W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]


def fit(labs):
    n = len(labs)
    mp, mv = sum(q for q, _ in labs) / n, sum(v for _, v in labs) / n
    m = sum((q - mp) * (v - mv) for q, v in labs) / sum((q - mp) ** 2 for q, _ in labs)
    c = mv - m * mp
    span = abs(labs[-1][1] - labs[0][1]) or 1.0
    assert all(abs(c + m * q - v) < 0.004 * span for q, v in labs), [round(c + m * q - v, 4) for q, v in labs]
    return lambda q: c + m * q


XL = [("9", 9.0), ("9.5", 9.5), ("10", 10.0), ("10.5", 10.5), ("11", 11.0), ("11.5", 11.5)]
fxs = []
for col in range(2):
    fr = fs[col]
    labs = [(cx, v) for t, cx, cy in W if cy > 395 and fr.x0 - 2 <= cx <= fr.x1 + 2 for tt, v in XL if t == tt]
    assert len(labs) == 6, (col, labs)
    fxs.append(fit(sorted(labs)))
fys = []
for row in range(2):
    fr = fs[2 * row]
    labs = sorted((cy, float(t)) for t, cx, cy in W if t in ("0", "0.5", "1", "1.5") and cx < fr.x0 and fr.y0 - 3 <= cy <= fr.y1 + 1)
    assert len(labs) == 4, (row, labs)
    fys.append(fit(labs))
OWN = {0: (0.0, 0.0, 1.0), 1: (0.0, 0.5, 0.0), 2: (0.85, 0.32, 0.1), 3: (1.0, 0.0, 0.0)}
STY = {"ms": (3.0, "[ 3 3 ]"), "quenched": (2.0, "[ 8 8 ]"), "all": (1.0, "[]")}
POP = {"ms": ("main-sequence galaxies (|dSFMS| < 0.5 dex of the ridge)", "main-sequence"), "quenched": ("quenched galaxies (dSFMS < -1 dex below the ridge)", "quenched"), "all": ("all galaxies", "all")}
SPOT = {("ms", 0): (10.5, 0.35, 0.8), ("all", 0): (11.5, 1.2, 1.6), ("quenched", 1): (10.2, 0.0, 0.4), ("all", 3): (10.0, -0.1, 0.4)}


def polyline(fr, color, width, dash):
    vs = {}
    for d in page.get_drawings():
        if d["type"] != "s" or d["color"] is None or tuple(round(v, 2) for v in d["color"]) != color or abs((d.get("width") or 0) - width) > 0.01:
            continue
        if not (d["dashes"] or "[]").startswith(dash):
            continue
        r = d["rect"]
        if not (fr.x0 - 1 <= r.x0 and r.x1 <= fr.x1 + 1 and fr.y0 - 1 <= r.y0 and r.y1 <= fr.y1 + 1):
            continue
        for it in d["items"]:
            if it[0] in ("l", "c"):
                for p in (it[1], it[-1]):
                    vs[round(p.x, 2)] = p
    return [vs[k] for k in sorted(vs)]


records = []
for z in range(4):
    fr = fs[z]
    fx, fy = fxs[z % 2], fys[z // 2]
    for k, (w, dash) in STY.items():
        pl = polyline(fr, OWN[z], w, dash)
        pts = [(round(fx(p.x), 3), round(fy(p.y), 4)) for p in pl]
        pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
        assert len(pts) >= (3 if k == "quenched" else 10) and all(8.5 < x < 12.0 and -0.3 < y < 1.7 for x, y in pts), (z, k, len(pts), pts[:2])
        if (k, z) in SPOT:
            xa, lo, hi = SPOT[(k, z)]
            yv = min(pts, key=lambda q: abs(q[0] - xa))[1]
            assert lo < yv < hi, (k, z, xa, yv)
        pop, nick = POP[k]
        records.append(vf.record(
            rid=f"genel18.tng100.size.{k}.z{z}", source="IllustrisTNG", run=f"TNG100-1 ({nick}, 3D half-mass size, Genel+18)", relation="size", z=float(z),
            axes={"xDefinition": "log10 stellar mass (all stellar particles assigned to the galaxy)", "xUnit": "log10(Msun)", "yDefinition": "log10 three-dimensional stellar half-mass radius R_star,3D (median)", "yUnit": "log10(kpc)"},
            points=pts, population=pop, interval="unspecified",
            definitions={"massDefinition": "total-subhalo", "imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "population": pop, "sizeDefinition": "3D radius enclosing half of the galaxy's stellar mass"},
            citation=f"Genel et al. 2018, MNRAS 474, 3976 (arXiv:{ARXIV}), median size-mass relations of TNG100 galaxies", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Median size-mass relations in TNG100 (3D half-mass sizes) at z=0, 1, 2, 3", panel=f"z={z} panel, {nick} line", sha=sha, member="f1.pdf", calibration="prediction",
            calib="x: labels 9-11.5 (label centres, bottom row, per column); y: labels 0-1.5 (label centres, left column, per row); least-squares with a residual check",
            warning=f"Median 3D stellar half-mass radius of TNG100-1 {pop} at z={z}, read from the vector line of Genel et al. 2018 (the central quiescent markers and the other redshifts' ghost lines are not extracted). Main-sequence is within 0.5 dex of the redshift-dependent ridge and quenched at least 1 dex below it. The paper states sizes in kpc without saying physical or comoving.", uncertainty=0.02))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "genel18-tng100-size.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} TNG100 size records from Genel+18")
