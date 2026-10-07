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
const EXPRESSIONS={
  "speagle14.sfms.evolution":{expression:"(0.84-0.026*t)*x-(6.51-0.11*t)",ageCosmology:{H0:70,Om:0.3}},
  "lelli19.btfr.z0":{expression:"slope*x+intercept"},
  "kormendyho13.bhsigma.z0":{expression:"normalizationAt200+slope*(x-log10(200))"}
};
for (const file of (await readdir(directory)).filter(file => file.endsWith(".json"))) {
  const url=new URL(file,directory),payload=JSON.parse(await readFile(url,"utf8"));
  for (const record of payload.records) {
    if(DEFINITIONS[record.source]?.[record.relation])record.definitions=definitionsFor(record.source,record.relation);
    else if(!record.definitions)throw new Error(`${record.id}: no structured definitions`);
    {const p=record.provenance,hay=[p.citation,p.url,p.sourceMember,p.extractionMethod].join(" "),hit=TERMS.find(t=>t.re.test(hay));if(hit)p.terms=hit.terms;else delete p.terms}
    if(record.kind==="simulation"&&!record.definitions.imf&&SUITE_IMF[record.source])record.definitions.imf=SUITE_IMF[record.source];
    if(record.representation.type==="points"&&!record.representation.intervalKind)record.representation.intervalKind=intervalKindFor(record);
    if(record.representation.type==="parametric"&&!record.representation.expression){
      const extra=EXPRESSIONS[record.id]||(record.source==="Stott et al. 2013"?{expression:"slope*(x-10)+intercept"}:null);
      if(!extra)throw new Error(`${record.id}: parametric record without expression`);
      Object.assign(record.representation,extra);
    }
  }
  await writeFile(url,`${JSON.stringify(payload,null,2)}\n`);
}
console.log("Structured definitions and parametric expressions annotated");
