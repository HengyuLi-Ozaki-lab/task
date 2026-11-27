"""``Equ.read_parm``: an &EQU namelist file, read by EQU's eqnlin."""
from __future__ import annotations

import pytest

from equlib import Equ, EqulibInvalidParamError
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


def test_missing_file(workdir):
    with Equ() as equ:
        with pytest.raises(EqulibInvalidParamError, match="cannot open"):
            equ.read_parm("no-such-equparm")


def test_no_equ_group(workdir):
    (workdir / "other").write_text(" &OTHER X=1 &END\n")
    with Equ() as equ:
        with pytest.raises(EqulibInvalidParamError, match="no &EQU namelist"):
            equ.read_parm("other")


def test_failed_read_is_undone(workdir):
    stage("quest", workdir)
    (workdir / "bad").write_text(" &EQU NV=1, NOSUCH=1 &END\n")
    with Equ() as equ:
        equ.read_parm("equparm")
        with pytest.raises(EqulibInvalidParamError, match="could not be read"):
            equ.read_parm("bad")
        # NV=1 came before the unknown name; it is undone with the read.
        assert equ.validate() == []


def test_read_overrides_only_what_it_names(workdir):
    stage("quest", workdir)
    (workdir / "tcur").write_text(" &EQU TCUR=0.3 &END\n")
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_param("NV", 1)
        equ.read_parm("tcur")
        assert [d.param for d in equ.validate()] == ["NV"]


def test_set_after_read_overrides(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.set_param("NV", 1)
        assert [d.param for d in equ.validate()] == ["NV"]


def test_c_level_path_limits(workdir):
    with Equ() as equ:
        assert equ._lib.equ_read_parm(b"a" * 1100) == 1
        assert "longer than 1023" in equ.last_error()
        assert equ._lib.equ_read_parm(b"") == 1
        assert "blank" in equ.last_error()
