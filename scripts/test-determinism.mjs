// The build is deterministic: building twice from the same inputs gives byte-identical files (so a change in dist/ always comes from a change in the inputs). Rebuilds dist/ twice.
import { spawnSync } from "node:child_process";
import { readdir, readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";

const ROOT = new URL("../", import.meta.url).pathname;
const BUILD = ["scripts/build-static.mjs", "scripts/build-highline.mjs", "scripts/build-site.mjs"];
async function hashTree(dir) {
  const out = {};
  for (const e of await readdir(dir, { withFileTypes: true, recursive: true })) {
    if (!e.isFile()) continue;
    const p = path.join(e.parentPath ?? e.path, e.name);
    out[path.relative(dir, p)] = createHash("sha256").update(await readFile(p)).digest("hex");
  }
  return out;
}
const build = () => { for (const b of BUILD) { const r = spawnSync(process.execPath, [b], { cwd: ROOT, encoding: "utf8" }); if (r.status !== 0) { console.log(r.stderr || r.stdout); process.exit(1); } } };
build(); const a = await hashTree(path.join(ROOT, "dist"));
await new Promise(r => setTimeout(r, 1100)); // a clock that leaks into the output would show after a second
build(); const b = await hashTree(path.join(ROOT, "dist"));
const diff = [...new Set([...Object.keys(a), ...Object.keys(b)])].filter(k => a[k] !== b[k]);
if (diff.length) { console.log("NOT deterministic:\n  " + diff.slice(0, 20).join("\n  ")); process.exit(1); }
console.log(`determinism: ${Object.keys(a).length} files in dist/ are byte-identical across two builds`);
