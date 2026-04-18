#!/usr/bin/env python3
"""Convert ti_regress.dat into a JSON for regression comparison.

Usage:
    extract_ti_metrics.py path/to/ti_regress.dat
Output schema (same scalars+profile shape as extract_tr_metrics.py so
compare_metrics.py can be reused unchanged):
    NT, NRMAX, NSMAX, nsa_max (top-level ints),
    scalars (dict[str,float]) - float scalars,
    scalars_int (dict[str,int]) - int counters (compared exactly),
    profile (list[dict]) - one dict per radial point.
"""
import argparse
import json
import re
import sys
from pathlib import Path


SCALAR_FLOAT_KEYS = {"T", "residual_loop_max"}
SCALAR_INT_KEYS = {"icount_loop_max", "icount_mat_max"}
RE_PROFILE_HEADER = re.compile(r"^#\s*profile columns:")


def parse(dump_path: Path) -> dict:
    lines = dump_path.read_text().splitlines()
    result = {"scalars": {}, "scalars_int": {}, "profile": []}
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
            if key in ("NT", "NRMAX", "NSMAX", "nsa_max"):
                result[key] = int(val)
            elif key in SCALAR_FLOAT_KEYS:
                result["scalars"][key] = float(val)
            elif key in SCALAR_INT_KEYS:
                result["scalars_int"][key] = int(val)
            else:
                pass  # ignore unknown
        else:
            parts = line.split()
            if len(parts) < 4:
                continue
            nsa = result.get("nsa_max", 0)
            if nsa <= 0:
                raise SystemExit("profile row encountered before nsa_max")
            # NR + RNA(nsa) + RTA(nsa) + RUA(nsa) + RBP + RQP + RJP + ZEFF + BETA + BETAP
            expected = 1 + 3 * nsa + 6
            if len(parts) != expected:
                raise SystemExit(
                    f"malformed profile row (expected {expected} cols, got {len(parts)}): {raw}"
                )
            nr = int(parts[0])
            off = 1
            rna = [float(x) for x in parts[off:off + nsa]]; off += nsa
            rta = [float(x) for x in parts[off:off + nsa]]; off += nsa
            rua = [float(x) for x in parts[off:off + nsa]]; off += nsa
            rbp, rqp, rjp, zeff, beta, betap = (float(x) for x in parts[off:off + 6])
            result["profile"].append({
                "NR": nr, "RNA": rna, "RTA": rta, "RUA": rua,
                "RBP": rbp, "RQP": rqp, "RJP": rjp,
                "ZEFF": zeff, "BETA": beta, "BETAP": betap,
            })
    for k in ("NT", "NRMAX", "NSMAX", "nsa_max"):
        if k not in result:
            raise SystemExit(f"missing header field: {k}")
    if len(result["profile"]) != result["NRMAX"]:
        raise SystemExit(
            f"profile row count {len(result['profile'])} != NRMAX {result['NRMAX']}"
        )
    if not result["scalars"]:
        raise SystemExit("no float scalars parsed")
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
