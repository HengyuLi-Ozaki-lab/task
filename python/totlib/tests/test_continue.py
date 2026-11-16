"""``Tot.continue_run``: ``tr_continue`` through ``tot`` (PR 3 of #96, Task 7 of the plan).

``tot_continue`` calls TR's ``tr_continue``; ``tot`` runs only TR, as ``tot_run`` does. In the mono image ``trlib`` and
``tot`` reach one TR, so ``Tot.continue_run`` must equal ``Trlib.continue_run`` on the same ``tr:`` inputs. TOT's
``eq:`` setter does not go through TR's registry; it tells TR (``tr_param_note_external_set``), so an ``eq:`` set after
a preparation is structural for ``tr_continue`` too (``Trlib`` does the same; the guard of PR 1 that refuses most
``eq:`` names after the first preparation is not in TOT and is not added).

One test per case (``--forked``). Run with MONO_LIB_PATH set and without.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from totlib import Tot
from totlib.errors import TotlibError, TotlibInvalidParamError, TotlibNotInitializedError

_REPO = Path(__file__).resolve().parents[3]
pytestmark = [
    pytest.mark.forked,
    pytest.mark.skipif(
        not (os.environ.get("MONO_LIB_PATH") or os.environ.get("TOTLIB_PATH") or (_REPO / "tot" / "libtotapi.so").exists()),
        reason="libtotapi.so is not built",
    ),
]

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
    with Tot() as tot:
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
    with Tot() as tot:
        _hot(tot)
        tot.run(10)
        tot.set_param("tr:PECTOT", 1.0)
        tot.continue_run(10)
        via_tot = {n: tot.get_scalar(f"tr:{n}") for n in names}
        nt_tot = tot.get_state().nt
    from trlib.tests.fixtures import tr_iter01_params as fixture
    with Trlib() as tr:
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
    with Tot() as tot:
        _hot(tot)
        tot.run(5)
        tot.set_param("tr:RR", 3.0)
        with pytest.raises(TotlibInvalidParamError) as e:
            tot.continue_run(5)
        assert "RR" in str(e.value)


def test_tot_continue_is_refused_after_an_eq_set_and_names_it():
    with Tot() as tot:
        _hot(tot)
        tot.run(5)
        tot.set_param("eq:RB", 2.1)
        with pytest.raises(TotlibInvalidParamError) as e:
            tot.continue_run(5)
        assert "eq:RB" in str(e.value)


def test_tot_continue_is_refused_after_an_eq_string_set_and_names_it():
    with Tot() as tot:
        _hot(tot)
        tot.run(5)
        tot.set_param_str("eq:KNAMEQ", "x")
        with pytest.raises(TotlibInvalidParamError) as e:
            tot.continue_run(5)
        assert "eq:KNAMEQ" in str(e.value)


def test_a_tot_run_after_an_eq_set_prepares_again_and_continue_works_again():
    with Tot() as tot:
        _hot(tot)
        tot.run(5)
        tot.set_param("eq:RB", 2.1)
        tot.run(5)                      # prepares again: NT starts from 0
        assert tot.get_state().nt == 5
        tot.continue_run(5)
        assert tot.get_state().nt == 10


def test_a_failed_eq_set_does_not_make_continue_refuse():
    with Tot() as tot:
        _hot(tot)
        tot.run(5)
        with pytest.raises(TotlibError):
            tot.set_param("eq:NOSUCHNAME", 1.0)
        tot.continue_run(5)
        assert tot.get_state().nt == 10


def test_tot_continue_before_a_run_is_refused():
    with Tot() as tot:
        _hot(tot)
        with pytest.raises(TotlibInvalidParamError):
            tot.continue_run(5)


def test_tot_continue_refuses_a_negative_count():
    with Tot() as tot:
        _hot(tot)
        tot.run(5)
        with pytest.raises(TotlibError):
            tot.continue_run(-1)


def test_tot_continue_before_init_is_not_initialized():
    tot = Tot()
    tot.close()
    with pytest.raises(TotlibError):
        tot.continue_run(1)


@pytest.mark.parametrize("bad", [2**31, 2**32 + 5, -1])
def test_tot_continue_refuses_a_count_a_c_int_cannot_hold(bad):
    with Tot() as tot:
        _hot(tot)
        tot.run(5)
        with pytest.raises(TotlibInvalidParamError):
            tot.continue_run(bad)
        assert tot.get_state().nt == 5            # nothing ran: 2**32 + 5 used to wrap to 5 steps


@pytest.mark.parametrize("bad", [2**31, 2**32 + 5, -1])
def test_tot_run_refuses_a_count_a_c_int_cannot_hold(bad):
    with Tot() as tot:
        _hot(tot)
        with pytest.raises(TotlibInvalidParamError):
            tot.run(bad)


def test_tot_continue_c_function_before_tot_init_returns_2():
    """The C entry point itself (the Python closed-handle guard above never reaches it)."""
    from totlib import _ffi
    lib = _ffi.load_library()
    assert lib.tot_continue(1) == 2
    assert lib.tot_continue(-1) == 2          # not initialised comes first, as in tot_run
    assert lib.tot_run(1) == 2
