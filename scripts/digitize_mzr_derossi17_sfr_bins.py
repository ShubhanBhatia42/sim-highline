"""De Rossi et al. 2017 (arXiv:1704.00006, MNRAS 472, 3354): median EAGLE (Recal-L025N0752) M* - O/H|SF,gas relations in three SFR bins, all galaxies below z~5,
lower panel of the FMR figure ('2D projection onto the mass-metallicity plane'). One mzr record per SFR bin, SFR range in `selection`; NOT converted to mu_alpha.
The figure's text is outlined, so the axes are calibrated on the drawn major ticks (labels read on the rendered figure) and validated by the Mannucci+10
surface that the figure draws at the centre of each SFR bin (black lines), which must equal the published polynomial of Mannucci et al. 2010 to <0.001 dex."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1704.00006"
DOI = "10.1093/mnras/stx2208"
FIGURE_EPS = "FMZR_since_z5_Mannucci09_vrot4_AllGal_v4.eps"
TEX = "paper_eagle_derossi_rev2.tex"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "data" / "curves" / "derossi17-eagle-mzr-sfr-bins.json"
tex = SRC / TEX
log = []


def quote(s):
    norm = lambda a: re.sub(r"\s+", " ", a).strip()
    flat, idx = "", []
    for n, l in enumerate(tex.read_text(errors="replace").splitlines(), 1):
        flat += norm(l) + " "
        idx += [n] * (len(norm(l)) + 1)
    k = flat.find(norm(s))
    assert k >= 0, ("quote not found", s)
    log.append(f"{TEX}:{idx[k]}: {norm(s)}")


quote(r"Upper panels: Median simulated $M_* - {\rm O/H}_{\rm SF,gas}$ relations binned according to SFR in the $M_*$ - SFR - O/H space for Recal-L025N0752 simulations.")
quote(r"$\log_{10} ({\rm SFR} / {\rm M}_{\sun} {\rm yr}^{-1})= -0.5-0.0$ (red dash-dotted line with diamonds),")
quote(r"$\log_{10} ({\rm SFR} / {\rm M}_{\sun} {\rm yr}^{-1}) = 0.0-0.5$ (blue dashed line with triangles) and")
quote(r"$\log_{10} ({\rm SFR} / {\rm M}_{\sun} {\rm yr}^{-1}) = 0.5-1.0$ (pink dotted line with crosses).")
quote(r"Bottom panel: 2D projection of the aforementioned relations onto the mass-metallicity plane.")
quote(r"For the simulation, all galaxies identified below $z\approx5$ have been considered for the calculations.")
quote(r"Note that in Fig. \ref{fig:MZR_bin} only $z=0$ galaxies were taken into account.")
quote(r"Thus, we calculated global oxygen abundances (${\rm O/H}|_{\rm SF,gas}$) considering gas particles with ${\dot m}_* > 0$ (see Eq. \ref{eq:sfr}) at radius $r \le 30$ kpc in a given subhalo.")
quote(r"report global properties of galaxies inside a sphere with radius 30 proper kpc (pkpc).")
quote(r"Only mass bins with $N_{\rm bin} > 10$ were considered for this analysis:")
quote(r"$N_{\rm bin} = 13-296, \ 25-142$ and $23-82$ at $\log_{10} ({\rm SFR} / {\rm M}_{\sun}yr^{-1}) \approx -0.25, \ 0.25$ and 0.75, respectively.")
quote(r"to the \citet{chabrier2003} IMF.")
quote(r"The residuals of this simulation are below $\approx 0.1$ dex for smaller galaxies ($M_* \la 10^{10.2} {\rm M}_{\sun}$) and below $\approx 0.2$ dex for more massive ones.")
quote(r"The shaded area represents the best-fit 2D surface taken from \citet{mannucci2010}.")
quote(r"Black lines trace the shaded surface at the center of each SFR bin.")

fig = SRC / FIGURE_EPS
with tempfile.TemporaryDirectory() as d:
    pdf = Path(d) / "f.pdf"
    subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite", "-dEPSCrop", f"-sOutputFile={pdf}", str(fig)], check=True, capture_output=True)
    page = pymupdf.open(pdf)[0]
    drawings = page.get_drawings()
# frame and tick marks (the glyphs are strokes, there are no text words)
frame = pymupdf.Rect(110.1, 24.0, 535.5, 466.2)
black = [it for d in drawings if d["color"] == (0.0, 0.0, 0.0) for it in d["items"] if it[0] == "l"]
assert sum(1 for it in black if abs(it[1].y - it[2].y) < 0.01 and abs(it[1].x - it[2].x) > 400) == 2 and sum(1 for it in black if abs(it[1].x - it[2].x) < 0.01 and abs(it[1].y - it[2].y) > 400) >= 2
xmaj = sorted({round(it[1].x, 2) for it in black if abs(it[1].x - it[2].x) < 0.01 and abs(max(it[1].y, it[2].y) - frame.y1) < 0.05 and 8 < abs(it[1].y - it[2].y) < 9.5})
ymaj = sorted({round(it[1].y, 2) for it in black if abs(it[1].y - it[2].y) < 0.01 and abs(min(it[1].x, it[2].x) - frame.x0) < 0.05 and 8 < abs(it[1].x - it[2].x) < 9.5 and frame.y0 < it[1].y < frame.y1})
assert len(xmaj) == 4 and len(ymaj) == 4, (xmaj, ymaj)
assert max(b - a for a, b in zip(xmaj, xmaj[1:])) - min(b - a for a, b in zip(xmaj, xmaj[1:])) < 0.1 and max(b - a for a, b in zip(ymaj, ymaj[1:])) - min(b - a for a, b in zip(ymaj, ymaj[1:])) < 0.1
# major ticks carry the labels 9.0, 9.5, 10.0, 10.5 (x) and 9.5, 9.0, 8.5, 8.0 (y, top to bottom), read on the rendered figure
PX = (xmaj[-1] - xmaj[0]) / 1.5
PY = (ymaj[-1] - ymaj[0]) / 1.5
fx = lambda px: 9.0 + (px - xmaj[0]) / PX
fy = lambda py: 9.5 - (py - ymaj[0]) / PY


def mannucci(logm, s):  # Mannucci et al. 2010 eq. (fit): 12+log(O/H) = 8.90+0.37m-0.14s-0.19m^2+0.12ms-0.054s^2, m = log M* - 10, s = log SFR
    m = logm - 10
    return 8.90 + 0.37 * m - 0.14 * s - 0.19 * m * m + 0.12 * m * s - 0.054 * s * s


# validation: the three black broken lines are the Mannucci surface at log SFR = -0.25, 0.25, 0.75
valid = {}
for d in drawings:
    if d["color"] == (0.0, 0.0, 0.0) and len(d["items"]) >= 90 and d["dashes"].replace(" ", "") != "[]0":
        pts = [d["items"][0][1]] + [it[-1] for it in d["items"]]
        P = np.array([(fx(p.x), fy(p.y)) for p in pts])
        dash = d["dashes"].replace(" ", "")
        s = {"[5.66932.834651.417332.83465]0": -0.25, "[5.66935.6693]0": 0.25, "[1.133862.83465]0": 0.75}[dash]
        diff = np.array([mannucci(x, s) - y for x, y in P])
        assert abs(diff).max() < 0.001, (s, abs(diff).max())
        valid[s] = float(abs(diff).max())
assert len(valid) == 3, valid


def curve(color, dash_prefix):
    """Vertices of a broken line: the end points of its single-segment strokes (each segment restarts the dash pattern)."""
    segs = [d["items"][0] for d in drawings if d["color"] and tuple(round(v, 2) for v in d["color"]) == color and (d["width"] or 0) > 2 and len(d["items"]) == 1 and d["items"][0][0] == "l" and d["dashes"].replace(" ", "").startswith("[" + dash_prefix)]
    assert len(segs) >= 8, len(segs)
    pts = [(segs[0][1].x, segs[0][1].y)] + [(s[2].x, s[2].y) for s in segs]
    for s, a, b in zip(segs, pts, pts[1:]):  # consecutive segments share vertices
        assert abs(s[1].x - a[0]) < 0.06 and abs(s[2].x - b[0]) < 0.06
    return [(fx(x), fy(y)) for x, y in pts]


def marker_centres(color, kind):
    out = []
    for d in drawings:
        if not d["color"] or tuple(round(v, 2) for v in d["color"]) != color or (d["width"] or 0) < 2:
            continue
        r = d["rect"]
        if kind == "tri" and len(d["items"]) == 3:
            out.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
        if kind == "cross" and len(d["items"]) == 4:
            xs = [it[1].x for it in d["items"]] + [it[2].x for it in d["items"]]
            ys = [it[1].y for it in d["items"]] + [it[2].y for it in d["items"]]
            out.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    return [(fx(x), fy(y)) for x, y in out]


BINS = [
    ("sfr-0.5-0.0", (1.0, 0.0, 0.25), "5.66932.83465", None, "-0.5 to 0.0", "diamonds, dash-dotted"),
    ("sfr0.0-0.5", (0.0, 0.0, 1.0), "5.66935.6693", "tri", "0.0 to 0.5", "triangles, dashed"),
    ("sfr0.5-1.0", (1.0, 0.0, 0.71), "1.133862.83465", "cross", "0.5 to 1.0", "crosses, dotted"),
]
records, notes = [], []
sha = vf.sha256(fig)
for tag, col, dash, mk, rng, style in BINS:
    pts = curve(col, dash)
    if mk:  # drawn markers sit on the vertices (checked for the two marker types that are stroked polylines)
        mc = marker_centres(col, mk)
        assert len(mc) == len(pts), (tag, len(mc), len(pts))
        for (x, y), (mx, my) in zip(sorted(pts), sorted(mc)):
            assert abs(x - mx) < 0.01 and abs(y - my) < 0.01, (tag, x, y, mx, my)
    pts = sorted(pts)
    assert all(a[0] < b[0] for a, b in zip(pts, pts[1:]))
    centre = float(rng.split(" to ")[0]) + 0.25
    near = np.mean([mannucci(x, centre) - y for x, y in pts if 9.0 <= x <= 10.3])
    lo_res = max(abs(mannucci(x, centre) - y) for x, y in pts if x <= 10.2)
    hi_res = max(abs(mannucci(x, centre) - y) for x, y in pts if x > 10.2)
    assert lo_res <= 0.10 and hi_res <= 0.25, (tag, lo_res, hi_res)  # paper text: residuals w.r.t. the observed FMR below ~0.1 dex (M* <~ 10^10.2) and below ~0.2 dex above
    notes.append(f"{tag}: max |Mannucci surface at the bin centre - EAGLE| = {lo_res:.3f} dex for log M* <= 10.2 (paper: below ~0.1) and {hi_res:.3f} above (paper: below ~0.2);")
    notes.append(f"{tag}: {len(pts)} median points, log M* {pts[0][0]:.2f}-{pts[-1][0]:.2f}, Z {min(p[1] for p in pts):.2f}-{max(p[1] for p in pts):.2f}; mean(Mannucci surface at the bin centre - EAGLE) over 9.0-10.3 = {near:+.3f} dex")
    rec = vf.record(
        rid=f"derossi17.eagle-recal-l025n0752.mzr.{tag}.zlt5", source="EAGLE", run="Recal-L025N0752 (De Rossi+17, SFR bin %s)" % rng, relation="mzr", z=2.5, z_range=(0.0, 5.0),
        axes={"xDefinition": "log10 stellar mass within 30 pkpc", "xUnit": "log10(Msun)",
              "yDefinition": "12+log10(O/H) of star-forming gas (mdot_* > 0) within 30 pkpc, median in stellar-mass bins, galaxies in the SFR bin", "yUnit": "dex"},
        points=pts, population="all galaxies at z<~5 pooled, SFR bin log10(SFR/(Msun/yr)) = %s" % rng, interval="unspecified",
        definitions={"imf": "chabrier03", "massDefinition": "aperture-30pkpc", "metallicityQuantity": "gas-O/H",
                     "metallicityCalibration": "intrinsic-simulation (star-forming gas, 30 pkpc)", "population": "all", "sfrTimescaleMyr": "unspecified",
                     "sfrBin": f"log10 SFR/(Msun/yr) = {rng}"},
        citation="De Rossi et al. 2017, MNRAS 472, 3354 (arXiv:1704.00006), Fig. 'FMR' bottom panel (2D projection onto the mass-metallicity plane), EAGLE Recal-L025N0752",
        doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="FMR figure, bottom panel: median M* - O/H|SF,gas in SFR bins for Recal-L025N0752, all galaxies below z~5",
        panel=f"{style}", sha=sha, member=FIGURE_EPS, calibration="prediction",
        calib="axes calibrated on the drawn major ticks (labels read on the rendered figure; the text is outlined) and validated by the Mannucci+10 surface drawn in the same panel (black lines, max |diff| < 0.001 dex)",
        warning=("MZR in a bin of SFR, not a mu_alpha relation (not converted). The paper pools all galaxies below z~5 (zRepresentative 2.5 is the midpoint, not a median; epoch range 0-5). "
                 "SFR bins as printed: log10(SFR/(Msun/yr)) = " + rng + "; the bin edge convention is not stated. SFR and stellar mass are global properties inside 30 pkpc; the SFR timescale is not stated. "
                 "Only mass bins with more than 10 galaxies are drawn (13-296, 25-142 and 23-82 galaxies per bin at log SFR ~ -0.25, 0.25, 0.75)."),
        note="Marker centres/segment end points of the vector figure; connect=true joins the drawn polyline.",
        scatter=None, connect=True, retrieved="2026-10-18")
    rec["scatter"] = None
    rec["epoch"]["mode"] = "published-epoch"
    records.append(rec)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
Path(str(OUT.with_suffix("")) + ".quotes.txt").write_text("\n".join(log + notes + [f"axis validation (Mannucci surface at log SFR -0.25/0.25/0.75, max |diff| dex): {valid}"]) + "\n")
print("\n".join(notes))
print("Wrote", len(records), "records to", OUT)
