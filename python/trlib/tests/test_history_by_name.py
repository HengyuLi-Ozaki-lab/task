"""TR's time history by name: ``Trlib.history``, ``history_names``, ``history_length``, ``history_full``.

TR records a row every NGTSTP steps (``tr_eval`` calls ``TRATOT``): ``GT(NGT)`` is the time and
``GVT(NGT, 1:110)`` the globals, in single precision, in ``tr/trrslt_globals.f90``. ``tr_prep`` sets NGT to 0
(``tr/trprep.f90``), so a run starts a history and a re-preparation starts it again. NTM = 10001 rows
(``tr/trcom0.f90``); TRATOT stops recording when they are full. The first row is the state at t = 0, and each
later call of ``tr_run`` adds nsteps / NGTSTP rows: the second call's first evaluation repeats the step the
first call ended on (``tr_loop``'s prologue), and that row is not recorded twice. One test per case.
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

from trlib import Trlib, TrlibParamError  # noqa: E402
from trlib import _ffi  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"

pytestmark = [
    pytest.mark.forked,
    pytest.mark.skipif(not DEFAULT_SO.exists() and not os.environ.get("MONO_LIB_PATH"),
                       reason=f"libtrapi.so not built at {DEFAULT_SO}"),
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
    """A cwd that holds eqdata.ITER01, for the length of a test."""
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
    with _Iter01(), Trlib() as t:
        _iter01_hot(t)
        t.run(20)                                    # the last step is a multiple of NGTSTP
        assert t.history(name)[name][-1] == pytest.approx(t.get_scalar(name), rel=1e-6, abs=0.0)


@pytest.mark.parametrize("name", ["BETAN", "PRFST"])
def test_the_last_row_of_a_derived_name_equals_the_final_scalar(name):
    with _Iter01(), Trlib() as t:
        _iter01_hot(t)
        t.run(20)
        assert t.history(name)[name][-1] == pytest.approx(t.get_scalar(name), rel=1e-6, abs=0.0)


def test_the_heating_powers_are_not_zero_in_the_case_these_tests_use():
    # A comparison of two zeros proves nothing.
    with _Iter01(), Trlib() as t:
        _iter01_hot(t)
        t.run(20)
        for n in ("PNFT", "PNBT", "POHT", "PINT", "PRFST", "PRLT", "WPT", "TAUE1", "VLOOP", "QF", "AJNBT"):
            assert t.history(n)[n][-1] != 0.0, n


def test_the_last_row_of_the_central_and_average_values_matches_the_state():
    # TS0 = FCTR(RM(1), RM(2), RT(1), RT(2)) = (9 RT(1) - RT(2)) / 8 on the half-step mesh (trrslt_globals.f90).
    with _Iter01(), Trlib() as t:
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
    with _Iter01(), Trlib() as t:
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
    # NTM = 10001 rows. NGTSTP 1 with a mesh of 5 radial points makes a row per step cheaply.
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
