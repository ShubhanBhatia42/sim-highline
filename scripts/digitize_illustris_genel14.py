import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1405.3749"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
COSMO = {"H0": 70.4, "Om": 0.2726}
OB_OM = math.log10(0.0456 / 0.2726)
DEFS = {"total-subhalo": "stellar mass of the full SUBFIND halo (bound mass out to roughly the virial radius for centrals, excluding satellites)",
        "aperture-2rhalf-stars": "stellar mass within twice the stellar half-mass radius (fiducial galactic radius r*)"}
LEFT = {(0.0, 0.5, 0.0): 7, (0.0, 0.0, 1.0): 5, (0.75, 0.0, 0.75): 3, (0.75, 0.75, 0.0): 1}
RIGHT = {(1.0, 0.0, 0.0): 6, (0.6, 0.2, 0.0): 4, (0.0, 1.0, 0.0): 2, (0.0, 0.0, 0.0): 0}
SH_SOLID = {(0.0, 0.0, 0.0): 0, (0.75, 0.75, 0.0): 1, (0.0, 1.0, 0.0): 2, (1.0, 0.0, 1.0): 3, (0.6, 0.2, 0.0): 4}
SH_DASH = {(0.0, 0.0, 0.0): 0, (0.75, 0.75, 0.0): 1, (0.0, 1.0, 0.0): 2, (0.75, 0.0, 0.75): 3, (0.6, 0.2, 0.0): 4}


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


def pick(table, color):
    return next((v for k, v in table.items() if near(color, k)), None)


def numlabels(words, pick_fn):
    out = []
    for w in words:
        s = w[4].replace("−", "-")
        if re.fullmatch(r"-?\d+(\.\d+)?", s) and pick_fn(w) is not None:
            out.append((pick_fn(w), float(s)))
    return sorted(out)


records = []
# ---- GSMF (f3)
pdf = SRC / "f3.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fl, fr_ = vf.frames(page)
words = page.get_text("words")
fy, yt = vf.axis_fit(page, fl, "y")
assert [v for _, v in yt][:3] == [-1.0, -1.5, -2.0] or sorted(v for _, v in yt)[:2] == [-5.0, -4.5], yt
for frame, table in ((fl, LEFT), (fr_, RIGHT)):
    lab = numlabels(words, lambda w, f=frame: (w[0] + w[2]) / 2 if w[1] > f.y1 and f.x0 - 2 <= (w[0] + w[2]) / 2 <= f.x1 + 2 else None)
    fx, xt = vf.axis_fit(page, frame, "x", labels=lab)
    assert len(xt) >= 5, xt
    xlo, xhi, ylo, yhi = fx(frame.x0), fx(frame.x1), fy(frame.y1), fy(frame.y0)
    found = {}
    for c in vf.curves(page, frame, fx, fy, min_items=8):
        z = pick(table, c["color"])
        if z is None:
            continue
        kind = "total-subhalo" if (c["width"] == 1.0 and c["dashes"] == "[] 0") else "aperture-2rhalf-stars" if (c["width"] == 0.5 and c["dashes"] == "[ 6 ] 0") else None
        if kind is None:
            continue
        pts = [(x, y) for x, y in c["points"] if xlo <= x <= xhi and ylo <= y <= yhi]
        assert (z, kind) not in found and len(pts) >= 6 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (z, kind)
        found[(z, kind)] = pts
    assert len(found) == 8, (len(found), sorted(found))
    for (z, kind), pts in sorted(found.items()):
        records.append(vf.record(
            rid=f"genel14.illustris-1.gsmf-{'full' if kind == 'total-subhalo' else 'r2'}.z{z}", source="Illustris", run=f"Illustris-1 ({'full SUBFIND mass' if kind == 'total-subhalo' else 'mass within 2 R_half'})", relation="gsmf", z=float(z), z_nominal=float(z),
            axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function (Mpc^-3 dex^-1)", "yUnit": "log10(Mpc^-3 dex^-1)"},
            points=pts, population="all galaxies",
            warning=f"Curve read from the vector paths of Genel et al. 2014 (MNRAS 445, 175), Fig. 3 (stellar mass function across cosmic time; arXiv source numbering); no table exists. The paper labels the redshifts approximately (z~{z}). "
                    f"Stellar mass: {DEFS[kind]}. The dotted curves repeated from the other panel are not extracted. Curve clipped to the plotted axis range.",
            definitions={"massDefinition": kind, "imf": "chabrier03", "cosmology": COSMO, "densityFrame": "comoving", "population": "all"},
            citation="Genel et al. 2014, MNRAS 445, 175, Fig. 3 (arXiv source numbering)", doi="10.1093/mnras/stu1654", url=f"https://arxiv.org/abs/{ARXIV}", figure="Figure 3", panel=f"z~{z}", sha=sha,
            member=f"f3.pdf ({'solid' if kind == 'total-subhalo' else 'dashed'} z~{z} curve)", calib="x: labelled ticks per panel; y: labelled ticks of the left panel (shared); asserted", calibration="target" if z == 0 else "prediction"))
# ---- SHMR (f6a)
pdf = SRC / "f6a.pdf"
page = vf.page_of(pdf)
sha6 = vf.sha256(pdf)
frame = vf.frames(page)[0]
words = page.get_text("words")
xl = numlabels(words, lambda w: (w[0] + w[2]) / 2 if w[1] > frame.y1 else None)
fx, xt = vf.axis_fit(page, frame, "x", labels=xl)
yl = [(p, math.log10(v)) for p, v in numlabels(words, lambda w: (w[1] + w[3]) / 2 if w[0] < frame.x0 else None)]
fy, yt = vf.axis_fit(page, frame, "y", labels=yl)
assert len(xt) >= 6 and len(yt) >= 5, (xt, yt)
xlo, xhi = fx(frame.x0), fx(frame.x1)
found = {}
for c in vf.curves(page, frame, fx, fy, min_items=8):
    for kind, table, wd, dsh in (("total-subhalo", SH_SOLID, 2.0, "[] 0"), ("aperture-2rhalf-stars", SH_DASH, 1.0, "[ 6 ] 0")):
        z = pick(table, c["color"])
        if z is not None and c["width"] == wd and c["dashes"] == dsh:
            pts = [(x, y + OB_OM) for x, y in c["points"] if xlo <= x <= xhi]
            assert (z, kind) not in found and len(pts) >= 8 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (z, kind)
            found[(z, kind)] = pts
assert len(found) == 10, sorted(found)
for (z, kind), pts in sorted(found.items()):
    records.append(vf.record(
        rid=f"genel14.illustris-1.shmr-{'full' if kind == 'total-subhalo' else 'r2'}.z{z}", source="Illustris", run=f"Illustris-1 ({'full mass inside R200c' if kind == 'total-subhalo' else 'mass within 2 R_half'}, DMO-matched halo mass)", relation="shmr", z=float(z),
        axes={"xDefinition": "log10 halo mass M200c (matched Illustris-Dark halo)", "xUnit": "log10(Msun)", "yDefinition": "log10 stellar-to-halo mass ratio, M*/M200c (converted from the plotted ratio normalised by Omega_b/Omega_m)", "yUnit": "dex"},
        points=pts, population="central galaxies",
        warning="Median-type curve read from the vector paths of Genel et al. 2014 Fig. 6 left panel (baryon conversion efficiency; arXiv source numbering); no table exists. The paper plots M*/(M200c Omega_b/Omega_m) with halo masses taken from individually matched Illustris-Dark halos "
                f"(for a fair comparison with abundance matching); converted by adding log10(Omega_b/Omega_m) = {OB_OM:.4f}. Stellar mass: " + ("full stellar mass inside R200c excluding satellites." if kind == "total-subhalo" else "stellar mass within the fiducial galactic radius r* (twice the half-mass radius), excluding satellites."),
        definitions={"massDefinition": "aperture-2rhalf-stars" if kind != "total-subhalo" else "stars-within-R200c-excluding-satellites", "imf": "chabrier03", "cosmology": COSMO, "haloMassDefinition": "M200crit-DMO-matched", "haloMassHistory": "current", "population": "centrals"},
        citation="Genel et al. 2014, MNRAS 445, 175, Fig. 6a (arXiv source numbering)", doi="10.1093/mnras/stu1654", url=f"https://arxiv.org/abs/{ARXIV}", figure="Figure 6 (left panel)", panel=f"z={z}", sha=sha6,
        member=f"f6a.pdf ({'solid' if kind == 'total-subhalo' else 'dashed'} z={z} curve)", calib="x: labelled ticks 11-14.5; y: log scale from labelled ticks 0.03-0.5; asserted", calibration="prediction"))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "genel14-illustris.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Illustris GSMF (z~0-7) and SHMR (z 0-4) records, full and 2 R_half stellar masses, from Genel+14 vector paths")
