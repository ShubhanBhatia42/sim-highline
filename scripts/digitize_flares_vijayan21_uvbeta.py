"""FLARES II (Vijayan et al. 2021, MNRAS 501, 3289; arXiv:2008.06057): the weighted median UV continuum slope against M_1500 at z = 5 to 10 with the weighted 16th to 84th percentile band, read from the vector figure
figures/beta_lum_z5_10.pdf (relation uvbeta; 6 records). Only the solid part of the median line is read (the bins with more than 5 galaxies: the paper's caption says "We only plot bins with more than 5 data points"; the dashed continuation is the
bins with fewer). The paper gives no wavelength window for beta, so betaWindow is unspecified.
The y labels of this figure sit 4.4 pt below their major ticks, so each axis is calibrated from its major tick marks (equally spaced, with the values taken from the numeric labels in order), not by snapping labels to the nearest tick.
Checks inside this script (every assert must pass or nothing is written): the observed points drawn in the panels (Bouwens et al. 2012 squares, Bouwens et al. 2014 diamonds) fall at the x of the dataset's own records of those papers and at their y values to 0.02 (two markers per panel have no record point and are not used);
every median vertex lies inside its band; and the z = 10 median agrees with the FLARES V curve of the same redshift (scripts/digitize_flares_wilkins22_uvbeta.py, data/curves/wilkins22-flares-uvbeta.json) where the two overlap.
Usage: python3 scripts/digitize_flares_vijayan21_uvbeta.py [SOURCE_DIR]   (writes data/curves/vijayan21-flares-uvbeta.json)"""
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ARXIV = "2008.06057"
DOI = "10.1093/mnras/staa3715"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
ROOT = Path(__file__).resolve().parent.parent
REF = vf.reference_root()
OUT = ROOT / "data" / "curves" / "vijayan21-flares-uvbeta.json"
pdf = SRC / "figures" / "beta_lum_z5_10.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
frames = vf.frames(page, 100, 100)
assert len(frames) == 6
checks = []


def check(cond, msg):
    assert cond, msg
    checks.append(msg)


# ---------------------------------------------------------------- definitions, each from a sentence of the paper
norm = lambda a: re.sub(r"\s+", " ", a).strip()
log = []


def quote(s):
    for f in sorted(SRC.glob("*.tex")):
        flat, idx = "", []
        for n, l in enumerate(f.read_text(errors="replace").splitlines(), 1):
            flat += norm(l) + " "
            idx += [n] * (len(norm(l)) + 1)
        k = flat.find(norm(s))
        if k >= 0:
            log.append(f"{f.name}:{idx[k]}: {norm(s)}")
            return f"{f.name}:{idx[k]}"
    raise AssertionError("quote not found: " + s[:80])


Q = {
    "beta": quote(r"The UV continuum slope $\beta$, defined such that f$_{\lambda}\,\propto\,\lambda^{\beta}$ \citep{Calzetti1994}, is commonly used as a tracer of the stellar continuum attenuation."),
    "caption": quote(r"UV continuum slope, $\beta$, against the UV magnitude for $z\in[5,10]$. The solid dashed line is the weighted median of the sample, with the shaded region indicating the weighted  84$^{\text{th}}$ and 16$^{\text{th}}$ percentiles."),
    "bins": quote(r"We only plot bins with more than 5 data points."),
    "observed_comparison": quote(r"Our weighted median of $\beta$'s  match observational values for almost all luminosities."),
    "extinction": quote(r"We find that the \flares\, galaxies prefer a steeper extinction curve similar to the SMC in order to reproduce UV continuum observations."),
    "imf_sps": quote(r"Throughout this work we utilise v2.2.1 of the Binary Population and Spectral Synthesis (BPASS) stellar population synthesis (SPS) models \citep{BPASS2.2.1} and assume a Chabrier initial mass function (IMF) throughout"),
    "curve": quote(r"This functional form yields an extinction curve flatter in the UV than the Small Magellanic Cloud curve \citep{Pei1992}, but not as flat as the \cite{Calzetti2000} curve."),
}


# ---------------------------------------------------------------- axes: major ticks, equally spaced, with the values of the numeric labels in order
def major_ticks(frame, axis):
    out = set()
    for d in page.get_drawings():
        if len(d["items"]) != 1 or d["items"][0][0] != "l":
            continue
        a, b = d["items"][0][1], d["items"][0][2]
        if axis == "x" and abs(a.x - b.x) < 0.01 and abs(abs(a.y - b.y) - 3.5) < 0.3 and abs(min(a.y, b.y) - frame.y1) < 0.6 and frame.x0 - 0.3 <= a.x <= frame.x1 + 0.3:
            out.add(round(a.x, 2))
        if axis == "y" and abs(a.y - b.y) < 0.01 and abs(abs(a.x - b.x) - 3.5) < 0.3 and abs(max(a.x, b.x) - frame.x0) < 0.6 and frame.y0 - 0.3 <= a.y <= frame.y1 - 0.5:  # the lower edge of a panel is the upper edge of the next row
            out.add(round(a.y, 2))
    return sorted(out)


def labels(frame, axis):
    out = []
    for w in page.get_text("words"):
        v = vf.number(w[4])
        if v is None:
            continue
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if axis == "x" and frame.x0 - 2 <= cx <= frame.x1 + 2 and 0 < cy - frame.y1 < 20:
            out.append((cx, v))
        if axis == "y" and frame.y0 <= cy <= frame.y1 and 0 < frame.x0 - cx < 40:
            out.append((cy, v))
    return [v for _, v in sorted(out)]


class Axis:
    def __init__(self, majors, values):
        assert len(majors) == len(values), (len(majors), values)
        n = len(majors)
        mp, mv = sum(majors) / n, sum(values) / n
        self.slope = sum((p - mp) * (v - mv) for p, v in zip(majors, values)) / sum((p - mp) ** 2 for p in majors)
        self.icpt = mv - self.slope * mp
        self.resid = max(abs(self.val(p) - v) for p, v in zip(majors, values)) / abs(self.slope)
        assert self.resid < 0.1, ("major ticks are not equally spaced", self.resid)
        self.majors, self.values = majors, values

    def val(self, p):
        return self.icpt + self.slope * p


AXX = [Axis(major_ticks(frames[3 + j], "x"), labels(frames[3 + j], "x")) for j in range(3)]
AXY = [Axis(major_ticks(frames[0], "y"), labels(frames[0], "y")), Axis(major_ticks(frames[3], "y"), labels(frames[3], "y"))]
assert all(a.values == [-17.0 - i for i in range(8)] for a in AXX), [a.values for a in AXX]
assert all(a.values == [-1.4 - 0.2 * i for i in range(7)] or all(abs(v - (-1.4 - 0.2 * i)) < 1e-9 for i, v in enumerate(a.values)) for a in AXY)
check(abs(AXY[0].val(frames[0].y0) + 1.4) < 0.01 and abs(AXY[1].val(frames[3].y0) + 1.4) < 0.01, "the top edge of each row is the major tick of beta = -1.4 (the label of -1.4 stands on it in the rendered figure)")
check(abs(AXX[0].slope - AXX[1].slope) < 1e-6 and abs(AXX[0].slope - AXX[2].slope) < 1e-6, f"the three columns have the same x scale ({1 / abs(AXX[0].slope):.2f} pt per mag); both rows the same y scale ({1 / abs(AXY[0].slope):.2f} pt per unit of beta)")

# ---------------------------------------------------------------- the median, the band and the drawn observations of each panel
bouwens = {}
for fn in ("uvbeta-bouwens12-14",):
    for r in json.loads((REF / "data" / "curves" / f"{fn}.json").read_text())["records"]:
        bouwens[r["id"]] = r
BREC = {5: ("bouwens12.uvbeta.z5", "bouwens14.uvbeta.z5"), 6: ("bouwens12.uvbeta.z6", "bouwens14.uvbeta.z6"), 7: ("bouwens12.uvbeta.z7", "bouwens14.uvbeta.z7"), 8: (None, "bouwens14.uvbeta.z8")}
panels = {}
n_match, n_off, worst = 0, 0, 0.0
for i, fr in enumerate(frames):
    z = 5 + i
    ax, ay = AXX[i % 3], AXY[i // 3]
    inside = lambda r: fr.x0 <= (r.x0 + r.x1) / 2 <= fr.x1 and fr.y0 <= (r.y0 + r.y1) / 2 <= fr.y1
    med = [d for d in page.get_drawings() if d["type"] == "s" and d["color"] is not None and max(d["color"]) < 0.1 and abs((d.get("width") or 0) - 2.0) < 0.05 and d["dashes"] == "[] 0" and len(d["items"]) >= 5 and inside(d["rect"])]
    band = [d for d in page.get_drawings() if d["type"] == "fs" and d["fill"] == (0.0, 0.0, 0.0) and abs((d.get("fill_opacity") or 0) - 0.5) < 0.01 and len(d["items"]) >= 15 and inside(d["rect"])]
    assert len(med) == 1 and len(band) == 1, (z, len(med), len(band))
    mp = [med[0]["items"][0][1]] + [it[2] for it in med[0]["items"]]
    bp = []
    for it in band[0]["items"]:
        if it[0] == "l":
            bp += [it[1], it[2]]
    pts = []
    for p in mp:
        v = [q for q in bp if abs(q.x - p.x) < 0.3]
        ys = sorted({round(q.y, 2) for q in v})
        assert len(ys) >= 2, (z, p)
        top, bot = ys[0], ys[-1]  # page y grows downward: the smaller y is the higher beta
        assert top - 0.01 <= p.y <= bot + 0.01, (z, "median outside the band", top, p.y, bot)
        pts.append({"x": round(ax.val(p.x), 3), "y": round(ay.val(p.y), 4), "yLow": round(ay.val(bot), 4), "yHigh": round(ay.val(top), 4)})
    assert all(a["x"] != b["x"] for a, b in zip(sorted(pts, key=lambda q: q["x"]), sorted(pts, key=lambda q: q["x"])[1:])), (z, [q["x"] for q in pts])
    pts = sorted(pts, key=lambda q: q["x"])
    panels[z] = pts
    # the observed points drawn in the panel
    for d in page.get_drawings():
        if d["type"] == "fs" and d["fill"] is not None and d["fill"][2] > 0.9 and d["fill"][0] < 0.1 and len(d["items"]) in (1, 4) and inside(d["rect"]):
            r = d["rect"]
            x, y = ax.val((r.x0 + r.x1) / 2), ay.val((r.y0 + r.y1) / 2)
            rid = BREC[z][0 if len(d["items"]) == 1 else 1]
            hit = [p for p in bouwens[rid]["representation"]["points"] if abs(p["x"] - x) < 0.01] if rid else []
            if hit:
                dy = abs(hit[0]["y"] - y)
                worst = max(worst, dy)
                assert dy < 0.02, (z, rid, x, y, hit[0])
                n_match += 1
            else:
                n_off += 1
check(n_match >= 30 and worst < 0.02, f"the drawn Bouwens et al. 2012 and 2014 points of the panels z = 5 to 8 sit at the x of the dataset's own records of those papers and within {worst:.3f} in beta of their y values ({n_match} markers; {n_off} markers have no record point and are not used)")
check(all(len(p) >= 8 for p in panels.values()), "median vertices per panel: " + ", ".join(f"z={z}: {len(p)}" for z, p in panels.items()))
check(all(p["yLow"] <= p["y"] <= p["yHigh"] for pts in panels.values() for p in pts), "every median vertex lies inside its 16th to 84th percentile band")
# FLARES V, same redshift, same simulation: the dust-attenuated curve of the other paper
v = {r["id"]: r for r in json.loads((REF / "data" / "curves" / "wilkins22-flares-uvbeta.json").read_text())["records"]}["wilkins22.flares.uvbeta.dust.z10"]["representation"]["points"]
xs5, ys5 = [p["x"] for p in v], [p["y"] for p in v]
diffs = [p["y"] - float(np.interp(p["x"], xs5, ys5)) for p in panels[10] if xs5[0] <= p["x"] <= xs5[-1]]
check(len(diffs) >= 2 and max(abs(d) for d in diffs) < 0.25, f"z = 10 median against the FLARES V dust-attenuated curve of the same redshift: {len(diffs)} overlapping vertices, differences {min(diffs):+.2f} to {max(diffs):+.2f} in beta (two papers, one simulation; the paper-to-paper agreement is not a check of the axes alone)")

records = []
for z, pts in panels.items():
    records.append(vf.record(
        rid=f"vijayan21.flares.uvbeta.z{z}", source="FLARES", run="40 resimulated regions (EAGLE AGNdT9 model), dust attenuated, weighted median", relation="uvbeta", z=float(z),
        axes={"xDefinition": "absolute UV magnitude M_1500 (the paper's x axis; dust attenuated, as the figure compares it with observed values)", "xUnit": "mag (AB)",
              "yDefinition": "UV-continuum slope beta, f_lambda ~ lambda^beta (weighted median of the galaxies in the M_1500 bin; band: weighted 16th to 84th percentile)", "yUnit": "dimensionless"},
        points=pts, population="all FLARES galaxies of the 40 resimulated regions in the bins with more than 5 galaxies, weighted combination",
        warning=(f"Weighted median beta of FLARES galaxies at z = {z} against M_1500, with the weighted 16th to 84th percentile band, read from the vector paths of Vijayan et al. 2021. Only the solid part of the line is read (bins with more than 5 galaxies); the dashed continuation to brighter bins with fewer galaxies is not. "
                 "The paper gives no wavelength window or fitting method for beta (both unspecified) and does not say that the M_1500 axis is dust attenuated; it is read as attenuated because the figure is compared with observed galaxies. The extinction curve is the paper's own power-law form (flatter in the UV than SMC, steeper than Calzetti), the model is tuned to the z = 5 UV luminosity function."),
        definitions={"betaWindow": "unspecified", "dustTreatment": "attenuated", "dustModel": "two-component line-of-sight dust model of the paper (ISM dust from the metal surface density along the line of sight plus birth-cloud dust; extinction curve flatter in the UV than SMC, steeper than Calzetti)",
                     "betaMethod": "unspecified", "stellarPopulation": "BPASS v2.2.1 with nebular emission", "imf": "chabrier03", "cosmology": {"H0": 67.77, "Om": 0.307}, "xVariable": "M_UV (M_1500)", "uvBand": "rest-frame 1500 A", "statistic": "weighted median", "population": "all galaxies of the resimulated regions"},
        citation=f"Vijayan et al. 2021, MNRAS 501, 3289 (arXiv:{ARXIV}), UV continuum slope against UV magnitude, z={z}", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
        figure="UV continuum slope against the UV magnitude for z = 5 to 10", panel=f"z={z}, weighted median (solid line) with weighted 16th-84th percentile band", sha=sha, member="figures/beta_lum_z5_10.pdf", calibration="prediction",
        calib={"xMajorTicks": [[round(p, 2), v] for p, v in zip(AXX[(z - 5) % 3].majors, AXX[(z - 5) % 3].values)], "yMajorTicks": [[round(p, 2), round(v, 2)] for p, v in zip(AXY[(z - 5) // 3].majors, AXY[(z - 5) // 3].values)],
               "labels": "numeric tick labels read from the text layer, assigned to the major ticks in order (the y labels sit 4.4 pt below their ticks)"},
        interval="scatter", scatter={"lower": "weighted 16th percentile", "upper": "weighted 84th percentile"}, uncertainty=0.02, retrieved="2026-10-25",
        note="Vector-path extraction; exact to PDF coordinate precision. Checks: " + "; ".join(checks) + "."))
    records[-1]["provenance"]["quotes"] = dict(Q)
    records[-1]["provenance"]["definitionBasis"] = ("beta: 'defined such that f_lambda is proportional to lambda^beta'; the wavelength window and the fitting method are not stated. dustTreatment: read, not stated: the paper compares this curve with observed beta and discusses how the extinction curve changes it. "
                                                    "imf: 'we assume a Chabrier initial mass function'. cosmology: as in the other FLARES records of this dataset.")
assert len(records) == 6
OUT.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} records; {len(checks)} checks passed:")
for c in checks:
    print("  -", c)
