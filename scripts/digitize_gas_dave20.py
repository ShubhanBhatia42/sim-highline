import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2002.07226"
DOI = "10.1093/mnras/staa1894"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
pdf = SRC / "gass_median_m100n1024.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
fs = vf.frames(page, 100, 100)
assert len(fs) == 9
fx, xt = vf.axis_fit(page, fs[6], "x")


def panel_y(frame):
    ws = sorted(((w[1] + w[3]) / 2, w[4]) for w in page.get_text("words") if 30 < (w[0] + w[2]) / 2 < frame.x0 and frame.y0 - 2 <= (w[1] + w[3]) / 2 <= frame.y1 + 2 and vf.number(w[4]) is not None)
    zero = [i for i, (_, t) in enumerate(ws) if float(t) == 0.0]
    assert len(zero) == 1 or (len(zero) == 0 and False)
    z = zero[0]
    lab = [(cy, 0.0 if i == z else (abs(float(t)) if i < z else -abs(float(t)))) for i, (cy, t) in enumerate(ws)]
    f, t = vf.axis_fit(page, frame, "y", labels=lab)
    return f, t


RUNS = {
    ((0.0, 0.0, 1.0), "[] 0"): ("SIMBA", "m100n1024 (all galaxies, Dave+20)", {"H0": 68.0, "Om": 0.3}, "on-the-fly Rahmati+13 self-shielding and Krumholz & Gnedin 2011 H2; all halo cold gas assigned to the most dynamically important galaxy (6D FOF galaxies)", "FOF"),
    ((0.86, 0.08, 0.24), "[] 0"): ("IllustrisTNG", "TNG100-1 (all galaxies, Dave+20)", {"H0": 67.74, "Om": 0.3089}, "post-processed Rahmati+13 and Gnedin & Kravtsov-type H2 following Stevens+19; BaryMP aperture of Stevens+14 (20-70 kpc)", "Subfind"),
    ((0.0, 0.5, 0.0), "[] 0"): ("EAGLE", "Ref-L100N1504 (all galaxies, Dave+20)", {"H0": 67.77, "Om": 0.307}, "post-processed Rahmati+13 and Gnedin & Kravtsov 2011 H2 following Crain+17; fixed 70 kpc aperture, bound gas only", "Subfind"),
    ((0.0, 0.5, 0.0), "[ 5.55 2.4 ] 0"): ("EAGLE", "Recal-L025N0752 (all galaxies, Dave+20)", {"H0": 67.77, "Om": 0.307}, "post-processed Rahmati+13 and Gnedin & Kravtsov 2011 H2 following Crain+17; fixed 70 kpc aperture, bound gas only; 8x better mass resolution", "Subfind"),
}
REL = {0: ("hi-fraction", "HI", "log10 median HI-to-stellar mass fraction", 0.0), 3: ("h2-fraction", "H2", "log10 median H2-to-stellar mass fraction", 0.0)}
CHECK = {("hi-fraction", "SIMBA"): ((9.2, -0.3, 0.6), (11.2, -1.8, -1.0)), ("h2-fraction", "IllustrisTNG"): ((11.0, -1.6, -1.1),)}
records = []
for fi, (rel, species, ydef, _) in REL.items():
    fy, yt = panel_y(fs[fi])
    cs = vf.curves(page, fs[fi], fx, fy, min_items=15)
    for (col, dash), (src, run, cosmo, method, halo) in RUNS.items():
        c = [k for k in cs if k["color"] == col and k["dashes"] == dash and k["opacity"] in (None, 1.0)]
        assert len(c) == 1, (rel, run, len(c))
        pts = vf.clip(c[0]["points"], 8.9, 12.6, -4, 2)
        pts = [p for i, p in enumerate(pts) if i == 0 or p[0] > pts[i - 1][0] + 1e-6]
        assert len(pts) >= 10 and pts[0][0] < 9.6 and pts[-1][0] > 10.5, (rel, run, pts[0], pts[-1])
        for (xa, lo, hi) in CHECK.get((rel, src), []):
            yv = min(pts, key=lambda p: abs(p[0] - xa))[1]
            assert lo < yv < hi, (rel, run, xa, yv)
        zrep = 0.0
        records.append(vf.record(
            rid=f"dave20.{src.lower().replace(' ', '')}.{rel}.{run.split(' ')[0].lower()}.z0", source=src, run=run, relation=rel, z=zrep,
            axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": ydef, "yUnit": "dex"},
            points=pts, population="all galaxies (running median in equal-number bins)", interval="unspecified",
            definitions={"gasDefinition": species, "gasMethod": method, "gasStatistic": "median", "massDefinition": "unspecified", "haloMassDefinition": halo, "population": "all", "imf": "unspecified", "cosmology": cosmo},
            citation=f"Dave et al. 2020, MNRAS 497, 146 (arXiv:{ARXIV}), gas fraction scaling relations at z=0", doi=DOI, url=f"https://arxiv.org/abs/{ARXIV}",
            figure="Gas fraction scaling relations at z=0", panel=f"{species}/M* versus M* (left column)", sha=sha, member="gass_median_m100n1024.pdf", calibration="prediction",
            calib="x: numeric tick labels (bottom row) snapped to ticks; y: tick labels with signs assigned from the 0.0 label (minus signs are separate glyphs), per panel",
            warning=f"Running median {species} to stellar mass ratio of {run} at z=0, read from the vector paths of Dave et al. 2020. The code-specific apertures and HI/H2 models differ ({method}), so offsets between codes partly reflect those choices, as the paper stresses for HI. The 16-84% band (SIMBA only) and the observational points are not extracted."))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "dave20-gas-fractions.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} cold gas fraction records from Dave+20")
