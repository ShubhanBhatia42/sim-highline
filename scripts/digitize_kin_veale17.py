"""Veale et al. 2017 (arXiv:1703.08573, MASSIVE VII): binned mean lambda_e and slow-rotator fraction versus stellar mass for MASSIVE + ATLAS3D early-type galaxies
(figure plotting/figs-rotation.pdf page 2, vector). The fraction bins carry their own n_slow/N labels in the figure; MASSIVE bins are re-derived from the paper's Table 'Properties of MASSIVE survey galaxies'.
Usage: python3 digitize_kin_veale17.py [extracted-arXiv-source-dir]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import curve_record_helpers as K
vf = K.vf

OUT_NAME = "kin_veale17"
ARXIV = "1703.08573"
DOI = "10.1093/mnras/stx1639"
ARCHIVE_SHA = "2192c63cfb45e775308ca313cfbc5b3e92a6519b1fff8de724d0971c91ca4a1c"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "plotting" / "figs-rotation.pdf"
page = vf.page_of(PDF, 1)
fu, fl = vf.frames(page, 50, 50)
assert abs(fu.y1 - fl.y0) < 0.1

# ---- x axis: top axis log10 M*, decade labels 10^10, 10^11, 10^12 validated by the minor-tick pattern at log10(2..9)
words = {w[4]: ((w[0] + w[2]) / 2) for w in page.get_text("words") if w[4] in ("1010", "1011", "1012")}
assert len(words) == 3
fxm, xt = vf.axis_fit_log2(page, fu, "x", [(words["1010"], 10), (words["1011"], 11), (words["1012"], 12)])
logM = lambda x: float(fxm(x))
assert abs(logM(43.78) - 10) < 0.01 and abs(logM(221.48) - 12) < 0.01
# ---- y axes from the major tick marks on the left frame edge (length 4 pt) and their numeric labels
left = sorted({round(it[1].y, 2) for d in page.get_drawings() for it in d["items"] if it[0] == "l" and abs(it[1].y - it[2].y) < 0.02 and 1.5 < abs(it[1].x - it[2].x) < 12 and abs(min(it[1].x, it[2].x) - fu.x0) < 0.6})
assert left == [57.83, 90.53, 123.24, 155.94, 188.64, 198.42, 222.78, 247.14, 271.5, 295.87, 320.23], left
upper, lower = [t for t in left if t < 190], [t for t in left if t > 190]
labs = sorted([((w[1] + w[3]) / 2, float(w[4])) for w in page.get_text("words") if vf.number(w[4]) is not None and w[0] < fu.x0 - 1 and w[4] in ("0.0", "0.2", "0.4", "0.6", "0.8", "1.0")])
up_l, lo_l = [l for l in labs if l[0] < 190], [l for l in labs if l[0] > 190]
assert [round(v, 1) for _, v in up_l] == [0.8, 0.6, 0.4, 0.2, 0.0] and [round(v, 1) for _, v in lo_l] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
assert all(abs(t - l[0]) < 5 for t, l in zip(upper, up_l)) and all(abs(t - l[0]) < 5 for t, l in zip(lower, lo_l))
Au = np.polyfit(upper, [v for _, v in up_l], 1)
Al = np.polyfit(lower, [v for _, v in lo_l], 1)
assert np.abs(np.polyval(Au, upper) - [v for _, v in up_l]).max() < 1e-3 and np.abs(np.polyval(Al, lower) - [v for _, v in lo_l]).max() < 1e-3
fyu = lambda y: float(np.polyval(Au, y))
fyl = lambda y: float(np.polyval(Al, y))

# ---- f_slow step histogram: horizontal segments of the three coloured step lines in the lower panel
bins = []
for d in page.get_drawings():
    if d["type"] == "s" and abs((d.get("width") or 0) - 2.0) < 0.01 and len(d["items"]) >= 5:
        pts = [d["items"][0][1]] + [it[-1] for it in d["items"]]
        if min(q.y for q in pts) < fl.y0:
            continue
        for a, b in zip(pts, pts[1:]):
            if abs(a.y - b.y) < 0.01 and abs(a.y - fl.y1) > 0.5:
                bins.append((min(a.x, b.x), max(a.x, b.x), a.y))
bins.sort()
assert len(bins) == 9 and all(abs(b[1] - n[0]) < 0.2 for b, n in zip(bins, bins[1:])), bins
counts = []
for w in page.get_text("words"):
    m = re.fullmatch(r"(\d+)/(\d+)", w[4])
    if m:
        counts.append(((w[0] + w[2]) / 2, int(m.group(1)), int(m.group(2))))
assert len(counts) == 9
fs = []
for x0, x1, y in bins:
    xc = (x0 + x1) / 2
    c = min(counts, key=lambda t: abs(t[0] - xc))
    assert abs(c[0] - xc) < 3.0
    f_geom = fyl(y)
    assert abs(f_geom - c[1] / c[2]) < 0.003, (f_geom, c)
    fs.append(dict(lo=logM(x0), hi=logM(x1), n=c[1], N=c[2], f=c[1] / c[2], f_geom=f_geom))
print("f_slow bins (log M* lo-hi, n/N, geometry):", [(round(b["lo"], 2), round(b["hi"], 2), f"{b['n']}/{b['N']}", round(b["f_geom"], 3)) for b in fs])
# legend of the figure: ranges 10^9.9-10^10.9 (olive), 10^10.9-10^11.7 (orange), 10^11.7-10^12.2 (red)
assert abs(fs[0]["lo"] - 9.9) < 0.05 and abs(fs[3]["hi"] - 10.9) < 0.05 and abs(fs[5]["hi"] - 11.7) < 0.05 and abs(fs[8]["hi"] - 12.2) < 0.05

# ---- <lambda_e> markers in the upper panel (coloured symbols at the bin centres)
mk = []
for d in page.get_drawings():
    if d["type"] == "fs" and d["fill"] is not None and any(all(abs(a - b) < 0.02 for a, b in zip(d["fill"], c)) for c in ((0.7, 0.7, 0.0), (1.0, 0.5, 0.0), (1.0, 0.0, 0.0))):
        r = d["rect"]
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if fu.x0 < cx < fu.x1 and fu.y0 < cy < fu.y1 and cy > 100:  # excludes the legend symbols at the top
            mk.append((cx, cy))
mk.sort()
assert len(mk) == 9, mk
lam = []
for (cx, cy), b, (x0, x1, _) in zip(mk, fs, bins):
    assert abs(cx - (x0 + x1) / 2) < 0.3
    lam.append((0.5 * (b["lo"] + b["hi"]), fyu(cy)))
print("<lambda_e> markers:", [(round(x, 2), round(y, 3)) for x, y in lam])

# ---- verification against the paper's MASSIVE table (75 galaxies with lambda_e): bin counts, slow fractions and mean lambda_e of the three MASSIVE bins
rows = []
for ln in (SRC / "plotting" / "tables-paper.tex").read_text().splitlines():
    c = [x.strip() for x in ln.replace("\\\\", "").split("&")]
    if len(c) < 14 or ln.startswith(("Galaxy", " &", "(")):
        continue
    num = lambda s: float(re.sub(r"[^0-9.\-]", "", s.replace("$", "").replace("\\dagger", "").replace("^*", "").replace("^", ""))) if re.search(r"\d", s) else None
    rows.append({"logM": num(c[5]), "lam": num(c[7]), "rot": c[8].replace("$", "").strip()})
rows = [r for r in rows if r["lam"] is not None]
assert len(rows) == 75 and sum(r["rot"] == "S" for r in rows) == 58
assert sum(b["N"] for b in fs[6:]) == 75 and sum(b["n"] for b in fs[6:]) == 58     # figure labels 32/44 + 18/22 + 8/9 = 58/75
srt = sorted(rows, key=lambda r: -r["logM"])
top = srt[:9]
assert sum(r["rot"] == "S" for r in top) == 8 and abs(np.mean([r["lam"] for r in top]) - lam[8][1]) < 0.003          # 8/9 and <lambda_e>=0.074
print("top MASSIVE bin from table: 8/9 slow, <lambda_e> %.3f (figure marker %.3f)" % (np.mean([r["lam"] for r in top]), lam[8][1]))
mid, low = srt[9:31], srt[31:]
# the two lower MASSIVE bins differ by one fast/slow swap of galaxies tied at log M*=11.79 (the table masses are rounded to 0.01): totals agree
dl_mid = lam[7][1] - np.mean([r["lam"] for r in mid])
dl_low = lam[6][1] - np.mean([r["lam"] for r in low])
print("lower MASSIVE bins: table (by sorted mass) mean %.3f / %.3f vs figure %.3f / %.3f" % (np.mean([r["lam"] for r in mid]), np.mean([r["lam"] for r in low]), lam[7][1], lam[6][1]))
assert abs(dl_mid) < 0.02 and abs(dl_low) < 0.02

AX_F = {"xDefinition": "log10 stellar mass estimated from the K-band magnitude M_K", "xUnit": "log10(Msun)", "yDefinition": "fraction of slow rotators among early-type galaxies in the mass bin, f_slow = N_slow/N_total", "yUnit": "dimensionless"}
AX_L = {"xDefinition": "log10 stellar mass estimated from the K-band magnitude M_K", "xUnit": "log10(Msun)", "yDefinition": "mean (not median) lambda_e of the early-type galaxies in the mass bin, lambda_e = lambda(<R_e)", "yUnit": "dimensionless"}
SPIN = ("lambda(<R) = <R|V|>/<R sqrt(V^2+sigma^2)>, lambda_e = lambda(<R_e); angle brackets are luminosity-weighted averages over all IFS bins within R (massive_vii.tex lines 506-508)")
PROJ = ("2D observed line-of-sight IFS velocity and dispersion maps; circular bins for MASSIVE, elliptical apertures for ATLAS3D (line 514); many ATLAS3D galaxies do not reach R_e (half to between 0.5 R_e and R_e)")
CRIT = "slow rotator if lambda_e < 0.31 sqrt(epsilon) (Emsellem+11 cutoff used 'hereafter', massive_vii.tex lines 516 and 519); no separate epsilon < 0.4 limit is stated"
POP = "early-type galaxies only: MASSIVE priority sample (M_K<-25.5, 75 galaxies, volume limited) + ATLAS3D early-type sample; late types are not included"
MASSDEF = {"massDefinition": "K-band luminosity proxy: M_* from M_K via equation 2 of Ma+14, taken from eq. 2 of Cappellari+13 (massive_vii.tex lines 223-224)", "imf": "unspecified"}
DEFC = dict(MASSDEF, cosmology="unspecified", population="early-type galaxies (MASSIVE + ATLAS3D)", projection="2D projected (IFS), within R_e")
EPOCH = dict(z=0.0, zmin=0.0, zmax=0.03, mode="observational-bin")
CIT = f"Veale et al. 2017, MNRAS 471, 1428 (arXiv:{ARXIV}), Fig. 'lam-mk' (spin parameter and slow rotator fraction versus M*)"
URL = f"https://arxiv.org/abs/{ARXIV}"
PROV = K.digitize_provenance(PDF, "plotting/figs-rotation.pdf page 2", "vector paths of the figure PDF (PyMuPDF): step-line segments, marker centres and the n/N text labels",
                             "x: top log axis, decade labels 10^10-10^12 validated on the minor ticks; y: major ticks + numeric labels; f_slow geometry equals the printed n/N to <0.003", 0.003,
                             "Fig. lam-mk: spin parameter (top) and slow rotator fraction (bottom) versus M*", "both panels", ARCHIVE_SHA)
WARN = ("Nine mass bins combining ATLAS3D (log M* 9.9-11.7) and MASSIVE (11.7-12.2) early-type galaxies; x is the bin centre in the figure's M_K-derived mass, xLow/xHigh the bin edges. "
        "Only early-type galaxies enter: this is NOT the slow-rotator fraction of all galaxies. Counts are small at low mass (3/43, 4/51, 6/37, 6/68): binomial errors are not given in the paper. "
        "zMax=0.03 is a rounding of D<108 Mpc (MASSIVE) assuming H0~70, not a paper statement.")
pts_f = [{"x": round(0.5 * (b["lo"] + b["hi"]), 3), "y": round(b["f"], 4), "xLow": round(b["lo"], 3), "xHigh": round(b["hi"], 3), "count": b["N"]} for b in fs]
pts_l = [{"x": round(x, 3), "y": round(y, 4), "xLow": round(b["lo"], 3), "xHigh": round(b["hi"], 3), "count": b["N"]} for (x, y), b in zip(lam, fs)]
recs = [
    K.build(rid="veale17.massive-atlas3d.fslow.etg.9bins", source="Veale et al. 2017 (MASSIVE+ATLAS3D)", run="ETGs, 9 mass bins, f_slow", kind="observation", relation="fslow",
            z=EPOCH["z"], zmin=EPOCH["zmin"], zmax=EPOCH["zmax"], mode=EPOCH["mode"], axes=AX_F, representation=K.points_rep(pts_f),
            domain={"xMin": pts_f[0]["x"], "xMax": pts_f[-1]["x"]}, population=POP, warning=WARN,
            definitions=dict(DEFC, slowRotatorCriterion=CRIT, spinDefinition=SPIN, projection=PROJ), tier="digitized-figure", citation=CIT, doi=DOI, url=URL,
            calibration="validation", rankable=False,
            notes="y = n_slow/N printed on the figure (e.g. 6/68, 8/9); the plotted step heights agree with n/N to <0.003. MASSIVE bins re-derived from the paper's table: 58 slow of 75, top bin 8/9.", provenance_extra=PROV),
    K.build(rid="veale17.massive-atlas3d.lambdar.etg.mean9bins", source="Veale et al. 2017 (MASSIVE+ATLAS3D)", run="ETGs, 9 mass bins, mean lambda_e", kind="observation", relation="lambdar",
            z=EPOCH["z"], zmin=EPOCH["zmin"], zmax=EPOCH["zmax"], mode=EPOCH["mode"], axes=AX_L, representation=K.points_rep(pts_l),
            domain={"xMin": pts_l[0]["x"], "xMax": pts_l[-1]["x"]}, population=POP,
            warning=WARN + " The statistic is the MEAN lambda_e per bin (the paper calls it the average), not the median used by the relation's y definition.",
            definitions=dict(DEFC, spinDefinition=SPIN, slowRotatorCriterion=CRIT, lambdaStatistic="mean"), tier="digitized-figure", citation=CIT, doi=DOI, url=URL,
            calibration="validation", rankable=False,
            notes="Marker centres of the coloured <lambda_e> symbols; the top MASSIVE bin reproduces the mean lambda_e of the 9 most massive table galaxies (0.074); the two lower MASSIVE bins agree with the table to <0.02 (one tied-mass swap).", provenance_extra=PROV)]
out = K.write_part(OUT_NAME, recs)
print("wrote", out, len(recs))
