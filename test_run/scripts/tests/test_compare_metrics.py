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

    def test_fails_when_baseline_is_tiny_and_actual_is_zero(self):
        # 1e-300 vs 0: absolute diff is negligible but the relative
        # error is 1.0 because the comparator clamps the denominator
        # at 1e-300. Documents this (intentional) failure mode so that
        # any later change to _rel_err breaks this test.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _minimal(scalars={"X": 1e-300}))
            write_json(act,  _minimal(scalars={"X": 0.0}))
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


if __name__ == "__main__":
    unittest.main()
