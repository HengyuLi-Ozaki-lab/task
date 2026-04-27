"""Test _MODULE_REGISTRY and lazy resolvers."""
import pytest
from totlib.pipeline import (
    _MODULE_REGISTRY,
    _import_wrapper,
    _import_module_error,
)
from totlib.errors import TotPipelineUnknownModuleError


def test_registry_has_all_six_modules():
    assert set(_MODULE_REGISTRY) == {"fp", "tr", "eq", "wr", "wrx", "ti"}


def test_registry_entries_have_three_fields():
    for name, entry in _MODULE_REGISTRY.items():
        assert len(entry) == 3, f"{name}: {entry}"
        pkg, cls, err = entry
        assert pkg.endswith("lib"), f"{name}: pkg={pkg}"
        assert err.endswith("Error"), f"{name}: err={err}"


def test_import_wrapper_unknown_raises():
    with pytest.raises(TotPipelineUnknownModuleError) as exc_info:
        _import_wrapper("nope")
    assert "nope" in str(exc_info.value)


def test_import_module_error_unknown_raises():
    with pytest.raises(TotPipelineUnknownModuleError):
        _import_module_error("nope")


def test_import_wrapper_returns_class_for_fp():
    """fp's wrapper class should be importable (does not require libfpapi.so;
    only the class object is returned, not an instance)."""
    cls = _import_wrapper("fp")
    assert cls.__name__ == "Fplib"


def test_import_module_error_returns_class_for_fp():
    err_cls = _import_module_error("fp")
    assert err_cls.__name__ == "FplibError"
    assert issubclass(err_cls, Exception)
