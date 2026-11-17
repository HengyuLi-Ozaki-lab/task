"""tr_mcp: the library's output names are in ``get_state``, in the schema with units, and in ``get_history``.

A name the library lists but the schema does not describe fails here, so a client never reads a number it
cannot interpret. The integration tests need ``tr/libtrapi.so`` (or MONO_LIB_PATH).
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


def _library_names(kind):
    from trlib import Trlib
    with Trlib() as t:
        return t.scalar_names() if kind == "scalar" else t.history_names()


def test_every_library_scalar_has_a_schema_entry_with_a_unit():
    props = srv.handle_describe_state_schema()["properties"]["scalars"]["properties"]
    missing = [n for n in _library_names("scalar") if n not in props]
    assert not missing, f"scalars the library exports and the schema does not describe: {missing}"
    for n, entry in props.items():
        assert "unit" in entry and "description" in entry, n


def test_the_schema_describes_no_scalar_the_library_lacks():
    props = srv.handle_describe_state_schema()["properties"]["scalars"]["properties"]
    assert set(props) == set(_library_names("scalar"))


def test_get_state_returns_all_the_scalars():
    names = set(_library_names("scalar"))        # a second live handle is refused: ask before the server opens one
    srv.handle_init()
    try:
        srv.handle_run(6)
        state = srv.handle_get_state()
        assert set(state["scalars"]) == names
        assert state["scalars"]["WPT"] > 0.0
    finally:
        srv.handle_finalize()
