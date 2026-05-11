"""Verify TotPipeline + dataclasses are exported at the package level."""


def test_tot_pipeline_importable_from_package():
    from totlib import TotPipeline
    assert TotPipeline.__name__ == "TotPipeline"


def test_pipeline_dataclasses_importable_from_package():
    from totlib import CouplingRule, PipelineStep, PipelineResult
    assert CouplingRule.__name__ == "CouplingRule"
    assert PipelineStep.__name__ == "PipelineStep"
    assert PipelineResult.__name__ == "PipelineResult"


def test_tot_pipeline_in_dunder_all():
    import totlib
    assert "TotPipeline" in totlib.__all__
    assert "CouplingRule" in totlib.__all__
    assert "PipelineStep" in totlib.__all__
    assert "PipelineResult" in totlib.__all__


def test_legacy_tot_still_exported():
    """Backwards compat: existing Tot import path must continue to work."""
    from totlib import Tot
    assert Tot.__name__ == "Tot"


def test_legacy_tot_state_still_exported():
    from totlib import TotState
    assert TotState.__name__ == "TotState"
