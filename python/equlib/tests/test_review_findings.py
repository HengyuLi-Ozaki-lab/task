"""Inputs the third in-house review of 2026-11-22 found to index past EQU's
arrays, or to reach a device through a link or a long path; each is now an
error of the run or refused before it. (The file checks are stat(2)'s since
the second Codex review: test_second_codex_review.py.)"""
from __future__ import annotations

import os
import re
import subprocess
import sys

import pytest

from equlib import Equ, EqulibCalculationFailedError, EqulibInvalidParamError
from equlib.tests._program import PROGRAM, stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


def _params(diags):
    return {d.param for d in diags}


@pytest.mark.parametrize("case,grid,error", [
    ("quest", {"NR": 17, "NZ": 33}, "eqlin: no crossing"),
    ("quest", {"NR": 9}, "eqlin: no crossing"),
    ("quest", {"NR": 17, "NZ": 17}, "eqlin: no crossing"),
    # ITER stops in eqtrc's own walk, which was there before.
    ("iter01", {"NR": 17}, "eqtrc:no starting point"),
])
def test_coarse_grid_is_an_error(workdir, case, grid, error):
    # eqlin's walk along the axis row had no lower bound: QUEST at NR = 17,
    # NZ = 33 read rg at -211 (Task 1's program: a runtime error). QUEST at
    # NR = 17 alone runs, in both.
    stage(case, workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_params(grid)
        assert equ.validate() == []
        with pytest.raises(EqulibCalculationFailedError, match=error):
            equ.run(1)
        equ.set_params({"NR": 257, "NZ": 257})
        equ.run(0)
        assert equ.get_state().nr == 257


@pytest.mark.skipif(not PROGRAM.exists(), reason="equ_nogr not built")
def test_program_exits_2_on_a_coarse_grid(workdir):
    # Outside library mode eqlin's new error stops with exit status 2, as
    # the runtime error (rg at -211) did.
    stage("quest", workdir)
    text = (workdir / "equparm").read_text()
    assert text.count(" &EQU ") == 1
    (workdir / "equparm").write_text(text.replace(" &EQU ", " &EQU NR=17, NZ=33, "))
    r = subprocess.run([str(PROGRAM)], cwd=workdir, input="R\nQ\n", capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 2 and "no flux surface crossing" in r.stdout


@pytest.mark.skipif(not PROGRAM.exists(), reason="equ_nogr not built")
def test_program_exits_2_when_eqtrc_starts_off_the_grid(workdir):
    # The program has no validate: QUEST with 'done' reaches eqtrc's start.
    stage("quest", workdir)
    text = (workdir / "equparm").read_text()
    assert text.count("KNAMCOIL='coildata'") == 1
    (workdir / "equparm").write_text(text.replace("KNAMCOIL='coildata'", "KNAMCOIL='done'"))
    r = subprocess.run([str(PROGRAM)], cwd=workdir, input="R\nQ\n", capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 2 and "starting point is off the grid" in r.stdout


def test_done_with_coil_groups_not_in_memory_refused(workdir):
    # KNAMCOIL = 'done' uses the coils in memory: after init only the
    # JT-60U groups 1..4. QUEST's namelist asks for groups 5 and 6 too,
    # whose filaments at R = 0 give no flux: the run started eqtrc off the
    # grid (Task 1's program: psi at -105).
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_param_str("KNAMCOIL", "done")
        assert {"NCOIL[5]", "NCOIL[6]"} <= _params(equ.validate())
        equ.set_params({"NCOIL[5]": 0, "NCOIL[6]": 0})
        assert equ.validate() == []
        equ.set_param("NCOIL[1]", 71)          # JT-60U's group 1 has 70
        assert "NCOIL[1]" in _params(equ.validate())


def test_done_after_a_run_does_not_use_the_runs_coil_file(workdir):
    # A run reads QUEST's coil file into memory; the inputs keep init's
    # coils, so 'done' after the run is refused as in a fresh process.
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(0)
        equ.set_param_str("KNAMCOIL", "done")
        assert {"NCOIL[5]", "NCOIL[6]"} <= _params(equ.validate())


@pytest.fixture
def quest_links(workdir):
    stage("quest", workdir)
    os.symlink("/dev/stdin", "in_link")
    os.symlink("/dev", "devdir")
    os.symlink("../" * 40 + "dev/stdout", "rel_link")
    # Linux's /proc/self/fd/0 links to "pipe:[n]", which realpath cannot
    # resolve; on macOS the link dangles. Either way it is refused.
    os.symlink("/proc/self/fd/0", "proc_link")
    # OPEN keeps leading blanks: ' lnk' is a name of its own.
    os.symlink("/dev/stdin", " lnk")
    os.symlink("/dev", " devdir")
    with Equ() as equ:
        equ.read_parm("equparm")
        yield equ


# Under pytest fd 0 is a device or a pipe and fd 1 a capture file: a link
# to either is "not a regular file" or one of the process's streams.
STREAM = r"not a regular file|standard input, output or error"
# /proc/self/fd/0 dangles on macOS (no /proc): nothing there to read.
PROC = STREAM if sys.platform.startswith("linux") else None


@pytest.mark.parametrize("path,refused", [
    ("in_link", STREAM), ("devdir/stdin", STREAM), ("rel_link", STREAM),
    ("proc_link", PROC or "cannot open"), (" lnk", STREAM), (" devdir/stdin", STREAM),
    ("/dev/" + "./" * 45 + "stdin", "under /dev or /proc")])
def test_links_to_devices_refused_for_read_parm(quest_links, path, refused):
    with pytest.raises(EqulibInvalidParamError, match=refused):
        quest_links.read_parm(path)


@pytest.mark.parametrize("path,refused", [
    ("in_link", STREAM), ("devdir/stdin", STREAM), ("rel_link", STREAM),
    ("proc_link", PROC or "no coil file"), (" lnk", STREAM)])
def test_links_to_devices_refused_for_the_coil_file(quest_links, path, refused):
    quest_links.set_param_str("KNAMCOIL", path)
    diags = [d for d in quest_links.validate() if d.param == "KNAMCOIL"]
    assert len(diags) == 1
    assert re.search(refused, diags[0].message), diags[0].message


@pytest.mark.parametrize("path,refused", [
    ("rel_link", STREAM), ("proc_link", PROC or "cannot be created"),
    (" devdir/stdout", STREAM),
    # over 80 characters: written from its directory, as "stdout" in /dev
    ("/dev/" + "./" * 45 + "stdout", STREAM)])
def test_links_to_devices_refused_for_geqdsk(quest_links, path, refused):
    quest_links.run(0)
    with pytest.raises(EqulibInvalidParamError, match=refused):
        quest_links.write_geqdsk(path, overwrite=True)
    quest_links.write_geqdsk("ok.geqdsk")
    assert os.path.getsize("ok.geqdsk") > 0


def test_read_only_file_refused_and_kept(workdir):
    # FWOPEN opens an existing file without ACTION: read-only when the
    # process may not write it, and the first WRITE failed.
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(0)
        equ.write_geqdsk("keep.geqdsk")
        before = (workdir / "keep.geqdsk").read_bytes()
        os.chmod("keep.geqdsk", 0o444)
        if os.access("keep.geqdsk", os.W_OK):
            pytest.skip("the process may write a read-only file (root)")
        with pytest.raises(EqulibInvalidParamError, match="not writable"):
            equ.write_geqdsk("keep.geqdsk", overwrite=True)
        assert (workdir / "keep.geqdsk").read_bytes() == before
