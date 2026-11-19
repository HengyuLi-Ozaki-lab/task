"""``MDLEQE`` chooses which density follows from quasi-neutrality; it leaves every other equation solved.

With the densities evolved (``MDLEQN`` 1), ``MDLEQE`` 0 solves the ion densities and takes the electrons from
quasi-neutrality, 2 solves the electrons and takes the bulk ions from it (``tr/trexec.f90``). ``TR_TABLE``
(``tr/trprep.f90``) marks the equation that is not solved. For ``MDLEQE`` 2 it marked equation 3, the bulk-ion
density only when B_theta is not solved (``MDLEQB`` 0); with B_theta solved (``MDLEQB`` 1, the default) equation 3
is the electron temperature, which was then left out of the solve: the PLATO case below reached Te0 117 eV with
``MDLEQE`` 2 against 228 eV with ``MDLEQE`` 0. For a hydrogen plasma (Z = 1) the two choices are the same model,
and with ``MDLEQB`` 0 they agreed before the fix as after it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)

A = 0.18
# PLATO (R 0.7 m, a 0.18 m, B 0.3 T, 40 kA, hydrogen) with a gas puff and the densities evolved.
CASE = {"RR": 0.7, "RA": A, "RKAP": 1.9, "RDLT": 0.4, "BB": 0.3, "RIPS": 0.04, "RIPE": 0.04, "NSMAX": 2,
        "PA[2]": 1.0, "PZ[2]": 1.0, "PN[1]": 0.1, "PN[2]": 0.1, "PNS[1]": 0.01, "PNS[2]": 0.01,
        "PT[1]": 0.13, "PT[2]": 0.035, "PTS[1]": 0.01, "PTS[2]": 0.01, "MDLKAI": 31, "CK0": 12.0, "CK1": 12.0,
        "MDLNB": 0, "DT": 1.0e-4, "MDLEQN": 1, "MDLPSC": 1, "NPSCMAX": 1, "PSCTOT[1]": 50.0,
        "PSCR0[1]": 0.7 * A, "PSCRW[1]": 0.1 * A, "NSPSC[1]": 2}
# 0.1 s, about thirty energy confinement times: the two choices then agree to about 1e-9 (1e-13 at 0.2 s).
NTMAX = 1000


def _central(mdleqe: int, mdleqb: int):
    with Trlib() as tr:
        for name, value in {**CASE, "MDLEQE": mdleqe, "MDLEQB": mdleqb}.items():
            tr.set_param(name, float(value))
        tr.run(NTMAX)
        s = tr.get_state()
        return s.RT[0][0], s.RT[0][1], s.RN[0][0], s.scalars["WPT"]


@pytest.mark.parametrize("mdleqb", [1, 0], ids=["B_theta solved", "B_theta held"])
def test_the_electrons_or_the_ions_from_quasi_neutrality_reach_the_same_state(mdleqb):
    assert _central(2, mdleqb) == pytest.approx(_central(0, mdleqb), rel=1e-7)


_TABLE_SCRIPT = """
import json, sys
from trlib import Trlib
with Trlib() as tr:
    for name, value in json.loads(sys.argv[1]).items():
        tr.set_param(name, float(value))
    tr.run(1)
"""


def _equation_table(mdleqe: int, mdleqb: int):
    """{NEQ: (NSS, NSV, NNS, NST)} as TR_EQS_SELECT writes it to unit 6 in tr_prep (read from a child process:
    gfortran's unit 6 is buffered until the process ends)."""
    params = {**CASE, "MDLEQE": mdleqe, "MDLEQB": mdleqb}
    env = {**os.environ, "PYTHONPATH": str(PYTHON_ROOT)}
    out = subprocess.run([sys.executable, "-c", _TABLE_SCRIPT, json.dumps(params)], capture_output=True, text=True,
                         timeout=60, env=env, check=True).stdout.splitlines()
    head = next(i for i, line in enumerate(out) if line.split()[:5] == ["NEQ", "NSS", "NSV", "NNS", "NST"])
    table = {}
    for line in out[head + 1:]:
        cols = line.split()
        if len(cols) != 5 or not all(c.lstrip("-").isdigit() for c in cols):
            break
        table[int(cols[0])] = tuple(int(c) for c in cols[1:])
    return table


# (MDLEQE, MDLEQB) -> the equation quasi-neutrality fills: the electron density (NSS 1, NSV 1) for MDLEQE 0, the
# bulk-ion density (NSS 2, NSV 1) for MDLEQE 2; every other equation is solved (NST /= 0).
@pytest.mark.parametrize("mdleqe, mdleqb", [(0, 1), (2, 1), (0, 0), (2, 0)])
def test_quasi_neutrality_fills_the_density_it_names_and_nothing_else(mdleqe, mdleqb):
    table = _equation_table(mdleqe, mdleqb)
    filled = [(nss, nsv) for nss, nsv, _, nst in table.values() if nst == 0]
    assert filled == [(1, 1) if mdleqe == 0 else (2, 1)], table
