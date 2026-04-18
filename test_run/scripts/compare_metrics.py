#!/usr/bin/env python3
"""Compare two metric JSONs within a relative tolerance.

Schema-agnostic enough to handle TR, TI, and FP regression dumps:
- TR (extract_tr_metrics.py): NT, NRMAX, NSMAX,
    scalars (dict), profile rows with NR, RN(list), RT(list), AJ, QP.
- TI (extract_ti_metrics.py): NT, NRMAX, NSMAX, nsa_max,
    scalars (dict), scalars_int (dict, exact match),
    profile rows with NR, list-typed fields (RNA/RTA/RUA) and
    float fields (RBP/RQP/RJP/ZEFF/BETA/BETAP).
- FP (extract_fp_metrics.py): NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2,
    scalars (dict, e.g. TIMEFP), profile rows with NR, NSA, RNT, RWT, ...

Top-level integer dimension keys present in either baseline or actual
must match exactly. The scalars dict is compared key-by-key. Profile is
compared row-by-row; integer index keys (NR, NSA) must match exactly,
all remaining numeric fields are compared within the relative tolerance.
List-valued fields (e.g. TR's RN, RT) are compared element-wise.

Also supports the extract_tot_metrics.py schema, which adds a top-level
``modules`` dict whose keys (TR_PRESENT, TI_PRESENT, FP_PRESENT,
WR_PRESENT) flag which TASK modules contributed to the dump. A drift in
those flags (e.g. tot stops calling wr_init) is treated as a structural
regression and fails the check, matching the docstring contract in
extract_tot_metrics.py.

Exit code 0 on match, 1 on mismatch.
"""
import argparse
import json
import math
import sys
from pathlib import Path


# Module presence flags emitted by extract_tot_metrics.py. Comparing these
# guards against silent structural drift (e.g. tot stops dumping a module
# it used to, or starts dumping one it did not before).
MODULE_KEYS = ("TR_PRESENT", "TI_PRESENT", "FP_PRESENT", "WR_PRESENT")


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


_INDEX_KEYS = ("NR", "NSA", "NS")
_DIMENSION_KEYS = ("NT", "NRMAX", "NSMAX", "NSAMAX", "NPMAX", "NTHMAX", "NTG2")


def compare(baseline: dict, actual: dict, tol: float) -> list:
    errors = []
    # Compare any top-level integer dimension key present in either side.
    dim_keys = sorted(
        (set(baseline) | set(actual)) & set(_DIMENSION_KEYS)
    )
    for k in dim_keys:
        if baseline.get(k) != actual.get(k):
            errors.append(f"{k}: baseline={baseline.get(k)} actual={actual.get(k)}")
    # Also compare 'nsa_max' (TI uses lowercase variant).
    if "nsa_max" in baseline or "nsa_max" in actual:
        if baseline.get("nsa_max") != actual.get("nsa_max"):
            errors.append(
                f"nsa_max: baseline={baseline.get('nsa_max')} actual={actual.get('nsa_max')}"
            )
    if errors:
        return errors  # dimensions differ; further comparison meaningless

    # Module presence flags (tot schema). Absent on the tr-only schema, in
    # which case both sides report {} and this loop is a no-op.
    b_mods = baseline.get("modules", {})
    a_mods = actual.get("modules", {})
    if b_mods or a_mods:
        for k in MODULE_KEYS:
            bv = b_mods.get(k)
            av = a_mods.get(k)
            if bv != av:
                errors.append(
                    f"modules.{k}: baseline={bv} actual={av} "
                    "(structural drift — module presence changed)"
                )
        # Surface any unexpected module key on either side so additions to
        # MODULE_KEYS aren't silently ignored.
        for k in sorted((set(b_mods) | set(a_mods)) - set(MODULE_KEYS)):
            errors.append(f"modules.{k}: unknown module key (baseline={b_mods.get(k)} actual={a_mods.get(k)})")

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
        # Index keys (NR, NSA, ...) must match exactly when present on either side.
        index_mismatch = False
        for ikey in _INDEX_KEYS:
            if ikey in br or ikey in ar:
                if br.get(ikey) != ar.get(ikey):
                    errors.append(
                        f"profile[{i}].{ikey}: baseline={br.get(ikey)} actual={ar.get(ikey)}"
                    )
                    index_mismatch = True
        if index_mismatch:
            # Rows are not the same data point; skip field-level comparison.
            continue
        # Compare any remaining numeric/list-valued field present in baseline or actual.
        all_keys = set(br) | set(ar)
        for field in sorted(all_keys - set(_INDEX_KEYS)):
            bv = br.get(field)
            av = ar.get(field)
            if bv is None or av is None:
                errors.append(f"profile[{i}].{field}: missing")
                continue
            if isinstance(bv, list) or isinstance(av, list):
                # legacy TR shape with list-valued fields (RN, RT)
                if not isinstance(bv, list) or not isinstance(av, list):
                    errors.append(f"profile[{i}].{field}: type mismatch")
                    continue
                if len(bv) != len(av):
                    errors.append(
                        f"profile[{i}].{field}: length differ ({len(bv)} vs {len(av)})"
                    )
                    continue
                for j, (bvj, avj) in enumerate(zip(bv, av)):
                    _check_scalar(
                        f"profile[{i}].{field}[{j}]", float(bvj), float(avj), tol, errors
                    )
            else:
                _check_scalar(
                    f"profile[{i}].{field}", float(bv), float(av), tol, errors
                )
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
