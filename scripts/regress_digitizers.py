import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
only = sys.argv[1:]
FILLS = {f["id"]: set(f["set"]) for f in json.loads((ROOT / "data" / "definition-fills.json").read_text())["fills"]}
SUPERSEDED = {"transcribe_colibre_gsmf_small_boxes.py"}
# records that the authors' own numbers replaced after the figure was read: the digitizer still makes the figure read, and the table script then replaces those records in place, as it did for the dataset
REPLACED_BY_TABLE = {"digitize_nihao_blank19.py": "ingest_nihao_bh_blank19_table.py", "digitize_nihao_tf_dutton17.py": "ingest_nihao_tf_dutton17_table.py", "digitize_thesan_kannan22_uvlf_sfrd.py": "ingest_thesan1_sfrd_kannan22.py"}
scripts = sorted(p for p in (ROOT / "scripts").glob("*.py") if p.name.startswith(("digitize_", "transcribe_")) and p.name not in SUPERSEDED and (not only or any(o in p.name for o in only)))
bad = []
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    shutil.copytree(ROOT / "scripts", tmp / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp / "data" / "curves").mkdir(parents=True)
    (tmp / "data" / "staged").mkdir(parents=True)  # a digitizer may write records that are held back from the dataset
    for s in scripts:
        r = subprocess.run([sys.executable, str(tmp / "scripts" / s.name)], capture_output=True, text=True, cwd=tmp / "scripts", env={**os.environ, "SIMHIGHLINE_REFERENCE_ROOT": str(ROOT)})
        if r.returncode:
            bad.append((s.name, "failed: " + (r.stderr.strip().splitlines() or ["?"])[-1]))
        elif s.name in REPLACED_BY_TABLE:
            r = subprocess.run([sys.executable, str(tmp / "scripts" / REPLACED_BY_TABLE[s.name])], capture_output=True, text=True, cwd=tmp / "scripts", env={**os.environ, "SIMHIGHLINE_REFERENCE_ROOT": str(ROOT)})
            if r.returncode:
                bad.append((REPLACED_BY_TABLE[s.name], "failed: " + (r.stderr.strip().splitlines() or ["?"])[-1]))
    for out in sorted((tmp / "data" / "curves").glob("*.json")):
        ref = ROOT / "data" / "curves" / out.name
        b = json.loads(ref.read_text())["records"] if ref.exists() else []
        # definition values recovered from source papers are owned by scripts/annotate-definitions.mjs (data/definition-fills.json), not by the digitizers
        filled = {r["id"]: {k for fid in r.get("provenance", {}).get("definitionFills", []) for k in FILLS.get(fid, ())} for r in b}

        def norm(rs):
            for r in rs:
                r.get("provenance", {}).pop("terms", None)  # owned by scripts/annotate-definitions.mjs (data/source-terms.json)
                r.get("provenance", {}).pop("definitionFills", None)
                for k in filled.get(r["id"], ()):
                    r.get("definitions", {}).pop(k, None)
            return rs
        a, b = norm(json.loads(out.read_text())["records"]), norm(b)
        if a != b:
            ia, ib = {r["id"]: r for r in a}, {r["id"]: r for r in b}
            bad.append((out.name, f"differs: {len(set(ia) - set(ib))} new, {len(set(ib) - set(ia))} missing, {sum(1 for k in ia.keys() & ib.keys() if ia[k] != ib[k])} changed"))
    n = len(list((tmp / "data" / "curves").glob("*.json")))
for name, why in bad:
    print("FAIL", name, why)
print(f"Digitizer regression: {len(scripts)} scripts, {n} output files, {len(bad)} problems")
sys.exit(1 if bad else 0)
