"""eq_mcp.get_psi_rz returns serialisable JSON with nrg/nzg/psi_rz."""
from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client


def test_get_psi_rz_via_mcp():
    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "eq_mcp.server"],
            env={**os.environ},
        )
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                result = await session.call_tool("get_psi_rz", {})
                payload = json.loads(result.content[0].text)
                assert "nrg" in payload and "nzg" in payload
                assert payload["nrg"] == 33 and payload["nzg"] == 33
                assert len(payload["psi_rz"]) == 33
                assert len(payload["psi_rz"][0]) == 33
    asyncio.run(run())
