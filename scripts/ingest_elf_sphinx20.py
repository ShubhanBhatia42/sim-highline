"""SPHINX20 H-alpha luminosity functions (relation elf) computed from the public data release (Katz et al. 2023, arXiv:2309.03269; https://github.com/HarleyKatz/SPHINX-20-data).

One intrinsic and one dust-attenuated function per snapshot (z = 4.64, 5, 6, 7, 8, 9, 10): number of galaxies per bin divided by the box volume (20 cMpc)^3 and the bin width (0.25 dex; the check against the paper's figure uses its 0.5 dex bins).
The dust-attenuated function is the mean over the ten sight lines of the release; the band is the range over the sight lines (drawn where every sight line has a galaxy in the bin).
Bins below the turnover of the intrinsic function are not written: the release holds only galaxies with SFR(10 Myr) >= 0.3 Msun/yr, so the faint end is incomplete by construction (the paper says so).

Checks inside this script (every assert must pass or nothing is written):
  * the table has 1380 galaxies, as the paper says, all with SFR(10 Myr) >= 0.3 Msun/yr, and the two intrinsic H-alpha columns of the release agree;
  * the function the paper plots in its line-luminosity-function figure (vector paths of Halpha_lum_func.pdf, axes calibrated on the tick labels) is reproduced to 0.05 dex rms by the release's columns, every
    plotted bin of every redshift, when the sight-line luminosities are corrected for reddening with the release's own E(B-V) and a single reddening coefficient k(Halpha) fitted here (the paper does not give it; the fit
    is reported), and lies between the dust-attenuated and the intrinsic function in every bin above the turnover. This fixes the volume, the bin width, the redshift labels and the units.
Definitions come from sentences of the paper (located verbatim in the arXiv source; file and line in data/quotes/elf-sphinx20.txt) and from the release README.
"""
import csv
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "2309.03269"
ROOT = Path(__file__).resolve().parent.parent
REPO = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/sphinx")
OUT = ROOT / "data" / "curves" / "elf-sphinx20.json"
QUOTES = ROOT / "data" / "quotes" / "elf-sphinx20.txt"
RETRIEVED = "2026-10-23"
URL = "https://github.com/HarleyKatz/SPHINX-20-data"
commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
TABLE = REPO / "data" / "all_basic_data.csv"
DIGEST = hashlib.sha256(TABLE.read_bytes()).hexdigest()
rows = list(csv.DictReader(TABLE.open()))
SRC = vf.fetch_arxiv(ARXIV)
TEX = SRC / "main.tex"
VOL = 20.0 ** 3
EDGES = np.arange(40.0, 44.51, 0.5)
CEN = (EDGES[:-1] + EDGES[1:]) / 2
ZS = [4.64, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
NDIR = 10


def js_numbers(o):
    """Integer-valued floats are written as integers, as the JavaScript step that normalises the records writes them (41.0 -> 41)."""
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: js_numbers(v) for k, v in o.items()}
    if isinstance(o, list):
        return [js_numbers(v) for v in o]
    return o


log = []
norm = lambda a: re.sub(r"\s+", " ", a).strip()
flat, idx = "", []
for n, l in enumerate(TEX.read_text(errors="replace").splitlines(), 1):
    flat += norm(l) + " "
    idx += [n] * (len(norm(l)) + 1)


def quote(s):
    k = flat.find(norm(s))
    assert k >= 0, f"quote not found: {s[:90]}"
    log.append(f"{TEX.name}:{idx[k]}: {norm(s)}")
    return f"{TEX.name}:{idx[k]}"


q_box = quote(r"with a volume of 20$^3$ co-moving Mpc$^3$.")
q_cosmo = quote(r"$\Omega_{\rm m} = 0.3175$, $\Omega_{\Lambda} = 0.6825$, $\Omega_{\rm b} = 0.049$, $\sigma_8 = 0.83$, $H_0 = 67.11 \ \ {\rm km\ s^{-1}\ Mpc^{-1}}$.")
q_gal = quote(r"For each halo, we designate its occupant galaxy to consist of all gas and stellar particles enclosed within its virial radius.")
q_sfr = quote(r"for each galaxy in \sphinxtw{} with a star formation rate $\geq0.3\ {\rm M_{\odot}\ yr^{-1}}$.")
q_dust = quote(r"Dust is assigned to all gas cells using the Small Magellanic Cloud (SMC) dust model described in \cite{Laursen_2009}.")
q_lines = quote(r"Intrinsic for all emission lines listed in Table~\ref{tab:emission_lines}, dust attenuated along ten sight lines for H$\alpha$")
q_n = quote(r"As our data set contains 1,380 galaxies, viewing each along ten sight lines results in 13,800 total spectra")
q_llf = quote(r"we show reddening corrected H$\alpha$ (top) and [O~III]~$\lambda$5007 (bottom) luminosity functions at multiple redshifts")
q_cut = quote(r"We note that the turnover at the faint-end of the luminosity function is due to our SFR cut rather than a physical effect")
q_ten = quote(r"For each redshift, we show a luminosity function for each of the ten different sight lines to demonstrate the expected variance with viewing angle.")
q_ebv = quote(r"Computed from the Balmer decrement (H$\alpha$ and H$\beta$)")
q_imf = quote(r"we have chosen a specific stellar IMF (Kroupa-like), a stellar population synthesis library")

# ---------------------------------------------------------------- check 1: the table
assert len(rows) == 1380, len(rows)
assert all(float(r["sfr_10"]) >= 0.3 - 1e-9 for r in rows), "release holds a galaxy below SFR(10 Myr) = 0.3"
a = np.array([float(r["H__1_6562.80A_int"]) for r in rows])
b = np.array([float(r["HI_6562.8_int"]) for r in rows])
assert np.max(np.abs(np.log10(a / b))) < 1e-3
zs_table = sorted({float(r["redshift"]) for r in rows})
assert zs_table == ZS, zs_table
by_z = {z: [r for r in rows if float(r["redshift"]) == z] for z in ZS}


EDGES_R = np.arange(40.0, 44.51, 0.25)  # the records use finer bins than the paper's figure: with 0.5 dex bins fewer than two bins per curve survive the completeness cut
CEN_R = (EDGES_R[:-1] + EDGES_R[1:]) / 2


def hist(L, edges=EDGES):
    n, _ = np.histogram(np.log10(L[L > 0]), bins=edges)
    return n


def log_phi(n, width=0.5):
    with np.errstate(divide="ignore"):
        return np.log10(n / (VOL * width))


def luminosities(z, kind, k=None, kHa=None):
    s = by_z[z]
    if kind == "int":
        return np.array([float(r["HI_6562.8_int"]) for r in s])
    L = np.array([float(r[f"HI_6562.8_dir_{k}"]) for r in s])
    if kHa is not None:
        L = L * 10 ** (0.4 * kHa * np.array([float(r[f"ebmv_dir_{k}"]) for r in s]))
    return L


# ---------------------------------------------------------------- check 2: the paper's plotted function
page = vf.page_of(SRC / "figures" / "Halpha_lum_func.pdf")
FIG_SHA = vf.sha256(SRC / "figures" / "Halpha_lum_func.pdf")
frame = max(vf.frames(page, 60, 60), key=lambda r: r.width * r.height)
fx, xt = vf.axis_fit(page, frame, "x")
fy, yt = vf.axis_fit(page, frame, "y", snap=5.0)
assert len(xt) >= 5 and len(yt) >= 8, (xt, yt)
COLOUR = {(0.28, 0.51, 0.71): 4.64, (0.53, 0.81, 0.92): 5.0, (0.74, 0.72, 0.42): 6.0, (0.0, 0.39, 0.0): 7.0, (1.0, 0.65, 0.0): 8.0, (0.8, 0.36, 0.36): 9.0, (0.5, 0.0, 0.0): 10.0}
fig = {z: [] for z in ZS}
for c in vf.curves(page, frame, fx, fy, min_items=2):
    z = COLOUR.get(c["color"])
    pts = [(x, y) for x, y in c["points"] if x > 40.5]
    if z is None or abs(c["width"] - 0.5) > 1e-6 or len(pts) < 2:
        continue
    if not all(abs((x - 40.75) / 0.5 - round((x - 40.75) / 0.5)) < 0.03 for x, _ in pts):
        continue  # legend swatches and markers do not sit on the bin centres
    fig[z].append({int(round((x - 40.75) / 0.5)) + 1: y for x, y in pts})  # bin index in CEN (centre 40.25 is index 0)
assert all(len(v) == NDIR for v in fig.values()), {z: len(v) for z, v in fig.items()}


def compare(kHa):
    diffs = []
    for z in ZS:
        per_dir = [hist(luminosities(z, "dir", k, kHa)) for k in range(NDIR)]
        for j in range(len(CEN)):
            drawn = sorted(c[j] for c in fig[z] if j in c)
            if len(drawn) != NDIR:
                continue
            mine = sorted(log_phi(n[j]) for n in per_dir)
            if not np.all(np.isfinite(mine)):
                continue
            diffs += [m - d for m, d in zip(mine, drawn)]
    return np.array(diffs)


best = None
for kHa in np.arange(1.8, 3.01, 0.1):
    d = compare(kHa)
    rms = float(np.sqrt(np.mean(d ** 2)))
    if best is None or rms < best[1]:
        best = (round(float(kHa), 1), rms, len(d), float(np.mean(d)))
KHA, RMS, NPLOT, MEAN = best
assert RMS < 0.05 and NPLOT >= 150 and 2.0 <= KHA <= 2.4, best
# bracket: attenuated <= drawn <= intrinsic in every bin above the turnover (0.05 dex of slack)
brackets = 0
turn = {}
for z in ZS:
    n_int = hist(luminosities(z, "int"))
    peak = int(np.argmax(n_int))
    turn[z] = peak
    for j in range(peak + 1, len(CEN)):
        if n_int[j] == 0:
            continue
        att = np.mean([hist(luminosities(z, "dir", k))[j] for k in range(NDIR)])
        for c in fig[z]:
            if j in c and att > 0:
                assert log_phi(att) - 0.05 <= c[j] <= log_phi(n_int[j]) + 0.05, (z, j, log_phi(att), c[j], log_phi(n_int[j]))
                brackets += 1
assert brackets >= 30, brackets
CHECK = (f"the release's columns reproduce the function the paper plots (reddening-corrected, ten sight lines) to {RMS:.3f} dex rms over {NPLOT} plotted bins (mean {MEAN:+.3f}) with a fitted k(Halpha) = {KHA}; "
         f"the plotted function lies between the dust-attenuated and intrinsic functions in {brackets} bin-and-sight-line cases above the turnover")

# ---------------------------------------------------------------- the records
records = []
for z in ZS:
    cut = float(EDGES[turn[z] + 1])  # lower edge of the first bin above the turnover bin of the intrinsic function (0.5 dex bins, as plotted in the paper)
    start = int(np.searchsorted(EDGES_R, cut - 1e-9))
    n_int = hist(luminosities(z, "int"), EDGES_R)
    per_dir = np.array([hist(luminosities(z, "dir", k), EDGES_R) for k in range(NDIR)])
    n_att = per_dir.mean(axis=0)
    for kind in ("int", "att"):
        pts = []
        for j in range(start, len(CEN_R)):
            if kind == "int":
                n = n_int[j]
                if n < 3:
                    continue
                pts.append({"x": round(float(CEN_R[j]), 3), "y": round(float(log_phi(n, 0.25)), 4), "yLow": round(float(log_phi(n - math.sqrt(n), 0.25)), 4), "yHigh": round(float(log_phi(n + math.sqrt(n), 0.25)), 4), "count": int(n)})
            else:
                if n_att[j] < 3:
                    continue
                p = {"x": round(float(CEN_R[j]), 3), "y": round(float(log_phi(n_att[j], 0.25)), 4), "count": round(float(n_att[j]), 1)}
                if per_dir[:, j].min() > 0:
                    p["yLow"], p["yHigh"] = round(float(log_phi(per_dir[:, j].min(), 0.25)), 4), round(float(log_phi(per_dir[:, j].max(), 0.25)), 4)
                pts.append(p)
        if len(pts) < 2:
            continue
        intrinsic = kind == "int"
        records.append({
            "id": f"katz23.sphinx20.elf.halpha.{'intrinsic' if intrinsic else 'attenuated'}.z{z:g}", "source": "SPHINX20",
            "run": "SPHINX20 H-alpha luminosity function, " + ("intrinsic (derived from the data release)" if intrinsic else "dust attenuated, mean over ten sight lines (derived from the data release)"),
            "kind": "simulation", "relation": "elf",
            "epoch": {"zRepresentative": z, "zNominal": z, "zMin": z, "zMax": z, "mode": "published-epoch", "snapshot": None},
            "axes": {"xDefinition": "log10 H-alpha (6563 A) line luminosity of the galaxy, " + ("intrinsic (before dust)" if intrinsic else "dust attenuated along a sight line"), "xUnit": "log10(erg s^-1)",
                     "yDefinition": "log10 comoving number density of galaxies per dex of line luminosity, bins of 0.25 dex" + ("" if intrinsic else "; mean over the ten sight lines"), "yUnit": "log10(cMpc^-3 dex^-1)"},
            "domain": {"xMin": pts[0]["x"], "xMax": pts[-1]["x"]},
            "representation": {"type": "points", "intervalKind": "uncertainty" if intrinsic else "scatter", "connect": True, "points": pts},
            "scatter": None if intrinsic else {"lower": "smallest of the ten sight-line functions", "upper": "largest of the ten sight-line functions"},
            "selection": {"population": "SPHINX20 data-release galaxies (SFR averaged over 10 Myr >= 0.3 Msun/yr)",
                          "warning": ("Computed by sim-highline from the per-galaxy table of the public release, not read from the paper's figure. Only galaxies with SFR(10 Myr) >= 0.3 Msun/yr are in the release, so the faint end is incomplete: "
                                      "bins at and below the turnover of the intrinsic function are not written. The 20 cMpc box has few bright galaxies (bins hold as few as 3) and one realisation of the density field. "
                                      + ("Error bars are the square root of the count." if intrinsic else "The band is the range over the ten sight lines, where all ten have a galaxy in the bin.")
                                      + " The paper plots a third version, reddening-corrected with the Balmer decrement; it is not a record here.")},
            "definitions": {
                "line": "H-alpha (without [NII])",
                "imf": "unspecified",
                "dustCorrection": "intrinsic" if intrinsic else "attenuated",
                "dustCorrectionMethod": "none (line luminosity before dust)" if intrinsic else "dust radiative transfer with the SMC dust model (RASCAS), mean over ten sight lines",
                "densityFrame": "comoving",
                "apertureDefinition": "all gas and stellar particles within the halo virial radius",
                "cosmology": {"H0": 67.11, "Om": 0.3175},
                "population": "galaxies with SFR(10 Myr) >= 0.3 Msun/yr in the 20 cMpc box (the data-release selection)",
            },
            "provenance": {"tier": "catalog-derived", "citation": "SPHINX20 public data release (Katz et al. 2023; Rosdahl et al. 2018, 2022); luminosity functions derived by sim-highline", "doi": None,
                           "url": URL, "retrieved": RETRIEVED, "compilation": f"{URL} @ {commit}", "sourceMember": "data/all_basic_data.csv", "checksumSha256": DIGEST,
                           "paper": "arXiv:2309.03269", "definitionBasis": "imf: the paper's caveats paragraph says 'we have chosen a specific stellar IMF (Kroupa-like)'; it is filled as Kroupa (2001), the nearest entry of the vocabulary, by data/definition-fills.json, as for the other SPHINX20 records (an earlier version of this note said the paper gave no sentence on the IMF; it does). The IMF is not a comparison key of this relation. line: the release lists H I 6562.80 and [N II] 6548/6583 as separate lines.", "quotes": {"box": q_box, "cosmology": q_cosmo, "galaxy": q_gal, "selection": q_sfr, "dust_model": q_dust, "line_columns": q_lines, "galaxies": q_n,
                                                                   "plotted_function": q_llf, "turnover": q_cut, "sight_lines": q_ten, "ebv": q_ebv, "imf": q_imf},
                           "checkAgainstFigure": {"figure": "Line luminosity functions for Halpha (top)", "checksumSha256": FIG_SHA, "sourceMember": "figures/Halpha_lum_func.pdf", "kHalpha": KHA, "rmsDex": round(RMS, 3), "bins": NPLOT}},
            "calibration": "prediction", "rankable": True,
            "notes": "RAMSES-RT radiation hydrodynamics of reionization in a 20 cMpc box. Volume (20 cMpc)^3 and bin width 0.25 dex (the check against the figure uses the paper's 0.5 dex bins). Checks: " + CHECK + ". The fitted coefficient is used only in that check; no value in this record depends on it (the record counts galaxies by the release's own intrinsic or dust-attenuated column). Intrinsic Halpha is the release column HI_6562.8_int; attenuated is HI_6562.8_dir_0..9. Re-derived from the release with separate code on 2026-10-25 (internal check; counts identical in every bin of every record, see scripts/check_sphinx20_release.py).",
        })
print({r['id']: len(r['representation']['points']) for r in records})
assert len(records) >= 4, len(records)
OUT.write_text(json.dumps(js_numbers({"schemaVersion": "1.0.0", "records": records}), indent=2) + "\n")
QUOTES.write_text("\n".join(log + ["check: " + CHECK, f"release: {URL} @ {commit}, all_basic_data.csv sha256 {DIGEST}", f"figure: figures/Halpha_lum_func.pdf sha256 {FIG_SHA}"]) + "\n")
print(CHECK)
print("turnover bins:", {z: float(CEN[turn[z]]) for z in ZS})
print("Wrote", len(records), "records to", OUT)
