"""Importing several MCP servers into one process (as tot_mcp does) must
keep sys.stdout on the original JSON-RPC pipe: each server's import-time
fd isolation may run only once per process."""
import itertools
import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON_ROOT = Path(__file__).resolve().parents[3]          # <repo>/python


@pytest.mark.parametrize("first,second", list(itertools.permutations(["eq_mcp", "tr_mcp", "fp_mcp"], 2)))
def test_two_servers_in_one_process_keep_stdout_on_the_pipe(first, second):
    code = (f"import {first}.server, {second}.server, sys\n"
            "sys.stdout.write('JSONRPC-MARKER'); sys.stdout.flush()\n")
    env = {**os.environ,
           "PYTHONPATH": os.pathsep.join([str(PYTHON_ROOT), str(PYTHON_ROOT / "mcp-servers")])}
    out = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
                         text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "JSONRPC-MARKER" in out.stdout
    assert "JSONRPC-MARKER" not in out.stderr
