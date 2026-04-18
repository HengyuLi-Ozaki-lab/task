"""Minimal ITER-like parameters mirroring ``test_run/inputs/ti_min.in``.

The ``ti_min`` namelist is the L-0 baseline for the TI module; it is the
tiniest ti run (NSMAX=1, NRMAX=10, NTMAX=2) and its baseline at
``test_run/baselines/ti_min/metrics.json`` is the canonical equivalence
target for Layer 1.

Note: this file is named ``ti_iter01_params.py`` to match the task
spec's reference to an "iter01" fixture, but it actually mirrors
``ti_min.in``. An ITER-scale ti case is not yet part of the test
corpus; when one is added this fixture will be upgraded. The
``SOURCE_INPUT`` / ``BASELINE_NAME`` attributes below document the
real source so callers don't need to guess.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/ti_min/metrics.json`` (once that
baseline exists).
"""
from __future__ import annotations

# Scalar parameters that ti_param_registry already accepts.
# Values copied verbatim from test_run/inputs/ti_min.in.
SCALARS = {
    "NSMAX":   1,
    "NRMAX":   10,
    "NTSTEP":  1,
    "NGTSTEP": 1,
    "NGRSTEP": 1,
    "NTMAX":   2,
}

# Array parameters: 1-origin subscripts matching Fortran convention.
# ti_min has no namelist arrays; kept empty for shape-parity with
# tr_iter01_params.
ARRAYS: dict = {}

# Namelist keys that appear in ti_min.in but are not yet registered
# in ti_param_registry.f90. ti_min actually lists all keys via
# registered names, so this is empty -- kept for shape-parity with
# tr fixtures.
UNREGISTERED_KEYS: tuple = ()

# Input file this fixture mirrors (relative to repo root).
SOURCE_INPUT = "test_run/inputs/ti_min.in"

# Layer-1 NTMAX used by the baseline (so the equivalence test runs the
# same number of time-steps as the Fortran driver did).
NTMAX = 2

# Name of the Phase-0 baseline directory under test_run/baselines/.
BASELINE_NAME = "ti_min"


def apply(ti) -> None:
    """Apply all *registered* ti_min parameters to a TiLib instance.

    Parameters
    ----------
    ti:
        An open :class:`tilib.TiLib` handle.
    """
    for name, value in SCALARS.items():
        ti.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        if isinstance(arr, dict):
            for i, v in arr.items():
                ti.set_param(f"{name}[{int(i)}]", float(v))
        else:
            for i, v in enumerate(arr, start=1):
                ti.set_param(f"{name}[{i}]", float(v))
