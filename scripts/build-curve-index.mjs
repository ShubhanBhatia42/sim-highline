import { readFile, readdir, writeFile } from "node:fs/promises";

const directory = new URL("../data/curves/", import.meta.url);
const files = (await readdir(directory)).filter(file => file.endsWith(".json")).sort();
const records = (await Promise.all(files.map(async file => JSON.parse(await readFile(new URL(file,directory),"utf8")).records))).flat();
const registry = JSON.parse(await readFile(new URL("../data/simulations.json", import.meta.url), "utf8"));
await writeFile(new URL("../data/curve-index.js", import.meta.url), `window.SIMHIGHLINE_CURVES=${JSON.stringify(records)};\nwindow.SIMHIGHLINE_REGISTRY=${JSON.stringify({families: registry.families, simulations: registry.simulations})};\n`);
console.log(`Built browser index with ${records.length} evidence records`);
