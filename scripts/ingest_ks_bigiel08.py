"""Bigiel et al. 2008 (arXiv:0810.2541, AJ 136, 2846): molecular star formation law at 750 pc in 7 spirals,
Sigma_SFR = a (Sigma_H2 / 10 Msun pc^-2)^N with N = 1.01, A = log10 a = -2.12 (HERACLES CO, FUV+24um SFR).
The paper's published fit is normalised at 10 Msun pc^-2 (eq. 'power-law'); the prose ensemble law (10^-2.1 Sigma_H2^1.0) drops that normalisation.
The script transcribes the fit, asserts it against the black fit line in the vector Fig. 9 (axis calibration validated by the paper's own constant-SFE
lines, which include the 1.36 helium factor) and writes the record. Fetches the source by arXiv id."""
import hashlib
import io
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import pymupdf

ARXIV = "0810.2541"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "ks-bigiel08.json"
QUOTES = Path(__file__).resolve().parent.parent / "data" / "quotes" / (OUT.stem + ".txt")   # the sentences used, verbatim, with file and line, and the numeric checks
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/vector_figure_src") / ARXIV
RETRIEVED = "2026-10-18"
TEX = SRC / "bigiel_sflaw.tex"
FIGURE = "f9.eps"


def fetch(arxiv_id, dest):
    if dest.exists() and any(dest.iterdir()):
        return
    dest.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(f"https://arxiv.org/e-print/{arxiv_id}", headers={"User-Agent": "Mozilla/5.0"})
    blob = urllib.request.urlopen(req).read()
    Path(str(dest) + ".tar").write_bytes(blob)
    print("sha256 of source archive", hashlib.sha256(blob).hexdigest())
    tarfile.open(fileobj=io.BytesIO(blob)).extractall(dest)


fetch(ARXIV, SRC)
log, FAILED = [], []


def quote(s, path=TEX):
    norm = lambda a: re.sub(r"\s+", " ", a).strip()
    flat, idx = "", []
    for n, l in enumerate(path.read_text(errors="replace").splitlines(), 1):
        flat += norm(l) + " "
        idx += [n] * (len(norm(l)) + 1)
    k = flat.find(norm(s))
    if k < 0:
        print("QUOTE NOT FOUND:", s[:100]); FAILED.append(s); return
    log.append(f"{path.name}:{idx[k]}: {norm(s)}")


quote(r"\Sigma_{\rm  SFR} = a~\left( \frac{\Sigma_{\rm HI,H2,gas}}{10~{\rm M}_{\odot}~{\rm pc}^{-2}} \right)^{N}~.")
quote(r"$\Sigma_{\rm SFR}$ at the fiducial gas surface density of $10$~M$_{\odot}$~pc$^{-2}$.")
quote(r"most fits in the literature quote `$A$' at $1$~M$_{\odot}$~pc$^{-2}$ rather than our fiducial $10$~M$_{\odot}$~pc$^{-2}$.")
quote(r"The best fit parameters are $N = 1.01$ and $A = -2.12$; the RMS scatter of $\Sigma_{\rm SFR}$ about the fit is $0.19$~dex")
quote(r"We thus derive a best fit molecular Schmidt law of")
quote(r"\Sigma_{\rm SFR} = 10^{-2.1 \pm 0.2} \Sigma_{\rm H2}^{1.0 \pm 0.2}.")
quote(r"we show the results of a power law fit to $\Sigma_{\rm SFR}$ vs. $\Sigma_{\rm H2}$ for CO data from HERACLES/BIMA SONG in spiral galaxies (where $\Sigma_{\rm gas} \approx \Sigma_{\rm H2}$).")
quote(r"We fit $\Sigma_{\rm SFR}$ vs. $\Sigma_{\rm H2}$ (middle panel) in the regime $\Sigma_{\rm H2} > 3$~M$_{\sun}$\,pc$^{-2}$ for the HERACLES data")
quote(r"These quantities all have units of M$_{\odot}$~pc$^{-2}$ and are {\em hydrogen} surface densities, i.e., they do not include any contribution from helium.")
quote(r"we adopt a CO-to-H$_2$ conversion factor of $2.0 \times 10^{20}$")
quote(r"We assume a ratio $I(2\rightarrow1) / I(1\rightarrow0) = 0.8$")
quote(r"=&3.2 \times 10^{-3} I_{24} \left[{\rm MJy~ster}^{-1}\right] \\ \nonumber &+& 8.1 \times 10^{-2} I_{FUV} \left[{\rm MJy~ster}^{-1}\right]~,")
quote(r"i.e., a Kroupa-type two-component IMF that extends to 120\,M$_\odot$.")
quote(r"one should multiply our $\Sigma_{\rm SFR}$ by a factor of 1.59.")
quote(r"In addition to sampling our data on a pixel-by-pixel basis at 750~pc resolution")
quote(r"Because our analysis is restricted to the regime within the optical radius $r_{25}$")
quote(r"using the ordinary least--squares (OLS) bisector.")
quote(r"The derived mean H$_{2}$ gas depletion time (including helium) is $2.0 \cdot 10^9$~yrs")
assert not FAILED, FAILED

# ---- fit as published ----
N_FIT, A_FIT, SCATTER = 1.01, -2.12, 0.19
fit = lambda x: A_FIT + N_FIT * (x - 1.0)  # normalised at Sigma = 10 Msun pc^-2

# ---- vector Fig. 9, top-left panel (HERACLES CO, FUV+24um, 750 pc): calibrate on drawn tick marks, validate on the drawn lines ----
fig = SRC / FIGURE
with tempfile.TemporaryDirectory() as d:
    pdf = Path(d) / "f9.pdf"
    subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", "-dEPSCrop", f"-sOutputFile={pdf}", str(fig)], check=True, capture_output=True)
    page = pymupdf.open(pdf)[0]
    drawings = page.get_drawings()
frame = pymupdf.Rect(62.9, 20.0, 310.0, 228.0)  # top-left panel: the four long frame strokes (asserted below)
long_h = [it for d in drawings for it in d["items"] if it[0] == "l" and abs(it[1].y - it[2].y) < 0.01 and abs(it[1].x - it[2].x) > 240]
assert any(abs(it[1].y - frame.y0) < 0.2 for it in long_h) and any(abs(it[1].y - frame.y1) < 0.2 for it in long_h)
ys_major = sorted({round(it[1].y, 2) for d in drawings for it in d["items"] if it[0] == "l" and abs(it[1].y - it[2].y) < 0.01 and abs(it[1].x - frame.x0) < 0.2
                   and abs(it[2].x - it[1].x) > 4 and abs(it[2].x - it[1].x) < 6 and frame.y0 < it[1].y < frame.y1})
assert len(ys_major) == 5 and max(b - a for a, b in zip(ys_major, ys_major[1:])) - min(b - a for a, b in zip(ys_major, ys_major[1:])) < 0.1, ys_major
PY_PER_DEX = (ys_major[-1] - ys_major[0]) / 4.0
fy = lambda py: -1.0 - (py - ys_major[0]) / PY_PER_DEX  # the five major ticks carry the labels -1 ... -5 (read on the rendered figure)
xs_minor = sorted({round(it[1].x, 2) for d in drawings for it in d["items"] if it[0] == "l" and abs(it[1].x - it[2].x) < 0.01 and abs(it[1].y - 644.1) < 0.2 and abs(it[3 - 1].y - it[1].y) < 12 and 62 < it[1].x < 311})
steps = [b - a for a, b in zip(xs_minor, xs_minor[1:])]
assert abs(sum(steps) / len(steps) - 7.0) < 0.05
PX_PER_DEX = 70.0  # minor ticks every 0.1 dex
X05 = min(xs_minor, key=lambda t: abs(t - 167.95))
fx = lambda px: 0.5 + (px - X05) / PX_PER_DEX  # tick under the dotted vertical Sigma_H2 sensitivity line carries the label 0.5
# validation of the calibration by the paper's own constant-SFE lines (1%, 10%, 100% of the gas, helium included, converted per 1e8 yr): y = x - 2 + log10(frac) + log10(1.36)
diag = [(d["dashes"], it) for d in drawings for it in d["items"] if it[0] == "l" and abs(it[1].x - frame.x0) < 0.2 and it[2].x > 250 and abs(it[1].y - it[2].y) > 50 and frame.y0 - 0.5 <= min(it[1].y, it[2].y) and max(it[1].y, it[2].y) <= frame.y1 + 0.5]
dotted = sorted((it for dsh, it in diag if dsh.strip() not in ("[] 0", "[ ] 0")), key=lambda it: -it[1].y)
solid = [it for dsh, it in diag if dsh.replace(" ", "") == "[]0"]
assert len(dotted) == 3 and len(solid) == 1, (len(dotted), len(solid))
for it, frac in zip(dotted, (0.01, 0.1, 1.0)):
    xa, xb = fx(it[1].x), fx(it[2].x)
    ya, yb = fy(it[1].y), fy(it[2].y)
    assert abs((yb - ya) / (xb - xa) - 1.0) < 0.01  # unit slope: constant SFE
    assert abs(ya - (xa - 2 + math.log10(frac) + math.log10(1.36))) < 0.02, (frac, ya)
it = solid[0]
xa, xb, ya, yb = fx(it[1].x), fx(it[2].x), fy(it[1].y), fy(it[2].y)
slope_fig, y_at_1 = (yb - ya) / (xb - xa), ya + (yb - ya) / (xb - xa) * (1.0 - xa)
assert abs(slope_fig - N_FIT) < 0.02 and abs(y_at_1 - A_FIT) < 0.02, (slope_fig, y_at_1)  # drawn line: slope 1.01 and Sigma_SFR(10 Msun/pc^2) = 10^-2.12
assert abs(fit(xa) - ya) < 0.02 and abs(fit(xb) - yb) < 0.02  # published expression reproduces both ends of the drawn line
# extent of the data cells (coloured fills: 1, 2, 5 points per cell) in the panel
cell_x = [fx(px) for d in drawings if d["fill"] is not None and max(d["fill"]) > 0 and d["fill"] != (1.0, 1.0, 1.0)
          for px in (d["rect"].x0, d["rect"].x1) if frame.x0 <= d["rect"].x0 and d["rect"].x1 <= frame.x1 + 0.5 and frame.y0 <= d["rect"].y0 and d["rect"].y1 <= frame.y1 + 0.5]
xmax_data = round(max(cell_x), 2)
xmin_stated = round(math.log10(3.0), 3)
checks = [
    f"Fig. 9 top-left drawn fit line: slope {slope_fig:.3f}, value at log Sigma_H2 = 1: {y_at_1:.3f}; at the frame edges (x={xa:.2f}, {xb:.2f}) the published expression gives {fit(xa):.3f}, {fit(xb):.3f} vs drawn {ya:.3f}, {yb:.3f}",
    f"calibration validated by the drawn 1%/10%/100% constant-SFE lines (unit slope, offsets log10(frac)-2+log10(1.36)); y scale {PY_PER_DEX:.3f} pt/dex, x scale 70.0 pt/dex",
    f"data cells of the panel span log Sigma_H2 = {round(min(cell_x), 2)}..{xmax_data}; fit performed for Sigma_H2 > 3 Msun/pc^2 (log = {xmin_stated})",
    "NOTE: the displayed ensemble equation Sigma_SFR = 10^-2.1 Sigma_H2^1.0 omits the 10 Msun/pc^2 normalisation of eq. 'power-law'; the figure confirms the normalised form",
]
print("\n".join(checks))

sha = hashlib.sha256((SRC / FIGURE).read_bytes()).hexdigest()
tar = Path(str(SRC) + ".tar")
prov = {"tier": "published-fit", "citation": "Bigiel et al. 2008, AJ 136, 2846 (arXiv:0810.2541), Sec. 'The Combined Molecular Schmidt Law' and Fig. 9 (top left)",
        "doi": "10.1088/0004-6256/136/6/2846", "url": "https://arxiv.org/abs/0810.2541", "retrieved": RETRIEVED, "sourceMember": "bigiel_sflaw.tex",
        "figureMember": FIGURE, "figureSha256": sha}
if tar.exists():
    prov["sourceArchiveSha256"] = hashlib.sha256(tar.read_bytes()).hexdigest()
rec = {
    "id": "bigiel08.spirals.ks.h2.750pc.heracles", "source": "Bigiel et al. 2008", "run": "molecular law, HERACLES CO, FUV+24um, 750 pc",
    "kind": "observation", "relation": "ks",
    "epoch": {"zRepresentative": 0, "zMin": 0, "zMax": 0, "mode": "observational-bin", "snapshot": None},
    "axes": {"xDefinition": "log10 H2 surface density at 750 pc resolution, from CO(2-1) with N(H2)=2.0e20 Ico, hydrogen only (no helium)",
             "xUnit": "log10(Msun pc^-2)",
             "yDefinition": "log10 SFR surface density from FUV + 24 micron (3.2e-3 I24 + 8.1e-2 IFUV), Kroupa-type IMF to 120 Msun",
             "yUnit": "log10(Msun yr^-1 kpc^-2)"},
    "domain": {"xMin": xmin_stated, "xMax": xmax_data},
    "representation": {"type": "parametric",
                       "equation": "Sigma_SFR = a (Sigma_H2 / 10 Msun pc^-2)^N, log a = A = -2.12, N = 1.01; i.e. log Sigma_SFR = A + N (log Sigma_H2 - 1)",
                       "expression": "A+N*(x-1)", "parameters": {"A": A_FIT, "N": N_FIT}},
    "scatter": {"value": SCATTER, "unit": "dex", "meaning": "RMS scatter of log Sigma_SFR about the fit (stated in the text for this panel)"},
    "selection": {"population": "pixels (750 pc sampling points) inside r25 of 7 nearby spirals with HERACLES CO and THINGS HI; Sigma_H2 > 3 Msun pc^-2",
                  "warning": "Molecular gas only (gasDefinition H2), sub-kpc resolved law: do not compare with a total-gas or galaxy-integrated KS law. The fit is normalised at 10 Msun pc^-2 (the prose ensemble law omits this). xMin is the stated CO sensitivity limit; xMax is the extent of the plotted data cells in Fig. 9 (digitized from the vector figure, not stated in the text). Fitted with the OLS bisector, equal weight per point."},
    "definitions": {
        "gasDefinition": "H2",
        "areaScale": "750 pc resolution pixels (pixel-by-pixel sampling inside r25)",
        "sfrIndicator": "FUV + 24 micron (Sigma_SFR = 3.2e-3 I24 + 8.1e-2 IFUV)",
        "sfrTimescaleMyr": "unspecified",
        "imf": "kroupa01",
        "imfNote": "paper: 'a Kroupa-type two-component IMF that extends to 120 Msun'; multiply Sigma_SFR by 1.59 for a truncated Salpeter IMF",
        "coConversion": "N(H2) = 2.0e20 Ico cm^-2 (K km/s)^-1 with I(2-1)/I(1-0) = 0.8, constant",
        "heliumIncluded": "no (hydrogen surface densities; multiply by ~1.36 for helium)",
        "fitNormalisation": "10 Msun pc^-2",
        "population": "all",
    },
    "provenance": prov, "calibration": "validation", "rankable": True,
    "notes": "N=1.01, A=-2.12, 0.19 dex scatter as published. " + " ".join(checks),
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + checks) + "\n")
print("Wrote 1 record to", OUT)
