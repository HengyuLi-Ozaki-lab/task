#!/usr/bin/env python3
"""Convert fp_regress.dat into a JSON for regression comparison.

Usage:
    extract_fp_metrics.py path/to/fp_regress.dat
Output (stdout JSON):
    NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2 (int),
    scalars (dict[str,float]) -- currently {"TIMEFP": ...},
    profile (list[dict]) -- one dict per (NR, NSA) row, fields:
        NR, NSA, RNT, RWT, RTT, RJT, RPCT, RPWT.
"""
import argparse
import json
import re
import sys
from pathlib import Path


INT_KEYS    = {"NRMAX", "NSAMAX", "NPMAX", "NTHMAX", "NTG2"}
SCALAR_KEYS = {"TIMEFP"}
PROFILE_FIELDS = ("RNT", "RWT", "RTT", "RJT", "RPCT", "RPWT")
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
            if key in INT_KEYS:
                result[key] = int(val)
            elif key in SCALAR_KEYS:
                result["scalars"][key] = float(val)
            else:
                pass  # ignore unknown
        else:
            parts = line.split()
            expected = 2 + len(PROFILE_FIELDS)  # NR + NSA + 6 fields
            if len(parts) != expected:
                raise SystemExit(
                    f"malformed profile row (expected {expected} cols, got {len(parts)}): {raw}"
                )
            row = {"NR": int(parts[0]), "NSA": int(parts[1])}
            for i, field in enumerate(PROFILE_FIELDS, start=2):
                row[field] = float(parts[i])
            result["profile"].append(row)

    for k in INT_KEYS:
        if k not in result:
            raise SystemExit(f"missing header field: {k}")
    expected_rows = result["NRMAX"] * result["NSAMAX"]
    if len(result["profile"]) != expected_rows:
        raise SystemExit(
            f"profile row count {len(result['profile'])} != NRMAX*NSAMAX {expected_rows}"
        )
    if "TIMEFP" not in result["scalars"]:
        raise SystemExit("missing TIMEFP")
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
