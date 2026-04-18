#!/usr/bin/env python3
"""Compare two regression metric JSONs within a relative tolerance.

Supports multiple schemas via runtime dispatch on dict shape:

  * TR (extract_tr_metrics.py):
        NT, NRMAX, NSMAX (ints), scalars (dict), profile (list[dict])
  * WR (extract_wr_metrics.py):
        NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, MODELG, MDLWRI, MDLWRQ, mode_beam
        (ints), scalars (dict), rays (list[dict]), profile_rs (list[dict]),
        profile_rl (list[dict])

Numeric fields inside profile/rays rows may be either scalars (float) or
lists of scalars (list[float]); the comparator handles both transparently
via runtime list-vs-float dispatch (so adding a new module's schema only
requires extending the structural template, not the comparator).

Exit code 0 on match, 1 on mismatch.
"""
import argparse
import json
import math
import sys
from pathlib import Path


# Per-schema descriptor:
#   integer_dimensions: top-level keys that must compare as ints
#   list_sections     : list of (section_key, integer_index_field, value_fields)
SCHEMAS = {
    "tr": {
        "integer_dimensions": ("NT", "NRMAX", "NSMAX"),
        "list_sections": (
            ("profile", "NR", ("AJ", "QP", "RN", "RT")),
        ),
    },
    "wr": {
        "integer_dimensions": (
            "NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX",
            "MODELG", "MDLWRI", "MDLWRQ", "mode_beam",
        ),
        "list_sections": (
            ("rays", "NRAY", ("NSTP_END", "pos_pwrmax_rs_nray", "RAYS_END")),
            ("profile_rs", "NRS", ("pos_nrs", "pwr_nrs")),
            ("profile_rl", "NRL", ("pos_nrl", "pwr_nrl")),
        ),
    },
}


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


def _check_int(label: str, bv, av, out: list) -> None:
    if bv != av:
        out.append(f"{label}: baseline={bv} actual={av}")


def _check_value(label: str, bv, av, tol: float, out: list) -> None:
    """Runtime dispatch: int-vs-int (exact), float-vs-float (tol),
    list-vs-list (recurse element-wise)."""
    if isinstance(bv, list) or isinstance(av, list):
        if not (isinstance(bv, list) and isinstance(av, list)):
            out.append(f"{label}: type mismatch (baseline={type(bv).__name__} actual={type(av).__name__})")
            return
        if len(bv) != len(av):
            out.append(f"{label}: length differ ({len(bv)} vs {len(av)})")
            return
        for j, (b_elem, a_elem) in enumerate(zip(bv, av)):
            _check_value(f"{label}[{j}]", b_elem, a_elem, tol, out)
        return
    if isinstance(bv, bool) or isinstance(av, bool):
        _check_int(label, bv, av, out)
        return
    if isinstance(bv, int) and isinstance(av, int):
        _check_int(label, bv, av, out)
        return
    _check_scalar(label, float(bv), float(av), tol, out)


def _detect_schema(data: dict) -> str:
    for name, desc in SCHEMAS.items():
        if all(k in data for k in desc["integer_dimensions"]):
            return name
    raise SystemExit(
        "could not detect schema (expected one of: "
        + ", ".join(SCHEMAS) + ")"
    )


def compare(baseline: dict, actual: dict, tol: float, schema: str | None = None) -> list:
    """Compare two metric dicts. If schema is None, auto-detect from the
    baseline's keys (TR vs WR). Returns a list of mismatch descriptions."""
    if schema is None:
        schema = _detect_schema(baseline)
    desc = SCHEMAS[schema]
    errors: list = []

    # 1. Top-level integer dimensions (exact match)
    for k in desc["integer_dimensions"]:
        if baseline.get(k) != actual.get(k):
            errors.append(f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}")
    if errors:
        return errors

    # 2. Top-level scalars (relative tolerance)
    b_scalars = baseline.get("scalars", {})
    a_scalars = actual.get("scalars", {})
    for k in sorted(set(b_scalars) | set(a_scalars)):
        if k not in b_scalars or k not in a_scalars:
            errors.append(f"scalars.{k}: missing")
            continue
        _check_scalar(f"scalars.{k}", float(b_scalars[k]), float(a_scalars[k]), tol, errors)

    # 3. List sections (per-row int key + numeric fields with runtime dispatch)
    for section, key_int, fields in desc["list_sections"]:
        b_list = baseline.get(section, [])
        a_list = actual.get(section, [])
        if len(b_list) != len(a_list):
            errors.append(f"{section} length: baseline={len(b_list)} actual={len(a_list)}")
            continue
        for i, (br, ar) in enumerate(zip(b_list, a_list)):
            if br.get(key_int) != ar.get(key_int):
                errors.append(
                    f"{section}[{i}].{key_int}: baseline={br.get(key_int)} actual={ar.get(key_int)}"
                )
                continue
            for f in fields:
                in_b, in_a = (f in br), (f in ar)
                if not in_b and not in_a:
                    # Symmetrically absent (e.g., WR rays whose NSTP_END
                    # is out of range omit the terminal-sample fields on
                    # both sides — that's deterministic, not a regression).
                    continue
                if not in_b or not in_a:
                    errors.append(f"{section}[{i}].{f}: missing")
                    continue
                _check_value(f"{section}[{i}].{f}", br[f], ar[f], tol, errors)
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", type=Path, required=True)
    ap.add_argument("--actual", type=Path, required=True)
    ap.add_argument("--tolerance", type=float, default=1e-10)
    ap.add_argument(
        "--schema",
        choices=tuple(SCHEMAS),
        default=None,
        help="schema to use (default: auto-detect from baseline keys)",
    )
    args = ap.parse_args()

    baseline = json.loads(args.baseline.read_text())
    actual = json.loads(args.actual.read_text())
    errors = compare(baseline, actual, args.tolerance, schema=args.schema)
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
