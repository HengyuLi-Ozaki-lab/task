"""tr_mcp's share of the fd-isolation checks (fd_isolation_cases): its
main() installs the shared isolation, and nothing else of it does."""
import sys
from pathlib import Path

import pytest

MCP_ROOT = Path(__file__).resolve().parents[2]             # <repo>/python/mcp-servers
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))

pytest.register_assert_rewrite("fd_isolation_cases")
import fd_isolation_cases as cases  # noqa: E402

SERVER = "tr_mcp"


def test_import_leaves_fd1_and_sys_stdout_alone():
    cases.import_leaves_fd1_and_sys_stdout_alone(SERVER)


def test_main_installs_the_isolation_before_the_stdio_server_is_built():
    cases.main_installs_the_isolation_before_the_stdio_server_is_built(SERVER)


@pytest.mark.parametrize("flag", ["--help", "--print-tools"])
def test_help_and_print_tools_install_nothing(flag):
    cases.flag_installs_nothing(SERVER, flag)


def test_missing_sdk_installs_nothing():
    cases.missing_sdk_installs_nothing(SERVER)


@pytest.mark.skipif(sys.platform == "win32",
                    reason="fstat gives a pipe no identity there: a merged stream is not recognised")
def test_stderr_merged_into_stdout_keeps_fortran_output_off_the_stream():
    cases.stderr_merged_into_stdout_keeps_fortran_output_off_the_stream(SERVER)


@pytest.mark.skipif(sys.platform == "win32", reason="preexec_fn is POSIX only")
def test_closed_fd2_keeps_everything_but_json_rpc_off_the_pipe():
    cases.closed_fd2_keeps_everything_but_json_rpc_off_the_pipe(SERVER)
