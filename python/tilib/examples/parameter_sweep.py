"""3x3 sweep over NRMAX and BB, collecting a convergence diagnostic.

Mirrors the tr ``parameter_sweep.py`` example but adapted to TI's state
fields — TI does not expose a ``WPT`` scalar, so the cell output is
``(icount_loop_max, residual_loop_max, max(ZEFF))`` instead.

One :class:`TiLib` context per cell so each case starts from a fresh
``ti_init`` state.

Run from the repository root::

    PYTHONPATH=python python3 python/tilib/examples/parameter_sweep.py
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Tuple

from tilib import TiLib


# Per-species (NS=3 = Ar) setup shared across cells, mirroring
# test_run/inputs/ti_ar.in. Atomic mass uses PA (registered name);
# the namelist's "PM(3)" key maps to plcomm's PA.
AR_SETUP = {
    "NPA[3]":         18.0,
    "PA[3]":          39.95,
    "ID_NS[3]":       10.0,
    "NZMIN_NS[3]":    15.0,
    "NZMAX_NS[3]":    18.0,
    "MODEL_BND[1,3]":  2.0,
    "BND_VALUE[1,3]":  1.0,
}


def _sweep(nrmax_vals: Iterable[int], bb_vals: Iterable[float],
           ntmax: int) -> List[Tuple[int, float, int, float, float]]:
    """Return list of ``(NRMAX, BB, iters, residual, zeff_max)`` tuples."""
    rows: List[Tuple[int, float, int, float, float]] = []
    for nrmax in nrmax_vals:
        for bb in bb_vals:
            with TiLib() as ti:
                ti.set_params(NSMAX=3, NRMAX=nrmax, BB=bb,
                              NTSTEP=1, NGTSTEP=1, NGRSTEP=1,
                              NTMAX=ntmax)
                for name, value in AR_SETUP.items():
                    ti.set_param(name, value)
                ti.run(ntmax=ntmax)
                s = ti.get_state()
            zeff_max = max(s.ZEFF) if s.ZEFF else 0.0
            rows.append((s.nrmax, bb, s.icount_loop_max,
                         s.residual_loop_max, zeff_max))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=5,
                        help="time-steps per cell (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the grid only; skip FFI calls")
    args = parser.parse_args(argv)

    nrmax_vals = (10, 15, 20)
    bb_vals = (4.5, 5.3, 6.0)

    if args.dry_run:
        print(f"[dry-run] grid: NRMAX={list(nrmax_vals)} x BB={list(bb_vals)}"
              f" ntmax={args.ntmax}")
        return 0

    rows = _sweep(nrmax_vals, bb_vals, args.ntmax)
    print(f"{'NRMAX':>5}  {'BB':>5}  {'iters':>6}  "
          f"{'residual':>12}  {'ZEFF_max':>10}")
    for nrmax, bb, iters, residual, zeff_max in rows:
        print(f"{nrmax:>5d}  {bb:>5.2f}  {iters:>6d}  "
              f"{residual:>12.3e}  {zeff_max:>10.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
