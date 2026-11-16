"""tot_mcp: the ``continue_run`` tool (``tot_continue``) and the ``run(0)`` warning in ``run``'s description."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

HERE = Path(__file__).resolve()
MCP_ROOT = HERE.parents[1]
PYTHON_ROOT = HERE.parents[3]
REPO_ROOT = HERE.parents[4]

for extra in (str(MCP_ROOT.parent), str(PYTHON_ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from tot_mcp import server as srv  # noqa: E402
from totlib.errors import TotlibInvalidParamError  # noqa: E402

FIXTURES_DIR = PYTHON_ROOT / "trlib" / "tests" / "fixtures"
has_lib = bool(os.environ.get("MONO_LIB_PATH") or os.environ.get("TOTLIB_PATH") or (REPO_ROOT / "tot" / "libtotapi.so").exists())


def _message(call):
    try:
        call()
    except Exception as exc:  # ToolError
        return str(exc)
    raise AssertionError("no error raised")


def test_continue_run_calls_the_library():
    fake = mock.Mock()
    with mock.patch.object(srv.STATE, "ensure_open", return_value=fake):
        out = srv.handle_continue_run(20)
    fake.continue_run.assert_called_once_with(20)
    assert "20" in out


def test_a_refusal_comes_back_as_an_invalid_parameter_error_with_the_message():
    tot = mock.Mock()
    tot.continue_run.side_effect = TotlibInvalidParamError("tot_continue(5): rc=1: nt=5 t=0.1 s: structural parameter eq:RB set")
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tot):
        msg = _message(lambda: srv.handle_continue_run(5))
    assert msg.startswith("invalid parameter: tot_continue(5)") and "eq:RB" in msg


def test_the_continue_tool_is_registered_and_run_warns_about_run_zero():
    if not srv.MCP_AVAILABLE:
        pytest.skip("mcp not installed")
    import asyncio
    server = srv.build_server()
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    assert "continue_run" in tools
    assert "run(0)" in tools["run"].description and "ramp" in tools["run"].description


@pytest.mark.skipif(not has_lib, reason="libtotapi.so not built")
@pytest.mark.forked
def test_continue_after_an_eq_set_is_refused_naming_it():
    from trlib.tests.fixtures import tr_iter01_params as fixture
    prev = os.getcwd()
    os.chdir(FIXTURES_DIR)
    try:
        params = {f"tr:{k}": v for k, v in fixture.STRINGS.items()}
        params.update({f"tr:{k}": v for k, v in fixture.SCALARS.items()})
        for name, values in fixture.ARRAYS.items():
            params.update({f"tr:{name}[{i}]": v for i, v in enumerate(values, 1)})
        for i in range(1, 5):
            params[f"tr:PT[{i}]"] = 10.0
            params[f"tr:PTS[{i}]"] = 1.0
        srv.handle_set_params(params)
        srv.handle_run(5)
        srv.handle_continue_run(5)                       # nothing set: goes on
        srv.handle_set_param("eq:RB", 2.1)
        msg = _message(lambda: srv.handle_continue_run(5))
    finally:
        srv.STATE.close()
        os.chdir(prev)
    assert msg.startswith("invalid parameter:") and "eq:RB" in msg, msg
