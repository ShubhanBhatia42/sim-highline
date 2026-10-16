"""The dials page evaluates the emulators from data/retune/retune.json; the analysis evaluates the full ones. At random dial settings (tests/parity/emulator-reference.json) they must give the same numbers: (1) the reference is not stale (recomputed here from the data), (2) the collapsed coefficients in retune.json, evaluated in Python, reproduce it. scripts/test-parity.mjs checks the page's own JavaScript against the same reference."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_joint_reachability as J
import analyze_model_form as A

ROOT = Path(__file__).resolve().parent.parent
ref = json.loads((ROOT / "tests" / "parity" / "emulator-reference.json").read_text())
rt = json.loads((ROOT / "data" / "retune" / "retune.json").read_text())
pts = np.array(ref["points"])
bad = []
# (1) the reference follows the data
data = J.load_galaxies()
keep, blocks, _ = J.eligibility(data)
emus, _ = J.build_emulators(data, keep)
for code in J.SUITES:
    fresh = A.predict_astro(emus[code], pts)[:, keep]
    saved = np.array([[np.nan if v is None else v for v in r] for r in ref["predictions"][code]])
    if not np.allclose(fresh, saved, rtol=0, atol=1e-7, equal_nan=True):
        bad.append(f"{code}: the saved reference differs from the emulators by {np.nanmax(np.abs(fresh - saved)):.2e}; rerun scripts/make_parity_reference.py")
# (2) the exported polynomial reproduces it (coefficients are stored to six significant digits)
worst = 0.0
for code in J.SUITES:
    q = rt["codes"][code]
    coef = np.array([[np.nan if v is None else v for v in row] for row in q["coef"]])
    saved = np.array([[np.nan if v is None else v for v in r] for r in ref["predictions"][code]])
    for a, want in zip(pts, saved):
        t = np.array([np.prod([a[j] for j in term]) if term else 1.0 for term in q["terms"]])
        got = t @ coef
        ok = np.isfinite(want)
        if not np.array_equal(ok, np.isfinite(got)):
            bad.append(f"{code}: a different set of outputs is undefined at {a.round(2)}")
            continue
        worst = max(worst, float(np.max(np.abs(got[ok] - want[ok]))))
if worst > 2e-4:
    bad.append(f"the exported coefficients reproduce the emulators only to {worst:.2e} (limit 2e-4)")
if len(rt["outputs"]) != len(ref["predictions"]["IllustrisTNG"][0]):
    bad.append("the number of exported outputs differs from the reference")
if bad:
    print("parity:\n  " + "\n  ".join(bad)); sys.exit(1)
print(f"parity: OK (retune.json reproduces the full emulators at {len(pts)} dial settings to {worst:.1e}; the reference is current)")
