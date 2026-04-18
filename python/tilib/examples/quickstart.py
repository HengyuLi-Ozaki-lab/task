"""Smallest possible TiLib run: init, set a few scalars, run, print.

Equivalent to running the standalone ``ti`` binary with
``test_run/inputs/ti_min.in`` (NSMAX=1, NRMAX=10, NTMAX=2).

Run from the repository root::

    PYTHONPATH=python python3 python/tilib/examples/quickstart.py

Prerequisites:
  - ``make -C ti libtiapi.so`` has been run once (see README "Known gap").
  - Optional: ``TILIB_PATH`` set if the library lives outside the repo.
"""
from __future__ import annotations

import argparse
import sys

from tilib import TiLib


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=2,
                        help="time-steps to advance (default: 2, matches ti_min.in)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate argument parsing only; skip FFI calls")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"[dry-run] would call TiLib().run(ntmax={args.ntmax})")
        return 0

    with TiLib() as ti:
        # ti_min.in: NSMAX=1, NRMAX=10, NTMAX=2.
        ti.set_params(NSMAX=1, NRMAX=10,
                      NTSTEP=1, NGTSTEP=1, NGRSTEP=1,
                      NTMAX=args.ntmax)
        ti.run(ntmax=args.ntmax)
        state = ti.get_state()

    print(f"NT={state.nt}  NRMAX={state.nrmax}  "
          f"NSA_MAX={state.nsa_max}  NSMAX={state.nsmax}")
    print(f"T                 = {state.T:.6e}")
    print(f"residual_loop_max = {state.residual_loop_max:.3e}")
    print(f"icount_loop_max   = {state.icount_loop_max}")

    print("\nradial profile (NR, RBP, RQP, RJP, ZEFF):")
    for r in range(state.nrmax):
        print(f"  {r+1:3d}  "
              f"{state.RBP[r]: .3e}  "
              f"{state.RQP[r]: .3e}  "
              f"{state.RJP[r]: .3e}  "
              f"{state.ZEFF[r]: .3e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
