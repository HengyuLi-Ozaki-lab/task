# Testing

The `eq` library has a **four-layer regression suite**. Each layer
verifies a different aspect.

## What each layer does

| Layer | Target | What it verifies | Tolerance |
|---|---|---|---|
| **Layer 1** | `eqlib_equivalence` | The output of `libeqapi.so` matches the Phase 0 Fortran baseline (`eqx2` binary) bit-for-bit | **1e-10** (strict) |
| **Layer 2** | `eqlib_c_abi`      | The 6 C ABI functions + `eq_validate` return correct ierr codes | — |
| **Layer 3** | `eqlib_ffi`, `eqlib_wrapper` | `_ffi.py` ctypes structures match the C side byte-for-byte; `Eq` lifecycle is correct | — |
| **Layer 4** | `eqlib_sweep`      | `run()` does not crash on a 3×3 = 9-case sweep over `RR`×`BB` (smoke) | — |

Layer 1 is the **lifeline** of this library. Releases are blocked
unless it passes at 1e-10 (see `feedback_equivalence_must_pass`).

```{note}
Layers 1 and 4 are skipped unless the **`EQ_RUN_OK` gate** is set,
because they have eq-specific prerequisites such as the EQDSK file.
The flag is determined automatically when launched via
`bash test_run/run_tests.sh`.
```

## How to run

### Run them individually

```bash
bash test_run/run_tests.sh eqlib_equivalence  # Layer 1 (most important)
bash test_run/run_tests.sh eqlib_c_abi        # Layer 2
bash test_run/run_tests.sh eqlib_ffi          # Layer 3 (low-level)
bash test_run/run_tests.sh eqlib_wrapper      # Layer 3 (high-level)
bash test_run/run_tests.sh eqlib_sweep        # Layer 4
```

### Run them together (pytest directly)

```bash
cd python/eqlib
pytest --forked --timeout=120 --timeout-method=signal tests/
```

`--forked` runs each test in a separate process. This keeps tests
that re-`eq_init` from cross-contaminating each other's Fortran
module state (related to the singleton constraint in {doc}`faq`
Q6). The SAVE-flag reset in `eqfini` (issue #110, PR #163) was also
designed assuming `--forked`.

## What Layer 1 (equivalence) actually does

`eqlib_equivalence` runs the following on two cases (`eq_iter01`,
`eq_tst2`):

1. Load `libeqapi.so` via `Eq()`.
2. Pour all registered parameters from the Phase 0 fixture into the
   library via `set_param` / `set_param_str` (including `KNAMEQ`).
3. Solve the equilibrium with `eq.run(mode=1)`.
4. Dump the result as JSON via `EqState.to_dict()`.
5. Diff against `test_run/baselines/<case>/metrics.json` using
   `compare_metrics.py` at tolerance `1e-10`.

In other words: "Does the result through `libeqapi.so` match the
result of the `eqx2` binary across every ψ-surface profile and every
scalar to ten decimal places?". A discrepancy in even one digit is
a FAIL.

```{admonition} eqdata file
:class: note

`eq_iter01` / `eq_tst2` with `MODELG=3` reads files such as
`eqdata.ITER01` from the current directory, so the test is executed
after a `cd` into `test_run/test_output/<case>/`. In environments
without that file the test is skipped (`EQ_RUN_OK=0`).
```

## What Layer 4 (sweep) does

`eqlib_sweep` runs:

- All combinations of `RR ∈ {6.0, 6.5, 7.0}` and
  `BB ∈ {3.0, 5.0, 5.3}` (9 total)
- For each combination, that `eq.run(mode=1)` returns `ierr=0`
- That `EqState.scalars["raxis"]` and friends are not NaN/Inf

It does **not** check numerical correctness. It is a smoke test for
"does it crash on an unfamiliar parameter combination?".

## Frequently used files

- `python/eqlib/tests/test_equivalence.py` — Layer 1
- `python/eqlib/tests/test_eqlib.py` — Layer 3 (high-level)
- `python/eqlib/tests/test_ffi.py` — Layer 3 (low-level)
- `python/eqlib/tests/test_sweep.py` — Layer 4
- `python/eqlib/tests/test_validate.py` — `validate` API from PR #164
- `test_run/fixtures/` — namelist / JSON fixtures
- `test_run/baselines/<case>/metrics.json` — Phase 0 baseline
- `test_run/test_definitions.conf` — target definitions (`eqlib_*`)

## Relationship with CI

CI runs the same flags (`--forked --timeout=120 --timeout-method=signal`).
Do not push something that fails locally — that is the iron rule of
the pre-push gate (see `CLAUDE.md`).

```{important}
**Skipping equivalence tests with `@pytest.mark.skip` is forbidden.**
If you cannot fix it, leave a `@pytest.mark.xfail(strict=True, reason="#<issue>")`
together with a linked issue.
```
