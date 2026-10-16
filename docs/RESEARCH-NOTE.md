# Can retuning make two galaxy-formation codes agree? Draft research note

Status: **draft for a reader who knows CAMELS.** Every claim below is one the evidence in this repository supports; claims that did not survive checking are listed at the end. Numbers are in noise units (1 = the scatter between one run of each code) unless a unit is given. Method and rules: `docs/PROTOCOL-joint-reachability.md` (written before the result); full result: `docs/ANALYSIS-joint-reachability.md`.

## Question

IllustrisTNG and SIMBA are two galaxy-formation codes, each with four feedback dials in the CAMELS suites (supernova wind strength and speed, black hole feedback strength and speed). Over the whole range of those dials, how close can retuning make one code's galaxy population come to the other's, property by property and all at once?

## Method in four lines

1. Emulate each of 186 galaxy-population outputs (mass function, quenched fraction, black hole properties, metallicities, sizes and others, at up to five epochs) as a polynomial in the dials, from 1,000 simulations per code.
2. Measure differences in units of the scatter between one run of each code, plus the emulators' own error.
3. For a set of outputs, search the dials of both codes for the smallest remaining difference.
4. Call the set *structural* if that difference stays above 1 across half-samples of the simulations and above what two halves of the same code give; *removable* if it falls to 1 or below; *unresolved* otherwise. The rule was fixed before the result and checked on synthetic worlds (0 of 17 worlds below 0.95 called structural; 8 of 8 above 1.1).

## What survived

1. **All at once, the codes stay 4.8 apart** (169 outputs, 35 blocks; half-sample range 4.6 to 4.9). A second implementation of the search gives 4.85 and a different kind of emulator 4.91. Other weightings of the outputs give 4.5 to 5.4 (`docs/ROBUSTNESS-joint-reachability.md`).
2. **Black hole occupation (9.5) and gas metallicity (1.7) stay apart at every setting of the dials tested** when taken alone (gas metallicity by 1.7 noise units, about 0.07 dex, which is beyond run-to-run scatter but small in absolute terms; the best settings sit at the edge of the dials' range, where the emulators are least tested). **Six of eleven properties can** (stellar mass function, quenched fraction, black hole mass, size, gas fraction, mass and SFR density). Three are borderline.
3. **Not just black hole occupation.** Without it the all-at-once distance is 3.7.
4. **One setting for all properties costs more than separate settings, but this is not claimed as a conflict.** Tuning each property with its own dials leaves 2.9; one set of dials for all leaves 4.8 (the squared distance is 2.8 times larger). The registered rule does not count that as above what two halves of the same code give (ratio 2.0, 95th percentile 2.7), so the result is classed as irreducible (a property is structural even alone) and not as a conflict between properties.
5. **A third code (exploratory):** on 97 outputs usable in all three codes, Astrid is 1.5 from TNG and 3.4 from SIMBA, and black hole occupation separates SIMBA from both others while TNG and Astrid agree. This suggests the black hole result is about SIMBA standing apart.
6. **Tuned to observed curves** (exploratory), either code reaches most stellar mass functions and quenched fractions easily (about 0.2 dex or less). Neither gets within one noise unit of the black hole mass relation (2 curves, 2.5 to 3.6 for the better code), one specific-SFR curve at z = 2.15, one quiescent mass function at z = 2.15 or the stellar metallicity curve; these rest on few curves with few bins. This is not a test of either code: definitions differ.

## What did not survive, or is not claimed

- **Not a discovery of difference.** CAMELS already reports that the codes differ; we add a size and a per-property answer, and have not established that the question is new (`docs/RELATED-WORK.md`).
- **Resolution.** Without the two lowest mass bins the all-at-once distance is 2.5, not 4.8. It stays above 1, but the headline depends on the faintest galaxies (`docs/RESOLUTION.md`).
- **Nothing about physical causes.** The dials of the two codes are not the same physical quantity; no claim is made about why a property is structural.
- **Nothing about other codes in general.** Three codes from one project at one resolution.
- **No observational test.** Simulation subhaloes are compared with each other; observations enter only in the exploratory fits above.

## A check on the edge of the dial range

The registered minimum sits at the edge of the range (4 of 8 coordinates on a bound), where the emulators are least tested. Afterwards, the simulations nearest each code's minimising setting were held out and predicted: their error is no worse than random simulations' (`docs/ANALYSIS-minimiser-check.md`). They are not at the minimum, and nothing has been run there.

## What a reader should check first

The choices never varied (`docs/CHOICES-joint-reachability.md`, rows marked *not tested*); the objections in `docs/SCEPTIC.md` marked *stands*; and whether the pre-registration timestamps can be trusted without an independent deposit.

## Reproduce

`python3 scripts/analyze_joint_reachability.py` (about 20 minutes on four cores) reproduces the registered numbers from `data/ensembles/camels-galaxies.json`; the exploratory checks are `scripts/explore_joint_robustness.py`, `scripts/explore_third_code.py` and `scripts/explore_tune_to_observations.py`.
