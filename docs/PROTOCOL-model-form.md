# Protocol: parametric versus structural uncertainty in the cosmic star formation history of simulated galaxy formation

Status: **pre-specified**. Written on 2026-10-14 after the data were assembled and checked (section 8 lists exactly what had been looked at) and **before** any between-family spread as a function of redshift, any variant-class deviation, any CAMELS parameter response or reachability distance, or any calibrated prediction was computed. The analysis code implements this text. Every departure is listed under "Deviations" in `docs/ANALYSIS-model-form.md`, which the code generates and which reports whatever comes out, including a null result.

## 1. Why this exists

Cosmological galaxy-formation simulations are tuned to a few observations at z about 0 (the stellar mass function, sizes, black hole masses, sometimes the cosmic star formation history) and are then used to predict what is not tuned: the early Universe, new relations, new surveys. Two different things limit such predictions. **Parametric** uncertainty is what a given model can still do by retuning its own free parameters; **structural** uncertainty is what the model's form (how winds, black holes, star formation and numerics are implemented) forces regardless of tuning. In climate science this distinction is made with perturbed-physics ensembles against multi-model ensembles. For galaxy formation it has not been quantified, because the usual comparison of two simulations mixes both.

Two things make it measurable now. First, the CAMELS project ran about a thousand simulations each of IllustrisTNG and SIMBA at identical resolution and box size with the same four astrophysical parameters (and two cosmological ones) varied over the same factors: a designed experiment with matched numerics. Second, the sim-highline dataset holds the published cosmic star formation histories of about a dozen independent codes, with the authors' own resolution, calibration and parameter variations for several of them. The cosmic star formation rate density (SFRD), as a function of redshift, is the observable with the most suites, no aperture or population ambiguity, and a conservation link to the stellar mass density; this protocol is about it.

Questions:

* **E1 (funnel).** Do published simulations disagree more about the SFRD at z = 5 to 7.5 than at z = 0.5 to 3?
* **E2 (tiers).** How large are the changes the authors themselves make by changing resolution, a subgrid parameter, a feature or the cosmology, compared with the disagreement between simulations?
* **E3 (reachability).** In the designed experiment, can IllustrisTNG reproduce SIMBA's SFRD by retuning its own four feedback parameters, and conversely? How far apart do the two codes stay (the structural distance), and is that more than the same code with two independent emulators?
* **E4 (calibrate and extrapolate).** If both codes are tuned to the same observed SFRD at z <= 3, how different are their predictions at z = 4 to 8 relative to how well each is constrained?
* **E5 (observational leverage).** Where do the published simulations bracket the observed SFRD, and where is their disagreement larger than the observational error?

## 2. Data

**2.1 Published curves.** All `sfrd` records of simulations in `data/curves` (55 records from 14 sources at the time of writing), with `data/model-variants.json` fixing, for each model family, its fiducial curve and each variant's class (numerical, parametric, calibration, cosmology, component, implementation, ablation) from the cited tables. Eligible as a family's fiducial curve: a total star formation rate density of a cosmological volume with the comoving density frame stated or inferred from evidence recorded with the curve. Not eligible: FLARES (galaxies with SFR above 0.1 Msun/yr only), THESAN-zoom (galaxies brighter than M_UV = -17 in 14 zooms), NewHorizon (a small non-volume-complete zoom, frame unstated), FIREbox 'massive' (a sub-sample). SIMBA and Horizon-AGN (frame, and for Horizon-AGN cosmology and SFR indicator, not stated) are excluded from the primary analysis and added in sensitivity S1. Nine families remain: Illustris, IllustrisTNG, EAGLE, FLAMINGO, COLIBRE, FIREbox, ASTRID, THESAN-1, Romulus25. The fiducial curves are those of the table, which coincide with the choice of the website's rule (`primaryUnits`) for every family except COLIBRE: for records with one epoch each the rule falls through to alphabetical order of the run name and would take m5 (L025), a 25 Mpc box; the table takes m6 (L200), the intermediate resolution of the flagship in a box of 200 Mpc, and sensitivity S5 draws among all of COLIBRE's runs.

**2.2 CAMELS.** The first generation (25 Mpc/h boxes, 256^3 dark matter particles plus 256^3 gas elements, h = 0.6711) of IllustrisTNG and SIMBA: the Latin-hypercube set LH (1000 simulations per code, each with its own seed; Omega_m in [0.1, 0.5], sigma_8 in [0.6, 1.0], and four astrophysical factors) and the cosmic-variance set CV (27 simulations per code at the fiducial parameters with 27 seeds). The star formation logs the codes wrote while running (`extra_files/sfr.txt`) are reduced by `scripts/ingest_camels_sfrd.py` to the time-averaged SFRD in redshift bins of 0.2 (0 to 14) and stored in `data/ensembles/camels-sfrd.json` with the SHA-256 of every file read. The astrophysical factors mean (CAMELS documentation) for IllustrisTNG: A_SN1 the galactic wind energy per unit star formation, A_AGN1 the kinetic-mode black hole feedback energy, A_SN2 the wind speed, A_AGN2 the burstiness of kinetic-mode feedback; for SIMBA: A_SN1 the wind mass loading, A_AGN1 the momentum flux of quasar and jet-mode feedback, A_SN2 the wind speed, A_AGN2 the jet speed. **The parameters of the two codes are not the same physical quantities**; the experiment compares what each code can do with four feedback dials of the same range, not what it does at the same physics. The IllustrisTNG LH and the SIMBA LH use different initial seeds and different parameter points (they are not pairs).

**2.3 Observations.** The Madau and Dickinson (2014) fit (record `madau14.sfrd.fit`, Salpeter IMF, divided by 1.6 for a Chabrier IMF as the record states) at z <= 8 and the Harikane et al. (2023) points at z = 9, 12, 16 (records `harikane23.sfrd.*`), both with a systematic error of 0.2 dex assumed (dust, IMF, star formation indicator: the fit has no uncertainty of its own that covers these).

## 3. Conventions

* The quantity is y = log10 SFRD in log10(Msun yr^-1 cMpc^-3). A curve's value at a grid redshift is the mean of y over plus or minus 0.125 (published curves) of the linearly interpolated curve, defined only where that window lies inside the curve (the plotted lines carry spikes from single outputs; windowing is a fixed smoothing, not a fit). Published grid: z = 0.25 to 8.0 in steps of 0.25. CAMELS grid: the bin centres 0.1, 0.3, ..., 8.1.
* No IMF conversion in the primary analyses: a simulated SFR is the gas mass converted into stars per unit time, a property of the model. (The earlier z about 0 mass-function analysis applied the website's IMF offsets as if they were a definition difference; for simulation-to-simulation comparison they are a convention for comparing with observations. That applies here only to observations in E5 and to sensitivity S4, and the earlier analysis's wording is corrected in the changelog.)
* Redshift bands: low = 0.5 to 3.0, high = 5.0 to 7.5 (published); low = 0.1 to 3.1, high = 3.1 to 8.1 for the CAMELS reachability, which has no galaxies resolved above z about 8.
* "Spread" is the unbiased standard deviation across families of the windowed y at a grid redshift where at least 5 families are defined.

## 4. Estimands and decision rules

**E1 - the funnel in published simulations (primary).** The balanced set is the families whose fiducial curve is defined at every grid point of both bands. With V_low and V_high the between-family variances averaged over the grid points of each band,

    phi = log10( S_high / S_low ),  S_band = sqrt(V_band).

*Success* requires both: the Pitman-Morgan test (exact for two correlated variances under bivariate normality) on the balanced families' band-mean offsets from the mean of the balanced families at the same redshift gives a one-sided p below 0.05 for the variance of the high band exceeding that of the low band; and the lower end of the 90 % cluster-bootstrap interval of phi (5000 resamples of families) is above 0. Otherwise the conclusion is "no funnel detected", with the power analysis of section 5 stating what could have been detected. Also reported (not part of the rule): the spread S(z) of all eligible families with its bootstrap band, the slope of log10 S(z) on z over 0.5 to 7.5 with a bootstrap interval, and the redshift of minimum spread (the anchor) with an interval.

**E2 - tiers (descriptive).** For each variant class in `data/model-variants.json` and each band, the root mean square difference in y between the variants and their base run (averaged first within families, then over families; also pooled over variants), with a variant-resampling interval, set beside S_band. Reported as a ratio. Not a test: the size of a variant is the authors' choice (a factor 2 in a wind parameter, a 4 sigma recalibration), so only the order of magnitude and the redshift dependence carry information. The designed experiment is E3.

**E3 - decomposition and reachability in CAMELS (primary for parametric against structural).** Per code, an emulator of y(z) in the six parameters x = ((Omega_m - 0.3)/0.2, (sigma_8 - 0.8)/0.2, log A_SN1/log 4, log A_AGN1/log 4, log A_SN2/log 2, log A_AGN2/log 2), all in [-1, 1]: weighted polynomial ridge regression (degree 2 or 3 chosen by 10-fold cross-validation; ridge 1e-3 of the mean diagonal; weights exp(-(x1^2 + x2^2)/(2 * 0.5^2)) so that the emulator is accurate near the fiducial cosmology, the only place the primary analyses use it). Cosmology is fixed at x1 = x2 = 0 in everything below except sensitivity S9.

* Seed noise: the standard deviation of the 27 CV curves at each z.
* Parametric spread P_c(z): the standard deviation of the emulator over a uniform on the four astrophysical coordinates, with its between-band ratio (the parametric funnel in a controlled setting).
* Structural offset at the fiducial parameters: the difference of the CV means of the two codes with its standard error, and its root mean square per band.
* Reachability distance D(c1, c2) = the minimum over the four astrophysical coordinates of each code of the root mean square difference of the two emulated curves over the grid (full range and the two bands). Compared with controls: the same quantity between two emulators of the same code trained on disjoint random halves of its LH set (200 splits per code), which measures what emulation and seed noise alone leave. *Structural* if the 5th percentile of the bootstrap distribution of D(TNG, SIMBA) (200 refits of both emulators on resampled simulations) exceeds the 95th percentile of the controls; *removable* if the 95th percentile of D(TNG, SIMBA) is below the median control. Otherwise unresolved. Also reported: D with the parameter ranges shrunk to 25, 50 and 75 % of their log half-width.

**E4 - calibrate and extrapolate (CAMELS).** For each code the posterior of the four astrophysical coordinates (cosmology fixed at the fiducial) given the Madau and Dickinson curve (Chabrier) at the bin centres 0.1, 0.5, 0.9, 1.3, 1.7, 2.1, 2.5, 2.9, with Gaussian errors of variance 0.2^2 + 0.15^2 + e_j^2: observational systematics 0.2 dex; a 0.15 dex allowance for the small box and the low resolution of CAMELS; and the emulator error e_j, the cross-validation error in excess of the seed noise (zero if it is smaller). Importance sampling from 400 000 prior draws. The posterior predictive medians and central 90 % intervals at the bin centres 4.1, 4.5, ..., 7.7. *Structural disagreement after calibration* if the 90 % intervals of the two codes do not overlap at half or more of those redshifts; *parametric* if they overlap at all of them; otherwise mixed. Also reported: the interval width against redshift for each code (a calibration funnel inside one code) and the ratio of its high to low value.

**E5 - observational leverage (descriptive).** At z = 1, ..., 7 the ensemble median, extremes and spread of the published fiducial curves converted to a Chabrier IMF (the website's offsets; S4's convention) against the Madau and Dickinson curve: whether it lies inside the envelope, the offset in units of the spread, and the spread in units of the 0.2 dex observational error (above 1 means the data are precise enough to rank the models); and the same at z = 9 and 12 against Harikane et al. where at least 5 families reach those redshifts.

**Validations (must hold for the corresponding conclusion to be stated without qualification; failures are reported and the qualification stated).**

* **V1 (CAMELS units and volume).** For 12 randomly chosen IllustrisTNG LH simulations (seed fixed), the stellar mass in the z = 0 subhalo catalogue per comoving volume divided by the time integral of the logged SFRD lies in [0.45, 0.75] (the surviving fraction after mass loss and the stars outside subhalos). Done in `scripts/validate_camels_closure.py`.
* **V2 (responses are not a CAMELS artefact).** The shift in y between A_SN1 = 2 (and separately A_SN2 = 2) and the fiducial parameters in the CAMELS-TNG emulator agrees with the shifts of the 'stronger winds x2' and 'faster winds x2' runs of the TNG model paper (the same parameters at four times the resolution) to a root mean square of 0.15 dex over z = 0.5 to 5. If it fails, E3 and E4 are stated for CAMELS resolution only (they are in any case).
* **V3 (frame of the unstated suites).** The mean CV curve of CAMELS-SIMBA agrees with the published SIMBA m100n1024 curve to within 0.3 dex (absolute mean) over z = 0.5 to 4, which supports treating the published SIMBA SFRD as comoving in S1.
* **V4 (emulator).** The 10-fold cross-validation root mean square error (on simulations within 0.5 of the fiducial cosmology) is at most 1.5 times the seed noise at every z in the grid; the emulator at the fiducial parameters agrees with the CV mean to within the larger of 0.05 dex and twice the standard error of the CV mean at every z up to 6.
* **V5 (stellar mass budget of the published curves).** For the runs that have both an SFRD and a stellar mass density curve (COLIBRE m6 L200, EAGLE Ref-L100N1504, FIREbox), the effective return fraction R_eff(z) = 1 - rho_*(z) / integral of SFRD above z at z = 0, 1, 2, 3 lies in [0.15, 0.60].

## 5. Power and calibration of the estimators

For E1, simulated before any real family spread was computed: seven families of Gaussian-process offsets (squared-exponential kernel, correlation length 1 or 2.5 in z, standard deviation 0.15 dex at z <= 1.75 growing log-linearly by the stated ratio to z = 6.25), the real grid, 200 replicates of each case, 300 bootstrap resamples.

| true SD ratio (high/low) | correlation length 1 | correlation length 2.5 |
|---|---|---|
| 1 (null) | success 3 % | success 4 % |
| 1.5 | 17 % | 19 % |
| 2 | 36 % | 31 % |
| 3 | 64 % | 65 % |
| 5 | 93 % | 93 % |

(success = both conditions of E1; the bootstrap condition alone is anti-conservative, 7-9 % at the null, and the Pitman-Morgan test alone is 4-5 %; phi is biased low by about 10 % of its value at n = 7.) With seven balanced families a funnel is detectable with about two thirds probability only if the spread grows by a factor of three. For E3 and E4 the controls (split halves) and the bootstrap are the calibration; the tests in `scripts/test_model_form.py` simulate an ensemble with a known structural offset and a known parametric range and check that both are recovered.

## 6. Sensitivity analyses (reported, not used to choose)

* S1 add SIMBA and Horizon-AGN (frame assumed comoving).
* S2 exclude boxes smaller than 30 cMpc (FIREbox, Romulus25).
* S3 bands low 0.25 to 2.0 and high 4.0 to 6.5.
* S4 convert to a Chabrier IMF with the website's offsets.
* S5 one random curve per family among its fiducial and its numerical variants (200 draws).
* S6 leave each family out.
* S7 window +-0.0625 and +-0.25 in z.
* S8 emulator degree 2 and 3, kernel width 0.35 and 0.8, ridge 1e-2 and 1e-4 (E3 and E4); observational error of E4 0.1 and 0.4 dex total.
* S9 cosmology free (x1 and x2 in [-1, 1]) in E3 and E4.

## 7. Limitations declared in advance

1. Nine families, seven balanced, are few: a failure to detect a funnel of modest size is not evidence against it (section 5).
2. The published curves differ in volume (from 22 cMpc to about 300 cMpc) and resolution; cosmic variance and numerical effects are not removed. E2 and the sensitivity S2 and S5 bound them.
3. Model families are not independent samples from a population of models: IllustrisTNG, Illustris and THESAN share subgrid heritage, EAGLE, FLAMINGO and COLIBRE another. The bootstrap treats families as exchangeable.
4. CAMELS boxes are 25 Mpc/h with 256^3 elements: star formation at z above about 6 is resolution-limited and the volume misses rare massive haloes at low z. E3 and E4 are about the response of the models at that resolution; they say nothing about the absolute SFRD of the full-resolution simulations. V2 tests one transfer.
5. The four CAMELS parameters of a code span the factors the CAMELS team chose, not the factors the code's authors would regard as acceptable; the reachable set depends on that prior (the shrinking-range report in E3 shows how).
6. Only two codes are in the designed experiment. Astrid and SWIFT-EAGLE have CAMELS runs but no star formation log was found for them; this analysis cannot say whether the TNG-SIMBA structural distance is typical.
7. The observational SFRD is a fit with a stated systematic error, not a measurement with a likelihood; E4's conclusions are conditional on it and on the error budget (S8).
8. Nothing here changes a stored record. Digitized curves have a stated 0.02 dex uncertainty and the SFRD lines are binned.

## 8. What had been looked at before this was written

* The 34 new digitized curves were drawn, rendered and read against their figures while they were extracted, so the visual impression that the TNG parameter variants span about an order of magnitude in SFRD at z < 5, that the FLAMINGO calibration and cosmology variants differ by well under 0.2 dex at z < 3, and that resolution changes the high-redshift SFRD by factors of several, was seen.
* The CAMELS file format, one stellar-mass closure check (IllustrisTNG LH_0: 0.59) and a pilot reduction of three LH and three CV simulations per code at nine redshifts (seed scatter 0.1 to 0.2 dex; a wide range of SFRD across LH; the fiducial CV curves of both codes 0.1 to 0.3 dex below the Madau and Dickinson curve at z = 0.1 and 2, computed by hand).
* Which families and how many have which redshift coverage, and the E1 power simulation of section 5 (synthetic data only).
* The V1 closure check of 12 IllustrisTNG simulations (ratios 0.58 to 0.60), the fraction of simulations without star formation at each redshift (below 1 % up to z = 8.1 for both codes), the seed scatter of the CV set (0.05 to 0.12 dex for both codes), and the cross-validation error of the degree 2 and 3 emulators relative to it (at most 1.3 times the seed scatter at the redshifts printed: 0.1, 0.9, 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1). The V1 and V4 thresholds and the redshift grid were written before these checks and were not changed by them.
* **Not** looked at: the between-family spread against redshift of the real curves, any class-wise variant deviation, any CAMELS emulator fit or its cross-validation, any parametric spread, offset or reachability distance, any posterior.

## 9. Amendments

(none yet)
