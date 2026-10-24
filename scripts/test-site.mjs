import assert from "node:assert/strict";
import { readFile, access } from "node:fs/promises";
import { createHash } from "node:crypto";
const root = new URL("../dist/", import.meta.url);
const manifest = JSON.parse(await readFile(new URL("../data/export/sim-highline-manifest.json", import.meta.url), "utf8"));
const release = JSON.parse(await readFile(new URL("../data/release.json", import.meta.url), "utf8"));
const PAGES = ["index", "studies", "study-definitions", "study-harmonization", "study-sfh", "study-joint", "study-shape", "seeding", "retune", "data", "methods", "sources", "glossary", "faq", "changes", "quality", "summary"];
const html = {};
for (const page of [...PAGES, "findings"]) {
  const h = html[page] = await readFile(new URL(`site/${page}.html`, root), "utf8");
  assert(!/\{\{|__CSS__/.test(h), `${page}: unreplaced placeholder`);
  assert(h.includes(`${manifest.version}`), `${page}: version missing`);
  for (const m of h.matchAll(/(?:href|src)="((?:\.\.\/|)[^":#]+)(?:#[^"]*)?"/g)) {
    const link = m[1];
    if (/^https?:|^mailto:/.test(link)) continue;
    await access(new URL(link, new URL(`site/${page}.html`, root))).catch(() => assert.fail(`${page}: broken link ${link}`));
  }
  assert(/<title>[^<]{10,}<\/title>/.test(h) && /name="description"/.test(h), `${page}: title or description missing`);
  assert((h.match(/<h1>/g) || []).length === 1, `${page}: exactly one h1`);
  // in-page anchors must exist
  for (const m of h.matchAll(/href="#([^"]+)"/g)) assert(h.includes(`id="${m[1]}"`), `${page}: anchor #${m[1]} has no target`);
  assert(h.includes('<a class="mark" href="index.html" aria-label="sim-highline home">sim-highline</a>'), `${page}: wordmark links home`);
  assert(h.includes("Michroma") === false && h.includes("Jost") === false, `${page}: old fonts must be gone`);
  assert(h.includes('<nav class="menu" aria-label="Main">') && h.includes('href="../highline.html">Explorer</a>') && h.includes('href="methods.html"'), `${page}: main navigation missing`);
  assert(h.includes(`v${release.version} · doi`), `${page}: version and DOI chip missing`);
  assert(!/concord/i.test(h.replace(/concordance/gi, "")), `${page}: no old project name`);
  assert(/<main id="main"/.test(h) && /class="skip"/.test(h), `${page}: landmark and skip link`);
  // sharing: a title, a description and a preview image that exists, at the right size
  const og = k => (h.match(new RegExp(`<meta property="og:${k}" content="([^"]+)"`)) || [])[1];
  assert(og("title") && og("description") && og("image"), `${page}: share title, description and image required`);
  assert(/^https:\/\/shubhanbhatia42\.github\.io\/sim-highline\/site\/og-[a-z-]+\.png$/.test(og("image")), `${page}: share image URL (${og("image")})`);
  await access(new URL(`site/${og("image").split("/site/")[1]}`, root)).catch(() => assert.fail(`${page}: share image missing from the build`));
  assert(h.includes('name="twitter:card" content="summary_large_image"'), `${page}: card type`);
  assert(og("description").length >= 50 && og("description").length <= 300, `${page}: share description length ${og("description").length}`);
}
// the preview images are PNGs of the size the card says
for (const f of ["default", "explorer", "retune", "study-joint"]) {
  const b = await readFile(new URL(`site/og-${f}.png`, root)); assert(b.subarray(1, 4).toString() === "PNG" && b.readUInt32BE(16) === 1200 && b.readUInt32BE(20) === 630, `og-${f}.png must be a 1200 x 630 PNG`);
}
// the plain-words paragraph of the joint study states which properties are structural alone and how many are removable or borderline: it must match the saved result
{
  const R = JSON.parse(await readFile(new URL("../data/analysis/joint-reachability.json", import.meta.url), "utf8")), J2 = R.verdicts.J2;
  const by = v => Object.keys(J2).filter(f => J2[f] === v).sort();
  assert.deepEqual(by("structural"), ["bhocc", "mzr"], "plain words name black hole occupation and gas metallicity as the structural ones");
  assert.equal(by("removable").length, 6, "plain words say six are removable"); assert.equal(by("unresolved").length, 3, "plain words say three are borderline");
  const plain = html["study-joint"].match(/<div class="plain">([\s\S]*?)<\/div>/)[1];
  assert(plain.includes(`${R.point.all.D.toFixed(1)} noise units`), "plain words quote the joint distance");
  const zJ = [...new Set(Object.values(R.meta.blocks).filter(b => b.family !== "hmf").map(b => b.z))].sort((a, b) => a - b);
  assert(html["study-joint"].includes(`z = ${zJ[0]} to ${zJ[zJ.length - 1]}`) && html.studies.includes(`z = ${zJ[0]} to ${zJ[zJ.length - 1]}`), "the redshift range in the abstracts is the range of the blocks in the saved result");
  assert(/Not reviewed by anyone outside/.test(html.methods) && /Not reviewed by any outside expert/.test(html.index) && !/independent review/i.test(html["study-joint"] + html["study-sfh"] + html.studies), "the pages say no outside expert has reviewed it and do not call the protocol reviews independent");
}
// structured dataset metadata on the front and data pages: valid JSON, the fields dataset search needs, and every download it lists exists in the build
for (const page of ["index", "data"]) {
  const m = html[page].match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/); assert(m, `${page}: dataset metadata missing`);
  const d = JSON.parse(m[1]);
  assert(d["@type"] === "Dataset" && d.name && d.description.length > 80 && d.license && d.identifier.includes(release.doi) && [].concat(d.creator)[0].name && d.version === release.version, `${page}: dataset metadata fields`);
  assert(d.distribution.length >= 5, `${page}: downloads listed`);
  for (const x of d.distribution) await access(new URL(x.contentUrl.replace("https://shubhanbhatia42.github.io/sim-highline/", ""), root)).catch(() => assert.fail(`${page}: listed download ${x.contentUrl} is not in the build`));
}
// the page that explains the black hole seeding difference: quotations, numbers and links all come from saved files, and the page says what it is
{
  const SRC = JSON.parse(await readFile(new URL("../data/seeding-sources.json", import.meta.url), "utf8")), page = html.seeding;
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  assert(SRC.quotes.length >= 6 && SRC.repository.length >= 2, "seeding: sources registry too small");
  for (const q of SRC.quotes) {
    assert(SRC.papers[q.paper] && /^\d{4}\.\d{4,5}$/.test(SRC.papers[q.paper].arxiv) && /^[0-9a-f]{64}$/.test(SRC.papers[q.paper].eprintSha256) && q.where && q.text.length > 5 && q.latex.length > 5, `seeding: quote ${q.id} lacks its paper, place or source text`);
    assert(page.includes(esc(q.text)), `seeding: the quotation ${q.id} is missing from the page`);
    assert(page.includes(`href="https://arxiv.org/abs/${SRC.papers[q.paper].arxiv}"`), `seeding: no link to arXiv:${SRC.papers[q.paper].arxiv}`);
  }
  for (const q of SRC.repository) {
    assert((await readFile(new URL(`../${q.file}`, import.meta.url), "utf8")).includes(q.text), `seeding: the quotation ${q.id} is not word for word in ${q.file}`);
    assert(page.includes(esc(q.text)), `seeding: the quotation ${q.id} is missing from the page`);
  }
  // numbers: re-derived here from the saved results, so a page that disagrees with them fails
  const R = JSON.parse(await readFile(new URL("../data/analysis/joint-reachability.json", import.meta.url), "utf8")), CG = JSON.parse(await readFile(new URL("../data/ensembles/camels-galaxies.json", import.meta.url), "utf8"));
  const f1 = v => v.toFixed(1), mean = a => a.reduce((t, v) => t + v, 0) / a.length;
  const cv = code => { const v = Object.values(CG.suites[code].CV).map(s => s.snaps["090"].values.bhocc[0]).filter(x => x != null); return mean(v); };
  assert(page.includes(`${Math.round(100 * cv("IllustrisTNG"))}% of IllustrisTNG galaxies in the lowest mass bin hold a black hole and ${Math.round(100 * cv("SIMBA"))}% of SIMBA galaxies do`), "seeding: lowest-bin occupation does not match the catalogues");
  for (const [label, v] of [["Without black hole occupation the all-at-once distance is", R.sensitivity.S7a_no_bhocc.D], ["without occupation and black hole mass it is", R.sensitivity.S7b_no_bhocc_no_bhms.D], ["The codes stay", R.splits.all.between.p50]]) assert(page.includes(`${label} ${f1(v)}`), `seeding: "${label}" must be followed by ${f1(v)}`);
  assert(page.includes(`takes the all-at-once distance from ${f1(R.splits.all.between.p50)} to ${f1(R.sensitivity.S8_no_two_lowest_mass_bins.D)}`), "seeding: the two-lowest-bins sensitivity differs from the saved result");
  const nRem = Object.entries(R.verdicts.J2).filter(([, v]) => v === "removable").length;
  assert(page.includes(`can close ${nRem} of the ${Object.keys(R.verdicts.J2).length} properties`), "seeding: count of removable properties differs from the saved verdicts");
  assert((page.match(/<tr><td>[^<]+<\/td><td>(structural|removable|unresolved)<\/td>/g) || []).length === Object.keys(R.verdicts.J2).length, "seeding: one table row per property");
  const bhRows = page.match(/<tr><td>Black hole[^<]*<\/td><td>[a-z]+<\/td><td class="n">[\d.]+<\/td><td class="n">\d+%<\/td><td>yes<\/td>/g) || [];
  assert(bhRows.length === 2, "seeding: the two properties that compare seeding rules are marked");
  // what the page says it is, and what it must not say
  assert(/No outside expert has reviewed/.test(page) && /internal result/.test(page) && /does not claim that the result, or the explanation, is new/.test(page), "seeding: must say it is an internal, unreviewed explanation and makes no novelty claim");
  assert(!/\b(novel|first[- ]ever|first to|unprecedented|ground-?breaking|new method|new approach)\b/i.test(page), "seeding: novelty wording");
  assert(!/\bclaude\b|anthropic|\bAI\b|language model|\bGPT\b/i.test(page), "seeding: no mention of AI assistants or models");
  assert(!/\bS[1-9][a-z]?\b/.test(page.replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<svg[\s\S]*?<\/svg>/g, "").replace(/<[^>]+>/g, " ")), "seeding: no study-code names such as S7a in the text");
  // linked from where it belongs
  for (const p of ["study-joint", "retune", "glossary", "faq", "studies"]) assert(html[p].includes('href="seeding.html"'), `${p}: must link to the seeding page`);
  for (const p of PAGES) assert(html[p].includes('<a href="seeding.html">Black hole seeding</a>'), `${p}: footer navigation must list the seeding page`);
  assert(/<a href="studies\.html"[^>]*aria-current="page"|aria-current="page"[^>]*>Studies/.test(html.seeding), "seeding: the Studies section must be marked current");
}
// discoverability: canonical and share tags on every page, sitemap, robots.txt, Atom feed, schema.org Dataset, Croissant and the index of the export; every file or link they list must exist
{
  const SITE = "https://shubhanbhatia42.github.io/sim-highline", sha = b => createHash("sha256").update(b).digest("hex");
  const rd = async p => readFile(new URL(p, root), "utf8"), exists = p => access(new URL(p, root)).then(() => true, () => false);
  const local = u => { assert(u.startsWith(SITE + "/"), `not on this site: ${u}`); return u.slice(SITE.length + 1); };
  const cov = JSON.parse(await readFile(new URL("../data/coverage-report.json", import.meta.url), "utf8")), cff = await readFile(new URL("../CITATION.cff", import.meta.url), "utf8"), changelog = await readFile(new URL("../CHANGELOG.md", import.meta.url), "utf8");
  // canonical, og:url, one of each, absolute, equal; the feed is announced; no request is made by any of it
  for (const p of [...PAGES, "findings"]) {
    const h = html[p], canon = [...h.matchAll(/<link rel="canonical" href="([^"]+)"/g)].map(m => m[1]), ogu = [...h.matchAll(/<meta property="og:url" content="([^"]+)"/g)].map(m => m[1]);
    assert.equal(canon.length, 1, `${p}: exactly one canonical link`);
    assert.equal(canon[0], p === "findings" ? `${SITE}/site/studies.html` : `${SITE}/site/${p}.html`, `${p}: canonical address`);
    assert.deepEqual(ogu, [canon[0]], `${p}: og:url must equal the canonical address`);
    assert(h.includes(`<link rel="alternate" type="application/atom+xml" title="sim-highline releases" href="${SITE}/feed.xml">`), `${p}: feed not announced`);
    assert(!/<script[^>]+src="https?:/i.test(h) && !/gtag\(|google-analytics|googletagmanager|plausible\.io|matomo|hotjar|segment\.com/i.test(h), `${p}: no analytics and no external script`);
  }
  for (const [file, want] of [["index.html", `${SITE}/site/index.html`], ["highline.html", `${SITE}/highline.html`]]) {
    const h = await rd(file); assert.equal([...h.matchAll(/<link rel="canonical" href="([^"]+)"/g)].map(m => m[1]).join(), want, `${file}: canonical`);
  }
  assert((await rd("highline.html")).includes(`<meta property="og:url" content="${SITE}/highline.html">`), "highline.html: og:url");
  const nf = await rd("404.html"); assert(/name="robots" content="noindex"/.test(nf) && !/rel="canonical"/.test(nf), "404: noindex and no canonical");
  // sitemap and robots
  const sm = await rd("sitemap.xml"), locs = [...sm.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
  assert.equal(new Set(locs).size, locs.length, "sitemap: no duplicate address");
  for (const u of locs) assert(await exists(local(u)), `sitemap lists ${u}, which is not in the build`);
  for (const want of [...PAGES.map(p => `${SITE}/site/${p}.html`), `${SITE}/highline.html`]) assert(locs.includes(want), `sitemap: ${want} is missing`);
  assert(!locs.some(u => u.endsWith("findings.html")), "sitemap: the redirect page is not listed");
  assert(/<lastmod>\d{4}-\d{2}-\d{2}<\/lastmod>/.test(sm) && sm.includes('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'), "sitemap: namespace and dates");
  const rb = await rd("robots.txt"); assert(/^User-agent: \*$/m.test(rb) && rb.includes(`Sitemap: ${SITE}/sitemap.xml`) && !/^Disallow: \/\s*$/m.test(rb), "robots.txt: allows crawling and names the sitemap");
  // Atom feed from CHANGELOG.md: one entry per released version, well formed
  const feed = await rd("feed.xml"), versions = [...changelog.matchAll(/^## (\d+\.\d+\.\d+) \((\d{4}-\d{2}-\d{2})\)/gm)].map(m => m[1]);
  assert(versions.length >= 5, "changelog: released versions found");
  const ents = feed.split("<entry>").slice(1);
  assert.equal(ents.length, Math.min(25, versions.length), "feed: one entry per released version (at most 25)");
  assert.equal((feed.match(/<\/entry>/g) || []).length, ents.length, "feed: entries closed");
  assert(!/&(?!amp;|lt;|gt;|quot;|apos;|#\d+;)/.test(feed), "feed: unescaped ampersand");
  versions.slice(0, ents.length).forEach((v, i) => assert(ents[i].includes(`<title>sim-highline ${v}</title>`) && /<updated>\d{4}-\d{2}-\d{2}T00:00:00Z<\/updated>/.test(ents[i]) && ents[i].includes("&lt;li&gt;"), `feed: entry ${i} must be version ${v} with its changes`));
  assert.equal(new Set([...feed.matchAll(/<id>([^<]+)<\/id>/g)].map(m => m[1])).size, ents.length + 1, "feed: unique ids");
  assert(!feed.includes("Unreleased") && feed.includes(`<id>${SITE}/feed.xml</id>`) && feed.includes('xmlns="http://www.w3.org/2005/Atom"'), "feed: header");
  // the CSV files as published, their header, and the checksums of everything listed
  const csvHead = async f => { let t = await rd(`data/export/${f}`); let c = 0; while (t.startsWith("#")) { c++; t = t.slice(t.indexOf("\n") + 1); } return { header: t.slice(0, t.indexOf("\n")).split(","), comments: c }; };
  const fileOk = async (url, bytes, hash, what) => { const b = await readFile(new URL(local(url), root)); assert.equal(b.length, bytes, `${what}: size of ${url}`); assert.equal(sha(b), hash, `${what}: sha256 of ${url}`); };
  // schema.org Dataset
  const ld = JSON.parse(html.data.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
  const given = [...cff.matchAll(/given-names:\s*"?([^"\n]+)"?\s*\n/g)].map(m => m[1].trim()), fams = [...cff.matchAll(/family-names:\s*"?([^"\n]+)"?/g)].map(m => m[1].trim());
  assert(fams.length >= 1 && given.length === fams.length, "CITATION.cff: authors found");
  assert.deepEqual([].concat(ld.creator).map(c => c.name), fams.map((f, i) => `${given[i]} ${f}`), "Dataset: creators are those of CITATION.cff");
  assert(ld.identifier === `https://doi.org/${release.doi}` && ld.license.includes("creativecommons.org/licenses/by/4.0") && ld.version === release.version && ld.datePublished === release.released, "Dataset: DOI, licence, version, date");
  assert.equal(ld.variableMeasured.length, Object.keys(cov.byRelation).length, "Dataset: one variableMeasured per relation");
  for (const v of ld.variableMeasured) assert(v["@type"] === "PropertyValue" && v.propertyID in cov.byRelation && v.name && new RegExp(`^${cov.byRelation[v.propertyID].records} records?, ${cov.byRelation[v.propertyID].rankable} usable`).test(v.description), `Dataset: variable ${v.propertyID}`);
  for (const d of ld.distribution) { const m = manifest.files[d.name]; if (m) { assert.equal(d.sha256, m.sha256, `Dataset: ${d.name} sha256 is the manifest's`); assert.equal(d.contentSize, `${m.bytes} B`); } await fileOk(d.contentUrl, Number(d.contentSize.replace(/ B$/, "")), d.sha256, "Dataset"); }
  for (const f of Object.keys(manifest.files).filter(f => /\.(csv|json|bib)$/.test(f))) assert(ld.distribution.some(d => d.name === f), `Dataset: ${f} not listed`);
  assert(ld.distribution.some(d => d.name === "sim-highline-croissant.json") && ld.distribution.some(d => d.name === "index.json"), "Dataset: Croissant and index listed");
  // Croissant (mlcommons)
  const cr = JSON.parse(await rd("data/export/sim-highline-croissant.json"));
  assert(cr["@type"] === "sc:Dataset" && cr.conformsTo === "http://mlcommons.org/croissant/1.0" && cr.name && cr.description.length > 80 && cr.license && cr.url && cr.version === release.version && cr.creator.length, "Croissant: required dataset properties");
  for (const k of ["cr", "sc", "dct", "recordSet", "field", "fileObject", "dataType", "extract", "source", "column", "citeAs", "conformsTo", "key", "data", "@vocab", "@language"]) assert(k in cr["@context"], `Croissant: @context lacks ${k}`);
  const fo = new Map(cr.distribution.map(d => [d["@id"], d]));
  assert.equal(fo.size, cr.distribution.length, "Croissant: unique file ids");
  for (const d of cr.distribution) { assert(d["@type"] === "cr:FileObject" && d.encodingFormat === "text/csv" && d.name === d["@id"], `Croissant: file object ${d["@id"]}`); assert.equal(d.sha256, manifest.files[d.name].sha256, `Croissant: ${d.name} sha256 is the manifest's`); await fileOk(d.contentUrl, Number(d.contentSize.replace(/ B$/, "")), d.sha256, "Croissant"); }
  assert.equal(fo.size, Object.keys(manifest.files).filter(f => f.endsWith(".csv")).length, "Croissant: every CSV export is described");
  const ids = new Set(), TYPES = new Set(["sc:Text", "sc:Integer", "sc:Float", "sc:Boolean", "sc:Date"]);
  for (const rs of cr.recordSet) {
    const file = [...new Set(rs.field.map(f => f.source.fileObject["@id"]))]; assert.equal(file.length, 1, `Croissant: ${rs.name} reads one file`);
    const { header, comments } = await csvHead(file[0]); assert(cr.description.includes(`${rs.name}: ${comments}`) && comments >= 1, `Croissant: the number of comment lines before the header of ${rs.name} is stated`);
    assert.deepEqual(rs.field.map(f => f.name), header, `Croissant: ${rs.name} fields are the CSV columns, in order`);
    for (const f of rs.field) { assert(!ids.has(f["@id"]) && f["@id"] === `${rs["@id"]}/${f.name}` && f["@type"] === "cr:Field" && TYPES.has(f.dataType) && fo.has(f.source.fileObject["@id"]) && f.source.extract.column === f.name, `Croissant: field ${f["@id"]}`); ids.add(f["@id"]); }
    if (rs.key) assert(ids.has(rs.key["@id"]), `Croissant: key of ${rs.name} is a field`);
  }
  // index of the export
  const ix = JSON.parse(await rd("data/export/index.json"));
  assert(ix.version === release.version && ix.doi === release.doi && ix.counts.records === manifest.nRecords && ix.relations.length === Object.keys(cov.byRelation).length, "index.json: version, DOI and counts come from the saved files");
  for (const f of ix.files) { assert(f.path === `data/export/${f.name}` && f.url === `${SITE}/${f.path}`, `index.json: ${f.name} address`); await fileOk(f.url, f.bytes, f.sha256, "index.json"); if (manifest.files[f.name]) assert.equal(f.sha256, manifest.files[f.name].sha256); }
  for (const f of Object.keys(manifest.files)) assert(ix.files.some(x => x.name === f), `index.json: ${f} not listed`);
  for (const u of [ix.discovery.sitemap, ix.discovery.feed, ix.discovery.croissant]) assert(await exists(local(u)), `index.json: ${u} is not in the build`);
}
// the old pages are gone and the old findings URL redirects
for (const gone of ["about", "use-cases"]) await access(new URL(`site/${gone}.html`, root)).then(() => assert.fail(`${gone}.html must be removed`), () => {});
assert(/http-equiv="refresh" content="0; url=studies.html"/.test(html.findings) && html.findings.includes('href="studies.html"'), "findings.html must redirect to studies.html");
for (const page of PAGES) assert(!/href="findings\.html"/.test(html[page]) && !/href="(about|use-cases)\.html"/.test(html[page]), `${page}: links to a retired page`);

const index = html.index;
assert(index.includes(manifest.nRecords.toLocaleString("en-US")), "index: record count must match the export manifest");
assert(/<svg viewBox/.test(index) && (index.match(/<path d="M/g) || []).length >= 5, "index: figure must contain curves");
assert(/Not reviewed by any outside expert/.test(index), "index must state limits");
assert(/Fig\. 1/.test(index) && /Records by relation/.test(index), "index: figure and data table expected");
for (const f of ["study-definitions", "study-harmonization", "study-sfh", "study-joint", "study-shape"]) assert(index.includes(`href="${f}.html"`), `index: study ${f} missing from the table`);
assert(/study-joint\.html[\s\S]*?Pre-registered · (pending|result)/.test(index), "index: the all-at-once study row must say pending or result");
assert(!/hero|What you get|What it is not|Start with a question|problem it removes/i.test(index), "index: marketing sections must be gone");

const studies = html.studies;
assert(["study-definitions", "study-harmonization", "study-sfh", "study-joint", "study-shape"].every(s => studies.includes(`href="${s}.html"`)), "studies: every study must be linked");
assert(/pre-registered|Protocol first/i.test(studies) && /Null results are reported/.test(studies), "studies: how studies are registered");
for (const [p, n] of [["study-definitions", 3], ["study-harmonization", 1], ["study-sfh", 3]]) {
  assert((html[p].match(/<figure class="fig/g) || []).length === n, `${p}: ${n} figures expected`);
  for (const s of ["Question", "Data", "Result", "Limits", "Reproduce"]) assert(new RegExp(`<h2 id="[a-z]+-h"><span class="sn">§\\d</span>[^<]*${s}`).test(html[p]), `${p}: section ${s}`);
  assert(/<div class="abstract">/.test(html[p]) && /Status<\/dt>/.test(html[p]), `${p}: abstract and status line`);
}
assert(html["study-harmonization"].includes("PROTOCOL-harmonization.md") && html["study-harmonization"].includes("ANALYSIS-harmonization.md"), "S2 links protocol and analysis");
assert(["PROTOCOL-model-form.md", "ANALYSIS-model-form.md", "POWER-model-form.md"].every(f => html["study-sfh"].includes(f)), "S3 links protocol, analysis and power study");
assert(["PROTOCOL-joint-reachability.md", "ANALYSIS-joint-reachability.md", "POWER-joint-reachability.md"].every(f => html["study-joint"].includes(f)) && /Pre-registered · (pending|result)/.test(html["study-joint"]), "S4 links protocol, analysis and calibration and states its status");
assert(html.retune.includes('id="retune"') && html.retune.includes('data-src="../data/retune/retune.json"') && html.retune.includes('src="retune.js"') && /<noscript>/.test(html.retune), "retune: instrument container, data source, script and a no-script note");

const data = html.data;
assert(/camels-sfrd\.json/.test(data) && /camels-galaxies\.json/.test(data), "data: both CAMELS ensembles listed");
assert(data.includes("sim-highline-records.csv") && data.includes("sim_highline.py") && data.includes("sim-highline-citations.bib") && data.includes("CITATION.cff") && data.includes(release.doi), "data: downloads, loader and citation");
assert(data.includes('href="sources.html"') && /id="tiers"/.test(data) && /id="relations"/.test(data), "data: relation table, tiers and the sources page");
const methods = html.methods;
for (const id of ["routes", "extraction", "definitions", "audit", "limits", "ledger", "undocumented"]) assert(methods.includes(`id="${id}"`), `methods: section ${id}`);
assert(/Not reviewed by anyone outside/.test(methods) && /Not a leaderboard/.test(methods) && /Thin relations/.test(methods), "methods: limits");

const sources = html.sources;
const profiles = JSON.parse(await readFile(new URL("../data/simulation-profiles.json", import.meta.url), "utf8")).profiles;
const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
for (const k of Object.keys(profiles)) assert(sources.includes(`id="${slug(k)}"`), `sources: missing simulation ${k}`);
assert(/Known metadata issues/.test(sources) && /not yet filled/.test(sources), "sources: must state what is unfilled");
assert((sources.match(/<article class="sim"/g) || []).length === Object.keys(profiles).length, "sources: one entry per simulation");
assert(!/class="card"/.test(sources), "sources: no cards");

const app = await readFile(new URL("highline.html", root), "utf8");
assert(app.includes("site/methods.html") && app.includes("site/sources.html") && app.includes("site/retune.html") && app.includes("site/studies.html"), "app must link to the Methods, Sources, Retune and Studies pages");
assert(!/about\.html|use-cases\.html/.test(app), "app: no links to retired pages");
assert(app.includes("Michroma") === false && app.includes("Jost") === false, "app: old fonts must be gone");
console.log(`Site pages valid: ${PAGES.length} pages + redirect, ${manifest.nRecords} records, links and anchors resolve`);
