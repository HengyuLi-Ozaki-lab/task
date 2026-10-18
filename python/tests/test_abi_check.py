"""python/_abi_check.py: the layout check that every wrapper runs at load (#246).

No shared library is needed: a stand-in object plays the ``ctypes.CDLL``.
The real libraries are covered by ``TestLibraryLayout`` in each wrapper's
``tests/test_ffi.py``.
"""
from __future__ import annotations

import ctypes
import sys
import unittest
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[1]
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from _abi_check import AbiMismatchError, check_state_layout  # noqa: E402


class _State(ctypes.Structure):
    _fields_ = [("nt", ctypes.c_int), ("x", ctypes.c_double * 4)]


class _Fn:
    """A ctypes-function stand-in: callable, accepts restype/argtypes."""

    def __init__(self, value):
        self._value = value
        self.restype = None
        self.argtypes = None

    def __call__(self):
        return self._value


class _Lib:
    def __init__(self, version=None, size=None):
        if version is not None:
            self.xx_state_abi_version = _Fn(version)
        if size is not None:
            self.xx_state_size = _Fn(size)


def _check(lib, version=3):
    check_state_layout(lib, prefix="xx", struct=_State,
                       expected_version=version, lib_name="libxxapi.so")


class TestCheckStateLayout(unittest.TestCase):
    def test_matching_library_passes_and_attaches_prototypes(self):
        lib = _Lib(version=3, size=ctypes.sizeof(_State))
        _check(lib)
        self.assertIs(lib.xx_state_abi_version.restype, ctypes.c_int)
        self.assertIs(lib.xx_state_size.restype, ctypes.c_size_t)
        self.assertEqual(lib.xx_state_abi_version.argtypes, [])

    def test_library_without_the_symbols_is_refused(self):
        with self.assertRaises(AbiMismatchError) as ctx:
            _check(_Lib())
        err = ctx.exception
        self.assertIsNone(err.library_version)
        self.assertIsNone(err.library_size)
        self.assertEqual(err.wrapper_size, ctypes.sizeof(_State))
        self.assertIn("before the layout check", str(err))
        self.assertIn("make -C xx libxxapi.so", str(err))

    def test_library_with_only_one_symbol_is_refused(self):
        with self.assertRaises(AbiMismatchError):
            _check(_Lib(version=3))

    def test_larger_library_struct_is_refused(self):
        """Old wrapper, new library: the library would write past the struct."""
        with self.assertRaises(AbiMismatchError) as ctx:
            _check(_Lib(version=3, size=ctypes.sizeof(_State) + 56))
        err = ctx.exception
        self.assertEqual(err.library_size, ctypes.sizeof(_State) + 56)
        self.assertEqual(err.wrapper_size, ctypes.sizeof(_State))
        self.assertIn(str(ctypes.sizeof(_State) + 56), str(err))
        self.assertIn(str(ctypes.sizeof(_State)), str(err))

    def test_smaller_library_struct_is_refused(self):
        """New wrapper, old library: appended fields would stay zero."""
        with self.assertRaises(AbiMismatchError):
            _check(_Lib(version=3, size=ctypes.sizeof(_State) - 8))

    def test_version_drift_with_equal_size_is_refused(self):
        """A reorder keeps the size; only the version tells."""
        with self.assertRaises(AbiMismatchError) as ctx:
            _check(_Lib(version=4, size=ctypes.sizeof(_State)))
        self.assertEqual(ctx.exception.library_version, 4)
        self.assertEqual(ctx.exception.wrapper_version, 3)

    def test_rebuild_hint_names_the_module_directory(self):
        with self.assertRaises(AbiMismatchError) as ctx:
            _check(_Lib())
        self.assertIn("`make -C xx libxxapi.so`", str(ctx.exception))

    def test_rebuild_hint_for_the_mono_image_points_at_tot(self):
        """A wrapper routed to libtotapi_mono.so must not say `make -C eq
        libtotapi_mono.so`: the mono image is built under tot."""
        with self.assertRaises(AbiMismatchError) as ctx:
            check_state_layout(_Lib(version=4, size=ctypes.sizeof(_State)),
                               prefix="xx", struct=_State, expected_version=3,
                               lib_name="libtotapi_mono.so")
        self.assertIn("`make -C tot libtotapi_mono.so`", str(ctx.exception))
        self.assertNotIn("make -C xx", str(ctx.exception))

    def test_rebuild_hint_for_a_dll_names_no_make_target(self):
        """The Makefiles have no .dll target: a Windows library is rebuilt from
        the sources, as the wrappers' not-found hint says."""
        for lib_name in ("libxxapi.dll", "libtotapi_mono.dll"):
            for lib in (_Lib(), _Lib(version=4, size=ctypes.sizeof(_State))):
                with self.subTest(lib_name=lib_name, query=hasattr(lib, "xx_state_size")):
                    with self.assertRaises(AbiMismatchError) as ctx:
                        check_state_layout(lib, prefix="xx", struct=_State,
                                           expected_version=3, lib_name=lib_name)
                    self.assertIn(f"{lib_name} from the Fortran sources", str(ctx.exception))
                    self.assertNotIn("make -C", str(ctx.exception))

    def test_error_is_a_runtime_error(self):
        self.assertTrue(issubclass(AbiMismatchError, RuntimeError))


if __name__ == "__main__":
    unittest.main()
