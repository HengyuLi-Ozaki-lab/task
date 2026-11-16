"""run(1), the load of an equilibrium file, reports a load that failed.

eq_save writes only after a run that succeeded, so the load's return code has
to be true: EQ_READ used to go on into EQCALQ after EQDSKR had failed
(MODELG=5, a missing file) and hand back EQCALQ's code, and left its code
unassigned for a MODELG that is no file format.

Against the library as it was: the MODELG=5 case does not fail, it ends its
process at a STOP inside EQCALQ (under --forked the session then stops with an
INTERNALERROR); the MODELG=2 case depends on what the unassigned variable
happened to hold, and so pins the behaviour more than it shows the change.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import eqlib

_HERE = Path(__file__).resolve()
_DEFAULT_SO = _HERE.parents[3] / "eq" / "libeqapi.so"

pytestmark = pytest.mark.skipif(
    not Path(os.environ.get("EQLIB_PATH") or _DEFAULT_SO).exists(),
    reason="libeqapi.so not built",
)


@pytest.fixture(autouse=True)
def _in_tmp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.mark.parametrize("modelg", [3, 5])
def test_load_of_a_missing_file_is_an_error(modelg):
    with eqlib.Eq() as e:
        e.set_param("MODELG", modelg)
        e.set_param_str("KNAMEQ", "no_such_file")
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)


def test_load_with_a_modelg_that_is_no_file_format_is_an_error():
    with eqlib.Eq() as e:
        e.set_param("MODELG", 2)
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)


# --- task-web-client #187: a load with MDLEQF >= 10 holds the file's axis to the box ---------

_FIXTURES = _HERE.parent / "fixtures"


def _load_tst2(**params):
    """Load the TST-2 fixture (MODELG=3) with ``params``; return the state."""
    import shutil
    shutil.copy(_FIXTURES / "eqdata.TST-2", "eqdata.TST-2")
    with eqlib.Eq() as e:
        e.set_param("MODELG", 3)
        e.set_params(**params)
        e.set_param_str("KNAMEQ", "eqdata.TST-2")
        e.run(1)
        return e.get_state()


def test_a_load_whose_axis_lies_outside_the_box_says_so():
    # TST-2's axis lies near R = 0.39 m, outside the default box 1.5..4.5 x -2..2 m that
    # MDLEQF >= 10 holds it to: the load fails (ierr=103), and the reason names both.
    axis = _load_tst2(MDLEQF=0).scalars["raxis"]
    with pytest.raises(eqlib.EqlibCalculationFailedError) as err:
        _load_tst2(MDLEQF=10)
    message = str(err.value)
    assert f"the search for the magnetic axis ended at (R, Z) = ({axis:.4f}, " in message
    assert "outside the box RGMIN..RGMAX = [1.5000, 4.5000], ZGMIN..ZGMAX = [-2.0000, 2.0000]" in message
    assert "MDLEQF >= 10 holds the axis to" in message
    assert message.endswith("(ierr=103)")


def test_the_same_load_with_a_box_around_the_axis_runs():
    state = _load_tst2(MDLEQF=10, RGMIN=0.05, RGMAX=0.8, ZGMIN=-0.6, ZGMAX=0.6)
    reference = _load_tst2(MDLEQF=0)
    # The axis of the load at MDLEQF=0; PVOL differs from it by 1.3e-4 (measured).
    assert state.scalars["raxis"] == pytest.approx(reference.scalars["raxis"], rel=1e-9)
    assert state.scalars["pvol"] == pytest.approx(reference.scalars["pvol"], rel=1e-3)


def test_an_analytic_solve_whose_axis_leaves_the_box_says_so():
    with eqlib.Eq() as e:
        e.set_params(MODELG=2, MDLEQF=10, RGMIN=3.001)
        with pytest.raises(eqlib.EqlibCalculationFailedError) as err:
            e.run(0)
    message = str(err.value)
    assert "the search for the magnetic axis ended at (R, Z) = (3.0000, " in message
    assert "RGMIN..RGMAX = [3.0010, 4.5000]" in message
    assert message.endswith("(ierr=103)")


# --- task-web-client #191: MODELG=15 reads the fixed eqdb.dat, and returns where it STOPped ---

# One child process per case: a STOP ends the process that meets it (under --forked it ends the
# pytest session too), and the child's standard input carries a line that the load must leave.
_MODELG15_CHILD = r"""
import sys
import eqlib
with eqlib.Eq() as e:
    e.set_param("MODELG", 15)
    e.set_param_str("KNAMEQ", "eqdata.TST-2")
    for attempt in (1, 2):
        try:
            e.run(1)
            print("LOADED", flush=True)
        except eqlib.EqlibCalculationFailedError as exc:
            print("REFUSED", exc, flush=True)
print("STDIN", repr(sys.stdin.read()), flush=True)
"""


def _load_modelg15(tmp_path, eqdb):
    import shutil
    import subprocess
    import sys
    if eqdb is not None:
        (tmp_path / "eqdb.dat").write_bytes(eqdb)
    shutil.copy(_FIXTURES / "eqdata.TST-2", tmp_path / "eqdata.TST-2")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_HERE.parents[2])] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    proc = subprocess.run([sys.executable, "-c", _MODELG15_CHILD], cwd=tmp_path, env=env,
                          input="a line\n", capture_output=True, text=True, errors="replace",
                          timeout=60)
    lines = [l for l in proc.stdout.splitlines() if l.startswith(("REFUSED", "LOADED", "STDIN"))]
    return proc, lines


def _record(payload: bytes) -> bytes:
    """One record of a gfortran unformatted sequential file."""
    import struct
    return struct.pack("<i", len(payload)) + payload + struct.pack("<i", len(payload))


@pytest.mark.parametrize("eqdb, reason", [
    (None, "'eqdb.dat' not found"),
    (_record(b"EQD" + b" " * 110), "'eqdb.dat' ends before the equilibrium does"),
    (b"", "'eqdb.dat' ends before the equilibrium does"),
    (b"not an eqdb file\n", "'eqdb.dat' could not be read"),
], ids=["missing", "header-only", "empty", "garbage"])
def test_modelg_15_returns_an_error_and_the_process_lives(tmp_path, eqdb, reason):
    # KNAMEQ names a file that is there; MODELG 15 reads eqdb.dat all the same.
    proc, lines = _load_modelg15(tmp_path, eqdb)
    expected = ("REFUSED eq_run(1): rc=3: EQ_READ: MODELG=15 reads the fixed file 'eqdb.dat', "
                f"not KNAMEQ: {reason}")
    assert lines == [expected, expected, "STDIN 'a line\\n'"], (proc.returncode, proc.stdout[-500:],
                                                                 proc.stderr[-500:])
    assert proc.returncode == 0


def _load_modelg8_first_file_only(tmp_path, knameq2=None):
    # EQJAEAR (MODELG=8) reads KNAMEQ, then opens KNAMEQ2 (default eqdata2). A small first
    # file in its layout (the grid counts, the box, psi, BtR) gets the load as far as that open.
    import struct
    first = (_record(struct.pack("<2i", 3, 3)) + _record(struct.pack("<4d", 0.1, 0.5, -0.3, 0.3))
             + _record(struct.pack("<9d", *([0.0] * 9))) + _record(struct.pack("<d", 1.0)))
    (tmp_path / "jaea.dat").write_bytes(first)
    with eqlib.Eq() as e:
        e.set_param("MODELG", 8)
        e.set_param_str("KNAMEQ", "jaea.dat")
        if knameq2 is not None:
            e.set_param_str("KNAMEQ2", knameq2)
        with pytest.raises(eqlib.EqlibCalculationFailedError) as err:
            e.run(1)
    return str(err.value)


def test_modelg_8_without_its_second_file_names_knameq2(tmp_path):
    # The reason names KNAMEQ2, where EQ_READ's fallback named KNAMEQ, which was read.
    assert _load_modelg8_first_file_only(tmp_path) == (
        "eq_run(1): rc=3: EQ_READ: MODELG=8 load failed: its second file KNAMEQ2='eqdata2' not found")


def test_modelg_8_with_a_blank_knameq2_says_so(tmp_path):
    assert _load_modelg8_first_file_only(tmp_path, knameq2="") == (
        "eq_run(1): rc=3: EQ_READ: MODELG=8 load failed: its second file KNAMEQ2 is blank")
