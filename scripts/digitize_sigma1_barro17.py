"""Barro et al. 2017 (arXiv:1509.00469): log Sigma_1kpc - log M* relations of star-forming and quiescent CANDELS/GOODS-S galaxies at 0.5<z<3.
Records are the published log-linear fits (Table 'Power Law Fits', etab1.tex, parsed from the source), checked against the fit lines drawn in Fig. 2B (fig2b.eps, vector).
Usage: python3 digitize_sigma1_barro17.py [extracted-arXiv-source-dir]"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import curve_record_helpers as K
vf = K.vf

OUT_NAME = "sigma1_barro17"
ARXIV = "1509.00469"
DOI = "10.3847/1538-4357/aa6b05"
ARCHIVE_SHA = "07485144467a1082df44b88961546ae628a902b25a42d5507507d43902c2afd6"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)

# ---- parse Table 'Power Law Fits' (etab1.tex rows 15-18): columns mu, logC | alpha, logA (Q) | alpha, logA (SF) | beta, logB (Q) | beta, logB (SF)
rows = {}
for ln in (SRC / "etab1.tex").read_text().splitlines():
    m = re.match(r"\s*\$(\d\.\d)<z<(\d\.\d)\$\s*&(.*)\\\\", ln)
    if not m:
        continue
    cells = [c for c in m.group(3).split("&")]
    nums = [float(re.search(r"(-?)\$?(\d+\.\d+)", c.replace("-$", "$-")).group(2)) * (-1 if "-$" in c else 1) for c in cells]
    assert len(nums) == 10, (ln, nums)
    rows[(float(m.group(1)), float(m.group(2)))] = {"Q": (nums[6], nums[7]), "SF": (nums[8], nums[9])}
assert sorted(rows) == [(0.5, 1.0), (1.0, 1.4), (1.4, 2.2), (2.2, 3.0)], rows
# hand cross-check of three entries against the table text read above
assert rows[(0.5, 1.0)] == {"Q": (0.65, 9.53), "SF": (0.89, 9.12)} and rows[(2.2, 3.0)] == {"Q": (0.67, 9.80), "SF": (0.89, 9.33)} and rows[(1.4, 2.2)]["Q"] == (0.64, 9.74)

# ---- verification against the lines plotted in Fig. 2B (panels left to right: 2.2-3.0, 1.4-2.2, 1.0-1.4, 0.5-1.0; thick blue = SFG fit, thick red = quiescent fit)
eps, pdf = K.eps_to_pdf(SRC, "fig2b.eps")
page = vf.page_of(pdf)
frs = vf.frames(page, 100, 60)
assert len(frs) == 4 and all(abs(f.y0 - frs[0].y0) < 0.1 and abs(f.y1 - frs[0].y1) < 0.1 for f in frs)
fy, yt = vf.axis_fit(page, frs[0], "y")           # y labels 7.5..10.5 shared by all panels (checked: equal frame heights)
order = [(2.2, 3.0), (1.4, 2.2), (1.0, 1.4), (0.5, 1.0)]
plotted, xt_all = {}, []
for fr, zb in zip(frs, order):
    fx, xt = vf.axis_fit(page, fr, "x")
    xt_all.append(xt)
    for d in page.get_drawings():
        if d["type"] != "s" or len(d["items"]) < 20 or abs((d.get("width") or 0) - 3.0) > 0.01:
            continue
        pts = [d["items"][0][1]] + [it[-1] for it in d["items"]]
        if sum(fr.x0 - 0.6 <= q.x <= fr.x1 + 0.6 for q in pts) < 0.9 * len(pts):
            continue
        xy = np.array([(fx(q.x), fy(q.y)) for q in pts])
        sl, ic = np.polyfit(xy[:, 0], xy[:, 1], 1)
        assert np.abs(xy[:, 1] - (sl * xy[:, 0] + ic)).max() < 0.003
        plotted[(zb, "Q" if d["color"][0] > 0.5 else "SF")] = (float(sl), float(sl * 10.5 + ic), float(xy[0, 0]), float(xy[-1, 0]))
assert len(plotted) == 8
worst = 0.0
for (zb, pop), (sl, b105, x0, x1) in sorted(plotted.items()):
    beta, logB = rows[zb][pop]
    # dlogSigma between the plotted line and the table expression over the plotted range
    xs = np.linspace(x0, x1, 50)
    dd = np.abs((sl * (xs - 10.5) + b105) - (beta * (xs - 10.5) + logB)).max()
    worst = max(worst, dd)
    print("z %s %-2s plotted slope %.3f logB(10.5) %.3f | table %.2f %.2f | max |diff| over range %.3f dex" % (zb, pop, sl, b105, beta, logB, dd))
    assert abs(b105 - logB) < 0.05 and dd < 0.10  # plotted lines use rounded slopes 0.85/0.65; tolerance reflects the paper's own table-vs-figure difference
print("worst plotted-vs-table difference %.3f dex" % worst)

AX = {"xDefinition": "log10 stellar mass (FAST SED fit, Chabrier IMF)", "xUnit": "log10(Msun)",
      "yDefinition": "log10 stellar surface density within 1 kpc, Sigma_1kpc = M(<1 kpc)/(pi (1 kpc)^2)", "yUnit": "log10(Msun/kpc^2)"}
CIT = f"Barro et al. 2017, ApJ 840, 47 (arXiv:{ARXIV})"
URL = f"https://arxiv.org/abs/{ARXIV}"
DEFS_COMMON = {"imf": "chabrier03", "cosmology": {"H0": 70, "Om": 0.3},
               "massDefinition": "sed-total",
               "sigma1Definition": "Sigma_1kpc=M(<1 kpc)/pi (1 kpc)^2, M(<1 kpc) from stellar mass profiles (multi-band HST SED fits, with a Sersic-dependent correction for PSF smearing within 1 kpc)"}
POP = {"SF": "star-forming (DeltaSFR >= -0.7 dex from the SFR main sequence)", "Q": "quiescent (DeltaSFR < -0.7 dex below the SFR main sequence)"}
recs = []
for (lo, hi) in order[::-1]:
    for pop in ("SF", "Q"):
        beta, logB = rows[(lo, hi)][pop]
        sl, b105, x0, x1 = plotted[((lo, hi), pop)]
        recs.append(K.build(
            rid=f"barro17.candels-goodss.sigma1.{pop.lower()}.z{lo:g}-{hi:g}", source="Barro et al. 2017 (CANDELS GOODS-S)",
            run=f"{'star-forming' if pop == 'SF' else 'quiescent'} galaxies, {lo:g}<z<{hi:g}, log-linear fit", kind="observation", relation="sigma1",
            z=round((lo + hi) / 2, 3), zmin=lo, zmax=hi, mode="observational-bin", axes=AX,
            representation={"type": "parametric", "equation": "log Sigma_1 = beta*(log M* - 10.5) + log B", "expression": "beta*(x-10.5)+logB", "parameters": {"beta": beta, "logB": logB}},
            domain={"xMin": round(x0, 2), "xMax": round(x1, 2)}, population=POP[pop],
            warning=("Domain = extent of the fit line plotted in Fig. 2B (SFG 9.0-11.6, quiescent 10.0-11.5); the paper says the fit uses galaxies down to log M*=9 (~70%% complete). "
                     "The plotted thick lines use slopes 0.85 (SFG) and 0.65 (quiescent) in all panels and differ from the tabulated fits by up to %.2f dex over the plotted range; the table is used here. "
                     "zRepresentative is the bin midpoint. Sigma_1 is derived assuming the stellar mass profile follows a Sersic fit (paper Eq. gammaeq). Single-field (GOODS-S), not volume limited." % worst),
            definitions=dict(DEFS_COMMON, population="star-forming" if pop == "SF" else "quiescent"),
            tier="published-fit", citation=CIT + f", Table 'Power Law Fits' (Sigma_1 columns), {lo:g}<z<{hi:g}", doi=DOI, url=URL, calibration="validation", rankable=True,
            notes="beta and log B as tabulated (errors: see etab1.tex); Fig. 2B thick-line check performed. Scatter quoted in the text: sigma(log Sigma_1)~0.25 dex (SFGs), 0.14 dex (quiescent).",
            scatter={"value": 0.25 if pop == "SF" else 0.14, "unit": "dex", "meaning": "sigma(log Sigma_1) quoted in the text (ms.tex:500), all redshifts"},
            provenance_extra={"sourceArchiveSha256": ARCHIVE_SHA, "sourceMember": "etab1.tex rows 15-18", "figureCheck": "fig2b.eps panel lines, " + K.digitize_provenance(pdf, "fig2b.eps", "vector path vertices of thick fit lines", "x and y tick labels read from the PDF text layer", 0.003, "Fig. 2B", "z panels", ARCHIVE_SHA)["checksumSha256"]}))
out = K.write_part(OUT_NAME, recs)
print("wrote", out, len(recs))
