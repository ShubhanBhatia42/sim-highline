# Drafts for the maintainers of the comparison-data compilation

**Nothing here has been sent.** These are drafts of issues for [calvin-sykes/velociraptor-comparison-data](https://github.com/calvin-sykes/velociraptor-comparison-data) (commit `fc740f4`, the one this dataset ingests), written so that someone who has not seen sim-highline can reproduce each point from the compilation's own files and the cited paper. Our own corrections are in `data/compilation-corrections.json`; the full table is in [COMPILATION-CHECK.md](COMPILATION-CHECK.md). The checks were made by one reader; none of these points has been confirmed by the compilation's maintainers or by the papers' authors.

The compilation is a useful public resource and most of its conversions are right (24 of 50 records checked agree with the paper). The points below are the ones where we think a number or a label is wrong.

## 1. Grazian et al. 2015: h_70 units treated as h-free

`GalaxyStellarMassFunction/conversion/convertGrazian2015.py` comments `# ORIGINAL_H = 0.7 ... not required, since data file is already in h-free units`, then computes `M = Mstar * h ** -2` and `Phi = 10 ** logPhi * h ** 3` with `h = cosmology.h` (0.6774). The raw file header says `Salpeter IMF, h=0.7` and the column is `Mstar/h**-2`; the paper labels its axes `M_star/h_70^-2` and `h_70^3 Mpc^-3` and adopts H0 = 70 (arXiv:1412.0532, grazian.tex:438-440). The data are therefore in h_70 units, as in the Duncan 2014, Muzzin 2013, Ilbert 2013, Tomczak 2014, Deshmukh 2018 and Gonzalez 2011 scripts, which use `(h / ORIGINAL_H) ** -2` and `** 3`. The stored curves are 0.310 dex too high in mass and 0.465 dex too low in number density (all four redshift bins).

## 2. Gonzalez et al. 2011: no Salpeter-to-Chabrier conversion

The raw file says `for Salpeter IMF` and the paper adopts a Salpeter IMF (arXiv:1008.3901, msAstroph.tex:216-218). `convertGonzalez2011.py` (line 134) says `Assuming Chabrier IMF (converted from Salpeter)` but lines 85-86 apply only the h conversion. Stored masses are 0.2175 dex (log10 of 1/0.606) too high for a Chabrier IMF.

## 3. Avila-Reese et al. 2008: unsupported mass transform on a digitized fit

`TullyFisherRelation/conversion/convertAvilaReese2008.py` applies `# IMF correction (Avila-Reese, private communication)`, `stellar_masses = 1e10 * 10.0 ** (((log10_stellar_masses - 10.0) - 0.130) / 0.922)`, to a fit that the same file says was `obtained directly from paper using webplotdigitizer`. The paper states no IMF. The map moves the masses by 0.16 to 0.41 dex depending on mass. The y quantity is the observed disk Vm, not a halo Vmax.

## 4. Zwaan et al. 2003: h_75 units not converted

The paper uses H0 = 75 and units of h_75 (paper.tex:233, :300). The script defines h = 0.7 but does not use it; the Schechter parameters are stored as printed, so the curve is 0.088 dex too low in mass and 0.133 dex too high in number density against the Planck15 convention of the rest of the compilation.

## 5. Scripts that call the data "h-free" when the paper states H0 = 70

Andrews & Martini 2013, Reyes et al. 2011, Chang et al. 2015, Bauer et al. 2013 (both curves), Moustakas et al. 2013, Haynes et al. 2011 and Muzzin et al. 2013 leave the stellar-mass (or mass-density) axis at H0 = 70 while the comments say the data are h-free or the warning says "h-corrected for SWIFT using Planck15". The effect is 0.0285 dex in mass (0.0142 dex in the Muzzin density). In Muzzin 2013 the lower error bars are also not converted from Kroupa to Chabrier (0.04 dex too high), which drops 3 of 7 intervals.

## 6. Provenance of three curves

- Gilbank et al. 2010: the cited paper (the SFR density of SDSS Stripe 82) contains no passive fraction against stellar mass; where the 13 values come from is not stated.
- Davies et al. 2016: the raw file says `Extracted by hand from the top-left panel of Figure 13`; the dataset marks it as a table.
- Lange et al. 2015: the sizes are binned medians of a per-galaxy file that is not in the paper.

## 7. Metadata that points to a different paper

Twelve records carry an `upstreamCitation` that names a different paper from the one in the title (for example Gruppioni et al. 2013 points to van der Burg et al. 2010; Smit et al. 2012 and Chang et al. 2015 point to bibcodes of other papers; xGASS is cited as "in prep"). The list is in [COMPILATION-CHECK.md](COMPILATION-CHECK.md) (section "Records whose own citation names another paper"); we could not settle the primary source of these from the metadata.

## What we are not claiming

That any of the compilation's other curves is wrong. We checked 50 records; the other records have not been looked at.
