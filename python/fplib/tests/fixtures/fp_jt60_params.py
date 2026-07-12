"""JT-60 FP parameters mirroring ``test_run/inputs/fp_jt60.in`` (``&fp`` block).

A 3-species (NSMAX=3) FP run with MODELC=4 used as an additional Layer 1
case alongside fp_dt1 and fp_iter01. The Fortran namelist is reproduced
below as Python data so equivalence replay does not need to shell out to
the ``fp`` binary.

The ``KNAMFP=' '`` (empty string) entry in the namelist is a no-op in the
Python wrapper path (no file I/O happens via ``libfpapi.so``); it is
listed in :data:`UNREGISTERED_KEYS` for documentation only.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/fp_jt60/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters accepted by fp_param_registry.
SCALARS = {
    "NSMAX":   3,
    "NRMAX":   11,
    "RMIN":    0.1,
    "RMAX":    0.4,
    "NTMAX":   1,
    "NPMAX":   100,
    "NTHMAX":  100,
}

ARRAYS = {
    # PA(2)=2.0, PA(3)=1.0 in the namelist (PA(1) default).
    "PA":  {2: 2.0, 3: 1.0},
    # PZ(2)=1.0, PZ(3)=1.0 in the namelist (PZ(1) default).
    "PZ":  {2: 1.0, 3: 1.0},
    # PN(1)=0.3, 0.285, 0.015
    "PN":   [0.3,   0.285,  0.015],
    "PNS":  [0.03,  0.0285, 0.0015],
    "PTPR": [3.7,   3.7,    3.7],
    "PTPP": [3.7,   3.7,    3.7],
    "PTS":  [0.4,   0.4,    0.4],
    # Fortran namelist `PMAX=20.D0` sets ONLY PMAX(1)=20; PMAX(2..NSMAX)
    # keep fp_init defaults (0.0). Writing [20,20,20] would broadcast
    # and shift NSB=2,3 DELP (fp/fpprep.f90:181) away from baseline.
    "PMAX":   {1: 20.0},
    # Same Fortran namelist rule: MODELC=4 sets MODELC(1)=4 only;
    # MODELC(2..NSMAX) stay at default 0 (different collision-operator
    # branch in fp/fpparm.f90:929).
    "MODELC": {1: 4},
}

# Namelist keys that are not (or do not need to be) routed through
# fp_set_param in the wrapper path. KNAMFP=' ' is empty -> no file I/O.
# PROFN2 / PROFT2 are plcomm namelist keys with no entry in
# fp_param_registry.f90 (would return ierr=2 from fp.set_param).
UNREGISTERED_KEYS = (
    "KNAMFP",   # namelist filename (string; not a numeric param)
    "PROFN2",   # radial profile exponent (plcomm) - not in fp registry
    "PROFT2",   # temperature profile exponent (plcomm) - not in fp registry
)

SOURCE_INPUT = "test_run/inputs/fp_jt60.in"
NTMAX = 1
BASELINE_NAME = "fp_jt60"


def _apply_array(fp, name, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val} dict)."""
    if isinstance(arr, dict):
        for i, v in arr.items():
            fp.set_param(f"{name}[{int(i)}]", float(v))
    else:
        for i, v in enumerate(arr, start=1):
            fp.set_param(f"{name}[{i}]", float(v))


def apply(fp) -> None:
    """Apply all *registered* JT-60 parameters to an :class:`Fplib` instance."""
    for name, value in SCALARS.items():
        fp.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        _apply_array(fp, name, arr)
