"""Smallest possible Fplib run: init, set a few params, run, print.

Equivalent to running the standalone ``fp`` binary with
``test_run/inputs/fp_iter01.in`` (MODELG=3, NSMAX=3, NTMAX=2), just
with a shrunk mesh so the example finishes quickly.

Run from the repository root::

    PYTHONPATH=python python3 python/fplib/examples/quickstart.py

Prerequisites:
  - ``make -C fp libs_pic && make -C fp libfpapi.so`` has been run once.
  - Optional: ``FPLIB_PATH`` set if the library lives outside the repo.
"""
from __future__ import annotations

import argparse
import sys

from fplib import Fplib


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=2,
                        help="time-steps to advance (default: 2, matches fp_iter01)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate argument parsing only; skip FFI calls")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"[dry-run] would call Fplib().run(ntmax={args.ntmax})")
        return 0

    with Fplib() as fp:
        # ITER-like fixture, shrunk mesh for a fast quickstart run.
        fp.set_params(
            MODELG=3, NSMAX=3,
            PA={2: 2.0, 3: 3.0},
            PN={1: 0.8, 2: 0.4, 3: 0.4},
            PNS={1: 0.01, 2: 0.005, 3: 0.005},
            PTPR={1: 20.0, 2: 20.0, 3: 20.0},
            PTPP={1: 20.0, 2: 20.0, 3: 20.0},
            PMAX={1: 10.0, 2: 10.0, 3: 10.0},
            NSAMAX=1, NSBMAX=3,
            NS_NSA={1: 1},
            NS_NSB={1: 1, 2: 2, 3: 3},
            MODELC={1: 4, 2: 4, 3: 4},
            MODELR=1,
            NRMAX=10, NPMAX=20, NTHMAX=20,
            NTMAX=args.ntmax, DELT=1.0e-3,
            RMIN=0.4, RMAX=0.8,
            PABS_WR=1.0,
        )
        fp.run(ntmax=args.ntmax)
        state = fp.get_state()

    print(f"TIMEFP = {state.timefp:.6e}")
    print(f"NRMAX  = {state.nrmax}  NSAMAX = {state.nsamax}")
    print(f"NPMAX  = {state.npmax}  NTHMAX = {state.nthmax}  NTG2 = {state.ntg2}")

    if state.RNT:
        head = state.RNT[0][: min(5, len(state.RNT[0]))]
        print(f"RNT[NSA=1, NR=1..{len(head)}] = "
              + ", ".join(f"{v: .3e}" for v in head))
    return 0


if __name__ == "__main__":
    sys.exit(main())
