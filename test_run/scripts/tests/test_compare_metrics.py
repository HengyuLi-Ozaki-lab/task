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


def _wr_sample() -> dict:
    return {
        "NRAYMAX": 2, "NSTPMAX": 10, "NRSMAX": 1, "NRLMAX": 1,
        "MODELG": 2, "MDLWRI": 101, "MDLWRQ": 0, "mode_beam": 0,
        "scalars": {"RF": 1.6e5, "pwrmax_rs": 0.123},
        "rays": [
            {"NRAY": 1, "NSTP_END": 8,
             "pos_pwrmax_rs_nray": 0.25,
             "RAYS_END": [4.0, 6.0, 0.0, 0.0, -1e3, 0.0, 0.0, 0.9, 0.0]},
            # OOB row: only the two ints (mirrors extractor output for
            # rays whose NSTPMAX_NRAY was out of range).
            {"NRAY": 2, "NSTP_END": -1},
        ],
        "profile_rs": [{"NRS": 1, "pos_nrs": 0.25, "pwr_nrs": 0.06}],
        "profile_rl": [{"NRL": 1, "pos_nrl": 6.5,  "pwr_nrl": 0.04}],
    }


class CompareMetricsWRTest(unittest.TestCase):
    def _paths(self, td):
        return Path(td) / "base.json", Path(td) / "act.json"

    def test_wr_passes_on_identical(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _wr_sample())
            write_json(act,  _wr_sample())
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_wr_fails_on_modelg_drift(self):
        # MODELG is in the WR integer_dimensions tuple; drift must fail.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _wr_sample())
            drifted = _wr_sample()
            drifted["MODELG"] = 9
            write_json(act, drifted)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("MODELG", res.stdout)

    def test_wr_fails_on_mdlwri_drift(self):
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _wr_sample())
            drifted = _wr_sample()
            drifted["MDLWRI"] = 999
            write_json(act, drifted)
            res = run_compare(act, base)
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("MDLWRI", res.stdout)

    def test_wr_oob_row_symmetric_missing_passes(self):
        # When both baseline and actual omit RAYS_END / pos_pwrmax_rs_nray
        # for an OOB row (deterministic), comparator must NOT report
        # "missing" — that's the symmetric-absence relaxation.
        with tempfile.TemporaryDirectory() as td:
            base, act = self._paths(td)
            write_json(base, _wr_sample())
            write_json(act,  _wr_sample())
            res = run_compare(act, base)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertNotIn("missing", res.stdout)


if __name__ == "__main__":
    unittest.main()
