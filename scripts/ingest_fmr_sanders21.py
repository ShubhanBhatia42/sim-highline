"""Sanders et al. 2021 (arXiv:2009.07292, ApJ 914, 19): z~0 fundamental metallicity relation projected on mu_0.60 = log M* - 0.60 log SFR,
cubic fit to the Andrews & Martini 2013 M*-SFR stacks (eq. 'fmr'). The transcribed cubic is compared with the best-fit curve drawn in the paper's
vector Fig. 'fmr' (upper right panel). Fetches the source by arXiv id."""
import hashlib
import io
import json
import math
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "2009.07292"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "fmr-sanders21.json"
QUOTES = Path(__file__).resolve().parent.parent / "data" / "quotes" / (OUT.stem + ".txt")   # the sentences used, verbatim, with file and line, and the numeric checks
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/vector_figure_src") / ARXIV
RETRIEVED = "2026-10-18"
TEX = SRC / "ms.tex"
FIGURE = "z0z2z3_fmr_combined.pdf"


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
    log.append(f"{path.parent.name}/{path.name}:{idx[k]}: {norm(s)}")


quote(r"12+\log(\mbox{O/H})= 8.80 + 0.188 y - 0.220 y^2 - 0.0531 y^3 \end{equation} where $y=\mu_{0.60} - 10$.")
quote(r"\mu_{\alpha} \equiv \log(M_*/\mbox{M}_{\odot}) - \alpha\times\text{log}\left(\frac{\text{SFR}}{\msun~\text{yr}^{-1}}\right) .")
quote(r"We find that the scatter of the $z\sim0$ stacks is minimized at a value of $\alpha=0.60$")
quote(r"where the coefficient of the SFR, $\alpha=0.60$, is that which minimizes the scatter of the $z\sim0$ \mstar+SFR binned stacks.")
quote(r"The black line displays the best-fit cubic function to the $z\sim0$ stacks, given in equation~\ref{eq:fmr}.")
quote(r"For a range of $\alpha$, we fit 12+log(O/H) vs.\ $\mu_{\alpha}$ of the $z\sim0$ stacks with a cubic function")
quote(r"We limit the $z\sim0$ sample to those \mstar-SFR bins containing at least 5 galaxies")
quote(r"galaxies at $z\sim0.08$ from \citet[][hereafter AM13]{and13}, binned both in stellar mass alone and in \mstar\ and SFR.")
quote(r"The stellar masses and SFRs of both the individual SDSS galaxies and \citet{and13} stacks have been shifted to a \citet{cha03} IMF, and the SFRs have also been renormalized to the \citet{hao11} H$\alpha$ calibration.")
quote(r"SFR and \mstar\ for stacked spectra are taken to be the median SFR and \mstar\ of the individual galaxies in each bin.")
quote(r"The \citet{and13} stacks were corrected for DIG contamination following \citet{san17}.")
quote(r"Note that we have not corrected the H$\alpha$-based SFRs for DIG")
quote(r"employing different metallicity calibrations at $z\sim0$ and $z>1$, all of which are empirically calibrated to direct-method metallicities, to reflect evolving ISM conditions.")
quote(r"At all redshifts, metallicities are estimated using line ratios of [O\ii], H$\beta$, [O\iii], and [Ne\iii].")
quote(r"Direct-method metallicities for both the AM13 and \citet{ber12} samples have been uniformly recalculated using PyNeb")
quote(r"Star-formation rates are derived from dust-corrected Balmer emission-line luminosities (H$\alpha$ if available, otherwise H$\beta$) using the H$\alpha$ conversion of \citet{hao11}, renormalized to a \citet{cha03} IMF")
quote(r"The FMR projection in the right panel of Figure~\ref{fig:fmr} displays a flattening above $\mu_{0.60}=10.0$")
quote(r"At $z=0$, the intrinsic scatter of the FMR is $\approx0.05$~dex")
assert not FAILED, FAILED
fetch("1211.3418", Path("/tmp/vector_figure_src") / "1211.3418")  # the Andrews & Martini source is read for one quote
quote(r"0.027~<~$z$~<~0.25 to ensure that the \oii\ line and the \oiia\ lines fall within the wavelength range of the SDSS spectrograph", path=Path("/tmp/vector_figure_src/1211.3418/ms.tex"))

alpha = 0.60
fit = lambda mu: 8.80 + 0.188 * (mu - 10) - 0.220 * (mu - 10) ** 2 - 0.0531 * (mu - 10) ** 3
import pymupdf  # noqa: E402

page = vf.page_of(SRC / FIGURE)
frames = vf.frames(page)
fl, fp = frames[0], frames[1]  # left panel (O/H vs M*) and upper-right panel (O/H vs mu_0.60)
words = page.get_text("words")
xl = [((w[0] + w[2]) / 2, vf.number(w[4])) for w in words if vf.number(w[4]) is not None and w[1] > 328 and fp.x0 <= (w[0] + w[2]) / 2 <= fp.x1]
fx, xt = vf.axis_fit(page, fp, "x", labels=xl)  # x labels of the right column sit under the lower-right residual panel
fy, yt = vf.axis_fit(page, fl, "y")  # the upper-right panel shares the y scale of the left panel: asserted on the tick positions
tl = {round(t, 1) for t in vf._tick_positions(page, fl, "y")}
tp = {round(t, 1) for t in vf._tick_positions(page, fp, "y")}
assert tp <= tl and abs(fl.y0 - fp.y0) < 0.1 and abs(fl.y1 - fp.y1) < 0.1
assert any("0.60" in w[4] and w[0] > 320 for w in words), "panel label must carry alpha=0.60"
strokes = [d for d in page.get_drawings() if d["type"] == "s" and d["color"] and max(d["color"]) < 0.1 and len(d["items"]) > 10 and abs((d.get("width") or 0) - 2.0) < 0.01]
assert len(strokes) == 1
pts = [strokes[0]["items"][0][1]] + [it[-1] for it in strokes[0]["items"]]
P = [(fx(p.x), fy(p.y)) for p in pts]
diff = [fit(x) - y for x, y in P]
mx = max(abs(v) for v in diff)
assert mx < 0.005, mx
xlo, xhi = round(P[0][0], 3), round(P[-1][0], 3)
peak = max(range(2001), key=lambda i: fit(9 + i * 0.0015))
checks = [f"drawn black best-fit cubic ({len(P)} vertices, x {xlo}..{xhi}) minus transcribed cubic: max |diff| = {mx:.4f} dex (rms {math.sqrt(sum(v * v for v in diff) / len(diff)):.4f}); ends: drawn {P[0][1]:.3f},{P[-1][1]:.3f} vs cubic {fit(P[0][0]):.3f},{fit(P[-1][0]):.3f}",
          f"cubic maximum {fit(9 + peak * 0.0015):.3f} at mu_0.60 = {9 + peak * 0.0015:.2f} (the paper: flattening above mu_0.60 = 10.0)"]
print("\n".join(checks))

tar = Path(str(SRC) + ".tar")
prov = {"tier": "published-fit", "citation": "Sanders et al. 2021, ApJ 914, 19 (arXiv:2009.07292), eq. 'fmr' (Sec. 'The fundamental metallicity relation at z=0-3.3')",
        "doi": "10.3847/1538-4357/abf4c1", "url": "https://arxiv.org/abs/2009.07292", "retrieved": RETRIEVED, "sourceMember": "ms.tex",
        "figureMember": FIGURE, "figureSha256": hashlib.sha256((SRC / FIGURE).read_bytes()).hexdigest()}
if tar.exists():
    prov["sourceArchiveSha256"] = hashlib.sha256(tar.read_bytes()).hexdigest()
rec = {
    "id": "sanders21.sdss-stacks.fmr.mu0.60.cubic", "source": "Sanders et al. 2021", "run": "z~0 cubic fit to Andrews & Martini stacks", "kind": "observation", "relation": "fmr",
    "epoch": {"zRepresentative": 0.08, "zMin": 0.027, "zMax": 0.25, "mode": "observational-bin", "snapshot": None},
    "axes": {"xDefinition": "mu_0.60 = log10(M*/Msun) - 0.60 log10(SFR/(Msun/yr)); median M* and median SFR of each stack, SFR from Halpha (Hao+11 calibration), Chabrier IMF",
             "xUnit": "log10(Msun)", "yDefinition": "12+log10(O/H), strong-line ratios ([OII], Hbeta, [OIII], [NeIII]) with z~0 calibrations anchored to direct-method (Te) metallicities, DIG-corrected", "yUnit": "dex"},
    "domain": {"xMin": xlo, "xMax": xhi},
    "representation": {"type": "parametric", "equation": "12+log(O/H) = 8.80 + 0.188 y - 0.220 y^2 - 0.0531 y^3, y = mu_0.60 - 10",
                       "expression": "8.80+0.188*(x-10)-0.220*Math.pow(x-10,2)-0.0531*Math.pow(x-10,3)", "parameters": {}},
    "scatter": {"value": 0.05, "unit": "dex", "meaning": "intrinsic scatter of the FMR at z=0 quoted in the paper text ('approximately 0.05 dex', citing Mannucci+10, Cresci+19, Curti+20); not measured for this fit"},
    "selection": {"population": "Andrews & Martini 2013 SDSS stacks in M*-SFR bins with at least 5 galaxies, DIG-corrected line fluxes; z~0.08",
                  "warning": "Cubic fit to z~0 stacks only; the paper reports that its z~2.3 and z~3.3 stacks fall on it without being fitted. x range is the extent of the curve drawn in the paper's figure (not stated in the text). The redshift range 0.027<z<0.25 is that of the Andrews & Martini stacks (their paper, Sec. 2), zRepresentative 0.08 is the paper's 'z~0.08'. The cubic turns over (maximum 8.84 at mu=10.38) and decreases beyond it, which is the shape drawn. SFRs are not DIG-corrected; metallicities are NOT the Andrews & Martini direct-method values but strong-line values calibrated to them."},
    "definitions": {"muAlpha": alpha, "metallicityQuantity": "gas-O/H",
                    "metallicityCalibration": "strong-line calibrations (O32, R23, [NeIII]/[OII] etc.) anchored to direct-method (Te) metallicities of SDSS stacks and dwarfs (Sanders+21 z~0 set), DIG-corrected",
                    "sfrTimescaleMyr": "unspecified", "sfrIndicator": "Halpha (dust-corrected Balmer lines), Hao+11 calibration renormalised to Chabrier IMF, not DIG-corrected",
                    "imf": "chabrier03", "massDefinition": "sed-total", "population": "star-forming"},
    "provenance": prov, "calibration": "validation", "rankable": True,
    "notes": "Cubic as published. " + " ".join(checks),
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": [rec]}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + checks) + "\n")
print("Wrote 1 record to", OUT)
