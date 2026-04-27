"""Unit tests for TotPipeline — mock-based, no lib*.so required.

Lifecycle subset (Task 1.4): __init__, __enter__/__exit__, _ensure_module,
set_param, close. run_pipeline tests are added in Task 1.5.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from totlib.errors import (
    TotPipelineCouplingError,
    TotPipelineLifecycleError,
    TotPipelineUnknownModuleError,
)
from totlib.pipeline import TotPipeline


@pytest.fixture
def patch_wrappers(monkeypatch):
    """Replace _import_wrapper / _import_module_error with mocks.

    The returned dict allows tests to inspect which wrappers were
    requested, capture set_param/run/get_state calls, and inject errors.
    """
    fp_mock_class = MagicMock(name="FplibClass")
    tr_mock_class = MagicMock(name="TrlibClass")
    fp_err_class = type("FplibError", (Exception,), {})
    tr_err_class = type("TrlibError", (Exception,), {})

    classes = {"fp": fp_mock_class, "tr": tr_mock_class}
    err_classes = {"fp": fp_err_class, "tr": tr_err_class}

    def fake_import_wrapper(name):
        if name not in classes:
            raise TotPipelineUnknownModuleError(name)
        return classes[name]

    def fake_import_module_error(name):
        if name not in err_classes:
            raise TotPipelineUnknownModuleError(name)
        return err_classes[name]

    monkeypatch.setattr("totlib.pipeline._import_wrapper", fake_import_wrapper)
    monkeypatch.setattr("totlib.pipeline._import_module_error", fake_import_module_error)

    return {"classes": classes, "errors": err_classes}


def test_init_does_not_open_anything(patch_wrappers):
    pipe = TotPipeline()
    assert pipe._modules == {}
    assert pipe._params == {}
    assert pipe._closed is False
    # No wrapper class was instantiated
    patch_wrappers["classes"]["fp"].assert_not_called()
    patch_wrappers["classes"]["tr"].assert_not_called()


def test_set_param_lazy_opens_target_module_only(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:NSAMAX", 2)
    # fp is opened
    patch_wrappers["classes"]["fp"].assert_called_once()
    # tr is NOT opened
    patch_wrappers["classes"]["tr"].assert_not_called()
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.set_param.assert_called_once_with("NSAMAX", 2.0)


def test_set_param_string_routes_to_set_param_str(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("tr:KNAMEQ", "/path/to/eqdsk")
    tr_inst = patch_wrappers["classes"]["tr"].return_value
    tr_inst.set_param_str.assert_called_once_with("KNAMEQ", "/path/to/eqdsk")
    tr_inst.set_param.assert_not_called()


def test_set_param_no_namespace_raises(patch_wrappers):
    pipe = TotPipeline()
    with pytest.raises(TotPipelineCouplingError, match="prefixed"):
        pipe.set_param("nokoron", 1.0)


def test_set_param_unknown_module_raises(patch_wrappers):
    pipe = TotPipeline()
    with pytest.raises(TotPipelineUnknownModuleError):
        pipe.set_param("xx:something", 1.0)


def test_set_param_records_into_params_dict(patch_wrappers):
    """set_param updates self._params after the wrapper accepts the value."""
    pipe = TotPipeline()
    pipe.set_param("tr:RR", 6.2)
    pipe.set_param("tr:RA", 2.0)
    pipe.set_param("fp:NSAMAX", 2)
    assert pipe._params == {"tr:RR": 6.2, "tr:RA": 2.0, "fp:NSAMAX": 2}


def test_set_param_string_to_module_without_set_param_str_raises(monkeypatch):
    """wr/wrx/ti wrappers don't expose set_param_str. Passing a string
    value to one of them must raise TotPipelineCouplingError, not a
    bare AttributeError. (Regression guard: real wrappers checked.)
    """
    # Build a fake wrapper class WITHOUT set_param_str
    fake_wrapper_class = MagicMock(name="WrxlibClass")
    fake_instance = MagicMock(spec=["set_param", "close"])  # no set_param_str
    fake_wrapper_class.return_value = fake_instance

    def fake_import_wrapper(name):
        if name == "wrx":
            return fake_wrapper_class
        raise TotPipelineUnknownModuleError(name)

    monkeypatch.setattr("totlib.pipeline._import_wrapper", fake_import_wrapper)
    pipe = TotPipeline()
    with pytest.raises(TotPipelineCouplingError, match="string parameters"):
        pipe.set_param("wrx:KFILE", "/path/to/something")


def test_close_finalizes_all_open_modules(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:A", 1.0)
    pipe.set_param("tr:B", 2.0)
    pipe.close()
    patch_wrappers["classes"]["fp"].return_value.close.assert_called_once()
    patch_wrappers["classes"]["tr"].return_value.close.assert_called_once()
    assert pipe._closed is True


def test_close_is_idempotent(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:A", 1.0)
    pipe.close()
    # Second close should not raise and should not re-call close()
    pipe.close()
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.close.assert_called_once()


def test_close_finalizes_remaining_modules_on_error(patch_wrappers):
    pipe = TotPipeline()
    pipe.set_param("fp:A", 1.0)
    pipe.set_param("tr:B", 2.0)
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    tr_inst = patch_wrappers["classes"]["tr"].return_value
    fp_inst.close.side_effect = RuntimeError("fp boom")
    with pytest.raises(RuntimeError, match="fp boom"):
        pipe.close()
    # tr.close was still called despite fp.close raising
    tr_inst.close.assert_called_once()


def test_set_param_after_close_raises_lifecycle(patch_wrappers):
    pipe = TotPipeline()
    pipe.close()
    with pytest.raises(TotPipelineLifecycleError):
        pipe.set_param("fp:A", 1.0)


def test_context_manager_closes_on_normal_exit(patch_wrappers):
    with TotPipeline() as pipe:
        pipe.set_param("fp:A", 1.0)
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.close.assert_called_once()


def test_context_manager_closes_on_exception(patch_wrappers):
    with pytest.raises(ValueError):
        with TotPipeline() as pipe:
            pipe.set_param("fp:A", 1.0)
            raise ValueError("inner")
    fp_inst = patch_wrappers["classes"]["fp"].return_value
    fp_inst.close.assert_called_once()
