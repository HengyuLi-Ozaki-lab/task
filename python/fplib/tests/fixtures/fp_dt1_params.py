"""DT1 minimal parameters mirroring ``test_run/inputs/fp_dt1.in``.

A minimal (NRMAX=1) FP configuration used as a fast Layer 1 case. The
Fortran namelist is reproduced below as Python data so the equivalence
replay does not need to shell out to the ``fp`` binary.

Parameters not yet registered in ``fp/fp_param_registry.f90`` (the DEC /
PEC / RFEC / DLH / ... wave-heating knobs) are listed in
:data:`UNREGISTERED_KEYS`; they are *not* set by :func:`apply`, so
Layer 1 equivalence will be tight only for fields these unregistered
knobs do not affect. See fallback-policy in the L-6 plan.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/fp_dt1/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters accepted by fp_param_registry.
SCALARS = {
    "NSMAX":  4,
    "NRMAX":  1,
    "NTHMAX": 50,
    "NPMAX":  50,
    "MODELR": 1,
    "NTMAX":  1,
}

ARRAYS = {
    # PA(2)=2, PA(3)=3, PA(4)=4 in the namelist (PA(1) default).
    "PA":    {2: 2.0, 3: 3.0, 4: 4.0},
    # PZ(2)=1, PZ(3)=1, PZ(4)=2  (PZ(1) default).
    "PZ":    {2: 1.0, 3: 1.0, 4: 2.0},
    # PN(1)=1, 0.45, 0.45, 0.05
    "PN":    [1.0, 0.45, 0.45, 0.05],
    "PNS":   [0.1, 0.045, 0.045, 0.005],
    "PTPR":  [20.0, 20.0, 20.0, 20.0],
    "PTPP":  [20.0, 20.0, 20.0, 20.0],
    "PTS":   [1.0, 1.0, 1.0, 1.0],
    # PMAX=20.D0 scalar broadcast in namelist -> apply to all 4 species.
    "PMAX":  [20.0, 20.0, 20.0, 20.0],
    # MODELW(1)=0 (explicit index 1 in namelist)
    "MODELW": {1: 0},
}

# Namelist keys that appear in fp_dt1.in but are not yet registered in
# fp_param_registry.f90. These are wave-heating shape / EC / LH
# parameters; adding them would tighten the Layer 1 match.
UNREGISTERED_KEYS = (
    "DEC", "PEC1", "PEC2", "RFEC", "DELYEC",
    "DLH", "PLH1", "PLH2", "RLH",
)

SOURCE_INPUT = "test_run/inputs/fp_dt1.in"
NTMAX = 1
BASELINE_NAME = "fp_dt1"


def _apply_array(fp, name, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val} dict)."""
    if isinstance(arr, dict):
        for i, v in arr.items():
            fp.set_param(f"{name}[{int(i)}]", float(v))
    else:
        for i, v in enumerate(arr, start=1):
            fp.set_param(f"{name}[{i}]", float(v))


def apply(fp) -> None:
    """Apply all *registered* DT1 parameters to an :class:`Fplib` instance."""
    for name, value in SCALARS.items():
        fp.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        _apply_array(fp, name, arr)
