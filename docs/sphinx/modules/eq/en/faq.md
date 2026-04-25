# FAQ — `eq` specifics

## Q1. Why is `PSIB` the only 0-origin array?

It is declared `REAL(8) :: PSIB(0:5)` in `eqcom1_mod.f90`. As a ψ
boundary condition, counting from $\psi = 0$ (the magnetic axis) is
the physically natural choice. The PF-coil arrays (`RIPFC`, `RPFC`,
`ZPFC`, `WPFC`) follow the usual 1-origin convention.

Through `set_param`, use `"PSIB[0]"` through `"PSIB[5]"`. The bare
name `"PSIB"` (no index) is explicitly rejected by the registry
(`EqlibInvalidParamError`).

## Q2. Why does `eq.run()` default to `mode=1`?

`mode=1` invokes `equnit::eq_load`, which reads the current `KNAMEQ`
(EQDSK file) and builds the equilibrium — that is the standard,
EQDSK-driven workflow. `mode=0` (a direct EQCALQ call) is reserved
and currently raises `EqlibNotImplementedError`. The `run` of
`tr`/`ti`/`wr`/`fp` takes a step count `ntmax`, but EQ has no time
evolution, so the argument has a different meaning.

## Q3. Passing `KNAMEQ` as a kwarg fails

`set_params(KNAMEQ="...")` is **not** supported. String parameters
must go through `set_param_str("KNAMEQ", "...")` (see
{doc}`parameter-setting`, method C).

## Q4. `EqlibError: libeqapi.so does not export eq_set_param_str`

You are loading a `libeqapi.so` from before Phase L-3. Rebuild with
`make -C eq libeqapi.so`.

## Q5. `EqlibCalculationFailedError: ierr=3`

The equilibrium iteration failed to converge, or the EQDSK file is
inconsistent. Common causes:

- The combination `RR`, `RA`, `BB`, `RIP` is physically implausible
  (e.g. an extremely low-aspect-ratio configuration)
- `EPSEQ` (convergence tolerance) is too tight — relax the default
  `1e-6` to `1e-4` and retry
- `NLPMAX` (maximum iterations) is too small — increase it from the
  default `100`
- The EQDSK file format does not match (version mismatch)

`validate()` only catches grid-dimension and file-existence issues
up-front; physical consistency is only known after `run()`.

## Q6. Can I create two `Eq()` instances in the same process?

**No.** This is enforced by a singleton boundary. The second `Eq()`
raises `EqlibError`. If you need multi-instance use, isolate them via
`multiprocessing` into separate processes.

## Q7. Results don't match `eqx2` (the CLI binary)

Run the regression test `eqlib_equivalence` and check the diff against
the Phase 0 baseline.

```bash
bash test_run/run_tests.sh eqlib_equivalence
```

The tolerance is `1e-10`. If the deviation exceeds it, check whether
you are missing a registered parameter that should have been set.

## Q8. Do I need NumPy?

**No.** `EqState` uses Python `list`s. If you want NumPy, convert
with `import numpy as np; np.array(state.psips)`.
