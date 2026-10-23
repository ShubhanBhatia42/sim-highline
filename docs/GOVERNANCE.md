# Who looks after this, and what happens if they cannot

## Now

- **Maintainer:** Shubhan Bhatia (GitHub `ShubhanBhatia42`). Owns the repository, the GitHub Pages site, the Zenodo link and the DOI.
- **Backup maintainer:** none yet. This file is the case for naming one and the list of what they would need.

## Why a backup matters here

The success measures in `PROJECT.md` are about people outside the project, and a data resource that nobody can correct is worse than none. The stopping rule archives the project as a dataset if nobody uses it; it does not say what happens if the one person who can publish stops answering. These are the single points of failure today:

| what | held by | what breaks if it is lost |
|---|---|---|
| the GitHub repository and Pages site | the maintainer's GitHub account | the live site and the place to report errors |
| the Zenodo link and DOI | the maintainer's Zenodo account, linked to GitHub | new versions cannot be archived; old DOIs keep working |
| tags and releases | only the maintainer can publish them (automation gets HTTP 403) | no new citable version |
| the knowledge of how a record is made | `CONTRIBUTING.md`, `docs/METHODS.md`, the ingest scripts | slowed corrections |

## What is already redundant

- **Zenodo** holds a version of the dataset with a DOI. **Software Heritage** archived the repository (save request 2567167 on 2026-10-21; the first attempt failed and the second visit, the same day, succeeded as a full snapshot). Its identifier, `swh:1:snp:3c71d0fd02f3a1436c56a78f02e6a2ce348496d2`, is in `CITATION.cff` and `codemeta.json`; it identifies the repository as it stood on that date, not a release, and a later visit gives a new one. The repository is public under MIT and CC-BY-4.0, so anyone may fork and continue it.
- Nothing needs a secret: the repository holds no tokens, the site is built by a workflow from the repository, and the data are plain JSON and CSV.
- `./scripts/verify-all.sh` rebuilds and checks everything offline; a new maintainer can tell in one run whether the dataset is in a good state.

## What a backup maintainer would need

1. Write access to the repository (or admin on a GitHub organisation that holds it) and an agreement on who may publish releases.
2. The release steps in `docs/RELEASE-CHECKLIST.md`, and the Zenodo account link (GitHub Settings, Applications, Zenodo) or their own Zenodo account added as a co-owner of the record.
3. The rules that make the data trustworthy, which are the project's: a record needs its source and two checks against numbers the paper prints; digitized curves are never rankable; a correction is logged in `docs/CORRECTIONS.md` with its evidence; the four registered studies are never rewritten, only amended in public.
4. Two hours with the maintainer to read `docs/ARCHITECTURE.md` and run the verification chain.

## Asking someone

> I maintain sim-highline, an open dataset of published galaxy scaling relations with the definitions that decide whether two curves can be compared (https://shubhanbhatia42.github.io/sim-highline/). It currently depends on me alone for publishing releases and keeping the site up. Would you be willing to be the named backup: write access, a shared view of corrections, and the authority to publish a release if I cannot? It would take about two hours to set up and nothing after that unless I am unavailable. `docs/GOVERNANCE.md` lists exactly what it involves.

## If nobody is available

If no maintainer has responded to an issue or pull request for twelve months, anyone may fork the repository, keep the licences and the citation to the DOI above, and continue under another name. The live site and the Zenodo record stay as they are.
