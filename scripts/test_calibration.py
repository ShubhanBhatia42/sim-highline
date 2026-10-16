"""The calibration on synthetic worlds (docs/POWER-joint-reachability.md) used the same settings as the analysis that was finally run: same block layout, margin, noise floor, and the numbers quoted in the calibration text are the ones in its data file."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import analyze_joint_reachability as J

real = json.loads((ROOT / "data" / "analysis" / "joint-reachability.json").read_text())
pw = json.loads((ROOT / "data" / "analysis" / "joint-reachability-power.json").read_text())
doc = (ROOT / "docs" / "POWER-joint-reachability.md").read_text()
bad = []

# the synthetic worlds have the layout of the real eligible outputs (bins per family and epoch)
snaps = real["meta"]["snapshots"]
real_layout = {f: [len(real["meta"]["blocks"].get(f"{f}|{s}", {}).get("outputs", [])) for s in snaps] for f in J.FAMILIES}
if real_layout != pw["layout"]:
    bad.append(f"block layout differs: real {real_layout} vs calibration {pw['layout']}")
if pw["n_outputs"] != real["meta"]["n_outputs_eligible"]:
    bad.append(f"outputs: calibration {pw['n_outputs']} vs analysis {real['meta']['n_outputs_eligible']}")
# the same rule constants
if real["meta"]["margin"] != J.MARGIN or real["meta"]["floor"] != J.FLOOR:
    bad.append("the analysis' margin or floor differs from the module constants the calibration imports")
# the calibration text quotes the analysis' own layout
joint_blocks = sum(1 for k in real["meta"]["blocks"] if not k.startswith("hmf|"))
joint_outputs = sum(len(v["outputs"]) for k, v in real["meta"]["blocks"].items() if not k.startswith("hmf|"))
m = re.search(r"\((\d+) joint blocks, (\d+) outputs", doc)
if not m or (int(m.group(1)), int(m.group(2))) != (joint_blocks, joint_outputs):
    bad.append(f"calibration text says {m.groups() if m else None} but the analysis has {joint_blocks} blocks and {joint_outputs} outputs")
if f"seed {pw['seed']}" not in doc:
    bad.append("the seed in the calibration text is not the seed in its data file")
# the headline counts of the reading come from the rows
low = [r for r in pw["rows"] if r["true_D_all"] < 0.95]
high = [r for r in pw["rows"] if r["true_D_all"] > 1.1]
m = re.search(r"Among the (\d+) runs whose true joint distance is below 0\.95 .*?, (\d+) receive a structural joint verdict with the emulator-corrected rule .*? among the (\d+) runs above 1\.1 .*?, (\d+) and (\d+) do", doc, re.S)
if not m:
    bad.append("the reading paragraph of the calibration text was not found")
else:
    nl, fl, nh, ch, rh = map(int, m.groups())
    got = (len(low), sum(r["J1_corrected"] == "structural" for r in low), len(high), sum(r["J1_corrected"] == "structural" for r in high), sum(r["J1_raw"] == "structural" for r in high))
    if (nl, fl, nh, ch, rh) != got:
        bad.append(f"calibration text quotes {(nl, fl, nh, ch, rh)} but its rows give {got}")
if bad:
    print("calibration check:\n  " + "\n  ".join(bad)); sys.exit(1)
print(f"calibration check: OK (layout {pw['n_outputs']} outputs, margin {J.MARGIN}, floor {J.FLOOR}; {len(low)} worlds below the margin, {len(high)} above, counts match the text)")
