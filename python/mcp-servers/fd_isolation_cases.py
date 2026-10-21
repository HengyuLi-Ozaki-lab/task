"""Checks of the fd isolation that every stdio server has to pass.

Not collected by pytest: each server's ``tests/test_fd_isolation.py`` calls
these with its own module name, so that a run of one server's directory
includes its share; ``python/tests/test_fd_isolation.py`` holds the checks of
the shared module itself, and checks that every server calls every case here.
A module that imports this one registers it for assertion rewriting first, so
that a failure shows the values.

Every check runs in a fresh interpreter: the redirect is process-global, and
in the test process it would take pytest's own capture of fd 1 with it.
"""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

MCP_ROOT = Path(__file__).resolve().parent                 # <repo>/python/mcp-servers
PYTHON_ROOT = MCP_ROOT.parent                              # <repo>/python
REPO_ROOT = PYTHON_ROOT.parent

# What the stdio transport, the Fortran library and the server's log do, in
# that order. The MCP SDK writes JSON-RPC through ``sys.stdout.buffer`` (wrapped
# in a TextIOWrapper of its own, flushed after every message); WRITE(6,...)
# goes straight to fd 1; the log goes to fd 2.
STUB_SERVER = """
import _fd_isolation
class _Stdio:
    def run(self):
        sys.stdout.buffer.write(b"JSONRPC-MARKER "); sys.stdout.buffer.flush()
        os.write(1, b"FORTRAN-MARKER ")
        os.write(2, b"STDERR-MARKER ")
def _build_server():
    # the isolation is in place before the server is built, not only before it runs
    assert _fd_isolation.installed(), "build_server() ran before the isolation was installed"
    return _Stdio()
def _stub(srv):
    srv.MCP_AVAILABLE = True          # build_server is replaced: the SDK is not needed
    srv.build_server = _build_server
"""

_MAIN_WITH_STUB = ("import importlib, os, sys\n"
                   "srv = importlib.import_module(sys.argv[1] + '.server')\n" + STUB_SERVER + """
_stub(srv)
assert srv.main([]) == 0
""")


def env():
    inherited = [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    return {**os.environ,
            "PYTHONPATH": os.pathsep.join([str(PYTHON_ROOT), str(MCP_ROOT), *inherited])}


def run(code, *args, stderr=subprocess.PIPE, preexec_fn=None):
    out = subprocess.run([sys.executable, "-c", textwrap.dedent(code), *args], env=env(),
                         cwd=str(REPO_ROOT), stdin=subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=stderr, preexec_fn=preexec_fn,
                         encoding="utf-8", errors="replace", timeout=60)
    assert out.returncode == 0, (out.stdout or "")[-1000:] + (out.stderr or "")[-2000:]
    return out


# ----- installed by main(), by nothing else -----

def import_leaves_fd1_and_sys_stdout_alone(server):
    out = run("""
        import importlib, os, sys
        before = os.fstat(1); stdout = sys.stdout
        srv = importlib.import_module(sys.argv[1] + ".server")
        import _fd_isolation
        after = os.fstat(1)
        print("fd1_same", (before.st_dev, before.st_ino) == (after.st_dev, after.st_ino))
        print("stdout_same", stdout is sys.stdout)
        print("shared", srv._fd_isolation is _fd_isolation)
        print("installed", _fd_isolation.installed())
        sys.stdout.flush()               # the prints first: os.write is not buffered
        os.write(1, b"FD1-MARKER")
    """, server)
    assert out.stdout.split() == ["fd1_same", "True", "stdout_same", "True",
                                  "shared", "True", "installed", "False", "FD1-MARKER"]
    assert "FD1-MARKER" not in out.stderr


def main_installs_the_isolation_before_the_stdio_server_is_built(server):
    out = run(_MAIN_WITH_STUB + "assert _fd_isolation.installed()\n", server)
    assert out.stdout == "JSONRPC-MARKER "
    assert "FORTRAN-MARKER" in out.stderr and "STDERR-MARKER" in out.stderr


def flag_installs_nothing(server, flag):
    """``--help`` and ``--print-tools`` return before the isolation."""
    out = run("""
        import importlib, os, sys
        srv = importlib.import_module(sys.argv[1] + ".server")
        import _fd_isolation
        assert srv.main([sys.argv[2]]) == 0
        print("installed", _fd_isolation.installed())
        sys.stdout.flush()
        os.write(1, b"FD1-MARKER")
    """, server, flag)
    assert "installed False" in out.stdout
    assert "FD1-MARKER" in out.stdout and "FD1-MARKER" not in out.stderr
    expected = server.replace("_", "-") if flag == "--help" else "run_and_get_state"
    assert expected in out.stdout


def missing_sdk_installs_nothing(server):
    out = run("""
        import importlib, os, sys
        srv = importlib.import_module(sys.argv[1] + ".server")
        import _fd_isolation
        srv.MCP_AVAILABLE = False
        rc = srv.main([])
        print("rc", rc, "installed", _fd_isolation.installed())
        sys.stdout.flush()
        os.write(1, b"FD1-MARKER")
    """, server)
    assert "rc 2 installed False" in out.stdout
    assert "FD1-MARKER" in out.stdout and "FD1-MARKER" not in out.stderr


# ----- descriptor layouts in which dup2(2, 1) alone does nothing -----

def stderr_merged_into_stdout_keeps_fortran_output_off_the_stream(server):
    # The host started the server with 2>&1: fd 1 and fd 2 are the same pipe.
    # What the server writes to stderr is on the stream by the host's choice;
    # what the library writes to fd 1 is not.
    out = run(_MAIN_WITH_STUB, server, stderr=subprocess.STDOUT)
    assert "JSONRPC-MARKER" in out.stdout and "STDERR-MARKER" in out.stdout
    assert "FORTRAN-MARKER" not in out.stdout
    assert "stdout and stderr of this MCP server are the same file" in out.stdout


def closed_fd2_keeps_everything_but_json_rpc_off_the_pipe(server):
    # With fd 2 closed, dup(1) returns 2 and dup2(2, 1) would copy the pipe
    # back onto fd 1; and without a descriptor of its own, what is written to
    # fd 2 afterwards would be on the pipe as well. POSIX only (preexec_fn).
    out = run(_MAIN_WITH_STUB, server, preexec_fn=lambda: os.close(2))
    assert out.stdout == "JSONRPC-MARKER "
