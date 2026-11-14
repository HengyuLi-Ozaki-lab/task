"""With MODELG 9, ``tr_run`` refuses a negative plasma current before the run; ``validate()`` reports it.

MODELG 9 has EQ solve the equilibrium with TR's own current (equnit's ``eq_calc``, from ``tr_set_metric`` and
every NTEQIT steps), and EQ's analytic solve does not treat the sign of the current: ``eq_run(0)`` refuses a negative
one (python/eqlib/tests/test_negative_current.py), but ``eq_calc`` calls EQCALC directly, which does not. So TR
checks RIPS and RIPE itself, in ``species_profile_violations`` (``tr/tr_api.f90``). On the TST-2 fixture with MODELG 9
and RIPS = RIPE = -0.015, EQ's iteration did not converge (XX EQLOOP: NLOOP exceeds NLPMAX), where it did with +0.015,
and the run went on. Another MODELG takes its current from a file, and the UFILE modes from the UFILE: neither is
checked. One test per case (``parametrize``, never ``subTest``).
"""
from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibParamError  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"
EQDATA = FIXTURES_DIR / "eqdata.TST-2"

pytestmark = [
    pytest.mark.skipif(not DEFAULT_SO.exists(), reason=f"libtrapi.so not built at {DEFAULT_SO}"),
    pytest.mark.skipif(not EQDATA.exists(), reason=f"fixture missing: {EQDATA}"),
]


@contextlib.contextmanager
def _pushd(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _tr(mutations: dict) -> Trlib:
    from trlib.tests.fixtures import tr_tst2_params as base
    tr = Trlib()
    base.apply(tr)
    tr.set_param("NTMAX", 2.0)
    for name, value in mutations.items():
        tr.set_param(name, float(value))
    return tr


@pytest.mark.parametrize("name", ["RIPS", "RIPE"])
def test_modelg_9_with_a_negative_current_is_refused_before_the_run(name):
    with _pushd(FIXTURES_DIR):
        tr = _tr({"MODELG": 9, name: -0.015})
        try:
            assert any(d.param == name for d in tr.validate())
            with pytest.raises(TrlibParamError):
                tr.run(2)
        finally:
            tr.close()


def test_modelg_9_with_a_positive_current_has_no_such_diagnostic():
    with _pushd(FIXTURES_DIR):
        tr = _tr({"MODELG": 9})
        try:
            assert not any(d.param in ("RIPS", "RIPE") for d in tr.validate())
        finally:
            tr.close()


def test_a_file_load_takes_its_current_from_the_file_and_is_not_checked():
    # MODELG 3 (the fixture): the equilibrium file's current replaces RIPS and RIPE.
    with _pushd(FIXTURES_DIR):
        tr = _tr({"RIPS": -0.015, "RIPE": -0.015})
        try:
            assert not any(d.param in ("RIPS", "RIPE") for d in tr.validate())
            tr.run(2)
        finally:
            tr.close()
