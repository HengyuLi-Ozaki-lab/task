"""High-level :py:meth:`Eq.validate` tests (Issue #143 pilot wrapper).

Exercises the supported Python surface introduced in the
``feat/eqlib-validate-python-wrapper`` PR. The same scenarios were
previously covered against raw ctypes; that path is preserved by the
underlying _ffi prototype but the user-facing tests now go through
:class:`Eq` so the coverage tracks the API contract.

Tests cover:

* the contract that constructing :class:`Eq` auto-initialises the
  library, so ``validate()`` after ``Eq()`` always sees an initialised
  state (the raw-ctypes "before init" smoke test is documented as a
  regression below — there is no Python entry point that lets a caller
  call validate before init without going around the wrapper);
* clean-default state after ``Eq()`` returns an empty list;
* OUT_OF_RANGE diagnostic fires for ``NRMAX`` above ``NRM=1001``;
* FILE_MISSING diagnostic fires when ``MODELG=3`` and ``KNAMEQ`` is
  blank.

Skipped automatically when ``libeqapi.so`` has not been built.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from eqlib import (  # noqa: E402
    Eq,
    EqDiagCode,
    EqDiagEntryPy,
    EqlibNotInitializedError,
)
from eqlib import _ffi  # noqa: E402

REPO = HERE.parents[3]
DEFAULT_SO = REPO / "eq" / "libeqapi.so"


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)
class TestEqValidate(unittest.TestCase):
    """High-level :py:meth:`Eq.validate` (Issue #143 pilot)."""

    def test_validate_after_close_raises_not_init(self) -> None:
        """Regression for the rc=2 (NOT_INIT) path.

        :class:`Eq` auto-initialises in ``__init__``, so the raw-ctypes
        "validate before init" scenario is unreachable through the
        wrapper. The closest user-visible equivalent is calling
        ``validate`` after ``close()``: the library is no longer
        initialised, and the wrapper raises
        :class:`EqlibNotInitializedError` (mapped from rc==2).
        """
        eq = Eq()
        eq.close()
        # Manually flip _closed back to False so validate() does not
        # short-circuit on the Python guard ("validate on closed Eq")
        # and instead exercises the underlying NOT_INIT contract from
        # the C library. This keeps the test honest about what the
        # Fortran side returns when g_initialized == .FALSE.
        eq._closed = False  # noqa: SLF001 - regression hook
        try:
            with self.assertRaises(EqlibNotInitializedError):
                eq.validate()
        finally:
            eq._closed = True  # noqa: SLF001

    def test_validate_clean_default_state_returns_empty_list(self) -> None:
        with Eq() as eq:
            diags = eq.validate()
        self.assertEqual(diags, [], "default eq state should validate cleanly")

    def test_validate_nrmax_overflow_emits_out_of_range(self) -> None:
        with Eq() as eq:
            # NRM compile-time max is 1001 (eq/eqcom0_mod.f90:29).
            eq.set_param("NRMAX", 9999.0)
            diags = eq.validate()

        self.assertGreaterEqual(len(diags), 1)
        e0 = diags[0]
        self.assertIsInstance(e0, EqDiagEntryPy)
        self.assertEqual(e0.param, "NRMAX")
        self.assertEqual(e0.code, EqDiagCode.OUT_OF_RANGE)
        self.assertIn("9999", e0.message)

    def test_validate_modelg3_blank_knameq_emits_file_missing(self) -> None:
        with Eq() as eq:
            # eq_init defaults are MODELG=2 / KNAMEQ='eqdata'; switch to
            # a MODELG that requires a file and clear KNAMEQ.
            eq.set_param("MODELG", 3.0)
            eq.set_param_str("KNAMEQ", "")
            diags = eq.validate()

        codes = [d.code for d in diags]
        self.assertIn(
            int(EqDiagCode.FILE_MISSING), codes,
            f"expected FILE_MISSING (code {int(EqDiagCode.FILE_MISSING)}) "
            f"in {codes}",
        )
        # The FILE_MISSING entry should refer to KNAMEQ specifically.
        knameq_diags = [
            d for d in diags
            if d.code == EqDiagCode.FILE_MISSING and d.param == "KNAMEQ"
        ]
        self.assertEqual(len(knameq_diags), 1)

    # --- M2-T7: grid-containment + wall-vs-minor-radius cross-checks ---
    # (task-web app/services/optimize/guards.py::eq_cross_checks upstream)

    def test_validate_rb_less_than_ra_emits_inconsistent_pair(self) -> None:
        """RB < RA (wall inside the plasma) is the reattributed M0
        live-crash class: the ITER preset (RR=6.2, RA=2.0 — see
        docs/superpowers/plans/2026-05-17-3d-tokamak-architecture-
        wiki.md's "iter" preset) run with RB left at the small-tokamak
        default (1.2) instead of an enclosing wall value. MODELG-
        agnostic: fires under the eq_init default MODELG=2 with no
        override. Mirrors guards.py::eq_cross_checks's RB<RA branch."""
        with Eq() as eq:
            eq.set_params(RR=6.2, RA=2.0)      # RB left at default (1.2)
            diags = eq.validate()

        codes = [d.code for d in diags]
        self.assertIn(int(EqDiagCode.INCONSISTENT_PAIR), codes)
        rb_diags = [d for d in diags if d.code == EqDiagCode.INCONSISTENT_PAIR]
        self.assertEqual(len(rb_diags), 1)
        self.assertEqual(rb_diags[0].param, "RB")
        self.assertIn("M0 crash class", rb_diags[0].message)

    def test_validate_m0_crash_preset_emits_nonempty_and_names_r_grid(self) -> None:
        """Decisive regression (Task 7 Step 2): the exact M0-verified
        crash case (RR=6.2, RA=2.0, default RB=1.2, MODELG=2) MUST now
        produce a non-empty validate() result naming the R-grid. It
        also trips the RB<RA wall check — both are genuine violations
        for this preset, so both are expected in the output."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, RR=6.2, RA=2.0)
            diags = eq.validate()

        self.assertTrue(diags, "expected non-empty diagnostics for the M0 crash preset")
        messages = " ".join(d.message for d in diags)
        self.assertIn("R-grid", messages)
        codes = {d.code for d in diags}
        self.assertIn(int(EqDiagCode.OUT_OF_RANGE_AFTER_DEP), codes)
        self.assertIn(int(EqDiagCode.INCONSISTENT_PAIR), codes)

    def test_validate_r_extent_uses_ra_not_rb(self) -> None:
        """R-extent basis is RA (plasma minor radius), NOT RB (wall): a
        healthy wall (RB >= RA) that still puts RR+/-RA outside the
        grid must independently trip OUT_OF_RANGE_AFTER_DEP naming RR,
        with NO wall violation reported alongside it."""
        with Eq() as eq:
            # RR+RA = 4.0+1.0 = 5.0 > RGMAX=4.5; RB=1.9 >= RA=1.0 (healthy wall).
            eq.set_params(MODELG=2.0, RR=4.0, RA=1.0, RB=1.9)
            diags = eq.validate()

        wall_diags = [d for d in diags if d.code == EqDiagCode.INCONSISTENT_PAIR]
        self.assertEqual(wall_diags, [], "healthy wall (RB>=RA) must not also fire")
        extent_diags = [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]
        self.assertEqual(len(extent_diags), 1)
        self.assertEqual(extent_diags[0].param, "RR")
        self.assertIn("R-grid", extent_diags[0].message)

    def test_validate_z_extent_uses_kappa_times_ra(self) -> None:
        """Z-extent = RKAP*RA (RA basis) must fit ZGMIN/ZGMAX. The true
        p1c ground-truth box corner (RKAP=1.9, RA=1.0 -> 1.9 < 2.0) is
        clean under the RA basis; the OLD RB basis (RKAP*RB=1.9*1.2=
        2.28>2.0) would have falsely rejected it (task-web guards.py
        commit 6002c5e) — this pins the fix on the Fortran side too."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, RR=3.0, RA=1.0, RKAP=1.9, RB=1.2)
            diags = eq.validate()
        self.assertEqual(
            diags, [], "true p1c box corner must validate cleanly under RA basis")

        with Eq() as eq:
            # RKAP*RA = 1.5*1.4 = 2.1 > ZGMAX=2.0; RB=2.0 >= RA=1.4 (healthy wall);
            # R-extent [1.6, 4.4] stays inside [1.5, 4.5] (extent-clean on R).
            eq.set_params(MODELG=2.0, RR=3.0, RA=1.4, RKAP=1.5, RB=2.0)
            diags = eq.validate()
        extent_diags = [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]
        self.assertEqual(len(extent_diags), 1)
        self.assertEqual(extent_diags[0].param, "RKAP")
        self.assertIn("Z-extent", extent_diags[0].message)

    def test_validate_modelg3_skips_grid_extent_check(self) -> None:
        """SCOPING REGRESSION (Task 7 reconciliation): the R/Z-extent
        check is MODELG==2 only. The ITER01 fixture geometry (RR=6.2,
        RA=2.0) sits far outside the default R-grid under the RA basis
        (RR+RA=8.2 >> RGMAX=4.5) yet is a legitimately-clean MODELG=3
        (EQDSK-load) configuration — see
        test_init_set_run_get_state_cycle_iter01 in eq_mcp's tests,
        which exercises this exact geometry end-to-end via eq_run(1).
        A MODELG-agnostic port of guards.py's check would regress that
        fixture, so it must stay gated to MODELG==2."""
        with Eq() as eq:
            eq.set_params(MODELG=3.0, RR=6.2, RA=2.0, RB=2.1)
            eq.set_param_str("KNAMEQ", "eqdata.ITER01")
            diags = eq.validate()
        extent_diags = [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]
        self.assertEqual(
            extent_diags, [],
            "grid-extent check must not fire for MODELG=3 (EQDSK load)")


class TestFFIBindings(unittest.TestCase):
    """Smoke tests for the new _ffi exports (no .so needed)."""

    def test_diag_constants_match_c_header(self) -> None:
        # Mirror the values from eq/eq_api.h enum eq_diag_code.
        self.assertEqual(_ffi.EQ_DIAG_OUT_OF_RANGE, 1)
        self.assertEqual(_ffi.EQ_DIAG_INCONSISTENT_PAIR, 2)
        self.assertEqual(_ffi.EQ_DIAG_OUT_OF_RANGE_AFTER_DEP, 3)
        self.assertEqual(_ffi.EQ_DIAG_FILE_MISSING, 4)
        self.assertEqual(_ffi.EQ_DIAG_MISSING_REQUIRED, 5)
        self.assertEqual(_ffi.EQ_DIAG_PARAM_LEN, 64)
        self.assertEqual(_ffi.EQ_DIAG_MSG_LEN, 128)

    def test_diag_struct_layout(self) -> None:
        # param[64] + int + msg[128] = 64 + 4 + 128 = 196 bytes (plus
        # potential trailing padding for 4-byte alignment, which is a
        # no-op here since 196 is already 4-aligned).
        import ctypes
        self.assertEqual(ctypes.sizeof(_ffi.EqDiagEntry), 64 + 4 + 128)

    def test_eq_diag_code_enum_matches_ffi(self) -> None:
        self.assertEqual(EqDiagCode.OUT_OF_RANGE, _ffi.EQ_DIAG_OUT_OF_RANGE)
        self.assertEqual(EqDiagCode.FILE_MISSING, _ffi.EQ_DIAG_FILE_MISSING)
        self.assertEqual(
            EqDiagCode.MISSING_REQUIRED, _ffi.EQ_DIAG_MISSING_REQUIRED
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
