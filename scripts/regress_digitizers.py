import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
only = sys.argv[1:]
SUPERSEDED = {"transcribe_colibre_gsmf_small_boxes.py"}
scripts = sorted(p for p in (ROOT / "scripts").glob("*.py") if p.name.startswith(("digitize_", "transcribe_")) and p.name not in SUPERSEDED and (not only or any(o in p.name for o in only)))
bad = []
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    shutil.copytree(ROOT / "scripts", tmp / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp / "data" / "curves").mkdir(parents=True)
    for s in scripts:
        r = subprocess.run([sys.executable, str(tmp / "scripts" / s.name)], capture_output=True, text=True, cwd=tmp / "scripts")
        if r.returncode:
            bad.append((s.name, "failed: " + (r.stderr.strip().splitlines() or ["?"])[-1]))
    for out in sorted((tmp / "data" / "curves").glob("*.json")):
        ref = ROOT / "data" / "curves" / out.name
        a = json.loads(out.read_text())["records"]
        b = json.loads(ref.read_text())["records"] if ref.exists() else []
        if a != b:
            ia, ib = {r["id"]: r for r in a}, {r["id"]: r for r in b}
            bad.append((out.name, f"differs: {len(set(ia) - set(ib))} new, {len(set(ib) - set(ia))} missing, {sum(1 for k in ia.keys() & ib.keys() if ia[k] != ib[k])} changed"))
    n = len(list((tmp / "data" / "curves").glob("*.json")))
for name, why in bad:
    print("FAIL", name, why)
print(f"Digitizer regression: {len(scripts)} scripts, {n} output files, {len(bad)} problems")
sys.exit(1 if bad else 0)
