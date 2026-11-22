# FAQ — `eq` specifics

## Q1. Why is `PSIB` the only 0-origin array?

It is declared `REAL(8) :: PSIB(0:5)` in `eqcom1_mod.f90`. As a ψ
boundary condition, counting from $\psi = 0$ (the magnetic axis) is
the physically natural choice. The PF-coil arrays (`RIPFC`, `RPFC`,
`ZPFC`, `WPFC`) follow the usual 1-origin convention.

Through `set_param`, use `"PSIB[0]"` through `"PSIB[5]"`. The bare
name `"PSIB"` (no index) is explicitly rejected by the registry
(`EqlibInvalidParamError`).

## Q2. What does the `mode` argument of `eq.run()` mean?

`eq.run(mode)` currently has two operating modes. Both correspond to
menu commands of the legacy `eqx2` CLI:

| `mode` | Purpose | Legacy CLI command | Required setup |
|---|---|---|---|
| `0` | **Grad-Shafranov solve** (`EQCALC`, iterated to `EPSEQ`, + post-processing) | `R` (Run) -> `F` (Fields) | `MODELG ∈ {0, 1, 2}`, profile coefficients (`PP*`, `PJ*`, `FF*`, ...) |
| `1` (default) | **Load an equilibrium file** (`equnit::eq_load`) | `L` (Load) | a file format: `MODELG` 3 or 9 (TASK/EQ), 5 or 25 (G-EQDSK) with `KNAMEQ` (filename), 8 (QST/JAEA) with `KNAMEQ` and `KNAMEQ2`; `MODELG = 15` reads `eqdb.dat` |

`mode=1` is the default because it is the **standard file-driven
workflow** (it fails with the default `MODELG=2`, which names no file
format). When you want to solve the equilibrium (giving only the
device parameters and profile coefficients), use `mode=0`. A negative
`mode` raises `EqlibInvalidParamError`, a mode above 1
`EqlibNotImplementedError` (a number that does not fit a C `int` raises
`EqlibInvalidParamError` before the library is called).

```{note}
The `run` of `tr`/`ti`/`wr`/`fp` takes a step count `ntmax`, but EQ
has no time evolution, so the argument has a different meaning.
```

## Q3. Passing `KNAMEQ` as a kwarg fails

`set_params(KNAMEQ="...")` is **not** supported. String parameters
must go through `set_param_str("KNAMEQ", "...")` (see
{doc}`parameter-setting`, method C).

## Q4. `EqlibError: libeqapi.so does not export eq_set_param_str`

You are loading a `libeqapi.so` from before Phase L-3. Rebuild with
`make -C eq libeqapi.so`.

## Q5. `EqlibCalculationFailedError: ierr=3`

The equilibrium iteration failed to converge, or the equilibrium file is
inconsistent. Common causes:

- The combination `RR`, `RA`, `BB`, `RIP` is physically implausible
  (e.g. an extremely low-aspect-ratio configuration)
- `EPSEQ` (convergence tolerance) is too tight — relax the default
  `1e-6` to `1e-4` and retry
- `NLPMAX` (maximum iterations) is too small — increase it from the
  default `100`
- The load (`mode=1`) cannot open the file (it is not there), or cannot
  read it: the file is not of the format `MODELG` names (a TASK/EQ file
  for 3 and 9, a G-EQDSK file for 5 and 25, a QST/JAEA pair for 8), is cut
  short (a TASK/EQ file cut inside its last record still loads, with
  `HJTRZ` 0), gives a grid size EQ cannot take, or, for 8, R and Z ranges
  that are no grid (empty, falling or not finite) or no magnetic axis in
  its psi. The exception message ends with the reason
  (`eq.last_error()`), which names the file, e.g. `EQ_READ: MODELG=5 load
  of KNAMEQ='eqdata.ITER01' failed: it does not read as a G-EQDSK file
  (...)`; in the parentheses, the message of the read that failed, the
  size, or for 8 the R and Z ranges. A load that cannot read its file puts the grid sizes back, but
  the other parameters it read from the file before it failed (`RR`,
  `BB`, `RIP`, ...) stay: set them again before a `run(mode=0)`

`validate()` catches grid dimensions, a missing load file (a blank `KNAMEQ` or one naming no file,
`KNAMEQ2` for `MODELG=8`, `eqdb.dat` for `MODELG=15`) and, for the
Grad-Shafranov solve, a wall inside the plasma, a negative current and a box
(`MDLEQF >= 10`) the solve cannot use up-front; physical consistency is
only known after `run()`.

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
