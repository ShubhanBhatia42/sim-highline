import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import "./build-curve-index.mjs";
import "./report-coverage.mjs";

const root = new URL("../", import.meta.url);
const dist = new URL("../dist/", import.meta.url);

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });
await cp(new URL("sim_highline.py", root), new URL("sim_highline.py", dist));
await cp(new URL("../data/", import.meta.url), new URL("../dist/data/", import.meta.url), { recursive: true, filter: src => !/\/data\/raw(\/|$)/.test(src) });
await writeFile(new URL("index.html", dist), `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>sim-highline</title><meta http-equiv="refresh" content="0; url=site/index.html"><link rel="canonical" href="site/index.html"></head><body><p><a href="site/index.html">sim-highline: galaxy scaling relations from simulations and observations</a></p></body></html>\n`);
try { await cp(new URL("../.openai/", import.meta.url), new URL("../dist/.openai/", import.meta.url), { recursive: true }); } catch (e) { if (e.code !== "ENOENT") throw e; }
console.log("Built sim-highline static output in dist/");
