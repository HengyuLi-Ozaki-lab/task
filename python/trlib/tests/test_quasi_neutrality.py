"""``validate()`` reports namelist densities that are not quasi-neutral (task-web-client #200).

TR takes the electrons' density equal to the ions' charge density, ``PN(1) = sum PZ(s) * PN(s)``
for ``s = 2..NSMAX`` (``trprof`` dilutes the main ions by the impurity model's charge, which it
takes in proportion to the electrons), and nothing makes the namelist agree. Measured on TR's
defaults (``PN(1) = 0.5``): ``PN(2)`` from 0.005 to 0.05 fails at step 0 (``NEGATIVE TEMPERATURE``),
at 0.1 and 0.4 completes. So ``validate()`` reports a difference above 1e-3 of the larger, at the
centre (``PN[1]``) and at the edge (``PNS[1]``), as ``INCONSISTENT_PAIR``, and ``tr_run`` does not
refuse it: a run that does not fail still runs. Not reported in the UFILE modes (``MDLUF`` 1, 2, 3)
or beside a finding of the species checks (``test_species_profile_checks.py``; ``RIPS``/``RIPE`` below
0 with ``MODELG = 9`` is one of them), which ``tr_run`` refuses. One test per case, no ``subTest``.
"""
from __future__ import annotations

import contextlib
import math
import os
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from trlib import Trlib, TrDiagCode  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"

CENTRE = ("not quasi-neutral at the centre: electrons  5.00E-01, ions' charge sum PZ*n  5.00E-03 "
          "(1e20/m3); TR takes them equal")


@contextlib.contextmanager
def _pushd(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def _validate(params: dict, fixture=None):
    """validate() on TR's defaults, or on ``fixture``'s parameters, with ``params`` set on top."""
    with _pushd(FIXTURES_DIR):
        with Trlib() as tr:
            if fixture is not None:
                fixture.apply(tr)
            for name, value in params.items():
                tr.set_param(name, float(value))
            return [(d.param, d.code, d.message) for d in tr.validate()]


def _pairs(diags):
    return [(param, code) for param, code, _ in diags]


@unittest.skipUnless(DEFAULT_SO.exists(), f"libtrapi.so not built at {DEFAULT_SO}")
class TestQuasiNeutrality(unittest.TestCase):

    def test_tr_defaults_are_quasi_neutral(self):
        self.assertEqual(_validate({}), [])

    def test_ions_far_below_the_electrons_are_reported(self):
        diags = _validate({"PN[2]": 0.005})
        self.assertEqual(diags, [("PN[1]", TrDiagCode.INCONSISTENT_PAIR, CENTRE)])

    def test_ions_above_the_electrons_are_reported(self):
        diags = _validate({"PN[1]": 0.4})
        self.assertEqual(_pairs(diags), [("PN[1]", TrDiagCode.INCONSISTENT_PAIR)])

    def test_the_edge_is_checked_on_its_own(self):
        diags = _validate({"PNS[2]": 0.04})
        self.assertEqual(_pairs(diags), [("PNS[1]", TrDiagCode.INCONSISTENT_PAIR)])
        self.assertIn("not quasi-neutral at the edge: electrons  5.00E-02, ions' charge sum PZ*n  4.00E-02",
                      diags[0][2])

    def test_a_difference_of_5e_4_is_not_reported(self):
        self.assertEqual(_validate({"PN[2]": 0.5 * (1 + 5e-4)}), [])

    def test_a_difference_of_2e_3_is_reported(self):
        diags = _validate({"PN[2]": 0.5 * (1 + 2e-3)})
        self.assertEqual(_pairs(diags), [("PN[1]", TrDiagCode.INCONSISTENT_PAIR)])

    def test_the_ions_count_by_their_charge(self):
        # tr_iter01: electrons 0.7, D 0.315, T 0.315, He 0.035 with PZ = 2 (0.1 and its parts at the
        # edge): quasi-neutral only when helium counts twice.
        from trlib.tests.fixtures import tr_iter01_params as iter01
        self.assertEqual(_validate({}, iter01), [])
        diags = _validate({"PZ[4]": 1.0}, iter01)
        self.assertEqual(_pairs(diags), [("PN[1]", TrDiagCode.INCONSISTENT_PAIR),
                                         ("PNS[1]", TrDiagCode.INCONSISTENT_PAIR)])

    # MDLUF 1, 2 and 3 take the densities from the UFILE, not from PN and PNS.
    def _ufile(self, mdluf):
        pairs = _pairs(_validate({"PN[2]": 0.005, "MDLUF": mdluf}))
        self.assertNotIn(("PN[1]", TrDiagCode.INCONSISTENT_PAIR), pairs)

    def test_not_reported_with_mdluf_1(self):
        self._ufile(1)

    def test_not_reported_with_mdluf_2(self):
        self._ufile(2)

    def test_not_reported_with_mdluf_3(self):
        self._ufile(3)

    def test_not_reported_beside_a_species_finding(self):
        # A negative density is refused by tr_run already; the electrons' sum is not reported too.
        self.assertEqual(_pairs(_validate({"PN[2]": -0.1})), [("PN[2]", TrDiagCode.OUT_OF_RANGE)])

    def test_a_charge_sum_that_overflows_is_reported(self):
        # PZ * PN overflows to inf at the centre: the comparison inf <= inf must not pass it as
        # quasi-neutral. (PZ = 2 puts the edge out too, at twice the electrons.)
        diags = _validate({"PZ[2]": 2.0, "PN[2]": 1e308})
        self.assertEqual(_pairs(diags), [("PN[1]", TrDiagCode.INCONSISTENT_PAIR),
                                         ("PNS[1]", TrDiagCode.INCONSISTENT_PAIR)])
        self.assertIn("ions' charge sum PZ*n  Infinity", diags[0][2])

    def test_a_reported_case_still_runs(self):
        # Reported, not refused: ions at 0.8 of the electrons run on TR's defaults (measured to 10 steps).
        with _pushd(FIXTURES_DIR):
            with Trlib() as tr:
                tr.set_param("PN[2]", 0.4)
                self.assertEqual([d.param for d in tr.validate()], ["PN[1]"])
                tr.set_param("NTMAX", 2.0)
                tr.run(2)
                state = tr.get_state()
        self.assertTrue(all(math.isfinite(v) for v in state.scalars.values()), state.scalars)


if __name__ == "__main__":
    unittest.main()
