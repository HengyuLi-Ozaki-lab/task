#!/usr/bin/env python3
"""Convert eq_regress.dat into a JSON for regression comparison.

Usage:
    extract_eq_metrics.py path/to/eq_regress.dat
Output:
    JSON to stdout with keys:
        NRMAX, NTHMAX, NSUMAX, NSGMAX, NTGMAX, NPSMAX, NRVMAX (int),
        scalars (dict[str,float]),
        profile (list[dict]) - one dict per radial point with
            NR, PSIP, PSIT, PPS, TTS, QPS, VPS, RST.
"""
import argparse
import json
import re
import sys
from pathlib import Path


DIM_KEYS = {
    "NRMAX", "NTHMAX", "NSUMAX", "NSGMAX", "NTGMAX", "NPSMAX", "NRVMAX",
}
SCALAR_KEYS = {
    "RAXIS", "ZAXIS", "PSI0", "PSIPA", "PSITA", "RIPX",
    "PVOL", "RAAVE", "BETAT", "BETAP", "QAXIS", "QSURF",
}
RE_PROFILE_HEADER = re.compile(r"^#\s*profile columns:")
RE_KEY_VAL = re.compile(r"^[A-Z_][A-Z0-9_]*\s*=")

# Profile columns: NR PSIP PSIT PPS TTS QPS VPS RST
PROFILE_FLOAT_COLS = ("PSIP", "PSIT", "PPS", "TTS", "QPS", "VPS", "RST")


def parse(dump_path: Path) -> dict:
    lines = dump_path.read_text().splitlines()
    result = {"scalars": {}, "profile": []}
    in_profile = False
    for raw in lines:
        line = raw.strip()
        if not line:
            in_profile = False
            continue
        if RE_PROFILE_HEADER.match(line):
            in_profile = True
            continue
        if line.startswith("#"):
            in_profile = False
            continue
        if RE_KEY_VAL.match(line):
            in_profile = False
        if not in_profile:
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key in DIM_KEYS:
                result[key] = int(val)
            elif key in SCALAR_KEYS:
                result["scalars"][key] = float(val)
            else:
                pass  # ignore unknown scalars
        else:
            parts = line.split()
            expected = 1 + len(PROFILE_FLOAT_COLS)
            if len(parts) != expected:
                raise SystemExit(
                    f"malformed profile row (expected {expected} cols, got {len(parts)}): {raw}"
                )
            nr = int(parts[0])
            row = {"NR": nr}
            for i, col in enumerate(PROFILE_FLOAT_COLS):
                row[col] = float(parts[1 + i])
            result["profile"].append(row)
    # sanity checks
    for k in ("NRMAX", "NTHMAX"):
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
