"""WR ITER LHCD parameters mirroring ``test_run/inputs/wr_iter_lhcd.in``.

Reproduces the namelist block (lines 5..41 of the .in file) as Python
data so Layer 1 (equivalence) and Layer 4 (sweep) tests can replay the
same physics case via ``libwrapi.so`` without shelling out to ``wr``.

Registered in ``wr/wr_param_registry.f90`` (L-3) -> forwarded here.
Unregistered namelist keys (currently: none for this fixture -- all
~30 namelist keys have setters) are listed in ``UNREGISTERED_KEYS`` for
future registry growth.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/wr_iter_lhcd/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters accepted by wr_param_registry. Values copied
# verbatim from test_run/inputs/wr_iter_lhcd.in.
SCALARS = {
    "MODELG":  2,
    "RR":      6.2,
    "RA":      2.0,
    "RKAP":    1.7,
    "RDLT":    0.33,
    "BB":      5.3,
    "RIP":     15.0,
    "NSMAX":   2,
    "PROFN1":  2.0,
    "PROFN2":  2.0,
    "PROFT1":  2.0,
    "PROFT2":  1.0,
    "NRAYMAX": 2,
    "NSTPMAX": 2000,
    "NRSMAX":  50,
    "NRLMAX":  100,
    "MDLWRI":  101,
    "MDLWRQ":  0,
    "MDLWRW":  0,
    "SMAX":    5.0,
    "DELS":    0.05,
}

# Array parameters: 1-origin subscripts matching Fortran convention.
# Each key is a bare name; the list is applied as NAME[1], NAME[2], ...
ARRAYS = {
    "PA":       [2.0, 1.0],
    "PZ":       [1.0, -1.0],
    "PN":       [1.0, 1.0],
    "PNS":      [0.1, 0.1],
    "PTPR":     [10.0, 10.0],
    "PTPP":     [10.0, 10.0],
    "PTS":      [0.5, 0.5],
    "MODELP":   [4, 4],
    "RFIN":     [5.0e3, 5.0e3],
    "RPIN":     [8.0, 8.0],
    "ZPIN":     [0.0, 0.0],
    "PHIIN":    [0.0, 0.0],
    "ANGZIN":   [0.0, 0.0],
    "ANGPHIN":  [30.0, 40.0],
    "UUIN":     [1.0, 1.0],
    "MODEWIN":  [1, 1],
}

# All namelist keys in wr_iter_lhcd.in are registered in
# wr_param_registry.f90 at the L-3 merge point. Keep this tuple as a
# hook for future registry growth / drift detection.
UNREGISTERED_KEYS = ()

# Input file this fixture mirrors (relative to repo root).
SOURCE_INPUT = "test_run/inputs/wr_iter_lhcd.in"

# Name of the Phase-0 baseline directory under test_run/baselines/.
BASELINE_NAME = "wr_iter_lhcd"

# nray_request passed to wr_run; 0 keeps the namelist NRAYMAX above.
NRAY_REQUEST = 0


def apply(wr) -> None:
    """Apply all *registered* ITER-LHCD parameters to a Wrlib instance.

    Parameters
    ----------
    wr:
        An open :class:`wrlib.Wrlib` handle.
    """
    for name, value in SCALARS.items():
        wr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            wr.set_param(f"{name}[{i}]", float(v))
