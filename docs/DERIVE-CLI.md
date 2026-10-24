# From your catalogue to a comparison: `sim-highline derive` and `sim-highline compare`

If you run simulations, two commands take a catalogue you hold to the nearest published curves, with the definitions and comparability rules the dataset and the website use:

```
sim-highline derive --format subfind --catalog groups_099/ --source MySim --run L25 --imf chabrier03 --baryon-particle-mass 1.4e6 --out run.json
sim-highline compare run.json
```

`derive` computes the standard relations (stellar mass function, star-forming main sequence, specific SFR, quenched fraction, size, stellar-to-halo mass ratio, black-hole mass, stellar and gas metallicity, HI and H2 fractions where the catalogue has them) with the same cuts for every catalogue, and writes them as records in the project's record format ([`schemas/curve-schema.json`](../schemas/curve-schema.json)). `compare` takes those records, or any file of records, and prints for each relation the nearest published observations and simulations that the rules allow, and in words why the others are not comparable. `derive --compare` does both in one command.

The one rule of `derive`: **a definition is taken from what you state or from what the file itself says, never assumed.** When the file does not say it and you did not, or when the file and your statement disagree, nothing is written; the message lists every such item, with the option that settles it.

## Install

```
pip install "sim-highline[derive]"      # the [derive] extra adds h5py, which reads the HDF5 catalogues
sim-highline derive --help
```

From a checkout: `python3 sim_highline.py derive ...`. `compare` needs only the base install (numpy, pandas).

## A worked example

The folder `tests/derive-cli/` holds a small synthetic catalogue for each format (2,000 galaxies; not a simulation, numbers drawn from simple laws so that the tests can check they are recovered; made by `scripts/make_derive_fixtures.py`). First, what happens when you state too little:

```
$ sim-highline derive --format subfind --catalog tests/derive-cli/subfind --out run.json
sim-highline derive: refusing to guess: 3 things the tool cannot know or that conflict
  1. source and run: the name of your simulation and of this run are yours to give. Add --source and --run (they appear in every record and in the comparison).
  2. imf: no catalogue format records the initial mass function the stellar masses assume. Add --imf (chabrier03, kroupa01, salpeter55).
  3. baryon particle mass: the resolution cut (stellar mass of at least 100 baryon particle masses) needs the initial baryon particle mass in Msun (not Msun/h). Add --baryon-particle-mass.
Nothing was written.
```

The exit code is 2 and `run.json` does not exist. With the statements added:

```
$ sim-highline derive --format subfind --catalog tests/derive-cli/subfind --source MySim --run L25 \
      --imf chabrier03 --baryon-particle-mass 1e6 --out run.json
sim-highline derive: 9 records written to run.json
  z = 0 (snapshot 99), groups_099: 2000 galaxies above the cut; relations written: gsmf, sfms, ssfr, quenched, size, shmr, bh, zstar, mzr
definitions used (each says whether you stated it or the file did):
  imf = chabrier03 (stated by you with --imf)
  baryon particle mass = 1e+06 Msun (stated by you)
  h = 0.6774 (read from the catalogue groups_099 (snapshot 99))
  omega_m = 0.3089 (read from the catalogue groups_099 (snapshot 99))
  box (comoving Mpc) = 36.9058 (read from the catalogue groups_099 (snapshot 99) (BoxSize in ckpc/h divided by h))
  units: lengths ckpc/h, masses 1e10 Msun/h (checked against the unit attributes in the file)
  mass: stellar mass within twice the stellar half-mass radius (SubhaloMassInRadType), SFR from SubhaloSFRinRad (the field's own definitions)
  SubhaloFlag: subhaloes flagged as not of cosmological origin are excluded
  calibration: not stated, so every record is marked unknown
```

Then the comparison (here only the stellar mass function, and only the first three of each list):

```
$ sim-highline compare run.json --relation gsmf --top 3
gsmf at z = 0: MySim L25 (derived.mysim.l25.gsmf.all.z0)
  observations: 5 published curves near this epoch, 5 fair to compare
    Wright et al. 2017 (GAMA-II) (z = 0.1, published-table): comparable with caveats; yours minus theirs: median +0.28, rms 0.51 log10(cMpc^-3 dex^-1) over 17 shared points
        caveat: massDefinition differs: yours is aperture-2rhalf-stars, the published curve's is sed-total
        ...
  simulations: 52 published curves near this epoch, 9 fair to compare
    ...
    not fair to compare: 43. Most common reasons (a curve can have several):
      41 curves: the published curve is marked context only (not for ranking)
      7 curves: densityFrame not documented: the published curve does not state it
      2 curves: shares fewer than 3 points with your curve (the mass ranges barely overlap)
```

The offsets of this example mean nothing physical: the catalogue is synthetic and its mass function is arbitrary. What the output shows is the form of the answer. "Fair to compare" means the rules allow the comparison (`comparable`, or `comparable with caveats`, each caveat listed); offsets are yours minus theirs in the y unit of the relation, evaluated at the x of the shorter curve and never extrapolated; a curve that shares fewer than three points with yours is not given an offset. These are the website's rules (`sim_highline.compare_run`, parity-tested against `compare.js` by `scripts/test_rules_parity.py`); `compare` adds no rule of its own. The counts in the listing above are those of the dataset when this page was written; they change when records are added or when a definition becomes a required match for a relation. Every record `derive` writes states its `population` (for example `all` for the mass function, `star-forming` for the main sequence), and a missing definition on either side is reported by name, for example `population not documented: your records do not state it` (a hand-made file of records without it) or `...: the published curve does not state it`.

## What each format needs

| `--format` | `--catalog` | read from the file, and checked | you must state | implied by the format |
|---|---|---|---|---|
| `subfind` | a folder (or one file) of group-catalogue files: `fof_subhalo_tab_NNN.*.hdf5`, `groups_NNN.*.hdf5` or `groups_NNN.hdf5`; one folder holds one or more snapshots | `Redshift`, `Time`, `BoxSize`, `HubbleParam`, `Omega0`, `OmegaLambda`, and `UnitLength_in_cm`/`UnitMass_in_g` | `--imf`, `--baryon-particle-mass`, `--source`, `--run`; `--units illustris` if the file carries no unit attributes; `--h`, `--omega-m`, `--box-mpc` for whatever the header lacks | stellar mass and SFR within twice the stellar half-mass radius (`SubhaloMassInRadType`, `SubhaloSFRinRad`), centrals from `GroupFirstSub`, halo mass `Group_M_Crit200` |
| `caesar` | one CAESAR `.hdf5` file per snapshot | redshift, `hubble_constant`, `omega_matter`, box and its units, the `unit` attribute of every dataset | `--imf`, `--baryon-particle-mass`, `--source`, `--run`; `--snapshot` if the file name has no number | total stellar mass of the 6D-FOF galaxy; M200crit (`m200c`) |
| `soap` | one SOAP `halo_properties_NNNN.hdf5` per snapshot | redshift, box (accepted only if plausibly comoving Mpc), `Cosmology` h and Omega_m, the CGS conversion attribute of every dataset | `--aperture` (always; for example `50kpc`, a group under `ExclusiveSphere`), `--imf`, `--baryon-particle-mass`, `--source`, `--run` | stellar mass and SFR in that exclusive sphere; M200crit from `SO/200_crit` |
| `eagle` | a CSV of the result of the query below | redshift and snapshot per row | `--units eagle-database`, `--aperture 30pkpc`, `--h`, `--omega-m`, `--box-mpc`, `--imf`, `--baryon-particle-mass`, `--source`, `--run` | 30 pkpc aperture quantities; sizes are `R_halfmass30` |

The EAGLE table is the output of the query in `scripts/derive_eagle_relations.py` (`EAGLE_QUERY`, one snapshot at a time; the columns are `GalaxyID, SnapNum, Redshift, SubGroupNumber, Mass_Star, SFR, Mass_BH, R_halfmass30, Group_M_Crit200`). It must hold every galaxy above 100 baryon particle masses; the tool refuses a table whose smallest stellar mass is more than twice that cut. `derive` never asks for a password: you run the query where you have access and give it the table. (The script `derive_eagle_relations.py` reads the database directly with your credentials; that is its own business and unchanged.)

The other options: `--calibrated-on gsmf,size` says which relations your run was tuned to at z < 0.2 (those records are marked `target` below z = 0.2; everything else is `unknown`, which is what the tool writes when you say nothing); `--url` is an https address that describes your catalogue (default: this page, which is where the method is described, not where the data are; the record's `citation` says the catalogue was supplied by the user and is not a public release); `--distributions` also writes the per-galaxy specific-SFR distribution as its own record; `--top N` sets the rows per list with `--compare`.

## What it refuses, always

- No IMF, no baryon particle mass, no source or run name: stated by you or not done. The IMF must be one of `chabrier03`, `kroupa01`, `salpeter55`, the three the comparison rules can convert between.
- Units that the file does not attest (Subfind without unit attributes, an EAGLE table) unless you state the convention; units that the file attests and that differ from the convention; any dataset whose unit is not one the tool knows (CAESAR, SOAP).
- h, Omega_m or the box size that neither the file nor you gives; a stated value that disagrees with the file (the tool does not choose between them); a Subfind catalogue whose cosmology is not flat; catalogues of one run that disagree on h or Omega_m.
- The SOAP aperture; an aperture that is not in the file; an EAGLE aperture other than 30 pkpc.
- A CAESAR catalogue whose only halo mass is the mean-density `m200` (the halo-mass relation would not be M200crit); a SOAP box that is not plausibly in Mpc.
- Fields or columns the relations are built on (the stellar mass, SFR, halo mass and centrals) when they are missing. Optional ones (sizes, black holes, metallicities, gas) are left out and the report names the relations not derived.

`scripts/test_derive_cli.py` has one case for each of these and fails if the tool starts to accept one. Everything the tool did decide is written in each record's `notes` (where each value came from) and `selection.warning` (the cuts).

## Python

```python
import sim_highline as sh, sim_highline_derive as sd
payload = sd.derive_run("subfind", "groups_099/", source="MySim", run="L25", imf="chabrier03", baryon_particle_mass=1.4e6)   # raises sd.UnderSpecified (a ValueError) with .problems
sd.write_payload(payload, "run.json")
sh.compare_records_cli(payload["records"], relations=["gsmf"])
```

## What the records are, and are not

- The same cuts as the dataset's catalogue-derived records: stellar mass of at least 100 baryon particle masses, bins of 0.2 dex, at least 10 galaxies for a median, comoving volumes, Poisson errors on the mass function. Nothing is converted for IMF, aperture or cosmology; differences appear as caveats, as in the Explorer.
- Subfind and SOAP objects are subhaloes or exclusive spheres, not galaxies on the sky; cosmic variance of your box is not in the error bars.
- Definition names follow the dataset's vocabulary so that the rules can match them (for example `aperture-2rhalf-stars`, `aperture-50pkpc`). The four scripts keep the labels they have always written (`aperture-2x-stellar-half-mass-radius`, `aperture-50pkpc-exclusive`), because their output must stay identical; `derive` and the scripts therefore differ in that one field for the same catalogue.
- The Subfind star-formation cut and the quenched fraction use the formulas of the scripts (`sSFR > 0.2 / t_age(z)`; `sSFR < 1e-11 /yr`). The solar metallicity of the stellar-metallicity relation is 0.0127, as stated in the record's axis definition.

## What was checked, and what was not

Checked by the author's tests only, no outside reader: the four formats on the synthetic catalogues (the injected stellar-to-halo ratio, sizes, quenched share, HI fraction and the box volume are recovered); the records pass `scripts/validate-curves.mjs` and the schema; each refusal above; and the scripts still write exactly what they wrote before their code moved into `sim_highline_derive.py` (sha256 of their output on these catalogues, recorded from the old scripts, in `tests/derive-cli/script-output-hashes.json`; also checked by diffing old and new output on the catalogues of the older pipeline tests).

**Not checked:** no real TNG, SIMBA, FLAMINGO, COLIBRE or EAGLE catalogue was available here, so the file layouts are those the existing scripts and their tests already assumed (and, for the unit attributes of Subfind files and the `Cosmology` group of SOAP files, the documented layouts, not a file). If a real file does not match, the likely result is a refusal that names the missing attribute, which is the intended failure. A report from a real catalogue is the most useful next check.
