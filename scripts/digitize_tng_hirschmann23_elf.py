"""Hirschmann et al. 2023 (MNRAS 526, 3610; arXiv:2212.02522): H-alpha luminosity functions of IllustrisTNG (TNG50, TNG100, TNG300) at z = 0.1 to 6, read from the vector figure
Ha_lumfct_IllustrisTNG_allz_Nov21.eps (the top two rows of the paper's luminosity-function figure; relation elf). The solid coloured lines are the total H-alpha luminosity of each galaxy (H II regions, AGN narrow-line regions,
post-AGB stars and shocks) without attenuation by dust outside H II regions; the dashed lines (H II regions only) are used for a check and are not records.
The figure has no text layer (the tick labels are strokes): each axis is calibrated from its tick marks (positions) with the label values read from the rendered figure, and the calibration is checked against numbers printed in the paper and against
the Sobral et al. 2013 Schechter curve that the figure draws (see the checks printed at the end). Points at or below the peak of a curve are not written: the paper says the peaks "arise from the resolution limits" and the densities below them
"are incomplete and hence not meaningful".
Definitions are located verbatim in the arXiv source (file and line in data/quotes/elf-tng-hirschmann23.txt). Needs PyMuPDF and epstopdf.
Usage: python3 scripts/digitize_tng_hirschmann23_elf.py [SOURCE_DIR]   (writes data/curves/elf-tng-hirschmann23.json)"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "2212.02522"
DOI = "10.1093/mnras/stad2955"
ROOT = Path(__file__).resolve().parent.parent
REF = vf.reference_root()
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
TEX = SRC / "Overview_TNG.tex"
EPS = SRC / "Ha_lumfct_IllustrisTNG_allz_Nov21.eps"
PDF = SRC / "pdf" / EPS.with_suffix(".pdf").name
if not PDF.exists():
    PDF.parent.mkdir(exist_ok=True)
    subprocess.run(["epstopdf", str(EPS), f"--outfile={PDF}"], check=True)
OUT = ROOT / "data" / "curves" / "elf-tng-hirschmann23.json"
QUOTES = ROOT / "data" / "quotes" / "elf-tng-hirschmann23.txt"
page = vf.page_of(PDF)
SHA = vf.sha256(PDF)  # of the original .eps
CITE = "Hirschmann et al. 2023, MNRAS 526, 3610 (arXiv:2212.02522), luminosity-function figure (Fig. 11 by the order of the source's figure environments), top two rows (H-alpha)"
FIGURE = "luminosity-function figure, top two rows (H-alpha), Ha_lumfct_IllustrisTNG_allz_Nov21.eps"
checks = []


def check(cond, msg, scope=None, number=False):
    """scope: None (applies to every record) or a function (simulation, z) -> bool; number: the check compares with a number that a paper prints."""
    assert cond, msg
    checks.append((msg, scope, number))


# ---------------------------------------------------------------- definitions, each from a sentence of the paper
norm = lambda a: re.sub(r"\s+", " ", a).strip()
flat, idx = "", []
for n, l in enumerate(TEX.read_text(errors="replace").splitlines(), 1):
    flat += norm(l) + " "
    idx += [n] * (len(norm(l)) + 1)
log = []


def quote(s):
    k = flat.find(norm(s))
    assert k >= 0, f"quote not found: {s[:90]}"
    log.append(f"{TEX.name}:{idx[k]}: {norm(s)}")
    return f"{TEX.name}:{idx[k]}"


Q = {
    "dust": quote(r"we do not consider attenuation by dust outside \hii\ regions and compare our predictions with observed emission-line ratios corrected for this effect"),
    "observations": quote(r"(all corrected for attenuation by dust; different grey- and black-line styles)"),
    "total": quote(r"which, when combined, constitute the total nebular emission of the galaxy"),
    "aperture": quote(r"all `bound' gas cells and star particles (as identified by the Subfind algorithm;"),
    "population": quote(r"galaxies more massive than $10^8\, \Msun$, $3 \times 10^9 \, \Msun$ and $10^{10} \,  \Msun$, respectively, at $z=0.1,$ 0.5, 1, 1.5, 2, 3, 4, 5 and 6 (different panels, as indicated)."),
    "progenitors": quote(r"For all these galaxies and their progenitors at $z>0$, nebular emission"),
    "mass_cuts": quote(r"TNG50 has $\sim8,800$ galaxies with stellar masses greater than $10^8 \Msun$, TNG100 $\sim18,000$ galaxies with stellar masses greater than $3\times 10^{9} \Msun$ and TNG300 $\sim47,000$ galaxies with stellar masses greater than $10^{10} \Msun$."),
    "peaks": quote(r"The peaks in the TNG100 and TNG300 luminosity functions arise from the resolution limits; galaxy number densities below the peak are incomplete and hence not meaningful."),
    "lines": quote(r"\hb, \oiii, \oi, \ha, \nii\ and \sii\,"),
    "imf": quote(r"a standard \citet{Chabrier03} initial mass function (IMF) truncated at 0.1 and 300\,$\Msun$"),
    "cosmology": quote(r"$\sigma_8 = 0.8159$, $\Omega_{\mathrm{m}}=0.3089$, $\Omega_{\Lambda}=0.6911$ and $h= 0.6774$"),
    "volumes": quote(r"TNG300, TNG100 and TNG50 comprise volumes of 302.6$^3$, 106.5$^3$ and 51.7$^3$ cMpc$^3$, respectively"),
    "decline": quote(r"by a factor of $\sim30$ between $z=3$ and $z=6$ at $\lha = 10^{42}$\,erg\,s$^{-1}$"),
    "hii": quote(r"Dashed coloured lines show the results obtained when considering only the contribution by \hii\ regions to the luminosity of each galaxy."),
}
BOX = {"TNG50": 51.7, "TNG100": 106.5, "TNG300": 302.6}
CUT = {"TNG50": 1e8, "TNG100": 3e9, "TNG300": 1e10}
NPAPER = {"TNG50": 8800, "TNG100": 18000, "TNG300": 47000}  # galaxies at z = 0 above the cut, as printed (with a tilde)

# ---------------------------------------------------------------- panels and axes
rows = vf.grid_from_long_lines(page, 60)
assert len(rows) == 3
top = [r for r in rows[0] if r.width > 100]
bottom = [r for r in rows[2] if r.width > 100][:4]  # the fifth slot of the lower row holds the legend and has no frame
assert len(top) == 5 and len(bottom) == 4
PANELS = list(zip([0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0], top + bottom))
BLACK = (0.0, 0.0, 0.0)


def black_segments():
    out = []
    for d in page.get_drawings():
        if d["color"] is None or max(d["color"]) > 0.15 or len(d["items"]) != 1 or d["items"][0][0] != "l":
            continue
        a, b = d["items"][0][1], d["items"][0][2]
        out.append((a.x, a.y, b.x, b.y))
    return out


SEGS = black_segments()


def ticks_on(frame, axis):
    """Tick marks that touch the left (y) or bottom (x) edge of a frame, as (position, length)."""
    out = []
    for a, b, c, d in SEGS:
        if axis == "x" and abs(a - c) < 0.01 and min(abs(b - frame.y1), abs(d - frame.y1)) < 0.6 and frame.x0 - 0.3 <= a <= frame.x1 + 0.3 and 1 < abs(d - b) < 12:
            out.append((round(a, 3), round(abs(d - b), 2)))
        if axis == "y" and abs(b - d) < 0.01 and min(abs(a - frame.x0), abs(c - frame.x0)) < 0.6 and frame.y0 - 0.3 <= b <= frame.y1 + 0.3 and 1 < abs(c - a) < 12:
            out.append((round(b, 3), round(abs(c - a), 2)))
    return sorted(set(out))


class Axis:
    """Linear map from page position to value, from the major ticks (those longer than 0.75 of the longest) given their values, with a check that they are equally spaced."""

    def __init__(self, ticks, values, tol=0.1):
        top_len = max(ln for _, ln in ticks)
        ms = []
        for p in sorted(p for p, ln in ticks if ln > 0.75 * top_len):
            if not ms or p - ms[-1] > 0.3:
                ms.append(p)
        assert len(ms) == len(values), (len(ms), len(values), ms)
        n = len(ms)
        mp, mv = sum(ms) / n, sum(values) / n
        self.slope = sum((p - mp) * (v - mv) for p, v in zip(ms, values)) / sum((p - mp) ** 2 for p in ms)
        self.icpt = mv - self.slope * mp
        self.resid = max(abs(self.val(p) - v) for p, v in zip(ms, values)) / abs(self.slope)  # pixels
        assert self.resid < tol, ("major ticks are not equally spaced", self.resid)
        self.ms = ms
        self.per_unit = abs(1.0 / self.slope)

    def val(self, p):
        return self.icpt + self.slope * p


XV = [40.5 + 0.5 * i for i in range(8)]  # major ticks every 0.5 dex from 40.5 (left edge) to 44 (right edge); the labelled ones read 41, 42, 43, 44
YV = [-1.0, -2.0, -3.0, -4.0, -5.0]
AX = {}
for z, fr in PANELS:
    AX[z] = (Axis(ticks_on(fr, "x"), XV), Axis(ticks_on(fr, "y"), YV))
perx = {round(a[0].per_unit, 2) for a in AX.values()}
pery = {round(a[1].per_unit, 2) for a in AX.values()}
check(len(perx) == 1 and len(pery) == 1, f"all nine panels have the same tick geometry: {perx.pop():.2f} pt per dex in log L, {pery.pop():.2f} pt per dex in log phi; major ticks equally spaced to {max(max(a[0].resid, a[1].resid) for a in AX.values()):.3f} pt")
# the labels of the lower-left panel: glyph strokes centred on the major ticks of 42, 43 and 44 (the values read from the render are 41, 42, 43, 44 on every second major tick)
fr = PANELS[5][1]
boxes = sorted((d["rect"] for d in page.get_drawings() if d["color"] is not None and max(d["color"]) < 0.15 and fr.y1 + 2 < d["rect"].y0 and d["rect"].y1 < fr.y1 + 20 and fr.x0 - 15 < d["rect"].x0 and d["rect"].x1 < fr.x1 + 12 and d["rect"].width < 12), key=lambda r: r.x0)
cl = []
for r in boxes:
    if cl and r.x0 - cl[-1][1] < 2.2:
        cl[-1][1] = max(cl[-1][1], r.x1)
    else:
        cl.append([r.x0, r.x1])
cent = [(a + b) / 2 for a, b in cl]
mx = AX[3.0][0].ms
near = [min(abs(c - m) for m in mx[3::2]) for c in cent[-3:]]
check(len(cent) >= 4 and all(n < 1.2 for n in near), f"x label glyphs of the lower-left panel centre on the major ticks of 42, 43 and 44 within {max(near):.2f} pt", scope=lambda s_, z_: z_ in (3.0, 4.0, 5.0, 6.0))

# ---------------------------------------------------------------- curves
COL = {"TNG50": (0.0, 0.8, 0.38), "TNG100": (0.8, 0.07, 0.03), "TNG300": (0.26, 0.0, 0.71)}


def paths(color, width, dashed):
    out = []
    for d in page.get_drawings():
        if d["type"] != "s" or d["color"] is None or abs((d.get("width") or 0) - width) > 0.01 or tuple(round(v, 2) for v in d["color"]) != color:
            continue
        if ("[]" not in str(d["dashes"])) == dashed and all(it[0] == "l" for it in d["items"]):
            out.append(d)
    return out


def vertices(d, frame, ax):
    """Interior vertices of a path (those on the frame edge are the clip points of the plotting program), in data coordinates."""
    pts = [d["items"][0][1]] + [it[2] for it in d["items"]]
    keep = [p for p in pts if frame.x0 + 0.35 < p.x < frame.x1 - 0.35 and frame.y0 + 0.35 < p.y < frame.y1 - 0.35]
    return [(ax[0].val(p.x), ax[1].val(p.y)) for p in keep], len(pts) - len(keep)


solid = {s: paths(c, 1.7, False) for s, c in COL.items()}
dashed = {s: paths(c, 0.85, True) for s, c in COL.items()}
check({s: len(v) for s, v in solid.items()} == {"TNG50": 9, "TNG100": 9, "TNG300": 8} and {s: len(v) for s, v in dashed.items()} == {"TNG50": 9, "TNG100": 9, "TNG300": 8}, "26 solid and 26 dashed curves: TNG50 in 9 panels, TNG100 in 9, TNG300 in 8")
curves = {}  # (sim, z) -> dict(solid=[(x, y)], dashed=[(x, y)], clipped=n)
for s in COL:
    for kind, lst in (("solid", solid[s]), ("dashed", dashed[s])):
        for d in lst:
            r = d["rect"]
            c = ((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
            hit = [z for z, fr in PANELS if fr.x0 <= c[0] <= fr.x1 and fr.y0 <= c[1] <= fr.y1]
            assert len(hit) == 1, (s, kind, c)
            z = hit[0]
            fr = dict(PANELS)[z]
            pts, nclip = vertices(d, fr, AX[z])
            assert (s, z, kind) not in curves
            curves[(s, z, kind)] = (pts, nclip)
for s in COL:
    for z, _ in PANELS:
        if (s, z, "solid") in curves:
            assert (s, z, "dashed") in curves, (s, z)
            xs = [p[0] for p in curves[(s, z, "solid")][0]]
            assert all(a < b for a, b in zip(xs, xs[1:])), (s, z, "x not increasing")


def interp(pts, x):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return float(np.interp(x, xs, ys)) if xs[0] <= x <= xs[-1] else None


# ---------------------------------------------------------------- checks against numbers in the paper and against the drawn HiZELS curve
# (1) the text says the bulk of the H-alpha luminosity comes from H II regions at any redshift (dashed lines) and that an AGN matters only above about 10^43 erg/s: over the range of each curve above its peak the luminosity density
# of the dashed curve must be most of, and not more than, that of the solid curve (the pairing of dashed and solid lines in a panel, and the vertical scale, enter)
ratios = []
for (s, z, k), (pts, _) in curves.items():
    if k != "solid":
        continue
    dpts = curves[(s, z, "dashed")][0]
    peak = max(range(len(pts)), key=lambda i: pts[i][1])
    lo, hi = max(pts[peak][0], dpts[0][0]), min(pts[-1][0], dpts[-1][0])
    grid = np.arange(lo, hi, 0.01)
    if len(grid) < 5:
        continue
    rho = lambda q: float(np.sum(10 ** (grid + np.interp(grid, [p[0] for p in q], [p[1] for p in q]))))
    ratios.append((rho(dpts) / rho(pts), s, z))
check(len(ratios) >= 20 and all(0.5 < r[0] < 1.2 for r in ratios), f"in {len(ratios)} of the 26 panels the H II-region-only (dashed) curve carries {min(r[0] for r in ratios):.2f} to {max(r[0] for r in ratios):.2f} of the luminosity density of the solid curve above its peak (the text: the bulk of the H-alpha luminosity arises from H II regions)")
# (2) the number of galaxies at z = 0.1 that the plotted function implies against the numbers the paper prints (about 8,800, 18,000 and 47,000 galaxies above the cuts at z = 0)
for s in COL:
    pts = curves[(s, 0.1, "solid")][0]
    xs = np.array([p[0] for p in pts])
    ph = 10 ** np.array([p[1] for p in pts])
    n_lf = float(np.sum(0.5 * (ph[1:] + ph[:-1]) * np.diff(xs))) * BOX[s] ** 3
    ratio = n_lf / NPAPER[s]
    check(0.05 < ratio < 1.15, f"{s} z = 0.1: the plotted function integrated over log L = {xs[0]:.2f} to {xs[-1]:.2f} and times ({BOX[s]} cMpc)^3 gives {n_lf:,.0f} galaxies against the printed about {NPAPER[s]:,} above the mass cut at z = 0 (ratio {ratio:.2f}; an upper bound only: the faint part below 10^{xs[0]:.1f} erg/s is not drawn)", scope=lambda s_, z_, s0=s: s_ == s0 and z_ == 0.1, number=True)
# (3) the factor of about 30 between z = 3 and z = 6 at L = 10^42 erg/s that the text states (it does not name the simulation: TNG100 gives about 40 and TNG50 about 14, so the statement lies between them)
f100 = interp(curves[("TNG100", 3.0, "solid")][0], 42.0) - interp(curves[("TNG100", 6.0, "solid")][0], 42.0)
f50 = interp(curves[("TNG50", 3.0, "solid")][0], 42.0) - interp(curves[("TNG50", 6.0, "solid")][0], 42.0)
check(abs(f100 - math.log10(30)) < 0.15 and f50 < math.log10(30) < f100, f"at log L = 42 the density falls between z = 3 and z = 6 by a factor of {10 ** f100:.0f} in TNG100 and {10 ** f50:.0f} in TNG50 (the text: a factor of about 30, simulation not named)", scope=lambda s_, z_: z_ in (3.0, 6.0) and s_ in ("TNG50", "TNG100"), number=True)
# (4) the HiZELS curves drawn in the figure against the Schechter parameters of Sobral et al. 2013 (Table 5), held by the dataset's own records of that paper
sob = {}
for r in json.loads((REF / "data" / "curves" / "elf-sobral13.json").read_text())["records"]:
    m = re.search(r"log L\*=([\d.]+), log phi\*=(-[\d.]+), alpha=(-[\d.]+)", r["notes"])
    sob[r["epoch"]["zRepresentative"]] = tuple(float(g) for g in m.groups())
schechter = lambda L, p: math.log10(math.log(10)) + p[1] + (p[2] + 1) * (L - p[0]) - 10 ** (L - p[0]) * math.log10(math.e)
GREY = (0.71, 0.71, 0.71)
hz = {}
for d in paths(GREY, 2.27, True):
    if "5.6693 5.6693" not in str(d["dashes"]) or len(d["items"]) < 5:
        continue
    r = d["rect"]
    z = [z for z, fr in PANELS if fr.x0 <= (r.x0 + r.x1) / 2 <= fr.x1 and fr.y0 <= (r.y0 + r.y1) / 2 <= fr.y1][0]
    hz[z] = vertices(d, dict(PANELS)[z], AX[z])[0]
check(sorted(hz) == [1.0, 1.5, 2.0], f"light-grey dashed (Sobral et al. 2013/2015) curves drawn in the panels z = {sorted(hz)}")
d15 = [y - schechter(x, sob[1.47]) for x, y in hz[1.5]]
check(len(d15) >= 4 and max(d15) - min(d15) < 0.005, f"z = 1.5 panel: the drawn HiZELS curve has the shape of the Table 5 Schechter function at z = 1.47 (log L* = 42.56, alpha = -1.62): difference constant to {max(d15) - min(d15):.4f} dex over {len(d15)} vertices spanning log L = {hz[1.5][0][0]:.1f} to {hz[1.5][-1][0]:.1f} and {abs(hz[1.5][0][1] - hz[1.5][-1][1]):.1f} dex in phi; the constant offset of {np.mean(d15):+.3f} dex in normalisation is not reconciled (the figure's curves are labelled Sobral+13/15)", scope=lambda s_, z_: z_ == 1.5, number=True)
d1 = [y - schechter(x, sob[0.84]) for x, y in hz[1.0]]
check(abs(d1[0]) < 0.01 and abs(d1[1]) < 0.01, f"z = 1 panel: the two faintest vertices of the drawn HiZELS curve lie within {max(abs(d1[0]), abs(d1[1])):.3f} dex of the Table 5 Schechter function at z = 0.84 (the brighter vertices differ by up to {max(abs(v) for v in d1):.2f} dex: the drawn curve is not exactly that function)", scope=lambda s_, z_: z_ == 1.0, number=True)

# ---------------------------------------------------------------- records
DEF = {"line": "H-alpha (without [NII])", "imf": "chabrier03", "dustCorrection": "intrinsic",
       "dustCorrectionMethod": "no attenuation by dust outside H II regions (the photoionization models of the H II regions include dust inside the nebulae)", "densityFrame": "unspecified",
       "apertureDefinition": "all bound gas cells and star particles of the Subfind galaxy (AGN narrow-line region: within 1 kpc of the black hole)", "cosmology": {"H0": 67.74, "Om": 0.3089}}
SIMNAME = {"TNG50": "TNG50-1", "TNG100": "TNG100-1", "TNG300": "TNG300-1"}
MASSCUT = {"TNG50": "1e8", "TNG100": "3e9", "TNG300": "1e10"}
def note_for(s, z):
    mine = [(m, n) for m, sc, n in checks if sc is None or sc(s, z)]
    nnum = sum(1 for _, n in mine if n)
    txt = ("Vector-path extraction of the solid line of one panel; exact to PDF coordinate precision. Axes calibrated from tick marks (the figure has no text layer; the label values are read from the rendered figure). Checks for this panel: " + "; ".join(m for m, _ in mine) + ".")
    if nnum < 2:
        txt += (f" Only {nnum} number printed in a paper can be compared with this panel; its calibration rests on the common layout of the nine panels (tick spacing identical to 0.00 pt), which was checked against printed numbers in the panels z = 0.1, 1, 1.5, 3 and 6.")
    return txt


records = []
dropped = []
for s in COL:
    for z, _ in PANELS:
        if (s, z, "solid") not in curves:
            continue
        pts, nclip = curves[(s, z, "solid")]
        ymax = max(range(len(pts)), key=lambda i: pts[i][1])
        kept = pts[ymax + 1:] if ymax > 0 else pts  # at or below the peak: not written (resolution limit, per the paper)
        peak = pts[ymax] if ymax > 0 else None
        if len(kept) < 3:
            dropped.append((s, z, len(pts), len(kept)))
            continue
        out = [{"x": round(x, 3), "y": round(y, 4)} for x, y in kept]
        run = f"{SIMNAME[s]}, H-alpha luminosity function of galaxies above M* = {MASSCUT[s]} Msun, no dust outside H II regions (Hirschmann+23)"
        rec = vf.record(
            rid=f"hirschmann23.{s.lower()}.elf.halpha.intrinsic.z{z:g}", source="IllustrisTNG", run=run, relation="elf", z=z,
            axes={"xDefinition": "log10 H-alpha (6563 A) line luminosity of the galaxy: total nebular emission of H II regions, AGN narrow-line regions, post-AGB stars and shocks, without attenuation by dust outside H II regions", "xUnit": "log10(erg s^-1)",
                  "yDefinition": "log10 number density of galaxies per dex of line luminosity (the figure's phi per log10 L_H-alpha)", "yUnit": "log10(Mpc^-3 dex^-1)"},
            points=out, population=f"{SIMNAME[s]} galaxies with stellar mass above {MASSCUT[s]} Msun",
            warning=("Digitized from the vector paths of a figure (not computed from the simulation), so never rankable. Luminosities are model nebular emission computed in post-processing (photoionization models coupled to the simulated gas and stars), not simulation output, "
                     "and carry no dust attenuation outside H II regions, so the curve belongs with dust-corrected observations, not with attenuated ones. The galaxy sample is those above the stellar-mass cut (the paper: nebular emission is computed 'for all these galaxies and their progenitors at z>0'); "
                     "whether the cut is applied again at each redshift is not stated. "
                     + (f"The curve has a peak at log L = {peak[0]:.2f} (the paper: peaks 'arise from the resolution limits; galaxy number densities below the peak are incomplete and hence not meaningful'); points at and below the peak are not written. " if peak else "The curve has no peak; the paper says the TNG50 faint end is shallowed by its stellar-mass cut and by resolution. ")
                     + "The density axis is labelled Mpc^-3 without saying comoving."),
            definitions={**DEF, "population": f"galaxies of all types above M* = {MASSCUT[s]} Msun in the {SIMNAME[s]} box ({BOX[s]} cMpc)"},
            citation=CITE, doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure=FIGURE, panel=f"{s}, z = {z:g}", sha=SHA, member="Ha_lumfct_IllustrisTNG_allz_Nov21.eps",
            calib={"xTicks": [[round(p, 2), v] for p, v in zip(AX[z][0].ms, XV)], "yTicks": [[round(p, 2), v] for p, v in zip(AX[z][1].ms, YV)], "labels": "no text layer; tick values read from the rendered labels (x: 41 to 44 on every second major tick; y: -1 to -5)"},
            calibration="prediction", interval="unspecified", retrieved="2026-10-25", z_range=None,
            note=note_for(s, z))
        rec["provenance"]["quotes"] = dict(Q)
        rec["provenance"]["paper"] = f"arXiv:{ARXIV}"
        rec["provenance"]["definitionBasis"] = ("line: the model computes H-alpha and [NII] as separate lines (the paper lists them separately). dustCorrection: 'we do not consider attenuation by dust outside H II regions'. "
                                                "imf: the H II-region models assume a Chabrier (2003) IMF truncated at 0.1 and 300 Msun (the simulation's own IMF is not read from this paper). densityFrame: not stated for the luminosity functions. "
                                                "The dashed lines (H II regions only) and the observational curves drawn in the figure are not records.")
        records.append(rec)
ids = [r["id"] for r in records]
assert len(set(ids)) == len(ids)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
QUOTES.parent.mkdir(parents=True, exist_ok=True)
QUOTES.write_text("\n".join(log + ["check: " + c[0] for c in checks] + [f"figure: Ha_lumfct_IllustrisTNG_allz_Nov21.eps sha256 {SHA}"]) + "\n")
print(f"Wrote {len(records)} records from Hirschmann et al. 2023; {len(checks)} checks passed; not written (fewer than three points above the peak): {dropped}")
for c in checks:
    print("  -", c[0])
