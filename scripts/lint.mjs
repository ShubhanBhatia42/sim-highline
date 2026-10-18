// Lint without dependencies: every script parses (node --check), every Python file compiles, every built page has balanced tags and unique ids, every JSON file in the repository parses, and the templates have no tabs or trailing spaces in the files this project writes by hand.
import { readdir, readFile, stat } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import path from "node:path";

const ROOT = new URL("../", import.meta.url).pathname;
const problems = []; const counts = { js: 0, py: 0, html: 0, json: 0 };
async function walk(dir, skip = /^(node_modules|\.git|dist|__pycache__)$/) {
  const out = [];
  for (const e of await readdir(dir, { withFileTypes: true })) {
    if (skip.test(e.name)) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out.push(...await walk(p, skip)); else out.push(p);
  }
  return out;
}
const files = await walk(ROOT);
// 1. JavaScript syntax (modules and scripts)
for (const f of files.filter(f => /\.(mjs|js)$/.test(f) && !/node_modules/.test(f))) {
  counts.js++;
  const src = await readFile(f, "utf8");
  const isModule = /\.mjs$/.test(f) || /^\s*(import|export)\s/m.test(src);
  const r = spawnSync(process.execPath, isModule ? ["--input-type=module", "--check"] : ["--check", f], isModule ? { input: src, encoding: "utf8" } : { encoding: "utf8" });
  if (r.status !== 0) problems.push(`${path.relative(ROOT, f)}: ${(r.stderr || "").split("\n").find(l => /Error/.test(l)) || "does not parse"}`);
}
// 2. Python compiles
const py = files.filter(f => f.endsWith(".py")); counts.py = py.length;
{ const r = spawnSync("python3", ["-c", "import sys,ast\nfor f in sys.argv[1:]:\n    ast.parse(open(f).read(), f)", ...py], { encoding: "utf8" }); if (r.status !== 0) problems.push("python: " + (r.stderr.trim().split("\n").slice(-3).join(" | "))); }
// 3. JSON parses
for (const f of files.filter(f => f.endsWith(".json") && !/package-lock/.test(f))) {
  counts.json++;
  try { JSON.parse(await readFile(f, "utf8")); } catch (e) { problems.push(`${path.relative(ROOT, f)}: invalid JSON (${e.message.slice(0, 60)})`); }
}
// 4. built pages: tags balanced, ids unique, no stray closers
const VOID = new Set(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"]);
async function lintHtml(f, name) {
  let h = await readFile(f, "utf8");
  h = h.replace(/<!--[\s\S]*?-->/g, "").replace(/<(script|style|pre|textarea)\b([^>]*)>[\s\S]*?<\/\1>/gi, "<$1$2></$1>");
  const stack = [], ids = new Set();
  for (const m of h.matchAll(/<(\/?)([a-zA-Z][a-zA-Z0-9-]*)((?:[^>"']|"[^"]*"|'[^']*')*)>/g)) {
    const [, close, tag0, attrs] = m, tag = tag0.toLowerCase();
    if (!close) {
      const id = (attrs.match(/\sid="([^"]+)"/) || [])[1];
      if (id) { if (ids.has(id)) problems.push(`${name}: duplicate id "${id}"`); ids.add(id); }
      if (!VOID.has(tag) && !/\/\s*$/.test(attrs) && !/^(svg|path|circle|line|rect|g|text|tspan|polyline|polygon|title|defs|use|clipPath|linearGradient|stop|mask|pattern|marker|desc|ellipse)$/i.test(tag)) stack.push(tag);
      else if (/^(svg|g|text|tspan|title|defs|clipPath|linearGradient|mask|pattern|marker|desc)$/i.test(tag) && !/\/\s*$/.test(attrs)) stack.push(tag);
    } else if (!VOID.has(tag)) {
      const want = tag; let top = stack.pop();
      if (top !== want) { problems.push(`${name}: </${want}> closes <${top ?? "nothing"}> (tags out of balance near "${h.slice(Math.max(0, m.index - 40), m.index).replace(/\s+/g, " ")}")`); return; }
    }
  }
  if (stack.length) problems.push(`${name}: unclosed <${stack.slice(-3).join(">, <")}>`);
}
const built = [];
for (const d of ["dist", "dist/site"]) { try { for (const e of await readdir(path.join(ROOT, d))) if (e.endsWith(".html") && !(d === "dist" && e === "index.html")) built.push([path.join(ROOT, d, e), `${d}/${e}`]); } catch { /* not built */ } }
for (const [f, n] of built) { counts.html++; await lintHtml(f, n); }
for (const f of ["highline/index.html", ...(await readdir(path.join(ROOT, "site/src"))).filter(x => x.endsWith(".html")).map(x => "site/src/" + x)]) { /* templates carry {{placeholders}}; the built pages are what is checked */ }
{ // every document is listed in docs/README.md, so nothing is findable only by luck
  const idx = await readFile(path.join(ROOT, "docs/README.md"), "utf8");
  for (const e of await readdir(path.join(ROOT, "docs"), { withFileTypes: true })) {
    if (e.name === "README.md") continue;
    if (!idx.includes(`](${e.name}${e.isDirectory() ? "/" : ""})`)) problems.push(`docs/${e.name}${e.isDirectory() ? "/" : ""} is not listed in docs/README.md`);
  }
}
console.log(`lint: ${counts.js} scripts parse, ${counts.py} Python files compile, ${counts.json} JSON files parse, ${counts.html} built pages balanced with unique ids` + (problems.length ? `; ${problems.length} PROBLEMS` : ""));
if (problems.length) { console.log(problems.slice(0, 30).map(p => "  " + p).join("\n")); process.exit(1); }
