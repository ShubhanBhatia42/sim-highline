import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2508.21126"
DOI = "10.1093/mnras/stag375"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
CITE = f"Schaye et al. 2026, MNRAS 548, stag375 (arXiv:{ARXIV}), COLIBRE overview"
URL = f"https://arxiv.org/abs/{ARXIV}"
BASE = {"imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "densityFrame": "comoving"}
WARN = "Solid (resolved) part of the curve only: the paper draws the line dotted where galaxies have too few particles, and that part is not extracted. The stellar-mass aperture and halo-mass definition are not stated next to this figure (companion COLIBRE papers use the bound stellar mass within 50 pkpc), so they are recorded as unspecified."
RUNS = {(0.82, 0.14, 0.14): "m7 (L400)", (1.0, 0.62, 0.43): "m6 (L200)", (0.77, 0.91, 1.0): "m5 (L025)"}
records = []


def exp(t):
    return int(t[2:].replace("−", "-"))


def words(page):
    return [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]


def log_fit(page, fr, axis, below):
    W = words(page)
    if axis == "x":
        labs = [(cx, exp(t)) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cy > fr.y1 and fr.x0 - 3 <= cx <= fr.x1 + 3]
    else:
        labs = [(cy, exp(t)) for t, cx, cy in W if t.startswith("10") and len(t) > 2 and cx < fr.x0 and fr.y0 - 3 <= cy <= fr.y1 + 3]
    assert len(labs) >= 3, (axis, labs)
    return vf.axis_fit_log2(page, fr, axis, labs)[0]


def solid(c):
    return c["dashes"].startswith("[ 3.5 0 ]")


def mk(rid, run, rel, z, axes, pts, pop, defs, figure, panel, sha, member, calib, extra, zr=None):
    return vf.record(rid=rid, source="COLIBRE", run=run, relation=rel, z=z, z_range=zr, axes=axes, points=pts, population=pop, interval="unspecified", definitions=dict(BASE, **defs),
                     citation=CITE + f", {figure.lower()}", doi=DOI, url=URL, figure=figure, panel=panel, sha=sha, member=member, calibration="prediction", calib=calib,
                     warning=f"{extra} {WARN}", uncertainty=0.02)


# ---- cosmic SFR density ----
pdf = SRC / "figures" / "sfh_z0p0_plot1.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page, 100, 100)[0]
W = words(page)
xt = vf._tick_positions(page, fr, "x")
zl = [(min(xt, key=lambda q: abs(q - cx)), math.log10(1 + float(t))) for t, cx, cy in W if t in ("0", "0.4", "1", "2", "3", "4", "5", "6", "7", "9", "11", "14", "18") and fr.y1 < cy < fr.y1 + 30]
assert len(zl) == 13, len(zl)
fl, _ = vf.axis_fit(page, fr, "x", labels=zl)
fy = log_fit(page, fr, "y", False)
SF = {("(0.82, 0.14, 0.14)", "[ 3.5 0 ]"): "m7 (L400)", ("(1.0, 0.62, 0.43)", "[ 3.5 0 ]"): "m6 (L200)", ("(0.77, 0.91, 1.0)", "[ 3.5 0 ]"): "m5 (L025)", ("(0.77, 0.91, 1.0)", "[ 9.8 3.5"): "m5 (L050)", ("(0.77, 0.91, 1.0)", "[ 3.5 3.5"): "m5 (L100)"}
got = {}
for c in vf.curves(page, fr, lambda q: q, fy, min_items=8):
    if abs(c["width"] - 3.5) > 0.05:
        continue
    for (col, dash), run in SF.items():
        if str(c["color"]) == col and c["dashes"].startswith(dash):
            got[run] = c
assert len(got) == 5, sorted(got)
SPOT = {"m7 (L400)": ((0.0, -2.1, -1.7), (2.0, -1.25, -1.0), (9.0, -3.3, -2.0))}
for run, c in sorted(got.items()):
    raw = sorted((round(10 ** fl(r.x) - 1, 3), round(y, 4)) for r, (_, y) in zip(c["raw"], c["points"]))
    pts = []
    for x, y in raw:
        if -0.01 <= x <= 20 and -5 < y < -0.3 and (not pts or x > pts[-1][0]):
            pts.append((x, y))
    near = lambda zz: min(pts, key=lambda q: abs(q[0] - zz))[1]
    assert len(pts) >= 10, (run, len(pts))
    for zz, lo, hi in SPOT.get(run, ()):
        assert lo < near(zz) < hi, (run, zz, near(zz))
    records.append(mk(f"schaye25.colibre.sfrd.{run.split()[0]}-{run.split('(')[1][:-1].lower()}", run, "sfrd", min(max(2.0, pts[0][0]), pts[-1][0]),
                      {"xDefinition": "redshift (axis is log10(1+z), converted exactly)", "xUnit": "redshift", "yDefinition": "log10 comoving cosmic star formation rate density", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
                      pts, "all star formation in the simulation volume", dict(sfrIndicator="instantaneous SFR", population="all galaxies in the volume"), "Evolution of the comoving cosmic star formation rate density",
                      f"{run} line", sha, "figures/sfh_z0p0_plot1.pdf", "x: labels 0-18 snapped to ticks in log10(1+z) and converted exactly to z; y: decade labels snapped to ticks (log10)",
                      f"Cosmic SFR density of COLIBRE {run}, z 0 to about 18. The paper notes the m6 and m7 resolutions converge except above z=10, where poorly resolved galaxies dominate.", zr=(pts[0][0], pts[-1][0])))

# ---- specific SFR and stellar-to-halo mass ----
for name, rel, xdef, ydef, yunit, pop, shift, spot in (
        ("ssfr_fixed_z0p0_plot1", "ssfr", "log10 stellar mass", "log10 median specific SFR of star-forming galaxies (sSFR > 1e-2 Gyr^-1; axis in Gyr^-1, converted to yr^-1)", "log10(yr^-1)", "star-forming galaxies, sSFR > 1e-2 Gyr^-1", -9.0, {"m7 (L400)": (10.0, -1.1, -0.6)}),
        ("smhm_z0p0_plot1", "shmr", "log10 halo mass", "log10 median stellar-to-halo mass ratio M*/Mhalo of central galaxies", "dex", "central galaxies", 0.0, {"m7 (L400)": (12.0, -2.4, -1.5)})):
    pdf = SRC / "figures" / f"{name}.pdf"
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frames(page, 100, 100)[0]
    fx = log_fit(page, fr, "x", False)
    fy = log_fit(page, fr, "y", False)
    cs = [c for c in vf.curves(page, fr, fx, fy, min_items=5) if abs(c["width"] - 3.5) < 0.05 and c["color"] in RUNS and solid(c)]
    assert len(cs) == 3, (name, len(cs))
    for c in cs:
        run = RUNS[c["color"]]
        pts = sorted((round(x, 3), round(y + shift, 4)) for x, y in c["points"])
        pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
        assert len(pts) >= 6, (name, run, len(pts))
        if run in spot:
            xa, lo, hi = spot[run]
            v = min(pts, key=lambda q: abs(q[0] - xa))[1] - shift
            assert lo < v < hi, (name, run, xa, v)
        records.append(mk(f"schaye25.colibre.{rel}.{run.split()[0]}-{run.split('(')[1][:-1].lower()}.z0", run, rel, 0.0,
                          {"xDefinition": xdef, "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": yunit}, pts, pop,
                          dict(population=pop, massDefinition="unspecified", **({"sfrStatistic": "median", "sfrTimescaleMyr": "unspecified"} if rel == "ssfr" else {"haloMassDefinition": "unspecified"})),
                          "Median z=0 specific star formation rate" if rel == "ssfr" else "Median z=0 stellar-to-halo mass ratio", f"{run} solid line", sha, f"figures/{name}.pdf",
                          "x and y: decade labels snapped to ticks and validated by the minor-tick pattern; log axes" + ("; y converted from Gyr^-1 to yr^-1 by subtracting 9 dex" if shift else ""),
                          f"Median of COLIBRE {run} {pop} at z=0."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "schaye25-colibre.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} COLIBRE records from Schaye+25")
