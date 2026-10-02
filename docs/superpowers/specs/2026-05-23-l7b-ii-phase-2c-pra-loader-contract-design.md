# L-7b-ii Phase 2c PR-A — Wrapper mono routing contract (design)

**Status**: design, pre-implementation
**Date**: 2026-05-23
**Tracking issues**: #208 (umbrella for Phase 2c, 2 PR chain), #201 (Phase 2 umbrella)
**Predecessors**: PR #206 (Phase 2a), PR #207 (Phase 2b), PR #211 (#209 cascade)
**Successor**: PR-B (rule activation + integration test) — out of scope here

## 1. Context

Phase 2a + 2b shipped `libtotapi_mono.so` as a co-linked monolithic
shared image and proved (via the Layer-C smoke test) that the BPSD
broker is shared across eq / tr code paths in the mono image. The
detection ABI (`tot_is_mono()`) distinguishes mono from default at
runtime.

What is still missing for production-ready mono BPSD coupling:

- Each of the 6 wrappers (`python/{eqlib, trlib, fplib, tilib,
  wrxlib, totlib}/_ffi.py`) currently loads its OWN per-module
  `lib<mod>api.so` via a fixed 4-step resolution chain (explicit
  `path` arg → `<MOD>LIB_PATH` env → `<repo>/<mod>/lib<mod>api.so` →
  `<repo>/lib/lib<mod>api.so`).
- Even with `TOTLIB_PATH=...libtotapi_mono.so` set, only the `Tot`
  wrapper sees the mono image; the sibling `Eqlib` / `Trlib` /…
  instances inside `TotPipeline` still each load their per-module
  `.so`, each carrying private bpsd storage.
- `TotPipeline._MONO_ONLY_RULES` is intentionally empty in Phase 2b
  because populating `("eq","tr")` would deterministically fail
  against still-per-module wrappers (Codex pre-push HOLD on PR #207
  caught this).

Phase 2c closes the gap via a Codex-recommended short PR chain:

- **PR-A (this spec)**: shared mono routing contract; 6 `_ffi.py`
  loaders updated. NO behavioral rule activation.
- **PR-B (separate spec, follow-up)**: populate `_MONO_ONLY_RULES`,
  add `TotPipeline.run_pipeline([(eq,…),(tr,…)])` integration test.

## 2. Goal

A **single authoritative routing rule** so that setting one env var
(`MONO_LIB_PATH`) makes every wrapper inside or outside `TotPipeline`
load the same mono image.

**Codex 2026-05-18 retrospective explicit constraint**: "single
authoritative loader semantics, NOT ad-hoc per-wrapper env handling".

## 3. Scope

### In scope (PR-A)

1. New helper module `python/_runtime_mode.py`.
2. Update `python/{eqlib, trlib, fplib, tilib, wrxlib, totlib}/_ffi.py`
   to consult the helper as a new priority-0 step.
3. New pytest `python/totlib/tests/test_mono_routing.py` exercising the
   contract (sanity, NOT behavioral).
4. CI extension on the mono-build job to run the new test.
5. Doc updates: per-wrapper docstrings, `python/totlib/README.md`,
   `tot/tot_api.h` (comment only — no ABI change).

### Out of scope (PR-A)

- Populating `_MONO_ONLY_RULES` with `("eq","tr")` — PR-B.
- Any `TotPipeline.run_pipeline` integration test that asserts
  end-to-end eq→tr BPSD round-trip — PR-B.
- Cross-module coupling rules other than `("eq","tr")`.
- Restructuring any Fortran source (`feedback_fortran_refactor_needs_lead_signoff.md`).
- Changing the existing per-module `_ffi.py` path-resolution
  priority for **non-mono** users — those 4 steps stay verbatim.
- Renaming `<MOD>LIB_PATH` env vars.

## 4. Design decisions

Each decision below records the chosen path, the alternatives
considered, and a one-line rationale.

### D-1: Public surface = single env var `MONO_LIB_PATH`

**Chosen**: env var only.
**Rejected**: programmatic `MonoRuntime.activate(path)` API only.
**Why**: env-var matches the existing `<MOD>LIB_PATH` precedent;
CI sets it from one shell line; no new API surface.

### D-2: Interpretation logic = single shared module

**Chosen**: `python/_runtime_mode.py` with a single function
`mono_lib_path()`.
**Rejected**: read `os.environ.get("MONO_LIB_PATH")` directly inside
each `_ffi.py`.
**Why**: Codex's "single authoritative" constraint. Adding the env
read in 6 places re-introduces the ad-hoc handling Codex flagged
against. The helper module owns the read + validation; wrappers are
mechanical consumers.

### D-3: Module placement = `python/_runtime_mode.py` (top-level)

**Chosen**: top-level file under `python/`.
**Rejected**:
- `python/totlib/_mono.py` — would invert the layering
  (`eqlib → totlib` is the wrong direction; today `totlib.pipeline`
  composes per-module wrappers, not the other way around).
- `python/_runtime/` subpackage — YAGNI; one file is enough until a
  second runtime-mode concept lands.

**Why**: matches existing import shape (tests already put
`<repo>/python` on `sys.path`; wrappers import packages as top-level
names). Codex independent review 2026-05-23 confirmed.

### D-4: Strictness = strict + verify

**Chosen**:
- `MONO_LIB_PATH` set but file missing → `FileNotFoundError`.
- `MONO_LIB_PATH` set + file exists but `tot_is_mono() == 0` →
  `RuntimeError("not a mono image")`.
- `MONO_LIB_PATH` unset → return `None` (wrappers fall back to
  existing per-module resolution).

**Rejected**: silent fallback when MONO_LIB_PATH points at an
invalid file.
**Why**: silent fallback masks misconfiguration and violates the
"single authoritative" intent. PR-B's behavioral tests then have a
clear contract to lean on. Verification cost is bounded — see D-6.

### D-5: Precedence inside each `_ffi.py`

**Order from highest to lowest priority**:

1. Explicit `path=` argument to `load_library(path)` — kept as the
   most-specific override (debug / one-off probes).
2. `mono_lib_path()` (NEW) — global mono override.
3. `<MOD>LIB_PATH` env var — per-module override (existing).
4. `<repo>/<mod>/lib<mod>api.so` — standard L-4 build location
   (existing).
5. `<repo>/lib/lib<mod>api.so` — install-style location (existing).

**Why explicit `path=` wins over MONO**: the explicit arg is what
debugging code uses to probe a *specific* .so. Forcing it to be
overridden by a forgotten env var would surprise diagnostic code
paths. The mono override applies to "default" loads only.

### D-6: Cache strategy

**Chosen**: `@functools.lru_cache(maxsize=None)` on
`mono_lib_path()`. The function takes no arguments.

- Env read + verification happens once per Python process.
- 6 wrappers in the same process each see the same cached result.
- Tests that mutate `MONO_LIB_PATH` at runtime must call
  `mono_lib_path.cache_clear()` — documented in the helper docstring.
- Under `--forked` (the standard for this repo) each test runs in a
  fresh process, so the cache is naturally invalidated between
  tests.

**Rejected**: per-call re-read.
**Why**: PR-B's pipeline will instantiate 5+ wrappers; per-call would
mean 5+ env reads + 5+ dlopen+verify cycles per `TotPipeline()`
construction. Cache + verify-once is the right shape.

### D-7: `totlib/_ffi.py` is included

`MONO_LIB_PATH` overrides `TOTLIB_PATH` on the `Tot` wrapper as well
as on the per-module wrappers. Without this, a user pipeline with
`MONO_LIB_PATH` set but `TOTLIB_PATH` unset would get the mono image
for eqlib/trlib/… but the default image for tot itself — same broker
inconsistency in mirror form.

## 5. Architecture

```
python/
  _runtime_mode.py            # NEW — D-2 / D-3
  __init__.py                 # unchanged (existing empty file)
  eqlib/_ffi.py               # MODIFIED — D-5 priority 0
  trlib/_ffi.py               # MODIFIED — D-5 priority 0
  fplib/_ffi.py               # MODIFIED — D-5 priority 0
  tilib/_ffi.py               # MODIFIED — D-5 priority 0
  wrxlib/_ffi.py              # MODIFIED — D-5 priority 0
  totlib/_ffi.py              # MODIFIED — D-5 priority 0 + D-7
  totlib/tests/
    test_mono_routing.py      # NEW — sanity test, NO rule activation
                              #   (placed under totlib/tests/ to match
                              #   the existing cross-module test home
                              #   already used by test_mono_bpsd_smoke
                              #   and test_tot_init_eq_api_cascade)
```

CI: existing `mono build (Linux libtotapi_mono.so)` job extended to
run `pytest python/totlib/tests/test_mono_routing.py --forked` with
`MONO_LIB_PATH` set to the just-built `libtotapi_mono.so`.

## 6. Helper API contract

```python
# python/_runtime_mode.py
"""Single authoritative source for runtime-mode routing decisions.

Today this only owns the MONO_LIB_PATH env var contract (#208 Phase
2c PR-A). Future runtime concerns (build flavor, debug mode) can
land here without touching per-module _ffi.py loaders again.
"""
from __future__ import annotations
import ctypes
import functools
import os
from pathlib import Path
from typing import Optional


@functools.lru_cache(maxsize=None)
def mono_lib_path() -> Optional[Path]:
    """Return the Path to libtotapi_mono.so if MONO_LIB_PATH is set
    and points at a valid mono image; return None otherwise.

    Raises:
        FileNotFoundError: MONO_LIB_PATH set, file missing.
        RuntimeError:      MONO_LIB_PATH set, file is not a mono image
                           (tot_is_mono() returned 0 instead of 1).

    Cache:
        Result memoized for the lifetime of the Python process.
        Call mono_lib_path.cache_clear() if the env var is mutated at
        runtime (tests; production code never needs this).
    """
    env = os.environ.get("MONO_LIB_PATH", "").strip()
    if not env:
        return None
    p = Path(env)
    if not p.exists():
        raise FileNotFoundError(
            f"MONO_LIB_PATH={env!r} does not exist. Unset the env var "
            f"or build the mono image: `make -C tot libtotapi_mono.so`."
        )
    # One-shot dlopen + tot_is_mono() check. We do NOT keep the handle —
    # each wrapper's load_library() will dlopen its own with the right
    # RTLD_LAZY mode and prototype-attach. The verification load is
    # disposable.
    # Wrap CDLL in try/except so wrong-arch / non-ELF / dep-broken
    # .so files surface as the friendly RuntimeError, NOT a raw OSError
    # with a cryptic dlerror string (Codex 2026-05-25 review MED-2).
    try:
        lib = ctypes.CDLL(str(p), mode=getattr(ctypes, "RTLD_LAZY", 1))
    except OSError as exc:
        raise RuntimeError(
            f"MONO_LIB_PATH={env!r} cannot be dlopen'd: {exc}. "
            "Likely wrong architecture, non-ELF, or missing dependency. "
            "Build via `make -C tot libtotapi_mono.so` on the same host."
        ) from exc
    if not hasattr(lib, "tot_is_mono"):
        raise RuntimeError(
            f"MONO_LIB_PATH={env!r} exposes no `tot_is_mono` symbol. "
            "This indicates a pre-Phase-2b .so. Rebuild against "
            "develop or a newer branch."
        )
    lib.tot_is_mono.restype = ctypes.c_int
    lib.tot_is_mono.argtypes = []
    if lib.tot_is_mono() != 1:
        raise RuntimeError(
            f"MONO_LIB_PATH={env!r} is not a mono image "
            f"(tot_is_mono() returned 0). Set MONO_LIB_PATH to a "
            "libtotapi_mono.so built via `make -C tot libtotapi_mono.so`."
        )
    return p
```

## 7. Per-wrapper modifications

The change to each `_ffi.py` is mechanical and identical in shape.
Example for `python/eqlib/_ffi.py`:

```python
# Add to imports
from _runtime_mode import mono_lib_path

# Replace _default_lib_path() with:
def _default_lib_path() -> Path:
    """Resolve the default libeqapi.so path.

    Priority (highest first):
      0. mono_lib_path()   — global mono override (MONO_LIB_PATH env)
      1. EQLIB_PATH env var
      2. <repo>/eq/libeqapi.so
      3. <repo>/lib/libeqapi.so

    `load_library(path=...)` accepts an explicit override that still
    wins over (0) — see the `path` argument handling below.
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

Identical patch shape for `trlib`, `fplib`, `tilib`, `wrxlib`,
`totlib`. The only differences: the `<MOD>LIB_PATH` env-var name and
the docstring's per-module wording.

`load_library(path=...)` is unchanged. The early `if path:` branch in
the existing code remains the highest-priority override.

The high-level wrapper constructors (`Eqlib(lib_path=...)`,
`Trlib(lib_path=...)`, ..., `Tot(lib_path=...)`) all forward
`lib_path` to `_ffi.load_library(lib_path)` (see e.g.
`python/totlib/totlib.py:104-109`, `python/eqlib/eqlib.py:119-124`).
Combined precedence for a user that passes `Tot(lib_path="path/to/foo.so")`
with `MONO_LIB_PATH` *also* set: the explicit `lib_path` STILL wins
because the early `if path:` branch in `load_library` runs before
`_default_lib_path()` is consulted. This is intentional — see D-5 —
and PR-A's tests assert it explicitly via the user-facing constructor
surface (§8.1 `test_explicit_constructor_path_still_wins`).

## 8. Tests

### 8.1 `python/totlib/tests/test_mono_routing.py` (new)

Module-level `pytestmark = [pytest.mark.forked]` (matches the pattern
established by `test_tot_init_eq_api_cascade.py` in PR #211).

Tests (all skip when neither `MONO_LIB_PATH` nor `TOTLIB_PATH`
fixtures are buildable):

- `test_unset_falls_back_to_per_module`: env unset, each of the 6
  wrappers' `_default_lib_path()` returns the per-module path.
- `test_set_routes_all_wrappers`: env set to a valid mono .so, each
  of the 6 wrappers' `_default_lib_path()` returns the mono path.
- `test_per_module_env_var_still_honored`: `MONO_LIB_PATH` unset and
  e.g. `TOTLIB_PATH=...` set — wrapper picks the per-module env var
  per the unchanged steps 2-4 (Codex 2026-05-25 review LOW-3 — pins
  the "default per-module priority is unaffected" guarantee from D-5
  so PR-B can lean on it).
- `test_missing_file_raises`: env set to `/nonexistent.so`, first
  wrapper call raises `FileNotFoundError`.
- `test_non_mono_so_raises`: env set to a default (per-module-link)
  `libtotapi.so` (already built by the CI mono job's "Build default
  libtotapi.so" step — see §9), first wrapper call raises
  `RuntimeError`.
- `test_wrong_so_without_tot_is_mono_raises`: env set to a valid
  but unrelated .so that dlopens fine but lacks the `tot_is_mono`
  symbol (e.g. `/usr/lib/libc.so.6` on Linux), first wrapper call
  raises `RuntimeError` mentioning "no `tot_is_mono` symbol". Skip
  cleanly when libc cannot be located. Exercises the §6 `hasattr`
  guard.
- `test_unreadable_so_raises_runtime_error`: env set to a path whose
  contents are NOT a valid shared object (e.g. an empty file or a
  text file written to a tmp path), first wrapper call raises
  `RuntimeError` mentioning "cannot be dlopen'd" (NOT a raw
  OSError). Exercises the §6 `try/except OSError` wrapping path
  added per Codex 2026-05-25 MED-2.
- `test_explicit_constructor_path_still_wins`: env set to mono,
  `Tot(lib_path=per_module_so)` (high-level constructor surface, not
  just `_ffi.load_library`) returns the per-module so. Mirrors the
  precedence rule documented in §7 (Codex 2026-05-25 MED-3 anchored).
- `test_helper_cache_clear`: documents cache behavior — sanity check
  that `cache_clear()` honors env mutation between calls.

### 8.2 What this PR does NOT test

- No assertion that any cross-module rule fires.
- No `TotPipeline.run_pipeline([eq, tr])` invocation.
- No `tr_check_bpsd_pull` round-trip.

These belong to PR-B.

## 9. CI

The existing `mono build (Linux libtotapi_mono.so)` job in
`.github/workflows/python-tests.yml` builds `libtotapi_mono.so` and
runs `pytest python/totlib/tests/test_mono_bpsd_smoke.py` (which
PR #211 modified to use the #209 cascade). PR-A extends this job:

```yaml
- name: Mono routing sanity (Phase 2c PR-A)
  env:
    MONO_LIB_PATH: ${{ github.workspace }}/tot/libtotapi_mono.so
    TOTLIB_PATH: ${{ github.workspace }}/tot/libtotapi.so
  run: |
    pytest python/totlib/tests/test_mono_routing.py \
           --forked --timeout=120 --timeout-method=signal -v
```

Bookkeeping: the existing CI mono-build job ALREADY builds the
default `libtotapi.so` for the Phase 2b Layer-C C-3 test (see
`.github/workflows/python-tests.yml` step "Build default libtotapi.so
(needed for Layer-C C-3 test)" — landed in PR #207). PR-A reuses
that artifact for `test_non_mono_so_raises`; no new build step
required (Codex 2026-05-25 review MED-1).

## 10. Risks and open questions

### R-1: lru_cache + mutable env var in long-lived processes

The helper caches the env read. Real-world usage rarely mutates
`MONO_LIB_PATH` mid-process, but if a future tutorial / MCP server
were to switch modes dynamically, it would need `cache_clear()`.
Mitigation: the docstring explicitly calls this out, and a new test
case `test_helper_cache_clear` (§8.1) exercises this exact pattern
so refactors cannot regress it silently. A first-class
`set_mono_lib_path(path)` setter that bypasses the env-var read is
deliberately deferred until a concrete in-process mode-switch user
appears (YAGNI — would be ~10 lines if the need surfaces).

### R-2: verification load may fail in restricted environments

The `ctypes.CDLL(...)` verification load needs read+exec on the .so.
In sandboxed Python environments (e.g. some MCP server hosts) this
may fail. Mitigation: PR-A's CI sanity test catches the common case;
deferred fix if a real user hits the sandbox issue. The fallback
would be a `MONO_LIB_PATH_SKIP_VERIFY=1` opt-out, NOT added in PR-A
(YAGNI).

### R-3: import order: `from _runtime_mode import mono_lib_path`

Top-level `python/` is on `sys.path` only when callers add it (tests
do this explicitly; production callers typically `pip install` the
wrappers or `cd python && python -c "..."`). Mitigation: import
inside `_default_lib_path()` rather than at module top (deferred
import) — fallback to `os.environ.get("MONO_LIB_PATH")` direct read
if the import fails, with a one-time stderr warning. Decision: do
top-level import; the wrappers' tests already assume `python/` is on
`sys.path`, and production users do too.

## 11. Acceptance criteria

PR-A is ready to merge when:

1. `python/_runtime_mode.py` lands with the contract from §6.
2. All 6 `python/<mod>lib/_ffi.py` files implement the priority-0
   hook per §7.
3. `python/totlib/tests/test_mono_routing.py` exists with the 9 cases
   from §8.1 and runs green locally (`pytest --forked`).
4. CI's mono-build job runs the new test green AND the default
   `mono build (Linux libtotapi_mono.so)` step (with the cascade
   from PR #211) stays green.
5. `_MONO_ONLY_RULES` remains empty — no rule activation.
6. 1e-10 equivalence (`totlib/tests/test_equivalence.py`) preserved.
7. Both in-house and Codex pre-push reviews report HIGH/MED-free
   (or any found are addressed and reviewers reconfirm).

## 12. References

- Parent: #208 Phase 2c umbrella (this is PR-A; PR-B is the rule
  activation follow-up).
- Predecessor (cascade fix): PR #211, closes #209.
- L-7b-ii spec: `docs/superpowers/specs/2026-05-03-l7b-ii-bpsd-broker-coupling-design.md`
  (§0 corrected by PR #206).
- Phase 2a findings: `docs/superpowers/specs/2026-05-14-l7b-ii-monolithic-poc-findings.md`.
- Phase 2b spec: `docs/superpowers/specs/2026-05-18-l7b-ii-phase-2b-design.md`.
- Codex retrospective 2026-05-18 items 2, 6, 7.
- Codex architecture review 2026-05-23 (this design): module
  placement Option A confirmed.
- Memory: `feedback_fortran_refactor_needs_lead_signoff.md` —
  PR-A stays inside the C-ABI / Python boundary; no Fortran refactor.
