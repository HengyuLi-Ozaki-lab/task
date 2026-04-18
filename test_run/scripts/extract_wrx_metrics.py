#!/usr/bin/env python3
"""Extract metrics from wrx_regress.dat (Phase L-0 dump format v1).

Usage:
    extract_wrx_metrics.py path/to/wrx_regress.dat

Output schema (printed as JSON to stdout):
  {
    "NRAYMAX": int, "NSTPMAX": int, "NRSMAX": int, "NRLMAX": int,
    "NSAMAX_WR": int, "NSMAX": int, "MODELG": int, "MDLWRQ": int,
    "scalars": {"pwr_tot": float, ...},
    "arrays":  {"NSTPMAX_NRAY": [int...], "pwr_nray": [float...], ...},
    "arrays2": {"pwr_nsa_nray": [[float...], ...], ...}
  }
"""
import argparse
import json
import re
import sys
from pathlib import Path


INT_KEYS = {"NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX",
            "NSAMAX_WR", "NSMAX", "MODELG", "MDLWRQ"}
FLOAT_SCALARS = {"pwr_tot"}
INT_ARRAYS = {"NSTPMAX_NRAY"}

# Fortran's 1PE format can drop the "E" for subnormal exponents (e.g.
# "4.8952117329314484-310" instead of "...E-310"). Repair such tokens
# before float() so we don't crash on legitimate numerics.
_FORTRAN_NO_E = re.compile(r"^([+-]?\d+\.\d+)([+-]\d{2,3})$")


def _to_float(token: str) -> float:
    s = token.strip()
    m = _FORTRAN_NO_E.match(s)
    if m:
        s = m.group(1) + "E" + m.group(2)
    return float(s)


def parse(path: Path) -> dict:
    out = {"scalars": {}, "arrays": {}, "arrays2": {}}
    text = path.read_text()
    lines = text.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i].rstrip()
        if not ln:
            i += 1
            continue
        if ln.startswith("# TASK"):
            i += 1
            continue
        # 2D array header: "# array2 <name> rows=<r> cols=<c>"
        m = re.match(r"#\s*array2\s+(\w+)\s+rows=(\d+)\s+cols=(\d+)\s*$", ln)
        if m:
            name = m.group(1)
            rows = int(m.group(2))
            cols = int(m.group(3))
            i += 1
            mat = []
            for _ in range(rows):
                if i >= n:
                    raise SystemExit(f"unexpected EOF inside array2 {name}")
                row = [_to_float(x) for x in lines[i].split()]
                if len(row) != cols:
                    raise SystemExit(
                        f"array2 {name}: expected {cols} cols, got {len(row)}"
                    )
                mat.append(row)
                i += 1
            out["arrays2"][name] = mat
            continue
        # 1D array header: "# array <name> n=<len>"
        m = re.match(r"#\s*array\s+(\w+)\s+n=(\d+)\s*$", ln)
        if m:
            name = m.group(1)
            length = int(m.group(2))
            i += 1
            vals = []
            for _ in range(length):
                if i >= n:
                    raise SystemExit(f"unexpected EOF inside array {name}")
                v = lines[i].strip()
                if name in INT_ARRAYS:
                    vals.append(int(v))
                else:
                    vals.append(_to_float(v))
                i += 1
            out["arrays"][name] = vals
            continue
        # other comment line
        if ln.startswith("#"):
            i += 1
            continue
        # scalar: KEY=VALUE
        if "=" in ln:
            key, val = ln.split("=", 1)
            key = key.strip()
            val = val.strip()
            if key in INT_KEYS:
                out[key] = int(val)
            elif key in FLOAT_SCALARS:
                out["scalars"][key] = _to_float(val)
            else:
                # forward-compat: try float, else ignore
                try:
                    out["scalars"][key] = _to_float(val)
                except ValueError:
                    pass
            i += 1
            continue
        i += 1
    # sanity
    for k in ("NRAYMAX", "NSAMAX_WR"):
        if k not in out:
            raise SystemExit(f"missing required header field: {k}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", type=Path)
    args = ap.parse_args()
    json.dump(parse(args.dump), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
