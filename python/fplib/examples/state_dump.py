"""Run once and dump ``FpState.to_dict()`` as JSON.

Useful to compare fplib output to the Phase 0 baseline JSON produced
by the FP regression tooling — the ``profile`` / scalar layout is
compatible with ``compare_metrics.py``-style diffing.

Run from the repository root::

    PYTHONPATH=python python3 python/fplib/examples/state_dump.py \\
        --out /tmp/fplib_state.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from fplib import Fplib


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=2,
                        help="time-steps to run before snapshot (default: 2)")
    parser.add_argument("--out", type=Path, default=None,
                        help="output JSON path (default: stdout)")
    parser.add_argument("--indent", type=int, default=2,
                        help="JSON indent (default: 2)")
    parser.add_argument("--dry-run", action="store_true",
                        help="validate argument parsing only; skip FFI calls")
    args = parser.parse_args(argv)

    if args.dry_run:
        print(f"[dry-run] ntmax={args.ntmax} out={args.out}")
        return 0

    with Fplib() as fp:
        # Minimal fp_iter01-style setup, shrunk mesh for a fast dump.
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

    payload = state.to_dict()
    text = json.dumps(payload, indent=args.indent, sort_keys=True)
    if args.out is None:
        print(text)
    else:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}  "
              f"({len(payload['profile'])} species rows, "
              f"NRMAX={payload['NRMAX']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
