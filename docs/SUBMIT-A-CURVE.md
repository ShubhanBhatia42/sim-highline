# Submitting a curve

If you made a published relation (an author of a simulation or a survey paper), the best curve in this dataset is the one you give us as numbers: it replaces a curve read from your figure, or fills a gap, and it carries your own statement of what the numbers mean. This page says what is needed and what happens next.

## What is accepted

- Values from a **table** in the paper, a supplementary file or a **data release** (tier `published-table`, `official-table`, `published-fit` for a fit with its parameters, or `catalog-derived` for values you computed from a public catalogue and describe fully). Curves read from a figure are not accepted as submissions; if all you have is a figure, open an issue instead.
- Values that you can share under **CC-BY-4.0 or CC0**. The dataset is CC-BY-4.0.
- One epoch (or one redshift bin) per folder. For several redshifts, one folder each.

## What you must say about the numbers

The reason this dataset exists is that two curves with different definitions cannot be compared. Every submission must state, as the relation requires:

- the **units** (the checker shows the units the dataset uses for that relation; they are log10 and h-free unless stated);
- the **definitions** that matter for that relation. The required ones (stellar mass aperture, IMF, which galaxies are counted, SFR timescale, cosmology, and so on) are listed when you run the checker. If the paper does not say, write `"unspecified"`. That is a useful answer and it is shown as such.
- where the numbers come from (`valuesFrom`), who to ask (`contact`), and whether the intervals are measurement **uncertainties** or the **scatter** of a population.

## How

1. Copy `submissions/_template/` to `submissions/<authorYY-what>/` and fill in `metadata.json` and `curve.csv` (header `x,y` or `x,y,yLow,yHigh`; x must increase unless you set `"connect": false`).
2. Run `node scripts/submission.mjs check submissions/<your-folder>`. Fix every ERROR; read every warning (a value outside the usual range is usually a units mistake).
3. Open a pull request that changes only `submissions/`. The same check runs on the pull request.
4. A maintainer compares two or more numbers against the paper, adds the record to `data/curves/` (with your name as the contact in its provenance and the shared-data licence), rebuilds, and tells you which release carries it. The record keeps a link back to the paper; the folder is removed.

If you would rather not use git, use the "Submit a curve table" issue form and paste the table.

## What we do not do

We do not interpolate, smooth or convert your numbers. If a conversion is needed to compare them with other curves (IMF, aperture, h), it is recorded as a definition, and where we apply a correction it is listed with its reason in `data/compilation-corrections.json`.
