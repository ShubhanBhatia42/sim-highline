# Observer layer: scatter, offsets, completeness and detection floors

*Wording written by hand; every number in the measurement part is written by `scripts/analyze_observer_layer.py` from `data/analysis/observer-layer.json`. Internal checks only: no outside expert has reviewed this.*

## What this is, and what it is not

A simulation catalogue holds true masses and true rates. A survey reports measured ones. The project already converts differences it can document on the simulation side (IMF, aperture, cosmology). This page covers a small
set of operations for the observer side, so a reader can ask "how much of this offset could a given measurement effect absorb?". They are plain arithmetic on the curves; **none is a calibrated model of any survey**, and
none of the numbers below says that any survey has the scatter, offset, limit or floor that is tried.

| operation | JavaScript (`observer-lib.js`) | Python (`sim_highline.py`) |
|---|---|---|
| Gaussian scatter in log stellar mass, constant or mass-dependent | `scatterPoints(points, sigma, opts)` | `scatter_points(points, sigma, **opts)` |
| a systematic offset in the measured mass | `shiftPoints(points, offset)` | `shift_points(points, offset)` |
| a limiting mass (hard cut) | `completenessCut(points, mLim)` | `completeness_cut(points, m_lim)` |
| a smooth completeness (logistic in measured mass) | `completenessWeight(points, m50, width)` | `completeness_weight(points, m50, width)` |
| the three in survey order | `observePoints(points, opts)` | `observe(points, sigma, offset, m_lim, completeness)` |
| a detection floor on a specific star formation rate curve | `ssfrFloorPoints(points, floor)` | `ssfr_floor_points(points, floor)` |
| the same, from per-galaxy counts | `ssfrFloorRow(row, yEdges, floorLog)` | `ssfr_floor_row(row, y_edges, floor_log)` |
| Poisson bands from counts | `poissonBands(points)` | `poisson_bands(points)` |

Points are the records' own format: `{x, y, yLow, yHigh, count}` with x = log10 stellar mass and y = log10 number density per dex. Functions return new points and never change their input. Each function's docstring (and the comment above it in `observer-lib.js`) lists its assumptions; the important ones follow.

### Scatter (Eddington bias)

- **Model.** A galaxy of true log mass m is measured at m + e with e Gaussian, standard deviation sigma(m), where sigma depends on the true mass (a single number gives a constant scatter). The measured density is the convolution n_obs(x) = integral of n(m) N(x - m; sigma(m)) dm. Number is conserved because the kernel integrates to one for every m. The effect is largest where the curve is steep (the high-mass end), where scatter moves more galaxies up than down.
- **Grid.** log10 n is interpolated linearly between the points and continued past the first and last point as a straight line with the slope fitted to the nearest three points (the slope above the last point is never positive). The integral is a sum over a uniform grid of 0.005 dex (or sigma/2 if sigma is smaller than 0.01), reaching 8 sigma on either side of each output mass, so the kernel sums to 1 to better than 1e-12. Outputs are at the same masses as the inputs.
- **The continuation is a guess.** Every output carries `edgeShare`, the fraction of its scattered density that came from the continuation, and `edge` when that is above 5 per cent. Near the ends of a curve the result depends on the guess; the measurement below is repeated without those bins.
- **Bands.** The output log density is a weighted average of the input log densities (the weights are the shares of the scattered density that come from the neighbourhood of each input point, and sum to one). Independent input errors then combine as the square root of the sum of squared weights times squared errors, separately for the upper and lower side. A point that has only a count gets Poisson bands first. Not propagated: the uncertainty of sigma, of the continuation slope and of the interpolation, and the correlation between neighbouring outputs (they are reported as if independent). Cosmic variance is whatever the input already carries.
- **A density, not a catalogue.** No noise is added to individual galaxies, and the scatter is assumed Gaussian in log mass and independent of everything else (real mass errors are often skewed, correlated with the SED model and with redshift).

### Offset, completeness, floor

- **Offset.** Measured log mass = true log mass + offset. A density per dex does not change when the axis slides, so only x moves. One offset for all masses; no mass-dependent offset.
- **Limiting mass.** Points below the limit are removed, as a survey that corrects for completeness above its limit and publishes nothing below it. **Smooth completeness** multiplies the density by C = 1/(1 + exp(-(x - m50)/width)), the density an uncorrected catalogue would show; the bands keep their relative size and no new Poisson noise is derived. The logistic is a convenient shape, not a measured completeness. Both act on the measured mass, so they come after scatter and offset.
- **Detection floor for a specific star formation rate (sSFR).** On a curve of medians with a 16 to 84 per cent band, a point whose median is below the floor is removed (the typical galaxy there is not detected, so no median can be measured) and a lower band below the floor is raised to it. This does not recompute the median of the detected galaxies, which is higher than the median of all of them. When per-galaxy counts exist (a record's distribution), `ssfrFloorRow` drops the counts below the floor and returns the detected fraction and the quantiles of the detected galaxies, with the same within-bin rule as `compare.js`. A floor in SFR becomes an sSFR floor of SFR_min - log10 M (`sfrFloorToSsfr`).
- **Not done.** Scatter in SFR, mass-dependent offsets, redshift errors, cosmic variance, dust, and any link between the mass error and the SFR error.

## How it is tested

- `scripts/test-observer.mjs` (JavaScript) and `scripts/test_observer.py` (Python), the same checks in both: a pure power law gains exactly exp((beta sigma ln10)^2 / 2) (tolerance 1e-9 dex); a Gaussian mass function of width s becomes a Gaussian of width sqrt(s^2 + sigma^2) (2e-4 dex, the interpolation of an input sampled every 0.01 dex); a Schechter function is checked against the defining integral by an independent quadrature at every mass from 8.4 to 12 and, below the knee, against the asymptotic series for the Eddington-biased Schechter function (1e-3 dex). The Schechter function has no elementary closed form after scatter, so the quadrature and the series are the references; the power law and the Gaussian are exact. Mass-dependent scatter is checked against quadrature (1e-6 dex).
- Invariants: zero scatter returns the input exactly; the integrated number is conserved to 2e-4 for constant and mass-dependent sigma (a deliberately kinked test density, which is the worst case for the grid sum); bands shrink under averaging and keep their asymmetry; offsets and cuts are exact.
- JavaScript equals Python to 1e-9 on thirteen cases stored in `tests/fixtures/observer-fixture.json`.
- Both tests also run the same checks on a convolution replaced by a no-op and on one with half the scatter, and require them to fail.

## Measurement: how much of an offset could scatter absorb?

**Result in brief.** Without scatter, 480 of the 613 classified pairs have an offset larger than the observational uncertainty. Scatter of 0.1, 0.2 and 0.3 dex moves 3, 17 and 36 of them to smaller, and moves 13, 27 and 44 pairs the other way. The median offset over all 722 pairs goes from +0.14 dex to +0.14, +0.16 and +0.20 dex: the simulations lie mostly above the observations, and scatter raises them further. At 0.3 dex, 36 of the 480 large offsets fall inside the uncertainty and 44 pairs that were inside move outside. This measures how much of an offset a given scatter could absorb; it is not evidence that any survey has that scatter.

**Question.** For every galaxy stellar mass function pair in the dataset, one from a simulation and one observed, that the comparison rules call comparable at similar redshift: how does the median offset change if the simulation curve is scattered by 0.1, 0.2 or 0.3 dex?

**Pairs.** Relation `gsmf`; the rules of `compare.js` (through `sim_highline.compatible`) must not return "not-comparable" (this already requires both records to be rankable, so digitized figures are out); the two redshift ranges must be at most max(0.15, 0.1 (1 + z)) apart, the tolerance the Explorer uses; and the stated populations must be equal. For this relation the rules of `compare.js` now require that (a quiescent-galaxy mass function is not compared with an all-galaxy one); an earlier version of the rules did not check it, and 76 such pairs had to be removed by hand in the first run of this measurement. The script still checks the populations itself as a safeguard and removes 0 pairs on that test. 308 simulation records and 57 observed records give 17556 possible pairs; 9444 are not comparable, 7291 are comparable but at redshifts too far apart, 0 are removed for population, leaving 821. 0 of those have a simulation curve with a gap over 1 dex that cannot be scattered, and 99 share fewer than 3 bins with the observed curve, so **722 pairs (128 simulation records, 50 observed records) are measured**. The pairs are not independent: one simulation curve is paired with every survey at its redshift, and neighbouring redshifts share a survey.

**Offset.** Simulation minus observation in log10 number density, the median over the bins the Explorer compares (observed bins inside the simulation's range, never extrapolated, at least 3 of them). Positive means the simulation lies above. The definition differences the rules list as caveats (aperture or total mass, cosmology, IMF) are **not** converted here, as in the Explorer; in these pairs the caveats are: massDefinition (722 pairs), H0 (715 pairs), epoch (126 pairs), imf (61 pairs). For scale, the Hubble-constant difference alone is worth 0.01 dex in number density (median; at most 0.05) in the comparable pairs and is not converted either.

**"Larger than the observational uncertainty".** The median offset's absolute value exceeds the median, over the bins compared, of the observed 1-sigma (the larger of upper and lower error). 109 of the measured pairs have an observed curve with no uncertainty and are left out of the counts of changes.

| scatter applied to the simulation | pairs | median offset without (dex) | median offset with | median absolute offset without | with | larger than the uncertainty without | with | larger to smaller | smaller to larger |
|---|---|---|---|---|---|---|---|---|---|
| 0.1 dex | 722 | +0.14 | +0.14 | 0.23 | 0.23 | 480 | 490 | 3 | 13 |
| 0.2 dex | 722 | +0.14 | +0.16 | 0.23 | 0.24 | 480 | 490 | 17 | 27 |
| 0.3 dex | 722 | +0.14 | +0.20 | 0.23 | 0.25 | 480 | 488 | 36 | 44 |

Reading the table: each row applies the scatter to the simulation and recomputes the offset for the same pairs ("without" is the offset as it stands). "Larger to smaller" is the number of pairs whose offset was larger than the observational uncertainty and is smaller after; "smaller to larger" is shown because scatter can also make an offset worse. In the simulation curves of these pairs, 90 per cent of the changes in log density caused by the scatter lie between -0.05 and +0.23 dex for 0.1 dex of scatter, -0.05 and +0.83 for 0.2 and -0.04 and +1.37 for 0.3 (5th to 95th percentile over all bins, bins flagged as depending on the continuation left out; a few far-tail points of fitted curves change by tens of dex and mean nothing): it raises the curve by little on a shallow slope and by a lot on the steep high-mass end, and lowers it slightly in a few bins where the curve has a bump. It therefore helps where the simulation lies below the observations and hurts where it lies above, and because the offset here is a median over bins, a change confined to the steep end moves it little.

Of the 613 classified pairs, the smallest tested sigma that brings the offset inside the observational uncertainty: already inside the uncertainty without scatter, 133; inside at 0.1 dex, 3; at 0.2 dex, 15; at 0.3 dex, 19; still outside at 0.3 dex, 443.

### Without the bins that depend on the continuation

| scatter applied to the simulation | pairs | median offset without (dex) | median offset with | median absolute offset without | with | larger than the uncertainty without | with | larger to smaller | smaller to larger |
|---|---|---|---|---|---|---|---|---|---|
| 0.1 dex | 672 | +0.15 | +0.16 | 0.24 | 0.24 | 464 | 467 | 6 | 9 |
| 0.2 dex | 636 | +0.16 | +0.18 | 0.24 | 0.25 | 429 | 442 | 13 | 26 |
| 0.3 dex | 609 | +0.15 | +0.21 | 0.24 | 0.25 | 397 | 421 | 27 | 51 |

The same, with the bins removed where more than 5 per cent of the scattered density comes from the guessed continuation. Before and after are compared on the same bins; a larger scatter flags more bins, so the pairs (and the baseline) differ from row to row, and pairs left with too few bins drop out.

### By simulation

| simulation | pairs | simulation records | median offset, none | after 0.1 dex | after 0.2 dex | after 0.3 dex | larger to smaller at 0.1 / 0.2 / 0.3 | smaller to larger at 0.1 / 0.2 / 0.3 |
|---|---|---|---|---|---|---|---|---|
| BlueTides | 7 | 3 | -0.50 | -0.46 | -0.37 | -0.24 | 0 / 0 / 1 | 0 / 1 / 2 |
| COLIBRE | 456 | 81 | +0.14 | +0.15 | +0.16 | +0.19 | 3 / 9 / 18 | 8 / 17 / 21 |
| DARWIN | 54 | 9 | +0.13 | +0.14 | +0.18 | +0.25 | 0 / 4 / 7 | 1 / 2 / 3 |
| EAGLE | 82 | 12 | +0.09 | +0.10 | +0.13 | +0.16 | 0 / 0 / 3 | 1 / 5 / 11 |
| FLARES | 27 | 6 | -0.24 | -0.22 | -0.16 | -0.07 | 0 / 1 / 2 | 1 / 0 / 1 |
| Magneticum Pathfinder | 82 | 14 | +0.34 | +0.35 | +0.39 | +0.44 | 0 / 2 / 2 | 2 / 2 / 6 |
| THESAN-1 | 14 | 3 | -0.24 | -0.22 | -0.17 | -0.10 | 0 / 1 / 3 | 0 / 0 / 0 |

Median over the pairs of that simulation, in dex; positive means the simulation lies above the observations. Pairs of one simulation are not independent.

## What this shows, and what it does not

- It shows how large an offset in number density a Gaussian mass scatter of 0.1, 0.2 or 0.3 dex could remove, pair by pair, with the Explorer's own offsets. A pair whose offset shrinks to within the observational uncertainty is a pair where that much scatter would be enough, not one where it is present.
- It does not show that any of the surveys has such scatter. Published mass functions of the observed side usually come with their own error treatment (some correct for the Eddington bias, some do not), and this project has not read that for each one.
- It does not separate scatter from the other differences left in these pairs (aperture against total stellar mass, cosmology, IMF, cosmic variance, resolution at the low-mass end). An offset that scatter absorbs may equally be absorbed by one of those.
- Applying the scatter to a simulation curve that already includes an observer-side convolution would count it twice. The rankable COLIBRE records state that no Eddington-bias scatter is added (the convolved variant in the same file is not ingested); the records of the other simulations in these pairs contain no sentence about it either way. That is read from the records' own text, not from the papers.
- The result depends on the dataset: it is regenerated whenever curves are added (`python3 scripts/analyze_observer_layer.py`; `scripts/test_observer_layer.py` fails if the saved file is out of date).

## Where an interface would attach (not built)

These are the places in the existing code where a control for the observer layer would connect. None is implemented; `highline/index.html` is untouched by this work. Names, not line numbers, because the page is being edited.

1. **Load the library next to `compare.js` and `export-lib.js`.** `scripts/build-highline.mjs` reads those two files (and `highline/logic.js`) and inlines them into the one-file Explorer; `observer-lib.js` would be read and inlined the same way and exposes `SimHighlineObserver`. `scripts/build-static.mjs` already copies `sim_highline.py` to `dist/`, so the Python half ships without a change. `scripts/coverage.sh` lists the JavaScript files it measures; `observer-lib.js` is added there.
2. **Where a plotted simulation curve is built.** In `highline/index.html`, `rawPoints(r, z)` takes a record's points (`rawPointsNative`) and applies the IMF shift (`imfShift`); `samples(r, z)` then applies the axis transform. The observer layer is a sibling of the IMF shift: it would run on the points `rawPoints` returns, simulations only, before `samples` transforms the axes, with its settings in the page state and the address. The original curve stays as a thin line; the observed-side curve is drawn dashed, as the page does for comparisons that are not definition-matched.
3. **The offset number in the legend and in the Tension view.** `offsetOf(r, a, z, raw)` calls `SimHighlineLogic.medianOffset` on `samples(...)` or `rawPoints(...)`; because it takes points, it works unchanged on scattered points. `renderLegend` would show the offset with and without the setting, and `renderTension` (the same function) would add the column.
4. **The Evidence panel.** `evidenceHtml` lists a record's definitions; it could list the operations applied (`observePoints(...).steps` is one line per operation) and the warning for bins flagged `edge`.
5. **My run.** `state.user` (parsed by `SimHighlineLogic.parseUserCurve`) and `compare_run` in `sim_highline.py` take the user's own curve; the same options (sigma, offset, limiting mass) would apply to it, in the same order.
6. **Specific star formation rate relations.** `ssfrFloorPoints` on the curves the page draws for relation `ssfr`; for records with `representation.distribution`, `ssfrFloorRow` next to `distributionStats` (`compare.js`), which already gives the quantiles the page draws.
7. **Command line and exports.** `sim_highline.main` (`sim-highline compare`) could take `--scatter 0.2 --mass-offset -0.1 --limiting-mass 8.5` and apply them to the user's curve. Exports are not made with any setting, and should stay so.
8. **Site pages.** `scripts/build-site.mjs` fills templates from saved results; a short page on the Methods route could point at this document and at `data/analysis/observer-layer.json`.
