"""``Tot.get_scalar("tr:NAME")`` and ``Tot.history``: TR's outputs by name through ``tot``.

``tot_get_scalar`` strips the ``tr:`` prefix and calls ``tr_get_scalar``; ``tot_history_*`` delegate to
``tr_history_*``. In the mono image ``trlib`` and ``tot`` reach one TR, so the same number must come back both ways.
Run it with MONO_LIB_PATH set (mono: one image for both) and without (libtotapi.so links libtrapi.so, the library
``trlib`` loads).
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

import pytest

from totlib import Tot
from totlib.errors import TotlibError

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


def _chdir():
    prev = os.getcwd()
    os.chdir(FIXTURES_DIR)
    return prev


def test_tot_get_scalar_equals_the_trlib_value_for_the_same_run():
    from trlib._ffi import load_library
    prev = _chdir()
    try:
        with Tot() as tot:
            _hot(tot)
            tot.set_param("tr:NTMAX", 20)
            tot.run(20)
            via_tot = {n: tot.get_scalar(f"tr:{n}") for n in ("PNFT", "WPT", "QF", "PINT", "RIP")}
            lib = load_library()                   # the mono image: the TR that tot drives
            for n, v in via_tot.items():
                out = ctypes.c_double()
                assert lib.tr_get_scalar(n.encode(), ctypes.byref(out)) == 0
                assert out.value == v, n
            assert via_tot["PNFT"] > 0.0 and via_tot["WPT"] > 0.0
    finally:
        os.chdir(prev)


def test_tot_get_scalar_refuses_a_bad_prefix_and_an_unknown_name():
    with Tot() as tot:
        for bad in ("PNFT", "eq:PNFT", "fp:PNFT", "tr:NOSUCH", "tr:", "tr:PNFT ", "tr: PNFT"):
            with pytest.raises(TotlibError):
                tot.get_scalar(bad)


# A C name that the 128-character buffer cuts: "tr:T", 124 blanks, "X" read as "tr:T" before the check.
_CUT_NAMES = [
    b"tr:T" + b" " * 124 + b"X",
    b"tr:T" + b" " * 124 + b"junk",
    b"tr:T" + b" " * 200 + b"X",
    b"tr:T" + b"A" * 130,
]


@pytest.mark.parametrize("name", _CUT_NAMES)
def test_tot_get_scalar_refuses_a_name_cut_by_its_buffer(name):
    with Tot() as tot:
        v = ctypes.c_double(-1.0)
        assert tot._lib.tot_get_scalar(b"tr:T", ctypes.byref(v)) == 0     # the uncut name is a scalar
        v = ctypes.c_double(-1.0)
        assert tot._lib.tot_get_scalar(name, ctypes.byref(v)) == 1
        assert v.value == -1.0                                           # left alone


@pytest.mark.parametrize("name", _CUT_NAMES)
def test_tot_history_get_refuses_a_name_cut_by_its_buffer(name):
    with Tot() as tot:
        buf = (ctypes.c_double * 4)()
        got = ctypes.c_int(-1)
        assert tot._lib.tot_history_get(b"tr:T", buf, 4, ctypes.byref(got)) == 0
        assert tot._lib.tot_history_get(name, buf, 4, ctypes.byref(got)) == 1
        assert got.value == 0
