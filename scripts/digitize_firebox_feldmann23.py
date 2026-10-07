import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2205.15325"
DOI = "10.1093/mnras/stad1205"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
CITE = f"Feldmann et al. 2023, MNRAS 522, 3831 (arXiv:{ARXIV})"
URL = f"https://arxiv.org/abs/{ARXIV}"
RUN = "FIREbox (FB1024, 22.1 cMpc box)"
DEF = {"imf": "kroupa01", "cosmology": {"H0": 67.74, "Om": 0.3089}, "population": "all galaxies", "densityFrame": "unspecified"}
WARN = "FIREbox abundances are re-weighted to account for cosmic variance of the halo mass function (paper appendix)."
records = []


def snap(page, frame, axis, labs):
    n = len(labs)
    mp, mv = sum(q for q, _ in labs) / n, sum(v for _, v in labs) / n
    m = sum((q - mp) * (v - mv) for q, v in labs) / sum((q - mp) ** 2 for q, _ in labs)
    c = mv - m * mp
    span = abs(labs[-1][1] - labs[0][1]) or 1.0
    assert all(abs(c + m * q - v) < 0.004 * span for q, v in labs), (axis, "labels not on one line", [round(c + m * q - v, 4) for q, v in labs])
    return lambda q: c + m * q


def words(page):
    return [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]


# ---- stellar mass function (fig9a) ----
pdf = SRC / "fig9a.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page, 100, 100)[0]
W = words(page)
xl = [(cx, float(t)) for t, cx, cy in W if t in ("6", "7", "8", "9", "10", "11", "12") and cy > fr.y1]
yw = sorted((cy, t) for t, cx, cy in W if t in ("0", "1", "2", "3", "4", "5") and cx < fr.x0 and cx > 40)
assert len(xl) == 7 and len(yw) == 7, (xl, yw)
yvals = [1.0, 0.0, -1.0, -2.0, -3.0, -4.0, -5.0]
assert [t for _, t in yw] == ["1", "0", "1", "2", "3", "4", "5"]
fx = snap(page, fr, "x", xl)
fy = snap(page, fr, "y", [(cy, v) for (cy, _), v in zip(yw, yvals)])
COL = {(0.7, 0.13, 0.13): 0.0, (1.0, 0.55, 0.0): 2.0, (0.18, 0.55, 0.34): 4.0, (0.0, 0.5, 0.5): 6.0, (0.27, 0.51, 0.71): 8.0, (0.58, 0.0, 0.83): 10.0}
got = {}
for c in vf.curves(page, fr, fx, fy, min_items=8):
    if c["color"] in COL and abs(c["width"] - 2.0) < 0.01 and c["dashes"].startswith("[]"):
        got[COL[c["color"]]] = c
assert sorted(got) == sorted(COL.values()), sorted(got)
SPOT = {0.0: (10.0, -2.1, -1.2), 2.0: (9.0, -2.0, -1.2), 4.0: (7.0, -1.3, -0.5), 8.0: (6.5, -2.0, -0.9)}
for z, c in sorted(got.items()):
    pts = sorted((round(x, 3), round(y, 4)) for x, y in c["points"] if 5.9 <= x <= 12.1 and -5.1 <= y <= 1.1)
    pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
    assert len(pts) >= 6, (z, len(pts))
    if z in SPOT:
        xa, lo, hi = SPOT[z]
        yv = min(pts, key=lambda q: abs(q[0] - xa))[1]
        assert lo < yv < hi, (z, xa, yv)
    records.append(vf.record(
        rid=f"feldmann23.firebox.gsmf.z{z:g}", source="FIREbox", run=RUN, relation="gsmf", z=z,
        axes={"xDefinition": "log10 stellar mass of the galaxy (bound stars within the galaxy radius R_g)", "xUnit": "log10(Msun)", "yDefinition": "log10 differential stellar mass function dn/dlg M", "yUnit": "log10(Mpc^-3 dex^-1)"},
        points=pts, population="all galaxies with M* > 1e6 Msun in the simulation volume", interval="unspecified", definitions=dict(DEF, massDefinition="unspecified"),
        citation=CITE + f", stellar mass function at z={z:g}", doi=DOI, url=URL, figure="Stellar mass function for z=0-10 (left panel, differential)", panel=f"z={z:g} line", sha=sha, member="fig9a.pdf", calibration="prediction",
        calib="x: numeric tick labels 6-12 (label centres; no tick marks are drawn as separate paths); y: tick labels 1 to -5 (minus glyphs are drawn as paths, so signs assigned in order down the axis), label centres",
        warning=f"Differential stellar mass function of FIREbox at z={z:g}, read from the vector line through the bin points of Feldmann et al. 2023 (error bars, the light bins with fewer than four galaxies and the observational estimates are not extracted). {WARN} The comoving or physical frame of the volume is not stated in the figure.", uncertainty=0.02))

# ---- cosmic histories (fig11a SFR density, fig11b stellar mass density) ----
HIST = {
    "sfrd": dict(fig="fig11a.pdf", ylab=("3.0", "2.5", "2.0", "1.5", "1.0", "0.5"), sign=-1.0, ylo=-3.3, yhi=0.0, spot=((0.0, -1.7, -1.2), (2.0, -1.3, -0.8), (6.0, -2.7, -2.0)),
                what="cosmic star formation rate density", yunit="log10(Msun yr^-1 cMpc^-3)", figure="Cosmic star formation history", extra="SFRs averaged over 20 Myr"),
    "smd": dict(fig="fig11b.pdf", ylab=("5.0", "5.5", "6.0", "6.5", "7.0", "7.5", "8.0", "8.5", "9.0"), sign=1.0, ylo=5.0, yhi=9.0, spot=((0.0, 8.4, 8.9), (2.0, 7.9, 8.5), (6.0, 6.0, 7.2)),
                what="cosmic stellar mass density", yunit="log10(Msun cMpc^-3)", figure="Cosmic stellar growth history", extra="stellar mass of the identified galaxies"),
}
for rel, H in HIST.items():
    pdf = SRC / H["fig"]
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frames(page, 100, 100)[0]
    W = words(page)
    zl = [(cx, math.log10(1 + float(t))) for t, cx, cy in W if t in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10") and fr.y1 < cy < fr.y1 + 25]
    yw = sorted((cy, t) for t, cx, cy in W if t in H["ylab"] and cx < fr.x0)
    assert len(zl) == 11 and len(yw) == len(H["ylab"]), (rel, len(zl), yw)
    fl = snap(page, fr, "x", zl)
    fy = snap(page, fr, "y", [(cy, H["sign"] * float(t)) for cy, t in yw])
    cs = vf.curves(page, fr, lambda q: q, fy, min_items=20)

    def pick(color, width, dashed):
        r = [c for c in cs if c["color"] == color and abs(c["width"] - width) < 0.01 and (c["dashes"].startswith("[]") != dashed) and len(c["points"]) > 30]
        assert len(r) == 1, (rel, color, width, len(r))
        return r[0]
    for slug, c, what in (("massive", pick((0.0, 0.0, 0.0), 2.5, False), "galaxies with M* > 10^9.3 Msun (the paper's black line)"), ("all", pick((0.27, 0.51, 0.71), 1.5, True), "all identified galaxies (the paper's blue dot-dashed line)")):
        raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(c["raw"], c["points"]))
        pts = []
        for x, y in raw:
            if -0.01 <= x <= 10.5 and H["ylo"] < y < H["yhi"] and (not pts or x > pts[-1][0]):
                pts.append((x, y))
        near = lambda zz: min(pts, key=lambda q: abs(q[0] - zz))[1]
        assert len(pts) > 30 and pts[0][0] < 0.1, (rel, slug, len(pts), pts[0])
        if slug == "massive":
            for zz, lo, hi in H["spot"]:
                assert lo < near(zz) < hi, (rel, zz, near(zz))
        records.append(vf.record(
            rid=f"feldmann23.firebox.{rel}.{slug}", source="FIREbox", run=RUN + f", {slug} galaxies", relation=rel, z=2.0,
            axes={"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": f"log10 {H['what']} of {what}", "yUnit": H["yunit"]},
            points=pts, population=what, interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
            definitions=dict(DEF, sfrIndicator="SFR averaged over the past 20 Myr", densityFrame="comoving", sfrTimescaleMyr=20) if rel == "sfrd" else dict(DEF, densityFrame="comoving"),
            citation=CITE + f", {H['figure'].lower()}", doi=DOI, url=URL, figure=H["figure"], panel=f"{slug} galaxies line", sha=sha, member=H["fig"], calibration="prediction",
            calib="x: labels 0-10 (label centres) in log10(1+z), converted exactly to z; y: tick labels (minus glyphs drawn as paths, so signs assigned where needed), label centres",
            warning=f"{H['what'].capitalize()} of FIREbox for {what}, {H['extra']}, read from the vector path of Feldmann et al. 2023 (stellar-mass-bin contributions and the observational compilation are not extracted). {WARN}", uncertainty=0.02))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "feldmann23-firebox.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FIREbox records from Feldmann+23")
