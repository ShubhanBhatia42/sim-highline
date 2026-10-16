# The ten questions, and the three walk-throughs

`scripts/test-journeys.mjs` walks each of these in a real browser against the built site. Each must reach its answer in at most four clicks and thirty seconds; on 2026-10-16 all ten did, in 0.7 to 3 seconds and 0 to 2 clicks.

| # | question a researcher brings | where it is answered |
|---|---|---|
| 1 | What do simulations predict for a relation at an epoch? | Explorer: pick the relation, move the epoch slider |
| 2 | How does my own run compare with the others? | Explorer, *Your run*, *Try an example* or paste your curve |
| 3 | Is a comparison fair (same IMF, aperture, population)? | *Your run*: declare definitions; each curve gets a mark and a reason on hover |
| 4 | Where does a curve come from and how was it obtained? | Click any curve: the evidence panel gives source, definitions, how it was obtained |
| 5 | Where do simulations disagree most? | Explorer, *Spread* view |
| 6 | How do simulations compare with observations? | Explorer, *Tension* view |
| 7 | How does a relation change with redshift? | Explorer, *Evolution* view |
| 8 | How do I cite this and get the BibTeX? | Explorer, *Get data* panel |
| 9 | What happens to my galaxies if feedback is stronger? | Dials page: move a dial, or press a match button |
| 10 | Can I load the data in a notebook? | Data page and the Python loader |

## Walk-through 1: a simulator with a curve

1. Open the Explorer on the stellar mass function at the epoch of your run.
2. Press *Your run*. Paste `x,y` rows (log stellar mass, log number density) or press *Try an example*.
3. Say what your numbers mean in the three drop-downs. The table marks which published curves are fair to compare with and gives the offset against them.
4. Download the comparison as a CSV, or copy the BibTeX of what you plotted.

## Walk-through 2: an observer who needs predictions

1. Open the Explorer on the relation of interest (for example the gas-phase mass-metallicity relation).
2. Switch off variants if the legend is crowded; read the legend badge to see whether each curve is an official table, a paper table, a fit or a digitized figure.
3. Click a curve for its source and definitions, then use *Get data* for BibTeX.

## Walk-through 3: a student

1. Open the dials page.
2. Press *Make SIMBA look like TNG*, read the sentence under the chart, and look at which panels stay shaded.
3. Change *Match on* to another property and press the button again; compare what is knocked out of agreement.
