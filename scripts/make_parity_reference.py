"""Reference predictions of the full (six-dimensional) emulators of the all-at-once analysis at random settings of the four dials, at the fiducial cosmology: the numbers the dials page must reproduce from the collapsed coefficients in data/retune/retune.json. Writes tests/parity/emulator-reference.json.
Rerun it when data/ensembles/camels-galaxies.json or the emulator settings change (scripts/test_parity.py says when). Usage: python3 scripts/make_parity_reference.py"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_joint_reachability as J
import analyze_model_form as A

ROOT = Path(__file__).resolve().parent.parent
N = 24


def main():
    data = J.load_galaxies()
    keep, blocks, _ = J.eligibility(data)
    emus, _ = J.build_emulators(data, keep)
    rng = np.random.default_rng(20261021)
    pts = rng.uniform(-1, 1, (N, 4))
    pts[0] = 0.0
    pts[1] = 1.0
    pts[2] = -1.0
    out = {"note": "log-scale predictions of the full emulators at the fiducial cosmology; points are the four astrophysical coordinates in [-1, 1]", "points": pts.round(6).tolist(),
           "data_sha256": hashlib.sha256((ROOT / "data" / "ensembles" / "camels-galaxies.json").read_bytes()).hexdigest(), "predictions": {}}
    for code in J.SUITES:
        P = A.predict_astro(emus[code], pts.round(6))[:, keep]
        out["predictions"][code] = [[None if not np.isfinite(v) else float(f"{v:.9g}") for v in row] for row in P]
    (ROOT / "tests" / "parity" / "emulator-reference.json").write_text(json.dumps(out, separators=(",", ":"), allow_nan=False) + "\n")
    print(f"parity reference: {N} points x {int(keep.sum())} outputs x {len(J.SUITES)} codes")


if __name__ == "__main__":
    main()
