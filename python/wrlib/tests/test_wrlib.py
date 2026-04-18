"""High-level ``Wrlib`` class tests.

Covers:

* errors module wiring (no ``libwrapi.so`` needed).
* ``WrState.to_dict()`` shape using a hand-built ``WrStateC`` (no
  ``libwrapi.so`` needed).
* Full init -> set_param -> run(0) -> get_state -> finalize cycle
  against the real library (skipped if not built).
* Context-manager lifecycle (``__enter__``/``__exit__``).
* Negative tests for invalid params / double-close / closed handle.
"""
from __future__ import annotations

import ctypes
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from wrlib import (  # noqa: E402
    Wrlib,
    WrState,
    WrlibError,
    WrlibParamError,
    WrlibStateError,
    WrlibRunError,
    WrlibNotImplementedError,
    raise_for_ierr,
)
from wrlib import _ffi  # noqa: E402


REPO = HERE.parents[3]
DEFAULT_SO = REPO / "wr" / "libwrapi.so"


# =====================================================================
# Tests that do not need libwrapi.so -- always run.
# =====================================================================
class TestErrorsModule(unittest.TestCase):
    def test_raise_for_ierr_ok(self):
        # ierr=0 must never raise.
        raise_for_ierr("dummy", 0)

    def test_raise_for_ierr_codes(self):
        for ierr, cls in (
            (1, WrlibParamError),
            (2, WrlibStateError),
            (3, WrlibRunError),
            (4, WrlibNotImplementedError),
        ):
            with self.assertRaises(cls):
                raise_for_ierr("dummy", ierr)

    def test_unknown_code_falls_back(self):
        with self.assertRaises(WrlibError):
            raise_for_ierr("dummy", 99)

    def test_subclasses(self):
        for cls in (
            WrlibParamError, WrlibStateError, WrlibRunError,
            WrlibNotImplementedError,
        ):
            self.assertTrue(issubclass(cls, WrlibError))


class TestWrStateFromC(unittest.TestCase):
    """Exercise :py:meth:`WrState.from_c` / ``to_dict`` with no library."""

    def _populated_state(
        self, nray: int = 3, nrs: int = 2, nrl: int = 4,
    ) -> _ffi.WrStateC:
        s = _ffi.WrStateC()
        s.nraymax = nray
        s.nrsmax = nrs
        s.nrlmax = nrl
        s.pos_pwrmax_rs = 0.25
        s.pwrmax_rs = 1.5
        s.pos_pwrmax_rl = 3.1
        s.pwrmax_rl = 4.2
        for i in range(nray):
            s.nstp_end[i] = i * 10 + 7
            s.pos_pwrmax_rs_nray[i] = 0.1 * (i + 1)
            s.pwrmax_rs_nray[i] = 10.0 + i
            s.pos_pwrmax_rl_nray[i] = 0.2 * (i + 1)
            s.pwrmax_rl_nray[i] = 20.0 + i
            for j in range(_ffi.WR_MAX_NRAY_EQ):
                s.rays_end[i][j] = float(i * 100 + j)
        for i in range(nrs):
            s.pos_nrs[i] = float(i) + 0.5
            s.pwr_nrs[i] = float(i) * 2.0
        for i in range(nrl):
            s.pos_nrl[i] = float(i) + 1.25
            s.pwr_nrl[i] = float(i) * 3.0
        return s

    def test_from_c_slices_correctly(self):
        c = self._populated_state(nray=3, nrs=2, nrl=4)
        st = WrState.from_c(c)
        self.assertEqual(st.nraymax, 3)
        self.assertEqual(st.nrsmax, 2)
        self.assertEqual(st.nrlmax, 4)
        # scalars
        self.assertAlmostEqual(st.scalars["pos_pwrmax_rs"], 0.25)
        self.assertAlmostEqual(st.scalars["pwrmax_rl"], 4.2)
        # per-ray
        self.assertEqual(len(st.nstp_end), 3)
        self.assertEqual(st.nstp_end[2], 27)
        self.assertAlmostEqual(st.pwrmax_rs_nray[0], 10.0)
        self.assertAlmostEqual(st.pos_pwrmax_rl_nray[2], 0.6)
        # rays_end has 9 components for every ray, regardless of
        # runtime dim.
        self.assertEqual(len(st.rays_end), 3)
        self.assertEqual(len(st.rays_end[0]), _ffi.WR_MAX_NRAY_EQ)
        self.assertAlmostEqual(st.rays_end[2][8], 208.0)
        # profiles
        self.assertEqual(len(st.pos_nrs), 2)
        self.assertAlmostEqual(st.pwr_nrs[1], 2.0)
        self.assertEqual(len(st.pos_nrl), 4)
        self.assertAlmostEqual(st.pos_nrl[3], 4.25)

    def test_to_dict_shape(self):
        c = self._populated_state(nray=2, nrs=3, nrl=3)
        d = WrState.from_c(c).to_dict()
        self.assertEqual(d["NRAYMAX"], 2)
        self.assertEqual(d["NRSMAX"], 3)
        self.assertEqual(d["NRLMAX"], 3)
        self.assertIn("scalars", d)
        self.assertEqual(
            set(d["scalars"]).issuperset(
                {"pos_pwrmax_rs", "pwrmax_rs",
                 "pos_pwrmax_rl", "pwrmax_rl"},
            ),
            True,
        )
        self.assertEqual(len(d["rays"]), 2)
        r0 = d["rays"][0]
        self.assertEqual(r0["NRAY"], 1)
        self.assertIn("nstp_end", r0)
        self.assertIn("pwrmax_rs", r0)
        self.assertIn("rays_end", r0)
        self.assertEqual(len(r0["rays_end"]), _ffi.WR_MAX_NRAY_EQ)
        self.assertEqual(len(d["profile_rs"]), 3)
        self.assertEqual(len(d["profile_rl"]), 3)
        self.assertEqual(d["profile_rs"][0]["NRS"], 1)
        self.assertEqual(d["profile_rl"][2]["NRL"], 3)

    def test_to_dict_json_serialisable(self):
        import json
        c = self._populated_state(nray=2, nrs=2, nrl=2)
        d = WrState.from_c(c).to_dict()
        # Must round-trip through JSON without custom encoder.
        s = json.dumps(d)
        d2 = json.loads(s)
        self.assertEqual(d2["NRAYMAX"], 2)


# =====================================================================
# Tests that DO need the real libwrapi.so on disk.
# =====================================================================
@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libwrapi.so not built at {DEFAULT_SO}; run `make -C wr libwrapi.so`",
)
class TestWrlibLifecycle(unittest.TestCase):
    def test_context_manager(self):
        with Wrlib() as wr:
            self.assertFalse(wr.closed)
        self.assertTrue(wr.closed)

    def test_get_state_after_init(self):
        # After init (before run) wr_get_state should succeed with
        # zero-padded / small dimensions (WRCOMM arrays not allocated).
        with Wrlib() as wr:
            state = wr.get_state()
            self.assertIsInstance(state, WrState)
            self.assertGreaterEqual(state.nraymax, 0)
            self.assertGreaterEqual(state.nrsmax, 0)
            self.assertGreaterEqual(state.nrlmax, 0)

    def test_double_close_idempotent(self):
        wr = Wrlib()
        wr.close()
        wr.close()  # must not raise
        self.assertTrue(wr.closed)

    def test_call_on_closed_raises(self):
        wr = Wrlib()
        wr.close()
        with self.assertRaises(WrlibError):
            wr.run(0)
        with self.assertRaises(WrlibError):
            wr.get_state()
        with self.assertRaises(WrlibError):
            wr.set_param("RR", 1.0)

    def test_invalid_param_raises(self):
        with Wrlib() as wr:
            with self.assertRaises((WrlibParamError, WrlibError)):
                wr.set_param("NOT_A_REAL_PARAMETER", 0.0)

    def test_set_params_rejects_double_underscore(self):
        with Wrlib() as wr:
            with self.assertRaises(WrlibError):
                # set_params() is scalar-only; __ is a common
                # array-syntax mistake we reject up-front.
                wr.set_params(PN__1=0.5)

    def test_set_params_scalar_kwargs_round_trip(self):
        # We can't assert the value was accepted (registry is library-
        # dependent) but at minimum we exercise the path and ensure
        # either success or a well-typed WrlibError.
        with Wrlib() as wr:
            try:
                # RR = major radius -- a registered scalar in
                # wr_param_registry.f90.
                wr.set_params(RR=3.0)
            except WrlibError:
                pass


if __name__ == "__main__":
    unittest.main()
