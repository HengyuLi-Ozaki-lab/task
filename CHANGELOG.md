# Changelog

All notable changes to the TASK code are recorded here. This file
starts with Phase L (library-ization) of TASK/TR; earlier history is
in `git log` and `HISTORY`.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## TR Phase L — library-ization (2026-04-18)

Phase L turned TASK/TR from a CLI-only Fortran program into an
additionally-loadable shared library with a Python wrapper. The `tr2`
binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #2)** — Phase 0 regression-test infrastructure:
  `test_run/baselines/tr_{iter01,m0904,tst2}.json`,
  `tools/extract_tr_metrics.py`, `tools/compare_metrics.py`.
- **L-1 (2026-04-18, PR #21)** — `tr/Makefile` graphics split; `tr2`
  still links graphics, `libtrapi.so` builds are graphics-free.
- **L-2 (2026-04-18, PR #27)** — C ABI foundation: `tr/tr_api.h`,
  `tr/tr_api.f90`, `tr/tr_state.f90`; 5 entry-point stubs exported
  from `libtrapi` returning `TR_ERR_NOT_IMPL` (ierr=4).
- **L-3 (2026-04-18, PR #33)** — Parameter registry
  (`tr/tr_param_registry.f90`, ~38 `SELECT CASE` entries) and real
  bodies for `tr_init` / `tr_run` / `tr_get_state` / `tr_finalize`.
  `tr_set_param` accepts `"NAME"` and `"NAME[idx]"` (1-origin).
- **L-4 (2026-04-18, PR #35)** — `make -C tr libtrapi.so` builds the
  shared library. PIC variants (`*_pic.a`) of `lib`, `pl`, `eq`, `ob`,
  `mtxp`, `bpsd` added to participating Makefiles. Non-PIC archives
  and `tr2` are unchanged.
- **L-5 (2026-04-18, PR #44)** — Python wrapper `python/trlib/`:
  `Trlib` context manager, `TrState` dataclass, exception hierarchy
  mirroring `enum tr_error`, `_ffi` ctypes layer with `TRLIB_PATH`
  override and `RTLD_LAZY` loading.
- **L-6 (2026-04-18, PR #53)** — 4-layer test suite wired into
  `test_run/test_definitions.conf`:
  `trlib_equivalence` (Layer 1 vs Phase 0 baselines, tol `1e-10`),
  `trlib_c_abi` (Layer 2 `make -C tr tr_api_check_all`),
  `trlib_ffi` + `trlib_wrapper` (Layer 3 Python),
  `trlib_sweep` (Layer 4 3×3 RR×BB smoke).
- **L-7 (2026-04-18, this PR)** — User-facing documentation:
  rewritten `python/trlib/README.md`, example scripts
  (`quickstart.py`, `parameter_sweep.py`, `state_dump.py`),
  architecture doc (`docs/tr-library/architecture.md`), and this
  changelog.

### Known issues

- `tr_m0904` Layer 1 comparison drifts from its Phase 0 baseline by
  `~1e-8` under current `tr2`; it is pinned to the baseline rather
  than regenerated. `tr_iter01` and `tr_tst2` match to `1e-10`.
- String parameters (`KNAMEQ`, `KNAMTR`, etc.) are not yet wired
  through `tr_set_param` (design spec §4.3 deferral).
- Single instance per process only — TR globals are COMMON-block
  state.

## TI Phase L — library-ization (2026-04-18)

Phase L mirrors the TR library-ization for the TASK/TI impurity-
transport module: the same 5 C ABI functions, the same wrapper
architecture, parameter registry, and 4-layer test structure. The
`ti` CLI binary and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #12)** — Phase 0 regression-test
  infrastructure for TI: `test_run/baselines/ti_{min,ar,w}/`,
  `tools/extract_ti_metrics.py`, `test_run/inputs/ti_*.in`.
- **L-1 (2026-04-18, PR #22)** — `ti/Makefile` split into
  CORE / GRAPHICS / MENU `SRCS` groups so graphics-free Fortran
  compilations can be staged without touching the `ti` binary
  build.
- **L-2 (2026-04-18, PR #28)** — C ABI foundation: `ti/ti_api.h`,
  `ti/ti_api.f90`, `ti/ti_state.f90`; 5 entry-point stubs returning
  `TI_ERR_NOT_IMPL` (ierr=4), plus `ti_api_check` target and first
  C-side smoke tests under `ti/tests/c_abi/`.
- **L-3 (2026-04-18, PR #34)** — Parameter registry
  (`ti/ti_param_registry.f90`, ~35 `SELECT CASE` entries covering
  scalars, 1-D arrays, and 2-D `[i,j]` subscripts) plus real bodies
  for `ti_init` / `ti_run` / `ti_get_state` / `ti_finalize`.
  `ti_set_param` accepts `"NAME"`, `"NAME[i]"`, and `"NAME[i,j]"`
  (1-origin). PA/PM naming deliberately exposes only `PA` (the
  PLCOMM true name).
- **L-4 (2026-04-18, PR #41)** — `make -C ti libtiapi.so` builds
  the shared library. PIC variants (`*_pic.a`) of `lib`, `pl`,
  `eq`, `adpost`, `open-adas/adf11`, `mtxp`, `bpsd` added to
  participating Makefiles. Non-PIC archives and the `ti` binary are
  unchanged. (Target is staged on feature branch; see Known issues.)
- **L-5 (2026-04-18, PR #47)** — Python wrapper `python/tilib/`:
  `TiLib` / `Tilib` context manager, `TiState` dataclass,
  exception hierarchy mirroring `enum ti_error`, `_ffi` ctypes
  layer with `TILIB_PATH` override and `RTLD_LAZY` loading.
- **L-6 (2026-04-18, PR #57)** — 4-layer test suite wired into
  `test_run/test_definitions.conf` (`tilib_equivalence` Layer 1
  vs Phase 0 baselines at tol `1e-10`, `tilib_c_abi` Layer 2
  `make -C ti ti_api_check_all`, `tilib_ffi` + `tilib_wrapper`
  Layer 3 Python, `tilib_sweep` Layer 4 3×3 DT×NRMAX smoke) plus
  Ar fixture applying atomic mass via `PA[3]` instead of the dead
  `PM` alias.
- **L-7 (2026-04-18, this PR)** — User-facing documentation:
  rewritten `python/tilib/README.md`, example scripts
  (`quickstart.py`, `parameter_sweep.py`, `state_dump.py`),
  architecture doc (`docs/ti-library/architecture.md`), and this
  changelog entry.

### Known issues

- `libtiapi.so` Makefile target has not yet merged into `develop`;
  it lives on `feature/ti-library-L4-shared-lib` and is pending a
  follow-up PR. The wrapper, examples, and tests all tolerate a
  missing library by skipping FFI-level checks.
- `ti_ar` baseline shows small drift similar in character to
  `tr_m0904`; when regeneration is needed pin the baseline rather
  than re-running against a moving `ti` output.
- String parameters (`KID_NS`, ...) are not wired through
  `ti_set_param`. Argon fixtures work around this by setting
  `NPA[3]=18` and letting `tiinit.f90` recompute the label.
- Per-species diffusion knobs `DN0`, `DT0`, `DR0`, `DRS`,
  `DN0_NS[i]` are not yet in the registry.
- Single instance per process only — TI globals are COMMON-block
  state.

## WR Phase L — library-ization (2026-04-18)

Phase L mirrors the TR library-ization for the TASK/WR ray-tracing
module: the same 5 C ABI functions, the same wrapper architecture,
parameter registry, and 4-layer test structure. The `wr` CLI binary
and its menu/graphics are unchanged.

### Added

- **L-0 (2026-04-18, PR #15)** — Phase 0 regression-test
  infrastructure for WR: `test_run/baselines/wr_{iter_lhcd,test001,
  tst2_ec}/metrics.json`, `tools/extract_wr_metrics.py`,
  `test_run/inputs/wr_*.in`.
- **L-1 (2026-04-18, PR #24)** — `wr/Makefile` SRCS split so the
  graphics-free Fortran layer can be staged into a shared library
  without touching the `wr` binary build.
- **L-2 (2026-04-18, PR #30)** — C ABI foundation: `wr/wr_api.h`,
  `wr/wr_api.f90`; 5 entry-point stubs returning `WR_ERR_NOT_IMPL`
  (ierr=4) with a `wr_api_check` smoke target under
  `wr/tests/c_abi/`.
- **L-3 (2026-04-18, PR #36)** — Parameter registry
  (`wr/wr_param_registry.f90`, ~80 `SELECT CASE` entries covering
  scalars and 1-D arrays) plus real bodies for `wr_init` / `wr_run`
  / `wr_get_state` / `wr_finalize`. `wr_set_param` accepts `"NAME"`
  and `"NAME[idx]"` (1-origin). Includes the Bugbot HIGH fix
  (double-free on finalize-then-reinit): `wr_allocate` SAVE flags
  moved to module scope, `wr_reset_alloc_state` added and called
  from `wr_finalize`, and every `wr_deallocate` guarded with
  `ALLOCATED()`. Expands `wr_api_check_all` with `test_param`,
  `test_run`, `test_reinit` C drivers.
- **L-4 (2026-04-18, PR #42)** — `make -C wr libwrapi.so` builds the
  shared library. PIC variants (`*_pic.a`) of `lib`, `pl`, `eq`,
  `dp`, `mtxp`, `bpsd` added to participating Makefiles. Non-PIC
  archives and the `wr` binary are unchanged.
- **L-5 (2026-04-18, PR #46)** — Python wrapper `python/wrlib/`:
  `Wrlib` context manager, `WrState` dataclass, exception hierarchy
  mirroring `enum wr_error`, `_ffi` ctypes layer with `WRLIB_PATH`
  override and `RTLD_LAZY` loading.
- **L-6 (2026-04-18, PR #60)** — 4-layer test suite wired into
  `test_run/test_definitions.conf`:
  `wrlib_equivalence` (Layer 1 vs Phase 0 baselines, tol `1e-10`),
  `wrlib_c_abi` (Layer 2 `make -C wr wr_api_check_all` covering
  smoke/param/run/reinit/run_so/negative),
  `wrlib_ffi` + `wrlib_wrapper` (Layer 3 Python),
  `wrlib_sweep` (Layer 4 3×3 RFIN × ANGPHIN smoke).
- **L-7 (2026-04-18, this PR)** — User-facing documentation:
  rewritten `python/wrlib/README.md`, example scripts
  (`quickstart.py`, `parameter_sweep.py`, `state_dump.py`),
  architecture doc (`docs/wr-library/architecture.md`), and this
  changelog entry.

### Known issues

- Post-finalize state-reset invariant: `wr_finalize` must call
  `wr_reset_alloc_state` to zero `wr_allocate`'s SAVE flags
  (`INIT`, `NRAYMAX_SAVE`, `NSTPMAX_SAVE`). Do not remove this hook
  when extending `wr_finalize`; the Layer-4 `wrlib_sweep` and the
  Layer-2 `test_reinit.c` driver both exercise 9+ full cycles and
  will crash if the invariant regresses (PR #36 Bugbot HIGH).
- Beam tracing (`mode_beam /= 0`) is not exposed through
  `wr_get_state`; only ray-tracing outputs are surfaced.
- Input scalars (`RF`, `RPI`, ...) are not echoed in
  `wr_get_state`; reading them back is a future-phase extension.
- String parameters are not wired through `wr_set_param`.
- Single instance per process only — WR globals are COMMON-block
  state plus module-scope allocation flags.
