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


# --- task-web-client #204: MODELG=8's reader returns an error where it ended the process ------

# One child process per case: the reader used to end the process that met a short or malformed
# file (a Fortran runtime error, exit status 2) or a map without an axis (STOP, exit status 0,
# no error returned); under --forked that ends the pytest session.
_MODELG8_CHILD = r"""
import eqlib
with eqlib.Eq() as e:
    e.set_param("MODELG", 8)
    e.set_param_str("KNAMEQ", "jaea.dat")
    try:
        e.run(1)
        print("LOADED", flush=True)
    except eqlib.EqlibCalculationFailedError as exc:
        print("REFUSED", exc, flush=True)
"""


def _jaea_first_file(nr=3, nz=3, psi=None, box=(0.1, 0.5, -0.3, 0.3), records=4):
    """KNAMEQ in EQJAEAR's layout: the grid counts, the R and Z ranges, psi (R fastest), BtR.

    ``records`` keeps only the first records; ``psi`` defaults to a map of zeros of the grid's size.
    """
    import struct
    psi = [0.0] * (nr * nz) if psi is None else list(psi)
    parts = [_record(struct.pack("<2i", nr, nz)), _record(struct.pack("<4d", *box)),
             _record(struct.pack(f"<{len(psi)}d", *psi)), _record(struct.pack("<d", 1.0))]
    return b"".join(parts[:records])


def _jaea_table(rows=41, bad_row=None):
    """KNAMEQ2: a header line and ``rows`` rows of (index, T, p); ``bad_row`` is not numbers."""
    return "header\n" + "".join("x y z\n" if i == bad_row else f"{i} 1.0 0.0\n"
                                for i in range(1, rows + 1))


def _load_modelg8(tmp_path, first: bytes, table: str):
    import subprocess
    import sys
    (tmp_path / "jaea.dat").write_bytes(first)
    (tmp_path / "eqdata2").write_text(table)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_HERE.parents[2])] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    proc = subprocess.run([sys.executable, "-c", _MODELG8_CHILD], cwd=tmp_path, env=env,
                          capture_output=True, text=True, errors="replace", timeout=60,
                          stdin=subprocess.DEVNULL)
    lines = [l for l in proc.stdout.splitlines() if l.startswith(("REFUSED", "LOADED"))]
    return proc, lines


_M8 = "eq_run(1): rc=3: EQ_READ: MODELG=8 load failed: "


@pytest.mark.parametrize("first, table, reason", [
    (b"", _jaea_table(), "KNAMEQ='jaea.dat' ends before its grid counts"),
    (_jaea_first_file(records=1), _jaea_table(), "KNAMEQ='jaea.dat' ends before its R and Z ranges"),
    (_jaea_first_file(records=2), _jaea_table(), "KNAMEQ='jaea.dat' ends before its psi map"),
    (_jaea_first_file(psi=[0.0] * 4), _jaea_table(), "KNAMEQ='jaea.dat' could not be read: its psi map"),
    (_jaea_first_file(records=3), _jaea_table(), "KNAMEQ='jaea.dat' ends before its BtR record"),
    (_jaea_first_file(nr=1000), _jaea_table(),
     "KNAMEQ='jaea.dat' gives a grid of 1000 x 3 points, outside 2..513 x 2..513"),
    (_jaea_first_file(nz=1), _jaea_table(),
     "KNAMEQ='jaea.dat' gives a grid of 3 x 1 points, outside 2..513 x 2..513"),
    (_jaea_first_file(box=(0.5, 0.5, -0.3, 0.3)), _jaea_table(),
     "KNAMEQ='jaea.dat' gives R and Z ranges that are no grid: R from 5.0000E-01 to 5.0000E-01, "
     "Z from -3.0000E-01 to 3.0000E-01"),
    (_jaea_first_file(box=(0.5, 0.1, -0.3, 0.3)), _jaea_table(),
     "KNAMEQ='jaea.dat' gives R and Z ranges that are no grid: R from 5.0000E-01 to 1.0000E-01, "
     "Z from -3.0000E-01 to 3.0000E-01"),
    (_jaea_first_file(box=(0.1, 0.5, 0.3, -0.3)), _jaea_table(),
     "KNAMEQ='jaea.dat' gives R and Z ranges that are no grid: R from 1.0000E-01 to 5.0000E-01, "
     "Z from 3.0000E-01 to -3.0000E-01"),
    (_jaea_first_file(box=(0.1, 0.5, -0.3, float("inf"))), _jaea_table(),
     "KNAMEQ='jaea.dat' gives R and Z ranges that are no grid: R from 1.0000E-01 to 5.0000E-01, "
     "Z from -3.0000E-01 to Infinity"),
    (_jaea_first_file(), "", "KNAMEQ2='eqdata2' ends before its header line"),
    (_jaea_first_file(), _jaea_table(rows=10), "KNAMEQ2='eqdata2' ends before its row 11 of 41"),
    (_jaea_first_file(), _jaea_table(bad_row=5), "KNAMEQ2='eqdata2' could not be read: its row 5 of 41"),
    # A 21 x 21 map of zeros: interior points to search, none where |grad psi| is below its neighbours.
    (_jaea_first_file(nr=21, nz=21), _jaea_table(),
     "the psi map in KNAMEQ='jaea.dat' has no magnetic axis: no interior point where |grad psi| "
     "is below its four neighbours (ierr=102)"),
], ids=["knameq-empty", "knameq-counts-only", "knameq-no-psi", "knameq-psi-short", "knameq-no-btr",
        "knameq-grid-1000", "knameq-grid-1", "knameq-r-empty", "knameq-r-falling", "knameq-z-falling",
        "knameq-z-infinite", "knameq2-empty", "knameq2-10-rows", "knameq2-bad-row", "map-without-axis"])
def test_modelg_8_returns_an_error_and_the_process_lives(tmp_path, first, table, reason):
    # Measured on 0e83ad3d (-O0 with run-time checks): nine ended the process with a Fortran
    # runtime error, exit status 2 (the 1000-point grid at an index past the arrays' 513, which
    # only the checks catch); the 3 x 1 grid and the map without an axis at STOP, exit status 0
    # with no error returned. The empty and the falling R range and the falling and the infinite
    # Z range, on a 3 x 3 map, reached that STOP too, as any 3 x 3 map does (no interior point to
    # search): they are refused now before the grid is built, which is what these four cases show.
    proc, lines = _load_modelg8(tmp_path, first, table)
    assert lines == ["REFUSED " + _M8 + reason], (proc.returncode, proc.stdout[-500:], proc.stderr[-500:])
    assert proc.returncode == 0


def _psi_map_whose_spline_is_nan(nr=21, nz=21):
    """A ramp in R with a bump, and one corner value NaN.

    The search on the grid values finds one interior minimum of |grad psi| (R = 1.15 m, Z = 0),
    away from the corner; the spline through the values, which the Newton search runs on, is NaN
    everywhere, so the search ends at a point that is not finite.
    """
    import math
    box = (0.5, 1.5, -0.5, 0.5)
    psi = []
    for j in range(nz):
        z = box[2] + (box[3] - box[2]) * j / (nz - 1)
        for i in range(nr):
            r = box[0] + (box[1] - box[0]) * i / (nr - 1)
            psi.append((r - 1.0) + 0.1 * math.exp(-((r - 1.0) ** 2 + z ** 2) / 0.2 ** 2))
    psi[0] = float("nan")
    return _jaea_first_file(nr=nr, nz=nz, psi=psi, box=box)


def test_modelg_8_axis_search_that_ends_at_nan_is_an_error(tmp_path):
    # find_axis's IERR=102 was its own variable: EQJAEAR went on from the search's last point,
    # here not finite, and on 0e83ad3d the load ended the process (eqcalq.f90, an index -1 below
    # the bound, exit status 2). A search that fails at a finite point goes on as it did.
    proc, lines = _load_modelg8(tmp_path, _psi_map_whose_spline_is_nan(), _jaea_table())
    assert len(lines) == 1, (proc.returncode, proc.stdout[-500:], proc.stderr[-500:])
    assert lines[0].startswith(
        "REFUSED " + _M8 + "the search for the magnetic axis from (R, Z) = "
        "(1.1500, 0.0000) did not converge (NEWTN IER="), lines[0]
    assert lines[0].endswith("): it ended at a point that is not finite (ierr=102)"), lines[0]
    assert proc.returncode == 0


@pytest.mark.skipif(not (_FIXTURES / "eqdata.ITER01").exists(), reason="fixture eqdata.ITER01 missing")
def test_a_file_load_whose_axis_search_does_not_converge_says_so(tmp_path):
    # EQAXIS (the MODELG 3/5/25 loads, through EQCALQ, and the analytic solve) returns
    # find_axis's 102. A g-eqdsk whose psi is a ramp in R has no axis, and the search ends at NaN;
    # on 0e83ad3d the load went on and failed with "ended at (R, Z) = (NaN, NaN), outside ...
    # (ierr=103)".
    # The ITER01 load and the g-eqdsk writer are test_qqps_psi_surface's (no fixture of its own).
    import numpy as np
    from eqlib.tests.test_qqps_psi_surface import _load_iter01, _write_geqdsk
    with eqlib.Eq() as e:
        st = _load_iter01(e)
        ramp = 10.0 * np.add.outer(np.array(st.rg) - st.scalars["raxis"], 0.0 * np.array(st.zg))
        _write_geqdsk(tmp_path / "g_ramp", st, ramp, lambda s: 1.0 + s)
        e.set_param("MODELG", 5)
        e.set_param_str("KNAMEQ", "g_ramp")
        with pytest.raises(eqlib.EqlibCalculationFailedError) as err:
            e.run(1)
    message = str(err.value)
    assert message.startswith(
        "eq_run(1): rc=3: EQAXIS: the search for the magnetic axis from (R, Z) = "
        f"({st.scalars['raxis']:.4f}, "), message
    assert "did not converge (NEWTN IER=" in message, message
    assert message.endswith("): it ended at a point that is not finite (ierr=102)"), message
