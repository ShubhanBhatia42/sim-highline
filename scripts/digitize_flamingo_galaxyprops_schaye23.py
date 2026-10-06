import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2306.04024"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "Images" / "galaxy_props_z01.pdf"
RUNS = {(0.07, 0.47, 0.2): ("l1_m9", "L1_m9"), (0.2, 0.13, 0.53): ("l2p8_m9", "L2p8_m9"), (0.87, 0.8, 0.47): ("l1_m10", "L1_m10"), (0.8, 0.4, 0.47): ("l1_m8", "L1_m8")}
DEF = {"imf": "chabrier03", "cosmology": {"H0": 68.1, "Om": 0.306}, "massDefinition": "aperture-50pkpc"}
NOTE = " Solid segment only, above the resolution-dependent limit (dotted below it is omitted); the L2p8_m9 16th-84th percentile shading is not extracted. The paper gives no table and does not state whether the 0.3 dex mock stellar-mass scatter of its SMF figure is applied to these panels."
ROWS = [
    dict(row=0, rel="ssfr", z=0.1, log=True, shift=-9.0, tag="ssfr-active", pop="active galaxies (sSFR > 1e-2 /Gyr)",
         ydef="log10 median specific SFR of active galaxies (converted from /Gyr to /yr)", yunit="log10(1/yr)", extra={"sfrTimescaleMyr": "instantaneous", "sfrStatistic": "median", "population": "active"}),
    dict(row=1, rel="quenched", z=0.0, log=False, shift=0.0, tag="passive", pop="all galaxies",
         ydef="passive fraction (sSFR < 1e-2 /Gyr), at z=0", yunit="fraction", extra={"quenchingCriterion": "ssfr<1e-11", "population": "all"}),
    dict(row=2, rel="zstar", z=0.1, log=True, shift=0.0, tag="zstar", pop="all galaxies",
         ydef="log10 stellar metallicity Z*/Zsun (median)", yunit="log10(Z/Zsun)", extra={"metallicityQuantity": "stellar-Z", "metallicityCalibration": "intrinsic-simulation", "population": "all"}),
    dict(row=3, rel="size", z=0.1, log=True, shift=0.0, tag="size-active", pop="active galaxies", ydef="log10 projected stellar half-mass radius R_1/2 (median, kpc), 2D aperture", yunit="log10(kpc)",
         extra={"sizeDefinition": "stellar-half-mass-projected", "population": "active"}),
    dict(row=4, rel="size", z=0.1, log=True, shift=0.0, tag="size-passive", pop="passive galaxies", ydef="log10 projected stellar half-mass radius R_1/2 (median, kpc), 2D aperture", yunit="log10(kpc)",
         extra={"sizeDefinition": "stellar-half-mass-projected", "population": "passive"}),
]


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


def explabels(words, f, axis):
    out = []
    for w in words:
        m = re.fullmatch(r"10([−-]?\d{1,2})", w[4])
        if not m:
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        e = float(m.group(1).replace("−", "-"))
        if axis == "x" and w[1] > f.y1 and f.x0 - 3 < cx < f.x1 + 3:
            out.append((cx, e))
        if axis == "y" and w[0] < f.x0 and f.y0 - 3 < cy < f.y1 + 3:
            out.append((cy, e))
    return sorted(out)


page = vf.page_of(PDF)
sha = vf.sha256(PDF)
fr = vf.frames(page)
assert len(fr) == 10
words = page.get_text("words")
fx, xt = vf.axis_fit_log2(page, fr[8], "x", explabels(words, fr[8], "x"))
assert [e for _, e in xt][:1] == [9.0] and xt[-1][1] == 12.0, xt
records = []
for cfg in ROWS:
    frame = fr[2 * cfg["row"]]
    if cfg["log"]:
        fy, yt = vf.axis_fit_log2(page, frame, "y", explabels(words, frame, "y"))
    else:
        nums = [((w[1] + w[3]) / 2, float(w[4])) for w in words if re.fullmatch(r"\d\.\d", w[4]) and w[0] < frame.x0 and frame.y0 - 3 < (w[1] + w[3]) / 2 < frame.y1 + 3]
        fy, yt = vf.axis_fit(page, frame, "y", labels=nums)
        assert [v for _, v in yt] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0], yt
    xlo, xhi = fx(frame.x0), fx(frame.x1)
    curves = [c for c in vf.curves(page, frame, fx, fy, min_items=8) if c["width"] == 1.5]
    for dsh, ap in (("[] 0", "50"), ("[ 5.55 2.4 ] 0", "100")):
        if ap == "100" and cfg["rel"] != "size":
            continue
        seen = {}
        for c in curves:
            run = next((v for k, v in RUNS.items() if near(c["color"], k)), None)
            if run is None or c["dashes"] != dsh:
                continue
            pts = [(x, y + cfg["shift"]) for x, y in c["points"] if xlo <= x <= xhi]
            if cfg["rel"] == "quenched":
                assert all(-0.01 <= y <= 1.01 for _, y in pts), run
            if len(pts) < 6:
                continue
            assert run[0] not in seen and all(a[0] < b[0] for a, b in zip(pts, pts[1:])), (cfg["tag"], run[0], dsh)
            seen[run[0]] = (pts, run[1])
        assert len(seen) >= 3, (cfg["tag"], dsh, sorted(seen))
        for rk, (pts, rname) in sorted(seen.items()):
            tag = cfg["tag"] + (f"-ap{ap}" if cfg["rel"] == "size" else "")
            records.append(vf.record(
                rid=f"schaye23.flamingo-{rk}.{tag}.z{cfg['z']:g}", source="FLAMINGO", run=f"{rname} ({cfg['tag'].split('-')[-1] if cfg['rel'] == 'size' else cfg['rel']}" + (f", {ap} kpc 2D aperture" if cfg["rel"] == "size" else "") + ")", relation=cfg["rel"], z=cfg["z"],
                axes={"xDefinition": "log10 stellar mass (3D 50 pkpc aperture)", "xUnit": "log10(Msun)", "yDefinition": cfg["ydef"], "yUnit": cfg["yunit"]},
                points=pts, population=cfg["pop"],
                warning=f"Median curve read from the vector paths of Schaye et al. 2023 (MNRAS 526, 4978), galaxy-properties figure (galaxy_props_z01; arXiv source numbering), left column, {cfg['tag']} row, z={cfg['z']:g}."
                        + (f" Half-mass radii are projected, computed within a {ap} kpc 2D aperture ({'solid' if ap == '50' else 'dashed'} curves)." if cfg["rel"] == "size" else "") + NOTE,
                definitions={**DEF, **cfg["extra"]}, citation=f"Schaye et al. 2023, MNRAS 526, 4978, galaxy-properties figure (galaxy_props_z01), {cfg['tag']}", doi="10.1093/mnras/stad2419", url=f"https://arxiv.org/abs/{ARXIV}",
                figure="galaxy_props_z01 (fig:gal_props)", panel=f"left column, {cfg['tag']}", sha=sha, member=f"Images/{PDF.name} ({rname} curve)",
                calib="x: labelled decades 10^9-10^12 (log, validated by the minor-tick pattern); y: labelled ticks/decades per row (log rows validated by minor ticks)", calibration="prediction"))
assert len(records) >= 24, len(records)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "schaye23-flamingo-galaxyprops.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} FLAMINGO galaxy-property records (sSFR, passive fraction, stellar Z, active/passive sizes) from Schaye+23 vector paths")
