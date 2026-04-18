# trlib - Python wrapper for TASK/TR

`trlib` is a ctypes-based Python binding for `tr/libtrapi.so` (Phase L-4
product). It uses only the Python standard library (`ctypes`,
`dataclasses`, `pathlib`, `os`). `numpy` is optional and not required.

See `docs/superpowers/specs/2026-04-17-tr-library-design.md` §6 for the
design.

## Architecture

Two layers:

* `trlib._ffi` - low-level ctypes binding. Exposes `TrStateC`
  (mirror of `tr_state_t`) and `load_library()` which resolves and
  `CDLL`-loads `libtrapi.so` with function prototypes attached.
* `trlib.Trlib` - high-level context manager with `init/run/set_param/
  get_state/finalize` methods and `TrState` dataclass output.

## Install / Build prerequisites

1. Build the shared library:

   ```bash
   cd tr && make libtrapi.so
   ```

   This produces `tr/libtrapi.so` and its 5 exported C symbols
   (`tr_init`, `tr_run`, `tr_set_param`, `tr_get_state`, `tr_finalize`).

2. Add the `python/` directory to `PYTHONPATH`:

   ```bash
   export PYTHONPATH=$(pwd)/python:$PYTHONPATH
   ```

## Library-path lookup

When you do `Trlib()` (no arguments) the loader searches in order:

1. `TRLIB_PATH` environment variable, if set
2. `<repo>/tr/libtrapi.so` (default build location)
3. `<repo>/lib/libtrapi.so` (install-style location)

Override by passing `Trlib(lib_path="/custom/path/libtrapi.so")`.

## Quick example

```python
from trlib import Trlib

with Trlib() as tr:
    tr.set_params(RR=7.5, BB=5.3)        # scalar params via kwargs
    tr.set_param("PN[1]", 0.7)            # array element by name
    tr.run(ntmax=100)
    state = tr.get_state()

print("T =", state.scalars["T"])
print("first RT row =", state.RT[0])

# JSON-serialisable dict in Phase-0 baseline format:
import json
print(json.dumps(state.to_dict())[:200])
```

## Errors

All exceptions derive from `trlib.TrlibError`. Specific subclasses
match the C ABI `enum tr_error` in `tr/tr_api.h`:

| `ierr` | exception | meaning |
|---|---|---|
| 0 | - | success |
| 1 | `TrlibParamError` | invalid parameter name / value |
| 2 | `TrlibStateError` | library not initialised |
| 3 | `TrlibRunError` | calculation / get_state failed |
| 4 | `TrlibNotImplementedError` | L-2 stub; not implemented yet |

Aliases with the `TrLib...` capitalisation (`TrLibInvalidParam`,
`TrLibNotInitialized`, `TrLibCalculationFailed`, `TrLibNotImplemented`)
are also exported for callers that prefer the spec naming.

## `set_params` vs `set_param`

`set_params(**kwargs)` is **scalar-only** because Python keyword
argument names cannot contain `[` or `]`. For array elements call
`set_param()` directly:

```python
tr.set_params(RR=3.0, BB=2.0)
tr.set_param("PN[1]", 0.7)      # array element
```

Keys containing `__` are rejected in `set_params` as a common
array-syntax mistake.

## Running the tests

```bash
cd python/trlib/tests
python3 -m unittest discover -v
```

Tests that require `libtrapi.so` are skipped when it hasn't been built
yet; the remaining tests (ctypes layout, error wiring,
`TrState.from_c`, `to_dict` shape) always run.
