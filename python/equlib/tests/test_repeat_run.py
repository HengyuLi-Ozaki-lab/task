"""Each run starts from the inputs as set (design, sections 5 and 9.3).

A second run in the same process, a run after another case, and a run
after a set that follows a run all give the result of a fresh process.
"""
from __future__ import annotations

from equlib import Equ
from equlib.tests._geqdsk import assert_same
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


def test_second_run_equals_first(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(1)
        equ.write_geqdsk("first.geqdsk")
        equ.run(1)
        equ.write_geqdsk("second.geqdsk")
    assert_same("first.geqdsk", "second.geqdsk", rtol=0.0, atol=0.0)


def test_run_after_another_case_equals_fresh(workdir, monkeypatch):
    # Paths stay relative (KNAMCOIL and G-EQDSK paths hold 80 characters):
    # each case runs in its own directory.
    a = workdir / "a"
    b = workdir / "b"
    a.mkdir()
    b.mkdir()
    stage("iter01", a)
    stage("quest", b)
    monkeypatch.chdir(b)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(1)
        equ.write_geqdsk("fresh.geqdsk")
    with Equ() as equ:
        monkeypatch.chdir(a)
        equ.read_parm("equparm")
        equ.run(1)
        equ.reset()
        monkeypatch.chdir(b)
        equ.read_parm("equparm")
        equ.run(1)
        equ.write_geqdsk("after.geqdsk")
    assert_same(b / "fresh.geqdsk", b / "after.geqdsk", rtol=0.0, atol=0.0)


def test_set_after_run_changes_the_input(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(0)
        equ.set_param("TCUR", 0.28)
        equ.run(0)
        equ.write_geqdsk("after.geqdsk")
        equ.reset()
        equ.read_parm("equparm")
        equ.set_param("TCUR", 0.28)
        equ.run(0)
        equ.write_geqdsk("direct.geqdsk")
    assert_same("after.geqdsk", "direct.geqdsk", rtol=0.0, atol=0.0)
