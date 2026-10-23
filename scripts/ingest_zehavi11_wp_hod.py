"""Zehavi et al. 2011 (arXiv:1005.2413): SDSS projected correlation functions (published table, luminosity thresholds)
and the halo occupation functions of the same paper (Fig. 10 right panel / HOD parameters, Table hod_thres and its footnote).

wp  : Table 'table:wp_thres' of the paper (13 r_p bins x 9 luminosity thresholds, diagonal errors) -> 9 records, tier published-table.
hod : (a) published-fit records evaluated from the paper's five-parameter HOD (eq. hod) for the thresholds whose published parameters reproduce the
          paper's own Fig. 10 curves to <0.02 dex (M_r<-21.0 from the table; the six fainter thresholds from the sharp-cutoff parameters in the table footnote);
      (b) digitized-figure records of the Fig. 10 curves for M_r<-21.5 and M_r<-22.0, whose table parameters (marginalised values) do NOT reproduce the plotted best-fit curves.
Run: python3 -I ingest_zehavi11_wp_hod.py [path-to-unpacked-arxiv-source]
"""
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.special import erf, gamma as gam

sys.path.insert(0, str(Path(__file__).resolve().parent))      
import vector_figure as vf  # noqa: E402
import pymupdf  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "wp-hod-zehavi11.json"
ARXIV = "1005.2413"
DOI = "10.1088/0004-637X/736/1/59"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
TEX = SRC / "ms.tex"
lines = TEX.read_text(errors="replace").split("\n")
C_KMS = 299792.458
THR = [-22.0, -21.5, -21.0, -20.5, -20.0, -19.5, -19.0, -18.5, -18.0]


def find(s, start=0):
    for i in range(start, len(lines)):
        if s in lines[i]:
            return i
    raise AssertionError(s)


# ---------------------------------------------------------------- tables
i0 = find("\\label{table:thres}")
sam = {}
for l in lines[i0:i0 + 45]:
    if not re.match(r"^-\d+\.\d &", l):
        continue
    c = [x.strip().rstrip("\\cr").strip() for x in l.split("&")]
    if "*" in c[1]:
        continue                                  # smaller-volume (Sloan Great Wall excluded) variants
    num = lambda x: float(x.split("$")[0].replace(",", ""))
    sam[float(c[0])] = dict(czmax=int(num(c[1])), ngal=int(num(c[2])), r0=num(c[5]), gamma=num(c[6]), nbar=float(c[10]) * 1e-2, pimax=int(float(c[11])))
assert sorted(sam) == sorted(THR), sam.keys()
# spot checks against the printed table (numbers read from the tex line, asserted here)
assert (sam[-21.0]["czmax"], sam[-21.0]["ngal"], sam[-21.0]["r0"], sam[-21.0]["gamma"], sam[-21.0]["pimax"]) == (47650, 83238, 5.98, 1.96, 60)
assert abs(sam[-21.0]["nbar"] - 0.00116) < 1e-9 and sam[-18.0]["pimax"] == 40 and sam[-18.0]["czmax"] == 12500 and sam[-22.0]["czmax"] == 73500

i1 = find("\\label{table:wp_thres}")
rows = []
for l in lines[i1:i1 + 30]:
    m = re.match(r"^([\d.]+) & (.*?)( \\cr)?\s*$", l)
    if m and "tablehead" not in l and "(" in l:
        cells = re.findall(r"(-?[\d.]+) \(([\d.]+)\)", m.group(2))
        assert len(cells) == 9, l
        rows.append((float(m.group(1)), [(float(a), float(b)) for a, b in cells]))
assert len(rows) == 13
RP = [r[0] for r in rows]
assert RP[0] == 0.17 and RP[-1] == 42.3
assert rows[0][1][2] == (586.2, 19.5) and rows[4][1][2] == (105.5, 3.0) and rows[-1][1][8] == (0.56, 1.26)   # -21.0 @0.17; -21.0 @1.1; -18.0 @42.3

# ---------------------------------------------------------------- consistency checks of the table
# (1) power-law r0,gamma quoted in the paper (eq. wp3): amplitude must agree with the measured wp at r_p ~ 1-5 within a factor 1.5 (weak check)
pl_report = {}
for t in THR:
    r0, g = sam[t]["r0"], sam[t]["gamma"]
    rr = []
    for rp, cells in rows:
        if 1.0 <= rp <= 5.0:
            wpl = rp * (rp / r0) ** (-g) * math.sqrt(math.pi) * gam((g - 1) / 2) / gam(g / 2)
            rr.append(wpl / cells[THR.index(t)][0])
    pl_report[t] = (min(rr), max(rr))
    assert 0.5 < min(rr) and max(rr) < 1.5, (t, rr)       # weak check: a power law is only a qualitative fit (paper: chi2/dof 1-9)

# (2) markers of the paper's Fig. 10 (left panel; staggered by 0.25 dex starting from M_r<-20.5) against the table, read from the vector paths
tmp = Path(tempfile.mkdtemp(prefix="z11_"))
ps10 = SRC / "fig10.ps"
subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dEPSCrop", "-sDEVICE=pdfwrite", f"-sOutputFile={tmp/'fig10.pdf'}", str(ps10)], check=True)
page = vf.page_of(tmp / "fig10.pdf")
SHA10 = vf.sha256(ps10)
LEFT = pymupdf.Rect(89.28, 141.92, 290.64, 343.28)
RIGHT = pymupdf.Rect(373.92, 141.92, 575.28, 343.28)


def tick_pos(frame, axis, major=9.5):
    out = set()
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if axis == "x" and abs(a.x - b.x) < 0.05 and frame.x0 - 1 <= a.x <= frame.x1 + 1 and abs(max(a.y, b.y) - frame.y1) < 1 and abs(a.y - b.y) > major and abs(a.y - b.y) < 12:
                out.add(round(a.x, 2))
            if axis == "y" and abs(a.y - b.y) < 0.05 and frame.y0 - 1 <= a.y <= frame.y1 + 1 and abs(min(a.x, b.x) - frame.x0) < 1 and abs(a.x - b.x) > major and abs(a.x - b.x) < 12:
                out.add(round(a.y, 2))
    return sorted(out)


# text in this figure is outlined, so the decade ticks are calibrated by hand from the figure's labels:
# left panel x: 0.1, 1, 10 h^-1Mpc ; y: 1e-2 ... 1e4 ; right panel x: 1e11..1e15 h^-1Msun ; y: 0.1, 1, 10, 100 (read from the rendered figure)
lx, ly, rx, ry = tick_pos(LEFT, "x"), tick_pos(LEFT, "y"), tick_pos(RIGHT, "x"), tick_pos(RIGHT, "y")
assert [round(v, 1) for v in lx] == [89.3, 161.0, 233.0] and len(ly) == 7 and len(rx) == 5 and len(ry) == 4, (lx, ly, rx, ry)
def decade_fit(ticks, first, step):
    """position -> value of a log10 axis whose major ticks are decades first, first+step, ...: least-squares fit, residuals asserted < 0.3 pt"""
    vals = np.array([first + step * i for i in range(len(ticks))], float)
    k, c = np.polyfit(ticks, vals, 1)
    assert np.max(np.abs((k * np.array(ticks) + c) - vals)) < 0.03, "ticks not uniformly spaced"
    return lambda p: k * p + c


fLx = decade_fit(lx, -1, 1)           # log10 r_p
fLy = decade_fit(ly, 4, -1)           # log10 w_p (staggered)
fRx = decade_fit(rx, 11, 1)           # log10 M_h
fRy = decade_fit(ry, 2, -1)           # log10 <N>
assert abs(fRy(ry[2])) < 0.02 and abs(fLy(ly[4])) < 0.02


def circles():
    parent = {}

    def fnd(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for d in page.get_drawings():
        col = tuple(round(v, 2) for v in d["color"]) if d["color"] else None
        if col is None or col == (0.21, 0.21, 0.22):
            continue
        for it in d["items"]:
            if it[0] != "l" or math.hypot(it[1].x - it[2].x, it[1].y - it[2].y) > 1.2:
                continue
            ka, kb = (col, round(it[1].x, 1), round(it[1].y, 1)), (col, round(it[2].x, 1), round(it[2].y, 1))
            parent.setdefault(ka, ka)
            parent.setdefault(kb, kb)
            ra, rb = fnd(ka), fnd(kb)
            if ra != rb:
                parent[ra] = rb
    g = {}
    for k in list(parent):
        g.setdefault(fnd(k), []).append(k)
    out = {}
    for ks in g.values():
        xs, ys = [k[1] for k in ks], [k[2] for k in ks]
        if max(xs) - min(xs) < 3.2 and max(ys) - min(ys) < 3.2 and len(ks) >= 8:
            cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
            if LEFT.x0 < cx < LEFT.x1 and LEFT.y0 < cy < LEFT.y1:
                out.setdefault(ks[0][0], []).append((cx, cy))
    return out


COL = {(0.94, 0.35, 0.13): -22.0, (0.97, 0.58, 0.12): -21.5, (1.0, 0.8, 0.02): -21.0, (0.83, 0.87, 0.14): -20.5, (0.0, 0.69, 0.3): -20.0,
       (0.0, 0.67, 0.7): -19.5, (0.0, 0.68, 0.94): -19.0, (0.0, 0.55, 0.82): -18.5, (0.0, 0.36, 0.67): -18.0}
mk = circles()
assert set(mk) == set(COL), mk.keys()
resid = []
for c, pts in mk.items():
    t = COL[c]
    off = 0.5 * (-20.5 - t)                                   # stagger: +0.25 dex per step brighter than -20.5 (caption: staggered by 0.25 dex starting from M_r<-20.5)
    for rp, cells in rows:
        ex = (math.log10(rp) - fLx(0)) / (fLx(1) - fLx(0))
        exy = math.log10(cells[THR.index(t)][0]) + off
        cand = [p for p in pts if abs(p[0] - ex) < 1.5]
        if not cand:
            continue
        p = min(cand, key=lambda q: abs(fLy(q[1]) - exy))
        resid.append(fLy(p[1]) - off - math.log10(cells[THR.index(t)][0]))
resid = np.array(resid)
assert len(resid) >= 105 and np.max(np.abs(resid)) < 0.01, (len(resid), np.max(np.abs(resid)))
MARKER_CHECK = (len(resid), float(np.max(np.abs(resid))))

# ---------------------------------------------------------------- wp records
CITE = "Zehavi et al. 2011, ApJ 736, 59 (arXiv:1005.2413)"
URL = f"https://arxiv.org/abs/{ARXIV}"
recs = []
for t in THR:
    s = sam[t]
    k = THR.index(t)
    zmax = s["czmax"] / C_KMS
    pts = []
    for rp, cells in rows:
        w, e = cells[k]
        p = {"x": round(math.log10(rp), 4), "y": round(math.log10(w), 4), "yHigh": round(math.log10(w + e), 4)}
        if w - e > 0:
            p["yLow"] = round(math.log10(w - e), 4)
        pts.append(p)
    sel = (f"volume-limited sample of all SDSS DR7 main-sample galaxies with M_r < {t:.1f} (r-band, K-corrected and evolved to z=0.1, h=1), 0.02 < z < {zmax:.4f} "
           f"(cz_max = {s['czmax']:,} km/s), 10.0 < m_r < 17.6; N_gal = {s['ngal']:,}; mean number density {s['nbar']:.5f} h^3 Mpc^-3")
    recs.append({
        "id": f"zehavi11.sdss.wp.lumthr-m{abs(t):.1f}",
        "source": "Zehavi et al. 2011 (SDSS DR7)", "run": f"M_r < {t:.1f} (volume-limited threshold sample)", "kind": "observation", "relation": "wp",
        "epoch": {"zRepresentative": round((0.02 + zmax) / 2, 4), "zNominal": 0.1, "zMin": 0.02, "zMax": round(zmax, 4), "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "log10 projected separation r_p (pair-weighted mean separation of the bin)", "xUnit": "log10(h^-1 Mpc)",
                 "yDefinition": "log10 projected correlation function w_p(r_p) = 2 int_0^pi_max d(pi) xi(r_p, pi) of the redshift-space correlation function", "yUnit": "log10(h^-1 Mpc)"},
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "uncertainty", "connect": False, "points": pts},
        "scatter": None,
        "selection": {"population": f"all galaxies with M_r < {t:.1f}",
                      "warning": f"{sel}. Table values w_p(r_p) with the diagonal element of the jackknife error covariance matrix (full covariance not published); the error bar is w_p +/- sigma_diag, "
                                 "yLow is omitted where w_p - sigma <= 0. Magnitudes are M_r + 5 log h with h = 1. zRepresentative is the middle of the volume-limited redshift range, not a measured median; "
                                 "the paper K-corrects to z=0.1. The same threshold also exists as a smaller-volume sample (Sloan Great Wall excluded); this record is the full volume-limited sample."},
        "definitions": {"sampleSelection": sel, "piMax": s["pimax"], "lengthUnit": "h^-1 Mpc", "projection": "redshift-space xi(r_p, pi) integrated along pi to pi_max (w_p = 2 int_0^pi_max d(pi) xi(r_p, pi)); not a real-space measurement",
                        "luminosityThreshold": f"M_r < {t:.1f}", "numberDensityHcubed": s["nbar"], "population": "all", "massDefinition": "not applicable (luminosity-threshold sample)",
                        "cosmologyAssumed": "distances: flat LCDM with Omega_m = 0.3; lengths in h^-1 Mpc (H0-independent)"},
        "provenance": {"tier": "published-table", "citation": CITE, "doi": DOI, "url": URL, "retrieved": "2026-10-18",
                       "figure": "Table 'Projected Correlation Function Measurements of Magnitude Threshold Samples' (label table:wp_thres, appendix); sample properties from label table:thres",
                       "sourceMember": "ms.tex (arXiv source), tables table:wp_thres and table:thres", "sourceArchiveSha256": "45d8bfbc7922d8666a9fd3a7385ccfe3f7bb75dfdb96ba141fd6a0fad428bf56",
                       "extractionMethod": "values parsed from the LaTeX tables; checked against the markers of Fig. 10 (left panel) of the same paper read from the vector paths"},
        "calibration": "validation", "rankable": True,
        "notes": f"Table transcription verified: {MARKER_CHECK[0]} Fig. 10 markers (all thresholds, staggered by 0.25 dex) agree with the table to <= {MARKER_CHECK[1]:.4f} dex; power-law (r0, gamma) from the table reproduce w_p(1-5 h^-1 Mpc) within a factor 1.5 (weak check) ({pl_report[t][0]:.2f}-{pl_report[t][1]:.2f})."})

# ---------------------------------------------------------------- HOD
i2 = find("\\label{table:hod_thres}")
hod = {}
for l in lines[i2:i2 + 30]:
    if not re.match(r"^-\d+\.\d &", l):
        continue
    c = [x.strip() for x in l.split("&")]
    v = [float(re.search(r"-?\d+\.\d+", x).group(0)) for x in c[1:9]]
    hod[float(c[0])] = dict(lmin=v[0], sig=v[1], l0=v[2], l1p=v[3], alpha=v[4], lm1=v[5], fsat=v[6], bg=v[7])
assert sorted(hod) == sorted(THR)
# footnote: sharp-cutoff models
iF = find("The parameters of the sharp-cutoff models plotted in Fig", i2)
foot = "".join(lines[iF:iF + 10])
sharp = {}
for m in re.finditer(r"\((-\d+\.\d), ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)\)", foot):
    t = float(m.group(1))
    sharp[t] = dict(lmin=float(m.group(2)), sig=float(m.group(3)), l0=float(m.group(4)), l1p=float(m.group(5)), alpha=float(m.group(6)))
assert sorted(sharp) == [-20.5, -20.0, -19.5, -19.0, -18.5, -18.0], sharp
assert sharp[-18.0] == dict(lmin=11.14, sig=0.02, l0=9.84, l1p=12.40, alpha=1.04)


def ncen(lm, p):
    return 0.5 * (1 + erf((lm - p["lmin"]) / p["sig"]))


def nsat(lm, p):
    base = (10 ** lm - 10 ** p["l0"]) / 10 ** p["l1p"]
    return np.where(base > 0, ncen(lm, p) * np.abs(base) ** p["alpha"], 0.0)


# figure curves of the right panel (calibrated above)
cs = vf.curves(page, RIGHT, fRx, fRy, min_items=3)


def fig_curve(color, width, dash):
    pts = []
    for c in cs:
        if c["color"] == color and abs(c["width"] - width) < 0.01 and c["dashes"].startswith(dash):
            pts += c["points"]
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    return np.array(pts)


CURV = {-18.0: ((0.0, 0.36, 0.67), 0.667), -18.5: ((0.0, 0.55, 0.82), 1.333), -19.0: ((0.0, 0.68, 0.94), 0.667), -19.5: ((0.0, 0.67, 0.7), 1.333), -20.0: ((0.0, 0.69, 0.3), 0.667),
        -20.5: ((0.83, 0.87, 0.14), 1.333), -21.0: ((1.0, 0.8, 0.02), 0.667), -21.5: ((0.97, 0.58, 0.12), 1.333), -22.0: ((0.94, 0.35, 0.13), 0.667)}
modelpar = {t: sharp[t] for t in sharp}
modelpar[-21.0] = hod[-21.0]
fitcheck = {}
for t in THR:
    col, w = CURV[t]
    fc = fig_curve(col, w, "[]")
    xs, ys = fc[:, 0], fc[:, 1]
    m = (ys > -0.98) & (ys < 1.98) & (xs > 10.6) & (xs < 15.4)
    pp = modelpar.get(t, hod[t])
    n = ncen(xs[m], pp) + nsat(xs[m], pp)
    ok = n > 1.05                                                  # rising part above the central plateau (the cutoff itself is checked below, where y(x) is nearly vertical)
    d = (ys[m] - np.log10(np.where(ok, n, 1)))[ok]
    # position of the central cutoff: x where the plotted total <N> crosses 0.5, against the model
    xf = float(np.interp(math.log10(0.5), ys[(xs > 10.6) & (xs < 15.45)], xs[(xs > 10.6) & (xs < 15.45)]))
    xg = np.arange(10.5, 15.5, 0.0005)
    xm = float(xg[np.argmax((ncen(xg, pp) + nsat(xg, pp)) >= 0.5)])
    fitcheck[t] = (float(np.sqrt(np.mean(d ** 2))), float(np.max(np.abs(d))), int(ok.sum()), xf - xm)
for t in modelpar:
    assert fitcheck[t][1] < 0.02 and abs(fitcheck[t][3]) < 0.02, (t, fitcheck[t])     # the published parameters reproduce the plotted curve (rising part and cutoff position)
for t in (-21.5, -22.0):
    assert fitcheck[t][1] > 0.05 or abs(fitcheck[t][3]) > 0.05, (t, fitcheck[t])       # table (marginalised) parameters do NOT reproduce the plotted curve: figure digitized instead

# derived-mass check: log M1 (<N_sat(M1)> = 1) from the table row against the quoted column
m1chk = {}
from scipy.optimize import brentq
for t in THR:
    p = hod[t]
    r = brentq(lambda lm: float(ncen(lm, p) * (((10 ** lm - 10 ** p["l0"]) / 10 ** p["l1p"]) ** p["alpha"]) - 1), p["l0"] + 1e-9, 17)
    m1chk[t] = (round(r, 3), p["lm1"])
assert abs(m1chk[-21.0][0] - 13.80) < 0.01 and abs(m1chk[-22.0][0] - 14.85) < 0.01 and abs(m1chk[-20.5][0] - 13.44) < 0.01

EQ = ("<N(M_h)> = 1/2 [1 + erf((log M_h - log M_min)/sigma_logM)] [1 + ((M_h - M_0)/M_1')^alpha]  (Zehavi+11 eq. hod); central = the 1/2[1+erf] term, "
      "satellite = that term times ((M_h - M_0)/M_1')^alpha")
HALO = "the mean density of halos is 200 times the background density"
GRID = np.round(np.arange(10.5, 15.5 + 1e-9, 0.01), 3)


def hod_rec(t, kind, par, label):
    nc = ncen(GRID, par)
    ns = nsat(GRID, par)
    n = {"all": nc + ns, "central": nc, "satellite": ns}[kind]
    keep = (n >= 0.1) & (n <= 100)
    xs, ys = GRID[keep], np.log10(n[keep])
    pts = [{"x": float(x), "y": round(float(y), 4) + 0.0} for x, y in zip(xs, ys)]
    sel = f"volume-limited SDSS DR7 sample, all galaxies with M_r < {t:.1f} (r-band, K-corrected and evolved to z=0.1, h=1), 10.0 < m_r < 17.6; clustering sample as in the wp record zehavi11.sdss.wp.lumthr-m{abs(t):.1f}"
    zmax = sam[t]["czmax"] / C_KMS
    return {
        "id": f"zehavi11.sdss.hod.lumthr-m{abs(t):.1f}.{kind}", "source": "Zehavi et al. 2011 (SDSS DR7 HOD)", "run": f"M_r < {t:.1f}, {kind} ({label})", "kind": "observation", "relation": "hod",
        "epoch": {"zRepresentative": round((0.02 + zmax) / 2, 4), "zNominal": 0.1, "zMin": 0.02, "zMax": round(zmax, 4), "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "log10 halo mass M_h (halo = mean density 200 times the background density)", "xUnit": "log10(h^-1 Msun)",
                 "yDefinition": f"log10 mean number of {kind if kind != 'all' else 'central plus satellite'} galaxies per halo <N(M_h)>", "yUnit": "log10(number per halo)"},
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "unspecified", "connect": True, "points": pts},
        "scatter": None,
        "selection": {"population": f"{kind} galaxies with M_r < {t:.1f}",
                      "warning": f"Evaluated by sim-highline from the published five-parameter HOD ({label}): log M_min = {par['lmin']}, sigma_logM = {par['sig']}, log M_0 = {par['l0']}, log M_1' = {par['l1p']}, alpha = {par['alpha']} (halo mass in h^-1 Msun). "
                                 f"{EQ}. Below M_0 the satellite term is set to zero (the printed equation is undefined there; the term is continuous at M_0). Evaluated every 0.01 dex over the range the paper plots in Fig. 10 "
                                 "(0.1 <= <N> <= 100). The HOD is inferred from w_p and the number density with the Zehavi+11 halo model; no uncertainty is stored."},
        "definitions": {"galaxyType": kind, "sampleSelection": sel, "haloMassDefinition": "M200mean", "haloMassDefinitionQuote": HALO, "massUnit": "h^-1 Msun",
                        "hodModel": EQ, "hodParameters": par, "cosmology": {"H0": 70, "Om": 0.25}, "cosmologyQuote": "Omega_m=0.25 ... H_0 = 70 km s^-1 Mpc^-1 (flat LCDM used for the HOD model)"},
        "provenance": {"tier": "published-fit", "citation": CITE, "doi": DOI, "url": URL, "retrieved": "2026-10-18",
                       "figure": "Table 'HOD and Derived Parameters for Luminosity Threshold Samples' (label table:hod_thres) and its footnote; Fig. 10 right panel for the check",
                       "sourceMember": "ms.tex (arXiv source); fig10.ps", "sourceArchiveSha256": "45d8bfbc7922d8666a9fd3a7385ccfe3f7bb75dfdb96ba141fd6a0fad428bf56", "figureChecksumSha256": SHA10,
                       "extractionMethod": "published parameterisation evaluated numerically (scipy.special.erf)"},
        "calibration": "validation", "rankable": True,
        "notes": f"Verified: evaluated total <N> agrees with the Fig. 10 curve read from its vector path to rms {fitcheck[t][0]:.4f} / max {fitcheck[t][1]:.4f} dex over {fitcheck[t][2]} points (axes calibrated by hand on decade ticks)."}


for t in (-21.0,):
    for kind in ("all", "central", "satellite"):
        recs.append(hod_rec(t, kind, {k: hod[t][k] for k in ("lmin", "sig", "l0", "l1p", "alpha")}, "best-fit values of the HOD table"))
for t in sorted(sharp, reverse=True):
    for kind in ("all", "central", "satellite"):
        recs.append(hod_rec(t, kind, sharp[t], "sharp-cutoff model plotted in Fig. 10, parameters in the table footnote"))

# digitized Fig. 10 curves for -21.5 and -22.0 (table parameters do not reproduce them)
def dig_rec(t, kind, color, width, dash, label):
    fc = fig_curve(color, width, dash)
    xs, ys = fc[:, 0], fc[:, 1]
    keep = (xs >= 10.5) & (xs <= 15.5) & (ys >= -1.0 - 1e-6) & (ys <= 2.0 + 1e-6)
    pts = []
    for x, y in zip(xs[keep], ys[keep]):
        if pts and x <= pts[-1]["x"]:
            continue
        pts.append({"x": round(float(x), 4), "y": round(float(y), 4)})
    assert len(pts) > 50
    zmax = sam[t]["czmax"] / C_KMS
    r = hod_rec(t, "all", hod[t], "x")           # reuse static fields
    r.update({"id": f"zehavi11.sdss.hod.lumthr-m{abs(t):.1f}.{kind}.fig10", "run": f"M_r < {t:.1f}, {kind} ({label})"})
    r["definitions"] = {k: v for k, v in r["definitions"].items() if k not in ("hodParameters",)}
    r["definitions"]["galaxyType"] = kind
    r["axes"]["yDefinition"] = f"log10 mean number of {kind if kind != 'all' else 'central plus satellite'} galaxies per halo <N(M_h)>"
    r["representation"] = {"type": "points", "intervalKind": "unspecified", "connect": True, "points": pts}
    r["domain"] = {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]}
    r["selection"] = {"population": f"{kind} galaxies with M_r < {t:.1f}",
                      "warning": f"Curve read from the vector paths of Fig. 10 (right panel) of Zehavi et al. 2011: best-fit HOD of the M_r < {t:.1f} sample ({kind}). The parameters printed in the HOD table for this threshold are marginalised values and do not reproduce this plotted curve "
                                 f"(difference up to {fitcheck[t][1]:.2f} dex), so the figure is used instead. Axes are outlined text: decade ticks calibrated by hand and validated by the sharp-cutoff models of the fainter thresholds, which "
                                 "reproduce the table-footnote parameters to <0.02 dex. Curve is clipped by the frame at 0.1 <= <N> <= 100 and 10^10.5 <= M_h <= 10^15.5 h^-1 Msun."}
    r["provenance"].update({"tier": "digitized-figure", "figure": "Figure 10 (right panel)", "panel": "luminosity-threshold HOD, right panel",
                            "extractionMethod": "vector path vertices from the figure (fig10.ps converted with ghostscript), axes calibrated by hand on decade ticks",
                            "axisCalibrationPixels": "right panel x: ticks at 394.08, 434.40, 474.72, 515.04, 555.12 pt = 10^11..10^15 h^-1 Msun; y: 141.92, 209.12, 276.08, 343.28 pt = 100, 10, 1, 0.1",
                            "digitizationUncertaintyDex": 0.01})
    r["calibration"] = "validation"
    r["rankable"] = False
    r["notes"] = "Vector-path extraction; exact to PDF coordinate precision."
    return r


recs.append(dig_rec(-21.5, "all", (0.97, 0.58, 0.12), 1.333, "[]", "digitized from Fig. 10"))
recs.append(dig_rec(-22.0, "all", (0.94, 0.35, 0.13), 0.667, "[]", "digitized from Fig. 10"))
recs.append(dig_rec(-22.0, "central", (0.94, 0.35, 0.13), 0.667, "[ 7", "digitized from Fig. 10"))
recs.append(dig_rec(-22.0, "satellite", (0.94, 0.35, 0.13), 0.667, "[ 1", "digitized from Fig. 10"))

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": recs}, indent=1) + "\n")
print(f"Wrote {len(recs)} records to {OUT}")
print("marker check", MARKER_CHECK)
print("power-law check", {t: tuple(round(v, 2) for v in r) for t, r in pl_report.items()})
print("HOD curve check (rms, max, n)", {t: tuple(round(v, 4) for v in r) for t, r in fitcheck.items()})
print("M1 check (computed, table)", m1chk)
