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

from trlib import _ffi as _tr_ffi  # noqa: E402

# Trlib()'s own resolution: MONO_LIB_PATH, TRLIB_PATH, tr/, lib/.
needs_lib = pytest.mark.skipif(not _tr_ffi._default_lib_path().exists(),
                               reason=f"libtrapi.so not found at {_tr_ffi._default_lib_path()}")


def _message(call):
    try:
        call()
    except Exception as exc:  # ToolError
        return str(exc)
    raise AssertionError("no error raised")


def test_continue_run_calls_the_library_and_says_how_many_steps():
    fake = mock.Mock()
    with mock.patch.object(srv.STATE, "ensure_open", return_value=fake), \
            mock.patch.object(srv.STATE, "evaluated", False), mock.patch.object(srv.STATE, "prepared", True):
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


def test_a_refusal_says_its_detail_once():
    f = TrFailure("REFUSED", 0, 10, 0.2, "structural parameter RR set since the preparation")
    tr = mock.Mock()
    tr.continue_run.side_effect = TrlibParamError("tr_continue(5) refused: " + f.detail, failure=f)
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr):
        msg = _message(lambda: srv.handle_continue_run(5))
    assert msg.count(f.detail) == 1, msg


def test_a_failed_run_says_its_detail_once_too():
    f = TrFailure("EQ_FAILED", 110, 50, 1.0, "eq_calc in tr_loop (NTEQIT)")
    tr = mock.Mock()
    tr.run.side_effect = TrlibRunError("tr_run(10): ierr=3", failure=f)
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr):
        msg = _message(lambda: srv.handle_run(10))
    assert msg.count(f.detail) == 1, msg


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
def test_describe_parameters_does_not_open_a_lifecycle():
    srv.STATE.close()
    with mock.patch.object(srv.STATE, "ensure_open", side_effect=AssertionError("opened a lifecycle")):
        out = srv.handle_describe_parameters()
    assert out["parameters"]["RIPE"]["class"] == 1 and "classes_unavailable" not in out


def test_describe_parameters_says_when_the_classes_cannot_be_read():
    with mock.patch("trlib._ffi.load_library", side_effect=FileNotFoundError("libtrapi.so not found at /nowhere")):
        out = srv.handle_describe_parameters()
    assert "class" not in out["parameters"]["RIPE"]
    assert "libtrapi.so not found" in out["classes_unavailable"]


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
def test_continue_after_a_control_set_shows_the_results_it_evaluated():
    # A control set hides the results until a step is run (fork #26's flag); continue_run's steps are this state's.
    try:
        srv.handle_init()
        srv.handle_set_param("PNBTOT", 10.0)
        srv.handle_run(5)
        srv.handle_set_param("PNBTOT", 0.0)
        srv.handle_continue_run(0)
        assert set(srv.handle_get_state()["scalars"]) == {"T"}
        srv.handle_continue_run(5)
        scalars = srv.handle_get_state()["scalars"]
        assert len(scalars) == 31 and scalars["PNBT"] == pytest.approx(0.0, abs=1e-12)
    finally:
        srv.STATE.close()


@needs_lib
@pytest.mark.forked
def test_a_continue_that_fails_before_a_new_row_keeps_the_results_hidden():
    # NGTSTP 5: run(3) records step 0 only, and its last step's globals are of PECTOT 0. PECTOT 1e7 then makes the
    # first continued step not finite (nt 4), before any output step: no global result of the new setting exists.
    try:
        srv.handle_init()
        srv.handle_set_param("NGTSTP", 5.0)
        srv.handle_run(3)
        srv.handle_set_param("PECTOT", 1.0e7)
        msg = _message(lambda: srv.handle_continue_run(5))
        assert "kind=NONFINITE" in msg and "nt=4" in msg, msg
        assert set(srv.handle_get_state()["scalars"]) == {"T"}
    finally:
        srv.STATE.close()


# A continue keeps the rows from before it: only a row it added shows that its steps computed the globals.
@pytest.mark.parametrize("rows, shown", [((3, 4), True), ((3, 3), False), ((0, 0), False)])
def test_a_continue_that_fails_in_its_steps_keeps_the_results_it_evaluated(rows, shown):
    f = TrFailure("NONFINITE", -3, 12, 1.2, "Q0, WPT or a central temperature is not finite")
    tr = mock.Mock()
    tr.continue_run.side_effect = TrlibRunError("tr_continue(10): ierr=3", failure=f)
    tr.history_length.side_effect = list(rows)
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr), \
            mock.patch.object(srv.STATE, "evaluated", False), mock.patch.object(srv.STATE, "prepared", True):
        with pytest.raises(Exception):
            srv.handle_continue_run(10)
        assert srv.STATE.evaluated is shown and srv.STATE.prepared is True


def test_a_refused_continue_changes_neither_flag():
    f = TrFailure("REFUSED", 0, 10, 0.2, "structural parameter RR set since the preparation")
    tr = mock.Mock()
    tr.continue_run.side_effect = TrlibParamError("tr_continue(5) refused: " + f.detail, failure=f)
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr), \
            mock.patch.object(srv.STATE, "evaluated", False), mock.patch.object(srv.STATE, "prepared", True):
        with pytest.raises(Exception):
            srv.handle_continue_run(5)
        assert srv.STATE.evaluated is False and srv.STATE.prepared is True


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


def test_continue_run_is_listed_by_print_tools(capsys):
    assert srv.main(["--print-tools"]) == 0
    assert "continue_run" in capsys.readouterr().out.split()


def test_print_tools_lists_exactly_the_registered_tools(capsys):
    if not srv.MCP_AVAILABLE:
        pytest.skip("mcp not installed")
    import asyncio
    assert srv.main(["--print-tools"]) == 0
    printed = capsys.readouterr().out.split()
    registered = sorted(t.name for t in asyncio.run(srv.build_server().list_tools()))
    assert printed == registered and len(printed) == 13
