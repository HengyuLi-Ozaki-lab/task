"""One TR mesh per process: ``tr_run`` refuses, and ``validate()`` reports, an ``NRMAX`` other than the first one.

bpsd sizes its equilibrium and metric splines at the first get and keeps that size, so a later preparation on a
larger mesh in the same process wrote past them (measured under MODELG 3: NaN everywhere, or SIGSEGV), across
``tr_finalize`` and ``tr_init`` too. Until the pinned bpsd resizes them (k-yoshimi/bpsd#7), ``mesh_violation``
(``tr/tr_api.f90``) holds every preparation of a process to the NRMAX of its first attempt, failed or not (tr_prep
sizes the splines before steps that can fail). Every test here is a process of its own (``--forked``), as a
task-web job is.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibParamError, TrlibRunError  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)


@pytest.mark.parametrize("second", [20, 40])
def test_another_nrmax_after_the_first_preparation_is_refused(second):
    with Trlib() as tr:
        tr.set_param("NRMAX", 30)
        tr.run(1)
        tr.set_param("NRMAX", second)
        assert "NRMAX" in [d.param for d in tr.validate()]
        with pytest.raises(TrlibParamError):
            tr.run(1)
        tr.set_param("NRMAX", 30)       # the handle stays usable on the first mesh
        assert tr.validate() == []
        tr.run(1)
        assert tr.get_state().nrmax == 30


def test_the_first_mesh_holds_across_finalize_and_init():
    with Trlib() as tr:
        tr.set_param("NRMAX", 30)
        tr.run(1)
    with Trlib() as tr:                 # tr_init sets NRMAX back to 50
        with pytest.raises(TrlibParamError):
            tr.run(1)
        tr.set_param("NRMAX", 30)
        tr.run(1)
        assert tr.get_state().nrmax == 30


def test_nrmax_may_change_before_the_first_preparation():
    with Trlib() as tr:
        tr.set_param("NRMAX", 30)
        tr.set_param("NRMAX", 40)
        tr.run(1)
        assert tr.get_state().nrmax == 40


def test_a_failed_first_preparation_fixes_the_mesh_too():
    with Trlib() as tr:
        tr.set_param("NRMAX", 30)
        tr.set_param("PA[2]", 40.0)       # TR_TABLE places no species of mass 40: tr_prep fails
        with pytest.raises(TrlibRunError):
            tr.run(1)
        tr.set_param("PA[2]", 2.0)
        tr.set_param("NRMAX", 40)
        with pytest.raises(TrlibParamError):
            tr.run(1)
        tr.set_param("NRMAX", 30)
        tr.run(1)
        assert tr.get_state().nrmax == 30
