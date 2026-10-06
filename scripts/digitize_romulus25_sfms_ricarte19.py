import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1904.10116"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
PDF = SRC / "sfms.pdf"
ZS = [0.05, 1.0, 3.0]
CLASSES = {"all": (0.7, 0.13, 0.13), "gt43": (0.25, 0.41, 0.88), "gt45": (0.0, 0.81, 0.82)}
page = vf.page_of(PDF)
sha = vf.sha256(PDF)
frames = [r for r in vf.frames(page) if abs(r.width - 164) < 3 and abs(r.height - 150) < 3]
assert len(frames) == 6
top, bottom = frames[:3], frames[3:]
words = page.get_text("words")
# y labels: split base/exponent words; the minus signs are lost, exponents must increase upward
f0 = top[0]
ys = []
for w in words:
    cy = (w[1] + w[3]) / 2
    if w[0] < f0.x0 and f0.y0 - 3 < cy < f0.y1 + 3:
        if w[4] == "10":
            ex = next(x for x in words if re.fullmatch(r"\d", x[4]) and abs((x[1] + x[3]) / 2 - cy) < 5 and x[0] > w[2] - 1 and x[0] < w[2] + 25)
            ys.append((cy, -float(ex[4])))
        elif re.fullmatch(r"10\d", w[4]):
            ys.append((cy, float(w[4][2:])))
ys.sort(reverse=True)
assert [v for _, v in ys] == [-4.0, -2.0, 0.0, 2.0], ys
fy, yt = vf.axis_fit_shifted(page, f0, "y", ys)
records = []
for i, (z, fr) in enumerate(zip(ZS, top)):
    assert any(w[4] == f"z={z:.2f}" or w[4] == f"z={z:.2f}".replace(".00", ".00") for w in words if fr.x0 <= w[0] <= fr.x1 and w[1] < fr.y0 + 20), z
    bf = bottom[i]
    cand = sorted(((w[0] + w[2]) / 2) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[1] > bf.y1 and bf.x0 - 2 < (w[0] + w[2]) / 2 < bf.x1 + 2 and (i == 2 or (w[0] + w[2]) / 2 < bf.x1 - 3))
    assert len(cand) == (5 if i == 2 else 4) and abs(cand[0] - bf.x0) < 2.5, (i, cand)
    xl = [(c, 8.0 + k) for k, c in enumerate(cand)]
    fx, xt = vf.axis_fit_log2(page, bf, "x", sorted(xl))
    assert len(xt) >= 3, xt
    xlo, xhi, ylo, yhi = fx(fr.x0), fx(fr.x1), min(fy(fr.y0), fy(fr.y1)), max(fy(fr.y0), fy(fr.y1))
    pts = []
    for color in CLASSES.values():
        pts += vf.markers(page, fr, fx, fy, color, max_size=3.6, min_size=2.4)
    keep = []
    for p in sorted(pts):
        if not (xlo <= p[0] <= xhi and ylo <= p[1] <= yhi):
            continue
        if keep and abs(p[0] - keep[-1][0]) < 1e-3 and abs(p[1] - keep[-1][1]) < 1e-3:
            continue
        keep.append(p)
    assert len(keep) >= 100, (z, len(keep))
    records.append(vf.record(
        rid=f"ricarte19.romulus25.sfms-galaxies.z{z:g}", source="Romulus25", run="Romulus25 (25 Mpc box, per galaxy)", relation="sfms", z=z,
        axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 SFR averaged over 300 Myr", "yUnit": "log10(Msun/yr)"},
        points=keep, population="all Romulus25 galaxies with SFR > 0 (markers coloured by AGN bolometric luminosity class are merged; zero-SFR upper-limit arrows excluded)",
        warning=f"Marker centres of the Romulus25 galaxies read from the vector paths of Ricarte et al. 2019 (MNRAS 489, 802), SFMS figure (sfms), top row, z={z:g}; no table is published. "
                "Markers are coloured by the bolometric luminosity of the most massive SMBH (all, >1e43, >1e45 erg/s); the three classes are merged into one galaxy sample. Galaxies with zero SFR are shown as arrows in the paper and are not extracted. "
                "SFR is averaged over 300 Myr. The blue R25 main-sequence fit band and the RomulusC (cluster zoom) panels are not extracted. Cosmology is only described as the Planck parameters in the paper.",
        interval="scatter", connect=False, strict=False,
        definitions={"imf": "kroupa01", "massDefinition": "unspecified", "sfrTimescaleMyr": 300, "sfrStatistic": "per-galaxy", "population": "all"},
        citation=f"Ricarte et al. 2019, MNRAS 489, 802, SFMS figure (sfms; arXiv source numbering), Romulus25 panel z={z:g}", doi="10.1093/mnras/stz2161", url=f"https://arxiv.org/abs/{ARXIV}",
        figure="sfms (fig:sfms), top row", panel=f"Romulus25, z={z:g}", sha=sha, member=f"{PDF.name} (circle markers, top row)",
        calib="x: log decades 10^8-10^12 from the bottom-row labels (minor-tick validated); y: labels 10^-4..10^2 shifted onto ticks; asserted", calibration="unknown"))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ricarte19-romulus25-sfms.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Romulus25 SFMS records with {[len(r['representation']['points']) for r in records]} galaxies")
