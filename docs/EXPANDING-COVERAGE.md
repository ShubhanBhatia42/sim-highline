# Expanding coverage on your machine

`data/sources-catalogue.json` lists every machine-readable product found so far with its status (`ingested`, `run-locally`, `discovered`, `request-only`). The `run-locally` adapters are tested on synthetic catalogs (`scripts/test_subfind_pipeline.py`, `scripts/test_colibre_gsmf.py`) and only need downloads or credentials that the build sandbox cannot reach.

```bash
# COLIBRE GSMF, 13 runs, z = 0-17 (Chaikin et al. 2026; public, CC-BY-4.0)
curl -o data/raw/2509.07960.yml https://colibre.strw.leidenuniv.nl/paper_data/2509.07960.yml
python3 scripts/ingest_colibre_gsmf.py data/raw/2509.07960.yml

# IllustrisTNG: fetch only the needed group-catalog fields (documented API subset endpoint, free API key)
TNG_API_KEY=... python3 scripts/fetch_tng.py TNG100-1 <root>
# (or download full group catalogs into <root>/groups_NNN/), then
python3 scripts/derive_subfind_relations.py TNG100-1 <root>
python3 scripts/derive_subfind_relations.py TNG50-1  <root50>
python3 scripts/derive_subfind_relations.py TNG300-1 <root300>

# EAGLE (free registration at virgodb.dur.ac.uk; pip install eagleSqlTools)
python3 scripts/derive_eagle_relations.py RefL0100N1504 --user <u> --password <p>

# FLAMINGO (public data release; SOAP halo catalogues, one file per snapshot)
python3 scripts/derive_soap_relations.py flamingo L1_m9 <baryon particle mass in Msun> halo_properties_*.hdf5

# Everything at once (skips any source whose credentials are not set)
TNG_API_KEY=... EAGLE_USER=... EAGLE_PASSWORD=... FLAMINGO_SOAP_DIR=... scripts/fetch_all.sh

# CAMELS or any other Subfind run
python3 scripts/derive_subfind_relations.py CAMELS-TNG-CV0 <dir> --flat --snaps 90 --source "CAMELS IllustrisTNG" --mbar <Msun> --h 0.6711 --Om 0.3
```

The Subfind and EAGLE pipelines apply identical cuts to every run (resolution limit of 100 baryon particle masses, 0.2 dex bins, at least 10 galaxies per median, sSFR > 0.2/t_age(z) for star-forming, sSFR < 1e-11 /yr for quenched). The only intended difference is the aperture: twice the stellar half-mass radius for TNG/Illustris group catalogs, 30 pkpc for EAGLE; the definition check reports it.


## A fourth code for the measured conversions: what was checked (2026-10-23)

The question: can a fourth code be added to `docs/CONVERSIONS.md` (stellar mass within an aperture, SFR, metallicities, M200crit, against the catalogue's own totals) from public sources that need no account or key? Checked by HTTP requests from the build machine; "not verified" means the check did not settle it. Nobody outside the project has reviewed this.

| Candidate | Access (evidence) | What is there | Verdict |
|---|---|---|---|
| CAMELS Swift-EAGLE, `Sims/Swift-EAGLE/L25n256/{CV,1P,LH}` | public HTTP, 200; the CV seeds hold `snapshot_NNN.hdf5` (1.2 to 1.8 GB each), `ICs/`, `extra_files/` | particles only, no `groups_NNN.hdf5` | no catalogues here. This is the only place the earlier version of this page looked. |
| CAMELS Swift-EAGLE, `FOF_Subfind/Swift-EAGLE/L25n256/CV/CV_0 ... CV_26/groups_{090,062,042}.hdf5` | public HTTP, 200 on all 81 files (27 seeds x 3 snapshots), 44 to 68 MB each, 4.35 GB in all; the three snapshots have z = 0, 0.951, 2.148, h = 0.6711, box 25000 ckpc/h | Subfind catalogues with every array the pipeline reads (`SubhaloMassType`, `SubhaloLenType`, `SubhaloMassIn{Rad,HalfRad,MaxRad}Type`, `SubhaloSFR`, `SubhaloSFRin{Rad,HalfRad,MaxRad}`, gas and stellar metallicity in the five weightings, `SubhaloMass`, `Group_M_Crit200`, `GroupFirstSub`); 47 subhalo and 25 group arrays in all (read in CV_0 at z = 0); stellar half-mass aperture median -0.301 to -0.306 dex in CV_0 at z = 0, as the definition requires | **usable** |
| CAMELS Magneticum, Ramses, CROCODILE, Obsidian, Enzo (first generation) | the Data Access page of the CAMELS documentation lists them as "Private" and says to fill in a form; none of them is in `Sims/` or `FOF_Subfind/` | | excluded (not credential-free) |
| CAMELS Multifield Dataset (`CMD/`) | public, 200: `2D_maps/` (1.1 TB) and `3D_grids/` (122 TB) | maps and grids, no subhalo catalogue | no aperture fields |
| CAMELS `Caesar/` (SIMBA, IllustrisTNG) | public, 200 | the same two codes as before | not a new code |
| SIMBA main run (`simba.roe.ac.uk`) | connection reset on two requests (not verified) | would be the same code as CAMELS-SIMBA | not a new code even if reachable |
| FIRE-2 public release (FlatHUB, `fire.northwestern.edu/data`) | public, 200; the project page lists z = 0 raw snapshots of m12f, m12i and m12m among other products | particles for a handful of zoom-in galaxies, no aperture catalogue | not done: an aperture would have to be measured by our own centre-and-bound rule on 3 or a few more galaxies, with no seed-to-seed spread and no box; that is a different kind of number and would be labelled as such, not put beside the 27-box ones |
| EAGLE public release (`icc.dur.ac.uk/Eagle/database.php`) | 200; the page says both the database and the particle data need an account | | excluded (account) |
| COLIBRE | `colibre.strw.leidenuniv.nl/paper_data/*.yml` public, 200 (already used for the mass function) | published tables, no catalogue | no aperture fields |
| FLAMINGO | project page 200, SOAP documentation 200; the data-access page I tried (`/data_access.html`) is 404 | SOAP catalogues have aperture masses, but I did not find a credential-free download | not verified; stays `run-locally` above |
| IllustrisTNG, Illustris (`tng-project.org/api`) | 403 without a key | | excluded (key) |
| Horizon-AGN, NewHorizon | home pages 200 (19 and 29 lines of text) | no data download or catalogue named on the pages read | not verified |
| Magneticum (`c2papcosmosim.uc.lrz.de`) | 200; the page says to log in or register for the services | | excluded (account) |

Licence and terms: the pages of the CAMELS documentation read (home, data access, organization, Subfind, citation) state no data licence; the citation page asks for the CAMELS paper (Villaescusa-Navarro et al. 2021, ApJ 915, 71). The Swift-EAGLE simulations are described there only as "Swift" and "EAGLE" subgrid model, with no describing paper named.

Two cautions from the CAMELS documentation that apply here. (1) The home and Subfind pages say that a bug in the generation of the Subfind catalogues affected all Swift-EAGLE sets (1P, CV, LH), that "all the data in the public FOF/Subfind directories is now fixed" and that the old data are available on request. The `groups_*.hdf5` files read here are dated 2025-06-17 in the directory listing; whether that is after the fix is not stated, so the fix is taken from the documentation and not tested here. (2) The same warning lists the SIMBA CV and 1P sets, and the first three codes of the measurement were read from `Sims/<code>/CV/` (SIMBA files dated 2023-05-03), not from `FOF_Subfind/<code>/L25n256/CV/` (SIMBA directory dated 2025-07-27). So the first three codes were checked against the current `FOF_Subfind` files: for all 243 files (3 codes, 27 boxes, 3 snapshots) the SHA-256 of the arrays the pipeline reads is identical to the one recorded when the `Sims` files were read. Their numbers are therefore not affected by the bug for the arrays used (this says nothing about the arrays not used).

Result: Swift-EAGLE was added to `data/conversions.json` and `docs/CONVERSIONS.md` (27 boxes, 3 snapshots, 81 files, no read errors); the blocks of the first three codes are byte-identical to before. Differences that a reader should know are written in the Swift-EAGLE point of `docs/CONVERSIONS.md` (a different place and probably a separate Subfind run; the SFR in the 2 R_half aperture falls below the total at high mass, unlike the first three; no paper or licence named by the CAMELS pages). No resolution test has been run for any of the four codes.

Cheapest next steps, in order: (a) ask the CAMELS authors for the paper that describes the Swift-EAGLE variant and the date of the catalogue fix (the contact address is on the CAMELS Data Access page); (b) find out whether the FLAMINGO SOAP catalogues can be fetched without an account (the one data-access URL tried was 404), which would add a code with real aperture fields at a much larger volume but at lower resolution; (c) a resolution test is not possible inside the first-generation CAMELS sets (one resolution); the `L50n512` tree of IllustrisTNG (listed at 11.9 TB, not opened) holds second-generation runs and might allow one for that code only.

## Emission-line luminosity functions: what is in, what is not (2026-10-23)

Relation `elf`, H-alpha only so far. In: Sobral et al. 2013 (table, `scripts/ingest_elf_sobral13.py`), Covelo-Paz et al. 2025 (table, `scripts/ingest_elf_covelopaz25.py`), SPHINX20 (computed from the data release, `scripts/ingest_elf_sphinx20.py`). Two keys decide fairness: `line` (H-alpha alone, or blended with [NII]; [OIII] 5007 alone, or with the other doublet line and H-beta; [OII] doublet) and `dustCorrection` (`intrinsic`: no dust in a simulation, or an observation corrected for dust; `attenuated`: as observed or after dust in a simulation). How the correction was made goes in `dustCorrectionMethod` (a caveat, not a block), the region in `apertureDefinition`.

Read, with the sentence that fixes the definition, but not ingested:

- Hirschmann et al. 2023 (arXiv:2212.02522), IllustrisTNG: H-alpha, [OIII]+H-beta and [OII] functions for TNG50, TNG100 and TNG300 at z = 0.1 to 6 in a vector figure (`Ha_lumfct_IllustrisTNG_allz_Nov21.eps`). Dust: "we do not consider attenuation by dust outside H II regions" (intrinsic); aperture: "all `bound' gas cells and star particles". It would be a digitized (not rankable) record set, 27 curves for H-alpha. The HiZELS Schechter curves drawn in the same figure could calibrate the axes against `ingest_elf_sobral13.py`. Best next step.
- Khostovan et al. 2015 (1503.00004, [OII] and H-beta+[OIII], HiZELS) and Gunawardhana et al. 2013 (1305.5308, H-alpha, GAMA): the LaTeX sources hold tables; their line and dust definitions were not read.
- FLARES XI (2301.13038): [OIII] 5007 and [OIII]+H-beta functions in vector figures (`LF_OIII5007.pdf`, `LF_OIIIHb.pdf`); no [OIII] observation is ingested to compare them with, so they were left.

Seen only in search results or not opened: the two IllustrisTNG JWST-prediction papers (1904.07238, 2002.10474); JELS (2609.01586), COSMOS-3D (2510.11373), FRESCO [OIII] (2405.05111), Sun et al. 2023, Matthee et al. 2023, Colbert et al. 2013, Mehta et al. 2015, Comparat et al. 2016 (1605.02875). A paper on H-alpha functions of Illustris-1 (arXiv id 2608.30698 in the search result) could not be opened and its identifier was not verified.

No published H-alpha, [OIII] or [OII] luminosity function was found for EAGLE (only star formation rate functions), SIMBA (emission-line modelling reported, no function), THESAN (line-luminosity relations, no function found), Astrid, FIRE or COLIBRE. That is the result of web searches and of reading abstracts, not an exhaustive survey.

The SPHINX20 records are computed from the release rather than read from the paper's plot, because the plotted function (reddening-corrected along each sight line) has no stated reddening coefficient. The release's columns reproduce the plotted curves to 0.015 dex rms with k(H-alpha) = 2.2, a value fitted here, not taken from the paper; the records therefore hold the two versions that have a stated meaning (intrinsic, and dust attenuated along ten sight lines).

## Papers looked at in the coverage round of 2026-10-24 and not ingested

Reason in one line each; none was read in full. A rejected paper is not a bad paper: it is one where the numbers could not be checked against anything the paper prints.

- Obelisk (2002.04045): vector figures for the mass function, UV luminosity function, SFR density, stellar-to-halo mass and black hole mass at one protocluster zoom; step-function histograms, a units inconsistency between text and axis (h^3 cMpc^-3 against cMpc^-3) and no printed number to check the axes against beyond "about 1e-2".
- FirstLight (2404.02537): mass and UV luminosity functions are drawn as Poisson bands with no central curve; the integrated efficiency is normalised by a baryon fraction whose value the paper does not give.
- CROC I (1403.4245): UV luminosity functions at six redshifts in one panel, each shifted by 1 dex, with no table and no printed value to check against.
- Renaissance (1503.01110), CoDa I (1511.00011), Horizon Run 5 (2408.07258), FLARES I (2004.07283, the main figures): raster images.
- Aurora (1603.00034): vector figures but their tick labels are outlined paths (no text layer) and the paper has no table; not read.
- Hydrangea (1703.10610): the mass functions are those of cluster satellites, several normalised by cluster mass, which is not a number density; not read.
- Dianoga (2006.13951): vector figures of the z = 0 mass function, the z about 2 main sequence and gas fractions exist; not read within the three-paper cap, a candidate for a later round.
- HESTIA (2008.04926): outlined tick labels; the table of z = 0 Local Group properties could give a stellar-to-halo mass table; not read.
- LYRA III and LYRA (Sureda) (2209.03366, 2511.10582), VELA (2210.15372), EDGE (1909.04664, 2004.09530), VINTERGATAN III (2006.06012): a handful of individual simulated galaxies each (VELA a larger set of zoom-ins); their tables of z = 0 properties could give stellar-to-halo mass and size points; not read.
- Romulus25 (Jung et al. 2022, 2203.00016): vector stellar-to-halo mass figure of group centrals; not read, a candidate.
- THESAN data release and companions (2309.06475, 2110.01628, 2110.02966): mostly data-release and intergalactic-medium content; the THESAN-1 relations they show are already in the dataset, and the THESAN-2 against TNG comparison figures of 2110.01628 were not read.
