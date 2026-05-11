# FAQ — `tot` specifics

## Q1. What does `tot` do?

`tot` is the **orchestrator** that runs the eq / tr / ti / fp / wr / wrx
modules in a single process. By attaching a prefix (`eq:`, `tr:`, ...)
to each parameter name, it routes the value to the correct sub-module.

Main uses:

- Self-consistent simulation of **equilibrium + transport + RF heating**
- **Dynamically pass results** between sub-modules (e.g. the q profile
  from `eq` is fed into the transport calculation in `tr`)
- No need to write code that calls each stand-alone module in turn

## Q2. Why are prefixes required?

eq, tr, ti, fp, wr, wrx all use **the same parameter names** (`RR`,
`BB`, `NSMAX`, ...). Without a prefix, `tot` would not know which module
should receive `RR`, so you must write `eq:RR`, `tr:RR`, and so on
explicitly.

An alternative design would have all modules share a single `RR`, but
the meanings differ slightly between modules (e.g. eq's `RR` is the
device design value while tr's `RR` is the plasma centre), so the
**explicit separation** is preferred.

## Q3. What is the difference between `tot` and `ti`?

Both integrate plasma simulations, but:

| | `ti` (integrated transport) | `tot` (orchestrator) |
|---|---|---|
| Integration approach | folds auxiliary physics into a single equation system | calls existing modules separately and exchanges results |
| Sub-modules | internal implementations (NBI, EC, NF, etc., implemented in-house) | calls external implementations (`wr`, `fp`, ...) |
| Parameter names | `MODEL_NB`, `MODEL_EC`, ... | `eq:RR`, `tr:NSMAX`, ... (prefixed) |
| Physics fidelity (RF) | simplified | full (`wr`/`wrx`) |
| Physics fidelity (fast ions) | fluid approximation | full (`fp`) |
| Compute cost | medium | **large** (all modules expanded) |

For research with **high fidelity**, use `tot`. For teaching where
**quick turnaround** matters, use `ti`.

## Q4. What happens when I construct `Tot()`?

`tot_init` is called, which in turn calls:

1. `pl_init` — common plasma module
2. `eq_init` — equilibrium
3. `tr_init` — transport
4. `ti_init` — integrated transport (if available)
5. `fp_init` — Fokker–Planck
6. `wr_init`, `wrx_init` — ray tracing

If everything succeeds, `state.<mod>_present = 1`. Modules that fail
become `_present = 0`, and trying to set a parameter under that prefix
raises an error.

## Q5. Can I unit-test a single sub-module inside `tot`?

There is no direct way to run **only one sub-module** from within a
`Tot()` session. You can, however, skip other modules' computation:

- Leave their parameters at the default values
- Turn the relevant switches (`MODEL_*`) to 0 (OFF)

For genuine single-module testing, the standard approach is to use the
**stand-alone module** (`Trlib`, `Wrlib`, ...).

## Q6. Out-of-memory errors

`tot` carries the state of every module, so memory consumption is high.
A rough estimate:

```
tr memory + eq memory + ti memory + fp memory + wr memory + wrx memory
≈ several hundred MB to several GB
```

Increasing `fp:NPMAX` and `fp:NTHMAX` can quickly push this past several
GB. Mitigations:

- Keep `fp:NPMAX`, `fp:NTHMAX` modest (see fp's FAQ Q3,
  `docs/sphinx/modules/fp/en/faq.md`)
- Keep `wr:NSTPMAX` modest
- Skip unused modules by simply not setting their parameters

## Q7. Results don't match the `tot_x2` (CLI) version

Run the regression test `totlib_equivalence`:

```bash
bash test_run/run_tests.sh totlib_equivalence
```

The tolerance is `1e-10`. The test is skipped unless the `TOT_RUN_OK`
gate is set (see {doc}`testing`).

## Q8. Are un-prefixed keys really forbidden?

**Yes.** `set_param("RR", 6.5)` raises `TotlibInvalidParamError`. Always
write `eq:RR`, `tr:RR`, etc.
