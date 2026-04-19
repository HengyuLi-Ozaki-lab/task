"""ITER01 parameters mirroring ``test_run/inputs/fp_iter01.in``.

The ``&fp`` namelist block (lines 6..33 of the .in file) is reproduced
here as Python data so Layer 1 (equivalence) and Layer 4 (sweep) tests
can replay the same physics case via ``libfpapi.so`` without shelling
out to ``fp``.

Registered in ``fp/fp_param_registry.f90`` (L-3) -> forwarded here.
Unregistered namelist keys (``KNAMFP``, ``PROFN2``, ``NTSTEP_COLL``)
are listed in ``UNREGISTERED_KEYS`` for future registry growth -- they
are *not* set by :func:`apply`.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/fp_iter01/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters that fp_param_registry already accepts.
# Values copied verbatim from test_run/inputs/fp_iter01.in.
SCALARS = {
    "NSMAX":  3,
    "NRMAX":  40,
    "RMIN":   0.4,
    "RMAX":   0.8,
    "NTMAX":  2,
    "NPMAX":  50,
    "NTHMAX": 50,
    # MODELG omitted — fp_iter01.in does not set it, so the original
    # Phase 0 baseline ran with the pl_init default (MODELG=2,
    # analytical equilibrium). Setting MODELG=3 here triggered the
    # eq_load file path with a missing KNAMEQ default (='eqdata') and
    # produced silent-NaN cascades through BESEKNX.
    "MODELR": 1,
    "DELT":   1.0e-3,
    "NSAMAX": 1,
    "NSBMAX": 3,
    "PABS_WR": 1.0,
}

# Array parameters: 1-origin subscripts matching Fortran convention.
# ARRAYS values may be a list (applied to indices 1..N) or a dict
# {idx: value} for sparse writes that rely on fp_init defaults for
# unset slots.
ARRAYS = {
    # PA(2)=2.0, PA(3)=3.0 in the namelist (PA(1) left at fp_init default)
    "PA":    {2: 2.0, 3: 3.0},
    # PN=0.8, 0.4, 0.4  (1-origin)
    "PN":    [0.8, 0.4, 0.4],
    "PNS":   [0.01, 0.005, 0.005],
    "PTPR":  [20.0, 20.0, 20.0],
    "PTPP":  [20.0, 20.0, 20.0],
    # PMAX is scalar broadcast in the namelist (PMAX=10.D0) -> apply to
    # all three species explicitly.
    "PMAX":  [10.0, 10.0, 10.0],
    # MODELC is scalar broadcast in the namelist (MODELC=4) -> apply to
    # all three species explicitly.
    "MODELC": [4, 4, 4],
    # NS_NSA(1)=1
    "NS_NSA": {1: 1},
    # NS_NSB(1)=1, NS_NSB(2)=2, NS_NSB(3)=3
    "NS_NSB": {1: 1, 2: 2, 3: 3},
}

# Namelist keys that appear in fp_iter01.in but are not yet registered
# in fp_param_registry.f90. Adding them there will let us uncomment the
# corresponding lines below and tighten the Layer 1 match.
UNREGISTERED_KEYS = (
    "KNAMFP",        # namelist filename (string; not a numeric param)
    "PROFN2",        # radial profile exponent (plcomm)
    "NTSTEP_COLL",   # collision step-count
)

# Input file this fixture mirrors (relative to repo root).
SOURCE_INPUT = "test_run/inputs/fp_iter01.in"

# Layer-1 NTMAX used by the baseline (so the equivalence test runs the
# same number of time-steps as the Fortran driver did).
NTMAX = 2

# Name of the Phase-0 baseline directory under test_run/baselines/.
BASELINE_NAME = "fp_iter01"


def _apply_array(fp, name, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val} dict)."""
    if isinstance(arr, dict):
        for i, v in arr.items():
            fp.set_param(f"{name}[{int(i)}]", float(v))
    else:
        for i, v in enumerate(arr, start=1):
            fp.set_param(f"{name}[{i}]", float(v))


def apply(fp) -> None:
    """Apply all *registered* ITER01 parameters to an :class:`Fplib` instance.

    Parameters
    ----------
    fp:
        An open :class:`fplib.Fplib` handle.
    """
    for name, value in SCALARS.items():
        fp.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        _apply_array(fp, name, arr)
