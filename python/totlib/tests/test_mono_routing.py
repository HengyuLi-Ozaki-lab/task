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
                    with self.assertRaises(FileNotFoundError) as ctx:
                        ffi._default_lib_path()
                    self.assertIn(
                        "does not exist", str(ctx.exception),
                        f"{modname} raised FileNotFoundError but message lacks "
                        f"'does not exist': {ctx.exception}",
                    )
        finally:
            if original_mono_lib_path is not None:
                os.environ["MONO_LIB_PATH"] = original_mono_lib_path
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()

    def test_per_module_env_var_still_honored(self):
        """MONO_LIB_PATH unset + per-module env var set -> uses
        per-module env (priority 1, unchanged from pre-#208 behavior).
        Pins D-5: the 4-step default chain stays verbatim when MONO
        is inactive (spec §8.1 LOW-3).
        """
        import _runtime_mode
        import tempfile

        # Capture mono path BEFORE popping MONO_LIB_PATH from env
        # (once popped, _mono_path() returns "" which resolves to ".").
        mono_so = _mono_path()
        original_mono = os.environ.pop("MONO_LIB_PATH", None)
        _runtime_mode.mono_lib_path.cache_clear()
        try:
            # Use a path that exists so the env-var branch returns it.
            # Reuse the mono .so path as a sentinel — its filename is
            # NOT libtrapi.so / libeqapi.so / ... so we can detect
            # that the env-var step is what selected it.
            with tempfile.TemporaryDirectory() as td:
                fake = Path(td) / "fake-per-module.so"
                fake.write_bytes(Path(mono_so).read_bytes()[:100])
                for modname, envname, _suffix in WRAPPER_MODULES:
                    with self.subTest(wrapper=modname, env=envname):
                        os.environ[envname] = str(fake)
                        try:
                            ffi = _import_ffi(modname)
                            resolved = ffi._default_lib_path()
                            self.assertEqual(
                                resolved, fake,
                                f"{modname}: {envname}={fake} but "
                                f"got {resolved}",
                            )
                        finally:
                            os.environ.pop(envname, None)
        finally:
            if original_mono is not None:
                os.environ["MONO_LIB_PATH"] = original_mono
            _runtime_mode.mono_lib_path.cache_clear()


@unittest.skipUnless(
    _mono_path() and _totlib_path(),
    "MONO_LIB_PATH and TOTLIB_PATH must both be set",
)
class TestNonMonoSoRaises(unittest.TestCase):
    """MONO_LIB_PATH pointed at a default (per-module-link)
    libtotapi.so -> RuntimeError. The default .so has tot_is_mono()
    returning 0, not 1.
    """

    def test_non_mono_so_raises(self):
        import _runtime_mode
        from eqlib import _ffi as eqlib_ffi

        original_mono = os.environ.get("MONO_LIB_PATH")
        os.environ["MONO_LIB_PATH"] = _totlib_path()
        _runtime_mode.mono_lib_path.cache_clear()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                eqlib_ffi._default_lib_path()
            self.assertIn("not a mono image", str(ctx.exception))
        finally:
            if original_mono is not None:
                os.environ["MONO_LIB_PATH"] = original_mono
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()


# Candidates for "a valid dlopen-able .so / .dylib that does NOT
# contain tot_is_mono" — used to test the §6 hasattr guard.
# Requirements: (a) real file on disk (Path.exists() == True), so it
# passes _runtime_mode's p.exists() gate; (b) can be dlopen'd; (c) no
# tot_is_mono symbol.
#
# Note: on macOS 12+ (dyld shared cache) system libraries like
# /usr/lib/libc.dylib or /usr/lib/libSystem.B.dylib are NOT present as
# real files (Path.exists() -> False), so they fail _runtime_mode's
# p.exists() check and raise FileNotFoundError instead of the RuntimeError
# we want. Use files that are real on disk: /usr/lib/libobjc-trampolines.dylib
# (macOS 12+) is always a real file and dlopen-able without tot_is_mono.
_UNRELATED_SO_CANDIDATES = (
    "/usr/lib/x86_64-linux-gnu/libc.so.6",       # Debian/Ubuntu
    "/lib/x86_64-linux-gnu/libc.so.6",           # older Debian
    "/lib64/libc.so.6",                          # RHEL/Fedora/CentOS
    "/usr/lib64/libc.so.6",                      # RHEL alt
    "/usr/lib/libc.so.6",                        # Arch + others
    "/lib/libc.musl-x86_64.so.1",                # Alpine musl
    "/usr/lib/libobjc-trampolines.dylib",        # macOS 12+ (real file, no tot_is_mono)
    "/usr/lib/libffi-trampolines.dylib",         # macOS 12+ alt
)

_UNRELATED_SO_PATH = next(
    (c for c in _UNRELATED_SO_CANDIDATES if Path(c).exists()),
    "",
)


@unittest.skipUnless(
    _UNRELATED_SO_PATH,
    "no unrelated .so / .dylib found at any expected location",
)
class TestWrongSoWithoutTotIsMono(unittest.TestCase):
    """MONO_LIB_PATH set to a valid but unrelated .so (libc /
    libobjc-trampolines) -> RuntimeError mentioning the missing
    tot_is_mono symbol. Exercises the §6 hasattr guard.
    """

    def test_wrong_so_without_tot_is_mono_raises(self):
        import _runtime_mode
        from eqlib import _ffi as eqlib_ffi

        unrelated = _UNRELATED_SO_PATH
        if not unrelated:
            self.skipTest("no unrelated .so candidate found at runtime")

        original_mono = os.environ.get("MONO_LIB_PATH")
        os.environ["MONO_LIB_PATH"] = unrelated
        _runtime_mode.mono_lib_path.cache_clear()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                eqlib_ffi._default_lib_path()
            self.assertIn("tot_is_mono", str(ctx.exception))
        finally:
            if original_mono is not None:
                os.environ["MONO_LIB_PATH"] = original_mono
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()


class TestUnreadableSoRaises(unittest.TestCase):
    """MONO_LIB_PATH set to a path whose contents are NOT a valid
    shared object (e.g. an empty file) -> friendly RuntimeError
    (NOT a raw OSError). Exercises the §6 try/except OSError wrap.
    """

    def test_unreadable_so_raises_runtime_error(self):
        import _runtime_mode
        import tempfile
        from eqlib import _ffi as eqlib_ffi

        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "not-a-real.so"
            bad.write_text("this is not an ELF/Mach-O shared object\n")

            original_mono = os.environ.get("MONO_LIB_PATH")
            os.environ["MONO_LIB_PATH"] = str(bad)
            _runtime_mode.mono_lib_path.cache_clear()
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    eqlib_ffi._default_lib_path()
                self.assertIn(
                    "cannot be dlopen'd", str(ctx.exception),
                )
            finally:
                if original_mono is not None:
                    os.environ["MONO_LIB_PATH"] = original_mono
                else:
                    os.environ.pop("MONO_LIB_PATH", None)
                _runtime_mode.mono_lib_path.cache_clear()


@unittest.skipUnless(
    _mono_path() and _totlib_path(),
    "MONO_LIB_PATH and TOTLIB_PATH must both be set",
)
class TestExplicitConstructorPathWins(unittest.TestCase):
    """Explicit ``lib_path=...`` to a high-level wrapper constructor
    STILL wins over MONO_LIB_PATH (spec D-5 + §7 Combined
    precedence). Uses the user-facing Tot(lib_path=...) constructor,
    not the low-level _ffi.load_library, so a regression here would
    be visible to actual library users.
    """

    def test_explicit_constructor_path_still_wins(self):
        import _runtime_mode
        from totlib import Tot

        original_mono = os.environ.get("MONO_LIB_PATH")
        os.environ["MONO_LIB_PATH"] = _mono_path()
        _runtime_mode.mono_lib_path.cache_clear()
        try:
            # Pass the default .so explicitly; it should be used,
            # NOT the mono path.
            tot = Tot(lib_path=_totlib_path())
            self.assertEqual(
                tot._lib._name, _totlib_path(),
                f"explicit lib_path should override MONO; "
                f"got {tot._lib._name}, expected {_totlib_path()}",
            )
            tot.close()
        finally:
            if original_mono is not None:
                os.environ["MONO_LIB_PATH"] = original_mono
            else:
                os.environ.pop("MONO_LIB_PATH", None)
            _runtime_mode.mono_lib_path.cache_clear()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
