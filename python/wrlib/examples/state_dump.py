"""Run once and dump ``WrState.to_dict()`` as JSON.

Useful to compare wrlib output to the Phase 0 baseline JSON produced
by ``tools/extract_wr_metrics.py`` — the two layouts are identical so
``compare_metrics.py`` can diff either source.

Run from the repository root::

    PYTHONPATH=python python3 python/wrlib/examples/state_dump.py \\
        --out /tmp/wrlib_state.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wrlib import Wrlib


def _apply_iter_lhcd(wr: Wrlib) -> None:
    """Apply a trimmed ``wr_iter_lhcd`` namelist (NRAYMAX=1, NSTPMAX=1000)."""
    wr.set_params(MODELG=2, RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33, BB=5.3,
                  RIP=15.0, NSMAX=2,
                  PROFN1=2.0, PROFN2=2.0, PROFT1=2.0, PROFT2=1.0,
                  NRAYMAX=1, NSTPMAX=1000, NRSMAX=50, NRLMAX=100,
                  MDLWRI=101, MDLWRQ=0, MDLWRW=0,
                  SMAX=5.0, DELS=0.05)
    wr.set_param("PA[1]", 2.0);    wr.set_param("PA[2]", 1.0)
    wr.set_param("PZ[1]", 1.0);    wr.set_param("PZ[2]", -1.0)
    wr.set_param("PN[1]", 1.0);    wr.set_param("PN[2]", 1.0)
    wr.set_param("PNS[1]", 0.1);   wr.set_param("PNS[2]", 0.1)
    wr.set_param("PTPR[1]", 10.0); wr.set_param("PTPP[1]", 10.0)
    wr.set_param("PTPR[2]", 10.0); wr.set_param("PTPP[2]", 10.0)
    wr.set_param("PTS[1]", 0.5);   wr.set_param("PTS[2]", 0.5)
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
    parser.add_argument("--out", type=Path, default=None,
                        help="output JSON path (default: stdout)")
    parser.add_argument("--indent", type=int, default=2,
                        help="JSON indent (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate argument parsing only; skip FFI calls")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"[dry-run] nray_request={args.nray_request} out={args.out}")
        return 0

    with Wrlib() as wr:
        _apply_iter_lhcd(wr)
        wr.run(nray_request=args.nray_request)
        state = wr.get_state()

    payload = state.to_dict()
    text = json.dumps(payload, indent=args.indent, sort_keys=True)
    if args.out is None:
        print(text)
    else:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}  "
              f"(NRAYMAX={payload['NRAYMAX']}, "
              f"NRSMAX={payload['NRSMAX']}, "
              f"NRLMAX={payload['NRLMAX']}, "
              f"{len(payload['scalars'])} scalars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
