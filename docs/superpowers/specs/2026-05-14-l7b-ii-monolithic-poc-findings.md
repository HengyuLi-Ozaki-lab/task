# L-7b-ii Monolithic libtotapi_mono.so PoC — Findings

**Date:** 2026-05-14
**Branch:** `chore/l7b-ii-monolithic-poc`
**Predecessor specs:** `2026-04-28-l7a-cross-module-coupling-design.md`,
`2026-05-03-l7b-ii-bpsd-broker-coupling-design.md`

---

## Summary

A monolithic-image build path (`libtotapi_mono.so`) is **technically
feasible** as the foundation for activating the `("eq", "tr")` BPSD
coupling rule deferred in L-7b-ii §0. The Makefile-only PoC in this
branch links eq + tr + fp + ti + wrx PIC objects together with a
**single** BPSD broker set, producing a Mach-O dylib that no longer
depends on `@rpath/libeqapi.so` / `libtrapi.so` and exports the same
`tot_*` C ABI as the default `libtotapi.so`.

The remaining hurdle — graphics-stub deduplication — is well-scoped
and bounded. The PoC stops short of the 1e-10 equivalence-test gate
pending the follow-up unified stubs file.

---

## What was verified

### 1. Codex finding: `libtotapi.so` is NOT monolithic today

Independent verification with `otool -L` and `nm` confirms the Codex
review's claim that the current `tot/libtotapi.so` links **against**
`libeqapi.so` / `libtrapi.so` / `libfpapi.so` / `libtiapi.so` /
`libwrxapi.so` as separate runtime shared libraries, NOT into a
single image:

```text
$ otool -L tot/libtotapi.so | grep apis
    @rpath/libeqapi.so
    @rpath/libtrapi.so
    @rpath/libfpapi.so
    @rpath/libtiapi.so
    @rpath/libwrxapi.so

$ nm tot/libtotapi.so | grep '_bpsd_.*_MOD_.*x_init_flag'
(no output — libtotapi.so carries no bpsd storage of its own)

$ nm eq/libeqapi.so tr/libtrapi.so | grep '_bpsd_device_MOD_bpsd_devicex_init_flag'
(present in BOTH — each .so has its own private copy)
```

**Consequence**: the legacy `Tot` API in `libtotapi.so` has the same
structural BPSD isolation as `TotPipeline` would have — `eq.run()`'s
BPSD writes through `libeqapi.so`'s broker do not reach `tr.run()`'s
reads through `libtrapi.so`'s broker. The 1e-10 equivalence tests for
`tot_demo2014_short` / `tot_ht6m_short` pass anyway because those
fixtures don't drive the BPSD-mediated profile coupling path; they
exercise the orchestrator-level fan-out but not the broker.

This **invalidates** the L-7b-ii spec §0's stated premise that
"レガシー `Tot` / `libtotapi.so` は eq + tr + bpsd を同一 .so に
co-link しているため本制約の影響を受けない". The premise is correct
in spirit (a monolithic image would solve the problem) but wrong in
fact about the current artifact. Spec §0 amendment proposed below.

### 2. Monolithic PoC builds cleanly

The PoC adds a `libtotapi_mono.so` target to `tot/Makefile` that
links the same per-module PIC objects but with **one** copy of bpsd
and the per-module .so files dropped from the link line. The build
succeeds on macOS arm64 with gfortran 15.x:

```text
$ make -C tot libtotapi_mono.so
gfortran -shared -fPIC -Wl,-install_name,@rpath/libtotapi_mono.so \
    -Wl,-undefined,dynamic_lookup \
    tot's own PIC + eq + tr + fp + ti + wrx PIC (excluding bpsd) + \
    one canonical bpsd set + mtxp + pl + libtask + libmds + dp + ob + \
    adf11 + adpost \
    -o libtotapi_mono.so

$ file tot/libtotapi_mono.so
tot/libtotapi_mono.so: Mach-O 64-bit dynamically linked shared library arm64
```

### 3. BPSD broker storage is deduplicated to one set

The build's primary correctness claim — one set of bpsd storage
symbols instead of five — is verified:

```text
$ nm tot/libtotapi_mono.so | grep '_bpsd_.*_MOD_.*x_init_flag' | sort -u
___bpsd_device_MOD_bpsd_devicex_init_flag
___bpsd_equ1d_MOD_bpsd_equ1dx_init_flag
___bpsd_metric1d_MOD_bpsd_metric1dx_init_flag
___bpsd_plasmaf_MOD_bpsd_plasmafx_init_flag
___bpsd_shot_MOD_bpsd_shotx_init_flag
___bpsd_species_MOD_bpsd_speciesx_init_flag
___bpsd_trmatrix_MOD_bpsd_trmatrixx_init_flag
___bpsd_trsource_MOD_bpsd_trsourcex_init_flag
```

Eight bpsd module types, each with exactly one storage symbol —
not 5×8=40 as would be the case if all 5 modules' bpsd PIC copies
were independently linked.

### 4. No per-module .so dependencies

```text
$ otool -L tot/libtotapi_mono.so
@rpath/libtotapi_mono.so (self)
/opt/homebrew/opt/gcc/lib/gcc/current/libgfortran.5.dylib
/opt/homebrew/opt/gcc/lib/gcc/current/libquadmath.0.dylib
/usr/lib/libSystem.B.dylib
```

No `@rpath/libeqapi.so` / `libtrapi.so` / etc. The image is
self-contained.

### 5. C ABI surface is identical

```text
$ nm tot/libtotapi_mono.so | grep ' T _tot_'
_tot_finalize
_tot_get_state
_tot_init
_tot_run
_tot_set_param
_tot_set_param_str
```

All 6 `tot_*` exports present — Python ctypes wrapper would see
the same surface.

---

## What was not verified

### 1e-10 equivalence test — blocked on graphics stub deduplication

The test `python/totlib/tests/test_equivalence.py` fails to import
the monolithic .so via Python ctypes:

```text
$ TOTLIB_PATH=$PWD/tot/libtotapi_mono.so python -m pytest ...
OSError: dlopen(.../libtotapi_mono.so, 0x0003):
    symbol not found in flat namespace '_getkgt_'
```

`_getkgt_` and `_getkrt_` are stubs defined uniquely in
`tr_graphics_stubs.o`. They are missing because the mono build
keeps only ONE of the five `<mod>_graphics_stubs.o` files
(`fp_graphics_stubs.o`, the broadest non-conflicting set), to avoid
duplicate-symbol link errors for `pages_`, `guflsh_`, etc.

Even fp's stubs miss tr-unique (`_getkgt_`, `_getkrt_`),
ti-unique (`_text_`, `_move_`, `_numbd_`), wrx-unique (`_contf2_`,
`_contf3_`, ... ~14 contour symbols, `_r2w2b_`), and a handful of
3-D plot symbols (`_gaxis3d_`, `_gview3d_`, etc.).

Linking `lib/libgrf_pic.a` (the real implementations) was tried and
rejected — it pulls in non-PIC graphics dependencies (`r2w2b_`,
`text_`, `move_`) that fail at runtime, exactly as the eq/Makefile
comment at line 391-394 warned for `libeqapi.so`.

Attempting `-Wl,-multiply_defined,suppress` (Darwin) was tried and
rejected — the flag is deprecated since macOS 14 and the linker
errors anyway.

Attempting per-module static-archive dedup (each module's PIC
objects bundled into a `.a`, relying on archive semantics to pull
in objects only when resolving undefined symbols) was tried and
rejected — once `fp_graphics_stubs.o` is pulled in for `grd1d_mod`,
its full symbol set (including `_pages_` etc.) duplicates symbols
already in tot's own stubs object. Static archives dedupe at the
object granularity, not the symbol granularity.

---

## Decision

**Recommended path** (deferred to follow-up PR): write a unified
`tot/tot_graphics_stubs_mono.f90` that consolidates the union of
graphics stub symbols across all 5 per-module `<mod>_graphics_stubs.f90`
files. ~60 symbols total, all trivial no-op or `CPU_TIME`-wrapping
bodies. Then the mono build uses this single stubs file and drops
all 5 per-module stubs from the link, plus tot_graphics_stubs.o
itself.

This is the cleanest engineering path and stays within the
"no Fortran-body refactor" constraint — we're adding a new
self-contained stubs file, not restructuring `trcomm.f90` or any
core module logic.

Estimated effort: 1-2 hours to enumerate the symbol union, copy
stub bodies from the per-module sources into one consolidated file,
build, and validate.

---

## Proposed L-7b-ii spec §0 amendment

Add this paragraph after the existing 2026-05-04 deferral note:

> **2026-05-14 update**: `nm`/`otool` verification on the actual
> shipped artifact shows the spec's prior assumption that
> `libtotapi.so` co-links eq + tr + bpsd into one image is incorrect
> for current builds. `libtotapi.so` depends on `libeqapi.so` /
> `libtrapi.so` / `libfpapi.so` / `libtiapi.so` / `libwrxapi.so` as
> separate runtime shared libraries (`otool -L tot/libtotapi.so`)
> and carries no bpsd storage of its own (`nm tot/libtotapi.so` has
> zero `___bpsd_*_MOD_*x_init_flag` lines). The existing tot
> equivalence tests pass at 1e-10 because their fixtures do not
> exercise the BPSD-mediated profile coupling path — they validate
> the orchestrator fan-out (init/run/get_state/finalize chain) but
> not the cross-module broker round-trip. A 2026-05-14 PoC branch
> (`chore/l7b-ii-monolithic-poc`) demonstrates that a true monolithic
> `libtotapi_mono.so` **links** with one canonical bpsd PIC set via
> `tot/Makefile` changes alone (no Fortran-source changes). The
> resulting `.so` is **not yet dlopen-loadable** through Python ctypes:
> ~30 graphics symbols (`_getkgt_`, `_getkrt_`, `_contX_`, `_r2w2b_`,
> `_text_`, etc.) unique to individual `<mod>_graphics_stubs.o` files
> remain undefined when the mono build keeps only one such stub file
> (the broadest non-conflicting set, fp's). Making the mono image
> runtime-usable — and therefore activating `("eq", "tr")` in
> `COUPLING_RULES` against it — requires a small follow-up:
> consolidate the union of per-module graphics-stub symbols into a
> single new `tot/tot_graphics_stubs_mono.f90`. That is the only
> remaining gap. See
> `docs/superpowers/specs/2026-05-14-l7b-ii-monolithic-poc-findings.md`
> for the full investigation log.

---

## Known sharp edges in this PoC

### Wildcard ordering on a fresh checkout

The per-module PIC object lists are computed by `$(wildcard
../<mod>/obj/pic/*.o ../<mod>/obj/pic/*/*.o)` in `tot/Makefile`.
On a tree where the `<mod>/obj/pic/` directories don't yet exist,
the wildcards would expand to empty strings. To prevent silently
producing a broken `.so`:

- The variables use **deferred (`=`) assignment** so the wildcard
  re-expands after `mono_pic_prereqs` (which triggers each module's
  `libXXapi.so` build) has populated the obj/pic/ trees.
- The link recipe additionally runs an explicit sanity guard that
  errors out if any of the six PIC variable groups expand empty,
  with a recovery suggestion ("`make -C tot clean_pic && make -C
  tot libtotapi_mono.so`").

The `libtotapi_mono_inspect` helper validates that exactly 8
unique bpsd storage symbols are present (one per bpsd module type:
device + equ1d + metric1d + plasmaf + shot + species + trmatrix +
trsource). If the per-module dedup ever fails, this check turns
the failure into a hard error rather than a silent count drift.

### `libtotapi.so` and `libtotapi_mono.so` coexistence

Both builds are independent; the mono build can be enabled
per-test by setting the existing `TOTLIB_PATH` env var that
`python/totlib/_ffi.py` already honors. The default test path
continues to use `libtotapi.so`. `make -C tot clean_pic` removes
both artifacts.

## Follow-up work

1. Write `tot/tot_graphics_stubs_mono.f90` consolidating the
   ~60-symbol union of per-module stubs.
2. Build `libtotapi_mono.so` against it and verify dlopen succeeds.
3. Run the existing tot Layer-1 equivalence test against
   `libtotapi_mono.so` — must still pass at 1e-10 (these fixtures
   don't exercise BPSD coupling, so they're a regression check that
   the monolithic build hasn't broken the existing path).
4. Add a Layer-C BPSD smoke test: in the same image, drive an
   eq-only path that pushes BPSD, then call `tr_check_bpsd_pull`
   (already shipped in PR #188). Expect `ok=1`. Same call against
   the default per-module `libtotapi.so` must return `ok=0` to
   confirm the test distinguishes the two builds.
5. Register `("eq", "tr")` in `COUPLING_RULES` for the mono
   build only (mono and per-module builds can coexist via the
   `TOTLIB_PATH` env var override).

Tracked: see the linked follow-up issue on the GitHub PR opened
from this branch.
