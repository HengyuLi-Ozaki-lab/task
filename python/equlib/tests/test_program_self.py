"""The comparison harness against itself: the program gives the same file twice.

``test_program_parity.py`` compares the library with ``equ_nogr`` through
these helpers; this file checks the helpers: two runs of the program on a
case in two directories write the same numbers, and the reader sees the
257 x 257 grid the examples ask for.
"""
from __future__ import annotations

import pytest

from equlib.tests._geqdsk import assert_same, read_numbers
from equlib.tests._program import PROGRAM, program_geqdsk

pytestmark = pytest.mark.skipif(not PROGRAM.exists(), reason="equ_nogr not built")


@pytest.mark.parametrize("case", ["quest", "iter01"])
def test_program_twice_same_file(case, tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    n = assert_same(program_geqdsk(case, a), program_geqdsk(case, b), rtol=0.0, atol=0.0)
    assert n > 257 * 257


def test_reader_sees_the_grid(tmp_path):
    ints, nums = read_numbers(program_geqdsk("quest", tmp_path))
    assert ints == [0, 257, 257]
    # 20 header numbers, four profiles and q of 257 points, psi of 257 x 257.
    assert len(nums) >= 20 + 5 * 257 + 257 * 257
