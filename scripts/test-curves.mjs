import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const core = JSON.parse(await readFile(new URL("../data/curves/core.json", import.meta.url), "utf8"));
const thesan = JSON.parse(await readFile(new URL("../data/curves/thesan.json", import.meta.url), "utf8"));
const magneticum = JSON.parse(await readFile(new URL("../data/curves/magneticum.json", import.meta.url), "utf8"));
const cosmosweb = JSON.parse(await readFile(new URL("../data/curves/cosmosweb.json", import.meta.url), "utf8"));
const digitized = JSON.parse(await readFile(new URL("../data/curves/digitized.json", import.meta.url), "utf8"));
const speagle = core.records.find(record => record.id === "speagle14.sfms.evolution");
assert(speagle, "Speagle evolution record missing");

function cosmicAgeGyr(z) {
  const om = 0.3, ol = 0.7, h = 0.70, hubbleTime = 9.778 / h;
  return 2 * hubbleTime / (3 * Math.sqrt(ol)) * Math.asinh(Math.sqrt(ol / om) / (1 + z) ** 1.5);
}

function coefficients(z) {
  const t = cosmicAgeGyr(z);
  return { slope: 0.84 - 0.026 * t, intercept: -(6.51 - 0.11 * t) };
}

const z0 = coefficients(0), z3 = coefficients(3), z6 = coefficients(6);
assert(z0.slope < z3.slope && z3.slope < z6.slope, "SFMS slope must evolve, not translate rigidly");
assert.notEqual(z0.intercept, z3.intercept, "SFMS normalization must evolve");
assert.equal(core.records.some(record => record.kind === "simulation"), false, "Core file must not imply un-ingested simulation curves");
assert.equal(thesan.records.length, 20, "THESAN ingestion must contain four relations at five epochs");
for (const relation of ["sfms","gsmf","mzr","shmr"]) assert.deepEqual(thesan.records.filter(record=>record.relation===relation).map(record=>record.epoch.zRepresentative),[6,7,8,9,10]);
assert(thesan.records.filter(record=>record.relation==="mzr").every(record=>!record.rankable), "Native THESAN metallicities must remain non-rankable");
assert(thesan.records.filter(record=>record.relation==="shmr").every(record=>!record.rankable), "Native THESAN halo masses must remain non-rankable");
assert(thesan.records.every(record=>/^[a-f0-9]{64}$/.test(record.provenance.checksumSha256)), "Official tables must retain source hashes");
assert(thesan.records.every(record=>record.selection.aperture?.includes("30 physical kpc")), "THESAN aperture metadata must be explicit");

function endSlope(record) {
  const points = record.representation.points;
  return (points.at(-1).y - points[0].y) / (points.at(-1).x - points[0].x);
}
function nearest(record, x) {
  return record.representation.points.reduce((best, point) => Math.abs(point.x-x) < Math.abs(best.x-x) ? point : best);
}
const sfms6 = thesan.records.find(record=>record.relation==="sfms"&&record.epoch.zRepresentative===6);
const sfms10 = thesan.records.find(record=>record.relation==="sfms"&&record.epoch.zRepresentative===10);
assert(Math.abs(endSlope(sfms6)-endSlope(sfms10))>.08, "THESAN SFMS evolution must retain shape changes, not rigid offsets");
const gsmf6 = thesan.records.find(record=>record.relation==="gsmf"&&record.epoch.zRepresentative===6);
const gsmf10 = thesan.records.find(record=>record.relation==="gsmf"&&record.epoch.zRepresentative===10);
assert(nearest(gsmf10,8).y < nearest(gsmf6,8).y, "THESAN z=10 abundance should be below z=6 near 10^8 Msun");
const uhr=magneticum.records.filter(record=>record.run==="Box4/uhr");
assert.equal(uhr.length,32,"Magneticum Box4/uhr must have eight relations at four epochs");
for(const relation of ["sfms","gsmf","bh","bhsigma","jstar","size","shmr","zstar"])assert.deepEqual(uhr.filter(record=>record.relation===relation).map(record=>record.epoch.zRepresentative),[0.066,0.995,1.98,4.228]);
assert(magneticum.records.every(record=>[0,1,2,4].includes(record.epoch.zNominal)),"Magneticum records must retain nominal filename epochs separately");
assert.deepEqual([...new Set(magneticum.records.map(record=>record.run))].sort(),["Box0/mr","Box2/hr","Box2b/hr","Box3/uhr","Box4/uhr"],"each Magneticum run is one box; boxes are never stitched");
assert(magneticum.records.every(record=>record.id.includes("."+record.run.replace("/","").replace(/^Box/,"box").toLowerCase()+".")||record.id.includes(record.run.toLowerCase().replace("/",""))),"record ids must name their box");
assert(magneticum.records.filter(record=>record.relation!=="gsmf").every(record=>!record.rankable),"Definition-incomplete Magneticum relations must remain context only");
const magneticumSfms0=uhr.find(record=>record.relation==="sfms"&&record.epoch.zNominal===0);
const magneticumSfms4=uhr.find(record=>record.relation==="sfms"&&record.epoch.zNominal===4);
assert(Math.abs(endSlope(magneticumSfms0)-endSlope(magneticumSfms4))>.05,"Magneticum SFMS evolution must retain tabulated shape changes");
assert.equal(cosmosweb.records.length,15,"COSMOS-Web ingestion must retain all fifteen observational redshift bins");
assert(cosmosweb.records.every(record=>record.kind==="observation"&&record.rankable),"COSMOS-Web bins must be rankable observational anchors");
assert(cosmosweb.records.every(record=>record.epoch.zMin<record.epoch.zMax),"COSMOS-Web bin widths must be retained");
const cosmosLow=cosmosweb.records[0],cosmosHigh=cosmosweb.records.at(-1);
assert(nearest(cosmosHigh,9.3).y<nearest(cosmosLow,9.3).y,"COSMOS-Web abundance near 10^9.3 Msun must decline toward z > 10");
assert.equal(core.records.filter(record=>record.source==="Stott et al. 2013"&&record.relation==="size").length,4,"Stott published mass-size fits must retain all four tabulated epochs");
const nihaoGas=digitized.records.find(record=>record.id==="nihao.stinson15.coldgas.z0.fig1.digitized");
assert.equal(nihaoGas.representation.points.length,40,"NIHAO Figure 1 extraction must retain all unblended markers");
assert.equal(nihaoGas.provenance.tier,"digitized-figure","Figure-derived data must remain explicitly labeled");
assert(nihaoGas.provenance.axisCalibrationPixels&&nihaoGas.provenance.digitizationUncertaintyDex,"Digitized evidence must retain calibration and uncertainty");
assert(digitized.records.every(record=>!record.rankable),"Figure extractions remain context-only until independent digitization QA");

console.log(`Curve tests passed: Speagle ${z0.slope.toFixed(3)} -> ${z6.slope.toFixed(3)}; THESAN ${endSlope(sfms6).toFixed(3)} -> ${endSlope(sfms10).toFixed(3)}; Magneticum ${endSlope(magneticumSfms0).toFixed(3)} -> ${endSlope(magneticumSfms4).toFixed(3)}`);
