import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

ARXIV = "1904.10116"
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else vf.fetch_arxiv(ARXIV)
DEF = {"imf": "kroupa01", "massDefinition": "unspecified", "bhMassMethod": "accreted-excluding-seed", "population": "bh-hosts"}
WARN = (" Marker centres of the Romulus25 galaxies (z=0.05, the latest available slice; the paper's text calls these z=0 relations) read from the vector paths; no table is published. "
        "M_BH,acc is the accreted mass of the most massive SMBH of each host (seed mass excluded), only for SMBHs within 2 kpc of the galactic centre. The RomulusC cluster-zoom panels, the colour coding and the observational lines are not extracted. "
        "Cosmology is only described as the Planck parameters in the paper.")


def small(page, frame, stroke_only=None, fill=None, size=(2.5, 3.6), items=8):
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if not (size[0] <= r.width <= size[1] and size[0] <= r.height <= size[1]) or len(d["items"]) != items:
            continue
        if stroke_only is True and (d["fill"] is not None or d["type"] != "s"):
            continue
        if fill is True and d["fill"] is None:
            continue
        cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
        if frame.x0 <= cx <= frame.x1 and frame.y0 <= cy <= frame.y1:
            out.append((cx, cy))
    return out


def dedupe(pts):
    keep = []
    for p in sorted(pts):
        if keep and abs(p[0] - keep[-1][0]) < 1e-3 and abs(p[1] - keep[-1][1]) < 1e-3:
            continue
        keep.append(p)
    return keep


records = []
# BH - M* (massRelations_fedd, top-left panel)
pdf = SRC / "massRelations_fedd.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
frame = vf.frames(page)[0]
words = page.get_text("words")
xl = sorted(((w[0] + w[2]) / 2, float(w[4][2:])) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[1] > vf.frames(page)[2].y1 and frame.x0 - 2 < (w[0] + w[2]) / 2 < frame.x1 - 1)
yl = sorted(((w[1] + w[3]) / 2, float(w[4][2:])) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[0] < frame.x0 and frame.y0 - 3 < (w[1] + w[3]) / 2 < frame.y1 + 3)
fx, xt = vf.axis_fit_log2(page, vf.frames(page)[2], "x", xl)
fy, yt = vf.axis_fit_log2(page, frame, "y", yl)
assert [v for _, v in xt][:3] == [8.0, 9.0, 10.0] and sorted(v for _, v in yt)[0] == 5.0, (xt, yt)
circ = small(page, frame, stroke_only=True, size=(3.0, 5.0), items=8)
stars = small(page, frame, fill=True, size=(6.0, 8.0), items=10)
pts = [(fx(cx), fy(cy)) for cx, cy in circ + stars]
xlo, xhi, ylo, yhi = fx(frame.x0), fx(frame.x1), min(fy(frame.y0), fy(frame.y1)), max(fy(frame.y0), fy(frame.y1))
pts = dedupe([p for p in pts if xlo <= p[0] <= xhi and ylo <= p[1] <= yhi])
assert len(pts) >= 300, len(pts)
records.append(vf.record(
    rid="ricarte19.romulus25.bh-galaxies.z0.05", source="Romulus25", run="Romulus25 (25 Mpc box, per galaxy)", relation="bh", z=0.05, z_range=(0.0, 0.05), z_nominal=0.0,
    axes={"xDefinition": "log10 stellar mass", "xUnit": "log10(Msun)", "yDefinition": "log10 accreted mass of the most massive SMBH (seed mass excluded)", "yUnit": "log10(Msun)"},
    points=pts, population="Romulus25 galaxies hosting an SMBH within 2 kpc of the centre",
    warning="Romulus25 SMBH mass versus host stellar mass, from the massRelations_fedd figure of Ricarte et al. 2019 (MNRAS 489, 802), top-left panel." + WARN + " Open circles (f_Edd <= 1e-2) and stars (f_Edd > 1e-2) are merged.",
    interval="scatter", connect=False, strict=False, definitions=dict(DEF),
    citation="Ricarte et al. 2019, MNRAS 489, 802, SMBH mass vs stellar mass (massRelations_fedd; arXiv source numbering), Romulus25", doi="10.1093/mnras/stz2161", url=f"https://arxiv.org/abs/{ARXIV}",
    figure="massRelations_fedd (fig:mass_relations), top-left", panel="Romulus25, M*", sha=sha, member=f"{pdf.name} (open circles and stars)",
    calib="x: labelled decades 10^8-10^12 (bottom frame, minor-tick validated); y: labelled decades 10^5-10^10 (minor-tick validated)", calibration="unknown"))
# BH - sigma (msigma_2panel, left panel)
pdf = SRC / "msigma_2panel.pdf"
page = vf.page_of(pdf)
sha = vf.sha256(pdf)
frame = next(r for r in vf.frames(page) if abs(r.x0 - 58.4) < 1 and abs(r.y0 - 13.3) < 1)
words = page.get_text("words")
lab = next(w for w in words if w[4] == "102" and frame.x0 < w[0] < frame.x1)
fx, xs_, scale = vf.axis_fit_log1(page, frame, "x", ((lab[0] + lab[2]) / 2, 2.0))
yl = sorted(((w[1] + w[3]) / 2, float(w[4][2:])) for w in words if re.fullmatch(r"10\d{1,2}", w[4]) and w[0] < frame.x0 and frame.y0 - 3 < (w[1] + w[3]) / 2 < frame.y1 + 3)
fy, yt = vf.axis_fit_log2(page, frame, "y", yl)
cs = small(page, frame, fill=True, size=(2.5, 3.6), items=8)
xlo, xhi, ylo, yhi = fx(frame.x0), fx(frame.x1), min(fy(frame.y0), fy(frame.y1)), max(fy(frame.y0), fy(frame.y1))
pts = dedupe([p for p in ((fx(cx), fy(cy)) for cx, cy in cs) if xlo <= p[0] <= xhi and ylo <= p[1] <= yhi])
assert len(pts) >= 300, len(pts)
records.append(vf.record(
    rid="ricarte19.romulus25.bhsigma-galaxies.z0.05", source="Romulus25", run="Romulus25 (25 Mpc box, per galaxy)", relation="bhsigma", z=0.05, z_range=(0.0, 0.05), z_nominal=0.0,
    axes={"xDefinition": "log10 maximum stellar velocity dispersion within the effective radius, sigma_max(<R_eff)", "xUnit": "log10(km/s)", "yDefinition": "log10 accreted mass of the most massive SMBH (seed mass excluded)", "yUnit": "log10(Msun)"},
    points=pts, population="Romulus25 galaxies hosting an SMBH",
    warning="Romulus25 SMBH mass versus stellar velocity dispersion, from the msigma_2panel figure of Ricarte et al. 2019 (MNRAS 489, 802), left panel." + WARN + " The four stellar-mass colour classes are merged.",
    interval="scatter", connect=False, strict=False, definitions={**DEF, "sigmaDefinition": "maximum stellar velocity dispersion within R_eff"},
    citation="Ricarte et al. 2019, MNRAS 489, 802, SMBH mass vs velocity dispersion (msigma_2panel; arXiv source numbering), Romulus25", doi="10.1093/mnras/stz2161", url=f"https://arxiv.org/abs/{ARXIV}",
    figure="msigma_2panel (fig:msigma), left", panel="Romulus25", sha=sha, member=f"{pdf.name} (filled circles)",
    calib=f"x: one labelled decade (10^2) with the log scale ({scale:.1f} pt/dex) fixed by the minor-tick pattern; y: labelled decades 10^5-10^10 (minor-tick validated)", calibration="unknown"))
out = Path(__file__).resolve().parent.parent / "data" / "curves" / "ricarte19-romulus25-bh.json"
out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Wrote {len(records)} Romulus25 BH records with {[len(r['representation']['points']) for r in records]} galaxies")
