"""equ_mcp over the real stdio transport: init, read_parm, run, write_geqdsk.

Spawns ``python -m equ_mcp.server`` in a directory holding the QUEST
example and speaks JSON-RPC to it; the solver's unit-6 output must not
reach the JSON-RPC stream (the fd isolation), and the file must be there.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve()
MCP_ROOT = HERE.parents[2]
PYTHON_ROOT = HERE.parents[3]
for extra in (str(MCP_ROOT), str(PYTHON_ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

pytest.importorskip("mcp", reason="Python MCP SDK (`mcp`) not installed")
from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

from equ_mcp import server as srv  # noqa: E402
from equlib import _ffi  # noqa: E402
from equlib.tests._program import stage  # noqa: E402


@pytest.mark.skipif(not srv.MCP_AVAILABLE, reason="mcp.server.fastmcp not installed")
@pytest.mark.skipif(not _ffi.default_lib_path().exists(), reason="libequapi.so not built")
def test_quest_through_mcp(tmp_path):
    stage("quest", tmp_path)

    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "equ_mcp.server"], cwd=str(tmp_path),
            env={**os.environ, "PYTHONPATH": os.pathsep.join(
                p for p in (str(MCP_ROOT), str(PYTHON_ROOT), os.environ.get("PYTHONPATH", ""))
                if p)})
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                await session.call_tool("init", {})
                await session.call_tool("read_parm", {"path": "equparm"})
                v = await session.call_tool("validate", {})
                assert not v.isError
                assert all(json.loads(c.text) == [] for c in v.content) or not v.content
                res = await session.call_tool("run", {"mode": 1})
                assert not res.isError, res.content
                st = await session.call_tool("get_state", {})
                state = json.loads(st.content[0].text)
                assert state["NR"] == 257 and state["scalars"]["MODE"] == 1
                g = await session.call_tool("write_geqdsk", {"path": "mcp.geqdsk"})
                assert not g.isError, g.content
                bad = await session.call_tool("run", {"mode": 2})
                assert bad.isError and "not implemented" in bad.content[0].text

    asyncio.run(run())
    assert (tmp_path / "mcp.geqdsk").stat().st_size > 1_000_000
