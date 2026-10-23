(function(root){
const UNSET=new Set([undefined,null,"unspecified","heterogeneous"]);
const RULES={
  gsmf:{hard:["densityFrame"],soft:["imf","massDefinition","cosmology"]},
  sfms:{hard:["population"],soft:["imf","massDefinition","sfrTimescaleMyr","sfrStatistic","cosmology"]},
  ssfr:{hard:["population"],soft:["imf","massDefinition","sfrTimescaleMyr","sfrStatistic","cosmology"]},
  quenched:{hard:["quenchingCriterion"],soft:["imf","massDefinition"]},
  size:{hard:["sizeDefinition","population"],soft:["imf","massDefinition"]},
  mzr:{hard:["metallicityQuantity"],soft:["metallicityCalibration","population","imf","massDefinition"]},
  shmr:{hard:["haloMassDefinition"],soft:["haloMassHistory","population","imf","massDefinition"]},
  gas:{hard:["gasDefinition"],soft:["population","imf"]},
  "hi-fraction":{hard:["gasDefinition"],soft:["gasStatistic","gasMethod","population","imf","massDefinition"]},
  "h2-fraction":{hard:["gasDefinition"],soft:["gasStatistic","gasMethod","population","imf","massDefinition"]},
  jstar:{hard:["jDefinition"],soft:["massDefinition","imf"]},
  btfr:{hard:["velocityDefinition"],soft:["massDefinition"]},
  smd:{hard:["densityFrame"],soft:["massDefinition","imf","cosmology"]},
  bhmd:{hard:["densityFrame"],soft:["bhMassMethod","cosmology"]},
  zstar:{hard:["metallicityQuantity"],soft:["metallicityCalibration","imf","massDefinition","population"]},
  age:{hard:[],soft:["ageWeighting","imf","massDefinition","population"]},
  himf:{hard:["gasDefinition","densityFrame"],soft:["gasMethod"]},
  uvlf:{hard:["uvBand","densityFrame"],soft:["dustCorrection","cosmology"]},
  sfrd:{hard:["densityFrame"],soft:["imf","sfrIndicator","sfrIntegrationLimit","dustCorrection","cosmology"]},
  smd:{hard:["densityFrame"],soft:["imf","massDefinition","cosmology"]},
  sfrf:{hard:["densityFrame"],soft:["sfrIndicator","imf","sfrTimescaleMyr"]},
  fgas500:{hard:["apertureDefinition","fgasNormalisation"],soft:["massMethod","population"]},
  metald:{hard:["densityFrame","metalPhase"],soft:[]},
  dmf:{hard:["densityFrame"],soft:["dustMethod"]},
  dtg:{hard:["gasDefinition"],soft:[]},
  stfr:{hard:["velocityDefinition"],soft:["imf"]},
  hmf:{hard:["haloMassDefinition","densityFrame"],soft:[]},
  bh:{hard:[],soft:["bhMassMethod","massDefinition","imf","population"]},
  bhsigma:{hard:["sigmaDefinition"],soft:["bhMassMethod","population"]},
  fmr:{hard:["muAlpha","metallicityQuantity"],soft:["metallicityCalibration","sfrIndicator","sfrTimescaleMyr","imf","massDefinition","population"]},
  ks:{hard:["gasDefinition","areaScale"],soft:["sfrIndicator","coConversion","heliumIncluded","imf","population"]},
  wp:{hard:["sampleSelection","lengthUnit"],soft:["piMax","cosmology"]},
  hod:{hard:["galaxyType","haloMassDefinition"],soft:["sampleSelection"]},
  colour:{hard:["colourBand","dustTreatment"],soft:["population","massDefinition","imf"]},
  sigmam:{hard:["sigmaDimension"],soft:["sigmaDefinition","sigmaWeighting","massDefinition","imf","population","cosmology"]},
  sigma1:{hard:["sigma1Definition"],soft:["massDefinition","imf","population","cosmology"]},
  lxm:{hard:["xrayBand","coreTreatment","haloMassDefinition"],soft:[]},
  ysz:{hard:["haloMassDefinition","szScaling"],soft:[]},
  agnlf:{hard:["luminosityBand","lfConvention","densityFrame"],soft:["bolometricCorrection","obscurationCorrection","population","cosmology"]},
  bhad:{hard:["densityFrame","bhadDefinition"],soft:["luminosityBand","radiativeEfficiency","obscurationCorrection","cosmology"]},
  lambdar:{hard:["lambdaStatistic","projection"],soft:["spinDefinition","massDefinition","imf","population"]},
  fslow:{hard:["slowRotatorCriterion"],soft:["spinDefinition","projection","massDefinition","imf","population"]},
  elf:{hard:["line","dustCorrection"],soft:["densityFrame"]},
  uvbeta:{hard:["betaWindow","dustTreatment"],soft:[]}
};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const IMF_DEX={kroupa01:0,chabrier03:-0.04,salpeter55:0.1775};  /* data/imf-offsets.json documents where these come from; scripts/test-compare.mjs keeps the two equal */
function cosmologyNote(relation,a,b){
  const ra=Math.log10(a.H0/b.H0);
  if(relation==="gsmf")return `H0 ${a.H0} vs ${b.H0}: up to ${Math.abs(3*ra).toFixed(3)} dex in Phi and ${Math.abs(2*ra).toFixed(3)} dex in mass if not converted`;
  return `H0 ${a.H0} vs ${b.H0}: observational masses shift by up to ${Math.abs(2*ra).toFixed(3)} dex`;
}
function compatible(a,b){
  const relation=a.relation,rule=RULES[relation]||{hard:[],soft:[]},blockers=[],caveats=[];
  if(a.relation!==b.relation)return{verdict:"not-comparable",blockers:["different relations"],caveats};
  for(const r of [a,b])if(!r.rankable)blockers.push(`${r.source}: ${r.selection?.warning||"record marked context only"}`);
  const da=a.definitions||{},db=b.definitions||{};
  if(!a.definitions||!b.definitions)blockers.push("structured definitions missing");
  for(const key of rule.hard){
    if(UNSET.has(da[key])||UNSET.has(db[key]))blockers.push(`${key} not documented`);
    else if(!same(da[key],db[key]))blockers.push(`${key}: ${da[key]} vs ${db[key]}`);
  }
  for(const key of rule.soft){
    if(key==="imf"&&da.imf in IMF_DEX&&db.imf in IMF_DEX){if(da.imf!==db.imf)caveats.push(`imf: ${da.imf} vs ${db.imf}: ${Math.abs(IMF_DEX[da.imf]-IMF_DEX[db.imf]).toFixed(3)} dex in stellar mass if not converted`);continue}
    if(key==="cosmology"){if(da.cosmology&&db.cosmology&&!same(da.cosmology,db.cosmology))caveats.push(cosmologyNote(relation,da.cosmology,db.cosmology));continue}
    if(UNSET.has(da[key])||UNSET.has(db[key]))caveats.push(`${key} not documented for ${UNSET.has(da[key])?a.source:b.source}`);
    else if(!same(da[key],db[key]))caveats.push(`${key}: ${da[key]} vs ${db[key]}`);
  }
  const analytic=[a,b].some(r=>r.epoch?.mode==="analytic-evolution"),dz=Math.abs((a.epoch?.zRepresentative??0)-(b.epoch?.zRepresentative??0));
  if(!analytic&&dz>.5)caveats.push(`epoch: z=${a.epoch.zRepresentative} vs z=${b.epoch.zRepresentative} (bin ${b.epoch.zMin}-${b.epoch.zMax}); evolution within the bin is not modelled`);
  return{verdict:blockers.length?"not-comparable":caveats.length?"comparable-with-caveats":"comparable",blockers,caveats};
}
const sigmaOf=p=>p.sigmaKind!=="uncertainty"?NaN:Math.max(Number.isFinite(p.yHigh)?p.yHigh-p.y:0,Number.isFinite(p.yLow)?p.y-p.yLow:0)||NaN;
function interpolate(points,x,key="y"){
  for(let i=1;i<points.length;i++)if(x>=points[i-1].x&&x<=points[i].x){const a=points[i-1],b=points[i],t=b.x===a.x?0:(x-a.x)/(b.x-a.x),va=key==="sigma"?sigmaOf(a):a[key],vb=key==="sigma"?sigmaOf(b):b[key];return va+t*(vb-va)}
  return NaN;
}
const tag=(points,kind)=>points.map(p=>p.sigmaKind?p:{...p,sigmaKind:kind});
function residuals(simPoints,refPoints,simKind="unspecified",refKind="unspecified"){
  const sim=tag(simPoints,simKind),ref=tag(refPoints,refKind);
  if(ref.length<sim.length)return ref.map(p=>{const y=interpolate(sim,p.x);if(!Number.isFinite(y))return null;const ss=interpolate(sim,p.x,"sigma"),sr=sigmaOf(p),sigma=Math.hypot(Number.isFinite(sr)?sr:0,Number.isFinite(ss)?ss:0);return{x:p.x,d:y-p.y,sigma:Number.isFinite(sr)&&sigma>0?sigma:NaN,sigmaSource:Number.isFinite(ss)?"both":"reference-only"}}).filter(Boolean);
  return sim.map(p=>{const y=interpolate(ref,p.x);if(!Number.isFinite(y))return null;const sr=interpolate(ref,p.x,"sigma"),ss=sigmaOf(p),sigma=Math.hypot(Number.isFinite(sr)?sr:0,Number.isFinite(ss)?ss:0);return{x:p.x,d:p.y-y,sigma:Number.isFinite(sr)&&sigma>0?sigma:NaN,sigmaSource:Number.isFinite(ss)?"both":"reference-only"}}).filter(Boolean);
}
const MIN_BINS=3;
function summarize(res){
  if(res.length<MIN_BINS)return null;
  const ds=res.map(r=>r.d).sort((a,b)=>a-b),n=ds.length,median=n%2?ds[(n-1)/2]:(ds[n/2-1]+ds[n/2])/2,mean=ds.reduce((a,b)=>a+b,0)/n,rms=Math.sqrt(ds.reduce((a,b)=>a+b*b,0)/n);
  const weighted=res.filter(r=>Number.isFinite(r.sigma));
  const meanAbsSigma=weighted.length===n?weighted.reduce((a,r)=>a+Math.abs(r.d)/r.sigma,0)/n:NaN;
  return{n,median,mean,rms,meanAbsSigma,sigmaSource:weighted.every(r=>r.sigmaSource==="both")?"both":"reference-only"};
}
function cosmicAgeGyr(z,cosmo={H0:67.74,Om:0.3089}){
  const om=cosmo.Om,ol=1-om,hubbleTime=977.8/cosmo.H0;
  return 2*hubbleTime/(3*Math.sqrt(ol))*Math.asinh(Math.sqrt(ol/om)/(1+z)**1.5);
}
function evaluator(record){
  const rep=record.representation;if(rep.type!=="parametric"||!rep.expression)return null;
  const params=Object.fromEntries(Object.entries(rep.parameters||{}).filter(([,v])=>typeof v==="number"));
  // a page whose content security policy forbids eval ships the expressions precompiled (window.SIMHIGHLINE_EXPR, written by scripts/build-highline.mjs from the same records); everything else compiles the expression here
  const names=Object.keys(params),pre=root.SIMHIGHLINE_EXPR&&root.SIMHIGHLINE_EXPR[names.join(",")+"|"+rep.expression];
  const fn=pre||new Function(...names,"x","t","z","log10",`return ${rep.expression};`);
  return(x,z)=>fn(...Object.values(params),x,rep.ageCosmology?cosmicAgeGyr(z,rep.ageCosmology):NaN,z,Math.log10);
}

/* Per-galaxy distributions. A record may carry representation.distribution = {xEdges, yEdges, counts[i][j], thresholds?}; the quantiles, the fractions below each threshold, the fraction between the two thresholds (for sSFR: the green valley) and the position of the two peaks are computed from the counts, here and nowhere else (scripts/distribution_stats.py mirrors it and a fixture test keeps them equal). */
const DIST_LEVELS=[.05,.16,.5,.84,.95],DIST_MIN=10;
function distQuantile(row,edges,total,q){
  const target=q*total;let cum=0;
  for(let j=0;j<row.length;j++){const c=row[j];if(c>0&&cum+c>=target){const t=(target-cum)/c;return edges[j]+Math.min(1,Math.max(0,t))*(edges[j+1]-edges[j])}cum+=c}
  return edges[edges.length-1];
}
function distFractionBelow(row,edges,total,thr){
  let cum=0;
  for(let j=0;j<row.length;j++){
    if(edges[j+1]<=thr){cum+=row[j];continue}
    if(edges[j]<thr)cum+=row[j]*(thr-edges[j])/(edges[j+1]-edges[j]);
    break;
  }
  return cum/total;
}
function distributionStats(d,opt){
  const levels=(opt&&opt.levels)||DIST_LEVELS,minCount=(opt&&opt.minCount)||DIST_MIN,thr=(d.thresholds||[]).slice().sort((a,b)=>a-b),nx=d.xEdges.length-1,r6=v=>Math.round(v*1e6)/1e6;
  const out={levels,minCount,thresholds:thr,n:[],quantiles:levels.map(()=>[]),fracBelow:thr.map(()=>[]),between:[],bluePeak:[],redPeak:[]};
  for(let i=0;i<nx;i++){
    const row=d.counts[i],tot=row.reduce((a,b)=>a+b,0);out.n.push(tot);
    if(tot<minCount){levels.forEach((_,k)=>out.quantiles[k].push(null));thr.forEach((_,k)=>out.fracBelow[k].push(null));out.between.push(null);out.bluePeak.push(null);out.redPeak.push(null);continue}
    levels.forEach((q,k)=>out.quantiles[k].push(r6(distQuantile(row,d.yEdges,tot,q))));
    const fb=thr.map(t=>distFractionBelow(row,d.yEdges,tot,t));fb.forEach((v,k)=>out.fracBelow[k].push(r6(v)));
    out.between.push(thr.length>=2?r6(fb[fb.length-1]-fb[0]):null);
    const peak=(from,to)=>{let best=-1,bj=-1;for(let j=0;j<row.length;j++){if(d.yEdges[j]>=from&&d.yEdges[j+1]<=to&&row[j]>best){best=row[j];bj=j}}return bj<0||best<=0?null:r6((d.yEdges[bj]+d.yEdges[bj+1])/2)};
    out.bluePeak.push(thr.length>=2?peak(thr[thr.length-1],Infinity):null);out.redPeak.push(thr.length>=2?peak(-Infinity,thr[0]):null);
  }
  out.xCentres=Array.from({length:nx},(_,i)=>r6((d.xEdges[i]+d.xEdges[i+1])/2));
  return out;
}
/* The median curve with its 16 to 84 per cent band as ordinary points (what every other part of the project already understands). */
function distributionPoints(d,stats){
  const s=stats||distributionStats(d),k16=s.levels.indexOf(.16),k50=s.levels.indexOf(.5),k84=s.levels.indexOf(.84),pts=[];
  for(let i=0;i<s.n.length;i++)if(s.quantiles[k50][i]!==null)pts.push({x:s.xCentres[i],y:s.quantiles[k50][i],yLow:s.quantiles[k16][i],yHigh:s.quantiles[k84][i],count:s.n[i]});
  return pts;
}
const KEY_LABEL={imf:"Initial mass function (IMF)",massDefinition:"Which stars count toward the mass",haloMassDefinition:"Halo mass definition",population:"Which galaxies are included",sfrTimescaleMyr:"Star formation rate averaged over",sfrStatistic:"How the star formation rate is measured",quenchingCriterion:"What counts as quenched",sizeDefinition:"Size definition",metallicityQuantity:"What metallicity means",gasPhase:"Which gas",densityFrame:"Volume for densities",ageWeighting:"How the stellar age is averaged",apertureDefinition:"Region the quantity is measured within",areaScale:"Scale the surface densities are measured on",betaWindow:"Wavelength window of the UV slope",bhMassMethod:"How the black hole mass is obtained",bhadDefinition:"How the accretion-rate density is defined",bolometricCorrection:"Bolometric correction",coConversion:"CO-to-H2 conversion factor",colourBand:"Which colour (bands)",coreTreatment:"Cluster core included or removed",cosmology:"Cosmology (H0, matter density)",dustCorrection:"Dust correction of the luminosities",dustMethod:"How the dust mass is measured",dustTreatment:"Dust treatment of the colours",fgasNormalisation:"Baryon fraction the gas fraction is divided by",galaxyType:"Central, satellite or all galaxies",gasDefinition:"Which gas (phase and region)",gasMethod:"How the gas phase is computed or measured",gasStatistic:"Mean or median of the gas fraction",haloMassHistory:"Halo mass: current or peak",heliumIncluded:"Helium in the gas surface density",jDefinition:"How the specific angular momentum is defined",lambdaStatistic:"Statistic of the spin parameter",lengthUnit:"Length unit (with or without h)",lfConvention:"Luminosity function convention",line:"Emission line",luminosityBand:"Luminosity band",massMethod:"How the mass is obtained",metalPhase:"Metals in gas or in stars",metallicityCalibration:"Metallicity calibration (and solar value)",muAlpha:"Mixing parameter of the metallicity relation",obscurationCorrection:"Obscured AGN: corrected or not",piMax:"Line-of-sight integration limit",projection:"Projection (3D, 2D or redshift space)",radiativeEfficiency:"Radiative efficiency of accretion",sampleSelection:"How the sample is selected",sfrIndicator:"Star formation rate indicator",sfrIntegrationLimit:"Region the SFR density is summed over",sigma1Definition:"How the inner surface density is defined",sigmaDefinition:"How the velocity dispersion is defined",sigmaDimension:"Velocity dispersion: dimension and aperture",sigmaWeighting:"Velocity dispersion weighted by light or mass",slowRotatorCriterion:"Slow-rotator cut",spinDefinition:"How the spin parameter is defined",szScaling:"Redshift scaling of the Compton-Y relation",uvBand:"Rest-frame UV band",velocityDefinition:"Which velocity (circular, rotation, maximum)",xrayBand:"X-ray band"};
root.SimHighlineCompare={KEY_LABEL,distributionStats,distributionPoints,IMF_DEX,RULES,MIN_BINS,compatible,interpolate,residuals,summarize,cosmicAgeGyr,evaluator,sigmaOf};
})(typeof globalThis!=="undefined"?globalThis:window);
