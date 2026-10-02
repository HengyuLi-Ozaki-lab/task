"""The fd isolation of the MCP servers: what it does, and when it runs.

Importing a server installs nothing (k-yoshimi/task#227 item 1; see
``eq_mcp/tests/test_import_isolation.py``). Each server installs the
isolation from its own ``main()``, once per PROCESS: tot_mcp imports several
of the others, and a second ``dup(1)`` would save the already-redirected
stderr as the "JSON-RPC pipe", so every response would then go to stderr.

These tests CALL the installers (an import-only test passes whether or not
the once-per-process guard exists) and run ``main()`` with a stand-in for the
stdio server, in a fresh subprocess each: the redirect is process-global and
irreversible.
"""
import itertools
import os
import subprocess
import sys
from pathlib import Path

import pytest

PYTHON_ROOT = Path(__file__).resolve().parents[3]          # <repo>/python
SERVERS = ["eq_mcp", "tr_mcp", "fp_mcp", "tot_mcp"]


def _run(code):
    env = {**os.environ,
           "PYTHONPATH": os.pathsep.join([str(PYTHON_ROOT), str(PYTHON_ROOT / "mcp-servers")])}
    return subprocess.run([sys.executable, "-c", code], env=env, capture_output=True,
                          stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace",
                          timeout=60)


@pytest.mark.parametrize("first,second", list(itertools.permutations(SERVERS, 2)))
def test_two_servers_in_one_process_keep_stdout_on_the_pipe(first, second):
    code = (f"import {first}.server as a, {second}.server as b, os, sys\n"
            "a._install_fd_isolation()\n"
            "b._install_fd_isolation()\n"       # unguarded, this saves stderr as the "pipe"
            "sys.stdout.write('JSONRPC-MARKER'); sys.stdout.flush()\n"
            "os.write(1, b'FORTRAN-MARKER')\n")  # what Fortran's WRITE(6) does
    out = _run(code)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "JSONRPC-MARKER" in out.stdout
    assert "JSONRPC-MARKER" not in out.stderr
    assert "FORTRAN-MARKER" in out.stderr
    assert "FORTRAN-MARKER" not in out.stdout


@pytest.mark.parametrize("server", SERVERS)
def test_main_installs_the_isolation_before_the_stdio_server_starts(server):
    code = (f"import {server}.server as s, os, sys\n"
            "s.MCP_AVAILABLE = True\n"            # build_server is stubbed: the SDK is not needed
            "class _Stdio:\n"
            "    def run(self):\n"               # the transport's first act: JSON-RPC on sys.stdout
            "        sys.stdout.write('JSONRPC-MARKER'); sys.stdout.flush()\n"
            "        os.write(1, b'FORTRAN-MARKER')\n"
            "s.build_server = lambda: _Stdio()\n"
            "s.main([])\n")
    out = _run(code)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "JSONRPC-MARKER" in out.stdout and "JSONRPC-MARKER" not in out.stderr
    assert "FORTRAN-MARKER" in out.stderr and "FORTRAN-MARKER" not in out.stdout, (
        f"{server}.main() did not install the fd isolation before server.run()")
