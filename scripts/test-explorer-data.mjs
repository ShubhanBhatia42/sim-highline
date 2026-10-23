// The Explorer loads its data one relation at a time (scripts/explorer-data.mjs, docs/ARCHITECTURE.md). This checks the built output against the index the rest of the project reads:
//   - every relation in data/curve-index.js has its file in dist/highline-data/, and no file is left over from a relation that is gone;
//   - each file holds exactly the records of that relation, in the index's order, with every field and every key in the index's order (so a visitor who opens the relation gets what the index says);
//   - the manifest embedded in dist/highline.html (record count and content hash per file) describes the files that are there;
//   - the embedded index lists every drawable record once, in the index's order, and nothing in an embedded entry disagrees with the full record;
//   - the embedded index is thin: it carries no points, parameters, distributions, definitions (except the metallicity pair the page uses to split that relation), selection or notes.
// The last part feeds the same checks a missing file, a changed number, a lost record, a swapped pair and a stale manifest, and fails if any of them is let through.
// Needs `node scripts/build-static.mjs && node scripts/build-highline.mjs` first.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, readdir } from "node:fs/promises";
import { parseIndex, DATA_DIR, drawable, lightRecord } from "./explorer-data.mjs";

const root = new URL("../", import.meta.url);
const { SIMHIGHLINE_CURVES: records } = parseIndex(await readFile(new URL("data/curve-index.js", root), "utf8"));
const html = await readFile(new URL("dist/highline.html", root), "utf8");
const m = html.match(/<script type="application\/json" id="curves-data">([\s\S]*?)<\/script>/);
assert.ok(m, "dist/highline.html has no embedded index (id=curves-data)");
const { SIMHIGHLINE_CURVES: light, SIMHIGHLINE_FILES: manifest } = JSON.parse(m[1]);
assert.ok(Array.isArray(light) && manifest && manifest.files, "the embedded index or its file manifest is missing");
assert.equal(manifest.dir, DATA_DIR, "the manifest names a different folder than the build writes");

const byRel = new Map();
for (const r of records) (byRel.get(r.relation) || byRel.set(r.relation, []).get(r.relation)).push(r);
const relNames = [...byRel.keys()];
const sha12 = text => createHash("sha256").update(text).digest("hex").slice(0, 12);

// the checks, as functions so that the last section can show they notice damage
function checkListing(names, rels, man) {
  assert.deepEqual([...names].sort(), [...rels].sort().map(k => `${k}.json`), `${DATA_DIR}/ must hold one file per relation in the index, and nothing else`);
  assert.deepEqual(Object.keys(man).sort(), [...rels].sort(), "the manifest in the page must list every relation in the index");
}
function checkFile(rel, text, want, entry) {
  const got = JSON.parse(text);
  assert.ok(Array.isArray(got), `${rel}: the file is not a list of records`);
  assert.equal(got.length, want.length, `${rel}: the file has ${got.length} records, the index ${want.length}`);
  for (let i = 0; i < want.length; i++) {
    assert.equal(got[i].id, want[i].id, `${rel}: record ${i} is ${got[i].id} in the file and ${want[i].id} in the index`);
    assert.equal(JSON.stringify(got[i]), JSON.stringify(want[i]), `${rel}: ${want[i].id} differs from the index`);
  }
  assert.deepEqual(entry, { v: sha12(text), n: want.length }, `${rel}: the manifest does not describe the file (record count or content hash)`);
}

// 1. the files
const onDisk = await readdir(new URL(`dist/${DATA_DIR}/`, root));
checkListing(onDisk, relNames, manifest.files);
const texts = new Map();
for (const [rel, want] of byRel) {
  const text = await readFile(new URL(`dist/${DATA_DIR}/${rel}.json`, root), "utf8");
  texts.set(rel, text);
  checkFile(rel, text, want, manifest.files[rel]);
}

// 2. the embedded index
const drawn = records.filter(drawable);
assert.equal(light.length, drawn.length, "the embedded index must list every drawable record once");
const isSubset = (a, b) => a === true && b ? true : a && typeof a === "object" && !Array.isArray(a) ? Object.entries(a).every(([k, v]) => b && isSubset(v, b[k])) : JSON.stringify(a) === JSON.stringify(b);
const allowed = new Set(["id", "source", "run", "kind", "relation", "epoch", "representation", "provenance", "rankable", "definitions", "axes"]);
for (let i = 0; i < drawn.length; i++) {
  const e = light[i];
  assert.deepEqual(e, JSON.parse(JSON.stringify(lightRecord(drawn[i]))), `${drawn[i].id}: the embedded entry is not what lightRecord makes of the record (or is out of order)`);
  assert.ok(isSubset(e, drawn[i]), `${drawn[i].id}: the embedded entry says something the record does not`);
  for (const k of Object.keys(e)) assert.ok(allowed.has(k), `${e.id}: the embedded entry carries "${k}", which belongs in the relation file`);
  assert.ok(!("points" in e.representation) && !("parameters" in e.representation) && typeof e.representation.distribution !== "object", `${e.id}: the embedded entry carries plotted data`);
  if (e.relation !== "mzr") assert.ok(!("definitions" in e) && !("axes" in e), `${e.id}: definitions and axes belong in the relation file`);
}
assert.ok(m[1].length < 1.2e6, `the embedded index is ${(m[1].length / 1e6).toFixed(2)} MB; it was cut down from 6 MB so that the first page load stays small`);

// 3. the checks must notice damage
const want = byRel.get("gsmf"), text = texts.get("gsmf"), entry = manifest.files.gsmf;
const damaged = (fn) => { const copy = JSON.parse(text); fn(copy); return JSON.stringify(copy); };
const mustFail = (label, fn) => { let failed = false; try { fn(); } catch (e) { if (e.name !== "AssertionError") throw e; failed = true; } assert.ok(failed, `self-check: the test let this through: ${label}`); };
mustFail("a file missing from dist/highline-data/", () => checkListing(onDisk.filter(n => n !== "gsmf.json"), relNames, manifest.files));
mustFail("a file left over from a relation that is gone", () => checkListing([...onDisk, "old.json"], relNames, manifest.files));
mustFail("a relation missing from the manifest", () => { const { gsmf, ...rest } = manifest.files; checkListing(onDisk, byRel.keys(), rest); });
mustFail("one number changed in the last digit", () => { const t = damaged(c => { const r = c.find(x => x.representation.points); r.representation.points[0].y += 1e-9; }); checkFile("gsmf", t, want, { v: sha12(t), n: want.length }); });
mustFail("a record lost", () => { const t = damaged(c => c.pop()); checkFile("gsmf", t, want, { v: sha12(t), n: want.length - 1 }); });
mustFail("two records swapped", () => { const t = damaged(c => { [c[0], c[1]] = [c[1], c[0]]; }); checkFile("gsmf", t, want, { v: sha12(t), n: want.length }); });
mustFail("keys of a record in another order", () => { const t = damaged(c => { const { id, ...rest } = c[0]; c[0] = { ...rest, id }; }); checkFile("gsmf", t, want, { v: sha12(t), n: want.length }); });
mustFail("a manifest hash that does not belong to the file", () => checkFile("gsmf", text, want, { ...entry, v: "000000000000" }));
mustFail("a manifest count that does not match", () => checkFile("gsmf", text, want, { ...entry, n: entry.n + 1 }));

console.log(`Explorer data valid: ${byRel.size} relation files hold the ${records.length} records of the index exactly (9 kinds of damage are caught); the embedded index lists ${light.length} of them in ${(m[1].length / 1e3).toFixed(0)} kB`);
