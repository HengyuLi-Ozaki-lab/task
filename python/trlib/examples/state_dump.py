"""Run once and dump ``TrState.to_dict()`` as JSON.

Useful to compare trlib output to the Phase 0 baseline JSON produced
by ``tools/extract_tr_metrics.py`` — the two layouts are identical.

Run from the repository root::

    PYTHONPATH=python python3 python/trlib/examples/state_dump.py \
        --out /tmp/trlib_state.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trlib import Trlib


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ntmax", type=int, default=20,
                        help="time-steps to run before snapshot (default: 20)")
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

    with Trlib() as tr:
        tr.set_params(RR=8.5, RA=2.0, RKAP=1.7, BB=5.3,
                      NSMAX=2, DT=0.1, NTSTEP=10)
        tr.set_param("PN[1]", 1.0)
        tr.set_param("PN[2]", 1.0)
        tr.set_param("PT[1]", 1.5)
        tr.set_param("PT[2]", 1.5)
        tr.run(ntmax=args.ntmax)
        state = tr.get_state()

    payload = state.to_dict()
    text = json.dumps(payload, indent=args.indent, sort_keys=True)
    if args.out is None:
        print(text)
    else:
        args.out.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}  "
              f"({len(payload['profile'])} radial rows, "
              f"{len(payload['scalars'])} scalars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
