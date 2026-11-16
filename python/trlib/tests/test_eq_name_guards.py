"""``eq:`` names that tr_set_param refuses.

1. One process, one EQ grid. bpsd sizes its splines at the first get and keeps that size (k-yoshimi/bpsd#7), so an
   ``eq:`` set after the process's first preparation attempt (``tr_run``'s tr_prep, failed or not) could change
   EQ's grid and write out of bounds: EQ_FAILED 103 from a spline written past its end (measured: eq:NRMAX 30
   then 60 across lifecycles, eq:RB 2.0 then 1.2 on one handle, on a bpsd without the fix). ``tr_set_param`` and
   ``tr_set_param_str`` refuse every ``eq:`` name from then on, across ``tr_finalize`` and ``tr_init``, with one
   line on unit 6. The guard comes off together with the NRMAX guard of 61ff3cdf.
2. Names that do nothing. Under MODELG 9 ``eq_bpsd_get`` overwrites EQ's RR, RA, RKAP, RDLT, BB and RIP from TR's
   device (measured: the same state hash as no set); under MODELG 3/5/8 ``tr_set_metric`` sets EQ's NRMAX, NTHMAX
   and NSUMAX and TR passes its own KNAMEQ to ``eq_load``. They are refused at set time and the message names TR's
   own parameter.

Each case runs in ``subprocess.run`` (a child process is a process of its own, as a task-web job is).
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


def _child(body: str) -> subprocess.CompletedProcess:
    code = (
        "import sys\nsys.path.insert(0, %r)\n" % str(PYTHON_ROOT)
        + "from trlib import Trlib, TrlibError, TrlibParamError\n"
        + textwrap.dedent(body)
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)


def _lines(p):
    return [l for l in p.stdout.splitlines() if l.startswith("XX tr_set_param")]


# ---- item 1 -----------------------------------------------------------------------------------

def test_an_eq_set_after_a_preparation_on_one_handle_is_refused():
    p = _child('''
        t = Trlib()
        t.run(1)
        try:
            t.set_param("eq:RB", 1.2); print("RC 0")
        except TrlibParamError:
            print("RC refused")
        t.run(1)
        print("NT", t.get_state().nt)
    ''')
    assert p.returncode == 0, p.stderr[-1500:]
    assert "RC refused" in p.stdout, p.stdout[-800:]
    assert "NT 2" in p.stdout      # no re-preparation: the refused set changed nothing
    ls = _lines(p)
    assert len(ls) == 1 and "bpsd#7" in ls[0] and "before" in ls[0], p.stdout[-800:]


def test_an_eq_set_in_a_second_lifecycle_is_refused():
    p = _child('''
        with Trlib() as t:
            t.set_param("eq:NRMAX", 30)
            t.run(1)
        with Trlib() as t:
            try:
                t.set_param("eq:NRMAX", 60); print("RC 0")
            except TrlibParamError:
                print("RC refused")
    ''')
    assert p.returncode == 0, p.stderr[-1500:]
    assert "RC refused" in p.stdout, p.stdout[-800:]


def test_an_eq_string_set_after_a_preparation_is_refused():
    p = _child('''
        t = Trlib()
        t.run(1)
        try:
            t.set_param_str("eq:KNAMEQ", "eqdata"); print("RC 0")
        except TrlibParamError:
            print("RC refused")
    ''')
    assert p.returncode == 0, p.stderr[-1500:]
    assert "RC refused" in p.stdout, p.stdout[-800:]


def test_a_failed_first_preparation_also_closes_the_eq_names():
    p = _child('''
        t = Trlib()
        t.set_param("PA[2]", 40.0)       # TR_TABLE places no species of mass 40: tr_prep fails
        try:
            t.run(1); print("RUN 0")
        except TrlibError:
            print("RUN failed")
        try:
            t.set_param("eq:RB", 2.1); print("RC 0")
        except TrlibParamError:
            print("RC refused")
    ''')
    assert p.returncode == 0, p.stderr[-1500:]
    assert "RUN failed" in p.stdout and "RC refused" in p.stdout, p.stdout[-800:]


def test_eq_names_are_taken_before_the_first_run_and_tr_names_after():
    p = _child('''
        t = Trlib()
        t.set_param("eq:RB", 2.1); t.set_param("eq:NSGMAX", 128)
        t.run(1)
        t.set_param("DT", 0.01)          # a TR name is not affected
        t.run(1)
        print("OK", t.get_state().nt)
    ''')
    assert p.returncode == 0, p.stderr[-1500:]
    assert "OK " in p.stdout, p.stdout[-800:]
    assert not _lines(p)


# ---- item 2 -----------------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["RR", "RA", "RKAP", "RDLT", "BB", "RIP"])
def test_an_eq_name_that_tr_overrides_is_refused_with_tr_s_name(name):
    p = _child('''
        t = Trlib()
        try:
            t.set_param("eq:%s", 1.5); print("RC 0")
        except TrlibParamError:
            print("RC refused")
    ''' % name)
    assert p.returncode == 0, p.stderr[-1500:]
    assert "RC refused" in p.stdout, p.stdout[-800:]
    ls = _lines(p)
    assert len(ls) == 1 and ("set %s (TR's)" % name) in ls[0], p.stdout[-800:]


def test_eq_knameq_is_refused_as_a_string_and_names_tr_s_knameq():
    p = _child('''
        t = Trlib()
        try:
            t.set_param_str("eq:KNAMEQ", "eqdata"); print("RC 0")
        except TrlibParamError:
            print("RC refused")
    ''')
    assert p.returncode == 0, p.stderr[-1500:]
    assert "RC refused" in p.stdout, p.stdout[-800:]
    ls = _lines(p)
    assert len(ls) == 1 and "set KNAMEQ (TR's)" in ls[0], p.stdout[-800:]


def test_eq_knameq_is_refused_as_a_number_too():
    p = _child('''
        t = Trlib()
        try:
            t.set_param("eq:KNAMEQ", 1.0); print("RC 0")
        except TrlibParamError:
            print("RC refused")
    ''')
    assert p.returncode == 0, p.stderr[-1500:]
    assert "RC refused" in p.stdout, p.stdout[-800:]


def test_the_refused_names_are_case_insensitive():
    p = _child('''
        t = Trlib()
        try:
            t.set_param("eq:rr", 6.0); print("RC 0")
        except TrlibParamError:
            print("RC refused")
    ''')
    assert "RC refused" in p.stdout, (p.stdout[-800:], p.stderr[-800:])
