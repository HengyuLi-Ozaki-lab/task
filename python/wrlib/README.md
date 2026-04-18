# wrlib - Python wrapper for TASK/WR

`wrlib` is a ctypes-based Python binding for `wr/libwrapi.so` (Phase
L-4 product). It uses only the Python standard library (`ctypes`,
`dataclasses`, `pathlib`, `os`). `numpy` is optional and not required.

See `docs/superpowers/plans/2026-04-18-wr-library-L5-python-wrapper.md`
for the design.

## Architecture

Two layers:

* `wrlib._ffi` - low-level ctypes binding. Exposes `WrStateC`
  (mirror of `wr_state_t`) and `load_library()` which resolves and
  `CDLL`-loads `libwrapi.so` with function prototypes attached.
* `wrlib.Wrlib` - high-level context manager with `init / run /
  set_param / get_state / finalize` methods and `WrState` dataclass
  output.

## Install / Build prerequisites

1. Build the shared library:

   ```bash
   cd wr && make libwrapi.so
   ```

   This produces `wr/libwrapi.so` and its 5 exported C symbols
   (`wr_init`, `wr_run`, `wr_set_param`, `wr_get_state`,
   `wr_finalize`).

2. Add the `python/` directory to `PYTHONPATH`:

   ```bash
   export PYTHONPATH=$(pwd)/python:$PYTHONPATH
   ```

## Library-path lookup

When you do `Wrlib()` (no arguments) the loader searches in order:

1. `WRLIB_PATH` environment variable, if set
2. `<repo>/wr/libwrapi.so` (default build location)
3. `<repo>/lib/libwrapi.so` (install-style location)

Override by passing `Wrlib(lib_path="/custom/path/libwrapi.so")`.

## Quick example

```python
from wrlib import Wrlib

with Wrlib() as wr:
    wr.set_params(RR=3.0, BB=3.5)    # scalar params via kwargs
    wr.set_param("PN[1]", 0.7)        # array element by name
    wr.run(nray_request=0)            # 0 keeps namelist NRAYMAX
    state = wr.get_state()

print("pwrmax_rs =", state.scalars["pwrmax_rs"])
print("first ray end =", state.rays_end[0])

# JSON-serialisable dict in Phase-0 baseline format:
import json
print(json.dumps(state.to_dict())[:200])
```

## Errors

All exceptions derive from `wrlib.WrlibError`. Specific subclasses
match the C ABI `enum wr_error` in `wr/wr_api.h`:

| `ierr` | exception | meaning |
|---|---|---|
| 0 | - | success |
| 1 | `WrlibParamError` | invalid parameter name / value |
| 2 | `WrlibStateError` | library not initialised |
| 3 | `WrlibRunError` | calculation / get_state failed |
| 4 | `WrlibNotImplementedError` | stub; not implemented yet |

Aliases with the `WrLib...` capitalisation (`WrLibInvalidParam`,
`WrLibNotInitialized`, `WrLibCalculationFailed`,
`WrLibNotImplemented`) are also exported for callers that prefer the
spec naming.

## `set_params` vs `set_param`

`set_params(**kwargs)` is **scalar-only** because Python keyword
argument names cannot contain `[` or `]`. For array elements call
`set_param()` directly:

```python
wr.set_params(RR=3.0, BB=3.5)
wr.set_param("PN[1]", 0.7)      # array element
```

Keys containing `__` are rejected in `set_params` as a common
array-syntax mistake.

## State shape

`WrState` carries three runtime dimensions and the associated arrays:

* `nraymax` - number of rays actually in use
  (`pos_pwrmax_rs_nray`, `pwrmax_rs_nray`, `pos_pwrmax_rl_nray`,
  `pwrmax_rl_nray`, `nstp_end`, `rays_end`)
* `nrsmax` - minor-radius profile length (`pos_nrs`, `pwr_nrs`)
* `nrlmax` - major-radius profile length (`pos_nrl`, `pwr_nrl`)

`rays_end[i]` always has 9 elements (the `RAYS(0:NEQ, ...)` columns)
regardless of `nraymax`; this matches the C ABI fixed-width layout.

## Running the tests

```bash
cd python/wrlib/tests
python3 -m unittest discover -v
```

Tests that require `libwrapi.so` are skipped when it hasn't been
built yet; the remaining tests (ctypes layout, error wiring,
`WrState.from_c`, `to_dict` shape) always run.
