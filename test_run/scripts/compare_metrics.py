#!/usr/bin/env python3
"""Compare two metric JSONs within a relative tolerance.

Supported schemas (auto-detected; defaults to TR for back-compat):
- TR (extract_tr_metrics.py): NT, NRMAX, NSMAX,
    scalars (dict), profile (list of dicts).
- WRX (extract_wrx_metrics.py): NRAYMAX, NSTPMAX, NRSMAX, NRLMAX,
    NSAMAX_WR, NSMAX, MODELG, MDLWRQ,
    scalars (dict), arrays (dict[str, list]), arrays2 (dict[str, list[list]]).

The TR `profile` block is preserved unchanged. The WRX `arrays`/`arrays2`
blocks are compared additively; either may be absent. Use `--schema wrx`
to force the WRX dimensional check; auto-detect picks WRX when the
baseline contains `NRAYMAX` or `arrays2`.

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


_WRX_DIM_KEYS = (
    "NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX",
    "NSAMAX_WR", "NSMAX", "MODELG", "MDLWRQ",
)


def compare_wrx(baseline: dict, actual: dict, tol: float) -> list:
    """Compare WRX-schema metric dicts with relative tolerance.

    Top-level integer dimension keys must match exactly; any mismatch
    aborts further comparison. scalars / arrays / arrays2 blocks are
    compared element-wise within `tol`. Integer arrays (e.g. NSTPMAX_NRAY)
    require exact equality.
    """
    errors = []
    for k in _WRX_DIM_KEYS:
        if k in baseline or k in actual:
            if baseline.get(k) != actual.get(k):
                errors.append(
                    f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}"
                )
    if errors:
        return errors

    bs = baseline.get("scalars", {})
    a_s = actual.get("scalars", {})
    for k in sorted(set(bs) | set(a_s)):
        if k not in bs or k not in a_s:
            errors.append(f"scalars.{k}: missing")
            continue
        _check_scalar(f"scalars.{k}", float(bs[k]), float(a_s[k]), tol, errors)

    ba = baseline.get("arrays", {})
    aa = actual.get("arrays", {})
    for k in sorted(set(ba) | set(aa)):
        if k not in ba or k not in aa:
            errors.append(f"arrays.{k}: missing")
            continue
        bv, av = ba[k], aa[k]
        if len(bv) != len(av):
            errors.append(
                f"arrays.{k}: length {len(bv)} vs {len(av)}"
            )
            continue
        for i, (b, a) in enumerate(zip(bv, av)):
            if isinstance(b, int) and isinstance(a, int):
                if b != a:
                    errors.append(
                        f"arrays.{k}[{i}]: baseline={b} actual={a}"
                    )
            else:
                _check_scalar(
                    f"arrays.{k}[{i}]", float(b), float(a), tol, errors
                )

    b2 = baseline.get("arrays2", {})
    a2 = actual.get("arrays2", {})
    for k in sorted(set(b2) | set(a2)):
        if k not in b2 or k not in a2:
            errors.append(f"arrays2.{k}: missing")
            continue
        bm, am = b2[k], a2[k]
        if len(bm) != len(am):
            errors.append(
                f"arrays2.{k}: rows {len(bm)} vs {len(am)}"
            )
            continue
        for i, (br, ar) in enumerate(zip(bm, am)):
            if len(br) != len(ar):
                errors.append(
                    f"arrays2.{k}[{i}]: cols {len(br)} vs {len(ar)}"
                )
                continue
            for j, (b, a) in enumerate(zip(br, ar)):
                _check_scalar(
                    f"arrays2.{k}[{i}][{j}]", float(b), float(a), tol, errors
                )
    return errors


def _detect_schema(baseline: dict) -> str:
    """Pick wrx if baseline carries WRX-only markers, else tr."""
    if "NRAYMAX" in baseline or "arrays2" in baseline or "NSAMAX_WR" in baseline:
        return "wrx"
    return "tr"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--actual", type=Path, required=True)
    ap.add_argument("--tolerance", type=float, default=1e-10)
    ap.add_argument(
        "--schema", choices=("auto", "tr", "wrx"), default="auto",
        help="Comparison schema (default: auto-detect from baseline keys).",
    )
    args = ap.parse_args()

    baseline = json.loads(args.baseline.read_text())
    actual   = json.loads(args.actual.read_text())
    schema = args.schema if args.schema != "auto" else _detect_schema(baseline)
    if schema == "wrx":
        errors = compare_wrx(baseline, actual, args.tolerance)
    else:
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
