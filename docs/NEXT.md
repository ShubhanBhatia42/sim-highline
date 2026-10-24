# What would make it great, next

Written 2026-10-23, replacing the list of 2026-10-16. In order of how much each would change the answer to "is this worth continuing?". Items that need a person are marked **(you)**. `docs/SEND-THIS-WEEK.md` has the same items as an ordered list with the text that is ready for each.

## 0. Publish the release **(you)**

No release has been published for 0.24.0 (GitHub refuses release and tag creation from the automated session, HTTP 403), so no Zenodo archive and no DOI of this version exist. `main` has moved on since 0.24.0 (commit `b8e0315`): it now also carries the work listed in `CHANGELOG.md` under "Unreleased", while the files still say 0.24.0. Tagging `v0.24.0` on today's `main` would put that work under the old number. Choose one:

- **One release, 0.25.0 (recommended).** Run `scripts/release.sh 0.25.0 "summary"`, which turns "Unreleased" into 0.25.0, bumps every file that carries the version and verifies; commit and merge it, then publish `v0.25.0` from `main`. No 0.24.0 release ever exists, which is simplest to cite.
- **Two releases.** Publish `v0.24.0` with the target set to commit `b8e0315` (the Releases page lets you pick the commit), then release 0.25.0 later as above.

Zenodo archives a published release by itself and mints the DOI, which goes into `CITATION.cff`.

## 1. Evidence that anyone wants it **(you)**

Send the pilot (`docs/outreach/PILOT.md`) to three people and write down what happens. Send the announcement (`docs/outreach/ANNOUNCEMENT.md`) to one or two communities where simulation people are. If two of three testers cannot say what it is for within two minutes, rewrite the front page before building anything else. Usage counts exist but are off (`data/usage-counts.json`); switching them on is a decision about visitors' privacy and is yours.

## 2. Outside checking of the data **(you)**

Send the audit packet to one expert who knows one of the simulations. A single reply that says "these ten curves are right, these two are off" is worth more than any amount of internal testing. The checks made here (the compilation check, the re-digitization sample, the released-table search) are internal: nobody outside the project has reviewed them. Also yours: file the issues in `docs/UPSTREAM-ISSUES.md` with the maintainers of the comparison compilation, and send the one-line questions in `docs/AUTHOR-QUESTIONS.md` (nothing has been sent).

## 3. A second, independent look at the studies **(you)**

Ask a CAMELS team member to read `docs/RESEARCH-NOTE.md` and `docs/ANALYSIS-quenching-shape.md` and tell you whether the questions and answers are known. If they are, say so on the pages; if not, that is the strongest reason to write them up. `docs/DATA-NOTE.md` is a generated draft of a data paper; whether and where to submit it is your decision.

## 4. Science not done

- **Resolution.** `docs/ANALYSIS-resolution.md` measures how published curves of one model change between resolutions (28 of 30 same-box steps exceed the CAMELS noise at the registered, strict margin; at twice the margin 12 do not). It uses other papers' runs. What remains open is CAMELS itself: a box of the same model at a second resolution needs compute, and is the only way to measure the resolution of the model the studies use.
- **More codes.** The measured conversions cover IllustrisTNG, SIMBA, Astrid and Swift-EAGLE (its catalogues are in the `FOF_Subfind` tree of the CAMELS server; an earlier note here that there were none was wrong). The other CAMELS suites are private (a form), EAGLE and Magneticum need an account, TNG and Illustris need a key; FLAMINGO SOAP access and the Horizon-AGN and SIMBA main-run sites could not be settled from here (`docs/EXPANDING-COVERAGE.md`).
- **Survey selection effects.** A library for scatter in stellar mass, offsets, completeness and a detection floor exists (`docs/OBSERVER-LAYER.md`) with a measurement of how much of a simulation-observation offset a given scatter could absorb. It is not a model of any survey, it is not in the Explorer yet, and fibre apertures and SED-fitting systematics are not modelled.
- **A third code on the dials page.** Astrid is ingested and analysed (exploratory); adding it needs the outputs all three codes have, so the page would lose coverage.

## 5. The digitized curves

53 % of simulation curves are read from figures. Each table an author releases replaces a digitized curve and raises the share of the data that is solid; the data-quality page lists which curves with a matching table are replaced and which are not (for example the COLIBRE mass function in a 50 pkpc aperture). The bottleneck is asking. DARWIN is the example of the other route: its catalogues are public, and the mass function is counted from them (it reproduces the paper's figure); the same catalogues could give a black hole mass relation, but the central/satellite definition and the black hole particle sums would have to be checked first, and they hold no radii or metallicities.

## 6. Smaller things

- **The Explorer is at its size budget.** The page transfers 799 kB against a budget of 800 kB (`scripts/test-performance.mjs`), so the next batch of records fails the check. The embedded curve index is 693 kB compressed, of which the plotted points are 403 kB. Options: load the index per relation instead of all at once (the lasting fix, a few hours); round plotted values to 3 decimals (saves about 60 kB, but the Explorer would then differ from the downloads in the fourth decimal); or raise the budget (about half a second more on the throttled phone for each 100 kB). It is a choice about the promise made to phone users.
- A real figure-export of the dials page in the paper's style (the current PNG export is screenshot quality).
- A page that explains the black hole seeding difference between the codes in plain words, since it carries the main result.
- Reading the Explorer aloud with a screen reader; the automated accessibility checks pass but a human check has not been done.
- Coverage of `compare.js` and `export-lib.js` (they are not instrumented).
- Relations with no records yet: emission-line luminosity functions and UV slopes (planned, not started).
