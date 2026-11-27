"""The tests' G-EQDSK reader (``_geqdsk.py``) on the fields EQU's writer can
produce (``equ/equ_eqdsk.f90``: ``(5e16.9)`` numbers, ``(2i5)`` counts, the last
record ``(i5,e16.9,i5)``), and on a ``D`` exponent, Fortran's other letter.
Fortran's E16.9 drops the ``E`` of a three-digit exponent; such a field read
as two numbers would make two identical files fail the count check."""
from __future__ import annotations

import pytest

from equlib.tests._geqdsk import _NUM, _number


def _read(text: str) -> list[float]:
    return [_number(x) for x in _NUM.findall(text)]


@pytest.mark.parametrize("text,numbers", [
    ("0.100000000-100", [1e-101]),
    ("-0.400000000+100", [-4e99]),
    ("0.100000000-100-0.987654321E-01", [1e-101, -0.0987654321]),
    ("0.100000000E+01-0.200000000E+00", [1.0, -0.2]),
    ("-0.512345678D-03 0.1D+01", [-0.512345678e-3, 1.0]),
    ("  604    0", [604.0, 0.0]),
    ("    0 0.000000000E+00    0", [0.0, 0.0, 0.0]),
])
def test_fields_of_the_writer(text, numbers):
    assert _read(text) == pytest.approx(numbers, rel=1e-15, abs=0.0)
