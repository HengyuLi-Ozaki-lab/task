"""DEMO2014 parameters mirroring ``test_run/inputs/tot_demo2014_short.in``.

The standalone ``tot`` driver consumes the input file as a sequence of
interactive menu commands; the ``&eq`` namelist block embedded inside
sets the geometry below (lines 7-16 of ``tot_demo2014_short.in``).

For the L-6 equivalence test we replay the same physics through
``libtotapi.so`` via the ``Tot`` orchestrator, which fans out to the
per-module registries (eq, tr, fp, ti, wr, wrx). Every key MUST carry
an ``<ns>:`` namespace prefix; bare names are rejected by both the
Python guard and the Fortran dispatcher (rc=1).

L-3 / L-4 / L-5 stub status: ``tot_init`` / ``tot_run`` /
``tot_get_state`` / ``tot_finalize`` all currently return
``TOT_ERR_NOT_IMPL`` (rc=4). The Layer 1 equivalence test therefore
auto-skips until the L-6 fan-out lands on the .so. ``set_param`` /
``set_param_str`` work end-to-end today and are exercised by the
namespace dispatch tests in ``test_class_full.py`` and Layer 2.

Edit cautiously: if you change the values here you must regenerate
``test_run/baselines/tot_demo2014_short/metrics.json`` to keep Layer
1 consistent. See the L-6 plan at
``docs/superpowers/plans/2026-04-18-tot-library-L6-test-4layers.md``
Task 4 for the iteration protocol.
"""
from __future__ import annotations

import warnings

# Namespaced scalar parameters. Values copied verbatim from the &eq
# block of test_run/inputs/tot_demo2014_short.in (lines 8-14).
#
# We intentionally do NOT add tr:* overrides here -- the standalone
# tot driver never sets any &tr namelist for demo2014_short, so it
# inherits all transport defaults. Adding tr:* keys would diverge from
# the baseline. Leave it minimal and let Layer 1 verify the match.
SCALARS = {
    # --- &eq block (geometry) ---
    "eq:RR":   8.5,
    "eq:RA":   2.42,
    "eq:RKAP": 1.65,
    "eq:RDLT": 0.33,
    "eq:RB":   2.60,
    "eq:BB":   5.94,
    "eq:RIP":  12.3,
}

# Array parameters: 1-origin for everything except eq:PSIB which is
# 0-origin (eq_param_registry handles the index translation). Values
# are lists indexed from 1, or dicts {idx: value} for explicit
# subscripts.
ARRAYS: dict = {
    # No array entries in tot_demo2014_short.in.
}

# String-valued parameters routed through tot_set_param_str. tr: and
# eq: are the only namespaces that back string setters at L-3.
STRINGS = {
    "eq:KNAMEQ": "eqdata.demo2014",
}

# Namelist variables present in tot_demo2014_short.in but not yet
# routable through any per-module registry. Move keys out of this
# tuple as the registries grow.
UNREGISTERED_KEYS: tuple = ()

# Source input file this fixture mirrors (relative to repo root).
SOURCE_INPUT = "test_run/inputs/tot_demo2014_short.in"

# ``tot.run(ntmax=...)`` argument used by Layer 1. The standalone tot
# driver's `r` (run) command for demo2014_short runs the default tr
# loop (NTMAX from trparm defaults); the baseline's NT field shows
# 100 steps were taken so we mirror that here.
NTMAX = 100

# Name of the Phase 0 baseline directory under ``test_run/baselines/``.
BASELINE_NAME = "tot_demo2014_short"


def _apply_array(tot, name: str, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val} dict).

    Lists are 1-origin to match Fortran convention; dicts use the
    explicit subscript so 0-origin arrays (e.g. ``eq:PSIB[0:5]``)
    remain expressible.
    """
    if isinstance(arr, dict):
        for i, v in arr.items():
            tot.set_param(f"{name}[{int(i)}]", float(v))
    else:
        for i, v in enumerate(arr, start=1):
            tot.set_param(f"{name}[{i}]", float(v))


def apply(tot) -> None:
    """Apply all registered DEMO2014 parameters to a :class:`totlib.Tot` handle.

    Keys listed in :data:`UNREGISTERED_KEYS` are skipped silently;
    keys that the per-module registry rejects (because they are not
    yet exposed) emit a warning and continue, so a partial fixture
    still produces useful diagnostics rather than aborting on the
    first missing setter.
    """
    from totlib import TotlibError  # local import to avoid hard dep at collect time

    for name, value in STRINGS.items():
        if name in UNREGISTERED_KEYS:
            continue
        try:
            tot.set_param_str(name, str(value))
        except TotlibError as exc:
            warnings.warn(
                f"tot_demo2014 fixture: STRING {name} not registered yet: "
                f"{exc}; move it to UNREGISTERED_KEYS or extend the "
                "per-module registry."
            )
    for name, value in SCALARS.items():
        if name in UNREGISTERED_KEYS:
            continue
        try:
            tot.set_param(name, float(value))
        except TotlibError as exc:
            warnings.warn(
                f"tot_demo2014 fixture: SCALAR {name} not registered yet: "
                f"{exc}; move it to UNREGISTERED_KEYS or extend the "
                "per-module registry."
            )
    for name, arr in ARRAYS.items():
        if name in UNREGISTERED_KEYS:
            continue
        try:
            _apply_array(tot, name, arr)
        except TotlibError as exc:
            warnings.warn(
                f"tot_demo2014 fixture: ARRAY {name} not registered yet: {exc}"
            )
