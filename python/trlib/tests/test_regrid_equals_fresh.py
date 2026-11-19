"""A change of grid inside one process gives what a fresh process gives.

Preparing TR on another grid than an earlier preparation of the same process
(a new lifecycle, or a new NRMAX on one handle) wrote out of bounds: NaN, an
abort or SIGSEGV. Two things kept the first grid: bpsd's splines in
``bpsd_get_equ1D`` / ``bpsd_get_metric1D`` (fixed in bpsd, k-yoshimi/bpsd#7) and ``eq_bpsd_put``'s arrays, sized once (``eq/eqbpsd.f90``).

These tests need BOTH fixes. Those that change TR's NRMAX are skipped (TR_MESH_GUARD) while tr_run holds one
mesh per process; the one that changes only EQ's grid is gated on TRLIB_BPSD_REGRID_FIX=1 (NEEDS_BPSD_FIX). Each case runs two child processes: one runs the
sequence, the other runs only its final configuration fresh; the final
``TrState.to_dict()`` of both is dumped as JSON (``repr`` floats) and must be
equal exactly. A child that crashes gives no dump and fails the test. The
one-handle case compares two first sizes instead (see its comment).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from trlib.tests.regrid_marks import NEEDS_BPSD_FIX, TR_MESH_GUARD

PYTHON_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SO = PYTHON_ROOT.parent / "tr" / "libtrapi.so"

pytestmark = pytest.mark.skipif(not SO.exists(), reason="libtrapi.so not built")

PRELUDE = f"""
import json, sys
sys.path.insert(0, {str(PYTHON_ROOT)!r})
from trlib import Trlib, TrlibError
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
        return t.get_state().to_dict()

def modelg9():
    with Trlib() as t:
        t.set_param("MODELG", 9)
        t.run(1)
        return t.get_state().to_dict()

def one_handle(first, second):
    with Trlib() as t:
        base.apply(t)
        t.set_param("NTMAX", 2)
        t.set_param("NRMAX", first)
        t.run(2)
        t.set_param("NRMAX", second)
        t.run(2)
        return t.get_state().to_dict()

def attempt(fn, *a):
    try:
        return fn(*a)
    except TrlibError:
        return None

def dump(d):
    print("DUMP " + json.dumps(d, sort_keys=True), flush=True)
"""


def _run(body):
    r = subprocess.run(
        [sys.executable, "-c", PRELUDE + body], cwd=str(FIXTURES),
        capture_output=True, text=True, timeout=240,
        env={**os.environ, "PYTHONPATH": str(PYTHON_ROOT)},
    )
    dumps = [l[5:] for l in r.stdout.splitlines() if l.startswith("DUMP ")]
    assert r.returncode == 0 and len(dumps) == 1, (r.returncode, r.stdout[-300:], r.stderr[-300:])
    return dumps[0]


def _same(sequence, fresh):
    a, b = _run(sequence), _run(fresh)
    assert a == b


@TR_MESH_GUARD
def test_tst2_at_10_then_tst2_at_the_default():
    _same("attempt(tst2, 10)\ndump(tst2())\n", "dump(tst2())\n")


@TR_MESH_GUARD
def test_tst2_at_40_then_50():
    _same("attempt(tst2, 40)\ndump(tst2(50))\n", "dump(tst2(50))\n")


@TR_MESH_GUARD
def test_tst2_at_10_then_modelg9():
    _same("attempt(tst2, 10)\ndump(modelg9())\n", "dump(modelg9())\n")


@NEEDS_BPSD_FIX
def test_modelg9_then_tst2_at_the_defaults():
    _same("attempt(modelg9)\ndump(tst2())\n", "dump(tst2())\n")


@TR_MESH_GUARD
def test_one_handle_10_then_50_does_not_depend_on_the_first_size():
    # What this shows: after a mesh change on one handle the result does not
    # depend on the earlier mesh, and the process survives. Measured: 10 -> 50,
    # 30 -> 50, 40 -> 50, 49 -> 50, 60 -> 50 and 10 -> 40 -> 50 all give WPT
    # 1.7172660285320113e-06.
    # What it does NOT show: it is not equal to a fresh 50 (1.7369279889563615e-06),
    # because of an older carry-over of TR's state across a re-preparation.
    # Do not compare it with 50 -> 50 (1.7172652391145013e-06): that does not
    # reallocate TRCOMM.
    a = _run("dump(one_handle(10, 50))\n")
    b = _run("dump(one_handle(40, 50))\n")
    assert a == b
    assert "NaN" not in a


@TR_MESH_GUARD
def test_a_failed_first_preparation_then_50():
    # NRMAX 10, MDLIMP 2, PNC 10: negative DILUTE, fails after the grid went
    # into bpsd.
    _same('attempt(tst2, 10, (("MDLIMP", 2), ("PNC", 10)))\ndump(tst2(50))\n',
          "dump(tst2(50))\n")
