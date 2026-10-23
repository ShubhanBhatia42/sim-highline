# What only you can do, in order

Nothing below has been done for you, and nothing has been sent. Each item names the text that is ready, what to send it with, and what to write down afterwards. The project's own success measures (`PROJECT.md`) count people, not releases, so items 2 to 5 matter more than any feature.

| # | do this | ready text | send with | write down |
|---|---|---|---|---|
| 1 | **Publish release v0.24.0 on GitHub** from `main` (Releases, Draft a new release, tag `v0.24.0` on `main`). Automation cannot create tags here (HTTP 403), so this is yours. Zenodo archives a published release by itself. | `RELEASE-CHECKLIST.md` item 7 | nothing | The new version's DOI; tell me and it goes into `CITATION.cff`. |
| 2 | **Three pilot sessions** (an observer, a simulator, a student; none who watched it being built). 25 minutes each, you say nothing beyond the first line. | `outreach/PILOT.md` | the address of the site only | `outreach/pilot-log.md` (create it); words they did not understand; what they asked for that is missing. |
| 3 | **One expert per suite checks two records.** Start with FLAMINGO, NewHorizon, Illustris/TNG, EAGLE or Horizon-AGN. | `expert-audit-request.md`, records in `expert-audit-sample.md` | the two record links and `site/methods.html` | `data/audit-outcomes.json` (record, reviewer or "anonymous", verdict). One reply counts for more than anything internal. |
| 4 | **Ask one person in CAMELS whether the main results are already known.** | `RESEARCH-NOTE.md` (read it first) and `ANALYSIS-quenching-shape.md` | the note and the two study pages | Their words. If it is known, say so on the pages. |
| 5 | **Ask the authors of the biggest figure-read sources for their tables.** | `author-requests.md`; the list of who has released what is in `analysis/released-tables.json` (FLAMINGO, 176 curves, is on request only) | one paper per message | The reply, and the file if they send one (tier `official-table`, with checksum). |
| 6 | **Post the issues about the comparison-data compilation**, if you agree with them. | `UPSTREAM-ISSUES.md` | the file paths and quotes in each draft | Their answers. |
| 7 | **One-line definition questions to authors** (the count is at the top of the file; it changes whenever records are added). | `AUTHOR-QUESTIONS.md` | the message at the top | Answers go into `data/definition-fills.json` as sourced rules. |
| 8 | **Name a backup maintainer.** | `GOVERNANCE.md` | the handover list in it | Their name in `GOVERNANCE.md`. |
| 9 | **Decide what to do with the data note** (a short paper about the dataset and its method). | `DATA-NOTE.md` | | The venue, and whether to go ahead. |

Two things are not yours to do but are worth knowing: the checks of 50 compilation curves against their papers (`COMPILATION-CHECK.md`) and the raster re-digitization (`DATA-QUALITY.md`) were made by one reader and have had no outside review. Item 3 is the way to change that.
