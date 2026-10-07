"""Read the figure and table captions of arXiv papers and report which relations they cover and whether the figures are vector, raster or tables.
Usage: python3 scripts/scan_literature.py IDS.txt OUT.json   (one arXiv id per line)   or   python3 scripts/scan_literature.py OUT.json 2205.15325 ...
Each source is fetched, read and deleted, so disk use stays at one paper. Needs PyMuPDF (scripts/vector_figure.py)."""
import glob
import json
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf

REL = {
    "gsmf": r"stellar mass function|mass function of galax", "sfms": r"main.sequence|SFR.{0,30}stellar mass|star.formation rate.{0,30}stellar mass", "ssfr": r"specific star",
    "mzr": r"mass.metallicity|metallicity relation|MZR|gas.phase metallicity", "zstar": r"stellar metallicity", "size": r"size.mass|mass.size|half.mass radi|effective radi|half.light radi",
    "shmr": r"stellar.to.halo|stellar mass.halo mass|SMHM|SHMR|galaxy formation efficiency", "bh": r"black hole mass.{0,40}stellar mass|M_\{?\\?rm ?BH", "bhsigma": r"velocity dispersion.{0,40}black hole|black hole.{0,40}velocity dispersion|M.{0,6}sigma",
    "jstar": r"angular momentum", "quenched": r"quenched fraction|passive fraction|quiescent fraction|fraction of quenched|fraction of quiescent", "hi": r"neutral hydrogen|atomic gas|H\{?\\?,?\s?[Ii]\}?", "h2": r"molecular gas|H\$_2\$|H_2",
    "tf": r"Tully", "uvlf": r"UV luminosity function|luminosity function", "sfrd": r"star.formation rate density|cosmic star.formation|SFRD|SFR density", "smd": r"stellar mass density", "gas": r"gas fraction|gas.to.stellar"}


def scan_one(i):
    d = vf.fetch_arxiv(i)
    hits = []
    try:
        for f in glob.glob(str(d) + "/**/*.tex", recursive=True):
            try:
                s = open(f, encoding="latin-1").read()
            except Exception:
                continue
            for kind, pat in (("fig", r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}"), ("tab", r"\\begin\{table\*?\}.*?\\end\{table\*?\}")):
                for m in re.finditer(pat, s, re.S):
                    t = m.group(0)
                    c = re.search(r"\\caption\{(.{0,260})", t, re.S)
                    cap = (c.group(1) if c else "").replace("\n", " ")
                    rels = [k for k, p in REL.items() if re.search(p, cap, re.I)]
                    if not rels:
                        continue
                    fl = re.findall(r"includegraphics[^{]*\{([^}]*)\}", t)
                    fmt = "table" if kind == "tab" else ("vector" if any(x.lower().endswith(".pdf") or "." not in x.split("/")[-1] for x in fl) else "raster")
                    hits.append({"rels": rels, "fmt": fmt, "files": [x.split("/")[-1] for x in fl][:3], "cap": cap[:200]})
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return hits


def scan(ids, out_path=None, delay=3.0, progress=True):
    out = {}
    for i in ids:
        try:
            out[i] = {"hits": scan_one(i)}
        except Exception as e:
            out[i] = {"error": str(e)[:80]}
        if progress:
            print(i, len(out[i].get("hits", [])), out[i].get("error", ""), flush=True)
        if out_path:
            Path(out_path).write_text(json.dumps(out))
        time.sleep(delay)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0].endswith(".json"):
        out_path, ids = a[0], a[1:]
    else:
        out_path, ids = a[1], [l.strip() for l in open(a[0]) if l.strip()]
    scan(ids, out_path)
