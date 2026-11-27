"""NTEQIT, TPRST and TR's NRMAX through the registry (tr/tr_param_registry.f90)."""
import ctypes
import os
import subprocess
import sys
from pathlib import Path

import pytest
from trlib import Trlib, TrlibParamError

pytestmark = pytest.mark.forked

NRMAX_MIN = 3   # measured: NRMAX 1 and 2 abort the run (Fortran bounds check), 3..10 run with finite WPT and Q0


def _lib():
    return Trlib()


def test_nteqit_is_settable():
    with _lib() as t:
        t.set_param("NTEQIT", 50)


def test_nteqit_negative_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("NTEQIT", -1)


def test_tprst_is_settable():
    with _lib() as t:
        t.set_param("TPRST", 0.5)


def test_tprst_zero_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("TPRST", 0.0)


def test_nrmax_set_before_the_first_run_gives_that_mesh():
    with _lib() as t:
        t.set_param("NRMAX", 30)
        t.run(1)
        assert t.get_state().nrmax == 30


def test_nrmax_above_the_state_bound_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("NRMAX", 501)   # TR_MAX_NRMAX = 500 (tr/tr_api.h)


def test_nrmax_at_the_state_bound_is_taken():
    with _lib() as t:
        t.set_param("NRMAX", 500)


def test_nrmax_below_the_minimum_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("NRMAX", NRMAX_MIN - 1)


def test_nrmax_at_the_minimum_is_taken():
    with _lib() as t:
        t.set_param("NRMAX", NRMAX_MIN)


# ---- the value reaches the module variable (not only "the name is known")

def _int_var(t, symbol):
    return ctypes.c_int.in_dll(t._lib, symbol).value


def _real_var(t, symbol):
    return ctypes.c_double.in_dll(t._lib, symbol).value


def test_nteqit_reaches_the_module_variable():
    with _lib() as t:
        t.set_param("NTEQIT", 37)
        assert _int_var(t, "__trcomm_ctrl_MOD_nteqit") == 37


def test_tprst_reaches_the_module_variable():
    with _lib() as t:
        t.set_param("TPRST", 0.375)
        assert _real_var(t, "__trcomm_param_MOD_tprst") == 0.375


# ---- NRMAX through a child process, one mesh per process (no grid change:
# these need no spline-resize fix in bpsd)

PYTHON_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

PRELUDE = f"""
import sys
sys.path.insert(0, {str(PYTHON_ROOT)!r})
from trlib import Trlib, TrlibRunError
from trlib.tests.fixtures import tr_tst2_params as base

def tst2(nrmax=None, extra=()):
    with Trlib() as t:
        base.apply(t)
        t.set_param("NTMAX", 2)
        if nrmax is not None:
            t.set_param("NRMAX", nrmax)
        for k, v in extra:
            t.set_param(k, v)
        t.run(2)
        return t.get_state()

def modelg9():
    with Trlib() as t:
        t.set_param("MODELG", 9)
        t.run(1)
        return t.get_state()

def outcome(fn, *a, **k):
    try:
        st = fn(*a, **k)
    except TrlibRunError:
        return "RUNERR"
    return "RAN nrmax=%d" % st.nrmax
"""


def _child(body):
    r = subprocess.run(
        [sys.executable, "-c", PRELUDE + body],
        cwd=str(FIXTURES), capture_output=True, text=True, timeout=180,
        env={**os.environ, "PYTHONPATH": str(PYTHON_ROOT)},
    )
    lines = [l for l in r.stdout.splitlines() if l.startswith("OUT ")]
    return r.returncode, [l[4:] for l in lines], r.stdout[-400:] + r.stderr[-400:]


def test_a_value_set_before_the_first_preparation_is_free():
    rc, out, log = _child('print("OUT", outcome(tst2, 10), flush=True)\n')
    assert rc == 0 and out == ["RAN nrmax=10"], log


def test_tst2_at_10_then_the_same_grid_runs():
    rc, out, log = _child(
        'print("OUT", outcome(tst2, 10), flush=True)\n'
        'print("OUT", outcome(tst2, 10), flush=True)\n')
    assert rc == 0 and out == ["RAN nrmax=10", "RAN nrmax=10"], log


def test_modelg9_twice_at_the_defaults_runs():
    rc, out, log = _child(
        'print("OUT", outcome(modelg9), flush=True)\n'
        'print("OUT", outcome(modelg9), flush=True)\n')
    assert rc == 0 and out == ["RAN nrmax=50", "RAN nrmax=50"], log
