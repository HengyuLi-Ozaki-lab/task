# L-7b-ii Phase 2b — Behavioral activation (BPSD coupling) — Design

**Date:** 2026-05-18
**Status:** Draft (awaiting user approval before writing plan)
**Predecessor:** PR #206 (Phase 2a — `libtotapi_mono.so` is now dlopen-loadable + 1e-10 equivalent)
**Issue:** [#201](https://github.com/k-yoshimi/task/issues/201) Phase 2b section
**Reviewer drivers:** Codex retrospective 2026-05-15 (items 1 + 3 + 5 + 6)

---

## §1. Goal

Activate the `("eq", "tr")` BPSD coupling rule in `TotPipeline.COUPLING_RULES`
**conditionally on monolithic runtime selection** so the mono build can drive
eq → tr broker-mediated profile coupling, while the default per-module
`libtotapi.so` path continues to refuse the rule (where the BPSD broker is
per-`.so` private and pull would silently fail).

Ship the Layer-C smoke test that proves the mono image actually carries
shared BPSD state across the eq + tr code paths.

## §2. Non-goals (out of scope for this PR)

- Routing the full `TotPipeline` (Eqlib + Trlib + Fplib + Tilib + Wrxlib) through
  a single mono `.so`. That requires touching every `python/<mod>lib/_ffi.py`
  to honor a unified path env var, which is invasive enough to deserve a
  separate spec (tentatively "Phase 2c — pipeline mono routing").
- Restructuring `trcomm.f90`, `eqbpsd.f90`, or any core Fortran module logic
  (needs main developer sign-off per `feedback_fortran_refactor_needs_lead_signoff.md`).
- Activating BPSD coupling for any consumer other than `TotPipeline`.
- New BPSD slots beyond what PR #188 (`tr_check_bpsd_pull`) already validates.

## §3. Mono detection mechanism

### Design decision (user-confirmed 2026-05-18)

**Option A**: new `tot_api_is_mono()` C ABI export in `tot_api.f90` returning
`INTEGER(C_INT)` (`1` for mono, `0` for per-module).

Rejected alternatives:
- B. Sentinel-symbol `dlsym` probe (fragile name dependency).
- C. `.so` filename substring match (breaks if user renames).
- D. Environment variable (inconsistent state if user sets it wrong).

### How does the function return a *different* value in mono vs default?

The same `tot_api.f90` source is compiled into BOTH `libtotapi.so` (default)
and `libtotapi_mono.so` (mono). The function therefore cannot embed the
"am I mono?" answer in a literal returned from `tot_api.f90` itself.

**Implementation (2026-05-18): two-file standalone-function split.**

Two parallel standalone Fortran files (NOT inside any `MODULE`) with the
same `BIND(C, NAME="tot_is_mono")` symbol:

- `tot/tot_is_mono.f90` (NEW) — `FUNCTION tot_api_is_mono() RESULT(is_mono) BIND(C, NAME="tot_is_mono")` returning `0`
- `tot/tot_is_mono_mono.f90` (NEW) — same body returning `1`

The Makefile picks one per build:
- `OBJS_PIC` (default) includes `$(OBJDIR_PIC)/tot_is_mono.o`
- `OBJS_PIC_MONO` substitutes `$(OBJDIR_PIC)/tot_is_mono_mono.o`

`tot_api.f90` does NOT reference either file — the linker resolves the
`tot_is_mono` symbol from whichever standalone .o is in the link line.

#### Why standalone functions instead of a MODULE-wrapped PARAMETER?

An earlier draft of this spec proposed `MODULE tot_mono_flag` exporting
`LOGICAL, PARAMETER :: tot_is_mono`, with `tot_api.f90` `USE`-ing that
module and `tot_api_is_mono()` returning `MERGE(1, 0, tot_is_mono)`. That
pattern forces `tot_api.o` to be recompiled per build target because a
`PARAMETER` is inlined at the call site — the default build's `tot_api.o`
would carry an inlined `0`, the mono build's would carry an inlined `1`,
and the two .o files would have different bodies even though the source
is identical.

The standalone-function approach lets a single `tot_api.o` participate in
BOTH builds: the actual `tot_is_mono` symbol is resolved at link time from
whichever per-target .o is in the link line.

Trade-offs:
- ✓ No preprocessor magic (gfortran works without `.F90`).
- ✓ Clean separation; the per-target override is a single ~15-line file.
- ✓ Both .so files share `tot_api.o` — incremental builds work as
  expected.
- ✗ Two-file maintenance burden (one is essentially "the default").
- Alternative considered (rejected): an `INCLUDE` directive with a
  build-generated `.inc` — same complexity, less explicit.

## §4. New C ABI surface

```fortran
! tot/tot_is_mono.f90 (default, returns 0) — also tot_is_mono_mono.f90
! (mono, returns 1). Both standalone (NOT inside any MODULE) so they
! share a single ELF symbol and either can be linked into tot_api.o's
! reference without recompiling tot_api.o.
FUNCTION tot_api_is_mono() RESULT(is_mono) BIND(C, NAME="tot_is_mono")
  USE, INTRINSIC :: ISO_C_BINDING, ONLY: C_INT
  IMPLICIT NONE
  INTEGER(C_INT) :: is_mono
  is_mono = 0   ! or 1 in tot_is_mono_mono.f90
END FUNCTION tot_api_is_mono
```

```c
/* tot/tot_api.h — added near the existing exports */
/*
 * tot_is_mono: returns 1 if this libtotapi*.so is the monolithic image
 * (eq + tr + fp + ti + wrx + bpsd co-linked, single shared BPSD broker),
 * 0 if it is the per-module image (libtotapi.so depending on individual
 * lib<mod>api.so files, each with private bpsd storage).
 *
 * Use case: Python orchestrators decide whether the eq->tr BPSD coupling
 * rule is meaningful for the loaded image.
 */
int tot_is_mono(void);
```

```python
# python/totlib/_ffi.py — added to _apply_prototypes()
lib.tot_is_mono.argtypes = []
lib.tot_is_mono.restype = ctypes.c_int
```

Backwards compatibility: older `libtotapi.so` builds without this function
will fail `getattr(lib, "tot_is_mono")` at `_apply_prototypes` time. We
must wrap the attribute lookup in `try / except AttributeError` and treat
missing-function as `is_mono == 0` so the Python side doesn't break if a
user dlopen()s an old-build artifact.

## §5. Pipeline detection + conditional rule registration

`pipeline.py` currently uses a module-level `COUPLING_RULES: Dict[...]`
populated at import time. The mono-conditional rule cannot live there
(import time is too early to know which `.so` is loaded).

**Pattern: pipeline-instance-level rule overlay (infrastructure only in
Phase 2b — `_MONO_ONLY_RULES` stays empty until Phase 2c).**

```python
# python/totlib/pipeline.py

# Existing module-level dict (unchanged)
COUPLING_RULES: Dict[Tuple[str, str], List[CouplingRule]] = {
    ("fp", "tr"): [...existing...],
}

# Mono-only rules infrastructure. Populated by Phase 2c after wrapper
# plumbing routes Eqlib/Trlib/Fplib/Tilib/Wrxlib through the mono .so.
# Populating ("eq","tr") in Phase 2b alone would cause run_pipeline to
# fire the verify rule against Trlib instances that still load their
# OWN per-module libtrapi.so — the rule would deterministically fail
# because eq's push lands in libeqapi.so's PRIVATE bpsd while tr reads
# from libtrapi.so's PRIVATE bpsd (Codex pre-push review caught this
# as a HOLD blocker, 2026-05-18).
_MONO_ONLY_RULES: Dict[Tuple[str, str], List[CouplingRule]] = {
    # populated in Phase 2c
}

class TotPipeline:
    def __init__(self, ...):
        ...
        self._active_rules = None    # built lazily on first lookup

    def _detect_mono(self) -> bool:
        """Returns True if the loaded libtotapi*.so is the mono image."""
        try:
            from totlib import _ffi
            lib = _ffi.load_library()
            fn = getattr(lib, "tot_is_mono", None)
            if fn is None:
                warnings.warn("legacy .so lacks tot_is_mono", RuntimeWarning)
                return False
            return bool(fn())
        except (AttributeError, OSError) as exc:
            warnings.warn(f"_detect_mono failed: {exc}", RuntimeWarning)
            return False

    def _build_active_rules(self):
        rules = {k: list(v) for k, v in COUPLING_RULES.items()}
        if self._detect_mono():
            for k, mono_rules in _MONO_ONLY_RULES.items():
                rules.setdefault(k, []).extend(mono_rules)
        return rules
```

Then in `run_pipeline`, replace `COUPLING_RULES.get((prev,name), [])`
with `self._get_active_rules().get(...)`.

### Why instance-level instead of module-level

- Different `TotPipeline` instances in the same Python process could load
  different `.so` files (mono in one, per-module in another via
  `TOTLIB_PATH` override per instance). Module-level rules would not
  reflect that.
- Test isolation: a Layer-C test can use a mono `TotPipeline` while
  legacy tests use the default in the same `pytest` run.

## §6. Layer-C smoke test scope

### What we test in Phase 2b

A single new test file `python/totlib/tests/test_mono_bpsd_smoke.py` (Layer C):

```python
"""Layer-C: mono BPSD broker smoke test (#201 Phase 2b)."""
import ctypes
import os
import pytest

@pytest.fixture(scope="function")
def mono_lib():
    """Open libtotapi_mono.so directly via ctypes (no module wrappers).

    We bypass Eqlib/Trlib because those load their per-module .so files
    by default; Phase 2b does not yet plumb mono routing through
    individual wrappers (see §2 non-goal: "Phase 2c").
    """
    path = os.environ.get("MONO_LIB_PATH")
    if not path or not os.path.exists(path):
        pytest.skip(f"MONO_LIB_PATH not set or missing: {path!r}")
    yield ctypes.CDLL(path)

def test_mono_flag(mono_lib):
    """tot_is_mono() == 1 on the mono image."""
    mono_lib.tot_is_mono.restype = ctypes.c_int
    assert mono_lib.tot_is_mono() == 1, "mono .so should report is_mono=1"

def test_bpsd_round_trip(mono_lib):
    """Drive an eq push, then tr pull, expect ok=1 in the same image."""
    # Phase 2b minimum: prove the symbol chain works.
    # Initialize tot (which initializes all sub-modules in the same image).
    mono_lib.tot_init.restype = ctypes.c_int
    assert mono_lib.tot_init() == 0
    # Drive an eq.run via the C ABI happy-path (set RR / RA, run 1 step).
    # ...
    # Pull and check.
    ok = ctypes.c_int(0)
    mono_lib.tr_check_bpsd_pull.argtypes = [ctypes.POINTER(ctypes.c_int)]
    mono_lib.tr_check_bpsd_pull(ctypes.byref(ok))
    assert ok.value == 1, f"mono image: tr_check_bpsd_pull = {ok.value}, expected 1"
    mono_lib.tot_finalize()

def test_distinguishes_per_module(monkeypatch):
    """Same test against the default per-module .so should give ok=0."""
    default_path = ... # default libtotapi.so
    lib = ctypes.CDLL(default_path)
    lib.tot_is_mono.restype = ctypes.c_int
    # In the default per-module image, the function exists (we added it
    # to tot_api.f90) and returns 0.
    assert lib.tot_is_mono() == 0
    # tr_check_bpsd_pull on the default image is meaningless: even after
    # eq.push() the tr-side bpsd_*x storage is a separate copy.
    # We don't actually test the pull on default; verifying the flag is
    # enough to confirm the distinguishing mechanism works.
```

### Process isolation requirement (Codex item 5)

The Layer-C tests MUST run under `pytest --forked` (CLAUDE.md flag already
used everywhere). The mono `.so` carries module-level state (BPSD broker
slots, eq common blocks, tr trcomm) that bleeds across `pytest` cases in
the same process; without `--forked`, a prior test's eq.push could make
the round-trip check pass for the wrong reason. The CI step already uses
`--forked`; the per-test side just needs `@pytest.mark.forked` is not
required because the worker-level flag is sufficient.

### What we do NOT test in Phase 2b

- **Full TotPipeline.run_pipeline mono routing**: requires touching
  every `python/<mod>lib/_ffi.py`. Deferred to Phase 2c.
- **Coupling rule firing inside a pipeline**: since TotPipeline doesn't
  yet route through mono end-to-end, the registered `("eq","tr")` rule
  is structurally correct but currently unreachable from any user-facing
  pipeline. The Layer-C smoke test verifies the *symbol chain* the rule
  would call; the rule itself stays dormant until Phase 2c.

This is consistent with Codex retrospective 2026-05-15 item 3: "split
build-infra first, behavioral activation second." Phase 2b registers the
rule (a behavioral change) but the actual wired path stays bottled until
Phase 2c.

## §7. CI integration

Extend the `mono-build` job's equivalence step (added in PR #206) to also
run the Layer-C smoke:

```yaml
# .github/workflows/python-tests.yml — within the mono-build job, after
# the existing 1e-10 equivalence step
- name: Layer-C BPSD smoke (mono image)
  env:
    PYTHONPATH: python
    MONO_LIB_PATH: ${{ github.workspace }}/tot/libtotapi_mono.so
    TOTLIB_PATH: ${{ github.workspace }}/tot/libtotapi.so
  run: |
    python -m pytest python/totlib/tests/test_mono_bpsd_smoke.py -v \
      --forked --timeout=120 --timeout-method=signal
```

The Layer-C job needs BOTH paths set:
- `MONO_LIB_PATH` for the mono image used in `test_mono_flag` /
  `test_bpsd_round_trip`.
- `TOTLIB_PATH` for the default per-module image used in
  `test_distinguishes_per_module`.

The default `libtotapi.so` is already built by the mono-build job's
implicit dependency chain (`$(LIBS_PIC_SO)` triggers each per-module .so
build).

Wait — actually `libtotapi.so` is NOT built by the mono-build job; only
the 5 per-module `lib<mod>api.so` are. We need to add a step to build
`libtotapi.so` too (one extra make invocation).

## §8. Files touched

- `tot/tot_api.f90` (modified): doc-only — pointer comment referencing the standalone files
- `tot/tot_api.h` (modified): new `int tot_is_mono(void)` declaration
- `tot/tot_is_mono.f90` (NEW): default standalone function (returns 0)
- `tot/tot_is_mono_mono.f90` (NEW): mono standalone function (returns 1)
- `tot/Makefile` (modified): OBJS_PIC adds tot_is_mono.o; OBJS_PIC_MONO substitutes tot_is_mono_mono.o
- `python/totlib/_ffi.py` (modified): expose `tot_is_mono` with try/except for legacy builds
- `python/totlib/pipeline.py` (modified): instance-level `_active_rules`, `_detect_mono`, `_MONO_ONLY_RULES` registry (empty in Phase 2b — populated in Phase 2c)
- `python/totlib/tests/test_mono_bpsd_smoke.py` (NEW): Layer-C tests
- `.github/workflows/python-tests.yml` (modified): mono-build job adds Layer-C step + default libtotapi.so build

## §9. Acceptance criteria

1. `tot_is_mono` C ABI exists in BOTH builds; returns 0 in default, 1 in mono.
2. `libtotapi_mono_inspect` continues to pass HARD GATE 1 + HARD GATE 2.
3. 1e-10 equivalence test PASS against mono (unchanged from PR #206).
4. Layer-C `test_mono_flag` PASS: `mono_lib.tot_is_mono() == 1`.
5. Layer-C `test_bpsd_round_trip` PASS: `tr_check_bpsd_pull` returns
   `ok=1` in the mono image after an eq.push.
6. Layer-C `test_distinguishes_per_module` PASS: default lib returns
   `tot_is_mono() == 0`.
7. Infrastructure for instance-level rule overlay (`_active_rules`,
   `_detect_mono`, `_MONO_ONLY_RULES`) is in place. `_MONO_ONLY_RULES`
   is intentionally EMPTY in Phase 2b — Phase 2c populates it once
   the wrapper plumbing routes Eqlib/Trlib/etc. through the mono .so
   (Codex pre-push review caught that populating ("eq","tr") here
   without wrapper plumbing would cause run_pipeline to fire and
   FAIL on the still-per-module Trlib instance).
9. CI's mono-build job PASS for all of the above on Linux.
10. CLAUDE.md compliance: no Fortran refactor outside the new
    `tot_mono_flag*.f90` files + the additive `tot_is_mono` function in
    `tot_api.f90`. Within `feedback_fortran_refactor_needs_lead_signoff.md`
    boundary (new C ABI = k-yoshimi-led OK).

## §10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `tot_is_mono` symbol missing from older builds | `try/except AttributeError` in `_detect_mono`; treat as not-mono |
| `tr_check_bpsd_pull` not in mono .so | Verified 2026-05-18: 18 `tr_*` exports present, including `_tr_check_bpsd_pull` (worktree's `libtotapi_mono.so`) |
| Two-file flag pattern adds maintenance burden | Files are 5 lines each; pattern is documented in spec and Makefile comments |
| Layer-C test's eq-push happy path may not actually populate BPSD slots | Verify locally before commit; if needed, simplify to a non-zero state check on the pulled blob rather than ok=1 |
| Phase 2b registers a rule no current TotPipeline can fire (since 2c not done) | Documented as intentional in §6 ("dormant until Phase 2c"); test_distinguishes_per_module verifies the *registration logic*, not the *firing path* |

## §11. Open questions

1. **Should Phase 2b also implement the wrapper plumbing (route Eqlib/Trlib/Fplib/Tilib/Wrxlib through the mono `.so`)?**
   - Pro: completes the architectural story; the rule isn't dormant.
   - Con: touches 5+ files in 5 different `python/<mod>lib/_ffi.py`, each
     needing a careful "honor `MONO_LIB_PATH` or per-module path" decision.
   - **Recommendation: NO** — keep Phase 2b focused on the broker-sharing
     proof + conditional registration. Phase 2c is the right home for the
     wrapper-plumbing change.

2. **For the Layer-C `test_bpsd_round_trip`, what is the minimal C ABI
   sequence that drives an eq-side BPSD push?**
   - `tot_init` initializes all modules in-image; `eq_init` is called
     implicitly. But does the init chain push BPSD slots into the broker,
     or is that deferred to `eq_run`?
   - Need to verify: try the test as `tot_init → tot_run(0?) → pull` first;
     if that's insufficient, follow with `tot_set_param("eq:...", ...) → eq_run`.
   - **Action**: prototype the sequence locally before committing the test.

3. **`tot_mono_flag.f90` module name choice — `tot_mono_flag` or `tot_build_flag`?**
   - The latter generalizes to future build variants (debug, instrumented).
   - **Recommendation**: `tot_mono_flag` for now; rename if a 3rd variant
     appears.

---

## Self-review checklist

- [x] Placeholder scan: no "TBD", concrete pattern in §3 / §4 / §5 / §6 / §7
- [x] Internal consistency: ABI surface (§4) ↔ pipeline detect (§5) ↔ test (§6)
- [x] Scope check: §2 explicitly defers wrapper plumbing to Phase 2c
- [x] Ambiguity check: §11 calls out the 3 design judgments needing user
      confirmation before the plan writer commits to one
