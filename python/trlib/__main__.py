"""``python -m trlib <config.toml>`` — TOML-driven runner.

Pipeline::

    init → apply_config → run(ntmax) → get_state → run_plots → finalize

Exit codes:

* 0 — success
* 1 — library / calculation error
* 2 — config error (missing file, malformed TOML, unknown variable)

Flags:

* ``--dry-run`` — parse and validate the TOML, print a summary, but
  skip every libtrapi.so call. Useful for CI and quick verification.
* ``--ntmax N`` — override ``[module].ntmax`` / ``[scalars].NTMAX``.
* ``--no-plots`` — apply scalars/arrays and run, but skip every plot
  spec. Handy when matplotlib is not installed in the runner env.
* ``--help`` — argparse-generated usage.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from .loader import apply_config, load_config, run_plots, run_sweep_plots


_EXIT_OK = 0
_EXIT_LIB = 1
_EXIT_CONFIG = 2


def build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser used by :func:`main`."""
    parser = argparse.ArgumentParser(
        prog="python -m trlib",
        description=(
            "Run a TASK/TR simulation defined by a TOML config file and "
            "optionally render plots. See python/trlib/samples/ for "
            "example configurations."
        ),
    )
    parser.add_argument(
        "config", type=Path,
        help="Path to a TOML config file.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse the config and print a summary; skip every library call.",
    )
    parser.add_argument(
        "--ntmax", type=int, default=None,
        help="Override the NTMAX scalar from the config.",
    )
    parser.add_argument(
        "--no-plots", action="store_true",
        help="Skip [plot] / [[plots]] execution even if the config defines them.",
    )
    return parser


def _summarise(cfg: dict) -> str:
    """Return a short human-readable summary of a parsed config."""
    lines = []
    module = cfg.get("module") or {}
    lines.append(f"module: {module.get('name', '<unnamed>')}")
    ntmax = cfg.get("scalars", {}).get("NTMAX")
    if ntmax is not None:
        lines.append(f"NTMAX:  {ntmax}")
    lines.append(f"scalars: {len(cfg.get('scalars', {}))} keys")
    lines.append(f"arrays:  {len(cfg.get('arrays', {}))} keys")
    lines.append(f"strings: {len(cfg.get('strings', {}))} keys")
    lines.append(f"plots:   {len(cfg.get('plots', []))} specs")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Program entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # --- Config load ---------------------------------------------------
    if not args.config.exists():
        print(f"[trlib] config not found: {args.config}", file=sys.stderr)
        return _EXIT_CONFIG
    try:
        cfg = load_config(args.config)
    except Exception as exc:
        print(f"[trlib] failed to parse {args.config}: {exc}", file=sys.stderr)
        return _EXIT_CONFIG

    # --- CLI overrides -------------------------------------------------
    if args.ntmax is not None:
        cfg.setdefault("scalars", {})["NTMAX"] = int(args.ntmax)
    if args.no_plots:
        cfg["plots"] = []

    # --- Summary + dry run --------------------------------------------
    print(f"[trlib] loaded {args.config}")
    print(_summarise(cfg))
    if args.dry_run:
        print("[trlib] --dry-run: skipping library calls")
        return _EXIT_OK

    ntmax = int(cfg.get("scalars", {}).get("NTMAX", 0))

    # --- Live run ------------------------------------------------------
    # Lazy import: importing ``Trlib`` triggers _ffi.load_library() which
    # probes libtrapi.so. Doing this only inside the live branch keeps
    # --dry-run functional on systems where the .so is not built.
    try:
        from . import Trlib
    except Exception as exc:  # pragma: no cover - extremely unusual
        print(f"[trlib] cannot import Trlib: {exc}", file=sys.stderr)
        return _EXIT_LIB

    try:
        # State-dependent plots run inside the with-block (need live tr).
        with Trlib() as tr:
            apply_config(tr, cfg)
            tr.run(ntmax=ntmax)
            state = tr.get_state()
            print(
                f"[trlib] run complete: NT={state.nt} NRMAX={state.nrmax} "
                f"NSMAX={state.nsmax}"
            )
            if cfg.get("plots"):
                try:
                    results = run_plots(tr, cfg)
                except ImportError as exc:
                    print(f"[trlib] plot backend unavailable: {exc}",
                          file=sys.stderr)
                    return _EXIT_CONFIG
                for name, descriptor in results:
                    print(f"[trlib] plot {name} -> {descriptor}")
        # Sweep plots run AFTER the outer Trlib closes — each sweep
        # sample needs its own tr_init/tr_run/tr_finalize cycle and
        # would collide with the still-live outer instance.
        if cfg.get("plots"):
            try:
                sweep_results = run_sweep_plots(cfg)
            except ImportError as exc:
                print(f"[trlib] plot backend unavailable: {exc}",
                      file=sys.stderr)
                return _EXIT_CONFIG
            for name, descriptor in sweep_results:
                print(f"[trlib] plot {name} -> {descriptor}")
    except Exception as exc:
        print(f"[trlib] library error: {exc}", file=sys.stderr)
        return _EXIT_LIB

    return _EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
