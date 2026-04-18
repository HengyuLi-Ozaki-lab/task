"""3x3 sweep over RFIN[1] (LH frequency) and ANGPHIN[1] (toroidal
injection angle), collecting the global peak-power scalar for each cell.

Mirrors the Layer-4 ``wrlib_sweep`` regression smoke
(``python/wrlib/tests/test_sweep.py``) and the design spec pattern 1
(coarse parameter survey). One :class:`Wrlib` context per cell so each
case starts from a fresh ``wr_init`` state and the Bugbot HIGH (PR #36)
post-finalize invariant is exercised 9 times.

Run from the repository root::

    PYTHONPATH=python python3 python/wrlib/examples/parameter_sweep.py
"""
from __future__ import annotations

import argparse
import sys
from typing import List, Sequence, Tuple

from wrlib import Wrlib


# Fixed physics baseline applied to every cell in the sweep. Values
# mirror the tests/fixtures/wr_iter_lhcd_params.py fixture with NRAYMAX
# trimmed to 1 so each cell completes quickly.
BASE_SCALARS = {
    "MODELG": 2, "RR": 6.2, "RA": 2.0, "RKAP": 1.7, "RDLT": 0.33,
    "BB": 5.3, "RIP": 15.0, "NSMAX": 2,
    "PROFN1": 2.0, "PROFN2": 2.0, "PROFT1": 2.0, "PROFT2": 1.0,
    "NRAYMAX": 1, "NSTPMAX": 1000, "NRSMAX": 50, "NRLMAX": 100,
    "MDLWRI": 101, "MDLWRQ": 0, "MDLWRW": 0,
    "SMAX": 5.0, "DELS": 0.05,
}
BASE_ARRAYS = {
    "PA":     [2.0, 1.0],
    "PZ":     [1.0, -1.0],
    "PN":     [1.0, 1.0],
    "PNS":    [0.1, 0.1],
    "PTPR":   [10.0, 10.0],
    "PTPP":   [10.0, 10.0],
    "PTS":    [0.5, 0.5],
    # Launcher defaults; RFIN[1] and ANGPHIN[1] are overridden per cell.
    "RPIN":    [8.0],
    "ZPIN":    [0.0],
    "PHIIN":   [0.0],
    "ANGZIN":  [0.0],
    "UUIN":    [1.0],
    "MODEWIN": [1],
}


def _apply_base(wr: Wrlib) -> None:
    for name, value in BASE_SCALARS.items():
        wr.set_param(name, float(value))
    for name, arr in BASE_ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            wr.set_param(f"{name}[{i}]", float(v))


def _sweep(rf_vals: Sequence[float], ang_vals: Sequence[float]
           ) -> List[Tuple[float, float, float, float]]:
    """Return list of ``(RFIN, ANGPHIN, pwrmax_rs, pos_pwrmax_rs)`` tuples."""
    rows: List[Tuple[float, float, float, float]] = []
    for rf in rf_vals:
        for ang in ang_vals:
            with Wrlib() as wr:
                _apply_base(wr)
                wr.set_param("RFIN[1]", rf)
                wr.set_param("ANGPHIN[1]", ang)
                wr.run(nray_request=0)
                s = wr.get_state()
            rows.append((rf, ang,
                         s.scalars["pwrmax_rs"],
                         s.scalars["pos_pwrmax_rs"]))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="print the grid only; skip FFI calls")
    args = parser.parse_args(argv)

    rf_vals = (4.0e3, 5.0e3, 6.0e3)     # MHz (LH frequency)
    ang_vals = (25.0, 30.0, 35.0)       # deg (toroidal launch angle)

    if args.dry_run:
        print(f"[dry-run] grid: RFIN={list(rf_vals)} x ANGPHIN={list(ang_vals)}")
        return 0

    rows = _sweep(rf_vals, ang_vals)
    print(f"{'RFIN':>8} {'ANGPHIN':>8} {'pwrmax_rs':>14} {'pos_pwrmax_rs':>14}")
    for rf, ang, peak, pos in rows:
        print(f"{rf:8.1f} {ang:8.2f} {peak:14.6g} {pos:14.6g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
