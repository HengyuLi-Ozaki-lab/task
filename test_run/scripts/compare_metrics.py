#!/usr/bin/env python3
"""Compare two TR metric JSONs within a relative tolerance.

Expects the schema produced by extract_tr_metrics.py:
    NT, NRMAX, NSMAX, scalars (dict), profile (list of dicts).

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
    e = _rel_err(bv, av)
    if e > tol:
        out.append(f"{label}: baseline={bv!r} actual={av!r} rel_err={e:.3e} > tol={tol:.3e}")


def compare(baseline: dict, actual: dict, tol: float) -> list:
    errors = []
    for k in ("NT", "NRMAX", "NSMAX"):
        if baseline.get(k) != actual.get(k):
            errors.append(f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}")
    if errors:
        return errors  # dimensions differ; further comparison is meaningless

    b_scalars = baseline.get("scalars", {})
    a_scalars = actual.get("scalars", {})
    for k in sorted(set(b_scalars) | set(a_scalars)):
        if k not in b_scalars or k not in a_scalars:
            errors.append(f"scalars.{k}: missing")
            continue
        _check_scalar(f"scalars.{k}", float(b_scalars[k]), float(a_scalars[k]), tol, errors)

    b_prof = baseline.get("profile", [])
    a_prof = actual.get("profile", [])
    if len(b_prof) != len(a_prof):
        errors.append(f"profile length: baseline={len(b_prof)} actual={len(a_prof)}")
        return errors
    for i, (br, ar) in enumerate(zip(b_prof, a_prof)):
        if br.get("NR") != ar.get("NR"):
            errors.append(f"profile[{i}].NR: baseline={br.get('NR')} actual={ar.get('NR')}")
            continue
        for field in ("AJ", "QP"):
            _check_scalar(f"profile[{i}].{field}", float(br[field]), float(ar[field]), tol, errors)
        for field in ("RN", "RT"):
            bv_list = br.get(field, [])
            av_list = ar.get(field, [])
            if len(bv_list) != len(av_list):
                errors.append(f"profile[{i}].{field}: length differ ({len(bv_list)} vs {len(av_list)})")
                continue
            for j, (bv, av) in enumerate(zip(bv_list, av_list)):
                _check_scalar(f"profile[{i}].{field}[{j}]", float(bv), float(av), tol, errors)
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
