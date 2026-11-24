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
import re
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
    assert ", 1.1E+00 below RGMIN, outside the box" in message
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
    assert "), 1.0E-03 below RGMIN, outside the box" in message
    assert message.endswith("(ierr=103)")


_IN_LOOP = re.compile(
    r"^EQAXIS: the axis is (\d\.\dE[-+]\d\d) below RGMIN = (\d+\.\d{4}) at "
    r"\(R, Z\) = \((-?\d+\.\d{4}), (-?\d+\.\d{4})\), in iteration (\d+) of the solve: "
    r"it moves as the solve goes on, and the box \(MDLEQF >= 10\) must hold its path "
    r"\(ierr=103\)$")


def _analytic_failure(**params):
    with eqlib.Eq() as e:
        e.set_params(MODELG=2, **params)
        with pytest.raises(eqlib.EqlibCalculationFailedError) as err:
            e.run(0)
        return str(err.value), e.last_error()


def test_an_axis_that_triangularity_moves_out_of_the_box_names_the_iteration():
    # tw#188: RR = RGMIN + 0.03 at RDLT 0.4; the axis starts inside and leaves on the way.
    message, last = _analytic_failure(MDLEQF=10, RDLT=0.4, RGMIN=2.97)
    m = _IN_LOOP.match(last)
    assert m, last
    assert int(m.group(5)) >= 2
    assert m.group(2) == "2.9700"
    assert float(m.group(1)) == pytest.approx(2.97 - float(m.group(3)), rel=0.02)
    assert len(last) <= 255 and "unprintable" not in last
    assert message.endswith(last)
    # TR's tr_last_error keeps about 72 characters of EQ's message: the crossing is within them
    assert last[:72].startswith("EQAXIS: the axis is ") and "below RGMIN" in last[:72]


def test_an_axis_that_ends_inside_but_leaves_on_the_way_names_the_iteration():
    # tw#188: at RDLT 0.2 the axis ends at 3.0219 with the default box, yet RGMIN 2.9995 fails.
    # The axis path's minimum is R = 2.9991 (the R the message prints); the start, R = 3.0, is
    # 5e-4 inside RGMIN, so iteration 1 passes and the failure is in the loop.
    _, last = _analytic_failure(MDLEQF=10, RDLT=0.2, RGMIN=2.9995)
    m = _IN_LOOP.match(last)
    assert m and int(m.group(5)) >= 2 and m.group(2) == "2.9995", last


def test_a_zgmax_just_below_the_axis_says_by_how_much():
    # tw#214: the axis's Z (about 0) and the bound ZGMAX = -2e-5 print alike at four decimals
    # (-0.0000); the clause gives the distance.
    _, last = _analytic_failure(MDLEQF=10, ZGMAX=-2.0e-5)
    assert "in iteration" not in last, last
    assert ", 2.0E-05 above ZGMAX, outside the box" in last
    assert "ZGMIN..ZGMAX = [-2.0000, -0.0000]" in last
    assert "that MDLEQF >= 10 holds the axis to (ierr=103)" in last


def test_a_load_after_a_solve_in_the_same_instance_uses_the_box_form():
    # EQ_NLOOP goes back to 0 when EQLOOP ends: a later failure outside the loop is not "in iteration".
    import shutil
    shutil.copy(_FIXTURES / "eqdata.TST-2", "eqdata.TST-2")
    with eqlib.Eq() as e:
        e.set_params(MODELG=2)
        e.run(0)
        e.set_param("MODELG", 3)
        e.set_param("MDLEQF", 10)
        e.set_param_str("KNAMEQ", "eqdata.TST-2")
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)
        last = e.last_error()
    assert "in iteration" not in last, last
    # the solve has reset RGMIN..ZGMAX to the box around its own plasma, so the numbers are not 1.5..4.5
    assert "outside the box RGMIN..RGMAX = [" in last, last


def test_a_load_after_a_failed_solve_in_the_same_instance_uses_the_box_form():
    # EQLOOP's error return resets EQ_NLOOP too: a load that fails after a failed solve is not "in iteration".
    import shutil
    shutil.copy(_FIXTURES / "eqdata.TST-2", "eqdata.TST-2")
    with eqlib.Eq() as e:
        e.set_params(MODELG=2, MDLEQF=10, RDLT=0.4, RGMIN=2.97)
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(0)
        assert "in iteration" in e.last_error()
        e.set_param("MODELG", 3)
        e.set_param_str("KNAMEQ", "eqdata.TST-2")
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)
        last = e.last_error()
    assert "in iteration" not in last, last
    assert "outside the box RGMIN..RGMAX = [" in last, last


# --- task-web-client #191, #203: MODELG=15 (the fixed eqdb.dat) is refused before the load ---

# EQDSK (eq/equread.f90) passes equ_set_psi one of the three arrays it takes, so the load of a
# well-formed eqdb.dat ended the process (SIGSEGV in equ_set_psi, eq/equintf.f90); a missing,
# short or unreadable file returned an error (#191). run(1) now refuses MODELG 15 whatever the
# files. One child process per case: the well-formed file ends the process that loads it on a
# build without the refusal. The child then loads a TASK file in the same session, and its
# standard input carries a line that the runs must leave.
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
        except eqlib.EqlibError as exc:
            print("REFUSED", type(exc).__name__, exc, flush=True)
    e.set_param("MODELG", 3)
    e.run(1)
    print("LOADED MODELG=3", flush=True)
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


def _eqdb_well_formed() -> bytes:
    """An eqdb.dat that EQDSK's two READs take whole: a header record, then a 3 x 3 grid,
    nv = nsu = 3, zeros elsewhere and the 950 trailing values (eq/equread.f90)."""
    import struct
    i = lambda *v: struct.pack(f"<{len(v)}i", *v)
    d = lambda *v: struct.pack(f"<{len(v)}d", *v)
    body = (i(3, 3) + d(0.1, 0.3, 0.5) + d(-0.2, 0.0, 0.2) + d(*[0.0] * 9)
            + i(3) + d(*[0.0] * 18)                      # pds fds vlv qqv prv xxx, 3 each
            + d(*[0.0] * 6) + d(*[0.0] * 6) + i(0, 0, 0, 0) + d(*[0.0] * 18)
            + i(3) + d(*[0.0] * 9)                       # nsu; rsu zsu csu
            + i(0) + d(0.0, 0.0, 0.0) + i(0) + i(0) + d(*[0.0] * 5) + i(*[0] * 8)
            + d(*[0.0] * 21) + i(*[0] * 5) + d(*[0.0] * 950))
    return _record(b"EQD" + b" " * 110) + _record(body)


_MODELG15_REFUSED = ("REFUSED EqlibInvalidParamError eq_run(1): rc=1: eq_run(1): MODELG=15 is refused: "
                     "its reader (EQDSK, eq/equread.f90) passes equ_set_psi one of its three arrays, "
                     "so a load of eqdb.dat ends the process")


@pytest.mark.parametrize("eqdb", [
    None,
    _record(b"EQD" + b" " * 110),
    b"",
    b"not an eqdb file\n",
    _eqdb_well_formed(),
], ids=["missing", "header-only", "empty", "garbage", "well-formed"])
def test_modelg_15_is_refused_and_the_process_lives(tmp_path, eqdb):
    # KNAMEQ names a file that is there; MODELG 15 reads eqdb.dat, and is refused whatever it holds.
    proc, lines = _load_modelg15(tmp_path, eqdb)
    assert lines == [_MODELG15_REFUSED, _MODELG15_REFUSED, "LOADED MODELG=3", "STDIN 'a line\\n'"], (
        proc.returncode, proc.stdout[-500:], proc.stderr[-500:])
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


# --- task-web-client #204: MODELG=8's reader, record by record, and the checks it adds ----------

# One child process per case: the reader used to end the process that met a short or malformed
# file (a Fortran runtime error, exit status 2) or a map without an axis (STOP, exit status 0,
# no error returned); under --forked that ends the pytest session. The reasons are the ones the
# readers share since fork PR #31 (above); #204 adds the R and Z ranges and find_axis's 102.
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


def _jaea_map(nr=3, nz=3, psi=None, box=(0.1, 0.5, -0.3, 0.3), records=4):
    """KNAMEQ in EQJAEAR's layout: the grid counts, the R and Z ranges, psi (R fastest), BtR.

    ``records`` keeps only the first records; ``psi`` defaults to a map of zeros of the grid's size.
    With the defaults it is the ``_jaea_first_file()`` of the block above.
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
_M8K = "load of KNAMEQ='jaea.dat' failed: "
_NOT_JAEA = _M8K + "it does not read as a QST/JAEA file ("
_NOT_PROFILES = "its second file KNAMEQ2='eqdata2' does not read as a QST/JAEA profile file ("


@pytest.mark.parametrize("first, table, reason", [
    (b"", _jaea_table(), _NOT_JAEA),
    (_jaea_map(records=1), _jaea_table(), _NOT_JAEA),
    (_jaea_map(records=2), _jaea_table(), _NOT_JAEA),
    (_jaea_map(psi=[0.0] * 4), _jaea_table(), _NOT_JAEA),
    (_jaea_map(records=3), _jaea_table(), _NOT_JAEA),
    (_jaea_map(nr=1000), _jaea_table(), _NOT_JAEA + "NRGMAX=1000 is not in 2..513)"),
    (_jaea_map(nz=1), _jaea_table(), _NOT_JAEA + "NZGMAX=1 is not in 2..513)"),
    (_jaea_map(box=(0.5, 0.5, -0.3, 0.3)), _jaea_table(),
     _NOT_JAEA + "R from 5.0000E-01 to 5.0000E-01, Z from -3.0000E-01 to 3.0000E-01: no grid)"),
    (_jaea_map(box=(0.5, 0.1, -0.3, 0.3)), _jaea_table(),
     _NOT_JAEA + "R from 5.0000E-01 to 1.0000E-01, Z from -3.0000E-01 to 3.0000E-01: no grid)"),
    (_jaea_map(box=(0.1, 0.5, 0.3, -0.3)), _jaea_table(),
     _NOT_JAEA + "R from 1.0000E-01 to 5.0000E-01, Z from 3.0000E-01 to -3.0000E-01: no grid)"),
    (_jaea_map(box=(0.1, 0.5, -0.3, float("inf"))), _jaea_table(),
     _NOT_JAEA + "R from 1.0000E-01 to 5.0000E-01, Z from -3.0000E-01 to Infinity: no grid)"),
    (_jaea_map(), "", _NOT_PROFILES),
    (_jaea_map(), _jaea_table(rows=10), _NOT_PROFILES),
    (_jaea_map(), _jaea_table(bad_row=5), _NOT_PROFILES),
    # A 21 x 21 map of zeros: interior points to search, none where |grad psi| is below its neighbours.
    (_jaea_map(nr=21, nz=21), _jaea_table(), _M8K + "no magnetic axis found in its psi"),
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
    # A reason that ends in "(" is followed by the message of the read that failed (gfortran's).
    proc, lines = _load_modelg8(tmp_path, first, table)
    detail = (proc.returncode, proc.stdout[-500:], proc.stderr[-500:])
    expected = ("eq_run(1): rc=3: EQ_READ: MODELG=8 " + reason) if reason.startswith("load of") else _M8 + reason
    assert len(lines) == 1, detail
    if reason.endswith("("):
        assert lines[0].startswith("REFUSED " + expected) and lines[0].endswith(")"), (lines, detail)
        assert len(lines[0]) > len("REFUSED " + expected) + 1, (lines, detail)
    else:
        assert lines == ["REFUSED " + expected], detail
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
    return _jaea_map(nr=nr, nz=nz, psi=psi, box=box)


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
    # EQAXIS (the MODELG 3/5/25 loads, through EQCALQ, and the Grad-Shafranov solve) returns
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
