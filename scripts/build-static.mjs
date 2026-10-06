import { cp, mkdir, rm } from "node:fs/promises";
import "./build-curve-index.mjs";
import "./report-coverage.mjs";

const root = new URL("../", import.meta.url);
const dist = new URL("../dist/", import.meta.url);

await rm(dist, { recursive: true, force: true });
await mkdir(dist, { recursive: true });

for (const file of ["index.html", "styles.css", "compare.js", "app.js", "views.js", "export-lib.js", "sim_highline.py"]) {
  await cp(new URL(file, root), new URL(file, dist));
}

await cp(new URL("../data/", import.meta.url), new URL("../dist/data/", import.meta.url), { recursive: true });
await cp(new URL("../.openai/", import.meta.url), new URL("../dist/.openai/", import.meta.url), { recursive: true });
console.log("Built sim-highline static output in dist/");
