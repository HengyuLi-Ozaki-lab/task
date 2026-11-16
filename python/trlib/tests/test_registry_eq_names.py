"""eq: names through tr_set_param: they reach EQ's registry inside libtrapi.so."""
import pytest
from trlib import Trlib, TrlibParamError

pytestmark = pytest.mark.forked


def test_eq_rb_is_settable_through_tr():
    with Trlib() as t:
        t.set_param("eq:RB", 2.1)
        t.set_param("eq:NSGMAX", 128)


def test_unknown_eq_name_is_refused():
    with Trlib() as t, pytest.raises(TrlibParamError):
        t.set_param("eq:NOSUCHNAME", 1.0)


def test_eq_str_name_is_refused_when_unknown():
    with Trlib() as t, pytest.raises(TrlibParamError):
        t.set_param_str("eq:NOSUCHNAME", "x")


def test_an_eq_set_prepares_tr_again():
    # Measured: after run(2) nt is 2; an accepted eq: set makes the next
    # run prepare again, so run(1) then gives nt == 1 (not 3).
    with Trlib() as t:
        t.run(2)
        assert t.get_state().nt == 2
        t.set_param("eq:RB", 2.1)
        t.run(1)
        assert t.get_state().nt == 1


def test_a_refused_eq_set_does_not_prepare_again():
    with Trlib() as t:
        t.run(2)
        with pytest.raises(TrlibParamError):
            t.set_param("eq:NOSUCHNAME", 1.0)
        t.run(1)
        assert t.get_state().nt == 3


def test_eq_str_name_is_taken():
    # eq_param_set_str: KNAMEQ is a string parameter of EQ's registry.
    with Trlib() as t:
        t.set_param_str("eq:KNAMEQ", "eqdata")


def test_an_eq_string_set_prepares_tr_again():
    # eq:KNAMEQ changes what the preparation reads: the next run prepares
    # again, so nt is the run's own count (1), not 3.
    with Trlib() as t:
        t.run(2)
        t.run(1)
        assert t.get_state().nt == 3
        t.set_param_str("eq:KNAMEQ", "eqdata")
        t.run(1)
        assert t.get_state().nt == 1


# ---- eq:NRMAX across lifecycles equals a fresh process (needs the bpsd
# spline-resize fix and eq_bpsd_put's re-initialisation, test_regrid_equals_fresh.py)

import json
import os
import subprocess
import sys
from pathlib import Path

from trlib.tests.regrid_marks import NEEDS_BPSD_FIX

PYTHON_ROOT = Path(__file__).resolve().parents[2]

PRELUDE = f"""
import json, sys
sys.path.insert(0, {str(PYTHON_ROOT)!r})
from trlib import Trlib, TrlibError

def m9(eq_nrmax=None):
    with Trlib() as t:
        t.set_param("MODELG", 9)
        if eq_nrmax is not None:
            t.set_param("eq:NRMAX", eq_nrmax)
        t.run(1)
        return t.get_state().to_dict()

def dump(d):
    print("DUMP " + json.dumps(d, sort_keys=True), flush=True)
"""


def _dump(body):
    r = subprocess.run(
        [sys.executable, "-c", PRELUDE + body], capture_output=True,
        text=True, timeout=240, env={**os.environ, "PYTHONPATH": str(PYTHON_ROOT)},
    )
    d = [l[5:] for l in r.stdout.splitlines() if l.startswith("DUMP ")]
    assert r.returncode == 0 and len(d) == 1, (r.returncode, r.stdout[-300:], r.stderr[-300:])
    return d[0]


@NEEDS_BPSD_FIX
def test_eq_nrmax_30_then_60_across_lifecycles_equals_a_fresh_60():
    seq = _dump("m9(30)\ndump(m9(60))\n")
    fresh = _dump("dump(m9(60))\n")
    assert seq == fresh


@NEEDS_BPSD_FIX
def test_eq_rb_2_then_the_defaults_in_two_lifecycles_equals_a_fresh_defaults_run():
    # eq:RB 2.0 changes EQ's NRPMAX (29 instead of 50) while EQ's NRMAX stays
    # the same: the case only the bpsd spline-resize fix covers.
    seq = _dump(
        'with Trlib() as t:\n'
        '    t.set_param("MODELG", 9)\n'
        '    t.set_param("eq:RB", 2.0)\n'
        '    t.run(1)\n'
        'dump(m9())\n')
    fresh = _dump("dump(m9())\n")
    assert seq == fresh
