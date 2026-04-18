"""3x3 sweep over RR and BB, collecting WPT for each cell.

Mirrors design spec §6.4 pattern 1. One ``Trlib`` context per cell so
each case starts from a fresh ``tr_init`` state.

Run from the repository root::

    PYTHONPATH=python python3 python/trlib/examples/parameter_sweep.py
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Tuple

from trlib import Trlib


def _sweep(rr_vals: Iterable[float], bb_vals: Iterable[float],
           ntmax: int) -> List[Tuple[float, float, float]]:
    """Return list of ``(RR, BB, WPT)`` tuples for each cell in the grid."""
    rows: List[Tuple[float, float, float]] = []
    for rr in rr_vals:
        for bb in bb_vals:
            with Trlib() as tr:
                tr.set_params(RR=rr, BB=bb, RA=2.0, RKAP=1.7,
                              NSMAX=2, DT=0.1, NTSTEP=10)
                tr.set_param("PN[1]", 1.0)
                tr.set_param("PN[2]", 1.0)
                tr.set_param("PT[1]", 1.5)
                tr.set_param("PT[2]", 1.5)
                tr.run(ntmax=ntmax)
                wpt = tr.get_state().scalars["WPT"]
            rows.append((rr, bb, wpt))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=20,
                        help="time-steps per cell (default: 20)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the grid only; skip FFI calls")
    args = parser.parse_args(argv)

    rr_vals = (7.5, 8.0, 8.5)
    bb_vals = (4.5, 5.0, 5.5)

    if args.dry_run:
        print(f"[dry-run] grid: RR={list(rr_vals)} x BB={list(bb_vals)}"
              f" ntmax={args.ntmax}")
        return 0

    rows = _sweep(rr_vals, bb_vals, args.ntmax)
    print(f"{'RR':>6} {'BB':>6} {'WPT':>14}")
    for rr, bb, wpt in rows:
        print(f"{rr:6.2f} {bb:6.2f} {wpt:14.6g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
