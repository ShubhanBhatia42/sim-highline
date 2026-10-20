// Tests of the submission checker: the template and a valid fixture pass; each broken fixture fails for the stated reason; a warning-only fixture passes with warnings; the record built from the valid fixture passes the dataset's own validator together with all existing records.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const root = new URL("../", import.meta.url).pathname;
const run = (...args) => spawnSync("node", [path.join(root, "scripts/submission.mjs"), ...args], { encoding: "utf8", cwd: root });
for (const ok of ["submissions/_template", "tests/submissions/valid-gsmf", "tests/submissions/warn-units"]) {
  const r = run("check", ok);
  assert.equal(r.status, 0, `${ok} should pass:\n${r.stdout}${r.stderr}`);
}
assert.match(run("check", "tests/submissions/warn-units").stdout, /outside the usual range/, "implausible values are warned about");
const expect = { "bad-nonmonotonic": /x must increase/, "bad-missing-hard": /densityFrame is required/, "bad-http": /https address/, "bad-digitized": /not accepted as submissions/, "bad-no-contact": /contact\.name is required/, "bad-duplicate": /already exists/ };
for (const [name, why] of Object.entries(expect)) {
  const r = run("check", `tests/submissions/${name}`);
  assert.equal(r.status, 1, `${name} should fail`);
  assert.match(r.stdout, why, `${name}: wrong reason\n${r.stdout}`);
}
const rec = JSON.parse(run("record", "tests/submissions/valid-gsmf").stdout);
assert.equal(rec.records.length, 1);
const r0 = rec.records[0];
assert.equal(r0.representation.points.length, 5);
assert.equal(r0.provenance.tier, "published-table");
assert.equal(r0.definitions.densityFrame, "comoving");
assert.ok(r0.domain.xMin < r0.domain.xMax);
const tmp = path.join(await mkdtemp(path.join(tmpdir(), "subtest-")), "r.json");
await writeFile(tmp, JSON.stringify(rec));
const v = spawnSync("node", [path.join(root, "scripts/validate-curves.mjs"), tmp], { encoding: "utf8", cwd: root });
assert.equal(v.status, 0, `the dataset validator accepts the built record:\n${v.stdout}${v.stderr}`);
console.log("submission checker: ok (template, valid fixture, warning fixture, 6 broken fixtures, built record validates with the dataset)");
