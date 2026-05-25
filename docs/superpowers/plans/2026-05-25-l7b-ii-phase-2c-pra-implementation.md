# L-7b-ii Phase 2c PR-A — Wrapper mono routing implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the single-authoritative mono routing contract from the design spec — `MONO_LIB_PATH` env var honored by a shared `python/_runtime_mode.py` helper, consumed by all 6 wrappers' `_ffi.py` loaders. NO behavioral rule activation in this PR (PR-B's scope).

**Architecture:** New top-level helper module `python/_runtime_mode.py` exposes `mono_lib_path()` which reads `MONO_LIB_PATH`, validates via dlopen + `tot_is_mono()`, returns `Path` or `None`. Each `python/{eqlib,trlib,fplib,tilib,wrxlib,totlib}/_ffi.py::_default_lib_path()` consults the helper as priority 0 before its existing 4-step resolution. Explicit `lib_path=` to a wrapper constructor still wins (most-specific override). One cross-cutting test file `python/totlib/tests/test_mono_routing.py` exercises the 9 contract cases.

**Tech Stack:** Python 3.10+ (CI 3.11/3.13), ctypes, `functools.lru_cache`, pytest 8 + pytest-forked. Fortran/build-system changes: none.

**Spec:** `docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md` (Codex 3-round SHIP IT).

**Branch base:** `origin/develop` at `c350381b` or later (spec already landed there).

---

## File Structure

**Created:**
- `python/_runtime_mode.py` — single authoritative mono routing helper.
- `python/totlib/tests/test_mono_routing.py` — 9 contract test cases.

**Modified:**
- `python/eqlib/_ffi.py` — `_default_lib_path()` gains priority-0 mono check.
- `python/trlib/_ffi.py` — same pattern.
- `python/fplib/_ffi.py` — same pattern.
- `python/tilib/_ffi.py` — same pattern.
- `python/wrxlib/_ffi.py` — same pattern.
- `python/totlib/_ffi.py` — same pattern (MONO overrides TOTLIB_PATH).
- `.github/workflows/python-tests.yml` — extend mono-build job to run new test with `MONO_LIB_PATH` and `TOTLIB_PATH` set.
- `tot/tot_api.h` — header comment mentions mono routing (no ABI change).
- `python/totlib/README.md` — short note + link to spec.

**Boundaries:** No Fortran source changes. No changes to `python/totlib/pipeline.py::_MONO_ONLY_RULES` (that lives in PR-B).

---

## Task 0: Worktree + baseline build

**Files:** none yet — environment setup.

- [ ] **Step 1: Confirm on develop with no local changes**

```bash
cd /Users/k-yoshimi/Dropbox/cursor/task
git fetch origin develop --quiet
git checkout develop
git pull --quiet
git log --oneline -1
```

Expected: HEAD matches `c350381b` or later (`docs(spec): L-7b-ii Phase 2c PR-A...`).

- [ ] **Step 2: Create worktree off develop**

```bash
git worktree add .claude/worktrees/l7b-ii-phase-2c-pra -b l7b-ii-phase-2c-pra origin/develop
cd .claude/worktrees/l7b-ii-phase-2c-pra
```

Expected: worktree created on a new branch tracking origin/develop.

- [ ] **Step 3: Copy build-config artifacts (gitignored)**

```bash
cp /Users/k-yoshimi/Dropbox/cursor/task/make.header make.header
cp /Users/k-yoshimi/Dropbox/cursor/task/mtxp/make.mtxp mtxp/make.mtxp
ls -l make.header mtxp/make.mtxp
```

Expected: both files present.

- [ ] **Step 4: Ensure bpsd symlink at worktrees parent**

```bash
test -L /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/bpsd \
  || ln -s /Users/k-yoshimi/Dropbox/cursor/task/../bpsd \
        /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/bpsd
readlink /Users/k-yoshimi/Dropbox/cursor/task/.claude/worktrees/bpsd
# From the worktree root, the build chain's `../../bpsd` from `pl/`
# resolves to `<wt-root>/../bpsd` (i.e. `.claude/worktrees/bpsd`).
# Verify the symlink resolves to the canonical bpsd checkout.
realpath ../bpsd
```

Expected: symlink resolves to the canonical bpsd checkout (e.g. `/Users/k-yoshimi/Dropbox/cursor/bpsd`).

- [ ] **Step 5: Build the mono image AND the default per-module image**

```bash
make -C dp libdp_pic.a
make -C ob libob_pic.a
make -C open-adas/adf11/adf11-lib lib-adf11_pic.a
make -C adpost lib-adpost_pic.a
make -C tot libtotapi.so libtotapi_mono.so
ls -l tot/libtotapi*.so
```

Expected: both `tot/libtotapi.so` and `tot/libtotapi_mono.so` present.

- [ ] **Step 6: Sanity — existing test suite green on baseline**

```bash
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
export TOTLIB_PATH="$PWD/tot/libtotapi.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/test_mono_bpsd_smoke.py totlib/tests/test_tot_init_eq_api_cascade.py -v 2>&1) | tail -15
```

Expected: 5 passed (3 from mono_bpsd_smoke + 2 from cascade).

---

## Task 1: Helper module `python/_runtime_mode.py`

**Files:**
- Create: `python/_runtime_mode.py`
- Create: `python/totlib/tests/test_mono_routing.py` (skeleton, will grow across tasks)

- [ ] **Step 1: Write the first failing test — `test_helper_cache_clear`**

Create `python/totlib/tests/test_mono_routing.py`:

```python
"""Cross-cutting mono routing contract (#208 Phase 2c PR-A).

Pins the contract for python/_runtime_mode.py and the 6 wrappers'
priority-0 mono routing hook. See
docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md
for the full design (D-1..D-7 decisions + acceptance criteria).

Process isolation: pytestmark forces per-test forking even when the
runner forgets `--forked`. The helper's lru_cache and the wrappers'
module-level state both bleed across in-process tests; forking
gives each test a fresh process.
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails for the right reason**

```bash
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/test_mono_routing.py -v 2>&1) | tail -10
```

Expected: FAIL or ERROR — `ModuleNotFoundError: No module named '_runtime_mode'`.

- [ ] **Step 3: Create `python/_runtime_mode.py` with the helper**

Create `python/_runtime_mode.py`:

```python
"""Single authoritative source for runtime-mode routing decisions.

Today this owns only the MONO_LIB_PATH env var contract introduced by
#208 Phase 2c PR-A. Future runtime concerns (build flavor, debug
mode) can land here without touching per-module _ffi.py loaders
again. See docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-
loader-contract-design.md for the full design.
"""
from __future__ import annotations

import ctypes
import functools
import os
from pathlib import Path
from typing import Optional


@functools.lru_cache(maxsize=None)
def mono_lib_path() -> Optional[Path]:
    """Return Path to libtotapi_mono.so if MONO_LIB_PATH is set and
    points at a valid mono image; return None otherwise.

    Raises:
        FileNotFoundError: MONO_LIB_PATH set, file missing.
        RuntimeError:      MONO_LIB_PATH set, file is not a mono image
                           (dlopen failed, or tot_is_mono symbol
                           missing, or tot_is_mono() returned 0).

    Cache:
        Result memoized for the lifetime of the Python process.
        Call ``mono_lib_path.cache_clear()`` if the env var is
        mutated at runtime (tests; production code never needs this).
        Under pytest's ``--forked`` each test runs in a fresh
        subprocess so the cache is naturally invalidated between
        tests.
    """
    env = os.environ.get("MONO_LIB_PATH", "").strip()
    if not env:
        return None
    p = Path(env)
    if not p.exists():
        raise FileNotFoundError(
            f"MONO_LIB_PATH={env!r} does not exist. Unset the env "
            "var or build the mono image: "
            "`make -C tot libtotapi_mono.so`."
        )
    # Wrap CDLL so wrong-arch / non-ELF / dep-broken .so files
    # surface as the friendly RuntimeError, NOT a raw OSError with a
    # cryptic dlerror string.
    try:
        lib = ctypes.CDLL(
            str(p), mode=getattr(ctypes, "RTLD_LAZY", 1)
        )
    except OSError as exc:
        raise RuntimeError(
            f"MONO_LIB_PATH={env!r} cannot be dlopen'd: {exc}. "
            "Likely wrong architecture, non-ELF, or missing "
            "dependency. Build via "
            "`make -C tot libtotapi_mono.so` on the same host."
        ) from exc
    if not hasattr(lib, "tot_is_mono"):
        raise RuntimeError(
            f"MONO_LIB_PATH={env!r} exposes no `tot_is_mono` "
            "symbol. This indicates a pre-Phase-2b .so. Rebuild "
            "against develop or a newer branch."
        )
    lib.tot_is_mono.restype = ctypes.c_int
    lib.tot_is_mono.argtypes = []
    if lib.tot_is_mono() != 1:
        raise RuntimeError(
            f"MONO_LIB_PATH={env!r} is not a mono image "
            "(tot_is_mono() returned 0). Set MONO_LIB_PATH to a "
            "libtotapi_mono.so built via "
            "`make -C tot libtotapi_mono.so`."
        )
    return p


__all__ = ["mono_lib_path"]
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/test_mono_routing.py -v 2>&1) | tail -10
```

Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add python/_runtime_mode.py python/totlib/tests/test_mono_routing.py
git commit -m "$(cat <<'EOF'
feat(python): MONO_LIB_PATH helper + cache_clear test (#208 PR-A)

Adds python/_runtime_mode.py with mono_lib_path() — the single
authoritative reader for the MONO_LIB_PATH env var. Strict + verify
per spec D-4: missing file -> FileNotFoundError; failed dlopen ->
RuntimeError; missing tot_is_mono symbol -> RuntimeError;
tot_is_mono() != 1 -> RuntimeError. lru_cache'd; cache_clear()
exposed for runtime env mutation (tests).

First test case from spec §8.1: test_helper_cache_clear pins the
cache + cache_clear contract so future refactors cannot silently
regress R-1.

Wrappers in subsequent commits will consume this helper as
priority-0 in their _default_lib_path() chains.

Spec: docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Wire eqlib + first routing tests

**Files:**
- Modify: `python/eqlib/_ffi.py` (add import + priority-0 in `_default_lib_path()`)
- Modify: `python/totlib/tests/test_mono_routing.py` (add 3 wrapper-flow tests)

- [ ] **Step 1: Add 3 failing tests (unset, set, missing-file) that go through eqlib**

Append to `python/totlib/tests/test_mono_routing.py` (after `TestHelperCacheClear`):

```python
@unittest.skipUnless(
    _mono_path(),
    "MONO_LIB_PATH not set or missing",
)
class TestEqlibRouting(unittest.TestCase):
    """First wrapper wiring (eqlib). Other wrappers added in Task 3."""

    def test_unset_falls_back_to_per_module(self):
        """MONO_LIB_PATH unset -> eqlib uses per-module default."""
        import _runtime_mode
        from eqlib import _ffi as eqlib_ffi

        os.environ.pop("MONO_LIB_PATH", None)
        _runtime_mode.mono_lib_path.cache_clear()

        resolved = eqlib_ffi._default_lib_path()
        self.assertTrue(
            str(resolved).endswith("eq/libeqapi.so")
            or str(resolved).endswith("lib/libeqapi.so"),
            f"expected per-module libeqapi.so, got {resolved}",
        )

    def test_set_routes_eqlib(self):
        """MONO_LIB_PATH set -> eqlib routes to mono image."""
        import _runtime_mode
        from eqlib import _ffi as eqlib_ffi

        mono = _mono_path()
        os.environ["MONO_LIB_PATH"] = mono
        _runtime_mode.mono_lib_path.cache_clear()

        resolved = eqlib_ffi._default_lib_path()
        self.assertEqual(
            resolved, Path(mono),
            f"MONO_LIB_PATH set but eqlib got {resolved}",
        )

    def test_missing_file_raises(self):
        """MONO_LIB_PATH points to /nonexistent -> FileNotFoundError."""
        import _runtime_mode
        from eqlib import _ffi as eqlib_ffi

        os.environ["MONO_LIB_PATH"] = "/nonexistent_mono.so"
        _runtime_mode.mono_lib_path.cache_clear()

        with self.assertRaises(FileNotFoundError) as ctx:
            eqlib_ffi._default_lib_path()
        self.assertIn("does not exist", str(ctx.exception))
```

- [ ] **Step 2: Verify these tests FAIL**

```bash
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/test_mono_routing.py::TestEqlibRouting -v 2>&1) | tail -15
```

Expected:
- `test_unset_falls_back_to_per_module`: PASS (eqlib already returns per-module path; our change is additive)
- `test_set_routes_eqlib`: FAIL (eqlib does NOT yet consult `_runtime_mode`)
- `test_missing_file_raises`: FAIL (same reason)

- [ ] **Step 3: Modify `python/eqlib/_ffi.py` — add top-level import**

Locate the import block near the top of the file (just after `from typing import Optional`). Insert:

```python
from _runtime_mode import mono_lib_path
```

Top-level (not function-local) per spec §10 R-3 explicit decision: "wrappers' tests already assume `python/` is on `sys.path`, and production users do too." Putting the import at module top avoids paying the import cost on every `_default_lib_path()` call and keeps the dependency declarative.

- [ ] **Step 4: Modify `python/eqlib/_ffi.py` — add priority-0 hook**

Locate `_default_lib_path()` (around line 169). Replace it with:

```python
def _default_lib_path() -> Path:
    """Resolve the default ``libeqapi.so`` path.

    Priority (highest first):
      0. ``mono_lib_path()`` — global mono override
         (``MONO_LIB_PATH`` env var). See #208 Phase 2c PR-A spec.
      1. ``EQLIB_PATH`` env var
      2. ``<repo>/eq/libeqapi.so``
      3. ``<repo>/lib/libeqapi.so``

    ``load_library(path=...)`` still accepts an explicit override that
    wins over (0) — the early ``if path:`` branch runs before this
    function is consulted.
    """
    mono = mono_lib_path()
    if mono is not None:
        return mono
    env = os.environ.get("EQLIB_PATH")
    if env:
        return Path(env)
    for cand in _candidate_paths():
        if cand.exists():
            return cand
    return _candidate_paths()[0]
```

Also update the module docstring's "Library-path resolution order" (around line 10) to prepend the new priority 0:

```python
"""Low-level ctypes FFI for libeqapi.so.

Mirrors ``eq/eq_api.h`` (C ABI). Higher-level helpers live in
``eqlib.py``; this module intentionally exposes only raw ctypes objects
so tests can exercise the boundary directly.

Library-path resolution order (first match wins):

0. ``MONO_LIB_PATH`` env var (#208 PR-A): if set, all wrappers route
   to the same monolithic image so eq/tr/etc. share one BPSD broker.
1. explicit ``path`` argument to :func:`load_library`
2. ``EQLIB_PATH`` environment variable
3. ``<repo>/eq/libeqapi.so`` (standard L-4 build location)
4. ``<repo>/lib/libeqapi.so`` (install-style location, future-proofing)

The package layout is ``python/eqlib/_ffi.py`` so the repository root is
two parents above this file (``__file__.parents[2]``).
"""
```

- [ ] **Step 5: Verify the 3 tests pass**

```bash
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/test_mono_routing.py -v 2>&1) | tail -15
```

Expected: 4 passed (TestHelperCacheClear + 3 from TestEqlibRouting).

- [ ] **Step 6: Verify eqlib's own test suite still green (no regression)**

```bash
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal eqlib/tests/ 2>&1) | tail -5
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add python/eqlib/_ffi.py python/totlib/tests/test_mono_routing.py
git commit -m "$(cat <<'EOF'
feat(eqlib): consume MONO_LIB_PATH helper as priority 0 (#208 PR-A)

eqlib._ffi._default_lib_path() now consults
python._runtime_mode.mono_lib_path() before its existing 4-step
resolution. If MONO_LIB_PATH is set + valid, the wrapper loads the
monolithic image instead of libeqapi.so. Explicit lib_path=... to
the Eqlib(...) constructor still wins (early branch in load_library
runs first).

Adds 3 tests from spec §8.1 going through the eqlib path:
test_unset_falls_back_to_per_module, test_set_routes_eqlib,
test_missing_file_raises. Other 5 wrappers wired in next commit;
test_set_routes_all_wrappers (5 of 6) lands after the rollout.

eqlib's own test suite (eqlib/tests/) stays green.

Spec: docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Roll out wiring to 5 remaining wrappers

**Files:**
- Modify: `python/trlib/_ffi.py`
- Modify: `python/fplib/_ffi.py`
- Modify: `python/tilib/_ffi.py`
- Modify: `python/wrxlib/_ffi.py`
- Modify: `python/totlib/_ffi.py`
- Modify: `python/totlib/tests/test_mono_routing.py` (expand to all-6 assertion + add 2 more cases)

The pattern is identical for each wrapper: add top-level `from _runtime_mode import mono_lib_path`, prepend `mono_lib_path()` as priority 0 in `_default_lib_path()`, update docstring. Below shows the per-wrapper substitution after the eqlib template from Task 2.

- [ ] **Step 1: Modify `python/trlib/_ffi.py`**

Add to the import block (just after `from typing import Optional`):

```python
from _runtime_mode import mono_lib_path
```

Locate the analogous `_default_lib_path()` (search `def _default_lib_path`) and replace with:

```python
def _default_lib_path() -> Path:
    """Resolve the default ``libtrapi.so`` path.

    Priority (highest first):
      0. ``mono_lib_path()`` — global mono override (``MONO_LIB_PATH``)
      1. ``TRLIB_PATH`` env var
      2. ``<repo>/tr/libtrapi.so``
      3. ``<repo>/lib/libtrapi.so``
    """
    mono = mono_lib_path()
    if mono is not None:
        return mono
    env = os.environ.get("TRLIB_PATH")
    if env:
        return Path(env)
    for cand in _candidate_paths():
        if cand.exists():
            return cand
    return _candidate_paths()[0]
```

Update module docstring to prepend priority 0 (same shape as eqlib's docstring update in Task 2 Step 4, the "add priority-0 hook" step).

- [ ] **Step 2: Modify `python/fplib/_ffi.py`** — identical pattern with `FPLIB_PATH`.

Add top-level import alongside the other imports:

```python
from _runtime_mode import mono_lib_path
```

Replace `_default_lib_path()`:

```python
def _default_lib_path() -> Path:
    """Resolve the default ``libfpapi.so`` path.

    Priority (highest first):
      0. ``mono_lib_path()`` — global mono override (``MONO_LIB_PATH``)
      1. ``FPLIB_PATH`` env var
      2. ``<repo>/fp/libfpapi.so``
      3. ``<repo>/lib/libfpapi.so``
    """
    mono = mono_lib_path()
    if mono is not None:
        return mono
    env = os.environ.get("FPLIB_PATH")
    if env:
        return Path(env)
    for cand in _candidate_paths():
        if cand.exists():
            return cand
    return _candidate_paths()[0]
```

Update docstring header analogously.

- [ ] **Step 3: Modify `python/tilib/_ffi.py`** — `TILIB_PATH`.

Add top-level import:

```python
from _runtime_mode import mono_lib_path
```

Replace `_default_lib_path()`:

```python
def _default_lib_path() -> Path:
    """Resolve the default ``libtiapi.so`` path.

    Priority (highest first):
      0. ``mono_lib_path()`` — global mono override (``MONO_LIB_PATH``)
      1. ``TILIB_PATH`` env var
      2. ``<repo>/ti/libtiapi.so``
      3. ``<repo>/lib/libtiapi.so``
    """
    mono = mono_lib_path()
    if mono is not None:
        return mono
    env = os.environ.get("TILIB_PATH")
    if env:
        return Path(env)
    for cand in _candidate_paths():
        if cand.exists():
            return cand
    return _candidate_paths()[0]
```

Update docstring header analogously.

- [ ] **Step 4: Modify `python/wrxlib/_ffi.py`** — `WRXLIB_PATH`.

Add top-level import:

```python
from _runtime_mode import mono_lib_path
```

Replace `_default_lib_path()`:

```python
def _default_lib_path() -> Path:
    """Resolve the default ``libwrxapi.so`` path.

    Priority (highest first):
      0. ``mono_lib_path()`` — global mono override (``MONO_LIB_PATH``)
      1. ``WRXLIB_PATH`` env var
      2. ``<repo>/wrx/libwrxapi.so``
      3. ``<repo>/lib/libwrxapi.so``
    """
    mono = mono_lib_path()
    if mono is not None:
        return mono
    env = os.environ.get("WRXLIB_PATH")
    if env:
        return Path(env)
    for cand in _candidate_paths():
        if cand.exists():
            return cand
    return _candidate_paths()[0]
```

Update docstring header analogously.

- [ ] **Step 5: Modify `python/totlib/_ffi.py`** — `TOTLIB_PATH` (D-7 explicitly applies: MONO overrides TOTLIB_PATH on tot itself).

Add top-level import:

```python
from _runtime_mode import mono_lib_path
```

Replace `_default_lib_path()`:

```python
def _default_lib_path() -> Path:
    """Resolve the default ``libtotapi.so`` path.

    Priority (highest first):
      0. ``mono_lib_path()`` — global mono override (``MONO_LIB_PATH``).
         When set, the orchestrator wrapper loads the same monolithic
         image as the sibling per-module wrappers — see #208 PR-A
         spec D-7 for why TOTLIB_PATH is subordinated here.
      1. ``TOTLIB_PATH`` env var
      2. ``<repo>/tot/libtotapi.so``
      3. ``<repo>/lib/libtotapi.so``
    """
    mono = mono_lib_path()
    if mono is not None:
        return mono
    env = os.environ.get("TOTLIB_PATH")
    if env:
        return Path(env)
    for cand in _candidate_paths():
        if cand.exists():
            return cand
    return _candidate_paths()[0]
```

Update docstring header analogously.

- [ ] **Step 6: Replace `TestEqlibRouting` with the cross-cutting `TestAllWrappersRouting`**

In `python/totlib/tests/test_mono_routing.py`, replace the `TestEqlibRouting` class with:

```python
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

    def test_set_routes_all_wrappers(self):
        import _runtime_mode

        mono = _mono_path()
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

    def test_missing_file_raises(self):
        import _runtime_mode

        os.environ["MONO_LIB_PATH"] = "/nonexistent_mono.so"
        _runtime_mode.mono_lib_path.cache_clear()
        for modname, _envname, _suffix in WRAPPER_MODULES:
            with self.subTest(wrapper=modname):
                ffi = _import_ffi(modname)
                with self.assertRaises(FileNotFoundError):
                    ffi._default_lib_path()
```

- [ ] **Step 7: Run the routing tests across all 6 wrappers**

```bash
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/test_mono_routing.py -v 2>&1) | tail -20
```

Expected: 4 tests pass (TestHelperCacheClear + 3 from TestAllWrappersRouting).

- [ ] **Step 8: Verify each per-module wrapper's own test suite still green**

```bash
for mod in eqlib trlib fplib tilib wrxlib totlib; do
  echo "=== $mod ==="
  (cd python && python -m pytest --forked --timeout=120 --timeout-method=signal $mod/tests/ 2>&1) | tail -3
done
```

Expected: every module's suite passes (no regressions from the priority-0 insertion).

- [ ] **Step 9: Commit**

```bash
git add python/{trlib,fplib,tilib,wrxlib,totlib}/_ffi.py \
        python/totlib/tests/test_mono_routing.py
git commit -m "$(cat <<'EOF'
feat(wrappers): wire 5 remaining wrappers to MONO_LIB_PATH helper

Roll out the priority-0 mono routing hook from eqlib (prior commit)
to trlib, fplib, tilib, wrxlib, and totlib. Pattern is identical
across wrappers — only the per-module <MOD>LIB_PATH name differs.

totlib's hook (D-7): MONO_LIB_PATH overrides TOTLIB_PATH on the
orchestrator wrapper, so a TotPipeline whose Tot has mono routing
gets a consistent broker view across all 6 wrappers it instantiates.

Tests expanded to a parameterized TestAllWrappersRouting that
exercises all 6 wrappers in a single subTest loop for each of:
unset_falls_back_to_per_module, set_routes_all_wrappers,
missing_file_raises.

Per-module test suites (eqlib/tests, trlib/tests, ...) all stay
green — priority-0 insertion is additive when MONO_LIB_PATH is
unset, which is the case for those existing tests.

Spec: docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Remaining 5 spec test cases

**Files:**
- Modify: `python/totlib/tests/test_mono_routing.py`

- [ ] **Step 1: Add `test_per_module_env_var_still_honored`**

Append to `TestAllWrappersRouting` (or as a new method in the same class):

```python
    def test_per_module_env_var_still_honored(self):
        """MONO_LIB_PATH unset + per-module env var set -> uses
        per-module env (priority 1, unchanged from pre-#208 behavior).
        Pins D-5: the 4-step default chain stays verbatim when MONO
        is inactive (spec §8.1 LOW-3).
        """
        import _runtime_mode
        import tempfile

        os.environ.pop("MONO_LIB_PATH", None)
        _runtime_mode.mono_lib_path.cache_clear()

        # Use a path that exists so the env-var branch returns it.
        # Reuse the mono .so path as a sentinel — its filename is
        # NOT libtrapi.so / libeqapi.so / ... so we can detect that
        # the env-var step is what selected it.
        mono_so = _mono_path()
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
                            f"{modname}: {envname}={fake} but got "
                            f"{resolved}",
                        )
                    finally:
                        os.environ.pop(envname, None)
```

- [ ] **Step 2: Add `test_non_mono_so_raises`**

```python
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

        os.environ["MONO_LIB_PATH"] = _totlib_path()
        _runtime_mode.mono_lib_path.cache_clear()
        with self.assertRaises(RuntimeError) as ctx:
            eqlib_ffi._default_lib_path()
        self.assertIn("not a mono image", str(ctx.exception))
```

- [ ] **Step 3: Add `test_wrong_so_without_tot_is_mono_raises`**

```python
# Cover Debian/Ubuntu, RHEL/Fedora/CentOS (lib64), older Linux,
# musl-based distros (Alpine), and macOS's libSystem fallback. The
# class-level skipUnless gates on any candidate existing; the
# loop inside test_* picks the first match so the friendly RuntimeError
# we raise actually points at a real dlopen-able .so.
_LIBC_CANDIDATES = (
    "/usr/lib/x86_64-linux-gnu/libc.so.6",       # Debian/Ubuntu
    "/lib/x86_64-linux-gnu/libc.so.6",           # older Debian
    "/lib64/libc.so.6",                          # RHEL/Fedora/CentOS
    "/usr/lib64/libc.so.6",                      # RHEL alt
    "/usr/lib/libc.so.6",                        # Arch + others
    "/lib/libc.musl-x86_64.so.1",                # Alpine musl
    "/usr/lib/libSystem.B.dylib",                # macOS (Mach-O)
)


@unittest.skipUnless(
    any(Path(c).exists() for c in _LIBC_CANDIDATES),
    "libc.so.6 / libSystem not at any expected location",
)
class TestWrongSoWithoutTotIsMono(unittest.TestCase):
    """MONO_LIB_PATH set to a valid but unrelated .so (libc) ->
    RuntimeError mentioning the missing tot_is_mono symbol.
    Exercises the §6 hasattr guard.
    """

    def test_wrong_so_without_tot_is_mono_raises(self):
        import _runtime_mode
        from eqlib import _ffi as eqlib_ffi

        libc = next(
            (c for c in _LIBC_CANDIDATES if Path(c).exists()),
            None,
        )
        if libc is None:
            self.skipTest("no libc candidate found at runtime")

        os.environ["MONO_LIB_PATH"] = libc
        _runtime_mode.mono_lib_path.cache_clear()
        with self.assertRaises(RuntimeError) as ctx:
            eqlib_ffi._default_lib_path()
        self.assertIn("tot_is_mono", str(ctx.exception))
```

- [ ] **Step 4: Add `test_unreadable_so_raises_runtime_error`**

```python
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

            os.environ["MONO_LIB_PATH"] = str(bad)
            _runtime_mode.mono_lib_path.cache_clear()
            with self.assertRaises(RuntimeError) as ctx:
                eqlib_ffi._default_lib_path()
            self.assertIn("cannot be dlopen'd", str(ctx.exception))
```

- [ ] **Step 5: Add `test_explicit_constructor_path_still_wins`**

```python
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

        os.environ["MONO_LIB_PATH"] = _mono_path()
        _runtime_mode.mono_lib_path.cache_clear()
        # Pass the default .so explicitly; it should be used, NOT
        # the mono path.
        tot = Tot(lib_path=_totlib_path())
        # The wrapper stores the loaded CDLL; check its _name (the
        # path ctypes was constructed with).
        self.assertEqual(
            tot._lib._name, _totlib_path(),
            f"explicit lib_path should override MONO; "
            f"got {tot._lib._name}, expected {_totlib_path()}",
        )
        tot.close()
```

- [ ] **Step 6: Run the full test_mono_routing.py — confirm all 9 cases**

```bash
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
export TOTLIB_PATH="$PWD/tot/libtotapi.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/test_mono_routing.py -v 2>&1) | tail -20
```

Expected: 9 tests pass (1 helper + 3 + 1 + 1 + 1 + 1 + 1).

All 9 tests run on every platform now that `_LIBC_CANDIDATES` includes the macOS Mach-O `/usr/lib/libSystem.B.dylib`. If the test runs in a non-standard sysroot with no libc / libSystem at any expected location, the class-level `skipUnless(any(exists))` skips cleanly.

- [ ] **Step 7: Commit**

```bash
git add python/totlib/tests/test_mono_routing.py
git commit -m "$(cat <<'EOF'
test(totlib): complete 9-case mono routing contract (#208 PR-A)

Adds the remaining 5 spec §8.1 cases on top of the 4 already in
place (1 helper + 3 wrapper-flow):

- test_per_module_env_var_still_honored: pins D-5 "non-mono chain
  unchanged" — uses tempfile-staged fake .so so the assertion is on
  the env-var step, not a side-effect of the fallback file existing.
- test_non_mono_so_raises: default libtotapi.so (tot_is_mono==0)
  surfaces "not a mono image" RuntimeError.
- test_wrong_so_without_tot_is_mono_raises: libc.so.6 (valid but
  unrelated .so) surfaces "no tot_is_mono symbol" RuntimeError.
  Skips on macOS (no libc.so).
- test_unreadable_so_raises_runtime_error: empty/text file surfaces
  "cannot be dlopen'd" — exercises the §6 try/except OSError wrap.
- test_explicit_constructor_path_still_wins: Tot(lib_path=...) at
  the user-facing constructor level beats MONO_LIB_PATH.

9 cases total; full local run green. libc test now portable across
Debian/Ubuntu, RHEL/Fedora, Alpine musl, and macOS via the
expanded _LIBC_CANDIDATES list (Codex pre-push review on 8d9f48a2).

Spec: docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: CI workflow extension

**Files:**
- Modify: `.github/workflows/python-tests.yml` (the mono-build job)

- [ ] **Step 1: Inspect the existing mono-build job**

```bash
grep -nE "mono build|libtotapi_mono|test_mono_bpsd_smoke" \
    .github/workflows/python-tests.yml
```

Note the line of the existing `pytest python/totlib/tests/test_mono_bpsd_smoke.py` step — the new step goes immediately after it.

- [ ] **Step 2: Add the mono-routing pytest step**

Insert this step in `.github/workflows/python-tests.yml` immediately after the existing `pytest python/totlib/tests/test_mono_bpsd_smoke.py` step in the `mono build (Linux libtotapi_mono.so)` job:

```yaml
      - name: Mono routing sanity (Phase 2c PR-A)
        # #208 PR-A — verify that setting MONO_LIB_PATH routes all 6
        # wrappers (eqlib/trlib/fplib/tilib/wrxlib/totlib) to the
        # monolithic image instead of each loading its per-module .so.
        # This is a SANITY test (plumbing only); the behavioral
        # eq->tr BPSD round-trip lives in PR-B.
        #
        # Re-uses the default libtotapi.so artifact built earlier in
        # this job (the "Build default libtotapi.so" step landed in
        # PR #207) for test_non_mono_so_raises.
        env:
          MONO_LIB_PATH: ${{ github.workspace }}/tot/libtotapi_mono.so
          TOTLIB_PATH: ${{ github.workspace }}/tot/libtotapi.so
          PYTHONPATH: python
        run: |
          python -m pytest python/totlib/tests/test_mono_routing.py \
                 --forked --timeout=120 --timeout-method=signal -v
```

- [ ] **Step 3: Quickly verify the yaml parses**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/python-tests.yml'))"
echo "yaml ok"
```

Expected: `yaml ok`.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/python-tests.yml
git commit -m "$(cat <<'EOF'
ci(python-tests): mono routing sanity step (#208 PR-A)

Extends the mono-build job to run python/totlib/tests/
test_mono_routing.py with MONO_LIB_PATH + TOTLIB_PATH both set. The
default libtotapi.so artifact for test_non_mono_so_raises is
already built by the "Build default libtotapi.so" step (PR #207),
so no new build step is required.

This is a sanity test only — no behavioral cross-module rule is
exercised. PR-B will add the TotPipeline.run_pipeline([eq, tr])
integration test that uses this same routing.

Spec: docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Documentation updates

**Files:**
- Modify: `tot/tot_api.h` (comment only — no ABI change)
- Modify: `python/totlib/README.md`

- [ ] **Step 1: Add mono-routing note to `tot/tot_api.h`**

In the header docstring block (around lines 8-30), append a paragraph after the existing "TOT is the orchestrator" prose:

Locate this passage:

```c
 * TOT is the orchestrator: its api fans out to per-module APIs
 * (eq_init + tr_init + ti_init + fp_init + wr_init, tr_run,
 * tr_get_state + ..., per-module *_set_param, *_finalize). The eq
 * cascade was added in #209 — direct ctypes callers can drive
 * eq_set_param / eq_run right after tot_init() without an extra
 * eq_init() round trip. Phase L-2 status: function
```

Insert the following paragraph after the eq cascade sentence (before "Phase L-2 status"):

```c
 *
 * Phase 2c PR-A (#208) introduces a single-authoritative routing
 * contract for the Python wrappers: setting the MONO_LIB_PATH env
 * var makes every per-module wrapper (Eqlib / Trlib / ...) and the
 * Tot orchestrator wrapper load libtotapi_mono.so instead of each
 * loading its per-module lib<mod>api.so. This is plumbing only at
 * the C ABI level — no new symbols added to this header.
```

- [ ] **Step 2: Add a mono-routing section to `python/totlib/README.md`**

Open `python/totlib/README.md` and append at the end (or near the existing TotPipeline section):

```markdown
## Mono routing (Phase 2c PR-A, #208)

To make every wrapper load the monolithic image (so eq/tr/fp/ti/wrx
all share one BPSD broker), set the `MONO_LIB_PATH` env var:

```bash
export MONO_LIB_PATH=/path/to/tot/libtotapi_mono.so
python -c "from totlib import Tot, TotPipeline; ..."
```

When set, the helper at `python/_runtime_mode.py` verifies the .so
is a real mono image (`tot_is_mono() == 1`) and short-circuits each
wrapper's per-module path resolution.

Errors are loud:
- missing file → `FileNotFoundError`
- non-mono `.so` → `RuntimeError("not a mono image")`
- non-shared-object file → `RuntimeError("cannot be dlopen'd")`

Explicit `lib_path=...` to a wrapper constructor still wins
(diagnostic / one-off probes are not affected).

The behavioral eq→tr BPSD coupling rule that this routing enables
is activated in PR-B (issue #208 follow-up).
```

- [ ] **Step 3: Commit**

```bash
git add tot/tot_api.h python/totlib/README.md
git commit -m "$(cat <<'EOF'
docs(tot+totlib): document MONO_LIB_PATH routing (#208 PR-A)

- tot/tot_api.h: 1 prose paragraph in the existing header docstring.
  No ABI / symbol changes.
- python/totlib/README.md: short "Mono routing" section with usage,
  failure-mode contract, and pointer to PR-B for the behavioral
  follow-up.

Spec: docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Pre-push gate, push, PR

**Files:** no edits; runs CLAUDE.md pre-push gate.

- [ ] **Step 1: Confirm the full local test pass**

```bash
export MONO_LIB_PATH="$PWD/tot/libtotapi_mono.so"
export TOTLIB_PATH="$PWD/tot/libtotapi.so"
(cd python && python -m pytest --forked --timeout=120 --timeout-method=signal totlib/tests/ 2>&1) | tail -20
```

Expected: all totlib tests pass (the 9 mono routing + existing mono smoke + cascade + pipeline + equiv). Pre-existing Python-3.10 ExceptionGroup failure (`test_close_raises_exception_group_when_multiple_modules_fail`) is unrelated — see PR #211 history.

- [ ] **Step 2: Launch BOTH reviewers in parallel**

In a single tool-call message, fire:

- `Agent(subagent_type="general-purpose", description="In-house code review for #208 PR-A", prompt=...)` — anchor: plan adherence to this plan + spec D-1..D-7; check Acceptance Criteria 1-7 from spec §11.
- `Agent(subagent_type="codex:codex-rescue", description="Codex independent review for #208 PR-A", prompt=...)` — anchor: cross-cutting code quality + edge cases (init-order, idempotency, error paths, test discipline).

Paste HIGH / MED findings back to the user before continuing.

- [ ] **Step 3: Address findings, re-review if any HIGH/MED. Loop until clean.**

- [ ] **Step 4: Write pre-push marker**

```bash
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
ls -l "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
```

Expected: marker file created at the `.git/` (shared common dir for worktrees).

- [ ] **Step 5: Push**

```bash
unset GITHUB_TOKEN
git push -u origin l7b-ii-phase-2c-pra
```

Expected: `pre-push: review marker present — OK` + new remote branch.

- [ ] **Step 6: Create the PR**

```bash
unset GITHUB_TOKEN
gh pr create --base develop --title "feat(python): MONO_LIB_PATH wrapper routing (#208 Phase 2c PR-A)" --body "$(cat <<'EOF'
## Summary

Closes #208 PR-A milestone (PR-B follow-up in a separate PR).

Adds a single-authoritative routing rule so that setting
`MONO_LIB_PATH=/path/to/libtotapi_mono.so` makes every wrapper
(eqlib/trlib/fplib/tilib/wrxlib/totlib) inside or outside
`TotPipeline` load the same mono image. This is the plumbing prereq
for PR-B's `_MONO_ONLY_RULES = {("eq","tr"): [...]}` behavioral
activation.

## What's in this PR (6 commits)

1. **Helper module** `python/_runtime_mode.py` + `test_helper_cache_clear`.
2. **Wire eqlib** as the proof-of-concept; 3 wrapper-flow tests.
3. **Roll out** to trlib/fplib/tilib/wrxlib/totlib (identical pattern; D-7 wires totlib too).
4. **Complete 9 spec test cases** — pins D-5 fallback, non-mono error, libc lacks-symbol, empty-file dlopen error, explicit lib_path beats MONO.
5. **CI** mono-build job runs `test_mono_routing.py` with both env vars set.
6. **Docs** — tot_api.h header note + totlib README mono-routing section.

## Behavior unchanged

- Default per-module path: untouched (the 4-step chain runs verbatim when MONO_LIB_PATH is unset).
- 1e-10 equivalence: preserved.
- `_MONO_ONLY_RULES` stays empty — no behavioral cross-module rule is activated. PR-B's scope.

## Spec + Plan

- Spec: `docs/superpowers/specs/2026-05-23-l7b-ii-phase-2c-pra-loader-contract-design.md` (3 Codex passes, SHIP IT)
- Plan: `docs/superpowers/plans/2026-05-25-l7b-ii-phase-2c-pra-implementation.md`

## Test plan
- [ ] CI green on `python-tests.yml` (3.11 + 3.13 + mono build with new routing step)
- [ ] Bugbot completes with no remaining HIGH/MED
- [ ] Local `pytest --forked` on totlib/eqlib/trlib stays green

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 7: Trigger Bugbot when CI green**

When all CI checks return SUCCESS, comment `@cursor review` on the PR. Wait for Bugbot to complete (~5-15 min) and address any HIGH/MED. Merge with `gh pr merge <num> --merge` only after Bugbot is clean.

---

## Self-review checklist (executed before sharing this plan)

**Spec coverage:**
- §3 In-scope items 1-5 ✅ (Tasks 1-6)
- §3 Out-of-scope items respected (no `_MONO_ONLY_RULES` changes, no Fortran edits)
- §4 D-1..D-7 each represented (D-1/D-2/D-3 in Task 1; D-4 in helper code Task 1 Step 3; D-5 explicit-wins in Task 4 test 5; D-6 lru_cache + cache_clear in Tasks 1+4 tests; D-7 totlib hook in Task 3 Step 5)
- §5 architecture file list matches Tasks 1-6 file-modify list
- §6 helper API verbatim in Task 1 Step 3
- §7 per-wrapper patch shape verbatim across Tasks 2+3 (5 full patches included, NOT abbreviated)
- §8 9 test cases verbatim across Tasks 1+2+3+4 (counted)
- §9 CI integration in Task 5
- §11 acceptance criteria 1-7 all reachable by plan exit

**Placeholder scan:** none — every code step has actual Python/Fortran/YAML/shell text.

**Type / name consistency:** `mono_lib_path` (function), `MONO_LIB_PATH` (env var), `_runtime_mode` (module) match across all Tasks and the spec.

**Coverage gap:** none found.
