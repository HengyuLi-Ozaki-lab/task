"""tr_mcp: the history columns the library names are in ``get_history`` and in its schema with units.

A column the library lists but the schema does not describe fails here. Needs ``tr/libtrapi.so`` (or MONO_LIB_PATH).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
MCP_ROOT = HERE.parents[1]
PYTHON_ROOT = HERE.parents[3]
REPO_ROOT = HERE.parents[4]

for extra in (str(MCP_ROOT.parent), str(PYTHON_ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from tr_mcp import server as srv  # noqa: E402

SO = REPO_ROOT / "tr" / "libtrapi.so"
needs_lib = pytest.mark.skipif(not SO.exists() and not os.environ.get("MONO_LIB_PATH"),
                               reason="libtrapi.so not built")
pytestmark = [pytest.mark.forked, needs_lib]


def _library_names():
    from trlib import Trlib
    with Trlib() as t:
        return t.history_names()


def test_every_library_history_name_has_a_schema_entry_with_a_unit():
    schema = srv.handle_describe_history_schema()
    missing = [n for n in _library_names() if n not in schema["columns"]]
    assert not missing, f"history columns the library exports and the schema does not describe: {missing}"
    assert set(schema["columns"]) == set(_library_names())
    for n, entry in schema["columns"].items():
        assert "unit" in entry and "description" in entry, n


def test_get_history_returns_the_columns_asked_for():
    names = set(_library_names())                # a second live handle is refused: ask before the server opens one
    srv.handle_init()
    try:
        srv.handle_run(6)
        h = srv.handle_get_history(["T", "WPT"])
        assert set(h["columns"]) == {"T", "WPT"} and h["rows"] == 4 and h["full"] is False
        assert len(h["columns"]["T"]) == 4 and h["columns"]["T"][0] == 0.0
        every = srv.handle_get_history(None)
        assert set(every["columns"]) == names
    finally:
        srv.handle_finalize()


def test_get_history_refuses_an_unknown_name():
    srv.handle_init()
    try:
        srv.handle_run(2)
        with pytest.raises(Exception) as exc:
            srv.handle_get_history(["NOSUCH"])
        assert "NOSUCH" in str(exc.value)
    finally:
        srv.handle_finalize()


def test_get_history_is_a_registered_tool():
    pytest.importorskip("mcp")
    import asyncio
    server = srv.build_server()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert "get_history" in names
