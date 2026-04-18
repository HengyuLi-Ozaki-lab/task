"""WRX TST-2 demo parameters mirroring ``test_run/inputs/wrx_demo.in``.

Namelist block reproduced as Python data for Layer 1 / Layer 4 replay
via ``libwrxapi.so``. Mirrors the tst-2 analytic 1-ray ECCD case used
by ``wrx/tests/c_abi/test_run_so.c``.

Unregistered keys are listed in :data:`UNREGISTERED_KEYS`; see the
module docstring of :mod:`wrx_iter01_params` for the registry-growth
protocol.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/wrx_demo/metrics.json``.
"""
from __future__ import annotations

SCALARS = {
    "MODELG":  2,
    "MODELQ":  0,
    "RR":      0.52,
    "RA":      0.3,
    "RB":      0.35,
    "BB":      0.308,
    "Q0":      1.0e4,
    "QA":      1.0e4,
    "PROFJ":   1.0,
    "NSMAX":   2,
    "MDLWRI":  2,
    "MDLWRQ":  2,
    "MDLWRG":  1,
    "MDLWRP":  1,
    "MDLWRW":  0,
    "pne_threshold": 1.0e-6,
    "SMAX":    1.0,
    "DELS":    1.0e-4,
    "NRAYMAX": 1,
}

ARRAYS = {
    "PROFN1":  [2.0,      2.0],
    "PROFN2":  [1.0,      1.0],
    "PROFT1":  [8.0,      8.0],
    "PROFT2":  [1.0,      1.0],
    "PA":      [5.4462e-4, 5.4462e-4],
    "PZ":      [-1.0,     -1.0],
    "PN":      [0.0194,   0.0006],
    "PNS":     [0.000194, 0.000006],
    "PTPR":    [0.03,     60.0],
    "PTPP":    [0.03,     60.0],
    "PTS":     [0.01,     1.0],
    "MODELP":  [206,      206],
    "MODELV":  [3,        0],
    "NCMIN":   [-2,      -2],
    "NCMAX":   [2,        2],
    # Single ray (NRAYMAX=1).
    "RFIN":    [28.0e3],
    "RPIN":    [0.85],
    "ZPIN":    [0.0],
    "PHIIN":   [0.0],
    "ANGPIN":  [0.0],
    "ANGTIN":  [10.0],
    "UUIN":    [1.0],
    "MODEWIN": [1],
}

UNREGISTERED_KEYS = (
    "KNAMWR",
)

SOURCE_INPUT = "test_run/inputs/wrx_demo.in"
BASELINE_NAME = "wrx_demo"
NRAY_REQUEST = 0


def apply(lib) -> None:
    """Apply all *registered* TST-2 demo parameters to a Wrxlib instance."""
    for name, value in SCALARS.items():
        lib.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            lib.set_param(f"{name}[{i}]", float(v))
