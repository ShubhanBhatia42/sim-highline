import { readFile } from "node:fs/promises";
import vm from "node:vm";
// Prints the units the website's SimHighlineLogic.primaryUnits picks from a list of records read on stdin (JSON array of {source, run, epoch, provenance}).
const root = new URL("../", import.meta.url);
const ctx = { globalThis: {} };
ctx.window = ctx.globalThis;
vm.runInNewContext(await readFile(new URL("highline/logic.js", root), "utf8"), ctx);
const L = ctx.globalThis.SimHighlineLogic;
let input = "";
for await (const chunk of process.stdin) input += chunk;
console.log(JSON.stringify([...L.primaryUnits(JSON.parse(input))].sort()));
