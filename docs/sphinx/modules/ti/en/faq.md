# FAQ — `ti` specifics

## Q1. What is the difference between `ti` and `tr`?

`tr` is a **plain 1-D transport-equation solver** that runs with a
minimal parameter set. `ti` is a **full package that integrates
transport with auxiliary physics** (NBI / EC / LH / IC / fusion /
impurities / pellets), with many model switches.

| | `tr` | `ti` |
|---|---|---|
| Main purpose | Pure transport benchmarking | Integrated simulations to reproduce experiments |
| Registered parameters | ~30 | 77 |
| `MODEL_*` switches | NBI/EC/LH/IC, JBS only | 18+ |
| Profile outputs | `RN`, `RT`, `AJ`, `QP` | `RNA`, `RTA`, `RUA`, `RBP`, `RQP`, `RJP`, `ZEFF`, `BETA` |

For a new project that needs to "reproduce an experiment in TASK", `ti`
is normally the right choice.

## Q2. Can I create `Tilib()` and `Trlib()` at the same time?

**No.** Both grab the same shared plasma state (the `pl_*` module), so
that would violate the singleton constraint. Sequential is fine:

```python
with Trlib() as tr:
    ...
# after tr_finalize
with Tilib() as ti:
    ...
```

## Q3. I cannot find a `validate()` method

`ti` does not currently implement `validate()` (see the note at the top
of {doc}`parameter-setting`). Range violations are caught immediately
when calling `set_param` (`TilibParamError`), and physics-consistency
violations are caught at `run()` time (`TilibRunError`).

## Q4. There are too many `MODEL_*` switches — which should I set?

The defaults are designed to **work as-is**. Out of the box, only
transport is ON and all heating / particle-source models are OFF.
Enable individually:

- `MODEL_NB=1` → NBI ON
- `MODEL_EC=1` → ECRF ON
- `MODEL_LH=1` → LHRF ON
- `MODEL_IC=1` → ICRF ON
- `MODEL_NF=1` → fusion ON
- `MODEL_NC=1` → NCLASS (neoclassical transport) ON

For details, see the "Module switches" section of {doc}`parameters`.

## Q5. Enabling NCLASS produced strange results

When you turn on `MODEL_NC=1` (NCLASS), NCLASS computes all the
neoclassical transport coefficients itself, so any other model that
overlaps (`MODEL_DRR`, `MODEL_VR`, …) will produce nonsense. Do **not
combine** NCLASS with the other transport models.

## Q6. The iteration does not converge (`MAXLOOP` reached)

The time step `DT` may be too large, or the parameters may be
inconsistent. Mitigations:

1. Reduce `DT` by a factor of 10 (e.g. 0.01 → 0.001)
2. Increase `MAXLOOP` (default 100 → 1000)
3. Loosen `EPSLOOP` (default 1e-6 → 1e-4)
4. Verify that the profile exponents (`PROFN1`, `PROFN2`, …) are
   physically reasonable

## Q7. Results disagree with `tix2` (the CLI)

Run the regression test `tilib_equivalence` to compare against the
Phase 0 baseline.

```bash
bash test_run/run_tests.sh tilib_equivalence
```

The tolerance is `1e-10`. Differences exceeding this often mean a
parameter is missing from the registry.
