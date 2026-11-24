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
  blank, and for the files every load format reads (``KNAMEQ`` for
  ``MODELG`` 3, 5, 8, 9 and 25, blank or naming no file, ``KNAMEQ2``
  too for 8: ``TestEqValidateFileMissing``), and ``MODELG`` 15, whose
  load ``run(1)`` refuses, is reported as ``OUT_OF_RANGE`` whatever the
  files;
* the wall check (``RB < RA``) is made for the analytic solve only
  (every ``MODELG`` but the file formats 3, 5, 8, 9, 15 and 25), not for
  a file load, which brings its own wall;
* the box check against ``RGMIN..ZGMAX`` is made only when the solver
  reads that box (an analytic solve with ``MDLEQF >= 10``), and flags
  only what fails or cuts the plasma there: ``RR`` outside
  ``RGMIN..RGMAX``, ``RGMAX`` below ``RR+RA``, a Z range without Z=0.
  The box and wall cases of ``TestEqValidateBoxGate`` and
  ``TestEqValidateWallGate`` are checked against a real ``run``, but at
  the exact bounds, where the run turns on rounding, for the message
  texts, and for the six file formats, which are checked by
  ``validate()`` alone.

Skipped automatically when ``libeqapi.so`` has not been built.
"""
from __future__ import annotations

import contextlib
import math
import os
import shutil
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
        the process in EQCALQP). Fires under the eq_init default
        MODELG=2 with no override."""
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

    def test_validate_wall_inside_plasma_with_mdleqf_10_adds_the_box_diagnostic(
        self,
    ) -> None:
        """The same input with MDLEQF=10 (the solver reads the box) trips
        the wall check and the box check: RR=6.2 lies outside
        RGMIN..RGMAX = [1.5, 4.5]."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=6.2, RA=2.0)
            diags = eq.validate()

        self.assertTrue(diags, "expected non-empty diagnostics")
        messages = " ".join(d.message for d in diags)
        self.assertIn("RR=6.200 outside RGMIN..RGMAX", messages)
        codes = {d.code for d in diags}
        self.assertIn(int(EqDiagCode.OUT_OF_RANGE_AFTER_DEP), codes)
        self.assertIn(int(EqDiagCode.INCONSISTENT_PAIR), codes)

    def test_validate_outer_edge_uses_ra_not_rb(self) -> None:
        """The outer edge RR+RA (plasma minor radius), NOT RR+RB (wall),
        is held against RGMAX. MDLEQF=10 throughout: only then does the
        box RGMIN..ZGMAX matter.

        Discriminating case (RR=4.0/RA=1.0/RB=1.9 fires under BOTH bases,
        so it cannot catch an RB-basis regression): RR=4.0, RA=0.4,
        RB=0.6 is CLEAN under the RA basis (edge 4.4 inside RGMAX=4.5)
        but an RB-basis implementation would fire (4.6 > 4.5).
        Cleanness here is what pins the RA basis. Wall is healthy
        (RB=0.6 >= RA=0.4), so the whole diagnostics list must be
        empty."""
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
        self.assertIn("outer edge RR+RA=5.000 lies 5.000E-01 beyond RGMAX=4.500", extent_diags[0].message)

    def test_validate_survives_unprintable_extreme_geometry(self) -> None:
        """IOSTAT hardening pin (review follow-up): RR=1e30 makes the
        RR diagnostic's F0.3 rendering exceed the CHARACTER(127)
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
        self.assertIn("RR outside RGMIN..RGMAX", rr_diags[0].message)
        self.assertIn("values unprintable", rr_diags[0].message)

    def test_validate_modelg3_skips_grid_extent_check(self) -> None:
        """SCOPING REGRESSION: the box check is for the analytic solve
        only (every MODELG but the file formats 3, 5, 8, 9, 15, 25).
        The ITER01 fixture geometry (RR=6.2, RA=2.0) sits far outside the
        default box under the RA basis (RR+RA=8.2 >> RGMAX=4.5) yet is a
        clean MODELG=3 (TASK-native EQRTSK load — eq/eqfile.f90's EQ_READ
        dispatch, NOT the EQDSK reader, which serves MODELG=5/25)
        configuration at the default MDLEQF — see
        test_init_set_run_get_state_cycle_iter01 in eq_mcp's tests, which
        exercises this exact geometry end-to-end via eq_run(1). A file
        load sets the geometry itself, so the pre-run RR/RA say nothing
        about the loaded plasma and the check must stay gated to
        the analytic MODELG. MDLEQF=10 is set here so that the MODELG gate, not the
        MDLEQF gate, is what keeps this case clean. (A load with
        MDLEQF >= 10 still reads the box in EQAXIS: ITER01 then fails with
        the default box, ierr=103, which validate() cannot see; the
        failure says where the axis search ended and names the box,
        test_load_errors.py.)"""
        with Eq() as eq:
            eq.set_params(MODELG=3.0, MDLEQF=10.0, RR=6.2, RA=2.0, RB=2.1)
            eq.set_param_str("KNAMEQ", "eqdata.ITER01")
            diags = eq.validate()
        extent_diags = [d for d in diags if d.code == EqDiagCode.OUT_OF_RANGE_AFTER_DEP]
        self.assertEqual(
            extent_diags, [],
            "box check must not fire for MODELG=3 (a TASK-native load)")


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
    """validate() holds the box RGMIN..ZGMAX against the plasma only when
    the solver reads that box (an analytic solve, every MODELG but the
    file formats, with MDLEQF >= 10), and flags only what fails or cuts
    the plasma there.

    The solver reads the box in one place, EQAXIS (eq/eqsub.f90): with
    MDLEQF < 10 the window the axis must lie in, and the bound of the
    outer-edge search, is RR +/- RB, +/- RKAP*RB (the same box EQTORZ
    tabulates psi on, eq/eqcalc.f90); with MDLEQF >= 10 it is RGMIN,
    RGMAX, ZGMIN, ZGMAX. The axis starts at (RR, 0), and the outer edge
    at Z=0 is RR+RA, so the run fails when RR or Z=0 is outside the box
    and is cut at RGMAX when RGMAX < RR+RA; any other part of the plasma
    may lie outside the box. EQCALQP overwrites the four with the traced
    plasma extent after the solve for any MDLEQF, so below 10 they are
    outputs only. A test pairs validate() with a real run, so a
    diagnostic is tied to what the solver does with the same input,
    except at the exact bounds (RGMIN=RR, ZGMIN=0, ZGMAX=0: the run turns
    on rounding), for the message texts, and for MDLEQF=9, whose run
    aborts.
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

    def test_large_device_with_mdleqf_10_flags_rr_and_run_fails(self) -> None:
        """(b) MDLEQF=10 makes the default box the axis window: RR=6.2 is
        outside it, the same input gets that diagnostic, and the run fails
        (EQAXIS: axis out of plasma, ierr=103). The Z range [-2, 2] holds
        Z=0, so the plasma's half-height 3.4 beyond it is no finding."""
        diags, err, state = self._validate_then_run(MDLEQF=10.0, **LARGE_DEVICE)
        extent = self._extent(diags)
        self.assertEqual([d.param for d in extent], ["RR"], str(diags))
        self.assertIn("RR=6.200 outside RGMIN..RGMAX [1.500, 4.500]", extent[0].message)
        self.assertIn("magnetic axis starts at RR", extent[0].message)
        self.assertIn("MDLEQF >= 10", extent[0].message)
        self.assertIsNotNone(err, "run(0) should fail with the default box")
        self.assertIn("ierr=103", str(err))
        self.assertIsNone(state)

    def test_large_device_with_mdleqf_11_is_gated_like_10(self) -> None:
        """The gate is `>= 10`, not `== 10`."""
        diags, err, _ = self._validate_then_run(MDLEQF=11.0, **LARGE_DEVICE)
        self.assertEqual([d.param for d in self._extent(diags)], ["RR"])
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
        """RR=1e11 gives an RR message of exactly 127 characters, the C
        field's, which prints in full. RR=1e12 gives one of 128, which
        the field would cut: it takes the fallback text. Both end with
        the closing parenthesis."""
        messages = {}
        for rr in (1.0e11, 1.0e12):
            with Eq() as eq:
                eq.set_params(MODELG=2.0, MDLEQF=10.0, RR=rr, RA=1.0)
                diags = eq.validate()
            messages[rr] = [d.message for d in diags if d.param == "RR"]
        self.assertEqual([len(m) for m in messages.values()], [1, 1], str(messages))
        self.assertEqual(len(messages[1.0e11][0]), 127, messages[1.0e11][0])
        self.assertTrue(messages[1.0e11][0].startswith("RR=100000000000.000 outside"),
                        messages[1.0e11][0])
        self.assertTrue(messages[1.0e11][0].endswith("(MDLEQF >= 10)"), messages[1.0e11][0])
        self.assertTrue(messages[1.0e12][0].startswith("RR outside RGMIN..RGMAX"),
                        messages[1.0e12][0])
        self.assertTrue(messages[1.0e12][0].endswith("(MDLEQF >= 10; values unprintable)"),
                        messages[1.0e12][0])

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

    # --- what the box is held to: the defaults (RR=3, RA=1, RKAP=1) with
    # MDLEQF=10, against the default box [1.5, 4.5] x [-2, 2] -------------

    def _assert_runs_as(self, state, ref, rel=0.0) -> None:
        """Every scalar of ``state`` as in ``ref``, to ``rel`` (0: bit for
        bit), but zaxis, which lies within rounding of 0 (1e-12 to 1e-9
        either side) and is held to 1e-8."""
        self.assertIsNotNone(state)
        for key, value in ref.scalars.items():
            if key == "zaxis":
                self.assertLessEqual(abs(state.scalars[key]), 1.0e-8, f"zaxis: {state.scalars[key]!r}")
                continue
            self.assertLessEqual(abs(state.scalars[key] - value), rel * abs(value),
                                 f"{key}: {state.scalars[key]!r} against {value!r}")

    def _reference(self, **params):
        diags, err, state = self._validate_then_run(MODELG=2.0, MDLEQF=10.0, **params)
        self.assertEqual(diags, [])
        self.assertIsNone(err)
        return state

    def _assert_flagged_and_fails(self, param, **params):
        diags, err, _ = self._validate_then_run(**params)
        extent = self._extent(diags)
        self.assertEqual([d.param for d in extent], [param], str(diags))
        self.assertIsNotNone(err, "run(0) should fail")
        self.assertIn("ierr=103", str(err))
        return extent[0].message

    def test_a_z_range_short_of_the_plasma_is_clean_and_runs_as_the_default_box(self) -> None:
        """ZGMAX=0.01 leaves the upper half of the plasma (up to Z=1.0)
        out of the box: no finding, and the run is the default box's."""
        ref = self._reference()
        diags, err, state = self._validate_then_run(MODELG=2.0, MDLEQF=10.0, ZGMAX=0.01)
        self.assertEqual(diags, [])
        self.assertIsNone(err)
        self._assert_runs_as(state, ref)

    def test_a_z_range_short_of_a_taller_plasma_is_clean_and_runs_as_the_default_box(self) -> None:
        """RKAP=1.8 (the plasma up to Z=1.8) with ZGMAX=0.3."""
        ref = self._reference(RKAP=1.8)
        diags, err, state = self._validate_then_run(
            MODELG=2.0, MDLEQF=10.0, RKAP=1.8, ZGMAX=0.3)
        self.assertEqual(diags, [])
        self.assertIsNone(err)
        self._assert_runs_as(state, ref)

    def test_rgmin_just_below_rr_is_clean_and_runs_as_the_default_box(self) -> None:
        """RGMIN=2.999 leaves the inner half of the plasma (from R=2.0) out
        of the box: no finding, and the run is the default box's."""
        ref = self._reference()
        diags, err, state = self._validate_then_run(MODELG=2.0, MDLEQF=10.0, RGMIN=2.999)
        self.assertEqual(diags, [])
        self.assertIsNone(err)
        self._assert_runs_as(state, ref)

    def test_rgmin_at_rr_is_clean(self) -> None:
        """RGMIN=RR exactly holds the axis's start; whether the run then
        keeps it in the box turns on rounding (it runs on macOS arm64 at
        -O0), so only validate()'s verdict is tested."""
        with Eq() as eq:
            eq.set_params(MODELG=2.0, MDLEQF=10.0, RGMIN=3.0)
            self.assertEqual(eq.validate(), [])

    def test_rgmin_just_above_rr_is_flagged_and_the_run_fails(self) -> None:
        """The axis starts at RR=3.0: RGMIN=3.001 fails, though the axis
        ends at RAXIS=3.070, inside the box."""
        message = self._assert_flagged_and_fails("RR", MODELG=2.0, MDLEQF=10.0, RGMIN=3.001)
        self.assertIn("RR=3.000 outside RGMIN..RGMAX [3.001, 4.500]", message)

    def test_rgmax_at_the_outer_edge_is_clean_and_runs_as_the_default_box(self) -> None:
        """RGMAX=4.0=RR+RA: no finding; the run is the default box's within
        the outer-edge search's tolerance (1e-8; 3.9e-9 measured)."""
        ref = self._reference()
        diags, err, state = self._validate_then_run(MODELG=2.0, MDLEQF=10.0, RGMAX=4.0)
        self.assertEqual(diags, [])
        self.assertIsNone(err)
        self._assert_runs_as(state, ref, rel=1.0e-8)

    def test_rgmax_just_inside_the_outer_edge_is_flagged_and_cuts_the_plasma(self) -> None:
        """RGMAX=3.999: the run succeeds with the plasma cut at RGMAX (PVOL
        59.07 against 59.16)."""
        ref = self._reference()
        diags, err, state = self._validate_then_run(MODELG=2.0, MDLEQF=10.0, RGMAX=3.999)
        extent = self._extent(diags)
        self.assertEqual([d.param for d in extent], ["RR"], str(diags))
        self.assertIn("outer edge RR+RA=4.000 lies 1.000E-03 beyond RGMAX=3.999", extent[0].message)
        self.assertIn("cuts the plasma", extent[0].message)
        self.assertIsNone(err)
        self.assertLess(state.scalars["pvol"], ref.scalars["pvol"] * (1.0 - 1.0e-3))

    def _assert_flagged_only(self, param, **params):
        with Eq() as eq:
            eq.set_params(**params)
            extent = self._extent(eq.validate())
        self.assertEqual([d.param for d in extent], [param], str(extent))
        return extent[0].message

    def test_zgmin_at_zero_is_flagged(self) -> None:
        """The axis's Z starts at exactly 0 and ends 1e-12 to one side, so
        at ZGMIN=0 the run turns on rounding (it fails on macOS arm64 at
        -O0): the box must hold Z=0 strictly, and only validate()'s verdict
        is tested."""
        message = self._assert_flagged_only("ZGMIN", MODELG=2.0, MDLEQF=10.0, ZGMIN=0.0)
        self.assertIn("leaves out Z=0", message)

    def test_zgmax_at_zero_is_flagged(self) -> None:
        message = self._assert_flagged_only("ZGMAX", MODELG=2.0, MDLEQF=10.0, ZGMAX=0.0)
        self.assertIn("leaves out Z=0", message)

    def test_a_z_range_below_zero_is_flagged_and_the_run_fails(self) -> None:
        message = self._assert_flagged_and_fails("ZGMAX", MODELG=2.0, MDLEQF=10.0, ZGMAX=-0.5)
        self.assertIn("ZGMIN..ZGMAX [-2.000, -.500] leaves out Z=0", message)

    def test_a_z_range_above_zero_is_flagged_and_the_run_fails(self) -> None:
        message = self._assert_flagged_and_fails("ZGMIN", MODELG=2.0, MDLEQF=10.0, ZGMIN=0.5)
        self.assertIn("ZGMIN..ZGMAX [.500, 2.000] leaves out Z=0", message)

    def test_every_modelg_but_a_file_format_gives_the_equilibrium_of_modelg_2(self) -> None:
        """EQCALC does not read MODELG: run(0) is one analytic solve for
        every MODELG that run(1) cannot load (the gate's premise)."""
        ref = self._reference()
        for modelg in (0.0, 1.0, 4.0, 6.0, 7.0, 26.0, -1.0):
            diags, err, state = self._validate_then_run(MODELG=modelg, MDLEQF=10.0)
            self.assertEqual(diags, [], f"MODELG={modelg}")
            self.assertIsNone(err, f"MODELG={modelg}")
            self._assert_runs_as(state, ref)

    def test_modelg_0_is_checked_like_modelg_2(self) -> None:
        self._assert_flagged_and_fails("RR", MODELG=0.0, MDLEQF=10.0, RGMIN=3.5)

    def test_modelg_4_is_checked_like_modelg_2(self) -> None:
        """MODELG=4 (VMEC output geometry) is no file format run(1) reads."""
        self._assert_flagged_and_fails("RR", MODELG=4.0, MDLEQF=10.0, RGMIN=3.5)

    def test_modelg_1_is_checked_like_modelg_2(self) -> None:
        """RGMAX=3.5 cuts the plasma (PVOL 11.7 against 59.2)."""
        ref = self._reference()
        diags, err, state = self._validate_then_run(MODELG=1.0, MDLEQF=10.0, RGMAX=3.5)
        self.assertEqual([d.param for d in self._extent(diags)], ["RR"], str(diags))
        self.assertIsNone(err)
        self.assertLess(state.scalars["pvol"], 0.5 * ref.scalars["pvol"])


FIXTURE_TST2 = HERE.parent / "fixtures" / "eqdata.TST-2"


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)
class TestEqValidateWallGate(unittest.TestCase):
    """The wall check (RB < RA) is for the analytic solve, every MODELG but
    the file formats, where the solve and its grid use RB; a file load
    brings its own."""

    def test_an_analytic_solve_with_rb_below_ra_is_flagged_for_any_modelg_solved(self) -> None:
        """RB=0.8 with RA=1.0 runs, but to another equilibrium (PVOL 57.97
        against 59.16), for MODELG 0, 1, 4 and 26 as for 2."""
        _, _, ref = TestEqValidateBoxGate._validate_then_run(MODELG=2.0)
        for modelg in (0.0, 1.0, 4.0, 26.0):
            diags, err, state = TestEqValidateBoxGate._validate_then_run(MODELG=modelg, RB=0.8)
            self.assertEqual([(d.param, d.code) for d in diags],
                             [("RB", EqDiagCode.INCONSISTENT_PAIR)], f"MODELG={modelg}")
            self.assertIsNone(err, f"MODELG={modelg}")
            self.assertLess(state.scalars["pvol"], ref.scalars["pvol"] * (1.0 - 1.0e-2),
                            f"MODELG={modelg}")

    @staticmethod
    def _validate_then_load(**params):
        """(diagnostics, state) of a MODELG=3 load of the TST-2 fixture."""
        with Eq() as eq:
            eq.set_params(MODELG=3.0, **params)
            with _in_tempdir() as tmp:
                shutil.copy(FIXTURE_TST2, Path(tmp) / "eqdata.TST-2")
                eq.set_param_str("KNAMEQ", "eqdata.TST-2")
                diags = eq.validate()
                eq.run(1)
                return diags, eq.get_state()

    def test_no_file_format_gets_a_geometry_check(self) -> None:
        """The six file formats (3, 5, 8, 9, 25, and 15, whose load run(1)
        refuses) are taken to be loaded: a wall inside the plasma, a box
        without RR and a negative current are not reported for any of
        them (validate only: no file is read)."""
        for modelg in (3.0, 5.0, 8.0, 9.0, 15.0, 25.0):
            with Eq() as eq:
                eq.set_params(MODELG=modelg, RB=0.8, MDLEQF=10.0, RGMIN=3.5, RIP=-3.0)
                params = [d.param for d in eq.validate()]
            for name in ("RB", "RR", "RIP"):
                self.assertNotIn(name, params, f"MODELG={modelg}: {params}")

    def test_a_file_load_with_rb_below_ra_is_not_flagged_and_loads_the_same(self) -> None:
        """The file brings its own RA and RB: RA=2.0 > RB=1.2 before the
        load gives the equilibrium of RA=0.2."""
        diags, state = self._validate_then_load(RA=2.0, RB=1.2)
        self.assertEqual(diags, [], str(diags))
        _, ref = self._validate_then_load(RA=0.2, RB=1.2)
        for key, value in ref.scalars.items():
            self.assertEqual(state.scalars[key], value, key)


_PLATO = dict(MODELG=2.0, RR=0.7, RA=0.18, RKAP=1.9, RDLT=0.4, BB=0.3, RIP=0.04)


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)
class TestEqValidateGridReachesRZero(unittest.TestCase):
    """An analytic solve tabulates psi on RR -/+ RB (EQTORZ, eq/eqcalc.f90),
    whatever MDLEQF: with RB >= RR that grid reaches R <= 0, the run goes on,
    and its result depends on RB (tw#217: PLATO's QSURF 5.646 with the
    default RB 1.2, 6.471 with RB = 1.2 RA). validate() flags it on RB,
    INCONSISTENT_PAIR; a file load brings its own grid."""

    @staticmethod
    def _rb(diags):
        return [(d.param, d.code, d.message) for d in diags if d.param == "RB"]

    def test_the_default_wall_of_a_small_device_is_flagged_and_the_run_still_completes(self) -> None:
        diags, err, state = TestEqValidateBoxGate._validate_then_run(**_PLATO)
        self.assertEqual(self._rb(diags), [(
            "RB", EqDiagCode.INCONSISTENT_PAIR,
            "RR -/+ RB = [-0.500, 1.900] reaches R <= 0 (RB=1.200 >= RR=0.700): "
            "set RB below RR (e.g. RB = 1.2*RA)")])
        self.assertIsNone(err)                       # validate() changes no run
        self.assertAlmostEqual(state.scalars["qsurf"], 5.646440769840485, places=9)

    def test_a_wall_of_1_2_ra_is_clean(self) -> None:
        diags, err, _ = TestEqValidateBoxGate._validate_then_run(**_PLATO, RB=0.216)
        self.assertEqual(diags, [])
        self.assertIsNone(err)

    def test_a_wall_equal_to_rr_is_flagged(self) -> None:
        with Eq() as eq:
            eq.set_params(**_PLATO, RB=0.7)
            rb = self._rb(eq.validate())
        self.assertEqual([(p, c) for p, c, _ in rb], [("RB", EqDiagCode.INCONSISTENT_PAIR)])
        self.assertIn("[0.000, 1.400] reaches R <= 0", rb[0][2])

    def test_a_wall_just_inside_rr_is_clean(self) -> None:
        with Eq() as eq:
            eq.set_params(**_PLATO, RB=0.6999)
            self.assertEqual(eq.validate(), [])

    def test_with_mdleqf_10_the_grid_is_checked_too(self) -> None:
        with Eq() as eq:
            eq.set_params(**_PLATO, MDLEQF=10.0, RGMIN=0.4, RGMAX=1.0, ZGMIN=-0.5, ZGMAX=0.5)
            self.assertEqual([(p, c) for p, c, _ in self._rb(eq.validate())],
                             [("RB", EqDiagCode.INCONSISTENT_PAIR)])

    def test_no_file_format_is_checked(self) -> None:
        for modelg in (3.0, 5.0, 8.0, 9.0, 15.0, 25.0):
            with Eq() as eq:
                eq.set_params(**{**_PLATO, "MODELG": modelg})
                self.assertEqual(self._rb(eq.validate()), [], f"MODELG={modelg}")

    def test_an_unprintable_wall_falls_back_to_a_static_message(self) -> None:
        with Eq() as eq:
            eq.set_params(MODELG=2.0, RB=1.0e30)
            rb = self._rb(eq.validate())
        self.assertEqual([(p, c) for p, c, _ in rb], [("RB", EqDiagCode.INCONSISTENT_PAIR)])
        self.assertIn("reaches R <= 0", rb[0][2])
        self.assertIn("values unprintable", rb[0][2])


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


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)
class TestEqValidateFileMissing(unittest.TestCase):
    """FILE_MISSING covers the files every load format reads (task-web-client
    #191): KNAMEQ for MODELG 3, 5, 8, 9 and 25, blank or naming no file,
    KNAMEQ2 too for MODELG 8. MODELG 15, which reads the fixed file eqdb.dat
    instead of KNAMEQ, is refused by run(1) (task-web-client #203) and
    reported as OUT_OF_RANGE, with or without the file.
    The load fails on each of them (test_load_errors.py); validate() says so
    before the run. Each case runs in a scratch directory, the working
    directory a load opens its file from."""

    KNAMEQ_FORMATS = (3.0, 5.0, 8.0, 9.0, 25.0)

    @staticmethod
    def _file_missing(modelg, knameq=None, files=()):
        with Eq() as eq, _in_tempdir() as tmp:
            for name in files:
                Path(tmp, name).write_bytes(b"x")
            eq.set_param("MODELG", modelg)
            if knameq is not None:
                eq.set_param_str("KNAMEQ", knameq)
            return [(d.param, d.message) for d in eq.validate()
                    if d.code == EqDiagCode.FILE_MISSING]

    def test_a_blank_knameq_is_reported_for_every_format_that_reads_it(self) -> None:
        for modelg in self.KNAMEQ_FORMATS:
            self.assertEqual(
                self._file_missing(modelg, "", files=["eqdata2"]),
                [("KNAMEQ", f"MODELG={int(modelg)} loads the file KNAMEQ names, and KNAMEQ is blank")],
                f"MODELG={modelg}")

    def test_a_knameq_that_names_no_file_is_reported(self) -> None:
        for modelg in self.KNAMEQ_FORMATS:
            self.assertEqual(
                self._file_missing(modelg, "nofile.dat", files=["eqdata2"]),
                [("KNAMEQ", f"KNAMEQ='nofile.dat' not found: MODELG={int(modelg)} loads it")],
                f"MODELG={modelg}")

    def test_the_default_knameq_is_looked_up_too(self) -> None:
        # eq_init sets KNAMEQ='eqdata' (and KNAMEQ2='eqdata2'), which a fresh folder does not hold.
        self.assertEqual(self._file_missing(3.0),
                         [("KNAMEQ", "KNAMEQ='eqdata' not found: MODELG=3 loads it")])
        self.assertEqual(self._file_missing(8.0),
                         [("KNAMEQ", "KNAMEQ='eqdata' not found: MODELG=8 loads it"),
                          ("KNAMEQ2", "KNAMEQ2='eqdata2' not found: MODELG=8 loads it too")])

    def test_a_knameq_that_is_there_is_clean(self) -> None:
        # eqdata2 is KNAMEQ2's default, which MODELG 8 reads too.
        for modelg in self.KNAMEQ_FORMATS:
            self.assertEqual(
                self._file_missing(modelg, "eqdata.TST-2", files=["eqdata.TST-2", "eqdata2"]), [],
                f"MODELG={modelg}")

    def test_modelg_8_reads_knameq2_too(self) -> None:
        # EQJAEAR opens KNAMEQ, then KNAMEQ2 (default eqdata2); the other formats do not.
        self.assertEqual(self._file_missing(8.0, "eqdata.TST-2", files=["eqdata.TST-2"]),
                         [("KNAMEQ2", "KNAMEQ2='eqdata2' not found: MODELG=8 loads it too")])
        for modelg in (3.0, 5.0, 9.0, 25.0):
            self.assertEqual(self._file_missing(modelg, "eqdata.TST-2", files=["eqdata.TST-2"]), [],
                             f"MODELG={modelg}")

    def test_a_blank_knameq2_is_reported_for_modelg_8(self) -> None:
        with Eq() as eq, _in_tempdir() as tmp:
            Path(tmp, "eqdata.TST-2").write_bytes(b"x")
            eq.set_param("MODELG", 8.0)
            eq.set_param_str("KNAMEQ", "eqdata.TST-2")
            eq.set_param_str("KNAMEQ2", "")
            found = [(d.param, d.message) for d in eq.validate()
                     if d.code == EqDiagCode.FILE_MISSING]
        self.assertEqual(found, [("KNAMEQ2", "MODELG=8 loads the file KNAMEQ2 names too, and KNAMEQ2 is blank")])

    def test_the_longest_knameq_is_named_whole(self) -> None:
        name = "k" * 80   # KNAMEQ holds 80 characters
        self.assertEqual(self._file_missing(25.0, name),
                         [("KNAMEQ", f"KNAMEQ='{name}' not found: MODELG=25 loads it")])
        with Eq() as eq, _in_tempdir() as tmp:
            Path(tmp, "eqdata.TST-2").write_bytes(b"x")
            eq.set_param("MODELG", 8.0)
            eq.set_param_str("KNAMEQ", "eqdata.TST-2")
            eq.set_param_str("KNAMEQ2", name)
            found = [(d.param, d.message) for d in eq.validate()]
        self.assertEqual(found, [("KNAMEQ2", f"KNAMEQ2='{name}' not found: MODELG=8 loads it too")])

    def test_modelg_15_is_reported_whatever_the_files(self) -> None:
        # run(1) refuses MODELG 15: its reader passes equ_set_psi one of the three arrays it takes
        # (task-web-client #203). The one finding, OUT_OF_RANGE on MODELG, is the same with or
        # without eqdb.dat, with a blank KNAMEQ or one that is there.
        expected = [("MODELG", int(EqDiagCode.OUT_OF_RANGE),
                     "MODELG=15 cannot be loaded: its reader passes equ_set_psi one of its three"
                     " arrays; run(1) refuses it")]
        for knameq, files in (("", ()), ("", ("eqdb.dat",)),
                              ("eqdata.TST-2", ("eqdata.TST-2", "eqdb.dat"))):
            with Eq() as eq, _in_tempdir() as tmp:
                for name in files:
                    Path(tmp, name).write_bytes(b"x")
                eq.set_param("MODELG", 15.0)
                eq.set_param_str("KNAMEQ", knameq)
                found = [(d.param, int(d.code), d.message) for d in eq.validate()]
            self.assertEqual(found, expected, (knameq, files))

    def test_a_model_that_loads_no_file_does_not_look_for_one(self) -> None:
        for modelg in (0.0, 1.0, 2.0, 4.0, 7.0, 26.0):
            self.assertEqual(self._file_missing(modelg, ""), [], f"MODELG={modelg}")
            self.assertEqual(self._file_missing(modelg, "nofile.dat"), [], f"MODELG={modelg}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
