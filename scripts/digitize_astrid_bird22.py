import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2111.01160"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
OB_OM = math.log10(0.0486 / 0.3089)
COSMO = {"H0": 67.74, "Om": 0.3089}
SHMR = {((0.0, 0.0, 0.0), "[] 0"): 4.0, ((0.0, 0.0, 1.0), "[ 5.55 2.4 ] 0"): 8.0, ((0.65, 0.16, 0.16), "[ 5.55 2.4 ] 0"): 6.0, ((0.5, 0.5, 0.5), "[ 1.5 2.475 ] 0"): 3.0, ((1.0, 0.0, 0.0), "[ 1.5 2.475 ] 0"): 10.0}
ZSTAR = {((0.0, 0.0, 0.0), "[] 0"): 10.0, ((1.0, 0.0, 0.0), "[ 9.6 2.4 1.5 2.4 ] 0"): 8.0, ((0.0, 0.0, 1.0), "[ 5.55 2.4 ] 0"): 6.0, ((0.65, 0.16, 0.16), "[ 1.5 2.475 ] 0"): 4.0, ((0.5, 0.5, 0.5), "[] 0"): 3.0}
CFG = {
    "shmr": dict(pdf="smhms.pdf", rel="shmr", map=SHMR, fig="smhm",
                 axes={"xDefinition": "log10 halo mass (FOF)", "xUnit": "log10(Msun)", "yDefinition": "log10 median stellar-to-halo mass ratio, M*/Mh (converted from the plotted ratio normalised by Omega_m/Omega_b)", "yUnit": "dex"},
                 defs={"imf": "unspecified", "cosmology": COSMO, "massDefinition": "unspecified", "haloMassDefinition": "FOF", "haloMassHistory": "current", "population": "all-halos-with-at-least-10-per-bin"}),
    "zstar": dict(pdf="starmetal_oh.pdf", rel="zstar", map=ZSTAR, fig="stellar_metal",
                  axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "12 + log10(O/H) of stars (oxygen number abundance per hydrogen, hydrogen mass assumed 0.76 M*)", "yUnit": "dex"},
                  defs={"imf": "unspecified", "cosmology": COSMO, "massDefinition": "unspecified", "metallicityQuantity": "stellar-O/H", "metallicityCalibration": "intrinsic-simulation", "population": "all"}),
}


def near(c, t, tol=0.02):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


records = []
for key, cfg in CFG.items():
    pdf = SRC / "plots" / cfg["pdf"]
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    frame = vf.frames(page)[0]
    words = page.get_text("words")
    xlab = sorted(((w[0] + w[2]) / 2, float(w[4][2:])) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[1] > frame.y1)
    fx, xt = vf.axis_fit(page, frame, "x", labels=xlab)
    if key == "shmr":
        bases = sorted(((w[1] + w[3]) / 2, w) for w in words if w[4] == "10" and w[0] < frame.x0)
        sups = {round((w[1] + w[3]) / 2): w[4] for w in words if w[4] in ("1", "2", "3") and w[0] < frame.x0 + 5 and w[0] > frame.x0 - 30}
        ylab = []
        for cy, bw in bases:
            sup = min(sups.items(), key=lambda kv: abs(kv[0] - cy))
            assert abs(sup[0] - cy) < 8, (cy, sup)
            ylab.append((cy, -float(sup[1])))
        fy, yt = vf.axis_fit(page, frame, "y", labels=ylab, snap=8.0)
    else:
        fy, yt = vf.axis_fit(page, frame, "y")
    xlo, xhi = fx(frame.x0), fx(frame.x1)
    if key == "shmr":
        assert [v for _, v in xt][:3] == [10, 11, 12] and sorted(v for _, v in yt) == [-3, -2, -1], (xt, yt)
    else:
        assert [v for _, v in xt] == [7, 8, 9, 10, 11, 12]
    seen = {}
    for c in vf.curves(page, frame, fx, fy, min_items=10):
        if c["width"] != 1.5:
            continue
        k = next((kk for kk in cfg["map"] if near(c["color"], kk[0]) and c["dashes"] == kk[1]), None)
        if k is None:
            continue
        z = cfg["map"][k]
        pts = [(x, y) for x, y in c["points"] if xlo <= x <= xhi]
        if key == "shmr":
            pts = [(x, y + OB_OM) for x, y in pts]
        assert z not in seen and len(pts) >= 8 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (key, z)
        seen[z] = pts
    assert set(seen) == set(cfg["map"].values()), (key, set(seen))
    for z, pts in sorted(seen.items()):
        records.append(vf.record(
            rid=f"bird22.astrid.{key}.z{z:g}", source="ASTRID", run="ASTRID (250 Mpc/h)", relation=cfg["rel"], z=z, axes=cfg["axes"], points=pts, population="all halos" if key == "shmr" else "all galaxies",
            warning=f"Median curve read from the vector paths of Bird et al. 2022 (MNRAS 512, 3703), figure {cfg['fig']} (arXiv source numbering); no table exists. "
                    + ("The paper plots (M*/Mh)/(Omega_m/Omega_b); converted by adding log10(Omega_b/Omega_m) = %.4f. Each halo mass bin has at least 10 halos. The 16th-84th percentile band shown only for z=3 and the THESAN comparison lines are not extracted." % OB_OM if key == "shmr"
                       else "Stellar oxygen abundance, hydrogen mass assumed 0.76 M*; the grey percentile band and the Sanders+21 observational band are not extracted."),
            definitions=dict(cfg["defs"]), citation=f"Bird et al. 2022, MNRAS 512, 3703, figure {cfg['fig']} (arXiv source numbering), z={z:g}", doi="10.1093/mnras/stac648", url=f"https://arxiv.org/abs/{ARXIV}",
            figure=cfg["fig"], panel=f"z={z:g} curve", sha=sha, member=f"plots/{cfg['pdf']} (z={z:g} line)",
            calib="both axes from labelled ticks (halo and stellar mass decades, log; SHMR y decades from the split base/exponent labels)", calibration="prediction"))
assert len(records) == 10
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "bird22-astrid.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} ASTRID SHMR and stellar O/H records from Bird+22 vector paths")
