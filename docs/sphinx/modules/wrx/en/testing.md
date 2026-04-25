# Testing

The `wrx` library ships with **four layers** of regression tests.

## Roles of the four layers

| Layer | Target | What it verifies | Tolerance |
|---|---|---|---|
| **Layer 1** | `wrxlib_equivalence` | `libwrxapi.so` outputs match the Phase-0 `wrx2` baselines exactly | **1e-10** (mandatory) |
| **Layer 2** | `wrxlib_c_abi`      | The 5 C-ABI functions return correct `ierr` | — |
| **Layer 3** | `wrxlib_ffi`, `wrxlib_wrapper` | ctypes structures, lifecycle | — |
| **Layer 4** | `wrxlib_sweep`     | Parameter-scan smoke | — |

## How to run

### One at a time

```bash
bash test_run/run_tests.sh wrxlib_equivalence
bash test_run/run_tests.sh wrxlib_c_abi
bash test_run/run_tests.sh wrxlib_ffi
bash test_run/run_tests.sh wrxlib_wrapper
bash test_run/run_tests.sh wrxlib_sweep
```

### All at once (pytest direct)

```bash
cd python/wrxlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

## What Layer 1 (the equivalence test) does

`wrxlib_equivalence` performs:

1. Load `libwrxapi.so` via `Wrxlib()`
2. Push parameters (including beam shape) from a Phase-0 fixture using
   `set_param`
3. Run beam tracing with `wrx.run(nray_request)`
4. Dump JSON via `WrxState.to_dict()`
5. Diff against `test_run/baselines/<case>/metrics.json` (tolerance
   `1e-10`)

It checks that `wrx2` and `libwrxapi.so` agree to 10 decimal places.

## Test challenges specific to beam tracing

`wrx` is more numerically sensitive than `wr` (because it evolves the
curvature tensor in time). Watch out for:

- **Initial beam width near zero**: setting `RBRADAIN` to something like
  `1e-6` should reproduce `wr` almost exactly, but the numerical
  integration might not match `wr` to full precision.
- **Numerical instability for diverging beams**: if `RCURVAIN` is set to
  a small positive value (diverging), the beam blows up rapidly and
  may exit the computational domain. The tests use fixed fixture
  values to avoid this.

## Useful files

- `python/wrxlib/tests/test_equivalence.py` — Layer 1
- `python/wrxlib/tests/test_wrxlib.py` — Layer 3, high level
- `python/wrxlib/tests/test_ffi.py` — Layer 3, low level
- `python/wrxlib/tests/test_sweep.py` — Layer 4

## Relationship to CI

CI runs with `--forked --timeout=120 --timeout-method=signal`.

```{important}
**Do not bypass the equivalence test with `@pytest.mark.skip`.** If you
cannot fix the failure, mark it with
`@pytest.mark.xfail(strict=True, reason="#<issue>")` and link the issue.
```
