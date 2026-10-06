(function(root){
const DEF_COLS=["imf","massDefinition","haloMassDefinition","population","sfrTimescaleMyr","sfrStatistic","quenchingCriterion","sizeDefinition","metallicityQuantity","gasPhase","densityFrame"];
const RECORD_COLS=["record_id","kind","source","run","relation","z","z_min","z_max","representation","interval_kind","connect","x_unit","y_unit","x_definition","y_definition","tier","rankable","calibration","population_note","mass_class","cosmology_h0","cosmology_om",...DEF_COLS.map(k=>k==="population"?"population":k.replace(/[A-Z]/g,c=>"_"+c.toLowerCase())),"citation","doi","url","checksum_sha256","retrieved","definitions_json"];
const POINT_COLS=["record_id","point_index","x","y","y_low","y_high","x_low","x_high","count"];
const NSAMPLE=40;
function massClass(d){
  const m=(d&&d.massDefinition)||"";
  if(!m||m==="unspecified"||m==="heterogeneous")return"unspecified";
  if(/^sed/.test(m))return"sed";
  if(/sfh/i.test(m))return"sfh-integral";
  if(/^aperture/.test(m)||/^sphere/.test(m))return"aperture";
  if(/total|caesar|subhalo/.test(m))return"total-subhalo";
  return"other";
}
function sampled(r,n=NSAMPLE,z){
  const ev=root.SimHighlineCompare&&root.SimHighlineCompare.evaluator(r);
  const {xMin,xMax}=r.domain||{};
  if(!ev||!Number.isFinite(xMin)||!Number.isFinite(xMax))return[];
  const out=[];
  for(let i=0;i<n;i++){const x=xMin+(xMax-xMin)*i/(n-1),y=ev(x,z===undefined?r.epoch.zRepresentative:z);if(Number.isFinite(y))out.push({x,y});}
  return out;
}
function pointsOf(r,z){return r.representation.type==="parametric"?sampled(r,NSAMPLE,z):(r.representation.points||[]);}
function snake(k){return k.replace(/[A-Z]/g,c=>"_"+c.toLowerCase());}
function recordRow(r,zEval){
  const d=r.definitions||{},p=r.provenance||{},e=r.epoch||{},rep=r.representation||{},a=r.axes||{},c=d.cosmology||{};
  const row={record_id:r.id,kind:r.kind,source:r.source,run:r.run,relation:r.relation,z:rep.type==="parametric"&&zEval!==undefined?zEval:e.zRepresentative,z_min:e.zMin,z_max:e.zMax,
    representation:rep.type==="parametric"?"sampled-parametric":"points",interval_kind:rep.intervalKind,connect:rep.connect!==false,
    x_unit:a.xUnit,y_unit:a.yUnit,x_definition:a.xDefinition,y_definition:a.yDefinition,tier:p.tier,rankable:!!r.rankable,calibration:r.calibration,
    population_note:r.selection&&r.selection.population,mass_class:massClass(d),cosmology_h0:c.H0,cosmology_om:c.Om,
    citation:p.citation,doi:p.doi,url:p.url,checksum_sha256:p.checksumSha256,retrieved:p.retrieved,definitions_json:JSON.stringify(d)};
  for(const k of DEF_COLS)row[snake(k)]=d[k];
  return row;
}
function pointRows(r,zEval){return pointsOf(r,zEval).map((p,i)=>({record_id:r.id,point_index:i,x:p.x,y:p.y,y_low:p.yLow,y_high:p.yHigh,x_low:p.xLow,x_high:p.xHigh,count:p.count}));}
function joined(records,zEval){
  const rows=[];
  for(const r of records){const rec=recordRow(r,zEval);for(const pt of pointRows(r,zEval))rows.push({...rec,...pt});}
  return rows;
}
const JOINED_COLS=[...RECORD_COLS.filter(k=>k!=="definitions_json"),"point_index","x","y","y_low","y_high","x_low","x_high","count","definitions_json"];
function cell(v){
  if(v===undefined||v===null)return"";
  const s=typeof v==="object"?JSON.stringify(v):String(v);
  return/[",\n\r]/.test(s)?`"${s.replace(/"/g,'""')}"`:s;
}
function toCsv(rows,cols,comments=[]){
  return comments.map(c=>`# ${c}`).join("\n")+(comments.length?"\n":"")+cols.join(",")+"\n"+rows.map(r=>cols.map(c=>cell(r[c])).join(",")).join("\n")+"\n";
}
function citations(records){
  const seen=new Map();
  for(const r of records){const p=r.provenance||{};const k=p.doi||p.url||p.citation;if(k&&!seen.has(k))seen.set(k,{citation:p.citation,doi:p.doi,url:p.url});}
  return[...seen.values()];
}
function bibtex(records){
  return citations(records).map((c,i)=>{
    const key=(c.doi||c.url||String(i)).replace(/[^A-Za-z0-9]+/g,"_").replace(/^_|_$/g,"");
    const f=[`  note = {${c.citation.replace(/,\s*(Fig\.|Figs\.|Figure|figure|Table|table|Eq\.|Tab\.|SFMS|supplementary).*$/,"").replace(/,\s[^,]*\(arXiv source numbering\).*$/,"").replace(/,\s*z=\S+( panel)?$/,"").replace(/[{}]/g,"")}}`];
    if(c.doi)f.unshift(`  doi = {${c.doi}}`);
    if(c.url)f.unshift(`  url = {${c.url}}`);
    return`@misc{${key},\n${f.join(",\n")}\n}`;
  }).join("\n\n")+"\n";
}
root.SimHighlineExport={RECORD_COLS,POINT_COLS,JOINED_COLS,NSAMPLE,massClass,sampled,recordRow,pointRows,joined,toCsv,citations,bibtex};
})(typeof globalThis!=="undefined"?globalThis:window);
