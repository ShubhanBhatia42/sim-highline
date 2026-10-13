import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_definition_budget as a

root = a.ROOT
recs, rb = a.load(), a.rules()
fresh = {"allRecords": a.analyse(recs, rb, False)}
saved = json.load(open(root / "data/analysis/definition-budget.json"))
assert json.loads(json.dumps(fresh["allRecords"])) == json.loads(json.dumps(saved["allRecords"])) or \
    all(abs((x.get("excess_differing_minus_matched") or 0) - (y.get("excess_differing_minus_matched") or 0)) < 1e-3 and x["counts"] == y["counts"]
        for x, y in zip(fresh["allRecords"], saved["allRecords"])), "analysis output is stale; rerun analyze_definition_budget.py"
assert saved["summary"]["pairs"] == sum(saved["summary"]["byClass"].values())
for r in saved["allRecords"]:
    assert len(r["suites"]) >= 3 and r["pairs"] == sum(r["counts"].values())
    if r.get("p_permutation") is not None: assert 0 < r["p_permutation"] <= 1
assert "do not edit by hand" in (root / "docs/ANALYSIS-definition-budget.md").read_text()
print("definition budget: OK")
