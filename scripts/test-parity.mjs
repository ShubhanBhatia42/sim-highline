// The dials page's own JavaScript evaluation of the emulators gives the numbers of the full analysis emulators (tests/parity/emulator-reference.json, from scripts/make_parity_reference.py) at 24 dial settings, to the six significant digits the coefficients are stored in.
import assert from "node:assert/strict";
import http from "node:http";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { launchBrowser } from "./browser-options.mjs";

const DIST = new URL("../dist/", import.meta.url).pathname;
const ref = JSON.parse(await readFile(new URL("../tests/parity/emulator-reference.json", import.meta.url), "utf8"));
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".css": "text/css" };
const server = http.createServer(async (req, res) => { const p = decodeURIComponent(new URL(req.url, "http://x").pathname); try { const f = path.join(DIST, p), b = await readFile(f); res.writeHead(200, { "content-type": TYPES[path.extname(f)] || "application/octet-stream" }); res.end(b); } catch { res.writeHead(404); res.end(); } });
await new Promise(r => server.listen(0, "127.0.0.1", r));
const browser = await launchBrowser(); const page = await browser.newPage();
await page.goto(`http://127.0.0.1:${server.address().port}/site/retune.html`); await page.waitForSelector(".rt-panel");
let worst = 0, n = 0;
for (const code of ["IllustrisTNG", "SIMBA"]) {
  const got = await page.evaluate(([c, pts]) => pts.map(a => document.getElementById("retune").__rt.predict(c, a)), [code, ref.points]);
  ref.predictions[code].forEach((want, i) => want.forEach((w, j) => {
    const g = got[i][j];
    if (w === null) assert.ok(Number.isNaN(g), `${code} point ${i} output ${j}: expected undefined, got ${g}`);
    else { const d = Math.abs(g - w); assert.ok(d < 2e-4, `${code} point ${i} output ${j}: ${g} against ${w}`); worst = Math.max(worst, d); n++; }
  }));
}
await browser.close(); server.close();
console.log(`parity: the page's emulators agree with the analysis' at ${ref.points.length} dial settings x 186 outputs x 2 codes (${n} numbers, largest difference ${worst.toExponential(1)})`);
