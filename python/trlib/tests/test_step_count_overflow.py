"""``tr_run`` and ``tr_continue`` refuse a step count that takes the step counter NT past its largest value; a refusal
before this lifecycle prepared anything records time 0.

``NTMAX = NT + nsteps`` overflowed a default integer: ``tr_init(); tr_run(1); tr_continue(2147483647)`` made NTMAX
negative, the loop left at once and the call reported success without a step. ``tr_continue`` now refuses
(``TR_ERR_INVALID`` with a ``REFUSED`` record) before it takes in a pending control set or changes NTMAX; ``tr_run``,
which had the same sum, returns ``TR_ERR_INVALID`` with an ``XX`` line. Only the refusals can be tested: a count that
fits would run for two billion steps.

``tr_init`` resets NT but not T, so ``tr_init(); tr_run(10); tr_finalize(); tr_init(); tr_continue(1)`` recorded the
previous lifecycle's T in its REFUSED record. A refusal made before this lifecycle attempted a preparation records
time 0.

Every case runs in a child process (it reads Fortran's unit 6).
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


# (steps already run, count): the sum NT + count is past INT_MAX in each; INT_MAX - 1 after one step would be accepted
# (the sum is INT_MAX) and run for two billion steps, so the accepted side of the bound is not run.
@pytest.mark.parametrize("done,count", [(1, INT_MAX), (10, INT_MAX - 5)])
def test_continue_refuses_a_count_that_overflows_nt(done, count):
    p = _child('''
        t = Trlib()
        t.run(%d)
        print("RC", t._lib.tr_continue(%d))
        f = t.last_error()
        print("KIND", f.kind, "|", f.detail)
        print("NT", t.get_state().nt)
    ''' % (done, count))
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "RC 1" in p.stdout, p.stdout[-800:]
    assert "KIND REFUSED |" in p.stdout and "step count" in p.stdout, p.stdout[-800:]
    assert "XX tr_continue: " in p.stdout
    assert "NT %d" % done in p.stdout        # nothing ran


def test_a_refused_overflowing_continue_leaves_the_pending_controls_pending():
    # tr_run prepares again after any set since its preparation; it would continue (NT 10) if the refused
    # tr_continue had taken the set in.
    p = _child('''
        t = Trlib()
        t.run(5)
        t.set_param("PECTOT", 1.0)
        print("RC", t._lib.tr_continue(%d))
        t.run(5)
        print("NT", t.get_state().nt)
    ''' % INT_MAX)
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "RC 1" in p.stdout and "NT 5" in p.stdout, p.stdout[-800:]


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


def test_a_refusal_before_this_lifecycle_prepared_anything_records_time_zero():
    p = _child('''
        with Trlib() as t:
            t.run(10)
            print("T1", t.get_scalar("T") > 0.0)
        t = Trlib()
        print("RC", t._lib.tr_continue(1))
        f = t.last_error()
        print("REC", f.kind, f.nt, f.time)
    ''')
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "RC 1" in p.stdout, p.stdout[-800:]
    assert "REC REFUSED 0 0.0" in p.stdout, p.stdout[-800:]
    assert "T1 True" in p.stdout          # the first lifecycle did advance T


def test_a_refusal_after_a_preparation_records_the_current_time():
    p = _child('''
        t = Trlib()
        t.run(10)
        print("RC", t._lib.tr_continue(-1))
        f = t.last_error()
        print("REC", f.kind, f.nt, abs(f.time - t.get_scalar("T")) < 1e-4, f.time > 0.0)
    ''')
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "REC REFUSED 10 True True" in p.stdout, p.stdout[-800:]
