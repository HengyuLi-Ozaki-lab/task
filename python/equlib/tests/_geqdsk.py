"""Every number of a G-EQDSK file, for comparing two files number by number.

EQU writes G-EQDSK with ``equ_eqdsk_write`` (``equ/equ_eqdsk.f90``): a header
line ``(6a8,3i4)`` and then blocks of ``(5e16.9)`` numbers, with integer
counts before the boundary and limiter points. Fields run together when a
number is negative (``0.1E+01-0.2E+00``), so the numbers are found with a
pattern, not by splitting on blanks. A Fortran exponent of three digits drops
its ``E`` (``0.1-100``); the pattern then reads two numbers, the same way in
both files being compared, so the comparison is still exact.
"""
from __future__ import annotations

import re
from pathlib import Path

_NUM = re.compile(r"[-+]?\d*\.\d+(?:[EeDd][-+]?\d+)?|[-+]?\d+")


def read_numbers(path: str | Path) -> tuple[list[int], list[float]]:
    """Return the header's integers (idum, nw, nh) and every later number."""
    with open(path) as f:
        head = f.readline()
        body = f.read()
    ints = [int(x) for x in head[48:].split()]
    nums = [float(x.replace("D", "E").replace("d", "e")) for x in _NUM.findall(body)]
    return ints, nums


def assert_same(path_a: str | Path, path_b: str | Path, rtol: float = 1e-10,
                atol: float = 1e-300) -> int:
    """Assert both files hold the same numbers within ``rtol``; return the count."""
    ia, na = read_numbers(path_a)
    ib, nb = read_numbers(path_b)
    assert ia == ib, f"headers differ: {ia} != {ib}"
    assert len(na) == len(nb), f"number counts differ: {len(na)} != {len(nb)}"
    for k, (x, y) in enumerate(zip(na, nb)):
        assert abs(x - y) <= max(atol, rtol * max(abs(x), abs(y))), \
            f"number {k} differs: {x!r} != {y!r}"
    return len(na)
