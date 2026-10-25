# Directions that would take the project up a notch

Written 2026-10-23 and updated 2026-10-25. This is a list of ideas with an honest ranking, not a promise. "Status" says what was done in the round that wrote it; the last column of each table is the one to read first. Items that need a person are marked **(you)**.

How the ideas were ranked: by whether someone can trust or use the project tomorrow because of it (value), by how long it takes (effort), and by how easily it could make the project say something wrong (risk). Tier 1 is high value, low risk. Tier 2 adds science or data and needs checking. Tier 3 needs compute, other people, or a decision that is not technical.

## Tier 1. Reach and trust (days, low risk)

| # | Direction | Why it matters | Status |
|---|---|---|---|
| 1 | **Load the Explorer's data per relation.** | The page was 1 kB from its own size budget; every new record would have broken the speed check on a phone. | **done**: a first visit transfers 225 kB instead of 794 kB; no displayed number changed (1,022 states compared) |
| 2 | **Figure export in a paper's style**, with an automatic caption (sources, redshifts, definitions that differ), the BibTeX of what is plotted, and footnotes for comparisons that are not like for like. | People take the figure, not the website, into a paper. A figure that carries its caveats is the most direct way to make the definitions matter. | not started (waited for the Explorer change; next in line) |
| 3 | **One command from your own catalogue to a comparison** (`sim-highline derive`, `compare`) with the same definitions as the dataset; it refuses to guess units or apertures. | The "check your run" page needs a curve; this produces the curve correctly. It is the step that makes a simulator use the project. | **done** (checked on synthetic catalogues only; no real TNG, SIMBA, FLAMINGO, COLIBRE or EAGLE file was available) |
| 4 | **Discoverability**: dataset metadata for dataset search engines, ML dataset metadata (Croissant), sitemap, a feed of the changelog. | Nobody can use what a search does not find. No tracking involved. | **done**: sitemap, feed, dataset description, Croissant file (validated with the official checker; the exports' `#` comment lines need a decision) |
| 5 | **A plain-words page on the black hole seeding difference**, the thing the main result rests on. | The result is only as useful as a reader's ability to say in a sentence what it is. | **done**: `seeding.html`, every quotation tied to its source; an internal explanation, not reviewed outside |
| 6 | **A walkthrough with the accessibility tree and a line edit of every page.** | The automated checks pass; reading order, labels and live updates need a careful look. This is not a substitute for a screen-reader user. | not started; **(you)** for the human check |

## Tier 2. Science and data (a week each, needs checking)

| # | Direction | Why it matters | Status |
|---|---|---|---|
| 7 | **More simulations from the backlog** (105 candidate papers listed, 45 ingested). | Coverage is the asset; each suite added makes every comparison less dependent on three codes. | **partly done**: three papers added (CoDa II, The Three Hundred, FLAMINGO calibration runs); 13 papers looked at and rejected with reasons; 100 or so candidates untouched |
| 8 | **The two relations that were planned and never started**: emission-line luminosity functions, UV slopes. | They test dust and stellar populations, which the other relations barely touch. | **partly done**: UV slopes (37 records), H-alpha luminosity functions (17); [OIII], [OII] and the TNG H-alpha function not done |
| 9 | **The observer layer**: what a survey would measure from a catalogue mass (scatter, offsets, completeness). | Part of every simulation-observation offset is measurement, not physics. The library comes first; an Explorer switch after it is tested. | **partly done**: the library, tests and a measurement; no Explorer switch yet |
| 10 | **A measured resolution effect**, using the same model published at several resolutions. | Turns the largest named caveat of the studies into a number, within the limits of the data. | **done** within its limits: 332 pairs from the dataset's own records; CAMELS itself not tested |
| 11 | **A fourth code in the measured conversions.** | Three codes make "the conversion is small" a statement about three codes. | **done**: Swift-EAGLE added (its catalogues exist; the earlier note was wrong); no other credential-free source found |
| 12 | **Catalogue-derived curves in place of figure reads** wherever a catalogue is public (done for DARWIN's mass function; halo and black hole relations in round 1). | A computed number replaces a digitized one. | **done** for DARWIN: mass function, stellar-to-halo ratio, black hole masses; CoDa II counted from its public catalogue |
| 13 | **A tension map**: simulations against observations, with the standardised offset in each cell and only comparable pairs filled. | A single view of where the disagreements are, with the comparability rules doing the work a reader would otherwise do by hand. Risk: a map can be read as a league table; it must show the number of comparable pairs in each cell. | idea only |

## Tier 3. Needs compute, people, or a decision

| # | Direction | What it needs |
|---|---|---|
| 14 | Runs of a CAMELS-like box at a second resolution. | Compute allocation. The only way to measure resolution for the model the studies use. |
| 15 | A held-out test of the dials page's emulators on published simulations. | Published runs with known parameters; a simulation team's help to be sure of the parameter mapping. |
| 16 | A third code on the dials page. | The outputs all three codes share; the page would lose coverage. |
| 17 | A structured outside review loop (a form that fills `data/audit-outcomes.json`). | People **(you)**: the packet exists; nobody has replied. |
| 18 | A data paper and a venue. | Your decision (`docs/DATA-NOTE.md` is a draft). |

## Considered and not recommended

- **A league table that ranks simulations overall.** Each relation compares different things with different uncertainties; a single score would say more than the data can.
- **Page analytics on by default.** A privacy decision that belongs to the maintainer; the switch exists and is off.
- **Text written by a language model on the site.** The pages state numbers that come from saved results; free text that no one can trace to a source goes against the rule that every statement has one.
- **Accepting community curves without the checks.** The submission checker is the gate; weakening it would put the data's one strong promise at risk.
