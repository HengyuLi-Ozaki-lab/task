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
