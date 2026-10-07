#!/usr/bin/env bash
# The whole offline verification chain, in one place (used by CONTRIBUTING.md and by CI). Needs node and python3 with requirements-dev.txt.
# Run from the repository root. Regenerates derived files; commit them if they change.
set -euo pipefail
node scripts/annotate-definitions.mjs
node scripts/validate-curves.mjs
node scripts/validate-manifest.mjs
node scripts/test-curves.mjs
node scripts/test-compare.mjs
node scripts/report-coverage.mjs
node scripts/build-curve-index.mjs
node scripts/export-dataset.mjs
node scripts/test-export.mjs
node scripts/build-static.mjs
node scripts/build-highline.mjs
node scripts/test-static.mjs
node scripts/test-logic.mjs
python3 scripts/build-literature-backlog.py
node scripts/test-literature.mjs
node scripts/test-notes.mjs
node scripts/test-profiles.mjs
node scripts/make-audit-sample.mjs
node scripts/make-author-requests.mjs
node scripts/make-heads-up.mjs
node scripts/build-site.mjs
node scripts/test-site.mjs
for t in scripts/test_*.py; do python3 "$t"; done
AUDIT=$(mktemp)
node scripts/audit-curves.mjs > "$AUDIT"
head -1 "$AUDIT"
grep -q "0 errors, 0 warnings" "$AUDIT" || { echo "audit is not clean"; exit 1; }
echo "verify-all: OK"
