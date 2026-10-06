import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "2008.00004"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
vf.TICK_MAX = 400
vf.LABEL_MAX = 200
SIMS = {"cent": {(1.0, 0.5, 0.05): "TNG300-1", (0.12, 0.47, 0.71): "TNG100-1", (0.0, 0.6, 0.0): "TNG50-1"},
        "sat": {(1.0, 0.5, 0.31): "TNG300-1", (0.12, 0.47, 0.71): "TNG100-1", (0.0, 0.6, 0.0): "TNG50-1"}}
ZS = [(0.1, "01"), (0.35, "035"), (0.65, "065")]
DEFS = {"imf": "chabrier03", "cosmology": {"H0": 67.74, "Om": 0.3089}, "massDefinition": "aperture-2rhalf-stars", "sfrTimescaleMyr": "instantaneous (gas cells within 2 R_half)",
        "quenchingCriterion": "log10 SFR below the star-forming main sequence by 1 dex"}
AX = {"xDefinition": "log10 stellar mass (within 2 R_half)", "xUnit": "log10(Msun)", "yDefinition": "fraction of galaxies classified as quenched", "yUnit": "fraction"}


def near(c, t, tol=0.015):
    return c is not None and all(abs(a - b) < tol for a, b in zip(c, t))


records = []
for z, tag in ZS:
    for kind in ("cent", "sat"):
        pdf = SRC / "figures" / f"QF_{'Cent' if kind == 'cent' else 'Sat'}_ALL_errors_z{tag}.pdf"
        page = vf.page_of(pdf)
        sha = vf.sha256(pdf)
        fr = vf.frames(page)
        assert len(fr) == 1
        frame = fr[0]
        fx, fy, cal = vf.calibrate(page, frame)
        assert [v for _, v in cal["yTicks"]] == [1.0, 0.8, 0.6, 0.4, 0.2, 0.0] and [v for _, v in cal["xTicks"]][:3] == [9.0, 9.5, 10.0]
        words = page.get_text("words")
        assert any(w[4] == f"z={z:g}" for w in words), (z, kind)
        xlo, xhi = fx(frame.x0), fx(frame.x1)
        host = {}
        if kind == "sat":
            names = sorted((w for w in words if w[4] in ("TNG300", "TNG100", "TNG50") and w[0] > frame.x0 + 200 and w[1] > 400), key=lambda w: w[1])
            starts = sorted((w for w in words if w[4] == "(Log" and w[0] > frame.x0 + 400 and w[1] > 400), key=lambda w: w[1])
            for tw, sw in (zip(names, starts[:3]) if len(names) == 3 and len(starts) >= 3 else []):
                tok = [w for w in words if abs((w[1] + w[3]) / 2 - (sw[1] + sw[3]) / 2) < 4 and w[0] >= sw[0] and w[0] < sw[0] + 260]
                m = re.search(r"Mhost/Msun=\s*([\d.]+-[\d.]+)", " ".join(w[4] for w in sorted(tok, key=lambda w: w[0])))
                assert m, (z, kind, tw[4])
                host[tw[4]] = m.group(1)
        drs = page.get_drawings()
        for color, run in SIMS[kind].items():
            lines = [c for c in vf.curves(page, frame, fx, fy, min_items=6) if c["width"] == 6.0 and near(c["color"], color)]
            assert len(lines) == 1, (z, kind, run, len(lines))
            line = [(x, y) for x, y in lines[0]["points"] if xlo - 1e-6 <= x <= xhi + 1e-6]
            band = []
            for d in drs:
                if d["type"] == "fs" and d["fill"] is not None and near(d["fill"], color) and near(d["color"], color) and len(d["items"]) >= 18 and all(i[0] == "l" for i in d["items"]):
                    pts = [(fx(p.x), fy(p.y)) for i in d["items"] for p in (i[1], i[2])]
                    if sum(1 for x, _ in pts if any(abs(x - lx) < 0.01 for lx, _ in line)) >= 0.8 * len(pts):
                        band = pts
            assert band, (z, kind, run)
            pts = []
            for x, y in line:
                ys = [py for px, py in band if abs(px - x) < 0.01]
                assert len(ys) >= 2, (z, kind, run, x)
                pts.append({"x": round(x, 3), "y": round(y, 4), "yLow": round(min(ys), 4), "yHigh": round(max(ys), 4)})
            key = run.split("-")[0].lower()
            hostnote = (f" Satellites in hosts with log10 M200c/Msun = {host[run.split('-')[0]]} (as annotated in the figure)." if run.split("-")[0] in host else " Host-mass selection for satellites is not annotated in this panel; see the paper text.") if kind == "sat" else ""
            records.append(vf.record(
                rid=f"donnari21.{key}.quenched-{kind}.z{z:g}", source="IllustrisTNG", run=f"{run} ({'centrals' if kind == 'cent' else 'satellites'})", relation="quenched", z=z, axes=AX, points=pts,
                population="central galaxies" if kind == "cent" else "satellite galaxies in massive hosts", interval="uncertainty",
                warning=f"Curve and shaded Poisson band read from the vector paths of Donnari et al. 2021 (MNRAS 506, 4760), nominal-comparison figure, {'centrals' if kind == 'cent' else 'satellites'} at z={z:g}; no table exists. "
                        "The figure legend notes mock observational uncertainties of 0.2 dex in M* and 0.6 dex in SFR, so these are not raw catalogue fractions. Cosmic-variance hatching around TNG100 is not extracted." + hostnote,
                definitions={**DEFS, "population": "centrals" if kind == "cent" else "satellites"}, citation=f"Donnari et al. 2021, MNRAS 506, 4760, quenched fractions vs observations (QF_{'Cent' if kind == 'cent' else 'Sat'}_ALL_errors_z{tag}), z={z:g}",
                doi="10.1093/mnras/stab1950", url=f"https://arxiv.org/abs/{ARXIV}", figure=f"QF_{'Cent' if kind == 'cent' else 'Sat'}_ALL_errors_z{tag}", panel=f"z={z:g}", sha=sha,
                member=f"{pdf.name} ({run} line with Poisson band)", calib="x: labelled ticks 9-12; y: labelled ticks 0-1; both asserted", calibration="prediction"))
assert len(records) == 18
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "donnari21-tng-quenched.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} TNG50/100/300 quenched-fraction records (centrals and satellites, 3 redshifts) from Donnari+21 vector paths")
