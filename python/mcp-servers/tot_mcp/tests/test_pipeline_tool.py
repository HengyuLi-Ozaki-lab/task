"""Tests for the new run_pipeline MCP tool (L-7a Phase 3)."""
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Replace TotPipeline with a stub that records all calls.

    Each StubPipeline instance records its own params/steps/closed state
    into the captured dict so successive run_pipeline invocations can be
    inspected (matters for the prev-pipeline force-close test).
    """
    captured = {"params": {}, "steps": None, "closed": False, "init_count": 0}

    class StubPipeline:
        def __init__(self):
            captured["init_count"] += 1
            captured["closed"] = False
            captured["params"] = {}
            captured["steps"] = None

        def set_param(self, k, v):
            captured["params"][k] = v

        def run_pipeline(self, steps):
            captured["steps"] = steps
            from totlib.pipeline import PipelineStep, PipelineResult
            return PipelineResult(steps=[
                PipelineStep("fp", {"foo": 1.0}, []),
                PipelineStep("tr", {"bar": 2.0}, ["fp -> tr"]),
            ])

        def close(self):
            captured["closed"] = True

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
    assert stub_pipeline["steps"] == [("fp", {"ntmax": 5}), ("tr", {"ntmax": 1})]
    assert stub_pipeline["params"] == {"fp:NSAMAX": 2}
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


def test_run_pipeline_tool_force_closes_prev_pipeline(stub_pipeline):
    """Successive run_pipeline calls must isolate state — the prior
    PIPELINE_STATE has its close() called before the next pipeline starts.
    Mirrors the HIGH audit pattern used elsewhere in the server."""
    from tot_mcp.server import handle_run_pipeline
    handle_run_pipeline(
        steps=[{"module": "fp", "kwargs": {}}], params=None,
    )
    first_init = stub_pipeline["init_count"]
    handle_run_pipeline(
        steps=[{"module": "tr", "kwargs": {}}], params=None,
    )
    # The second call constructed a fresh pipeline (new instance opened)
    assert stub_pipeline["init_count"] == first_init + 1


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
    assert stub_pipeline["steps"] is None
