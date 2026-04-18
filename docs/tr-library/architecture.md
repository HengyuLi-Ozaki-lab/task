# TASK/TR library-ization — architecture

Phase L delivered a shared-library + Python-wrapper alternative to the
traditional `tr2` CLI. This doc diagrams the moving pieces and tracks
per-phase status.

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
   |  python/trlib    |  |  <C driver>   |                   |
   |  (ctypes)        |  |  (#include    |                   |
   |                  |  |   tr_api.h)   |                   |
   |  Trlib / TrState |  +-------+-------+                   |
   |  errors / _ffi   |          |                           |
   +--------+---------+          |                           |
            |                    |                           |
            +----------+---------+                           |
                       |                                     |
                       v                                     v
            +-----------------------+               +----------------+
            |   tr/libtrapi.so      |               |   tr/tr2       |
            |   (shared lib)        |               |   (CLI binary) |
            |                       |               |                |
            |   5 exported symbols  |               |   menu loop,   |
            |   tr_init / tr_run /  |               |   graphics,    |
            |   tr_set_param /      |               |   file I/O     |
            |   tr_get_state /      |               +-------+--------+
            |   tr_finalize         |                       |
            +-----------+-----------+                       |
                        |                                   |
                        v                                   v
            +---------------------------------------------------+
            |  Fortran backend  (shared code)                    |
            |                                                    |
            |   tr_api.f90       wraps TRCOMM globals            |
            |   tr_param_registry.f90  name -> variable dispatch |
            |   trloop / trcalc / ...  time-advance kernels      |
            |   trcomm.f90 + submodules  COMMON-block state      |
            +-------------------+-------------------------------+
                                |
                                v
            +---------------------------------------------------+
            |  Dependency libraries (PIC + non-PIC variants)    |
            |   lib/ plfile_pic.a   pl/plcomm_pic.a             |
            |   eq/libeq_pic.a      ob/libob_pic.a              |
            |   mtxp/libmtxp_pic.a  bpsd/libbpsd_pic.a ...      |
            +---------------------------------------------------+
```

## Layering

| Layer | Artefact | Purpose |
|---|---|---|
| 0. Regression baseline | `test_run/baselines/tr_*.json` | Phase 0 ground truth (tol `1e-10`) |
| 1. Fortran backend | `tr/tr_api.f90`, `tr_param_registry.f90`, `trloop`, `trcalc`, ... | Numerics, shared with `tr2` |
| 2. C ABI | `tr/tr_api.h` + BIND(C) exports in `tr_api.f90` | 5 functions, stable contract |
| 3. Shared library | `tr/libtrapi.so` | `make -C tr libtrapi.so`, links `lib*_pic.a` |
| 4. Python FFI | `python/trlib/_ffi.py` | `ctypes` layout mirror of `tr_state_t` |
| 5. High-level wrapper | `python/trlib/trlib.py`, `state.py`, `errors.py` | Context manager + dataclass |
| 6. User scripts | `python/trlib/examples/*.py`, user notebooks | |

### 5 C ABI entry points

From `tr/tr_api.h`:

```c
int tr_init(void);
int tr_run(int ntmax);
int tr_set_param(const char *name, double value);
int tr_get_state(tr_state_t *state);
int tr_finalize(void);
```

Return codes (`enum tr_error`):

| code | meaning | Python exception |
|---|---|---|
| 0 | OK | — |
| 1 | invalid name / value | `TrlibParamError` |
| 2 | not initialised | `TrlibStateError` |
| 3 | calculation failed | `TrlibRunError` |
| 4 | not implemented (Phase L-2 stub) | `TrlibNotImplementedError` |

### Fortran backend

- `tr_api.f90` owns the BIND(C) wrappers. Each function is a thin
  shim that marshals C arguments into the existing Fortran entry
  points and maps Fortran ierr to the C `enum tr_error`.
- `tr_param_registry.f90` implements a hand-written `SELECT CASE`
  dispatch (~38 cases) mapping `"NAME"` or `"NAME[idx]"` strings to
  TRCOMM module variables. Extending the registry is the **only**
  code change needed to expose new parameters.
- Kernel code (`trloop`, `trcalc`, `trbpsd`, ...) is unchanged and
  shared with the `tr2` binary.

### Python wrapper

- `trlib._ffi.TrStateC` mirrors `tr_state_t` byte-for-byte (padded to
  `TR_MAX_NRMAX=500`, `TR_MAX_NSMAX=8`).
- `trlib._ffi.load_library` resolves the shared library via
  `TRLIB_PATH` → `tr/libtrapi.so` → `lib/libtrapi.so` and uses
  `RTLD_LAZy` so dangling graphics references never block loading.
- `trlib.Trlib` is a context manager: `__enter__` calls `tr_init`,
  `__exit__` calls `tr_finalize`. All 5 entry points map 1:1 to
  methods.
- `trlib.TrState` is a `@dataclass` snapshot; `to_dict()` is
  JSON-serialisable and matches the Phase 0 baseline layout so
  `compare_metrics.py` can diff wrapper output against `tr2` runs.

## Phase L completion matrix

| Phase | Deliverable | Plan | Merge PR | Date |
|---|---|---|---|---|
| L-0 | Phase 0 regression baselines (`tr_iter01`, `tr_m0904`, `tr_tst2`) | `2026-04-18-tr-library-L0-baseline.md` | #2 | 2026-04-18 |
| L-1 | Makefile graphics-split (`libtrgrf` separated) | `2026-04-18-tr-library-L1-graphics-split.md` | #21 | 2026-04-18 |
| L-2 | C ABI foundation (`tr_api.h`, stub exports returning ierr=4) | `2026-04-18-tr-library-L2-c-abi-foundation.md` | #27 | 2026-04-18 |
| L-3 | Parameter registry + real `tr_init/run/get_state/finalize` | `2026-04-18-tr-library-L3-param-registry.md` | #33 | 2026-04-18 |
| L-4 | `libtrapi.so` shared-library build + PIC variants | `2026-04-18-tr-library-L4-shared-lib-build.md` | #35 | 2026-04-18 |
| L-5 | `python/trlib/` ctypes wrapper (`Trlib`, `TrState`, errors) | `2026-04-18-tr-library-L5-python-wrapper.md` | #44 | 2026-04-18 |
| L-6 | 4-layer test suite wired into `run_tests.sh` | `2026-04-18-tr-library-L6-test-4layers.md` | #53 | 2026-04-18 |
| L-7 | Library documentation (this doc, README, examples, CHANGELOG) | `2026-04-18-tr-library-L7-docs.md` | this PR | 2026-04-18 |

## Acceptance criteria status (design spec §12.2)

| Criterion | Sub-phase | How to verify |
|---|---|---|
| `libtrapi.so` generated | L-4 | `ls tr/libtrapi.so && file tr/libtrapi.so` |
| `import trlib` works | L-5 | `python3 -c "from trlib import Trlib"` |
| Layer 1 equivalence 3 cases PASS | L-6 | `test_run/run_tests.sh trlib_equivalence` |
| Layer 2 C ABI PASS | L-6 | `test_run/run_tests.sh trlib_c_abi` |
| Layer 3 Python wrapper PASS | L-6 | `test_run/run_tests.sh trlib_ffi trlib_wrapper` |
| Layer 4 sweep smoke PASS | L-6 | `test_run/run_tests.sh trlib_sweep` |
| `tr2` numerics match Phase 0 | L-0..L-6 | `test_run/run_tests.sh tr_iter01 tr_m0904 tr_tst2` |
| `python/trlib/README.md` with examples | L-7 | visual review + `python3 -m py_compile examples/*.py` |
| `run_tests.sh` trlib_* wired | L-6 | `grep trlib_ test_run/test_definitions.conf` |

## References

- Design spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md`
- User README: `python/trlib/README.md`
- Phase plans: `docs/superpowers/plans/2026-04-18-tr-library-L*.md`
- Changelog: top-level `CHANGELOG.md`
