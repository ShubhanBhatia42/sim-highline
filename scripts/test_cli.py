"""The Python side of "check your own run": the curve reader on the five realistic messy inputs, the command line, and that every code cell of the notebook runs."""
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
try:
    import numpy as np
    import pandas  # noqa: F401
except ImportError:
    print("cli: skipped, numpy or pandas not installed")
    raise SystemExit(0)
import sim_highline as sh

# the reader agrees with the browser on how many points each realistic input holds
expect = {"1-linear-tab-comments.txt": 8, "2-semicolon-decimal-comma.csv": 7, "3-bom-crlf-header.csv": 7, "4-sfr-linear-whitespace.txt": 5, "5-units-row-and-nan.csv": 6}
for f, n in expect.items():
    x, y, e = sh.read_curve(ROOT / "tests" / "user-curves" / f)
    assert len(x) == n, f"{f}: {len(x)} points, expected {n}"
x, y, e = sh.read_curve(ROOT / "tests" / "user-curves" / "2-semicolon-decimal-comma.csv")
assert abs(x[0] - 8.0) < 1e-9 and abs(y[0] + 0.67) < 1e-9 and abs(e[0] - 0.05) < 1e-9, "decimal commas"

# the command line
r = subprocess.run([sys.executable, str(ROOT / "sim_highline.py"), "compare", str(ROOT / "tests/user-curves/3-bom-crlf-header.csv"), "--relation", "gsmf", "--z", "0.1", "--define", "imf=chabrier03", "--define", "densityFrame=comoving", "--top", "3"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr[-300:]
assert "7 points read" in r.stdout and "Your run is" in r.stdout, r.stdout[:300]
r = subprocess.run([sys.executable, str(ROOT / "sim_highline.py"), "compare", str(ROOT / "tests/user-curves/3-bom-crlf-header.csv"), "--relation", "gsmf", "--z", "0.1"], capture_output=True, text=True)
assert "nothing can be called comparable" in r.stdout and "None of the" in r.stdout, "with no definitions the answer says nothing is comparable"
bad = subprocess.run([sys.executable, str(ROOT / "sim_highline.py"), "compare", str(ROOT / "README.md"), "--relation", "gsmf", "--z", "0.1"], capture_output=True, text=True)
assert bad.returncode != 0 and "fewer than three" in (bad.stderr + bad.stdout), "a file with no numbers is refused with a clear message"

# every code cell of the notebook runs from the repository root
import os
os.chdir(ROOT)
nb = json.loads((ROOT / "notebooks" / "compare-your-run.ipynb").read_text())
import matplotlib
matplotlib.use("Agg")
g = {}
for cell in nb["cells"]:
    if cell["cell_type"] == "code":
        src = "".join(cell["source"]).replace("plt.show()", "plt.close('all')")
        exec(compile(src, "notebook cell", "exec"), g)
print("cli: OK")
