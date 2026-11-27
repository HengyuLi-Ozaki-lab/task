"""A failed ``eq_run`` says so, and ``eq_last_error`` says why.

* A g-eqdsk load (``MODELG=5``) of a missing file used to return
  ``EQ_OK`` with the previous equilibrium still in place: ``EQ_READ``
  called ``EQCALQ`` after ``EQDSKR`` failed, and ``EQCALQ`` reset the
  error. In a fresh session ``EQCALQ`` then ran on an empty state and
  the process died.
* ``eq_last_error`` (``Eq.last_error()``) returns the reason for the
  most recent failed ``eq_run`` ('' after a success), and ``Eq.run()``
  puts it in the exception, which the eq MCP server passes on.
"""
from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from eqlib import Eq, EqlibCalculationFailedError  # noqa: E402
from eqlib import _ffi  # noqa: E402

LIB_PATH = _ffi._default_lib_path()
FIXTURES_DIR = HERE.parent / "fixtures"
FIXTURE_EQDATA = FIXTURES_DIR / "eqdata.ITER01"

pytestmark = [
    pytest.mark.skipif(
        not LIB_PATH.exists(),
        reason=f"{LIB_PATH.name} not found at {LIB_PATH}; "
        "run `make -C eq libeqapi.so`",
    ),
    pytest.mark.skipif(
        not FIXTURE_EQDATA.exists(), reason=f"fixture {FIXTURE_EQDATA} missing"
    ),
]


@contextlib.contextmanager
def _pushd(target: Path):
    """Run the body with ``cwd`` switched to ``target`` (KNAMEQ is relative)."""
    prev = Path.cwd()
    os.chdir(target)
    try:
        yield target
    finally:
        os.chdir(prev)


def _load_iter01(eq: Eq):
    with _pushd(FIXTURES_DIR):
        eq.set_param("MODELG", 3)
        eq.set_param_str("KNAMEQ", FIXTURE_EQDATA.name)
        eq.run(mode=1)
    return eq.get_state()


def test_missing_geqdsk_fails_and_keeps_the_previous_equilibrium(tmp_path):
    with Eq() as eq:
        before = _load_iter01(eq)
        assert eq.last_error() == ""
        with _pushd(tmp_path):
            eq.set_param("MODELG", 5)
            eq.set_param_str("KNAMEQ", "no_such_geqdsk")
            with pytest.raises(EqlibCalculationFailedError) as failed:
                eq.run(mode=1)
        reason = eq.last_error()
        after = eq.get_state()
    assert "no_such_geqdsk" in reason and "not found" in reason
    assert reason in str(failed.value)
    # EQDSKR stopped at the open: nothing in the state changed.
    assert after.to_dict() == before.to_dict()


def test_file_load_with_an_analytic_modelg_fails_with_the_reason():
    """eq_run(mode=1) needs a file MODELG; the default MODELG=2 is not one."""
    with Eq() as eq:
        eq.set_param("MODELG", 2)
        with pytest.raises(EqlibCalculationFailedError) as failed:
            eq.run(mode=1)
        reason = eq.last_error()
    assert "MODELG=2" in reason
    assert reason in str(failed.value)
