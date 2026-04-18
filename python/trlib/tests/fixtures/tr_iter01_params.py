"""ITER01 parameters mirroring ``test_run/inputs/tr_iter01.in``.

The namelist block (lines 5..34 of the .in file) is reproduced here as
Python data so Layer 1 (equivalence) and Layer 4 (sweep) tests can
replay the same physics case via ``libtrapi.so`` without shelling out to
``tr2``.

Registered in ``tr/tr_param_registry.f90`` (L-3) -> forwarded here.
Unregistered namelist keys (``modelg``, ``KNAMEQ``, ``PROFN2``,
``MDLNF``, ``PNBR0``, ``PNBRW``, ``PNBENG``, ``PNBRTG``, ``PICCD``,
``PICR0``, ``PICRW``, ``PICNPR``, ``PECCD``, ``PECR0``, ``PECRW``,
``PECNPR``, ``PLHCD``, ``PLHR0``, ``PLHRW``, ``PLHNPR``) are listed in
``UNREGISTERED_KEYS`` for future registry growth -- they are *not* set
by :func:`apply`.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/tr_iter01/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters that tr_param_registry already accepts.
# Values copied verbatim from test_run/inputs/tr_iter01.in.
SCALARS = {
    "NSMAX":  4,
    "DT":     0.02,
    "NTSTEP": 100,
    "NTMAX":  100,
    "RIPS":   2.0,
    "RIPE":   7.0,
}

# Array parameters: 1-origin subscripts matching Fortran convention.
# Each key is a bare name; the list is applied as NAME[1], NAME[2], ...
ARRAYS = {
    "PN":  [0.7,   0.315,  0.315,  0.035],
    "PNS": [0.1,   0.045,  0.045,  0.005],
    "PT":  [1.0,   1.0,    1.0,    1.0],
    "PTS": [0.1,   0.1,    0.1,    0.1],
}

# Namelist keys that appear in tr_iter01.in but are not yet registered
# in tr_param_registry.f90. Adding them there will let us uncomment the
# corresponding lines below and tighten the Layer 1 match.
UNREGISTERED_KEYS = (
    "modelg", "KNAMEQ",
    "PROFN2", "MDLNF",
    "PNBR0", "PNBRW", "PNBENG", "PNBRTG",
    "PICCD", "PICR0", "PICRW", "PICNPR",
    "PECCD", "PECR0", "PECRW", "PECNPR",
    "PLHCD", "PLHR0", "PLHRW", "PLHNPR",
)

# Input file this fixture mirrors (relative to repo root).
SOURCE_INPUT = "test_run/inputs/tr_iter01.in"

# Layer-1 NTMAX used by the baseline (so the equivalence test runs the
# same number of time-steps as the Fortran driver did).
NTMAX = 100

# Name of the Phase-0 baseline directory under test_run/baselines/.
BASELINE_NAME = "tr_iter01"


def apply(tr) -> None:
    """Apply all *registered* ITER01 parameters to a Trlib instance.

    Parameters
    ----------
    tr:
        An open :class:`trlib.Trlib` handle.
    """
    for name, value in SCALARS.items():
        tr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            tr.set_param(f"{name}[{i}]", float(v))
