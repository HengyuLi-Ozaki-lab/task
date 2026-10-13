"""The fd isolation of eq_mcp, tr_mcp and tot_mcp is installed by ``main()``,
never by an import (#227 item 1).

The isolation (``dup(1)`` / ``dup2(2, 1)`` / a new ``sys.stdout`` on the saved
pipe) keeps Fortran ``WRITE(6,...)`` off the JSON-RPC pipe of a stdio server.
Run at module scope it would redirect fd 1 of whatever process imports a
server: pytest during collection, a notebook, an embedding application, and
tot_mcp, which imports its siblings for their parameter registries.

Every check runs in a fresh interpreter: the redirect is process-global, and
in the test process it would take pytest's own capture of fd 1 with it.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PYTHON_ROOT = Path(__file__).resolve().parents[3]          # <repo>/python
REPO_ROOT = PYTHON_ROOT.parent
SERVERS = ["eq_mcp", "tr_mcp", "tot_mcp"]

# What the stdio transport and the Fortran library do, in that order:
# JSON-RPC through sys.stdout, WRITE(6,...) straight to fd 1.
_STUB_SERVER = """
class _Stdio:
    def run(self):
        sys.stdout.write("JSONRPC-MARKER"); sys.stdout.flush()
        os.write(1, b"FORTRAN-MARKER")
def _build_server():
    # the isolation is in place before the server is built, not only before it runs
    assert srv._FD_ISOLATION_INSTALLED, "build_server() ran before the isolation was installed"
    return _Stdio()
srv.MCP_AVAILABLE = True          # build_server is replaced: the SDK is not needed
srv.build_server = _build_server
"""


def _run(code, *args):
    env = {**os.environ,
           "PYTHONPATH": os.pathsep.join([str(PYTHON_ROOT), str(PYTHON_ROOT / "mcp-servers")])}
    out = subprocess.run([sys.executable, "-c", textwrap.dedent(code), *args], env=env,
                         cwd=str(REPO_ROOT), capture_output=True, stdin=subprocess.DEVNULL,
                         encoding="utf-8", errors="replace", timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    return out


@pytest.mark.parametrize("server", SERVERS)
def test_import_leaves_fd1_and_sys_stdout_alone(server):
    out = _run("""
        import importlib, os, sys
        before = os.fstat(1); stdout = sys.stdout
        srv = importlib.import_module(sys.argv[1] + ".server")
        after = os.fstat(1)
        print("fd1_same", (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino))
        print("stdout_same", stdout is sys.stdout)
        print("hook", callable(getattr(srv, "_install_fd_isolation", None)))
        print("installed", srv._FD_ISOLATION_INSTALLED)
        sys.stdout.flush()               # the prints first: os.write is not buffered
        os.write(1, b"FD1-MARKER")
    """, server)
    assert out.stdout.split() == ["fd1_same", "True", "stdout_same", "True",
                                  "hook", "True", "installed", "False", "FD1-MARKER"]
    assert "FD1-MARKER" not in out.stderr


@pytest.mark.parametrize("server", SERVERS)
def test_main_installs_the_isolation_before_the_stdio_server_starts(server):
    out = _run("import importlib, os, sys\n"
               "srv = importlib.import_module(sys.argv[1] + '.server')\n" + _STUB_SERVER + """
assert srv.main([]) == 0
assert srv._FD_ISOLATION_INSTALLED
""", server)
    assert "JSONRPC-MARKER" in out.stdout and "JSONRPC-MARKER" not in out.stderr
    assert "FORTRAN-MARKER" in out.stderr and "FORTRAN-MARKER" not in out.stdout


@pytest.mark.parametrize("server", SERVERS)
def test_installing_twice_keeps_sys_stdout_on_the_pipe(server):
    # A second dup(1) would save the already-redirected stderr as "the pipe".
    out = _run("""
        import importlib, os, sys
        srv = importlib.import_module(sys.argv[1] + ".server")
        srv._install_fd_isolation()
        srv._install_fd_isolation()
        sys.stdout.write("JSONRPC-MARKER"); sys.stdout.flush()
        os.write(1, b"FORTRAN-MARKER")
    """, server)
    assert "JSONRPC-MARKER" in out.stdout and "JSONRPC-MARKER" not in out.stderr
    assert "FORTRAN-MARKER" in out.stderr and "FORTRAN-MARKER" not in out.stdout


@pytest.mark.parametrize("server", SERVERS)
@pytest.mark.parametrize("flag", ["--help", "--print-tools"])
def test_help_and_print_tools_install_nothing(server, flag):
    out = _run("""
        import importlib, os, sys
        srv = importlib.import_module(sys.argv[1] + ".server")
        assert srv.main([sys.argv[2]]) == 0
        print("installed", srv._FD_ISOLATION_INSTALLED)
        sys.stdout.flush()
        os.write(1, b"FD1-MARKER")
    """, server, flag)
    assert "installed False" in out.stdout
    assert "FD1-MARKER" in out.stdout and "FD1-MARKER" not in out.stderr
    expected = server.replace("_", "-") if flag == "--help" else "run_and_get_state"
    assert expected in out.stdout


@pytest.mark.parametrize("server", SERVERS)
def test_missing_sdk_installs_nothing(server):
    out = _run("""
        import importlib, os, sys
        srv = importlib.import_module(sys.argv[1] + ".server")
        srv.MCP_AVAILABLE = False
        rc = srv.main([])
        print("rc", rc, "installed", srv._FD_ISOLATION_INSTALLED)
        sys.stdout.flush()
        os.write(1, b"FD1-MARKER")
    """, server)
    assert "rc 2 installed False" in out.stdout
    assert "FD1-MARKER" in out.stdout and "FD1-MARKER" not in out.stderr


def test_tot_mcp_main_leaves_the_siblings_it_imports_uninstalled():
    # tot_mcp imports tr_mcp (and its other siblings) for their registries.
    # Only the server whose main() runs installs the isolation.
    out = _run("import os, sys\nimport tot_mcp.server as srv\n" + _STUB_SERVER + """
import tr_mcp.server as tr
assert srv.main([]) == 0
sys.stdout.write(" tot=%s tr=%s" % (srv._FD_ISOLATION_INSTALLED, tr._FD_ISOLATION_INSTALLED))
sys.stdout.flush()
""")
    assert "tot=True tr=False" in out.stdout
