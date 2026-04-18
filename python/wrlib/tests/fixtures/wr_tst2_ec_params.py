"""WR TST-2 EC parameters mirroring ``test_run/inputs/wr_tst2_ec.in``.

Reproduces the namelist block (lines 5..39 of the .in file) as Python
data for Layer 1 / Layer 4 replay via ``libwrapi.so``.

This is the smallest of the three wr baseline cases -- NRAYMAX=1 and
modest NSTPMAX/NRSMAX/NRLMAX -- so it's the primary smoke candidate if
the larger cases hit timeouts in CI.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/wr_tst2_ec/metrics.json``.
"""
from __future__ import annotations

SCALARS = {
    "MODELG":  2,
    "RR":      0.38,
    "RA":      0.16,
    "RKAP":    1.0,
    "RDLT":    0.0,
    "BB":      0.3,
    "RIP":     0.2,
    "NSMAX":   2,
    "PROFN1":  2.0,
    "PROFN2":  2.0,
    "NRAYMAX": 1,
    "NSTPMAX": 2000,
    "NRSMAX":  30,
    "NRLMAX":  60,
    "MDLWRI":  101,
    "MDLWRQ":  0,
    "MDLWRW":  0,
    "SMAX":    1.0,
    "DELS":    0.005,
}

ARRAYS = {
    "PA":      [2.0, 1.0],
    "PZ":      [1.0, -1.0],
    "PN":      [0.5, 0.5],
    "PNS":     [0.05, 0.05],
    "PTPR":    [0.5, 0.5],
    "PTPP":    [0.5, 0.5],
    "PTS":     [0.05, 0.05],
    "MODELP":  [4, 4],
    "RFIN":    [8.2e3],
    "RPIN":    [0.5],
    "ZPIN":    [0.0],
    "PHIIN":   [0.0],
    "ANGZIN":  [0.0],
    "ANGPHIN": [0.0],
    "UUIN":    [1.0],
    "MODEWIN": [1],
}

UNREGISTERED_KEYS = ()
SOURCE_INPUT = "test_run/inputs/wr_tst2_ec.in"
BASELINE_NAME = "wr_tst2_ec"
NRAY_REQUEST = 0


def apply(wr) -> None:
    """Apply all *registered* TST-2 EC parameters to a Wrlib instance."""
    for name, value in SCALARS.items():
        wr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            wr.set_param(f"{name}[{i}]", float(v))
