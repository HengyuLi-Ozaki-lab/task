# Testing

The `tot` library ships with a **four-layer regression test suite**.

## Roles of the four layers

| Layer | Target | What it verifies | Tolerance |
|---|---|---|---|
| **Layer 1** | `totlib_equivalence` | `libtotapi.so` output matches the Phase 0 baseline exactly | **1e-10** (strict) |
| **Layer 2** | `totlib_c_abi`      | The 6 C-ABI functions (including set_param_str) return correct ierr | — |
| **Layer 3** | `totlib_ffi`, `totlib_wrapper` | Prefix routing, lifecycle | — |
| **Layer 4** | `totlib_sweep`     | `eq:RR × eq:BB` 3×3 sweep | — |

```{note}
Layers 1 and 4 are **gated by `TOT_RUN_OK`** — they are skipped unless
that flag is set (the same mechanism as eq's `EQ_RUN_OK`). It is an
environment variable that asserts that tot-specific prerequisites such
as the EQDSK files are in place.
```

## How to run

### One layer at a time

```bash
bash test_run/run_tests.sh totlib_equivalence  # Layer 1 (most important)
bash test_run/run_tests.sh totlib_c_abi        # Layer 2
bash test_run/run_tests.sh totlib_ffi          # Layer 3 (low level)
bash test_run/run_tests.sh totlib_wrapper      # Layer 3 (high level)
bash test_run/run_tests.sh totlib_sweep        # Layer 4
```

### All at once (pytest directly)

```bash
cd python/totlib
pytest --forked --timeout=300 --timeout-method=signal tests/
```

`--forked` is mandatory. Because `tot` retains state across every
sub-module, process isolation is even more important than with the
stand-alone modules.

## Inside Layer 1 (the equivalence test)

`totlib_equivalence` does the following:

1. Load `libtotapi.so` via `Tot()` (which initialises every sub-module)
2. Stream prefixed parameters from the Phase 0 fixture into `set_param`
   (`eq:RR`, `tr:NSMAX`, ...)
3. Run the integrated simulation with `tot.run(ntmax)`
4. Dump JSON via `TotState.to_dict()` (presence flags + scalars +
   profiles)
5. Diff against `test_run/baselines/<case>/metrics.json` (tolerance
   `1e-10`)

This checks that the `tot_x2` binary and `libtotapi.so` agree to 10
decimal digits.

## tot-specific test challenges

### Numerical reproducibility of sub-module coupling

Because `tot` chains eq → tr → wr → fp through several modules, error
propagation between steps becomes an issue. Even if each stand-alone
module passes at 1e-10, the integrated run can degrade to roughly 1e-9
because of differences in numerical sensitivity.

### The TOT_RUN_OK gate

In environments where `TOT_RUN_OK` is not set, Layer 1 and Layer 4 are
skipped:

- `EQ_RUN_OK` (eq's EQDSK files in place) is a prerequisite
- The smoke test of every sub-module is a prerequisite
- See `test_run/scripts/check_run_ok.sh` for details

## Files you'll touch most often

- `python/totlib/tests/test_equivalence.py` — Layer 1
- `python/totlib/tests/test_totlib.py` — Layer 3 high-level
- `python/totlib/tests/test_ffi.py` — Layer 3 low-level
- `python/totlib/tests/test_sweep.py` — Layer 4

## Relationship to CI

CI runs the layers in parallel, but `tot` is normally scheduled after
the stand-alone module tests because of the dependency.

```{important}
**Do not skip the equivalence test with `@pytest.mark.skip`.** If you
cannot fix the underlying issue, replace it with
`@pytest.mark.xfail(strict=True, reason="#<issue>")` and link the
issue.
```
