# C ABI state structs — runtime layout check (design, #246)

**Status**: design, pre-implementation, awaiting one decision (§7)
**Date**: 2026-10-17
**Tracking issue**: #246 (raised by the Codex review of #233)
**Related**: #187 / #193 (AJRFT, the first `tr_state_t` / `tot_state_t`
growth), #233 (fp global scalars, open, grows `fp_state_t`), #244 (fp
regress mirror, depends on #233), #245 / #248 (`fp_get_state` extents)

## 1. Problem

Every module exposes one fixed-layout struct, filled by
`X_get_state(X_state_t*)`:

| module | struct | header | Fortran mirror | version macro today |
|---|---|---|---|---|
| tr  | `tr_state_t`  | `tr/tr_api.h`   | `tr/tr_state.f90`  `tr_state_c`  | `TR_STATE_ABI_VERSION 2` (compile-time only) |
| tot | `tot_state_t` | `tot/tot_api.h` | `tot/tot_state.f90` `tot_state_c` | `TOT_STATE_ABI_VERSION 2` (compile-time only) |
| eq  | `eq_state_t`  | `eq/eq_api.h`   | `eq/eq_state.f90`  | none |
| fp  | `fp_state_t`  | `fp/fp_api.h`   | `fp/fp_state.f90`  | none |
| ti  | `ti_state_t`  | `ti/ti_api.h`   | `ti/ti_state.f90`  | none |
| wr  | `wr_state_t`  | `wr/wr_api.h`   | `wr/wr_state.f90`  | none |
| wrx | `wrx_state_t` | `wrx/wrx_api.h` | `wrx/wrx_state.f90` | none |

The only rule is "append at the end, bump the macro where one exists,
rebuild `libXapi.so` in the same commit". Nothing checks it at run time,
so a layout change fails silently in two ways:

- **old caller, new library**: `X_get_state` writes the appended members
  past the caller's shorter allocation (56 bytes in #233's case, during
  the unconditional zeroing, even on an error return);
- **new caller, old library**: the appended members are never written,
  the ctypes struct is zero-initialised, and the wrapper, the MCP server
  and the Web Client receive plausible `0.0` values with no indication
  that the library lacks the field.

The Python `test_size_matches_header_math` tests only check ctypes
arithmetic against numbers typed into the test; nothing compares the
ctypes layout with the `BIND(C)` type that the library actually fills.

## 2. Goals

1. Both failure modes are refused **before any struct is passed**, with
   an error that names the fix ("rebuild `libXapi.so`" or "update the
   wrapper").
2. One source of truth for the layout version, checked mechanically
   between Fortran, the C header and Python.
3. Same mechanism in all seven modules and in the mono image, with no
   change to the existing `X_get_state` signature or to any struct.
4. Small enough to land as one PR per layer (Fortran+header, Python,
   docs) or one PR in total.

Non-goals: making old callers *work* with new libraries (no versioned
getters, no per-field presence flags), and dynamic sizing of the arrays
(the `X_MAX_*` capacities stay compile-time).

## 3. Options considered

**(1) Size-negotiated getter** `int X_get_state_v2(X_state_t*, size_t
sizeof_state)`: the library fills `min(given, sizeof(X_state_t))` bytes
and returns a distinct code when the caller's struct is smaller. Precise,
and it protects a raw C caller that never asks for a version. Cost: a
second getter per module to keep forever (or a deprecation cycle for the
first), a new error code, and the wrapper still needs a version query to
tell "smaller because old" from "smaller because wrong".

**(2) Runtime layout query**: each library exports its struct version
and `sizeof`; the wrapper compares both with its own at load time. Cost:
two trivial functions per module. It does not protect a C caller that
ignores the query, but every in-tree C consumer rebuilds from the header
and the only downstream consumer (the TASK Web Client, via the MCP
servers) goes through the Python wrappers.

**Recommendation: (2) now, (1) only if an out-of-tree C consumer
appears.** (2) alone meets goals 1–3: a pre-#246 library has no query
symbol (new caller / old library → refused at load), and a library whose
struct grew reports a larger size than the wrapper's (old caller / new
library → refused at load).

## 4. Design (option 2)

### 4.1 Fortran: version and size next to the type

In each `X_state.f90`, next to `TYPE, BIND(C) :: X_state_c`:

```fortran
  ! Layout version of X_state_c / X_state_t. Bump together with
  ! X_STATE_ABI_VERSION in X_api.h whenever a field is added, removed or
  ! reordered; the C-ABI driver fails when the two drift (§4.3).
  INTEGER(C_INT), PARAMETER :: X_STATE_ABI_VERSION = 1   ! 2 for tr, tot
```

In each `X_api.f90`, two `BIND(C)` functions (no lifecycle check, no
side effects, callable before `X_init`):

```fortran
  FUNCTION X_api_state_abi_version() RESULT(v) BIND(C, NAME="X_state_abi_version")
    INTEGER(C_INT) :: v
    v = X_STATE_ABI_VERSION
  END FUNCTION

  FUNCTION X_api_state_size() RESULT(n) BIND(C, NAME="X_state_size")
    INTEGER(C_SIZE_T) :: n
    TYPE(X_state_c) :: probe
    n = INT(C_SIZEOF(probe), C_SIZE_T)   ! or STORAGE_SIZE(probe)/8
  END FUNCTION
```

The size comes from the `BIND(C)` type, so the library, not the header,
is authoritative. `probe` is a local of up to ~5 MB for eq (the type is
large); if a compiler objects to the stack frame, `STORAGE_SIZE` of a
dummy with `TYPE(X_state_c), INTENT(IN) :: t` needs no object at all —
pick whichever gfortran 13 and the `-fcheck=all` build accept and use
it in all seven.

Mono image: `libtotapi_mono.so` co-links every module's objects, so it
exports all fourteen symbols without any tot-level addition; the
version is per module, not per image. The `libtotapi_mono_inspect`
target gets one more `nm` line asserting the seven `_state_size`
symbols are present.

### 4.2 C header: macro mirrors the PARAMETER

```c
#define X_STATE_ABI_VERSION 1          /* mirror of X_state.f90 */
int    X_state_abi_version(void);      /* the library's value */
size_t X_state_size(void);             /* sizeof the library's X_state_t */
```

tr and tot already have the macro at 2 with a History block; eq, fp,
ti, wr, wrx get it at 1 with the same block. Rule text (one paragraph,
same in all seven headers): bump the PARAMETER and the macro together
in the commit that changes the struct; rebuild the library; the wrapper
refuses any other combination.

### 4.3 C-ABI drivers: Fortran vs header cross-check

In each module's `tests/c_abi/test_negative.c` (runs before init, which
is exactly when these must work):

```c
EXPECT_EQ(X_state_abi_version(), X_STATE_ABI_VERSION, "abi-version-matches-header");
EXPECT_EQ((long) X_state_size(), (long) sizeof(X_state_t), "state-size-matches-header");
```

This is the Fortran `BIND(C)`-type vs C-struct check the issue asks
for. `X_api_check_so` (dlopen path) gets the same two lines so the
shared library, not only the static link, is checked.

### 4.4 Python: one helper, called from every `_ffi.py`

New `python/_abi_check.py` (next to `_runtime_mode.py`, importable by
all seven wrappers through the existing `sys.path` setup):

```python
def check_state_layout(lib, *, prefix, struct, expected_version, lib_name):
    """Refuse a library whose X_state_t layout differs from `struct`."""
    try:
        fn_v = getattr(lib, f"{prefix}_state_abi_version")
        fn_s = getattr(lib, f"{prefix}_state_size")
    except AttributeError as exc:
        raise AbiMismatchError(
            f"{lib_name} does not export {prefix}_state_abi_version / "
            f"{prefix}_state_size: it predates the layout check (#246); "
            f"rebuild it (`make -C {prefix} {lib_name}`)") from exc
    fn_v.restype = ctypes.c_int;    fn_v.argtypes = []
    fn_s.restype = ctypes.c_size_t; fn_s.argtypes = []
    have_v, have_s = fn_v(), fn_s()
    want_s = ctypes.sizeof(struct)
    if have_v != expected_version or have_s != want_s:
        raise AbiMismatchError(
            f"{lib_name} state layout is v{have_v} / {have_s} bytes, this "
            f"wrapper expects v{expected_version} / {want_s} bytes; rebuild "
            f"the library or update python/{prefix}lib/_ffi.py")
```

`AbiMismatchError` subclasses each wrapper's base error (`TrlibError`,
…) through a small adapter so existing `except XlibError` handlers keep
working; concretely the helper raises a plain `RuntimeError` subclass
and each `_ffi.py` re-raises as its own `XlibError`. Called from
`_apply_prototypes` (where the `try/except AttributeError` pattern for
optional symbols already lives), so it runs once per `load_library`,
before any struct is passed. `X_STATE_ABI_VERSION` is a constant in each
`_ffi.py`, next to the `X_MAX_*` constants that already mirror the
header.

Mono routing needs nothing extra: a wrapper routed to
`libtotapi_mono.so` checks its own module's pair in that image.

### 4.5 Tests

Per wrapper, in `python/Xlib/tests/test_ffi.py` (real library; skipped
when the `.so` is absent, as the sibling tests are):

- `test_library_layout_matches_wrapper`: `load_library()` succeeds and
  `X_state_size()` equals `ctypes.sizeof(XStateC)`, `X_state_abi_version()`
  equals the wrapper constant.
- `test_stale_wrapper_layout_is_refused`: a ctypes struct with the last
  field removed, passed to the helper → `AbiMismatchError` naming both
  sizes (the "old caller / new library" case).
- `test_version_drift_is_refused`: the real struct with
  `expected_version + 1` → refused (a reorder that keeps the size).
- `test_library_without_the_symbols_is_refused`: a stub object without
  the two attributes → the "predates the layout check" error (the "new
  caller / old library" case).

The helper itself gets `python/tests/test_abi_check.py` with the same
four cases on a fake library, so the logic is tested once without any
`.so`.

C side: §4.3. CI runs only `tot_api_check_all` today
(`.github/workflows/python-tests.yml:244`); the six per-module drivers
run locally (`make -C X X_api_check_all`, which on macOS fails to link
for tr because of the missing graphics library, while `X_api_check_so`
links everywhere). The PR adds the six `X_api_check_so` targets to the
pytest job so the dlopen-path cross-check runs on Linux for every
module; the static-link drivers stay local.

### 4.6 Docs

- `docs/*-library/architecture.md` (seven): a short "State struct
  layout" rule: append only; bump PARAMETER + macro together; rebuild;
  the wrapper refuses a mismatch; what the error looks like.
- `docs/sphinx/modules/tr/{en,ja}/extending-tr.md` step 5: "bump the
  Fortran PARAMETER and the header macro together; the C driver fails
  when they drift" (the existing text mentions the macro only).
- `python/Xlib/README.md` (seven): one line under the load section:
  the library must match the wrapper's layout; the error names the fix.
- CHANGELOG: Added.

## 5. Sequencing with #233 / #244

#233 (external, open) appends seven doubles to `fp_state_t`. Two
orderings:

- **#246 first (proposed)**: fp starts at version 1 with today's
  layout; #233 rebases, bumps `FP_STATE_ABI_VERSION` 1 → 2 in both
  places, and its wrapper test asserts version 2. One comment on #233
  says so. #244 follows #233 unchanged.
- #233 first: #246 starts fp at 1 with the grown layout and #233 needs
  no change. #233 is waiting on its author for a totlib fix and docs,
  so this ordering is not in our hands.

Either way the two cannot both merge without the second rebasing; the
conflict is a one-line macro and a test constant.

## 6. Work breakdown

| step | files | size |
|---|---|---|
| A. Fortran + header, 7 modules | `X_state.f90`, `X_api.f90`, `X_api.h` | ~15 lines each |
| B. C drivers | 7 × `tests/c_abi/test_negative.c`, `X_api_check_so` drivers | ~4 lines each |
| C. Python helper + 7 `_ffi.py` + errors | `python/_abi_check.py`, `python/Xlib/_ffi.py`, `python/Xlib/errors.py` | helper ~40 lines, ~10 per wrapper |
| D. Tests | `python/tests/test_abi_check.py`, 7 × `test_ffi.py` | ~30 + 7 × ~40 lines |
| E. Docs + CHANGELOG + mono inspect line | as §4.6 | text |

One PR is feasible (all mechanical, same shape ×7); if split, A+B first
(no behaviour change), then C+D (the refusal appears), then E.

Scope boundary for the sign-off rule: `X_state.f90` / `X_api.f90` /
`X_api.h` are the L-2 C-ABI layer, not module physics; no `trprep` /
`eqcalc` / … change.

## 7. Decisions requested

1. **Mechanism**: option 2 only (runtime version + size, wrapper refuses
   a mismatch), or option 2 plus the `_v2` size-negotiated getter from
   the start? Recommendation: 2 only.
2. **Ordering with #233**: land #246 first and ask #233 to bump fp to
   version 2 (recommendation), or wait for #233?
3. **Packaging**: one PR for A–E, or A+B / C+D / E as three?
   Recommendation: one PR, reviewed as one diff.
