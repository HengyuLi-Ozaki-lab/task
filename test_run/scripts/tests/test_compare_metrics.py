import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "compare_metrics.py"


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj))


def run_compare(actual: Path, baseline: Path, tol: str = "1e-10"):
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--baseline", str(baseline),
         "--actual", str(actual),
         "--tolerance", tol],
        capture_output=True, text=True,
    )


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


if __name__ == "__main__":
    unittest.main()
