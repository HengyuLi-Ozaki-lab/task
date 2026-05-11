# Testing

The `fp` library ships with a **four-layer regression test suite**.

## Role of each layer

| Layer | Target | What it verifies | Tolerance |
|---|---|---|---|
| **Layer 1** | `fplib_equivalence` | `libfpapi.so` output matches the Phase 0 `fpx2` baseline exactly | **1e-10** (mandatory) |
| **Layer 2** | `fplib_c_abi`      | The 6 C-ABI functions return the correct `ierr` | — |
| **Layer 3** | `fplib_ffi`, `fplib_wrapper` | ctypes structs, lifecycle | — |
| **Layer 4** | `fplib_sweep`     | Smoke test of a 3×3 RR×BB scan | — |

Layer 1 is the **lifeline** of this library. If `1e-10` fails, the
release does not ship.

```{note}
Because `fp` is memory-hungry, Layers 1 and 4 take noticeably longer
than the other tests (typically 5–10 minutes). The timeout in
`test_definitions.conf` is set to 600 seconds.
```

## How to run

### One layer at a time

```bash
bash test_run/run_tests.sh fplib_equivalence  # Layer 1 (most important)
bash test_run/run_tests.sh fplib_c_abi        # Layer 2
bash test_run/run_tests.sh fplib_ffi          # Layer 3 (low-level)
bash test_run/run_tests.sh fplib_wrapper      # Layer 3 (high-level)
bash test_run/run_tests.sh fplib_sweep        # Layer 4
```

### All at once (pytest direct)

```bash
cd python/fplib
pytest --forked --timeout=600 --timeout-method=signal tests/
```

`--forked` is paired with `--timeout=600` (10 minutes) — process
isolation is required because of how `fp` manages reset state.

## Inside Layer 1 (equivalence test)

`fplib_equivalence` performs the following:

1. Load `libfpapi.so` via `Fplib()`.
2. Push registered parameters from the Phase 0 fixture in via
   `set_param` / `set_param_str` (including `KNAMEQ`).
3. Step in time with `run()` until the fixture's `NTMAX`.
4. Emit JSON via `FpState.to_dict()` (moment quantities).
5. Diff against `test_run/baselines/<case>/metrics.json` at tolerance
   `1e-10`.

It checks that the result via `libfpapi.so` matches the `fpx2` binary
to ten decimal places. Because `fp` is a precision distribution-function
solver, even small numerical noise shows up at 10 digits.

## Frequently used files

- `python/fplib/tests/test_equivalence.py` — Layer 1
- `python/fplib/tests/test_fplib.py` — Layer 3 high-level
- `python/fplib/tests/test_ffi.py` — Layer 3 low-level
- `python/fplib/tests/test_sweep.py` — Layer 4
- `test_run/test_definitions.conf` — `fplib_*` definitions (timeout=600)

## Relation to CI

CI runs the layers in parallel. Memory-heavy `fp` tests routinely
finish later than the lighter modules (tr, eq).

```{important}
**Skipping the equivalence test with `@pytest.mark.skip` is forbidden.**
If you cannot fix it, leave `@pytest.mark.xfail(strict=True,
reason="#<issue>")` plus a link to the issue.
```
