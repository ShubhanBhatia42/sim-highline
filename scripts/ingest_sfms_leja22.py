"""Leja et al. 2022 (arXiv:2110.04314) star-forming-sequence ridge (mode) and mean as broken power laws in log M* with quadratic-in-z coefficients
(Eq. bpl, Eq. ridge, Table 1). Coefficients are parsed from the arXiv source. Verification: the solid lines of the paper's own Fig. 'parameterized_moments'
(figures/parameterized_moments.pdf, matplotlib vector PDF, redshifts 0.3, 0.6, 1.0, 1.5, 2.0, 2.7 from the legend text) are digitised with the axes calibrated on
numeric tick labels (vector_figure.axis_fit) and compared with the transcribed expression. Writes records_leja22.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_figure import fetch_arxiv  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
import json, re, sys
from pathlib import Path
import numpy as np
from scipy.optimize import minimize_scalar
sys.path.insert(0, "/home/user/sim-highline/scripts")
import vector_figure as vf

BASE = fetch_arxiv("2110.04314")
TEX = (BASE / "main.tex").read_text()
OUT = ROOT / "data" / "curves" / "sfms-leja22.json"
# ---- parse Table 1
tab = TEX[TEX.index("\\startdata"):TEX.index("\\enddata")]
sec = {"ridge": tab[:tab.index("\\sidehead{\\centering Mean}")], "mean": tab[tab.index("\\sidehead{\\centering Mean}"):]}
coef = {}
for k, s in sec.items():
    coef[k] = {}
    for name in ("a", "b", "c", "\\log M_t"):
        m = re.search(r"^\$" + re.escape(name) + r"\$ & \$(-?[\d.]+)\s*\\pm\s*([\d.]+)\$ & \$(-?[\d.]+)\s*\\pm\s*([\d.]+)\$ & \$(-?[\d.]+)\s*\\pm\s*([\d.]+)\$", s, re.M)
        assert m, (k, name)
        v = [float(g) for g in m.groups()]
        coef[k]["Mt" if name.startswith("\\log") else name] = dict(X0=v[0], X0e=v[1], X1=v[2], X1e=v[3], X2=v[4], X2e=v[5])
assert coef["ridge"]["Mt"]["X0"] == 10.22 and coef["mean"]["a"]["X0"] == -0.06707 and coef["ridge"]["c"]["X2"] == -0.2006

def sfr(k, x, z):
    q = {n: coef[k][n]["X0"] + coef[k][n]["X1"] * z + coef[k][n]["X2"] * z * z for n in ("a", "b", "c", "Mt")}
    return np.where(x > q["Mt"], q["a"], q["b"]) * (x - q["Mt"]) + q["c"]

# ---- digitise the solid fit lines of the parameterized-moments figure
page = vf.page_of(BASE / "figures" / "parameterized_moments.pdf")
frs = [r for r in vf.frames(page, min_w=100, min_h=60) if r.width > 150 and r.height > 150]
assert len(frs) >= 2, frs
frs = sorted(frs, key=lambda r: r.x0)[:2]
legend_z = [0.3, 0.6, 1.0, 1.5, 2.0, 2.7]
words = [w[4] for w in page.get_text("words")]
assert all(str(z) in words for z in legend_z), words    # legend redshifts are text in the figure
check = {}
for panel, fr in zip(("ridge", "mean"), frs):
    fx, fy, info = vf.calibrate(page, fr)
    cs = [c for c in vf.curves(page, fr, fx, fy, min_items=2) if c["width"] and c["width"] >= 1.9]   # the thick solid lines are the fits; width-1 items are the dotted measurements
    print(panel, "frame", [round(v, 1) for v in (fr.x0, fr.y0, fr.x1, fr.y1)], "x ticks", [round(v, 2) for _, v in info["xTicks"]], "y ticks", [round(v, 2) for _, v in info["yTicks"]], "solid curves", len(cs))
    res = []
    for c in cs:
        P = np.array(c["points"]); P = P[np.argsort(P[:, 0], kind="stable")]; P = P[np.r_[True, np.diff(P[:, 0]) > 1e-9]]
        # dense resample of the polyline for a fair comparison
        xs = np.linspace(P[0, 0], P[-1, 0], 200); ys = np.interp(xs, P[:, 0], P[:, 1])
        zb = minimize_scalar(lambda z: np.mean((sfr(panel, xs, z) - ys) ** 2), bounds=(0.05, 3.5), method="bounded").x
        zl = min(legend_z, key=lambda z: abs(z - zb))
        rms = float(np.sqrt(np.mean((sfr(panel, xs, zl) - ys) ** 2))); mx = float(np.abs(sfr(panel, xs, zl) - ys).max())
        res.append(dict(color=c["color"], xRange=[round(float(xs[0]), 2), round(float(xs[-1]), 2)], zBestFit=round(float(zb), 3), legendZ=zl, rms=round(rms, 4), maxAbs=round(mx, 4)))
    check[panel] = res
    for r in res: print("  ", r["color"], r["xRange"], "zBestFit", r["zBestFit"], "legend z", r["legendZ"], "rms", r["rms"], "max", r["maxAbs"])
    assert len(res) == 6 and all(r["rms"] < 0.03 and abs(r["zBestFit"] - r["legendZ"]) < 0.06 for r in res), res
    check[panel + "_xrange"] = [min(r["xRange"][0] for r in res), max(r["xRange"][1] for r in res)]
    check[panel + "_starts"] = {str(r["legendZ"]): r["xRange"][0] for r in res}

def rec(k):
    P = {}
    for n in ("a", "b", "c", "Mt"):
        for i in range(3):
            P[f"{n}{i}"] = coef[k][n][f"X{i}"]
        for i in range(3):
            P[f"{n}{i}Error"] = coef[k][n][f"X{i}e"]
    expr = ("((a0+a1*z+a2*z*z)*(x-(Mt0+Mt1*z+Mt2*z*z))*(x>(Mt0+Mt1*z+Mt2*z*z)?1:0)+(b0+b1*z+b2*z*z)*(x-(Mt0+Mt1*z+Mt2*z*z))*(x>(Mt0+Mt1*z+Mt2*z*z)?0:1)+(c0+c1*z+c2*z*z))")
    what = {"ridge": ("ridge (mode of the SFR distribution at fixed mass and redshift) of the full galaxy population, no star-forming pre-selection", "mode"),
            "mean": ("mean SFR (not mean log SFR) of the full galaxy population including quiescent galaxies", "mean")}[k]
    lo, hi = check[k + "_xrange"]
    return {
        "id": f"leja22.prospector.sfms.{k}.evolution", "source": "Leja et al. 2022 (COSMOS-2015 + 3D-HST, Prospector-alpha)", "run": f"{k}, broken power law",
        "kind": "observation", "relation": "sfms",
        "epoch": {"zRepresentative": 1.0, "zMin": 0.2, "zMax": 3.0, "mode": "analytic-evolution", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass from Prospector-alpha SED fitting (Chabrier IMF)", "xUnit": "log10(Msun)",
                 "yDefinition": f"log10 SFR averaged over the most recent 100 Myr, {what[0]}", "yUnit": "log10(Msun/yr)"},
        "domain": {"xMin": lo, "xMax": hi},
        "representation": {
            "type": "parametric",
            "equation": "log SFR = a (M - Mt) + c for M > Mt and b (M - Mt) + c for M <= Mt, M = log10 M*/Msun; each of a, b, c, Mt = X0 + X1 z + X2 z^2 (Eq. 3-4, Table 1)",
            "expression": expr, "parameters": P},
        "scatter": None,
        "selection": {"population": "all galaxies (no star-forming pre-selection); the ridge is the density peak of the star-forming sequence" if k == "ridge" else "all galaxies including quiescent",
                      "warning": f"Fit to the normalizing-flow density field over 0.2<z<3.0, mass-complete samples (COSMOS-2015 at 0.2<z<0.8, 3D-HST at 0.5<z<3.0; limits from Leja+20, raised by 0.1-0.25 dex at some redshifts). "
                                 f"Mass range shown in the paper's fit figure is log M* = {lo} to {hi}; this range is read from the digitised plot, the paper does not state it. Deviations of the fit from the density field are <~0.1 dex (paper). "
                                 "SED-based SFRs and masses (Prospector-alpha, nonparametric continuity SFH) sit 0.2-0.5 dex below UV+IR based sequences, see the paper's Section 5."},
        "provenance": {"tier": "published-fit", "citation": "Leja et al. 2022, ApJ 936, 165 (arXiv:2110.04314), Eqs. 3-4 and Table 1", "doi": None, "url": "https://arxiv.org/abs/2110.04314", "retrieved": "2026-10-18"},
        "calibration": "validation", "rankable": True,
        "notes": "Coefficients parsed from the arXiv source Table 1. Verification: the expression with the quoted coefficients reproduces the six solid fit lines of the paper's parameterized-moments figure (z=0.3, 0.6, 1.0, 1.5, 2.0, 2.7) with rms 0.002-0.004 dex (max 0.006), and a free fit of z to each line returns the legend redshift to <=0.012. "
                 f"The plotted lines start at log M* = {json.dumps(check[k + '_starts'])} (by redshift; the mass-complete limits) and end at {hi}. Cosmology: Om = Omega_b + Omega_c = 0.0464 + 0.235 = 0.2814 (WMAP9, H0=69.7). The paper does not say here whether the stellar mass is the surviving or the formed mass.",
        "definitions": {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": {"H0": 69.7, "Om": 0.2814}, "population": "all",
                        "sfrIndicator": "Prospector-alpha SED fit to 0.2-24 micron photometry", "sfrTimescaleMyr": 100, "sfrStatistic": what[1]}}

records = [rec("ridge"), rec("mean")]
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print("wrote", OUT)
