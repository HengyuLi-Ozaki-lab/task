"""3x3 sweep over RR and BB, collecting TIMEFP for each cell.

Mirrors design spec §6.4 pattern 1 (also used by the Layer 4
``fplib_sweep`` regression). One ``Fplib`` context per cell so each
case starts from a fresh ``fp_init`` state.

Run from the repository root::

    PYTHONPATH=python python3 python/fplib/examples/parameter_sweep.py
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Tuple

from fplib import Fplib


# Shared ITER01-style setup applied to every cell. Only RR and BB are
# swept. Mesh is shrunk so the 9-point grid finishes well under the
# test runner timeout.
BASE_PARAMS = {
    "MODELG": 3, "NSMAX": 3,
    "PA":   {2: 2.0, 3: 3.0},
    "PN":   {1: 0.8, 2: 0.4, 3: 0.4},
    "PNS":  {1: 0.01, 2: 0.005, 3: 0.005},
    "PTPR": {1: 20.0, 2: 20.0, 3: 20.0},
    "PTPP": {1: 20.0, 2: 20.0, 3: 20.0},
    "PMAX": {1: 10.0, 2: 10.0, 3: 10.0},
    "NSAMAX": 1, "NSBMAX": 3,
    "NS_NSA": {1: 1},
    "NS_NSB": {1: 1, 2: 2, 3: 3},
    "MODELC": {1: 4, 2: 4, 3: 4},
    "MODELR": 1,
    "NRMAX": 10, "NPMAX": 20, "NTHMAX": 20,
    "DELT": 1.0e-3,
    "RMIN": 0.4, "RMAX": 0.8,
    "PABS_WR": 1.0,
}


def _sweep(rr_vals: Iterable[float], bb_vals: Iterable[float],
           ntmax: int) -> List[Tuple[float, float, float]]:
    """Return list of ``(RR, BB, TIMEFP)`` tuples for each cell in the grid."""
    rows: List[Tuple[float, float, float]] = []
    for rr in rr_vals:
        for bb in bb_vals:
            with Fplib() as fp:
                fp.set_params(**BASE_PARAMS,
                              RR=float(rr), BB=float(bb),
                              NTMAX=ntmax)
                fp.run(ntmax=ntmax)
                timefp = fp.get_state().timefp
            rows.append((float(rr), float(bb), float(timefp)))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=1,
                        help="time-steps per cell (default: 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the grid only; skip FFI calls")
    args = parser.parse_args(argv)

    rr_vals = (6.0, 6.5, 7.0)
    bb_vals = (5.0, 5.3, 5.6)

    if args.dry_run:
        print(f"[dry-run] grid: RR={list(rr_vals)} x BB={list(bb_vals)}"
              f" ntmax={args.ntmax}")
        return 0

    rows = _sweep(rr_vals, bb_vals, args.ntmax)
    print(f"{'RR':>6} {'BB':>6} {'TIMEFP':>14}")
    for rr, bb, timefp in rows:
        print(f"{rr:6.2f} {bb:6.2f} {timefp:14.6e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
