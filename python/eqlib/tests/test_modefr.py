"""MODEFR, FROPEN's MODEP for every load, takes 0 only (task-web-client #202).

With ``MODEFR = 1`` FROPEN (``lib/libfio.f90``) reads the file name from standard input (unit 5),
which for the stdio MCP servers is the protocol's channel: a load ate the client's next message as a
file name and then failed naming ``KNAMEQ``, the file that was there. Other values are no mode of
FROPEN (its ``IERR`` 3). ``set_param`` refuses both, through EQ's registry, so through every caller
of it too (TR's ``eq:`` names, ``python/trlib/tests/test_eq_modefr.py``; TOT's ``eq:`` names); after a
refusal the load reads ``KNAMEQ`` and leaves standard input alone (the child process below).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import eqlib

_HERE = Path(__file__).resolve()
_DEFAULT_SO = _HERE.parents[3] / "eq" / "libeqapi.so"
_TST2 = _HERE.parent / "fixtures" / "eqdata.TST-2"

pytestmark = pytest.mark.skipif(
    not Path(os.environ.get("EQLIB_PATH") or _DEFAULT_SO).exists(),
    reason="libeqapi.so not built",
)


@pytest.mark.parametrize("value", [1.0, 2.0, -1.0, 4.0, 1.5])
def test_modefr_other_than_0_is_refused(value):
    with eqlib.Eq() as e:
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.set_param("MODEFR", value)


@pytest.mark.parametrize("value", [0.0, -0.0])
def test_modefr_0_is_taken(value):
    with eqlib.Eq() as e:
        e.set_param("MODEFR", value)


# A child process: its standard input carries a line, as a stdio MCP server's does.
_CHILD = r"""
import sys
import eqlib
with eqlib.Eq() as e:
    e.set_param("MODELG", 3)
    e.set_param_str("KNAMEQ", "eqdata.TST-2")
    try:
        e.set_param("MODEFR", 1)
        print("SET", flush=True)
    except eqlib.EqlibInvalidParamError:
        print("SET REFUSED", flush=True)
    e.run(1)
    print("LOADED", flush=True)
print("STDIN", repr(sys.stdin.read()), flush=True)
"""


def test_a_refused_modefr_leaves_standard_input_to_its_owner(tmp_path):
    # With MODEFR = 1 taken, the load read the line as a file name, failed, and left nothing.
    shutil.copy(_TST2, tmp_path / "eqdata.TST-2")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_HERE.parents[2])] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    line = '{"jsonrpc":"2.0","id":7,"method":"tools/list"}\n'
    proc = subprocess.run([sys.executable, "-c", _CHILD], cwd=tmp_path, env=env, input=line,
                          capture_output=True, text=True, errors="replace", timeout=60)
    lines = [x for x in proc.stdout.splitlines() if x.startswith(("SET", "LOADED", "STDIN"))]
    assert lines == ["SET REFUSED", "LOADED", f"STDIN {line!r}"], (proc.returncode, proc.stdout[-500:],
                                                                   proc.stderr[-500:])
