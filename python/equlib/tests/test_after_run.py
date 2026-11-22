"""After a run: checks and sets do not touch the run's result (review H1).

The solver overwrites some inputs; the library keeps the inputs in an
image. A validate, a refused set and a failed read after a run use the
inputs and leave the run's values in place, so get_state and write_geqdsk
still report the run; a set that succeeds starts a new input and drops the
result.
"""
from __future__ import annotations

import pytest

from equlib import Equ, EqulibInvalidParamError
from equlib.tests._geqdsk import assert_same
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


@pytest.fixture
def ran(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(1)
        equ.write_geqdsk("before.geqdsk")
        yield equ, equ.get_state()


def _same_state(a, b):
    assert a.scalars == b.scalars
    assert a.cvac == b.cvac and a.profiles == b.profiles and a.rsu == b.rsu


def test_validate_leaves_the_result(ran):
    equ, before = ran
    assert equ.validate() == []
    _same_state(equ.get_state(), before)
    equ.write_geqdsk("after.geqdsk")
    assert_same("before.geqdsk", "after.geqdsk", rtol=0.0, atol=0.0)
    # The run's fitted coil currents are not the namelist's.
    assert any(c != 0.0 for c in before.cvac)


def test_refused_set_leaves_the_result(ran):
    equ, before = ran
    with pytest.raises(EqulibInvalidParamError):
        equ.set_param("NO_SUCH_NAME", 1)
    with pytest.raises(EqulibInvalidParamError):
        equ.set_param("IVAC[19]", 1)
    with pytest.raises(EqulibInvalidParamError):
        equ.set_param_str("DEVICE", "LONGER_THAN_8")
    _same_state(equ.get_state(), before)
    equ.write_geqdsk("after.geqdsk")
    assert_same("before.geqdsk", "after.geqdsk", rtol=0.0, atol=0.0)


def test_failed_read_leaves_the_result(ran, workdir):
    equ, before = ran
    (workdir / "bad").write_text(" &EQU NV=1, NOSUCH=1 &END\n")
    with pytest.raises(EqulibInvalidParamError):
        equ.read_parm("bad")
    _same_state(equ.get_state(), before)
    # ... and the inputs are as before the failed read.
    assert equ.validate() == []


def test_set_after_a_run_drops_the_result(ran):
    equ, _ = ran
    equ.set_param("TCUR", 0.28)
    with pytest.raises(EqulibInvalidParamError, match="no equilibrium"):
        equ.get_state()
