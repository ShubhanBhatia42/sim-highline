"""Derive uniform scaling relations from the public EAGLE SQL database (McAlpine et al. 2016); a thin wrapper around sim_highline_derive. `sim-highline derive --format eagle` reads an exported table instead and needs no password."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim_highline_derive import DM, EAGLE_QUERY as QUERY, EAGLE_RUNS as RUNS, EAGLE_SNAPS as SNAPS, MIN_PER_BIN, MIN_STAR_PARTICLES, eagle_records, relations_from_arrays, write_records  # noqa: E402,F401


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from the public EAGLE SQL database (McAlpine et al. 2016).")
    ap.add_argument("sim", choices=sorted(RUNS))
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--out", help="write the records here instead of data/curves/eagle-<sim>.json")
    args = ap.parse_args()
    import eagleSqlTools as sql
    con = sql.connect(args.user, password=args.password)
    records = eagle_records(args.sim, lambda query: sql.execute_query(con, query))
    out = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "data" / "curves" / f"eagle-{args.sim.lower()}.json"
    write_records(records, out)
    print(f"EAGLE {args.sim}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
