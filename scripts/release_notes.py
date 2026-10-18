"""The text of one release, for the GitHub release page: the section of CHANGELOG.md for that version, plus how to cite it.
Refuses to run when the tag does not match data/release.json, so a tag cannot publish a release of the wrong version.
Usage: python3 scripts/release_notes.py v0.24.0 > notes.md"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
    version = tag.lstrip("v")
    rel = json.loads((ROOT / "data" / "release.json").read_text())
    if rel["version"] != version:
        sys.exit(f"tag {tag} does not match data/release.json (version {rel['version']}); run scripts/release.sh first")
    text = (ROOT / "CHANGELOG.md").read_text()
    m = re.search(rf"(?ms)^## {re.escape(version)}\b[^\n]*\n(.*?)(?=^## |\Z)", text)
    if not m:
        sys.exit(f"CHANGELOG.md has no section for {version}")
    body = m.group(1).strip()
    print(body)
    print(f"\n---\n\nCite the dataset with the Zenodo DOI for all versions, https://doi.org/{rel['doi']}, and the original paper of every curve you use (the Explorer's Get data panel writes the BibTeX). Site: https://shubhanbhatia42.github.io/sim-highline/")


if __name__ == "__main__":
    main()
