// The optional page-count beacon is off, and nothing about it reaches a built page while it is off; if it were on, it would send the page path only and the privacy sentence would have to say so.
import assert from "node:assert/strict";
import fs from "node:fs";
import { spawnSync } from "node:child_process";

const ROOT = new URL("../", import.meta.url).pathname;
const cfg = JSON.parse(fs.readFileSync(ROOT + "data/usage-counts.json", "utf8"));
const pages = [ROOT + "dist/highline.html", ...fs.readdirSync(ROOT + "dist/site").filter(f => f.endsWith(".html")).map(f => ROOT + "dist/site/" + f)];
for (const p of pages) {
  const html = fs.readFileSync(p, "utf8");
  if (!cfg.enabled) {
    assert.ok(!/sendBeacon/.test(html), `${p}: no beacon while usage counts are off`);
    assert.ok(/connect-src 'self'[;"]/.test(html) || !/connect-src/.test(html), `${p}: connect-src stays 'self'`);
  }
}
const proj = fs.readFileSync(ROOT + "docs/PROJECT.md", "utf8");
if (cfg.enabled) assert.ok(/page path/i.test(proj), "PROJECT.md says what the beacon sends when it is on");
else assert.ok(/will not collect user data/.test(proj), "PROJECT.md says nothing is collected while the beacon is off");
// the switch works: build one test page with the beacon on, in a throwaway process
const r = spawnSync("node", ["--input-type=module", "-e", `
import fs from "node:fs";
const real = fs.readFileSync(new URL("file://${ROOT}data/usage-counts.json"), "utf8");
fs.writeFileSync("${ROOT}data/usage-counts.json", JSON.stringify({enabled:true,endpoint:"https://counts.example.org/hit"}));
try { const { withCsp } = await import("file://${ROOT}scripts/csp.mjs?x=" + Date.now()); const out = withCsp('<meta charset="utf-8"><body>x</body>'); console.log(JSON.stringify({ beacon: /sendBeacon/.test(out), connect: /connect-src 'self' https:\\/\\/counts\\.example\\.org/.test(out), dnt: /doNotTrack/.test(out), onlyPath: /\\{path:location\\.pathname\\}/.test(out) })); } finally { fs.writeFileSync("${ROOT}data/usage-counts.json", real); }
`], { encoding: "utf8" });
const res = JSON.parse(r.stdout.trim().split("\n").pop());
assert.deepEqual(res, { beacon: true, connect: true, dnt: true, onlyPath: true }, r.stderr);
assert.deepEqual(JSON.parse(fs.readFileSync(ROOT + "data/usage-counts.json", "utf8")), cfg, "the configuration file is back as it was");
console.log(`usage counts: ${cfg.enabled ? "ON" : "off"}; with the switch on, a page sends its path only, honours Do Not Track and the policy allows only that address`);
