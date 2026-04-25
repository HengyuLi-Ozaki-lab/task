# Testing

The `tr` library ships with **four layers of regression tests**.
This page describes concretely what each layer verifies.

## The four layers and their roles

| Layer | Target | What it verifies | Tolerance |
|---|---|---|---|
| **Layer 1** | `trlib_equivalence` | Output of `libtrapi.so` matches the Phase 0 Fortran baseline (the `tr2` CLI version) exactly | **1e-10** (strict) |
| **Layer 2** | `trlib_c_abi`      | The 5 C-ABI functions return correct ierr (smoke / nominal / error paths) | — |
| **Layer 3** | `trlib_ffi`, `trlib_wrapper` | The `_ffi.py` ctypes structs match the C side byte-for-byte; the `Trlib` class lifecycle (`__enter__`/`__exit__` etc.) is correct | — |
| **Layer 4** | `trlib_sweep`     | Across 3×3 = 9 cases of `RR` × `BB`, `run()` does not crash (smoke) | — |

Layer 1 is the **lifeline** of this library. If it does not match at
1e-10, the change cannot be released
(see `feedback_equivalence_must_pass`).

## How to run

### Run them one by one

```bash
bash test_run/run_tests.sh trlib_equivalence  # Layer 1 (most important)
bash test_run/run_tests.sh trlib_c_abi        # Layer 2
bash test_run/run_tests.sh trlib_ffi          # Layer 3 (low-level)
bash test_run/run_tests.sh trlib_wrapper      # Layer 3 (high-level)
bash test_run/run_tests.sh trlib_sweep        # Layer 4
```

### Run them all at once (pytest directly)

```bash
cd python/trlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

`--forked` is the flag that runs each test in a separate process,
preventing tests that repeat `tr_init` from contaminating each
other's Fortran-module state (this is also the reason for the
singleton constraint discussed in Q4 of {doc}`faq`).

## What Layer 1 (the equivalence test) does

`trlib_equivalence` performs the following for two cases (`tr_iter01`,
`tr_tst2`):

1. Load `libtrapi.so` via `Trlib()`.
2. Push registered parameters from a Phase 0 fixture
   (`test_run/fixtures/<case>.nml`) using `set_param` /
   `set_param_str`.
3. Advance with `run()` up to the fixture's `NTMAX`.
4. Dump JSON via `TrState.to_dict()`.
5. Diff against `test_run/baselines/<case>/metrics.json` using
   `compare_metrics.py` (tolerance `1e-10`).

In other words: "does the output via `libtrapi.so` match the output
of the `tr2` binary at all radii, all profiles, and all scalars at
the final time, agreeing to 10 decimal places?" A single-digit
mismatch fails.

```{admonition} eqdata file
:class: note

The `tr_iter01` / `tr_tst2` cases with `MODELG=3` read files such as
`eqdata.ITER01` from the current directory, so the test runs after
`cd`'ing into `test_run/test_output/<case>/`. In environments where
the file is not present, the test is skipped.
```

## Files used frequently

- `python/trlib/tests/test_equivalence.py` — Layer 1
- `python/trlib/tests/test_trlib.py` — Layer 3 (high-level)
- `python/trlib/tests/test_ffi.py` — Layer 3 (low-level)
- `python/trlib/tests/test_sweep.py` — Layer 4
- `python/trlib/tests/test_validate.py` — `validate` API from PR #172
- `test_run/fixtures/` — namelist / JSON fixtures
- `test_run/baselines/<case>/metrics.json` — Phase 0 baseline
- `test_run/test_definitions.conf` — target definitions (`trlib_*`)

## Relationship to CI

CI runs with the same flags
(`--forked --timeout=120 --timeout-method=signal`). The rule is
to never push something that fails locally
(see the pre-push gate in `CLAUDE.md`).

```{important}
**Skipping equivalence tests via `@pytest.mark.skip` is forbidden.**
If you cannot fix it, leave a
`@pytest.mark.xfail(strict=True, reason="#<issue>")` and an issue
link.
```
