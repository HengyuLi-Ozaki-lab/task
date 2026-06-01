"""W-impurity parameters mirroring ``test_run/inputs/ti_w.in``.

The ``ti_w`` namelist adds tungsten (Z=74) as the third plasma species to
the minimum-setup template: NSMAX=3, NRMAX=20, NTMAX=5. It exercises the
high-Z impurity-transport code path; its baseline at
``test_run/baselines/ti_w/metrics.json`` is the Layer 1 equivalence
target for W transport.

The ``KID_NS(3)='W'`` line cannot be replayed via the float-only
``ti_set_param`` ABI; ``KID_NS`` is recomputed from ``NPA(3)=74`` in
``tiinit.f90`` (same mechanism documented in ti_ar_params.py).

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/ti_w/metrics.json``.
"""
from __future__ import annotations

SCALARS = {
    "NSMAX":   3,
    "DN0":     0.1,
    "DT0":     1.0,
    "DR0":     1.0,
    "DRS":     3.0,
    "NRMAX":   20,
    "NTSTEP":  1,
    "NGTSTEP": 1,
    "NGRSTEP": 1,
    "NTMAX":   5,
}

# 2D arrays keyed by (i, j) tuples so 1-origin subscripts stay explicit.
# MODEL_BND(1,3)=2 and BND_VALUE(1,3)=1.D-3 in the namelist.
MATRIX_ARRAYS = {
    "MODEL_BND": {(1, 3): 2},
    "BND_VALUE": {(1, 3): 1.0e-3},
}

# 1D arrays: namelist uses sparse subscripts like NPA(3)=74, so we use
# {index: value} dicts rather than full lists.
ARRAYS = {
    "NPA":      {3: 74},
    "PA":       {3: 183.84},  # tungsten atomic mass; namelist key PM is
                              # ticomm-aliased to PA in the registry.
    "PZ":       {3: 74.0},
    "ID_NS":    {3: 10},
    "NZMIN_NS": {3: 20},
    "NZMAX_NS": {3: 45},
    "DN0_NS":   {1: 0.0, 2: 0.0},
}

# Namelist keys NOT settable via the float-only ti ABI.
# KID_NS is char-valued (recomputed from NPA in tiinit.f90).
# PM is the namelist form of PA (different name in ticomm); PA is in
# ARRAYS above, so PM is documented but skipped.
UNREGISTERED_KEYS = (
    "KID_NS",
    "PM",
)

SOURCE_INPUT = "test_run/inputs/ti_w.in"
NTMAX = 5
BASELINE_NAME = "ti_w"


def _apply_array(ti, name, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val})."""
    if isinstance(arr, dict):
        for i, v in arr.items():
            try:
                ti.set_param(f"{name}[{int(i)}]", float(v))
            except Exception:  # pragma: no cover - unregistered is OK
                if name not in UNREGISTERED_KEYS:
                    raise
    else:
        for i, v in enumerate(arr, start=1):
            try:
                ti.set_param(f"{name}[{i}]", float(v))
            except Exception:  # pragma: no cover - unregistered is OK
                if name not in UNREGISTERED_KEYS:
                    raise


def apply(ti) -> None:
    """Apply all *registered* ti_w parameters to a TiLib instance."""
    for name, value in SCALARS.items():
        try:
            ti.set_param(name, float(value))
        except Exception:
            if name not in UNREGISTERED_KEYS:
                raise
    for name, arr in ARRAYS.items():
        _apply_array(ti, name, arr)
    # 2D (i, j) subscripts: pattern from ti_ar_params.py:96-102.
    for name, mat in MATRIX_ARRAYS.items():
        for (i, j), v in mat.items():
            try:
                ti.set_param(f"{name}[{int(i)},{int(j)}]", float(v))
            except Exception:
                if name not in UNREGISTERED_KEYS:
                    raise
