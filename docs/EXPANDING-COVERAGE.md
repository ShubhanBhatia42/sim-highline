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
| CAMELS Swift-EAGLE, `FOF_Subfind/Swift-EAGLE/L25n256/CV/CV_0 ... CV_26/groups_{090,062,042}.hdf5` | public HTTP, 200 on all 81 files (27 seeds x 3 snapshots), 44 to 68 MB each, 4.35 GB in all; the three snapshots have z = 0, 0.951, 2.148, h = 0.6711, box 25000 ckpc/h | Subfind catalogues with every array the pipeline reads (`SubhaloMassType`, `SubhaloLenType`, `SubhaloMassIn{Rad,HalfRad,MaxRad}Type`, `SubhaloSFR`, `SubhaloSFRin{Rad,HalfRad,MaxRad}`, gas and stellar metallicity in the five weightings, `SubhaloMass`, `Group_M_Crit200`, `GroupFirstSub`); the same 47 subhalo arrays as the other three codes; stellar half-mass aperture median -0.301 to -0.306 dex in CV_0 at z = 0, as the definition requires | **usable** |
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

Two cautions from the CAMELS documentation that apply here. (1) The home and Subfind pages say that a bug in the generation of the Subfind catalogues affected all Swift-EAGLE sets (1P, CV, LH), that "all the data in the public FOF/Subfind directories is now fixed" and that the old data are available on request. The `groups_*.hdf5` files read here are dated 2025-06-17 in the directory listing; whether that is after the fix is not stated, so the fix is taken from the documentation and not tested here. (2) The same warning lists SIMBA CV and 1P sets, which the existing three-code measurement reads from `Sims/SIMBA/CV/` (files dated 2023-05-03) and not from `FOF_Subfind/SIMBA/CV/` (directory dated 2025-07-27). See the note in `docs/CONVERSIONS.md` for what was checked about that.
