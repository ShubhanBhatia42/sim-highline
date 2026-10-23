# Staged records

Records that were extracted and checked but are **not** in the dataset (`data/curves/`), with the reason. Nothing here is read by the Explorer, the exports, the Python loader or the analyses. Each file is the complete output of the script named in `data/staged/*.json`'s own records (`provenance`), so it can be regenerated.

| file | records | why not in the dataset | what would change that |
|---|---|---|---|
| `m2-donnari19-sfms-contour-bands.json` | 75 (relation `sfms`) | Density contours of the TNG star-forming main sequence (Donnari+19) stored as vertical-envelope bands: a band fills any concavity of the contour (12 of the 85 loops have many gaps), and 75 extra curves would crowd the main-sequence plot. The exact polygons are in `polygons_donnari19.json`. | A polygon or contour representation in the schema and a view that draws it. |
| `nelson18-tng-colour-all.json` | 19 (relation `colour`) | 10 of them are the same kind of contour band (Nelson+18 g-r against mass). The 9 distribution records are in the dataset (promoted, see `promoted.json`). | As above. |
| `trayford15-eagle-colour-all.json` | 23 (relation `colour`) | 20 are one-mass-bin histograms of the EAGLE colour distribution under four dust models; as separate records they would add 20 panels to the Distribution view. The 3 records with galaxy counts are in the dataset. | Merging the mass bins of one run and dust model into one record (empty bins between them). |
| `braspenning24-flamingo-lxm.json` | 12 (relation `lxm`) | FLAMINGO X-ray luminosity against mass (Braspenning+24), digitized. Only partly verified: the paper does not define the halo-mass pivot of its fit, an inferred pivot reproduces the paper's slope to 0.04 and the normalisation to 0.03 dex but not exactly, and y is scaled by E(z)^-2. The dataset's rule is two checks against numbers the paper prints. | A pivot stated by the authors, or their table. |
| `dave19-simba-ssfr-hist.json`, `polygons_*.json` | | The Dave+19 record is in the dataset. The polygon files are reference only (they fail the validator's rule that x increases along a curve). | |
