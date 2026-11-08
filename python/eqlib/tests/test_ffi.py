"""Direct ctypes-layer tests for :mod:`eqlib._ffi`.

These exercise the FFI without going through the high-level :class:`Eq`
class. They verify that:

* the package imports without a libeqapi.so on disk (load is lazy),
* :class:`EqStateC` has the expected size and field set,
* :func:`load_library` errors clearly when the .so is missing,
* when libeqapi.so **is** present, prototypes are attached and the 6
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

from eqlib import _ffi  # noqa: E402


REPO = HERE.parents[3]
DEFAULT_SO = REPO / "eq" / "libeqapi.so"


def _resolved_so() -> Path:
    """Mirror :func:`_ffi._default_lib_path` for skip predicates."""
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    return DEFAULT_SO


class TestFfiImport(unittest.TestCase):
    """Importing _ffi must not require libeqapi.so on disk."""

    def test_module_imports(self):
        self.assertTrue(hasattr(_ffi, "EqStateC"))
        self.assertTrue(hasattr(_ffi, "load_library"))

    def test_constants_match_header(self):
        # Must match eq/eq_api.h exactly.
        self.assertEqual(_ffi.EQ_MAX_NRGM, 513)
        self.assertEqual(_ffi.EQ_MAX_NZGM, 513)
        self.assertEqual(_ffi.EQ_MAX_NPSM, 513)
        self.assertEqual(_ffi.EQ_MAX_NRM, 1001)
        self.assertEqual(_ffi.EQ_MAX_NTHM, 2049)
        self.assertEqual(_ffi.EQ_MAX_NSUM, 1343)
        self.assertEqual(_ffi.EQ_OK, 0)
        self.assertEqual(_ffi.EQ_ERR_INVALID, 1)
        self.assertEqual(_ffi.EQ_ERR_NOT_INIT, 2)
        self.assertEqual(_ffi.EQ_ERR_CALC_FAILED, 3)
        self.assertEqual(_ffi.EQ_ERR_NOT_IMPL, 4)


class TestEqStateCLayout(unittest.TestCase):
    """Structural checks on the ctypes mirror of ``eq_state_t``."""

    def test_has_expected_fields(self):
        names = [f[0] for f in _ffi.EqStateC._fields_]
        for n in (
            "nrgmax", "nzgmax", "npsmax", "nrmax", "nthmax", "nsumax",
            "raxis", "zaxis", "psi0", "psipa", "psita",
            "qaxis", "qsurf", "betat", "betap", "pvol", "raave", "ripx",
            "psips", "ppps", "ttps", "qqps", "rg", "zg",
        ):
            self.assertIn(n, names, f"missing field {n}")

    def test_size_matches_header_math(self):
        # 9 ints (6 grid counters + 3 secondary nrvmax/nsgmax/ntgmax) +
        # 12 doubles + 4*NPSM + NRGM + NZGM + 7*NRM doubles.
        # 9 ints = 36 bytes; compilers may pad to 40 to align the
        # following double, accept either.
        nps = _ffi.EQ_MAX_NPSM
        nrg = _ffi.EQ_MAX_NRGM
        nzg = _ffi.EQ_MAX_NZGM
        nrm = _ffi.EQ_MAX_NRM
        exp_doubles = 8 * (12 + 4 * nps + nrg + nzg + 7 * nrm)
        sz = ctypes.sizeof(_ffi.EqStateC)
        self.assertIn(
            sz,
            (36 + exp_doubles, 40 + exp_doubles),
            f"unexpected EqStateC size {sz}; "
            f"expected {36 + exp_doubles} or {40 + exp_doubles}",
        )

    def test_array_dimensions(self):
        s = _ffi.EqStateC()
        self.assertEqual(len(s.psips), _ffi.EQ_MAX_NPSM)
        self.assertEqual(len(s.qqps), _ffi.EQ_MAX_NPSM)
        self.assertEqual(len(s.rg), _ffi.EQ_MAX_NRGM)
        self.assertEqual(len(s.zg), _ffi.EQ_MAX_NZGM)


class TestLoadLibraryMissing(unittest.TestCase):
    """Error-path test that runs whether or not .so exists."""

    def test_load_bogus_path_raises(self):
        with self.assertRaises(FileNotFoundError):
            _ffi.load_library("/nonexistent/path/to/libeqapi.so")

    def test_candidate_paths_listed(self):
        cands = _ffi._candidate_paths()
        self.assertTrue(any(str(p).endswith("eq/libeqapi.so") for p in cands))
        self.assertTrue(any(str(p).endswith("lib/libeqapi.so") for p in cands))


@unittest.skipUnless(
    _resolved_so().exists(),
    f"libeqapi.so not built at {_resolved_so()}; "
    "run `make -C eq libeqapi.so`",
)
class TestLoadLibraryReal(unittest.TestCase):
    """Tests that require the real shared library on disk."""

    def test_load_default(self):
        lib = _ffi.load_library()
        self.assertIsInstance(lib, ctypes.CDLL)
        for sym in (
            "eq_init",
            "eq_run",
            "eq_set_param",
            "eq_set_param_str",
            "eq_get_state",
            "eq_finalize",
        ):
            self.assertTrue(hasattr(lib, sym), f"missing export {sym}")

    def test_env_override(self):
        old = os.environ.get("EQLIB_PATH")
        os.environ["EQLIB_PATH"] = str(_resolved_so())
        try:
            lib = _ffi.load_library()
            self.assertIsInstance(lib, ctypes.CDLL)
        finally:
            if old is None:
                os.environ.pop("EQLIB_PATH", None)
            else:
                os.environ["EQLIB_PATH"] = old

    def test_prototypes_applied(self):
        lib = _ffi.load_library()
        self.assertEqual(lib.eq_init.restype, ctypes.c_int)
        self.assertEqual(lib.eq_run.argtypes, [ctypes.c_int])
        self.assertEqual(
            lib.eq_set_param.argtypes,
            [ctypes.c_char_p, ctypes.c_double],
        )
        self.assertEqual(
            lib.eq_set_param_str.argtypes,
            [ctypes.c_char_p, ctypes.c_char_p],
        )


class TestLibraryLayout(unittest.TestCase):
    """#246: the library's eq_state_t layout must be EqStateC's.

    ``load_library`` compares ``eq_state_abi_version()`` / ``eq_state_size()``
    with ``EQ_STATE_ABI_VERSION`` / ``ctypes.sizeof(EqStateC)`` and raises
    ``EqlibAbiError`` on any difference. The guards run in ``setUp``: the
    ``.so`` is a mutable precondition.
    """

    def setUp(self):
        if not _ffi._default_lib_path().exists():
            self.skipTest(f"libeqapi.so not built at {_ffi._default_lib_path()}")
        self.lib = _ffi.load_library()

    def test_library_layout_matches_wrapper(self):
        self.assertEqual(self.lib.eq_state_abi_version(), _ffi.EQ_STATE_ABI_VERSION)
        self.assertEqual(self.lib.eq_state_size(), ctypes.sizeof(_ffi.EqStateC))

    def test_stale_wrapper_layout_is_refused(self):
        """Old wrapper, new library: one field short, the library would
        write past the allocation. Refused before any struct is passed."""
        from _abi_check import AbiMismatchError, check_state_layout

        class Stale(ctypes.Structure):
            _fields_ = _ffi.EqStateC._fields_[:-1]

        with self.assertRaises(AbiMismatchError) as ctx:
            check_state_layout(self.lib, prefix="eq", struct=Stale,
                               expected_version=_ffi.EQ_STATE_ABI_VERSION,
                               lib_name="libeqapi.so")
        self.assertEqual(ctx.exception.library_size, ctypes.sizeof(_ffi.EqStateC))
        self.assertEqual(ctx.exception.wrapper_size, ctypes.sizeof(Stale))

    def test_version_drift_is_refused_through_load_library(self):
        """A reorder keeps the size; the version tells. Exercised through
        load_library so the wrapper's own error class is what callers see."""
        from unittest import mock
        from eqlib.errors import EqlibAbiError

        with mock.patch.object(_ffi, "EQ_STATE_ABI_VERSION",
                               _ffi.EQ_STATE_ABI_VERSION + 1):
            with self.assertRaises(EqlibAbiError) as ctx:
                _ffi.load_library()
        self.assertIn("different commits", str(ctx.exception))

    def test_library_without_the_query_is_refused(self):
        """A library built before #246 exports neither symbol."""
        from _abi_check import AbiMismatchError, check_state_layout

        class _NoQuery:
            pass

        with self.assertRaises(AbiMismatchError) as ctx:
            check_state_layout(_NoQuery(), prefix="eq", struct=_ffi.EqStateC,
                               expected_version=_ffi.EQ_STATE_ABI_VERSION,
                               lib_name="libeqapi.so")
        self.assertIn("before the layout check", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
