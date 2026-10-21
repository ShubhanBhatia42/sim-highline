"""Iyer et al. 2018 (arXiv:1809.04099) SFR-M* correlation evolution, Eq. (eqn:2): log SFR = (0.80 - 0.017 t) log M* - (6.487 - 0.039 t), t = age of the universe in Gyr.
Coefficients parsed from the arXiv source. Verification: Eq. 2 is evaluated at t(z=1..6) in the paper's flat LCDM (H0=70, Om=0.3) and compared with the 'total' slope m and normalization
c9 (log SFR at 1e9 Msun) of the paper's own results table (12 numbers, each with its 1-sigma error). Writes records_iyer18.json."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_figure import fetch_arxiv  # noqa: E402
ROOT = Path(__file__).resolve().parent.parent
import json, re
from pathlib import Path
import numpy as np
TEX = (fetch_arxiv("1809.04099") / "iyer_et_al_sfr_mstar_toprint.tex").read_text()
OUT = ROOT / "data" / "curves" / "sfms-iyer18.json"
m = re.search(r"\\log SFR &= \(([\d.]+) \\pm ([\d.]+)  - ([\d.]+) \\pm ([\d.]+)   \\times  t_\{univ\}\) \\log M_\* \\nonumber \\\\    &- \( ([\d.]+)  \\pm ([\d.]+) - ([\d.]+)  \\pm ([\d.]+)  \\times  t_\{univ\}\)", TEX)
assert m, "equation not found"
a0, a0e, a1, a1e, b0, b0e, b1, b1e = [float(v) for v in m.groups()]
assert (a0, a1, b0, b1) == (0.80, 0.017, 6.487, 0.039)
# results table: z | m_direct m_traj m_total | c9 direct traj total | sigma ... | conf
k = TEX.index("\\label{table:slope_norm_evol_table}"); i = TEX.rindex("\\hline \\hline", 0, k); blk = TEX[i:k]
pm = r"([\d.]+)\$\\pm\$([\d.]+)"
tab = {}
for l in blk.split("\n"):
    mm = re.match(r"\s*(\d) & " + " & ".join([pm] * 9) + r" & ([\d.]+)\\%", l)
    if mm:
        v = [float(x) for x in mm.groups()]; z = int(v[0]); tab[z] = dict(m=(v[5], v[6]), c9=(v[11], v[12]))
assert sorted(tab) == [1, 2, 3, 4, 5, 6], tab
def age(z, H0=70.0, Om=0.3):
    ol = 1 - Om; ht = 977.8 / H0
    return 2 * ht / (3 * np.sqrt(ol)) * np.arcsinh(np.sqrt(ol / Om) / (1 + z) ** 1.5)
res = []
for z in range(1, 7):
    t = age(z); mm = a0 - a1 * t; cc = 9 * mm - (b0 - b1 * t)
    dm = (mm - tab[z]["m"][0]) / tab[z]["m"][1]; dc = (cc - tab[z]["c9"][0]) / tab[z]["c9"][1]
    res.append(dict(z=z, t=round(float(t), 3), m=round(float(mm), 3), m_table=tab[z]["m"], c9=round(float(cc), 3), c9_table=tab[z]["c9"], sigma_m=round(float(dm), 2), sigma_c9=round(float(dc), 2)))
    print(res[-1])
assert max(abs(r["sigma_m"]) for r in res) < 1 and max(abs(r["sigma_c9"]) for r in res) < 1
rec = {
    "id": "iyer18.goods-s.sfms.evolution", "source": "Iyer et al. 2018 (CANDELS GOODS-S, Dense Basis SFHs)", "run": "combined direct fits and SFR-M* trajectories",
    "kind": "observation", "relation": "sfms",
    "epoch": {"zRepresentative": 3.0, "zMin": 1.0, "zMax": 6.0, "mode": "analytic-evolution", "snapshot": None},
    "axes": {"xDefinition": "log10 stellar mass from Dense Basis SED fitting (FSPS, Chabrier IMF)", "xUnit": "log10(Msun)",
             "yDefinition": "log10 SFR from Dense Basis SED fitting: effectively instantaneous SFR at the epoch of observation (direct fits) or at the epoch of interest along the reconstructed SFH (trajectories)", "yUnit": "log10(Msun/yr)"},
    "domain": {"xMin": 7.38, "xMax": 10.5},
    "representation": {"type": "parametric", "equation": "log SFR = (0.80 - 0.017 t) log M* - (6.487 - 0.039 t), t = age of the universe in Gyr (Eq. 2)",
                       "expression": "(a0-a1*t)*x-(b0-b1*t)", "parameters": {"a0": a0, "a1": a1, "b0": b0, "b1": b1, "a0Error": a0e, "a1Error": a1e, "b0Error": b0e, "b1Error": b1e},
                       "ageCosmology": {"H0": 70, "Om": 0.3}},
    "scatter": {"value": 0.27, "unit": "dex", "meaning": "observed scatter of the combined (direct + trajectory) sample at z=3-6 (0.27-0.28 dex; 0.38 at z=1, 0.29 at z=2), not an uncertainty of the curve"},
    "selection": {"population": "galaxies of the CANDELS GOODS-S catalogue at 0.5<z<6 (17,873 after removing stars, X-ray AGN and chi2>50 fits), high-confidence trajectories (combined uncertainty < 1 dex), linear fit with iterative robust outlier rejection; no UVJ or sSFR pre-selection",
                  "warning": "The relation is a linear fit at z=1,2,3,4,5,6 whose slope and normalization are then fitted as linear functions of cosmic time (valid 1<=z<=6). Combines galaxies observed at each epoch with galaxies observed at later epochs propagated back along their SFHs. "
                             "The mass range is not stated as a validity range: the lower end 7.38 is the lowest 10th-percentile stellar mass probed by trajectories (z=6, Table of lowest masses probed); the upper end 10.5 is where the paper says earlier studies find a turnover, 'most of our galaxies fall below this mass range'. "
                             "The paper finds this relation 0.2-0.4 dex below Speagle+14 and notes the SED-based SFRs are not comparable with UV+IR SFRs."},
    "provenance": {"tier": "published-fit", "citation": "Iyer et al. 2018, ApJ 866, 120 (arXiv:1809.04099), Eq. 2 and Table of slope/normalization", "doi": None, "url": "https://arxiv.org/abs/1809.04099", "retrieved": "2026-10-18"},
    "calibration": "validation", "rankable": True,
    "notes": "Coefficients parsed from the arXiv source. Verification: Eq. 2 at t(z=1..6) in the paper's flat LCDM (H0=70, Om=0.3) reproduces the paper's own total slope m and normalization c9 (log SFR at 1e9 Msun) at z=1-6 within 0.51 sigma for all 12 numbers (differences <= 0.04 dex).",
    "definitions": {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": {"H0": 70, "Om": 0.3}, "population": "all", "sfrIndicator": "Dense Basis SED fitting of 0.3-8 micron photometry", "sfrTimescaleMyr": "instantaneous",
                    "sfrTimescaleBasis": "'Fits to the galaxy SEDs ... provide us with both the Stellar Masses and effectively instantaneous Star Formation Rates at the epoch of observation'", "sfrStatistic": "unspecified",
                    "sfrStatisticNote": "linear fit to individual galaxies with iterative robust outlier exclusion (Holland & Welsch 1977), not a median or mean"}}
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
print("wrote", OUT)
