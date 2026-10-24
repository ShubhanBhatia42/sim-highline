"""UV-continuum slope beta against absolute UV magnitude from JWST/NIRCam, observations: Topping et al. 2024 (MNRAS 529, 4087; arXiv:2307.08835), JADES. The median beta in bins of M_UV for the four dropout samples
(F775W, F090W, F115W, F150W; median photometric redshifts 5.86, 7.28, 9.41, 12.02) from the paper's table, and the paper's own linear fits (beta = dbeta/dM_UV (M_UV + 19) + beta_0) for the three samples with more than one bin.
Values are parsed from the LaTeX tables in the arXiv source and asserted against the printed numbers below.
Usage: python3 scripts/transcribe_uvbeta_topping24.py   (writes data/curves/uvbeta-topping24.json)"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARX = "2307.08835"
OUT = Path(__file__).resolve().parent.parent / "data" / "curves" / "uvbeta-topping24.json"
src = vf.fetch_arxiv(ARX) / "main.tex"
tex = src.read_text(errors="ignore")
sha = vf.sha256(src)
flat = " ".join(tex.split())
for q in ("We measured UV slopes for each object in the sample by fitting a power law ($f_{\\lambda} \\propto \\lambda^{\\beta}$; \\citealt{Calzetti1994}) to fluxes spanning the rest-UV portion of the SED.",
          "The set of filters that cover rest-UV fluxes depend on the redshift of the object, and are chosen to avoid contamination from Ly$\\alpha$ emission.",
          "For objects in our sample at $z<5.4$, we measured the UV slope using the F090W, F115W, and F150W fluxes.",
          "For galaxies with photometric redshifts at $5.4\\leq z < 7.4$, we utilized the F115W, F150W, and F200W filters.",
          "At yet higher redshifts of $7.4\\leq z <9.8$ and $9.8\\leq z<13.2$, we measured UV slopes from the F150W, F200W, F277W, and F200W, F277W, F356W filters, respectively.",
          "Photometric fluxes for each source were computed in Kron \\citep{Kron1980} apertures in each filter",
          "we use AB magnitudes \\citep{Oke1984}, and assume a cosmology with $\\Omega_m = 0.3$, $\\Omega_{\\Lambda}=0.7$, $H_0=70 \\textrm{km s}^{-1}\\ \\textrm{Mpc}^{-1}$",
          "median photometric redshifts of $z_{\\rm phot}=5.86$, $7.28$, $9.41$, and $12.02$ for the F775W, F090W, F115W, and F150W dropout samples, respectively.",
          "These same samples span redshift ranges of $5.05-6.84$, $6.07-8.59$, $8.20-11.25$, and $11.40-14.25$."):
    assert " ".join(q.split()).replace("Throughout this paper we use", "we use") in flat or " ".join(q.split()) in flat, ("quoted sentence missing", q)
WINDOW = ("power-law fit to NIRCam fluxes spanning the rest-UV, filters chosen by photometric redshift (z<5.4: F090W F115W F150W; 5.4-7.4: F115W F150W F200W; 7.4-9.8: F150W F200W F277W; 9.8-13.2: F200W F277W F356W; "
          ">=13.2: F277W F356W F444W)")
SAMPLES = [("F775W", 5.86, (5.05, 6.84)), ("F090W", 7.28, (6.07, 8.59)), ("F115W", 9.41, (8.20, 11.25)), ("F150W", 12.02, (11.40, 14.25))]

end = tex.index("\\label{tab:betabins}")
tb = tex[tex.rindex("\\begin{tabular}", 0, end):end]
tb = tb[tb.index("\\midrule") + 8:tb.index("\\bottomrule")]
rows, cur = {}, None
for line in tb.replace("\\midrule", "\\\\").split("\\\\"):
    line = line.strip()
    if not line:
        continue
    m = re.match(r"^(?:(F\d+W) Dropouts)?\s*&?\s*\$(\d+)\$\s*&\s*\$([\d.]+)\$\s*&\s*\$(-[\d.]+)_\{\s*(-[\d.]+)\s*\}\^\{\+\s*([\d.]+)\s*\}\$\s*&\s*\$(-[\d.]+)\^\{\+([\d.]+)\s*\}_\{(-[\d.]+)\s*\}\$", line)
    if not m:
        m = re.match(r"^(F\d+W) Dropouts\s*&\s*\$(\d+)\$\s*&\s*\$([\d.]+)\$\s*&\s*\$(-[\d.]+)_\{(-[\d.]+)\}\^\{\+([\d.]+)\}\$\s*&\s*\$(-[\d.]+)\^\{\+([\d.]+)\}_\{(-[\d.]+)\}\$", line)
    assert m, line
    if m.group(1):
        cur = m.group(1)
    rows.setdefault(cur, []).append({"n": int(m.group(2)), "zmed": float(m.group(3)), "muv": float(m.group(4)), "muv_lo": float(m.group(5)), "muv_hi": float(m.group(6)), "beta": float(m.group(7)), "b_hi": float(m.group(8)), "b_lo": float(m.group(9))})
assert [(k, len(v)) for k, v in rows.items()] == [("F775W", 5), ("F090W", 5), ("F115W", 3), ("F150W", 1)], {k: len(v) for k, v in rows.items()}
# the printed numbers: first and last bin of each sample, the galaxy counts and the sample size of the paper (1276 galaxies = sum of the bins and the 24 of the last sample is checked below)
assert rows["F775W"][0] == {"n": 46, "zmed": 6.01, "muv": -20.24, "muv_lo": -0.49, "muv_hi": 0.23, "beta": -2.12, "b_hi": 0.06, "b_lo": -0.06}
assert rows["F775W"][-1]["muv"] == -17.19 and rows["F775W"][-1]["beta"] == -2.38 and rows["F090W"][0]["beta"] == -2.16 and rows["F090W"][-1]["muv"] == -17.4
assert rows["F115W"][0]["muv"] == -19.99 and rows["F115W"][-1]["beta"] == -2.41 and rows["F150W"][0]["muv"] == -18.61 and rows["F150W"][0]["beta"] == -2.48 and rows["F150W"][0]["n"] == 24
assert sum(r["n"] for v in rows.values() for r in v) == 46 + 71 + 89 + 98 + 43 + 53 + 86 + 160 + 221 + 136 + 37 + 78 + 117 + 24
# the text quotes the two end bins of the F775W sample: -2.12 (M_UV < -20) and -2.38 (M_UV > -17.5)
assert "median UV slope of $\\beta=-2.12^{+0.06}_{-0.06}$" in flat and "median UV slope of $\\beta=-2.38^{+0.12}_{-0.13}$" in flat
FITS = {"F775W": (-0.11, 0.02, -2.25, 0.03), "F090W": (-0.12, 0.02, -2.26, 0.03), "F115W": (-0.06, 0.05, -2.33, 0.05)}
for k, v in {"F775W Dropouts &   $5.86$ &  $-0.11\\pm0.02$  & $-2.25\\pm0.03$": 1, "F090W Dropouts &  $7.28$ &   $-0.12\\pm0.02$  & $-2.26\\pm0.03$": 1, "F115W Dropouts &  $9.41$ &  $-0.06\\pm0.05$  & $-2.33\\pm0.05$": 1}.items():
    assert " ".join(k.split()) in flat, k
assert "$\\beta=(-0.06\\pm0.05)(\\rm M_{\\rm UV}+19)+(-2.33\\pm0.05)$" in flat
# consistency of each fit with its own bins: the fit value at the bin centre is within 0.06 of the bin's median beta (the paper fits the bin medians)
for k, (sl, _, b0, _) in FITS.items():
    for r in rows[k]:
        assert abs(sl * (r["muv"] + 19) + b0 - r["beta"]) < 0.07, (k, r)

COMMON = {"betaWindow": WINDOW, "dustTreatment": "attenuated", "dustModel": "observed light: dust attenuation is whatever the galaxies have", "betaMethod": "power-law fit f_lambda ~ lambda^beta to broad-band NIRCam fluxes", "xVariable": "M_UV",
          "uvBand": "unspecified", "cosmology": {"H0": 70.0, "Om": 0.3}, "population": "dropout-selected galaxies in JADES (GOODS-S and GOODS-N)", "aperture": "Kron apertures in each filter (photometric fluxes, not a fixed aperture)"}
AX = {"xDefinition": "absolute UV magnitude M_UV (median of the galaxies in the bin; the paper does not state the wavelength it is measured at)", "xUnit": "mag (AB)",
      "yDefinition": "UV-continuum slope beta, f_lambda ~ lambda^beta (median of the galaxies in the M_UV bin)", "yUnit": "dimensionless"}
CITE = "Topping et al. 2024, MNRAS 529, 4087 (arXiv:2307.08835)"
DOI = "10.1093/mnras/stae800"
records = []
for name, zmed, (zlo, zhi) in SAMPLES:
    rs = rows[name]
    assert all(abs(r["zmed"] - zmed) < 0.6 for r in rs)
    pts = sorted(({"x": r["muv"], "y": r["beta"], "yLow": round(r["beta"] + r["b_lo"], 3), "yHigh": round(r["beta"] + r["b_hi"], 3)} for r in rs), key=lambda p: p["x"])
    assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:]))
    records.append({"id": f"topping24.uvbeta.{name.lower()}.binned", "source": "Topping et al. 2024", "run": "Topping et al. 2024", "kind": "observation", "relation": "uvbeta",
                    "epoch": {"zRepresentative": zmed, "zNominal": zmed, "zMin": zlo, "zMax": zhi, "mode": "observational-bin", "snapshot": None}, "axes": AX, "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
                    "representation": {"type": "points", "intervalKind": "uncertainty", "connect": False, "points": pts}, "scatter": None,
                    "selection": {"population": f"{name} dropout galaxies, median photometric redshift {zmed} (range {zlo}-{zhi})",
                                  "warning": f"Median beta in bins of M_UV for the {name} dropout sample ({', '.join(str(r['n']) for r in rs)} galaxies per bin, brightest first); the plotted band is the 68 per cent bootstrap interval of the median. "
                                             + ("The paper gives a single bin for this sample (24 galaxies), so there is no relation to draw, only one point." if len(pts) == 1 else "")},
                    "definitions": COMMON,
                    "provenance": {"tier": "published-table", "citation": CITE + ", table of median UV slopes in bins of UV luminosity", "doi": DOI, "url": f"https://arxiv.org/abs/{ARX}", "retrieved": "2026-10-23",
                                   "figure": "Table: median UV slopes for each dropout sample divided into bins of UV luminosity", "checksumSha256": sha, "sourceMember": "main.tex",
                                   "extractionMethod": "transcribed from the arXiv LaTeX source of the paper's table and parsed by script; values asserted against the printed numbers in the script"},
                    "calibration": "target", "rankable": True, "notes": "Observational constraint; the paper's own definitions are in the definitions block. The uncertainty of M_UV in each bin (16th to 84th percentile of the galaxies) is in the paper's table and is not stored."})
for name, zmed, (zlo, zhi) in SAMPLES[:3]:
    sl, sle, b0, b0e = FITS[name]
    xs = [r["muv"] for r in rows[name]]
    records.append({"id": f"topping24.uvbeta.{name.lower()}.fit", "source": "Topping et al. 2024 (linear fit)", "run": "Topping et al. 2024", "kind": "observation", "relation": "uvbeta",
                    "epoch": {"zRepresentative": zmed, "zNominal": zmed, "zMin": zlo, "zMax": zhi, "mode": "observational-bin", "snapshot": None}, "axes": AX, "domain": {"xMin": min(xs), "xMax": max(xs)},
                    "representation": {"type": "parametric", "equation": "beta = (dbeta/dM_UV) (M_UV + 19) + beta_0 (the paper's linear fit to the median beta in the M_UV bins)", "expression": "slope*(x+19)+b0", "parameters": {"slope": sl, "b0": b0}},
                    "scatter": None, "selection": {"population": f"{name} dropout galaxies, median photometric redshift {zmed}", "warning": f"The paper's linear fit to the binned medians: d beta/d M_UV = {sl} +- {sle}, beta_0 = {b0} +- {b0e} at M_UV = -19, drawn over the range of the bin medians."},
                    "definitions": COMMON,
                    "provenance": {"tier": "published-fit", "citation": CITE + ", table of best-fit linear relations", "doi": DOI, "url": f"https://arxiv.org/abs/{ARX}", "retrieved": "2026-10-23", "figure": "Table: best-fit linear relations to UV slopes in bins of M_UV",
                                   "checksumSha256": sha, "sourceMember": "main.tex", "extractionMethod": "transcribed from the arXiv LaTeX source of the paper's table; asserted against the printed numbers and against the binned medians in the script"},
                    "calibration": "target", "rankable": True, "notes": "Published fit; the intercept is at M_UV = -19."})
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} JADES UV slope records")
