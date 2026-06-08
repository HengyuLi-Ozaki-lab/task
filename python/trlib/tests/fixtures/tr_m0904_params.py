"""M0904 parameters mirroring ``test_run/inputs/tr_m0904.in``.

A MODELG=2 analytic-geometry TR case (RR=8.481m, RA=2.574m, ITER-scale
geometry but with the analytic profile path — no external eqdata
required). Used as a Layer 1 case alongside tr_iter01 and tr_tst2.

The Fortran-driver baseline at ``test_run/baselines/tr_m0904/metrics.json``
has a documented ``KNOWN_ISSUE.md`` describing environment-dependent
drift (308 mismatches at 1e-10 on different gfortran/libbpsd/LAPACK
builds, root-caused to external libs not source logic). The
Linux-canonical CI runner is the reference environment; if drift is
observed on that runner a new issue will be filed (see
docs/baseline-policy.md and feedback_equivalence_must_pass.md).

Edit cautiously: changing values invalidates the Layer 1 equivalence
test against ``test_run/baselines/tr_m0904/metrics.json``.
"""
from __future__ import annotations

SCALARS = {
    "MODELG":  2,
    "RR":      8.481,
    "RA":      2.574,
    "RKAP":    1.816,
    "RDLT":    0.3478,
    "BB":      5.953,
    "NSMAX":   4,
    "PROFN2":  0.15,
    "MDLNF":   1,
    "PNBR0":   1.0,
    "DT":      0.02,
    "NTSTEP":  50,
    "NTMAX":   50,
    "RIPS":    2.0,
    "RIPE":    3.0,
}

ARRAYS = {
    "PN":   [0.1,  0.045, 0.045, 0.005],
    "PNS":  [0.01, 0.0045, 0.0045, 0.0005],
    "PT":   [1.0,  1.0,   1.0,   1.0],
    "PTS":  [0.1,  0.1,   0.1,   0.1],
}

# No STRINGS dict: MODELG=2 is analytic geometry, no KNAMEQ required.

# Namelist keys NOT registered in tr/tr_param_registry.f90.
# MDNCLS (NCLASS toggle) and PNBCD (NBI current-drive switch) have no
# CASE entry in the registry today; pre-audit found grep returns 0 in
# tr_param_registry.f90. They appear in tr_m0904.in but cannot be set
# via the float-only ABI in this build.
UNREGISTERED_KEYS = (
    "MDNCLS",
    "PNBCD",
)

SOURCE_INPUT = "test_run/inputs/tr_m0904.in"
NTMAX = 50
BASELINE_NAME = "tr_m0904"


def _apply_array(tr, name, arr) -> None:
    """Set ``NAME[i]`` for each element of ``arr`` (list or {idx: val} dict)."""
    if isinstance(arr, dict):
        for i, v in arr.items():
            tr.set_param(f"{name}[{int(i)}]", float(v))
    else:
        for i, v in enumerate(arr, start=1):
            tr.set_param(f"{name}[{i}]", float(v))


def apply(tr) -> None:
    """Apply all registered M0904 parameters to a Trlib instance."""
    for name, value in SCALARS.items():
        tr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        _apply_array(tr, name, arr)
