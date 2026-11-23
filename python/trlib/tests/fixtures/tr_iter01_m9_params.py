"""ITER under MODELG 9 in three stages, mirroring ``test_run/inputs/tr_iter01_m9.in`` (RESULTS section 5, NTEQIT 0).

``tr2`` reads the file as ``r`` (1500 steps, RIP 2 to 7 MA), then ``c`` (2000 steps, RIP 7 to 9 MA, heating on), then
``c`` (6500 steps, flat). The library does the same as ``run(1500)``, the sets of stage 2, ``continue_run(2000)``,
``continue_run(6500)``. The ``eq:`` names are EQ's ``eqparm`` of the case (``test_run/inputs/tr_iter01_m9.eqparm``);
they are set before the first preparation, as the library requires. EQ's ``RR``, ``RA``, ``RKAP``, ``RDLT``, ``BB`` and
``RIP`` of that file are TR's own under MODELG 9 and are not repeated.

The baseline is ``tr2``'s dump at the end of the third stage. ``tr2``'s ``C`` starts ``NT`` at 0 again, so its ``NT``
is the third stage's 6500 where the library's is 10000 (``tr/tr_api.h``); the equivalence test moves the library's
``NT`` to ``tr2``'s before it compares. Every stage length is a multiple of ``NTSTEP`` (250) and ``NGTSTP`` (2), the
step counts ``tr2`` and the library count from different origins.
"""
from __future__ import annotations

# Stage 1 (before ``r``): tr.ITER01's namelist. NTMAX is the first call's step count.
SCALARS = {
    "MODELG": 9,
    "NTEQIT": 0,
    "RR":     6.2,
    "RA":     2.0,
    "RKAP":   1.7,
    "RDLT":   0.33,
    "BB":     5.3,
    "NSMAX":  4,
    "PROFN2": 0.15,
    "MDLNF":  1,
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
    "NTSTEP": 250,
    "RIPS":   2.0,
    "RIPE":   7.0,
}

ARRAYS = {
    "PN":  [0.7,   0.315,  0.315,  0.035],
    "PNS": [0.1,   0.045,  0.045,  0.005],
    "PT":  [1.0,   1.0,    1.0,    1.0],
    "PTS": [0.1,   0.1,    0.1,    0.1],
}

# EQ's eqparm of the case; set before the first run.
EQ = {
    "eq:RB":     2.1,
    "eq:NSGMAX": 128,
}

# The stages: (steps, control parameters set before it). Stage 1 is a run, the others continue it.
STAGES = [
    (1500, {}),
    (2000, {"RIPE": 9.0, "PNBTOT": 25.0, "PICTOT": 5.0, "PECTOT": 20.0}),
    (6500, {}),
]

# tr2's NT at the end of the last stage (its C starts NT at 0 again).
TR2_FINAL_NT = STAGES[-1][0]

SOURCE_INPUT = "test_run/inputs/tr_iter01_m9.in"
BASELINE_NAME = "tr_iter01_m9"


def apply(tr) -> None:
    """The namelist of stage 1 and EQ's names, through a Trlib handle."""
    for name, value in SCALARS.items():
        tr.set_param(name, float(value))
    for name, arr in ARRAYS.items():
        for i, v in enumerate(arr, start=1):
            tr.set_param(f"{name}[{i}]", float(v))
    for name, value in EQ.items():
        tr.set_param(name, float(value))


def run_stages(tr) -> None:
    """``run`` the first stage and ``continue_run`` the others, setting each stage's parameters before it."""
    for k, (steps, sets) in enumerate(STAGES):
        for name, value in sets.items():
            tr.set_param(name, float(value))
        if k == 0:
            tr.run(steps)
        else:
            tr.continue_run(steps)
