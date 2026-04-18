#!/usr/bin/env python3
"""Compare two metric JSONs within a relative tolerance.

Supports both TR and TI schemas:
    Common: NT, NRMAX, NSMAX, scalars (dict), profile (list of dicts)
    TI extras: nsa_max, scalars_int (dict, exact match), profile entries
               with list-typed fields (RNA/RTA/RUA) and float fields
               (RBP/RQP/RJP/ZEFF/BETA/BETAP).

The compare() routine inspects each profile dict's value type at runtime,
so it works for either schema without a schema flag.

Exit code 0 on match, 1 on mismatch.
"""
import argparse
import json
import math
import sys
from pathlib import Path


def _rel_err(a: float, b: float) -> float:
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom


def _check_scalar(label: str, bv: float, av: float, tol: float, out: list) -> None:
    if math.isnan(bv) or math.isnan(av):
        out.append(f"{label}: NaN (baseline={bv} actual={av})")
        return
    if math.isinf(bv) or math.isinf(av):
        if bv != av:
            out.append(f"{label}: Inf mismatch (baseline={bv} actual={av})")
        return
    e = _rel_err(bv, av)
    if e > tol:
        out.append(f"{label}: baseline={bv!r} actual={av!r} rel_err={e:.3e} > tol={tol:.3e}")


def compare(baseline: dict, actual: dict, tol: float) -> list:
    errors = []
    # Top-level dimensional invariants (only check keys present on either side).
    for k in ("NT", "NRMAX", "NSMAX", "nsa_max"):
        if k in baseline or k in actual:
            if baseline.get(k) != actual.get(k):
                errors.append(f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}")
    if errors:
        return errors  # dimensions differ; further comparison meaningless

    # Float scalars (relative-tolerance comparison).
    b_scalars = baseline.get("scalars", {})
    a_scalars = actual.get("scalars", {})
    for k in sorted(set(b_scalars) | set(a_scalars)):
        if k not in b_scalars or k not in a_scalars:
            errors.append(f"scalars.{k}: missing")
            continue
        _check_scalar(f"scalars.{k}", float(b_scalars[k]), float(a_scalars[k]), tol, errors)

    # Integer scalars (exact match required).
    b_int = baseline.get("scalars_int", {})
    a_int = actual.get("scalars_int", {})
    for k in sorted(set(b_int) | set(a_int)):
        if b_int.get(k) != a_int.get(k):
            errors.append(f"scalars_int.{k}: baseline={b_int.get(k)} actual={a_int.get(k)}")

    # Profiles: dispatch list-vs-float per dict key at runtime.
    b_prof = baseline.get("profile", [])
    a_prof = actual.get("profile", [])
    if len(b_prof) != len(a_prof):
        errors.append(f"profile length: baseline={len(b_prof)} actual={len(a_prof)}")
        return errors
    for i, (br, ar) in enumerate(zip(b_prof, a_prof)):
        if br.get("NR") != ar.get("NR"):
            errors.append(f"profile[{i}].NR: baseline={br.get('NR')} actual={ar.get('NR')}")
            continue
        keys = sorted(set(br) | set(ar))
        for field in keys:
            if field == "NR":
                continue
            bv = br.get(field)
            av = ar.get(field)
            if bv is None or av is None:
                errors.append(f"profile[{i}].{field}: missing in one side")
                continue
            if isinstance(bv, list) or isinstance(av, list):
                if not isinstance(bv, list) or not isinstance(av, list):
                    errors.append(f"profile[{i}].{field}: type mismatch")
                    continue
                if len(bv) != len(av):
                    errors.append(
                        f"profile[{i}].{field}: length differ ({len(bv)} vs {len(av)})"
                    )
                    continue
                for j, (bx, ax) in enumerate(zip(bv, av)):
                    _check_scalar(
                        f"profile[{i}].{field}[{j}]", float(bx), float(ax), tol, errors
                    )
            else:
                _check_scalar(f"profile[{i}].{field}", float(bv), float(av), tol, errors)
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--actual", type=Path, required=True)
    ap.add_argument("--tolerance", type=float, default=1e-10)
    args = ap.parse_args()

    baseline = json.loads(args.baseline.read_text())
    actual   = json.loads(args.actual.read_text())
    errors = compare(baseline, actual, args.tolerance)
    if errors:
        print(f"FAIL: {len(errors)} mismatch(es) (tolerance={args.tolerance:g})")
        for e in errors[:50]:
            print(f"  - {e}")
        if len(errors) > 50:
            print(f"  ... and {len(errors) - 50} more")
        return 1
    print(f"OK: metrics match within tol={args.tolerance:g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
