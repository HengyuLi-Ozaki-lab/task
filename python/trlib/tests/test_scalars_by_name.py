"""TR's global results by name: ``Trlib.scalar_names()``, ``get_scalar`` and ``TrState.scalars``.

The table is in ``tr/tr_api.f90`` (``scalar_table``); each unit is read from ``tr/trrslt_globals.f90``.
TRGLOB computes the globals on output steps and on a run's last step (group N), so they are current after
``tr_run``. One test per case (``parametrize``, never ``subTest``: it passes under ``--forked``).
"""
from __future__ import annotations

import ctypes
import math
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibError, TrlibParamError  # noqa: E402
from trlib import _ffi  # noqa: E402
from trlib.state import SCALAR_FIELDS  # noqa: E402

REPO = HERE.parents[3]
FIXTURES_DIR = HERE.parent / "fixtures"

pytestmark = [
    pytest.mark.forked,
    pytest.mark.skipif(not _ffi._default_lib_path().exists(),          # Trlib()'s own resolution: MONO_LIB_PATH,
                       reason=f"libtrapi.so not found at {_ffi._default_lib_path()}"),   # TRLIB_PATH, tr/, lib/
]

# The table of the plan's Task 5 (31 names), in the order the library lists them.
EXPECTED = (
    "T", "WPT", "AJT", "Q0", "BETA0", "BETAP0", "BETAA", "BETAN", "TAUE1", "TAUE2", "ZEFF0", "ALI", "RQ1", "AJRFT",
    "PNFT", "QF", "PINT", "POHT", "PNBT", "PRFST", "PEXST", "PRLT", "POUT",
    "AJOHT", "AJNBT", "AJBST", "RIP", "VLOOP", "WPDOT", "H98Y2", "TAUE98",
)


def test_every_enumerated_scalar_is_finite_after_steps():
    with Trlib() as t:
        t.run(20)                       # defaults; group N gives the globals of the last step
        names = t.scalar_names()
        assert len(names) == 31 and len(set(names)) == 31
        for n in names:
            assert math.isfinite(t.get_scalar(n)), n


def test_the_table_is_the_plans_table():
    with Trlib() as t:
        assert tuple(t.scalar_names()) == EXPECTED


def test_qf_matches_its_formula():
    with Trlib() as t:
        t.run(20)
        g = t.get_scalar
        denom = g("POHT") + g("PNBT") + g("PRFST") + g("PEXST")
        assert g("QF") == pytest.approx(5.0 * g("PNFT") / denom, rel=1e-12)


def _iter01_hot(t):
    from trlib.tests.fixtures import tr_iter01_params as HOT
    HOT.apply(t)
    for i in range(1, 5):
        t.set_param(f"PT[{i}]", 10.0)
        t.set_param(f"PTS[{i}]", 1.0)
    t.set_param("PICTOT", 5.0)            # ITER01 sets the profiles of the RF sources, not their powers [MW]
    t.set_param("PECTOT", 3.0)
    t.set_param("PLHTOT", 2.0)


def test_pint_includes_the_alpha_power_and_every_heating_power_is_counted():
    # trrslt_globals.f90: PINT = POHT + PNBT + PRFST + PNFT + PEXST.
    with Trlib() as t:                  # before the chdir: a relative TRLIB_PATH is resolved from the start cwd
        prev = os.getcwd()
        os.chdir(FIXTURES_DIR)
        try:
            _iter01_hot(t)
            t.run(10)
            g = t.get_scalar
            assert g("PNFT") > 0.0 and g("PNBT") > 0.0 and g("POHT") > 0.0 and g("PRFST") > 0.0
            assert g("PINT") == pytest.approx(g("POHT") + g("PNBT") + g("PRFST") + g("PNFT") + g("PEXST"),
                                              rel=1e-12)
            assert g("QF") == pytest.approx(5.0 * g("PNFT") / (g("POHT") + g("PNBT") + g("PRFST") + g("PEXST")),
                                            rel=1e-12)
        finally:
            os.chdir(prev)


def test_struct_scalars_agree_with_the_table():
    with Trlib() as t:
        t.run(20)
        c = _ffi.TrStateC()                           # the C struct itself, not TrState (whose dict is filled
        assert t._lib.tr_get_state(ctypes.byref(c)) == 0  # from the table)
        for n in SCALAR_FIELDS:
            assert t.get_scalar(n) == getattr(c, n), n
        assert c.WPT > 0.0


def test_rip_is_the_plasma_current_in_ma():
    with Trlib() as t:
        t.set_param("RIPS", 4.0)
        t.set_param("RIPE", 4.0)
        t.run(4)
        assert t.get_scalar("RIP") == pytest.approx(4.0, rel=1e-12)


def test_unknown_scalar_is_refused():
    with Trlib() as t, pytest.raises(TrlibParamError):
        t.get_scalar("NOSUCH")


@pytest.mark.parametrize("name", ["t", "Wpt", "", "T ", "TT", "PNFT\n"])
def test_a_name_must_match_exactly(name):
    with Trlib() as t:
        with pytest.raises(TrlibParamError):
            t.get_scalar(name)


def test_state_carries_the_scalars_and_to_dict_is_unchanged():
    with Trlib() as t:
        t.run(5)
        s = t.get_state()
        assert set(s.scalars) == set(t.scalar_names())
        for n in t.scalar_names():                             # each by its own name, not one value for all
            assert s.scalars[n] == t.get_scalar(n), n
        assert len({s.scalars[n] for n in s.scalars}) > 20     # 31 different quantities
        d = s.to_dict()
        assert "PNFT" not in d["scalars"]                      # baselines compare to_dict at 1e-10
        assert tuple(d["scalars"]) == SCALAR_FIELDS            # the same 14, in the same order
        assert len(d["scalars"]) == 14


def test_get_scalar_before_tr_init_is_not_init():
    lib = _ffi.load_library()
    out = ctypes.c_double(-1.0)
    assert lib.tr_get_scalar(b"WPT", ctypes.byref(out)) == _ffi.TR_ERR_NOT_INIT
    assert out.value == -1.0


def test_scalar_count_name_and_a_short_buffer_in_c():
    lib = _ffi.load_library()
    assert lib.tr_scalar_count() == 31
    buf = ctypes.create_string_buffer(32)
    assert lib.tr_scalar_name(1, buf, 32) == 0 and buf.value == b"T"
    assert lib.tr_scalar_name(31, buf, 32) == 0 and buf.value == b"TAUE98"
    assert lib.tr_scalar_name(0, buf, 32) == _ffi.TR_ERR_INVALID
    assert lib.tr_scalar_name(32, buf, 32) == _ffi.TR_ERR_INVALID
    small = ctypes.create_string_buffer(6)               # "TAUE98" needs 7 with its NUL
    assert lib.tr_scalar_name(31, small, 6) == _ffi.TR_ERR_INVALID
    exact = ctypes.create_string_buffer(7)
    assert lib.tr_scalar_name(31, exact, 7) == 0 and exact.value == b"TAUE98"


def test_an_unknown_name_leaves_the_value_as_it_was():
    lib = _ffi.load_library()
    with Trlib():
        out = ctypes.c_double(-7.0)
        assert lib.tr_get_scalar(b"NOSUCH", ctypes.byref(out)) == _ffi.TR_ERR_INVALID
        assert lib.tr_get_scalar(b"WPT ", ctypes.byref(out)) == _ffi.TR_ERR_INVALID
        assert out.value == -7.0


class _WithoutScalarTable:
    """The real library with the PR 2 symbols hidden: a libtrapi.so built at PR 1 (tr_last_error, no scalar table)."""

    _HIDDEN = ("tr_scalar_count", "tr_scalar_name", "tr_get_scalar",
               "tr_history_count", "tr_history_name", "tr_history_length", "tr_history_full", "tr_history_get")

    def __init__(self, real):
        self._real = real

    def __getattr__(self, name):
        if name in self._HIDDEN:
            raise AttributeError(name)
        return getattr(self._real, name)


def test_get_state_on_a_library_without_the_scalar_table_holds_the_struct_scalars():
    with Trlib() as t:
        t.run(1)
        with_table = t.get_state()
        real = t._lib
        t._lib = _WithoutScalarTable(real)
        try:
            state = t.get_state()               # used to raise TrlibError: the library does not export tr_scalar_count
            assert tuple(state.scalars) == tuple(SCALAR_FIELDS)
            assert all(state.scalars[k] == with_table.scalars[k] for k in SCALAR_FIELDS)
            with pytest.raises(TrlibError):     # the by-name calls still say what is missing
                t.get_scalar("T")
        finally:
            t._lib = real


def test_a_run_of_zero_steps_evaluates_no_step():
    # tr_run(0) prepares again after a changed parameter but evaluates no step (tr_loop returns before tr_eval), so
    # TRGLOB does not run. What the preparation sets is new (T is 0, RIP is RIPS, Q0 under MODELG 2, the default);
    # what only a step computes (PNBT, WPT) is still the run before's until a run of one step or more.
    with Trlib() as t:
        t.set_param("PNBTOT", 10.0)
        t.run(20)
        before = {n: t.get_scalar(n) for n in ("PNBT", "WPT", "RIP", "Q0")}
        assert before["PNBT"] == pytest.approx(10.0)
        t.set_param("PNBTOT", 0.0)
        t.set_param("RIPS", 0.7)
        t.set_param("RIPE", 0.7)
        t.run(0)
        assert t.get_scalar("T") == 0.0
        assert t.get_scalar("RIP") == 0.7
        assert t.get_scalar("Q0") != before["Q0"]
        assert t.get_scalar("PNBT") == before["PNBT"] and t.get_scalar("WPT") == before["WPT"]
        t.run(1)
        assert t.get_scalar("PNBT") == 0.0 and t.get_scalar("WPT") != before["WPT"]


def test_get_state_keeps_the_struct_scalars_and_reads_only_the_others_by_name(monkeypatch):
    # The baselines compare get_state().to_dict(), the 14 of tr_state_t: they must be tr_get_state's copy, not the
    # by-name values (equal today, so a getter that answers -1 tells the two apart).
    with Trlib() as t:
        t.run(6)
        monkeypatch.setattr(Trlib, "get_scalar", lambda self, name: -1.0)
        state = t.get_state()
        assert all(state.scalars[n] != -1.0 for n in SCALAR_FIELDS)
        assert state.scalars["PNBT"] == -1.0 and state.scalars["H98Y2"] == -1.0
        assert list(state.scalars)[:3] == ["T", "WPT", "AJT"]
