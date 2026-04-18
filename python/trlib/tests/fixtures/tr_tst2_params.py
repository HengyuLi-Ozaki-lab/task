"""TST-2 parameters mirroring ``test_run/inputs/tr_tst2.in``.

Namelist block (lines 5..29 of the .in file) reproduced as Python data
for Layer 1 / Layer 4 replay via ``libtrapi.so``.

Unregistered keys are listed in ``UNREGISTERED_KEYS``; see the module
docstring of :mod:`tr_iter01_params` for the registry-growth protocol.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/tr_tst2/metrics.json``.
"""
from __future__ import annotations

SCALARS = {
    "NSMAX":  2,
    "RIPS":   0.015,
    "RIPE":   0.015,
    "NTSTEP": 1,
    "DT":     1.0e-5,
    "NTMAX":  10,
}

ARRAYS = {
    # PA(2)=1.0 and PZ(2)=1.0 in the namelist: we set the second element
    # only, relying on tr_init's defaults for index 1.
    "PA":  {2: 1.0},
    "PZ":  {2: 1.0},
    "PN":  [0.010, 0.010],
    "PNS": [0.001, 0.001],
    "PT":  [0.010, 0.0010],
    "PTS": [0.001, 0.0001],
}

# Keys present in tr_tst2.in but not yet in tr_param_registry.f90.
UNREGISTERED_KEYS = (
    "modelg", "KNAMEQ",
    "PROFN1", "PROFN2",
    "MDLIMP", "PNC",
    "PLHCD", "PLHR0", "PLHRW", "PLHNPR",
    "NGTSTP", "NGRSTP",
    "PLHTOT",
)

SOURCE_INPUT = "test_run/inputs/tr_tst2.in"
NTMAX = 10
BASELINE_NAME = "tr_tst2"


def _apply_array(tr, name, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val} dict)."""
    if isinstance(arr, dict):
        for i, v in arr.items():
            tr.set_param(f"{name}[{int(i)}]", float(v))
    else:
        for i, v in enumerate(arr, start=1):
            tr.set_param(f"{name}[{i}]", float(v))


def apply(tr) -> None:
    """Apply all *registered* TST-2 parameters to a Trlib instance."""
    for name, value in SCALARS.items():
        tr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        _apply_array(tr, name, arr)
