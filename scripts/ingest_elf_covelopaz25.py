"""Covelo-Paz et al. 2025 (arXiv:2409.17241, A&A 694, A178): observed H-alpha luminosity functions at z ~ 4.45, 5.30 and 6.15 from JWST NIRCam grism spectroscopy
(CONGRESS and FRESCO), from the paper's Table 3 (relation elf).

The values are transcribed from the table in the arXiv LaTeX source. The luminosities are observed ones, not corrected for dust.
Checks inside this script (every assert must pass or nothing is written):
  * the number of sources in the table bins does not exceed the number of sources the text gives for the redshift bin (527, 379 and 94, broad-line emitters removed);
  * the best-fitting Schechter functions of the paper's Table 4 reproduce the tabulated number densities within the printed errors, bin by bin (this also fixes the unit: per dex, not per 0.25 dex bin).
Every definition used by the record is located verbatim in the arXiv source; file and line are written to data/quotes/elf-covelopaz25.txt.
"""
import hashlib
import io
import json
import math
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np

ARXIV = "2409.17241"
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "data" / "curves" / "elf-covelopaz25.json"
QUOTES = ROOT / "data" / "quotes" / (OUT.stem + ".txt")
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/elf_sources") / ARXIV
RETRIEVED = "2026-10-23"
TEX = SRC / "main.tex"


def fetch(arxiv_id, dest):
    if dest.exists() and any(dest.iterdir()):
        return
    dest.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{arxiv_id}", headers={"User-Agent": "Mozilla/5.0"})
    blob = urllib.request.urlopen(req).read()
    Path(str(dest) + ".tar").write_bytes(blob)
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(dest)


fetch(ARXIV, SRC)
ARCHIVE_SHA = hashlib.sha256(Path(str(SRC) + ".tar").read_bytes()).hexdigest() if Path(str(SRC) + ".tar").exists() else None
text = TEX.read_text(errors="replace")
log = []
norm = lambda a: re.sub(r"\s+", " ", a).strip()
flat, idx = "", []
for n, l in enumerate(text.splitlines(), 1):
    flat += norm(l) + " "
    idx += [n] * (len(norm(l)) + 1)


def quote(s):
    k = flat.find(norm(s))
    assert k >= 0, f"quote not found: {s[:90]}"
    log.append(f"{TEX.name}:{idx[k]}: {norm(s)}")
    return f"{TEX.name}:{idx[k]}"


q_obs = quote(r"We compute the observed H$\alpha$ luminosity functions (LFs) in three bins centered at $z\sim4.45$, $5.30$, and $6.15$")
q_cosmo = quote(r"we adopt a concordance flat $\Lambda$CDM cosmology with $H_0=70\,\textrm{km}\,\textrm{s}^{-1}\,\textrm{Mpc}^{-1}$, $\Omega_m=0.3$, and $\Omega_\Lambda=0.7$.")
q_ap = quote(r"While the grism data measures the full (spatially resolved) emission line without flux loss (in principle)")
q_bins = quote(r"one for all CONGRESS data, with $3.8<z<5.1$; and two for FRESCO data, splitting our redshift range in half: $4.9<z<5.7$, and $5.7<z<6.6$.")
q_broad = quote(r"We remove the broad-line H$\alpha$ emitters from the luminosity function calculation, as their H$\alpha$ flux does not only probe star formation")
q_cnt = quote(r"This resulted in 527 CONGRESS sources at $z\sim4.45$, 379 FRESCO sources at $z\sim5.3$, and 94 FRESCO sources in the last bin centered at $z\sim6.15$.")
q_vmax = quote(r"For each redshift bin, we derive the observed H$\alpha$ luminosity function following the $V/V_\textrm{max}$ method")
q_sn = quote(r"Our final catalog only contains sources with an H$\alpha$ flux $\textrm{S/N}>5$")
q_eq = quote(r"\phi=\frac{dn}{d\log{L}}=\ln{(10)}\,\phi^*")
q_mock = quote(r"one line of H$\alpha$ ($6\,564.59\AA$), a doublet of [NII] ($6\,549.84\AA$,  $6\,585.23\AA$), and a doublet of [SII]")
q_comp = quote(r"The completeness is a multiplication of the detection, extraction, line detection, and visual inspection completeness computed for each source")
q_unc = quote(r"The uncertainty of the number density includes Poisson noise, the completeness uncertainty, as well as cosmic variance following \citet{Trenti+08}")

# ---------------------------------------------------------------- Table 3 (binned LF) and Table 4 (Schechter fits)
i = text.index("\\label{tab:HaLF}")
tab = text[text.rindex("\\begin{table}", 0, i):i]
rows = {}
key = None
for line in tab.split("\n"):
    m = re.search(r"multicolumn\{4\}\{c\}\{(Congress|FRESCO) \(\$z\\sim([\d.]+)\$\)\}", line)
    if m:
        key = float(m.group(2))
        rows[key] = []
        continue
    m = re.match(r"\s*([\d.]+) & (\d+) & ([\d.]+) & \$([\d.]+)_\{-([\d.]+)\}\^\{\+([\d.]+)\}\$", line)
    if m and key is not None:
        v = [float(g) for g in m.groups()]
        rows[key].append(dict(logL=v[0], n=int(v[1]), comp=v[2], phi=v[3] * 1e-3, lo=v[4] * 1e-3, hi=v[5] * 1e-3))
assert {k: len(v) for k, v in rows.items()} == {4.45: 6, 5.3: 5, 6.15: 4}, {k: len(v) for k, v in rows.items()}
j = text.index("\\label{tab:HaLF_fit}")
t4 = text[text.rindex("\\begin{table}", 0, j):j]
fit = {}
for m in re.finditer(r"\n\s*([\d.]+)&\$([\d.]+)\^\{\+([\d.]+)\}_\{-([\d.]+)\}\$ & \$([\d.]+)\^\{\+[\d.]+\}_\{-[\d.]+\}\$ & \$(-[\d.]+)\^\{\+[\d.]+\}_\{-[\d.]+\}\$", t4):
    fit[float(m.group(1))] = dict(logLs=float(m.group(2)), phis=float(m.group(5)) * 1e-3, alpha=float(m.group(6)))
assert sorted(fit) == [4.45, 5.3, 6.15], fit
TOTAL = {4.45: 527, 5.3: 379, 6.15: 94}
ZBIN = {4.45: (3.8, 5.1), 5.3: (4.9, 5.7), 6.15: (5.7, 6.6)}
SURVEY = {4.45: "CONGRESS (F356W grism, GOODS-North, 62 arcmin2)", 5.3: "FRESCO (F444W grism, GOODS-North and GOODS-South)", 6.15: "FRESCO (F444W grism, GOODS-North and GOODS-South)"}


def schechter_dex(logL, p):
    """dn/dlogL = ln10 phi* x^(alpha+1) exp(-x), x = L/L* (the printed equation writes exp[+x]; the minus sign is the Schechter form)."""
    x = 10 ** (np.asarray(logL) - p["logLs"])
    return math.log(10) * p["phis"] * x ** (p["alpha"] + 1) * np.exp(-x)


records, checks = [], {}
for zz in (4.45, 5.3, 6.15):
    b = rows[zz]
    x = np.array([r["logL"] for r in b])
    phi = np.array([r["phi"] for r in b])
    lo = np.array([r["lo"] for r in b])
    hi = np.array([r["hi"] for r in b])
    assert np.all(np.diff(x) > 0) and np.all(phi - lo > 0)
    nsrc = sum(r["n"] for r in b)
    assert nsrc <= TOTAL[zz], (zz, nsrc)
    model = schechter_dex(x, fit[zz])
    sig = np.where(model > phi, hi, lo)  # error on the side of the point facing the model
    z_score = (phi - model) / sig
    per_bin = schechter_dex(x, fit[zz]) * 0.25  # if the table were per 0.25 dex bin, it would match this instead
    assert np.max(np.abs(z_score)) < 2.0, (zz, z_score)
    assert np.sum(np.abs(np.log10(phi / model))) < np.sum(np.abs(np.log10(phi / per_bin))), "unit (per dex) not supported by the fit"
    chi = float(np.sqrt(np.mean(z_score ** 2)))
    checks[zz] = dict(sources=nsrc, sources_in_bin=TOTAL[zz], rms_z_vs_fit=round(chi, 2), max_abs_z=round(float(np.max(np.abs(z_score))), 2))
    pts = [{"x": round(float(xx), 3), "y": round(math.log10(p), 4), "yLow": round(math.log10(p - l), 4), "yHigh": round(math.log10(p + h), 4)} for xx, p, l, h in zip(x, phi, lo, hi)]
    zlo, zhi = ZBIN[zz]
    note = (f"Table 3 transcribed ({len(b)} bins of 0.25 dex, {nsrc} of the {TOTAL[zz]} H-alpha emitters of the redshift bin; bins below 65 per cent average completeness are not tabulated). "
            f"Checks: the Table 4 Schechter fit (log L*={fit[zz]['logLs']}, phi*={fit[zz]['phis']*1e3:g}e-3, alpha={fit[zz]['alpha']}) agrees with every point to within 2 sigma of the printed error "
            f"(rms {chi:.2f} sigma), which also shows the table is per dex; the number of sources in the bins is below the {TOTAL[zz]} the text gives for the redshift bin.")
    records.append({
        "id": f"covelopaz25.fresco-congress.elf.halpha.z{zz:g}", "source": "Covelo-Paz et al. 2025 (FRESCO, CONGRESS)", "run": "observed H-alpha luminosity function (Table 3, completeness-corrected phi)",
        "kind": "observation", "relation": "elf",
        "epoch": {"zRepresentative": zz, "zNominal": zz, "zMin": zlo, "zMax": zhi, "mode": "observational-bin", "snapshot": None},
        "axes": {"xDefinition": "log10 observed H-alpha line luminosity (grism line flux, not corrected for dust)", "xUnit": "log10(erg s^-1)",
                 "yDefinition": "log10 number density of H-alpha emitters per dex of luminosity from the V/Vmax method, corrected for the completeness of each source", "yUnit": "log10(Mpc^-3 dex^-1)"},
        "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
        "representation": {"type": "points", "intervalKind": "uncertainty", "connect": True, "points": pts},
        "scatter": None,
        "selection": {"population": f"H-alpha emitters with line S/N > 5 and quality flag q >= 1.75 in {SURVEY[zz]}; broad-line emitters removed",
                      "warning": "Observed luminosities: no dust correction. Only bins with average completeness of at least 65 per cent are tabulated. Errors are Poisson, completeness uncertainty and cosmic variance (asymmetric; the band is the printed error). "
                                 "Luminosity bins of 0.25 dex; each redshift bin is wide (3.8 < z < 5.1, 4.9 < z < 5.7, 5.7 < z < 6.6), and evolution inside the bin is not modelled."},
        "definitions": {
            "line": "H-alpha (without [NII])",
            "dustCorrection": "attenuated",
            "dustCorrectionMethod": "none (observed luminosities)",
            "densityFrame": "comoving",
            "apertureDefinition": "total grism line flux of the whole galaxy (spatially resolved, no flux loss in principle)",
            "cosmology": {"H0": 70, "Om": 0.3},
            "population": "H-alpha emitters in the grism surveys, broad-line emitters removed (star-forming galaxies and narrow-line AGN)",
        },
        "provenance": {"tier": "published-table", "citation": "Covelo-Paz et al. 2025, A&A 694, A178 (arXiv:2409.17241), Table 3", "doi": "10.1051/0004-6361/202452363",
                       "url": "https://arxiv.org/abs/2409.17241", "retrieved": RETRIEVED, "sourceMember": TEX.name, "sourceArchiveSha256": ARCHIVE_SHA,
                       "quotes": {"observed": q_obs, "cosmology": q_cosmo, "aperture": q_ap, "redshift_bins": q_bins, "broad_line": q_broad, "counts": q_cnt, "method": q_vmax, "line_snr": q_sn,
                                  "per_dex": q_eq, "mock_lines": q_mock, "completeness": q_comp, "errors": q_unc},
                       "definitionBasis": "line: the paper calls the measured quantity the H-alpha flux and models H-alpha, [NII] and [SII] as separate lines in its completeness simulations; it does not say in a sentence that the real fluxes exclude [NII] (read, not stated). densityFrame: Mpc^-3 is not called comoving anywhere (read, not stated)."},
        "calibration": "validation", "rankable": True,
        "notes": note,
    })
assert len(records) == 3
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + ["check z=%g: %s" % (k, json.dumps(v)) for k, v in checks.items()]) + "\n")
for k, v in checks.items():
    print(k, v)
print("Wrote", len(records), "records to", OUT)
