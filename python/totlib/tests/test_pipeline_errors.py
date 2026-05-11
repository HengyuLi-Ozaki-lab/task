"""Verify the TotPipeline error hierarchy is wired correctly."""
import pytest
from totlib.errors import (
    TotlibError,
    TotPipelineError,
    TotPipelineUnknownModuleError,
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineRunError,
)


def test_tot_pipeline_error_inherits_totlib_error():
    assert issubclass(TotPipelineError, TotlibError)


@pytest.mark.parametrize("cls", [
    TotPipelineUnknownModuleError,
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineRunError,
])
def test_subclasses_inherit_pipeline_error(cls):
    assert issubclass(cls, TotPipelineError)


def test_run_error_carries_partial_result():
    sentinel = object()
    err = TotPipelineRunError(
        "boom",
        partial_result=sentinel,
        failed_step_index=1,
        failed_module="fp",
    )
    assert err.partial_result is sentinel
    assert err.failed_step_index == 1
    assert err.failed_module == "fp"
    assert "boom" in str(err)
