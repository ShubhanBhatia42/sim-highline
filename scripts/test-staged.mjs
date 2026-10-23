// The records promoted from data/staged/ into data/curves/ are still identical to their staged originals (apart from the summary and points that scripts/derive-distributions.mjs adds), and nothing staged is also in the dataset by accident.
import assert from "node:assert/strict";
import fs from "node:fs";

const ROOT = new URL("../", import.meta.url).pathname;
const promoted = JSON.parse(fs.readFileSync(ROOT + "data/staged/promoted.json", "utf8")).promoted;
const staged = new Map();
for (const f of fs.readdirSync(ROOT + "data/staged").filter(f => f.endsWith(".json") && !f.startsWith("promoted") && !f.startsWith("polygons"))) for (const r of JSON.parse(fs.readFileSync(ROOT + "data/staged/" + f, "utf8")).records) staged.set(r.id, r);
const curves = new Map();
for (const f of fs.readdirSync(ROOT + "data/curves").filter(f => f.endsWith(".json"))) for (const r of JSON.parse(fs.readFileSync(ROOT + "data/curves/" + f, "utf8")).records) curves.set(r.id, r);
for (const id of promoted) {
  const a = staged.get(id), b = curves.get(id);
  assert.ok(a && b, `${id} is staged and in the dataset`);
  const strip = r => { const c = JSON.parse(JSON.stringify(r)); const rep = c.representation; if (rep.distribution) { delete rep.distribution.summary; delete rep.distribution.thresholds; } delete rep.points; delete rep.connect; delete rep.intervalKind; delete rep.type; delete rep.distribution?.weighting; delete c.selection?.warning; delete c.domain; delete c.scatter; delete c.provenance?.terms; delete c.provenance?.definitionFills; delete c.definitions?.population; return c; };
  const sa = strip(a), sb = strip(b);
  assert.deepEqual(sb.representation?.distribution?.counts, a.representation.counts ?? a.representation.distribution?.counts, `${id}: counts are the staged counts`);
  assert.equal(b.provenance.checksumSha256, a.provenance.checksumSha256, `${id}: same source checksum`);
}
for (const id of staged.keys()) if (!promoted.includes(id)) assert.ok(!curves.has(id), `${id} is staged but not promoted, and also in the dataset`);
console.log(`staged records: ${promoted.length} promoted records match their staged originals; ${staged.size - promoted.length} withheld records are not in the dataset`);
