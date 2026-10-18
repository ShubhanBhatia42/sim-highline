#!/usr/bin/env bash
# One command from "the work is done" to "ready to tag": bump the version, put it in every place that carries it, rebuild, verify, and print the exact commands to commit, tag and publish. It never pushes and never tags.
#   scripts/release.sh 0.24.0 "one-line summary of what changed"
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
V="${1:?usage: scripts/release.sh X.Y.Z \"summary\"}"; MSG="${2:?a one-line summary is required}"
[[ "$V" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "version must look like 1.2.3"; exit 1; }
git diff --quiet || { echo "commit or stash your changes first: the release commit should contain only the release"; exit 1; }
TODAY=$(date -u +%F)
python3 - "$V" "$TODAY" <<'PY'
import json, re, sys
v, d = sys.argv[1:3]
r = json.load(open("data/release.json")); r["version"], r["released"] = v, d
open("data/release.json", "w").write(json.dumps(r, indent=2) + "\n")
c = open("CITATION.cff").read()
c = re.sub(r"(?m)^version: .*$", f"version: {v}", c); c = re.sub(r"(?m)^date-released: .*$", f"date-released: {d}", c)
open("CITATION.cff", "w").write(c)
z = json.load(open(".zenodo.json")); z["version"] = v
open(".zenodo.json", "w").write(json.dumps(z, indent=2) + "\n")
PY
python3 - "$V" "$TODAY" "$MSG" <<'PY'
import sys
v, d, msg = sys.argv[1:4]
t = open("CHANGELOG.md").read()
head, sep, rest = t.partition("\n## ")
import re as _re
if _re.search(r"(?m)^## Unreleased", t):  # the work was logged as it was done: that section becomes this release
    t = _re.sub(r"(?m)^## Unreleased[^\n]*\n", f"## {v} ({d})\n\n- {msg}\n", t, count=1)
    open("CHANGELOG.md", "w").write(t)
else:
    open("CHANGELOG.md", "w").write(f"{head}\n## {v} ({d})\n\n- {msg}\n\n## {rest}" if sep else t + f"\n## {v} ({d})\n\n- {msg}\n")
PY
node scripts/build-static.mjs >/dev/null && node scripts/build-highline.mjs >/dev/null && node scripts/build-site.mjs >/dev/null
./scripts/verify-all.sh
node scripts/lint.mjs
cat <<EOF

Release $V is prepared and verified. Review the diff, then:
  git add -A && git commit -m "Release $V: $MSG"
  git tag -a v$V -m "$MSG"
  # after it is merged to main:  git push origin v$V   (the release workflow then publishes the GitHub release from the tag, and Zenodo archives that release if its integration is on)
EOF
