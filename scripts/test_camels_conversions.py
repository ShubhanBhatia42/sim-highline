"""Tests for the measured conversions: the per-catalogue function recovers known shifts from a synthetic catalogue, and the published numbers pass the checks the catalogues allow (the half-mass aperture is log10(0.5) by definition; quantiles are ordered; the SFR aperture ratio is near 1)."""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ingest_camels_conversions as C  # noqa: E402

DATA = json.loads((HERE.parent / "data" / "conversions.json").read_text())


def synthetic(n=4000, seed=1):
    rng = np.random.default_rng(seed)
    h = 0.6711
    ms = 10 ** rng.uniform(9.0, 11.4, n) / 1e10 * h
    arr = {k: np.zeros((n, 6)) if k.endswith("Type") else np.zeros(n) for k in C.ARRAYS + C.GROUP_ARRAYS}
    arr["SubhaloMassType"][:, 4] = ms
    arr["SubhaloLenType"][:] = 500
    for lab, name in C.MASS_DEFS:
        arr[name][:, 4] = ms * 0.8
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


class Published(unittest.TestCase):
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
        """The documented claim in docs/CONVERSIONS.md: the SFR in the 2 R_half aperture is within 0.02 dex of the total, in the median."""
        for suite in C.SUITES:
            for r in DATA["suites"][suite]["z0"]["pairs"]["sfr.total-to-rad2"]:
                self.assertLess(abs(r["median"]), 0.02, (suite, r["x"]))

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
