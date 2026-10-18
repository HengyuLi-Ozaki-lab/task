import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "compare_metrics.py"


def write_json(path: Path, obj: dict) -> None:
    # Use the default Python json encoder, which serialises NaN/Inf as
    # the non-standard tokens NaN/Infinity (Python's json round-trips
    # them). compare_metrics.py reads the same way so this is fine.
    path.write_text(json.dumps(obj))


def write_text(path: Path, raw: str) -> None:
    path.write_text(raw)


def run_compare(actual: Path, baseline: Path, tol: str = "1e-10"):
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--baseline", str(baseline),
         "--actual", str(actual),
         "--tolerance", tol],
        capture_output=True, text=True,
    )


def _minimal(scalars=None, profile=None,
             NT=1, NRMAX=1, NSMAX=1) -> dict:
    """Smallest valid metric dict; lets each test override only what it cares about."""
    return {
        "NT": NT, "NRMAX": NRMAX, "NSMAX": NSMAX,
        "scalars": dict(scalars or {}),
        "profile": list(profile or []),
    }


def _profile_row(NR=1, RN=None, RT=None, AJ=0.0, QP=0.0) -> dict:
    return {
        "NR": NR,
        "RN": list(RN if RN is not None else [0.0]),
        "RT": list(RT if RT is not None else [0.0]),
        "AJ": AJ,
        "QP": QP,
    }


def _sample() -> dict:
    return {
        "NT": 100, "NRMAX": 2, "NSMAX": 2,
        "scalars": {
            "T": 2.0, "WPT": 41.13, "AJT": 15.451, "Q0": 0.579,
            "BETA0": 0.0123, "BETAP0": 0.089, "BETAA": 0.00234, "BETAN": 0.0456,
            "TAUE1": 2.265, "TAUE2": 2.1, "ZEFF0": 1.5, "ALI": 0.75, "RQ1": 1.8,
        },
        "profile": [
            {"NR": 1, "RN": [0.7, 0.315], "RT": [4.565, 4.275], "AJ": 15.451, "QP": 0.579},
            {"NR": 2, "RN": [0.65, 0.3],  "RT": [4.2, 3.9],     "AJ": 14.0,   "QP": 0.65},
        ],
    }


def _tot_sample() -> dict:
    """Sample that mirrors the extract_tot_metrics.py schema (with ``modules``)."""
    s = _sample()
    s["modules"] = {
        "TR_PRESENT": 1, "TI_PRESENT": 0, "FP_PRESENT": 0, "WR_PRESENT": 0,
    }
    return s


class CompareMetricsTest(unittest.TestCase):

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_passes_on_identical(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())
            write_json(act,  _sample())
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_fails_on_scalar_drift(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())
            drifted = _sample()
            drifted["scalars"]["WPT"] = 41.13 * (1.0 + 1e-7)   # > 1e-10
            write_json(act, drifted)
            res = run_compare(act, base, tol="1e-10")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("WPT", res.stdout)

    def test_passes_on_drift_within_tolerance(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())
            close = _sample()
            close["scalars"]["WPT"] = 41.13 * (1.0 + 1e-13)   # < 1e-10
            write_json(act, close)
            res = run_compare(act, base, tol="1e-10")
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_fails_on_profile_drift(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())
            drifted = _sample()
            drifted["profile"][1]["RT"][0] = 4.2 * (1.0 + 1e-5)
            write_json(act, drifted)
            res = run_compare(act, base, tol="1e-10")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("RT", res.stdout)

    def test_fails_when_dimensions_differ(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())
            short = _sample()
            short["NRMAX"] = 1
            short["profile"] = short["profile"][:1]
            write_json(act, short)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)

    def test_fails_when_actual_is_inf(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())
            infected = _sample()
            infected["scalars"]["WPT"] = float("inf")
            write_json(act, infected)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("WPT", res.stdout)
            self.assertIn("Inf", res.stdout)

    def test_fails_when_baseline_is_inf(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            inf_base = _sample()
            inf_base["scalars"]["WPT"] = float("inf")
            write_json(base, inf_base)
            write_json(act, _sample())
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("WPT", res.stdout)
            self.assertIn("Inf", res.stdout)

    def test_passes_when_both_are_same_inf(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            inf_sample = _sample()
            inf_sample["scalars"]["WPT"] = float("inf")
            write_json(base, inf_sample)
            write_json(act,  inf_sample)
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stderr)

    # --- modules dict (tot schema) ----------------------------------------

    def test_passes_on_identical_tot_modules(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _tot_sample())
            write_json(act,  _tot_sample())
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_fails_on_module_presence_drift(self):
        """Bugbot MEDIUM: structural drift in modules dict must fail."""
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _tot_sample())
            drifted = _tot_sample()
            drifted["modules"]["TR_PRESENT"] = 0  # was 1 in baseline
            write_json(act, drifted)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("TR_PRESENT", res.stdout)
            self.assertIn("modules", res.stdout)

    def test_fails_when_module_appears_only_in_actual(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())  # tr-only schema, no modules dict
            tot = _tot_sample()
            write_json(act, tot)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("modules", res.stdout)

    def test_fails_on_unknown_module_key(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _tot_sample())
            drifted = _tot_sample()
            drifted["modules"]["EQ_PRESENT"] = 1  # not in MODULE_KEYS
            write_json(act, drifted)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("EQ_PRESENT", res.stdout)


class CompareMetricsSchemaTest(unittest.TestCase):
    """Edge cases around the top-level metric dict schema."""

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_fails_when_top_level_dim_missing_in_actual(self):
        # NT in baseline but absent in actual -> should be reported clearly.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(NT=100))
            actual = _minimal(NT=100)
            actual.pop("NT")
            write_json(act, actual)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("NT", res.stdout)

    def test_fails_when_extra_scalar_only_in_actual(self):
        # A scalar present in actual but missing in baseline must be flagged
        # (catches accidental additions to the dump that the baseline
        # doesn't yet pin).
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"A": 1.0}))
            write_json(act,  _minimal(scalars={"A": 1.0, "B": 2.0}))
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("scalars.B", res.stdout)
            self.assertIn("missing", res.stdout)

    def test_fails_when_scalar_only_in_baseline(self):
        # Symmetric to the previous test: dropping a scalar from the
        # actual output must fail (catches silent regression in
        # extract_*_metrics).
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"A": 1.0, "B": 2.0}))
            write_json(act,  _minimal(scalars={"A": 1.0}))
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("scalars.B", res.stdout)

    def test_passes_when_top_level_scalars_key_absent_on_both_sides(self):
        # Both sides omit the optional 'scalars' key entirely.
        # Documented behaviour: defaults to empty dict, so this matches.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            stub = {"NT": 1, "NRMAX": 1, "NSMAX": 1, "profile": []}
            write_json(base, stub)
            write_json(act,  stub)
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


class CompareMetricsNumericTest(unittest.TestCase):
    """Edge cases around floating point comparison."""

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_passes_when_baseline_is_tiny_and_actual_is_zero(self):
        # 1e-300 vs 0: both below _NEAR_ZERO_THRESHOLD (1e-10), so the
        # comparator uses the absolute difference instead of the
        # relative error (0ed723fc). Before that commit this case failed
        # with rel_err = 1.0; the test kept asserting the old behaviour
        # and nobody noticed because test_run/scripts/tests was not in
        # the CI pytest run (#239).
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": 1e-300}))
            write_json(act,  _minimal(scalars={"X": 0.0}))
            res = run_compare(act, base, tol="1e-10")
            self.assertEqual(res.returncode, 0, res.stdout)

    def test_fails_when_only_one_side_is_near_zero(self):
        # 1e-300 vs 2e-10: the actual is above the near-zero threshold,
        # so the relative rule applies and rel_err = 1.0 > tol.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": 1e-300}))
            write_json(act,  _minimal(scalars={"X": 2e-10}))
            res = run_compare(act, base, tol="1e-10")
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("scalars.X", res.stdout)

    def test_passes_for_subnormal_compared_to_zero(self):
        # The smallest positive subnormal (~5e-324) divided by the
        # 1e-300 denom floor yields rel_err ~5e-24, which is well
        # under any realistic tolerance.
        sub = math.nextafter(0.0, 1.0)
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": sub}))
            write_json(act,  _minimal(scalars={"X": 0.0}))
            res = run_compare(act, base, tol="1e-10")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_passes_for_negative_zero_vs_positive_zero(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": -0.0}))
            write_json(act,  _minimal(scalars={"X":  0.0}))
            res = run_compare(act, base, tol="0")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_fails_when_both_are_nan(self):
        # Documents current behaviour: NaN never compares equal here,
        # even when both sides are NaN. Any NaN in either dump fails.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            nan_dict = _minimal(scalars={"X": float("nan")})
            write_json(base, nan_dict)
            write_json(act,  nan_dict)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("NaN", res.stdout)
            self.assertIn("scalars.X", res.stdout)

    def test_passes_for_int_vs_float_same_value(self):
        # Baseline often comes from a checked-in JSON which can carry
        # bare ints (e.g. 42) while extract_* may emit 42.0.
        # _check_scalar coerces both via float(), so this must match.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"K": 42}))
            write_json(act,  _minimal(scalars={"K": 42.0}))
            res = run_compare(act, base, tol="0")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_fails_for_int_vs_slightly_different_float(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"K": 42}))
            write_json(act,  _minimal(scalars={"K": 42.0001}))
            res = run_compare(act, base, tol="1e-10")
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("scalars.K", res.stdout)


class CompareMetricsToleranceBoundaryTest(unittest.TestCase):
    """Tolerance comparison is `e > tol`, so equality at tol must pass."""

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_passes_when_relative_error_equals_tolerance(self):
        # rel_err(2.0, 1.0) == 0.5 exactly. tol=0.5 => e > tol is false => PASS.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": 2.0}))
            write_json(act,  _minimal(scalars={"X": 1.0}))
            res = run_compare(act, base, tol="0.5")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_fails_when_relative_error_just_over_tolerance(self):
        # Same construction; pick a tol just below 0.5 -> FAIL.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": 2.0}))
            write_json(act,  _minimal(scalars={"X": 1.0}))
            res = run_compare(act, base, tol="0.49")
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("scalars.X", res.stdout)

    def test_zero_tolerance_passes_only_on_bit_exact(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": 1.234567890123456}))
            write_json(act,  _minimal(scalars={"X": 1.234567890123456}))
            res = run_compare(act, base, tol="0")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)

    def test_zero_tolerance_fails_on_one_ulp_difference(self):
        a = 1.234567890123456
        b = math.nextafter(a, math.inf)
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": a}))
            write_json(act,  _minimal(scalars={"X": b}))
            res = run_compare(act, base, tol="0")
            self.assertNotEqual(res.returncode, 0, res.stdout)


class CompareMetricsProfileTest(unittest.TestCase):
    """Edge cases inside the profile list-of-dicts."""

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_fails_when_profile_row_count_differs(self):
        # NRMAX matches but profile length differs -> still flagged
        # (script checks both dimensions and the actual list length).
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            base_dict = _minimal(NRMAX=2,
                                 profile=[_profile_row(NR=1), _profile_row(NR=2)])
            act_dict  = _minimal(NRMAX=2,
                                 profile=[_profile_row(NR=1)])
            write_json(base, base_dict)
            write_json(act,  act_dict)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("profile length", res.stdout)

    def test_fails_when_profile_row_NR_field_differs(self):
        # Same number of rows, but rows are misaligned (NR labels diverge).
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            base_dict = _minimal(NRMAX=2,
                                 profile=[_profile_row(NR=1), _profile_row(NR=2)])
            act_dict  = _minimal(NRMAX=2,
                                 profile=[_profile_row(NR=1), _profile_row(NR=3)])
            write_json(base, base_dict)
            write_json(act,  act_dict)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("profile[1].NR", res.stdout)

    def test_fails_when_profile_RN_list_lengths_differ(self):
        # The list-vs-float dispatch must catch shape changes inside a row.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            base_dict = _minimal(NRMAX=1,
                                 profile=[_profile_row(NR=1, RN=[0.7, 0.3])])
            act_dict  = _minimal(NRMAX=1,
                                 profile=[_profile_row(NR=1, RN=[0.7, 0.3, 0.1])])
            write_json(base, base_dict)
            write_json(act,  act_dict)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0, res.stdout)
            self.assertIn("profile[0].RN", res.stdout)
            self.assertIn("length differ", res.stdout)

    def test_passes_when_profile_RN_list_values_match(self):
        # Counterpart to the length test: equal-length RN lists with
        # equal values must succeed even at zero tolerance.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            row = _profile_row(NR=1, RN=[0.7, 0.3], RT=[4.5, 4.0],
                               AJ=15.4, QP=0.58)
            base_dict = _minimal(NRMAX=1, profile=[row])
            act_dict  = _minimal(NRMAX=1, profile=[row])
            write_json(base, base_dict)
            write_json(act,  act_dict)
            res = run_compare(act, base, tol="0")
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)


class CompareMetricsJsonIoTest(unittest.TestCase):
    """JSON input errors should surface, not silently 'pass'."""

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_fails_on_malformed_baseline_json(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_text(base, "{ this is not valid json")
            write_json(act, _minimal())
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            # CPython surfaces json.JSONDecodeError to stderr via the traceback.
            self.assertIn("JSONDecodeError", res.stderr)

    def test_fails_on_empty_baseline_file(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_text(base, "")
            write_json(act, _minimal())
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("JSONDecodeError", res.stderr)

    def test_fails_on_malformed_actual_json(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal())
            write_text(act, "garbage")
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("JSONDecodeError", res.stderr)


def _fp_sample() -> dict:
    return {
        "NRMAX": 2, "NSAMAX": 2, "NPMAX": 10, "NTHMAX": 10, "NTG2": 1,
        "scalars": {"TIMEFP": 1.0e-3},
        "profile": [
            {"NR": 1, "NSA": 1, "RNT": 0.7,  "RWT": 4.5, "RTT": 4.2, "RJT": 15.4, "RPCT": 0.3,   "RPWT": 0.12},
            {"NR": 2, "NSA": 1, "RNT": 0.65, "RWT": 4.2, "RTT": 3.9, "RJT": 14.0, "RPCT": 0.28,  "RPWT": 0.11},
            {"NR": 1, "NSA": 2, "RNT": 0.31, "RWT": 2.0, "RTT": 2.1, "RJT": 3.4,  "RPCT": 0.04,  "RPWT": 0.03},
            {"NR": 2, "NSA": 2, "RNT": 0.30, "RWT": 1.8, "RTT": 1.9, "RJT": 3.0,  "RPCT": 0.035, "RPWT": 0.025},
        ],
    }


class CompareMetricsFpTest(unittest.TestCase):
    """Verify compare_metrics is module-agnostic enough for FP schema."""

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_passes_on_identical_fp_schema(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _fp_sample())
            write_json(act,  _fp_sample())
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_fails_on_fp_profile_drift(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _fp_sample())
            drifted = _fp_sample()
            drifted["profile"][0]["RWT"] = 4.5 * (1.0 + 1e-7)
            write_json(act, drifted)
            res = run_compare(act, base, tol="1e-10")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("RWT", res.stdout)

    def test_fails_when_fp_dimensions_differ(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _fp_sample())
            short = _fp_sample()
            short["NRMAX"] = 1
            short["profile"] = short["profile"][:2]
            write_json(act, short)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)


def _wrx_sample() -> dict:
    """extract_wrx_metrics.py shape: {arrays, arrays2, scalars} (#239).

    ``*_nsa_nray`` rows are species (NSAMAX_WR x NRAYMAX, as
    wrx/wrxregress.f90 writes them); ``pwr_nrs_nsa`` rows are bins.
    """
    return {
        "MDLWRQ": 1, "MODELG": 2, "NRAYMAX": 2, "NRLMAX": 3, "NRSMAX": 2,
        "NSAMAX_WR": 2, "NSMAX": 2, "NSTPMAX": 100,
        "scalars": {"pwr_tot": 0.75},
        "arrays": {
            "NSTPMAX_NRAY": [17, 23],
            "pwr_nray": [0.5, 0.25],
            "pwr_nsa": [0.7, 0.05],
            "pos_nrs": [0.25, 0.75],
            "pos_nrl": [3.0, 3.5, 4.0],
        },
        "arrays2": {
            "pwr_nsa_nray": [[0.45, 0.25], [0.05, 0.0]],
            "pwr_nrs_nsa": [[0.3, 0.02], [0.4, 0.03]],
            "pwr_nrl_nsa": [[0.1, 0.0], [0.5, 0.05], [0.1, 0.0]],
            "pos_pwrmax_rs_nsa_nray": [[0.3, 0.4], [0.3, 0.0]],
            "pos_pwrmax_rl_nsa_nray": [[3.2, 3.4], [3.2, 0.0]],
            "pwrmax_rs_nsa_nray": [[0.2, 0.1], [0.02, 0.0]],
            "pwrmax_rl_nsa_nray": [[0.2, 0.1], [0.02, 0.0]],
        },
    }


class CompareMetricsWrxArraysTest(unittest.TestCase):
    """``arrays`` / ``arrays2`` are compared element-wise (#239).

    Before the fix only the dimension header and ``scalars.pwr_tot``
    were checked for the wrx schema; corrupting or dropping the array
    groups passed.
    """

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def _run(self, mutate) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _wrx_sample())
            actual = _wrx_sample()
            mutate(actual)
            write_json(act, actual)
            return run_compare(act, base)

    def test_passes_on_identical(self):
        res = self._run(lambda a: None)
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_passes_on_array_drift_within_tolerance(self):
        def mutate(a):
            a["arrays"]["pwr_nray"][0] *= 1.0 + 1e-12
            a["arrays2"]["pwr_nsa_nray"][0][1] *= 1.0 + 1e-12
        res = self._run(mutate)
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_fails_on_1d_array_drift(self):
        def mutate(a):
            a["arrays"]["pwr_nray"][1] += 1e-6
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays.pwr_nray[1]", res.stdout)

    def test_fails_on_2d_array_drift(self):
        def mutate(a):
            a["arrays2"]["pwr_nrl_nsa"][1][1] += 1e-6
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays2.pwr_nrl_nsa[1][1]", res.stdout)

    def test_fails_when_every_array_value_is_corrupted(self):
        # The issue's MWE: +1e6 on every element with scalars intact.
        def mutate(a):
            for k, v in a["arrays"].items():
                a["arrays"][k] = [x + 1e6 for x in v]
            for k, rows in a["arrays2"].items():
                a["arrays2"][k] = [[x + 1e6 for x in row] for row in rows]
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("FAIL", res.stdout)

    def test_fails_when_array_groups_are_dropped(self):
        def mutate(a):
            del a["arrays"]
            del a["arrays2"]
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays: missing on one side", res.stdout)
        self.assertIn("arrays2: missing on one side", res.stdout)

    def test_fails_when_array_name_missing_on_one_side(self):
        def mutate(a):
            del a["arrays2"]["pwrmax_rl_nsa_nray"]
            a["arrays"]["extra"] = [1.0]
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays2.pwrmax_rl_nsa_nray: missing", res.stdout)
        self.assertIn("arrays.extra: missing", res.stdout)

    def test_fails_on_1d_length_mismatch_against_header(self):
        # A known name whose length disagrees with the dimension header
        # is reported against the header, before any element comparison.
        def mutate(a):
            a["arrays"]["pos_nrl"].append(4.5)
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays.pos_nrl (actual): shape (4,) does not match the header {'NRLMAX': 3}", res.stdout)

    def test_fails_on_1d_length_mismatch_for_unknown_name(self):
        # A name without a header rule only has to agree between sides.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            b = _wrx_sample(); b["arrays"]["extra"] = [1.0, 2.0, 3.0]
            a = _wrx_sample(); a["arrays"]["extra"] = [1.0, 2.0, 3.0, 4.0]
            write_json(base, b); write_json(act, a)
            res = run_compare(act, base)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays.extra: length differ (3 vs 4)", res.stdout)

    def test_fails_on_2d_row_length_mismatch_for_unknown_name(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            b = _wrx_sample(); b["arrays2"]["extra"] = [[1.0, 2.0], [3.0, 4.0]]
            a = _wrx_sample(); a["arrays2"]["extra"] = [[1.0, 2.0, 0.0], [3.0, 4.0, 0.0]]
            write_json(base, b); write_json(act, a)
            res = run_compare(act, base)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays2.extra[0]: row length differ (2 vs 3)", res.stdout)

    def test_fails_on_transposed_2d_array(self):
        # The to_dict() bug hidden by the old comparator: same values,
        # rows = ray instead of rows = species. A square block
        # (NRAYMAX == NSAMAX_WR == 2) so only the values can tell.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            b = _wrx_sample()
            b["arrays2"]["pwr_nsa_nray"] = [[1.0, 2.0], [3.0, 4.0]]
            write_json(base, b)
            actual = _wrx_sample()
            actual["arrays2"]["pwr_nsa_nray"] = [[1.0, 3.0], [2.0, 4.0]]
            write_json(act, actual)
            res = run_compare(act, base)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays2.pwr_nsa_nray[0][1]", res.stdout)

    def test_fails_on_2d_shape_mismatch_against_header(self):
        def mutate(a):
            a["arrays2"]["pwr_nsa_nray"] = [[0.45, 0.25, 0.0], [0.05, 0.0, 0.0]]
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays2.pwr_nsa_nray (actual): shape (2, 3) does not match the header {'NSAMAX_WR': 2, 'NRAYMAX': 2}", res.stdout)

    def test_int_array_must_match_exactly(self):
        def mutate(a):
            a["arrays"]["NSTPMAX_NRAY"][0] = 18
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays.NSTPMAX_NRAY[0]: baseline=17 actual=18", res.stdout)

    def test_int_array_accepts_integral_float(self):
        def mutate(a):
            a["arrays"]["NSTPMAX_NRAY"][0] = 17.0
        res = self._run(mutate)
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_int_array_rejects_drifting_float(self):
        # Within the float tolerance, but an int array must not drift.
        def mutate(a):
            a["arrays"]["NSTPMAX_NRAY"][0] = 17.000000000001
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays.NSTPMAX_NRAY[0]", res.stdout)
        self.assertIn("integer", res.stdout)

    def test_fails_on_ragged_rows_even_when_identical(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            b = _wrx_sample()
            b["arrays2"]["pwr_nrs_nsa"] = [[0.3, 0.02], [0.4]]
            write_json(base, b)
            write_json(act, b)
            res = run_compare(act, base)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays2.pwr_nrs_nsa (baseline): ragged rows", res.stdout)
        self.assertIn("arrays2.pwr_nrs_nsa (actual): ragged rows", res.stdout)

    def test_fails_when_array_shape_disagrees_with_header_on_both_sides(self):
        # Both dumps carry the same malformed block: fewer rows than
        # NSAMAX_WR says. Element-wise they match; the header does not.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            b = _wrx_sample()
            b["arrays2"]["pwr_nsa_nray"] = [[0.45, 0.25]]
            b["arrays"]["pwr_nsa"] = [0.7]
            write_json(base, b)
            write_json(act, b)
            res = run_compare(act, base)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays2.pwr_nsa_nray (baseline): shape (1, 2) does not match the header", res.stdout)
        self.assertIn("arrays.pwr_nsa (baseline): shape (1,) does not match the header", res.stdout)

    def test_passes_with_zero_rays(self):
        # No rays: NRAYMAX=0, per-ray lists empty, *_nsa_nray has one
        # empty row per species (what wrxregress.f90 writes).
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            b = _wrx_sample()
            b["NRAYMAX"] = 0
            b["arrays"]["NSTPMAX_NRAY"] = []
            b["arrays"]["pwr_nray"] = []
            for k in ("pwr_nsa_nray", "pos_pwrmax_rs_nsa_nray", "pos_pwrmax_rl_nsa_nray",
                      "pwrmax_rs_nsa_nray", "pwrmax_rl_nsa_nray"):
                b["arrays2"][k] = [[], []]
            write_json(base, b)
            write_json(act, b)
            res = run_compare(act, base)
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_fails_on_boolean_nan_and_non_numeric_elements(self):
        def mutate(a):
            a["arrays"]["pwr_nray"][0] = True
            a["arrays"]["pos_nrs"][1] = "0.75"
            a["arrays2"]["pwr_nrl_nsa"][0][0] = float("nan")
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays.pwr_nray[0]: boolean, not numeric data", res.stdout)
        self.assertIn("arrays.pos_nrs[1]: non-numeric", res.stdout)
        self.assertIn("arrays2.pwr_nrl_nsa[0][0]: NaN", res.stdout)

    def test_fails_when_array_value_is_not_a_list(self):
        def mutate(a):
            a["arrays"]["pwr_nsa"] = 0.75
            a["arrays2"]["pwr_nsa_nray"] = [0.45, 0.05]
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("arrays.pwr_nsa: not a list on both sides", res.stdout)
        self.assertIn("arrays2.pwr_nsa_nray[0] (actual): row is not a list", res.stdout)

    def test_fails_on_nsamax_wr_dimension_drift(self):
        def mutate(a):
            a["NSAMAX_WR"] = 3
        res = self._run(mutate)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("NSAMAX_WR: baseline=2 actual=3", res.stdout)

    def test_non_wrx_schema_without_array_groups_still_passes(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _sample())
            write_json(act, _sample())
            res = run_compare(act, base)
        self.assertEqual(res.returncode, 0, res.stdout)


if __name__ == "__main__":
    unittest.main()
