"""Tests for the measured conversions: the per-catalogue function recovers known shifts from a synthetic catalogue, adding a code to the saved ensemble leaves the other codes exactly as they were, a fourth code comes out in the same schema as the first three, and the published numbers pass the checks the catalogues allow (the half-mass aperture is log10(0.5) by definition; quantiles are ordered; the SFR aperture ratio is near 1 for the first three codes and never above 1 for any)."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ingest_camels_conversions as C  # noqa: E402

DATA = json.loads((HERE.parent / "data" / "conversions.json").read_text())
ORIGINAL = ("IllustrisTNG", "SIMBA", "Astrid")                 # the codes measured first; their numbers must not move when a code is added


def synthetic(n=4000, seed=1, frac=0.8, tail=False):
    """A catalogue of n galaxies whose aperture masses are `frac` of the total. Masses are uniform in log from 9 to 11.4, or (tail=True) fall exponentially with a 0.5 dex scale from 9, which gives the smooth abundance function that the fixed-number-density shift needs."""
    rng = np.random.default_rng(seed)
    h = 0.6711
    if tail:
        logm = 9.0 + rng.exponential(0.5, n)
        while (bad := logm > 11.9).any():            # keep every mass inside the mass-function bins (8.5 to 12.0), so no galaxy is lost to the histogram range
            logm[bad] = 9.0 + rng.exponential(0.5, int(bad.sum()))
    else:
        logm = rng.uniform(9.0, 11.4, n)
    ms = 10 ** logm / 1e10 * h
    arr = {k: np.zeros((n, 6)) if k.endswith("Type") else np.zeros(n) for k in C.ARRAYS + C.GROUP_ARRAYS}
    arr["SubhaloMassType"][:, 4] = ms
    arr["SubhaloLenType"][:] = 500
    for lab, name in C.MASS_DEFS:
        arr[name][:, 4] = ms * frac
    arr["SubhaloSFR"][:] = 1.0
    for lab, name in C.SFR_DEFS:
        arr[name][:] = 0.5
    arr["SubhaloGasMetallicity"][:] = 0.01
    arr["SubhaloStarMetallicity"][:] = 0.01
    for lab, name in C.GASZ_DEFS + C.STARZ_DEFS:
        arr[name][:] = 0.02
    arr["GroupFirstSub"] = np.arange(100)
    arr["Group_M_Crit200"] = np.full(100, 100.0)       # 1e12 Msun/h
    arr["SubhaloMass"][:100] = 150.0
    return arr, h


class Synthetic(unittest.TestCase):
    def test_known_shifts(self):
        arr, h = synthetic()
        o = C.conversions(arr, h)
        self.assertEqual(o["nSelected"], 4000)
        for key, want in (("mass.total-to-rad2", np.log10(0.8)), ("sfr.total-to-rad2", np.log10(0.5)), ("gasz.all-to-sfr", np.log10(2.0)), ("starz.all-to-rad1", np.log10(2.0))):
            med = [m for m in o["pairs"][key]["median"] if m is not None]
            self.assertTrue(med)
            for m in med:
                self.assertAlmostEqual(m, want, places=4, msg=key)
        halo = [m for m in o["pairs"]["halo.m200crit-to-subhalo"]["median"] if m is not None]
        self.assertAlmostEqual(halo[0], np.log10(1.5), places=4)
        self.assertEqual(sum(o["gsmf"]["total"]), 4000)

    def test_zero_other_is_counted_not_averaged(self):
        arr, h = synthetic()
        arr["SubhaloSFRinRad"][:1000] = 0.0
        o = C.conversions(arr, h)
        b = o["pairs"]["sfr.total-to-rad2"]
        self.assertEqual(sum(b["nZeroOther"]), 1000)
        self.assertEqual(sum(b["nRef"]), 4000)


def seed_results(code, frac, n_seeds=6, snaps=("090",)):
    """Per-seed results of one code as stage 1 would return them, from synthetic catalogues (a different galaxy sample per seed)."""
    out = []
    for i in range(n_seeds):
        arr, h = synthetic(n=8000, seed=100 * len(code) + i, frac=frac, tail=True)
        res = {s: {"z": 0.0, "h": h, "boxCkpcH": 25000.0, "arraysSha256": f"{code}-{i}-{s}", **C.conversions(arr, h)} for s in snaps}
        out.append((code, f"CV_{i}", res))
    return out


def derive_from(ens):
    """Run the offline stage on an ensemble dictionary, writing to temporary files, and return the result."""
    with tempfile.TemporaryDirectory() as d:
        ens_path, out_path = Path(d) / "ens.json", Path(d) / "conversions.json"
        ens_path.write_text(json.dumps(ens))
        with mock.patch.object(C, "ENS", ens_path), mock.patch.object(C, "OUT", out_path):
            C.derive()
        return json.loads(out_path.read_text())


class FourthCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first3 = [r for code, frac in zip(ORIGINAL, (0.8, 0.8, 0.8)) for r in seed_results(code, frac)]
        cls.fourth = seed_results("Swift-EAGLE", 0.7)           # a deliberately different aperture shift
        cls.ens3 = C.build_ensemble(cls.first3, list(ORIGINAL), today="2026-01-01")

    def test_catalogue_urls(self):
        base = "https://users.flatironinstitute.org/~camels"
        for code in ORIGINAL:
            self.assertEqual(C.catalogue_url(code, "CV_3", "062"), f"{base}/Sims/{code}/CV/CV_3/groups_062.hdf5")
        self.assertEqual(C.catalogue_url("Swift-EAGLE", "CV_3", "062"), f"{base}/FOF_Subfind/Swift-EAGLE/L25n256/CV/CV_3/groups_062.hdf5")

    def test_adding_a_code_keeps_the_others_exactly(self):
        before = json.dumps(self.ens3, sort_keys=False)
        new = C.build_ensemble(copy.deepcopy(self.fourth), ["Swift-EAGLE"], existing=json.loads(before), today="2026-02-02")
        old = json.loads(before)
        for code in ORIGINAL:
            self.assertEqual(json.dumps(new["suites"][code]), json.dumps(old["suites"][code]), code)
            self.assertEqual(json.dumps(new["pooledGrids"][code]), json.dumps(old["pooledGrids"][code]), code)
        self.assertEqual(list(new["suites"]), list(ORIGINAL) + ["Swift-EAGLE"])
        self.assertEqual(new["retrieved"], "2026-01-01")                    # the date of the first three is not rewritten
        self.assertEqual(new["retrievedBySuite"]["Swift-EAGLE"], "2026-02-02")
        self.assertEqual(new["retrievedBySuite"]["SIMBA"], "2026-01-01")
        self.assertEqual(len(new["suites"]["Swift-EAGLE"]), 6)

    def test_adding_a_code_refuses_when_the_bins_differ(self):
        old = json.loads(json.dumps(self.ens3))
        old["xEdges"] = old["xEdges"][:-1]
        with self.assertRaises(ValueError):
            C.build_ensemble(copy.deepcopy(self.fourth), ["Swift-EAGLE"], existing=old)

    def test_fourth_code_has_the_same_schema_and_the_others_do_not_move(self):
        out3 = derive_from(self.ens3)
        ens4 = C.build_ensemble(copy.deepcopy(self.fourth), ["Swift-EAGLE"], existing=json.loads(json.dumps(self.ens3)), today="2026-02-02")
        out4 = derive_from(ens4)
        for code in ORIGINAL:
            self.assertEqual(json.dumps(out3["suites"][code]), json.dumps(out4["suites"][code]), code)
        a, b = out4["suites"]["IllustrisTNG"]["z0"], out4["suites"]["Swift-EAGLE"]["z0"]
        self.assertEqual(sorted(a), sorted(b))
        self.assertEqual(list(a["pairs"]), list(b["pairs"]))
        self.assertEqual(sorted(a["gsmfShiftAtFixedNumberDensity"]), sorted(b["gsmfShiftAtFixedNumberDensity"]))
        self.assertEqual(b["nSeeds"], 6)
        self.assertEqual(sorted(out4["suiteSources"]), sorted(ORIGINAL + ("Swift-EAGLE",)))
        self.assertIn("four codes", out4["about"])
        self.assertIn("three codes", out3["about"])

    def test_fourth_code_recovers_its_own_shift_with_a_spread(self):
        out = derive_from(C.build_ensemble(copy.deepcopy(self.fourth), ["Swift-EAGLE"], existing=json.loads(json.dumps(self.ens3))))
        blk = out["suites"]["Swift-EAGLE"]["z0"]
        rows = blk["pairs"]["mass.total-to-rad2"]
        self.assertTrue(rows)
        for r in rows:
            self.assertAlmostEqual(r["median"], np.log10(0.7), places=3)
            self.assertIsNotNone(r["seedSe"])
        for nd, v in blk["gsmfShiftAtFixedNumberDensity"]["total-to-rad2"].items():
            self.assertIsNotNone(v["shiftDex"], nd)
            self.assertAlmostEqual(v["shiftDex"], np.log10(0.7), delta=0.02, msg=nd)
            self.assertIsNotNone(v["seedSe"], nd)
        other = out["suites"]["IllustrisTNG"]["z0"]["pairs"]["mass.total-to-rad2"]
        self.assertAlmostEqual(other[0]["median"], np.log10(0.8), places=3)       # the first three keep their own value


class Published(unittest.TestCase):
    def test_four_codes_and_where_they_were_read(self):
        self.assertEqual(list(DATA["suites"]), list(C.SUITES))
        self.assertEqual(C.SUITES[:3], ORIGINAL)
        self.assertIn("Swift-EAGLE", DATA["suites"])
        for code in ORIGINAL:
            self.assertTrue(DATA["suiteSources"][code].startswith("Sims/"), code)
        self.assertTrue(DATA["suiteSources"]["Swift-EAGLE"].startswith("FOF_Subfind/Swift-EAGLE/"))

    def test_structure(self):
        for suite in C.SUITES:
            for z in ("z0", "z0.95", "z2.15"):
                blk = DATA["suites"][suite][z]
                self.assertEqual(blk["nSeeds"], 27, (suite, z))
                self.assertIn("mass.total-to-rad2", blk["pairs"])
                for rows in blk["pairs"].values():
                    for r in rows:
                        self.assertGreaterEqual(r["n"], DATA["minPooledGalaxies"])
                        self.assertLessEqual(r["p16"], r["p84"])

    def test_half_mass_aperture_is_log_half(self):
        """The stars within the stellar half-mass radius are half of the stars, by definition of that radius."""
        for suite in C.SUITES:
            for z in ("z0", "z0.95", "z2.15"):
                for r in DATA["suites"][suite][z]["pairs"]["mass.total-to-rad1"]:
                    self.assertAlmostEqual(r["median"], np.log10(0.5), delta=0.012, msg=(suite, z, r["x"]))

    def test_aperture_never_adds_much_mass(self):
        for suite in C.SUITES:
            for r in DATA["suites"][suite]["z0"]["pairs"]["mass.total-to-rad2"]:
                self.assertLess(r["median"], 0.0)
                self.assertGreater(r["median"], -0.5)

    def test_sfr_aperture_ratio_near_one(self):
        """The documented claim in docs/CONVERSIONS.md for the first three codes: the SFR in the 2 R_half aperture is within 0.02 dex of the total, in the median. Swift-EAGLE is not held to it (its aperture SFR falls below the total at high mass, which the page reports)."""
        for suite in ORIGINAL:
            for r in DATA["suites"][suite]["z0"]["pairs"]["sfr.total-to-rad2"]:
                self.assertLess(abs(r["median"]), 0.02, (suite, r["x"]))

    def test_sfr_aperture_never_clearly_above_total(self):
        """An aperture inside the subhalo cannot have more SFR than the subhalo: no code may show a median above +0.02 dex."""
        for suite in C.SUITES:
            for r in DATA["suites"][suite]["z0"]["pairs"]["sfr.total-to-rad2"]:
                self.assertLess(r["median"], 0.02, (suite, r["x"]))

    def test_swift_eagle_sfr_aperture_deficit_is_reported_not_hidden(self):
        """The page says the Swift-EAGLE aperture SFR drops below the total at high mass; this checks that is what the data show (a value below -0.03 dex in some bin with 100 or more galaxies)."""
        rows = [r for r in DATA["suites"]["Swift-EAGLE"]["z0"]["pairs"]["sfr.total-to-rad2"] if r["n"] >= 100]
        self.assertLess(min(r["median"] for r in rows), -0.03)

    def test_gsmf_shift_matches_median_shift_roughly(self):
        """At fixed abundance the mass-function shift should lie within the spread of per-galaxy shifts, a consistency check between two independent measurements."""
        for suite in C.SUITES:
            blk = DATA["suites"][suite]["z0"]
            rows = blk["pairs"]["mass.total-to-rad2"]
            lo, hi = min(r["p16"] for r in rows), max(r["p84"] for r in rows)
            for nd, v in blk["gsmfShiftAtFixedNumberDensity"]["total-to-rad2"].items():
                if v["shiftDex"] is not None:
                    self.assertTrue(lo - 0.05 <= v["shiftDex"] <= hi + 0.05, (suite, nd, v, lo, hi))


if __name__ == "__main__":
    unittest.main(verbosity=1)
