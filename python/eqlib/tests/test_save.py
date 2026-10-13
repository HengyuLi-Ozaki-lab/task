"""Eq.save(): the equilibrium file is written and loads back, and a save
that wrote nothing is an error (#227 item 3).

The tests work in a temporary directory with relative file names: KNAMEQ
holds 80 characters, and a temporary directory's own path can be longer.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

import eqlib

_HERE = Path(__file__).resolve()
_DEFAULT_SO = _HERE.parents[3] / "eq" / "libeqapi.so"


def _resolved_so() -> Path:
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    return _DEFAULT_SO


pytestmark = pytest.mark.skipif(
    not _resolved_so().exists(), reason="libeqapi.so not built"
)


@pytest.fixture(autouse=True)
def _in_tmp_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def _solved():
    """An Eq with the analytic equilibrium of the defaults computed."""
    e = eqlib.Eq()
    e.run(0)
    return e


def _files():
    """The working directory's entries. Compared before and after a refused
    save: a run may leave files of its own there (EQ_REGRESS_DUMP)."""
    return sorted(os.listdir("."))


def test_save_writes_a_file_that_loads_back():
    """The file of ``save`` is what ``MODELG=3`` + ``KNAMEQ`` reads."""
    with _solved() as e:
        saved = e.get_state()
        e.save("eq.bin")
    assert os.path.getsize("eq.bin") > 0

    with eqlib.Eq() as e:
        e.set_param("MODELG", 3)
        e.set_param_str("KNAMEQ", "eq.bin")
        e.run(1)                        # eq_load of the TASK/EQ file
        loaded = e.get_state()

    # Records of the file, read back as they were written.
    assert (loaded.nrgmax, loaded.nzgmax, loaded.npsmax) == (
        saved.nrgmax, saved.nzgmax, saved.npsmax)
    assert loaded.rg == saved.rg and loaded.zg == saved.zg
    assert loaded.psips == saved.psips and loaded.ppps == saved.ppps
    # Recomputed from the loaded fields after the load (EQCALQ).
    for name in ("raxis", "zaxis", "psi0", "psipa", "psita"):
        assert loaded.scalars[name] == pytest.approx(saved.scalars[name], rel=1e-9), name


def test_save_accepts_a_pathlib_path():
    with _solved() as e:
        e.save(Path("eq.bin"))
    assert os.path.getsize("eq.bin") > 0


def test_save_before_any_run_is_refused():
    """There is no equilibrium to write, and the file EQSAVE would produce
    ends the process that loads it."""
    with eqlib.Eq() as e:
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("eq.bin")
    assert not os.path.exists("eq.bin")


def test_save_after_a_run_that_failed_is_refused():
    """A run that fails leaves the fields part-way: they are no longer the
    equilibrium of the run before it. (MODELG is set before the good run and
    only a file name after it, so that nothing but the failed run stands
    between that run and the save.)"""
    with eqlib.Eq() as e:
        e.set_param("MODELG", 3)
        e.run(0)
        e.set_param_str("KNAMEQ", "no_such_file")
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("eq.bin")
        assert not os.path.exists("eq.bin")
        e.run(0)                        # and a good run makes it savable again
        e.save("eq.bin")
    assert os.path.getsize("eq.bin") > 0


def test_a_failed_eqdsk_load_does_not_make_old_fields_savable():
    """The load of a missing EQDSK file used to return success (EQ_READ kept
    EQCALQ's code, not EQDSKR's), over the fields of the earlier run and
    with whatever parameters had been set since."""
    with _solved() as e:
        e.set_param("PP0", 123.0)
        e.set_param("MODELG", 5)
        e.set_param_str("KNAMEQ", "no_such_file")
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.run(1)
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("eq.bin")
    assert not os.path.exists("eq.bin")


def test_save_after_a_parameter_change_waits_for_the_next_run():
    """EQSAVE writes the parameters and counts as they stand, over fields
    that were computed for the old ones: a grid count raised after the run
    gave a file that stopped the process loading it."""
    with _solved() as e:
        e.set_param("NRGMAX", 65)
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("eq.bin")
        assert not os.path.exists("eq.bin")
        e.run(0)                        # the equilibrium of the new count
        e.save("eq.bin")
    assert os.path.getsize("eq.bin") > 0


def test_save_is_still_allowed_after_the_file_modes_are_set():
    """MODEFR and MODEFW say how a file is opened, not what the equilibrium
    is."""
    with _solved() as e:
        e.set_param("MODEFR", 0)
        e.set_param("MODEFW", 0)
        e.save("eq.bin")
    assert os.path.getsize("eq.bin") > 0


def test_save_raises_when_directory_missing():
    """FWOPEN cannot create the file: the save is an error, not EQ_OK."""
    with _solved() as e:
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.save("no_such_dir/eq.bin")
    assert not os.path.exists("no_such_dir")


def test_save_wants_a_path():
    with _solved() as e:
        with pytest.raises(TypeError):
            e.save(None)


def test_save_rejects_blank_path():
    """A blank KNAMEQ can never produce a file."""
    with _solved() as e:
        before = _files()
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("")
        assert _files() == before


def test_save_takes_80_bytes_and_refuses_81():
    """KNAMEQ is CHARACTER(LEN=80): a longer path is refused, not cut."""
    with _solved() as e:
        e.save("x" * 80)
        assert os.path.getsize("x" * 80) > 0
        before = _files()
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("y" * 81)
        assert _files() == before


def test_save_refuses_a_path_that_ends_in_a_blank():
    """Fortran drops a trailing blank: ``"result "`` would be written as
    ``"result"``, over whatever is there."""
    Path("result").write_bytes(b"something else")
    with _solved() as e:
        before = _files()
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("result ")
        assert _files() == before
    assert Path("result").read_bytes() == b"something else"


def test_save_raises_when_reopen_refused_and_an_earlier_file_exists():
    """A repeat save must not pass for a success because of the first file.

    After one successful save, a save that fails leaves the earlier file in
    place, and "a non-empty file exists afterwards" holds. MODEFW=3 makes
    FWOPEN refuse an existing file; EQSAVE reports that through its
    argument.
    """
    with _solved() as e:
        e.save("eq.bin")
        first = Path("eq.bin").read_bytes()
        assert first

        e.set_param("MODEFW", 3)
        with pytest.raises(eqlib.EqlibCalculationFailedError):
            e.save("eq.bin")

    # the earlier file is left exactly as it was
    assert Path("eq.bin").read_bytes() == first


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root writes to a read-only file",
)
def test_save_onto_a_read_only_file_is_an_error_not_an_abort():
    """An existing file without write permission is opened for reading by
    FWOPEN, which then returns 0; the first WRITE of EQSAVE fails. That is
    an error return, not the end of the process."""
    with _solved() as e:
        e.save("eq.bin")
        first = Path("eq.bin").read_bytes()
        os.chmod("eq.bin", 0o444)
        try:
            with pytest.raises(eqlib.EqlibCalculationFailedError):
                e.save("eq.bin")
        finally:
            os.chmod("eq.bin", 0o644)
        # the handle is still usable
        e.save("again.bin")
    assert Path("eq.bin").read_bytes() == first
    assert os.path.getsize("again.bin") > 0


@pytest.mark.parametrize("modefw", [1, 2, 4, 5, 6, 7])
def test_save_refuses_the_file_modes_that_ask_on_unit_5(modefw):
    """With MODEFW 1 or 2 FWOPEN asks Y/N before it overwrites, with 4 to 7
    it asks for the file name, both on unit 5: the JSON-RPC pipe of a stdio
    server. Only 0 (overwrite) and 3 (refuse an existing file) are taken."""
    with _solved() as e:
        e.save("eq.bin")
        first = Path("eq.bin").read_bytes()
        e.set_param("MODEFW", modefw)
        before = _files()
        with pytest.raises(eqlib.EqlibInvalidParamError):
            e.save("eq.bin")
        assert _files() == before
    assert Path("eq.bin").read_bytes() == first
