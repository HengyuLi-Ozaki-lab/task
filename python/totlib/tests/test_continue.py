"""``Tot.continue_run``: ``tr_continue`` through ``tot`` (PR 3 of #96, Task 7 of the plan).

``tot_continue`` calls TR's ``tr_continue``; ``tot`` runs only TR, as ``tot_run`` does. In the mono image ``trlib`` and
``tot`` reach one TR, so ``Tot.continue_run`` must equal ``Trlib.continue_run`` on the same ``tr:`` inputs. TOT's
``eq:`` setters refuse a set once TR has prepared the case (``tr_api_eq_set_refused_in_case``): such a set would make the
next ``tot_run`` prepare again, which TR's own route refuses until the pinned bpsd has k-yoshimi/bpsd#7. Before a
preparation, and in a new case after ``tot_finalize`` and ``tot_init``, they are taken as before. TR's process-wide
guard and its always-refused names are not applied in TOT.

The library is resolved before the tests enter the fixtures directory (a relative ``TOTLIB_PATH`` or
``MONO_LIB_PATH``).

One test per case (``--forked``). Run with MONO_LIB_PATH set and without.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from totlib import Tot
from totlib import _ffi as _tot_ffi
from totlib.errors import TotlibError, TotlibInvalidParamError, TotlibNotInitializedError

# Tot()'s and Trlib()'s own resolution (MONO_LIB_PATH, TOTLIB_PATH or TRLIB_PATH, tot/ or tr/, lib/), made absolute
# here, before the fixture below changes the directory.
_TOT_LIB = _tot_ffi._default_lib_path().resolve()
pytestmark = [
    pytest.mark.forked,
    pytest.mark.skipif(not _TOT_LIB.exists(), reason=f"libtotapi.so not found at {_TOT_LIB}"),
]


def _tr_lib() -> str:
    from trlib import _ffi as _tr_ffi
    return str(_tr_ffi._default_lib_path().resolve())


_TR_LIB = _tr_lib()

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "trlib" / "tests" / "fixtures"


def _hot(tot):
    from trlib.tests.fixtures import tr_iter01_params as fixture
    for name, value in fixture.STRINGS.items():
        tot.set_param_str(f"tr:{name}", str(value))
    for name, value in fixture.SCALARS.items():
        tot.set_param(f"tr:{name}", float(value))
    for name, values in fixture.ARRAYS.items():
        for i, value in enumerate(values, 1):
            tot.set_param(f"tr:{name}[{i}]", float(value))
    for i in range(1, 5):
        tot.set_param(f"tr:PT[{i}]", 10.0)
        tot.set_param(f"tr:PTS[{i}]", 1.0)


@pytest.fixture(autouse=True)
def _in_fixtures_dir():
    prev = os.getcwd()
    os.chdir(FIXTURES_DIR)
    yield
    os.chdir(prev)


def test_tot_continue_carries_nt_and_t_after_a_control_set():
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(10)
        s0 = tot.get_state()
        tot.set_param("tr:PECTOT", 1.0)
        tot.continue_run(10)
        s1 = tot.get_state()
        assert s1.nt == s0.nt + 10 and s1.scalars["T"] > s0.scalars["T"]


def test_tot_continue_equals_trlib_continue_on_the_same_inputs():
    from trlib import Trlib
    names = ("WPT", "PNFT", "Q0", "RIP", "PINT")
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(10)
        tot.set_param("tr:PECTOT", 1.0)
        tot.continue_run(10)
        via_tot = {n: tot.get_scalar(f"tr:{n}") for n in names}
        nt_tot = tot.get_state().nt
    from trlib.tests.fixtures import tr_iter01_params as fixture
    with Trlib(_TR_LIB) as tr:
        for name, value in fixture.STRINGS.items():
            tr.set_param_str(name, str(value))
        for name, value in fixture.SCALARS.items():
            tr.set_param(name, float(value))
        for name, values in fixture.ARRAYS.items():
            for i, value in enumerate(values, 1):
                tr.set_param(f"{name}[{i}]", float(value))
        for i in range(1, 5):
            tr.set_param(f"PT[{i}]", 10.0)
            tr.set_param(f"PTS[{i}]", 1.0)
        tr.run(10)
        tr.set_param("PECTOT", 1.0)
        tr.continue_run(10)
        assert tr.get_state().nt == nt_tot
        for n, v in via_tot.items():
            assert tr.get_scalar(n) == v, n


def test_tot_continue_is_refused_after_a_structural_tr_set_and_names_it():
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(5)
        tot.set_param("tr:RR", 3.0)
        with pytest.raises(TotlibInvalidParamError) as e:
            tot.continue_run(5)
        assert "RR" in str(e.value)


def test_an_eq_set_after_a_tot_run_is_refused_and_the_case_goes_on():
    # It would make the next tot_run prepare again (with bpsd before k-yoshimi/bpsd#7, past the splines of the first
    # preparation; on the split build with TR's own EQ, which the set never reaches).
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(5)
        with pytest.raises(TotlibInvalidParamError) as e:
            tot.set_param("eq:RB", 2.1)
        assert "eq:RB" in str(e.value)
        tot.continue_run(5)
        assert tot.get_state().nt == 10


def test_an_eq_string_set_after_a_tot_run_is_refused_and_the_case_goes_on():
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(5)
        with pytest.raises(TotlibInvalidParamError) as e:
            tot.set_param_str("eq:KNAMEQ", "x")
        assert "eq:KNAMEQ" in str(e.value)
        tot.continue_run(5)
        assert tot.get_state().nt == 10


def test_an_eq_set_after_a_failed_preparation_is_refused():
    # MODEL_PNF 5: tr_prep fails (set_usigmav_nf refuses it) before it sizes anything, so this refusal is conservative;
    # it pins the failed-preparation half of the guard (g_failed), as a tr_prep that fails later has sized the splines.
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.set_param("tr:MODEL_PNF", 5.0)
        with pytest.raises(TotlibError):
            tot.run(5)
        with pytest.raises(TotlibInvalidParamError):
            tot.set_param("eq:RB", 2.1)


def test_an_eq_name_with_a_blank_before_its_colon_is_refused_through_the_c_function_too():
    # tot_param_set takes "eq :RB" as an eq: name (the prefix is trimmed); totlib refuses it before the call.
    from totlib import _ffi
    import ctypes
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(5)
        lib = _ffi.load_library(str(_TOT_LIB))
        assert lib.tot_set_param(b"eq :RB", ctypes.c_double(2.1)) == 1
        assert lib.tot_set_param(b"eq" + b" " * 14 + b"x:RB", ctypes.c_double(2.1)) == 1   # the prefix is cut at 16
        tot.continue_run(5)
        assert tot.get_state().nt == 10


def test_an_eq_set_before_the_first_run_is_taken():
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.set_param("eq:RB", 2.1)
        tot.set_param_str("eq:KNAMEQ", "eqdata.ITER01")
        tot.run(5)
        tot.continue_run(5)
        assert tot.get_state().nt == 10


def test_a_new_case_takes_eq_sets_again():
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(5)
    with Tot(str(_TOT_LIB)) as tot:                 # tot_finalize, then tot_init: TR's lifecycle starts again
        tot.set_param("eq:RB", 2.1)
        _hot(tot)
        tot.run(5)
        assert tot.get_state().nt == 5


def test_tot_continue_before_a_run_is_refused():
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        with pytest.raises(TotlibInvalidParamError):
            tot.continue_run(5)


def test_tot_continue_refuses_a_negative_count():
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(5)
        with pytest.raises(TotlibError):
            tot.continue_run(-1)


def test_tot_continue_before_init_is_not_initialized():
    tot = Tot(str(_TOT_LIB))
    tot.close()
    with pytest.raises(TotlibError):
        tot.continue_run(1)


@pytest.mark.parametrize("bad", [2**31, 2**32 + 5, -1])
def test_tot_continue_refuses_a_count_a_c_int_cannot_hold(bad):
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        tot.run(5)
        with pytest.raises(TotlibInvalidParamError):
            tot.continue_run(bad)
        assert tot.get_state().nt == 5            # nothing ran: 2**32 + 5 used to wrap to 5 steps


@pytest.mark.parametrize("bad", [2**31, 2**32 + 5, -1])
def test_tot_run_refuses_a_count_a_c_int_cannot_hold(bad):
    with Tot(str(_TOT_LIB)) as tot:
        _hot(tot)
        with pytest.raises(TotlibInvalidParamError):
            tot.run(bad)


def test_tot_continue_c_function_before_tot_init_returns_2():
    """The C entry point itself (the Python closed-handle guard above never reaches it)."""
    from totlib import _ffi
    lib = _ffi.load_library(str(_TOT_LIB))
    assert lib.tot_continue(1) == 2
    assert lib.tot_continue(-1) == 2          # not initialised comes first, as in tot_run
    assert lib.tot_run(1) == 2
