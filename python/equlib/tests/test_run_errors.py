"""``Equ.run``: the refusals and the failures that used to end the process.

QUEST with marker 1 moved to R = 0.5 (inside the plasma) makes eqtrc find
no starting point: eqerr used to STOP; with marker 0 at R = 0.2 the traced
contour outgrew its arrays (a bounds abort). Both now come back as
``EqulibCalculationFailedError`` and the handle stays usable.
"""
from __future__ import annotations

import pytest

from equlib import (Equ, EqulibCalculationFailedError, EqulibInvalidParamError,
                    EqulibNotImplementedError)
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


def test_run_with_the_defaults_names_the_coil_file(workdir):
    with Equ() as equ:
        with pytest.raises(EqulibInvalidParamError, match="KNAMCOIL"):
            equ.run(1)


@pytest.mark.parametrize("mode,exc", [(-1, EqulibInvalidParamError),
                                      (2, EqulibNotImplementedError),
                                      (True, EqulibInvalidParamError),
                                      (1.0, EqulibInvalidParamError)])
def test_modes(workdir, mode, exc):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        with pytest.raises(exc):
            equ.run(mode)


def test_no_starting_point_is_an_error_not_an_exit(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_param("RVAC[1]", 0.5)
        with pytest.raises(EqulibCalculationFailedError, match="no starting point"):
            equ.run(1)
        with pytest.raises(EqulibInvalidParamError, match="no equilibrium"):
            equ.get_state()
        # The library is usable afterwards.
        equ.reset()
        equ.read_parm("equparm")
        equ.run(0)
        assert equ.get_state().nr == 257


def test_contour_longer_than_its_arrays_is_an_error(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_param("RVAC[0]", 0.2)
        with pytest.raises(EqulibCalculationFailedError, match="isrzdm"):
            equ.run(1)


def test_mode0_state(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(0)
        st = equ.get_state()
    assert st.mode == 0
    assert (st.nr, st.nz, st.nv) == (257, 257, 101)
    assert st.fct_steps == 10           # eqset's "check of accuracy" loop
    assert 0.25 < st.ip < 0.35          # QUEST: TCUR = 0.3 MA
    assert st.pressure[0] > st.pressure[-1] >= 0.0
