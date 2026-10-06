import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const notes = JSON.parse(await readFile(new URL("../data/relation-notes.json", import.meta.url), "utf8")).relations;
const html = await readFile(new URL("../highline/index.html", import.meta.url), "utf8");
const rel = html.match(/const REL=\{([\s\S]*?)\n\};/)[1];
const keys = [...rel.matchAll(/^\s*(?:"([^"]+)"|([a-z0-9]+)):\{t:/gm)].map(m => m[1] || m[2]);
assert(keys.length >= 16, `REL keys not parsed: ${keys}`);
const ROLES = /^(review|compilation|observation|simulation vs data|(past|present): (observation|compilation|local observation|empirical model))$/;
for (const k of keys) {
  const n = notes[k];
  assert(n, `no note for relation ${k}`);
  const words = n.paragraph.trim().split(/\s+/).length;
  assert(words >= 120 && words <= 260, `${k}: paragraph has ${words} words`);
  assert(!n.paragraph.includes("\n"), `${k}: must be one paragraph`);
  assert(n.refs.length >= 3, `${k}: needs at least three references`);
  assert(n.refs.some(r => r.role === "review" || r.role.endsWith("compilation") || r.role === "compilation"), `${k}: needs a review or compilation among the references`);
  assert(n.refs.some(r => r.role === "simulation vs data") || ["bhsigma"].includes(k), `${k}: needs a simulation-versus-data reference`);
  for (const r of n.refs) {
    assert(/^(\d{4}\.\d{4,5}|[a-z-]+\/\d{7})$/.test(r.arxiv), `${k}: bad arXiv id ${r.arxiv}`);
    assert(/^10\.\d{4,9}\//.test(r.doi), `${k}: bad doi ${r.doi}`);
    assert(ROLES.test(r.role), `${k}: unknown role ${r.role}`);
    assert(/^.+ \d{4}, .+ \S+, \S+$/.test(r.cite), `${k}: bad cite ${r.cite}`);
  }
  const used = new Set();
  for (const m of n.paragraph.matchAll(/([A-Za-z\-]+) et al\. \(?(\d{4})\)?/g)) {
    const ref = n.refs.find(r => new RegExp(`${m[1]} et al\\. ${m[2]},`).test(r.cite));
    assert(ref, `${k}: "${m[0]}" is not among the references`);
    used.add(ref.key);
  }
  for (const m of n.paragraph.matchAll(/([A-Z][A-Za-z\-]+) & ([A-Z][A-Za-z\-]+),? \(?(\d{4})\)?/g)) {
    const ref = n.refs.find(r => r.cite.startsWith(`${m[1]} & ${m[2]} ${m[3]},`));
    assert(ref, `${k}: "${m[0]}" is not among the references`);
    used.add(ref.key);
  }
  for (const r of n.refs) {
    const who = r.cite.split(/ \d{4},/)[0], yr = r.cite.match(/ (\d{4}),/)[1];
    if (!used.has(r.key)) assert(new RegExp(`${who.replace(/[.&]/g, m => "\\" + m)} \\(?${yr}`).test(n.paragraph), `${k}: reference ${r.key} (${r.cite}) is not used in the paragraph`);
  }
}
console.log(`Relation notes valid: ${keys.length} relations, ${new Set(Object.values(notes).flatMap(n => n.refs.map(r => r.arxiv))).size} distinct references`);
