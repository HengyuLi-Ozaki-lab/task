"""``Equ.write_geqdsk``: refusals, overwrite, a file that cannot be written."""
from __future__ import annotations

from pathlib import Path

import pytest

from equlib import Equ, EqulibCalculationFailedError, EqulibInvalidParamError
from equlib.tests._program import stage
from equlib.tests.conftest import requires_lib

pytestmark = requires_lib


@pytest.fixture
def solved(workdir):
    stage("quest", workdir)
    with Equ() as equ:
        equ.read_parm("equparm")
        equ.run(0)
        yield equ


def test_before_a_run(workdir):
    with Equ() as equ:
        with pytest.raises(EqulibInvalidParamError, match="no equilibrium"):
            equ.write_geqdsk("g")


def test_blank_and_long_paths(solved):
    with pytest.raises(EqulibInvalidParamError, match="blank"):
        solved.write_geqdsk(" ")
    with pytest.raises(EqulibInvalidParamError, match="longer than 80"):
        solved.write_geqdsk("g" * 81)


def test_existing_file(solved, workdir):
    (workdir / "g").write_text("old\n")
    with pytest.raises(EqulibInvalidParamError, match="exists"):
        solved.write_geqdsk("g")
    assert (workdir / "g").read_text() == "old\n"
    solved.write_geqdsk("g", overwrite=True)
    assert (workdir / "g").stat().st_size > 1_000_000


def test_directory_missing(solved):
    with pytest.raises(EqulibCalculationFailedError, match="not written"):
        solved.write_geqdsk("no-such-dir/g")


def test_a_path_longer_than_80_characters(solved, workdir):
    deep = workdir / ("d" * 60) / ("e" * 30)
    deep.mkdir(parents=True)
    target = deep / "long.geqdsk"
    assert len(str(target)) > 80
    solved.write_geqdsk(str(target))
    assert target.stat().st_size > 1_000_000
    assert not (workdir / "long.geqdsk").exists()
    assert Path.cwd() == workdir
    # Refused (exists, no overwrite): the directory comes back too.
    with pytest.raises(EqulibInvalidParamError, match="exists"):
        solved.write_geqdsk(str(target))
    assert Path.cwd() == workdir
    solved.write_geqdsk(str(target), overwrite=True)
    assert Path.cwd() == workdir
