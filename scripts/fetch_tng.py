import argparse
import os
import time
import urllib.request
from pathlib import Path

from derive_subfind_relations import FIELDS, GROUP_FIELDS, SNAPS_TNG

BASE = "https://www.tng-project.org/api/{run}/files/groupcat-{snap}/?{kind}={field}"


def fetch(run, root, key, snaps):
    for snap in snaps:
        target = Path(root) / f"groups_{snap:03d}"
        target.mkdir(parents=True, exist_ok=True)
        for kind, fields in (("Subhalo", FIELDS), ("Group", GROUP_FIELDS)):
            for field in fields:
                out = target / f"fof_subhalo_tab_{snap:03d}.{kind}.{field}.hdf5"
                if out.exists() and out.stat().st_size > 0:
                    continue
                url = BASE.format(run=run, snap=snap, kind=kind, field=field)
                for attempt in range(4):
                    try:
                        req = urllib.request.Request(url, headers={"api-key": key, "Accept-Language": "en-us,en;q=0.5"})
                        with urllib.request.urlopen(req, timeout=600) as r, open(out, "wb") as f:
                            f.write(r.read())
                        break
                    except Exception as err:
                        if attempt == 3:
                            raise SystemExit(f"{url}: {err}")
                        time.sleep(5 * (attempt + 1))
                print(f"{run} snap {snap}: {out.name}")


def main():
    ap = argparse.ArgumentParser(description="Download only the group-catalog fields sim-highline needs, via the documented TNG API subset endpoint.")
    ap.add_argument("run", choices=["TNG50-1", "TNG100-1", "TNG300-1"])
    ap.add_argument("root")
    ap.add_argument("--key", default=os.environ.get("TNG_API_KEY"))
    ap.add_argument("--snaps", default=",".join(str(s) for s in SNAPS_TNG))
    args = ap.parse_args()
    if not args.key:
        raise SystemExit("set TNG_API_KEY or pass --key")
    fetch(args.run, args.root, args.key, [int(s) for s in args.snaps.split(",")])


if __name__ == "__main__":
    main()
