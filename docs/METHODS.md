# Methods

How a number gets into sim-highline, and what it is allowed to mean.

## Evidence tiers

Every record carries one tier in `provenance.tier`.

| tier | meaning | rankable |
|---|---|---|
| `catalog-derived` | computed by a sim-highline script from a public catalogue with the standard cuts | yes, if its definitions are documented |
| `official-table` | a table released by the collaboration; the SHA-256 of the file is stored | yes |
| `published-table` | values transcribed from a paper table; spot-checked against quoted numbers inside the script | yes |
| `published-fit` | a published fitting function, fit line or parametric relation | yes |
| `digitized-figure` | values read from the vector paths of a published figure | never |

Transcribed values are never labelled `official-table`. "Rankable" means a curve may be used to score or rank a simulation against data; the front end marks everything else as context only.

## Reading numbers from figures

No raster tracing is used. Figures are taken from the arXiv source of each paper (`https://arxiv.org/e-print/<id>`), which almost always holds the figure as vector PDF, EPS or PS. The curves, markers and fill polygons are read from the drawing commands with PyMuPDF (`scripts/vector_figure.py`), so values are exact to the coordinate precision of the file.

Axes are calibrated from the labelled ticks of the same figure:

- linear axes: a robust fit over numeric labels snapped to tick marks (at least three labels must agree);
- log axes: decade labels are matched to major ticks and the fit is validated by the minor-tick pattern at log10(2..9);
- shared-axis panels: calibration is translated between panels and checked against labels;
- figures with outlined text: major ticks are calibrated by hand and validated by independent features (seed-mass floors, resolution limits, quoted fit slopes, virial lines, guide lines).

Every digitizer asserts its calibration and, where the paper quotes numbers, spot-checks against them. Bands are read from fill polygons (`yLow`, `yHigh`); per-galaxy scatter plots are stored as marker centres with `connect: false`. A record never contains a point the figure does not draw. Points with no drawn error bar have no band.

All digitizers are deterministic: they re-fetch the source and the shipped records are regenerated exactly by `python3 scripts/regress_digitizers.py`. The stored checksum is that of the original `.eps`/`.ps`/`.pdf`, not of a locally converted file.

## Units and conversions

Records are physical, h-free and log10, as published; each axis states its definition and unit. Conversions applied by sim-highline are recorded in the axis definition or the selection warning (for example sSFR from per Gyr to per yr, SHMR from M*/(Mh Omega_b/Omega_m) to M*/Mh). IMF and cosmology are not converted: they are stored in `definitions` and the compatibility check (below) reports the dex that an unconverted difference would make.

## Definitions and comparison

`definitions` is structured (mass aperture, halo definition, IMF, cosmology, population, SFR timescale and statistic, quenching criterion, size definition, metallicity tracer and calibration, and others). `compare.js` holds, per relation, the fields that must match (hard) and those that only warrant a caveat (soft). A pair of records is `comparable`, `comparable-with-caveats` or `not-comparable`; the website shows this next to the legend and gives the reasons in the evidence panel. The exported `mass_class` groups the mass definitions into aperture, total-subhalo, SED, SFH-integral, other and unspecified for quick filtering; it is a convenience, not a conversion.

## What the website computes

Only exact operations: unit-preserving transforms the reader asks for (y minus x, y plus x, physical tick labels), residuals against a chosen reference record using the plotted points only, a least-squares line over the plotted points inside the visible range, and, in the vs-redshift view, reading each published curve at one chosen x inside the plotted range of that curve (no extrapolation; points are joined only between consecutive published epochs). A suite with no epoch near the chosen redshift disappears; nothing is interpolated in redshift.

## Default view: fiducial runs

A simulation can carry dozens of records for one relation (resolutions, model variations, populations, fits and per-galaxy samples). The website shows one fiducial run per simulation and relation by default and keeps the rest one click away (the variants switch and each run in the legend). The fiducial run is chosen by an explicit preference for a few suites (FLAMINGO L1_m9, Magneticum Box2/hr, Illustris-1, SPHINX20 100 Myr), then by not being a variant by name (low resolution, variation, per galaxy, noAGN, fits), then by the number of epochs, then by tier. Exports follow what is visible.

## Checks

`scripts/audit-curves.mjs` runs on every record: epoch order, provenance, checksum rules, finite and plausible ranges per relation, band consistency, monotone x, duplicate data, and cross-source agreement where two sources describe the same run with identical definitions. Accepted findings live in `data/audit-known.json` with a reason each; anything else fails the build. `docs/expert-audit-sample.md` lists a stable sample of records for an independent check by people who know each suite.

## UV luminosity function and cosmic SFR density

`uvlf`: x is the absolute UV magnitude (rest-frame 1500 A, AB; brighter to the right in the app), y is log10 of the number per comoving Mpc^3 per magnitude. Observed functions are tabulated (Bouwens+21 stepwise, Harikane+23, Donnan+24) or parametric Schechter fits, `Phi(M) = 0.4 ln10 phi* 10^(-0.4 (M-M*)(alpha+1)) exp(-10^(-0.4 (M-M*)))`. Simulation functions are dust attenuated (THESAN) or intrinsic (FIRE-2, Ma+18); the `dustCorrection` definition is a hard comparability key, so the two are never silently compared. Where a figure offsets curves for display (Kannan+22 plot each redshift offset by -(z-8) dex) the offset is added back and recorded.

`sfrd`: x is redshift, y is log10 of the star-formation rate per comoving Mpc^3. One record is a whole curve (no epoch slider); the epoch block carries its redshift range. The IMF (`imf`) and the SFR indicator and integration limit (`sfrIntegrationLimit`, e.g. UV integrated to M_UV = -17) are definitions; Madau & Dickinson 2014 assume a Salpeter IMF, so convert before reading offsets as physics.

## Exact conversions applied to figure axes

Where a paper plots a different but exactly equivalent axis, the digitizer converts it and states the conversion in the record's warning. Nothing here is a fit or an interpolation.

- Far-UV luminosity to absolute magnitude: `M_UV = 51.595 - 2.5 log10(L_nu / erg s^-1 Hz^-1)` (AB, 10 pc); density per dex to per magnitude: `log phi_mag = log phi_dex + log10(0.4)` (FLARES, Wilkins+22).
- Cosmic time to redshift for SFR density curves (SIMBA, Dave+19): the flat LCDM age relation with the paper's H0 and Omega_m, solved for z and validated against the figure's own redshift axis at z=0, 1, 2, 4, 6 within 0.2 Gyr.
- `log10(1+z)` axes to z (EAGLE Furlong+15, Horizon-AGN Kaviraj+17, NewHorizon Dubois+21).
- Gyr^-1 to yr^-1 by subtracting 9 dex (sSFR, Dave+20); display offsets such as the -(z-8) dex of Kannan+22 are added back.
- Redshift-evolving fits (Marszewski+24, Z/Zsun) are stored as analytic-evolution records: the published expression is evaluated at the epoch on screen, inside the redshift range of the paper, using the `z` variable of the expression.

## Anchors and the tension map

Each relation has a default observational anchor (`REL[...].anchor` in `highline/index.html`, drawn bold): a widely used reference compilation for that relation. The number beside each simulation in the legend is its median offset from the anchor, in y units, over the x range they share at the chosen epoch, computed from the plotted points by exact interpolation inside that range (`SimHighlineLogic.medianOffset`, unit-tested in `scripts/test-logic.mjs`). The Tension view tabulates the same number for each simulation's fiducial run at one reference redshift. It is a compact picture of where predictions and data differ, not a ranking: cells whose definitions do not agree are marked and drawn with a dashed outline, and an offset there is not a verdict on the simulation.

## Known limitations

- Digitized figures carry the author's plotting choices (binning, which runs are drawn); they are context, not ranking evidence.
- Zoom samples (NIHAO, FIRE-2, NewHorizon) are not volume complete.
- Observational mocks in simulations (for example Horizon-AGN GSMF, TNG quenched UVJ) are labelled by their definitions; intrinsic and mock quantities are not mixed.
- Catalogue-level runs for TNG and EAGLE need user credentials and are provided as scripts, not data.
- Suite-level redshift ranges record the verified run extent; initial-condition redshifts are separate.

## Optional IMF conversion (beta)

Customise > "convert stellar masses and SFRs to a Chabrier IMF" shifts, on screen only, the axes that carry stellar mass or SFR (x for mass functions, mass-metallicity, size, quenched fraction, black hole relations and sSFR; x and y for the main sequence; y for the stellar-to-halo ratio, SFR density and stellar mass density) by the standard offsets already used by the comparability check in `compare.js` (`IMF_DEX`: Kroupa 0, Chabrier -0.025, Salpeter +0.21 dex in stellar mass, so Kroupa to Chabrier is -0.025 and Salpeter to Chabrier is -0.235 dex). Curves with an unstated IMF are never shifted. The offsets are population-averaged conventions, not exact for any single galaxy, so the conversion is off by default, labelled in the legend, the Evidence panel and exported figures, and **downloads and the Python loader always contain the published values**.

Exported sample points of parametric curves are rounded to 6 decimals so that the exported tables are identical on every platform (last-digit floating-point differences otherwise change a few dozen rows between Node builds).
