# wrxlib - Python wrapper for TASK/WRX

`wrxlib` is a ctypes-based Python binding for `wrx/libwrxapi.so`
(Phase L-4 product). It uses only the Python standard library
(`ctypes`, `dataclasses`, `pathlib`, `os`). `numpy` is optional and
not required.

Sister package to [`wrlib`](../wrlib/). They share the same two-layer
architecture but bind to different shared libraries (`wrx_*` vs
`wr_*` C symbols). Both can coexist in the same Python process.

See `docs/superpowers/plans/2026-04-18-wrx-library-L5-python-wrapper.md`
for the design.

## Architecture

Two layers:

* `wrxlib._ffi` - low-level ctypes binding. Exposes `WrxStateC`
  (mirror of `wrx_state_t`) and `load_library()` which resolves and
  `CDLL`-loads `libwrxapi.so` with function prototypes attached.
* `wrxlib.Wrxlib` - high-level context manager with `init / run /
  set_param / get_state / finalize` methods and `WrxState` dataclass
  output.

## Install / Build prerequisites

1. Build the shared library:

   ```bash
   cd wrx && make libwrxapi.so
   ```

   This produces `wrx/libwrxapi.so` and its 5 exported C symbols
   (`wrx_init`, `wrx_run`, `wrx_set_param`, `wrx_get_state`,
   `wrx_finalize`).

2. Add the `python/` directory to `PYTHONPATH`:

   ```bash
   export PYTHONPATH=$(pwd)/python:$PYTHONPATH
   ```

## Library-path lookup

When you do `Wrxlib()` (no arguments) the loader searches in order:

1. `WRXLIB_PATH` environment variable, if set
2. `<repo>/wrx/libwrxapi.so` (default build location)
3. `<repo>/lib/libwrxapi.so` (install-style location)

Override by passing `Wrxlib(lib_path="/custom/path/libwrxapi.so")`.

## Quick example

```python
from wrxlib import Wrxlib

with Wrxlib() as wrx:
    wrx.set_params(MODELG=2, RR=6.2, BB=5.3, NSMAX=2, NRAYMAX=1)
    wrx.set_param("RFIN[1]", 170.0e3)      # array element by name
    wrx.run(nray_request=0)                # WARNING: see Known limitation
    state = wrx.get_state()

print("pwr_tot =", state.scalars["pwr_tot"])
print("nray, nsa =", state.nraymax, state.nsamax)
print("rs pwrmax per species =", state.pwrmax_rs_nsa)

# JSON-serialisable dict for L-6 regression diffs:
import json
print(json.dumps(state.to_dict())[:200])
```

## Errors

All exceptions derive from `wrxlib.WrxlibError`. Specific subclasses
match the C ABI `enum wrx_error` in `wrx/wrx_api.h`:

| `ierr` | exception | meaning |
|---|---|---|
| 0 | - | success |
| 1 | `WrxlibParamError` | invalid parameter name / value |
| 2 | `WrxlibStateError` | library not initialised |
| 3 | `WrxlibRunError` | calculation / get_state failed |
| 4 | `WrxlibNotImplementedError` | stub; not implemented yet |

Aliases with the `WrxLib...` capitalisation (`WrxLibInvalidParam`,
`WrxLibNotInitialized`, `WrxLibCalculationFailed`,
`WrxLibNotImplemented`) are also exported for callers that prefer the
spec naming. `raise_for_rc` is an alias of `raise_for_ierr` matching
the `fplib` / `trlib` naming.

## `set_params` vs `set_param`

`set_params(**kwargs)` is **scalar-only** because Python keyword
argument names cannot contain `[` or `]`. For array elements call
`set_param()` directly:

```python
wrx.set_params(RR=6.2, BB=5.3)
wrx.set_param("RFIN[1]", 170.0e3)   # array element
```

Keys containing `__` are rejected in `set_params` as a common
array-syntax mistake.

## State shape

`WrxState` carries two runtime dimensions plus per-species and
per-ray arrays:

* `nraymax` - number of rays actually in use
  (`nstp_end`, `pwr_nray`, `pwr_nsa_nray[i]`)
* `nsamax`  - number of plasma species in use
  (`pwr_nsa`, `pos_pwrmax_rs_nsa`, `pwrmax_rs_nsa`,
  `pos_pwrmax_rl_nsa`, `pwrmax_rl_nsa`)
* scalars: `pwr_tot` (total absorbed power)

`pwr_nsa_nray[i]` always has `nsamax` elements; `to_dict()` slices
both axes to the active runtime size so zero-padded struct tails
never leak into the Python view.

## Known limitation: `wrx_run` in the shared build

The L-4 build of `libwrxapi.so` retains a reference to
`libgrf::grd1d` through `wrcalpwr.f90` that cannot be fully satisfied
at load time through the regular `.so` symbol graph. As a result:

* `wrx_init`, `wrx_set_param`, `wrx_get_state` (before run),
  `wrx_finalize` - work reliably from the `.so`.
* **`wrx_run`** may segfault inside the shared library when
  `wrcalpwr` dispatches to `grd1d`.

The C dlopen smoke test (`wrx/tests/c_abi/test_run_so.c`) skips
`wrx_run` for the same reason. `python/wrxlib/tests/test_wrxlib.py`
follows that convention: the `wrx_run`-dependent test (
`TestWrxlibRun`) is gated behind the `WRX_RUN_OK=1` environment
variable. Set it only if your build has patched the `grd1d`
dependency:

```bash
WRX_RUN_OK=1 python3 -m unittest python.wrxlib.tests.test_wrxlib -v
```

If you need the full `wrx_run` pipeline today, use the Layer-1 driver
(`wrx/wrxregress`) or the Layer-2 C harness that statically links
against `libgrf.a`.

## Running the tests

```bash
cd python/wrxlib/tests
python3 -m unittest discover -v
```

Or from the repo root:

```bash
python3 -m unittest discover python/wrxlib/tests -v
```

Tests that require `libwrxapi.so` are skipped automatically when it
hasn't been built yet; the remaining tests (ctypes layout, error
wiring, `WrxState.from_c`, `to_dict` shape) always run.

## Independence from `wrlib`

`wrlib` (sister WR Phase L-5 package) and `wrxlib` use distinct C
symbol prefixes (`wr_*` vs `wrx_*`) and distinct shared libraries
(`libwrapi.so` vs `libwrxapi.so`). They can coexist in the same
Python process:

```python
from wrlib import Wrlib
from wrxlib import Wrxlib
# both can be loaded simultaneously
```
