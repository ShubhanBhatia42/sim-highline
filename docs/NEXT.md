# What would make it great, next

Written 2026-10-23, replacing the list of 2026-10-16. In order of how much each would change the answer to "is this worth continuing?". Items that need a person are marked **(you)**. `docs/SEND-THIS-WEEK.md` has the same items as an ordered list with the text that is ready for each.

## 0. Publish the release **(you)**

`main` is at version 0.24.0 (commit `b8e0315`), whose GitHub release has not been published: GitHub refuses release and tag creation from the automated session (HTTP 403), so the Zenodo archive of 0.24.0 does not exist yet. Publish the release from `main`; Zenodo then mints the DOI, which goes into `CITATION.cff`. The work since then is in `CHANGELOG.md` under "Unreleased" and would be 0.25.0.

## 1. Evidence that anyone wants it **(you)**

Send the pilot (`docs/outreach/PILOT.md`) to three people and write down what happens. Send the announcement (`docs/outreach/ANNOUNCEMENT.md`) to one or two communities where simulation people are. If two of three testers cannot say what it is for within two minutes, rewrite the front page before building anything else. Usage counts exist but are off (`data/usage-counts.json`); switching them on is a decision about visitors' privacy and is yours.

## 2. Outside checking of the data **(you)**

Send the audit packet to one expert who knows one of the simulations. A single reply that says "these ten curves are right, these two are off" is worth more than any amount of internal testing. The checks made here (the compilation check, the re-digitization sample, the released-table search) are internal: nobody outside the project has reviewed them. Also yours: file the issues in `docs/UPSTREAM-ISSUES.md` with the maintainers of the comparison compilation, and send the one-line questions in `docs/AUTHOR-QUESTIONS.md` (nothing has been sent).

## 3. A second, independent look at the studies **(you)**

Ask a CAMELS team member to read `docs/RESEARCH-NOTE.md` and `docs/ANALYSIS-quenching-shape.md` and tell you whether the questions and answers are known. If they are, say so on the pages; if not, that is the strongest reason to write them up. `docs/DATA-NOTE.md` is a generated draft of a data paper; whether and where to submit it is your decision.

## 4. Science not done

- **Resolution.** The largest open weakness of the joint-reachability result is the 25 Mpc/h box at 256^3. A set of runs of one model at a second resolution would turn the caveat into a measurement. The same holds for the shape study, whose lowest mass bins rest on few particles.
- **More codes.** The measured conversions cover IllustrisTNG, SIMBA and Astrid. The public Swift-EAGLE runs have only particle snapshots, no catalogues, so they need a halo finder before an aperture can be measured. Magneticum and others are outside CAMELS.
- **Survey selection effects.** Converting a catalogue stellar mass into what a survey would measure (SED fitting, fibre apertures, completeness) needs mock observations and was not attempted.
- **A third code on the dials page.** Astrid is ingested and analysed (exploratory); adding it needs the outputs all three codes have, so the page would lose coverage.

## 5. The digitized curves

55 % of simulation curves are read from figures. Each table an author releases replaces a digitized curve and raises the share of the data that is solid; the data-quality page lists which curves with a matching table are replaced and which are not (for example the COLIBRE mass function in a 50 pkpc aperture). The bottleneck is asking.

## 6. Smaller things

- A real figure-export of the dials page in the paper's style (the current PNG export is screenshot quality).
- A page that explains the black hole seeding difference between the codes in plain words, since it carries the main result.
- Reading the Explorer aloud with a screen reader; the automated accessibility checks pass but a human check has not been done.
- Coverage of `compare.js` and `export-lib.js` (they are not instrumented).
- Relations with no records yet: emission-line luminosity functions and UV slopes (planned, not started).
