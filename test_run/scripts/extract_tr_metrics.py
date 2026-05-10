#!/usr/bin/env python3
"""Convert tr_regress.dat into a JSON for regression comparison.

Usage:
    extract_tr_metrics.py path/to/tr_regress.dat
Output:
    JSON to stdout with keys:
        NT (int), NRMAX (int), NSMAX (int),
        scalars (dict[str,float]),
        profile (list[dict]) — one dict per radial point.
"""
import argparse
import json
import re
import sys
from pathlib import Path


SCALAR_KEYS = {
    "T", "WPT", "AJT", "AJRFT", "Q0", "BETA0", "BETAP0", "BETAA", "BETAN",
    "TAUE1", "TAUE2", "ZEFF0", "ALI", "RQ1",
}
RE_PROFILE_HEADER = re.compile(r"^#\s*profile columns:")


def parse(dump_path: Path) -> dict:
    lines = dump_path.read_text().splitlines()
    result = {"scalars": {}, "profile": []}
    in_profile = False
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        if RE_PROFILE_HEADER.match(line):
            in_profile = True
            continue
        if line.startswith("#"):
            continue
        if not in_profile:
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key in ("NT", "NRMAX", "NSMAX"):
                result[key] = int(val)
            elif key in SCALAR_KEYS:
                result["scalars"][key] = float(val)
            else:
                pass  # ignore unknown scalars
        else:
            parts = line.split()
            if len(parts) < 4:
                continue
            nsmax = result.get("NSMAX", 0)
            if nsmax <= 0:
                raise SystemExit("profile row encountered before NSMAX")
            expected = 1 + 2 * nsmax + 2  # NR + RN(NSMAX) + RT(NSMAX) + AJ + QP
            if len(parts) != expected:
                raise SystemExit(
                    f"malformed profile row (expected {expected} cols, got {len(parts)}): {raw}"
                )
            nr = int(parts[0])
            rn = [float(x) for x in parts[1 : 1 + nsmax]]
            rt = [float(x) for x in parts[1 + nsmax : 1 + 2 * nsmax]]
            aj = float(parts[1 + 2 * nsmax])
            qp = float(parts[2 + 2 * nsmax])
            result["profile"].append({"NR": nr, "RN": rn, "RT": rt, "AJ": aj, "QP": qp})
    # sanity check
    for k in ("NT", "NRMAX", "NSMAX"):
        if k not in result:
            raise SystemExit(f"missing header field: {k}")
    if len(result["profile"]) != result["NRMAX"]:
        raise SystemExit(
            f"profile row count {len(result['profile'])} != NRMAX {result['NRMAX']}"
        )
    if not result["scalars"]:
        raise SystemExit("no scalars parsed")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", type=Path)
    args = ap.parse_args()
    json.dump(parse(args.dump), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
