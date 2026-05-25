"""Cross-cutting mono routing contract (#208 Phase 2c PR-A).

Pins the contract for python/_runtime_mode.py and the 6 wrappers'
priority-0 mono routing hook. See
docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md
for the full design (D-1..D-7 decisions + acceptance criteria).

Process isolation: pytestmark requests per-test forking; effective when
pytest-forked is installed (which CI always has and local dev installs).
The helper's lru_cache and the wrappers' module-level state both bleed
across in-process tests; forking gives each test a fresh process.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

import pytest

pytestmark = [pytest.mark.forked]

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
PYTHON_ROOT = REPO / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


def _mono_path() -> str:
    p = os.environ.get("MONO_LIB_PATH", "")
    return p if p and os.path.exists(p) else ""


def _totlib_path() -> str:
    p = os.environ.get("TOTLIB_PATH", "")
    return p if p and os.path.exists(p) else ""


@unittest.skipUnless(
    _mono_path(),
    "MONO_LIB_PATH not set or missing; build with "
    "`make -C tot libtotapi_mono.so`",
)
class TestHelperCacheClear(unittest.TestCase):
    """Helper's lru_cache must honor env mutation when cache_clear is
    called. Pins the contract from spec §10 R-1 + D-6.
    """

    def test_helper_cache_clear(self):
        import _runtime_mode

        mono = _mono_path()
        # Save original state for restore in finally block.
        original_mono_lib_path = os.environ.get("MONO_LIB_PATH")

        try:
            # Prime cache with mono.
            os.environ["MONO_LIB_PATH"] = mono
            _runtime_mode.mono_lib_path.cache_clear()
            self.assertEqual(
                _runtime_mode.mono_lib_path(), Path(mono),
                "primed call should return mono path",
            )

            # Mutate env, no clear -> still see cached.
            os.environ["MONO_LIB_PATH"] = ""
            self.assertEqual(
                _runtime_mode.mono_lib_path(), Path(mono),
                "no cache_clear -> still cached",
            )

            # Clear -> empty env now visible.
            _runtime_mode.mono_lib_path.cache_clear()
            self.assertIsNone(
                _runtime_mode.mono_lib_path(),
                "after cache_clear + empty env -> None",
            )
        finally:
            # Restore original MONO_LIB_PATH and clear cache to ensure
            # clean state (protects against case where pytest.mark.forked
            # is somehow not active).
            if original_mono_lib_path is not None:
                os.environ["MONO_LIB_PATH"] = original_mono_lib_path
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()


WRAPPER_MODULES = (
    ("eqlib._ffi",   "EQLIB_PATH",   "eq/libeqapi.so"),
    ("trlib._ffi",   "TRLIB_PATH",   "tr/libtrapi.so"),
    ("fplib._ffi",   "FPLIB_PATH",   "fp/libfpapi.so"),
    ("tilib._ffi",   "TILIB_PATH",   "ti/libtiapi.so"),
    ("wrxlib._ffi",  "WRXLIB_PATH",  "wrx/libwrxapi.so"),
    ("totlib._ffi",  "TOTLIB_PATH",  "tot/libtotapi.so"),
)


def _import_ffi(modname: str):
    """Import e.g. 'eqlib._ffi' and return the module."""
    parts = modname.split(".")
    mod = __import__(modname)
    for p in parts[1:]:
        mod = getattr(mod, p)
    return mod


@unittest.skipUnless(
    _mono_path(),
    "MONO_LIB_PATH not set or missing",
)
class TestAllWrappersRouting(unittest.TestCase):
    """All 6 wrappers (eqlib/trlib/fplib/tilib/wrxlib/totlib) consume
    the priority-0 mono routing hook from _runtime_mode.
    """

    def test_unset_falls_back_to_per_module(self):
        import _runtime_mode

        original_mono_lib_path = os.environ.get("MONO_LIB_PATH")

        try:
            os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()
            for modname, _envname, suffix in WRAPPER_MODULES:
                with self.subTest(wrapper=modname):
                    ffi = _import_ffi(modname)
                    resolved = ffi._default_lib_path()
                    self.assertTrue(
                        str(resolved).endswith(suffix)
                        or str(resolved).endswith(
                            "lib/" + suffix.split("/")[-1]
                        ),
                        f"{modname} expected per-module {suffix}, "
                        f"got {resolved}",
                    )
        finally:
            if original_mono_lib_path is not None:
                os.environ["MONO_LIB_PATH"] = original_mono_lib_path
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()

    def test_set_routes_all_wrappers(self):
        import _runtime_mode

        mono = _mono_path()
        original_mono_lib_path = os.environ.get("MONO_LIB_PATH")

        try:
            os.environ["MONO_LIB_PATH"] = mono
            _runtime_mode.mono_lib_path.cache_clear()
            for modname, _envname, _suffix in WRAPPER_MODULES:
                with self.subTest(wrapper=modname):
                    ffi = _import_ffi(modname)
                    resolved = ffi._default_lib_path()
                    self.assertEqual(
                        resolved, Path(mono),
                        f"{modname}: MONO_LIB_PATH set but got {resolved}",
                    )
        finally:
            if original_mono_lib_path is not None:
                os.environ["MONO_LIB_PATH"] = original_mono_lib_path
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()

    def test_missing_file_raises(self):
        import _runtime_mode

        original_mono_lib_path = os.environ.get("MONO_LIB_PATH")

        try:
            os.environ["MONO_LIB_PATH"] = "/nonexistent_mono.so"
            _runtime_mode.mono_lib_path.cache_clear()
            for modname, _envname, _suffix in WRAPPER_MODULES:
                with self.subTest(wrapper=modname):
                    ffi = _import_ffi(modname)
                    with self.assertRaises(FileNotFoundError):
                        ffi._default_lib_path()
        finally:
            if original_mono_lib_path is not None:
                os.environ["MONO_LIB_PATH"] = original_mono_lib_path
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
