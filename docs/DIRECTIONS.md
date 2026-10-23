# Directions that would take the project up a notch

Written 2026-10-23. This is a list of ideas with an honest ranking, not a promise. "Status" says what was done in the round that wrote it; the last column of each table is the one to read first. Items that need a person are marked **(you)**.

How the ideas were ranked: by whether someone can trust or use the project tomorrow because of it (value), by how long it takes (effort), and by how easily it could make the project say something wrong (risk). Tier 1 is high value, low risk. Tier 2 adds science or data and needs checking. Tier 3 needs compute, other people, or a decision that is not technical.

## Tier 1. Reach and trust (days, low risk)

| # | Direction | Why it matters | Status |
|---|---|---|---|
| 1 | **Load the Explorer's data per relation.** | The page was 1 kB from its own size budget; every new record would have broken the speed check on a phone. | task force, round 1 |
| 2 | **Figure export in a paper's style**, with an automatic caption (sources, redshifts, definitions that differ), the BibTeX of what is plotted, and footnotes for comparisons that are not like for like. | People take the figure, not the website, into a paper. A figure that carries its caveats is the most direct way to make the definitions matter. | task force, round 2 |
| 3 | **One command from your own catalogue to a comparison** (`sim-highline derive`, `compare`) with the same definitions as the dataset; it refuses to guess units or apertures. | The "check your run" page needs a curve; this produces the curve correctly. It is the step that makes a simulator use the project. | task force, round 1 |
| 4 | **Discoverability**: dataset metadata for dataset search engines, ML dataset metadata (Croissant), sitemap, a feed of the changelog. | Nobody can use what a search does not find. No tracking involved. | task force, round 1 |
| 5 | **A plain-words page on the black hole seeding difference**, the thing the main result rests on. | The result is only as useful as a reader's ability to say in a sentence what it is. | task force, round 1 |
| 6 | **A walkthrough with the accessibility tree and a line edit of every page.** | The automated checks pass; reading order, labels and live updates need a careful look. This is not a substitute for a screen-reader user. | task force, round 2 **(you)** for the human check |

## Tier 2. Science and data (a week each, needs checking)

| # | Direction | Why it matters | Status |
|---|---|---|---|
| 7 | **More simulations from the backlog** (105 candidate papers listed, 45 ingested). | Coverage is the asset; each suite added makes every comparison less dependent on three codes. | task force, round 2 |
| 8 | **The two relations that were planned and never started**: emission-line luminosity functions, UV slopes. | They test dust and stellar populations, which the other relations barely touch. | task force, round 1 |
| 9 | **The observer layer**: what a survey would measure from a catalogue mass (scatter, offsets, completeness). | Part of every simulation-observation offset is measurement, not physics. The library comes first; an Explorer switch after it is tested. | task force, round 1 (library) |
| 10 | **A measured resolution effect**, using the same model published at several resolutions. | Turns the largest named caveat of the studies into a number, within the limits of the data. | task force, round 1 |
| 11 | **A fourth code in the measured conversions.** | Three codes make "the conversion is small" a statement about three codes. | task force, round 1 (feasibility first) |
| 12 | **Catalogue-derived curves in place of figure reads** wherever a catalogue is public (done for DARWIN's mass function; halo and black hole relations in round 1). | A computed number replaces a digitized one. | task force, round 1 |
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
