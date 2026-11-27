"""The library's G-EQDSK equals the program's (design 2026-11-22, section 14).

For QUEST and ITER#1 of equ/example: the program equ_nogr runs R then E;
the library runs mode 1 on the same input, once through ``read_parm`` and
once through ``set_params`` replaying the same namelist; every number of
the files agrees within 1e-10 (relative). Same machine, same build: this
holds on macOS and Linux alike.
"""
from __future__ import annotations

import pytest

from equlib import Equ
from equlib.tests._geqdsk import assert_same
from equlib.tests._namelist import read_equ_namelist
from equlib.tests._program import PROGRAM, program_geqdsk, stage
from equlib.tests.conftest import requires_lib

pytestmark = [requires_lib,
              pytest.mark.skipif(not PROGRAM.exists(), reason="equ_nogr not built")]


def _library_geqdsk(case, d, route):
    parm = stage(case, d)
    with Equ() as equ:
        if route == "read_parm":
            equ.read_parm(parm.name)
        else:
            equ.set_params(read_equ_namelist(parm))
        equ.run(1)
        equ.write_geqdsk("lib.geqdsk")
    return d / "lib.geqdsk"


@pytest.mark.parametrize("route", ["read_parm", "set_params"])
@pytest.mark.parametrize("case", ["quest", "iter01"])
def test_library_equals_program(case, route, workdir):
    prog_dir = workdir / "prog"
    prog_dir.mkdir()
    prog = program_geqdsk(case, prog_dir)
    n = assert_same(prog, _library_geqdsk(case, workdir, route), rtol=1e-10)
    assert n > 257 * 257
