// Realistic messy inputs for "check your own run": tab and space separated, comments, semicolons with decimal commas, a byte-order mark and Windows line endings, linear values, a units row and missing values.
import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import "../highline/logic.js";
const L = globalThis.SimHighlineLogic;
const dir = new URL("../tests/user-curves/", import.meta.url);
const read = async f => readFile(new URL(f, dir), "utf8");
const expect = {
  "1-linear-tab-comments.txt": { linear: true, n: 8, xlo: 8, xhi: 11.5 },
  "2-semicolon-decimal-comma.csv": { linear: false, n: 7, xlo: 8, xhi: 11, err: true },
  "3-bom-crlf-header.csv": { linear: false, n: 7, xlo: 8, xhi: 11, err: true },
  "4-sfr-linear-whitespace.txt": { linear: true, n: 5, xlo: 9, xhi: 11, header: true },
  "5-units-row-and-nan.csv": { linear: false, n: 6, xlo: 8, xhi: 11, skipped: 2 },
};
let n = 0;
for (const f of (await readdir(dir)).sort()) {
  const e = expect[f]; if (!e) continue;
  const r = L.parseUserCurve(await read(f), { linear: e.linear });
  assert.equal(r.pts.length, e.n, `${f}: ${r.pts.length} points read, expected ${e.n}`);
  if (e.linear) assert.ok(r.pts.every(p => Number.isFinite(p.y)), `${f}: linear values converted to logs`);
  assert.ok(Math.abs(r.pts[0].x - e.xlo) < 1e-9 || e.linear, `${f}: first x`);
  if (e.err) assert.ok(r.pts.every(p => Number.isFinite(p.lo) && Number.isFinite(p.hi)), `${f}: error column used`);
  if (e.skipped !== undefined) assert.equal(r.skipped, e.skipped, `${f}: skipped rows`);
  const d = L.inspectUserCurve(await read(f), { linear: e.linear });
  assert.ok(d.summary.length > 10, `${f}: a summary of what was understood`);
  n++;
}
// diagnostics that must catch common mistakes
const lin = L.inspectUserCurve(await read("1-linear-tab-comments.txt"), { linear: false });
assert.ok(lin.warnings.some(w => /linear/i.test(w)), "linear values with 'log' ticked are noticed");
const logs = L.inspectUserCurve(await read("3-bom-crlf-header.csv"), { linear: true });
assert.ok(logs.warnings.some(w => /already|log/i.test(w)), "log values with 'linear' ticked are noticed");
const far = L.inspectUserCurve(await read("3-bom-crlf-header.csv"), { linear: false }, { xlo: 0.0, xhi: 1.5, ylo: 20, yhi: 30 });
assert.ok(far.warnings.some(w => /overlap|range/i.test(w)), "a curve far from every published curve is noticed");
const empty = L.inspectUserCurve("", {});
assert.equal(empty.points, 0); assert.ok(/no numeric/i.test(empty.summary));
console.log(`user curves: ${n} realistic inputs parsed, 4 diagnostics checked`);
