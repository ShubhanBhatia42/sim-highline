"""Zahid et al. 2016 (arXiv:1607.04275): stellar mass - central stellar velocity dispersion relation of quiescent galaxies (SDSS and SHELS).
Writes parametric published-fit records (Table 'Fit Parameters') and vector-digitized binned medians (Fig. 5 = fig5.eps).
Usage: python3 digitize_sigmam_zahid16.py [extracted-arXiv-source-dir]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import curve_record_helpers as K
vf = K.vf

OUT_NAME = "sigmam_zahid16"          # -> data/curves/<OUT_NAME>.json
ARXIV = "1607.04275"
DOI = "10.3847/0004-637x/832/2/203"
ARCHIVE_SHA = "aa9308b57ad3d6187ce7cf5eb9422561c94b9dd8c52d2eede77b293f29cab81e"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
eps, pdf = K.eps_to_pdf(SRC, "fig5.eps")
page = vf.page_of(pdf)
fr = vf.frame_from_long_lines(page, 100)

# Axis calibration. The IDL EPS carries the tick labels as outlines (no text layer), so the labels cannot be read by axis_fit.
# Ticks: 31 equally spaced x ticks from the left to the right frame edge (10 minor intervals per unit) and 21 y ticks (0.05 dex apart).
# Labels read from the rendered figure: x runs 9 ... 12 (frame edges), y runs 1.6 (bottom) ... 2.6 (top). Validated below against the paper's own fit table.
tx = vf._tick_positions(page, fr, "x")
ty = vf._tick_positions(page, fr, "y")
assert len(tx) == 31 and len(ty) == 21 and abs(tx[0] - fr.x0) < 0.1 and abs(tx[-1] - fr.x1) < 0.1 and abs(ty[0] - fr.y0) < 0.1 and abs(ty[-1] - fr.y1) < 0.1
assert np.allclose(np.diff(tx), np.diff(tx).mean(), atol=0.1) and np.allclose(np.diff(ty), np.diff(ty).mean(), atol=0.1)
fx = lambda x: 9.0 + 3.0 * (x - tx[0]) / (tx[-1] - tx[0])
fy = lambda y: 2.6 - 1.0 * (y - ty[0]) / (ty[-1] - ty[0])

# Table 'Fit Parameters' of the paper (revised.tex lines 478-479): log Mb, log sigma_b, alpha1, alpha2
SDSS = dict(logMb=10.26, logSigb=2.073, alpha1=0.403, alpha2=0.293)
SHELS = dict(logMb=10.26, logSigb=2.071, alpha2=0.281)
sdss_fit = lambda x: SDSS["logSigb"] + np.where(x <= SDSS["logMb"], SDSS["alpha1"], SDSS["alpha2"]) * (x - SDSS["logMb"])
shels_fit = lambda x: SHELS["logSigb"] + SHELS["alpha2"] * (x - SHELS["logMb"])

dr = page.get_drawings()
black_lines = [d for d in dr if d["type"] == "s" and d["color"] == (0.0, 0.0, 0.0) and len(d["items"]) > 100]
red_lines = [d for d in dr if d["type"] == "s" and d["color"] == (1.0, 0.0, 0.0) and len(d["items"]) == 24]
assert len(black_lines) == 1 and len(red_lines) == 1
def verts(d):
    its = d["items"]
    return [(fx(p.x), fy(p.y)) for p in [its[0][1]] + [i[2] for i in its]]
vb, vr = np.array(verts(black_lines[0])), np.array(verts(red_lines[0]))
# (1) calibration check: the plotted best-fit lines must coincide with the paper's tabulated fits (two independent constraints per axis)
rb = vb[:, 1] - sdss_fit(vb[:, 0])
rr = vr[:, 1] - shels_fit(vr[:, 0])
assert np.abs(rb).max() < 0.004 and np.abs(rr).max() < 0.004, (np.abs(rb).max(), np.abs(rr).max())
print("fit-line vs tabulated fit: max |dlogsigma| SDSS %.4f SHELS %.4f" % (np.abs(rb).max(), np.abs(rr).max()))

circ = [(d["fill"], (d["rect"].x0 + d["rect"].x1) / 2, (d["rect"].y0 + d["rect"].y1) / 2) for d in dr if d["fill"] is not None and len(d["items"]) == 48]
sd = sorted((fx(x), fy(y)) for f, x, y in circ if f == (0.0, 0.0, 0.0) and fr.x0 <= x <= fr.x1 and fr.y0 <= y <= fr.y1)
sh = sorted((fx(x), fy(y)) for f, x, y in circ if f == (1.0, 0.0, 0.0) and fr.x0 <= x <= fr.x1 and fr.y0 <= y <= fr.y1)
assert len(sd) == 200 and len(sh) == 25, (len(sd), len(sh))
sd_a, sh_a = np.array(sd), np.array(sh)
assert np.all(np.diff(sd_a[:, 0]) > 0) and np.all(np.diff(sh_a[:, 0]) > 0)
# (2) the medians vs the table: slope of the SDSS medians above the break and sigma at the break
hi = sd_a[sd_a[:, 0] > SDSS["logMb"]]
slope_hi = np.polyfit(hi[:, 0], hi[:, 1], 1)[0]
lo = sd_a[sd_a[:, 0] < SDSS["logMb"]]
slope_lo = np.polyfit(lo[:, 0], lo[:, 1], 1)[0]
near = sd_a[np.argmin(np.abs(sd_a[:, 0] - SDSS["logMb"]))]
print("digitized SDSS medians: slope above break %.3f (table alpha2 0.293), below %.3f (alpha1 0.403); log sigma at x=%.3f: %.3f (table 2.073)" % (slope_hi, slope_lo, near[0], near[1]))
assert abs(slope_hi - SDSS["alpha2"]) < 0.02 and abs(slope_lo - SDSS["alpha1"]) < 0.03 and abs(near[1] - SDSS["logSigb"]) < 0.01
shs = np.polyfit(sh_a[:, 0], sh_a[:, 1], 1)
print("digitized SHELS medians slope %.3f (table 0.281)" % shs[0])
assert abs(shs[0] - SHELS["alpha2"]) < 0.03
# (3) quoted numbers: sigma(10^11) of the separate fit to SDSS M*>Mb is log 2.2969 (table); the broken power law gives %.4f
print("full-sample fit at logM=11: %.4f vs separate M*>Mb fit 2.2969" % sdss_fit(np.array(11.0)))
assert abs(float(sdss_fit(np.array(11.0))) - 2.2969) < 0.01

AX = {"xDefinition": "log10 stellar mass (SED fit, Chabrier IMF)", "xUnit": "log10(Msun)",
      "yDefinition": "log10 central line-of-sight stellar velocity dispersion (fibre, corrected to a 3 kpc aperture)", "yUnit": "log10(km/s)"}
SIGDEF = ("central LOS stellar velocity dispersion measured from stellar absorption lines through circular fibre apertures centred on each galaxy, "
          "corrected with sigma_SDSS/sigma_HECTO = (R_SDSS/R_HECTO)^beta, beta=-0.033, to a fiducial physical aperture of 3 kpc (revised.tex lines 84, 110, 120)")
DEFS = {"sigmaDefinition": SIGDEF, "massDefinition": "sed-total", "imf": "chabrier03", "cosmology": "unspecified", "population": "quiescent (Dn4000>1.5)",
        "sigmaDimension": "1D line of sight, central fibre aperture", "sigmaWeighting": "unspecified (spectrum-weighted, i.e. light; not stated in the paper)"}
CIT = f"Zahid et al. 2016, ApJ 832, 203 (arXiv:{ARXIV})"
URL = f"https://arxiv.org/abs/{ARXIV}"
METHOD = "vector path vertices/marker centres from fig5.eps (converted with epstopdf; PyMuPDF get_drawings), transformed through axes calibrated on tick marks"
CAL = ("x: 31 equally spaced ticks, frame edges = 9 and 12; y: 21 ticks, bottom/top frame edges = 1.6 and 2.6 (labels read from the rendered figure: IDL outlines, no text layer); "
       "verified: the plotted best-fit lines reproduce the table fits to < 0.004 dex at every vertex")
PROV = K.digitize_provenance(pdf, "fig5.eps (converted to PDF)", METHOD, CAL, 0.003, "Fig. 5: median velocity dispersion in bins of stellar mass, SDSS (black) and SHELS (red)", "single panel", ARCHIVE_SHA)
WARN_COMMON = ("Quiescent galaxies only (SDSS: M*>1e9 Msun, 0.02<z<0.2, Dn4000>1.5; SHELS: R<20.6, M*>10^9.5 Msun, Dn4000>1.5). The relation is for the median log sigma in equally populated stellar-mass bins, "
               "so it is not a relation for star-forming/disc galaxies, whose stellar kinematics are partly ordered rotation. Stellar masses are 0.13 dex below the Portsmouth Kroupa passive masses (paper footnote).")

recs = []
recs.append(K.build(
    rid="zahid16.sdss.sigmam.fit", source="Zahid et al. 2016 (SDSS)", run="SDSS DR12 quiescent, broken power-law fit", kind="observation", relation="sigmam",
    z=0.11, zmin=0.02, zmax=0.2, mode="observational-bin", axes=AX,
    representation={"type": "parametric", "equation": "log sigma = log sigma_b + alpha*(log M - log Mb), alpha = alpha1 (M<=Mb), alpha2 (M>Mb)",
                    "expression": "logSigb+(x<=logMb?alpha1:alpha2)*(x-logMb)", "parameters": dict(SDSS)},
    domain={"xMin": round(float(vb[0, 0]), 3), "xMax": round(float(vb[-1, 0]), 3)}, population="quiescent (Dn4000>1.5), median log sigma in equally populated mass bins",
    warning="Domain = extent of the best-fit line plotted in Fig. 5 (log M* 9.36-11.66); the paper fits all bins. " + WARN_COMMON + " zRepresentative is the midpoint of the 0.02<z<0.2 selection, not a median.",
    definitions=dict(DEFS), tier="published-fit", citation=CIT + ", Table 'Fit Parameters' row SDSS (N=371884)", doi=DOI, url=URL, calibration="validation", rankable=True,
    notes="log Mb=10.26+-0.01, log sigma_b=2.073+-0.003, alpha1=0.403+-0.004, alpha2=0.293+-0.001. The expression reproduces the plotted line of Fig. 5 to <0.004 dex.",
    provenance_extra={"sourceArchiveSha256": ARCHIVE_SHA, "sourceMember": "revised.tex lines 478-479 (Table Fit Parameters, rows SDSS and SHELS)"}))
recs.append(K.build(
    rid="zahid16.sdss.sigmam.medians", source="Zahid et al. 2016 (SDSS)", run="SDSS DR12 quiescent, binned medians", kind="observation", relation="sigmam",
    z=0.11, zmin=0.02, zmax=0.2, mode="observational-bin", axes=AX, representation=K.points_rep(K.points_from(sd)),
    domain={"xMin": round(sd[0][0], 3), "xMax": round(sd[-1][0], 3)}, population="quiescent (Dn4000>1.5), median log sigma in 200 equally populated mass bins",
    warning="200 binned medians (marker centres, error bars not extracted). " + WARN_COMMON, definitions=dict(DEFS), tier="digitized-figure", citation=CIT + ", Fig. 5", doi=DOI, url=URL,
    calibration="validation", rankable=False, notes="Marker centres of the black filled circles of Fig. 5; the paper states the medians are taken in equally populated stellar mass bins with bootstrapped errors (revised.tex:189).",
    provenance_extra=PROV))
recs.append(K.build(
    rid="zahid16.shels.sigmam.fit", source="Zahid et al. 2016 (SHELS)", run="SHELS F2 quiescent z<0.7, single power-law fit (Mb fixed)", kind="observation", relation="sigmam",
    z=0.3, zmin=0.0, zmax=0.7, mode="observational-bin", axes=AX,
    representation={"type": "parametric", "equation": "log sigma = log sigma_b + alpha2*(log M - log Mb), Mb fixed", "expression": "logSigb+alpha2*(x-logMb)", "parameters": dict(SHELS)},
    domain={"xMin": round(float(vr[0, 0]), 3), "xMax": round(float(vr[-1, 0]), 3)}, population="quiescent (Dn4000>1.5), median log sigma in equally populated mass bins",
    warning="Domain = extent of the red best-fit line in Fig. 5 (log M* 9.86-11.59). Sample covers 0<z<0.7 with no redshift evolution found (zRepresentative 0.3 = median redshift quoted for SHELS in the paper). " + WARN_COMMON,
    definitions=dict(DEFS, sigmaDefinition=SIGDEF.replace("circular fibre apertures", "circular fibre apertures (SHELS: 1.5 arcsec Hectospec fibre)")),
    tier="published-fit", citation=CIT + ", Table 'Fit Parameters' row SHELS (N=4585)", doi=DOI, url=URL, calibration="validation", rankable=True,
    notes="log sigma_b=2.071+-0.004 at fixed log Mb=10.26, alpha2=0.281+-0.005. Expression reproduces the plotted red line of Fig. 5 to <0.004 dex.",
    provenance_extra={"sourceArchiveSha256": ARCHIVE_SHA, "sourceMember": "revised.tex lines 478-479 (Table Fit Parameters, rows SDSS and SHELS)"}))
recs.append(K.build(
    rid="zahid16.shels.sigmam.medians", source="Zahid et al. 2016 (SHELS)", run="SHELS F2 quiescent z<0.7, binned medians", kind="observation", relation="sigmam",
    z=0.3, zmin=0.0, zmax=0.7, mode="observational-bin", axes=AX, representation=K.points_rep(K.points_from(sh)),
    domain={"xMin": round(sh[0][0], 3), "xMax": round(sh[-1][0], 3)}, population="quiescent (Dn4000>1.5), 25 bins of median log sigma",
    warning="25 binned medians (marker centres, bootstrap error bars not extracted). " + WARN_COMMON, definitions=dict(DEFS), tier="digitized-figure", citation=CIT + ", Fig. 5", doi=DOI, url=URL,
    calibration="validation", rankable=False, notes="Marker centres of the red filled circles of Fig. 5.", provenance_extra=PROV))
out = K.write_part(OUT_NAME, recs)
print("wrote", out, len(recs))
