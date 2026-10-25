import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import vm from "node:vm";
const root = new URL("../", import.meta.url);
const ctx = {};
vm.runInNewContext(await readFile(new URL("highline/logic.js", root), "utf8"), ctx);
const L = ctx.SimHighlineLogic;
const rec = (source, run, z, tier = "catalog-derived") => ({ source, run, epoch: { zRepresentative: z }, provenance: { tier } });

assert.equal(L.tol(0), .15);
assert.ok(Math.abs(L.tol(9) - 1) < 1e-12);
assert.equal(L.nearest([], 3), 0);
assert.equal(L.nearest([0, 1, 2, 4], 2.9), 2);
assert.equal(L.nearest([0, 1, 2, 4], 3.1), 4);

const fl = L.primaryUnits([rec("FLAMINGO", "L1_m9", 0), rec("FLAMINGO", "L1_m9 variation Jet", 0), rec("FLAMINGO", "L1_m10", 0), rec("FLAMINGO", "L1_m10", 1)]);
assert.deepEqual([...fl], ["FLAMINGO|L1_m9"], "fiducial pattern wins over more epochs");
const variants = L.primaryUnits([rec("X", "low-res", 0), rec("X", "low-res", 1), rec("X", "main", 0)]);
assert.deepEqual([...variants], ["X|main"], "variant-like runs lose to plain runs");
const epochs = L.primaryUnits([rec("Y", "a", 0), rec("Y", "b", 0), rec("Y", "b", 1)]);
assert.deepEqual([...epochs], ["Y|b"], "more epochs wins among equals");
const tiers = L.primaryUnits([rec("Z", "a", 0, "digitized-figure"), rec("Z", "b", 0, "official-table")]);
assert.deepEqual([...tiers], ["Z|b"], "better evidence tier wins on a tie");
assert.deepEqual([...L.primaryUnits([rec("W", "b", 0), rec("W", "a", 0)])], ["W|a"], "alphabetical last resort");
assert.equal(L.primaryUnits([rec("A", "r", 0), rec("B", "r", 0)]).size, 2, "one unit per source");

const interp = (pts, x) => { for (let i = 0; i < pts.length - 1; i++) if (x >= pts[i].x && x <= pts[i + 1].x) return pts[i].y + (pts[i + 1].y - pts[i].y) * (x - pts[i].x) / (pts[i + 1].x - pts[i].x); return NaN; };
const line = (a, b, xs) => xs.map(x => ({ x, y: a + b * x }));
assert.ok(Math.abs(L.medianOffset(line(0, 1, [1, 2, 3, 4]), line(0.5, 1, [0, 1, 2, 3, 4, 5]), interp) - 0.5) < 1e-12, "constant offset recovered");
assert.equal(L.medianOffset(line(0, 1, [1, 2]), line(0, 1, [0, 5, 6]), interp), null, "fewer than three anchor points");
assert.equal(L.medianOffset(line(0, 1, [8, 9, 10]), line(0, 1, [0, 1, 2]), interp), null, "no overlap gives no offset");
assert.equal(L.medianOffset(line(0, 1, [0, 1, 2, 3, 20]), line(1, 1, [0, 1, 2, 3, 4]), interp), 1, "points outside the simulation range are ignored");

const obs = [{ source: "COSMOS-Web 2025", epoch: { zRepresentative: 1 } }, { source: "COSMOS-Web 2025", epoch: { zRepresentative: 3 } }, { source: "Baldry et al. 2012 (GAMA)", epoch: { zRepresentative: 0.03 } }];
assert.equal(L.pickAnchor(obs, /COSMOS-Web 2025|Baldry/, 0).source, "Baldry et al. 2012 (GAMA)");
assert.equal(L.pickAnchor(obs, /COSMOS-Web 2025|Baldry/, 2.6).epoch.zRepresentative, 3);
assert.equal(L.pickAnchor(obs, /Nothing/, 1), null);

const records = [];
for (const f of (await readdir(new URL("data/curves/", root))).filter(f => f.endsWith(".json"))) for (const r of JSON.parse(await readFile(new URL(`data/curves/${f}`, root), "utf8")).records) if (r.kind === "simulation") records.push(r);
const rels = [...new Set(records.map(r => r.relation))];
for (const rel of rels) {
  const rs = records.filter(r => r.relation === rel), prim = L.primaryUnits(rs);
  for (const s of new Set(rs.map(r => r.source))) assert.equal([...prim].filter(u => u.startsWith(s + "|")).length, 1, `${rel}: ${s} must have exactly one fiducial run`);
}
const btfr = L.primaryUnits(records.filter(r => r.relation === "btfr"));
assert.ok([...btfr].includes("SIMBA|m100n1024 + hires (combined), V_flat fit"), "SIMBA BTFR defaults to the combined V_flat fit");
assert.ok([...L.primaryUnits(records.filter(r => r.relation === "gsmf"))].some(u => u.startsWith("FLAMINGO|L1_m9")), "FLAMINGO fiducial is L1_m9");
const sz = L.primaryUnits(records.filter(r => r.relation === "size"));
assert.ok([...sz].some(u => /^COLIBRE\|.*centrals, star-forming/.test(u)), "COLIBRE size defaults to star-forming centrals");
console.log(`Logic tests passed: ${rels.length} relations, one fiducial run per source in each`);

const pu = L.parseUserCurve("# my run\nx,y,err\n9,-2,0.1\n10,-3,0.2\nbad,row\n11,-4,0.3");
assert.equal(pu.pts.length, 3); assert.equal(pu.skipped, 1);
assert.ok(Math.abs(pu.pts[0].lo - -2.1) < 1e-12 && Math.abs(pu.pts[0].hi - -1.9) < 1e-12);
const pl = L.parseUserCurve("1e9 1e-2\n1e10 1e-3\n0 5", { linear: true });
assert.equal(pl.pts.length, 2); assert.equal(pl.skipped, 1); assert.ok(Math.abs(pl.pts[0].x - 9) < 1e-12 && Math.abs(pl.pts[1].y - -3) < 1e-12);
const p4 = L.parseUserCurve("9\t-2\t-2.2\t-1.8\n8\t-1\t-1.1\t-0.9");
assert.equal(p4.pts[0].x, 8); assert.equal(p4.pts[0].lo, -1.1); assert.equal(p4.pts[1].hi, -1.8);
console.log("logic: user curve parsing OK");

const par = (o, n = 8) => Array.from({ length: n }, (_, i) => ({ x: 8 + i * .5, y: -1 - i * .3 + o }));
const sp = L.spread([par(0), par(.1), par(-.1)]);
assert.ok(sp && Math.abs(sp.sigma - .1) < 1e-9 && sp.suites === 3, "three parallel curves 0.1 dex apart have spread 0.1");
assert.equal(L.spread([par(0), par(.1)]), null, "fewer than three suites give no spread");
assert.equal(L.spread([par(0), par(.1), [{ x: 20, y: 0 }, { x: 21, y: 0 }]]), null, "non-overlapping curves give no spread");
const gap = par(0).filter((_, i) => i !== 3 && i !== 4);
assert.ok(L.spread([gap, par(.1), par(-.1)]).grid < L.spread([par(0), par(.1), par(-.1)]).grid, "gaps wider than 0.6 dex are never interpolated");
console.log("logic: spread OK");

// The caveat line of a figure (plotCaveats): generated from the comparison rules in compare.js, not typed per relation.
{
  const c2 = {};
  vm.runInNewContext(await readFile(new URL("compare.js", root), "utf8"), c2);
  vm.runInNewContext(await readFile(new URL("highline/logic.js", root), "utf8"), c2);
  const C = c2.SimHighlineCompare, PC = (...args) => JSON.parse(JSON.stringify(c2.SimHighlineLogic.plotCaveats(...args))), R = C.RULES.sfms; // a JSON copy, so that arrays made inside the vm context compare with the ones here
  const base = { relation: "sfms", rankable: true, epoch: { zRepresentative: 0 }, definitions: { population: "all galaxies", imf: "chabrier03", massDefinition: "total-bound-subhalo", sfrTimescaleMyr: 100, sfrStatistic: "mean", cosmology: { H0: 67.74, Om: 0.3089 } } };
  const mk = (id, source, over = {}, top = {}) => ({ ...base, id, source, ...top, definitions: { ...base.definitions, ...over } });
  const names = { name: r => r.source };
  // 1. a hard difference (which galaxies) is reported with the plain label from compare.js and the curves on each side
  const a = mk("a", "Sim A"), b = mk("b", "Sim B", { population: "star-forming" }), c = mk("c", "Obs C", { population: "all" });
  const h = PC([a, b, c], C, names);
  assert.equal(h.like, false);
  assert.deepEqual(h.hard.map(d => d.key), ["population"], "only the population differs");
  assert.equal(h.hard[0].label, C.KEY_LABEL.population);
  assert.deepEqual(h.hard[0].groups.map(g => [g.value, g.names]), [["all", ["Obs C", "Sim A"]], ["star-forming", ["Sim B"]]], "spelling variants of one population are one group; the other population stands alone");
  assert.match(h.long, /^Not like for like: Which galaxies are included: all \(Obs C, Sim A\) against star-forming \(Sim B\)\./);
  assert.match(h.short[0], /^Not like for like\. Which galaxies are included: all \(Obs C, Sim A\) against star-forming \(Sim B\)\.$/);
  assert.deepEqual(h.soft, [], "no soft difference among these three");
  // 2. the words come from compare.js: changing the label there changes the sentence (nothing is typed here)
  const C2 = { ...C, KEY_LABEL: { ...C.KEY_LABEL, population: "Zzz galaxies" } };
  assert.match(PC([a, b], C2, names).long, /Zzz galaxies: all \(Sim A\) against star-forming \(Sim B\)/);
  // 3. the rules decide what is hard: a key that is not in the hard list of the relation is not reported as hard
  const C3 = { ...C, RULES: { ...C.RULES, sfms: { hard: [], soft: R.soft } } };
  assert.deepEqual(PC([a, b], C3, names).hard, [], "with no hard keys in the rules, nothing is reported as hard");
  // 4. all like for like says so, and names the definitions that were checked
  const same = PC([mk("a", "Sim A"), mk("b", "Sim B", { population: "all" }), mk("c", "Obs C", { population: "All galaxies (PGalF)" })], C, names);
  assert.equal(same.like, true);
  assert.match(same.long, /^All 3 plotted curves are like for like: the definitions that must agree for this relation \(which galaxies are included\) agree, and none of the smaller differences/);
  assert.match(same.short[0], /^All 3 plotted curves are like for like/);
  // 5. soft differences only: the hard definitions agree, the smaller differences are listed with KEY_LABEL
  const soft = PC([a, mk("b", "Sim B", { imf: "kroupa01", massDefinition: "aperture-30pkpc" })], C, names);
  assert.equal(soft.like, false); assert.deepEqual(soft.hard, []);
  assert.deepEqual(soft.soft.map(d => d.key), ["imf", "massDefinition"], "soft keys come in the order of the rules");
  assert.match(soft.long, /Smaller differences remain, left as published: Initial mass function \(IMF\): chabrier03 \(Sim A\) against kroupa01 \(Sim B\)\. Which stars count toward the mass:/);
  assert.ok(!/Not like for like/.test(soft.long));
  assert.match(soft.short.join(" "), /Smaller differences remain: initial mass function \(IMF\); which stars count toward the mass\./);
  assert.match(PC([a, mk("b", "Sim B", { imf: "kroupa01" })], C, { ...names, imfConverted: true }).long, /converted to Chabrier in this plot where the IMF is stated/);
  // 6. an unstated hard definition is not like for like, even when two curves leave it out in the same way
  const un = PC([mk("a", "Sim A", { population: "unspecified" }), mk("b", "Sim B", { population: "unspecified" })], C, names);
  assert.equal(un.like, false); assert.match(un.long, /Which galaxies are included: not stated for Sim A, Sim B/);
  // 7. a curve that is not rankable is named as context only
  const ctxOnly = PC([a, mk("b", "Fig D", {}, { rankable: false })], C, names);
  assert.deepEqual(ctxOnly.context, ["Fig D"]); assert.match(ctxOnly.long, /Context only, not rankable: Fig D\./);
  // 8. duplicates are one curve; one curve has nothing to compare with
  assert.equal(PC([a, a, a], C, names).n, 1); assert.match(PC([a], C, names).long, /nothing to compare/);
  // 9. a relation with no hard keys at all
  const age = { ...base, relation: "age", definitions: { ageWeighting: "mass", imf: "chabrier03", massDefinition: "x", population: "all" } };
  assert.match(PC([{ ...age, id: "x", source: "S1" }, { ...age, id: "y", source: "S2" }], C, names).long, /this relation has no definition that must agree/);
  console.log("logic: figure caveats OK");
}
