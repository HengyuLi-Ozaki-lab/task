"""JT-60 WRX ECCD parameters mirroring ``test_run/inputs/wrx_jt60.in``.

A 2-ray MODELG=2 analytic-geometry WRX run (RR=3.4m, RA=1.0m) used as a
Layer 1 case alongside wrx_iter01 and wrx_demo. The .in file's leading
menu lines (``0 / f / wrx_jt60.gs / c / p``) are driver-side and
bypassed by the Python wrapper; only the ``&wr`` namelist contents are
mirrored here.

The ``KNAMWR='wrx_jt60.data'`` namelist entry names the output data file
written by the Fortran driver; the wrapper does not perform that file
write so the key is listed in :data:`UNREGISTERED_KEYS`.

All array parameters in this fixture **must** be Python lists (not dicts);
``wrxlib`` fixture convention uses ``enumerate(arr, start=1)`` only -- a
dict-form array would silently iterate over keys (likely TypeError on
``float(name)``). A defensive ``assert isinstance(arr, list)`` in
:func:`apply` catches future fixture mistakes early.

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/wrx_jt60/metrics.json``.
"""
from __future__ import annotations

# Scalar parameters registered in wrx_param_registry.f90 with bare-name
# (idx=0) CASE entries. PROFN1/PROFN2/PROFT1/PROFT2 are NOT in this dict
# despite being scalar-form in the namelist; they are array-only per
# registry lines 113-125 and live in ARRAYS below as [v, v] (NSMAX=2),
# mirroring wrx_iter01_params.py:45-48 precedent.
SCALARS = {
    "BB":             3.5,
    "RA":             1.0,
    "RR":             3.4,
    "RB":             1.1,
    "NSMAX":          2,
    "MODELG":         2,
    "MDLWRQ":         1,
    "MODELQ":         0,
    "Q0":             1.2,
    "QA":             4.0,
    "PROFJ":          1,
    "MDLWRI":         2,
    "MDLWRW":         0,
    "MDLWRG":         1,
    "MDLWRP":         1,
    "pne_threshold":  1.0e-6,
    "DELS":           1.0e-3,
    "SMAX":           1.5,
    "NRAYMAX":        2,
}

# All arrays as lists (NOT dicts) -- see module docstring.
# PROFN1/PROFN2/PROFT1/PROFT2 broadcast to [v, v] for NSMAX=2 mirrors
# wrx_iter01_params.py:45-48 precedent; namelist `PROFN1=2` populates
# all species per the wrx registry's array semantics.
ARRAYS = {
    "PROFN1":  [2.0,  2.0],
    "PROFN2":  [1.0,  1.0],
    "PROFT1":  [2.0,  2.0],
    "PROFT2":  [1.0,  1.0],
    "MODELP":  [206,  206],
    "MODELV":  [3,    0],
    "PN":      [0.5,  0.5],
    "PNS":     [0.025, 0.025],
    "PTPR":    [5.0,  5.0],
    "PTPP":    [5.0,  5.0],
    "PTS":     [0.3,  0.3],
    "PA":      [2.0,  5.4462e-4],
    "PZ":      [1.0,  -1.0],
    # NCMIN(1)=-3, NCMIN(2)=-3 (per-element in the namelist; list form
    # because both indices 1 and 2 are present).
    "NCMIN":   [-3,   -3],
    "NCMAX":   [3,    3],
    # Fortran replicated initializer `RFIN(1)=2*110.D3` expanded to list.
    "RFIN":    [110.0e3, 110.0e3],
    "RPIN":    [4.5,  4.5],
    "ZPIN":    [0.0,  0.0],
    "PHIIN":   [0.0,  0.0],
    "UUIN":    [1.0,  1.0],
    "MODEWIN": [1,    1],
    # Per-ray distinct values:
    "ANGPIN":  [0.0,  10.0],
    "ANGTIN":  [15.0, 25.0],
}

# KNAMWR is an output filename used by the Fortran driver; the wrapper
# does not perform the file write, so the key is documented here and
# not applied.
UNREGISTERED_KEYS = (
    "KNAMWR",
)

SOURCE_INPUT = "test_run/inputs/wrx_jt60.in"

# wrxlib equivalence harness reads this attribute (see
# python/wrxlib/tests/test_equivalence.py:163-172). 0 means "keep
# whatever NRAYMAX was set via SCALARS" (= 2 here).
NRAY_REQUEST = 0

BASELINE_NAME = "wrx_jt60"


def apply(lib) -> None:
    """Apply all *registered* wrx_jt60 parameters to a Wrxlib instance.

    Parameters
    ----------
    lib:
        An open :class:`wrxlib.Wrxlib` handle.
    """
    for name, value in SCALARS.items():
        lib.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        # Defensive guard: wrxlib's enumerate path iterates list values;
        # a dict-form array would iterate dict keys and silently misapply.
        assert isinstance(arr, list), (
            f"wrx_jt60_params.ARRAYS[{name!r}] must be a list, "
            f"got {type(arr).__name__}"
        )
        for i, v in enumerate(arr, start=1):
            lib.set_param(f"{name}[{i}]", float(v))
