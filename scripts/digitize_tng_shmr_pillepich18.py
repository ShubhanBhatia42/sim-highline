import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1707.03406"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
L = math.log10
RUNS = {
    (0.84, 0.15, 0.16): ("illustris", "Illustris", "Illustris-1 M200c", L(0.0456 / 0.2726), {"H0": 70.4, "Om": 0.2726}),
    (0.12, 0.47, 0.71): ("tng100", "IllustrisTNG", "TNG100-1 M200c", L(0.0486 / 0.3089), {"H0": 67.74, "Om": 0.3089}),
    (1.0, 0.5, 0.05): ("rtng300", "IllustrisTNG", "rTNG300-1 (resolution-corrected) M200c", L(0.0486 / 0.3089), {"H0": 67.74, "Om": 0.3089}),
}
XLABELS = ("1010", "1011", "1012", "1013", "1014", "1015")


def xfit(page, frame):
    lab = [((w[0] + w[2]) / 2, float(w[4][2:])) for w in page.get_text("words") if w[4] in XLABELS]
    return vf.axis_fit(page, frame, "x", labels=lab)


def points(c, fy_is_log, ymin=None):
    pts = [(x, y if fy_is_log else L(y)) for x, y in c["points"] if (fy_is_log or y > 0)]
    return [(x, y) for x, y in pts if ymin is None or y > ymin]


def build(key, source, run, off, cosmo, z, pts, figname, panel, sha, member, calib, ill):
    return vf.record(
        rid=f"pillepich18.{key}.shmr.z{z:g}", source=source, run=run, relation="shmr", z=z,
        axes={"xDefinition": "log10 halo mass M200c", "xUnit": "log10(Msun)", "yDefinition": "log10 stellar-to-halo mass ratio, M*(<30 pkpc)/M200c (converted from the plotted ratio normalised by Omega_b/Omega_m)", "yUnit": "dex"},
        points=[(x, y + off) for x, y in pts], population="central galaxies",
        warning=f"Curve vertices read from the vector paths of Pillepich et al. 2018 (MNRAS 475, 648), {figname}; no table exists. The paper plots (M*/Mhalo)/(Omega_b/Omega_m); "
                f"converted by adding log10(Omega_b/Omega_m) = {off:.4f} using the simulation's own cosmology"
                + ("; the paper does not state which Omega_b/Omega_m was used for Illustris, so a +-0.03 dex normalisation uncertainty is assumed." if ill else ".")
                + (" The z label in the paper is approximate (z~)." if z > 0 else "")
                + (" rTNG300 is TNG300 with the paper's resolution correction to stellar masses; not an unmodified catalogue." if key == "rtng300" else ""),
        definitions={"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "cosmology": cosmo, "haloMassDefinition": "M200crit", "haloMassHistory": "current", "population": "centrals"},
        citation=f"Pillepich et al. 2018, MNRAS 475, 648, {figname}", doi="10.1093/mnras/stx3112", url=f"https://arxiv.org/abs/{ARXIV}",
        figure="Figure 11", panel=panel, sha=sha, member=member, calib=calib, uncertainty=0.03 if ill else 0.01,
        calibration="target" if z == 0 else "prediction")


records = []
pdf1 = SRC / "fig_sm2hm_1.pdf"
pg1 = vf.page_of(pdf1)
fr1 = vf.frames(pg1)[1]
fx1, xt = xfit(pg1, fr1)
fy1, yt = vf.axis_fit(pg1, fr1, "y")
assert [v for _, v in xt] == [10, 11, 12, 13, 14, 15] and [v for _, v in yt] == [0.3, 0.25, 0.2, 0.15, 0.1, 0.05, 0.0]
sha1 = vf.sha256(pdf1)
z0 = {}
for c in vf.curves(pg1, fr1, fx1, fy1, min_items=6):
    if c["color"] in RUNS and c["width"] == 8.0 and c["dashes"] == "[] 0":
        key, source, run, off, cosmo = RUNS[c["color"]]
        pts = points(c, False)
        z0[key] = pts
        records.append(build(key, source, run, off, cosmo, 0.0, pts, "Fig. 11 (arXiv source numbering; top-left panel, fig_sm2hm_1)", "top left, z=0 centrals, <30 kpc (thick solid)", sha1,
                             f"{pdf1.name} (thick solid {run} line, 8 pt stroke)", "x: ticks 10^10-10^15 (139.8 pt/dex); y: linear ticks 0-0.3 (1797 pt per unit); frame and labels asserted", key == "illustris"))
assert set(z0) == {"illustris", "tng100", "rtng300"}, set(z0)

pdf3 = SRC / "fig_sm2hm_3.pdf"
pg3 = vf.page_of(pdf3)
fr3 = vf.frames(pg3)[1]
ylab = [(257.29, -1.0)] + [(y, L(v)) for y, v in [(276.91, .09), (298.84, .08), (323.71, .07), (352.42, .06), (386.37, .05), (427.92, .04), (481.49, .03), (128.21, .2), (52.71, .3)]]
fy3, yt3 = vf.axis_fit(pg3, fr3, "y", labels=ylab)
fx3, xt3 = xfit(pg3, fr3)
assert len(yt3) == 10 and [v for _, v in xt3] == [10, 11, 12, 13, 14, 15]
sha3 = vf.sha256(pdf3)
YMIN = fy3(fr3.y1) + 0.002
ZS = {"[] 0": 0.0, "[ 3 3 ] 0": 0.5, "[ 12 12 ] 0": 1.0}
words = " ".join(w[4] for w in pg3.get_text("words"))
assert "z = 0.0" in words and "z = 0.5" in words and "z = 1.0" in words
tng100_z0 = None
for c in vf.curves(pg3, fr3, fx3, fy3, min_items=6):
    if c["color"] not in RUNS or c["color"] == (0.84, 0.15, 0.16) or c["dashes"] not in ZS or c["width"] not in (3.0, 5.0):
        continue
    key, source, run, off, cosmo = RUNS[c["color"]]
    z = ZS[c["dashes"]]
    pts = points(c, True, YMIN)
    if z == 0.0:
        if key == "tng100":
            tng100_z0 = pts
        continue
    records.append(build(key, source, run, off, cosmo, z, pts, "Fig. 11 (arXiv source numbering; bottom-left panel, fig_sm2hm_3)", f"bottom left, z~{z:g} centrals, <30 kpc", sha3,
                         f"{pdf3.name} ({c['dashes']} dashed {run} line)", "x: ticks 10^10-10^15; y: log axis calibrated on 10 labelled/minor ticks (0.03-0.3, 428.8 pt/dex); all agree", False))
assert tng100_z0 is not None
for x, y in tng100_z0[3:-3:4]:
    y1 = min(z0["tng100"], key=lambda p: abs(p[0] - x))
    assert abs(x - y1[0]) < 0.06 and abs(y - y1[1]) < 0.05, (x, y, y1)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "pillepich18-shmr.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} SHMR records from Pillepich+18 vector paths; z=0 TNG100 agrees across both figures")
