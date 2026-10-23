#!/usr/bin/env bash
# Coverage of the code that matters: the package, the analyses and their statistics (Python, from the Python tests), and the comparison, export and observer libraries (JavaScript, from the Node tests). One-off ingestion scripts are left out on purpose: they run once and are checked by their own spot checks.
# Needs `pip install coverage` and, for JavaScript, `npm install --no-save c8`. Takes about 5 minutes.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export OPENBLAS_NUM_THREADS=1
rm -f .coverage
CORE="sim_highline.py,scripts/analyze_*.py,scripts/modelform_stats.py,scripts/vector_figure.py,scripts/export_retune_data.py,scripts/screen_outliers.py,scripts/power_*.py"
for t in scripts/test_*.py; do python3 -m coverage run -a --include="$CORE" "$t" > /dev/null; done
python3 -m coverage report --skip-empty | tee coverage-python.txt | tail -25
if npx --no-install c8 --version >/dev/null 2>&1; then
  npx --no-install c8 --include=compare.js --include=export-lib.js --include=observer-lib.js --include=highline/logic.js --reporter=text node scripts/test-compare.mjs > /dev/null 2>&1 || true
  npx --no-install c8 --include=compare.js --include=export-lib.js --include=observer-lib.js --include=highline/logic.js --reporter=text sh -c 'node scripts/test-compare.mjs; node scripts/test-export.mjs; node scripts/test-observer.mjs; node scripts/test-logic.mjs; node scripts/test-user-curves.mjs' | tee coverage-js.txt | tail -12
else
  echo "JavaScript coverage skipped: npm install --no-save c8 first"
fi
