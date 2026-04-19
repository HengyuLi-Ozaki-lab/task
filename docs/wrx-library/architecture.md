# TASK/WRX library-ization — architecture

Phase L delivered a shared-library + Python-wrapper alternative to the
traditional `wrx` CLI for the TASK extended ray-tracing module. The
WRX project mirrors the WR Phase L structure (see
`docs/wr-library/architecture.md`); this doc records the WRX-specific
diagram, per-phase status, and the libgrf::grd1d shared-library
limitation that gates `wrx_run` behind `WRX_RUN_OK=1`.

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
   |  python/wrxlib   |  |  <C driver>   |                   |
   |  (ctypes)        |  |  (#include    |                   |
   |                  |  |   wrx_api.h)  |                   |
   |  Wrxlib/WrxState |  +-------+-------+                   |
   |  errors / _ffi   |          |                           |
   +--------+---------+          |                           |
            |                    |                           |
            +----------+---------+                           |
                       |                                     |
                       v                                     v
            +-----------------------+               +----------------+
            |   wrx/libwrxapi.so    |               |   wrx/wrx      |
            |   (shared lib, L-4)   |               |   (CLI binary) |
            |                       |               |                |
            |   5 exported symbols  |               |   menu loop,   |
            |   wrx_init/wrx_run /  |               |   graphics,    |
            |   wrx_set_param /     |               |   file I/O     |
            |   wrx_get_state /     |               +-------+--------+
            |   wrx_finalize        |                       |
            |                       |                       |
            |   * wrx_run gated:    |                       |
            |     libgrf::grd1d     |                       |
            |     unresolved (see   |                       |
            |     limitation below) |                       |
            +-----------+-----------+                       |
                        |                                   |
                        v                                   v
            +---------------------------------------------------+
            |  Fortran backend  (shared code)                    |
            |                                                    |
            |   wrx_api.f90             wraps WRCOMM globals     |
            |   wrx_param_registry.f90  name -> variable dispatch|
            |   wr_setup / wr_exec      ray-tracing kernels      |
            |   wrcalpwr.f90            calls libgrf::grd1d (!!) |
            |   wrcomm.f90              COMMON/module state      |
            +-------------------+-------------------------------+
                                |
                                v
            +---------------------------------------------------+
            |  Dependency libraries (PIC + non-PIC variants)    |
            |   lib/ libtask_pic.a   pl/ libpl_pic.a            |
            |   eq/ libeq_pic.a      dp/ libdp_pic.a            |
            |   mtxp/ libmtxp_pic.a  ../bpsd/ libbpsd_pic.a     |
            |                                                    |
            |   libgrf:  graphics-only; only statically linkable |
            |            into wrx CLI; not in libwrxapi.so       |
            +---------------------------------------------------+
```

## Layering

| Layer | Artefact | Purpose |
|---|---|---|
| 0. Regression baseline | `test_run/baselines/wrx_*/metrics.json` | Phase 0 ground truth (tol `1e-10`) |
| 1. Fortran backend | `wrx/wrx_api.f90`, `wrx_param_registry.f90`, `wr_setup`, `wr_exec`, ... | Numerics, shared with `wrx` binary |
| 2. C ABI | `wrx/wrx_api.h` + BIND(C) exports in `wrx_api.f90` | 5 functions, stable contract |
| 3. Shared library | `wrx/libwrxapi.so` | `make -C wrx libwrxapi.so`, links `lib*_pic.a` (no `libgrf`) |
| 4. Python FFI | `python/wrxlib/_ffi.py` | `ctypes` layout mirror of `wrx_state_t` |
| 5. High-level wrapper | `python/wrxlib/wrxlib.py`, `state.py`, `errors.py` | Context manager + dataclass |
| 6. User scripts | `python/wrxlib/examples/*.py`, user notebooks | |

### 5 C ABI entry points

From `wrx/wrx_api.h`:

```c
int wrx_init(void);
int wrx_run(int nstpmax);
int wrx_set_param(const char *name, double value);
int wrx_get_state(wrx_state_t *state);
int wrx_finalize(void);
```

Return codes (`enum wrx_error`):

| code | meaning | Python exception |
|---|---|---|
| 0 | OK | — |
| 1 | invalid name / value | `WrxlibParamError` |
| 2 | not initialised | `WrxlibStateError` |
| 3 | calculation failed (`wr_setup`/`wr_exec`/`wrx_get_state`) | `WrxlibRunError` |
| 4 | not implemented (legacy L-2 stub; no longer returned) | `WrxlibNotImplementedError` |

`wrx_state_t` carries two runtime dimensions (`nraymax`, `nsamax`)
bounded by `WRX_MAX_NRAYMAX=100` and `WRX_MAX_NSAMAX=8`. It includes
six int scalars (`nraymax`, `nstpmax`, `nsamax`, `nsmax`, `modelg`,
`mdlwrq`), one double scalar (`pwr_tot`), one `[NRAYMAX]` int array
(`nstpmax_nray`), one `[NRAYMAX]` double array (`pwr_nray`), one
`[NSAMAX]` double array (`pwr_nsa`), one
`pwr_nsa_nray[NRAYMAX][NSAMAX]` 2-D matrix (C row-major == Fortran
`(NSAMAX, NRAYMAX)` column-major byte-for-byte), and four `[NSAMAX]`
peak arrays (`pos_pwrmax_rs_nsa`, `pwrmax_rs_nsa`,
`pos_pwrmax_rl_nsa`, `pwrmax_rl_nsa`) — `_rs` is short-path /
resonance absorption, `_rl` is long-path / Landau absorption.

### Fortran backend

- `wrx_api.f90` owns the BIND(C) wrappers. Each function is a thin
  shim that marshals C arguments into the existing Fortran entry
  points (`pl_init / EQINIT / dp_init / wr_init`; `wr_prep +
  wr_allocate + wr_setup + wr_exec`; `wr_deallocate`) and maps
  Fortran ierr to the C `enum wrx_error`.
- `wrx_param_registry.f90` implements a hand-written `SELECT CASE`
  dispatch (~70 cases covering ~120 settable variables) mapping
  `"NAME"` or `"NAME[idx]"` strings to WRCOMM / WRCOMM_PARM / PLCOMM
  / DPCOMM module variables. Extending the registry is the **only**
  code change needed to expose new parameters.
- Kernel code (`wr_setup`, `wr_exec`, `wrsub`, `wrdisp`,
  `wrcalpwr`, ...) is unchanged and shared with the `wrx` binary.

### Python wrapper

- `wrxlib._ffi.WrxStateC` mirrors `wrx_state_t` byte-for-byte (padded
  to `WRX_MAX_NRAYMAX=100`, `WRX_MAX_NSAMAX=8`). The C
  `pwr_nsa_nray[NRAYMAX][NSAMAX]` and the Fortran
  `pwr_nsa_nray(NSAMAX, NRAYMAX)` are the same bytes; only the index
  order differs.
- `wrxlib._ffi.load_library` resolves the shared library via
  `WRXLIB_PATH` → `wrx/libwrxapi.so` → `lib/libwrxapi.so` and uses
  `RTLD_LAZY` so dangling graphics references never block loading
  (relevant to the `libgrf::grd1d` limitation below).
- `wrxlib.Wrxlib` is a context manager: `__init__` calls `wrx_init`,
  `__exit__` / `close()` calls `wrx_finalize`. All 5 entry points
  map 1:1 to methods.
- `wrxlib.WrxState` is a `@dataclass` snapshot; `to_dict()` is
  JSON-serialisable.

## libgrf::grd1d limitation (critical, gates `wrx_run`)

### Symptom

Calling `Wrxlib.run()` (i.e. dispatching the C `wrx_run` entry point
through `libwrxapi.so`) may segfault inside `wrcalpwr.f90` when
control reaches the `grd1d` graphics call. This is **not** caught by
ctypes; the Python interpreter crashes with SIGSEGV.

The C-side smoke test `wrx/tests/c_abi/test_run_so.c` (Layer 2 dlopen
path) exhibits the same crash and accordingly skips `wrx_run`. The
statically-linked C harness `test_run.c` (Layer 2 static path) and
the `wrx` CLI binary itself both work because they link `libgrf.a`
directly.

### Root cause

`wrcalpwr.f90` (a kernel routine that emits a 1-D plot of the
power-deposition profile) makes an unconditional call to
`libgrf::grd1d`. `libgrf` is the TASK Fortran-90 graphics archive; it
depends transitively on PGPlot and on its own COMMON/save state.

The L-1 Makefile split (PR #25) deliberately excluded the
`graphics-only` SRCS group from `libwrxapi.so`. `wrcalpwr.f90` is a
**core** routine — it lives in the kernel SRCS group and is
unavoidably part of the shared-library build — but its `grd1d` call
target is *only* available from the `libgrf.a` archive. The L-4
build (PR #52) consequently produces a `libwrxapi.so` with an
unresolved symbol that is hidden from `dlopen` by `RTLD_LAZY` but
manifests as a segfault the first time the symbol is touched (i.e.
when `wrcalpwr` runs after `wrx_setup`/`wrx_exec`).

### Mitigation in this Phase L

Rather than carry `libgrf` (and its PGPlot dependency) into the
shared-library build — which would defeat the L-1 graphics split —
Phase L uses a runtime gate:

- **Test gate**: every `.run()`-dependent test class checks
  `os.environ.get("WRX_RUN_OK") == "1"` and uses
  `@unittest.skipUnless`. Affected tests:
  - `python/wrxlib/tests/test_wrxlib.py::TestWrxlibRun`
  - `python/wrxlib/tests/test_equivalence.py` (entire module)
  - `python/wrxlib/tests/test_sweep.py` (entire module)
  - `wrx/tests/c_abi/test_run_so.c` (skips `wrx_run` calls)
- **Test-suite registration**: `wrxlib_equivalence` and
  `wrxlib_sweep` in `test_run/test_definitions.conf` are documented
  as "WRX_RUN_OK gated".
- **Wrapper docs**: `Wrxlib.run` docstring carries a `.. warning::`
  pointing at the limitation. README has a dedicated "WRX_RUN_OK
  gate" section near the top.
- **Examples**: `examples/quickstart.py`, `parameter_sweep.py`, and
  `state_dump.py` all support `--dry-run` so users can validate
  their environment without invoking the FFI; the docstrings
  prominently mention the `WRX_RUN_OK=1` requirement.

### Remediation roadmap (post-Phase-L)

Three options, ordered by intrusiveness:

1. **Stub `grd1d` symbol** in a tiny `wrx/wrx_grd1d_stub.f90` linked
   into `libwrxapi.so`. Zero-cost runtime no-op when graphics is
   disabled. Recommended next step.
2. **Conditionalise `wrcalpwr`** with a runtime mode flag (`MDLWRG ==
   0` skips the `grd1d` call). Requires touching kernel source so
   coordinate with the WR module (`wr_iter_lhcd` may rely on the
   plot side-effect for diagnostics).
3. **Add a PIC `libgrf_pic.a`** (matching the L-1 PIC archive
   pattern) and link it into `libwrxapi.so`. Pulls in PGPlot at
   runtime; defeats the graphics split but is the most faithful
   mirror of the CLI behaviour.

Option 1 is preferred and tracked as a follow-up issue.

## Phase L completion matrix

| Phase | Deliverable | Plan | Merge PR | Date |
|---|---|---|---|---|
| L-0 | Phase 0 regression baselines (`wrx_iter01`) | `2026-04-18-wrx-library-L0-baseline.md` | #16 | 2026-04-18 |
| L-1 | Makefile graphics split | `2026-04-18-wrx-library-L1-graphics-split.md` | #25 | 2026-04-18 |
| L-2 | C ABI foundation (`wrx_api.h`, stub exports returning ierr=4) | `2026-04-18-wrx-library-L2-c-abi-foundation.md` | #31 | 2026-04-18 |
| L-3 | Parameter registry + real `wrx_init/run/get_state/finalize` | `2026-04-18-wrx-library-L3-param-registry.md` | #38 | 2026-04-18 |
| L-4 | `libwrxapi.so` shared-library build + PIC variants | `2026-04-18-wrx-library-L4-shared-lib-build.md` | #52 | 2026-04-18 |
| L-5 | `python/wrxlib/` ctypes wrapper (`Wrxlib`, `WrxState`, errors) | `2026-04-18-wrx-library-L5-python-wrapper.md` | #59 | 2026-04-18 |
| L-6 | 4-layer test suite wired into `run_tests.sh` | `2026-04-18-wrx-library-L6-test-4layers.md` | #67 | 2026-04-18 |
| L-7 | Library documentation (this doc, README, examples, CHANGELOG) | `2026-04-18-wrx-library-L7-docs.md` | this PR | 2026-04-19 |

## Acceptance criteria status

Mirrors the tr spec's §12.2 for the WRX module:

| Criterion | Sub-phase | How to verify |
|---|---|---|
| `libwrxapi.so` generated | L-4 | `ls wrx/libwrxapi.so && file wrx/libwrxapi.so` |
| `import wrxlib` works | L-5 | `python3 -c "from wrxlib import Wrxlib"` |
| Layer 1 equivalence PASS | L-6 | `WRX_RUN_OK=1 test_run/run_tests.sh wrxlib_equivalence` |
| Layer 2 C ABI PASS | L-6 | `test_run/run_tests.sh wrxlib_c_abi` |
| Layer 3 Python wrapper PASS | L-6 | `test_run/run_tests.sh wrxlib_ffi wrxlib_wrapper` |
| Layer 4 sweep smoke PASS | L-6 | `WRX_RUN_OK=1 test_run/run_tests.sh wrxlib_sweep` |
| `wrx` numerics match Phase 0 | L-0..L-6 | `test_run/run_tests.sh wrx_iter01` |
| `python/wrxlib/README.md` with examples | L-7 | visual review + `python3 -m py_compile examples/*.py` |
| `run_tests.sh` wrxlib_* wired | L-6 | `grep wrxlib_ test_run/test_definitions.conf` |

## Known limitations

- **`wrx_run` segfaults on the shared build (libgrf::grd1d).** See
  the dedicated section above. Tests gate behind `WRX_RUN_OK=1`.
  Remediation tracked as a Phase L follow-up.
- **Single instance per process.** WRX's `wrcomm` module holds
  COMMON blocks plus SAVE allocation flags. Two concurrent
  `Wrxlib()` handles in the same process share state. Use
  `multiprocessing` for parallel sweeps — each worker gets its own
  `libwrxapi.so` state.
- **Beam tracing (`mode_beam /= 0`) outputs are not exposed through
  `wrx_get_state`.** The solver runs, but only ray-tracing
  per-species power-deposition outputs are surfaced.
- **Input scalars (`RFIN`, `RPIN`, ...) are not echoed in
  `wrx_get_state`.** Use `set_param` round-trip for confirmation;
  reading them back is a future-phase extension.
- **String parameters not yet wired** — no character-valued
  namelist keys are currently registered (design spec §4.3
  deferral).

## References

- Design spec: `docs/superpowers/specs/2026-04-17-tr-library-design.md`
  (WRX follows the same pattern; no separate WRX spec)
- User README: `python/wrxlib/README.md`
- Phase plans: `docs/superpowers/plans/2026-04-18-wrx-library-L*.md`
- wr counterpart: `docs/wr-library/architecture.md`
- tr counterpart: `docs/tr-library/architecture.md`
- Changelog: top-level `CHANGELOG.md`
