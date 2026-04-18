"""Unit tests for extract_wr_metrics.py."""
import json
import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "extract_wr_metrics.py"
FIXTURE = HERE / "fixtures" / "sample_wr_regress.dat"


class TestExtract(unittest.TestCase):
    def setUp(self):
        out = subprocess.run(
            [sys.executable, str(SCRIPT), str(FIXTURE)],
            capture_output=True, text=True, check=True,
        )
        self.data = json.loads(out.stdout)

    def test_dimensions(self):
        self.assertEqual(self.data["NRAYMAX"], 2)
        self.assertEqual(self.data["NSTPMAX"], 10)
        self.assertEqual(self.data["NRSMAX"], 2)
        self.assertEqual(self.data["NRLMAX"], 2)
        self.assertEqual(self.data["MODELG"], 2)
        self.assertEqual(self.data["MDLWRQ"], 0)

    def test_scalars(self):
        s = self.data["scalars"]
        self.assertAlmostEqual(s["RF"], 1.6e5)
        self.assertAlmostEqual(s["RPI"], 8.5)
        self.assertAlmostEqual(s["pos_pwrmax_rs"], 0.25)
        self.assertAlmostEqual(s["pwrmax_rs"], 0.123)
        self.assertAlmostEqual(s["pwrmax_rl"], 0.0456)

    def test_rays(self):
        rays = self.data["rays"]
        self.assertEqual(len(rays), 2)
        self.assertEqual(rays[0]["NRAY"], 1)
        self.assertEqual(rays[0]["NSTP_END"], 8)
        # NEQ=8 => RAYS(0:NEQ,end) has 9 elements
        self.assertEqual(len(rays[0]["RAYS_END"]), 9)
        self.assertAlmostEqual(rays[0]["RAYS_END"][0], 4.0)
        self.assertAlmostEqual(rays[1]["pos_pwrmax_rs_nray"], 0.35)

    def test_profile_rs(self):
        p = self.data["profile_rs"]
        self.assertEqual(len(p), 2)
        self.assertEqual(p[0]["NRS"], 1)
        self.assertAlmostEqual(p[1]["pos_nrs"], 0.75)
        self.assertAlmostEqual(p[1]["pwr_nrs"], 0.030)

    def test_profile_rl(self):
        p = self.data["profile_rl"]
        self.assertEqual(len(p), 2)
        self.assertEqual(p[1]["NRL"], 2)
        self.assertAlmostEqual(p[0]["pos_nrl"], 6.5)
        self.assertAlmostEqual(p[1]["pwr_nrl"], 0.020)


if __name__ == "__main__":
    unittest.main()
