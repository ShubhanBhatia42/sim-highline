"""Table 4 of Tomczak et al. 2016 (arXiv:1510.06072) parsed from the arXiv source: stacked UV+IR SFRs per mass and redshift bin, used by ingest_sfms_tomczak16.py as a second check."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from vector_figure import fetch_arxiv  # noqa: E402
import re, json
from pathlib import Path
tex = (fetch_arxiv("1510.06072") / "ms.tex").read_text()
i = tex.index("\\begin{longtable*}"); j = tex.index("\\end{longtable*}")
rows = []; zb = None
cell = re.compile(r"\$?\s*(-?[\d.]+)_\{-([\d.]+)\}\^\{\+([\d.]+)\}\$?")
for line in tex[i:j].split("\n"):
    m = re.match(r"\s*\$([\d.]+) < z < ([\d.]+)\$\s*&(.*)", line)
    if m: zb = (float(m.group(1)), float(m.group(2))); rest = m.group(3)
    elif line.strip().startswith("&"): rest = line.strip()[1:]
    else: continue
    c = [x.strip() for x in re.split(r"\\\\", rest)[0].split("&")]
    if len(c) < 9: continue
    def g(k):
        mm = cell.match(c[k]); return (float(mm.group(1)), float(mm.group(2)), float(mm.group(3)))
    rows.append(dict(z=zb, logM=float(c[0]), psi_all=g(3), psi_sf=g(6), Nall=int(c[7]), Nsf=int(c[8])))
if __name__ == "__main__":
    from collections import Counter
    print(len(rows), Counter(r["z"] for r in rows))
    print(rows[0]); print(rows[-1])
