# Resolution: what it can do to these results

Everything in this project that comes from CAMELS is at CAMELS resolution: 25 Mpc/h boxes with 256³ dark matter and 256³ gas elements. That is coarse. A galaxy with 10⁹ solar masses of stars is about 80 star particles (one is about 1.3×10⁷ solar masses); black holes are planted by a rule that depends on resolution; star formation and black hole growth are both resolution-dependent in both codes. The pre-registered protocol declared this in advance (limit 2 of section 9), and the results are statements about CAMELS resolution, not about the codes at any resolution.

## What the project measured

- **Dropping the two lowest mass bins takes the all-at-once distance from 4.8 to 2.5** noise units (registered sensitivity S8, 28 blocks left). It stays above the margin of 1. This is the largest change of any sensitivity, so the headline number is partly about the faintest galaxies, where resolution matters most.
- **Black hole occupation** (the fraction of galaxies that have a central black hole at all) is the property that separates the codes most, and it is also the one most set by a resolution-dependent rule. The smallest non-zero black hole masses in the two catalogues differ by a factor of about 40 (1.2×10⁶ in TNG, 2.8×10⁴ solar masses in SIMBA, from the amendment A1 input checks), because the codes seed black holes differently. Without black hole occupation the distance is 3.7; without both black hole properties 3.8.
- **High redshift**: at z = 3 and 4 only the stellar mass function and the two densities have enough usable bins, and the protocol says so.

## What the project did not measure

- No simulation at a different resolution has been run or ingested, so nothing here shows how the distances would change with resolution. The only evidence is the mass-bin cut above, which is indirect.
- No convergence test of either code at CAMELS resolution is reproduced here.

## Where to look

These are pointers, not checked quotations (the full texts have not been read for this note):

- the CAMELS papers (Villaescusa-Navarro et al. 2021, ApJ 915, 71, and the data release paper, arXiv:2201.01300) for the box, the particle numbers and the parameter definitions;
- the IllustrisTNG methods paper (Pillepich et al. 2018, MNRAS 473, 4077) for how the model was calibrated at fixed resolution and what happens at other resolutions;
- the SIMBA paper (Davé et al. 2019, MNRAS 486, 2827) for the resolution dependence of its black hole seeding and growth.

## What to do about it

A reader who needs the result to hold at higher resolution should not use this project for that. The useful next test is the same analysis on a set of runs at a second resolution of the same model, which CAMELS does not provide.
