"""UV-continuum slope beta against stellar mass, observations: the median beta in three bins of stellar mass (log M/Msun = 7-8, 8-9, 9-10) at z = 4 to 8 from Table 5 of Finkelstein et al. 2012 (ApJ 756, 164; arXiv:1110.3785,
'CANDELS: the evolution of galaxy rest-frame ultraviolet colors from z = 8 to 4'). Values are parsed from the LaTeX table in the arXiv source and asserted against the printed numbers below. beta is measured on the best-fit SED
(a power law in the wavelength windows of Calzetti et al. 1994), so it is the slope of the best-fit model spectrum, with the dust attenuation of that fit included.
Usage: python3 scripts/transcribe_uvbetam_finkelstein12.py   (writes data/curves/uvbetam-finkelstein12.json)"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARX = "1110.3785"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "uvbetam-finkelstein12.json"
root = vf.fetch_arxiv(ARX)
tex = (root / "tab5.tex").read_text(errors="ignore")
ms = (root / "ms.tex").read_text(errors="ignore")
sha = vf.sha256(root / "tab5.tex")
sha_ms = vf.sha256(root / "ms.tex")
flat = " ".join(ms.split())
for q in ("We measure $\\beta$ by performing spectral energy distribution (SED) fitting on our sample of galaxies",
          "We created a suite of stellar population models assuming a Salpeter initial mass function (IMF)",
          "we measure the value of $\\beta$ directly from this best-fit spectrum by fitting a power law to the spectrum using the wavelength windows specified by \\citet{calzetti94}",
          "$7 < $log M/M\\sol$ < 8$, $8 < $log M/M\\sol$ < 9$ and $9 < $log M/M\\sol$ < 10$. The median values of $\\beta$ in these bins are given in Table 5."):
    assert " ".join(q.split()) in flat, ("quoted sentence missing", q)
assert "Values of the UV Spectral Slope $\\beta$ Split by Stellar Mass" in tex and "log M/M\\sol\\ = 7 -- 8" in tex
rows = {}
for line in tex[tex.index("\\startdata") + 10:tex.index("\\enddata")].split("\\\\"):
    line = line.strip()
    m = re.match(r"^\$z =\$\s*(\d)\s*&(.*)$", line)
    if not m:
        continue
    cells = [c.strip() for c in m.group(2).split("&")]
    assert len(cells) == 5, cells
    vals = []
    for c in cells[:3]:
        mm = re.match(r"^\$-\$([\d.]+)\$\^\{\+([\d.]+)\}_\{-([\d.]+)\}\$$", c)
        assert mm, c
        vals.append((-float(mm.group(1)), float(mm.group(2)), float(mm.group(3))))
    n = [int(v) for v in cells[3].split("/")]
    sl = re.match(r"^([\d.]+) \$\\pm\$ ([\d.]+)$", cells[4])
    assert sl, cells[4]
    rows[int(m.group(1))] = {"bins": vals, "n": n, "slope": (float(sl.group(1)), float(sl.group(2)))}
assert sorted(rows) == [4, 5, 6, 7, 8]
# the printed numbers, read from the typeset table: first row, last row, a middle value, the galaxy counts and the slopes
assert rows[4]["bins"] == [(-2.22, 0.13, 0.05), (-2.03, 0.02, 0.04), (-1.88, 0.02, 0.02)] and rows[4]["n"] == [52, 510, 927] and rows[4]["slope"] == (0.17, 0.03)
assert rows[8]["bins"] == [(-2.5, 1.26, 0.43), (-2.35, 0.46, 0.16), (-1.6, 0.32, 0.54)] and rows[8]["n"] == [3, 15, 12] and rows[8]["slope"] == (0.45, 0.37)
assert rows[6]["bins"][1] == (-2.2, 0.05, 0.16) and rows[7]["bins"][2] == (-1.76, 0.23, 0.33) and rows[5]["n"] == [24, 227, 223]
# the paper's slope column against its own medians: the end-to-end rise of the medians per dex of mass is within 0.12 of the fitted slope in every sample
for z, r in rows.items():
    rise = (r["bins"][2][0] - r["bins"][0][0]) / 2.0
    assert abs(rise - r["slope"][0]) < 0.12, (z, rise, r["slope"])
    assert r["bins"][0][0] < r["bins"][1][0] < r["bins"][2][0], z
AX = {"xDefinition": "log10 stellar mass, from the SED fit to the rest-UV photometry (bin centre of the 1 dex bin; the bin edges are the paper's)", "xUnit": "log10(Msun)",
      "yDefinition": "UV-continuum slope beta, f_lambda ~ lambda^beta (median of the galaxies in the stellar-mass bin)", "yUnit": "dimensionless"}
DEF = {"betaWindow": "power-law fit to the best-fit SED spectrum in the wavelength windows of Calzetti et al. 1994 (the paper does not list the windows)", "dustTreatment": "attenuated",
       "dustModel": "observed light: the SED fit includes dust attenuation with the Calzetti et al. 2000 law, 0 <= A_V <= 2", "betaMethod": "SED fitting, then a power law fitted to the best-fit model spectrum",
       "xVariable": "stellar mass", "massDefinition": "SED-fitting stellar mass from the rest-UV photometry (BC03 2011 models, Calzetti attenuation); no aperture statement", "imf": "salpeter55",
       "population": "Lyman-break galaxies at z = 4 to 8 (CANDELS-GOODS-S, HUDF09, ERS)", "cosmology": "unspecified"}
records = []
for z in (4, 5, 6, 7, 8):
    r = rows[z]
    pts = [{"x": 7.5 + i, "y": b, "yLow": round(b - lo, 3), "yHigh": round(b + hi, 3)} for i, (b, hi, lo) in enumerate(r["bins"])]
    records.append({"id": f"finkelstein12.uvbetam.z{z}", "source": "Finkelstein et al. 2012", "run": "Finkelstein et al. 2012", "kind": "observation", "relation": "uvbetam",
                    "epoch": {"zRepresentative": float(z), "zNominal": float(z), "zMin": float(z), "zMax": float(z), "mode": "observational-bin", "snapshot": None}, "axes": AX, "domain": {"xMin": 7.5, "xMax": 9.5},
                    "representation": {"type": "points", "intervalKind": "uncertainty", "connect": False, "points": pts}, "scatter": None,
                    "selection": {"population": f"Lyman-break galaxies at z = {z} (photometric-redshift samples of the paper)",
                                  "warning": f"Median beta in the three stellar-mass bins 7-8, 8-9 and 9-10 (galaxies per bin, low/middle/high: {'/'.join(str(v) for v in r['n'])}); the x value is the bin centre, not a measured median mass; the band is the 68 per cent range from the paper's Monte Carlo. "
                                             "The paper warns that completeness may drive part of the trend (low-mass red galaxies are harder to detect) and that the masses use only rest-UV photometry. "
                                             f"The paper's fitted slope is {r['slope'][0]} +- {r['slope'][1]} per dex."},
                    "definitions": DEF,
                    "provenance": {"tier": "published-table", "citation": "Finkelstein et al. 2012, ApJ 756, 164 (arXiv:1110.3785), Table 5: values of the UV spectral slope split by stellar mass", "doi": "10.1088/0004-637X/756/2/164", "url": f"https://arxiv.org/abs/{ARX}",
                                   "retrieved": "2026-10-23", "figure": "Table 5", "checksumSha256": sha, "sourceMember": "tab5.tex", "sourceTexSha256": sha_ms,
                                   "extractionMethod": "transcribed from the arXiv LaTeX source of the paper's table and parsed by script; values asserted against the printed numbers in the script"},
                    "calibration": "target", "rankable": True, "notes": "Observational constraint; the paper's own definitions are in the definitions block."})
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} observational UV slope against stellar mass records")
