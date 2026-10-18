"""Direct ctypes-layer tests.

These exercise :mod:`fplib._ffi` without going through the high-level
``Fplib`` class. They verify that:

* the package imports without a libfpapi.so on disk (load is lazy),
* :class:`FpStateC` has the expected size and layout,
* :func:`load_library` errors clearly when the .so is missing,
* when libfpapi.so **is** present, prototypes are attached and the 5
  symbols resolve.

Tests that require the shared library are skipped automatically when
it has not been built yet.
"""
from __future__ import annotations

import ctypes
import os
import sys
import unittest
from pathlib import Path

# Make sure the package is importable when tests are run from the
# repo root with ``python3 -m unittest discover``.
HERE = Path(__file__).resolve()
PYTHON_ROOT = HERE.parents[2]  # .../python
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from fplib import _ffi  # noqa: E402
from fplib import state  # noqa: E402


REPO = HERE.parents[3]
DEFAULT_SO = REPO / "fp" / "libfpapi.so"


class TestFfiImport(unittest.TestCase):
    """Importing _ffi must not require libfpapi.so on disk."""

    def test_module_imports(self):
        self.assertTrue(hasattr(_ffi, "FpStateC"))
        self.assertTrue(hasattr(_ffi, "load_library"))

    def test_constants_match_header(self):
        # Must match fp/fp_api.h exactly.
        self.assertEqual(_ffi.FP_MAX_NRMAX, 100)
        self.assertEqual(_ffi.FP_MAX_NSAMAX, 8)
        self.assertEqual(_ffi.FP_OK, 0)
        self.assertEqual(_ffi.FP_ERR_INVALID, 1)
        self.assertEqual(_ffi.FP_ERR_NOT_INIT, 2)
        self.assertEqual(_ffi.FP_ERR_CALC_FAILED, 3)
        self.assertEqual(_ffi.FP_ERR_NOT_IMPL, 4)


class TestFpStateCLayout(unittest.TestCase):
    """Structural checks on the ctypes mirror of ``fp_state_t``."""

    def test_has_expected_fields(self):
        names = [f[0] for f in _ffi.FpStateC._fields_]
        for n in (
            "nrmax", "nsamax", "npmax", "nthmax", "ntg2", "timefp",
            "RNT", "RWT", "RTT", "RJT", "RPCT", "RPWT",
        ):
            self.assertIn(n, names, f"missing field {n}")

    def test_global_scalars_are_appended_last(self):
        # ABI contract: the 7 global scalars sit at the END of the
        # struct so every pre-existing member keeps its offset. If a
        # future field is inserted before them, this fails.
        names = [f[0] for f in _ffi.FpStateC._fields_]
        self.assertEqual(names[-7:], list(state.SCALAR_FIELDS))
        for n in state.SCALAR_FIELDS:
            self.assertEqual(
                dict(f[:2] for f in _ffi.FpStateC._fields_)[n], ctypes.c_double
            )

    def test_size_matches_header_math(self):
        # 5 ints + 1 double + 6 * NSA*NR doubles + 7 scalar doubles.
        # Compilers may pad the 5 ints to a multiple of 8 before the
        # first double, so we accept the natural rounding range.
        nr = _ffi.FP_MAX_NRMAX
        nsa = _ffi.FP_MAX_NSAMAX
        exp_core = 8 + 6 * nr * nsa * 8 + len(state.SCALAR_FIELDS) * 8
        sz = ctypes.sizeof(_ffi.FpStateC)
        # 5 ints = 20 bytes, padded up to either 24 (8-byte align) or
        # possibly 32 on pathological ABIs.
        self.assertIn(
            sz,
            (20 + exp_core, 24 + exp_core, 32 + exp_core),
            f"unexpected FpStateC size {sz}",
        )

    def test_profile_array_dimensions(self):
        # RNT / RWT / ...: [NSAMAX][NRMAX] row-major in C, equivalent to
        # Fortran RNT(NRMAX, NSAMAX) column-major -- same memory layout.
        s = _ffi.FpStateC()
        # First index has NSAMAX entries, second has NRMAX.
        self.assertEqual(len(s.RNT), _ffi.FP_MAX_NSAMAX)
        self.assertEqual(len(s.RNT[0]), _ffi.FP_MAX_NRMAX)
        for name in ("RWT", "RTT", "RJT", "RPCT", "RPWT"):
            arr = getattr(s, name)
            self.assertEqual(len(arr), _ffi.FP_MAX_NSAMAX)
            self.assertEqual(len(arr[0]), _ffi.FP_MAX_NRMAX)


class TestLoadLibraryMissing(unittest.TestCase):
    """Error-path test that runs whether or not .so exists."""

    def test_load_bogus_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            _ffi.load_library("/nonexistent/path/to/libfpapi.so")

    def test_candidate_paths_listed(self):
        cands = _ffi._candidate_paths()
        self.assertTrue(any(str(p).endswith("fp/libfpapi.so") for p in cands))
        self.assertTrue(any(str(p).endswith("lib/libfpapi.so") for p in cands))


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libfpapi.so not built at {DEFAULT_SO}; run `make -C fp libfpapi.so`",
)
class TestLoadLibraryReal(unittest.TestCase):
    """Tests that require the real shared library on disk."""

    def test_load_default(self):
        lib = _ffi.load_library()
        self.assertIsInstance(lib, ctypes.CDLL)
        for sym in (
            "fp_init", "fp_run", "fp_set_param", "fp_get_state", "fp_finalize"
        ):
            self.assertTrue(hasattr(lib, sym), f"missing export {sym}")

    def test_env_override(self):
        old = os.environ.get("FPLIB_PATH")
        os.environ["FPLIB_PATH"] = str(DEFAULT_SO)
        try:
            lib = _ffi.load_library()
            self.assertIsInstance(lib, ctypes.CDLL)
        finally:
            if old is None:
                os.environ.pop("FPLIB_PATH", None)
            else:
                os.environ["FPLIB_PATH"] = old

    def test_prototypes_applied(self):
        lib = _ffi.load_library()
        self.assertEqual(lib.fp_init.restype, ctypes.c_int)
        self.assertEqual(lib.fp_run.argtypes, [ctypes.c_int])
        self.assertEqual(
            lib.fp_set_param.argtypes,
            [ctypes.c_char_p, ctypes.c_double],
        )


class TestLibraryLayout(unittest.TestCase):
    """#246: the library's fp_state_t layout must be FpStateC's.

    ``load_library`` compares ``fp_state_abi_version()`` / ``fp_state_size()``
    with ``FP_STATE_ABI_VERSION`` / ``ctypes.sizeof(FpStateC)`` and raises
    ``FplibAbiError`` on any difference. The guards run in ``setUp``: the
    ``.so`` is a mutable precondition.
    """

    def setUp(self):
        if not _ffi._default_lib_path().exists():
            self.skipTest(f"libfpapi.so not built at {_ffi._default_lib_path()}")
        self.lib = _ffi.load_library()

    def test_library_layout_matches_wrapper(self):
        self.assertEqual(self.lib.fp_state_abi_version(), _ffi.FP_STATE_ABI_VERSION)
        self.assertEqual(self.lib.fp_state_size(), ctypes.sizeof(_ffi.FpStateC))

    def test_stale_wrapper_layout_is_refused(self):
        """Old wrapper, new library: one field short, the library would
        write past the allocation. Refused before any struct is passed."""
        from _abi_check import AbiMismatchError, check_state_layout

        class Stale(ctypes.Structure):
            _fields_ = _ffi.FpStateC._fields_[:-1]

        with self.assertRaises(AbiMismatchError) as ctx:
            check_state_layout(self.lib, prefix="fp", struct=Stale,
                               expected_version=_ffi.FP_STATE_ABI_VERSION,
                               lib_name="libfpapi.so")
        self.assertEqual(ctx.exception.library_size, ctypes.sizeof(_ffi.FpStateC))
        self.assertEqual(ctx.exception.wrapper_size, ctypes.sizeof(Stale))

    def test_version_drift_is_refused_through_load_library(self):
        """A reorder keeps the size; the version tells. Exercised through
        load_library so the wrapper's own error class is what callers see."""
        from unittest import mock
        from fplib.errors import FplibAbiError

        with mock.patch.object(_ffi, "FP_STATE_ABI_VERSION",
                               _ffi.FP_STATE_ABI_VERSION + 1):
            with self.assertRaises(FplibAbiError) as ctx:
                _ffi.load_library()
        self.assertIn("different commits", str(ctx.exception))

    def test_library_without_the_query_is_refused(self):
        """A library built before #246 exports neither symbol."""
        from _abi_check import AbiMismatchError, check_state_layout

        class _NoQuery:
            pass

        with self.assertRaises(AbiMismatchError) as ctx:
            check_state_layout(_NoQuery(), prefix="fp", struct=_ffi.FpStateC,
                               expected_version=_ffi.FP_STATE_ABI_VERSION,
                               lib_name="libfpapi.so")
        self.assertIn("before the layout check", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
