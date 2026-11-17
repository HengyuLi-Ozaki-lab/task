"""``TRSAWT`` (``tr/trcalc.f90``) prints its profiles up to two points past the mixing radius ``IZEROX``.

``IZEROX`` runs up to ``NRMAX`` when q is below 1 out to the edge, so the print read ``RM``, ``QP``, ``BP`` and
``QONE`` past the end of the mesh: a bounds-checking build stopped the process ("Fortran runtime error"), others
read beyond the arrays. ``MDLST`` was settable before; ``TPRST`` below DT/2 (now settable) fires the sawtooth every
step, and a small ``NRMAX`` (now settable) reaches the edge sooner. Each case runs in a child process, since the
overrun ended the process before the fix. A build without bounds checks (CI's -O3) read past the arrays and went on,
so the test also reads the print: no line may name a point beyond the mesh.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
REPO = HERE.parents[3]
DEFAULT_SO = REPO / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(
    not DEFAULT_SO.exists(),
    reason=f"libtrapi.so not built at {DEFAULT_SO}; run `make -C tr libtrapi.so`",
)

# PLATO's shape (R 0.7 m, a 0.18 m, B 0.3 T, hydrogen) at 150 kA: q below 1 out to the edge, so the mixing radius
# is the last mesh point (measured before the fix: "Index '51' of dimension 1 of array 'rm' above upper bound of 50",
# and '4' above 3 with NRMAX 3).
CASE = {"RR": 0.7, "RA": 0.18, "RKAP": 1.9, "RDLT": 0.4, "BB": 0.3, "RIPS": 0.15, "RIPE": 0.15, "NSMAX": 2,
        "PA[2]": 1.0, "PZ[2]": 1.0, "PN[1]": 0.1, "PN[2]": 0.1, "PNS[1]": 0.01, "PNS[2]": 0.01,
        "PT[1]": 0.13, "PT[2]": 0.035, "PTS[1]": 0.01, "PTS[2]": 0.01, "MDLKAI": 31, "CK0": 12.0, "CK1": 12.0,
        "MDLNB": 0, "DT": 1.0e-4, "MDLST": 1, "TPRST": 1.0e-6}

_SCRIPT = """
import json, math, sys
from trlib import Trlib
with Trlib() as tr:
    for name, value in json.loads(sys.argv[1]).items():
        tr.set_param(name, float(value))
    tr.run(5)
    s = tr.get_state()
    print("STATE", s.nrmax, all(math.isfinite(x) for row in s.RT + s.RN for x in row))
"""


@pytest.mark.parametrize("nrmax", [3, 4, 50])
def test_a_sawtooth_every_step_runs_on_any_mesh(nrmax):
    env = {**os.environ, "PYTHONPATH": str(PYTHON_ROOT)}
    r = subprocess.run([sys.executable, "-c", _SCRIPT, json.dumps({**CASE, "NRMAX": nrmax})], capture_output=True,
                       text=True, timeout=120, env=env)
    assert r.returncode == 0, (r.returncode, r.stderr[-600:])
    assert f"STATE {nrmax} True" in r.stdout, r.stdout[-600:]
    printed = [int(line.split()[1]) for line in r.stdout.splitlines() if line.startswith("NR,R,Q,B,Q,S=")]
    assert printed and max(printed) <= nrmax, printed[-5:]
