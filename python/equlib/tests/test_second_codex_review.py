"""What the second Codex review of 2026-11-22 found: inputs that validate and
then indexed past EQU's arrays (eqaxi, flxfun), and files the library could
reach that are not regular files, or that a failed write left behind. The
kernel's are errors of the run now (exit status 2 in the program); the
library opens only regular files that are not the process's standard
streams, and removes only a G-EQDSK file it created."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from equlib import Equ, EqulibCalculationFailedError, EqulibInvalidParamError
from equlib.tests._program import PROGRAM, REPO, stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib

NO_PROGRAM = pytest.mark.skipif(not PROGRAM.exists(), reason="equ_nogr not built")

# QUEST with the markers 0 and 1 in the box's first row: eqsol puts the axis
# there and eqaxi's walk read psi below 1 (index -108).
AXIS_AT_THE_EDGE = {"IUDSYM": 0, "ZVAC[0]": -1.295, "ZVAC[1]": -1.295}
AXIS_AT_THE_EDGE_NML = "IUDSYM=0, ZVAC(0)=-1.295, ZVAC(1)=-1.295"


def _namelist_adds(workdir: Path, text: str) -> None:
    """Assign TEXT at the end of the &EQU namelist, where it wins."""
    p = workdir / "equparm"
    t = p.read_text()
    assert t.count("&END") == 1
    p.write_text(t.replace("&END", text + "\n     &END"))


def _filament_on_the_box_edge(workdir: Path) -> None:
    # QUEST's box starts at RWMN = 0.10 and has a row at Z = 0: the first
    # filament of group 1 moves onto that grid point.
    p = workdir / "coildata"
    lines = p.read_text().splitlines()
    assert lines[0].startswith(" #1")
    lines[1] = f"{0.10:10.4f}{0.0:10.4f}{0.10:10.4f}"
    p.write_text("\n".join(lines) + "\n")


def _run_program(workdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(PROGRAM)], cwd=workdir, input="R\nQ\n", capture_output=True,
                          text=True, timeout=120)


def test_axis_search_at_the_box_edge_is_an_error(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_params(AXIS_AT_THE_EDGE)
        assert equ.validate() == []
        with pytest.raises(EqulibCalculationFailedError, match="eqaxi: the search"):
            equ.run(1)
        equ.read_parm("equparm")
        equ.run(0)


@NO_PROGRAM
def test_program_exits_2_when_the_axis_search_reaches_the_box(workdir):
    stage("quest", workdir)
    _namelist_adds(workdir, AXIS_AT_THE_EDGE_NML)
    r = _run_program(workdir)
    assert r.returncode == 2 and "axis search reached the box edge" in r.stdout


def test_filament_on_a_grid_point_is_an_error(workdir):
    # flxfun took INT of dlog(0): -2**31 on x86 (xtab out of bounds); on
    # arm64 it saturated and the run went on with the table's last value.
    stage("quest", workdir)
    _filament_on_the_box_edge(workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_param("ISVAC", 1)
        assert equ.validate() == []
        with pytest.raises(EqulibCalculationFailedError, match="flxfun: a current filament"):
            equ.run(1)
        equ.set_param("ISVAC", 0)
        equ.run(0)


@NO_PROGRAM
def test_program_exits_2_on_a_filament_on_a_grid_point(workdir):
    stage("quest", workdir)
    _filament_on_the_box_edge(workdir)
    _namelist_adds(workdir, "ISVAC=1")
    r = _run_program(workdir)
    assert r.returncode == 2 and "stop at flxfun" in r.stdout


# --- the files the library opens ---------------------------------------

_STREAMS_CHILD = r"""
import os, sys
from equlib import Equ, EqulibError
os.symlink("/dev/stdin", "in_link")
alias = "/proc/self/fd/0" if sys.platform.startswith("linux") else "/dev/fd/0"
os.symlink(alias, "fd_link")
with Equ() as e:
    for p in ("in_link", "fd_link"):
        try:
            e.read_parm(p)
            print("ACCEPTED", p)
        except EqulibError as x:
            print("REFUSED", p, x)
        e.set_param_str("KNAMCOIL", p)
        print("COIL", p, [d.message for d in e.validate() if d.param == "KNAMCOIL"])
print("STDIN", repr(sys.stdin.read()))
"""

_STDIN_TEXT = " &EQU NR=17 /\n" * 3


def _streams_child(workdir: Path, **stdin):
    env = {**os.environ, "PYTHONPATH": str(REPO / "python")}
    return subprocess.run([sys.executable, "-c", _STREAMS_CHILD], cwd=workdir,
                          capture_output=True, text=True, timeout=60, env=env, **stdin)


def _assert_refused_and_unread(r, refused: str):
    out = [l for l in r.stdout.splitlines() if l.split(" ")[0] in ("ACCEPTED", "REFUSED",
                                                                    "COIL", "STDIN")]
    assert r.returncode == 0, r.stderr[-2000:]
    assert not [l for l in out if l.startswith("ACCEPTED")], out
    refusals = [l for l in out if l.startswith(("REFUSED", "COIL"))]
    assert len(refusals) == 4 and all(refused in l for l in refusals), refusals
    assert out[-1] == "STDIN " + repr(_STDIN_TEXT), out[-1]


def test_links_to_a_pipe_on_stdin_refused_and_stdin_unread(workdir):
    # fd 0 is a pipe here, as in an MCP stdio server; through a link the
    # name is not under /dev or /proc, and the pipe is not a regular file.
    r = _streams_child(workdir, input=_STDIN_TEXT)
    _assert_refused_and_unread(r, "not a regular file")


def test_links_to_a_file_on_stdin_refused_and_stdin_unread(workdir):
    # fd 0 a regular file: /dev/fd/0 on macOS shares its offset, so a read
    # through it would consume the host's input. The file is the stream's.
    (workdir / "stdin.txt").write_text(_STDIN_TEXT)
    with open(workdir / "stdin.txt") as f:
        r = _streams_child(workdir, stdin=f)
    _assert_refused_and_unread(r, "standard input, output or error")


@pytest.fixture
def quest(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        yield equ


def test_fifo_refused_without_blocking(quest):
    # OPEN of a FIFO blocks until a writer comes; the check comes first.
    os.mkfifo("fifo")
    with pytest.raises(EqulibInvalidParamError, match="not a regular file"):
        quest.read_parm("fifo")
    quest.set_param_str("KNAMCOIL", "fifo")
    assert any(d.param == "KNAMCOIL" and "not a regular file" in d.message
               for d in quest.validate())
    quest.set_param_str("KNAMCOIL", "coildata")
    quest.run(0)
    with pytest.raises(EqulibInvalidParamError, match="not a regular file"):
        quest.write_geqdsk("fifo", overwrite=True)


def test_directory_refused(quest):
    os.mkdir("adir")
    with pytest.raises(EqulibInvalidParamError, match="not a regular file"):
        quest.read_parm("adir")
    quest.run(0)
    with pytest.raises(EqulibInvalidParamError, match="not a regular file"):
        quest.write_geqdsk("adir", overwrite=True)


def test_a_relative_name_that_starts_with_a_blank_is_read(quest, workdir):
    # ' /dev/input' is relative (OPEN keeps the blank): a file under the
    # directory ' ', not under /dev.
    (workdir / " " / "dev").mkdir(parents=True)
    (workdir / " " / "dev" / "input").write_text((workdir / "equparm").read_text())
    quest.read_parm(" /dev/input")
    quest.run(0)


@pytest.mark.parametrize("overwrite", [False, True])
def test_dangling_link_not_followed(quest, workdir, overwrite):
    # The new file is opened with STATUS='NEW' (O_EXCL), which does not
    # create the link's target.
    quest.run(0)
    os.symlink("target", "dangling")
    with pytest.raises(EqulibInvalidParamError, match="cannot be created"):
        quest.write_geqdsk("dangling", overwrite=overwrite)
    assert not (workdir / "target").exists()


def test_long_path_through_a_link_and_dotdot(quest, workdir):
    # Over 80 characters, the file is written from its directory: the
    # directory as the file system resolves it (link/.. is data/, not w/).
    (workdir / "data" / "run").mkdir(parents=True)
    w = workdir / ("w" * 60)
    w.mkdir()
    os.symlink(workdir / "data" / "run", w / "link")
    quest.run(0)
    target = f"{w}/link/../g.geqdsk"
    assert len(target) > 80
    quest.write_geqdsk(target)
    assert (workdir / "data" / "g.geqdsk").stat().st_size > 1_000_000
    assert not (w / "g.geqdsk").exists()


_FSIZE_CHILD = r"""
import os, resource, signal
from equlib import Equ, EqulibError
from equlib.tests._program import stage
stage("quest", ".")
with Equ() as e:
    e.read_parm("equparm")
    e.run(0)
    with open("old.geqdsk", "w") as f:
        f.write("x" * 100)
    signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    resource.setrlimit(resource.RLIMIT_FSIZE, (4096, hard))
    for name, overwrite in (("new.geqdsk", False), ("old.geqdsk", True)):
        try:
            e.write_geqdsk(name, overwrite=overwrite)
            print("WRITTEN", name)
        except EqulibError as x:
            print("FAILED", name, x)
        print("EXISTS", name, os.path.exists(name))
"""


def test_failed_write_removes_only_the_file_it_created(workdir):
    # RLIMIT_FSIZE makes the write fail after the file exists (EFBIG).
    env = {**os.environ, "PYTHONPATH": str(REPO / "python")}
    r = subprocess.run([sys.executable, "-c", _FSIZE_CHILD], cwd=workdir, capture_output=True,
                       text=True, timeout=120, env=env)
    out = [l for l in r.stdout.splitlines() if l.split(" ")[0] in ("WRITTEN", "FAILED",
                                                                    "EXISTS")]
    assert r.returncode == 0, r.stderr[-2000:]
    assert len(out) == 4, out
    assert out[0].startswith("FAILED new.geqdsk") and "the part-written file was removed" in out[0]
    assert out[1] == "EXISTS new.geqdsk False"
    assert out[2].startswith("FAILED old.geqdsk") and "may be incomplete" in out[2]
    assert out[3] == "EXISTS old.geqdsk True"
