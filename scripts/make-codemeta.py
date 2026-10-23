"""Writes codemeta.json (CodeMeta 2.0 / schema.org JSON-LD) from CITATION.cff and data/release.json, so that software indexes and Software Heritage read the same name, version, authors, licences and DOI as the citation file. Generated; do not edit by hand.
Usage: python3 scripts/make-codemeta.py"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rel = json.loads((ROOT / "data" / "release.json").read_text())
cff = (ROOT / "CITATION.cff").read_text()


def field(name):
    m = re.search(rf'^{name}:\s*"?([^"\n]+)"?\s*$', cff, re.M)
    return m.group(1).strip() if m else None


author = {"@type": "Person", "givenName": re.search(r"given-names:\s*(.+)", cff).group(1).strip(), "familyName": re.search(r"family-names:\s*(.+)", cff).group(1).strip()}
email = re.search(r"email:\s*(\S+)", cff)
if email:
    author["email"] = email.group(1)
doc = {
    "@context": "https://doi.org/10.5063/schema/codemeta-2.0",
    "@type": "SoftwareSourceCode",
    "name": "sim-highline",
    "description": "Galaxy scaling relations from cosmological simulations and observations, with the definitions that decide whether two curves can be compared: a dataset, an Explorer, a Python loader and four pre-registered studies.",
    "version": rel["version"],
    "dateModified": rel["released"],
    "identifier": f"https://doi.org/{rel['doi']}",
    "codeRepository": rel["repo"],
    "issueTracker": rel["repo"] + "/issues",
    "license": ["https://spdx.org/licenses/MIT", "https://spdx.org/licenses/CC-BY-4.0"],
    "author": [author],
    "programmingLanguage": ["Python", "JavaScript"],
    "keywords": ["astronomy", "galaxy formation", "cosmological simulations", "scaling relations", "open data"],
    "readme": rel["repo"] + "/blob/main/README.md",
    "developmentStatus": "active",
    "runtimePlatform": "Python 3.9+, Node 22 (build and tests)",
    "softwareRequirements": ["numpy", "pandas"],
    "isAccessibleForFree": True,
}
swh = re.search(r"value:\s*(swh:1:snp:[0-9a-f]{40})", cff)
if swh:
    doc["sameAs"] = ["https://archive.softwareheritage.org/" + swh.group(1)]
(ROOT / "codemeta.json").write_text(json.dumps(doc, indent=2) + "\n")
print("wrote codemeta.json")
