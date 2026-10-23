"""Derive uniform scaling relations from Subfind group catalogs (Illustris, IllustrisTNG, CAMELS); a thin wrapper around sim_highline_derive, which also serves `sim-highline derive`."""
import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim_highline_derive import (DM, FIELDS, GROUP_FIELDS, MIN_PER_BIN, MIN_STAR_PARTICLES, RUNS, SNAPS_TNG, age_gyr, binned_median, derive, load, load_field_files,  # noqa: E402,F401
                                 relations_from_arrays, update_digest, write_records)


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from Subfind group catalogs.")
    ap.add_argument("run", help=f"one of {sorted(RUNS)} or a custom label used with --source/--mbar/--h/--Om")
    ap.add_argument("groups_root", help="directory containing groups_NNN/ subdirectories (or the group files themselves with --flat)")
    ap.add_argument("--flat", action="store_true", help="group files sit directly in groups_root (e.g. CAMELS groups_090.hdf5)")
    ap.add_argument("--source")
    ap.add_argument("--mbar", type=float, help="initial baryon particle mass in Msun (not Msun/h)")
    ap.add_argument("--h", type=float)
    ap.add_argument("--Om", type=float)
    ap.add_argument("--url", default="")
    ap.add_argument("--snaps", help="comma-separated snapshot numbers (default: TNG full-snapshot ladder)")
    ap.add_argument("--out", help="write the records here instead of data/curves/subfind-<run>.json")
    args = ap.parse_args()
    if args.run not in RUNS:
        if None in (args.source, args.mbar, args.h, args.Om):
            raise SystemExit("custom runs need --source, --mbar, --h and --Om")
        RUNS[args.run] = {"source": args.source, "run": args.run, "mbar": args.mbar, "h": args.h, "Om": args.Om, "url": args.url, "calibrated": ()}
    snaps = SNAPS_TNG if not args.snaps else {int(s): None for s in args.snaps.split(",")}
    records = []
    for snap, z in snaps.items():
        groupdir = Path(args.groups_root) if args.flat else Path(args.groups_root) / f"groups_{snap:03d}"
        records += derive(args.run, groupdir, {snap: z}, date.today().isoformat())
    out = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "data" / "curves" / f"subfind-{args.run.lower()}.json"
    write_records(records, out)
    print(f"{args.run}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
