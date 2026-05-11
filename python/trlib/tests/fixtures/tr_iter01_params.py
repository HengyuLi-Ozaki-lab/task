"""ITER01 parameters mirroring ``test_run/inputs/tr_iter01.in``.

The namelist block (lines 5..34 of the .in file) is reproduced here as
Python data so Layer 1 (equivalence) and Layer 4 (sweep) tests can
replay the same physics case via ``libtrapi.so`` without shelling out to
``tr2``.

Registered in ``tr/tr_param_registry.f90``:
  - L-3 initial set: NSMAX, DT, NTSTEP, NTMAX, RIPS, RIPE, PN/PNS/PT/PTS
  - L-6 extension:   MODELG, PROFN2, MDLNF,
                     PNBTOT/PNBR0/PNBRW/PNBENG/PNBRTG,
                     PIC*, PEC*, PLH* scalars, and KNAMEQ via
                     ``tr_param_set_str``.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/tr_iter01/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters that tr_param_registry accepts through tr_param_set.
# Values copied verbatim from test_run/inputs/tr_iter01.in.
SCALARS = {
    "MODELG": 3,
    "NSMAX":  4,
    "PROFN2": 0.15,
    "MDLNF":  1,
    "PNBTOT": 25.0,
    "PNBR0":  0.0,
    "PNBRW":  1.0,
    "PNBENG": 1000.0,
    "PNBRTG": 6.2,
    "PICCD":  0.1,
    "PICR0":  0.0,
    "PICRW":  0.2,
    "PICNPR": 5.0,
    "PECCD":  0.5,
    "PECR0":  1.1,
    "PECRW":  0.05,
    "PECNPR": 5.0,
    "PLHCD":  1.0,
    "PLHR0":  0.8,
    "PLHRW":  0.2,
    "PLHNPR": 2.0,
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

# String-valued parameters routed through tr_param_set_str
# (libtrapi.so >= L-6).
STRINGS = {
    "KNAMEQ": "eqdata.ITER01",
}

# All namelist keys now flow through the registry. Kept as an empty
# tuple so existing consumers (tests, docs) keep working after the
# L-6 registry extension.
UNREGISTERED_KEYS: tuple = ()

# Input file this fixture mirrors (relative to repo root).
SOURCE_INPUT = "test_run/inputs/tr_iter01.in"

# Layer-1 NTMAX used by the baseline (so the equivalence test runs the
# same number of time-steps as the Fortran driver did).
NTMAX = 100

# Name of the Phase-0 baseline directory under test_run/baselines/.
BASELINE_NAME = "tr_iter01"


def apply(tr) -> None:
    """Apply all registered ITER01 parameters to a Trlib instance.

    Parameters
    ----------
    tr:
        An open :class:`trlib.Trlib` handle.
    """
    for name, value in STRINGS.items():
        tr.set_param_str(name, str(value))
    for name, value in SCALARS.items():
        tr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            tr.set_param(f"{name}[{i}]", float(v))
