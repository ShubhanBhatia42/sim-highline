"""Fang et al. 2013 (arXiv:1308.5224): inner (1 kpc) stellar surface density Sigma_1 and 1-kpc-aperture velocity dispersion sigma_1 versus stellar mass for
green-valley and red-sequence SDSS central galaxies. Records are the published closed-form fits (Eq. sd1_mass_eqn and the sigma_1 fit in Sec. 'The Relation Between Velocity Dispersion and Stellar Mass'),
verified against the fit lines drawn in f4.pdf (Sigma_1) and f11.pdf (sigma_1), both vector figures.
Usage: python3 digitize_sigma1_fang13.py [extracted-arXiv-source-dir]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import curve_record_helpers as K
vf = K.vf

OUT_NAME = "sigma1_fang13"
ARXIV = "1308.5224"
DOI = "10.1088/0004-637X/776/1/63"
ARCHIVE_SHA = "e41adaecc34114a227801cbe2cd9dde2f6636ea11a3012a0fac4cab893c3ee9f"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
FITS = {  # figure, (intercept at logM=10.25, slope), scatter quoted in the paper
    "sigma1": ("f4.pdf", (9.29, 0.64), 0.16),
    "sigmam": ("f11.pdf", (2.09, 0.29), 0.09),
}


def check(fig, a, b):
    """Calibrate on the major ticks (length 10.8 pt) + their numeric labels and compare the drawn fit line with a + b (x - 10.25)."""
    pdf = SRC / fig
    p = vf.page_of(pdf)
    fr = vf.frame_from_long_lines(p, 100)
    maj = sorted({round(it[1].y, 2) for d in p.get_drawings() if d["type"] == "s" and d["color"] and max(d["color"]) < 0.2 for it in d["items"]
                  if it[0] == "l" and abs(it[1].y - it[2].y) < 0.02 and abs(abs(it[1].x - it[2].x) - 10.8) < 0.2 and abs(min(it[1].x, it[2].x) - fr.x0) < 0.6})
    labs = sorted([((w[1] + w[3]) / 2, float(w[4])) for w in p.get_text("words") if vf.number(w[4]) is not None and w[0] < fr.x0 - 1 and fr.y0 - 5 < (w[1] + w[3]) / 2 < fr.y1 + 5])
    assert len(maj) == len(labs) >= 5 and all(abs(m - l[0]) < 5 for m, l in zip(maj, labs))
    A = np.polyfit(maj, [v for _, v in labs], 1)
    assert np.abs(np.polyval(A, maj) - [v for _, v in labs]).max() < 1e-3
    fx, xt = vf.axis_fit(p, fr, "x")
    assert len(xt) >= 5
    fy = lambda y: A[0] * y + A[1]
    lines = [d for d in p.get_drawings() if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and abs(d["width"] - 1.33) < 0.02 and len(d["items"]) == 3]
    assert len(lines) == 1
    its = lines[0]["items"]
    pts = [(fx(its[0][1].x), fy(its[0][1].y))] + [(fx(i[2].x), fy(i[2].y)) for i in its]
    worst = max(abs(y - (a + b * (x - 10.25))) for x, y in pts)
    print(fig, "line vertices", [(round(x, 3), round(y, 3)) for x, y in pts], "max |dy| vs closed form %.4f" % worst)
    assert worst < 0.01
    return pdf, worst


CIT = f"Fang et al. 2013, ApJ 776, 63 (arXiv:{ARXIV})"
URL = f"https://arxiv.org/abs/{ARXIV}"
POPW = ("SDSS DR7 central galaxies (most massive group member, Yang+12), 0.005<z<0.075, b/a>0.6, green-valley and red-sequence (NUV-r>4) galaxies only, 9.75<log M*<11.25, "
        "volume-limited per 0.25 dex mass bin; blue-cloud galaxies lie below the ridge and are excluded from the fit. Not a relation for all galaxies.")
MASSDEF = "sed-total"  # total stellar masses from the MPA/JHU DR7 catalogue (fits to the integrated SDSS photometry)
recs = []
pdf1, w1 = check(*FITS["sigma1"][:1], *FITS["sigma1"][1])
a, b = FITS["sigma1"][1]
recs.append(K.build(
    rid="fang13.sdss.sigma1.green-red.fit", source="Fang et al. 2013 (SDSS)", run="central green+red galaxies, z<0.075, least-squares fit", kind="observation", relation="sigma1",
    z=0.04, zmin=0.005, zmax=0.075, mode="observational-bin",
    axes={"xDefinition": "log10 total stellar mass (MPA/JHU DR7)", "xUnit": "log10(Msun)", "yDefinition": "log10 average stellar surface mass density within a circular aperture of radius 1 kpc, Sigma_1", "yUnit": "log10(Msun/kpc^2)"},
    representation={"type": "parametric", "equation": "log Sigma_1 = 9.29 + 0.64 (log M* - 10.25)", "expression": "a+b*(x-10.25)", "parameters": {"a": a, "b": b}},
    domain={"xMin": 9.75, "xMax": 11.25}, population="central, green valley + red sequence",
    warning=POPW + " zRepresentative is the midpoint of 0.005<z<0.075 (not a median). The drawn line in Fig. 4 spans log M* 9-11.5; the fit uses the 9.75-11.25 sample. IMF and cosmology are not stated in the paper. "
            "Sigma_1 is from SDSS i-band surface-brightness profiles converted with a g-i colour M/L calibrated on the MPA/JHU masses, so it inherits SDSS seeing (HWHM 0.7 arcsec ~ 1 kpc at z=0.075).",
    definitions={"imf": "unspecified", "cosmology": "unspecified", "massDefinition": MASSDEF, "population": "central green-valley and red-sequence",
                 "sigma1Definition": "average surface mass density within a circular aperture of radius 1 kpc, computed by directly integrating the mass profiles from the innermost point out to R=1 kpc"},
    tier="published-fit", citation=CIT + ", fit to Fig. 4 (Sigma_1 vs M*)", doi=DOI, url=URL, calibration="validation", rankable=True,
    notes="Fit 9.29(+0.10,-0.10) + 0.64(+0.23,-0.20)(log M* - 10.25), 1 sigma scatter 0.16 dex (bootstrap 16-84%%). Drawn line in f4.pdf reproduces the closed form to %.3f dex at all vertices." % w1,
    scatter={"value": 0.16, "unit": "dex", "meaning": "1 sigma scatter of green and red galaxies about the relation"},
    provenance_extra={"sourceArchiveSha256": ARCHIVE_SHA, "sourceMember": "ms_v2.tex lines 193-197 (Eq. sd1_mass_eqn)", "figureCheck": "f4.pdf checksum " + vf.sha256(pdf1)}))
pdf2, w2 = check(*FITS["sigmam"][:1], *FITS["sigmam"][1])
a, b = FITS["sigmam"][1]
recs.append(K.build(
    rid="fang13.sdss.sigmam.sigma1kpc.green-red.fit", source="Fang et al. 2013 (SDSS)", run="central green+red galaxies, sigma scaled to 1 kpc, z<0.075, least-squares fit", kind="observation", relation="sigmam",
    z=0.04, zmin=0.005, zmax=0.075, mode="observational-bin",
    axes={"xDefinition": "log10 total stellar mass (MPA/JHU DR7)", "xUnit": "log10(Msun)", "yDefinition": "log10 SDSS fibre velocity dispersion scaled to a circular aperture of radius 1 kpc, sigma_1", "yUnit": "log10(km/s)"},
    representation={"type": "parametric", "equation": "log sigma_1 = 2.09 + 0.29 (log M* - 10.25)", "expression": "a+b*(x-10.25)", "parameters": {"a": a, "b": b}},
    domain={"xMin": 9.75, "xMax": 11.25}, population="central, green valley + red sequence",
    warning=POPW + " The aperture is 1 kpc (not R_e and not the 3 kpc of Zahid+16): fibre dispersions were scaled with sigma ~ R^-0.66 (Cappellari+06). zRepresentative is the midpoint of the redshift range. IMF and cosmology not stated.",
    definitions={"imf": "unspecified", "cosmology": "unspecified", "massDefinition": MASSDEF, "population": "central green-valley and red-sequence",
                 "sigmaDefinition": "SDSS fibre (3 arcsec) stellar velocity dispersion scaled to a circular aperture of radius 1 kpc with sigma ~ R^-0.66 (Cappellari+06); 1D line of sight",
                 "sigmaDimension": "1D line of sight, scaled to 1 kpc aperture", "sigmaWeighting": "unspecified"},
    tier="published-fit", citation=CIT + ", fit to Fig. 11 (sigma_1 vs M*)", doi=DOI, url=URL, calibration="validation", rankable=True,
    notes="Fit 2.09(+0.05,-0.08) + 0.29(+0.13,-0.10)(log M* - 10.25); 1 sigma scatter 0.09 dex. Drawn line in f11.pdf reproduces the closed form to %.3f dex at all vertices." % w2,
    scatter={"value": 0.09, "unit": "dex", "meaning": "1 sigma vertical scatter of green and red galaxies about the relation"},
    provenance_extra={"sourceArchiveSha256": ARCHIVE_SHA, "sourceMember": "ms_v2.tex lines 339-344", "figureCheck": "f11.pdf checksum " + vf.sha256(pdf2)}))
out = K.write_part(OUT_NAME, recs)
print("wrote", out, len(recs))
