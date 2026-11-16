"""tr_mcp: the ``continue_run`` tool (``tr_continue``) and the parameter class in ``describe_parameters``.

Pure-Python tests use a recorder for the library; the integration tests need ``tr/libtrapi.so``.
A refusal comes back in the form PR 1 gave a failed run: the exception text, then ``[failure: kind=... code=...
nt=... time=... s; detail]`` from the library's record.
"""
from __future__ import annotations

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

from tr_mcp import server as srv  # noqa: E402
from trlib import TrFailure, TrlibParamError, TrlibRunError  # noqa: E402

SO = REPO_ROOT / "tr" / "libtrapi.so"
needs_lib = pytest.mark.skipif(not SO.exists(), reason="libtrapi.so not built")


def _message(call):
    try:
        call()
    except Exception as exc:  # ToolError
        return str(exc)
    raise AssertionError("no error raised")


def test_continue_run_calls_the_library_and_says_how_many_steps():
    fake = mock.Mock()
    with mock.patch.object(srv.STATE, "ensure_open", return_value=fake):
        out = srv.handle_continue_run(20)
    fake.continue_run.assert_called_once_with(20)
    assert "20" in out


def test_a_refusal_carries_the_library_record_in_the_same_form_as_a_failed_run():
    f = TrFailure("REFUSED", 0, 10, 0.2, "structural parameter RR set since the preparation")
    tr = mock.Mock()
    tr.continue_run.side_effect = TrlibParamError("tr_continue(5) refused: " + f.detail, failure=f)
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr):
        msg = _message(lambda: srv.handle_continue_run(5))
    assert msg.startswith("invalid parameter:")
    for part in ("failure: kind=REFUSED", "code=0", "nt=10", "time=0.2", "structural parameter RR"):
        assert part in msg, msg


def test_a_refusal_without_a_record_keeps_the_plain_message():
    tr = mock.Mock()
    tr.continue_run.side_effect = TrlibParamError("tr_continue: the step count must be 0 to 2147483647")
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr):
        msg = _message(lambda: srv.handle_continue_run(-1))
    assert msg == "invalid parameter: tr_continue: the step count must be 0 to 2147483647"


def test_a_failed_loop_carries_its_record():
    f = TrFailure("EQ_FAILED", 110, 50, 1.0, "eq_calc in tr_loop (NTEQIT)")
    tr = mock.Mock()
    tr.continue_run.side_effect = TrlibRunError("tr_continue(10): ierr=3", failure=f)
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr):
        msg = _message(lambda: srv.handle_continue_run(10))
    assert msg.startswith("calculation failed:") and "EQ_FAILED" in msg and "nt=50" in msg


def test_the_continue_tool_is_registered_and_run_warns_about_run_zero():
    if not srv.MCP_AVAILABLE:
        pytest.skip("mcp not installed")
    import asyncio
    server = srv.build_server()
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    assert "continue_run" in tools
    assert "run(0)" in tools["run"].description and "ramp" in tools["run"].description
    assert "run(0)" not in tools["continue_run"].description or "only checks" in tools["continue_run"].description


@needs_lib
def test_describe_parameters_shows_each_names_class():
    params = srv.handle_describe_parameters()["parameters"]
    try:
        assert params["RIPE"]["class"] == 1
        for control in ("PNBTOT", "PICTOT", "PECTOT", "PLHTOT", "NTEQIT", "TPRST"):
            assert params[control]["class"] == 1, control
        assert params["RR"]["class"] == 0 and params["PN"]["class"] == 0
        assert all(p["class"] in (0, 1) for p in params.values())     # none unknown (-1)
        text = srv.handle_describe_parameters()["classes"]
        assert "1 control" in text and "0 structural" in text and "-1 unknown" in text and "eq:" in text
    finally:
        srv.STATE.close()


@needs_lib
@pytest.mark.forked
def test_continue_after_a_control_set_advances_nt():
    try:
        srv.handle_run(10)
        nt0 = srv.handle_get_state()["NT"]
        srv.handle_set_param("PECTOT", 1.0)
        srv.handle_continue_run(10)
        assert srv.handle_get_state()["NT"] == nt0 + 10
    finally:
        srv.STATE.close()


@needs_lib
@pytest.mark.forked
def test_continue_after_a_structural_set_returns_the_refusal_record():
    try:
        srv.handle_run(10)
        srv.handle_set_param("RR", 3.0)
        msg = _message(lambda: srv.handle_continue_run(5))
    finally:
        srv.STATE.close()
    assert msg.startswith("invalid parameter:"), msg
    assert "kind=REFUSED" in msg and "RR" in msg and "nt=10" in msg, msg
