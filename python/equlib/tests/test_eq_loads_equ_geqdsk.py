"""EQ loads EQU's G-EQDSK (MODELG 5), and the pressure comes in MPa.

A characterisation of what the documents say: TASK/EQ (eqlib) reads the
file EQU writes; the magnetic axis agrees; the pressure on axis is the
state's in Pa times 1e-6, because EQU's writer gives MPa (a question for
the code's lead; when it is answered and the writer changed, this test
changes with it). EQ runs in a child process so the two libraries do not
share one.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from equlib import Equ
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

PYTHON = Path(__file__).resolve().parents[2]
EQLIB_SO = Path(os.environ.get("EQLIB_PATH", PYTHON.parent / "eq" / "libeqapi.so"))

pytestmark = [requires_lib, pytest.mark.skipif(not EQLIB_SO.exists(), reason="libeqapi.so not built")]

CHILD = """
import json, sys
sys.path.insert(0, sys.argv[1])
import eqlib
with eqlib.Eq() as eq:
    eq.set_param('MODEFR', 0)
    eq.set_param('MODELG', 5)
    eq.set_param_str('KNAMEQ', 'q.geqdsk')
    eq.run(1)
    s = eq.get_state()
    print('EQ-LOAD-RESULT ' + json.dumps({'raxis': s.scalars['raxis'], 'p0': s.ppps[0]}), flush=True)
"""


def test_eq_loads_the_file(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(1)
        st = equ.get_state()
        equ.write_geqdsk("q.geqdsk")
    env = dict(os.environ)
    env.pop("MONO_LIB_PATH", None)
    r = subprocess.run([sys.executable, "-c", CHILD, str(PYTHON)], cwd=workdir, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    # libgfortran flushes EQ's unit 6 at exit, after Python's own output:
    # take the marked line, not the last one.
    line = [l for l in r.stdout.splitlines() if l.startswith('EQ-LOAD-RESULT ')]
    assert len(line) == 1, r.stdout[-2000:]
    got = json.loads(line[0][len('EQ-LOAD-RESULT '):])
    assert abs(got["raxis"] - st.raxis) < 1e-3
    assert got["p0"] == pytest.approx(st.pressure[0] * 1e-6, rel=1e-8)
