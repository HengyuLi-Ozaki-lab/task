"""Smallest possible Tot run: init, set namespaced params, (would-)run, print.

Run from the repository root::

    PYTHONPATH=python python3 python/totlib/examples/quickstart.py --dry-run
    PYTHONPATH=python python3 python/totlib/examples/quickstart.py

Prerequisites:
  - ``make -C tot libtotapi.so`` has been run once.
  - Optional: ``TOTLIB_PATH`` set if the library lives outside the repo.

Stub status note:
  At Phase L-3/L-4, ``tot_run`` and ``tot_get_state`` are stubs that
  return ``TOT_ERR_NOT_IMPL``; this script catches that case so the
  wrapper exercise still completes. Once Phase L-6 lands fan-out, the
  ``run`` / ``get_state`` calls succeed and the printout shows real
  scalars.
"""
from __future__ import annotations

import argparse
import sys

from totlib import Tot, TotlibNotImplementedError


def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=10,
                        help="time-steps to advance (default: 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate argument parsing only; skip FFI calls")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"[dry-run] would call Tot().run(ntmax={args.ntmax})")
        print("[dry-run] would set: eq:RR=6.5, eq:BB=5.3, tr:DT=0.01, "
              "fp:NSMAX=2, ti:RR=6.5")
        return 0

    with Tot() as tot:
        # Namespaced parameters across the 6 backing registries.
        tot.set_params({
            "eq:RR":    6.5,   # equilibrium major radius [m]
            "eq:BB":    5.3,   # equilibrium toroidal field [T]
            "eq:RIP":   1.5,   # equilibrium plasma current [MA]
            "tr:RA":    2.0,   # transport minor radius [m]
            "tr:DT":    0.01,  # transport time step [s]
            "tr:NTMAX": args.ntmax,
            "fp:NSMAX": 2,     # FP species count
            "ti:RR":    6.5,   # TI major radius [m]
            "wrx:RFIN": 170.0, # WRX RF frequency [GHz]
        })
        # Array element: 1-origin per the per-module registry convention.
        tot.set_param("tr:PN[1]", 1.0)
        tot.set_param("tr:PN[2]", 1.0)

        try:
            tot.run(ntmax=args.ntmax)
            state = tot.get_state()
        except TotlibNotImplementedError as e:
            print(f"[stub] run/get_state not yet wired (L-6 fan-out pending): {e}")
            return 0

    print(f"NT={state.nt}  NRMAX={state.nrmax}  NSMAX={state.nsmax}")
    print(f"presence: tr={state.tr_present} ti={state.ti_present} "
          f"fp={state.fp_present} wr={state.wr_present}")
    if state.scalars:
        print(f"T    = {state.scalars['T']:.6g}")
        print(f"WPT  = {state.scalars['WPT']:.6g}")
        print(f"Q0   = {state.scalars['Q0']:.6g}")
        print(f"BETAA= {state.scalars['BETAA']:.6g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
