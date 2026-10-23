"""Checks of the DARWIN-1 halo-mass and black hole relations counted from the public catalogues (scripts/ingest_darwin1_catalogue.py): the choice of the central galaxy and of the complete halo-mass bins on small synthetic catalogues, the saved counts against themselves, the committed records against what stage 2 builds from the saved counts, and the definitions that keep the halo-mass relation apart from M200-based ones.
Offline; reads data/ensembles/darwin1-shmr-bh.json and data/curves/darwin-catalogue.json."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import ingest_darwin1_catalogue as I  # noqa: E402

# the central galaxy: largest stellar mass among the galaxies of the halo, ties to the higher index, halos without a galaxy have none
hi = np.array([0, 0, 0, 1, 2, 2, 3])
ms = np.array([5.0, 9.0, 9.0, 0.0, 3.0, 4.0, 0.0])
gal = ms > 0
mt = np.array([1.0, 1.0, 7.0, 2.0, 1.0, 1.0, 9.0])
assert I.central_galaxies(hi, gal, ms).tolist() == [2, 5], "central = largest stellar mass, ties to the higher index; a halo with only a substructure without stars has no central galaxy"
assert I.central_galaxies(hi, gal, np.array([1.0, 8.0, 7.0, 2.0, 5.0, 1.0, 9.0])).tolist() == [1, 4], "the alternative choice (largest total mass) must pick other galaxies here, and never a substructure without stars"
assert I.central_galaxies(hi, np.zeros(7, bool), ms).tolist() == [], "no galaxies, no centrals"

# the complete bins: the lowest halo-mass bin from which every bin that holds halos has a galaxy in every halo
halos = np.zeros(I.HALO_N, int); withg = np.zeros(I.HALO_N, int)
halos[10:20] = [50, 40, 30, 20, 20, 10, 10, 8, 5, 5]; withg[10:20] = [5, 20, 30, 20, 20, 10, 9, 8, 5, 5]   # coarse bins 5 to 9 (two fine bins each); the bin of fine 16 and 17 is short of one halo
k0, top, h, g = I.x_range_complete(halos, withg)
assert (k0, top) == (9, 9), "a bin in which one halo has no galaxy must not be used, and neither may any bin below it"
withg[16] = 10
k0, top, h, g = I.x_range_complete(halos, withg)
assert k0 == 6, "bins 6 to 9 are complete once the short bin is complete; bin 5 (fine 10 and 11) holds 90 halos of which only 25 have a galaxy"

# the raster check on synthetic figures with known content: the tick calibration, the line and dot readers and the signs of the differences must give back what was drawn
try:
    import pymupdf
    import scipy  # noqa: F401
except ImportError:
    print("raster check test skipped: pymupdf/scipy not installed")
else:
    import tempfile
    import darwin_raster_check as R

    def figure(w, h, frame_rows, frame_cols, x_ticks, y_ticks):
        a = np.full((h, w, 3), 255, np.uint8)
        for r in frame_rows:
            a[r:r + 4, frame_cols[0]:frame_cols[1] + 4] = 0
        for c in frame_cols:
            a[frame_rows[0]:frame_rows[-1] + 4, c:c + 4] = 0
        for x in x_ticks:
            a[frame_rows[-1] - 14:frame_rows[-1], x - 1:x + 2] = 0
        for y in y_ticks:
            a[y - 1:y + 2, frame_cols[0] + 4:frame_cols[0] + 34] = 0
        return a

    def save(a, path):
        pymupdf.Pixmap(pymupdf.csRGB, a.shape[1], a.shape[0], a.tobytes(), False).save(str(path))

    with tempfile.TemporaryDirectory() as tmp:
        # Fig. 11 like: x ticks 10^8 to 10^12 every 250 px (10^7 at the left frame), y ticks 10^10 down to 10^6 every 120 px in each of two panels
        fr, fc = (20, 700, 1380), (100, 1400)
        y_top, y_bot = [60 + 120 * k for k in range(5)], [740 + 120 * k for k in range(5)]
        a = figure(1500, 1400, fr, fc, [354 + 250 * k for k in range(5)], y_top + y_bot)
        rng = np.random.default_rng(3)
        gal = {}
        for k, key in enumerate(("z2.1", "z0.19")):
            x = rng.uniform(7.2, 11.5, 2500); y = 5.0 + 0.8 * (x - 7.0) + rng.normal(0, 0.3, 2500)
            gal[key] = (x, y)
            for xx, yy in zip(x, y):
                cx, cy = round(354 + (xx - 8) * 250), round((y_top[0] if k == 0 else y_bot[0]) + (10 - yy) * 120)
                if 110 < cx < 1390 and (30 < cy < 690 if k == 0 else 710 < cy < 1370):
                    for dy in range(-3, 4):
                        for dx in range(-3, 4):
                            if dx * dx + dy * dy <= 9:
                                a[cy + dy, cx + dx] = (163, 163, 162)
        save(a, Path(tmp) / "bh.png")
        edges = 7.0 + np.arange(17) / 3
        same = R.check_bh(Path(tmp) / "bh.png", {k: {"A": v} for k, v in gal.items()}, edges)
        assert abs(same["calibration"]["xPixelsPerDecade"] - 250) < 0.6 and same["calibration"]["yPixelsPerDecade"] == [120.0, 120.0], same["calibration"]
        for key in gal:
            r = same[key]["A"]
            assert r["binsCompared"] >= 8 and r["diff50Max"] < 0.05, f"the same dots must give the same percentiles ({key}: {r['diff50Max']})"
        shifted = R.check_bh(Path(tmp) / "bh.png", {k: {"A": (v[0], v[1] + 0.3)} for k, v in gal.items()}, edges)
        for key in gal:
            r = shifted[key]["A"]
            assert abs(r["diff50Median"] - 0.3) < 0.06 and r["diff50WithinHalfDex"] == 0, f"dots 0.3 dex higher must read +0.3 dex ({key}: {r['diff50Median']})"
        # Fig. 10 like: x ticks 10^9 to 10^14 every 200 px, y ticks 10^12 down to 10^6 every 100 px, median line drawn as M* = x + ratio(x) with ratio(x) = -2 + 0.1 (x - 11)
        y_top, y_bot = [60 + 100 * k for k in range(7)], [740 + 100 * k for k in range(7)]
        a = figure(1500, 1400, fr, fc, [300 + 200 * k for k in range(6)], y_top + y_bot)
        ratio = lambda x: -2.0 + 0.1 * (x - 11)
        for k, y0 in enumerate((y_top[0], y_bot[0])):
            for c in range(round(300 + 1.5 * 200), round(300 + 4.0 * 200)):
                x = 9 + (c - 300) / 200
                r = round(y0 + (12 - (x + ratio(x))) * 100)
                a[r - 4:r + 5, c] = (102, 102, 101)
        save(a, Path(tmp) / "shmr.png")
        xc = [10.5 + 0.25 * i for i in range(10)]
        res = R.check_shmr(Path(tmp) / "shmr.png", {k: [(x, 100, ratio(x) - 0.1, True) for x in xc] for k in ("z3", "z0.19")})
        for key in ("z3", "z0.19"):
            r = res[key]
            assert r["binsCompared"] == len(xc) and abs(r["paperMinusCatalogueMin"] - 0.1) < 0.02 and abs(r["paperMinusCatalogueMax"] - 0.1) < 0.02, f"a catalogue curve 0.1 dex below the drawn line must read +0.1 ({key}: {r['paperMinusCatalogueMin']}, {r['paperMinusCatalogueMax']})"

# the saved counts are consistent with themselves
ens = json.loads(I.ENS2.read_text())
assert ens["grids"]["haloN"] == I.HALO_N and ens["grids"]["bhN"] == I.BH_N and ens["grids"]["galaxyN"] == I.GX_N, "the saved grids must be the ones the script uses"
for sn, s in ens["snapshots"].items():
    r, b = s["shmr"], s["bh"]
    assert r["nOutsideGrid"] == 0 and b["nOutsideGrid"] == 0, f"snapshot {sn}: no galaxy may fall outside the stellar-mass and black hole mass grids"
    assert all(w <= n for w, n in zip(r["halosWithGalaxy"], r["halos"])), f"snapshot {sn}: more halos with a galaxy than halos"
    assert sum(map(sum, r["counts"])) == sum(r["halosWithGalaxy"]), f"snapshot {sn}: the central counts must add up to the halos that have a galaxy"
    assert all(o <= w <= n for o, w, n in zip(b["withOneBH"], b["withBH"], b["galaxies"])), f"snapshot {sn}: galaxies with one black hole <= with a black hole <= galaxies"
    assert sum(map(sum, b["counts"])) == sum(b["withBH"]) and all(p >= w for p, w in zip(b["bhParticles"], b["withBH"])), f"snapshot {sn}: black hole counts"
    assert r["altCentral"]["maxAbsDiffMedianDex"] < 0.05, f"snapshot {sn}: the choice of central changes a median by {r['altCentral']['maxAbsDiffMedianDex']} dex"

# the committed records are what stage 2 builds from the saved counts
committed = {r["id"]: r for r in json.loads(I.OUT.read_text())["records"]}
fresh = I.shmr_records(ens) + I.bh_records(ens)
assert len(fresh) >= 20 and len({r["id"] for r in fresh}) == len(fresh)
for r in fresh:
    c = committed[r["id"]]
    for k in ("axes", "selection", "definitions", "epoch", "scatter", "calibration", "rankable", "notes", "representation", "domain"):
        assert c[k] == r[k], f"{r['id']}: committed {k} differ from stage 2"
    assert all(c["provenance"][k] == v for k, v in r["provenance"].items()), f"{r['id']}: provenance differs from stage 2"
shmr = [r for r in fresh if r["relation"] == "shmr"]; bh = [r for r in fresh if r["relation"] == "bh"]
assert shmr and bh
for r in shmr:
    d = r["definitions"]
    assert d["haloMassDefinition"] == "FoF-total-mass-all-species" and d["galaxyType"] == "central" and "not M200,c" in r["axes"]["xDefinition"], r["id"]
    assert "not comparable with M200-based" in r["selection"]["warning"], r["id"]
    s = ens["snapshots"][str(r["epoch"]["snapshot"])]["shmr"]
    k0, top, h, g = I.x_range_complete(s["halos"], s["halosWithGalaxy"])
    used = [round((p["x"] - I.HALO_LO) / (I.HALO_STEP * I.HALO_COARSE) - 0.5) for p in r["representation"]["points"]]
    assert min(used) >= k0 and all(h[k] == g[k] for k in used) and all(p["count"] >= 10 for p in r["representation"]["points"]), f"{r['id']}: a bin in which some halo has no galaxy, or fewer than 10 centrals, was used"
    assert all(p["yLow"] <= p["y"] <= p["yHigh"] for p in r["representation"]["points"]) and r["representation"]["intervalKind"] == "scatter", r["id"]
for r in bh:
    d = r["definitions"]
    assert d["bhMassMethod"] == "intrinsic-sum-of-bh-particles" and "sum" in r["selection"]["warning"] and "at least one black hole particle" in r["selection"]["warning"], r["id"]
    assert min(p["x"] for p in r["representation"]["points"]) > I.LOGM_MIN and all(p["count"] >= 10 and p["yLow"] <= p["y"] <= p["yHigh"] for p in r["representation"]["points"]), f"{r['id']}: galaxies below 100 star particles (10^7 Msun) must not be used"

# what was compared with the paper's raster figures, as saved
chk = ens["figureCheck"]
for panel, p in ((k, chk["shmr"][k]) for k in I.FIG_SHMR):
    assert p["binsCompleteCompared"] >= 5 and 0 <= p["completeMin"] and p["completeMax"] < 0.3, f"Fig. 10 {panel}: the paper's median line must lie above the FoF-mass curve by less than 0.3 dex ({p['completeMin']} to {p['completeMax']})"
for panel in I.FIG_BH:
    a, b = chk["bh"][panel]["A"], chk["bh"][panel]["B"]
    assert a["binsCompared"] >= 10 and a["diff50WithinHalfDex"] >= a["binsCompared"] - 3 and a["diff50Max"] < 0.35, f"Fig. 11 {panel}: summed black hole masses must reproduce the dots of the figure"
    assert len(b["binsWithPaperDotsButNoCatalogueDots"]) >= 3, f"Fig. 11 {panel}: galaxies with exactly one black hole must fail to cover the figure at high stellar mass"
    note = next(r for r in bh if r["epoch"]["snapshot"] == chk["bh"]["snapshots"][panel])["selection"]["warning"]
    assert f"{a['diff50Median']:+.2f} dex" in note, f"Fig. 11 {panel}: the record must quote the saved comparison"
print(f"DARWIN catalogue relations OK: {len(shmr)} halo-mass and {len(bh)} black hole records match the saved counts")
