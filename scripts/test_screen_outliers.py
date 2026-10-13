import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import screen_outliers as s


def frame():
    rows = []
    x = np.linspace(9, 11, 8)
    for i, src in enumerate("ABCDE"):
        off = 2.0 if src == "E" else 0.03 * i
        for xi in x:
            rows.append(dict(record_id=f"{src}.1", source=src, run="r", relation="sfms", kind="simulation", z=0.0, x_unit="log10(Msun)", y_unit="log10(Msun/yr)", metallicity_quantity=None, x=xi, y=0.8 * (xi - 10) + off))
    for xi in x:
        rows.append(dict(record_id="F.1", source="F", run="r", relation="sfms", kind="simulation", z=3.0, x_unit="log10(Msun)", y_unit="log10(Msun/yr)", metallicity_quantity=None, x=xi, y=99.0))
    return pd.DataFrame(rows)


res = {o["id"]: o for o in s.screen(frame())}
assert res["E.1"]["flag"] and abs(res["E.1"]["medianOffsetDex"] - 1.9) < 0.1, res["E.1"]
assert not any(res[k]["flag"] for k in "A.1 B.1 C.1 D.1".split())
assert "F.1" not in res, "a curve with no peers at its epoch must not be screened"
doc = json.loads((ROOT / "data" / "analysis" / "plausibility-screen.json").read_text())
assert doc["nFlagged"] == len(doc["flagged"]) and all(abs(o["medianOffsetDex"]) >= s.FLAG_DEX for o in doc["flagged"])
print("plausibility screen: OK")
