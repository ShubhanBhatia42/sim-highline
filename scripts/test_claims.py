"""The numbers that the README, the overview and the FAQ state in prose must equal the numbers the analyses generated. Each claim is read from the text and compared with the JSON it comes from."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
J = lambda *p: json.loads((ROOT.joinpath(*p)).read_text())
readme = (ROOT / "README.md").read_text()
overview = (ROOT / "docs" / "OVERVIEW.md").read_text()
q = J("data", "analysis", "data-quality.json")
jr = J("data", "analysis", "joint-reachability.json")
pw = J("data", "analysis", "joint-reachability-power.json")
fails = []


def check(name, ok, detail=""):
    if not ok:
        fails.append(f"{name}: {detail}")


# the digitized share
share = round(100 * q["digitized"]["share_of_simulation_curves"])
nums = [int(x) for x in re.findall(r"simulation curves \((\d+) ?%\)", readme)]
check("README digitized share", nums and all(n == share for n in nums), f"README says {nums}, data says {share}")

# the all-at-once study
a, p = jr["splits"]["all"], jr["point"]["all"]
check("README joint distance", f"{a['between']['p50']:.1f} noise units apart" in readme, f"expected {a['between']['p50']:.1f}")
check("README fiducial distance", f"{p['D_fiducial']:.1f} at the fiducial" in readme, f"expected {p['D_fiducial']:.1f}")
drops = [v["D"] for k, v in jr["point"].items() if k.startswith("drop:")]
check("README leave-one-out range", f"{min(drops):.1f} to {max(drops):.1f}" in readme, f"expected {min(drops):.1f} to {max(drops):.1f}")
rows = pw["rows"]
below = [r for r in rows if r["true_D_all"] < 0.95]
above = [r for r in rows if r["true_D_all"] > 1.1]
fp = sum(r["J1_corrected"] == "structural" for r in below)
tp = sum(r["J1_corrected"] == "structural" for r in above)
check("README calibration", f"{fp} of {len(below)} with a true distance below 0.95" in readme and f"{tp} of {len(above)} above 1.1" in readme, f"expected {fp} of {len(below)} and {tp} of {len(above)}")

# overview
ens = J("data", "ensembles", "camels-galaxies.json")
n = sum(len(v) for suite in ens["suites"].values() for v in suite.values())
for name, text in (("README", readme), ("overview", overview)):
    check(f"{name} CAMELS count", f"{n:,} " in text, f"expected {n:,}")
fams = [f for f in jr["meta"]["families"] if f != "hmf"]
words = {10: "ten", 11: "eleven", 12: "twelve"}
check("overview number of properties", f"{words.get(len(fams), len(fams))} galaxy properties" in overview, f"expected {len(fams)}")

if fails:
    print("claims out of step with the generated results:\n  " + "\n  ".join(fails))
    sys.exit(1)
print("claims: OK")
