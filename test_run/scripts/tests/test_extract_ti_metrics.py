import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_ti_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_ti_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


class ExtractTiMetricsTest(unittest.TestCase):

    def test_extracts_scalars(self):
        data = run_extract(FIXTURE)
        self.assertEqual(data["NT"], 10)
        self.assertEqual(data["NRMAX"], 2)
        self.assertEqual(data["NSMAX"], 2)
        self.assertEqual(data["nsa_max"], 2)
        self.assertEqual(data["scalars"]["T"], 0.01)
        self.assertIn("residual_loop_max", data["scalars"])
        self.assertEqual(data["scalars_int"]["icount_loop_max"], 3)
        self.assertEqual(data["scalars_int"]["icount_mat_max"], 2)

    def test_extracts_profile_rows(self):
        data = run_extract(FIXTURE)
        prof = data["profile"]
        self.assertEqual(len(prof), 2)
        row = prof[0]
        self.assertEqual(row["NR"], 1)
        self.assertEqual(len(row["RNA"]), 2)
        self.assertEqual(len(row["RTA"]), 2)
        self.assertEqual(len(row["RUA"]), 2)
        self.assertAlmostEqual(row["RNA"][0], 0.7)
        self.assertEqual(row["ZEFF"], 1.0)
        self.assertAlmostEqual(row["BETA"], 0.0123)

    def test_rejects_incomplete_dump(self):
        with tempfile.TemporaryDirectory() as td:
            incomplete = Path(td) / "bad.dat"
            incomplete.write_text("# TASK/TI regression dump (format v1)\nNT=1\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(incomplete)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
