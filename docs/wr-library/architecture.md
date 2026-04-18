# TASK/WR library-ization — architecture

Phase L delivered a shared-library + Python-wrapper alternative to the
traditional `wr` CLI for the TASK ray-tracing module. The WR project
mirrors the TR Phase L structure (see
`docs/tr-library/architecture.md`); this doc records the WR-specific
diagram and per-phase status.

## System diagram

```
+-------------------------------------------------------------------+
| User code                                                          |
|                                                                    |
|   Python scripts            C / C++ drivers          Interactive   |
|   (examples/, tests/)       (own main.c, etc.)       shell users   |
+-----------+-----------------+---------------+--------------+-------+
            |                 |               |              |
            v                 v               v              |
   +------------------+  +---------------+                   |
   |  python/wrlib    |  |  <C driver>   |                   |
   |  (ctypes)        |  |  (#include    |                   |
   |                  |  |   wr_api.h)   |                   |
   |  Wrlib / WrState |  +-------+-------+                   |
   |  errors / _ffi   |          |                           |
   +--------+---------+          |                           |
            |                    |                           |
            +----------+---------+                           |
                       |                                     |
                       v                                     v
            +-----------------------+               +----------------+
            |   wr/libwrapi.so      |               |   wr/wr        |
            |   (shared lib, L-4)   |               |   (CLI binary) |
            |                       |               |                |
            |   5 exported symbols  |               |   menu loop,   |
            |   wr_init / wr_run /  |               |   graphics,    |
            |   wr_set_param /      |               |   file I/O     |
            |   wr_get_state /      |               +-------+--------+
            |   wr_finalize         |                       |
            +-----------+-----------+                       |
                        |                                   |
                        v                                   v
            +---------------------------------------------------+
            |  Fortran backend  (shared code)                    |
            |                                                    |
            |   wr_api.f90              wraps WRCOMM globals     |
            |   wr_param_registry.f90   name -> variable dispatch|
            |   wr_setup / wr_exec      ray-tracing kernels      |
            |   wrcomm.f90 + wrcomm_parm.f90  COMMON/module state|
            |   wr_allocate / wr_deallocate / wr_reset_alloc_state|
            +-------------------+-------------------------------+
                                |
                                v
            +---------------------------------------------------+
            |  Dependency libraries (PIC + non-PIC variants)    |
            |   lib/ libtask_pic.a   pl/ libpl_pic.a            |
            |   eq/ libeq_pic.a      dp/ libdp_pic.a            |
            |   mtxp/ libmtxp_pic.a  ../bpsd/ libbpsd_pic.a     |
            +---------------------------------------------------+
```

## Layering

| Layer | Artefact | Purpose |
|---|---|---|
| 0. Regression baseline | `test_run/baselines/wr_*/metrics.json` | Phase 0 ground truth (tol `1e-10`) |
| 1. Fortran backend | `wr/wr_api.f90`, `wr_param_registry.f90`, `wr_setup`, `wr_exec`, ... | Numerics, shared with `wr` binary |
| 2. C ABI | `wr/wr_api.h` + BIND(C) exports in `wr_api.f90` | 5 functions, stable contract |
| 3. Shared library | `wr/libwrapi.so` | `make -C wr libwrapi.so`, links `lib*_pic.a` |
| 4. Python FFI | `python/wrlib/_ffi.py` | `ctypes` layout mirror of `wr_state_t` |
| 5. High-level wrapper | `python/wrlib/wrlib.py`, `state.py`, `errors.py` | Context manager + dataclass |
| 6. User scripts | `python/wrlib/examples/*.py`, user notebooks | |

### 5 C ABI entry points

From `wr/wr_api.h`:

```c
int wr_init(void);
int wr_run(int nray_request);
int wr_set_param(const char *name, double value);
int wr_get_state(wr_state_t *state);
int wr_finalize(void);
```

Return codes (`enum wr_error`):

| code | meaning | Python exception |
|---|---|---|
| 0 | OK | — |
| 1 | invalid name / value | `WrlibParamError` |
| 2 | not initialised | `WrlibStateError` |
| 3 | calculation failed (`wr_setup`/`wr_exec`/`wr_get_state`) | `WrlibRunError` |
| 4 | not implemented (Phase L-2 stub) | `WrlibNotImplementedError` |

`wr_state_t` carries three runtime dimensions (`nraymax`, `nrsmax`,
`nrlmax`) bounded by `WR_MAX_NRAYMAX=100`, `WR_MAX_NRSMAX=200`,
`WR_MAX_NRLMAX=400`. It includes four global peak-power scalars
(`pos_pwrmax_rs`, `pwrmax_rs`, `pos_pwrmax_rl`, `pwrmax_rl`),
five `[NRAYMAX]` per-ray arrays (`nstp_end`, `pos_pwrmax_rs_nray`,
`pwrmax_rs_nray`, `pos_pwrmax_rl_nray`, `pwrmax_rl_nray`), a
`rays_end[NRAYMAX][WR_MAX_NRAY_EQ=9]` end-state table (mirror of
`RAYS(0:NEQ, end, i)` with `NEQ=8` ⇒ 9 components), and two
deposition-profile pairs (`pos_nrs[NRSMAX]`/`pwr_nrs[NRSMAX]` for the
minor-radius axis and `pos_nrl[NRLMAX]`/`pwr_nrl[NRLMAX]` for the
major-radius axis).

### Fortran backend

- `wr_api.f90` owns the BIND(C) wrappers. Each function is a thin
  shim that marshals C arguments into the existing Fortran entry
  points and maps Fortran ierr to the C `enum wr_error`.
- `wr_param_registry.f90` implements a hand-written `SELECT CASE`
  dispatch (~80 cases) mapping `"NAME"` or `"NAME[idx]"` strings to
  WRCOMM / WRCOMM_PARM / PLCOMM / DPCOMM module variables. Extending
  the registry is the **only** code change needed to expose new
  parameters.
- Kernel code (`wr_setup`, `wr_exec`, `wrsub`, `wrdisp`, ...) is
  unchanged and shared with the `wr` binary.

### Python wrapper

- `wrlib._ffi.WrStateC` mirrors `wr_state_t` byte-for-byte (padded to
  `WR_MAX_NRAYMAX=100`, `WR_MAX_NRSMAX=200`, `WR_MAX_NRLMAX=400`,
  `WR_MAX_NRAY_EQ=9`). The C `rays_end[NRAYMAX][NRAY_EQ]` and the
  Fortran `rays_end(NRAY_EQ, NRAYMAX)` are the same bytes; only the
  index order differs.
- `wrlib._ffi.load_library` resolves the shared library via
  `WRLIB_PATH` → `wr/libwrapi.so` → `lib/libwrapi.so` and uses
  `RTLD_LAZY` so dangling graphics references never block loading.
- `wrlib.Wrlib` is a context manager: `__init__` calls `wr_init`,
  `__exit__` / `close()` calls `wr_finalize`. All 5 entry points map
  1:1 to methods.
- `wrlib.WrState` is a `@dataclass` snapshot; `to_dict()` is
  JSON-serialisable and matches the Phase 0 baseline layout so
  `compare_metrics.py` can diff wrapper output against `wr` runs.

### Post-finalize state-reset invariant (PR #36 Bugbot HIGH)

`wr_allocate` tracks whether its arrays are already sized by SAVE
flags (`INIT`, `NRAYMAX_SAVE`, `NSTPMAX_SAVE`). PR #36 surfaced that
`wr_finalize` did not reset these flags, so a
`wr_init → wr_run → wr_finalize → wr_init → wr_run` cycle would enter
the ELSE branch of `wr_allocate`, call `wr_deallocate` on already-freed
arrays, and crash with a Fortran runtime error.

The fix introduces a helper `wr_reset_alloc_state` (module-scope
subroutine) that zeroes the SAVE flags, and `wr_finalize` calls it
after `wr_deallocate`. Every `DEALLOCATE` is also now guarded with
`ALLOCATED()`, so repeated finalize/init cycles are idempotent.

The invariant is regression-covered at three layers: Layer 2 adds
`wr/tests/c_abi/test_reinit.c`, Layer 3's `test_wrlib.py` reopens a
`Wrlib()` context, and Layer 4's `wrlib_sweep` executes 9 full
init/finalize cycles back-to-back. Any future `wr_finalize` rewrite
must preserve `CALL wr_reset_alloc_state` or add an equivalent hook.

## Phase L completion matrix

| Phase | Deliverable | Plan | Merge PR | Date |
|---|---|---|---|---|
| L-0 | Phase 0 regression baselines (`wr_iter_lhcd`, `wr_test001`, `wr_tst2_ec`) | `2026-04-18-wr-library-L0-baseline.md` | #15 | 2026-04-18 |
| L-1 | Makefile graphics split | `2026-04-18-wr-library-L1-graphics-split.md` | #24 | 2026-04-18 |
| L-2 | C ABI foundation (`wr_api.h`, stub exports returning ierr=4) | `2026-04-18-wr-library-L2-c-abi-foundation.md` | #30 | 2026-04-18 |
| L-3 | Parameter registry + real `wr_init/run/get_state/finalize` (+ Bugbot HIGH reset fix) | `2026-04-18-wr-library-L3-param-registry.md` | #36 | 2026-04-18 |
| L-4 | `libwrapi.so` shared-library build + PIC variants | `2026-04-18-wr-library-L4-shared-lib-build.md` | #42 | 2026-04-18 |
| L-5 | `python/wrlib/` ctypes wrapper (`Wrlib`, `WrState`, errors) | `2026-04-18-wr-library-L5-python-wrapper.md` | #46 | 2026-04-18 |
| L-6 | 4-layer test suite wired into `run_tests.sh` | `2026-04-18-wr-library-L6-test-4layers.md` | #60 | 2026-04-18 |
| L-7 | Library documentation (this doc, README, examples, CHANGELOG) | `2026-04-18-wr-library-L7-docs.md` | this PR | 2026-04-18 |

## Acceptance criteria status

Mirrors the tr spec's §12.2 for the WR module:

| Criterion | Sub-phase | How to verify |
|---|---|---|
| `libwrapi.so` generated | L-4 | `ls wr/libwrapi.so && file wr/libwrapi.so` |
| `import wrlib` works | L-5 | `python3 -c "from wrlib import Wrlib"` |
| Layer 1 equivalence PASS | L-6 | `test_run/run_tests.sh wrlib_equivalence` |
| Layer 2 C ABI PASS | L-6 | `test_run/run_tests.sh wrlib_c_abi` |
| Layer 3 Python wrapper PASS | L-6 | `test_run/run_tests.sh wrlib_ffi wrlib_wrapper` |
| Layer 4 sweep smoke PASS | L-6 | `test_run/run_tests.sh wrlib_sweep` |
| `wr` numerics match Phase 0 | L-0..L-6 | `test_run/run_tests.sh wr_iter_lhcd wr_test001 wr_tst2_ec` |
| `python/wrlib/README.md` with examples | L-7 | visual review + `python3 -m py_compile examples/*.py` |
| `run_tests.sh` wrlib_* wired | L-6 | `grep wrlib_ test_run/test_definitions.conf` |

## Known limitations

- **Single instance per process.** WR's `wrcomm` module holds COMMON
  blocks plus SAVE allocation flags. `wr_reset_alloc_state` makes the
  init/finalize cycle idempotent within a single process, but two
  concurrent `Wrlib()` handles in the same process still share state.
  Use `multiprocessing` for parallel sweeps.
- **Beam tracing (`mode_beam /= 0`) is not exposed through `wr_get_state`.**
  The solver runs, but only ray-tracing outputs are surfaced.
- **Input scalars (`RF`, `RPI`, ...) are not echoed in `wr_get_state`.**
  Use `set_param` round-trip for confirmation; reading them back is a
  future-phase extension (`wr_get_param`).
- **String parameters not yet wired** — no character-valued namelist
  keys are currently registered (design spec §4.3 deferral).

## References

- Design spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md`
  (WR follows the same pattern; no separate WR spec)
- User README: `python/wrlib/README.md`
- Phase plans: `docs/superpowers/plans/2026-04-18-wr-library-L*.md`
- tr counterpart: `docs/tr-library/architecture.md`
- ti counterpart: `docs/ti-library/architecture.md`
- Changelog: top-level `CHANGELOG.md`
