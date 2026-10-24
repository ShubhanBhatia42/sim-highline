"""Derive uniform scaling relations from SWIFT/SOAP halo catalogues (FLAMINGO, COLIBRE); a thin wrapper around sim_highline_derive, which also serves `sim-highline derive`."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sim_highline_derive import DM, KPC_CM, MIN_PER_BIN, MIN_STAR_PARTICLES, MSUN_G, SOAP_SUITES as SUITES, YR_S, relations_from_arrays, soap_records, update_digest, write_records  # noqa: E402,F401


def main():
    ap = argparse.ArgumentParser(description="Derive uniform scaling relations from SWIFT/SOAP halo catalogues (FLAMINGO, COLIBRE).")
    ap.add_argument("suite", choices=sorted(SUITES))
    ap.add_argument("run", help="run label, e.g. L1_m8")
    ap.add_argument("mbar", type=float, help="initial baryon particle mass in Msun")
    ap.add_argument("catalogues", nargs="+", help="SOAP halo_properties_NNNN.hdf5 files")
    ap.add_argument("--aperture", default="50kpc")
    ap.add_argument("--out", help="write the records here instead of data/curves/soap-<suite>-<run>.json")
    args = ap.parse_args()
    records = soap_records(args.suite, args.run, args.mbar, args.catalogues, args.aperture)
    out = Path(args.out) if args.out else Path(__file__).resolve().parent.parent / "data" / "curves" / f"soap-{args.suite}-{args.run.lower()}.json"
    write_records(records, out)
    print(f"{SUITES[args.suite]['source']} {args.run}: {len(records)} records written to {out}")


if __name__ == "__main__":
    main()
