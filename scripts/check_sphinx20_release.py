"""Check of the SPHINX20 records against the public data release and the paper (Katz et al. 2023, arXiv:2309.03269), written separately from scripts/ingest_elf_sphinx20.py and scripts/ingest_sphinx.py.

usage: check_sphinx20_release.py <clone of https://github.com/HarleyKatz/SPHINX-20-data>

What it asserts (an assertion that fails stops the script; the printed numbers are the ones quoted in data/screen-triaged.json):
  1. the paper's Table 1 (galaxies per snapshot, maximum and median log stellar mass and log virial mass) is reproduced by the release table;
  2. the halo-mass unit: the paper's halo mass function figure (x in Msun/h, y per (cMpc/h)^3, solid lines = haloes in the release) is reproduced count for count only if the release's `mvir` is in Msun and the box is 20 cMpc;
     the paper's stellar-mass-halo-mass figure (both axes in Msun) is reproduced by the release columns as they are;
  3. the virial mass and radius of the release imply a fixed overdensity (Bryan and Norman give about 177 times the critical density at these redshifts);
  4. the H-alpha luminosity function records of two snapshots (z = 5 and 8, and all others) are re-derived from the release with separate binning code and agree bin by bin;
  5. the release's luminosity unit: L(H-alpha) per ionizing photon is below the case-B value of 1.36e-12 erg, and the reddening coefficient fitted to the paper's figure is 2.1 to 2.2 snapshot by snapshot with the volume left free.
"""
import csv
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
REPO = Path(sys.argv[1])
SRC = vf.fetch_arxiv("2309.03269")
H0, OM, OL = 67.11, 0.3175, 0.6825
h = H0 / 100
with open(REPO / "data" / "all_basic_data.csv") as f:
    rd = csv.reader(f)
    head = next(rd)
    rows = list(rd)
col = {k: i for i, k in enumerate(head)}


def g(name):
    return np.array([float(r[col[name]]) if r[col[name]] != "" else np.nan for r in rows])


Z, MV, RV, MS, S10 = g("redshift"), g("mvir"), g("rvir"), g("stellar_mass"), g("sfr_10")
LINT = g("HI_6562.8_int")
assert len(rows) == 1380

# 1. Table 1 of the paper ------------------------------------------------------------------------------------------------------------------
tex = (SRC / "main.tex").read_text(errors="replace")
tab = tex.split("\\label{tab:sample}")[1].split("\\end{tabular}")[0]
table1 = {}
for line in tab.splitlines():
    m = re.match(r"\s*([\d.]+)\s*&\s*(\d+)\s*&\s*([\d.]+)\s*&\s*([\d.]+)\s*&\s*([\d.]+)\s*&\s*([\d.]+)", line)
    if m:
        table1[float(m.group(1))] = [float(v) for v in m.groups()[1:]]
assert len(table1) == 7, table1
diffs = []
for zp, v in table1.items():
    z = 4.64 if zp == 4.6 else zp
    s = np.isclose(Z, z)
    mine = [s.sum(), MS[s].max(), np.median(MS[s]), MV[s].max(), np.median(MV[s])]
    assert mine[0] == v[0], (z, mine[0], v[0])
    diffs += [abs(a - b) for a, b in zip(mine[1:], v[1:])]
n_equal = sum(d < 0.0051 for d in diffs)
print(f"1. Table 1: galaxy counts identical in 7 of 7 snapshots; {n_equal} of {len(diffs)} printed log masses agree to within the printed rounding, largest difference {max(diffs):.3f} dex")
assert n_equal >= 27 and max(diffs) <= 0.0101

# 2a. halo mass function figure -------------------------------------------------------------------------------------------------------------
page = vf.page_of(SRC / "figures" / "hmf_sphinx.pdf")
frame = max(vf.frames(page, 60, 60), key=lambda r: r.width * r.height)
fx, _ = vf.axis_fit(page, frame, "x")
fy, yt = vf.axis_fit(page, frame, "y", snap=5.0)  # the helper reads the labels 10^2, 10^1, 10^0 as 102, 101, 100 (the exponents are superscripts); the lower decades have minus signs it does not read
assert [v for _, v in yt] == [102.0, 101.0, 100.0], yt
fyl = lambda py: fy(py) - 100.0  # log10 of the plotted density
assert abs(fyl(frame.y1) + 4.0) < 0.02, fyl(frame.y1)  # the frame bottom is the 10^-4 line
COL = {10.0: (0.5, 0.0, 0.0), 8.0: (1.0, 0.65, 0.0), 6.0: (0.74, 0.72, 0.42), 4.64: (0.28, 0.51, 0.71)}
n_ok = {"H1 (mass in Msun/h = mvir + log h, volume (20 h)^3)": 0, "H0 (mvir as is, volume 20^3)": 0, "H2 (mvir as is, volume (20 h)^3)": 0}
n_bins = 0
for d in page.get_drawings():
    if "[]" not in str(d.get("dashes")) or abs((d.get("width") or 0) - 1.0) > 1e-6 or len(d["items"]) < 8:
        continue
    for z, c in COL.items():
        if not (d.get("color") and all(abs(a - b) < 0.02 for a, b in zip(d["color"], c))):
            continue
        m = MV[np.isclose(Z, z)]
        for it in d["items"]:
            if it[0] != "l" or abs(it[1].y - it[2].y) > 1e-3 or abs(it[1].x - it[2].x) < 1.0:
                continue
            x0, x1, ly = fx(min(it[1].x, it[2].x)), fx(max(it[1].x, it[2].x)), fyl(it[1].y)
            n_bins += 1
            for name, sh, vol in (("H1 (mass in Msun/h = mvir + log h, volume (20 h)^3)", np.log10(h), (20 * h) ** 3), ("H0 (mvir as is, volume 20^3)", 0.0, 20.0 ** 3), ("H2 (mvir as is, volume (20 h)^3)", 0.0, (20 * h) ** 3)):
                n_fig = 10 ** ly * vol * (x1 - x0)
                n_rel = ((m + sh >= x0 - 1e-6) & (m + sh < x1 - 1e-6)).sum()
                n_ok[name] += abs(n_fig - n_rel) < 0.2
print(f"2a. halo mass function figure, {n_bins} plotted bins (z = 4.64, 6, 8, 10): same integer count as the release in " + "; ".join(f"{k}: {v}" for k, v in n_ok.items()))
assert n_bins == 50 and list(n_ok.values())[0] == 50 and list(n_ok.values())[1] == 0

# 2b. stellar mass - halo mass figure ---------------------------------------------------------------------------------------------------------
page = vf.page_of(SRC / "figures" / "m_star_m_halo.pdf")
frame = max(vf.frames(page, 60, 60), key=lambda r: r.width * r.height)
fx, _ = vf.axis_fit(page, frame, "x")
fy, _ = vf.axis_fit(page, frame, "y")
pts = []
for d in page.get_drawings():
    r = d["rect"]
    if d["fill"] is not None and 0.5 <= r.width <= 6 and 0.5 <= r.height <= 6 and frame.x0 <= (r.x0 + r.x1) / 2 <= frame.x1 and frame.y0 <= (r.y0 + r.y1) / 2 <= frame.y1:
        pts.append((fx((r.x0 + r.x1) / 2), fy((r.y0 + r.y1) / 2)))
pts = np.array(pts)
rel = np.column_stack([MV, MS])
dist = np.array([np.min(np.hypot(*(pts - q).T)) for q in rel])
shifted = np.array([np.min(np.hypot(*(pts - (q + np.array([np.log10(h), 0.0]))).T)) for q in rel])
print(f"2b. stellar mass - halo mass figure: {(dist < 0.001).sum()} of {len(rel)} release galaxies lie within 0.001 dex of a plotted marker as they are (largest distance {dist.max():.4f}); with the halo mass shifted by log10 h, {(shifted < 0.001).sum()}")
assert (dist < 0.001).sum() == 1380 and (shifted < 0.001).sum() < 200

# 3. virial overdensity -----------------------------------------------------------------------------------------------------------------------
G = 4.30091e-6  # kpc (km/s)^2 / Msun
out = []
for z in sorted(set(Z)):
    s = np.isclose(Z, z)
    E2 = OM * (1 + z) ** 3 + OL
    rho_c = 3 * (H0 / 1000.0) ** 2 * E2 / (8 * np.pi * G)  # Msun / kpc^3
    x = OM * (1 + z) ** 3 / E2 - 1
    bn = 18 * np.pi ** 2 + 82 * x - 39 * x ** 2
    delta = 10 ** MV[s] / (4.0 / 3.0 * np.pi * (RV[s] * 20000.0 / (1 + z)) ** 3) / rho_c
    spread = np.percentile(delta, 84) / np.percentile(delta, 16)
    out.append((z, float(np.median(delta)), bn))
    assert spread < 1.02 and 0.9 * bn < np.median(delta) < 1.25 * bn, (z, np.median(delta), bn)
    assert not (0.8 * bn < np.median(delta) * h ** 3 < 1.25 * bn)  # not a box of 20 cMpc/h
    assert not (0.8 * bn < np.median(delta) / h < 1.25 * bn)  # not masses in Msun/h
print("3. M_vir and R_vir (R_vir in units of 20 cMpc, physical = x 20 cMpc/(1+z)) imply Delta_c = " + ", ".join(f"{d:.0f} (z={z:g})" for z, d, _ in out) + "; Bryan and Norman: " + f"{out[0][2]:.0f} to {out[-1][2]:.0f}")

# 4. H-alpha luminosity function records re-derived ---------------------------------------------------------------------------------------------
recs = {r["id"]: r for r in json.loads((ROOT / "data" / "curves" / "elf-sphinx20.json").read_text())["records"]}
VOL, W = 20.0 ** 3, 0.25
worst = {}
for z in sorted(set(Z)):
    s = np.isclose(Z, z)

    def counts(lum):
        k = np.floor((np.log10(lum) - 40.0) / W + 1e-9).astype(int)
        return {int(a): int((k == a).sum()) for a in np.unique(k)}
    r = recs[f"katz23.sphinx20.elf.halpha.intrinsic.z{z:g}"]
    c = counts(LINT[s])
    d = max(abs(np.log10(c[int(round((p["x"] - 40.0) / W - 0.5))] / (VOL * W)) - p["y"]) for p in r["representation"]["points"])
    worst[(z, "intrinsic")] = d
    ra = recs.get(f"katz23.sphinx20.elf.halpha.attenuated.z{z:g}")
    if ra:
        per = [counts(g(f"HI_6562.8_dir_{k}")[s]) for k in range(10)]
        d = max(abs(np.log10(np.mean([q.get(int(round((p["x"] - 40.0) / W - 0.5)), 0) for q in per]) / (VOL * W)) - p["y"]) for p in ra["representation"]["points"])
        worst[(z, "attenuated")] = d
print(f"4. luminosity function records re-derived with separate code: {len(worst)} records, {sum(len(recs[k]['representation']['points']) for k in recs)} bins, largest difference {max(worst.values()):.5f} dex (rounding of the stored value to four decimals)")
assert max(worst.values()) < 1e-4

# 5. unit of the luminosity and the reddening coefficient --------------------------------------------------------------------------------------
Q = 10 ** g("ionizing_luminosity")
ok = np.isfinite(Q)
ratio = np.median(LINT[ok] / Q[ok])
print(f"5a. L(H-alpha) per ionizing photon, median over {ok.sum()} galaxies: {ratio:.2e} erg (case B without escape: 1.36e-12)")
assert 0.6e-12 < ratio < 1.36e-12
page = vf.page_of(SRC / "figures" / "Halpha_lum_func.pdf")
frame = max(vf.frames(page, 60, 60), key=lambda r: r.width * r.height)
fx, _ = vf.axis_fit(page, frame, "x")
fy, _ = vf.axis_fit(page, frame, "y", snap=5.0)
PAL = {(0.28, 0.51, 0.71): 4.64, (0.53, 0.81, 0.92): 5.0, (0.74, 0.72, 0.42): 6.0, (0.0, 0.39, 0.0): 7.0, (1.0, 0.65, 0.0): 8.0, (0.8, 0.36, 0.36): 9.0, (0.5, 0.0, 0.0): 10.0}
fig = {z: [] for z in PAL.values()}
for c in vf.curves(page, frame, fx, fy, min_items=2):
    z = PAL.get(c["color"])
    p = [(x, y) for x, y in c["points"] if x > 40.5]
    if z is None or abs((c["width"] or 0) - 0.5) > 1e-6 or len(p) < 2 or not all(abs((x - 40.75) / 0.5 - round((x - 40.75) / 0.5)) < 0.03 for x, _ in p):
        continue
    fig[z].append(p)
assert all(len(v) == 10 for v in fig.values())
LD = {k: g(f"HI_6562.8_dir_{k}") for k in range(10)}
ED = {k: g(f"ebmv_dir_{k}") for k in range(10)}


def resid(kHa, zs):
    res = []
    for z in zs:
        s = np.isclose(Z, z)
        mods = [np.histogram(np.log10(LD[k][s] * 10 ** (0.4 * kHa * ED[k][s])), np.arange(40.0, 45.01, 0.5))[0] for k in range(10)]
        for j in range(10):
            xc = 40.25 + 0.5 * j
            drawn = sorted(y for c in fig[z] for x, y in c if abs(x - xc) < 0.02)
            if len(drawn) == 10 and all(n[j] > 0 for n in mods):
                res += [a - b for a, b in zip(sorted(np.log10(n[j] / (VOL * 0.5)) for n in mods), drawn)]
    return np.array(res)


per_z = {}
for z in fig:
    best = min(((np.sqrt(np.mean(resid(k, [z]) ** 2)), round(k, 1)) for k in np.arange(1.0, 4.01, 0.1) if len(resid(k, [z]))), key=lambda t: t[0])
    per_z[z] = best
r = resid(2.2, list(fig))
print(f"5b. reddening coefficient fitted to the paper's plotted function, snapshot by snapshot: " + ", ".join(f"z={z:g}: k={b[1]}" for z, b in per_z.items()) + f"; at k = 2.2: {len(r)} bins, rms {np.sqrt(np.mean(r ** 2)):.3f} dex, mean offset {r.mean():+.4f} dex (a box of 20 cMpc/h would give {3 * np.log10(h):+.2f})")
assert all(2.0 <= b[1] <= 2.3 for b in per_z.values()) and abs(r.mean()) < 0.02 and np.sqrt(np.mean(r ** 2)) < 0.03
