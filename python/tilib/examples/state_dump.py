"""Run once and dump ``TiState.to_dict()`` as JSON.

Useful to compare tilib output to the Phase 0 baseline JSON produced
by the TI regression tooling — the profile/scalars layouts are
compatible with ``compare_metrics.py`` style diffing.

Run from the repository root::

    PYTHONPATH=python python3 python/tilib/examples/state_dump.py \\
        --out /tmp/tilib_state.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tilib import TiLib


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

    with TiLib() as ti:
        # Minimal ti_min-style setup so the run completes quickly.
        ti.set_params(NSMAX=1, NRMAX=10,
                      NTSTEP=1, NGTSTEP=1, NGRSTEP=1,
                      NTMAX=args.ntmax)
        ti.run(ntmax=args.ntmax)
        state = ti.get_state()

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
