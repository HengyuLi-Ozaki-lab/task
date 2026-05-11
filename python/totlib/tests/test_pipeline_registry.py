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


# Parametrized coverage across all 6 modules so a silent rename in any
# sibling errors.py / wrapper module is caught immediately by the
# registry tests (rather than waiting for L-7b to light up that module).
@pytest.mark.parametrize("name", sorted(_MODULE_REGISTRY))
def test_import_wrapper_class_name_matches_registry(name):
    expected_cls_name = _MODULE_REGISTRY[name][1]
    cls = _import_wrapper(name)
    assert cls.__name__ == expected_cls_name, (
        f"registry says {name} -> {expected_cls_name}, got {cls.__name__}"
    )


@pytest.mark.parametrize("name", sorted(_MODULE_REGISTRY))
def test_import_module_error_name_matches_registry(name):
    expected_err_name = _MODULE_REGISTRY[name][2]
    err_cls = _import_module_error(name)
    assert err_cls.__name__ == expected_err_name, (
        f"registry says {name} -> {expected_err_name}, got {err_cls.__name__}"
    )
    assert issubclass(err_cls, Exception)
