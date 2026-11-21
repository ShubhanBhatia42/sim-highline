# `sim-highline derive` on a real catalogue: one CAMELS-TNG box

Until now `derive` had been tested only on synthetic catalogues (`tests/derive-cli/`). This page is the first run on a real, public catalogue: the z = 0 Subfind catalogue of one cosmic-variance box (`CV_0`, 25 Mpc/h on a side) of CAMELS-TNG. The same box is already in the dataset as one of the 27 that make up the stored CAMELS-TNG curves, so the result can be set beside a reference that the project's other pipeline made from this box and 26 others. One box, one snapshot, one code: read the last section before drawing anything from it.

## What was done

The file is on the public CAMELS server and needs no account (16 MB):

```
mkdir camels-tng-cv0 && cd camels-tng-cv0
curl -fLO https://users.flatironinstitute.org/~camels/Sims/IllustrisTNG/CV/CV_0/groups_090.hdf5
cd ..
sim-highline derive --format subfind --catalog camels-tng-cv0 --out run.json
```

The last command refuses, as it should, and lists three things only the user knows: the names of the source and run, the initial mass function, and the baryon particle mass. Nothing is written. What was stated:

| Stated | Value | Where it comes from |
|---|---|---|
| `--source`, `--run` | `CAMELS-TNG`, `CV_0` | the names the dataset already uses |
| `--imf` | `chabrier03` | the TNG model paper (Pillepich et al. 2018), as the stored CAMELS curves already assume; the CAMELS paper does not restate it |
| `--baryon-particle-mass` | `1.89e7` Msun | the CAMELS paper (Villaescusa-Navarro et al. 2021, section 3) gives the initial gas element mass as 1.27×10⁷ h⁻¹ Msun; divided by h = 0.6711, which the file states, that is 1.89×10⁷ Msun |

```
sim-highline derive --format subfind --catalog camels-tng-cv0 --source CAMELS-TNG --run CV_0 \
    --imf chabrier03 --baryon-particle-mass 1.89e7 --out run.json
sim-highline compare run.json
```

Everything else was read from the file or checked against it: h = 0.6711, Ω_m = 0.3, the box (25 000 ckpc/h = 37.25 comoving Mpc) and the units (the file carries its unit attributes). The file has no `SubhaloFlag`, so no subhalo is excluded as spurious, and the report says so. Nine records were written (stellar mass function, star-forming main sequence, specific SFR, quenched fraction, size, stellar-to-halo mass ratio, black-hole mass, stellar metallicity, gas metallicity). The committed records are `tests/derive-cli/camels-tng-cv0-derived.json`.

## What was checked

The stored CAMELS-TNG curves are the mean over the 27 boxes of a per-box statistic, measured with the total stellar mass of the subhalo and a lower limit of 10⁹ Msun. `derive` uses the dataset's catalogue definitions: the stellar mass within twice the stellar half-mass radius and a lower limit of 100 baryon particle masses. They differ on purpose, so the comparison is a test of whether the rules notice that, and how large it is.

<!-- result-table:start -->
| Relation | What `compare` says | Offset: derived box minus the stored 27-box mean (median over the shared points; unit of the relation) | of which: the definitions (the same box measured both ways) | of which: this box against the mean of the 27 boxes | Scatter between the 27 boxes (1 SD) | Definitions that differ |
|---|---|---|---|---|---|---|
| quenched fraction | comparable with caveats | +0.02 fraction | +0.04 | -0.01 | 0.07 | massDefinition: aperture-2rhalf-stars vs total-bound-subhalo |
| stellar size | comparable with caveats | +0.02 dex | +0.02 | -0.01 | 0.02 | massDefinition: aperture-2rhalf-stars vs total-bound-subhalo |
| stellar-to-halo mass ratio | comparable with caveats | -0.11 dex | -0.09 | -0.01 | 0.04 | massDefinition: aperture-2rhalf-stars vs total-bound-subhalo |
| black-hole mass | comparable with caveats | +0.15 dex | +0.09 | -0.01 | 0.09 | bhMassMethod: intrinsic vs intrinsic-sum-of-bh-particles; massDefinition: aperture-2rhalf-stars vs total-bound-subhalo; population: centrals vs bh-hosts |
| stellar metallicity | comparable with caveats | +0.03 dex | +0.02 | +0.00 | 0.01 | massDefinition: aperture-2rhalf-stars vs total-bound-subhalo |
| gas metallicity | not comparable | not given | not given | not given | not given | metallicityQuantity: gas-O/H vs gas-metal-mass-fraction; metallicityCalibration: intrinsic-simulation (SFR-weighted) vs intrinsic-simulation (star-forming gas, SFR-weighted; Zsun = 0.0127); population: star-forming vs all galaxies with non-zero SFR; massDefinition: aperture-2rhalf-stars vs total-bound-subhalo |

- The file is 16,278,844 bytes, SHA-256 `2c8b25df9c8f7b8c8dd44a5e8b9695250e45fcc7773ae85099ad63de0fc2d3d4`. The hash of the arrays the ingest script reads from it, and the per-box summary computed from them, equal the values stored in `data/ensembles/camels-galaxies.json` for this box: yes.
- `derive` kept 304 galaxies above the resolution cut (100 baryon particle masses = 1.89e9 Msun of stellar mass within twice the half-mass radius).
- Separate plain-numpy code, written from the documented definitions and reading the same file, reproduces every point and count of 5 of the 5 relations that can be compared (quenched, size, shmr, bh, zstar): all agree to the last digit.
- Stellar-to-halo mass ratio recomputed with the stellar mass of the whole subhalo instead of the mass within twice the half-mass radius (cut and bins unchanged, 6 shared points): the aperture version lies -0.112 dex from it, and the whole-subhalo version lies +0.006 dex from the stored 27-box mean (the offset of the aperture version is -0.113 dex).
<!-- result-table:end -->

Offsets are medians over the points the two curves share, as `compare` prints them; the three columns are medians of their own differences and need not add up exactly. The scatter is the standard deviation of the 27 box values, averaged over the shared points.

## Reading it

- The numbers `derive` wrote are right for what they say they are: an independent recomputation agrees exactly, and the file is the one the stored summaries were made from.
- The rules did what they are for. Five relations came out as "comparable with caveats", each naming the definition that differs, and the gas metallicity came out as "not comparable" because `derive` writes 12 + log(O/H) and the stored curve is the metal mass fraction: they are different quantities, and no offset is given.
- For the stellar-to-halo mass ratio the stated caveat accounts for the offset. The derived curve lies 0.11 dex below the stored mean, which is about three times the scatter between boxes (0.04 dex), and recomputing it with the whole subhalo's stellar mass brings it to within 0.01 dex. For the quenched fraction the difference from the mean is about a third of the scatter between boxes, and for the size about the same as it. For the stellar metallicity (two and a half times the scatter) and the black-hole mass (1.7 times) it is larger, and the listed definitions are the likely reason, but that was not tested here.
- This box lies close to the mean of the 27: its median distance from the mean is 0.011 or less in every relation and smaller than the scatter between boxes, so on these relations one box was a fair stand-in for the suite.

## Two small findings about `derive` itself

- The report printed the redshift as `z = 2.22e-16`, the floating-point noise in the file's header. The record already stored it rounded to 4 decimals; the report line now does too.
- The black-hole mass is the same Subfind field (`SubhaloBHMass`) in both pipelines, but `derive` labels it `intrinsic` and the CAMELS curves `intrinsic-sum-of-bh-particles`, so the rules list a difference that is not one. The two scripts that share this code must keep writing `intrinsic` (their output is pinned by hashes), and the rule is a caveat, not a blocker, so nothing was changed; whether the vocabulary should merge the two labels is open. The same relation also differs in population (central galaxies against every galaxy that hosts a black hole), which is a real difference.

## What this does not show

- One box at one redshift from one code. The other formats (CAESAR, SOAP, the EAGLE table) have still not met a real file, and neither has a catalogue larger than 16 MB.
- The baryon particle mass was stated by the person running it, from the paper. `derive` cannot check it, and a wrong value moves the resolution cut. Here the cut leaves 304 galaxies, 10 to 55 per bin, and the derived curves start at a stellar mass of 10^9.3 Msun where the stored ones start at 10^9.1.
- The independent recomputation was written by the same person from the same documentation, so it catches slips in the code, not a misreading of what a definition should be.
- The split into "definitions" and "box" uses the stored per-box values of the same pipeline; only the stellar-to-halo ratio was tested directly.
- No outside person has run it. A report from someone else's catalogue is still the most useful next check.

## Reproduce it

`scripts/derive_real_example.py` takes the folder `camels-tng-cv0` (the folder's name is part of the records' notes), repeats the checks above and prints the table; with `--write` it rewrites the committed files. `scripts/test_derive_real.py` checks, without the download, that the committed records are valid, that the table and the sentences above follow from them and from the stored curves, and that this page contains exactly the generated table; with `SIMHL_CAMELS_CV0=camels-tng-cv0` it also repeats the whole run on the file and requires the same result.
