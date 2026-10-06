const planck15={H0:67.74,Om:0.3089};
const wmap7={H0:70.4,Om:0.272};
const concordance={H0:70,Om:0.3};

const thesanBase={massDefinition:"aperture-30pkpc",imf:"chabrier03",imfBasis:"TNG model paper",cosmology:planck15,population:"all"};
const magneticumBase={massDefinition:"unspecified",imf:"chabrier03",imfBasis:"model paper; not stated in table header",cosmology:wmap7,population:"all"};

export const DEFINITIONS={
  "THESAN-1":{
    gsmf:{...thesanBase,densityFrame:"comoving"},
    sfms:{...thesanBase,sfrTimescaleMyr:"unspecified",sfrStatistic:"median"},
    mzr:{...thesanBase,metallicityQuantity:"gas-metal-mass-fraction",metallicityCalibration:"intrinsic-simulation"},
    shmr:{...thesanBase,haloMassDefinition:"unspecified"}
  },
  "Magneticum Pathfinder":{
    gsmf:{...magneticumBase,densityFrame:"comoving"},
    sfms:{...magneticumBase,sfrTimescaleMyr:"unspecified",sfrStatistic:"unspecified"},
    bh:{...magneticumBase,bhMassMethod:"intrinsic"},
    bhsigma:{...magneticumBase,sigmaDefinition:"unspecified",bhMassMethod:"intrinsic"},
    jstar:{...magneticumBase,jDefinition:"unspecified"},
    size:{...magneticumBase,sizeDefinition:"stellar-half-mass"},
    shmr:{...magneticumBase,massDefinition:"aperture-0.1rvir",haloMassDefinition:"M200crit",haloMassHistory:"current"},
    zstar:{...magneticumBase,metallicityQuantity:"stellar-Z",metallicityCalibration:"intrinsic (Zsun=0.0142); weighting not stated"}
  },
  "COSMOS-Web 2025":{
    gsmf:{massDefinition:"sed-total",imf:"chabrier03",cosmology:concordance,densityFrame:"comoving",population:"all"}
  },
  "Speagle et al. 2014":{
    sfms:{massDefinition:"sed-total",imf:"kroupa01",cosmology:concordance,population:"star-forming",sfrTimescaleMyr:"heterogeneous",sfrStatistic:"unspecified"}
  },
  "Popesso et al. 2023":{
    sfms:{massDefinition:"sed-total",imf:"kroupa01",cosmology:concordance,population:"star-forming",sfrTimescaleMyr:"heterogeneous",sfrStatistic:"mean"}
  },
  "Baldry et al. 2012 (GAMA)":{
    gsmf:{massDefinition:"sed-total",imf:"chabrier03",cosmology:concordance,densityFrame:"comoving",population:"all"}
  },
  "van der Wel et al. 2014":{
    "size-late":{massDefinition:"sed-total",imf:"chabrier03",cosmology:{H0:71,Om:0.27},sizeDefinition:"optical-half-light-major-axis",population:"star-forming"},
    "size-early":{massDefinition:"sed-total",imf:"chabrier03",cosmology:{H0:71,Om:0.27},sizeDefinition:"optical-half-light-major-axis",population:"quiescent"},
    "size-all":{massDefinition:"sed-total",imf:"chabrier03",cosmology:{H0:71,Om:0.27},sizeDefinition:"optical-half-light-major-axis",population:"all"}
  },
  "Reines & Volonteri 2015":{
    bh:{massDefinition:"sed-total",imf:"unspecified",bhMassMethod:"single-epoch-virial",population:"broad-line-agn-hosts"}
  },
  "Curti et al. 2020":{
    mzr:{massDefinition:"sed-total",imf:"unspecified",metallicityQuantity:"gas-O/H",metallicityCalibration:"Te-anchored-strong-line (Curti+17)",population:"star-forming"}
  },
  "SPARC / Lelli et al. 2019":{
    btfr:{massDefinition:"stars-plus-atomic-gas",velocityDefinition:"vflat"}
  },
  "Kormendy & Ho 2013":{
    bhsigma:{sigmaDefinition:"sigma-e",bhMassMethod:"dynamical",population:"classical-bulges-and-ellipticals"}
  },
  "Stott et al. 2013":{
    size:{sizeDefinition:"optical-half-light",population:"halpha-star-forming",imf:"unspecified",massDefinition:"sed-total"}
  },
  "NIHAO zoom suite":{
    gas:{gasDefinition:"HI+H2",population:"isolated-centrals",imf:"chabrier03"}
  },
  "Bradford et al. 2015":{
    gas:{gasDefinition:"HI+H2",population:"isolated",imf:"chabrier03"}
  }
};

export function definitionsFor(source,relation){
  const d=DEFINITIONS[source]?.[relation];
  if(!d)throw new Error(`No structured definitions for ${source} / ${relation}`);
  return d;
}
