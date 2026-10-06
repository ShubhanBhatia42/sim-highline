import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2306.04024"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
D3A, PLANCK = {"H0": 68.1, "Om": 0.306}, {"H0": 67.3, "Om": 0.316}
VARS = [
    ("fgas+2s", (0.67, 0.82, 0.9), "fgas+2sigma", "cluster gas fractions shifted by +2 sigma before calibration, thermal AGN", D3A),
    ("fgas-2s", (0.42, 0.68, 0.84), "fgas-2sigma", "cluster gas fractions shifted by -2 sigma before calibration, thermal AGN", D3A),
    ("fgas-4s", (0.22, 0.53, 0.75), "fgas-4sigma", "cluster gas fractions shifted by -4 sigma before calibration, thermal AGN", D3A),
    ("fgas-8s", (0.06, 0.36, 0.64), "fgas-8sigma", "cluster gas fractions shifted by -8 sigma before calibration, thermal AGN", D3A),
    ("mstar-s", (1.0, 0.55, 0.25), "M*-sigma", "observed stellar masses decreased by the 0.14 dex systematic error before calibration, thermal AGN", D3A),
    ("mstar-s-fgas-4s", (0.8, 0.26, 0.08), "M*-sigma_fgas-4sigma", "stellar masses shifted by -1 sigma (0.14 dex) and cluster gas fractions by -4 sigma, thermal AGN", D3A),
    ("jet", (0.49, 1.0, 0.29), "Jet", "kinetic jet-like AGN feedback instead of thermal", D3A),
    ("jet-fgas-4s", (0.33, 0.88, 0.56), "Jet_fgas-4sigma", "kinetic jet AGN feedback with cluster gas fractions shifted by -4 sigma", D3A),
    ("planck", (0.27, 0.67, 0.6), "Planck", "Planck cosmology (h=0.673, Om=0.316, sigma8=0.812), fiducial galaxy formation model", PLANCK),
    ("planck-nu0p24fix", (0.6, 0.6, 0.2), "PlanckNu0p24Fix", "Planck cosmology with sum m_nu = 0.24 eV, other parameters fixed (sigma8=0.769)", PLANCK),
    ("planck-nu0p24var", (0.67, 0.27, 0.6), "PlanckNu0p24Var", "Planck-based cosmology with sum m_nu = 0.24 eV and h=0.662, Om=0.328 (sigma8=0.772)", {"H0": 66.2, "Om": 0.328}),
    ("ls8", (0.53, 0.13, 0.33), "LS8", "low-S8 cosmology (h=0.682, Om=0.305, sigma8=0.760)", {"H0": 68.2, "Om": 0.305}),
]
CFG = {
    "gsmf": dict(pdf="SMF_2_Panel.pdf", rel="gsmf", z=0.0, lx=0, fidx=(0, 1), logy=True, ysign=-1, shift=0.0, minpts=8,
                 axes={"xDefinition": "log10 stellar mass (3D 50 pkpc aperture, with 0.3 dex mock scatter)", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function, dn/dlog10(M*)", "yUnit": "log10(Mpc^-3 dex^-1)"},
                 defs={"massDefinition": "aperture-50pkpc", "imf": "chabrier03", "densityFrame": "comoving", "population": "all"}, pop="all galaxies", what="z=0 GSMF"),
    "shmr": dict(pdf="SMHM_2_Panel.pdf", rel="shmr", z=0.0, fidx=(0, 1), logy=True, ysign=1, shift="shmr", minpts=8,
                 axes={"xDefinition": "log10 halo mass M_BN98 (Bryan & Norman 1998)", "xUnit": "log10(Msun)", "yDefinition": "log10 median stellar-to-halo mass ratio, M*(<50 pkpc)/M_BN98", "yUnit": "dex"},
                 defs={"massDefinition": "aperture-50pkpc", "imf": "chabrier03", "haloMassDefinition": "BN98", "haloMassHistory": "current", "population": "centrals"}, pop="central galaxies", what="z=0 SHMR"),
    "bh": dict(pdf="SMBHM_2_panel.pdf", rel="bh", z=0.0, fidx=(0, 1), logy=True, ysign=1, shift=0.0, minpts=8,
               axes={"xDefinition": "log10 stellar mass (3D 50 pkpc aperture, with 0.3 dex mock scatter)", "xUnit": "log10(Msun)", "yDefinition": "log10 median mass of the most massive black hole in the galaxy", "yUnit": "log10(Msun)"},
               defs={"massDefinition": "aperture-50pkpc", "imf": "chabrier03", "population": "all", "bhMassMethod": "intrinsic"}, pop="all galaxies", what="z=0 BH mass vs stellar mass"),
}
GP_ROWS = [
    dict(row=0, rel="ssfr", z=0.1, log=True, shift=-9.0, tag="ssfr-active", pop="active galaxies (sSFR > 1e-2 /Gyr)", ydef="log10 median specific SFR of active galaxies (converted from /Gyr to /yr)", yunit="log10(1/yr)", extra={"sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median", "population": "active"}),
    dict(row=1, rel="quenched", z=0.0, log=False, shift=0.0, tag="passive", pop="all galaxies", ydef="passive fraction (sSFR < 1e-2 /Gyr), at z=0", yunit="fraction", extra={"quenchingCriterion": "ssfr<1e-11", "population": "all"}),
    dict(row=2, rel="zstar", z=0.1, log=True, shift=0.0, tag="zstar", pop="all galaxies", ydef="log10 stellar metallicity Z*/Zsun (median)", yunit="log10(Z/Zsun)", extra={"metallicityQuantity": "stellar-Z", "metallicityCalibration": "intrinsic-simulation", "population": "all"}),
    dict(row=3, rel="size", z=0.1, log=True, shift=0.0, tag="size-active", pop="active galaxies", ydef="log10 projected stellar half-mass radius R_1/2 (median, kpc), 2D aperture", yunit="log10(kpc)", extra={"sizeDefinition": "stellar-half-mass-projected", "population": "active"}),
    dict(row=4, rel="size", z=0.1, log=True, shift=0.0, tag="size-passive", pop="passive galaxies", ydef="log10 projected stellar half-mass radius R_1/2 (median, kpc), 2D aperture", yunit="log10(kpc)", extra={"sizeDefinition": "stellar-half-mass-projected", "population": "passive"}),
]
NOTE = " Solid segment only, above the resolution-dependent limit (dotted below it is omitted). The paper gives no table. This is one of 12 variations of the L1_m9 model (1 cGpc, intermediate resolution): "


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


def explabels(words, f, axis, edge=2.0):
    out = []
    for w in words:
        m = re.fullmatch(r"10([−-]?\d{1,2})", w[4])
        if not m:
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        e = float(m.group(1).replace("−", "-"))
        if axis == "x" and w[1] > f.y1 and f.x0 - edge < cx < f.x1 + edge:
            out.append((cx, e))
        if axis == "y" and w[0] < f.x0 and f.y0 - 3 < cy < f.y1 + 3:
            out.append((cy, e))
    return sorted(out)


def variant_curves(page, frame, fx, fy, xlo, xhi):
    found = {}
    for c in vf.curves(page, frame, fx, fy, min_items=6):
        if c["width"] != 1.5 or c["dashes"] != "[] 0":
            continue
        v = next((v for v in VARS if near(c["color"], v[1])), None)
        if v is None:
            continue
        found.setdefault(v[0], []).append(c)
    return found


def build(rel, key, vname, vdesc, cosmo, z, pts, axes, defs, pop, citation, figure, panel, sha, member, extra_warning):
    return vf.record(
        rid=f"schaye23.flamingo-{key}.{vname[0]}.z{z:g}", source="FLAMINGO", run=f"L1_m9 variation {vname[2]} ({key.replace('-ap', ', ') + ' kpc 2D aperture' if '-ap' in key else key})", relation=rel, z=z, axes=axes, points=pts, population=pop,
        warning=extra_warning + NOTE + vdesc + ".", definitions={**defs, "cosmology": cosmo}, citation=citation, doi="10.1093/mnras/stad2419", url=f"https://arxiv.org/abs/{ARXIV}", figure=figure, panel=panel, sha=sha, member=member,
        calib="x and y from labelled decades/ticks (log axes validated by the minor-tick pattern; right panels share the y axis with the left panels where unlabelled)", calibration="prediction")


records = []
legend_checked = False
for key, cfg in CFG.items():
    pdf = SRC / "Images" / cfg["pdf"]
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frames(page)
    words = page.get_text("words")
    left, right = fr[0], fr[1]
    if key == "gsmf":
        ylab = explabels(words, left, "y")
        fy, _ = vf.axis_fit_log2(page, left, "y", ylab)
    else:
        ylab = explabels(words, left, "y")
        fy, _ = vf.axis_fit_log2(page, left, "y", ylab)
    fx, xt = vf.axis_fit_log2(page, right, "x", explabels(words, right, "x"))
    assert len(xt) >= 3, (key, xt)
    xlo, xhi = fx(right.x0), fx(right.x1)
    found = variant_curves(page, right, fx, fy, xlo, xhi)
    assert len(found) == 12, (key, sorted(found))
    for v in VARS:
        cs = found[v[0]]
        c = max(cs, key=lambda c: len(c["points"]))
        ylo, yhi = sorted((fy(left.y0), fy(left.y1)))
        pts = [(x, y) for x, y in c["points"] if xlo <= x <= xhi and ylo - 0.02 <= y <= yhi + 0.02]
        if cfg["shift"] == "shmr":
            pts = [(x, y - x) for x, y in pts]
        pts = [(x, y) for x, y in pts]
        assert len(pts) >= cfg["minpts"] and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (key, v[0], len(pts))
        records.append(build(cfg["rel"], key, v, v[3], v[4], cfg["z"], pts, cfg["axes"], cfg["defs"], cfg["pop"],
                             f"Schaye et al. 2023, MNRAS 526, 4978, {cfg['pdf'].split('.')[0]} right panel (model variations)", cfg["pdf"].split(".")[0], f"right panel, {v[2]}", sha, f"Images/{cfg['pdf']} ({v[2]} solid curve)",
                             f"Curve read from the vector paths of Schaye et al. 2023 (MNRAS 526, 4978), right panel of the {cfg['what']} figure."))
# galaxy properties, right column
pdf = SRC / "Images" / "galaxy_props_z01.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fr = vf.frames(page)
words = page.get_text("words")
fx, xt = vf.axis_fit_log2(page, fr[9], "x", explabels(words, fr[9], "x"))
for g in GP_ROWS:
    lf, rf = fr[2 * g["row"]], fr[2 * g["row"] + 1]
    if g["log"]:
        fy, _ = vf.axis_fit_log2(page, lf, "y", explabels(words, lf, "y"))
    else:
        nums = [((w[1] + w[3]) / 2, float(w[4])) for w in words if re.fullmatch(r"\d\.\d", w[4]) and w[0] < lf.x0 and lf.y0 - 3 < (w[1] + w[3]) / 2 < lf.y1 + 3]
        fy, yt = vf.axis_fit(page, lf, "y", labels=nums)
        assert [v for _, v in yt] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]
    xlo, xhi = fx(rf.x0), fx(rf.x1)
    found = {}
    for c in vf.curves(page, rf, fx, fy, min_items=6):
        if c["width"] != 1.5 or c["dashes"] not in ("[] 0", "[ 5.55 2.4 ] 0"):
            continue
        v = next((v for v in VARS if near(c["color"], v[1])), None)
        if v is None:
            continue
        ap = "50" if c["dashes"] == "[] 0" else "100"
        found.setdefault((v[0], ap), []).append(c)
    for ap in (("50", "100") if g["rel"] == "size" else ("50",)):
        assert sum(1 for k in found if k[1] == ap) == 12, (g["tag"], ap, sorted(k for k in found if k[1] == ap))
        for v in VARS:
            c = max(found[(v[0], ap)], key=lambda c: len(c["points"]))
            ylo, yhi = sorted((fy(lf.y0), fy(lf.y1)))
            pts = [(x, y + g["shift"]) for x, y in c["points"] if xlo <= x <= xhi and ylo - 0.02 <= y <= yhi + 0.02]
            if g["rel"] == "quenched":
                assert all(-0.01 <= y <= 1.01 for _, y in pts), v[0]
            assert len(pts) >= 6 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (g["tag"], v[0], ap, len(pts))
            tag = g["tag"] + (f"-ap{ap}" if g["rel"] == "size" else "")
            records.append(build(g["rel"], tag, v, v[3], v[4], g["z"], pts,
                                 {"xDefinition": "log10 stellar mass (3D 50 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": g["ydef"], "yUnit": g["yunit"]},
                                 {"massDefinition": "aperture-50pkpc", "imf": "chabrier03", **g["extra"]}, g["pop"],
                                 f"Schaye et al. 2023, MNRAS 526, 4978, galaxy_props_z01 right column, {g['tag']} (model variations)", "galaxy_props_z01", f"right column, {g['tag']}, {v[2]}", sha, f"Images/{pdf.name} ({v[2]} curve)",
                                 f"Median curve read from the vector paths of Schaye et al. 2023 (MNRAS 526, 4978), galaxy-properties figure, right column, {g['tag']} row, z={g['z']:g}." + (f" Projected half-mass radii in a {ap} kpc 2D aperture." if g["rel"] == "size" else "")))
assert len(records) == 12 * 10, len(records)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "schaye23-flamingo-variations.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FLAMINGO model-variation records (12 variations x GSMF, SHMR, BH, sSFR, passive fraction, stellar Z, sizes)")
