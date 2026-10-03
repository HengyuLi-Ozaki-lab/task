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
  blank;
* the plasma-extent check against the ``RGMIN..ZGMAX`` box fires only
  when the solver reads that box (``MODELG=2`` and ``MDLEQF >= 10``),
  each case checked against a real ``run(0)``.

Skipped automatically when ``libeqapi.so`` has not been built.
"""
from __future__ import annotations

import contextlib
import math
import os
import sys
import tempfile
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
    EqlibCalculationFailedError,
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

    # --- wall-vs-minor-radius and plasma-extent cross-checks ---------------

    def test_validate_rb_less_than_ra_emits_inconsistent_pair(self) -> None:
        """RB < RA (wall inside the plasma) is flagged: the solver can
        abort or return a wrong equilibrium (a large device, RR=6.2,
        RA=2.0, run with RB left at the small-tokamak default 1.2, aborts
        the process in EQCALQP). MODELG-agnostic: fires under the
        eq_init default MODELG=2 with no override."""
        with Eq() as eq:
            eq.set_params(RR=6.2, RA=2.0)      # RB left at default (1.2)
            diags = eq.validate()

        codes = [d.code for d in diags]
        self.assertIn(int(EqDiagCode.INCONSISTENT_PAIR), codes)
        rb_diags = [d for d in diags if d.code == EqDiagCode.INCONSISTENT_PAIR]
        self.assertEqual(len(rb_diags), 1)
        self.assertEqual(rb_diags[0].param, "RB")
        self.assertIn("RB=1.200 < minor radius RA=2.000", rb_diags[0].message)
        self.assertIn("solver can abort", rb_diags[0].message)

    def test_validate_wall_inside_plasma_on_a_large_device_flags_only_the_wall(
        self,
    ) -> None:
        """Large device (RR=6.2, RA=2.0), RB left at 1.2 < RA, MODELG=2,
        MDLEQF at its default: the wall check fires and the extent check
        does not. The box RGMIN..ZGMAX is not read by a default-MDLEQF
        solve (see TestEqValidateBoxGate), so the plasma being outside
        it is no finding. The run itself is not attempted: it aborts the
        process (the RB<RA case above)."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, RR=6.2, RA=2.0)
            diags = eq.validate()

        self.assertEqual(
            [(d.param, d.code) for d in diags],
            [("RB", EqDiagCode.INCONSISTENT_PAIR)],
            f"expected only the wall diagnostic, got {diags}")

    def test_validate_wall_inside_plasma_with_mdleqf_10_adds_the_extent_diagnostics(
        self,
    ) -> None:
        """The same input with MDLEQF=10 (the solver reads the box) trips
        the wall check and both extent checks."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=6.2, RA=2.0)
            diags = eq.validate()

        self.assertTrue(diags, "expected non-empty diagnostics")
        messages = " ".join(d.message for d in diags)
        self.assertIn("R-grid", messages)
        codes = {d.code for d in diags}
        self.assertIn(int(EqDiagCode.OUT_OF_RANGE_AFTER_DEP), codes)
        self.assertIn(int(EqDiagCode.INCONSISTENT_PAIR), codes)

    def test_validate_r_extent_uses_ra_not_rb(self) -> None:
        """R-extent basis is RA (plasma minor radius), NOT RB (wall).
        MDLEQF=10 throughout: only then does the box RGMIN..ZGMAX matter.

        Discriminating case (RR=4.0/RA=1.0/RB=1.9 fires under BOTH bases,
        so it cannot catch an RB-basis regression): RR=4.0, RA=0.4,
        RB=0.6 is CLEAN under the RA basis (extent [3.6, 4.4] inside
        [1.5, 4.5]) but an RB-basis implementation would fire ([3.4, 4.6]
        -> 4.6 > RGMAX=4.5). Cleanness here is what pins the RA basis.
        Wall is healthy (RB=0.6 >= RA=0.4) and Z-extent 1.0*0.4 is tiny,
        so the whole diagnostics list must be empty."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=4.0, RA=0.4, RB=0.6)
            diags = eq.validate()
        self.assertEqual(
            diags, [],
            "RA-basis clean case fired — extent check is using the wall RB?")

        # Firing direction (kept from the original test): a healthy wall
        # (RB >= RA) with RR+RA = 5.0 > RGMAX must trip exactly one
        # OUT_OF_RANGE_AFTER_DEP naming RR, with NO wall diag alongside.
        with Eq() as eq:
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=4.0, RA=1.0, RB=1.9)
            diags = eq.validate()

        wall_diags = [d for d in diags if d.code == EqDiagCode.INCONSISTENT_PAIR]
        self.assertEqual(wall_diags, [], "healthy wall (RB>=RA) must not also fire")
        extent_diags = [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]
        self.assertEqual(len(extent_diags), 1)
        self.assertEqual(extent_diags[0].param, "RR")
        self.assertIn("R-grid", extent_diags[0].message)

    def test_validate_survives_unprintable_extreme_geometry(self) -> None:
        """IOSTAT hardening pin (review follow-up): RR=1e30 makes the
        R-extent diagnostic's F0.3 rendering exceed the CHARACTER(128)
        msgbuf — an unguarded internal WRITE hits gfortran's "End of
        record" and ABORTS the whole process (library-reachable abort
        inside the function whose purpose is returning diagnostics
        instead of crashing; reproduced live pre-fix). With IOSTAT
        guards, validate() must SURVIVE and still return a non-empty
        list naming RR via the static fallback message."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=1.0e30, RA=1.0)
            diags = eq.validate()      # pre-fix: process abort (exit 2)

        self.assertTrue(diags, "expected diagnostics for RR=1e30")
        rr_diags = [d for d in diags if d.param == "RR"]
        self.assertEqual(len(rr_diags), 1)
        self.assertEqual(rr_diags[0].code, EqDiagCode.OUT_OF_RANGE_AFTER_DEP)
        self.assertIn("R-grid", rr_diags[0].message)

    def test_validate_z_extent_uses_kappa_times_ra(self) -> None:
        """Z-extent = RKAP*RA (RA basis) must fit ZGMIN/ZGMAX (MDLEQF=10:
        the solver reads the box). RKAP=1.9, RA=1.0 -> 1.9 < 2.0 is clean
        under the RA basis; the wall basis (RKAP*RB=1.9*1.2=2.28 > 2.0)
        would falsely reject it."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=3.0, RA=1.0, RKAP=1.9, RB=1.2)
            diags = eq.validate()
        self.assertEqual(
            diags, [], "RKAP*RA inside the Z box must validate cleanly (RA basis)")

        with Eq() as eq:
            # RKAP*RA = 1.5*1.4 = 2.1 > ZGMAX=2.0; RB=2.0 >= RA=1.4 (healthy wall);
            # R-extent [1.6, 4.4] stays inside [1.5, 4.5] (extent-clean on R).
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=3.0, RA=1.4, RKAP=1.5, RB=2.0)
            diags = eq.validate()
        extent_diags = [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]
        self.assertEqual(len(extent_diags), 1)
        self.assertEqual(extent_diags[0].param, "RKAP")
        self.assertIn("Z-extent", extent_diags[0].message)

    def test_validate_modelg3_skips_grid_extent_check(self) -> None:
        """SCOPING REGRESSION: the R/Z-extent check is MODELG==2 only.
        The ITER01 fixture geometry (RR=6.2, RA=2.0) sits far outside the
        default box under the RA basis (RR+RA=8.2 >> RGMAX=4.5) yet is a
        clean MODELG=3 (TASK-native EQRTSK load — eq/eqfile.f90's EQ_READ
        dispatch, NOT the EQDSK reader, which serves MODELG=5/25)
        configuration at the default MDLEQF — see
        test_init_set_run_get_state_cycle_iter01 in eq_mcp's tests, which
        exercises this exact geometry end-to-end via eq_run(1). A file
        load sets the geometry itself, so the pre-run RR/RA say nothing
        about the loaded plasma and the check must stay gated to
        MODELG==2. MDLEQF=10 is set here so that the MODELG gate, not the
        MDLEQF gate, is what keeps this case clean. (A load with
        MDLEQF >= 10 still reads the box in EQAXIS: ITER01 then fails with
        the default box, ierr=103, and validate() cannot see it.)"""
        with Eq() as eq:
            eq.set_params(MODELG=3.0, MDLEQF=10.0, RR=6.2, RA=2.0, RB=2.1)
            eq.set_param_str("KNAMEQ", "eqdata.ITER01")
            diags = eq.validate()
        extent_diags = [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]
        self.assertEqual(
            extent_diags, [],
            "grid-extent check must not fire for MODELG=3 (EQDSK load)")


@contextlib.contextmanager
def _in_tempdir():
    """Run the body in a scratch directory (a solve may write files)."""
    prev = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            yield tmp
        finally:
            os.chdir(prev)


# An ITER-sized analytic case: RR +/- RA = [4.2, 8.2] and the half-height
# RKAP*RA = 3.4 lie far outside the default box RGMIN..ZGMAX =
# [1.5, 4.5] x [-2, 2]; the wall RB = 2.1 encloses the plasma.
LARGE_DEVICE = dict(MODELG=2.0, RR=6.2, RA=2.0, RKAP=1.7, RB=2.1)


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)
class TestEqValidateBoxGate(unittest.TestCase):
    """validate() compares the plasma extent with RGMIN..ZGMAX only when
    the solver reads that box: MODELG=2 and MDLEQF >= 10.

    The solver reads the box in one place, EQAXIS (eq/eqsub.f90): with
    MDLEQF < 10 the window the axis must lie in, and the bound of the
    outer-edge search, is RR +/- RB, +/- RKAP*RB (the same box EQTORZ
    tabulates psi on, eq/eqcalc.f90); with MDLEQF >= 10 it is RGMIN,
    RGMAX, ZGMIN, ZGMAX. EQCALQP overwrites the four with the traced
    plasma extent after the solve for any MDLEQF, so below 10 they are
    outputs only. Every test pairs validate() with a real run(0) (except
    MDLEQF=9, whose run aborts), so a diagnostic is tied to what the
    solver does with the same input.
    """

    @staticmethod
    def _extent(diags):
        return [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]

    @staticmethod
    def _validate_then_run(**params):
        """(diagnostics, error from run(0) or None, state or None)."""
        with Eq() as eq:
            eq.set_params(**params)
            diags = eq.validate()
            with _in_tempdir():
                try:
                    eq.run(0)
                except EqlibCalculationFailedError as exc:
                    return diags, exc, None
                return diags, None, eq.get_state()

    def _assert_clean_run(self, state) -> None:
        self.assertIsNotNone(state)
        for key in ("raxis", "qaxis", "qsurf", "pvol"):
            self.assertTrue(math.isfinite(state.scalars[key]),
                            f"{key} = {state.scalars[key]}")

    def test_defaults_are_clean_and_run(self) -> None:
        diags, err, state = self._validate_then_run(MODELG=2.0)
        self.assertEqual(diags, [])
        self.assertIsNone(err)
        self._assert_clean_run(state)

    def test_large_device_at_default_mdleqf_has_no_extent_diagnostic(self) -> None:
        """(a) MDLEQF < 10 ignores the box: validate() is clean and the
        run succeeds, though the plasma is far outside [1.5, 4.5]."""
        diags, err, state = self._validate_then_run(**LARGE_DEVICE)
        self.assertEqual(self._extent(diags), [],
                         f"extent diagnostic for a default-MDLEQF solve: {diags}")
        self.assertEqual(diags, [])
        self.assertIsNone(err, f"run(0) failed: {err}")
        self._assert_clean_run(state)

    def test_large_device_with_mdleqf_10_flags_both_extents_and_run_fails(self) -> None:
        """(b) MDLEQF=10 makes the default box the axis window: the same
        input gets both extent diagnostics and the run fails (EQAXIS:
        axis out of plasma, ierr=103)."""
        diags, err, state = self._validate_then_run(MDLEQF=10.0, **LARGE_DEVICE)
        extent = self._extent(diags)
        self.assertEqual(sorted(d.param for d in extent), ["RKAP", "RR"], str(diags))
        by_param = {d.param: d.message for d in extent}
        self.assertIn("R-extent [4.200, 8.200]", by_param["RR"])
        self.assertIn("RGMIN..RGMAX [1.500, 4.500]", by_param["RR"])
        self.assertIn("Z-extent +/-3.400", by_param["RKAP"])
        self.assertIn("ZGMIN..ZGMAX [-2.000, 2.000]", by_param["RKAP"])
        for message in by_param.values():
            self.assertIn("MDLEQF >= 10", message)
        self.assertIsNotNone(err, "run(0) should fail with the default box")
        self.assertIn("ierr=103", str(err))
        self.assertIsNone(state)

    def test_large_device_with_mdleqf_11_is_gated_like_10(self) -> None:
        """The gate is `>= 10`, not `== 10`."""
        diags, err, _ = self._validate_then_run(MDLEQF=11.0, **LARGE_DEVICE)
        self.assertEqual(sorted(d.param for d in self._extent(diags)), ["RKAP", "RR"])
        self.assertIsNotNone(err, "run(0) should fail with the default box")
        self.assertIn("ierr=103", str(err))

    def test_mdleqf_10_with_a_box_around_the_plasma_is_clean_and_runs(self) -> None:
        """(c) The box set around the plasma (inside the wall box
        4.1..8.3 x +/-3.57): no diagnostic, and the run succeeds."""
        diags, err, state = self._validate_then_run(
            MDLEQF=10.0, RGMIN=4.15, RGMAX=8.25, ZGMIN=-3.5, ZGMAX=3.5,
            **LARGE_DEVICE)
        self.assertEqual(diags, [], str(diags))
        self.assertIsNone(err, f"run(0) failed: {err}")
        self._assert_clean_run(state)

    def test_mdleqf_between_1_and_9_is_not_gated_on_the_box(self) -> None:
        """(d) MDLEQF=2 (neither the default 0 nor >= 10): like the
        default, the box is not read, so no diagnostic and the run
        succeeds."""
        diags, err, state = self._validate_then_run(MDLEQF=2.0, **LARGE_DEVICE)
        self.assertEqual(diags, [], str(diags))
        self.assertIsNone(err, f"run(0) failed: {err}")
        self._assert_clean_run(state)

    def test_mdleqf_9_is_below_the_gate(self) -> None:
        """MDLEQF=9 is the last value below the gate. Validate only: the
        spline-profile models 5..9 abort run(0) with this input, whatever
        the box."""
        with Eq() as eq:
            eq.set_params(MDLEQF=9.0, **LARGE_DEVICE)
            diags = eq.validate()
        self.assertEqual(diags, [], str(diags))

    def test_longest_printable_extent_messages_keep_their_ending(self) -> None:
        """RR=1e12 gives a 126-character R-extent message that prints in
        full. RR=1e13 gives one of exactly 128 characters, which the
        127-character C field cut (the closing parenthesis was lost): it
        now takes the fallback text. Both end with the closing
        parenthesis."""
        messages = {}
        for rr in (1.0e12, 1.0e13):
            with Eq() as eq:
                eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=rr, RA=1.0)
                diags = eq.validate()
            messages[rr] = [d.message for d in diags if d.param == "RR"]
        self.assertEqual([len(m) for m in messages.values()], [1, 1], str(messages))
        self.assertTrue(messages[1.0e12][0].endswith("(solver box for MDLEQF >= 10)"),
                        messages[1.0e12][0])
        self.assertTrue(messages[1.0e13][0].endswith(")"), messages[1.0e13][0])

    def test_state_grid_is_rr_pm_rb_whatever_the_box(self) -> None:
        """The box is not the grid psi is tabulated on: with MDLEQF=10 and
        a box that differs from RR +/- RB on every side, state.rg / state.zg
        still span RR +/- RB and +/- RKAP*RB (EQTORZ)."""
        _, err, state = self._validate_then_run(
            MDLEQF=10.0, RGMIN=4.15, RGMAX=8.25, ZGMIN=-3.5, ZGMAX=3.5,
            **LARGE_DEVICE)
        self.assertIsNone(err)
        self.assertAlmostEqual(state.rg[0], 6.2 - 2.1, places=9)
        self.assertAlmostEqual(state.rg[state.nrgmax - 1], 6.2 + 2.1, places=9)
        self.assertAlmostEqual(state.zg[0], -1.7 * 2.1, places=9)
        self.assertAlmostEqual(state.zg[state.nzgmax - 1], 1.7 * 2.1, places=9)


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
