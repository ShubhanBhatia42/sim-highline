# What would make it great, next

Written 2026-10-16. In order of how much each would change the answer to "is this worth continuing?". Items that need a person are marked **(you)**.

## 1. Evidence that anyone wants it **(you)**

Send the pilot (`docs/outreach/PILOT.md`) to three people and write down what happens. Send the announcement (`docs/outreach/ANNOUNCEMENT.md`) to one or two communities where simulation people are (a collaboration chat, a CAMELS channel). If two of three testers could not say what it is for within two minutes, rewrite the front page before building anything else. This is the only item here that can change the verdict on the project.

## 2. Outside checking of the data **(you)**

Send the audit packet to one expert who knows one of the simulations. A single reply that says "these ten curves are right, these two are off" is worth more than any amount of internal testing. Ask the authors of the largest digitized sources (FLAMINGO, NewHorizon, Habouzit et al.) for their tables; `docs/author-requests.md` has the drafts, permission requests first.

## 3. A second, independent look at the main result **(you)**

Ask a CAMELS team member to read `docs/RESEARCH-NOTE.md` and tell you whether the question and the answer are known. If they are, say so on the pages and keep the tool; if they are not, that is the strongest reason to write the note up. Deposit the analysis data with a DOI so that the dates in the registration trail do not rest on git alone.

## 3b. Run the analysis on something that is not CAMELS 25 Mpc/h

The largest open weakness of the result is resolution and box size. Without the two lowest mass bins the headline falls from 4.8 to 2.5. A set of runs of one model at a second resolution would turn that from a caveat into a measurement.

## 4. A third code on the dials page

Astrid is ingested and analysed (exploratory). Adding it to the dials page needs the outputs all three codes have (97 of the 186), so the page would lose coverage in exchange for a third universe. Worth doing if testers ask "what about Astrid?".

## 5. The digitized curves

55% of simulation curves are read from figures. Each table an author releases replaces a digitized curve and raises the share of the data that is solid. The weekly literature watcher already lists new papers; the bottleneck is asking.

## 6. Smaller things

- A real figure-export of the dials page in the paper's style (the current PNG export is a screenshot-quality figure).
- A learning path for the student persona: three short guided questions on the dials page, each ending in a sentence they could say aloud.
- A page that explains the black hole seeding difference between the codes in plain words, since it carries the main result.
- Firefox and Safari runs of the browser tests (configured, never run here).
- Reading the Explorer aloud with a screen reader; the automated accessibility checks pass but a human check has not been done.
- Coverage of `compare.js` and `export-lib.js` (they are not instrumented).
