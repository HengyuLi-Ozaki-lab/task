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


def _ti_sample() -> dict:
    return {
        "NT": 10, "NRMAX": 2, "NSMAX": 2, "nsa_max": 2,
        "scalars": {"T": 0.01, "residual_loop_max": 1.23e-8},
        "scalars_int": {"icount_loop_max": 3, "icount_mat_max": 2},
        "profile": [
            {"NR": 1, "RNA": [0.7, 0.315], "RTA": [4.565, 4.275], "RUA": [0.0, 0.0],
             "RBP": 1.0, "RQP": 2.0, "RJP": 3.0, "ZEFF": 1.0, "BETA": 0.0123, "BETAP": 0.089},
            {"NR": 2, "RNA": [0.65, 0.30], "RTA": [4.20, 3.90], "RUA": [0.0, 0.0],
             "RBP": 1.5, "RQP": 2.5, "RJP": 3.5, "ZEFF": 1.1, "BETA": 0.011, "BETAP": 0.075},
        ],
    }


class CompareMetricsTiTest(unittest.TestCase):

    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_passes_on_identical_ti(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _ti_sample())
            write_json(act, _ti_sample())
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_fails_on_ti_profile_drift(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _ti_sample())
            drifted = _ti_sample()
            drifted["profile"][0]["RNA"][1] = 0.315 * (1.0 + 1e-5)
            write_json(act, drifted)
            res = run_compare(act, base, tol="1e-10")
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("RNA", res.stdout)

    def test_fails_on_ti_int_counter_drift(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _ti_sample())
            drifted = _ti_sample()
            drifted["scalars_int"]["icount_loop_max"] = 4
            write_json(act, drifted)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("icount_loop_max", res.stdout)


if __name__ == "__main__":
    unittest.main()
