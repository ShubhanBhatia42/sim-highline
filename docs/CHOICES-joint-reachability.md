# Every choice that could have changed the all-at-once result

The headline of the all-at-once study: after each code has had its four dials tuned as well as possible, IllustrisTNG and SIMBA stay **4.8 noise units apart** over 169 outputs in 35 blocks (one noise unit is the scatter between one run of each code). Each row below is one decision that went into that number, what was chosen, and what happened to the number when the decision was changed. Rows marked *registered* were varied in the pre-registered sensitivity analysis; rows marked *exploratory* were checked after the run (`docs/ROBUSTNESS-joint-reachability.md`, `docs/ANALYSIS-third-code.md`) and change no verdict. Rows marked *not tested* are choices nobody has varied yet.

| decision | what was chosen | when changed | status |
|---|---|---|---|
| Which properties count | 11 properties (mass function, quenched fraction, main sequence, black hole mass, black hole occupation, gas metallicity, stellar metallicity, size, gas fraction, stellar-to-halo mass ratio, stellar mass and SFR density); the halo mass function is kept apart as a control | without black hole occupation 3.7; without both black hole properties 3.8; without the two densities 5.2; without the two densities and the halo-mass ratio 5.4 | registered and exploratory |
| Which epochs | z = 0, 0.95, 2.15, 3, 4 wherever the outputs are usable | z = 0 and 0.95 only: 3.8 | registered |
| Which mass bins | all eligible bins | without the two lowest mass bins: **2.5** (the biggest change of any row; still above 1) | registered |
| Which outputs are usable | at least 90 % of the 1,000 simulations give a value and at least 20 of the 27 same-parameter runs do: 186 of 530 outputs | other thresholds | *not tested* |
| How outputs are weighted | every block (a property at one epoch) gets the same total weight | every output the same: 4.5; every property the same: 4.5 | exploratory |
| The unit of distance | the scatter between one run of each code, plus the emulators' own error, with a floor of 0.02 | without the emulator error: 5.9; floor 0.01: 4.9; floor 0.05: 4.1 | registered |
| The emulator | polynomial of degree 2 or 3 chosen per code by cross-validation (both chose 3) | degree 2: 4.8; degree 3: 4.8; kernel width 0.35: 4.8; width 0.8: 4.8; a different kind of emulator (kernel ridge): 4.9 | registered and exploratory |
| The search | projected gradient descent from the fiducial point and random starts | a second optimiser (L-BFGS-B, 40 starts): 4.85 | exploratory |
| The range of the dials | the full CAMELS box | cut to 75 % of the half-width: 5.0 | registered |
| Emulator noise at the minimiser | removed in quadrature (amendment A1) | uncorrected: 4.85 against 4.82 corrected | registered |
| The margin that makes a result "structural" | 1 noise unit | margin 2: still structural (half-sample median 4.8) | registered |
| Cosmology | fixed at the fiducial point in the dials and the search | other cosmologies | *not tested* |
| Which dials | the four astrophysical dials of each code that CAMELS varies | any other parameter of either code | *not tested*, and not testable with this data |
| Which codes | IllustrisTNG and SIMBA | adding Astrid: TNG–Astrid 1.5, SIMBA–Astrid 3.4 on the 97 outputs usable in all three | exploratory |
| Which simulations feed the emulator | the 1,000 Latin-hypercube runs per code | half-samples: 200 random halves, median 4.8, 5th to 95th percentile 4.6 to 4.9 | registered |
| The random seed | 20261016 | other seeds | *not tested* (the half-sample spread is the guide) |

## What this says

- The headline moves between 3.7 and 5.9 across everything that was varied except the mass-bin cut, which takes it to 2.5. It never falls below the margin of 1.
- The two choices that move it most are about **which outputs** (the low-mass bins, the black hole occupation) and about **what the unit is** (with or without the emulator error). Neither is a bug; both are judgement calls and both are listed so that a reader can make a different one.
- Choices that were never varied are listed above as *not tested*. They are the first place to look for a result that does not survive.
