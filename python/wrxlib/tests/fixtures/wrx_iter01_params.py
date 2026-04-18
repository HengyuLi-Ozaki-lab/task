"""WRX ITER-ECCD parameters mirroring ``test_run/inputs/wrx_iter01.in``.

The namelist block (lines 6..50 of the .in file) is reproduced here as
Python data so Layer 1 (equivalence) and Layer 4 (sweep) tests can
replay the same physics case via ``libwrxapi.so`` without shelling out
to the ``wrx`` binary.

Only keys that appear in ``wrx/wrx_param_registry.f90`` (L-3) are
listed in :data:`SCALARS` / :data:`ARRAYS`. Namelist keys that are not
yet registered are tracked in :data:`UNREGISTERED_KEYS` for future
registry growth -- they are *not* set by :func:`apply`.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/wrx_iter01/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters registered in wrx_param_registry.f90.
# Values copied verbatim from test_run/inputs/wrx_iter01.in.
SCALARS = {
    "MODELG":  2,
    "MODELQ":  0,
    "RR":      6.2,
    "RA":      2.0,
    "RB":      2.2,
    "BB":      5.3,
    "Q0":      1.0,
    "QA":      3.5,
    "PROFJ":   1.0,
    "NSMAX":   2,
    "MDLWRI":  2,
    "MDLWRQ":  1,
    "MDLWRG":  1,
    "MDLWRP":  1,
    "MDLWRW":  0,
    "pne_threshold": 1.0e-6,
    "SMAX":    2.0,
    "DELS":    1.0e-3,
    "NRAYMAX": 4,
}

# Array parameters: 1-origin subscripts matching Fortran convention.
# Each list is applied as NAME[1], NAME[2], ...
ARRAYS = {
    "PROFN1":  [2.0,     2.0],
    "PROFN2":  [1.0,     1.0],
    "PROFT1":  [2.0,     2.0],
    "PROFT2":  [1.0,     1.0],
    "PA":      [2.0,     5.4462e-4],
    "PZ":      [1.0,    -1.0],
    "PN":      [1.0,     1.0],
    "PNS":     [0.05,    0.05],
    "PTPR":    [10.0,    10.0],
    "PTPP":    [10.0,    10.0],
    "PTS":     [0.5,     0.5],
    "MODELP":  [206,     206],
    "MODELV":  [3,       0],
    "NCMIN":   [-3,     -3],
    "NCMAX":   [3,       3],
    # 4 rays (NRAYMAX=4).
    "RFIN":    [170.0e3, 170.0e3, 170.0e3, 170.0e3],
    "RPIN":    [8.0,     8.0,     8.0,     8.0],
    "ZPIN":    [0.0,     0.0,     0.0,     0.0],
    "PHIIN":   [0.0,     0.0,     0.0,     0.0],
    "ANGPIN":  [0.0,     5.0,     10.0,    15.0],
    "ANGTIN":  [10.0,    20.0,    30.0,    40.0],
    "UUIN":    [1.0,     1.0,     1.0,     1.0],
    "MODEWIN": [1,       1,       1,       1],
}

# Namelist keys that appear in wrx_iter01.in but are not yet registered
# in wrx_param_registry.f90. Adding them there will let us tighten the
# Layer 1 match.
UNREGISTERED_KEYS = (
    "KNAMWR",
)

# Input file this fixture mirrors (relative to repo root).
SOURCE_INPUT = "test_run/inputs/wrx_iter01.in"

# Name of the Phase-0 baseline directory under test_run/baselines/.
BASELINE_NAME = "wrx_iter01"

# ``nray_request`` passed to :py:meth:`wrxlib.Wrxlib.run`. Zero keeps
# whatever NRAYMAX was set via set_param (matching the namelist).
NRAY_REQUEST = 0


def apply(lib) -> None:
    """Apply all *registered* ITER-ECCD parameters to a Wrxlib instance.

    Parameters
    ----------
    lib:
        An open :class:`wrxlib.Wrxlib` handle.
    """
    for name, value in SCALARS.items():
        lib.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            lib.set_param(f"{name}[{i}]", float(v))
