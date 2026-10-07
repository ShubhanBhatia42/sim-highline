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
  bhsigma:{hard:["sigmaDefinition"],soft:["bhMassMethod","population"]}
};
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const IMF_DEX={kroupa01:0,chabrier03:-0.025,salpeter55:0.21};
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
  const fn=new Function(...Object.keys(params),"x","t","z","log10",`return ${rep.expression};`);
  return(x,z)=>fn(...Object.values(params),x,rep.ageCosmology?cosmicAgeGyr(z,rep.ageCosmology):NaN,z,Math.log10);
}
root.SimHighlineCompare={IMF_DEX,RULES,MIN_BINS,compatible,interpolate,residuals,summarize,cosmicAgeGyr,evaluator,sigmaOf};
})(typeof globalThis!=="undefined"?globalThis:window);
