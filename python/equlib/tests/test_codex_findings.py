"""Inputs and sequences the Codex review of 2026-11-22 found to hang, end
the process, read unset memory or leak between runs; each is refused
before the run or now behaves as in a fresh process."""
from __future__ import annotations

import subprocess

import pytest

from equlib import Equ, EqulibInvalidParamError
from equlib.tests._geqdsk import assert_same
from equlib.tests._program import PROGRAM, stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


@pytest.fixture
def quest(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        yield equ


def _params(diags):
    return {d.param for d in diags}


@pytest.mark.parametrize("name,value,param", [
    ("NZ", 3, "NZ"),            # eqgrd's csrz recursion: csrz(0), or a loop
    ("NR", 3, "NR"),
    ("IODMAX", 0, "IODMAX"),    # eqode's loop would not run
    ("EODMAX", 1.0, "EODMAX"),
    ("ILIMT", 1, "ILIMT"),      # eqlim's limiter branch reads unset locals
])
def test_refused(quest, name, value, param):
    quest.set_param(name, value)
    assert param in _params(quest.validate())


def test_nv3_with_icp9_refused(quest):
    quest.set_param("NV", 3)
    quest.set_param("ICP[1]", 9)
    assert "NV" in _params(quest.validate())


def test_negative_coil_radius_refused(quest, workdir):
    text = (workdir / "coildata").read_text().replace("    0.1545   -0.5816", "   -0.1545   -0.5816", 1)
    (workdir / "coildata").write_text(text)
    diags = quest.validate()
    assert "KNAMCOIL" in _params(diags) and "R must be > 0" in " ".join(d.message for d in diags)


def test_equal_marker_radii_refused(quest):
    # QUEST's markers 0 and 1 at the same R: eqadj divides by RVAC(1) - RVAC(0).
    quest.set_param("RVAC[1]", 0.28)
    assert "RVAC[1]" in _params(quest.validate())


@pytest.mark.parametrize("path", ["/dev/stdin", "/dev/fd/0", "/proc/self/fd/0"])
def test_device_paths_refused(quest, path):
    with pytest.raises(EqulibInvalidParamError, match="/dev or /proc"):
        quest.read_parm(path)
    quest.set_param_str("KNAMCOIL", path)
    assert "KNAMCOIL" in _params(quest.validate())


def test_device_path_for_geqdsk_refused(quest):
    quest.run(0)
    with pytest.raises(EqulibInvalidParamError, match="/dev or /proc"):
        quest.write_geqdsk("/dev/stdout", overwrite=True)


def test_recovery_after_a_failed_run_without_reset(quest):
    quest.set_param("RVAC[1]", 0.5)
    with pytest.raises(Exception, match="no starting point"):
        quest.run(1)
    quest.read_parm("equparm")
    assert quest.validate() == []          # no stale failure flag
    quest.run(0)
    assert quest.get_state().nr == 257


def test_ieqmax_zero_reports_no_fct_steps(quest):
    quest.set_param("IEQMAX", 0)
    quest.run(1)
    assert quest.get_state().fct_steps == 0


def test_isep0_after_a_diverted_run_equals_fresh(workdir):
    # ITER#1 (ISEP = 1) runs with ISEP = 0 too; QUEST's boundary then reaches
    # the box (test_boundary_at_the_box_edge_is_an_error).
    stage("iter01", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_param("ISEP", 0)
        equ.run(0)
        fresh = equ.get_state()
        equ.write_geqdsk("fresh.geqdsk")
    with Equ() as equ:
        equ.read_parm("equparm")       # ISEP = 1: an X point
        equ.run(0)
        assert equ.get_state().xpoint_status > 0
        equ.set_param("ISEP", 0)
        equ.run(0)
        after = equ.get_state()
        equ.write_geqdsk("after.geqdsk")
    assert after.psi_sep == fresh.psi_sep and after.xpoint_status == fresh.xpoint_status
    assert_same("fresh.geqdsk", "after.geqdsk", rtol=0.0, atol=0.0)


def test_symmetric_run_does_not_fold_the_next_runs_coils(workdir):
    # KNAMCOIL = 'done': the JT-60U coils in memory are inputs; a run with
    # IUDSYM = 1 folded zcoil below the midplane (eqvac0).
    def run(equ):
        equ.set_param_str("KNAMCOIL", "done")
        equ.set_param("IUDSYM", 0)
        equ.run(0)
        equ.write_geqdsk("g", overwrite=True)
        return (workdir / "g").read_text()
    with Equ() as equ:
        fresh = run(equ)
    with Equ() as equ:
        equ.set_param_str("KNAMCOIL", "done")
        equ.set_param("IUDSYM", 1)
        equ.run(0)
        after = run(equ)
    assert after == fresh


@pytest.mark.skipif(not PROGRAM.exists(), reason="equ_nogr not built")
def test_program_exits_nonzero_without_its_coil_file(workdir):
    stage("quest", workdir)
    (workdir / "coildata").unlink()
    r = subprocess.run([str(PROGRAM)], cwd=workdir, input="R\nQ\n", capture_output=True,
                       text=True, timeout=120)
    assert r.returncode == 2 and "cannot open the coil file" in r.stdout


def test_boundary_at_the_box_edge_is_an_error(quest):
    # QUEST without its X point: the boundary reaches the box and eqind
    # indexed psi at -248; it now fails through equ_fail.
    quest.set_param("ISEP", 0)
    with pytest.raises(Exception, match="reaches the edge of the box"):
        quest.run(0)
    quest.set_param("ISEP", 1)
    quest.run(0)
    assert quest.get_state().nr == 257
