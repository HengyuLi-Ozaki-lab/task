"""A TR fusion switch changed between two runs of one ``tot`` session.

``tot``'s dispatch sets a TR parameter by calling ``tr_param_set`` itself
(``tot/tot_param_registry.f90``, ``dispatch_tr``).  Before upstream #259 that
did not clear ``tr_api``'s prepared flag, so after a first run nothing
prepared TR again.  A switch whose effect is fixed at prepare was then out of
step with the case, and ``MODEL_PNF`` is such a switch -- its reaction tables
and the flag that arms the path are set by ``tr_prep``.

Measured through this entry point before ``TRCALC`` read the switches of the
moment (tr_iter01 at 20 keV): ``tr:MODEL_PNF=1`` set after a first run was
ignored without a word; ``tr:MDLNF=1`` set after a ``MODEL_PNF=1`` run ran
both fusion paths into the same arrays, the pair ``tr_prep`` refuses; and
both set back to 0 went on publishing the fusion power.

Since #259 the registry counts every successful set, ``tot``'s included, and
``tr_run`` prepares again when the count has changed.  So a ``MODEL_PNF`` of
1 after a first run, and of 4 after a run at 1, are prepared for and run;
``MDLNF`` beside it and the undefined 9 are refused by ``tr_prep``, and 0 is
off.  ``TRCALC``'s own check of the switches stays for the paths that still
do not prepare again (the standalone ``tr2``'s ``L`` then ``C``).

``python/trlib/tests/test_model_pnf_dispatch.py`` holds the same rules by
writing the module variables between two ``Trlib.run`` calls.  This file goes
through ``libtotapi.so``.
"""

from __future__ import annotations

import ctypes
from pathlib import Path

import pytest

from totlib import Tot
from totlib.errors import TotlibError

TR_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "trlib" / "tests" / "fixtures"


def _hot_iter01(tot):
    """tr_iter01 through the ``tr:`` namespace, at 20 keV, legacy fusion off."""
    from trlib.tests.fixtures import tr_iter01_params as fixture

    for name, value in fixture.STRINGS.items():
        tot.set_param_str(f"tr:{name}", str(value))
    for name, value in fixture.SCALARS.items():
        tot.set_param(f"tr:{name}", float(value))
    for name, values in fixture.ARRAYS.items():
        for i, value in enumerate(values, 1):
            tot.set_param(f"tr:{name}[{i}]", float(value))
    for i in range(1, 5):
        tot.set_param(f"tr:PT[{i}]", 20.0)
        tot.set_param(f"tr:PTS[{i}]", 2.0)
    tot.set_param("tr:MDLNF", 0.0)


def _max_pnf():
    """The largest value of TR's published fusion power profile.

    Read from the image ``trlib`` resolves, which is the one ``Tot`` drives:
    ``libtrapi.so`` beside ``libtotapi.so`` in the per-module build, and the
    one mono image when ``MONO_LIB_PATH`` is set (both loaders look at that
    variable first).  If they were ever not the same, PNF would not be
    allocated in this one and the assertion below says so -- in a process
    that has not initialised TR through trlib before, as under --forked.
    """
    from trlib._ffi import load_library

    lib = load_library()
    nrmax = ctypes.c_int.in_dll(lib, "__trcom0_MOD_nrmax").value
    addr = ctypes.c_void_p.in_dll(lib, "__trcomm_profile_MOD_pnf").value
    assert addr, "TR's PNF is not allocated in the image trlib resolves: tot is driving another one"
    return max((ctypes.c_double * nrmax).from_address(addr))


@pytest.fixture(autouse=True)
def _switches_back_to_zero():
    """tot_finalize does not reset TR's switches, and a later init is what does.

    Under --forked that does not matter.  In one interpreter a test that left
    MODEL_PNF at 1, 4 or 9 would hand it to whatever loads the TR library
    next: test_libnf.py asserts that it finds 0.
    """
    yield
    from trlib._ffi import load_library

    lib = load_library()
    for symbol in ("__trcomm_param_MOD_model_pnf", "__trcomm_param_MOD_mdlnf"):
        ctypes.c_int.in_dll(lib, symbol).value = 0


def test_mdlnf_set_after_a_model_pnf_run_is_refused_and_the_case_goes_on(monkeypatch):
    monkeypatch.chdir(TR_FIXTURES_DIR)
    with Tot() as tot:
        _hot_iter01(tot)
        tot.set_param("tr:MODEL_PNF", 1.0)
        tot.run(1)
        published = _max_pnf()
        assert published > 0.0, "the premise: MODEL_PNF = 1 publishes a fusion power at 20 keV"

        tot.set_param("tr:MDLNF", 1.0)
        with pytest.raises(TotlibError):
            tot.run(1)
        assert _max_pnf() == published, "the refused step wrote the fusion power profile"

        tot.set_param("tr:MDLNF", 0.0)
        tot.run(1)
        assert _max_pnf() > 0.0


def test_model_pnf_set_back_to_zero_is_off(monkeypatch):
    monkeypatch.chdir(TR_FIXTURES_DIR)
    with Tot() as tot:
        _hot_iter01(tot)
        tot.set_param("tr:MODEL_PNF", 1.0)
        tot.run(1)
        assert _max_pnf() > 0.0, "the premise: it was publishing"

        tot.set_param("tr:MODEL_PNF", 0.0)
        tot.run(1)
        assert _max_pnf() == 0.0, "MODEL_PNF is 0 and the fusion power is still published"


def test_a_model_pnf_that_is_no_model_after_a_run_is_refused(monkeypatch):
    """9 is no model at all: tr_prep refuses it."""
    monkeypatch.chdir(TR_FIXTURES_DIR)
    with Tot() as tot:
        _hot_iter01(tot)
        tot.set_param("tr:MODEL_PNF", 1.0)
        tot.run(1)

        tot.set_param("tr:MODEL_PNF", 9.0)
        with pytest.raises(TotlibError):
            tot.run(1)

        # Refused for the switch and not for anything else: put back, it runs.
        tot.set_param("tr:MODEL_PNF", 1.0)
        tot.run(1)
        assert _max_pnf() > 0.0


def test_another_model_pnf_after_a_run_is_prepared_for(monkeypatch):
    """4 after a run at 1: TR prepares again (#259) and runs the 13 reactions.

    With more than one reaction the rates are evaluated and nothing reaches
    the solve, so nothing is published.
    """
    monkeypatch.chdir(TR_FIXTURES_DIR)
    with Tot() as tot:
        _hot_iter01(tot)
        tot.set_param("tr:MODEL_PNF", 1.0)
        tot.run(1)
        assert _max_pnf() > 0.0, "the premise: MODEL_PNF = 1 publishes a fusion power at 20 keV"

        tot.set_param("tr:MODEL_PNF", 4.0)
        tot.run(1)
        assert _max_pnf() == 0.0, "MODEL_PNF = 4 passes nothing to the solve"


def test_model_pnf_set_after_a_first_run_is_not_ignored(monkeypatch):
    """It was: the run went on at MODEL_PNF = 0 and said nothing.

    Since #259 TR prepares again for it and publishes the fusion power.
    """
    monkeypatch.chdir(TR_FIXTURES_DIR)
    with Tot() as tot:
        _hot_iter01(tot)
        tot.run(1)
        assert _max_pnf() == 0.0, "the premise: no fusion model is on"

        tot.set_param("tr:MODEL_PNF", 1.0)
        tot.run(1)
        assert _max_pnf() > 0.0, "MODEL_PNF = 1 set after a first run was ignored"
