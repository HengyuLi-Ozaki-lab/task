"""``tr_run`` refuses a step count that takes the step counter NT past its largest value.

``NTMAX = NT + ntmax_in`` overflowed a default integer: after ``tr_init(); tr_run(1)``, ``tr_run(2147483647)`` made
NTMAX negative and the loop left at once (a pre-existing overflow, fixed in this PR). ``tr_run`` now returns
``TR_ERR_INVALID`` with an ``XX tr_run`` line on unit 6, before it changes NTMAX. Only the refusal can be tested: a
count that fits would run for two billion steps. Every case runs in a child process (it reads Fortran's unit 6).
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]
DEFAULT_SO = HERE.parents[3] / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(not DEFAULT_SO.exists(), reason="libtrapi.so not built")

INT_MAX = 2147483647


def _child(body: str) -> subprocess.CompletedProcess:
    code = (
        "import sys\nsys.path.insert(0, %r)\n" % str(PYTHON_ROOT)
        + "from trlib import Trlib, TrlibParamError, TrlibRunError\n"
        + textwrap.dedent(body)
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)


def test_run_refuses_a_count_that_overflows_nt():
    p = _child('''
        t = Trlib()
        t.run(1)
        print("RC", t._lib.tr_run(%d))
        print("NT", t.get_state().nt)
    ''' % INT_MAX)
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "RC 1" in p.stdout, p.stdout[-800:]
    assert "XX tr_run: " in p.stdout and "step counter" in p.stdout, p.stdout[-800:]
    assert "NT 1" in p.stdout


def test_run_after_a_refused_overflow_still_works():
    p = _child('''
        t = Trlib()
        t.run(1)
        t._lib.tr_run(%d)
        t.run(3)
        print("NT", t.get_state().nt)
    ''' % INT_MAX)
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "NT 4" in p.stdout, p.stdout[-800:]
