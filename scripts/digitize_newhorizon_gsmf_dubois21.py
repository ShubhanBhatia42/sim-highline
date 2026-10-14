import json
import math
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2009.10578"
DOI = "10.1051/0004-6361/202039429"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "hsc-nh_mass_function.pdf"
SQUARE, CIRCLE = (0.68, 0.85, 0.9), (0.42, 0.35, 0.8)
OFFSET = 0.15
ZS = {0: 0.25, 1: 1.0, 2: 2.0, 3: 4.0}
close = lambda c, t, tol=0.02: c is not None and all(abs(a - b) < tol for a, b in zip(c, t))
cx = lambda w: (w[0] + w[2]) / 2
cy = lambda w: (w[1] + w[3]) / 2

page = vf.page_of(PDF)
sha = vf.sha256(PDF)
frames = vf.frames(page, 100, 100)[:4]
assert len(frames) == 4 and frames[0].x1 == frames[1].x0 and frames[0].y1 == frames[2].y0, frames
words = page.get_text("words")


def xlabels(fr):
    return [(cx(w), float(m.group(1))) for w in words for m in [re.fullmatch(r"10(\d{1,2})", w[4])] if m and fr.y1 < cy(w) < fr.y1 + 30 and fr.x0 - 3 <= cx(w) < fr.x1 - 3]


def ylabels(fr):
    out = []
    for w in words:
        if w[4] == "10" and fr.y0 + 4 <= cy(w) <= fr.y1 + 5 and fr.x0 - 60 < cx(w) < fr.x0:
            ex = [v for v in words if re.fullmatch(r"\d", v[4]) and 0 < cx(v) - w[2] < 25 and 0 < cy(w) - cy(v) < 12]
            assert len(ex) == 1, (w, ex)
            out.append((cy(w), -float(ex[0][4])))
    return out


def panel_z(fr):
    zs = [w for w in words if w[4] == "z" and fr.x0 < cx(w) < fr.x0 + 120 and fr.y0 < cy(w) < fr.y0 + 50]
    assert len(zs) == 1, fr
    row = sorted((w for w in words if abs(cy(w) - cy(zs[0])) < 2 and cx(w) > cx(zs[0]) and cx(w) < fr.x0 + 200), key=cx)
    assert row[0][4] == "=", row
    return float(row[1][4])


drawings, clips = [], []
for d in page.get_drawings(extended=True):
    if d["type"] == "clip":
        while clips and clips[-1][1] >= d["level"]:
            clips.pop()
        clips.append((d["scissor"], d["level"]))
    elif d["type"] in ("fs", "f", "s"):
        while clips and clips[-1][1] >= d["level"]:
            clips.pop()
        d["_clip"] = clips[-1][0] if clips else None
        drawings.append(d)


def shown(d):
    """Marker or bar that survives the axes clip: matplotlib keeps clipped points in the file (their clip box is empty or does not contain them)."""
    c, r = d["_clip"], d["rect"]
    if c is None:
        return True
    return c.x0 < c.x1 and c.y0 < c.y1 and c.x0 - 0.01 <= (r.x0 + r.x1) / 2 <= c.x1 + 0.01 and c.y0 - 0.01 <= (r.y0 + r.y1) / 2 <= c.y1 + 0.01


legends = [d for d in drawings if d["fill"] is not None and close(d["fill"], (1, 1, 1)) and close(d["color"], (0.8, 0.8, 0.8)) and d["rect"].width > 50]
assert len(legends) == 5, len(legends)


def in_legend(d):
    return any(d["seqno"] > g["seqno"] and g["rect"].contains(pymupdf.Point((d["rect"].x0 + d["rect"].x1) / 2, (d["rect"].y0 + d["rect"].y1) / 2)) for g in legends)


def series(fr, fx, fy, color):
    ms = sorted((d for d in drawings if d["fill"] is not None and close(d["fill"], color) and abs(d["rect"].width - 7.5) < 0.1 and abs(d["rect"].height - 7.5) < 0.1
                 and fr.contains(d["rect"]) and shown(d) and not in_legend(d)), key=lambda d: d["rect"].x0)
    bars = [(it[1].x, min(it[1].y, it[2].y), max(it[1].y, it[2].y)) for d in drawings if d["type"] == "s" and close(d["color"], color) and abs((d.get("width") or 0) - 3.0) < 0.01
            and shown(d) for it in d["items"] if it[0] == "l" and abs(it[1].x - it[2].x) < 0.01]
    pts = []
    for d in ms:
        r = d["rect"]
        mx, my = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        b = [t for t in bars if abs(t[0] - mx) < 0.3 and t[1] - 0.6 <= my <= t[2] + 0.6 and t[2] > fr.y0 and t[1] < fr.y1]
        assert len(b) == 1, (mx, my, b)
        _, top, bottom = b[0]
        p = {"x": fx(mx), "y": fy(my)}
        if top >= fr.y0 - 0.5:
            p["yHigh"] = fy(top)
        if bottom <= fr.y1 + 0.5:
            p["yLow"] = fy(bottom)
        pts.append(p)
    return pts


AX = {"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 galaxy stellar mass function, dN/dlog10(M) (axis label phi in cMpc^-3 dex^-1)", "yUnit": "log10(cMpc^-3 dex^-1)"}
DEF = {"imf": "chabrier03", "cosmology": {"H0": 70.4, "Om": 0.272}, "massDefinition": "unspecified", "densityFrame": "comoving", "population": "all"}
VOLUME = ("Normalised by the initial zoom-in volume, (16 Mpc)^3; the paper states that volume-integrated quantities are therefore lower limits that could be a few tens of per cent higher. "
          "Poisson error bars as plotted: where a bar runs off the bottom of the axis its lower end is not recorded, and where the recorded lower end equals the value the figure draws no lower error. Observational overlays (HSC-SSP, literature compilations) are not extracted.")
records = []
for k, fr in enumerate(frames):
    z = panel_z(fr)
    assert z == ZS[k], (k, z)
    bot = frames[2 + k % 2]
    fx, xt = vf.axis_fit_log2(page, fr, "x", xlabels(bot))
    fy, yt = vf.axis_fit_log2(page, fr, "y", ylabels(frames[0] if k < 2 else frames[2]), snap=7.0)
    sq, ci = series(fr, fx, fy, SQUARE), series(fr, fx, fy, CIRCLE)
    assert len(sq) == len(ci) >= 5 and all(abs(a["x"] - b["x"] - OFFSET) < 0.002 for a, b in zip(sq, ci)), (z, len(sq), len(ci))
    for a in sq:
        a["x"] -= OFFSET
    calib = "x: labelled decades 10^7 to 10^11 of the bottom frame of the panel column; y: labelled decades 10^-5 to 10^-1 of the left frame of the panel row; both validated by the minor-tick pattern"
    common = dict(source="NewHorizon", relation="gsmf", z=z, axes=AX, citation=f"Dubois et al. 2021, A&A 651, A109 (arXiv:{ARXIV}), galaxy stellar mass function, z={z:g}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
                  figure="galaxy stellar mass function (hsc-nh_mass_function)", panel=f"z={z:g}", sha=sha, member=PDF.name, calibration="prediction", calib=calib, interval="uncertainty", retrieved="2026-10-14")
    for tag, run, pts, pop, what in (
            ("gsmf-raw", "NewHorizon (all galaxies)", sq, "all galaxies in the zoom region, including those in halos contaminated by low-resolution particles",
             f"Light blue squares (all galaxies, Poisson errors). The figure draws them offset by {OFFSET} dex in mass for legibility; the offset is removed here, which puts every square on the bin centre of the circle of the same bin."),
            ("gsmf-uncontaminated", "NewHorizon (uncontaminated halos)", ci, "galaxies in halos not contaminated by low-resolution particles; mass function divided by the fraction of uncontaminated galaxies",
             "Purple circles (only galaxies whose halos are not contaminated by low-resolution particles; the mass function is divided by the fraction of uncontaminated galaxies to account for the smaller effective volume).")):
        assert all(a["x"] < b["x"] for a, b in zip(pts, pts[1:]))
        pts = [{kk: round(v, 3 if kk == "x" else 4) for kk, v in p.items()} for p in pts]
        records.append(vf.record(rid=f"dubois21.newhorizon.{tag}.z{z:g}", run=run, points=pts, population=pop, definitions=dict(DEF),
                                 warning=f"Galaxy stellar mass function at z={z:g} read from the marker and error-bar vector paths of Dubois et al. 2021 (figure of the mass function; the caption describes z=0.25 only, the file has four panels); no table exists. {what} {VOLUME}", **common))
    if z == 0.25:
        sty = [c for c in vf.curves(page, fr, fx, fy, min_items=20) if close(c["color"], CIRCLE) and abs((c["width"] or 0) - 8.0) < 0.01 and c["dashes"] and c["dashes"].startswith("[ 8")]
        assert len(sty) == 1, len(sty)
        pts = vf.clip(sty[0]["points"], 7.0, 12.0, -5.0, 0.0)
        pts = [(round(x, 3), round(y, 4)) for x, y in pts]
        assert all(a[0] < b[0] for a, b in zip(pts, pts[1:])) and len(pts) > 10
        assert pts[0][0] == 8.3 and pts[1][0] == 8.8 and all(abs(x * 10 - round(x * 10)) < 0.01 for x, _ in pts), pts[:3]
        records.append(vf.record(
            rid="dubois21.newhorizon.gsmf-sty-hsc.z0.25", run="NewHorizon (STY, HSC-like selection)", points=pts, population="mock-observed galaxies: selected by effective surface brightness with the HSC-SSP completeness and an r-band cut of 26 mag, Sandage-Tammann-Yahil estimator",
            definitions=dict(DEF), connect=True, strict=True,
            warning="Thick purple dotted line of Dubois et al. 2021 (z=0.25 panel): the NewHorizon mass function constructed with the Sandage-Tammann-Yahil (STY) method after applying a surface-brightness selection that mimics the HSC-SSP deep layer and an r < 26 cut "
                    "(masses from LePhare SED fits of dust-attenuated mock g, r, i, z magnitudes of HOP galaxies, with the knee fixed). It is a mock-observed estimator, not the binned count of the raw simulation, so it is kept as its own run and should be compared with survey mass functions rather than with the binned curves. "
                    "No table exists. The line is a coarse polyline whose vertices sit on a 0.1 dex grid (24 inside the plotted range); its first vertex lies left of the plot (log M about 5.95), so the stretch from the left edge of the plot to log M = 8.3 is not recorded. The HSC-SSP curve it is compared with is not extracted.",
            **common))
    print(f"z={z:g}: {len(sq)} bins, calibration {len(xt)} x labels, {len(yt)} y labels")

for rid, x, y in (("dubois21.newhorizon.gsmf-uncontaminated.z0.25", 7.227, -1.127), ("dubois21.newhorizon.gsmf-uncontaminated.z1", 7.227, -0.958)):
    p = next(r for r in records if r["id"] == rid)["representation"]["points"][0]
    assert abs(p["x"] - x) < 0.005 and abs(p["y"] - y) < 0.005, (rid, p)
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dubois21-newhorizon-gsmf.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} NewHorizon galaxy stellar mass function records from Dubois+21 vector paths")
