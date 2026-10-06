import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import h5py
import numpy as np

root = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/vcd_calvin-sykes")
commit = sys.argv[2] if len(sys.argv) > 2 else "fc740f4d0856efd711f03242d40c03caea969a20"
output = Path(__file__).resolve().parent.parent / "data" / "curves" / "comparison-data.json"
repo_url = "https://github.com/calvin-sykes/velociraptor-comparison-data"
planck15 = {"H0": 67.74, "Om": 0.3075}
concordance = {"H0": 70, "Om": 0.3}
retrieved = date.today().isoformat()

GSMF = dict(relation="gsmf", x="log10 stellar mass", xu="log10(Msun)", y="log10 galaxy number density per dex", yu="log10(Mpc^-3 dex^-1)", ylog=True)
SHMR = dict(relation="shmr", x="log10 halo mass", xu="log10(Msun)", y="log10 stellar-to-halo mass ratio", yu="dex", ylog=True)
MZR = dict(relation="mzr", x="log10 stellar mass", xu="log10(Msun)", y="gas-phase 12+log(O/H)", yu="dex", ylog=False)
SIZE = dict(relation="size", x="log10 stellar mass", xu="log10(Msun)", y="log10 effective radius", yu="log10(kpc)", ylog=True)
SSFR = dict(relation="ssfr", x="log10 stellar mass", xu="log10(Msun)", y="log10 specific star-formation rate", yu="log10(yr^-1)", ylog=True)
SFMS = dict(relation="sfms", x="log10 stellar mass", xu="log10(Msun)", y="log10 star-formation rate", yu="log10(Msun/yr)", ylog=True)
FQ = dict(relation="quenched", x="log10 stellar mass", xu="log10(Msun)", y="quenched (passive) fraction", yu="fraction", ylog=False)
BH = dict(relation="bh", x="log10 stellar mass", xu="log10(Msun)", y="log10 black-hole mass", yu="log10(Msun)", ylog=True)
BHS = dict(relation="bhsigma", x="log10 stellar velocity dispersion", xu="log10(km/s)", y="log10 black-hole mass", yu="log10(Msun)", ylog=True)
H2 = dict(relation="h2-fraction", x="log10 stellar mass", xu="log10(Msun)", y="log10 mean H2-to-stellar mass fraction", yu="dex", ylog=True)
SMD = dict(relation="smd", x="redshift", xu="redshift", y="log10 cosmic stellar mass density", yu="log10(Msun cMpc^-3)", ylog=True, xform="scale_factor_to_z")
BHMD = dict(relation="bhmd", x="redshift", xu="redshift", y="log10 cosmic black-hole mass density", yu="log10(Msun cMpc^-3)", ylog=True, xform="scale_factor_to_z")
ZSTAR = dict(relation="zstar", x="log10 stellar mass", xu="log10(Msun)", y="log10 stellar metallicity (Z/Zsun)", yu="dex", ylog=True)
AGE = dict(relation="age", x="log10 stellar mass", xu="log10(Msun)", y="log10 stellar age", yu="log10(yr)", ylog=True)
HIMF = dict(relation="himf", x="log10 HI mass", xu="log10(Msun)", y="log10 HI mass function per dex", yu="log10(Mpc^-3 dex^-1)", ylog=True)
SFRF = dict(relation="sfrf", x="log10 star-formation rate", xu="log10(Msun/yr)", y="log10 SFR function per dex", yu="log10(Mpc^-3 dex^-1)", ylog=True)
FGAS = dict(relation="fgas500", x="log10 halo mass M500crit", xu="log10(Msun)", y="log10 gas fraction within R500 normalised by the cosmic baryon fraction Omega_b/Omega_m (Planck15)", yu="dex", ylog=True)
ZDENS = dict(relation="metald", x="redshift", xu="redshift", y="log10 cosmic metal mass density", yu="log10(Msun cMpc^-3)", ylog=True, xform="scale_factor_to_z")
DMF = dict(relation="dmf", x="log10 dust mass", xu="log10(Msun)", y="log10 dust mass function per dex", yu="log10(Mpc^-3 dex^-1)", ylog=True)
DTG = dict(relation="dtg", x="gas-phase 12+log(O/H)", xu="dex", y="log10 dust-to-gas ratio", yu="dex", ylog=True, xform="identity")
STFR = dict(relation="stfr", x="log10 stellar mass", xu="log10(Msun)", y="log10 halo Vmax", yu="log10(km/s)", ylog=True)
HMF = dict(relation="hmf", x="log10 halo mass", xu="log10(Msun)", y="log10 halo mass function per dex", yu="log10(Mpc^-3 dex^-1)", ylog=True)
HI = dict(relation="hi-fraction", x="log10 stellar mass", xu="log10(Msun)", y="log10 mean HI-to-stellar mass fraction", yu="dex", ylog=True)

obs_gsmf = lambda **kw: {"massDefinition": "sed-total", "imf": "chabrier03", "densityFrame": "comoving", "population": "all", "cosmology": planck15, **kw}

DATASETS = [
    ("GalaxyStellarMassFunction/LiWhite2009", "Li & White 2009", None, "observation", GSMF, obs_gsmf(), "uncertainty", (0.0, 0.2)),
    ("GalaxyStellarMassFunction/Wright2017", "Wright et al. 2017 (GAMA-II)", None, "observation", GSMF, obs_gsmf(), "uncertainty", (0.0, 0.1)),
    ("GalaxyStellarMassFunction/DSouza2015", "D'Souza et al. 2015", None, "observation", GSMF, obs_gsmf(), "unspecified", (0.0, 0.2)),
    *[(f"GalaxyStellarMassFunction/Ilbert2013_z{z}", "Ilbert et al. 2013", None, "observation", GSMF, obs_gsmf(), "uncertainty", edges)
      for z, edges in [("000p200", (0.2, 0.5)), ("000p500", (0.5, 0.8)), ("000p800", (0.8, 1.1)), ("001p100", (1.1, 1.5)), ("001p500", (1.5, 2.0)), ("002p000", (2.0, 2.5)), ("002p500", (2.5, 3.0)), ("003p000", (3.0, 4.0))]],
    ("GalaxyStellarMassFunction/Tomczak2013", "Tomczak et al. 2014", None, "observation", GSMF, obs_gsmf(), "uncertainty",
     {"z000.625": (0.5, 0.75), "z000.875": (0.75, 1.0), "z001.125": (1.0, 1.25), "z001.375": (1.25, 1.5), "z001.750": (1.5, 2.0), "z002.250": (2.0, 2.5), "z002.750": (2.5, 3.0)}),
    *[(f"GalaxyStellarMassFunction/Deshmukh2018_z{z}", "Deshmukh et al. 2018", None, "observation", GSMF, obs_gsmf(), "uncertainty", None)
      for z in ["002p000", "002p500", "003p000", "004p000", "005p000"]],
    ("GalaxyStellarMassFunction/Duncan2014", "Duncan et al. 2014", None, "observation", GSMF, obs_gsmf(), "uncertainty", None),
    ("GalaxyStellarMassFunction/Grazian2015", "Grazian et al. 2015", None, "observation", GSMF, obs_gsmf(), "uncertainty", None),
    ("GalaxyStellarMassFunction/Gonzalez2011", "Gonzalez et al. 2011", None, "observation", GSMF, obs_gsmf(), "uncertainty", None),
    ("GalaxyStellarMassStarFormationRate/Davies2016_z0p1", "Davies et al. 2016 (GAMA)", None, "observation", SFMS,
     {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": concordance, "population": "unspecified", "sfrTimescaleMyr": "unspecified", "sfrStatistic": "unspecified"}, "unspecified", (0.0, 0.1)),
    ("GalaxyStellarMassSpecificStarFormationRate/Bauer2013_AllGalaxies", "Bauer et al. 2013 (GAMA)", "all galaxies", "observation", SSFR,
     {"massDefinition": "sed-total", "imf": "chabrier03", "population": "all", "sfrTimescaleMyr": "unspecified", "sfrStatistic": "unspecified"}, "unspecified", (0.05, 0.32)),
    ("GalaxyStellarMassSpecificStarFormationRate/Bauer2013_StarForming", "Bauer et al. 2013 (GAMA)", "star-forming", "observation", SSFR,
     {"massDefinition": "sed-total", "imf": "chabrier03", "population": "star-forming", "sfrTimescaleMyr": "unspecified", "sfrStatistic": "unspecified"}, "unspecified", (0.05, 0.32)),
    ("GalaxyStellarMassSpecificStarFormationRate/Chang2015", "Chang et al. 2015 (SDSS)", None, "observation", SSFR,
     {"massDefinition": "sed-total", "imf": "chabrier03", "population": "unspecified", "sfrTimescaleMyr": "unspecified", "sfrStatistic": "unspecified"}, "unspecified", (0.01, 0.2)),
    ("GalaxyStellarMassGalaxySize/Lange2015rBand", "Lange et al. 2015 (GAMA)", "r band", "observation", SIZE,
     {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": concordance, "sizeDefinition": "optical-half-light-r-band", "population": "all"}, "unspecified", (0.0, 0.1)),
    ("GalaxyStellarMassGalaxySize/Lange2015HBand", "Lange et al. 2015 (GAMA)", "H band", "observation", SIZE,
     {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": concordance, "sizeDefinition": "nir-half-light-H-band", "population": "all"}, "unspecified", (0.0, 0.1)),
    ("GalaxyStellarMassGalaxySize/Mosleh2020_SF", "Mosleh et al. 2020", "star-forming", "observation", SIZE,
     {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": concordance, "sizeDefinition": "unspecified", "population": "star-forming"}, "unspecified", None),
    ("GalaxyStellarMassGalaxySize/Mosleh2020_Q", "Mosleh et al. 2020", "quiescent", "observation", SIZE,
     {"massDefinition": "sed-total", "imf": "chabrier03", "cosmology": concordance, "sizeDefinition": "unspecified", "population": "quiescent"}, "unspecified", None),
    ("GalaxyStellarMassGalaxySize/Crain2015_REF25_z0p1", "EAGLE", "Ref-L025N0376", "simulation", SIZE,
     {"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "sizeDefinition": "stellar-half-mass-3d-30pkpc", "population": "unspecified"}, "scatter", None),
    ("GalaxyStellarMassHaloMass/Behroozi2013Ratio", "Behroozi et al. 2013", "M200crit", "empirical-model", SHMR,
     {"imf": "chabrier03", "haloMassDefinition": "M200crit", "haloMassHistory": "current", "population": "centrals"}, "unspecified", (0.0, 0.0)),
    ("GalaxyStellarMassHaloMass/Moster2013Ratio", "Moster et al. 2013", "M200crit", "empirical-model", SHMR,
     {"imf": "chabrier03", "haloMassDefinition": "M200crit", "haloMassHistory": "current", "population": "centrals"}, "unspecified", (0.0, 0.0)),
    ("GalaxyStellarMassHaloMass/Behroozi2019Ratio", "Behroozi et al. 2019 (UniverseMachine)", "BN98 peak", "empirical-model", SHMR,
     {"imf": "chabrier03", "haloMassDefinition": "BN98", "haloMassHistory": "peak", "population": "centrals"}, "unspecified", None),
    ("GalaxyStellarMassHaloMass/Read2017_Ratio", "Read et al. 2017", None, "observation", SHMR,
     {"imf": "unspecified", "haloMassDefinition": "M200crit", "haloMassHistory": "current", "population": "isolated-dwarfs"}, "uncertainty", (0.0, 0.0)),
    ("GalaxyStellarMassHaloMass/Schaye2015_Ref_100_M200_Ratio", "EAGLE", "Ref-L100N1504 M200crit", "simulation", SHMR,
     {"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "haloMassDefinition": "M200crit", "haloMassHistory": "current", "population": "centrals"}, "scatter", None),
    ("GalaxyStellarMassHaloMass/Schaye2015_Ref_100_MBN98_Ratio", "EAGLE", "Ref-L100N1504 BN98", "simulation", SHMR,
     {"massDefinition": "aperture-30pkpc", "imf": "chabrier03", "haloMassDefinition": "BN98", "haloMassHistory": "current", "population": "centrals"}, "scatter", None),
    ("GalaxyStellarMassPassiveFraction/Behroozi2019", "Behroozi et al. 2019 (UniverseMachine)", "all", "empirical-model", FQ,
     {"imf": "chabrier03", "quenchingCriterion": "ssfr<1e-11", "population": "all"}, "unspecified", None),
    ("GalaxyStellarMassPassiveFraction/Behroozi2019_centrals", "Behroozi et al. 2019 (UniverseMachine)", "centrals", "empirical-model", FQ,
     {"imf": "chabrier03", "quenchingCriterion": "ssfr<1e-11", "population": "centrals"}, "unspecified", None),
    ("GalaxyStellarMassPassiveFraction/Gilbank2010", "Gilbank et al. 2010 (SDSS)", None, "observation", FQ,
     {"imf": "kroupa01", "quenchingCriterion": "unspecified", "population": "all"}, "unspecified", (0.01, 0.2)),
    ("GalaxyStellarMassPassiveFraction/Moustakas2013", "Moustakas et al. 2013 (SDSS)", None, "observation", FQ,
     {"imf": "chabrier03", "quenchingCriterion": "unspecified", "population": "all"}, "unspecified", (0.01, 0.2)),
    ("GalaxyStellarMassBlackHoleMass/McConnell2013_Data", "McConnell & Ma 2013", "galaxies", "observation", BH,
     {"massDefinition": "bulge-as-total", "imf": "unspecified", "bhMassMethod": "dynamical", "population": "dynamical-bh-hosts"}, "uncertainty", (0.0, 0.05)),
    ("GalaxyStellarMassBlackHoleMass/Sahu2019_ETG", "Sahu et al. 2019", "early-type", "observation", BH,
     {"massDefinition": "bulge-as-total", "imf": "unspecified", "bhMassMethod": "dynamical", "population": "early-type"}, "uncertainty", (0.0, 0.05)),
    ("StellarVelocityDispersionBlackHoleMass/Sahu2019", "Sahu et al. 2019", "M-sigma fit", "observation", BHS,
     {"sigmaDefinition": "sigma-fixed-0.6kpc-aperture", "bhMassMethod": "dynamical", "population": "all"}, "unspecified", (0.0, 0.05)),
    ("GalaxyStellarMassGasMetallicity/Tremonti2004_Data", "Tremonti et al. 2004 (SDSS)", None, "observation", MZR,
     {"massDefinition": "sed-total", "imf": "kroupa01", "metallicityQuantity": "gas-O/H", "metallicityCalibration": "CL01-Bayesian", "population": "star-forming"}, "scatter", (0.005, 0.25)),
    ("GalaxyStellarMassGasMetallicity/Andrews2013_Data", "Andrews & Martini 2013 (SDSS)", None, "observation", MZR,
     {"massDefinition": "sed-total", "imf": "chabrier03", "metallicityQuantity": "gas-O/H", "metallicityCalibration": "Te-stacked", "population": "star-forming"}, "unspecified", (0.027, 0.25)),
    ("GalaxyStellarMassGasMetallicity/Zahid2014_Data", "Zahid et al. 2014", None, "observation", MZR,
     {"massDefinition": "sed-total", "imf": "chabrier03", "metallicityQuantity": "gas-O/H", "metallicityCalibration": "KK04", "population": "star-forming"}, "unspecified", None),
    ("GalaxyStellarMassGasMetallicity/Chartab2021", "Chartab et al. 2021 (MOSDEF)", None, "observation", MZR,
     {"massDefinition": "sed-total", "imf": "chabrier03", "metallicityQuantity": "gas-O/H", "metallicityCalibration": "unspecified", "population": "star-forming"}, "unspecified", None),
    ("GalaxyH2Fractions/Saintonge2017_abcissa_M_star", "Saintonge et al. 2017 (xCOLD GASS)", None, "observation", H2,
     {"gasDefinition": "H2", "gasMethod": "CO with alpha_CO conversion", "gasStatistic": "mean-linear", "population": "all", "imf": "unspecified"}, "uncertainty", (0.01, 0.05)),
    ("GalaxyStellarMassFunction/Baldry2012", "Baldry et al. 2012 (GAMA)", "binned table", "observation", GSMF, obs_gsmf(), "uncertainty", (0.002, 0.06)),
    ("GalaxyStellarMassGalaxySize/xGASS", "xGASS (Catinella et al. 2018)", "sizes", "observation", SIZE,
     {"massDefinition": "sed-total", "imf": "chabrier03", "sizeDefinition": "unspecified", "population": "all"}, "unspecified", (0.01, 0.05)),
    ("GalaxyStellarMassGasMetallicity/Lee2006_Data", "Lee et al. 2006 (dwarfs)", None, "observation", MZR,
     {"massDefinition": "sed-total", "imf": "unspecified", "metallicityQuantity": "gas-O/H", "metallicityCalibration": "Te (direct)", "population": "star-forming dwarfs"}, "unspecified", (0.0, 0.01)),
    ("GalaxyStellarMassBlackHoleMass/McConnell2013_Fit", "McConnell & Ma 2013", "fit", "observation", BH,
     {"massDefinition": "bulge-as-total", "imf": "unspecified", "bhMassMethod": "dynamical", "population": "dynamical-bh-hosts"}, "unspecified", (0.0, 0.05)),
    ("GalaxyStellarMassBlackHoleMass/Sahu2019_LTG", "Sahu et al. 2019", "late-type", "observation", BH,
     {"massDefinition": "bulge-as-total", "imf": "unspecified", "bhMassMethod": "dynamical", "population": "late-type"}, "uncertainty", (0.0, 0.05)),
    *[(f"HaloMassGasFractions/{n}", src, None, "observation", FGAS, {"apertureDefinition": "R500crit", "fgasNormalisation": "Omega_b/Omega_m (Planck15)", "massMethod": method, "population": "groups and clusters"}, interval, (0.0, 0.3))
      for n, src, method, interval in [("Vikhlinin2006", "Vikhlinin et al. 2006 (Chandra)", "hydrostatic X-ray", "uncertainty"), ("Sun2009", "Sun et al. 2009 (Chandra groups)", "hydrostatic X-ray", "unspecified"),
                                       ("Lin2012", "Lin et al. 2012", "X-ray scaling", "unspecified"), ("Lovisari2015", "Lovisari et al. 2015 (XMM groups)", "hydrostatic X-ray", "unspecified"),
                                       ("Eckert2016", "Eckert et al. 2016 (XXL)", "weak-lensing-calibrated X-ray", "unspecified")]],
    ("MetalMassDensity/Schaye2015_gas", "EAGLE", "Ref-L100N1504 gas metals", "simulation", ZDENS, {"densityFrame": "comoving", "metalPhase": "gas"}, "unspecified", (0.0, 20.0)),
    ("MetalMassDensity/Schaye2015_stars", "EAGLE", "Ref-L100N1504 stellar metals", "simulation", ZDENS, {"densityFrame": "comoving", "metalPhase": "stars"}, "unspecified", (0.0, 20.0)),
    ("StellarMassDensity/Schaye2015_Ref12", "EAGLE", "Ref-L012N0188 all stars", "simulation", SMD, {"massDefinition": "all star particles", "imf": "chabrier03", "densityFrame": "comoving"}, "unspecified", (0.0, 20.0)),
    ("GalaxyDustMassFunction/Beeston2018_z000p000", "Beeston et al. 2018 (H-ATLAS/GAMA)", None, "observation", DMF, {"densityFrame": "comoving", "dustMethod": "FIR SED"}, "uncertainty", (0.0, 0.1)),
    ("GalaxyDustMassFunction/Pozzi2020_z000p100", "Pozzi et al. 2020", None, "observation", DMF, {"densityFrame": "comoving", "dustMethod": "FIR SED"}, "uncertainty", (0.0, 0.25)),
    ("GalaxyDustMassFunction/Pozzi2020_z001p800", "Pozzi et al. 2020", None, "observation", DMF, {"densityFrame": "comoving", "dustMethod": "FIR SED"}, "uncertainty", None),
    ("GalaxyMetallicityDusttoGasRatio/RemyRuyer2014_Data_COZ", "Remy-Ruyer et al. 2014", "X_CO(Z)", "observation", DTG, {"gasDefinition": "HI+H2 (X_CO metallicity-dependent)"}, "uncertainty", (0.0, 0.02)),
    ("GalaxyMetallicityDusttoGasRatio/RemyRuyer2014_Data_COMW", "Remy-Ruyer et al. 2014", "X_CO(MW)", "observation", DTG, {"gasDefinition": "HI+H2 (Milky Way X_CO)"}, "uncertainty", (0.0, 0.02)),
    ("TullyFisherRelation/Reyes2011", "Reyes et al. 2011", None, "observation", STFR, {"velocityDefinition": "halo Vmax (lensing-informed)", "imf": "chabrier03"}, "unspecified", (0.0, 0.1)),
    ("TullyFisherRelation/AvilaReese2008", "Avila-Reese et al. 2008", None, "observation", STFR, {"velocityDefinition": "halo Vmax (model-converted)", "imf": "chabrier03"}, "unspecified", (0.0, 0.05)),
    ("HaloMassFunction/Tinker2008", "Tinker et al. 2008 (colossus, Planck13)", "M200m", "empirical-model", HMF, {"haloMassDefinition": "unspecified", "densityFrame": "comoving"}, "unspecified", (0.0, 0.0)),
    ("HaloMassFunction/Bocquet2016", "Bocquet et al. 2016", None, "empirical-model", HMF, {"haloMassDefinition": "unspecified", "densityFrame": "comoving"}, "unspecified", (0.0, 0.0)),
    ("StellarMassDensity/Muzzin2013", "Muzzin et al. 2013 (UltraVISTA)", None, "observation", SMD, {"massDefinition": "galaxies above 1e8 Msun", "imf": "chabrier03", "densityFrame": "comoving", "cosmology": planck15}, "uncertainty", (0.0, 4.0)),
    ("StellarMassDensity/Wright2017", "Wright et al. 2017 (GAMA-II)", "density", "observation", SMD, {"massDefinition": "galaxies (SED)", "imf": "chabrier03", "densityFrame": "comoving", "cosmology": planck15}, "uncertainty", (0.0, 4.0)),
    ("StellarMassDensity/Schaye2015_Ref100", "EAGLE", "Ref-L100N1504 all stars", "simulation", SMD, {"massDefinition": "all star particles", "imf": "chabrier03", "densityFrame": "comoving"}, "unspecified", (0.0, 20.0)),
    ("BlackHoleMassHistory/Aird2015", "Aird et al. 2015 (X-ray)", None, "observation", BHMD, {"bhMassMethod": "X-ray luminosity function integration", "densityFrame": "comoving", "cosmology": planck15}, "unspecified", (0.0, 5.0)),
    ("GalaxyStellarMassStellarMetallicity/Gallazzi2005_Data", "Gallazzi et al. 2005 (SDSS)", None, "observation", ZSTAR, {"massDefinition": "sed-total", "imf": "chabrier03", "metallicityQuantity": "stellar-Z", "metallicityCalibration": "Lick indices (BC03)", "population": "all"}, "scatter", (0.005, 0.22)),
    ("GalaxyStellarMassStellarMetallicity/Kirby2013_Data", "Kirby et al. 2013 (Local Group dwarfs)", None, "observation", ZSTAR, {"massDefinition": "sed-total", "imf": "unspecified", "metallicityQuantity": "stellar-Z", "metallicityCalibration": "resolved-star [Fe/H]", "population": "dwarfs"}, "uncertainty", (0.0, 0.0)),
    ("GalaxyStellarMassStellarAges/Gallazzi2005_Data", "Gallazzi et al. 2005 (SDSS)", None, "observation", AGE, {"massDefinition": "sed-total", "imf": "chabrier03", "ageWeighting": "r-band light", "population": "all"}, "scatter", (0.005, 0.22)),
    ("GalaxyHIMassFunction/Haynes2011", "Haynes et al. 2011 (ALFALFA)", None, "observation", HIMF, {"gasDefinition": "HI", "gasMethod": "21cm", "densityFrame": "comoving"}, "unspecified", (0.0, 0.06)),
    ("GalaxyHIMassFunction/Zwaan2003", "Zwaan et al. 2003 (HIPASS)", None, "observation", HIMF, {"gasDefinition": "HI", "gasMethod": "21cm", "densityFrame": "comoving"}, "unspecified", (0.0, 0.04)),
    ("GalaxyHIFractions/Catinella2018_abcissa_M_star", "Catinella et al. 2018 (xGASS)", None, "observation", HI,
     {"gasDefinition": "HI", "gasMethod": "21cm", "gasStatistic": "mean-linear", "population": "all", "imf": "unspecified"}, "uncertainty", (0.01, 0.05)),
]

SFRF_NAMES = {"Alavi2016": "Alavi et al. 2016", "Bouwens2015": "Bouwens et al. 2015 (UV-derived)", "Gruppioni2013": "Gruppioni et al. 2013 (Herschel IR)", "Parsa2016": "Parsa et al. 2016",
              "Smit2012": "Smit et al. 2012 (UV-derived)", "Bell2007": "Bell et al. 2007"}
for _f in sorted((root / "data" / "GalaxyStarFormationRateFunction").glob("*.hdf5")):
    _key = _f.stem.split("_z")[0]
    DATASETS.append((f"GalaxyStarFormationRateFunction/{_f.stem}", SFRF_NAMES.get(_key, _key), None, "observation", SFRF,
                     {"imf": "chabrier03", "sfrIndicator": "dust-corrected UV" if _key in ("Bouwens2015", "Smit2012", "Alavi2016", "Parsa2016") else "IR", "densityFrame": "comoving"}, "uncertainty", None))


def slug(text):
    return "".join(ch if ch.isalnum() else "-" for ch in text.lower()).strip("-").replace("--", "-")

def groups(handle):
    if "metadata" in handle:
        yield None, dict(handle["metadata"].attrs), handle["x"]["values"][()], handle["y"]["values"][()], handle["y"]["scatter"][()] if "scatter" in handle["y"] else None
        return
    for prefix in handle["multi_file_metadata"].attrs["prefixes"]:
        prefix = str(prefix)
        scatter = handle["y"].get(f"{prefix}_scatter")
        yield prefix, dict(handle[f"{prefix}_metadata"].attrs), handle["x"][f"{prefix}_values"][()], handle["y"][f"{prefix}_values"][()], scatter[()] if scatter is not None else None

def build():
    records, problems = [], []
    for path, source, run, kind, rel, definitions, interval, edges in DATASETS:
        file = root / "data" / f"{path}.hdf5"
        if not file.exists():
            problems.append(f"missing {file}")
            continue
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        with h5py.File(file, "r") as handle:
            for prefix, meta, x, y, scatter in groups(handle):
                z = max(float(meta.get("redshift", 0.0)), 0.0)
                if isinstance(edges, dict):
                    z_min, z_max = edges[prefix]
                elif isinstance(edges, tuple):
                    z_min, z_max = edges
                else:
                    z_min = z_max = z
                z_min, z_max = min(z_min, z), max(z_max, z)
                sc = np.atleast_2d(np.asarray(scatter, dtype=float)) if scatter is not None else None
                if sc is not None and sc.shape[0] == 1:
                    sc = np.vstack([sc[0], sc[0]])
                if sc is not None and sc.shape[-1] != len(y):
                    sc = None
                lo = sc[0] if sc is not None else np.full(len(y), np.nan)
                hi = sc[1] if sc is not None else np.full(len(y), np.nan)
                points, dropped = [], 0
                xt = 1 / np.asarray(x, dtype=float) - 1 if rel.get("xform") == "scale_factor_to_z" else np.asarray(x, dtype=float) if rel.get("xform") == "identity" else np.log10(np.where(np.asarray(x) > 0, x, np.nan))
                for xv, yv, lv, hv in sorted(zip(xt, y, lo, hi)):
                    if not (np.isfinite(xv) and np.isfinite(yv)) or (rel["ylog"] and yv <= 0):
                        continue
                    point = {"x": round(float(xv), 6), "y": round(float(np.log10(yv) if rel["ylog"] else yv), 6)}
                    if np.isfinite(lv) and np.isfinite(hv) and (lv < 0 or hv < 0):
                        dropped += 1
                    elif np.isfinite(lv) and np.isfinite(hv) and (lv > 0 or hv > 0):
                        low, high = yv - lv, yv + hv
                        if rel["ylog"]:
                            if low > 0:
                                point["yLow"] = round(float(np.log10(low)), 6)
                            point["yHigh"] = round(float(np.log10(high)), 6)
                        else:
                            point["yLow"], point["yHigh"] = round(float(low), 6), round(float(high), 6)
                    if points and point["x"] <= points[-1]["x"]:
                        continue
                    points.append(point)
                if len(points) < 2:
                    problems.append(f"{path} {prefix}: fewer than two usable points")
                    continue
                comment = str(meta.get("comment", ""))
                if dropped:
                    comment += f" [sim-highline: {dropped} interval(s) not bracketing the central value were dropped rather than reordered.]"
                defs = dict(definitions)
                if "cosmology" not in defs and "h-corrected" in comment:
                    defs["cosmology"] = planck15
                bibcode = str(meta.get("bibcode", "")).strip()
                ztag = f"z{z:.3f}".rstrip("0").rstrip(".")
                records.append({
                    "id": f"vcd.{slug(source)}.{slug(run or 'main')}.{rel['relation']}.{ztag}",
                    "source": source, "run": run, "kind": kind, "relation": rel["relation"],
                    "epoch": {"zRepresentative": round(z, 4), "zMin": round(z_min, 4), "zMax": round(z_max, 4),
                              "mode": "observational-bin" if kind == "observation" else "published-epoch", "snapshot": None},
                    "axes": {"xDefinition": rel["x"], "xUnit": rel["xu"], "yDefinition": rel["y"], "yUnit": rel["yu"]},
                    "domain": {"xMin": points[0]["x"], "xMax": points[-1]["x"]},
                    "representation": {"type": "points", "intervalKind": interval, "connect": str(meta.get("plot_as")) == "line", "points": points},
                    "scatter": None,
                    "selection": {"population": defs.get("population", "unspecified"), "warning": comment},
                    "definitions": defs,
                    "provenance": {
                        "tier": "published-table", "citation": f"{meta.get('citation')} [{bibcode}]",
                        "doi": None, "url": f"https://ui.adsabs.harvard.edu/abs/{bibcode}" if bibcode and bibcode != "None available" else repo_url,
                        "retrieved": retrieved, "compilation": f"VELOCIraptor/SWIFT observational comparison data, {repo_url} @ {commit}",
                        "sourceMember": f"data/{path}.hdf5", "checksumSha256": digest,
                    },
                    "calibration": "unknown" if kind == "simulation" else "validation",
                    "rankable": True,
                    "notes": "Ingested from the converted VELOCIraptor comparison-data HDF5; unit and h conversions were applied by that compilation's per-dataset scripts as described in the warning text.",
                })
    for record in records:
        if record["source"] == "EAGLE":
            z = record["epoch"]["zRepresentative"]
            record["calibration"] = "target" if record["relation"] == "size" and z < 0.2 else "calibration-adjacent" if z < 0.2 else "prediction"
    return records, problems

records, problems = build()
output.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
print(f"Ingested {len(records)} comparison-data records" + (f"; {len(problems)} problems:\n" + "\n".join(problems) if problems else ""))
