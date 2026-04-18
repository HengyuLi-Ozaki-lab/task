"""Smallest possible Trlib run: init, set a few scalars, run, print.

Run from the repository root::

    PYTHONPATH=python python3 python/trlib/examples/quickstart.py

Prerequisites:
  - ``make -C tr libtrapi.so`` has been run once.
  - Optional: ``TRLIB_PATH`` set if the library lives outside the repo.
"""
from __future__ import annotations

import argparse
import sys

from trlib import Trlib


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=50,
                        help="time-steps to advance (default: 50)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate argument parsing only; skip FFI calls")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"[dry-run] would call Trlib().run(ntmax={args.ntmax})")
        return 0

    with Trlib() as tr:
        # ITER-like geometry (truncated; see tests/fixtures/ for full set).
        tr.set_params(RR=8.5, RA=2.0, RKAP=1.7, BB=5.3,
                      NSMAX=2, DT=0.1, NTSTEP=10)
        tr.set_param("PN[1]", 1.0)
        tr.set_param("PN[2]", 1.0)
        tr.set_param("PT[1]", 1.5)
        tr.set_param("PT[2]", 1.5)

        tr.run(ntmax=args.ntmax)
        state = tr.get_state()

    print(f"NT={state.nt}  NRMAX={state.nrmax}  NSMAX={state.nsmax}")
    print(f"T    = {state.scalars['T']:.6g}")
    print(f"WPT  = {state.scalars['WPT']:.6g}")
    print(f"Q0   = {state.scalars['Q0']:.6g}")
    print(f"BETAA= {state.scalars['BETAA']:.6g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
