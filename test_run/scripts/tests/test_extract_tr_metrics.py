import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_tr_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_tr_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


class ExtractTrMetricsTest(unittest.TestCase):

    def test_extracts_scalars(self):
        data = run_extract(FIXTURE)
        self.assertEqual(data["NT"], 100)
        self.assertEqual(data["NRMAX"], 2)
        self.assertEqual(data["NSMAX"], 2)
        self.assertEqual(data["scalars"]["T"], 2.0)
        self.assertEqual(data["scalars"]["WPT"], 41.13)
        self.assertEqual(data["scalars"]["Q0"], 0.579)
        self.assertIn("BETA0", data["scalars"])
        self.assertIn("ALI", data["scalars"])

    def test_extracts_profile_rows(self):
        data = run_extract(FIXTURE)
        prof = data["profile"]
        self.assertEqual(len(prof), 2)
        row = prof[0]
        self.assertEqual(row["NR"], 1)
        self.assertEqual(len(row["RN"]), 2)
        self.assertEqual(len(row["RT"]), 2)
        self.assertEqual(row["RN"][0], 0.7)
        self.assertEqual(row["AJ"], 15.451)
        self.assertEqual(row["QP"], 0.579)

    def test_rejects_incomplete_dump(self):
        with tempfile.TemporaryDirectory() as td:
            incomplete = Path(td) / "bad.dat"
            incomplete.write_text("# TASK/TR regression dump (format v1)\nNT=1\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(incomplete)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
