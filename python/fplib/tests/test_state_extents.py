"""``fp_get_state`` returns a snapshot bounded by what is allocated (#245).

The FPCOMM profile arrays (``RNT``, ``RWT``, ... in ``fp/fpcomm.f90``) keep
the extents of the last ``fp_prep``; ``NRMAX`` / ``NSAMAX`` are the current
namelist values. ``fp_set_param`` on either count clears ``g_prepared``
without reallocating, so until the next ``fp_run`` the two disagree, and
``fp_get_state`` used to copy ``nsa = 1..NSAMAX``, ``nr = 1..NRMAX`` out of
arrays that are smaller than that (a read past the allocation: an abort
under ``-fcheck=all``, garbage in the padding otherwise).

``fp_get_state`` now copies, along each axis, the lesser of the current
count and the allocated extent, and reports the copied extents in
``nrmax`` / ``nsamax``, so the ``[nsamax][nrmax]`` slice the caller gets is
exactly the data that exists: a lowered count truncates the snapshot at
once, a raised count stays capped at the old allocation until the next run.
Before the first run no array is allocated: ``nrmax`` / ``nsamax`` are the
namelist values and the profiles are zero, as before.

The assertions are on the reported extents and the copied values, so they
hold with or without run-time bounds checking in the library build. One
test per case, no ``subTest``.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "fp" / "libfpapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from fplib import Fplib, FplibCalcFailedError, FpState  # noqa: E402
from fplib import _ffi  # noqa: E402

_NEEDS_THE_LIBRARY = unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`",
)

# Small momentum grid so one step is quick; DELT so TIMEFP shows the step ran.
NPMAX = 10
NTHMAX = 10
DELT = 0.002

PROFILES = ("RNT", "RWT", "RTT", "RJT", "RPCT", "RPWT")


def _run_once(fp: Fplib, **counts: float) -> None:
    fp.set_param("NPMAX", float(NPMAX))
    fp.set_param("NTHMAX", float(NTHMAX))
    fp.set_param("DELT", DELT)
    for name, value in counts.items():
        fp.set_param(name, float(value))
    fp.run(1)


def _profiles(state: FpState) -> dict:
    return {name: getattr(state, name) for name in PROFILES}


@_NEEDS_THE_LIBRARY
class TestGetStateExtents(unittest.TestCase):
    """Change a count after a run, read the state before the next run."""

    def assertSameProfiles(self, after: FpState, before: FpState) -> None:
        for name in PROFILES:
            self.assertEqual(getattr(after, name), getattr(before, name), name)

    def test_nsamax_raised_without_run_reports_allocated_extent(self):
        with Fplib() as fp:
            _run_once(fp)
            before = fp.get_state()
            self.assertGreater(before.timefp, 0.0)
            fp.set_param("NSAMAX", float(before.nsamax + 1))
            after = fp.get_state()
        self.assertEqual(after.nsamax, before.nsamax)
        self.assertEqual(after.nrmax, before.nrmax)
        for name, rows in _profiles(after).items():
            self.assertEqual(len(rows), after.nsamax, name)
        self.assertSameProfiles(after, before)

    def test_nrmax_raised_without_run_reports_allocated_extent(self):
        with Fplib() as fp:
            _run_once(fp)
            before = fp.get_state()
            fp.set_param("NRMAX", float(before.nrmax + 2))
            after = fp.get_state()
        self.assertEqual(after.nrmax, before.nrmax)
        self.assertEqual(after.nsamax, before.nsamax)
        for name, rows in _profiles(after).items():
            self.assertEqual(len(rows[0]), after.nrmax, name)
        self.assertSameProfiles(after, before)

    def test_nrmax_lowered_without_run_reports_lowered_count(self):
        # Lowering never read past the arrays; the snapshot is the leading
        # slice of the data that exists.
        with Fplib() as fp:
            _run_once(fp, NRMAX=3)
            before = fp.get_state()
            self.assertEqual(before.nrmax, 3)
            fp.set_param("NRMAX", 2.0)
            after = fp.get_state()
        self.assertEqual(after.nrmax, 2)
        for name, rows in _profiles(after).items():
            self.assertEqual(rows[0], _profiles(before)[name][0][:2], name)

    def test_nsamax_lowered_without_run_reports_lowered_count(self):
        # Two evolved species need two background slots and two species
        # with profiles (fp_param_check, fp/fp_param_registry.f90).
        with Fplib() as fp:
            _run_once(fp, NSMAX=2, NSAMAX=2, NSBMAX=2)
            before = fp.get_state()
            self.assertEqual(before.nsamax, 2)
            fp.set_param("NSAMAX", 1.0)
            after = fp.get_state()
        self.assertEqual(after.nsamax, 1)
        for name, rows in _profiles(after).items():
            self.assertEqual(rows, _profiles(before)[name][:1], name)

    def test_nrmax_raised_then_run_reports_new_extent(self):
        # The bound must follow a reallocation: after the next run the
        # arrays have the new extent and the state reports it.
        with Fplib() as fp:
            _run_once(fp)
            before = fp.get_state()
            fp.set_param("NRMAX", float(before.nrmax + 2))
            fp.run(1)
            after = fp.get_state()
        self.assertEqual(after.nrmax, before.nrmax + 2)
        for name, rows in _profiles(after).items():
            self.assertEqual(len(rows[0]), after.nrmax, name)
        self.assertGreater(after.timefp, 0.0)

    def test_nrmax_above_cap_without_run_is_still_refused(self):
        # The static fp_state_t cannot hold the grid: rc=3, as before.
        with Fplib() as fp:
            _run_once(fp)
            fp.set_param("NRMAX", float(_ffi.FP_MAX_NRMAX + 1))
            with self.assertRaises(FplibCalcFailedError):
                fp.get_state()

    def test_run_zero_steps_reports_allocated_initial_sample(self):
        # fp_run(0) runs fp_prep only: arrays allocated, the initial
        # profile saved as sample 1, no time advanced.
        with Fplib() as fp:
            fp.set_param("NPMAX", float(NPMAX))
            fp.set_param("NTHMAX", float(NTHMAX))
            fp.run(0)
            state = fp.get_state()
        self.assertEqual(state.timefp, 0.0)
        self.assertEqual(state.ntg2, 1)
        self.assertEqual(len(state.RNT), state.nsamax)
        self.assertEqual(len(state.RNT[0]), state.nrmax)
        self.assertGreater(state.RNT[0][0], 0.0)

    def test_second_handle_before_its_first_run_sees_truncated_old_data(self):
        # The arrays are per process: fp_finalize keeps them and fp_init
        # resets the counts to 1, so a second handle that reads before its
        # own first run gets the previous handle's data as a 1 x 1 slice.
        with Fplib() as fp:
            _run_once(fp, NRMAX=3)
            before = fp.get_state()
        with Fplib() as fp2:
            state = fp2.get_state()
        self.assertEqual((state.nrmax, state.nsamax), (1, 1))
        for name, rows in _profiles(state).items():
            self.assertEqual(rows, [[_profiles(before)[name][0][0]]], name)

    def test_before_first_run_reports_namelist_counts_and_zeros(self):
        # Nothing is allocated yet: the counts are the namelist values and
        # every profile value is zero (unchanged behaviour).
        with Fplib() as fp:
            fp.set_param("NRMAX", 3.0)
            state = fp.get_state()
        self.assertEqual(state.nrmax, 3)
        self.assertEqual(state.timefp, 0.0)
        for name, rows in _profiles(state).items():
            self.assertEqual(len(rows[0]), 3, name)
            self.assertTrue(all(v == 0.0 for row in rows for v in row), name)


if __name__ == "__main__":
    unittest.main()
