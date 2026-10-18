"""eq_mcp's ``save`` tool: the handler, its error mapping, the tool list,
and one save through the real library."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[3]  # .../python
REPO_ROOT = HERE.parents[4]    # repo root
for extra in (str(HERE.parents[2]), str(PYTHON_ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from eq_mcp import server as srv  # noqa: E402
from eqlib import (  # noqa: E402
    EqlibCalculationFailedError,
    EqlibInvalidParamError,
)


class _Eq:
    """Stands in for eqlib.Eq: records a save and the parameters set before
    it, or raises what it is given."""

    def __init__(self, exc=None):
        self.saved = []
        self.params = []
        self._exc = exc

    def set_param(self, name, value):
        self.params.append((name, value))

    def save(self, path):
        if self._exc is not None:
            raise self._exc
        self.saved.append(path)

    def close(self):
        pass


def _serve(monkeypatch, eq):
    state = srv._ServerState()
    monkeypatch.setattr(state, "ensure_open", lambda: eq)
    monkeypatch.setattr(srv, "STATE", state)


def test_handle_save_saves_to_the_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)         # the handler looks at the path first
    eq = _Eq()
    _serve(monkeypatch, eq)
    message = srv.handle_save("out/eq.bin")
    assert eq.saved == ["out/eq.bin"]
    assert "out/eq.bin" in message


def test_handle_save_refuses_an_existing_file_by_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("eq.bin").write_bytes(b"earlier")
    eq = _Eq()
    _serve(monkeypatch, eq)
    with pytest.raises(Exception) as info:
        srv.handle_save("eq.bin")
    assert "exists" in str(info.value) and "overwrite" in str(info.value)
    assert eq.saved == [] and eq.params == []
    assert Path("eq.bin").read_bytes() == b"earlier"


def test_handle_save_does_not_offer_overwrite_for_what_is_not_a_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    os.mkdir("there")
    eq = _Eq()
    _serve(monkeypatch, eq)
    with pytest.raises(Exception) as info:
        srv.handle_save("there")
    assert "not a regular file" in str(info.value) and "overwrite" not in str(info.value)
    assert eq.saved == [] and eq.params == []


def test_handle_save_sets_the_write_mode_itself(monkeypatch, tmp_path):
    """3 (FWOPEN refuses an existing file) unless ``overwrite``, then 0."""
    monkeypatch.chdir(tmp_path)
    eq = _Eq()
    _serve(monkeypatch, eq)
    srv.handle_save("new.bin")
    assert eq.params == [("MODEFW", 3)]
    Path("old.bin").write_bytes(b"earlier")
    srv.handle_save("old.bin", overwrite=True)
    assert eq.params == [("MODEFW", 3), ("MODEFW", 0)]
    assert eq.saved == ["new.bin", "old.bin"]


def test_handle_save_reports_a_save_that_wrote_nothing(monkeypatch):
    _serve(monkeypatch, _Eq(EqlibCalculationFailedError("eq_save: rc=3")))
    with pytest.raises(Exception) as info:      # ToolError, or RuntimeError without the SDK
        srv.handle_save("/no/such/dir/eq.bin")
    assert "calculation failed" in str(info.value)


def test_handle_save_reports_a_blank_path(monkeypatch):
    _serve(monkeypatch, _Eq(EqlibInvalidParamError("eq_save: rc=1")))
    with pytest.raises(Exception) as info:
        srv.handle_save("")
    assert "invalid parameter" in str(info.value)


def test_save_is_listed_by_print_tools(capsys):
    assert srv.main(["--print-tools"]) == 0
    assert "save" in capsys.readouterr().out.split()


@pytest.mark.skipif(
    not Path(os.environ.get("EQLIB_PATH") or REPO_ROOT / "eq" / "libeqapi.so").exists(),
    reason="libeqapi.so not built",
)
def test_save_through_the_real_library(monkeypatch, tmp_path):
    # relative names: KNAMEQ holds 80 characters
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(srv, "STATE", srv._ServerState())
    try:
        srv.handle_init()
        with pytest.raises(Exception) as info:          # no run yet
            srv.handle_save("eq.bin")
        assert "invalid parameter" in str(info.value)
        assert not os.path.exists("eq.bin")

        srv.handle_run(0)
        assert "eq.bin" in srv.handle_save("eq.bin")
        size = os.path.getsize("eq.bin")
        assert size > 0

        # a second save to the same path: refused, then allowed
        Path("eq.bin").write_bytes(b"earlier")
        with pytest.raises(Exception) as info:
            srv.handle_save("eq.bin")
        assert "overwrite" in str(info.value)
        assert Path("eq.bin").read_bytes() == b"earlier"
        assert "eq.bin" in srv.handle_save("eq.bin", overwrite=True)
        assert os.path.getsize("eq.bin") == size

        # a file that appears after the handler's look: FWOPEN's mode 3 holds
        Path("late.bin").write_bytes(b"earlier")
        with monkeypatch.context() as patched:
            patched.setattr(srv.os.path, "lexists", lambda path: False)
            with pytest.raises(Exception) as info:
                srv.handle_save("late.bin")
        assert "calculation failed" in str(info.value)
        assert Path("late.bin").read_bytes() == b"earlier"

        with pytest.raises(Exception) as info:
            srv.handle_save("no_such_dir/eq.bin")
        assert "calculation failed" in str(info.value)
    finally:
        srv.STATE.close()


def test_the_file_modes_are_described_as_file_modes():
    registry = srv.PARAMETER_REGISTRY
    assert "FWOPEN" in registry["MODEFW"]["description"]
    assert "FROPEN" in registry["MODEFR"]["description"]
