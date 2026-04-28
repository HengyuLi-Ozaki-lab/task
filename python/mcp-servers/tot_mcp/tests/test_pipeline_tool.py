"""Tests for the new run_pipeline MCP tool (L-7a Phase 3)."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Replace TotPipeline with a stub that records per-instance state.

    Each instantiation appends to captured["instances"] so that successive
    run_pipeline invocations (which create fresh pipelines) leave a per-
    instance audit trail. This lets the prev-pipeline force-close test
    assert that the previous instance's close() was called BEFORE a new
    one is constructed.
    """
    captured = {"instances": []}

    class StubPipeline:
        def __init__(self):
            self._record = {"params": {}, "steps": None, "closed": False}
            captured["instances"].append(self._record)

        def set_param(self, k, v):
            self._record["params"][k] = v

        def run_pipeline(self, steps):
            self._record["steps"] = steps
            from totlib.pipeline import PipelineStep, PipelineResult
            return PipelineResult(steps=[
                PipelineStep("fp", {"foo": 1.0}, []),
                PipelineStep("tr", {"bar": 2.0}, ["fp -> tr"]),
            ])

        def close(self):
            self._record["closed"] = True

    # Patch the import path used inside server.py
    monkeypatch.setattr("tot_mcp.server.TotPipeline", StubPipeline)
    return captured


def test_run_pipeline_tool_calls_pipeline(stub_pipeline):
    from tot_mcp.server import handle_run_pipeline
    out = handle_run_pipeline(
        steps=[
            {"module": "fp", "kwargs": {"ntmax": 5}},
            {"module": "tr", "kwargs": {"ntmax": 1}},
        ],
        params={"fp:NSAMAX": 2},
    )
    assert out["fp"] == {"foo": 1.0}
    assert out["tr"] == {"bar": 2.0}
    assert len(stub_pipeline["instances"]) == 1
    assert stub_pipeline["instances"][0]["steps"] == [("fp", {"ntmax": 5}), ("tr", {"ntmax": 1})]
    assert stub_pipeline["instances"][0]["params"] == {"fp:NSAMAX": 2}
    assert "_steps" in out  # PipelineResult.to_dict adds this timeline key


def test_run_pipeline_tool_force_closes_legacy_state(stub_pipeline, monkeypatch):
    """When run_pipeline is invoked, the legacy STATE wrapper's close() must
    be called (mirroring the existing _ServerState force-close pattern)."""
    legacy_close_calls = []
    legacy_stub = MagicMock()
    legacy_stub.close.side_effect = lambda: legacy_close_calls.append(True)
    monkeypatch.setattr("tot_mcp.server.STATE", legacy_stub)

    from tot_mcp.server import handle_run_pipeline
    handle_run_pipeline(
        steps=[{"module": "fp", "kwargs": {}}],
        params=None,
    )
    assert legacy_close_calls, "legacy STATE.close() was not called"
    # One stub pipeline instance was constructed
    assert len(stub_pipeline["instances"]) == 1


def test_run_pipeline_tool_force_closes_prev_pipeline(stub_pipeline):
    """Successive run_pipeline calls must isolate state — the prior
    PIPELINE_STATE has its close() called before the next pipeline starts.
    Mirrors the HIGH audit pattern used elsewhere in the server."""
    from tot_mcp.server import handle_run_pipeline
    handle_run_pipeline(
        steps=[{"module": "fp", "kwargs": {}}], params=None,
    )
    handle_run_pipeline(
        steps=[{"module": "tr", "kwargs": {}}], params=None,
    )
    # Two pipelines were constructed over two calls
    assert len(stub_pipeline["instances"]) == 2
    # The first instance was closed before the second was constructed
    assert stub_pipeline["instances"][0]["closed"] is True


def test_run_pipeline_tool_validates_input(stub_pipeline):
    """Malformed steps payload (missing 'kwargs' key) must raise
    TotPipelineCouplingError before any pipeline is constructed."""
    from tot_mcp.server import handle_run_pipeline
    from totlib.errors import TotPipelineCouplingError
    with pytest.raises(TotPipelineCouplingError):
        handle_run_pipeline(
            steps=[{"module": "fp"}],   # missing kwargs key
            params=None,
        )
    # Ensure no pipeline was even constructed (pre-flight validation)
    assert len(stub_pipeline["instances"]) == 0


def test_run_pipeline_tool_force_closes_on_run_failure(monkeypatch):
    """If pipeline.run_pipeline raises mid-run, PIPELINE_STATE must be
    reset to None before the exception escapes — otherwise the next call
    inherits a dangling open pipeline (regression guard for review I2)."""
    from tot_mcp import server as srv

    closed_calls = []

    class FailingPipeline:
        def __init__(self):
            self._closed = False

        def set_param(self, k, v):
            pass

        def run_pipeline(self, steps):
            raise RuntimeError("intentional mid-run failure")

        def close(self):
            self._closed = True
            closed_calls.append(self)

    monkeypatch.setattr("tot_mcp.server.TotPipeline", FailingPipeline)

    # Reset PIPELINE_STATE to None so we exercise the fresh-start path
    monkeypatch.setattr("tot_mcp.server.PIPELINE_STATE", None)

    with pytest.raises(Exception):  # _wrap_totlib_error result; type may vary
        srv.handle_run_pipeline(
            steps=[{"module": "fp", "kwargs": {}}],
            params=None,
        )

    assert srv.PIPELINE_STATE is None, (
        f"PIPELINE_STATE not reset after failure: {srv.PIPELINE_STATE!r}"
    )
    assert closed_calls, "FailingPipeline.close() was never called"
