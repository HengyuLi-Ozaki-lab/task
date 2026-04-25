# Testing

The `ti` library has **4 layers of regression tests**.

## Role of each layer

| Layer | Target | What it checks | Tolerance |
|---|---|---|---|
| **Layer 1** | `tilib_equivalence` | `libtiapi.so` output matches the Phase 0 `tix2` baseline exactly | **1e-10** (strict) |
| **Layer 2** | `tilib_c_abi`      | The 5 C-ABI functions return correct `ierr` values | — |
| **Layer 3** | `tilib_ffi`, `tilib_wrapper` | ctypes struct integrity, lifecycle | — |
| **Layer 4** | `tilib_sweep`     | Smoke test of parameter sweeps | — |

Layer 1 is the **lifeline** of this library
(see `feedback_equivalence_must_pass`).

## How to run

### Run individual layers

```bash
bash test_run/run_tests.sh tilib_equivalence  # Layer 1 (most important)
bash test_run/run_tests.sh tilib_c_abi        # Layer 2
bash test_run/run_tests.sh tilib_ffi          # Layer 3 (low level)
bash test_run/run_tests.sh tilib_wrapper      # Layer 3 (high level)
bash test_run/run_tests.sh tilib_sweep        # Layer 4
```

### Run all together (pytest directly)

```bash
cd python/tilib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

`--forked` runs each test in a separate process to prevent the shared
`pl_*` state from being polluted (related to the singleton constraint
in {doc}`faq` Q2).

## What Layer 1 (the equivalence test) does

`tilib_equivalence` performs the following:

1. Load `libtiapi.so` via `Tilib()`
2. Feed registered parameters from the Phase 0 fixture using
   `set_param`
3. Advance `run()` up to the fixture's `NTMAX`
4. Emit JSON via `TiState.to_dict()` (scalars + scalars_int + profiles)
5. Diff against `test_run/baselines/<case>/metrics.json` (tolerance
   `1e-10`)

It checks that the result via `libtiapi.so` matches the `tix2` binary
to 10 decimal places.

## Files you'll often touch

- `python/tilib/tests/test_equivalence.py` — Layer 1
- `python/tilib/tests/test_tilib.py` — Layer 3 (high level)
- `python/tilib/tests/test_ffi.py` — Layer 3 (low level)
- `python/tilib/tests/test_sweep.py` — Layer 4
- `test_run/test_definitions.conf` — `tilib_*` definitions

## Relation to CI

CI runs the same command — `--forked --timeout=120
--timeout-method=signal`. Never push something that fails locally
(see the pre-push gate in `CLAUDE.md`).

```{important}
**Skipping equivalence tests with `@pytest.mark.skip` is forbidden.**
If you cannot fix the issue, mark the test with
`@pytest.mark.xfail(strict=True, reason="#<issue>")` and leave a link
to the issue.
```
