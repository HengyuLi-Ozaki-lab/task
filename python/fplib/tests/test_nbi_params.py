"""The NBI source and MODELA through the registry, and the run rules (task-web-client #232).

Eight names are set through fp_set_param: MODELA, NBEAMMAX, NSSPB[i], SPBTOT[i],
SPBENG[i], SPBANG[i], SPBR0[i], SPBRW[i] (i = 1 .. NBEAMM = 20). SPBPANG is not
registered: no source under fp/ reads it.

fp_param_check refuses, before fp_prep, MODELA other than 0 or 1, NBEAMMAX outside
0 .. 20 (fp_init gives it no value), and, with MODEL_NBI = 1, SPBRW <= 0 on any beam
up to NBEAMMAX (a 0/0 source even without SPBTOT), and a beam with a source
(SPBTOT /= 0) that NBI_SOURCE_A0 would leave without a deposit: beyond NBEAMMAX,
on no kinetic species, SPBANG outside 0 <= x < 180, SPBENG < 0. Each rule writes
one "XX fp_run:" line to unit 6. Not checked (they need fp_prep's mesh): a beam
beyond PMAX, and a source too narrow to reach any radial point.

Every case runs in a child process: without its rule, a case can run past an array
bound (NBEAMMAX = 21), which ends a forked test without a report. One test per
case, no subTest.
"""
from __future__ import annotations

import json
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

DELT = 0.002
STEPS = 2

# Deuterium (namelist species 2) is kinetic species 1, at 3 keV, on a momentum mesh
# that holds an 80 keV beam: p = sqrt(2E/T) = 7.3 is beyond the default PMAX of 7.
D_RUN = {
    "NSMAX": 2, "NSAMAX": 1, "NSBMAX": 2, "NS_NSA[1]": 2,
    "PTPR[1]": 3.0, "PTPP[1]": 3.0, "PTPR[2]": 3.0, "PTPP[2]": 3.0,
    "PMAX[2]": 10.0, "NPMAX": 20, "NTHMAX": 10, "DELT": DELT,
}
BEAM = {
    # SPBTOT is in 1e20 particles/s; 1e19 is a source of 1e39 /s, large for a clear signal (f is linear).
    "MODEL_NBI": 1, "NBEAMMAX": 1, "NSSPB[1]": 2, "SPBTOT[1]": 1.0e19,
    "SPBENG[1]": 8.0e4, "SPBANG[1]": 30.0, "SPBR0[1]": 0.0, "SPBRW[1]": 0.5,
}

_NEEDS_THE_LIBRARY = unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`",
)

_CHILD = r"""
import json
import math
import os
import sys
sys.path.insert(0, sys.argv[1])
from fplib import Fplib, FplibInvalidParamError
params = json.loads(sys.argv[2])
with Fplib() as fp:
    for name, value in params.items():
        fp.set_param(name, float(value))
    try:
        fp.run(int(sys.argv[3]))
    except FplibInvalidParamError:
        print("VERDICT REFUSED", flush=True)
    else:
        st = fp.get_state()
        finite = all(math.isfinite(v) for row in st.RNT for v in row)
        print("VERDICT RAN", repr(st.timefp), "FINITE" if finite else "NONFINITE", flush=True)
os._exit(0)
"""


def _child(params, steps=STEPS):
    """(verdict line, everything the child wrote) of a run with PARAMS, in order."""
    done = subprocess.run(
        [sys.executable, "-c", _CHILD, str(PYTHON_ROOT), json.dumps(params), str(steps)],
        capture_output=True, text=True, errors="replace", timeout=60,
    )
    verdicts = [line for line in done.stdout.splitlines() if line.startswith("VERDICT ")]
    assert done.returncode == 0 and len(verdicts) == 1, done.stdout[-600:] + done.stderr[-600:]
    return verdicts[0], done.stdout


@_NEEDS_THE_LIBRARY
class TestTheNamesAreSet(unittest.TestCase):
    def test_each_name_is_set(self):
        with Fplib() as fp:
            for name, value in [("MODELA", 1), ("NBEAMMAX", 20), ("NSSPB[20]", 2),
                                ("SPBTOT[1]", 1.0e19), ("SPBENG[1]", 8.0e4), ("SPBANG[1]", 30.0),
                                ("SPBR0[1]", 0.3), ("SPBRW[1]", 0.4)]:
                fp.set_param(name, float(value))
            # NBEAMMAX survives finalize/init (fp_init gives it no value): leave
            # the process as it found it, for the tests that follow in it. MODELA
            # goes back to fp_init's 0 too.
            fp.set_param("NBEAMMAX", 0.0)
            fp.set_param("MODELA", 0.0)

    def test_an_index_beyond_nbeamm_is_refused(self):
        with Fplib() as fp:
            with self.assertRaises(FplibInvalidParamError):
                fp.set_param("SPBENG[21]", 8.0e4)

    def test_index_0_is_refused(self):
        with Fplib() as fp:
            with self.assertRaises(FplibInvalidParamError):
                fp.set_param("NSSPB[0]", 2.0)

    def test_spbpang_is_not_registered(self):
        with Fplib() as fp:
            with self.assertRaises(FplibInvalidParamError):
                fp.set_param("SPBPANG[1]", 10.0)


@_NEEDS_THE_LIBRARY
class TestRunRules(unittest.TestCase):
    def assert_refused(self, params, line):
        verdict, out = _child({**D_RUN, **BEAM, **params})
        self.assertEqual(verdict, "VERDICT REFUSED", out[-600:])
        self.assertIn(line, out)

    def assert_runs(self, params):
        verdict, out = _child({**D_RUN, **BEAM, **params})
        self.assertTrue(verdict.startswith("VERDICT RAN"), out[-600:])
        self.assertAlmostEqual(float(verdict.split()[2]), STEPS * DELT, places=12)
        self.assertEqual(verdict.split()[3], "FINITE", out[-600:])

    def test_the_beam_as_given_runs(self):
        self.assert_runs({})

    def test_modela_2_is_refused(self):
        self.assert_refused({"MODELA": 2}, "XX fp_run: MODELA = 2")

    def test_modela_minus_1_is_refused(self):
        self.assert_refused({"MODELA": -1}, "XX fp_run: MODELA = -1")

    def test_modela_1_runs(self):
        self.assert_runs({"MODELA": 1})

    def test_nbeammax_21_is_refused(self):
        self.assert_refused({"NBEAMMAX": 21}, "XX fp_run: NBEAMMAX = 21")

    def test_nbeammax_minus_1_is_refused(self):
        self.assert_refused({"NBEAMMAX": -1, "SPBTOT[1]": 0.0}, "XX fp_run: NBEAMMAX = -1")

    def test_nbeammax_20_runs(self):
        self.assert_runs({"NBEAMMAX": 20})

    def test_nbeammax_0_without_a_source_runs(self):
        self.assert_runs({"NBEAMMAX": 0, "SPBTOT[1]": 0.0})

    def test_a_source_beyond_nbeammax_is_refused(self):
        self.assert_refused({"SPBTOT[2]": 1.0e19}, "XX fp_run: SPBTOT(2) is set, but NBEAMMAX = 1")

    def test_a_source_beyond_nbeammax_runs_without_model_nbi(self):
        self.assert_runs({"MODEL_NBI": 0, "SPBTOT[2]": 1.0e19})

    def test_a_beam_on_a_species_that_is_not_kinetic_is_refused(self):
        self.assert_refused({"NSSPB[1]": 1}, "XX fp_run: NSSPB(1) = 1")

    def test_a_beam_on_a_species_beyond_nsmax_is_refused(self):
        self.assert_refused({"NSSPB[1]": 3}, "XX fp_run: NSSPB(1) = 3")

    def test_ns_nsa_0_is_read_as_the_slot_number_and_refused(self):
        # NS_NSA(1) = 0 is species 1 (electrons): the beam on species 2 has no kinetic species.
        self.assert_refused({"NS_NSA[1]": 0}, "XX fp_run: NSSPB(1) = 2")

    def test_ns_nsa_0_in_slot_2_is_species_2_and_runs(self):
        self.assert_runs({"NSAMAX": 2, "NS_NSA[1]": 1, "NS_NSA[2]": 0})

    def test_spbrw_0_is_refused(self):
        self.assert_refused({"SPBRW[1]": 0.0}, "XX fp_run: SPBRW(1)")

    def test_spbrw_0_05_runs(self):
        self.assert_runs({"SPBRW[1]": 0.05})

    def test_spbang_180_is_refused(self):
        self.assert_refused({"SPBANG[1]": 180.0}, "XX fp_run: SPBANG(1)")

    def test_spbang_minus_1_is_refused(self):
        self.assert_refused({"SPBANG[1]": -1.0}, "XX fp_run: SPBANG(1)")

    def test_spbang_0_runs(self):
        self.assert_runs({"SPBANG[1]": 0.0})

    def test_spbang_179_9_runs(self):
        self.assert_runs({"SPBANG[1]": 179.9})

    def test_spbeng_minus_1_is_refused(self):
        self.assert_refused({"SPBENG[1]": -1.0}, "XX fp_run: SPBENG(1)")

    def test_spbeng_0_runs(self):
        self.assert_runs({"SPBENG[1]": 0.0})

    def test_spbrw_0_on_a_beam_without_a_source_is_refused(self):
        # NBI_SOURCE_A0 takes beam 2 too (NBEAMMAX 2): SPBRW 0 makes 0 * 0 / 0.
        self.assert_refused({"NBEAMMAX": 2, "SPBRW[2]": 0.0}, "XX fp_run: SPBRW(2)")

    def test_spbrw_0_beyond_nbeammax_runs(self):
        self.assert_runs({"SPBRW[2]": 0.0})

    def test_the_same_beam_runs_once_ns_nsa_points_at_its_species(self):
        # The beam on species 1 (refused above with NS_NSA(1) = 2) runs once species 1 is kinetic.
        self.assert_runs({"NSSPB[1]": 1, "NS_NSA[1]": 1})

    def test_the_beam_rules_need_model_nbi_1(self):
        self.assert_runs({"MODEL_NBI": 0, "SPBRW[1]": 0.0, "SPBANG[1]": 180.0, "NSSPB[1]": 1})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
