"""``tr_set_param`` and ``tr_set_param_str`` refuse a string they cannot hold whole.

The C entry points copy a name into ``CHARACTER(LEN=64)`` and a string value
into ``CHARACTER(LEN=128)``, and stopped at the buffer's end: a longer string
was cut, and what the cut left could be another parameter's name. ``"RR"``, 62
blanks and ``"junk"`` set ``RR``. A string that is longer only by blanks loses
nothing by the copy and is still taken.

The value's buffer is longer than the parameter it is for: ``KNAMEQ`` is
``CHARACTER(LEN=80)``, so a value of 81 to 128 characters passed the copy and
was cut by the assignment. That one the wrapper did send: ``set_param_str``
took a path of 100 characters and kept its first 80.

The Python wrapper never sends a name that long (``_encode_name`` refuses one
of more than 63 bytes), so the name tests call the C functions themselves, as
a C or Fortran caller does. One test per case (``parametrize``, never
``subTest``).
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrlibParamError  # noqa: E402

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)

NAME_BUFFER = 64
VALUE_BUFFER = 128      # the C entry point's
PARAMETER = 80          # KNAMEQ, CHARACTER(LEN=80)
OK, INVALID = 0, 1


def _set_param(name: bytes, value: float) -> int:
    with Trlib() as lib:
        return lib._lib.tr_set_param(name, ctypes.c_double(value))


def _set_param_str(name: bytes, value: bytes) -> int:
    with Trlib() as lib:
        return lib._lib.tr_set_param_str(name, value)


@pytest.mark.parametrize("name", [
    b"RR" + b" " * (NAME_BUFFER - 2) + b"junk",
    b"RR" + b" " * (NAME_BUFFER - 2) + b"x",          # one character more than the buffer
    b"PN[1]" + b" " * (NAME_BUFFER - 5) + b"x",
    b"R" * (NAME_BUFFER + 1),
], ids=["RR+62 blanks+junk", "RR+62 blanks+x", "PN[1]+blanks+x", "65 characters"])
def test_set_param_refuses_a_name_longer_than_its_buffer(name):
    assert _set_param(name, 3.0) == INVALID


@pytest.mark.parametrize("blanks", [NAME_BUFFER - 2, NAME_BUFFER - 1, 300])
def test_set_param_takes_a_name_that_is_long_only_by_blanks(blanks):
    # Trailing blanks are no part of a name: a blank-padded buffer is "RR".
    assert _set_param(b"RR" + b" " * blanks, 3.0) == OK


SCAN = 4096             # characters looked at beyond the buffer for the string's end


def test_a_string_that_ends_with_the_last_character_looked_at_is_taken():
    assert _set_param(b"RR" + b" " * (NAME_BUFFER - 2 + SCAN - 1), 3.0) == OK


@pytest.mark.parametrize("more", [SCAN, 5000])
def test_a_string_with_no_end_in_reach_is_refused(more):
    assert _set_param(b"RR" + b" " * (NAME_BUFFER - 2 + more), 3.0) == INVALID


@pytest.mark.parametrize("name", [
    b"KNAMEQ" + b" " * (NAME_BUFFER - 6) + b"junk",
    b"KNAMEQ" + b" " * (NAME_BUFFER - 6) + b"x",
], ids=["KNAMEQ+58 blanks+junk", "KNAMEQ+58 blanks+x"])
def test_set_param_str_refuses_a_name_longer_than_its_buffer(name):
    assert _set_param_str(name, b"eqdata") == INVALID


@pytest.mark.parametrize("length", sorted({PARAMETER + 1, VALUE_BUFFER, VALUE_BUFFER + 1} - {PARAMETER}))
def test_set_param_str_refuses_a_value_longer_than_the_parameter(length):
    assert _set_param_str(b"KNAMEQ", b"a" * length) == INVALID


def test_set_param_str_takes_a_value_that_fills_the_parameter():
    assert _set_param_str(b"KNAMEQ", b"a" * PARAMETER) == OK
    assert _set_param_str(b"KNAMEQ" + b" " * (NAME_BUFFER - 6), b"eqdata") == OK


def test_set_param_str_refuses_a_value_longer_than_its_buffer_whatever_is_left_of_it():
    # Cut at the buffer's end this would be "eqdata" and blanks: a value the parameter holds.
    assert _set_param_str(b"KNAMEQ", b"eqdata" + b" " * (VALUE_BUFFER - 6) + b"junk") == INVALID


@pytest.mark.parametrize("blanks", [VALUE_BUFFER - 6, VALUE_BUFFER - 5, 300])
def test_set_param_str_takes_a_value_that_is_long_only_by_blanks(blanks):
    # Trailing blanks are no part of the value: this is "eqdata".
    assert _set_param_str(b"KNAMEQ", b"eqdata" + b" " * blanks) == OK


@pytest.mark.parametrize("length", [PARAMETER + 1, 100])
def test_the_wrapper_refuses_a_value_longer_than_the_parameter(length):
    with Trlib() as lib:
        with pytest.raises(TrlibParamError):
            lib.set_param_str("KNAMEQ", "a" * length)


def test_the_wrapper_takes_a_value_that_fills_the_parameter():
    with Trlib() as lib:
        lib.set_param_str("KNAMEQ", "a" * PARAMETER)
