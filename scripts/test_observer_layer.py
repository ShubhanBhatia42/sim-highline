"""The saved observer-layer measurement (data/analysis/observer-layer.json and docs/OBSERVER-LAYER.md) is what scripts/analyze_observer_layer.py produces from the dataset now, its counts add up,
its classification is consistent with the per-pair numbers it lists, and the page keeps the plain statements about what the measurement does not show. If this fails after curves were added,
run python3 scripts/analyze_observer_layer.py and commit the two files."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import numpy as np  # noqa: F401
    import pandas  # noqa: F401
except ImportError:
    print("observer-layer test skipped: numpy/pandas not installed")
    raise SystemExit(0)
import analyze_observer_layer as A

saved = json.loads(A.OUT_JSON.read_text())
doc = A.OUT_DOC.read_text()
fresh = A.compute()
assert json.dumps(fresh, indent=1, ensure_ascii=False) + "\n" == A.OUT_JSON.read_text(), "data/analysis/observer-layer.json is not what the script produces from the current curves: run python3 scripts/analyze_observer_layer.py"
assert A.render(fresh) == doc, "docs/OBSERVER-LAYER.md is not what the script produces: run python3 scripts/analyze_observer_layer.py"

c = saved["counts"]
assert c["pairsTotal"] == c["simulationRecords"] * c["observationRecords"]
assert c["pairsTotal"] == c.get("notComparable", 0) + c.get("comparableButEpochsFarApart", 0) + c.get("populationMismatch", 0) + c["comparablePairs"]
assert c["comparablePairs"] == c["pairsMeasured"] + c.get("simulationCurveHasGapOver1dex", 0) + c.get("fewerThanMinBins", 0)
assert c["pairsMeasured"] == len(saved["pairs"]) >= 200

# classification: recomputed from the per-pair numbers
for sg in A.SIGMAS:
    b = saved["results"]["main"]["bySigma"][str(sg)]
    t = {"largerToSmaller": 0, "smallerToLarger": 0, "stayLarger": 0, "staySmaller": 0}
    none = 0
    for p in saved["pairs"]:
        k = A.classify(p["before"], p["after"][str(sg)], p["obsSigma"])
        if k is None:
            none += 1
        else:
            t[k] += 1
    assert all(b[k] == v for k, v in t.items()) and b["noObservationalUncertainty"] == none, (sg, b, t, none)
    assert b["largerBefore"] == t["largerToSmaller"] + t["stayLarger"] and b["largerAfter"] == t["smallerToLarger"] + t["stayLarger"]
    assert b["pairs"] == len(saved["pairs"]) == sum(t.values()) + none
# scatter never changes anything else: the 'before' numbers do not depend on sigma
assert len({p["before"] for p in saved["pairs"]}) > 50
# the pair rules were applied: no pair has a population mismatch or a non-comparable verdict
assert all(p["verdict"] in ("comparable", "comparable-with-caveats") for p in saved["pairs"])
assert not any("qsmf" in p["obs"] for p in saved["pairs"]), "a quiescent-galaxy mass function was paired with an all-galaxy simulation"

# the page keeps its plain statements and its numbers
for sentence in ("none is a calibrated model of any survey", "It does not show that any of the surveys has such scatter", "Internal checks only: no outside expert has reviewed this", "not evidence that any survey has that scatter"):
    assert sentence in doc, sentence
assert f"**{c['pairsMeasured']} pairs" in doc
for banned in (r"\bnovel\b", r"\bfirst of its kind\b", r"\bnew method\b", r"\bClaude\b", r"\bAI\b", r"\bLLM\b", r"\bS[1-5]\b"):
    assert not re.search(banned, doc), banned
print(f"observer-layer tests passed: the saved measurement ({c['pairsMeasured']} pairs) is what the script produces now, the counts add up and the classification follows from the per-pair numbers")
