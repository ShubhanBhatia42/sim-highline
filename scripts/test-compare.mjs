import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const context = { globalThis: {} };
vm.runInNewContext(await readFile(new URL("../compare.js", import.meta.url), "utf8"), context, { filename: new URL("../compare.js", import.meta.url).href }); // the file name lets scripts/coverage.sh attribute coverage to the file
const { compatible, residuals, summarize, evaluator, MIN_BINS } = context.globalThis.SimHighlineCompare;
const load = async name => JSON.parse(await readFile(new URL(`../data/curves/${name}.json`, import.meta.url), "utf8")).records;
const [core, thesan, magneticum, cosmosweb, literature, vcd, sharda] = await Promise.all(["core", "thesan", "magneticum", "cosmosweb", "literature", "comparison-data", "colibre-mzr"].map(load));
const byId = id => [...core, ...thesan, ...magneticum, ...cosmosweb, ...literature, ...vcd].find(record => record.id === id);

const smf6 = byId("thesan1.gsmf.z6.official"), cw6 = cosmosweb.find(r => r.epoch.zMin <= 6 && 6 <= r.epoch.zMax);
const gsmfCheck = compatible(smf6, cw6);
assert.equal(gsmfCheck.verdict, "comparable-with-caveats", "THESAN vs COSMOS-Web GSMF must be comparable with documented caveats");
assert(gsmfCheck.caveats.some(c => c.startsWith("massDefinition")), "aperture vs SED-total mass caveat must surface");
assert(gsmfCheck.caveats.some(c => c.startsWith("H0")), "cosmology difference must surface");

const sfms6 = byId("thesan1.sfms.z6.official"), speagle = byId("speagle14.sfms.evolution");
assert.equal(compatible(sfms6, speagle).verdict, "not-comparable", "all-galaxy medians must not be scored against star-forming fits");
assert.equal(compatible(byId("thesan1.mzr.z6.official"), byId("thesan1.mzr.z6.official")).verdict, "not-comparable", "record-level context veto must hold");
assert.equal(compatible(magneticum.find(r => r.relation === "sfms"), speagle).verdict, "not-comparable", "Magneticum SFMS and THESAN SFMS must be judged by the same rule");

const res = residuals(smf6.representation.points, cw6.representation.points, smf6.representation.intervalKind, cw6.representation.intervalKind);
const stats = summarize(res);
assert(stats && stats.n >= MIN_BINS, "THESAN z=6 must overlap COSMOS-Web in at least MIN_BINS bins");
assert(Number.isFinite(stats.meanAbsSigma), "official tables with errors must yield sigma-normalised residuals");
assert.equal(stats.sigmaSource, "both", "THESAN GSMF statistical errors and COSMOS-Web errors must both enter sigma");
const scatterOnly = residuals(sfms6.representation.points, sfms6.representation.points, "scatter", "scatter");
assert(scatterOnly.every(r => !Number.isFinite(r.sigma)), "population percentiles must never be used as measurement uncertainties");
assert.equal(summarize(res.slice(0, MIN_BINS - 1)), null, "fewer than MIN_BINS overlaps must not be summarised");

const kh = evaluator(byId("kormendyho13.bhsigma.z0"));
assert(Math.abs(kh(Math.log10(200), 0) - 8.49) < 1e-9, "Kormendy-Ho expression must reproduce its normalisation");
const sp = evaluator(speagle);
assert(sp(10, 0) < sp(10, 2), "Speagle normalisation must rise with redshift");
for (const record of core.filter(r => r.representation.type === "parametric")) assert(Number.isFinite(evaluator(record)(record.domain.xMin, record.epoch.zRepresentative)), `${record.id}: expression must evaluate`);

const near = (a, b, tol, msg) => assert(Math.abs(a - b) < tol, `${msg}: ${a}`);
near(evaluator(byId("popesso23.sfms.evolution"))(10, 0), -0.05, 0.03, "Popesso+23 Eq. 14 at 10^10 Msun, z=0");
assert(evaluator(byId("popesso23.sfms.evolution"))(10, 2) > 1, "Popesso+23 normalisation must exceed 10 Msun/yr at 10^10 Msun, z=2");
near(evaluator(byId("baldry12.gsmf.z0"))(10, 0), -2.24, 0.02, "Baldry+12 double Schechter at 10^10 Msun");
near(evaluator(byId("curti20.mzr.z0"))(10.02, 0), 8.793 - 0.28 / 1.2 * Math.log10(2), 1e-9, "Curti+20 at the turnover mass");
const mag0 = magneticum.find(r => r.relation === "gsmf" && r.epoch.zNominal === 0), gama = byId("baldry12.gsmf.z0");
assert.equal(compatible(mag0, gama).verdict, "comparable-with-caveats", "Magneticum z~0 GSMF must be scoreable against GAMA with caveats");
assert(compatible(sfms6, byId("popesso23.sfms.evolution")).blockers.some(b => b.startsWith("population")), "population mismatch must block SFMS scoring");

const eagle = (run, z) => vcd.find(r => r.source === "EAGLE" && r.run === run && r.epoch.zRepresentative === z);
const b19 = vcd.find(r => r.source.startsWith("Behroozi et al. 2019") && r.relation === "shmr" && r.epoch.zRepresentative === 0);
const bn98 = compatible(eagle("Ref-L100N1504 BN98", 0), b19);
assert.equal(bn98.verdict, "comparable-with-caveats", "EAGLE BN98 SHMR must be comparable to UniverseMachine with caveats");
assert(bn98.caveats.some(c => c.startsWith("haloMassHistory")), "current vs peak halo mass must surface");
assert.equal(compatible(eagle("Ref-L100N1504 M200crit", 0), b19).verdict, "not-comparable", "M200crit must not be scored against BN98 haloes");
const lange = vcd.find(r => r.source.startsWith("Lange") && r.run === "r band");
assert.equal(compatible(eagle("Ref-L025N0376", 0.1006) || vcd.find(r => r.source === "EAGLE" && r.relation === "size"), lange).verdict, "not-comparable", "3D half-mass radii must not be scored against half-light radii");
assert(eagle("Ref-L025N0376", vcd.find(r => r.source === "EAGLE" && r.relation === "size").epoch.zRepresentative).calibration === "target", "EAGLE z~0.1 sizes were a calibration target");
assert(vcd.every(r => /@ [0-9a-f]{40}$/.test(r.provenance.compilation) && /^[0-9a-f]{64}$/.test(r.provenance.checksumSha256)), "compilation records must pin the commit and file hash");
const magZ0 = magneticum.find(r => r.run === "Box4/uhr" && r.relation === "gsmf" && r.epoch.zNominal === 0);
const lowz = vcd.filter(r => r.relation === "gsmf" && r.epoch.zRepresentative <= 0.1).map(r => summarize(residuals(magZ0.representation.points, r.representation.points, "unspecified", r.representation.intervalKind))).filter(Boolean);
assert(lowz.length >= 3 && lowz.every(st => st.median > 0.1), "Magneticum z~0 GSMF excess must be reproduced against independent low-z surveys (audit item, not a pass condition on the model)");

const colibre0 = sharda.find(r => r.source === "COLIBRE" && r.run === "m6" && r.epoch.zRepresentative === 0), curti = byId("curti20.mzr.z0");
const mzrCheck = compatible(colibre0, curti);
assert.equal(mzrCheck.verdict, "comparable-with-caveats", "intrinsic simulated O/H must be comparable to Te-anchored O/H with a calibration caveat");
assert(mzrCheck.caveats.some(c => c.startsWith("metallicityCalibration")), "metallicity calibration difference must surface");
assert(compatible(thesan.find(r => r.relation === "mzr"), curti).blockers.some(b => b.startsWith("metallicityQuantity")), "total metal mass fraction must never be scored against O/H");
assert(sharda.filter(r => r.kind === "simulation" && r.representation.type === "points" && r.source !== "SIMBA" && r.source !== "FIREbox").every(r => r.representation.points.every(p => p.count >= 20)), "Sharda+26 resolution and count cuts must be applied");
assert(sharda.filter(r => r.provenance.tier === "catalog-derived").every(r => /bootstrap/i.test(r.selection.warning)), "sim-highline-binned data must say how it was binned");
const jades = sharda.find(r => r.id === "curti24.jades.mzr.z3-6.binned"), colibre3 = sharda.find(r => r.source === "COLIBRE" && r.run === "m6" && r.epoch.zRepresentative === 3);
assert(compatible(colibre3, jades).caveats.some(c => c.startsWith("epoch")), "a single-epoch model inside a wide redshift bin must carry an epoch caveat");

const vik = vcd.find(r => r.source.startsWith("Vikhlinin") && r.relation === "fgas500");
assert(vik && vik.representation.points.every(p => p.y > Math.log10(0.2) && p.y < Math.log10(1.3)), "cluster gas fractions are normalised by Omega_b/Omega_m in the compilation and must be labelled so");
assert(vcd.filter(r => r.relation === "sfrf").length >= 20, "SFR functions from the compilation must be ingested across redshift");
const jwst = sharda.find(r => r.id === "sharda26.compilation.mzr.z6-8");
assert(jwst && jwst.representation.points.length >= 5 && /Binned by sim-highline from \d+ galaxies/.test(jwst.selection.warning), "the high-z MZR compilation must state its sample");

console.log(`Comparison tests passed: THESAN z=6 vs COSMOS-Web median ${stats.median.toFixed(3)} dex, mean |d|/sigma ${stats.meanAbsSigma.toFixed(1)} over ${stats.n} bins`);

{ // one documented set of IMF offsets: compare.js equals data/imf-offsets.json
  const { readFile: rf } = await import("node:fs/promises");
  const vm2 = await import("node:vm");
  const c2 = { globalThis: {} };
  vm2.default.runInNewContext(await rf(new URL("../compare.js", import.meta.url), "utf8"), c2);
  const off = JSON.parse(await rf(new URL("../data/imf-offsets.json", import.meta.url), "utf8"));
  assert.deepEqual(JSON.parse(JSON.stringify(c2.globalThis.SimHighlineCompare.IMF_DEX)), off.compareJs, "compare.js IMF_DEX must equal data/imf-offsets.json");
  const D = c2.globalThis.SimHighlineCompare.IMF_DEX;
  assert.ok(Math.abs((D.chabrier03 - D.kroupa01) - off.toChabrierDex.kroupa01) < 1e-9 && Math.abs((D.chabrier03 - D.salpeter55) - off.toChabrierDex.salpeter55) < 1e-9, "the offsets to Chabrier follow from the table");
  assert.ok(Math.abs(Math.log10(off.massFactorToChabrier.kroupa01) - off.toChabrierDex.kroupa01) < 1e-4 && Math.abs(Math.log10(off.massFactorToChabrier.salpeter55) - off.toChabrierDex.salpeter55) < 1e-4, "dex and factors agree");
}

// every definition key a comparability rule uses has a plain-language name, and the Explorer's "your run" form explains it
{
  const { RULES, KEY_LABEL } = context.globalThis.SimHighlineCompare;
  const keys = new Set(Object.values(RULES).flatMap(r => [...r.hard, ...r.soft]));
  const unnamed = [...keys].filter(k => !KEY_LABEL[k]);
  assert.deepEqual(unnamed, [], `definition keys without a plain name in compare.js KEY_LABEL: ${unnamed.join(", ")}`);
  assert(Object.values(KEY_LABEL).every(v => typeof v === "string" && v.length > 3 && !/^[a-z]+[A-Z]/.test(v)), "a KEY_LABEL value looks like a code name, not words");
  const html = await readFile(new URL("../highline/index.html", import.meta.url), "utf8");
  const help = html.match(/const MINE_HELP=\{[\s\S]*?\};/)[0];
  const unexplained = [...keys].filter(k => !new RegExp(`[{,]${k}:"`).test(help));
  assert.deepEqual(unexplained, [], `definition keys without help text in the Explorer's MINE_HELP: ${unexplained.join(", ")}`);
  assert(!/const KEY_LABEL=\{/.test(html), "the Explorer must read KEY_LABEL from compare.js, not keep its own copy");
}
{ // a mass function of quiescent galaxies, of centrals only, or of a zoom sample is not the mass function of all galaxies; spelling variants of "all" are one population
  const { populationClass } = context.globalThis.SimHighlineCompare;
  const cases = { all: "all", "all galaxies": "all", "all galaxies (PGalF)": "all", "All galaxies": "all", quiescent: "quiescent", passive: "quiescent", "all galaxies, passive": "quiescent", "star-forming": "star-forming", "all galaxies, star-forming": "star-forming", centrals: "centrals", satellites: "satellites", "all galaxies of the zoom sample, as drawn": "zoom",
    "star-forming-centrals": "centrals star-forming", "zoom-centrals": "centrals zoom", "isolated-zoom-centrals": "centrals isolated zoom", "star-forming galaxies, sSFR > 0.2 / t_H(z)": "star-forming galaxies, sSFR > 0.2 / t_H(z)" };
  for (const [text, want] of Object.entries(cases)) assert.equal(populationClass(text), want, `population "${text}" must read as "${want}"`);
  assert.equal(populationClass("something else"), "something else", "an unknown population stays as written");
  assert.equal(populationClass(undefined), undefined);
  const rec = (population, source) => ({ relation: "gsmf", source, rankable: true, epoch: { zRepresentative: 1 }, definitions: { densityFrame: "comoving", imf: "chabrier03", massDefinition: "total", cosmology: { H0: 70, Om: 0.3 }, population } });
  const v = (a, b) => compatible(rec(a, "A"), rec(b, "B"));
  assert.equal(v("all", "all galaxies").verdict, "comparable", "'all' and 'all galaxies' are the same population");
  for (const other of ["quiescent", "centrals", "all galaxies of the zoom sample, as drawn", "star-forming"]) {
    const r = v("all", other);
    assert.equal(r.verdict, "not-comparable", `a mass function of '${other}' must not be compared with one of all galaxies`);
    assert(r.blockers.some(b => b.startsWith("population")), "the blocker must name the population");
  }
  assert.equal(v("quiescent", "passive").verdict, "comparable", "'quiescent' and 'passive' are the same population");
}
