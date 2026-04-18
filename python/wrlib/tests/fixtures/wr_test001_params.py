"""WR test001 short-case parameters mirroring ``test_run/inputs/wr_test001.in``.

Reproduces the namelist block (lines 5..37 of the .in file) as Python
data for Layer 1 / Layer 4 replay via ``libwrapi.so``.

Units (per ``wr/wrexecr.f90``: ``omega = 2.D6 * PI * RFIN(nray)``):

* ``RFIN[i]`` is in MHz, so ``160.0e3`` = 160 GHz, matching the
  ``RFIN(1)=2*160.D3`` row in ``wr_test001.in``.
* ``RPIN[i]`` / ``ZPIN[i]`` are in meters.
* ``ANGZIN[i]`` / ``ANGPHIN[i]`` are in degrees.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/wr_test001/metrics.json``.
"""
from __future__ import annotations

SCALARS = {
    "MODELG":  2,
    "RR":      6.2,
    "RA":      2.0,
    "RKAP":    1.7,
    "BB":      5.3,
    "NSMAX":   4,
    "PROFN1":  3.7,
    "PROFN2":  2.7,
    "MDLWRI":  101,
    "MDLWRQ":  0,
    "MDLWRW":  0,
    "SMAX":    5.0,
    "DELS":    0.01,
    "NRAYMAX": 2,
    "NSTPMAX": 2000,
    "NRSMAX":  50,
    "NRLMAX":  100,
}

# PA/PZ start at index 2 in the namelist (PA(2)=...). We use dicts to
# set only the indices specified, letting wr_init's defaults fill PA(1)
# / PZ(1). Other arrays use full lists from index 1.
ARRAYS = {
    # PA(2..4) = 2, 3, 4 (PA(1) left at default 1.0, H)
    "PA":      {2: 2.0, 3: 3.0, 4: 4.0},
    # PZ(2..4) = 1, 1, 2 (PZ(1) left at default -1.0, electron)
    "PZ":      {2: 1.0, 3: 1.0, 4: 2.0},
    "PN":      [0.9, 0.40, 0.40, 0.05],
    "PNS":     [0.03, 0.0133, 0.0133, 0.0017],
    "PTPR":    [35.0, 35.0, 35.0, 35.0],
    "PTPP":    [35.0, 35.0, 35.0, 35.0],
    "PTS":     [1.0, 1.0, 1.0, 1.0],
    "MODELP":  [4, 4, 4, 4],
    "RFIN":    [160.0e3, 160.0e3],
    "RPIN":    [8.5, 8.5],
    "ZPIN":    [0.0, 0.0],
    "PHIIN":   [0.0, 0.0],
    "ANGZIN":  [-30.0, -30.0],
    "ANGPHIN": [20.0, 30.0],
    "UUIN":    [1.0, 1.0],
    "MODEWIN": [1, 1],
}

UNREGISTERED_KEYS = ()
SOURCE_INPUT = "test_run/inputs/wr_test001.in"
BASELINE_NAME = "wr_test001"
NRAY_REQUEST = 0


def _apply_array(wr, name, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val})."""
    if isinstance(arr, dict):
        for i, v in arr.items():
            wr.set_param(f"{name}[{int(i)}]", float(v))
    else:
        for i, v in enumerate(arr, start=1):
            wr.set_param(f"{name}[{i}]", float(v))


def apply(wr) -> None:
    """Apply all *registered* test001 parameters to a Wrlib instance."""
    for name, value in SCALARS.items():
        wr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        _apply_array(wr, name, arr)
