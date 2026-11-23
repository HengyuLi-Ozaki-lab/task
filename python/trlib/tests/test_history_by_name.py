"""TR's time history by name: ``Trlib.history``, ``history_names``, ``history_length``, ``history_full``.

TR records a row every NGTSTP steps (``tr_eval`` calls ``TRATOT``): ``GT(NGT)`` is the time and
``GVT(NGT, 1:110)`` the globals, in single precision, in ``tr/trrslt_globals.f90``. ``tr_prep`` sets NGT to 0
(``tr/trprep.f90``), so a run starts a history and a re-preparation starts it again. NTM = 10001 rows
(``tr/trcom0.f90``); TRATOT stops recording when they are full. The first row is the state at t = 0, and each
later call of ``tr_run`` adds the multiples of NGTSTP among the steps it runs (nsteps / NGTSTP when it starts on
one): the second call's first evaluation repeats the step the
first call ended on (``tr_loop``'s prologue), and that row is not recorded twice. One test per case.

The last row equals the final scalar to single precision, except under MODELG 9 when the last step is a multiple
of NTEQIT: ``tr_eval`` writes the row before the step's equilibrium re-solve, so for Q0 and what TRCALC recomputes
after it the row holds the value before the re-solve, as ``tr2`` prints it (TRSNAP), and ``get_scalar`` the value
after it (measured on Q0: 7.7e-5 to 4.9e-4 relative). The cases here are ITER01 under MODELG 3, with no re-solve.
"""
from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibParamError, TrlibRunError  # noqa: E402
from trlib import _ffi  # noqa: E402

REPO = HERE.parents[3]
FIXTURES_DIR = HERE.parent / "fixtures"

pytestmark = [
    pytest.mark.forked,
    pytest.mark.skipif(not _ffi._default_lib_path().exists(),          # Trlib()'s own resolution: MONO_LIB_PATH,
                       reason=f"libtrapi.so not found at {_ffi._default_lib_path()}"),   # TRLIB_PATH, tr/, lib/
]

# name -> GVT column (0 = GT), read from tr/trrslt_globals.f90 TRATOT (lines 427-549 at the base).
COLUMNS = {
    "T": 0,
    "NE0": 1, "NEAV": 5, "TE0": 9, "TI0": 10, "TEAV": 13, "TIAV": 14,
    "WPT": 33,
    "AJT": 34, "AJOHT": 35, "AJNBT": 36, "AJRFT": 37, "AJBST": 38,
    "PINT": 39, "POHT": 40, "PNBT": 41, "PRFE": 42, "PRFD": 43, "PNFT": 46,
    "POUT": 57,
    "VLOOP": 74, "ALI": 75, "RQ1": 76, "Q0": 77,
    "WPDOT": 78, "TAUE1": 79, "TAUE2": 80,
    "BETAP0": 82, "BETA0": 84, "BETAA": 85,
    "ZEFF0": 86, "QF": 87, "RIP": 88,
    "PEXE": 89, "PEXI": 90,
    "PECE": 91, "PECI": 92, "PLHE": 93, "PLHI": 94, "PICE": 95, "PICI": 96,
    "TAUE98": 102, "H98Y2": 103, "NLAV": 104, "PRLT": 110,
}
DERIVED = ("BETAN", "PRFST")          # no column of their own: computed from columns of the same row

# The names of the history that are also names of the scalar table: the last row must equal the scalar.
SHARED = ("T", "WPT", "AJT", "AJOHT", "AJNBT", "AJRFT", "AJBST", "PINT", "POHT", "PNBT", "PNFT", "POUT",
          "VLOOP", "ALI", "RQ1", "Q0", "WPDOT", "TAUE1", "TAUE2", "BETAP0", "BETA0", "BETAA", "ZEFF0", "QF",
          "RIP", "TAUE98", "H98Y2", "PRLT", "BETAN", "PRFST")


def _iter01_hot(t):
    from trlib.tests.fixtures import tr_iter01_params as HOT
    HOT.apply(t)
    for i in range(1, 5):
        t.set_param(f"PT[{i}]", 10.0)
        t.set_param(f"PTS[{i}]", 1.0)
    t.set_param("PICTOT", 5.0)            # ITER01 sets the profiles of the RF sources, not their powers [MW]
    t.set_param("PECTOT", 3.0)
    t.set_param("PLHTOT", 2.0)
    t.set_param("MDLIMP", 1)              # carbon (PNC %), so that the line radiation PRLT is not 0
    t.set_param("PNC", 2.0)


class _Iter01:
    """A cwd that holds eqdata.ITER01, for the length of a test. Enter it after Trlib(): a relative TRLIB_PATH or
    MONO_LIB_PATH is resolved from the cwd the test started in."""
    def __enter__(self):
        self.prev = os.getcwd()
        os.chdir(FIXTURES_DIR)

    def __exit__(self, *exc):
        os.chdir(self.prev)


def test_the_names_are_the_curated_list_and_the_derived_ones():
    with Trlib() as t:
        names = t.history_names()
        assert set(names) == set(COLUMNS) | set(DERIVED)
        assert len(names) == len(set(names))
        assert names[0] == "T"


def test_a_run_records_the_start_and_every_ngtstp_th_step():
    with Trlib() as t:
        assert t.history_length() == 0               # nothing prepared yet
        t.run(20)                                    # NGTSTP is 2: steps 0, 2, ..., 20
        assert t.history_length() == 11
        h = t.history()
        assert all(len(v) == 11 for v in h.values())
        assert h["T"][0] == 0.0
        assert np.all(np.diff(h["T"]) > 0.0)         # no row twice


@pytest.mark.parametrize("ngtstp,steps,rows", [(1, 20, 21), (3, 20, 7), (5, 20, 5), (7, 3, 1), (100, 20, 1)])
def test_the_number_of_rows_follows_ngtstp(ngtstp, steps, rows):
    with Trlib() as t:
        t.set_param("NGTSTP", ngtstp)
        t.run(steps)
        assert t.history_length() == rows


def test_each_call_adds_nsteps_over_ngtstp_rows():
    with Trlib() as t:
        t.run(20)
        assert t.history_length() == 11
        t.run(10)                                    # steps 22 .. 30: five rows, not six
        assert t.history_length() == 16
        t.run(4)
        assert t.history_length() == 18
        h = t.history("T")["T"]
        assert np.all(np.diff(h) > 0.0)


def test_a_call_of_zero_steps_records_nothing():
    with Trlib() as t:
        t.run(10)
        before = t.history_length()
        t.run(0)
        assert t.history_length() == before


@pytest.mark.parametrize("name", sorted(set(SHARED) - {"BETAN", "PRFST"}))
def test_the_last_row_equals_the_final_scalar(name):
    with Trlib() as t, _Iter01():
        _iter01_hot(t)
        t.run(20)                                    # the last step is a multiple of NGTSTP
        assert t.history(name)[name][-1] == pytest.approx(t.get_scalar(name), rel=1e-6, abs=0.0)


@pytest.mark.parametrize("name", ["BETAN", "PRFST"])
def test_the_last_row_of_a_derived_name_equals_the_final_scalar(name):
    with Trlib() as t, _Iter01():
        _iter01_hot(t)
        t.run(20)
        assert t.history(name)[name][-1] == pytest.approx(t.get_scalar(name), rel=1e-6, abs=0.0)


def test_the_heating_powers_are_not_zero_in_the_case_these_tests_use():
    # A comparison of two zeros proves nothing.
    with Trlib() as t, _Iter01():
        _iter01_hot(t)
        t.run(20)
        for n in ("PNFT", "PNBT", "POHT", "PINT", "PRFST", "PRLT", "WPT", "TAUE1", "VLOOP", "QF", "AJNBT"):
            assert t.history(n)[n][-1] != 0.0, n


def test_the_last_row_of_the_central_and_average_values_matches_the_state():
    # TS0 = FCTR(RM(1), RM(2), RT(1), RT(2)) = (9 RT(1) - RT(2)) / 8 on the half-step mesh (trrslt_globals.f90).
    with Trlib() as t, _Iter01():
        _iter01_hot(t)
        t.run(20)
        s = t.get_state()
        h = t.history(["TE0", "TI0", "NE0"])
        te0 = (9.0 * s.RT[0][0] - s.RT[1][0]) / 8.0
        ti0 = (9.0 * s.RT[0][1] - s.RT[1][1]) / 8.0
        ne0 = (9.0 * s.RN[0][0] - s.RN[1][0]) / 8.0
        assert h["TE0"][-1] == pytest.approx(te0, rel=1e-6)
        assert h["TI0"][-1] == pytest.approx(ti0, rel=1e-6)
        assert h["NE0"][-1] == pytest.approx(ne0, rel=1e-6)


def test_rf_columns_are_the_right_modes_and_species():
    # PRFVT(NS, mode): 1 = ECH, 2 = LH, 3 = ICRH; NS 1 electrons, 2 ions. ITER01 drives all three.
    with Trlib() as t, _Iter01():
        _iter01_hot(t)
        t.run(20)
        h = t.history(["PECE", "PECI", "PLHE", "PLHI", "PICE", "PICI", "PRFE", "PRFD", "PRFST", "PEXE"])
        total = sum(h[n][-1] for n in ("PRFE", "PRFD"))
        assert total <= h["PRFST"][-1] * (1 + 1e-6)         # species 3, 4 take the rest
        by_mode = sum(h[n][-1] for n in ("PECE", "PECI", "PLHE", "PLHI", "PICE", "PICI"))
        assert by_mode == pytest.approx(h["PRFE"][-1] + h["PRFD"][-1], rel=1e-5)


def test_history_with_names_returns_only_those_and_in_order():
    with Trlib() as t:
        t.run(6)
        h = t.history(["WPT", "T"])
        assert list(h) == ["WPT", "T"]
        assert h["T"].dtype == np.float64 and h["T"].shape == (4,)


def test_an_unknown_history_name_is_refused():
    with Trlib() as t:
        t.run(2)
        with pytest.raises(TrlibParamError):
            t.history(["T", "NOSUCH"])


def test_history_before_init_in_c():
    lib = _ffi.load_library()
    assert lib.tr_history_length() == 0
    buf = (ctypes.c_double * 4)()
    got = ctypes.c_int(-1)
    assert lib.tr_history_get(b"T", buf, 4, ctypes.byref(got)) == _ffi.TR_ERR_NOT_INIT


def test_c_get_copies_at_most_n_rows_and_says_how_many():
    lib = _ffi.load_library()
    with Trlib() as t:
        t.run(20)
        buf = (ctypes.c_double * 4)()
        got = ctypes.c_int(-1)
        assert lib.tr_history_get(b"T", buf, 4, ctypes.byref(got)) == 0
        assert got.value == 4                         # min(n, rows)
        big = (ctypes.c_double * 50)()
        assert lib.tr_history_get(b"T", big, 50, ctypes.byref(got)) == 0
        assert got.value == 11
        assert lib.tr_history_get(b"T", big, -1, ctypes.byref(got)) == _ffi.TR_ERR_INVALID
        assert lib.tr_history_get(b"NOSUCH", big, 50, ctypes.byref(got)) == _ffi.TR_ERR_INVALID


def test_c_name_enumeration_matches_the_count():
    lib = _ffi.load_library()
    with Trlib() as t:
        n = lib.tr_history_count()
        assert n == len(COLUMNS) + len(DERIVED)
        buf = ctypes.create_string_buffer(32)
        seen = []
        for i in range(1, n + 1):
            assert lib.tr_history_name(i, buf, 32) == 0
            seen.append(buf.value.decode())
        assert seen == t.history_names()
        assert lib.tr_history_name(0, buf, 32) == _ffi.TR_ERR_INVALID
        assert lib.tr_history_name(n + 1, buf, 32) == _ffi.TR_ERR_INVALID
        tiny = ctypes.create_string_buffer(2)
        assert lib.tr_history_name(n, tiny, 2) == _ffi.TR_ERR_INVALID    # "PRFST" does not fit


def test_the_history_after_a_re_preparation_starts_again():
    with Trlib() as t:
        t.run(10)
        assert t.history_length() == 6
        t.set_param("RR", 3.1)                        # a changed parameter: tr_run prepares again
        t.run(4)
        assert t.history_length() == 3                # steps 0, 2, 4 of the new run
        h = t.history("T")["T"]
        assert h[0] == 0.0


def test_a_full_buffer_is_reported_and_stops_recording():
    # NTM = 10001 rows. NGTSTP 1 and a small DT make a row per step.
    with Trlib() as t:
        t.set_param("NGTSTP", 1)
        t.set_param("NTSTEP", 100000)
        t.set_param("NGRSTP", 100000)
        t.set_param("DT", 1.0e-4)
        t.run(5000)
        assert not t.history_full()
        assert t.history_length() == 5001
        t.run(5100)                                   # 5001 + 5100 = 10101 > 10001
        assert t.history_full()
        assert t.history_length() == 10001
        h = t.history("T")["T"]
        assert len(h) == 10001 and np.all(np.diff(h) > 0.0)
        t.run(10)                                     # nothing more is recorded, nothing breaks
        assert t.history_length() == 10001
        # a new preparation empties it
        t.set_param("RR", 3.1)
        t.run(2)
        assert not t.history_full()
        assert t.history_length() == 3


def test_a_new_lifecycle_has_no_history_before_its_first_run():
    # NGT keeps its value across tr_finalize and tr_init until tr_prep sets it to 0 (trprep.f90): the library
    # reports 0 rows for an unprepared TR, whatever NGT holds.
    with Trlib() as t:
        t.run(10)
        assert t.history_length() == 6
    with Trlib() as t:
        assert t.history_length() == 0
        assert not t.history_full()
        assert len(t.history("T")["T"]) == 0
        t.run(4)
        assert t.history_length() == 3


# What each column holds, as the expression TRATOT writes (tr/trrslt_globals.f90). The test reads the column number
# from that source, so the library's column map is checked against the code and not against this file's own numbers.
EXPRESSION = {
    "NE0": "ANS0(1)", "NEAV": "ANSAV(1)", "TE0": "TS0(1)", "TI0": "TS0(2)", "TEAV": "TSAV(1)", "TIAV": "TSAV(2)",
    "WPT": "WPT", "AJT": "AJT", "AJOHT": "AJOHT", "AJNBT": "AJNBT", "AJRFT": "AJRFT", "AJBST": "AJBST",
    "PINT": "PINT", "POHT": "POHT", "PNBT": "PNBT", "PRFE": "PRFT(1)", "PRFD": "PRFT(2)", "PNFT": "PNFT",
    "POUT": "POUT", "VLOOP": "VLOOP", "ALI": "ALI", "RQ1": "RQ1", "Q0": "Q0", "WPDOT": "WPDOT",
    "TAUE1": "TAUE1", "TAUE2": "TAUE2", "BETAP0": "BETAP0", "BETA0": "BETA0", "BETAA": "BETAA", "ZEFF0": "ZEFF0",
    "QF": "QF", "RIP": "RIP", "PEXE": "PEXT(1)", "PEXI": "PEXT(2)",
    "PECE": "PRFVT(1,1)", "PECI": "PRFVT(2,1)", "PLHE": "PRFVT(1,2)", "PLHI": "PRFVT(2,2)",
    "PICE": "PRFVT(1,3)", "PICI": "PRFVT(2,3)", "TAUE98": "TAUE98", "H98Y2": "H98Y2", "NLAV": "ANLAV(1)",
    "PRLT": "PRLT",
}


def _source_columns():
    import re
    src = (REPO / "tr" / "trrslt_globals.f90").read_text()
    cols = {}
    for num, expr in re.findall(r"GVT\(NGT,\s*(\d+)\)\s*=\s*GUCLIP\(([^!\n]*)\)", src):
        cols[expr.replace(" ", "")] = int(num)
    return cols


def _write_gvt(lib, row, col, value):
    ntm = 10001
    arr = (ctypes.c_float * (ntm * 110)).in_dll(lib, "__trcomm_profile_MOD_gvt")
    arr[(col - 1) * ntm + row] = value


@pytest.mark.parametrize("name", sorted(EXPRESSION))
def test_a_name_reads_the_column_the_source_writes_its_quantity_to(name):
    # A sentinel (the column number + 0.5) in each column of the last row: the name must return the sentinel of
    # the column TRATOT writes its expression to.
    col = _source_columns()[EXPRESSION[name].replace(" ", "")]
    lib = _ffi.load_library()
    with Trlib() as t:
        t.run(4)
        last = t.history_length() - 1
        for c in range(1, 111):
            _write_gvt(lib, last, c, c + 0.5)
        assert t.history(name)[name][-1] == col + 0.5, (name, col)


def test_every_expression_in_the_table_is_a_column_of_the_source():
    cols = _source_columns()
    assert len(cols) == 110
    for name, expr in EXPRESSION.items():
        assert expr in cols, name
    assert set(EXPRESSION) == set(COLUMNS) - {"T"}


def test_derived_names_are_computed_from_the_columns_the_source_gives():
    cols = _source_columns()
    lib = _ffi.load_library()
    with Trlib() as t:
        t.run(4)
        last = t.history_length() - 1
        for c in range(1, 111):
            _write_gvt(lib, last, c, c + 0.5)
        h = t.history(["PRFST", "BETAN"])
        prf = sum(cols[f"PRFT({k})"] + 0.5 for k in (1, 2, 3, 4))       # species 3 and 4 included
        assert h["PRFST"][-1] == pytest.approx(prf, rel=1e-6)
        v = lambda e: cols[e] + 0.5                                      # noqa: E731
        betan = 100.0 * v("BETAA") / (v("RIP") / (v("RA") * v("BB")))
        assert h["BETAN"][-1] == pytest.approx(betan, rel=1e-6)


def test_the_average_and_line_averaged_values_match_the_state():
    # Independent of the column map: a circular plasma weights a cell by its radius, so NEAV, TEAV, TIAV are the
    # radius-weighted means of the state's profiles to a few per cent, and NLAV is the plain mean of ne. Electron
    # and ion temperatures start 12 and 8 keV apart, and ne is twice the ion density, so a wrong species or column
    # (NEAV for the density of the first ion, TEAV for TIAV) is out of tolerance.
    with Trlib() as t, _Iter01():
        _iter01_hot(t)
        t.set_param("PT[1]", 12.0)
        for i in (2, 3, 4):
            t.set_param(f"PT[{i}]", 8.0)
        t.run(20)
        s = t.get_state()
        n = len(s.RN)
        w = [(i + 0.5) for i in range(n)]
        ne = [r[0] for r in s.RN]
        te = [r[0] for r in s.RT]
        ti = [r[1] for r in s.RT]
        ni = [r[1] for r in s.RN]

        def weighted(values, density):                 # radius-weighted, density-weighted mean
            return sum(v * d * x for v, d, x in zip(values, density, w)) / sum(d * x for d, x in zip(density, w))

        h = t.history(["NEAV", "TEAV", "TIAV", "NLAV"])
        assert h["NEAV"][-1] == pytest.approx(weighted(ne, [1.0] * n), rel=0.05)
        assert h["TEAV"][-1] == pytest.approx(weighted(te, ne), rel=0.05)
        assert h["TIAV"][-1] == pytest.approx(weighted(ti, ni), rel=0.05)
        assert h["NLAV"][-1] == pytest.approx(sum(ne) / n, rel=0.05)
        assert abs(h["TEAV"][-1] - h["TIAV"][-1]) > 0.5      # the two differ: a swap is seen


def test_a_run_of_one_step_then_a_changed_parameter_restarts_at_t_zero():
    # NT_ROW (tr_eval) keeps the step of the last row; tr_prep sets NGT to 0, and the next run must record its
    # own step 0 although the old NT_ROW can be 0 too: run(1) records step 0 only (NGTSTP 2).
    with Trlib() as t:
        t.run(1)
        assert t.history_length() == 1
        t.set_param("RR", 3.1)
        t.run(4)
        assert t.history_length() == 3
        h = t.history("T")["T"]
        assert h[0] == 0.0 and np.all(np.diff(h) > 0.0)


def test_the_last_row_can_lag_the_state_when_the_last_step_was_not_recorded():
    # The README's condition: the last row agrees with get_scalar only when the call's last step was recorded.
    # NGTSTP 2 (the default): run(1) records no row, so T's last row is the state at t = 0 while get_scalar is DT.
    with Trlib() as t:
        t.run(1)
        assert t.history("T")["T"][-1] == 0.0
        assert t.get_scalar("T") == pytest.approx(t.get_state().scalars["T"]) and t.get_scalar("T") > 0.0


def test_a_history_that_fills_exactly_at_the_end_of_a_call_is_still_current():
    # NGTSTP 1: run(10000) records rows 0..10000 = 10001 = NTM. Full and current at once; one more step is not recorded.
    with Trlib() as t:
        t.set_param("NGTSTP", 1)
        t.set_param("NTSTEP", 100000)
        t.set_param("NGRSTP", 100000)
        t.set_param("DT", 1.0e-4)
        t.run(10000)
        assert t.history_full() and t.history_length() == 10001
        assert t.history("T")["T"][-1] == pytest.approx(t.get_scalar("T"), rel=1e-6)
        t.run(1)
        assert t.history_length() == 10001
        assert t.history("T")["T"][-1] < t.get_scalar("T") - 0.5e-4


def test_the_last_row_stays_behind_the_state_once_the_buffer_is_full():
    with Trlib() as t:
        t.set_param("NGTSTP", 1)
        t.set_param("NTSTEP", 100000)
        t.set_param("NGRSTP", 100000)
        t.set_param("DT", 1.0e-4)
        t.run(10100)
        assert t.history_full()
        assert t.history("T")["T"][-1] < t.get_scalar("T") - 1.0e-3


@pytest.mark.parametrize("ngtstp,times", [(1, [0.0, 100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0]),
                                          (2, [0.0, 200.0, 400.0, 600.0, 800.0]),
                                          (3, [0.0, 300.0, 600.0])])
def test_a_failed_step_is_not_a_row_of_the_history(ngtstp, times):
    # DT = 100 s: TRCHCK finds a negative temperature in the step from 800 s (test_loop_failures). tr_exec records the
    # failed iterate for tr2's graphics (TRATOT at the failure, at the time of the step before, outside the NGTSTP
    # cadence: before, a row T = 800 with TE0 3.7e6 followed the step's own row). In library mode it is not a row:
    # the history holds recorded steps only, and tr_last_error says where the run failed.
    with Trlib() as t:
        t.set_param("DT", 100.0)
        t.set_param("NGTSTP", ngtstp)
        with pytest.raises(TrlibRunError) as err:
            t.run(30)
        assert (err.value.failure.kind, err.value.failure.nt) == ("TR_CHECK", 8)
        assert t.history_length() == len(times)
        assert list(t.history("T")["T"]) == pytest.approx(times, abs=1e-3)


def _modelg9(t, nteqit):
    t.set_param("MODELG", 9)
    t.set_param("RIPS", 3.0)
    t.set_param("RIPE", 3.0)
    t.set_param("NTEQIT", nteqit)
    t.set_param("NGTSTP", 1)


def test_after_an_eq_re_solve_on_the_last_step_only_q0_differs_from_the_row():
    # MODELG 9: tr_loop records the step (tr_eval) before it re-solves EQ on a multiple of NTEQIT, and then recomputes
    # Q0 on the new metric (tr_bpsd_get, TRCALC: tr/trloop.f90). The row keeps the Q0 of before the re-solve and
    # get_scalar gives the one after it (measured: 6.6e-5 relative here); the other names are TRGLOB's and agree.
    with Trlib() as t:
        _modelg9(t, 5)
        t.run(10)
        h = t.history(list(SHARED))
        differ = {n for n in SHARED if h[n][-1] != pytest.approx(t.get_scalar(n), rel=1e-6, abs=0.0)}
        assert differ == {"Q0"}


@pytest.mark.parametrize("name", SHARED)
def test_off_an_eq_re_solve_step_the_last_row_agrees_under_modelg_9(name):
    with Trlib() as t:
        _modelg9(t, 5)
        t.run(12)                                    # step 12 is recorded and is not a multiple of NTEQIT
        assert t.history(name)[name][-1] == pytest.approx(t.get_scalar(name), rel=1e-6, abs=0.0)


def test_the_sawtooth_record_cannot_be_started_through_the_library():
    # TRATOTN (tr/trexec.f90) writes the sawtooth record's temperatures into GVT columns 89 to 88 + 4 NGPST of its
    # own rows (NGST, counted from the record's start) when MDLST /= 0 and T >= TSST: over PEXE ... NLAV and over
    # RA and BB, which BETAN is computed from. tr_eval does not call TRATOTN in library mode; TSST (1e9 s,
    # tr/trinit.f90) is also not a library parameter, which this test pins.
    with Trlib() as t:
        with pytest.raises(TrlibParamError):
            t.set_param("TSST", 0.0)


@pytest.mark.parametrize("ngtstp,times", [(1, [0.0, 1.0e6]), (2, [0.0])])
def test_a_step_that_is_not_finite_is_not_a_row_of_the_history(ngtstp, times):
    # DT = 1e6 s: the state is NaN after the second step (test_loop_failures). tr_eval records the step before tr_loop
    # finds it not finite (NONFINITE); the row is taken back, and the rows before it stay.
    with Trlib() as t:
        t.set_param("DT", 1.0e6)
        t.set_param("NGTSTP", ngtstp)
        with pytest.raises(TrlibRunError) as err:
            t.run(30)
        assert (err.value.failure.kind, err.value.failure.nt) == ("NONFINITE", 2)
        assert t.history_length() == len(times)
        h = t.history()
        assert list(h["T"]) == pytest.approx(times)
        assert all(np.all(np.isfinite(v)) for v in h.values())


def test_a_failed_preparation_leaves_no_history_of_the_run_before():
    # MODEL_PNF and MDLNF both set: tr_prep refuses before it starts the history again (NGT = 0). The rows of the run
    # before are not this run's.
    with Trlib() as t:
        t.run(20)
        assert t.history_length() == 11
        t.set_param("MODEL_PNF", 1)
        t.set_param("MDLNF", 1)
        with pytest.raises(TrlibRunError) as err:
            t.run(10)
        assert err.value.failure.kind == "PREP_FAILED"
        assert t.history_length() == 0
        assert len(t.history("T")["T"]) == 0


def test_a_retry_after_a_step_that_is_not_finite_does_not_record_that_step_again():
    # A second run on the same handle, with no changed parameter, starts at the failed step: tr_loop's prologue
    # evaluates it again. The step stays out of the history.
    with Trlib() as t:
        t.set_param("DT", 1.0e6)
        t.set_param("NGTSTP", 1)
        with pytest.raises(TrlibRunError):
            t.run(30)
        rows = t.history_length()
        try:
            t.run(4)
        except TrlibRunError:
            pass
        h = t.history()
        assert t.history_length() == rows
        assert all(np.all(np.isfinite(v)) for v in h.values())
