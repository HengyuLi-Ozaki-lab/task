"""``Equ.get_psi_rz`` equals the psirz block of the G-EQDSK the library writes.

The writer prints E16.9: a mantissa 0.1 <= m < 1 with 9 digits, so a
printed number is within 5e-10 / 0.1 = 5e-9 of the value, relative; the
comparison is at that, with a floor of 1e-12 for the zeros.
"""
from __future__ import annotations

import numpy as np

from equlib import Equ
from equlib.tests._geqdsk import read_numbers
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


def test_psi_rz_equals_geqdsk(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(1)
        psi = equ.get_psi_rz()
        st = equ.get_state()
        equ.write_geqdsk("g")
    (_, nw, nh), nums = read_numbers("g")
    assert psi.shape == (st.nr, st.nz) == (nw, nh)
    start = 20 + 4 * nw
    block = np.array(nums[start:start + nw * nh]).reshape(nh, nw).T
    np.testing.assert_allclose(psi, block, rtol=5e-9, atol=1e-12)
