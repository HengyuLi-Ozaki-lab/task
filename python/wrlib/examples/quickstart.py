"""Smallest possible Wrlib run: init, set a few params, run, print.

Mirrors the ITER LHCD ray-tracing case from
``test_run/inputs/wr_iter_lhcd.in`` with ``NRAYMAX`` trimmed to 1 so
the example finishes in a few seconds.

Run from the repository root::

    PYTHONPATH=python python3 python/wrlib/examples/quickstart.py

Prerequisites:
  - ``make -C wr libwrapi.so`` has been run once.
  - Optional: ``WRLIB_PATH`` set if the library lives outside the repo.
"""
from __future__ import annotations

import argparse
import sys

from wrlib import Wrlib


def _apply_iter_lhcd(wr: Wrlib) -> None:
    """Apply a trimmed ``wr_iter_lhcd`` namelist to an open Wrlib handle."""
    wr.set_params(MODELG=2, RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33, BB=5.3,
                  RIP=15.0, NSMAX=2,
                  PROFN1=2.0, PROFN2=2.0, PROFT1=2.0, PROFT2=1.0,
                  NRAYMAX=1, NSTPMAX=1000, NRSMAX=50, NRLMAX=100,
                  MDLWRI=101, MDLWRQ=0, MDLWRW=0,
                  SMAX=5.0, DELS=0.05)
    # Per-species (D + electrons)
    wr.set_param("PA[1]", 2.0);    wr.set_param("PA[2]", 1.0)
    wr.set_param("PZ[1]", 1.0);    wr.set_param("PZ[2]", -1.0)
    wr.set_param("PN[1]", 1.0);    wr.set_param("PN[2]", 1.0)
    wr.set_param("PNS[1]", 0.1);   wr.set_param("PNS[2]", 0.1)
    wr.set_param("PTPR[1]", 10.0); wr.set_param("PTPP[1]", 10.0)
    wr.set_param("PTPR[2]", 10.0); wr.set_param("PTPP[2]", 10.0)
    wr.set_param("PTS[1]", 0.5);   wr.set_param("PTS[2]", 0.5)
    # LH launcher at R=8.0 m, 5 GHz, 30 deg toroidal angle
    wr.set_param("RFIN[1]", 5.0e3)
    wr.set_param("RPIN[1]", 8.0)
    wr.set_param("ZPIN[1]", 0.0)
    wr.set_param("PHIIN[1]", 0.0)
    wr.set_param("ANGZIN[1]", 0.0)
    wr.set_param("ANGPHIN[1]", 30.0)
    wr.set_param("UUIN[1]", 1.0)
    wr.set_param("MODEWIN[1]", 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nray-request", type=int, default=0,
                        help="override NRAYMAX for wr_run (0 keeps namelist)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate argument parsing only; skip FFI calls")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"[dry-run] would call Wrlib().run(nray_request={args.nray_request})")
        return 0

    with Wrlib() as wr:
        _apply_iter_lhcd(wr)
        wr.run(nray_request=args.nray_request)
        state = wr.get_state()

    print(f"NRAYMAX={state.nraymax}  NRSMAX={state.nrsmax}  "
          f"NRLMAX={state.nrlmax}")
    print(f"pos_pwrmax_rs = {state.scalars['pos_pwrmax_rs']:.6g}")
    print(f"pwrmax_rs     = {state.scalars['pwrmax_rs']:.6g}")
    print(f"pos_pwrmax_rl = {state.scalars['pos_pwrmax_rl']:.6g}")
    print(f"pwrmax_rl     = {state.scalars['pwrmax_rl']:.6g}")

    if state.nstp_end:
        print(f"ray 1 ended at step {state.nstp_end[0]}")
    if state.pos_nrs:
        head = ", ".join(f"{v:.3g}" for v in state.pos_nrs[:5])
        print(f"first 5 pos_nrs = [{head}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
