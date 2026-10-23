"""Derive uniform scaling relations from CAESAR catalogues (SIMBA and other CAESAR-processed runs); a thin wrapper around sim_highline_derive, which also serves `sim-highline derive`."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim_highline_derive import CAESAR_HALO_MASS_KEYS as HALO_MASS_KEYS, CAESAR_RUNS as RUNS, DM, LENGTH, MIN_PER_BIN, MIN_STAR_PARTICLES, caesar_records, relations_from_arrays, to_physical, update_digest, write_records  # noqa: E402,F401


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from CAESAR catalogues (SIMBA and other CAESAR-processed runs).")
    ap.add_argument("run", help=f"one of {sorted(RUNS)} or a custom label with --mbar")
    ap.add_argument("catalogues", nargs="+")
    ap.add_argument("--source", default="SIMBA")
    ap.add_argument("--mbar", type=float)
    ap.add_argument("--out", help="write the records here instead of data/curves/caesar-<source>-<run>.json")
    args = ap.parse_args()
    mbar = args.mbar or RUNS.get(args.run)
    if mbar is None:
        raise SystemExit("unknown run: pass --mbar")
    records = caesar_records(args.run, args.catalogues, args.source, mbar)
    out = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "data" / "curves" / f"caesar-{args.source.lower()}-{args.run.lower()}.json"
    write_records(records, out)
    print(f"{args.source} {args.run}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
