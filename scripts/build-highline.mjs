import { withCsp } from "./csp.mjs";
import { parseIndex, splitForExplorer, DATA_DIR } from "./explorer-data.mjs";
import { readFile, writeFile, mkdir, rm } from "node:fs/promises";
const root = new URL("../", import.meta.url);
const tpl = await readFile(new URL("highline/index.html", root), "utf8");
const dataJs = await readFile(new URL("data/curve-index.js", root), "utf8");
// the page embeds a thin index of every record (what it needs to list, count and search them) and fetches each relation's complete records from dist/highline-data/<relation>.json when it first needs them; scripts/explorer-data.mjs says what stays in the index
// the embedded text is one JSON text parsed with JSON.parse, which is several times faster than the JavaScript parser on a large literal
const { SIMHIGHLINE_CURVES: records, SIMHIGHLINE_REGISTRY: registry } = parseIndex(dataJs);
const split = splitForExplorer(records);
const data = JSON.stringify({ SIMHIGHLINE_CURVES: split.light, SIMHIGHLINE_REGISTRY: registry, SIMHIGHLINE_FILES: split.manifest });
await rm(new URL(`dist/${DATA_DIR}/`, root), { recursive: true, force: true });
await mkdir(new URL(`dist/${DATA_DIR}/`, root), { recursive: true });
for (const [rel, f] of split.files) await writeFile(new URL(`dist/${DATA_DIR}/${rel}.json`, root), f.text);
const compare = await readFile(new URL("compare.js", root), "utf8");
const exportLib = await readFile(new URL("export-lib.js", root), "utf8");
const logic = await readFile(new URL("highline/logic.js", root), "utf8");
const release = await readFile(new URL("data/release.json", root), "utf8");
const palette = await readFile(new URL("data/palette.css", root), "utf8");
const notes = await readFile(new URL("data/relation-notes.json", root), "utf8");
const analysis = JSON.parse(await readFile(new URL("data/analysis/definition-budget.json", root), "utf8"));
const sens = JSON.stringify(analysis.sensitivity.summary.map(({ source, relation, key, from, to, epochs, zRange, median_dy, medianRange, max_abs_dy }) => ({ source, relation, key, from, to, epochs, zRange, median: median_dy, medianRange, max: max_abs_dy })));
const audit = JSON.stringify(Object.fromEntries((JSON.parse(await readFile(new URL("data/audit-outcomes.json", root), "utf8")).outcomes || []).map(o => [o.record, { verdict: o.verdict, reviewer: o.reviewer || "anonymous", date: o.date }])));
const safe = s => s.replaceAll("</script", "<\\/script");
// the parametric expressions of the records, compiled by the browser as ordinary script (the page's policy has no eval): one function per distinct (parameter names, expression)
const exprs = new Map();
for (const r of records) {
  const rep = r.representation;
  if (rep.type !== "parametric" || !rep.expression) continue;
  const names = Object.entries(rep.parameters || {}).filter(([, v]) => typeof v === "number").map(([k]) => k);
  if (!names.every(n => /^[A-Za-z_$][\w$]*$/.test(n))) throw new Error(`${r.id}: a parameter name is not an identifier`);
  exprs.set(names.join(",") + "|" + rep.expression, `function(${[...names, "x", "t", "z", "log10"].join(",")}){return ${rep.expression};}`);
}
const exprJs = `window.SIMHIGHLINE_EXPR={${[...exprs].map(([k, f]) => JSON.stringify(k) + ":" + f).join(",")}};\n`;
const html = tpl.replace("/*__PALETTE__*/", () => palette).replace("/*__DATA__*/", () => safe(data)).replace("/*__COMPARE__*/", () => safe(exprJs + compare)).replace("/*__EXPORT__*/", () => safe(exportLib)).replace("/*__LOGIC__*/", () => safe(logic)).replace("/*__RELEASE__*/", () => JSON.stringify(JSON.parse(release))).replace("/*__NOTES__*/", () => JSON.stringify(JSON.parse(notes))).replace("/*__SENS__*/", () => sens).replace("/*__AUDIT__*/", () => audit);
await mkdir(new URL("dist/", root), { recursive: true });
await writeFile(new URL("dist/highline.html", root), withCsp(html));
console.log(`Built dist/highline.html (${(html.length / 1e6).toFixed(2)} MB) and ${split.files.size} relation files in dist/${DATA_DIR}/ (${(split.light.length)} records indexed)`);
