import { definitionsFor } from "./definitions.mjs";
import { readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";

const sourceDir = process.argv[2] ? new URL(`file://${process.argv[2].replace(/\/$/, "")}/`) : new URL("file:///private/tmp/");
const output = new URL("../data/curves/thesan.json", import.meta.url);
const retrieved = new Date().toISOString().slice(0, 10);
const citation = "Kannan et al. 2022; Garaldi et al. 2024; THESAN data release";
const baseUrl = "https://www.thesan-project.com/thesan/quantities/";
const inputFiles = ["gms_Thesan1.dat", "mzr_Thesan1.dat", "smf_Thesan1.dat", "smhm_Thesan1.dat"];
const hashes = Object.fromEntries(await Promise.all(inputFiles.map(async file => {
  const bytes = await readFile(new URL(file, sourceDir));
  return [file, createHash("sha256").update(bytes).digest("hex")];
})));

function finite(value) { return Number.isFinite(value) && value > 0; }
function log(value) { return +Math.log10(value).toFixed(6); }
async function rows(file) {
  const text = await readFile(new URL(file, sourceDir), "utf8");
  return text.split(/\r?\n/).filter(line => line.trim() && !line.startsWith("#")).map(line => line.trim().split(/\s+/).map(Number));
}
function groups(rows) {
  return Map.groupBy(rows, row => row[0]);
}
function record({relation, z, file, axes, points, domain, scatter, selection, rankable, notes}) {
  selection.aperture = "inner 30 physical kpc for StellarMass and SFR, per THESAN release changelog";
  return {
    id:`thesan1.${relation}.z${z}.official`,source:"THESAN-1",run:"THESAN-1",kind:"simulation",relation,
    epoch:{zRepresentative:z,zMin:z,zMax:z,mode:"published-epoch",snapshot:null},axes,domain,
    representation:{type:"points",intervalKind:relation==="gsmf"?"uncertainty":"scatter",points},scatter,selection,definitions:definitionsFor("THESAN-1",relation),
    provenance:{tier:"official-table",citation,doi:null,url:`${baseUrl}${file}`,retrieved,checksumSha256:hashes[file]},
    calibration:"prediction",rankable,notes
  };
}

const records = [];
for (const [z, values] of groups(await rows("gms_Thesan1.dat"))) {
  const points = values.filter(([,m,y,lo,hi]) => [m,y,lo,hi].every(finite)).map(([,m,y,lo,hi]) => ({x:log(m),y:log(y),yLow:log(lo),yHigh:log(hi)}));
  records.push(record({relation:"sfms",z,file:"gms_Thesan1.dat",axes:{xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 star-formation rate",yUnit:"log10(Msun/yr)"},points,domain:{xMin:points[0].x,xMax:points.at(-1).x},scatter:{lower:"16th percentile",upper:"84th percentile"},selection:{population:"THESAN-1 galaxies",warning:"Published table does not specify an observationally matched SFR averaging timescale."},rankable:true,notes:"Official medians and percentiles; linear values converted to base-10 logarithms."}));
}
for (const [z, values] of groups(await rows("mzr_Thesan1.dat"))) {
  const points = values.filter(([,m,y,lo,hi]) => [m,y,lo,hi].every(finite)).map(([,m,y,lo,hi]) => ({x:log(m),y:log(y),yLow:log(lo),yHigh:log(hi)}));
  records.push(record({relation:"mzr",z,file:"mzr_Thesan1.dat",axes:{xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 gas metallicity mass fraction",yUnit:"log10(Zgas)"},points,domain:{xMin:points[0].x,xMax:points.at(-1).x},scatter:{lower:"16th percentile",upper:"84th percentile"},selection:{population:"THESAN-1 galaxies",warning:"Not directly comparable to strong-line 12+log(O/H)."},rankable:false,notes:"Retained in native metallicity definition; requires abundance conversion or forward modelling."}));
}
for (const [z, values] of groups(await rows("smf_Thesan1.dat"))) {
  const points = values.filter(([,m,y,e]) => [m,y,e].every(finite) && y > e).map(([,m,y,e]) => ({x:log(m),y:log(y),yLow:log(y-e),yHigh:log(y+e)}));
  records.push(record({relation:"gsmf",z,file:"smf_Thesan1.dat",axes:{xDefinition:"log10 stellar mass",xUnit:"log10(Msun)",yDefinition:"log10 galaxy number density per dex",yUnit:"log10(cMpc^-3 dex^-1)"},points,domain:{xMin:points[0].x,xMax:points.at(-1).x},scatter:{lower:"tabulated statistical error",upper:"tabulated statistical error"},selection:{population:"THESAN-1 galaxies",warning:"Simulation volume limits the rare high-mass tail."},rankable:true,notes:"Linear number densities and symmetric errors transformed to log space."}));
}
for (const [z, values] of groups(await rows("smhm_Thesan1.dat"))) {
  const points = values.filter(([,m,y,lo,hi]) => finite(m) && finite(y) && finite(lo) && finite(hi)).map(([,m,y,lo,hi]) => ({x:log(m),y:log(y),yLow:log(lo),yHigh:log(hi)}));
  records.push(record({relation:"shmr",z,file:"smhm_Thesan1.dat",axes:{xDefinition:"log10 halo mass",xUnit:"log10(Msun)",yDefinition:"log10 stellar-to-halo mass ratio",yUnit:"dex"},points,domain:{xMin:points[0].x,xMax:points.at(-1).x},scatter:{lower:"10th percentile",upper:"90th percentile"},selection:{population:"THESAN-1 haloes",warning:"Halo mass convention must be matched before ranking."},rankable:false,notes:"Zeros removed before logarithmic conversion; native 10th/90th percentiles retained."}));
}

records.sort((a,b) => a.relation.localeCompare(b.relation) || a.epoch.zRepresentative-b.epoch.zRepresentative);
await writeFile(output, `${JSON.stringify({schemaVersion:"1.0.0",records},null,2)}\n`);

console.log(`Ingested ${records.length} THESAN relation records`);
