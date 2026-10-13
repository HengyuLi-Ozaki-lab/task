"""``tr_run`` refuses an active species whose namelist profile cannot be
evolved; ``validate()`` reports the same findings (#189).

With ``MDLUF=0`` (every fixture in the repo) ``tr_prof`` builds the
density and temperature of species ``1..NSMAX`` from the namelist pairs
``PN/PNS`` (centre / edge density) and ``PT/PTS`` (centre / edge
temperature). The transport step divides by both, so a species whose
density is identically zero (``PN=PNS=0``, the ``tr_init`` default for
species 3 and 4) or negative, or whose temperature is non-positive at
the centre or the edge, turns every scalar into NaN after one step.
``PN=0`` with ``PNS>0`` runs finite and stays allowed.

``tr_run`` now returns ``TR_ERR_INVALID`` (``TrlibParamError``) before
``tr_prep`` with one ``XX tr_run:`` line per finding on unit 6, and
``tr_validate`` emits the same findings as diagnostics named by the
registry spelling (``PN[3]``, ``PT[3]``, ...). Non-finite values are
refused as well, and so is ``NSMAX`` above the compile-time ``NSM``
(which only ``validate()`` used to report). The check covers every
``MDLUF`` outside the UFILE modes 1/2/3 (tr_prof's namelist branch).
One test per case, no ``subTest``.
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

from trlib import Trlib, TrDiagCode, TrlibParamError  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"
FIXTURES_DIR = HERE.parent / "fixtures"
EQDATA = FIXTURES_DIR / "eqdata.TST-2"

NTMAX = 2


@contextlib.contextmanager
def _pushd(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
@unittest.skipUnless(EQDATA.exists(), f"fixture missing: {EQDATA}")
class TestSpeciesProfileChecks(unittest.TestCase):
    """tst2 fixture + NSMAX=3; species 3 is driven through the cases."""

    def _run(self, mutations: dict):
        from trlib.tests.fixtures import tr_tst2_params as base
        with _pushd(FIXTURES_DIR):
            with Trlib() as tr:
                base.apply(tr)
                tr.set_param("NTMAX", float(NTMAX))
                for name, value in mutations.items():
                    tr.set_param(name, float(value))
                tr.run(NTMAX)
                return tr.get_state()

    def _validate(self, mutations: dict):
        from trlib.tests.fixtures import tr_tst2_params as base
        with _pushd(FIXTURES_DIR):
            with Trlib() as tr:
                base.apply(tr)
                for name, value in mutations.items():
                    tr.set_param(name, float(value))
                return tr.validate()

    @staticmethod
    def _finite(state) -> bool:
        def ok(v):
            return not math.isnan(v) and not math.isinf(v)
        return (all(ok(v) for v in state.scalars.values())
                and all(ok(v) for row in state.RN for v in row)
                and all(ok(v) for row in state.RT for v in row))

    # A species-3 profile the solver can evolve (used by the accept cases).
    SPECIES_3 = {"NSMAX": 3, "PN[3]": 0.005, "PNS[3]": 0.0005,
                 "PT[3]": 0.001, "PTS[3]": 0.0001}

    # --- refused before tr_prep ------------------------------------------

    def test_default_species_3_is_refused(self):
        # tr_init leaves PN(3)=PNS(3)=0: zero density everywhere.
        with self.assertRaises(TrlibParamError):
            self._run({"NSMAX": 3})

    def test_zero_density_everywhere_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PN[3]": 0.0, "PNS[3]": 0.0})

    def test_negative_centre_density_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PN[3]": -0.001})

    def test_negative_edge_density_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PNS[3]": -0.0001})

    def test_zero_centre_temperature_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PT[3]": 0.0})

    def test_zero_edge_temperature_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PTS[3]": 0.0})

    def test_negative_temperature_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PT[3]": -0.001})

    def test_nan_density_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PN[3]": float("nan")})

    def test_infinite_temperature_is_refused(self):
        with self.assertRaises(TrlibParamError):
            self._run({**self.SPECIES_3, "PT[3]": float("inf")})

    def test_nsmax_above_compile_time_maximum_is_refused_at_run(self):
        # The registry accepts NSMAX up to 8 (C ABI capacity); the solver
        # is compiled for NSM=4. validate() already reports it; run()
        # must not reach tr_prep with it even when every profile is set.
        mutations = {"NSMAX": 5}
        for ns in (3, 4, 5):
            mutations.update({f"PN[{ns}]": 0.001, f"PNS[{ns}]": 0.0001,
                              f"PT[{ns}]": 0.001, f"PTS[{ns}]": 0.0001})
        with self.assertRaises(TrlibParamError):
            self._run(mutations)

    def test_unsupported_mdluf_takes_the_namelist_branch_and_is_refused(self):
        # tr_prof's `select case(MDLUF)` has cases 1/2/3 and a default
        # namelist branch, so MDLUF=4 is checked like MDLUF=0.
        with self.assertRaises(TrlibParamError):
            self._run({"NSMAX": 3, "MDLUF": 4})

    def test_zero_density_of_species_2_is_refused_not_a_run_error(self):
        # NSMAX=2 with PN(2)=PNS(2)=0 used to fail inside tr_loop
        # (TrlibRunError, ierr=3); it is now refused up front like the
        # other cases.
        with self.assertRaises(TrlibParamError):
            self._run({"PN[2]": 0.0, "PNS[2]": 0.0})

    # --- accepted ----------------------------------------------------------

    def test_species_3_with_profiles_runs_finite(self):
        state = self._run(self.SPECIES_3)
        self.assertEqual(state.nsmax, 3)
        self.assertTrue(self._finite(state), state.scalars)

    def test_zero_centre_density_with_edge_density_runs_finite(self):
        # PN=0, PNS>0 gives a non-zero profile; allowed and finite.
        state = self._run({**self.SPECIES_3, "PN[3]": 0.0})
        self.assertTrue(self._finite(state), state.scalars)

    def test_fixture_as_is_runs_finite(self):
        state = self._run({})
        self.assertEqual(state.nsmax, 2)
        self.assertTrue(self._finite(state), state.scalars)

    def test_handle_stays_usable_after_refusal(self):
        from trlib.tests.fixtures import tr_tst2_params as base
        with _pushd(FIXTURES_DIR):
            with Trlib() as tr:
                base.apply(tr)
                tr.set_param("NTMAX", float(NTMAX))
                tr.set_param("NSMAX", 3.0)
                with self.assertRaises(TrlibParamError):
                    tr.run(NTMAX)
                for name, value in self.SPECIES_3.items():
                    tr.set_param(name, float(value))
                tr.run(NTMAX)
                state = tr.get_state()
        self.assertEqual(state.nsmax, 3)
        self.assertTrue(self._finite(state), state.scalars)

    # --- validate() reports the same findings ------------------------------

    def test_validate_default_species_3(self):
        diags = self._validate({"NSMAX": 3})
        pn = [d for d in diags if d.param == "PN[3]"]
        self.assertEqual(len(pn), 1, diags)
        self.assertEqual(pn[0].code, TrDiagCode.OUT_OF_RANGE_AFTER_DEP)
        self.assertIn("NSMAX", pn[0].message)
        self.assertEqual([d.param for d in diags if d.param.startswith("PT")], [])

    def test_validate_negative_density_and_zero_temperatures(self):
        diags = self._validate({**self.SPECIES_3, "PN[3]": -0.001,
                                "PT[3]": 0.0, "PTS[3]": 0.0})
        by_param = {d.param: d for d in diags}
        self.assertEqual(set(by_param), {"PN[3]", "PT[3]", "PTS[3]"}, diags)
        for name in ("PN[3]", "PT[3]", "PTS[3]"):
            self.assertEqual(by_param[name].code, TrDiagCode.OUT_OF_RANGE, name)

    def test_validate_non_finite_values(self):
        diags = self._validate({**self.SPECIES_3, "PNS[3]": float("-inf")})
        self.assertEqual([d.param for d in diags], ["PN[3]"], diags)
        self.assertEqual(diags[0].code, TrDiagCode.OUT_OF_RANGE)
        self.assertIn("non-finite", diags[0].message)

    def test_validate_clean_when_species_3_has_profiles(self):
        diags = self._validate(self.SPECIES_3)
        self.assertEqual(diags, [])

    def test_validate_only_looks_at_active_species(self):
        # Species 3/4 keep PN=PNS=0 but are inactive with NSMAX=2.
        diags = self._validate({"NSMAX": 2})
        self.assertEqual(diags, [])


if __name__ == "__main__":
    unittest.main()
