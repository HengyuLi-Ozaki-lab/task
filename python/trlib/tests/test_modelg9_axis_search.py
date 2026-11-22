"""A TR run with ``MODELG = 9`` goes on from an axis search that did not converge (task-web-client #204).

With ``MODELG = 9`` TR has EQ solve the equilibrium again every ``NTEQIT`` steps, and inside each
solve EQ's ``find_axis`` runs Newton's method from the last axis. When the method does not converge
it hands back the best point it found, and EQ goes on from it: ``find_axis`` returns 102 only for a
point that is not finite. Measured on 0e83ad3d (``MODELG = 9``, TR's defaults varied and its three
fixtures): 23 of 60 runs
met such failures (IER 1 and 2), and 6 of them completed with finite results; with every failure
returned instead, the run
below ends with NaN (others shifted ``Q0`` by about 5 %, failed or ended the process).

The run is a child process, whose unit 6 shows the failed search (``XX EQAXIS: NEWTN ERROR``):
where the search converges (another platform or compiler), the case tests nothing and is skipped.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

_CHILD = r"""
import json, math
from trlib import Trlib
with Trlib() as tr:
    for name, value in (("MODELG", 9), ("NTEQIT", 5), ("RIPS", 1.0), ("RIPE", 1.0), ("RKAP", 1.6),
                        ("RDLT", 0.0), ("NTMAX", 20)):
        tr.set_param(name, float(value))
    tr.run(20)
    scalars = tr.get_state().scalars
    bad = sorted(k for k, v in scalars.items() if isinstance(v, float) and not math.isfinite(v))
    print("RESULT " + json.dumps({"non_finite": bad}), flush=True)
"""


@unittest.skipUnless(DEFAULT_SO.exists(), f"libtrapi.so not built at {DEFAULT_SO}")
class TestModelg9AxisSearch(unittest.TestCase):

    def test_run_goes_on_from_a_failed_axis_search(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [str(PYTHON_ROOT)] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        proc = subprocess.run([sys.executable, "-c", _CHILD], env=env, capture_output=True, text=True,
                              errors="replace", timeout=300, stdin=subprocess.DEVNULL)
        out = proc.stdout + proc.stderr
        result = [line for line in proc.stdout.splitlines() if line.startswith("RESULT ")]
        self.assertEqual(len(result), 1, (proc.returncode, out[-800:]))
        if "XX EQAXIS: NEWTN ERROR" not in out:
            self.skipTest("the axis search converged in every re-solve here")
        self.assertEqual(json.loads(result[0][7:])["non_finite"], [])
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
