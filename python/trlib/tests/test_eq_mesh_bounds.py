"""EQ's mesh sizes set through ``eq:`` names are held to EQ's array maxima (``eq_mesh_violation``, tr/tr_api.f90).

Before the check, ``tr_init(); tr_set_param("MODELG", 9); tr_set_param("eq:NSGMAX", 129); tr_run(0)`` succeeded in
both setters, ``tr_validate`` said nothing, and the preparation wrote ``SIGM(129)`` past its 128 elements
(eq/eqcalc.f90:63): a Fortran run-time error ending the process. The bounds are those of ``eq_validate``
(eq/eq_api.f90) taken from EQ's own parameters (eqcom0_mod).

Every case that can end the process runs in ``subprocess.run`` with a timeout.
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

# name -> EQ's compile-time maximum (eq/eqcom0_mod.f90:20-30)
BOUNDS = {
    "NSGMAX": 128, "NTGMAX": 128, "NUGMAX": 128, "NRGMAX": 513, "NZGMAX": 513,
    "NPSMAX": 513, "NRVMAX": 1001, "NRMAX": 1001, "NTHMAX": 2049, "NSUMAX": 1343,
}


def _child(body: str) -> subprocess.CompletedProcess:
    code = (
        "import sys\nsys.path.insert(0, %r)\n" % str(PYTHON_ROOT)
        + "from trlib import Trlib, TrlibError, TrlibParamError\n"
        + textwrap.dedent(body)
    )
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300)


@pytest.mark.parametrize("name", sorted(BOUNDS))
def test_modelg9_run_refuses_an_eq_mesh_size_over_its_maximum(name):
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9)
        t.set_param("eq:%s", %d)
        print("VALIDATE", [d.param for d in t.validate()])
        try:
            t.run(0); print("RUN 0")
        except TrlibParamError:
            print("RUN refused")
        try:
            t.set_param("DT", 0.01); print("USABLE")
        except Exception:
            print("NOT USABLE")
    ''' % (name, BOUNDS[name] + 1))
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "RUN refused" in p.stdout, p.stdout[-800:]
    assert "VALIDATE ['eq:%s']" % name in p.stdout, p.stdout[-800:]
    assert "XX tr_run: eq:%s" % name in p.stdout and "%d" % BOUNDS[name] in p.stdout, p.stdout[-800:]
    assert "USABLE" in p.stdout


@pytest.mark.parametrize("name", ["NSGMAX", "NTGMAX"])
def test_modelg9_run_accepts_an_eq_mesh_size_at_its_maximum(name):
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9)
        t.set_param("eq:%s", %d)
        print("VALIDATE", [d.param for d in t.validate()])
        t.run(1)
        print("NT", t.get_state().nt)
    ''' % (name, BOUNDS[name]))
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "VALIDATE []" in p.stdout and "NT 1" in p.stdout, p.stdout[-800:]


@pytest.mark.parametrize("name", ["NSGMAX", "NRGMAX", "NRVMAX"])
def test_a_file_load_modelg_holds_the_seven_grid_sizes_to_their_maximum(name):
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 3)
        t.set_param("eq:%s", %d)
        print("VALIDATE", sorted(d.param for d in t.validate()))
    ''' % (name, BOUNDS[name] + 1))
    assert p.returncode == 0, p.stderr[-1200:]
    assert "eq:%s" % name in p.stdout, p.stdout[-800:]


def test_a_file_load_modelg_leaves_the_sizes_that_tr_overwrites_alone():
    # tr_set_metric sets EQ's NRMAX, NTHMAX, NSUMAX under MODELG 3/5/8: a value set through eq: is never used.
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 3)
        t.set_param("eq:NRMAX", 5000)
        print("VALIDATE", sorted(d.param for d in t.validate()))
    ''')
    assert p.returncode == 0, p.stderr[-1200:]
    assert "eq:NRMAX" not in p.stdout, p.stdout[-800:]


def test_a_modelg_that_does_not_use_eq_s_grid_checks_nothing():
    p = _child('''
        t = Trlib()
        t.set_param("eq:NSGMAX", 129)
        print("VALIDATE", [d.param for d in t.validate()])
        t.run(1)
        print("NT", t.get_state().nt)
    ''')
    assert p.returncode == 0, p.stdout[-600:] + p.stderr[-1200:]
    assert "VALIDATE []" in p.stdout and "NT 1" in p.stdout, p.stdout[-800:]
