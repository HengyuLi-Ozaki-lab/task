# Testing

The `wr` library ships with a **four-layer regression test suite**.

## Role of each layer

| Layer | Target | What it verifies | Tolerance |
|---|---|---|---|
| **Layer 1** | `wrlib_equivalence` | `libwrapi.so` output matches the Phase 0 `wrx2` baseline exactly | **1e-10** (strict) |
| **Layer 2** | `wrlib_c_abi`      | the 5 C-ABI functions return correct `ierr` | — |
| **Layer 3** | `wrlib_ffi`, `wrlib_wrapper` | ctypes structs, life cycle | — |
| **Layer 4** | `wrlib_sweep`     | parameter-sweep smoke | — |

Layer 1 is the **lifeblood** of this library.

## How to run

### Run a single suite

```bash
bash test_run/run_tests.sh wrlib_equivalence  # Layer 1 (most important)
bash test_run/run_tests.sh wrlib_c_abi        # Layer 2
bash test_run/run_tests.sh wrlib_ffi          # Layer 3 (low level)
bash test_run/run_tests.sh wrlib_wrapper      # Layer 3 (high level)
bash test_run/run_tests.sh wrlib_sweep        # Layer 4
```

### Run them all at once (pytest directly)

```bash
cd python/wrlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

## Inside Layer 1 (equivalence test)

`wrlib_equivalence` does the following:

1. Load `libwrapi.so` via `Wrlib()`
2. Replay the registered parameters from the Phase 0 fixture using
   `set_param`
3. Run the ray trace via `wr.run(nray_request)`
4. Emit JSON via `WrState.to_dict()`
5. Diff against `test_run/baselines/<case>/metrics.json` at tolerance
   `1e-10`

It checks that the `wrx2` binary and the `libwrapi.so` route agree to
ten decimal places. Ray trajectories are highly sensitive numerically,
so 1e-10 agreement is a stringent benchmark.

## Ray-tracing-specific testing concerns

Because `wr` does not advance in time, its tests depend more heavily on
initial conditions than typical unit tests. Caveats:

- **Path-dependence of numerical integration**: changing `EPSRAY`,
  `DELRAY`, etc., perturbs the path slightly and can break 1e-10
  agreement. The tests assume the fixture's exact values.
- **Resonance-position sensitivity**: when frequency and plasma
  parameters sit close to a resonance, tiny parameter changes can
  produce large output swings.

## Frequently used files

- `python/wrlib/tests/test_equivalence.py` — Layer 1
- `python/wrlib/tests/test_wrlib.py` — Layer 3 high-level
- `python/wrlib/tests/test_ffi.py` — Layer 3 low-level
- `python/wrlib/tests/test_sweep.py` — Layer 4

## CI integration

CI runs them with `--forked --timeout=120 --timeout-method=signal`.

```{important}
**Do not skip the equivalence test with `@pytest.mark.skip`.** If you
cannot fix it immediately, mark it `@pytest.mark.xfail(strict=True,
reason="#<issue>")` and link the issue.
```
