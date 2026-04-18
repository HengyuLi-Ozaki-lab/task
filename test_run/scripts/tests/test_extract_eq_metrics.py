import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_eq_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_eq_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


class ExtractEqMetricsTest(unittest.TestCase):

    def test_extracts_dimensions(self):
        data = run_extract(FIXTURE)
        self.assertEqual(data["NRMAX"], 3)
        self.assertEqual(data["NTHMAX"], 64)
        self.assertEqual(data["NSUMAX"], 65)
        self.assertEqual(data["NSGMAX"], 32)
        self.assertEqual(data["NTGMAX"], 32)
        self.assertEqual(data["NPSMAX"], 21)
        self.assertEqual(data["NRVMAX"], 50)

    def test_extracts_scalars(self):
        data = run_extract(FIXTURE)
        scalars = data["scalars"]
        self.assertIn("RAXIS", scalars)
        self.assertIn("PSI0", scalars)
        self.assertIn("QAXIS", scalars)
        self.assertIn("BETAT", scalars)
        self.assertAlmostEqual(scalars["QSURF"], 3.3252330541683550)
        self.assertAlmostEqual(scalars["RAXIS"], 6.3415044159719480)

    def test_extracts_profile_rows(self):
        data = run_extract(FIXTURE)
        prof = data["profile"]
        self.assertEqual(len(prof), 3)
        row = prof[0]
        self.assertEqual(row["NR"], 1)
        self.assertIn("PSIP", row)
        self.assertIn("PSIT", row)
        self.assertIn("PPS", row)
        self.assertIn("TTS", row)
        self.assertIn("QPS", row)
        self.assertIn("VPS", row)
        self.assertIn("RST", row)
        self.assertAlmostEqual(row["PPS"], 640000.0)
        self.assertEqual(prof[2]["NR"], 3)

    def test_rejects_incomplete_dump(self):
        with tempfile.TemporaryDirectory() as td:
            incomplete = Path(td) / "bad.dat"
            incomplete.write_text("# TASK/EQ regression dump (format v1)\nNRMAX=3\n")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(incomplete)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_rejects_profile_count_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.dat"
            # NRMAX=5 declared, only 3 profile rows -> count mismatch.
            bad.write_text(
                "# TASK/EQ regression dump (format v1)\n"
                "NRMAX=5\n"
                "NTHMAX=8\n"
                "RAXIS=  1.0E+00\n"
                "# profile columns: NR PSIP PSIT PPS TTS QPS VPS RST\n"
                "    1   0.0E+00   0.0E+00   1.0E+00   1.0E+00   1.0E+00   0.0E+00   0.0E+00\n"
                "    2   1.0E-01   1.0E-01   1.0E+00   1.0E+00   1.0E+00   1.0E-01   1.0E-01\n"
                "    3   2.0E-01   2.0E-01   1.0E+00   1.0E+00   1.0E+00   2.0E-01   2.0E-01\n"
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(bad)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
