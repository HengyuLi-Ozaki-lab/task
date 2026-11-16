"""``Tot.history`` and its companions: TR's time history by name through ``tot``.

``tot_history_*`` delegate to ``tr_history_*``, names carrying the ``tr:`` prefix. In the mono image ``trlib`` and
``tot`` reach one TR, so the same rows must come back both ways.
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


def test_tot_history_equals_the_tr_history_of_the_same_image():
    from trlib._ffi import load_library
    prev = _chdir()
    try:
        with Tot() as tot:
            _hot(tot)
            tot.run(20)
            h = tot.history(["tr:T", "tr:WPT", "tr:PNFT"])
            assert set(h) == {"tr:T", "tr:WPT", "tr:PNFT"}
            assert all(len(v) == 11 for v in h.values())
            assert h["tr:T"][0] == 0.0 and h["tr:WPT"][-1] > 0.0 and h["tr:PNFT"][-1] > 0.0
            lib = load_library()
            buf = (ctypes.c_double * 11)()
            got = ctypes.c_int()
            assert lib.tr_history_get(b"WPT", buf, 11, ctypes.byref(got)) == 0 and got.value == 11
            assert list(buf) == list(h["tr:WPT"])
            names = tot.history_names()
            assert "tr:PNFT" in names and "tr:T" in names
            assert len(names) == lib.tr_history_count() == 47
            tr_names = []
            for i in range(1, lib.tr_history_count() + 1):
                nbuf = ctypes.create_string_buffer(32)
                assert lib.tr_history_name(i, nbuf, 32) == 0
                tr_names.append("tr:" + nbuf.value.decode())
            assert names == tr_names
            assert tot.history_length() == 11 and tot.history_full() is False
            every = tot.history()
            assert set(every) == set(names)
    finally:
        os.chdir(prev)


def test_tot_history_refuses_a_bad_name():
    with Tot() as tot:
        for bad in (["T"], ["eq:T"], ["tr:NOSUCH"]):
            with pytest.raises(TotlibError):
                tot.history(bad)


def test_tot_history_reports_a_full_buffer():
    with Tot() as tot:
        assert tot.history_length() == 0 and tot.history_full() is False
        for name, value in (("NGTSTP", 1), ("NTSTEP", 100000), ("NGRSTP", 100000), ("DT", 1.0e-4)):
            tot.set_param(f"tr:{name}", float(value))
        tot.run(10100)
        assert tot.history_full() is True
        assert tot.history_length() == 10001
        assert len(tot.history("tr:T")["tr:T"]) == 10001
