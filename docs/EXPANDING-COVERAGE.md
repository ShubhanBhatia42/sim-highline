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

## Emission-line luminosity functions: what is in, what is not (2026-10-23)

Relation `elf`, H-alpha only so far. In: Sobral et al. 2013 (table, `scripts/ingest_elf_sobral13.py`), Covelo-Paz et al. 2025 (table, `scripts/ingest_elf_covelopaz25.py`), SPHINX20 (computed from the data release, `scripts/ingest_elf_sphinx20.py`). Two keys decide fairness: `line` (H-alpha alone, or blended with [NII]; [OIII] 5007 alone, or with the other doublet line and H-beta; [OII] doublet) and `dustCorrection` (`intrinsic`: no dust in a simulation, or an observation corrected for dust; `attenuated`: as observed or after dust in a simulation). How the correction was made goes in `dustCorrectionMethod` (a caveat, not a block), the region in `apertureDefinition`.

Read, with the sentence that fixes the definition, but not ingested:

- Hirschmann et al. 2023 (arXiv:2212.02522), IllustrisTNG: H-alpha, [OIII]+H-beta and [OII] functions for TNG50, TNG100 and TNG300 at z = 0.1 to 6 in a vector figure (`Ha_lumfct_IllustrisTNG_allz_Nov21.eps`). Dust: "we do not consider attenuation by dust outside H II regions" (intrinsic); aperture: "all `bound' gas cells and star particles". It would be a digitized (not rankable) record set, 27 curves for H-alpha. The HiZELS Schechter curves drawn in the same figure could calibrate the axes against `ingest_elf_sobral13.py`. Best next step.
- Khostovan et al. 2015 (1503.00004, [OII] and H-beta+[OIII], HiZELS) and Gunawardhana et al. 2013 (1305.5308, H-alpha, GAMA): the LaTeX sources hold tables; their line and dust definitions were not read.
- FLARES XI (2301.13038): [OIII] 5007 and [OIII]+H-beta functions in vector figures (`LF_OIII5007.pdf`, `LF_OIIIHb.pdf`); no [OIII] observation is ingested to compare them with, so they were left.

Seen only in search results or not opened: the two IllustrisTNG JWST-prediction papers (1904.07238, 2002.10474); JELS (2609.01586), COSMOS-3D (2510.11373), FRESCO [OIII] (2405.05111), Sun et al. 2023, Matthee et al. 2023, Colbert et al. 2013, Mehta et al. 2015, Comparat et al. 2016 (1605.02875). A paper on H-alpha functions of Illustris-1 (arXiv id 2608.30698 in the search result) could not be opened and its identifier was not verified.

No published H-alpha, [OIII] or [OII] luminosity function was found for EAGLE (only star formation rate functions), SIMBA (emission-line modelling reported, no function), THESAN (line-luminosity relations, no function found), Astrid, FIRE or COLIBRE. That is the result of web searches and of reading abstracts, not an exhaustive survey.

The SPHINX20 records are computed from the release rather than read from the paper's plot, because the plotted function (reddening-corrected along each sight line) has no stated reddening coefficient. The release's columns reproduce the plotted curves to 0.015 dex rms with k(H-alpha) = 2.2, a value fitted here, not taken from the paper; the records therefore hold the two versions that have a stated meaning (intrinsic, and dust attenuated along ten sight lines).

