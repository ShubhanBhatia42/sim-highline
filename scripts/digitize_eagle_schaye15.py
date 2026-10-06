import json
import math
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1407.7040"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
RUNS = {(0.2, 0.13, 0.53): ("ref", "Ref-L100N1504", 1e5 / 0.6777), (0.8, 0.4, 0.47): ("agndt9", "AGNdT9-L050N0752", 1e5 / 0.6777), (0.27, 0.67, 0.6): ("recal", "Recal-L025N0752", 1e5 / 0.6777)}
FIGS = {
    "bh": dict(pdf="bh_2scat_Stars_030kpc_BH_MostMassive_MERGED.pdf", x0=70.81, rel="bh", xs=7.0, ymin=5.0, ystep=1.0, ny=7, fig="BH mass vs stellar mass (fig:bh)",
               axes={"xDefinition": "log10 stellar mass (3D 30 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": "log10 mass of the most massive black hole in the galaxy", "yUnit": "log10(Msun)"},
               shift=0.0, pop="all galaxies", what="median mass of the central supermassive black hole vs stellar mass at z=0.1",
               defs={"imf": "chabrier03", "massDefinition": "aperture-30pkpc", "bhMassMethod": "intrinsic", "population": "all"}),
    "ssfr": dict(pdf="ssfr_2scat.pdf", x0=73.42, rel="ssfr", xs=7.0, ymin=-2.5, ystep=0.5, ny=7, fig="sSFR of star-forming galaxies (fig:ssfr, left panel)",
                 axes={"xDefinition": "log10 stellar mass (3D 30 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": "log10 median specific SFR of star-forming galaxies (sSFR > 1e-2 /Gyr), converted from /Gyr to /yr", "yUnit": "log10(1/yr)"},
                 shift=-9.0, pop="star-forming galaxies (sSFR > 1e-2 Gyr^-1)", what="median specific SFR of actively star-forming galaxies at z=0.1 (converted by subtracting 9 from the plotted log10 Gyr^-1)",
                 defs={"imf": "chabrier03", "massDefinition": "aperture-30pkpc", "sfrTimescaleMyr": "instantaneous (gas, 30 pkpc)", "sfrStatistic": "median", "population": "star-forming"}),
    "stfr": dict(pdf="tf_vmax_2scat.pdf", x0=70.81, rel="stfr", xs=7.0, ymin=1.4, ystep=0.2, ny=8, fig="Tully-Fisher analogue (fig:tf)",
                 axes={"xDefinition": "log10 stellar mass (3D 30 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": "log10 maximum circular velocity (median, late-type galaxies)", "yUnit": "log10(km/s)"},
                 shift=0.0, pop="late-type galaxies (Sersic index n_s < 2.5)", what="median maximum circular velocity vs stellar mass for late-type galaxies at z=0.1",
                 defs={"imf": "chabrier03", "massDefinition": "aperture-30pkpc", "velocityDefinition": "maximum circular velocity", "population": "late-type"}),
}
FRAME_Y = (17.6, 398.57)


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


records = []
for key, cfg in FIGS.items():
    pdf = SRC / cfg["pdf"]
    page = pymupdf.open(pdf)[0]
    sha = vf.sha256(pdf)
    dr = page.get_drawings()
    ticks_x, ticks_y = [], []
    for d in dr:
        for it in d["items"]:
            if it[0] != "l":
                continue
            a, b = it[1], it[2]
            if abs(a.x - b.x) < 0.01 and abs(max(a.y, b.y) - FRAME_Y[1]) < 0.3 and 7.0 < abs(a.y - b.y) < 8.2:
                ticks_x.append(a.x)
            if abs(a.y - b.y) < 0.01 and abs(min(a.x, b.x) - cfg["x0"]) < 0.3 and 8.0 < abs(a.x - b.x) < 8.8:
                ticks_y.append(a.y)
    tx, ty = sorted(set(round(v, 2) for v in ticks_x)), sorted(set(round(v, 2) for v in ticks_y), reverse=True)
    assert len(tx) == 6 and len(ty) == cfg["ny"], (key, tx, ty)
    sx = (tx[-1] - tx[0]) / 5
    sy = (ty[0] - ty[-1]) / (cfg["ny"] - 1)
    assert all(abs(tx[k] - (tx[0] + k * sx)) < 0.1 for k in range(6)) and all(abs(ty[k] - (ty[0] - k * sy)) < 0.1 for k in range(cfg["ny"])), (key, "ticks not uniform")
    fx = lambda px: cfg["xs"] + (px - tx[0]) / sx
    fy = lambda py: cfg["ymin"] + (ty[0] - py) / sy * cfg["ystep"]
    frame = pymupdf.Rect(cfg["x0"], FRAME_Y[0], 492.9, FRAME_Y[1])
    if key == "ssfr":
        hl = [d for d in dr if d["items"] and d["items"][0][0] == "l" and abs(d["items"][0][1].y - d["items"][0][2].y) < 0.01 and abs(d["items"][0][1].x - d["items"][0][2].x) > 200 and abs(d["items"][0][1].y - 335.08) < 0.3 and d["dashes"] != "[] 0"]
        assert abs(fy(335.08) - (-2.0)) < 0.01 and len(hl) >= 1, ("sSFR limit line", len(hl))
    seen = {}
    for c in vf.curves(page, frame, fx, fy, min_items=8):
        run = next((v for k, v in RUNS.items() if near(c["color"], k)), None)
        if run is None or c["width"] is None or abs(c["width"] - 3.1) > 0.15 or c["dashes"] != "[] 0":
            continue
        pts = [(x, y + cfg["shift"]) for x, y in c["points"]]
        pts = [(x, y) for x, y in pts if fx(frame.x0) <= x <= fx(frame.x1)]
        assert run[0] not in seen and len(pts) >= 8 and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (key, run[0])
        seen[run[0]] = (pts, run)
    assert set(seen) == {"ref", "agndt9", "recal"}, (key, set(seen))
    if key == "bh":
        for rk, (pts, run) in seen.items():
            assert abs(min(y for _, y in pts) - math.log10(run[2])) < 0.06, ("BH seed-mass floor", rk, min(y for _, y in pts), math.log10(run[2]))
    if key == "stfr":
        assert abs(seen["ref"][0][0][0] - math.log10(100 * 1.81e6)) < 0.2 and abs(seen["recal"][0][0][0] - math.log10(100 * 2.26e5)) < 0.2, ("resolution-limit start", seen["ref"][0][0][0], seen["recal"][0][0][0])
    for rk, (pts, run) in sorted(seen.items()):
        records.append(vf.record(
            rid=f"schaye15.eagle-{rk}.{key}.z0.1", source="EAGLE", run=run[1], relation=cfg["rel"], z=0.1, axes=cfg["axes"], points=pts, population=cfg["pop"],
            warning=f"Solid segment only of the median curve in Schaye et al. 2015 (MNRAS 446, 521), {cfg['fig']}: {cfg['what']}. The dotted part below the resolution limit, the 1-sigma shading (shown for only two runs) and individual objects in sparse bins are omitted; no table exists. "
                    "Axis text is outlined, so axes were calibrated from the major tick marks and checked against " + {"bh": "the BH seed-mass floor (1e5/h Msun = log 5.17).", "ssfr": "the dashed sSFR = 1e-2 /Gyr limit line.", "stfr": "the 100-stellar-particle resolution limits where the solid curves start."}[key],
            definitions={**cfg["defs"], "cosmology": {"H0": 67.77, "Om": 0.307}}, citation=f"Schaye et al. 2015, MNRAS 446, 521, {cfg['fig']}", doi="10.1093/mnras/stu2058", url=f"https://arxiv.org/abs/{ARXIV}",
            figure=cfg["fig"], panel="z=0.1", sha=sha, member=f"{cfg['pdf']} ({run[1]} solid median)",
            calib="manual: major ticks (x: 7-12, 76.75 pt/dex; y per figure), uniform spacing asserted; independent checks in the script", calibration="prediction"))
assert len(records) == 9
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "schaye15-eagle.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} EAGLE z=0.1 records (BH-M*, sSFR, Tully-Fisher analogue; 3 runs each) from Schaye+15 vector paths")
