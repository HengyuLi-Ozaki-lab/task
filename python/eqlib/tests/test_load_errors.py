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


# --- A file that is not of the format MODELG names: the readers return where the process ended ---

# EQRTSK (MODELG 3 and 9), EQDSKR (5 and 25) and EQJAEAR (8) did not check their reads: a file of
# another format, or one cut short, ended the process with a Fortran runtime error (exit status 2),
# and a size read from such a file was used before it was checked. Each case runs in a child process,
# which then loads the TST-2 fixture in the same session.
_WRONG_FORMAT_CHILD = r"""
import sys
import eqlib
modelg, knameq, knameq2 = int(sys.argv[1]), sys.argv[2], sys.argv[3]
with eqlib.Eq() as e:
    if modelg:
        e.set_param("MODELG", modelg)
        e.set_param_str("KNAMEQ", knameq)
        if knameq2:
            e.set_param_str("KNAMEQ2", knameq2)
        before = e.get_state().nrgmax
        try:
            e.run(1)
            print("LOADED", flush=True)
        except eqlib.EqlibCalculationFailedError as exc:
            print("REFUSED", exc, flush=True)
        print("NRGMAX", before, e.get_state().nrgmax, flush=True)
    e.set_param("MODELG", 3)
    e.set_param_str("KNAMEQ", "eqdata.TST-2")
    e.run(1)
    print("THEN", repr(e.get_state().scalars["raxis"]), flush=True)
"""


def _run_wrong_format(tmp_path, modelg, knameq="", knameq2=""):
    import shutil
    import subprocess
    import sys
    shutil.copy(_FIXTURES / "eqdata.TST-2", tmp_path / "eqdata.TST-2")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_HERE.parents[2])] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    proc = subprocess.run([sys.executable, "-c", _WRONG_FORMAT_CHILD, str(modelg), knameq, knameq2],
                          cwd=tmp_path, env=env, capture_output=True, text=True, errors="replace",
                          timeout=60)
    lines = {}
    for line in proc.stdout.splitlines():
        key, _, rest = line.partition(" ")
        if key in ("LOADED", "REFUSED", "NRGMAX", "THEN"):
            lines[key] = rest
    return proc, lines


# A G-EQDSK-like text file: the header as EQDSKR reads it (6a8,3i4), then rows of (5e16.9).
def _geqdsk_text(nr=33, nz=33):
    rows = "".join(f"{1.0:16.9e}" * 5 + "\n" for _ in range(4))
    return f"{'  TEST':<48}{0:4d}{nr:4d}{nz:4d}\n" + rows


def _jaea_first_file():
    """A small first file in EQJAEAR's layout: the grid counts, the box, psi (all 0), BtR."""
    import struct
    return (_record(struct.pack("<2i", 3, 3)) + _record(struct.pack("<4d", 0.1, 0.5, -0.3, 0.3))
            + _record(struct.pack("<9d", *([0.0] * 9))) + _record(struct.pack("<d", 1.0)))


def _jaea_profiles():
    """EQJAEAR's second file: a header line, then 41 lines of (i, TT, PP)."""
    return "header\n" + "".join(f"{i} 1.0 0.0\n" for i in range(1, 42))


def _write(tmp_path, name, content):
    path = tmp_path / name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)
    return name


def _tst2_cut(size=3000):
    return (_FIXTURES / "eqdata.TST-2").read_bytes()[:size]


def _tst2_header(nrgmax, nzgmax):
    """The first two records of a TASK/EQ file (RR, BB, RIP; NRGMAX, NZGMAX), and nothing more."""
    import struct
    return _record(struct.pack("<3d", 0.3, 0.3, 0.1)) + _record(struct.pack("<2i", nrgmax, nzgmax))


@pytest.fixture(scope="module")
def _reference_raxis(tmp_path_factory):
    """RAXIS of the TST-2 load in a session that loaded nothing before it."""
    proc, lines = _run_wrong_format(tmp_path_factory.mktemp("reference"), 0)
    assert "THEN" in lines, (proc.returncode, proc.stdout[-500:], proc.stderr[-500:])
    return lines["THEN"]


@pytest.mark.parametrize("modelg, files, reason", [
    (3, {"KNAMEQ": ("g.txt", _geqdsk_text())},
     "EQ_READ: MODELG=3 load of KNAMEQ='g.txt' failed: it does not read as a TASK/EQ file ("),
    (9, {"KNAMEQ": ("g.txt", _geqdsk_text())},
     "EQ_READ: MODELG=9 load of KNAMEQ='g.txt' failed: it does not read as a TASK/EQ file ("),
    (3, {"KNAMEQ": ("cut.bin", _tst2_cut())},
     "EQ_READ: MODELG=3 load of KNAMEQ='cut.bin' failed: it does not read as a TASK/EQ file ("),
    (3, {"KNAMEQ": ("big.bin", _tst2_header(100000, 33))},
     "EQ_READ: MODELG=3 load of KNAMEQ='big.bin' failed: it does not read as a TASK/EQ file "
     "(NRGMAX=100000 is not in 2..513)"),
    (5, {"KNAMEQ": ("eqdata.TST-2", None)},
     "EQ_READ: MODELG=5 load of KNAMEQ='eqdata.TST-2' failed: it does not read as a G-EQDSK file ("),
    (25, {"KNAMEQ": ("eqdata.TST-2", None)},
     "EQ_READ: MODELG=25 load of KNAMEQ='eqdata.TST-2' failed: it does not read as a G-EQDSK file ("),
    (5, {"KNAMEQ": ("g.txt", _geqdsk_text(nr=1000))},
     "EQ_READ: MODELG=5 load of KNAMEQ='g.txt' failed: it does not read as a G-EQDSK file "
     "(NRGMAX=1000 is not in 2..513)"),
    (5, {"KNAMEQ": ("g.txt", _geqdsk_text())},
     "EQ_READ: MODELG=5 load of KNAMEQ='g.txt' failed: it does not read as a G-EQDSK file ("),
    (8, {"KNAMEQ": ("g.txt", _geqdsk_text())},
     "EQ_READ: MODELG=8 load of KNAMEQ='g.txt' failed: it does not read as a QST/JAEA file ("),
    (8, {"KNAMEQ": ("jaea.dat", _jaea_first_file()), "KNAMEQ2": ("eqdata.TST-2", None)},
     "EQ_READ: MODELG=8 load failed: its second file KNAMEQ2='eqdata.TST-2' does not read as a QST/JAEA "
     "profile file ("),
    (8, {"KNAMEQ": ("jaea.dat", _jaea_first_file()), "KNAMEQ2": ("prof.txt", _jaea_profiles())},
     "EQ_READ: MODELG=8 load of KNAMEQ='jaea.dat' failed: no magnetic axis found in its psi"),
], ids=["3-text", "9-text", "3-cut", "3-size", "5-binary", "25-binary", "5-size", "5-short", "8-text",
        "8-second-binary", "8-no-axis"])
def test_a_file_of_another_format_is_an_error_and_the_process_lives(
        tmp_path, _reference_raxis, modelg, files, reason):
    names = {}
    for key, (name, content) in files.items():
        names[key] = _write(tmp_path, name, content) if content is not None else name
    proc, lines = _run_wrong_format(tmp_path, modelg, names["KNAMEQ"], names.get("KNAMEQ2", ""))
    detail = (proc.returncode, proc.stdout[-800:], proc.stderr[-800:])
    assert proc.returncode == 0, detail
    assert "LOADED" not in lines, detail
    message = lines["REFUSED"]
    assert message.startswith("eq_run(1): rc=3: " + reason), detail
    if reason.endswith("("):
        assert message.endswith(")") and len(message) > len("eq_run(1): rc=3: " + reason) + 1, detail
    # A failed load leaves the grid sizes as they were (EQ_READ puts them back).
    before, after = lines["NRGMAX"].split()
    assert before == after, detail
    # The same session loads the fixture afterwards, and gets what a fresh session gets.
    assert lines["THEN"] == _reference_raxis, detail


_SOLVE_AFTER_CHILD = r"""
import sys
import eqlib
with eqlib.Eq() as e:
    # Sizes the TST-2 file does not have (33, 21, 32, 32, 50).
    e.set_params(NRGMAX=41, NPSMAX=31, NSGMAX=24, NTGMAX=24, NRVMAX=40)
    if sys.argv[1]:
        e.set_param("MODELG", 3)
        e.set_param_str("KNAMEQ", sys.argv[1])
        try:
            e.run(1)
            print("LOADED", flush=True)
        except eqlib.EqlibCalculationFailedError as exc:
            print("REFUSED", exc, flush=True)
        e.set_param("MODELG", 2)
    s = e.get_state()
    print("SIZES", s.nrgmax, s.nzgmax, s.npsmax, s.nsgmax, s.ntgmax, s.nrvmax, s.nrmax, s.nthmax,
          s.nsumax, flush=True)
    e.set_params(RR=3.0, RA=1.0, BB=3.0, RIP=1.5)
    e.run(0)
    print("THEN", repr(e.get_state().scalars["raxis"]), flush=True)
"""


def _records(blob: bytes) -> list[bytes]:
    """The payloads of a gfortran unformatted sequential file."""
    import struct
    out, i = [], 0
    while i < len(blob):
        (n,) = struct.unpack_from("<i", blob, i)
        out.append(blob[i + 4:i + 4 + n])
        i += n + 8
    return out


def test_a_load_that_fails_part_way_leaves_the_grid_sizes_as_they_were(tmp_path):
    # TST-2's first twelve records, up to its counters (NSGMAX..NTVMAX), and nothing after them:
    # the load sets NRGMAX, NZGMAX, NPSMAX and the counters from the file, then fails at the next
    # record. EQ_READ puts every grid size back, so the solve after it runs on the sizes set before
    # the load and gives what it gives in a session that loaded nothing. (A size left from the file
    # can fit its array and still be too small for the solve.)
    import subprocess
    import sys
    recs = _records((_FIXTURES / "eqdata.TST-2").read_bytes())
    (tmp_path / "cut.bin").write_bytes(b"".join(_record(r) for r in recs[:12]))
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_HERE.parents[2])] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

    def child(knameq):
        proc = subprocess.run([sys.executable, "-c", _SOLVE_AFTER_CHILD, knameq], cwd=tmp_path,
                              env=env, capture_output=True, text=True, errors="replace", timeout=60)
        lines = dict(l.partition(" ")[::2] for l in proc.stdout.splitlines()
                     if l.startswith(("LOADED", "REFUSED", "SIZES", "THEN")))
        return proc, lines

    ref_proc, ref = child("")
    proc, got = child("cut.bin")
    detail = (proc.returncode, proc.stdout[-800:], proc.stderr[-800:])
    assert ref_proc.returncode == 0 and "THEN" in ref, (ref_proc.stdout[-500:], ref_proc.stderr[-500:])
    assert proc.returncode == 0, detail
    assert got["REFUSED"].startswith(
        "eq_run(1): rc=3: EQ_READ: MODELG=3 load of KNAMEQ='cut.bin' failed: it does not read as a "
        "TASK/EQ file ("), detail
    assert got["SIZES"] == ref["SIZES"], detail
    assert got["THEN"] == ref["THEN"], detail
