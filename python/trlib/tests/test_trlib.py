"""High-level ``Trlib`` class tests.

Covers:

* errors module wiring (no ``libtrapi.so`` needed).
* ``TrState.to_dict()`` shape using a hand-built ``TrStateC`` (no
  ``libtrapi.so`` needed).
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

from trlib import (  # noqa: E402
    Trlib,
    TrState,
    TrlibError,
    TrlibParamError,
    TrlibStateError,
    TrlibRunError,
    TrlibNotImplementedError,
    raise_for_ierr,
)
from trlib import _ffi  # noqa: E402


REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"


# =====================================================================
# Tests that do not need libtrapi.so -- always run.
# =====================================================================
class TestErrorsModule(unittest.TestCase):
    def test_raise_for_ierr_ok(self):
        # ierr=0 must never raise.
        raise_for_ierr("dummy", 0)

    def test_raise_for_ierr_codes(self):
        for ierr, cls in (
            (1, TrlibParamError),
            (2, TrlibStateError),
            (3, TrlibRunError),
            (4, TrlibNotImplementedError),
        ):
            with self.assertRaises(cls):
                raise_for_ierr("dummy", ierr)

    def test_unknown_code_falls_back(self):
        with self.assertRaises(TrlibError):
            raise_for_ierr("dummy", 99)

    def test_subclasses(self):
        for cls in (
            TrlibParamError, TrlibStateError, TrlibRunError,
            TrlibNotImplementedError,
        ):
            self.assertTrue(issubclass(cls, TrlibError))


class TestTrStateFromC(unittest.TestCase):
    """Exercise :py:meth:`TrState.from_c` / ``to_dict`` with no library."""

    def _populated_state(self, nr: int = 3, ns: int = 2) -> _ffi.TrStateC:
        s = _ffi.TrStateC()
        s.nt = 7
        s.nrmax = nr
        s.nsmax = ns
        s.T = 1.25
        s.WPT = 2.5
        s.AJT = 3.75
        s.Q0 = 0.9
        s.BETA0 = 0.1
        s.BETAP0 = 0.2
        s.BETAA = 0.3
        s.BETAN = 0.4
        s.TAUE1 = 5.0
        s.TAUE2 = 6.0
        s.ZEFF0 = 1.5
        s.ALI = 0.7
        s.RQ1 = 1.1
        for i in range(nr):
            for j in range(ns):
                s.RN[i][j] = float(i * 10 + j)
                s.RT[i][j] = float(i * 10 + j) + 0.5
            s.AJ[i] = float(i) + 0.25
            s.QP[i] = float(i) + 0.75
        return s

    def test_from_c_slices_correctly(self):
        c = self._populated_state(nr=3, ns=2)
        st = TrState.from_c(c)
        self.assertEqual(st.nt, 7)
        self.assertEqual(st.nrmax, 3)
        self.assertEqual(st.nsmax, 2)
        self.assertEqual(len(st.RN), 3)
        self.assertEqual(len(st.RN[0]), 2)
        self.assertAlmostEqual(st.RN[2][1], 21.0)
        self.assertAlmostEqual(st.RT[1][0], 10.5)
        self.assertAlmostEqual(st.AJ[2], 2.25)
        self.assertAlmostEqual(st.QP[0], 0.75)
        self.assertAlmostEqual(st.scalars["T"], 1.25)
        self.assertAlmostEqual(st.scalars["ZEFF0"], 1.5)

    def test_to_dict_shape(self):
        c = self._populated_state(nr=2, ns=2)
        d = TrState.from_c(c).to_dict()
        self.assertEqual(d["NT"], 7)
        self.assertEqual(d["NRMAX"], 2)
        self.assertEqual(d["NSMAX"], 2)
        self.assertIn("scalars", d)
        self.assertEqual(set(d["scalars"]).issuperset({"T", "WPT", "ZEFF0"}), True)
        self.assertEqual(len(d["profile"]), 2)
        p0 = d["profile"][0]
        self.assertEqual(p0["NR"], 1)
        self.assertIn("RN", p0)
        self.assertIn("RT", p0)
        self.assertIn("AJ", p0)
        self.assertIn("QP", p0)
        self.assertEqual(len(p0["RN"]), 2)  # NSMAX entries

    def test_to_dict_json_serialisable(self):
        import json
        c = self._populated_state(nr=2, ns=2)
        d = TrState.from_c(c).to_dict()
        # Must round-trip through JSON without custom encoder.
        s = json.dumps(d)
        d2 = json.loads(s)
        self.assertEqual(d2["NRMAX"], 2)


# =====================================================================
# Tests that DO need the real libtrapi.so on disk.
# =====================================================================
@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)
class TestTrlibLifecycle(unittest.TestCase):
    def test_context_manager(self):
        with Trlib() as tr:
            self.assertFalse(tr.closed)
        self.assertTrue(tr.closed)

    def test_run_zero_and_get_state(self):
        with Trlib() as tr:
            tr.run(0)   # stubs may be no-op; we only require ierr==0
            state = tr.get_state()
            self.assertIsInstance(state, TrState)
            self.assertGreaterEqual(state.nrmax, 0)
            self.assertGreaterEqual(state.nsmax, 0)

    def test_double_close_idempotent(self):
        tr = Trlib()
        tr.close()
        tr.close()  # must not raise
        self.assertTrue(tr.closed)

    def test_call_on_closed_raises(self):
        tr = Trlib()
        tr.close()
        with self.assertRaises(TrlibError):
            tr.run(0)
        with self.assertRaises(TrlibError):
            tr.get_state()
        with self.assertRaises(TrlibError):
            tr.set_param("RR", 1.0)

    def test_invalid_param_raises(self):
        with Trlib() as tr:
            with self.assertRaises((TrlibParamError, TrlibError)):
                tr.set_param("NOT_A_REAL_PARAMETER", 0.0)

    def test_set_params_rejects_double_underscore(self):
        with Trlib() as tr:
            with self.assertRaises(TrlibError):
                # set_params() is scalar-only; __ is a common array-syntax
                # mistake we reject up-front.
                tr.set_params(PN__1=0.5)

    def test_set_params_scalar_kwargs_round_trip(self):
        # We can't assert the value was accepted (registry is library-
        # dependent) but at minimum we exercise the path and ensure
        # either success or a well-typed TrlibError.
        with Trlib() as tr:
            try:
                # RR = major radius -- a commonly registered scalar.
                tr.set_params(RR=3.0)
            except TrlibError:
                pass


if __name__ == "__main__":
    unittest.main()
