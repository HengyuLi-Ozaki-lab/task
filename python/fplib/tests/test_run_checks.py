"""``fp_run`` refuses, before any work, the counts it cannot run with.

Each of these was accepted when it was set and then stopped the host
process, never returned, or made a run whose results could not be read:

* ``NRMAX`` below 1 runs past an array bound in ``fp_mesh`` (an abort when
  the library is built with run-time checks); above ``FP_MAX_NRMAX`` the run
  is made and ``fp_get_state`` then refuses to return it (rc=3).
* ``NPMAX`` or ``NTHMAX`` below 2 runs past an array bound.
* ``LMAXFP`` below 0 makes no pass, and ``fp_loop`` then tests an error flag
  that no pass has set (on the build measured the process ends, ``XX
  mtx_abort``); at the largest integer the iteration's exit, ``N_IMPL = 1 +
  LMAXFP`` (``fp/fploop.f90``), overflows and a step never ends.
* ``NSAMAX`` above ``NSBMAX``, an evolved species number above ``NSBMAX`` or
  ``NSMAX``, and a background species number above ``NSMAX`` run past an
  array bound.

``fp_run`` now returns ``FP_ERR_INVALID`` for them (``fp_param_check``,
``fp/fp_param_registry.f90``), and the values next to each limit still run.

One test per case, no ``subTest``: under ``--forked`` a failing ``subTest``
is reported as passed. Each species case breaks one rule only, so that a
rule taken out is a test that fails.
"""
from __future__ import annotations

import math
import subprocess
import sys
import unittest
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
DEFAULT_SO = REPO / "fp" / "libfpapi.so"

if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from fplib import Fplib, FplibInvalidParamError  # noqa: E402
from fplib import _ffi  # noqa: E402

LARGEST_INTEGER = 2**31 - 1
DELT = 0.002  # not fp_init's 0.01, so that TIMEFP shows the steps were made
STEPS = 3

_NEEDS_THE_LIBRARY = unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`",
)

# The same run as _set() and fp.run(), for a case that may never return: a forked
# test that hangs inside a Fortran loop cannot be stopped (the suite's timeout ends
# the session and leaves the child running), so such a case gets a process of its
# own, which subprocess.run() kills when it does not end.
_CHILD = """
import os
import sys
sys.path.insert(0, sys.argv[1])
from fplib import Fplib, FplibInvalidParamError
with Fplib() as fp:
    fp.set_param("NPMAX", 10.0)
    fp.set_param("NTHMAX", 10.0)
    fp.set_param("DELT", float(sys.argv[2]))
    fp.set_param("LMAXFP", float(sys.argv[3]))
    try:
        fp.run(int(sys.argv[4]))
    except FplibInvalidParamError:
        print("VERDICT REFUSED", flush=True)
    else:
        state = fp.get_state()
        print("VERDICT RAN", repr(state.timefp), state.nrmax, state.nsamax, repr(state.RNT[0][0]), flush=True)
# The verdict is out: leave as a forked test does, without the interpreter's and the
# Fortran run-time's own exit paths, which are not what this case is about.
os._exit(0)
"""


def _set(fp, params):
    """A small momentum mesh and DELT, then PARAMS in their own order."""
    fp.set_param("NPMAX", 10.0)
    fp.set_param("NTHMAX", 10.0)
    fp.set_param("DELT", DELT)
    for name, value in params.items():
        fp.set_param(name, float(value))


def _in_a_process_of_its_own(lmaxfp):
    """(verdict line, everything the child wrote) of STEPS steps with LMAXFP."""
    done = subprocess.run(
        [sys.executable, "-c", _CHILD, str(PYTHON_ROOT), repr(DELT), str(lmaxfp), str(STEPS)],
        capture_output=True, text=True, errors="replace", timeout=30,
    )
    assert done.returncode == 0, done.stdout[-400:] + done.stderr[-400:]
    verdicts = [line for line in done.stdout.splitlines() if line.startswith("VERDICT ")]
    assert len(verdicts) == 1, done.stdout[-400:]
    return verdicts[0], done.stdout


class _RunChecks(unittest.TestCase):
    def assert_refused(self, params, ntmax=1):
        with Fplib() as fp:
            _set(fp, params)
            with self.assertRaises(FplibInvalidParamError):
                fp.run(ntmax)

    def assert_runs(self, params, nrmax=1, nsamax=1):
        """The run is made: TIMEFP is STEPS steps on, the state has the surfaces
        and the evolved species asked for, and every density is finite and
        positive."""
        with Fplib() as fp:
            _set(fp, params)
            fp.run(STEPS)
            state = fp.get_state()
        self.assertAlmostEqual(state.timefp, STEPS * DELT, places=12)
        self.assertEqual((state.nrmax, state.nsamax), (nrmax, nsamax))
        self.assertEqual([len(densities) for densities in state.RNT], [nrmax] * nsamax)
        for densities in state.RNT:
            for density in densities:
                self.assertTrue(math.isfinite(density) and density > 0.0, density)


@_NEEDS_THE_LIBRARY
class TestRunRefusesTheMeshItCannotRun(_RunChecks):
    def test_more_surfaces_than_the_state_holds(self):
        self.assert_refused({"NRMAX": _ffi.FP_MAX_NRMAX + 1, "RMIN": 0.05, "RMAX": 0.95})

    def test_more_surfaces_than_the_state_holds_without_a_step(self):
        self.assert_refused({"NRMAX": _ffi.FP_MAX_NRMAX + 1, "RMIN": 0.05, "RMAX": 0.95}, ntmax=0)

    def test_no_surface(self):
        self.assert_refused({"NRMAX": 0})

    def test_no_surface_without_a_step(self):
        self.assert_refused({"NRMAX": 0}, ntmax=0)

    def test_a_negative_number_of_surfaces(self):
        self.assert_refused({"NRMAX": -1})

    def test_one_momentum_cell(self):
        self.assert_refused({"NPMAX": 1})

    def test_no_momentum_cell(self):
        self.assert_refused({"NPMAX": 0})

    def test_one_pitch_cell(self):
        self.assert_refused({"NTHMAX": 1})

    def test_no_pitch_cell(self):
        self.assert_refused({"NTHMAX": 0})

    def test_as_many_surfaces_as_the_state_holds_run_and_are_returned(self):
        self.assert_runs({"NRMAX": _ffi.FP_MAX_NRMAX, "RMIN": 0.05, "RMAX": 0.95}, nrmax=_ffi.FP_MAX_NRMAX)

    def test_two_momentum_cells_run(self):
        # Too coarse for a result (the density it returns is wrong): the check is about
        # what the solver cannot run, so only the time reached is asserted.
        with Fplib() as fp:
            _set(fp, {"NPMAX": 2})
            fp.run(STEPS)
            state = fp.get_state()
        self.assertEqual(state.npmax, 2)
        self.assertAlmostEqual(state.timefp, STEPS * DELT, places=12)

    def test_two_pitch_cells_run(self):
        with Fplib() as fp:
            _set(fp, {"NTHMAX": 2})
            fp.run(STEPS)
            state = fp.get_state()
        self.assertEqual(state.nthmax, 2)
        self.assertAlmostEqual(state.timefp, STEPS * DELT, places=12)


@_NEEDS_THE_LIBRARY
class TestRunRefusesThePassLimitItCannotRun(_RunChecks):
    def test_a_negative_pass_limit(self):
        self.assert_refused({"LMAXFP": -1})

    def test_the_largest_integer(self):
        # Without the check fp_run never returns.
        verdict, out = _in_a_process_of_its_own(LARGEST_INTEGER)
        self.assertEqual(verdict, "VERDICT REFUSED")
        self.assertIn(f"XX fp_run: LMAXFP = {LARGEST_INTEGER} is outside 0 to {LARGEST_INTEGER - 1}", out)

    def test_the_integer_below_the_largest(self):
        # It ends because the iteration converges after a pass or two, as with any
        # limit; a build where it did not would never return, hence the process.
        verdict, _ = _in_a_process_of_its_own(LARGEST_INTEGER - 1)
        self.assertEqual(verdict.split()[:2], ["VERDICT", "RAN"])
        timefp, nrmax, nsamax, density = verdict.split()[2:]
        self.assertAlmostEqual(float(timefp), STEPS * DELT, places=12)
        self.assertEqual((int(nrmax), int(nsamax)), (1, 1))
        self.assertTrue(math.isfinite(float(density)) and float(density) > 0.0, density)

    def test_one_pass(self):
        self.assert_runs({"LMAXFP": 0})


@_NEEDS_THE_LIBRARY
class TestRunRefusesTheSpeciesItCannotRun(_RunChecks):
    def test_more_evolved_than_background_species(self):
        # Both evolved slots hold species 1, so only NSAMAX <= NSBMAX is broken.
        self.assert_refused({"NSAMAX": 2, "NSBMAX": 1, "NS_NSA[2]": 1})

    def test_an_evolved_species_number_above_nsbmax(self):
        # Species 3 has profiles (NSMAX = 3); the background array has two slots.
        self.assert_refused({"NSMAX": 3, "NSBMAX": 2, "NS_NSA[1]": 3})

    def test_an_evolved_species_number_above_nsmax(self):
        # Three background slots, all of species that exist; species 3 does not.
        self.assert_refused({"NSMAX": 2, "NSBMAX": 3, "NS_NSB[3]": 1, "NS_NSA[1]": 3})

    def test_a_background_species_number_above_nsmax(self):
        self.assert_refused({"NSMAX": 2, "NSBMAX": 2, "NS_NSB[2]": 3})

    def test_a_background_slot_whose_own_number_is_above_nsmax(self):
        # fp_init numbers the slots 1, 2, 3, ...: the third is species 3, within NSBMAX and beyond NSMAX.
        self.assert_refused({"NSMAX": 2, "NSBMAX": 3})

    def test_a_negative_evolved_species_number(self):
        self.assert_refused({"NS_NSA[1]": -1})

    def test_a_negative_background_species_number(self):
        self.assert_refused({"NSMAX": 2, "NSBMAX": 2, "NS_NSB[2]": -1})

    def test_a_zero_in_the_evolved_map_is_refused_as_the_slots_own_number(self):
        # Slot 2 would become species 2, which has no profiles (NSMAX = 1); as species 1 it runs.
        self.assert_refused({"NSMAX": 1, "NSAMAX": 2, "NSBMAX": 2, "NS_NSB[2]": 1, "NS_NSA[2]": 0})

    def test_a_zero_in_the_background_map_is_refused_as_the_slots_own_number(self):
        # Slot 3 would become species 3, beyond NSMAX; as species 1 it runs (below).
        self.assert_refused({"NSMAX": 2, "NSBMAX": 3, "NS_NSB[3]": 0})

    def test_two_evolved_species_among_two_background_species_run(self):
        self.assert_runs({"NSMAX": 2, "NSAMAX": 2, "NSBMAX": 2}, nsamax=2)

    def test_the_second_species_evolved_alone_runs(self):
        # NS_NSA(1) = 2 needs NSBMAX >= 2; species 2 is then background slot 2.
        self.assert_runs({"NSMAX": 2, "NSBMAX": 2, "NS_NSA[1]": 2})

    def test_more_background_slots_than_species_run_when_every_slot_names_one(self):
        # NSBMAX above NSMAX is not refused in itself: the slots' species numbers are what is read.
        self.assert_runs({"NSMAX": 2, "NSBMAX": 3, "NS_NSB[3]": 1})

    def test_a_zero_in_the_maps_runs_as_the_slots_own_number(self):
        self.assert_runs({"NSMAX": 2, "NSAMAX": 2, "NSBMAX": 2, "NS_NSA[2]": 0, "NS_NSB[2]": 0}, nsamax=2)

    def test_the_same_species_in_two_evolved_slots_runs(self):
        # The neighbour of the refused zero above: slot 2 as species 1, which exists.
        self.assert_runs({"NSMAX": 1, "NSAMAX": 2, "NSBMAX": 2, "NS_NSB[2]": 1, "NS_NSA[2]": 1}, nsamax=2)

    def test_an_evolved_species_that_no_background_slot_names_still_runs(self):
        # Not refused: fp_set_nsa_nsb reports it ("XX NS_NSA has no correponding NS_NSB")
        # and the run is made without that species' collisions with its own kind.
        self.assert_runs({"NSMAX": 2, "NSBMAX": 1, "NS_NSB[1]": 2})


@_NEEDS_THE_LIBRARY
class TestARefusalLeavesTheLibraryUsable(unittest.TestCase):
    def test_a_corrected_count_runs_on_the_same_handle(self):
        with Fplib() as fp:
            _set(fp, {"NRMAX": 0})
            with self.assertRaises(FplibInvalidParamError):
                fp.run(STEPS)
            fp.set_param("NRMAX", 1.0)
            fp.run(STEPS)
            state = fp.get_state()
        self.assertEqual(state.nrmax, 1)
        self.assertAlmostEqual(state.timefp, STEPS * DELT, places=12)
        self.assertTrue(math.isfinite(state.RNT[0][0]) and state.RNT[0][0] > 0.0)


@pytest.mark.skipif(not DEFAULT_SO.exists(), reason=f"libfpapi.so not built at {DEFAULT_SO}")
def test_a_refusal_names_every_count_it_refuses(capfd):
    """One line per violation on the library's standard output, in TASK's own
    'XX' form, so that a caller's log says which counts were refused."""
    with Fplib() as fp:
        _set(fp, {"NRMAX": 0, "NPMAX": 1, "NTHMAX": 1, "LMAXFP": -1,
                  "NSAMAX": 2, "NSBMAX": 1, "NS_NSA[1]": -1, "NS_NSB[1]": -1})
        with pytest.raises(FplibInvalidParamError):
            fp.run(1)
    refusals = [line for line in capfd.readouterr().out.splitlines() if line.startswith("XX fp_run:")]
    assert refusals == [
        f"XX fp_run: NRMAX = 0 is outside 1 to {_ffi.FP_MAX_NRMAX}",
        "XX fp_run: NPMAX = 1 is below 2",
        "XX fp_run: NTHMAX = 1 is below 2",
        f"XX fp_run: LMAXFP = -1 is outside 0 to {LARGEST_INTEGER - 1}",
        "XX fp_run: NSAMAX = 2 is above NSBMAX = 1",
        "XX fp_run: NS_NSA(1) = -1 is outside 1 to MIN(NSMAX, NSBMAX) = 1",
        "XX fp_run: NS_NSA(2) = 2 is outside 1 to MIN(NSMAX, NSBMAX) = 1",
        "XX fp_run: NS_NSB(1) = -1 is outside 1 to NSMAX = 2",
    ]


@pytest.mark.skipif(not DEFAULT_SO.exists(), reason=f"libfpapi.so not built at {DEFAULT_SO}")
def test_a_refusal_names_the_surfaces_the_state_holds(capfd):
    with Fplib() as fp:
        _set(fp, {"NRMAX": _ffi.FP_MAX_NRMAX + 1})
        with pytest.raises(FplibInvalidParamError):
            fp.run(1)
    out = capfd.readouterr().out
    assert f"XX fp_run: NRMAX = {_ffi.FP_MAX_NRMAX + 1} is outside 1 to {_ffi.FP_MAX_NRMAX}" in out.splitlines()


if __name__ == "__main__":
    unittest.main()
