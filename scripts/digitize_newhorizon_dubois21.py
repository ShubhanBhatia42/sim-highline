import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2009.10578"
DOI = "10.1051/0004-6361/202039429"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
COL = {(1.0, 0.0, 0.0): 4.0, (0.5996, 0.8301, 0.0): 2.0, (0.0, 0.498, 1.0): 1.0, (0.5488, 0.0, 0.8301): 0.25}
DEF = {"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.272}, "massDefinition": "aperture-Reff-stars", "population": "all"}
Z0 = {"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.272}, "massDefinition": "aperture-Reff-stars", "population": "all"}
MASSAX = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)"}
STD = dict(lw=1.417, dash="[] 0", bar_lw=1.417)
FIGS = {
    "ssfr": dict(pdf="ssfrvsmgal_reff-eps-converted-to.pdf", ylog=True, fig="sSFR versus stellar mass", layers=[dict(
        STD, rel="ssfr", shift=-9.0, axes={**MASSAX, "yDefinition": "log10 mean specific SFR, converted from /Gyr to /yr", "yUnit": "log10(1/yr)"},
        what="mean sSFR (solid lines with errors of the mean)", defs={**Z0, "sfrStatistic": "mean", "sfrTimescaleMyr": 100}, tag="", run="NewHorizon",
        meas="Stellar mass and sSFR are measured within the effective radius R_eff (SFR from stars younger than 100 Myr).", extra="")]),
    "mzr": dict(pdf="metgvsmgal_reff_nmin1d-1_tmax2d4-eps-converted-to.pdf", ylog=False, fig="cold-gas oxygen abundance versus stellar mass", layers=[dict(
        STD, rel="mzr", shift=0.0, axes={**MASSAX, "yDefinition": "average oxygen abundance of cold gas, 12+log10(O/H)", "yUnit": "12+log10(O/H)"},
        what="average cold-gas oxygen abundance (solid lines with errors of the mean)", defs={**Z0, "metallicityQuantity": "gas-O/H"}, tag="", run="NewHorizon",
        meas="Stellar mass within R_eff.", extra=" Oxygen is not followed by the code: the gas metallicity is rescaled to oxygen with solar fractions (H 73.4%, O 43% of metals), a crude estimate per the paper; cold gas is n > 0.1 cm^-3 and T < 2e4 K.")]),
    "met": dict(pdf="metsvsmgal_reff-eps-converted-to.pdf", ylog=True, fig="stellar and gas metallicity versus stellar mass", layers=[
        dict(lw=2.8, dash="[] 0", bar_lw=2.8, rel="zstar", shift=0.0, axes={**MASSAX, "yDefinition": "log10 mass-weighted stellar metallicity Zs / Zsun (Zsun = 0.01345)", "yUnit": "dex"},
             what="average mass-weighted stellar metallicity (thick solid lines with errors of the mean)", defs={**Z0, "metallicityQuantity": "stellar-Z", "metallicityCalibration": "intrinsic mass-weighted (Zsun=0.01345)"}, tag="", run="NewHorizon",
             meas="Stellar mass and metallicity within R_eff; the solar value is 0.01345.", extra=""),
        dict(lw=0.8, dash="[ 5.6693 5.6693 ] 0", bar_lw=0.8, rel="mzr", shift=0.0, axes={**MASSAX, "yDefinition": "log10 cold-gas metallicity Zg / Zsun (Zsun = 0.01345)", "yUnit": "dex"},
             what="average cold-gas metallicity (thin dashed lines with errors of the mean)", defs={**Z0, "metallicityQuantity": "gas-metal-mass-fraction", "metallicityCalibration": "intrinsic (cold gas n > 0.1 cm^-3, T < 2e4 K)"}, tag="gas", run="NewHorizon (cold gas Z/Zsun)",
             meas="Stellar mass within R_eff.", extra="")]),
}


def numlab(w):
    return float(w[4].replace("−", "-")) if re.fullmatch(r"[−-]?\d+(\.\d+)?", w[4]) else None


records = []
for key, cfg in FIGS.items():
    pdf = next(SRC.rglob(cfg["pdf"]))
    page = vf.page_of(pdf)
    sha = vf.sha256(pdf)
    fr = vf.frame_from_long_lines(page)
    words = page.get_text("words")
    xlab = sorted(((w[0] + w[2]) / 2, float(w[4][2:])) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[1] > fr.y1)
    fx, xt = vf.axis_fit_log2(page, fr, "x", xlab)
    ylab = sorted(((w[1] + w[3]) / 2, numlab(w)) for w in words if numlab(w) is not None and w[2] < fr.x0 and fr.y0 - 8 < (w[1] + w[3]) / 2 < fr.y1 + 8)
    if cfg["ylog"]:
        fy, yt = vf.axis_fit_log2(page, fr, "y", [(p, math.log10(v)) for p, v in ylab], snap=7.0)
    else:
        fy, yt = vf.axis_fit(page, fr, "y", labels=ylab)
    for lay in cfg["layers"]:
        lines, bars = {}, []
        for d in page.get_drawings():
            c, its = d["color"], d["items"]
            z = next((z for k, z in COL.items() if c and all(abs(a - b) < 0.01 for a, b in zip(c, k))), None)
            if z is None or any(i[0] != "l" for i in its):
                continue
            w = d.get("width") or 0
            pts = [its[0][1]] + [i[2] for i in its]
            if len(its) == 5 and abs(w - lay["bar_lw"]) < 0.05 and d["dashes"] == "[] 0" and all(abs(p.x - pts[0].x) < 5 for p in pts) and abs(its[2][1].x - its[2][2].x) < 0.01:
                bars.append((z, its[2][1].x, sorted((fy(its[2][1].y), fy(its[2][2].y)))))
            elif len(its) >= 3 and abs(w - lay["lw"]) < 0.05 and d["dashes"] == lay["dash"] and pts[0].x < pts[-1].x and fr.x0 - 1 <= pts[0].x and pts[-1].x <= fr.x1 + 1:
                lines.setdefault(z, []).append(pts)
        print(key, lay["tag"], {z: [len(l) for l in ls] for z, ls in lines.items()}, {z: sum(1 for b in bars if b[0] == z) for z in COL.values()})
        assert set(lines) == set(COL.values()), (key, lay["tag"], set(lines))
        for z, ls in sorted(lines.items()):
            assert len(ls) == 1, (key, z, len(ls))
            pts = []
            for p in ls[0]:
                b = next((b for b in bars if b[0] == z and abs(b[1] - p.x) < 0.5), None)
                y = fy(p.y) + lay["shift"]
                pt = {"x": round(fx(p.x), 3), "y": round(y, 4)}
                if b is not None:
                    pt.update(yLow=round(b[2][0] + lay["shift"], 4), yHigh=round(b[2][1] + lay["shift"], 4))
                pts.append(pt)
            nobar = sum(1 for p in pts if "yLow" not in p)
            assert nobar <= 1 and all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and all(p["yLow"] <= p["y"] + 1e-6 <= p["yHigh"] + 2e-6 for p in pts if "yLow" in p), (key, z)
            miss = " The point without an error bar has none drawn in the figure." if nobar else ""
            conv = " Plotted log10 Gyr^-1 converted to log10 yr^-1 by subtracting 9." if lay["shift"] else ""
            tag = f"-{lay['tag']}" if lay["tag"] else ""
            records.append(vf.record(
                rid=f"dubois21.newhorizon.{lay['rel']}{tag}.z{z:g}", source="NewHorizon", run=lay["run"], relation=lay["rel"], z=z, axes=lay["axes"], points=pts, population="all galaxies",
                warning=f"{lay['what'][0].upper() + lay['what'][1:]} at z={z:g} read from the vector paths of Dubois et al. 2021 ({cfg['fig']}); error bars are the plotted errors of the mean, not a scatter. "
                        f"No table exists. Observational overlays on the figure are not extracted. {lay['meas']}{conv}{lay['extra']}{miss}",
                definitions=lay["defs"], interval="uncertainty", citation=f"Dubois et al. 2021, A&A 651, A109 (arXiv:{ARXIV}), {cfg['fig']}, z={z:g}", doi=DOI,
                url=f"https://arxiv.org/abs/{ARXIV}", figure=cfg["fig"], panel=f"z={z:g}", sha=sha, member=f"{pdf.name}", calibration="prediction",
                calib="x: labelled decades validated by the minor-tick pattern; y: labelled " + ("log decades" if cfg["ylog"] else "ticks")))

pdf = next(SRC.rglob("mstarovermhalovsmhalo-eps-converted-to.pdf"))
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
grid = vf.grid_from_long_lines(page)
assert len(grid) == 2 and all(len(r) == 2 for r in grid)
words = page.get_text("words")
ZPAN = {(0, 0): 4.0, (0, 1): 2.0, (1, 0): 1.0, (1, 1): 0.25}
zlab = {w[4]: w for w in words if re.fullmatch(r"z=\d(\.\d+)?", w[4])}
fxc, fyr = {}, {}
for col in (0, 1):
    pn = grid[1][col]
    fxc[col], xt = vf.axis_fit(page, pn, "x")
    assert len(xt) >= 4, xt
for row in (0, 1):
    pn = grid[row][0]
    lab = sorted(((w[1] + w[3]) / 2, numlab(w)) for w in words if numlab(w) is not None and w[2] < pn.x0 and pn.y0 - 3 < (w[1] + w[3]) / 2 < pn.y1 + 3)
    fyr[row], yt = vf.axis_fit_shifted(page, pn, "y", lab)
    assert len(lab) >= 4, lab
RED, ORANGE = (1.0, 0.0, 0.0), (0.98, 0.62, 0.35)
close = lambda c, t: c is not None and all(abs(a - b) < 0.02 for a, b in zip(c, t))
shmr_defs = {**Z0, "haloMassDefinition": "BN98", "haloMassHistory": "current", "population": "main halos (AdaptaHOP galaxies; satellites not shown)"}
shmr_axes = {"xDefinition": "log10 halo mass (total mass within the Bryan and Norman 1998 overdensity radius)", "xUnit": "log10(Msun)", "yDefinition": "log10 stellar-to-halo mass ratio, M*/Mh", "yUnit": "dex"}
for (row, col), z in sorted(ZPAN.items(), key=lambda kv: -kv[1]):
    pn = grid[row][col]
    fx, fy = fxc[col], fyr[row]
    zw = zlab[f"z={z:g}" if z != 4.0 and z != 2.0 and z != 1.0 else f"z={z:.1f}"]
    assert pn.x0 <= zw[0] <= pn.x1 and pn.y0 <= zw[1] <= pn.y1, z
    solid, dashed, gal = [], [], []
    for d in page.get_drawings():
        its, r = d["items"], d["rect"]
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if not (pn.x0 < cx < pn.x1 and pn.y0 < cy < pn.y1) or any(i[0] != "l" for i in its):
            continue
        if close(d["color"], ORANGE) and len(its) == 4 and r.width < 8 and r.height < 8:
            gal.append((fx(cx), fy(cy)))
        elif close(d["color"], RED) and len(its) >= 3 and (d.get("width") or 0) < 1.5:
            pts = [its[0][1]] + [i[2] for i in its]
            (dashed if d["dashes"] != "[] 0" else solid).append(pts)
    assert len(solid) == 1 and len(dashed) == 2 and len(gal) >= 100, (z, len(solid), len(dashed), len(gal))
    line = solid[0]
    pts = []
    for p in line:
        ys = [q.y for dl in dashed for q in dl if abs(q.x - p.x) < 0.3]
        pt = {"x": round(fx(p.x), 3), "y": round(fy(p.y), 4)}
        if len(ys) == 2:
            lo, hi = sorted(fy(v) for v in ys)
            pt.update(yLow=round(lo, 4), yHigh=round(hi, 4))
        pts.append(pt)
    nobar = sum(1 for p in pts if "yLow" not in p)
    assert nobar <= 1 and all(a["x"] < b["x"] for a, b in zip(pts, pts[1:])) and all(p["yLow"] <= p["y"] + 1e-6 <= p["yHigh"] + 1e-6 for p in pts if "yLow" in p), (z, nobar)
    assert all(-5 < p["y"] < -0.5 for p in pts), z
    common = dict(source="NewHorizon", relation="shmr", z=z, axes=shmr_axes, definitions=shmr_defs, citation=f"Dubois et al. 2021, A&A 651, A109 (arXiv:{ARXIV}), stellar-to-halo mass ratio versus halo mass, z={z:g}",
                  doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}", figure="stellar-to-halo mass ratio versus halo mass", panel=f"z={z:g}", sha=sha, member=pdf.name, calibration="prediction",
                  calib="x: labelled ticks of the bottom-row panels (shared by column); y: labelled ticks of the left-column panels (shared by row, offset-aware fit)")
    records.append(vf.record(
        rid=f"dubois21.newhorizon.shmr.z{z:g}", run="NewHorizon", points=pts, population="main halos (satellites not shown)", interval="uncertainty",
        warning=f"Mean M*/Mh in halo-mass bins (red solid line) with the plotted errors of the mean (red dashed lines) at z={z:g}, read from the vector paths of Dubois et al. 2021; no table exists. "
                "Halo mass is the total mass within the radius of overdensity Delta_c times the critical density, with Delta_c from Bryan and Norman 1998; satellites are connected to their subhalo mass and are not shown. "
                "Semi-empirical overlays (Moster+13, Behroozi+13) and baryon-fraction guide lines are not extracted." + (" The point without a band has none drawn." if nobar else ""), **common))
    gal.sort()
    records.append(vf.record(
        rid=f"dubois21.newhorizon.shmr-galaxies.z{z:g}", run="NewHorizon (per galaxy)", points=gal, population="individual main-halo galaxies (zoom, not volume complete)", interval="scatter", connect=False, strict=False,
        warning=f"Marker centres (orange crosses) of the simulated galaxies at z={z:g} read from the vector paths of Dubois et al. 2021; no table exists. Zoom-in region, not volume complete; main halos only.", **common))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dubois21-newhorizon.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} NewHorizon records")
