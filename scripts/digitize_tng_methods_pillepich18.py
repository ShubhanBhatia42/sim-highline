import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1703.02970"
DOI = "10.1093/mnras/stx2656"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
ROOT = Path(__file__).resolve().parent.parent
CITE = f"Pillepich et al. 2018, MNRAS 473, 4077 (doi:{DOI}; arXiv:{ARXIV}), the IllustrisTNG model"
BIN = 0.05  # dz of the resampling: the plotted lines carry 1e3 to 2.5e4 vertices (one per output time), far more than the eye or any later use resolves

# curve key -> (source, run, slug, what, parameter change as listed in the paper's variation table)
CURVES = {
    "tng": ("IllustrisTNG", "L25n512 (fiducial TNG model, Pillepich+18)", "tng-l25n512.fiducial", "fiducial TNG model", "none"),
    "ill": ("Illustris", "L25n512 (Illustris model on the TNG box and cosmology, Pillepich+18)", "illustris-model-l25n512.fiducial", "fiducial Illustris model", "none (the original Illustris model run in the same volume with Planck cosmology)"),
    "tng256": ("IllustrisTNG", "L25n256 (low resolution, TNG model, Pillepich+18)", "tng-l25n256.fiducial", "TNG model at L25n256 (low resolution)", "resolution only"),
    "tng128": ("IllustrisTNG", "L25n128 (low resolution, TNG model, Pillepich+18)", "tng-l25n128.fiducial", "TNG model at L25n128 (low resolution)", "resolution only"),
    "ill256": ("Illustris", "L25n256 (low resolution, Illustris model, Pillepich+18)", "illustris-model-l25n256.fiducial", "Illustris model at L25n256 (low resolution)", "resolution only"),
    "ill128": ("Illustris", "L25n128 (low resolution, Illustris model, Pillepich+18)", "illustris-model-l25n128.fiducial", "Illustris model at L25n128 (low resolution)", "resolution only"),
    "noZ": ("IllustrisTNG", "L25n512 variation: no Z-dependent wind energy (Pillepich+18)", "tng-l25n512.var-noZ-wind-energy", "no metallicity scaling of the wind energy", "wind energy factor 3.6 -> 0.9 and Z-dependence reduction factor 0.25 -> 0"),
    "noHz": ("IllustrisTNG", "L25n512 variation: no z-dependent wind velocity (Pillepich+18)", "tng-l25n512.var-no-z-wind-velocity", "no redshift (H(z)) scaling of the wind velocity", "wind velocity factor 7.4 -> 3.7, no H(z) dependence"),
    "nofloor": ("IllustrisTNG", "L25n512 variation: no wind velocity floor (Pillepich+18)", "tng-l25n512.var-no-wind-vel-floor", "no wind velocity floor", "wind velocity floor 350 -> 0 km/s"),
    "noniso": ("IllustrisTNG", "L25n512 variation: not isotropic winds (Pillepich+18)", "tng-l25n512.var-not-isotropic-winds", "wind particles injected along v x grad(Phi) instead of in random directions", "wind direction at injection"),
    "illwinds": ("IllustrisTNG", "L25n512 variation: Illustris winds (Pillepich+18)", "tng-l25n512.var-illustris-winds", "TNG model with the galactic winds exactly as in Illustris", "all wind-related changes reverted (minimum SNII mass stays at the TNG value of 8 Msun)"),
    "strong": ("IllustrisTNG", "L25n512 variation: stronger winds x2 (Pillepich+18)", "tng-l25n512.var-stronger-winds-x2", "wind energy factor doubled", "wind energy factor 3.6 -> 7.2"),
    "fast": ("IllustrisTNG", "L25n512 variation: faster winds x2 (Pillepich+18)", "tng-l25n512.var-faster-winds-x2", "wind velocity factor doubled", "wind velocity factor 7.4 -> 14.8"),
    "fastfid": ("IllustrisTNG", "L25n512 variation: faster winds, fiducial loading (Pillepich+18)", "tng-l25n512.var-faster-winds-fiducial-loading", "faster winds with the mass loading kept at its fiducial value", "wind energy factor 3.6 -> 14.4 and wind velocity factor 7.4 -> 14.8"),
    "warm": ("IllustrisTNG", "L25n512 variation: warmer winds (Pillepich+18)", "tng-l25n512.var-warmer-winds", "warmer winds", "wind thermal fraction 0.1 -> 0.5"),
    "cold": ("IllustrisTNG", "L25n512 variation: cold winds (Pillepich+18)", "tng-l25n512.var-cold-winds", "cold winds", "wind thermal fraction 0.1 -> 0.0"),
    "noB": ("IllustrisTNG", "L25n512 variation: no magnetic fields (Pillepich+18)", "tng-l25n512.var-no-B-fields", "no magnetic fields", "seed field 1.6e-10 Gauss at z=127 -> 0"),
    "noBH": ("IllustrisTNG", "L25n512 variation: no black holes or feedback (Pillepich+18)", "tng-l25n512.var-no-BH-feedback", "no black holes and no black hole feedback", "all black hole related physics removed"),
}
# figure file -> {(colour, dashed): key}; the legends were read against the rendered figures and the captions
FIGS = {
    "TNG_method_paper_fiducial_sfrd_xlog0.pdf": ("top-left panel of the figure on the fiducial model (galaxy population statistics)", {((0.0, 0.0, 0.0), False): "tng", ((0.89, 0.1, 0.11), False): "ill"}),
    "TNG_method_res_sfrd_xlog0.pdf": ("top-left panel of the resolution-dependence figure", {((0.749, 0.82, 0.898), False): "tng128", ((0.388, 0.553, 0.733), False): "tng256", ((0.023, 0.302, 0.529), False): "tng",
                                                                                    ((0.965, 0.706, 0.706), False): "ill128", ((0.929, 0.428, 0.428), False): "ill256", ((0.894, 0.102, 0.11), False): "ill"}),
    "TNG_method_paper_winds_1_sfrd_xlog0.pdf": ("top panel of the figure on removing the new wind features one at a time", {((0.0, 0.0, 0.0), False): "tng", ((0.91, 0.16, 0.54), False): "noZ", ((0.46, 0.44, 0.7), False): "noHz",
                                                                                                         ((0.85, 0.37, 0.01), False): "nofloor", ((0.11, 0.62, 0.47), False): "noniso", ((0.6, 0.0, 0.0), False): "illwinds"}),
    "TNG_method_paper_winds_2_sfrd_xlog0.pdf": ("top panel of the figure on alternative wind parameter values", {((0.0, 0.0, 0.0), False): "tng", ((0.0, 0.0, 0.75), False): "strong", ((0.13, 0.55, 0.13), False): "fast", ((0.4, 0.8, 0.0), False): "fastfid",
                                                                                                    ((1.0, 0.65, 0.0), False): "warm", ((1.0, 0.65, 0.0), True): "cold", ((0.85, 0.37, 0.01), False): "nofloor"}),
    "TNG_method_paper_misc_sfrd_xlog0.pdf": ("top panel of the figure on switching model components off", {((0.0, 0.0, 0.0), False): "tng", ((0.89, 0.1, 0.11), False): "ill", ((0.22, 0.49, 0.72), False): "noB", ((0.3, 0.69, 0.29), False): "noBH"}),
}
# 'no galactic winds' (orange in the misc figure) leaves the plotted range between z = 1.4 and 7 and is not extracted: the two visible pieces are not one function of z


def near(c, t, tol=0.01):
    return all(abs(a - b) < tol for a, b in zip(c, t))


def read_figure(name):
    pdf = SRC / name
    page = vf.page_of(pdf)
    fr = vf.frame_from_long_lines(page, 100)
    W = [(w[4], (w[0] + w[2]) / 2, (w[1] + w[3]) / 2) for w in page.get_text("words")]
    fx, _ = vf.axis_fit(page, fr, "x")
    ylab = [(cy, float(int(t[2:].replace("−", "-")))) for t, cx, cy in W if t in ("10-1", "10-2") and cx < fr.x0]
    assert len(ylab) == 2, ylab
    fy, _ = vf.axis_fit_log2(page, fr, "y", ylab)
    assert abs(fx(fr.x0)) < 0.02 and abs(fx(fr.x1) - 10) < 0.02, (name, fx(fr.x0), fx(fr.x1))
    # the dark grey circles are Oesch et al. 2015 at z = 3.8, 5, 5.9, 6.8, 8: they confirm the redshift axis independently of the tick labels
    circ = sorted(round(fx((d["rect"].x0 + d["rect"].x1) / 2), 2) for d in page.get_drawings() if d["fill"] is not None and near(d["fill"], (0.4, 0.4, 0.4)) and 8 < d["rect"].width < 14 and len(d["items"]) >= 8)
    assert len(circ) == 5 and all(abs(a - b) < 0.05 for a, b in zip(circ, (3.8, 5.0, 5.9, 6.8, 8.0))), (name, circ)
    paths = vf.curves(page, fr, fx, fy, min_items=3)
    return page, fr, fx, fy, paths, vf.sha256(pdf)


def resample(points, fr, fy):
    """Vertices on the frame's top or bottom edge are where the plot clips the line, not data: they are dropped, and so is everything that lies outside the frame. Binned on BIN in z by the mean of log10 y."""
    pts = sorted((x, y) for x, y in points if -0.001 <= x <= 10.001 and -4 < y < 0)
    bins = {}
    for x, y in pts:
        bins.setdefault(int(x / BIN + 1e-9), []).append((x, y))
    return [(round(float(np.mean([p[0] for p in v])), 3), round(float(np.mean([p[1] for p in v])), 4)) for k, v in sorted(bins.items())]


results = {}  # key -> {figure: points}
shas = {}
for name, (panel, cmap) in FIGS.items():
    page, fr, fx, fy, paths, sha = read_figure(name)
    shas[name] = sha
    for (col, dashed), key in cmap.items():
        mine = [p for p in paths if near(p["color"], col) and bool(p["dashes"] and p["dashes"].replace("[", "").replace("]", "").strip(" 0") not in ("",)) == dashed]
        assert mine, (name, key, "no path of that colour", [p["color"] for p in paths])
        raw = []
        for p in mine:
            for (rx, ry), (x, y) in zip(p["raw"], p["points"]):
                if abs(ry - fr.y0) > 0.8 and abs(ry - fr.y1) > 0.8:  # clipped end points
                    raw.append((x, y))
        pts = resample(raw, fr, fy)
        assert len(pts) > 40 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (name, key, len(pts))
        results.setdefault(key, {})[name] = pts


def at(pts, z):
    return float(np.interp(z, [p[0] for p in pts], [p[1] for p in pts]))


# the same run is drawn in several figures: every copy must agree
for key, figs in results.items():
    if len(figs) < 2:
        continue
    names = sorted(figs)
    for other in names[1:]:
        a, b = figs[names[0]], figs[other]
        lo, hi = max(a[0][0], b[0][0]), min(a[-1][0], b[-1][0])
        grid = np.arange(lo + 0.1, hi - 0.1, 0.1)
        dd = [abs(at(a, z) - at(b, z)) for z in grid]
        print(f"{key}: {names[0][17:30]} vs {other[17:30]}  median |dlog10 SFRD| = {np.median(dd):.4f}, max = {max(dd):.3f} over z {lo:.1f}-{hi:.1f}")
        assert np.median(dd) < 0.01 and max(dd) < 0.06, (key, names[0], other, np.median(dd), max(dd))
# the dark blue n512 TNG line of the resolution figure is the fiducial run, and the red n512 Illustris line is the fiducial Illustris run
for key in ("tng", "ill"):
    figs = results[key]
    assert len(figs) >= 3, (key, sorted(figs))

# spot checks against the figure: peak, z = 0, z = 8 (read from the axes by eye: black near 0.07 at z = 2, 0.0105 at z = 0, 0.006 at z = 8; red near 0.09 at z = 2)
tng, ill = results["tng"]["TNG_method_paper_fiducial_sfrd_xlog0.pdf"], results["ill"]["TNG_method_paper_fiducial_sfrd_xlog0.pdf"]
assert abs(at(tng, 2.0) - math.log10(0.068)) < 0.08 and abs(at(tng, 0.0) - math.log10(0.0105)) < 0.08 and abs(at(tng, 8.0) - math.log10(0.0058)) < 0.08, (at(tng, 2), at(tng, 0), at(tng, 8))
assert abs(at(ill, 2.0) - math.log10(0.092)) < 0.08 and at(ill, 0.5) > at(tng, 0.5), (at(ill, 2), at(ill, 0.5), at(tng, 0.5))
# independent check: the Illustris model on the 25 Mpc/h box against the Illustris-1 record of Vogelsberger+14 (a different paper and the full 75 Mpc/h box, the same model up to the cosmology)
rec = json.loads((vf.reference_root() / "data" / "curves" / "vogelsberger14-illustris.json").read_text()) if (vf.reference_root() / "data" / "curves" / "vogelsberger14-illustris.json").exists() else None
if rec is not None:
    r1 = next(r for r in rec["records"] if r["id"] == "vogelsberger14.illustris.sfrd.total")
    p1 = [(p["x"], p["y"]) for p in r1["representation"]["points"]]
    diffs = [(z, at(ill, z) - at(p1, z)) for z in np.arange(0.5, 6.01, 0.5)]
    print("Illustris model L25n512 minus Illustris-1 record (dex):", " ".join(f"z={z:.1f}:{d:+.2f}" for z, d in diffs))
    assert max(abs(d) for _, d in diffs) < 0.25, diffs

records = []
for key, figs in results.items():
    source, run, slug, what, change = CURVES[key]
    name = "TNG_method_paper_fiducial_sfrd_xlog0.pdf" if key in ("tng", "ill") else max(sorted(figs), key=lambda n: (figs[n][-1][0] - figs[n][0][0], len(figs[n])))  # the copy that covers the widest redshift range
    pts = figs[name]
    panel, _ = FIGS[name]
    others = [n for n in sorted(figs) if n != name]
    warning = (f"Cosmic (global) star formation rate density of the {what} in the 25 Mpc/h box L25n{slug.split('l25n')[1][:3] if 'l25n' in slug else '512'}, z 0 to 10, read from the vector path of Pillepich et al. 2018 ({panel}). "
               f"Parameter change with respect to the fiducial TNG model, from the paper's variation table: {change}. All runs of the paper share one initial-condition realization (chosen for a typical halo mass function) and the Planck 2015 cosmology, so differences between them are model differences only. "
               "A single small box: cosmic variance is not included and the high-redshift end is limited by resolution. The line carries one vertex per output time (1e3 to 2.5e4 in the figure); it is resampled on bins of 0.05 in z by the mean of log10 SFRD. "
               "The density frame is not stated in the caption; the overlaid observational compilations (Behroozi+13, Oesch+15) are comoving densities and coincide with the curves, so comoving is inferred. "
               "Observational points are not extracted." + (f" The same curve is drawn in {len(others)} other figure(s) of the paper and agrees with this copy (median difference below 0.01 dex, at most 0.06 dex at narrow spikes)." if others else ""))
    records.append(vf.record(
        rid=f"pillepich18.{slug}.sfrd", source=source, run=run, relation="sfrd", z=2.0,
        axes={"xDefinition": "redshift", "xUnit": "redshift", "yDefinition": "log10 cosmic (global) star formation rate density of the simulated box", "yUnit": "log10(Msun yr^-1 cMpc^-3)"},
        points=pts, population="all star formation in the box", interval="unspecified", z_range=(pts[0][0], pts[-1][0]),
        definitions={"imf": "chabrier03", "cosmology": {"H0": 67.7, "Om": 0.31}, "densityFrame": "comoving", "population": "all galaxies", "sfrIntegrationLimit": "global star formation of the simulated box", "dustCorrection": "none"},
        citation=CITE + f", {what}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="star formation rate density versus redshift", panel=panel, sha=shas[name], member=name, calibration="prediction", uncertainty=0.02,
        calib="x: numeric tick labels 0-10 (five Oesch+15 circles recover z = 3.8, 5, 5.9, 6.8 and 8 to 0.05); y: the two decade labels 10^-2 and 10^-1 validated by the minor-tick pattern of a log axis",
        warning=warning))
out = ROOT / "data" / "curves" / "pillepich18-tng-methods-sfrd.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} cosmic star formation history records from the TNG model paper")
for r in records:
    p = r["representation"]["points"]
    print(f"{r['id']:62s} {len(p):4d} z {p[0]['x']:.2f}->{p[-1]['x']:.2f}  log SFRD {p[0]['y']:.2f} -> {p[-1]['y']:.2f}")
