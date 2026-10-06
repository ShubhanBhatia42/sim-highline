import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2008.06057"
DOI = "10.1093/mnras/staa3715"
src = vf.fetch_arxiv(ARXIV) / "appendix.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
tabs = re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", tex, re.S)
assert len(tabs) == 2
VAL = re.compile(r"\(([\d.]+)\$\\pm\$([\d.]+)\)\$\\times 10\^\{(-?\d+)\}\$")
bins = {}
zs = []
for line in tabs[0].split("\\\\"):
    zm = re.findall(r"z = (\d+)", line)
    if "multicolumn" in line and zm:
        zs = [float(z) for z in zm]
        continue
    c = [x.strip() for x in line.replace("\\hline", "").split("&")]
    if len(c) == 6 and zs:
        for i, z in enumerate(zs):
            m, v = c[2 * i], VAL.search(c[2 * i + 1])
            if v and re.fullmatch(r"-?[\d.]+", m):
                e = 10.0 ** int(v.group(3))
                bins.setdefault(z, []).append((float(m), float(v.group(1)) * e, float(v.group(2)) * e))
assert sorted(bins) == [5.0, 6.0, 7.0, 8.0, 9.0, 10.0], sorted(bins)
assert bins[5.0][0][0] == -24.286 and abs(bins[5.0][-1][1] - 1.126e-2) < 1e-9 and len(bins[5.0]) == 15 and abs(bins[6.0][3][1] - 8.369e-6) < 1e-12, (bins[5.0][-1], bins[6.0][3])
sch = {}
PM = re.compile(r"(-?[\d.]+)\$\^\{\+([\d.]+)\}_\{-([\d.]+)\}\$")
rows = [l for l in tabs[1].split("\\\\") if "$^{+" in l]
zlist = [5, 6, 7, 8, 9, 10]
assert len(rows) == 12, len(rows)
for i, z in enumerate(zlist):
    m = PM.findall(rows[2 * i])
    assert len(m) == 3, (z, rows[2 * i])
    sch[float(z)] = tuple(float(t[0]) for t in m)
assert sch[5.0] == (-21.844, -3.662, -1.984) and sch[8.0] == (-22.082, -5.307, -2.732) and sch[10.0] == (-20.453, -4.768, -3.136), sch
RUN = "40 resimulated regions (EAGLE AGNdT9 model), dust attenuated, Vijayan+21 table"
SCH = "log10(0.4*Math.LN10*phi*Math.pow(10,-0.4*(x-Ms)*(alpha+1))*Math.exp(-Math.pow(10,-0.4*(x-Ms))))"
AX = {"xDefinition": "absolute UV magnitude M_1500 (dust attenuated, AB)", "xUnit": "mag (AB)", "yDefinition": "log10 UV luminosity function per magnitude", "yUnit": "log10(cMpc^-3 mag^-1)"}
DEF = {"imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "densityFrame": "comoving", "uvBand": "rest-frame 1500 A, AB", "dustCorrection": "dust attenuated (the paper's 'observed' UV LF)", "population": "all"}
records = []
for z, rows_ in sorted(bins.items()):
    pts = []
    for m, v, e in sorted(rows_):
        p = {"x": round(m, 3), "y": round(math.log10(v), 4), "yHigh": round(math.log10(v + e), 4)}
        if v - e > 0:
            p["yLow"] = round(math.log10(v - e), 4)
        pts.append(p)
    records.append({
        "id": f"vijayan21.flares.uvlf.binned.z{z:g}", "source": "FLARES", "run": RUN, "kind": "simulation", "relation": "uvlf",
        "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None}, "axes": AX,
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]}, "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": pts}, "scatter": None,
        "selection": {"population": "all galaxies in the weighted combination of the resimulated regions", "warning": f"Binned UV luminosity function of FLARES at z={z:g} (0.5 mag bins) as tabulated in the appendix of Vijayan et al. 2021; the quoted uncertainty is the weighted 1-sigma Poisson error, converted to log10 (a lower bound is omitted where the error equals the value)."},
        "definitions": DEF,
        "provenance": {"tier": "published-table", "citation": "Vijayan et al. 2021, MNRAS (doi 10.1093/mnras/staa3715), appendix table of binned UV luminosity functions", "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": vf.RETRIEVED, "checksumSha256": sha,
                       "sourceMember": "appendix.tex binned UV LF table (arXiv source, transcribed)", "extractionMethod": "transcribed from the arXiv LaTeX table and parsed by script; spot-checked against quoted values in the script"},
        "calibration": "prediction", "rankable": True, "notes": "Values as tabulated by the authors."})
for z, (ms, lp, al) in sorted(sch.items()):
    xs = [p[0] for p in bins[z]]
    records.append({
        "id": f"vijayan21.flares.uvlf.schechter.z{z:g}", "source": "FLARES", "run": RUN.replace("Vijayan+21 table", "Schechter fit"), "kind": "simulation", "relation": "uvlf",
        "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None}, "axes": AX,
        "domain": {"xMin": min(xs), "xMax": max(xs)},
        "representation": {"type": "parametric", "equation": "Phi(M) = 0.4 ln10 phi* 10^(-0.4 (M-M*)(alpha+1)) exp(-10^(-0.4 (M-M*))) per mag", "expression": SCH, "parameters": {"phi": 10 ** lp, "Ms": ms, "alpha": al}},
        "scatter": None,
        "selection": {"population": "all galaxies in the weighted combination of the resimulated regions", "warning": f"Schechter fit (first row of the paper's parameter table) to the observed UV LF at z={z:g}: M*={ms}, log phi*={lp}, alpha={al}. The double power-law row is not used. The domain is the span of the tabulated bins because the paper does not state the fitted range."},
        "definitions": DEF,
        "provenance": {"tier": "published-fit", "citation": "Vijayan et al. 2021, MNRAS (doi 10.1093/mnras/staa3715), best-fitting Schechter and double power-law parameters", "doi": DOI, "url": f"https://arxiv.org/abs/{ARXIV}", "retrieved": vf.RETRIEVED, "checksumSha256": sha,
                       "sourceMember": "appendix.tex fit-parameter table (arXiv source, transcribed)", "extractionMethod": "transcribed from the arXiv LaTeX table"},
        "calibration": "prediction", "rankable": False, "notes": "Fit, not the simulation curve itself."})
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "vijayan21-flares-uvlf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FLARES UV luminosity function records from Vijayan+21")
