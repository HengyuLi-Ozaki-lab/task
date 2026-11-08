#!/usr/bin/env python3
"""Compare two metric JSONs within a relative tolerance.

Schema-agnostic enough to handle TR, TI, FP, and EQ regression dumps:
- TR (extract_tr_metrics.py): NT, NRMAX, NSMAX,
    scalars (dict), profile rows with NR, RN(list), RT(list), AJ, QP.
- TI (extract_ti_metrics.py): NT, NRMAX, NSMAX, nsa_max,
    scalars (dict), scalars_int (dict, exact match),
    profile rows with NR, list-typed fields (RNA/RTA/RUA) and
    float fields (RBP/RQP/RJP/ZEFF/BETA/BETAP).
- FP (extract_fp_metrics.py): NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2,
    scalars (dict, e.g. TIMEFP), profile rows with NR, NSA, RNT, RWT, ...
- EQ (extract_eq_metrics.py): NRMAX, NTHMAX, NSUMAX, NSGMAX, NTGMAX,
    NPSMAX, NRVMAX, scalars (dict, e.g. RAXIS/PSI0/QAXIS/...),
    profile rows with NR and float fields PSIP/PSIT/PPS/TTS/QPS/VPS/RST.

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

WRX (extract_wrx_metrics.py) uses ``{arrays, arrays2, scalars}``:
``arrays`` maps a name to a 1-D list (ints such as NSTPMAX_NRAY must
match exactly, floats within the tolerance), ``arrays2`` maps a name to
a list of rows. Both groups are compared element-wise; a group or a
name missing on one side and a length / row-shape mismatch are errors
(#239: before this, only ``scalars.pwr_tot`` was checked for wrx).

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


# When BOTH values are below this magnitude we treat the comparison as
# "near-zero" and require only that the absolute difference fits within
# this same threshold, instead of relative error. Without this, e.g. a
# ZAXIS that should be exactly 0.0 but converges to -2e-15 vs -2e-13
# (both essentially zero) FAILS with rel_err ~1.0 even though both are
# within machine epsilon for the typical magnitude scale.
_NEAR_ZERO_THRESHOLD = 1e-10


def _check_scalar(label: str, bv: float, av: float, tol: float, out: list) -> None:
    if math.isnan(bv) or math.isnan(av):
        out.append(f"{label}: NaN (baseline={bv} actual={av})")
        return
    if math.isinf(bv) or math.isinf(av):
        if bv != av:
            out.append(f"{label}: Inf mismatch (baseline={bv} actual={av})")
        return
    # Near-zero short-circuit: when both values are below the near-zero
    # threshold, fall back to absolute-error comparison (the value is
    # effectively a representation of mathematical zero and rel_err is
    # not meaningful).
    if abs(bv) < _NEAR_ZERO_THRESHOLD and abs(av) < _NEAR_ZERO_THRESHOLD:
        abs_diff = abs(av - bv)
        if abs_diff > _NEAR_ZERO_THRESHOLD:
            out.append(f"{label}: near-zero abs_diff={abs_diff:.3e} > {_NEAR_ZERO_THRESHOLD:.3e} (baseline={bv!r} actual={av!r})")
        return
    e = _rel_err(bv, av)
    if e > tol:
        out.append(f"{label}: baseline={bv!r} actual={av!r} rel_err={e:.3e} > tol={tol:.3e}")


_INDEX_KEYS = ("NR", "NSA", "NS", "NRS", "NRL", "NRAY")
_DIMENSION_KEYS = ("NT", "NRMAX", "NSMAX", "NSAMAX", "NPMAX", "NTHMAX", "NTG2",
                   "NRAYMAX", "NSTPMAX", "NRSMAX", "NRLMAX",
                   "MODELG", "MDLWRI", "MDLWRQ", "mode_beam",
                   # WRX (extract_wrx_metrics.py): the active-species count
                   # is written as NSAMAX_WR, not NSAMAX.
                   "NSAMAX_WR",
                   # EQ-specific dims (extract_eq_metrics.py):
                   "NSUMAX", "NSGMAX", "NTGMAX", "NPSMAX", "NRVMAX")
# Additional list-of-dict sections beyond the default "profile" (used by WR).
_PROFILE_SECTIONS = ("profile", "profile_rs", "profile_rl", "rays")
# Dict-of-list sections (WRX, extract_wrx_metrics.py): "arrays" maps a name
# to a 1-D list, "arrays2" maps a name to a list of equal-length rows.
_ARRAY_SECTIONS = ("arrays",)
_ARRAY2_SECTIONS = ("arrays2",)


# Expected shapes of the WRX arrays in terms of the dimension header, so a
# dump whose arrays disagree with its own header (or two dumps that are
# both malformed the same way) cannot pass. Names not listed here are only
# required to have the same shape on both sides.
_WRX_ARRAY_DIMS = {
    "NSTPMAX_NRAY": ("NRAYMAX",),
    "pwr_nray": ("NRAYMAX",),
    "pwr_nsa": ("NSAMAX_WR",),
    "pos_nrs": ("NRSMAX",),
    "pos_nrl": ("NRLMAX",),
}
_WRX_ARRAY2_DIMS = {
    "pwr_nsa_nray": ("NSAMAX_WR", "NRAYMAX"),
    "pwr_nrs_nsa": ("NRSMAX", "NSAMAX_WR"),
    "pwr_nrl_nsa": ("NRLMAX", "NSAMAX_WR"),
    "pos_pwrmax_rs_nsa_nray": ("NSAMAX_WR", "NRAYMAX"),
    "pos_pwrmax_rl_nsa_nray": ("NSAMAX_WR", "NRAYMAX"),
    "pwrmax_rs_nsa_nray": ("NSAMAX_WR", "NRAYMAX"),
    "pwrmax_rl_nsa_nray": ("NSAMAX_WR", "NRAYMAX"),
}


def _check_value(label: str, bv, av, tol: float, out: list) -> None:
    """One element of an array.

    If either side is an int the values must be equal exactly (17 vs 17.0
    passes, 17 vs 17.000000000001 fails: an integer array that comes back
    as drifting floats is a producer regression, not rounding). Otherwise
    the float rule of ``_check_scalar`` applies.
    """
    if isinstance(bv, bool) or isinstance(av, bool):
        out.append(f"{label}: boolean, not numeric data (baseline={bv!r} actual={av!r})")
        return
    if not isinstance(bv, (int, float)) or not isinstance(av, (int, float)):
        out.append(f"{label}: non-numeric (baseline={bv!r} actual={av!r})")
        return
    if isinstance(bv, int) or isinstance(av, int):
        if bv != av:
            out.append(f"{label}: baseline={bv!r} actual={av!r} (integer: exact match required)")
        return
    _check_scalar(label, bv, av, tol, out)


def _check_shape(section: str, name: str, value: list, is_2d: bool,
                 header: dict, side: str, errors: list) -> bool:
    """Rectangularity and, for the known WRX names, agreement with the
    dimension header of ``side`` ('baseline' / 'actual'). Returns False
    when the value should not be compared element-wise."""
    ok = True
    if is_2d:
        bad_rows = [i for i, row in enumerate(value) if not isinstance(row, list)]
        if bad_rows:
            errors.append(f"{section}.{name}[{bad_rows[0]}] ({side}): row is not a list")
            return False
        widths = {len(row) for row in value}
        if len(widths) > 1:
            errors.append(
                f"{section}.{name} ({side}): ragged rows (widths {sorted(widths)})"
            )
            return False
    dims = (_WRX_ARRAY2_DIMS if is_2d else _WRX_ARRAY_DIMS).get(name)
    if dims and all(k in header for k in dims):
        expected = tuple(int(header[k]) for k in dims)
        if is_2d:
            got = (len(value), len(value[0]) if value else 0)
            # No rows: the column count is unobservable, accept it.
            if got[0] != expected[0] or (value and got[1] != expected[1]):
                ok = False
        else:
            got = (len(value),)
            ok = got == expected
        if not ok:
            errors.append(
                f"{section}.{name} ({side}): shape {got} does not match the "
                f"header {dict(zip(dims, expected))}"
            )
    return ok


def _compare_arrays(baseline: dict, actual: dict, tol: float, errors: list) -> None:
    """Compare the WRX ``arrays`` / ``arrays2`` groups element-wise.

    A group missing on one side, a name missing on one side, a length or
    row-shape mismatch, and any element outside the tolerance are all
    errors, so a dump that drops or corrupts these groups cannot pass.
    """
    for section, is_2d in [(s, False) for s in _ARRAY_SECTIONS] + \
                          [(s, True) for s in _ARRAY2_SECTIONS]:
        b_grp = baseline.get(section)
        a_grp = actual.get(section)
        if b_grp is None and a_grp is None:
            continue
        if b_grp is None or a_grp is None:
            errors.append(f"{section}: missing on one side")
            continue
        if not isinstance(b_grp, dict) or not isinstance(a_grp, dict):
            errors.append(f"{section}: not a name->array mapping on both sides")
            continue
        for name in sorted(set(b_grp) | set(a_grp)):
            if name not in b_grp or name not in a_grp:
                errors.append(f"{section}.{name}: missing")
                continue
            bv, av = b_grp[name], a_grp[name]
            if not isinstance(bv, list) or not isinstance(av, list):
                errors.append(f"{section}.{name}: not a list on both sides")
                continue
            b_ok = _check_shape(section, name, bv, is_2d, baseline, "baseline", errors)
            a_ok = _check_shape(section, name, av, is_2d, actual, "actual", errors)
            if not (b_ok and a_ok):
                continue
            if len(bv) != len(av):
                errors.append(
                    f"{section}.{name}: length differ ({len(bv)} vs {len(av)})"
                )
                continue
            if not is_2d:
                for j, (bj, aj) in enumerate(zip(bv, av)):
                    _check_value(f"{section}.{name}[{j}]", bj, aj, tol, errors)
                continue
            for i, (brow, arow) in enumerate(zip(bv, av)):
                if len(brow) != len(arow):
                    errors.append(
                        f"{section}.{name}[{i}]: row length differ "
                        f"({len(brow)} vs {len(arow)})"
                    )
                    continue
                for j, (bj, aj) in enumerate(zip(brow, arow)):
                    _check_value(f"{section}.{name}[{i}][{j}]", bj, aj, tol, errors)


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

    # Profiles: iterate all known list-of-dict sections; dispatch list-vs-float at runtime.
    for section in _PROFILE_SECTIONS:
        b_prof = baseline.get(section)
        a_prof = actual.get(section)
        if b_prof is None and a_prof is None:
            continue
        if b_prof is None or a_prof is None:
            errors.append(f"{section}: missing on one side")
            continue
        if len(b_prof) != len(a_prof):
            errors.append(f"{section} length: baseline={len(b_prof)} actual={len(a_prof)}")
            continue
        for i, (br, ar) in enumerate(zip(b_prof, a_prof)):
            index_mismatch = False
            for ikey in _INDEX_KEYS:
                if ikey in br or ikey in ar:
                    if br.get(ikey) != ar.get(ikey):
                        errors.append(
                            f"{section}[{i}].{ikey}: baseline={br.get(ikey)} actual={ar.get(ikey)}"
                        )
                        index_mismatch = True
            if index_mismatch:
                continue
            all_keys = set(br) | set(ar)
            for field in sorted(all_keys - set(_INDEX_KEYS)):
                bv = br.get(field)
                av = ar.get(field)
                if bv is None or av is None:
                    errors.append(f"{section}[{i}].{field}: missing")
                    continue
                if isinstance(bv, list) or isinstance(av, list):
                    if not isinstance(bv, list) or not isinstance(av, list):
                        errors.append(f"{section}[{i}].{field}: type mismatch")
                        continue
                    if len(bv) != len(av):
                        errors.append(
                            f"{section}[{i}].{field}: length differ ({len(bv)} vs {len(av)})"
                        )
                        continue
                    for j, (bvj, avj) in enumerate(zip(bv, av)):
                        _check_scalar(
                            f"{section}[{i}].{field}[{j}]", float(bvj), float(avj), tol, errors
                        )
                else:
                    _check_scalar(
                        f"{section}[{i}].{field}", float(bv), float(av), tol, errors
                    )

    # WRX dict-of-list groups (arrays / arrays2).
    _compare_arrays(baseline, actual, tol, errors)
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
