# wrlib — Python wrapper for TASK/WR

`wrlib` is a thin `ctypes`-based Python wrapper around
`wr/libwrapi.so`, the in-process shared-library version of the TASK/WR
ray-tracing code. It lets scripts drive WR simulations from Python
without shelling out to the standalone `wr` binary or going through
namelist files.

## Overview

TASK/WR has two user-facing deliverables:

| | Traditional CLI | Library (Phase L) |
|---|---|---|
| Binary | `wr/wr` | `wr/libwrapi.so` |
| Entry | interactive menu | 5 C ABI functions |
| I/O | namelist + ASCII output | in-memory state struct |
| Graphics | PGPlot / Fortran 90 graphics | excluded |
| Python | — | `python/wrlib` |

The C ABI is defined in `wr/wr_api.h`; the Fortran backend
(`wr/wr_api.f90`, `wr/wr_param_registry.f90`) is unchanged Fortran that
is also linked into the `wr` binary. `python/wrlib` only wraps the 5 C
entry points and marshals a `wr_state_t` struct into the pure-Python
`WrState` dataclass.

No third-party dependencies — Python 3.8+ stdlib only (`ctypes`,
`dataclasses`, `pathlib`, `os`). `numpy` is optional.

## Installation

Build the shared library once:

```bash
cd /path/to/task
make -C wr libwrapi.so
```

This produces `wr/libwrapi.so` with 5 exported symbols (`wr_init`,
`wr_run`, `wr_set_param`, `wr_get_state`, `wr_finalize`) plus PIC
variants of the dependent libraries (`lib*_pic.a`). The pre-existing
non-PIC `*.a` archives and the `wr` binary are unchanged.

Put the wrapper on `PYTHONPATH`:

```bash
export PYTHONPATH=/path/to/task/python:$PYTHONPATH
```

Optionally point at a library file outside the repository:

```bash
export WRLIB_PATH=/custom/path/libwrapi.so
```

Library lookup order (first match wins): `WRLIB_PATH` env var,
`<repo>/wr/libwrapi.so`, `<repo>/lib/libwrapi.so`.

## Quick start

```python
from wrlib import Wrlib

with Wrlib() as wr:
    wr.set_params(MODELG=2, RR=6.2, RA=2.0, BB=5.3,
                  NSMAX=2, NRAYMAX=1, NSTPMAX=1000,
                  MDLWRI=101, MDLWRQ=0, SMAX=5.0, DELS=0.05)
    wr.set_param("PA[1]", 2.0);    wr.set_param("PA[2]", 1.0)
    wr.set_param("PZ[1]", 1.0);    wr.set_param("PZ[2]", -1.0)
    wr.set_param("PN[1]", 1.0);    wr.set_param("PN[2]", 1.0)
    wr.set_param("PTPR[1]", 10.0); wr.set_param("PTPP[1]", 10.0)
    wr.set_param("PTPR[2]", 10.0); wr.set_param("PTPP[2]", 10.0)
    wr.set_param("RFIN[1]", 5.0e3)
    wr.set_param("RPIN[1]", 8.0)
    wr.set_param("ANGPHIN[1]", 30.0)
    wr.set_param("UUIN[1]", 1.0)
    wr.set_param("MODEWIN[1]", 1)

    wr.run(nray_request=0)        # 0 keeps namelist NRAYMAX
    state = wr.get_state()

print(f"pwrmax_rs = {state.scalars['pwrmax_rs']:.4g}"
      f" at rho = {state.scalars['pos_pwrmax_rs']:.4g}")
```

See `examples/` for runnable scripts:

- `examples/quickstart.py` — smallest complete run (mirrors `wr_iter_lhcd`)
- `examples/parameter_sweep.py` — 3×3 RFIN × ANGPHIN grid
- `examples/state_dump.py` — single run, full `WrState.to_dict()` as JSON

## API reference

### `Wrlib(lib_path: str | None = None)`

Context manager. `__init__` calls `wr_init`; `__exit__` / `close()`
calls `wr_finalize`. Only one live instance per process is meaningful
(WR backend holds global COMMON-block state).

### `Wrlib.set_param(name, value) -> None`

Set a single parameter. Use `"NAME[i]"` (1-origin) for array elements
(e.g. `"RFIN[1]"`, `"PN[2]"`); Python keyword arguments cannot contain
brackets so array elements must use `set_param`, not `set_params`.

### `Wrlib.set_params(**kwargs) -> None`

Bulk-set **scalar** parameters. Raises `WrlibError` on keys containing
`__` (common array-syntax mistake).

### `Wrlib.run(nray_request: int = 0) -> None`

Execute `wr_setup → wr_exec`. `nray_request > 0` overrides the
namelist `NRAYMAX` before allocation; `nray_request <= 0` keeps
whatever NRAYMAX is currently set.

### `Wrlib.get_state() -> WrState`

Snapshot current WRCOMM dimensions, peak-power scalars, per-ray
end-state, and `[0:nrsmax]` / `[0:nrlmax]` profile arrays into a
`WrState` dataclass. Trailing padding (up to `WR_MAX_NRAYMAX=100`,
`WR_MAX_NRSMAX=200`, `WR_MAX_NRLMAX=400`) is ignored.

### `Wrlib.close() -> None`

Idempotent. The context manager calls this automatically.

## Supported parameters

The registry below reflects `wr/wr_param_registry.f90` at Phase L-3
(~80 names). Add to it by extending that Fortran `SELECT CASE`; no
Python change is required — the wrapper forwards names verbatim.

| Group | Names | Notes |
|---|---|---|
| Geometry / device (plcomm) | `RR`, `RA`, `RB`, `RKAP`, `RDLT`, `BB`, `Q0`, `QA`, `RIP` | scalar doubles |
| Plasma scalars (plcomm) | `NSMAX` | INT cast |
| Plasma per-species (1..NSM) | `PA[i]`, `PZ[i]`, `PN[i]`, `PNS[i]`, `PTPR[i]`, `PTPP[i]`, `PTS[i]`, `PU[i]`, `PUS[i]`, `PZCL[i]` | doubles, 1-origin |
| Profile shape (plcomm) | `PROFN1`, `PROFN2`, `PROFT1`, `PROFT2`, `PROFU1`, `PROFU2`, `RHOMIN`, `QMIN`, `RHOEDG`, `PPN0`, `PTN0`, `RF_PL` | scalars |
| Model switches (plcomm / dpcomm) | `MODELG`, `MODELQ`, `MODEL_PROF`, `MODEL_NPROF`, `MODEFW`, `MODEFR`, `IDEBUG`, `MODELP[i]`, `MODELV[i]`, `NCMIN[i]`, `NCMAX[i]` | INT cast |
| WR control scalars (wrcomm) | `NRAYMAX`, `NSTPMAX`, `NRSMAX`, `NRLMAX`, `LMAXNW`, `mode_beam`, `MDLWRI`, `MDLWRG`, `MDLWRP`, `MDLWRQ`, `MDLWRW`, `MODEW`, `nres_max`, `nres_type`, `mode_wline`, `SMAX`, `DELS`, `UUMIN`, `EPSRAY`, `DELRAY`, `DELDER`, `DELKR`, `EPSNW`, `Rmax_wr`, `Rmin_wr`, `Zmax_wr`, `Zmin_wr`, `pne_threshold`, `bdr_threshold` | mixed int/double |
| WR per-ray initial conditions (wrcomm) | `RFIN[i]`, `RPIN[i]`, `ZPIN[i]`, `PHIIN[i]`, `RKRIN[i]`, `RNZIN[i]`, `RNPHIIN[i]`, `ANGZIN[i]`, `ANGPHIN[i]`, `UUIN[i]`, `MODEWIN[i]`, `RCURVAIN[i]`, `RCURVBIN[i]`, `RBRADAIN[i]`, `RBRADBIN[i]` | 1-origin; MODEWIN INT cast |

Unknown names return ierr=1 (raised as `WrlibParamError`). Out-of-range
indices (`PA[0]` or `PN[NSM+1]`) also return ierr=1.

## `WrState` fields

Matches `wr_state_t` in `wr/wr_api.h`. Full dict layout is available
via `state.to_dict()` (JSON-serialisable; matches the Phase 0 baseline
format produced by `tools/extract_wr_metrics.py` so `compare_metrics.py`
can diff wrapper output against `wr` CLI runs).

| Attribute | Type | Meaning |
|---|---|---|
| `nraymax` | int | rays actually in use |
| `nrsmax` | int | minor-radius profile size actually in use |
| `nrlmax` | int | major-radius profile size actually in use |
| `scalars` | dict[str, float] | global peaks: `pos_pwrmax_rs`, `pwrmax_rs`, `pos_pwrmax_rl`, `pwrmax_rl` |
| `nstp_end` | list[int] | `[nraymax]` end-step index for each ray |
| `pos_pwrmax_rs_nray` | list[float] | `[nraymax]` per-ray peak position (minor radius) |
| `pwrmax_rs_nray` | list[float] | `[nraymax]` per-ray peak value (minor radius) |
| `pos_pwrmax_rl_nray` | list[float] | `[nraymax]` per-ray peak position (major radius) |
| `pwrmax_rl_nray` | list[float] | `[nraymax]` per-ray peak value (major radius) |
| `rays_end` | list[list[float]] | `[nraymax][9]` end-state of each ray (`RAYS(0:NEQ, end, i)`, NEQ=8 ⇒ 9 components) |
| `pos_nrs` / `pwr_nrs` | list[float] | `[nrsmax]` minor-radius deposition profile |
| `pos_nrl` / `pwr_nrl` | list[float] | `[nrlmax]` major-radius deposition profile |

`rays_end[i]` always has 9 elements regardless of `nraymax`; this
matches the C ABI fixed-width layout `rays_end[WR_MAX_NRAYMAX][WR_MAX_NRAY_EQ]`.

## Exceptions

Every `wr_*` return code maps to a concrete subclass of `WrlibError`:

| ierr | class | meaning |
|---|---|---|
| 0 | — | success |
| 1 | `WrlibParamError` | invalid parameter name / index / value |
| 2 | `WrlibStateError` | API call before `wr_init` or after `close` |
| 3 | `WrlibRunError` | calculation (`wr_setup`/`wr_exec`) or `wr_get_state` failed |
| 4 | `WrlibNotImplementedError` | Phase L-2 stub return |

Spec-style aliases (`WrLibInvalidParam`, `WrLibNotInitialized`,
`WrLibCalculationFailed`, `WrLibNotImplemented`) are also exported.

## Migration: `wr` CLI → `wrlib.Wrlib`

| CLI step | `wrlib` equivalent |
|---|---|
| edit `wrparm` namelist | `wr.set_param(...)` / `wr.set_params(...)` |
| menu option `R` (run) | `wr.run(nray_request=...)` |
| inspect output file | `wr.get_state()` / `state.to_dict()` |
| menu `Q` (quit) | exit context manager / `wr.close()` |
| batch parameter sweep | Python `for` loop (see `examples/parameter_sweep.py`) |

The wrapper does **not** wrap graphics, file output, or the
interactive menu — those live in `wr/wr` only.

## Known limitations

- **Single instance per process.** WR backend uses COMMON blocks plus
  module-scope allocation flags. Two concurrent `Wrlib()` instances
  share state; the second `wr_init` resets globals. For parallel
  sweeps use `multiprocessing` — each worker gets its own libwrapi.so
  state.
- **Post-finalize state-reset invariant.** `wr_allocate` uses SAVE
  flags (`INIT`, `NRAYMAX_SAVE`, `NSTPMAX_SAVE`) to skip re-allocation
  on unchanged dimensions. PR #36 (Bugbot HIGH) surfaced that these
  flags were not reset on `wr_finalize`, so a subsequent
  `wr_init → wr_run` cycle would call `wr_deallocate` on already-freed
  arrays and crash. The L-3 fix introduced `wr_reset_alloc_state`
  (called inside `wr_finalize`) and `ALLOCATED()` guards on every
  `DEALLOCATE`. The `wrlib_sweep` Layer-4 test (and
  `wr/tests/c_abi/test_reinit.c`) exercise this invariant; do **not**
  remove the reset hook when extending `wr_finalize`.
- **No graphics, no MPI, no OpenMP API.** Graphics symbols exist but
  are not reachable from the 5 exported entry points; the loader uses
  `RTLD_LAZY` so dangling graphics references never resolve.
- **Beam-tracing (`mode_beam /= 0`) is not exposed through `wr_get_state`.**
  The ray-tracing solver runs, but only ray-tracing outputs are
  surfaced. `RFIN`, `RPIN`, ... inputs are set via `set_param`; echoing
  them back is a future-phase extension.
- **String parameters not yet wired.** Currently-deferred; see
  `docs/superpowers/specs/2026-04-17-tr-library-design.md` §4.3.

## Testing

```bash
cd python/wrlib/tests
python3 -m unittest discover -v
```

Tests that require `libwrapi.so` are skipped when the shared library
is absent; pure-Python tests (ctypes layout, error wiring,
`WrState.from_c`, `to_dict` shape) always run.

The Phase L-6 4-layer suite is wired into
`test_run/test_definitions.conf`:

- `wrlib_c_abi` — Layer 2 C ABI (`make -C wr wr_api_check_all`;
  includes `test_smoke`, `test_param`, `test_run`, `test_reinit`,
  `test_run_so`, `test_negative`)
- `wrlib_ffi`, `wrlib_wrapper` — Layer 3 Python wrapper
- `wrlib_equivalence` — Layer 1 vs Phase 0 baselines (tol `1e-10`)
  for `wr_iter_lhcd`, `wr_test001`, `wr_tst2_ec`
- `wrlib_sweep` — Layer 4 3×3 RFIN × ANGPHIN smoke

## License / contributions

`wrlib` is part of the TASK code and distributed under the repository's
top-level license. Bug reports and PRs are welcome; please keep
wrapper changes minimal — the C ABI is the stable layer, so new
parameters should be added to the Fortran registry first.

## See also

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` — shared
  TR/TI/WR Phase L design (WR follows the same pattern)
- `docs/wr-library/architecture.md` — system diagram and Phase
  completion matrix
- `wr/wr_api.h` — C ABI header
- `wr/wr_param_registry.f90` — parameter-name dispatch table
- `CHANGELOG.md` — per-phase history
