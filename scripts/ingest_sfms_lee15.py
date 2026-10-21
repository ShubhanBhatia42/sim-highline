"""Lee et al. 2015 (arXiv:1501.01080), COSMOS star-forming main sequence: per-redshift-bin best fits S = S0 - log[1 + (10^M/10^M0)^-gamma] (Eq. ms_fit, Table 'tab:param').
Six records (observational-bin). Table parsed from the arXiv source. Verification: the six solid best-fit curves of the paper's Fig. nrk_mseq_allz (vector PDF, axes calibrated
on tick labels) are compared with the expression evaluated with the table parameters. Writes records_lee15.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_figure import fetch_arxiv  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
import json, re, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, "/home/user/sim-highline/scripts")
import vector_figure as vf
BASE = fetch_arxiv("1501.01080"); TEX = (BASE / "main_sequence_hyperref.tex").read_text()
OUT = ROOT / "data" / "curves" / "sfms-lee15.json"
k = TEX.index("\\colhead{Redshift Range}"); i = TEX.index("\\startdata\n", k); j = TEX.index("\\enddata\n", i)
num = r"([\d.]+)"
pat = re.compile(r"\s*" + num + r"--" + num + r"\s*&\s*" + num + r"\s*&\s*" + num + r"\s*&\s*" + num + r" \$\\pm\$ " + num + r"\s*&\s*" + num + r" \$\\pm\$ " + num + r"\s*&\s*" + num + r" \$\\pm\$ " + num + r"\s*&\s*" + num)
T = [dict(zlo=v[0], zhi=v[1], zmean=v[2], mlim=v[3], S0=v[4], S0e=v[5], M0=v[6], M0e=v[7], g=v[8], ge=v[9], chi2=v[10]) for v in (list(map(float, pat.match(l).groups())) for l in TEX[i:j].split("\n") if "--" in l)]
assert len(T) == 6 and T[0]["S0"] == 0.80 and T[5]["M0"] == 10.31 and T[3]["g"] == 1.28
f = lambda x, p: p["S0"] - np.log10(1 + 10 ** (-p["g"] * (x - p["M0"])))
page = vf.page_of(BASE / "nrk_mseq_allz-eps-converted-to.pdf")
fr = vf.frame_from_long_lines(page, 100)
fx, fy, info = vf.calibrate(page, fr)
print("x ticks", [round(v, 2) for _, v in info["xTicks"]], "y ticks", [round(v, 2) for _, v in info["yTicks"]])
cs = [c for c in vf.curves(page, fr, fx, fy, min_items=5) if c["width"] and c["width"] > 1.9]
print("thick curves", len(cs), [len(c["points"]) for c in cs], [c["color"] for c in cs])
cs.sort(key=lambda c: float(np.interp(10.0, *zip(*sorted((p[0], p[1]) for p in c["points"])))))
res = []
for c, p in zip(cs, T):
    P = np.array(c["points"]); P = P[np.argsort(P[:, 0], kind="stable")]
    d = f(P[:, 0], p) - P[:, 1]
    res.append(dict(zmean=p["zmean"], xRange=[round(float(P[0, 0]), 2), round(float(P[-1, 0]), 2)], rms=round(float(np.sqrt(np.mean(d ** 2))), 4), maxAbs=round(float(np.abs(d).max()), 4)))
    print(res[-1])
assert len(cs) == 6 and all(r["rms"] < 0.03 for r in res), res

hi = max(r["xRange"][1] for r in res)
def rec(p, r):
    tag = f"z{p['zlo']:g}-{p['zhi']:g}"
    P = dict(S0=p["S0"], M0=p["M0"], gamma=p["g"], S0Error=p["S0e"], M0Error=p["M0e"], gammaError=p["ge"])
    return {
        "id": f"lee15.cosmos.sfms.{tag}", "source": "Lee et al. 2015 (COSMOS, Herschel/Spitzer/NRK)", "run": "best-fit curve, median SFR in 30 stellar-mass bins",
        "kind": "observation", "relation": "sfms",
        "epoch": {"zRepresentative": p["zmean"], "zMin": p["zlo"], "zMax": p["zhi"], "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "log10 stellar mass (SED fitting with BC03 models, Ilbert+13 catalogue; IMF not stated in the paper)", "xUnit": "log10(Msun)",
                 "yDefinition": "log10 of the median total SFR = 8.6e-11 (L_IR + 2.3 nu L_nu(2300 A)) of star-forming galaxies in a stellar-mass bin; L_IR from Herschel, Spitzer 24 micron or the NRK method (ladder of indicators)", "yUnit": "log10(Msun/yr)"},
        "domain": {"xMin": p["mlim"], "xMax": hi},
        "representation": {"type": "parametric", "equation": "S = S0 - log[1 + (10^M / 10^M0)^-gamma], S = log SFR, M = log10 M*/Msun (Eq. 2, Table 1)",
                           "expression": "S0-Math.log10(1+Math.pow(10,-gamma*(x-M0)))", "parameters": P},
        "scatter": {"value": 0.36, "unit": "dex", "meaning": "standard deviation of the SFRs in each stellar-mass bin, 'sigma ~ 0.36 dex in all bins' (population scatter, not an uncertainty of the curve)"},
        "selection": {"population": "mass-complete star-forming galaxies, Ks<24 UltraVISTA/COSMOS2015-predecessor catalogue; 'quiescent' = M_NUV-M_r > 3(M_r-M_J)+1 and M_NUV-M_r > 3.1, except IR-detected 'quiescent' galaxies, which are kept as star-forming",
                      "warning": f"Six equally populated redshift bins; fit to the medians of 30 equally populated mass bins above a 'conservative mass limit' log M* = {p['mlim']}; the plotted curve ends at {hi} (digitised). Reduced chi^2 = {p['chi2']}. IMF, cosmology and SFR averaging timescale are not stated in the paper."},
        "provenance": {"tier": "published-fit", "citation": "Lee et al. 2015, ApJ 801, 80 (arXiv:1501.01080), Eq. 2 and Table 1", "doi": None, "url": "https://arxiv.org/abs/1501.01080", "retrieved": "2026-10-18"},
        "calibration": "validation", "rankable": True,
        "notes": f"Table parsed from the arXiv source. Verification: the expression with these parameters reproduces the paper's plotted best-fit curve for this bin (rms {r['rms']} dex, max {r['maxAbs']} dex over {r['xRange']}), and the six tabulated gammas span 0.92-1.28 as the abstract's 'low mass power-law slope ranges from 0.9-1.3'.",
        "definitions": {"massDefinition": "sed-total", "imf": "unspecified", "cosmology": "unspecified", "population": "star-forming", "sfrIndicator": "total SFR = SFR_IR + SFR_UV, L_IR from Herschel / Spitzer 24 micron / NRK", "sfrTimescaleMyr": "unspecified", "sfrStatistic": "median"}}
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec(p, r) for p, r in zip(T, res)]}, indent=2) + "\n")
print("wrote", OUT)
