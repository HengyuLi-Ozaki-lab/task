"""The numbers ``set_params`` and ``set_param`` hand to the library (fp_mcp).

An element of a list or a dict goes through ``float()``, which also takes the
strings ``"nan"``, ``"inf"``, ``"-inf"`` and ``"1e309"`` (infinity): they
reached the registry as NaN or an infinity. And ``float()`` of an integer too
large for a float raises ``OverflowError``, which the bulk path did not
catch, so the caller saw ``OverflowError: int too large to convert to float``
instead of the server's own message.

Both are the server's "invalid numeric value" now, raised before the library
is called. A string that is a finite number is still taken (``"2.5"`` in a
list), and a string on its own still goes to ``set_param_str``.

Pure Python: the library is a recorder. One test per case (``parametrize``,
never ``subTest``).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List
from unittest import mock

import pytest

HERE = Path(__file__).resolve()
MCP_ROOT = HERE.parents[1]
PYTHON_ROOT = HERE.parents[3]  # .../python

for extra in (str(MCP_ROOT.parent), str(PYTHON_ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from fp_mcp import server as srv  # noqa: E402
from fplib import FplibError  # noqa: E402

NOT_FINITE = [
    pytest.param("nan", id="'nan'"), pytest.param("NaN", id="'NaN'"),
    pytest.param("inf", id="'inf'"), pytest.param("-inf", id="'-inf'"),
    pytest.param("Infinity", id="'Infinity'"), pytest.param("1e309", id="'1e309'"),
    pytest.param("-1e309", id="'-1e309'"),
    pytest.param(float("nan"), id="nan"), pytest.param(float("inf"), id="inf"),
    pytest.param(float("-inf"), id="-inf"),
]
# float() raises OverflowError for these; the last is longer than Python prints.
TOO_LARGE = [pytest.param(10**400, id="10**400"), pytest.param(-(10**400), id="-10**400"),
             pytest.param(10**5000, id="10**5000")]


class _Recorder:
    """Stands in for the library: what set_param and set_param_str are called with."""

    def __init__(self) -> None:
        self.calls: List[tuple] = []
        self.str_calls: List[tuple] = []

    def set_param(self, name: str, value: float) -> None:
        self.calls.append((name, value))

    def set_param_str(self, name: str, value: str) -> None:
        self.str_calls.append((name, value))


@pytest.mark.parametrize("value", NOT_FINITE + TOO_LARGE)
def test_a_list_element_that_is_no_finite_number_is_refused(value):
    lib = _Recorder()
    with pytest.raises(FplibError) as caught:
        srv._apply_bulk_params(lib, {"PN": [1.0, value]})
    assert "invalid numeric value for 'PN[2]'" in str(caught.value)
    assert lib.calls == [("PN[1]", 1.0)]          # the element before it was applied


@pytest.mark.parametrize("value", NOT_FINITE + TOO_LARGE)
def test_a_dict_value_that_is_no_finite_number_is_refused(value):
    lib = _Recorder()
    with pytest.raises(FplibError) as caught:
        srv._apply_bulk_params(lib, {"PN": {"2": value}})
    assert "invalid numeric value for 'PN[2]'" in str(caught.value)
    assert lib.calls == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")] + TOO_LARGE)
def test_a_scalar_that_is_no_finite_number_is_refused(value):
    lib = _Recorder()
    with pytest.raises(FplibError) as caught:
        srv._apply_bulk_params(lib, {"RR": value})
    assert "invalid numeric value for 'RR'" in str(caught.value)
    assert lib.calls == []


@pytest.mark.parametrize("value", [float("nan"), float("inf")] + TOO_LARGE)
def test_set_param_refuses_what_is_no_finite_number(value):
    lib = _Recorder()
    with mock.patch.object(srv.STATE, "ensure_open", return_value=lib):
        with pytest.raises(Exception) as caught:
            srv.handle_set_param("RR", value)
    assert "invalid numeric value for 'RR'" in str(caught.value)
    assert "OverflowError" not in str(caught.value)
    assert lib.calls == []


def test_a_string_that_is_no_number_is_the_servers_own_error():
    lib = _Recorder()
    with pytest.raises(FplibError) as caught:
        srv._apply_bulk_params(lib, {"PN": [1.0, "oops"]})
    assert "invalid numeric value for 'PN[2]'" in str(caught.value)


def test_the_error_does_not_repeat_a_long_value():
    lib = _Recorder()
    with pytest.raises(FplibError) as caught:
        srv._apply_bulk_params(lib, {"PN": ["9" * 100000 + "x"]})
    assert "invalid numeric value for 'PN[1]'" in str(caught.value)
    assert len(str(caught.value)) < 300


def test_the_error_does_not_repeat_a_long_name():
    lib = _Recorder()
    with pytest.raises(FplibError) as caught:
        srv._apply_bulk_params(lib, {"N" * 100000: ["nan"]})
    assert "invalid numeric value for 'NNNN" in str(caught.value)
    assert len(str(caught.value)) < 300


def test_finite_numbers_are_applied_as_before():
    lib = _Recorder()
    applied = srv._apply_bulk_params(lib, {
        "RR": 3,                       # an integer is a number
        "PN": [0.5, "2.5", 1e300],     # a string that is a finite number is still taken
        "PA": {"2": -4.0},
    })
    assert lib.calls == [("RR", 3.0), ("PN[1]", 0.5), ("PN[2]", 2.5), ("PN[3]", 1e300), ("PA[2]", -4.0)]
    assert applied == ["RR", "PN[1]", "PN[2]", "PN[3]", "PA[2]"]


def test_a_string_on_its_own_still_goes_to_set_param_str():
    lib = _Recorder()
    srv._apply_bulk_params(lib, {"KNAMEQ": "eqdata", "RR": "nan"})
    assert lib.str_calls == [("KNAMEQ", "eqdata"), ("RR", "nan")] and lib.calls == []
