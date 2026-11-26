"""The NBI source and MODELA through the registry, and the run rules (task-web-client #232).

Eight names are set through fp_set_param: MODELA, NBEAMMAX, NSSPB[i], SPBTOT[i],
SPBENG[i], SPBANG[i], SPBR0[i], SPBRW[i] (i = 1 .. NBEAMM = 20). SPBPANG is not
registered: no source under fp/ reads it.

fp_param_check refuses, before fp_prep, MODELA other than 0 or 1, NBEAMMAX outside
0 .. 20 (fp_init gives it no value), NAVMAX < 1 with MODELA = 1 or MODEL_WAVE /= 0
(both divide by it), and, with MODEL_NBI = 1, SPBRW <= 0 on any beam
up to NBEAMMAX (a 0/0 source even without SPBTOT), and a beam with a source
(SPBTOT /= 0) that NBI_SOURCE_A0 would leave without a deposit: beyond NBEAMMAX,
on no kinetic species, SPBANG outside 0 <= x < 180, SPBENG < 0, a beam whose
momentum is at or beyond its species' mesh edge (PMAX, or EMAX's; FP's own arithmetic)
or whose species' temperature is not above 0, and, with kinetic electrons and
NSSPB(1) /= 1, a beam whose electron source falls beyond the electron mesh edge, or whose
species' PZ differs from the PZ that FP's electron compensating source reads (an FP bug,
reported). Each rule writes one
"XX fp_run:" line to unit 6. Not checked (it needs fp_prep's mesh): a source too
narrow to reach any radial point.

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


def xx_lines(out):
    """The 'XX fp_run:' diagnostics in OUT, in order."""
    return [line for line in out.splitlines() if line.startswith("XX fp_run:")]


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
        # An 80 keV beam at 3 keV is p = 7.30, beyond the default electron PMAX of 7: PMAX[1] 10 holds it.
        self.assert_runs({"NSSPB[1]": 1, "NS_NSA[1]": 1, "PMAX[1]": 10.0})

    # --- a beam beyond the ion momentum mesh (task-web-client #232 follow-up) ---
    def test_a_beam_beyond_pmax_is_refused(self):
        # 80 keV at 3 keV: p = 7.30 > PMAX 7. No ion would be deposited.
        self.assert_refused({"PMAX[2]": 7.0}, "beyond its mesh edge")

    def test_a_beam_just_inside_pmax_runs(self):
        self.assert_runs({"PMAX[2]": 7.4})

    def test_a_lower_energy_beam_runs_with_pmax_7(self):
        # 70 keV: p = 6.83 < 7.
        self.assert_runs({"PMAX[2]": 7.0, "SPBENG[1]": 7.0e4})

    def test_emax_is_not_registered_so_pmax_is_the_mesh_edge(self):
        with Fplib() as fp:
            with self.assertRaises(FplibInvalidParamError):
                fp.set_param("EMAX[2]", 1.0)

    def test_p_exactly_at_pmax_is_refused(self):
        # 6000 eV at T = 3 keV is p = 2 exactly, and FP deposits only where PG(NP+1) > PSP.
        # With FP's own arithmetic (amfp = PA*AMP, SQRT(2 amfp E AEE)/SQRT(T 1e3 AEE amfp)) it is
        # bitwise 2.0 = PMAX (PG(NPMAX+1) is exactly PMAX).
        self.assert_refused({"PMAX[2]": 2.0, "SPBENG[1]": 6000.0}, "beyond its mesh edge")

    def test_p_one_ulp_below_pmax_in_fps_arithmetic_runs(self):
        # Deuterium, T = 2 keV, 49000 eV, PMAX 7: sqrt(2E/(1000 T)) is exactly 7, but FP's own
        # expression (fpcoef.f90 ~535) gives 6.999999999999999: FP deposits, so the run is not refused.
        self.assert_runs({"PTPR[2]": 2.0, "PTPP[2]": 2.0, "PMAX[2]": 7.0, "SPBENG[1]": 49000.0})

    def test_a_beam_just_above_pmax_in_fps_arithmetic_is_refused(self):
        # 73500 eV at 3 keV: FP's p = 7.000000000000001 > PMAX 7.
        self.assert_refused({"PMAX[2]": 7.0, "SPBENG[1]": 73500.0}, "beyond its mesh edge")

    def test_a_temperature_not_above_0_is_refused(self):
        verdict, out = _child({**D_RUN, **BEAM, "PTPR[2]": 0.0, "PTPP[2]": 0.0})
        self.assertEqual(verdict, "VERDICT REFUSED", out[-600:])
        lines = xx_lines(out)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("beam 1: the temperature of species 2 is not above 0", lines[0])

    def test_a_temperature_not_above_0_needs_a_source(self):
        # Without a source (SPBTOT 0) the beam is not looked at.
        self.assert_runs({"PTPR[2]": 3.0, "PTPP[2]": 3.0, "SPBTOT[1]": 0.0})

    def test_the_temperature_is_the_pressure_average_of_ptpr_and_ptpp(self):
        # T = (PTPR + 2 PTPP)/3 = 3 keV: p = 7.30 < 7.4 runs; T = PTPR (1) would be p = 12.6.
        self.assert_runs({"PMAX[2]": 7.4, "PTPR[2]": 1.0, "PTPP[2]": 4.0})
        # T = (4 + 2)/3 = 2 keV: p = 8.94 > 7.4 (T = PTPP, 1 keV, would be even larger; T = PTPR 4 keV would run).
        self.assert_refused({"PMAX[2]": 7.4, "PTPR[2]": 4.0, "PTPP[2]": 1.0}, "beyond its mesh edge")
        # T = 3 keV: p = 7.30 > 7 is refused (a PTPP-only temperature, 4 keV, p = 6.32, would run).
        self.assert_refused({"PMAX[2]": 7.0, "PTPR[2]": 1.0, "PTPP[2]": 4.0}, "beyond its mesh edge")

    def test_a_beam_on_a_non_kinetic_species_is_refused_once(self):
        verdict, out = _child({**D_RUN, **BEAM, "NSSPB[1]": 1, "PMAX[1]": 0.5})
        self.assertEqual(verdict, "VERDICT REFUSED", out[-600:])
        lines = xx_lines(out)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("is no kinetic species", lines[0])

    def test_the_pmax_rule_needs_model_nbi_1(self):
        self.assert_runs({"MODEL_NBI": 0, "PMAX[2]": 7.0})

    # --- the electron compensating source takes PZ of the wrong species ---
    ELECTRONS_AND_HE4 = {
        "NSMAX": 4, "NSAMAX": 2, "NSBMAX": 4, "NS_NSA[1]": 1, "NS_NSA[2]": 4,
        "NSSPB[1]": 4, "PTPR[1]": 3.0, "PTPP[1]": 3.0, "PTPR[4]": 3.0, "PTPP[4]": 3.0,
        "PMAX[1]": 10.0, "PMAX[4]": 10.0,
        # pl_init gives species 4 a temperature (5 keV) but no density (NaN densities otherwise).
        "PN[4]": 0.1, "PNS[4]": 0.05, "PTS[4]": 1.0,
    }

    def test_the_electron_source_with_the_wrong_charge_is_refused(self):
        # Species 4 (He4, PZ 2) is kinetic slot 2; the electron branch takes PZ(2) = 1 (D).
        self.assert_refused(self.ELECTRONS_AND_HE4, "XX fp_run: beam 1 on species 4: FP's electron source takes PZ(2)")

    def test_the_pz_case_is_one_line(self):
        verdict, out = _child({**D_RUN, **BEAM, **self.ELECTRONS_AND_HE4})
        self.assertEqual(verdict, "VERDICT REFUSED", out[-600:])
        self.assertEqual(len(xx_lines(out)), 1, xx_lines(out))

    def test_a_beam_beyond_the_electron_mesh_is_refused_with_its_own_line_not_pz(self):
        # The electron momentum of an 80 keV He4 beam at 3 keV electrons is about 0.085: PMAX[1] 0.05
        # leaves it outside the electron mesh, where FP deposits no electrons (and reads no PZ).
        verdict, out = _child({**D_RUN, **BEAM, **self.ELECTRONS_AND_HE4, "PMAX[1]": 0.05})
        self.assertEqual(verdict, "VERDICT REFUSED", out[-600:])
        lines = xx_lines(out)
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("the electron compensating source of beam 1 falls beyond the electron mesh edge", lines[0])
        self.assertNotIn("PZ", lines[0])

    def test_a_deuterium_beam_beyond_the_electron_mesh_is_refused(self):
        self.assert_refused({"NSAMAX": 2, "NS_NSA[1]": 1, "NS_NSA[2]": 2, "PTPR[1]": 3.0, "PTPP[1]": 3.0,
                             "PMAX[1]": 0.05},
                            "XX fp_run: the electron compensating source of beam 1 falls beyond the electron mesh edge")

    # FP's electron momentum of the 80 keV deuterium beam at 3 keV electrons, with its own arithmetic
    # (amfp_e = (AME/AMP)*AMP, ptfp0_e = sqrt(T 1e3 AEE amfp_e), pe = sqrt(2 amfp_e**2 E AEE/amfp_b)/ptfp0_e).
    P_E = 0.12051191050234175
    ELECTRONS_AND_D = {"NSAMAX": 2, "NS_NSA[1]": 1, "NS_NSA[2]": 2, "PTPR[1]": 3.0, "PTPP[1]": 3.0}

    def test_the_electron_momentum_exactly_at_the_electron_mesh_edge_is_refused(self):
        self.assert_refused({**self.ELECTRONS_AND_D, "PMAX[1]": self.P_E},
                            "XX fp_run: the electron compensating source of beam 1 falls beyond the electron mesh edge")

    def test_the_electron_momentum_one_ulp_inside_the_electron_mesh_edge_runs(self):
        import math
        self.assert_runs({**self.ELECTRONS_AND_D, "PMAX[1]": math.nextafter(self.P_E, math.inf)})

    def test_a_beam_inside_the_electron_mesh_is_not_refused_for_it(self):
        self.assert_runs({**self.ELECTRONS_AND_HE4, "PZ[2]": 2.0, "PMAX[1]": 0.2})

    def test_the_last_slot_of_the_species_is_the_one_fp_takes(self):
        # Slots 2 and 3 both hold species 4: FP's loop ends on slot 3 (PZ 1), the first match (PZ 2) would pass.
        self.assert_refused({**self.ELECTRONS_AND_HE4, "NSAMAX": 3, "NS_NSA[3]": 4, "PZ[2]": 2.0, "PZ[3]": 1.0},
                            "XX fp_run: beam 1 on species 4: FP's electron source takes PZ(3)")

    def test_beam_2_with_the_wrong_charge_is_refused_too(self):
        self.assert_refused({**self.ELECTRONS_AND_HE4, "NSSPB[1]": 2, "NSSPB[2]": 4, "NBEAMMAX": 2,
                             "SPBTOT[2]": 1.0e19, "SPBENG[2]": 8.0e4, "SPBANG[2]": 30.0, "SPBR0[2]": 0.0,
                             "SPBRW[2]": 0.5, "SPBTOT[1]": 0.0},
                            "XX fp_run: beam 2 on species 4: FP's electron source takes PZ(2)")

    def test_the_electron_branch_runs_only_when_beam_1_is_not_on_electrons(self):
        # NSSPB(1) = 1 (beam 1 without a source): FP skips the electron branch, so beam 2's PZ case is harmless.
        self.assert_runs({**self.ELECTRONS_AND_HE4, "NSSPB[1]": 1, "NSSPB[2]": 4, "NBEAMMAX": 2,
                          "SPBTOT[1]": 0.0, "SPBTOT[2]": 1.0e19, "SPBENG[2]": 8.0e4, "SPBANG[2]": 30.0,
                          "SPBR0[2]": 0.0, "SPBRW[2]": 0.5})

    def test_the_same_case_runs_when_pz_2_equals_pz_4(self):
        self.assert_runs({**self.ELECTRONS_AND_HE4, "PZ[2]": 2.0})

    def test_electrons_kinetic_with_the_identity_map_runs(self):
        self.assert_runs({"NSAMAX": 2, "NS_NSA[1]": 1, "NS_NSA[2]": 2, "PTPR[1]": 3.0, "PTPP[1]": 3.0,
                          "PMAX[1]": 10.0})

    def test_the_pz_rule_needs_model_nbi_1(self):
        self.assert_runs({**self.ELECTRONS_AND_HE4, "MODEL_NBI": 0})

    # --- MODELA 1 divides by NAVMAX ---
    def test_modela_1_with_navmax_0_is_refused(self):
        self.assert_refused({"MODEL_NBI": 0, "MODELA": 1, "NAVMAX": 0},
                            "XX fp_run: NAVMAX = 0 must be >= 1 with MODELA = 1 or MODEL_WAVE /= 0")

    def test_model_wave_1_with_navmax_0_is_refused_without_modela(self):
        # FPSUMW divides by NAVMAX whatever MODELA: 0 * Inf = NaN in DPP, even without wave power.
        self.assert_refused({"MODEL_NBI": 0, "MODELA": 0, "MODEL_WAVE": 1, "NAVMAX": 0},
                            "XX fp_run: NAVMAX = 0 must be >= 1 with MODELA = 1 or MODEL_WAVE /= 0")

    def test_modela_1_with_navmax_minus_3_is_refused(self):
        self.assert_refused({"MODEL_NBI": 0, "MODELA": 1, "NAVMAX": -3},
                            "XX fp_run: NAVMAX = -3 must be >= 1")

    def test_modela_1_with_navmax_1_runs(self):
        self.assert_runs({"MODEL_NBI": 0, "MODELA": 1, "NAVMAX": 1})

    def test_model_wave_1_with_navmax_1_runs(self):
        self.assert_runs({"MODEL_NBI": 0, "NBEAMMAX": 0, "MODELA": 0, "MODEL_WAVE": 1, "NAVMAX": 1})

    def test_modela_0_model_wave_0_with_navmax_0_runs(self):
        # NAVMAX is unused there.
        self.assert_runs({"MODEL_NBI": 0, "MODELA": 0, "MODEL_WAVE": 0, "NAVMAX": 0})

    def test_the_beam_rules_need_model_nbi_1(self):
        self.assert_runs({"MODEL_NBI": 0, "SPBRW[1]": 0.0, "SPBANG[1]": 180.0, "NSSPB[1]": 1})


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
