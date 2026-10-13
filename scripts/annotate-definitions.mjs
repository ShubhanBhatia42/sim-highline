import { readFile, readdir, writeFile } from "node:fs/promises";
import { DEFINITIONS, definitionsFor } from "./definitions.mjs";

const directory = new URL("../data/curves/", import.meta.url);
const TERMS = JSON.parse(await readFile(new URL("../data/source-terms.json", import.meta.url), "utf8")).rules.map(r => ({ ...r, re: new RegExp(r.match, "i") }));
function intervalKindFor(record){
  if(record.source==="COSMOS-Web 2025")return "uncertainty";
  if(record.source==="THESAN-1")return record.relation==="gsmf"?"uncertainty":"scatter";
  return "unspecified";
}
const SUITE_IMF={"EAGLE":"chabrier03"};
const FILLS=JSON.parse(await readFile(new URL("../data/definition-fills.json",import.meta.url),"utf8")).fills;
const UNSET=new Set([undefined,null,"unspecified","heterogeneous"]);
const applied=new Map(FILLS.map(f=>[f.id,0]));
function fillDefinitions(record){
  const ids=[],prior=record.provenance.definitionFills||[];
  for(const f of FILLS){
    const m=f.match;
    if(m.source!==record.source||(m.relation&&![].concat(m.relation).includes(record.relation))||(m.citationIncludes&&!String(record.provenance.citation).includes(m.citationIncludes)))continue;
    let used=false;
    for(const [k,v] of Object.entries(f.set)){
      const cur=record.definitions[k];
      if(UNSET.has(cur)){record.definitions[k]=v;used=true}
      else if(cur===v&&prior.includes(f.id))used=true;
      else if(cur!==v)throw new Error(`${record.id}: fill ${f.id} would overwrite ${k}=${cur} with ${v}`);
    }
    if(used){ids.push(f.id);applied.set(f.id,applied.get(f.id)+1)}
  }
  if(ids.length)record.provenance.definitionFills=ids;else delete record.provenance.definitionFills;
}
const EXPRESSIONS={
  "speagle14.sfms.evolution":{expression:"(0.84-0.026*t)*x-(6.51-0.11*t)",ageCosmology:{H0:70,Om:0.3}},
  "lelli19.btfr.z0":{expression:"slope*x+intercept"},
  "kormendyho13.bhsigma.z0":{expression:"normalizationAt200+slope*(x-log10(200))"}
};
for (const file of (await readdir(directory)).filter(file => file.endsWith(".json"))) {
  const url=new URL(file,directory),payload=JSON.parse(await readFile(url,"utf8"));
  for (const record of payload.records) {
    if(DEFINITIONS[record.source]?.[record.relation])record.definitions=structuredClone(definitionsFor(record.source,record.relation));
    else if(!record.definitions)throw new Error(`${record.id}: no structured definitions`);
    {const p=record.provenance,hay=[p.citation,p.url,p.sourceMember,p.extractionMethod].join(" "),hit=TERMS.find(t=>t.re.test(hay));if(hit)p.terms=hit.terms;else delete p.terms}
    if(record.kind==="simulation"&&!record.definitions.imf&&SUITE_IMF[record.source])record.definitions.imf=SUITE_IMF[record.source];
    fillDefinitions(record);
    if(record.representation.type==="points"&&!record.representation.intervalKind)record.representation.intervalKind=intervalKindFor(record);
    if(record.representation.type==="parametric"&&!record.representation.expression){
      const extra=EXPRESSIONS[record.id]||(record.source==="Stott et al. 2013"?{expression:"slope*(x-10)+intercept"}:null);
      if(!extra)throw new Error(`${record.id}: parametric record without expression`);
      Object.assign(record.representation,extra);
    }
  }
  await writeFile(url,`${JSON.stringify(payload,null,2)}\n`);
}
for(const [id,n] of applied)if(!n)throw new Error(`definition fill ${id} matched no record`);
console.log(`Structured definitions and parametric expressions annotated; ${[...applied.values()].reduce((a,b)=>a+b,0)} record fills from ${applied.size} sourced rules`);
