import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pymupdf
import vector_figure as vf

ARXIV = "2009.10578"
DOI = "10.1051/0004-6361/202039429"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
COL = {(1.0, 0.0, 0.0): 4.0, (0.5996, 0.8301, 0.0): 2.0, (0.0, 0.498, 1.0): 1.0, (0.5488, 0.0, 0.8301): 0.25}
Z0 = {"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.272}, "massDefinition": "unspecified", "population": "all"}
MASSAX = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)"}
SOLID, DASHED = "[] 0", "[ 5.6693 5.6693 ] 0"
cite = lambda fig, z: f"Dubois et al. 2021, A&A 651, A109 (arXiv:{ARXIV}), {fig}, z={z:g}"
close = lambda c, t, tol=0.02: c is not None and all(abs(a - b) < tol for a, b in zip(c, t))
records = []


def numlab(w):
    return float(w[4].replace("−", "-")) if re.fullmatch(r"[−-]?\d+(\.\d+)?", w[4]) else None


def xlog_labels(page, fr):
    return sorted(((w[0] + w[2]) / 2, float(w[4][2:])) for w in page.get_text("words") if re.fullmatch(r"10\d{1,2}", w[4]) and w[1] > fr.y1)


def ylog_labels(page, fr):
    return [(p, math.log10(v)) for p, v in sorted(((w[1] + w[3]) / 2, numlab(w)) for w in page.get_text("words") if numlab(w) is not None and w[2] < fr.x0 and fr.y0 - 8 < (w[1] + w[3]) / 2 < fr.y1 + 8)]


def mean_band(page, fr, match, fy, fx):
    """Solid mean line and the dashed pair sharing its vertices; returns [(x, y, ylo, yhi)] in page-mapped data coordinates."""
    solid, dashed = [], []
    for d in page.get_drawings():
        its = d["items"]
        if not match(d) or len(its) < 3 or any(i[0] != "l" for i in its):
            continue
        pts = [its[0][1]] + [i[2] for i in its]
        if not (fr.x0 - 1 <= pts[0].x and pts[-1].x <= fr.x1 + 1 and pts[0].x < pts[-1].x):
            continue
        (solid if d["dashes"] == SOLID else dashed).append(pts)
    out = []
    for s in solid:
        pair = [dl for dl in dashed if len(dl) == len(s) and all(abs(a.x - b.x) < 0.3 for a, b in zip(dl, s))]
        if len(pair) != 2:
            continue
        out.append([(fx(p.x), fy(p.y), *sorted((fy(pair[0][i].y), fy(pair[1][i].y)))) for i, p in enumerate(s)])
    return out


def rec_points(rows, tf=lambda y: y, swap=False):
    pts = []
    for x, y, lo, hi in rows:
        a, b, c = tf(y), tf(lo), tf(hi)
        pts.append({"x": round(x, 3), "y": round(a, 4), "yLow": round(min(b, c), 4), "yHigh": round(max(b, c), 4)})
    return pts


# ---- sizes (4 snapshots) ----
SNAP = {"00110": 4.0, "00251": 2.0, "00446": 1.0, "00925": 0.25}
pages = {s: (next(SRC.rglob(f"reffvsmstar_{s}-eps-converted-to.pdf"))) for s in SNAP}
pg = {s: vf.page_of(p) for s, p in pages.items()}
frs = {s: vf.frame_from_long_lines(pg[s]) for s in SNAP}
assert all(abs(frs[s].x0 - frs["00925"].x0) < 0.1 and abs(frs[s].y1 - frs["00925"].y1) < 0.1 for s in SNAP)
fr = frs["00925"]
fx, _ = vf.axis_fit_log2(pg["00925"], fr, "x", xlog_labels(pg["00925"], fr))
fy, _ = vf.axis_fit_log2(pg["00110"], fr, "y", ylog_labels(pg["00110"], fr), snap=7.0)
for s, z in SNAP.items():
    page = pg[s]
    zw = [w for w in page.get_text("words") if w[4].startswith("z=")][0]
    assert abs(float(zw[4][2:]) - z) < 1e-9, (s, zw[4])
    rows = mean_band(page, fr, lambda d: close(d["color"], (0, 0, 0)) and abs((d.get("width") or 0) - 1.4) < 0.05, fy, fx)
    assert len(rows) == 1, (s, len(rows))
    gal = sorted((fx((d["rect"].x0 + d["rect"].x1) / 2), fy((d["rect"].y0 + d["rect"].y1) / 2)) for d in page.get_drawings()
                 if close(d["color"], (0.55, 0.55, 0.55)) and len(d["items"]) == 4 and d["rect"].width < 8 and d["rect"].height < 8 and fr.contains(d["rect"]))
    assert len(gal) > 300, (s, len(gal))
    sha = vf.sha256(pages[s])
    axes = {**MASSAX, "yDefinition": "log10 effective radius R_eff [kpc], geometric mean of the three projected half-mass radii", "yUnit": "log10(kpc)"}
    defs = {**Z0, "sizeDefinition": "stellar-half-mass-projected", "population": "AdaptaHOP galaxies (clumps removed)"}
    common = dict(source="NewHorizon", relation="size", z=z, axes=axes, definitions=defs, citation=cite("effective radius versus stellar mass", z), doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
                  figure="effective radius versus stellar mass", panel=f"z={z:g}", sha=sha, member=pages[s].name, calibration="prediction",
                  calib="x: labelled decades of the z=0.25 panel (shared frame, asserted identical); y: labelled decades of the z=4 panel; both validated by the minor-tick pattern")
    pts = rec_points(rows[0])
    assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and all(p["yLow"] <= p["y"] + 1e-6 <= p["yHigh"] + 1e-6 for p in pts)
    records.append(vf.record(rid=f"dubois21.newhorizon.size.z{z:g}", run="NewHorizon", points=pts, population="AdaptaHOP galaxies", interval="uncertainty",
                             warning=f"Mean R_eff in stellar-mass bins (solid black line) with the dashed lines at z={z:g}, read from the vector paths of Dubois et al. 2021; no table exists. The caption calls the dashed lines the standard deviation while the text calls them the error around the mean, so the band is stored as an uncertainty of unstated kind. Observational overlays (Mowla+19) are not extracted.", **common))
    records.append(vf.record(rid=f"dubois21.newhorizon.size-galaxies.z{z:g}", run="NewHorizon (per galaxy)", points=gal, population="individual AdaptaHOP galaxies (zoom, not volume complete)", interval="scatter", connect=False, strict=False,
                             warning=f"Marker centres (grey crosses) of the simulated galaxies at z={z:g} read from the vector paths of Dubois et al. 2021; no table exists. Zoom region, not volume complete. Crosses clipped by the frame edge are not included.", **common))

# ---- baryonic Tully-Fisher (axes swapped to the sim-highline orientation: x velocity, y baryonic mass) ----
pdf = next(SRC.rglob("tullyfishermgal_2reff-eps-converted-to.pdf"))
page = vf.page_of(pdf)
fr = vf.frame_from_long_lines(page)
fx, _ = vf.axis_fit_log2(page, fr, "x", xlog_labels(page, fr))
fy, _ = vf.axis_fit_log2(page, fr, "y", ylog_labels(page, fr), snap=7.0)
sha = vf.sha256(pdf)
rows_by_z = {}
for ckey, z in COL.items():
    r = mean_band(page, fr, lambda d, ck=ckey: close(d["color"], ck, 0.01) and abs((d.get("width") or 0) - 1.4) < 0.05, lambda p: p, lambda p: p)
    assert len(r) == 1, (z, len(r))
    rows_by_z[z] = r[0]
tf_axes = {"xDefinition": "log10 circular velocity V_g,f (flat part of the gas rotation curve)", "xUnit": "log10(km/s)", "yDefinition": "log10 baryonic mass M_b", "yUnit": "log10(Msun)"}
tf_defs = {**Z0, "massDefinition": "aperture-2Reff-baryons", "velocityDefinition": "gas rotation velocity, flat part (V_g,f), within 2 R_eff", "population": "disc galaxies"}
for z, rows in sorted(rows_by_z.items(), reverse=True):
    pts = []
    for px, py, a, b in rows:
        mb, v, vlo, vhi = fx(px), fy(py), *sorted((fy(a), fy(b)))
        pts.append({"x": round(v, 3), "y": round(mb, 3), "xLow": round(min(vlo, vhi), 3), "xHigh": round(max(vlo, vhi), 3)})
    mono = all(a["x"] < b["x"] for a, b in zip(pts, pts[1:]))
    common = dict(source="NewHorizon", relation="btfr", z=z, axes=tf_axes, definitions=tf_defs, citation=cite("baryonic Tully-Fisher relation", z), doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
                  figure="baryonic Tully-Fisher relation", panel=f"z={z:g}", sha=sha, member=pdf.name, calibration="prediction", calib="x: labelled decades validated by the minor-tick pattern; y: labelled decades")
    records.append(vf.record(rid=f"dubois21.newhorizon.btfr.z{z:g}", run="NewHorizon", points=pts, population="disc galaxies", interval="uncertainty", connect=mono, strict=False,
                             warning=f"Mean binned relation (solid line) and the dashed lines of the same colour at z={z:g}, read from the vector paths of Dubois et al. 2021; no table exists. The plot has baryonic mass on x and velocity on y; sim-highline stores velocity on x, so the axes are swapped and the dashed lines (not explained in the caption) become xLow/xHigh in velocity. "
                                     + ("" if mono else "The swapped curve is not monotone in velocity at the massive end, so it is stored as unconnected points. ") + "Observational fits are not extracted.", **common))
gal = sorted((fy((d["rect"].y0 + d["rect"].y1) / 2), fx((d["rect"].x0 + d["rect"].x1) / 2)) for d in page.get_drawings()
             if close(d["color"], (0.5488, 0.0, 0.8301), 0.01) and abs((d.get("width") or 0) - 1.1) < 0.05 and len(d["items"]) == 4 and fr.contains(d["rect"]))
assert len(gal) > 100, len(gal)
common = dict(source="NewHorizon", relation="btfr", z=0.25, axes=tf_axes, definitions=tf_defs, citation=cite("baryonic Tully-Fisher relation", 0.25), doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
              figure="baryonic Tully-Fisher relation", panel="z=0.25", sha=sha, member=pdf.name, calibration="prediction", calib="x: labelled decades validated by the minor-tick pattern; y: labelled decades")
records.append(vf.record(rid="dubois21.newhorizon.btfr-galaxies.z0.25", run="NewHorizon (per galaxy)", points=gal, population="individual disc galaxies (zoom, not volume complete)", interval="scatter", connect=False, strict=False,
                         warning="Marker centres (purple plus signs) of the simulated disc galaxies at z=0.25 read from the vector paths of Dubois et al. 2021; the axes are swapped to sim-highline's orientation (velocity on x). Zoom region, not volume complete.", **common))

# ---- cold gas fraction Mcd/(Mcd+Ms), converted to log10(Mgas/Mstar) ----
for tag, ncut in (("nmin1d-1", "0.1"), ("nmin1d1", "10")):
    pdf = next(SRC.rglob(f"fgascoldsigmavsmgal_2reff_{tag}_tmax2d4-eps-converted-to.pdf"))
    page = vf.page_of(pdf)
    fr = vf.frame_from_long_lines(page)
    xt = vf._tick_positions(page, fr, "x")
    major = [t for t in xt if any(abs(t - (xt[0] + 111.7 * k)) < 0.8 for k in range(4))]
    assert len(major) == 4, major
    fx, _ = vf.axis_fit_log2(page, fr, "x", [(t, 8.0 + k) for k, t in enumerate(major)])
    ylab = sorted(((w[1] + w[3]) / 2, numlab(w)) for w in page.get_text("words") if numlab(w) is not None and w[2] < fr.x0 and fr.y0 - 8 < (w[1] + w[3]) / 2 < fr.y1 + 8)
    yticks = vf._tick_positions(page, fr, "y")
    if ylab:
        fy, _ = vf.axis_fit_shifted(page, fr, "y", ylab)
        yref = yticks
    else:
        assert yticks == yref, "unlabelled panel must share the y axis of the labelled one"
    sha = vf.sha256(pdf)
    gx = lambda f: math.log10(f / (1 - f))
    for ckey, z in COL.items():
        r = mean_band(page, fr, lambda d, ck=ckey: close(d["color"], ck, 0.01) and abs((d.get("width") or 0) - 1.4) < 0.05, fy, fx)
        assert len(r) == 1, (tag, z, len(r))
        pts = rec_points(r[0], tf=gx)
        assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:]))
        defs = {**Z0, "massDefinition": "aperture-2Reff-stars", "gasDefinition": f"cold gas n > {ncut} cm^-3 and T < 2e4 K within 2 R_eff", "gasStatistic": "mean"}
        records.append(vf.record(
            rid=f"dubois21.newhorizon.gas-n{ncut.replace('.', 'p')}.z{z:g}", source="NewHorizon", run=f"NewHorizon (cold gas n>{ncut})", relation="gas", z=z,
            axes={**MASSAX, "yDefinition": f"log10 cold-gas-to-stellar mass ratio Mcd/Ms (cold gas n > {ncut} cm^-3, T < 2e4 K, within 2 R_eff), converted from the plotted Mcd/(Mcd+Ms)", "yUnit": "dex"},
            points=pts, population="all galaxies", interval="uncertainty", definitions=defs, citation=cite("cold gas fraction versus stellar mass", z), doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="cold gas fraction versus stellar mass", panel=f"z={z:g}", sha=sha, member=pdf.name, calibration="prediction",
            calib="x: tick labels are outlined, so the four major decade ticks (10^8 at the frame edge, 111.7 pt/dex) were validated by the minor-tick pattern; this figure's x range differs slightly from the other NewHorizon figures; y: labelled ticks (offset-aware fit; the unlabelled n>10 panel shares the y axis of the labelled n>0.1 panel, tick positions asserted identical)",
            warning=f"Mean cold-gas fraction Mcd/(Mcd+Ms) (solid line) with the plotted errors of the mean (dashed lines) at z={z:g}, read from the vector paths of Dubois et al. 2021 and converted to log10(Mcd/Ms) = log10(f/(1-f)), an exact transform applied to the line and to the band edges. Observational overlays are not extracted."))
# ---- black hole mass versus stellar mass (matplotlib figure; per-MBH markers) ----
pdf = next(SRC.rglob("mstar_mbh.pdf"))
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page)[0]
words = [(w[4], w[0], w[1], w[2], w[3]) for w in page.get_text("words")]
xl, yl = [], []
for t, x0, y0, x1, y1 in words:
    if t == "10" and y1 - y0 > 15 and y0 > fr.y1:
        e = next(w for w in words if w[0].isdigit() and 0 < w[1] - x1 < 2 and w[2] < y0 + 1)
        xl.append(((x0 + e[3]) / 2, float(e[0])))
    if t == "10" and y1 - y0 > 15 and x1 < fr.x0 and fr.y0 < y0 < fr.y1:
        e = next(w for w in words if w[0].isdigit() and 0 < w[1] - x1 < 2 and w[2] < y0 + 1)
        yl.append(((y0 + y1) / 2, float(e[0])))
xl, yl = sorted(xl), sorted(yl)
assert len(xl) >= 5 and len(yl) >= 5, (xl, yl)
fx, _ = vf.axis_fit_log2(page, fr, "x", xl, snap=6.0)
fy, _ = vf.axis_fit_log2(page, fr, "y", yl, snap=8.0)
legend = next(d["rect"] for d in page.get_drawings() if d.get("fill") and abs(d["fill"][0] - 1) < 0.01 and d["type"] == "fs" and 80 < d["rect"].width < 300 and 80 < d["rect"].height < 300)
by = {}
for d in page.get_drawings():
    f, r = d.get("fill"), d["rect"]
    if d["type"] != "fs" or not f or len(d["items"]) != 8 or r.width > 8 or not fr.contains(r):
        continue
    cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
    if legend.contains(pymupdf.Point(cx, cy)) and abs(cx - 85.6) < 0.2:
        continue
    by.setdefault((tuple(round(v, 2) for v in f), round(r.width)), []).append((fx(cx), fy(cy)))
MB = {((1.0, 0.8, 0.36), 3): (4.0, "NewHorizon (all MBHs)", "all MBHs within 2 R_eff of their host galaxy"), ((0.99, 0.55, 0.24), 3): (2.0, "NewHorizon (all MBHs)", "all MBHs within 2 R_eff of their host galaxy"),
      ((0.94, 0.23, 0.13), 3): (1.0, "NewHorizon (all MBHs)", "all MBHs within 2 R_eff of their host galaxy"), ((0.74, 0.0, 0.15), 3): (0.25, "NewHorizon (secondary MBHs)", "secondary MBHs within 2 R_eff of their host galaxy"),
      ((0.74, 0.0, 0.15), 7): (0.25, "NewHorizon (primary MBH per galaxy)", "the most massive (primary) MBH of each galaxy")}
assert set(by) == set(MB), set(by)
bh_axes = {**MASSAX, "yDefinition": "log10 black hole mass", "yUnit": "log10(Msun)"}
bh_defs = {**Z0, "bhMassMethod": "intrinsic", "population": "MBHs within 2 R_eff of their host galaxy"}
small, big = sorted(by[((0.74, 0.0, 0.15), 3)]), sorted(by[((0.74, 0.0, 0.15), 7)])
secondary = list(small)
for b in big:
    j = min(range(len(secondary)), key=lambda k: abs(secondary[k][0] - b[0]) + abs(secondary[k][1] - b[1]))
    assert abs(secondary[j][0] - b[0]) < 0.02 and abs(secondary[j][1] - b[1]) < 0.02, "every primary MBH has a small marker underneath (the small markers are all MBHs at z=0.25)"
    secondary.pop(j)
by[((0.74, 0.0, 0.15), 3)] = secondary
for key, (z, run, what) in MB.items():
    pts = sorted(by[key])
    assert len(pts) > 200 and all(3.5 < p[0] < 12.5 and 3.5 < p[1] < 10.5 for p in pts), (z, run, len(pts))
    rid = {"NewHorizon (all MBHs)": "bh-mbh", "NewHorizon (secondary MBHs)": "bh-secondary", "NewHorizon (primary MBH per galaxy)": "bh-primary"}[run]
    records.append(vf.record(
        rid=f"dubois21.newhorizon.{rid}.z{z:g}", source="NewHorizon", run=run, relation="bh", z=z, axes=bh_axes, definitions=bh_defs, points=pts, population=what, interval="scatter", connect=False, strict=False,
        citation=cite("MBH mass versus galaxy stellar mass", z), doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="MBH mass versus galaxy stellar mass", panel=f"z={z:g}", sha=sha, member=pdf.name, calibration="prediction",
        calib="x and y: labelled decades (base and exponent glyphs paired) validated by the minor-tick pattern",
        warning=f"Marker centres of {what} at z={z:g}, read from the vector paths of Dubois et al. 2021; no table exists. Seed-mass floor near 10^4 Msun."
                + (" The figure draws small markers for every MBH at z=0.25 under the large primary markers; the primaries were matched one to one and removed, so this set may omit a secondary hidden exactly under a primary." if "secondary" in run else "") + f" Zoom region, not volume complete. Observational overlays (RV15, Greene20, BM19) are not extracted."))
mean = [d for d in page.get_drawings() if d["type"] == "s" and close(d["color"], (0, 0, 0)) and len(d["items"]) >= 10 and d["rect"].width > 50]
assert len(mean) == 1
mp = [mean[0]["items"][0][1]] + [i[2] for i in mean[0]["items"]]
mpts = [(fx(p.x), fy(p.y)) for p in mp]
assert all(a[0] < b[0] for a, b in zip(mpts, mpts[1:]))
records.append(vf.record(
    rid="dubois21.newhorizon.bh-mean.z0.25", source="NewHorizon", run="NewHorizon (mean of primary MBHs)", relation="bh", z=0.25, axes=bh_axes, definitions=bh_defs, points=mpts, population="primary MBH of each galaxy, mean in stellar-mass bins",
    citation=cite("MBH mass versus galaxy stellar mass", 0.25), doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="MBH mass versus galaxy stellar mass", panel="z=0.25", sha=sha, member=pdf.name, calibration="prediction",
    calib="x and y: labelled decades (base and exponent glyphs paired) validated by the minor-tick pattern",
    warning="Mean MBH mass of the primary MBHs in stellar-mass bins at z=0.25 (black line), read from the vector paths of Dubois et al. 2021; no table exists. The mean is of MBH mass itself (the caption does not say whether it is a mean of the logarithm)."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dubois21-newhorizon-extra.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} NewHorizon records (size, BTFR, cold gas fraction, BH-M*)")
