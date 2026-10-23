#!/usr/bin/env bash
# The whole offline verification chain, in one place (used by CONTRIBUTING.md and by CI). Needs node and python3 with requirements-dev.txt.
# Run from the repository root. Regenerates derived files; commit them if they change.
set -euo pipefail
# The three slow Python tests (a few minutes together) are skipped when nothing they can read has changed since they last passed here (stamp in .verify-cache/). FRESH=1 runs them anyway; CI starts without stamps, so it always runs everything.
SLOW="test_joint_reachability test_model_form test_harmonization test_quenching_shape"
stamp_of() { cat scripts/*.py data/ensembles/*.json data/analysis/*.json data/retune/retune.json 2>/dev/null | sha256sum | cut -d' ' -f1; }
python3 scripts/ingest_camels_distributions.py --records
python3 scripts/ingest_darwin1_catalogue.py --records
node scripts/derive-distributions.mjs
python3 scripts/ingest_camels_conversions.py --derive
python3 scripts/make-conversions-doc.py
python3 scripts/make-compilation-check-doc.py
node scripts/apply-compilation-corrections.mjs
node scripts/apply-attribution.mjs
node scripts/annotate-definitions.mjs
node scripts/validate-curves.mjs
node scripts/validate-manifest.mjs
node scripts/test-curves.mjs
node scripts/test-compare.mjs
node scripts/test-distributions.mjs
node scripts/test-compilation-corrections.mjs
node scripts/test-submission.mjs
node scripts/test-attribution.mjs
node scripts/test-staged.mjs
node scripts/report-coverage.mjs
python3 scripts/analyze_definition_budget.py > /dev/null
python3 scripts/analyze_harmonization.py > /dev/null
# the model-form analysis takes about 20 minutes: FULL=1 reruns it; scripts/test_model_form.py always checks that its saved output is not stale
if [ "${FULL:-0}" = "1" ]; then python3 scripts/analyze_model_form.py > /dev/null; fi
# the quenching-shape analysis is a one-time registered run (docs/PROTOCOL-quenching-shape.md); FULL=1 reruns it, scripts/test_quenching_shape.py checks that its saved output is not stale
if [ "${FULL:-0}" = "1" ]; then python3 scripts/analyze_quenching_shape.py > /dev/null; fi
python3 scripts/screen_outliers.py
node scripts/report-undocumented.mjs
node scripts/build-curve-index.mjs
node scripts/export-dataset.mjs
node scripts/test-export.mjs
python3 scripts/analyze_data_quality.py > /dev/null
python3 scripts/make-data-note.py > /dev/null
node scripts/build-static.mjs
node scripts/build-highline.mjs
node scripts/test-static.mjs
node scripts/test-logic.mjs
node scripts/test-user-curves.mjs
python3 scripts/build-literature-backlog.py
node scripts/test-literature.mjs
node scripts/test-notes.mjs
node scripts/test-profiles.mjs
node scripts/make-audit-sample.mjs
node scripts/make-author-requests.mjs
node scripts/make-heads-up.mjs
node scripts/make-outreach.mjs
node scripts/make-author-questions.mjs
node scripts/build-site.mjs
node scripts/test-site.mjs
node scripts/test-usage-counts.mjs
node scripts/lint.mjs
python3 scripts/check_prose.py
python3 scripts/audit_conversions.py   # refreshes the record counts; the comparison-compilation numbers are kept unless a clone of that repository is given
python3 scripts/audit_conversions.py --check
python3 scripts/make-codemeta.py
python3 scripts/make-scripts-index.py
STAMP=$(stamp_of); mkdir -p .verify-cache
for t in scripts/test_*.py; do
  n=$(basename "$t" .py)
  if [[ " $SLOW " == *" $n "* && "${FRESH:-0}" != "1" && -f ".verify-cache/$n" && "$(cat ".verify-cache/$n")" == "$STAMP" ]]; then echo "$n: unchanged since the last pass, skipped (FRESH=1 to run it anyway)"; continue; fi
  python3 "$t"
  [[ " $SLOW " == *" $n "* ]] && echo "$STAMP" > ".verify-cache/$n"
done
AUDIT=$(mktemp)
node scripts/audit-curves.mjs > "$AUDIT"
head -1 "$AUDIT"
grep -q "0 errors, 0 warnings" "$AUDIT" || { echo "audit is not clean"; exit 1; }
echo "verify-all: OK"
