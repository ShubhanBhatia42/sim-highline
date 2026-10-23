"""Helpers shared by the digitizers/ingest scripts for sigma-M, Sigma_1, lambda_R and slow-rotator fraction records: record skeleton, point lists, EPS to PDF, output into data/curves.
Not a digitizer itself (name does not start with digitize_)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vector_figure as vf  # noqa: E402

RETRIEVED = "2026-10-18"
HERE = Path(__file__).resolve().parent
PARTS = HERE.parent / "data" / "curves"


def eps_to_pdf(src_dir, eps_name):
    """Convert one EPS figure of an arXiv source tree to PDF (epstopdf) next to it, in <src>/pdf/."""
    eps = next(Path(src_dir).rglob(eps_name))
    pdf = Path(src_dir) / "pdf" / eps.with_suffix(".pdf").name
    if not pdf.exists():
        pdf.parent.mkdir(exist_ok=True)
        subprocess.run(["epstopdf", str(eps), f"--outfile={pdf}"], check=True)
    return eps, pdf


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def points_from(xy, nd=(3, 4)):
    return [{"x": round(x, nd[0]), "y": round(y, nd[1])} for x, y in xy]


def build(*, rid, source, run, kind, relation, z, zmin, zmax, mode, axes, representation, domain, population, warning,
          definitions, tier, citation, doi, url, calibration, rankable, notes, provenance_extra=None, scatter=None, selection_extra=None):
    sel = {"population": population, "warning": warning}
    if selection_extra:
        sel.update(selection_extra)
    prov = {"tier": tier, "citation": citation, "doi": doi, "url": url, "retrieved": RETRIEVED}
    prov.update(provenance_extra or {})
    return {
        "id": rid, "source": source, "run": run, "kind": kind, "relation": relation,
        "epoch": {"zRepresentative": z, "zNominal": z, "zMin": zmin, "zMax": zmax, "mode": mode, "snapshot": None},
        "axes": axes, "domain": domain, "representation": representation, "scatter": scatter,
        "selection": sel, "definitions": definitions, "provenance": prov, "calibration": calibration,
        "rankable": rankable, "notes": notes}


def points_rep(pts, interval="unspecified", connect=True):
    return {"type": "points", "intervalKind": interval, "connect": connect, "points": pts}


def write_part(name, records):
    PARTS.mkdir(parents=True, exist_ok=True)
    out = PARTS / f"{name.replace('_', '-')}.json"
    out.write_text(json.dumps({"schemaVersion": "1.0.0", "records": records}, indent=2) + "\n")
    return out


def digitize_provenance(pdf, member, method, calib, unc, figure, panel, src_archive_sha):
    return {"figure": figure, "panel": panel, "checksumSha256": vf.sha256(pdf), "sourceMember": member,
            "sourceArchiveSha256": src_archive_sha, "extractionMethod": method, "axisCalibrationPixels": calib,
            "digitizationUncertaintyDex": unc}
