import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "extract_wrx_metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "sample_wrx_regress.dat"


def run_extract(dump_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(dump_path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


class ExtractWrxMetricsTest(unittest.TestCase):

    def test_extracts_top_level_ints(self):
        d = run_extract(FIXTURE)
        self.assertEqual(d["NRAYMAX"], 2)
        self.assertEqual(d["NSTPMAX"], 10)
        self.assertEqual(d["NRSMAX"], 3)
        self.assertEqual(d["NRLMAX"], 3)
        self.assertEqual(d["NSAMAX_WR"], 2)
        self.assertEqual(d["NSMAX"], 2)
        self.assertEqual(d["MODELG"], 2)
        self.assertEqual(d["MDLWRQ"], 1)

    def test_extracts_scalar(self):
        d = run_extract(FIXTURE)
        self.assertAlmostEqual(d["scalars"]["pwr_tot"], 1.0)

    def test_extracts_1d_arrays(self):
        d = run_extract(FIXTURE)
        # integer array
        self.assertEqual(d["arrays"]["NSTPMAX_NRAY"], [8, 9])
        # float arrays
        self.assertEqual(len(d["arrays"]["pwr_nray"]), 2)
        self.assertAlmostEqual(d["arrays"]["pwr_nray"][0], 0.6)
        self.assertAlmostEqual(d["arrays"]["pwr_nray"][1], 0.4)
        self.assertEqual(len(d["arrays"]["pwr_nsa"]), 2)
        self.assertAlmostEqual(d["arrays"]["pwr_nsa"][0], 0.7)
        self.assertEqual(len(d["arrays"]["pos_nrs"]), 3)
        self.assertEqual(len(d["arrays"]["pos_nrl"]), 3)

    def test_extracts_2d_arrays(self):
        d = run_extract(FIXTURE)
        self.assertEqual(d["arrays2"]["pwr_nsa_nray"],
                         [[0.3, 0.4], [0.2, 0.1]])
        self.assertEqual(d["arrays2"]["pwr_nrs_nsa"],
                         [[0.01, 0.02], [0.03, 0.04], [0.05, 0.06]])
        self.assertEqual(d["arrays2"]["pwr_nrl_nsa"],
                         [[0.011, 0.021], [0.031, 0.041], [0.051, 0.061]])
        self.assertEqual(len(d["arrays2"]["pos_pwrmax_rs_nsa_nray"]), 2)
        self.assertEqual(len(d["arrays2"]["pwrmax_rs_nsa_nray"]), 2)
        self.assertEqual(len(d["arrays2"]["pos_pwrmax_rl_nsa_nray"]), 2)
        self.assertEqual(len(d["arrays2"]["pwrmax_rl_nsa_nray"]), 2)

    def test_handles_fortran_subnormal_no_e(self):
        """Fortran 1PE format drops the 'E' for some subnormal values
        (e.g. '4.8952117329314484-310'). Extractor must reconstruct the
        exponent rather than crash."""
        with tempfile.TemporaryDirectory() as td:
            dump = Path(td) / "subn.dat"
            dump.write_text(
                "# TASK/WRX regression dump (format v1)\n"
                "NRAYMAX=1\nNSTPMAX=10\nNRSMAX=1\nNRLMAX=1\n"
                "NSAMAX_WR=1\nNSMAX=1\nMODELG=2\nMDLWRQ=1\n"
                "pwr_tot=  4.8952117329314484-310\n"
                "# array NSTPMAX_NRAY n=1\n5\n"
                "# array pwr_nray n=1\n  4.8952117329314484-310\n"
                "# array pwr_nsa n=1\n  0.0000000000000000E+00\n"
                "# array pos_nrs n=1\n  0.0000000000000000E+00\n"
                "# array pos_nrl n=1\n  0.0000000000000000E+00\n"
                "# array2 pwr_nsa_nray rows=1 cols=1\n"
                "  4.8952117329314484-310 \n"
            )
            r = subprocess.run(
                [sys.executable, str(SCRIPT), str(dump)],
                capture_output=True, text=True,
            )
            self.assertEqual(r.returncode, 0,
                             f"stdout={r.stdout!r} stderr={r.stderr!r}")
            d = json.loads(r.stdout)
            # subnormal value reconstructed
            self.assertLess(d["scalars"]["pwr_tot"], 1e-300)
            self.assertGreater(d["scalars"]["pwr_tot"], 0.0)
            self.assertLess(d["arrays"]["pwr_nray"][0], 1e-300)
            self.assertLess(d["arrays2"]["pwr_nsa_nray"][0][0], 1e-300)

    def test_rejects_incomplete_dump(self):
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.dat"
            bad.write_text("# TASK/WRX regression dump (format v1)\nMODELG=2\n")
            r = subprocess.run(
                [sys.executable, str(SCRIPT), str(bad)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
