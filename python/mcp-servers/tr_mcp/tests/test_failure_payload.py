"""tr_mcp: a failed run's error carries the library's failure record (kind, code, step, time)."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve()
for extra in (str(HERE.parents[2]), str(HERE.parents[3])):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from tr_mcp import server as srv  # noqa: E402
from trlib import TrFailure, TrlibRunError  # noqa: E402


def _failing_handle():
    f = TrFailure("EQ_FAILED", 110, 50, 1.0, "eq_calc in tr_loop (NTEQIT)")
    tr = mock.Mock()
    tr.run.side_effect = TrlibRunError("tr_run(10): ierr=3", failure=f)
    return tr


def _message(call):
    try:
        call()
    except Exception as exc:  # ToolError
        return str(exc)
    raise AssertionError("no error raised")


def test_run_puts_the_failure_in_its_error():
    with mock.patch.object(srv.STATE, "ensure_open", return_value=_failing_handle()):
        msg = _message(lambda: srv.handle_run(10))
    assert msg.startswith("calculation failed:")
    for part in ("EQ_FAILED", "code=110", "nt=50", "time=1", "eq_calc in tr_loop"):
        assert part in msg, msg


def test_run_and_get_state_puts_the_failure_in_its_error():
    with mock.patch.object(srv.STATE, "close"), \
            mock.patch.object(srv.STATE, "ensure_open", return_value=_failing_handle()):
        msg = _message(lambda: srv.handle_run_and_get_state({}, 10))
    assert "EQ_FAILED" in msg and "nt=50" in msg


def test_a_run_error_without_a_record_keeps_the_old_message():
    tr = mock.Mock()
    tr.run.side_effect = TrlibRunError("tr_run(10): ierr=3")
    with mock.patch.object(srv.STATE, "ensure_open", return_value=tr):
        msg = _message(lambda: srv.handle_run(10))
    assert msg == "calculation failed: tr_run(10): ierr=3"
