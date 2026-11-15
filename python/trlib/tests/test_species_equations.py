"""``tr_run`` returns an error, and the process lives, when a species gets no equation or the electron is not species 1.

TR gives each species its equations by its mass alone (``TR_TABLE``, ``tr/trprep.f90``): the electron is
PA = AME/AMM to 1e-10 (place 1), hydrogen PA = 1 or deuterium 1.5 < PA < 2.5 (place 2; deuterium after a hydrogen
3), tritium 2.5 < PA < 3.5 (3; after hydrogen and deuterium 4), helium 3.5 < PA < 4.5 (4), carbon 9 < PA < 15
with NSMAX = 3 (3). Species 1..NSMAX must take these places once each, the electron as species 1; the places
follow the order of the species, so e/D/H gives two species place 2, while e/T/H is fine. When one matched no class, the table was left short and ``NEA(NSS(NEQ),NSV(NEQ))`` was written with index
-1 (trprep.f90); when two took one place, or one took a place above NSMAX, a species had no equation and the
solve stopped at trexec.f90 ("Index 0 of dimension 2 of array 'b'"); with the electron as species 2 the run
ended with WPT and TAUE1 NaN. Measured on the TST-2 fixture (NSMAX 2: e, H), each in its own process: each case
below that is refused now stopped the process before (rc 2), or ended NaN, and each case that runs ran before.
One test per case (``parametrize``, never ``subTest``).
"""
from __future__ import annotations

import contextlib
import math
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibRunError  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"
EQDATA = FIXTURES_DIR / "eqdata.TST-2"

pytestmark = [
    pytest.mark.skipif(not DEFAULT_SO.exists(), reason=f"libtrapi.so not built at {DEFAULT_SO}"),
    pytest.mark.skipif(not EQDATA.exists(), reason=f"fixture missing: {EQDATA}"),
]

NTMAX = 2
SP3 = {"PN[3]": 0.005, "PNS[3]": 0.0005, "PT[3]": 0.001, "PTS[3]": 0.0001}
SP4 = {"PN[4]": 0.002, "PNS[4]": 0.0002, "PT[4]": 0.001, "PTS[4]": 0.0001}


@contextlib.contextmanager
def _pushd(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _run(tr: Trlib, mutations: dict):
    from trlib.tests.fixtures import tr_tst2_params as base
    base.apply(tr)
    tr.set_param("NTMAX", float(NTMAX))
    for name, value in mutations.items():
        tr.set_param(name, float(value))
    tr.run(NTMAX)
    return tr.get_state()


def _finite(state) -> bool:
    return all(math.isfinite(v) for v in state.scalars.values())


NO_EQUATION = {
    "n2 tritium as species 2": {"PA[2]": 3.0},
    "n2 helium as species 2": {"PA[2]": 4.0, "PZ[2]": 2.0},
    "n2 mass 1.008": {"PA[2]": 1.008},
    "n2 mass 1.5": {"PA[2]": 1.5},
    "n2 carbon with NSMAX 2": {"PA[2]": 12.0, "PZ[2]": 6.0},
    "n2 mass 0": {"PA[2]": 0.0},
    "n2 two hydrogens, no electron": {"PA[1]": 1.0, "PZ[1]": 1.0},
    "n2 the electron to four digits": {"PA[1]": 0.0005446},
    "n2 deuterium first, the electron second": {"PA[1]": 2.0, "PZ[1]": 1.0,
                                                "PA[2]": 9.10938215e-31 / 1.672621637e-27, "PZ[2]": -1.0},
    "n3 helium as species 3": {"NSMAX": 3, "PA[2]": 2.0, "PA[3]": 4.0, "PZ[3]": 2.0, **SP3},
    "n3 mass 1.008 as species 3": {"NSMAX": 3, "PA[3]": 1.008, "PZ[3]": 1.0, **SP3},
    "n3 e, D, H (deuterium before the hydrogen)": {"NSMAX": 3, "PA[2]": 2.0, "PA[3]": 1.0, "PZ[3]": 1.0, **SP3},
    "n4 e, H, T, D (tritium before the deuterium)": {"NSMAX": 4, "PA[3]": 3.0, "PZ[3]": 1.0, "PA[4]": 2.0, "PZ[4]": 1.0,
                                                     **SP3, **SP4},
    "n4 carbon with NSMAX 4": {"NSMAX": 4, "PA[2]": 2.0, "PA[3]": 3.0, "PZ[3]": 1.0, "PA[4]": 12.0, "PZ[4]": 6.0,
                               **SP3, **SP4},
}

RUNS = {
    "n2 electron, hydrogen (the fixture)": {},
    "n2 electron, deuterium": {"PA[2]": 2.0},
    "n2 mass 1.51 is deuterium": {"PA[2]": 1.51},
    "n3 e, H, D": {"NSMAX": 3, "PA[3]": 2.0, "PZ[3]": 1.0, **SP3},
    "n3 e, D, T": {"NSMAX": 3, "PA[2]": 2.0, "PA[3]": 3.0, "PZ[3]": 1.0, **SP3},
    "n3 e, H, T": {"NSMAX": 3, "PA[3]": 3.0, "PZ[3]": 1.0, **SP3},
    "n3 e, T, H (another order)": {"NSMAX": 3, "PA[2]": 3.0, "PA[3]": 1.0, "PZ[3]": 1.0, **SP3},
    "n3 e, T, D (another order)": {"NSMAX": 3, "PA[2]": 3.0, "PA[3]": 2.0, "PZ[3]": 1.0, **SP3},
    "n4 e, D, T, He": {"NSMAX": 4, "PA[2]": 2.0, "PA[3]": 3.0, "PZ[3]": 1.0, "PA[4]": 4.0, "PZ[4]": 2.0,
                       **SP3, **SP4},
    "n4 e, H, D, T": {"NSMAX": 4, "PA[3]": 2.0, "PZ[3]": 1.0, "PA[4]": 3.0, "PZ[4]": 1.0, **SP3, **SP4},
    "n4 e, D, He, T (another order)": {"NSMAX": 4, "PA[2]": 2.0, "PA[3]": 4.0, "PZ[3]": 2.0, "PA[4]": 3.0,
                                       "PZ[4]": 1.0, **SP3, **SP4},
}


@pytest.mark.parametrize("case", sorted(NO_EQUATION))
def test_a_species_without_an_equation_is_an_error_and_the_handle_lives(case):
    from trlib.tests.fixtures import tr_tst2_params as base
    with _pushd(FIXTURES_DIR):
        with Trlib() as tr:
            with pytest.raises(TrlibRunError):
                _run(tr, NO_EQUATION[case])
            # The handle stays usable: the fixture as it is runs on it.
            base.apply(tr)
            for name, value in {"NSMAX": 2, "PA[1]": 9.10938215e-31 / 1.672621637e-27, "PZ[1]": -1,
                                "PA[2]": 1.0, "PZ[2]": 1.0}.items():
                tr.set_param(name, float(value))
            tr.run(NTMAX)
            assert _finite(tr.get_state())


@pytest.mark.parametrize("case", sorted(RUNS))
def test_species_that_take_each_place_once_run(case):
    with _pushd(FIXTURES_DIR):
        with Trlib() as tr:
            assert _finite(_run(tr, RUNS[case]))
