import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "compare_metrics.py"

WRX_BASE = {
    "NRAYMAX": 2, "NSTPMAX": 10, "NRSMAX": 3, "NRLMAX": 3,
    "NSAMAX_WR": 2, "NSMAX": 2, "MODELG": 2, "MDLWRQ": 1,
    "scalars": {"pwr_tot": 1.0},
    "arrays": {
        "NSTPMAX_NRAY": [8, 9],
        "pwr_nray": [0.6, 0.4],
        "pwr_nsa": [0.7, 0.3],
        "pos_nrs": [0.1, 0.3, 0.5],
        "pos_nrl": [0.2, 0.4, 0.6],
    },
    "arrays2": {
        "pwr_nsa_nray": [[0.3, 0.4], [0.2, 0.1]],
    },
}


def _run(baseline: dict, actual: dict, tol: str = "1e-10",
         schema: str = "wrx") -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as d:
        bp = Path(d) / "b.json"
        ap_ = Path(d) / "a.json"
        bp.write_text(json.dumps(baseline))
        ap_.write_text(json.dumps(actual))
        return subprocess.run(
            [sys.executable, str(SCRIPT),
             "--baseline", str(bp), "--actual", str(ap_),
             "--tolerance", tol, "--schema", schema],
            capture_output=True, text=True,
        )


class CompareMetricsWrxTest(unittest.TestCase):

    def test_match_explicit_schema(self):
        r = _run(WRX_BASE, WRX_BASE)
        self.assertEqual(r.returncode, 0,
                         f"stdout={r.stdout!r} stderr={r.stderr!r}")

    def test_match_auto_schema(self):
        r = _run(WRX_BASE, WRX_BASE, schema="auto")
        self.assertEqual(r.returncode, 0,
                         f"stdout={r.stdout!r} stderr={r.stderr!r}")

    def test_pwr_tot_drift(self):
        actual = copy.deepcopy(WRX_BASE)
        actual["scalars"]["pwr_tot"] = 1.0 + 1e-5
        r = _run(WRX_BASE, actual)
        self.assertNotEqual(r.returncode, 0)

    def test_int_array_mismatch(self):
        actual = copy.deepcopy(WRX_BASE)
        actual["arrays"]["NSTPMAX_NRAY"] = [8, 10]
        r = _run(WRX_BASE, actual)
        self.assertNotEqual(r.returncode, 0)

    def test_array2_drift(self):
        actual = copy.deepcopy(WRX_BASE)
        actual["arrays2"]["pwr_nsa_nray"][0][1] = 0.4 + 1e-5
        r = _run(WRX_BASE, actual)
        self.assertNotEqual(r.returncode, 0)

    def test_dim_mismatch_aborts(self):
        actual = copy.deepcopy(WRX_BASE)
        actual["NRAYMAX"] = 3
        r = _run(WRX_BASE, actual)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("NRAYMAX", r.stdout)


if __name__ == "__main__":
    unittest.main()
