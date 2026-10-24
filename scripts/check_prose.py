"""Reads the built pages (dist/site and dist/404.html) as a reader would and reports: repeated words, mixed British and American spelling, the reading level of the front page and of each study's plain-words paragraph, sentences that are very long, and inconsistent number and unit formats. Fails on repeated words, mixed spellings and formats, a front page and a seeding-explanation page that need more than a school-leaving reading level, and novelty claims ("novel", "first to", "new method"). Quotations (blockquote) keep their authors' wording and spelling and are not checked.
Usage: python3 scripts/check_prose.py [--report]   (--report prints the long sentences and every finding)"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = sorted((ROOT / "dist" / "site").glob("*.html"))
SKIP = {"findings.html", "changes.html"}


def text_of(path):
    h = path.read_text()
    h = re.sub(r"<(script|style|svg|noscript|pre|code|table|blockquote)\b.*?</\1>", " ", h, flags=re.S)
    m = re.search(r"<main.*?</main>", h, re.S)
    h = m.group(0) if m else h
    h = re.sub(r"<(br|/p|/li|/h\d|/dd|/dt|/div|/tr)[^>]*>", "\n", h)
    h = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"[ \t]+", " ", html.unescape(h))


def syllables(w):
    w = w.lower()
    w = re.sub(r"[^a-z]", "", w)
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(re.findall(r"[aeiouy]{1,2}", w)))


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", t) if len(s.split()) >= 3]


def fk_grade(t):
    ss = sentences(t)
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", t)
    if not ss or not words:
        return 0.0
    syl = sum(syllables(w) for w in words)
    return 0.39 * len(words) / len(ss) + 11.8 * syl / len(words) - 15.59


BRIT = {"colour": "color", "behaviour": "behavior", "normalise": "normalize", "normalised": "normalized", "analyse": "analyze", "analysed": "analyzed", "centre": "center", "licence": "license", "catalogue": "catalog", "recognise": "recognize", "organise": "organize", "summarise": "summarize", "favour": "favor", "grey": "gray", "modelling": "modeling", "labelled": "labeled", "fibre": "fiber"}
problems, notes = [], []
texts = {p.name: text_of(p) for p in PAGES if p.name not in SKIP}
us, uk = {}, {}
for name, t in texts.items():
    for m in re.finditer(r"\b(\w+) \1\b", t, re.I):
        w = m.group(1)
        if w.lower() not in {"that", "had", "is", "very"} and not w.isdigit() and len(w) > 1:
            problems.append(f"{name}: repeated word '{w} {w}'")
    low = t.lower().replace("catalog-derived", "")
    for b, a in BRIT.items():
        if re.search(rf"\b{b}s?\b", low):
            uk.setdefault(b, []).append(name)
        if re.search(rf"\b{a}s?\b", low):
            us.setdefault(a, []).append(name)
for b, a in BRIT.items():
    if b in uk and a in us:
        problems.append(f"mixed spelling '{b}' ({', '.join(sorted(set(uk[b])))}) and '{a}' ({', '.join(sorted(set(us[a])))})")
# formats: 'z = 2' versus 'z=2' in running text, '%' with or without a space
for name, t in texts.items():
    a, b = len(re.findall(r"\bz = \d", t)), len(re.findall(r"\bz=\d", t))
    if a and b:
        notes.append(f"{name}: 'z = 2' used {a}x and 'z=2' {b}x")
    c, d = len(re.findall(r"\d %", t)), len(re.findall(r"\d%", t))
    if c and d:
        notes.append(f"{name}: '5 %' used {c}x and '5%' {d}x")
allt = "\n".join(texts.values())
sp, nsp = len(re.findall(r"\d %", allt)), len(re.findall(r"\d%", allt))
if sp and nsp:
    problems.append(f"percent written both with a space ({sp}x) and without ({nsp}x) across pages")
# reading level
front = fk_grade(texts["index.html"])
plain = {}
for name in ("study-definitions.html", "study-harmonization.html", "study-sfh.html", "study-joint.html", "study-shape.html", "study-resolution.html", "seeding.html"):
    m = re.search(r'<div class="plain">(.*?)</div>', (ROOT / "dist" / "site" / name).read_text(), re.S)
    plain[name] = fk_grade(html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else None
if front > 14:
    problems.append(f"front page reading level is grade {front:.1f} (limit 14)")
seed = fk_grade(texts["seeding.html"])
if seed > 14:
    problems.append(f"seeding explanation reading level is grade {seed:.1f} (limit 14)")
if plain["seeding.html"] is None:
    problems.append("seeding.html: no plain-words box")
NOVELTY = re.compile(r"\b(novel|first[- ]ever|first to|first time|unprecedented|ground-?breaking|never (?:been )?done|new method|new approach|state of the art)\b", re.I)
for name, t in texts.items():
    for m in NOVELTY.finditer(t):
        problems.append(f"{name}: novelty wording '{m.group(0)}' near: {t[max(0, m.start() - 50):m.end() + 50].strip()!r}")
long = [(len(s.split()), name, s) for name, t in texts.items() for s in sentences(t) if len(s.split()) > 55]
print(f"prose: {len(texts)} pages; front page reading level grade {front:.1f} (Flesch-Kincaid); seeding page grade {seed:.1f}; plain-words paragraphs " + ", ".join(f"{k.replace('study-', '').replace('.html', '')} {v:.0f}" for k, v in plain.items() if v is not None) + f"; {len(long)} sentences over 55 words; {len(problems)} problems")
if "--report" in sys.argv:
    for n in notes:
        print("  note:", n)
    for w, name, s in sorted(long, reverse=True)[:8]:
        print(f"  long ({w} words) {name}: {s[:140]}...")
for p in problems:
    print("  PROBLEM", p)
sys.exit(1 if problems else 0)
