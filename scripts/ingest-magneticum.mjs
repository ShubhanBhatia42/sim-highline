import { definitionsFor } from "./definitions.mjs";
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";

const sourceDir = process.argv[2] ? new URL(`file://${process.argv[2].replace(/\/$/,"")}/`) : new URL("file:///private/tmp/magneticum/data/");
const output = new URL("../data/curves/magneticum.json", import.meta.url);
const archiveUrl = "https://wwwmpa.mpa-garching.mpg.de/HydroSims/Magneticum/Downloads/data.zip";
const citation = "Dolag et al. 2025, Encyclopedia Magneticum";
const retrieved = new Date().toISOString().slice(0,10);
const epochs = [0,1,2,4];
const definitions = [
  {stem:"SFMS",relation:"sfms",xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 star-formation rate",yUnit:"log10(Msun/yr)",rankable:false,warning:"Box4/uhr table does not document a star-forming selection or SFR averaging timescale."},
  {stem:"stellar_mass_function",relation:"gsmf",xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 galaxy number density per dex",yUnit:"log10(Mpc^-3 dex^-1)",rankable:true,warning:"Box4/uhr volume limits the massive tail; published h^3 densities converted with h=0.704.",transform:y=>y+3*Math.log10(.704)},
  {stem:"Mbh_Mstar",relation:"bh",xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 black-hole mass",yUnit:"log10(Msun)",rankable:false,warning:"Galaxy aperture and black-hole occupation selection require paper-level audit before ranking."},
  {stem:"Mbh_sigma",relation:"bhsigma",xDefinition:"log10 stellar velocity dispersion",xUnit:"log10(km/s)",yDefinition:"log10 black-hole mass",yUnit:"log10(Msun)",rankable:false,warning:"Velocity-dispersion aperture and black-hole selection require paper-level audit before ranking."},
  {stem:"specific_angular_momentum_relation",relation:"jstar",xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 stellar specific angular momentum",yUnit:"log10(kpc km/s)",rankable:false,warning:"Morphology and radial aperture are not specified in the table header."}
  ,{stem:"Mstar_M200c",relation:"shmr",xDefinition:"log10 halo mass M200c",xUnit:"log10(Msun)",yDefinition:"log10 stellar-to-halo mass ratio M*(<0.1 rvir)/M200c, from the released log10 M*(<0.1 rvir)",yUnit:"dex",rankable:false,warning:"Stellar mass is within 0.1 rvir; the released table gives log10 M*, converted here by subtracting log10 M200c.",transform:(y,x)=>y-x}
  ,{stem:"Mstar_Zstar",relation:"zstar",xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 stellar metallicity Z*/Zsun (Zsun = 0.0142, Asplund+09)",yUnit:"dex",rankable:false,warning:"Weighting and aperture of the stellar metallicity are not stated in the table header."}
  ,{stem:"Mass_Size",relation:"size",xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 stellar half-mass radius",yUnit:"log10(kpc)",rankable:false,warning:"The released relation is a stellar half-mass radius for the full galaxy population; observational half-light fits and star-forming selections are shown as definition-mismatched context."}
];

async function parse(file) {
  const bytes = await readFile(new URL(file,sourceDir));
  const text = bytes.toString("utf8");
  const header = text.split(/\r?\n/).find(line=>/Boxes and Redshifts/i.test(line));
  const boxes = [...(header||"").matchAll(/Box(\w+) (\w+) z=([0-9.]+)/g)].map(m=>({name:m[1],res:m[2],z:Number(m[3]),points:[]}));
  if(!boxes.some(b=>b.name==="4"&&b.res==="uhr")) throw new Error(`${file}: Box4/uhr redshift missing from header`);
  const rows = text.split(/\r?\n/).filter(line=>line.trim()&&!line.startsWith("#")).map(line=>line.trim().split(/\s+/).map(Number));
  if(rows.some(r=>r.length!==1+3*boxes.length)) throw new Error(`${file}: ${boxes.length} boxes but a row has a different column count`);
  for(const row of rows) boxes.forEach((b,k)=>{const [y,lo,hi]=row.slice(1+3*k,4+3*k);if([row[0],y,lo,hi].every(Number.isFinite))b.points.push({x:row[0],y,yLow:lo,yHigh:hi})});
  return {checksum:createHash("sha256").update(bytes).digest("hex"),boxes};
}

const records=[];
for(const definition of definitions) for(const z of epochs){
  const file=`Magneticum_${definition.stem}_z${z}.dat`,parsed=await parse(file),convert=definition.transform||((value)=>value);
  for(const box of parsed.boxes){
    const run=`Box${box.name}/${box.res}`,isMain=box.name==="4"&&box.res==="uhr";
    const points=box.points.map(point=>({x:+point.x.toFixed(6),y:+convert(point.y,point.x).toFixed(6),yLow:+convert(point.yLow,point.x).toFixed(6),yHigh:+convert(point.yHigh,point.x).toFixed(6)}));
    if(points.length<2){if(isMain)throw new Error(`${file}: fewer than two finite Box4/uhr points`);continue}
    records.push({
      id:`magneticum.box${box.name.toLowerCase()}${box.res}.${definition.relation}.z${z}.official`,source:"Magneticum Pathfinder",run,kind:"simulation",relation:definition.relation,
      epoch:{zRepresentative:box.z,zNominal:z,zMin:box.z,zMax:box.z,mode:"published-epoch",snapshot:null},
      axes:{xDefinition:definition.xDefinition,xUnit:definition.xUnit,yDefinition:definition.yDefinition,yUnit:definition.yUnit},
      domain:{xMin:points[0].x,xMax:points.at(-1).x},representation:{type:"points",intervalKind:"unspecified",points},
      scatter:{lower:"published lower 1-sigma bound",upper:"published upper 1-sigma bound"},
      selection:{population:`Magneticum ${run} galaxies`,warning:definition.warning.replaceAll("Box4/uhr",run)},definitions:definitionsFor("Magneticum Pathfinder",definition.relation),
      provenance:{tier:"official-table",citation,doi:null,url:archiveUrl,sourceMember:`data/${file}`,retrieved,checksumSha256:parsed.checksum},
      calibration:"prediction",rankable:definition.rankable,notes:`${run} column of the released multi-box table; no cross-box stitching. Filename epoch z=${z}; the header gives the actual ${run} output z=${box.z}.`
    });
  }
}
records.sort((a,b)=>a.relation.localeCompare(b.relation)||a.epoch.zRepresentative-b.epoch.zRepresentative);
await writeFile(output,`${JSON.stringify({schemaVersion:"1.0.0",records},null,2)}\n`);
console.log(`Ingested ${records.length} Magneticum relation records (all released boxes)`);
