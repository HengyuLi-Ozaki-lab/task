# TASK/TI library-ization — architecture

Phase L delivers a shared-library + Python-wrapper alternative to the
traditional `ti` CLI for the TASK impurity-transport module. The TI
project mirrors the TR Phase L structure (see
`docs/tr-library/architecture.md`); this doc records the TI-specific
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
   |  python/tilib    |  |  <C driver>   |                   |
   |  (ctypes)        |  |  (#include    |                   |
   |                  |  |   ti_api.h)   |                   |
   |  TiLib / TiState |  +-------+-------+                   |
   |  errors / _ffi   |          |                           |
   +--------+---------+          |                           |
            |                    |                           |
            +----------+---------+                           |
                       |                                     |
                       v                                     v
            +-----------------------+               +----------------+
            |   ti/libtiapi.so      |               |   ti/ti        |
            |   (shared lib, L-4)   |               |   (CLI binary) |
            |                       |               |                |
            |   5 exported symbols  |               |   menu loop,   |
            |   ti_init / ti_run /  |               |   graphics,    |
            |   ti_set_param /      |               |   file I/O     |
            |   ti_get_state /      |               +-------+--------+
            |   ti_finalize         |                       |
            +-----------+-----------+                       |
                        |                                   |
                        v                                   v
            +---------------------------------------------------+
            |  Fortran backend  (shared code)                    |
            |                                                    |
            |   ti_api.f90              wraps TICOMM globals     |
            |   ti_param_registry.f90   name -> variable dispatch|
            |   tiprep / tiexec / ...   time-advance kernels     |
            |   ticomm.f90 + ticomm_parm.f90  COMMON/module state|
            +-------------------+-------------------------------+
                                |
                                v
            +---------------------------------------------------+
            |  Dependency libraries (PIC + non-PIC variants)    |
            |   lib/ libtask_pic.a   pl/ libpl_pic.a            |
            |   eq/ libeq_pic.a      adpost/ lib-adpost_pic.a   |
            |   open-adas/adf11/ lib-adf11_pic.a                |
            |   mtxp/ libmtxp_pic.a  ../bpsd/ libbpsd_pic.a     |
            +---------------------------------------------------+
```

## Layering

| Layer | Artefact | Purpose |
|---|---|---|
| 0. Regression baseline | `test_run/baselines/ti_*/metrics.json` | Phase 0 ground truth (tol `1e-10`) |
| 1. Fortran backend | `ti/ti_api.f90`, `ti_param_registry.f90`, `tiprep`, `tiexec`, ... | Numerics, shared with `ti` binary |
| 2. C ABI | `ti/ti_api.h` + BIND(C) exports in `ti_api.f90` | 5 functions, stable contract |
| 3. Shared library | `ti/libtiapi.so` | `make -C ti libtiapi.so` (target lands in L-4) |
| 4. Python FFI | `python/tilib/_ffi.py` | `ctypes` layout mirror of `ti_state_t` |
| 5. High-level wrapper | `python/tilib/tilib.py`, `state.py`, `errors.py` | Context manager + dataclass |
| 6. User scripts | `python/tilib/examples/*.py`, user notebooks | |

### 5 C ABI entry points

From `ti/ti_api.h`:

```c
int ti_init(void);
int ti_run(int ntmax);
int ti_set_param(const char *name, double value);
int ti_get_state(ti_state_t *state);
int ti_finalize(void);
```

Return codes (`enum ti_error`):

| code | meaning | Python exception |
|---|---|---|
| 0 | OK | — |
| 1 | invalid name / value | `TilibParamError` |
| 2 | not initialised | `TilibStateError` |
| 3 | calculation failed | `TilibRunError` |
| 4 | not implemented (Phase L-2 stub) | `TilibNotImplementedError` |

`ti_state_t` carries four scalars (`nt`, `nrmax`, `nsa_max`, `nsmax`)
plus `T`, `residual_loop_max`, `icount_loop_max`, `icount_mat_max`,
three 2-D profile arrays (`RNA`, `RTA`, `RUA` of shape
`[TI_MAX_NRMAX][TI_MAX_NSA_MAX]`), and six 1-D profile arrays (`RBP`,
`RQP`, `RJP`, `ZEFF`, `BETA`, `BETAP`). The runtime copy uses only
the `[0:nrmax][0:nsa_max]` slice.

### Fortran backend

- `ti_api.f90` owns the BIND(C) wrappers. Each function is a thin
  shim that marshals C arguments into the existing Fortran entry
  points and maps Fortran ierr to the C `enum ti_error`.
- `ti_param_registry.f90` implements a hand-written `SELECT CASE`
  dispatch (~35 cases) mapping `"NAME"`, `"NAME[i]"`, or
  `"NAME[i,j]"` strings to TICOMM/PLCOMM module variables. Extending
  the registry is the **only** code change needed to expose new
  parameters.
- Kernel code (`tiprep`, `tiexec`, `ticoef`, `tisource`, ...) is
  unchanged and shared with the `ti` binary.
- The `ticomm.f90` module uses `USE plcomm, pm=>pa` to alias the
  atomic-mass array inside TI as `pm`, but the rename is local. The
  registry exposes the true PLCOMM name `PA` to callers.

### Python wrapper

- `tilib._ffi.TiStateC` mirrors `ti_state_t` byte-for-byte (padded to
  `TI_MAX_NRMAX=200`, `TI_MAX_NSA_MAX=20`).
- `tilib._ffi.load_library` resolves the shared library via
  `TILIB_PATH` → `ti/libtiapi.so` → `lib/libtiapi.so` and uses
  `RTLD_LAZY` so dangling graphics references never block loading.
- `tilib.TiLib` is a context manager: `__enter__` calls `ti_init`,
  `__exit__` calls `ti_finalize`. All 5 entry points map 1:1 to
  methods; a lowercase alias `Tilib` is exported.
- `tilib.TiState` is a `@dataclass` snapshot; `to_dict()` is
  JSON-serialisable and uses a `{"scalars": {...}, "profile": [...]}`
  layout so downstream tools can diff wrapper output against
  `ti` CLI runs.

## Phase L completion matrix

| Phase | Deliverable | Plan | Merge PR | Date |
|---|---|---|---|---|
| L-0 | Phase 0 regression baselines (`ti_min`, `ti_ar`, `ti_w`) | `2026-04-18-ti-library-L0-baseline.md` | #12 | 2026-04-18 |
| L-1 | Makefile graphics-split (core/graphics/menu) | `2026-04-18-ti-library-L1-graphics-split.md` | #22 | 2026-04-18 |
| L-2 | C ABI foundation (`ti_api.h`, stub exports returning ierr=4) | `2026-04-18-ti-library-L2-c-abi-foundation.md` | #28 | 2026-04-18 |
| L-3 | Parameter registry + real `ti_init/run/get_state/finalize` | `2026-04-18-ti-library-L3-param-registry.md` | #34 | 2026-04-18 |
| L-4 | `libtiapi.so` shared-library build + PIC variants | `2026-04-18-ti-library-L4-shared-lib-build.md` | #41 | 2026-04-18 |
| L-5 | `python/tilib/` ctypes wrapper (`TiLib`, `TiState`, errors) | `2026-04-18-ti-library-L5-python-wrapper.md` | #47 | 2026-04-18 |
| L-6 | 4-layer test suite wired into `run_tests.sh` | `2026-04-18-ti-library-L6-test-4layers.md` | #57 | 2026-04-18 |
| L-7 | Library documentation (this doc, README, examples, CHANGELOG) | `2026-04-18-ti-library-L7-docs.md` | this PR | 2026-04-18 |

## Acceptance criteria status

Mirrors the tr spec's §12.2 for the TI module:

| Criterion | Sub-phase | How to verify |
|---|---|---|
| `libtiapi.so` generated | L-4 | `ls ti/libtiapi.so && file ti/libtiapi.so` |
| `import tilib` works | L-5 | `python3 -c "from tilib import TiLib"` |
| Layer 1 equivalence PASS | L-6 | `test_run/run_tests.sh tilib_equivalence` |
| Layer 2 C ABI PASS | L-6 | `test_run/run_tests.sh tilib_c_abi` |
| Layer 3 Python wrapper PASS | L-6 | `test_run/run_tests.sh tilib_ffi tilib_wrapper` |
| Layer 4 sweep smoke PASS | L-6 | `test_run/run_tests.sh tilib_sweep` |
| `ti` numerics match Phase 0 | L-0..L-6 | `test_run/run_tests.sh ti_min ti_ar ti_w` |
| `python/tilib/README.md` with examples | L-7 | visual review + `python3 -m py_compile examples/*.py` |
| `run_tests.sh` tilib_* wired | L-6 | `grep tilib_ test_run/test_definitions.conf` |

## Known gaps at L-7 merge

- `libtiapi.so` Makefile target lives on `feature/ti-library-L4-
  shared-lib`; it is not yet merged into `ti/Makefile` on `develop`
  at the time of this L-7 PR. The README documents the gap and the
  wrapper + examples degrade gracefully when the library is absent.
- String parameters (`KID_NS`, ...) remain outside the float-only
  C ABI. The Ar fixture works around this by setting `NPA[3]=18`
  and relying on `tiinit.f90` to re-derive `KID_NS(3)='Ar'`.
- `DN0`, `DT0`, `DR0`, `DRS`, `DN0_NS[i]` are namelist keys not yet
  in `ti_param_registry.f90`; the L-6 fixtures list them under
  `UNREGISTERED_KEYS` and fall back to `ti_init` defaults.

## References

- Design spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md`
  (TI follows the same pattern; no separate TI spec)
- User README: `python/tilib/README.md`
- Phase plans: `docs/superpowers/plans/2026-04-18-ti-library-L*.md`
- tr counterpart: `docs/tr-library/architecture.md`
- Changelog: top-level `CHANGELOG.md`
