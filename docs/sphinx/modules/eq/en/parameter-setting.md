# Setting Input Parameters

There are four ways.

## Method A — scalars (`set_param`)

Unlike `tr`, `eq`'s `set_params(**kwargs)` accepts only scalars (a
positional mapping argument is also supported; see B below). The
typical pattern is `set_param("NAME", value)`, one at a time:

```python
eq.set_param("RR", 6.5)
eq.set_param("MODELG", 3)      # int passed as double is fine
eq.set_param("RIPFC[1]", 0.5)  # PF-coil current (1-origin, 1..10)
```

```{admonition} Only `PSIB` is 0-origin
:class: warning

The Fortran declaration is `REAL(KIND=8) :: PSIB(0:5)`, so the index
also runs from `PSIB[0]` to `PSIB[5]`. The bare name `"PSIB"` (no
index) is explicitly rejected by the registry
(`EqlibInvalidParamError`). All other 1-D arrays (`RIPFC`, `RPFC`,
`ZPFC`, `WPFC`) are 1-origin.
```

## Method B — bulk dict / kwargs (`set_params`)

```python
eq.set_params(RR=6.5, BB=5.3, MODELG=3)       # kwargs form
eq.set_params({"RR": 6.5, "BB": 5.3})          # positional mapping form
```

## Method C — string parameters (`set_param_str`)

EQDSK-family filenames are `CHARACTER(LEN=80)`, and the **dedicated
API** is required. They cannot be passed through `set_param`.

```python
eq.set_param_str("KNAMEQ",  "eqdata.ITER01")
eq.set_param_str("KNAMWR",  "wrdata.dat")
```

There are **7** valid keys:
`KNAMEQ`, `KNAMEQ2`, `KNAMWR`, `KNAMWM`, `KNAMFP`, `KNAMFO`, `KNAMPF`.

## Method D — pre-run validation (`validate`)

```{admonition} New feature (PR #164)
:class: important

`validate()` is the API that batch-checks parameters before `run()`.
It returns a list of diagnostic dataclasses describing grid-dimension
inconsistencies, missing files, and the like. The recommended flow is
to call it after setting parameters, before `run()`.
```

```python
from eqlib import Eq, EqDiagCode

with Eq() as eq:
    eq.set_params(RR=6.5, BB=5.3, RIP=1.5, MODELG=3)
    eq.set_param_str("KNAMEQ", "eqdata.missing")  # nonexistent file

    diags = eq.validate()
    for d in diags:
        print(f"[{EqDiagCode(d.code).name}] {d.param}: {d.message}")
    if diags:
        raise SystemExit("fix the diagnostics before running")

    eq.run()  # mode=1 (EQDSK load)
```

For an analytic solve, pass `mode=0`:

```python
with Eq() as eq:
    eq.set_params(RR=3.0, RA=1.0, BB=3.0, RIP=1.5)  # MODELG=2 by default
    diags = eq.validate()
    if diags:
        raise SystemExit("fix the diagnostics before running")
    eq.run(mode=0)  # EQCALC + EQCALQ — solved analytically
```

The diagnostic codes are the same five shared with `tr`:

| Code | Meaning |
|---|---|
| `OUT_OF_RANGE`           | value outside the allowed range |
| `INCONSISTENT_PAIR`      | inconsistency between related parameters |
| `OUT_OF_RANGE_AFTER_DEP` | range violation after dependency resolution |
| `FILE_MISSING`           | the specified file does not exist (`KNAMEQ`, etc.) |
| `MISSING_REQUIRED`       | a required parameter is unset |

`eq_validate` checks **ten grid dimensions** (`NSGMAX`, `NTGMAX`,
`NUGMAX`, `NRGMAX`, `NZGMAX`, `NPSMAX`, `NRMAX`, `NTHMAX`, `NSUMAX`,
`NRVMAX`) and the existence of `KNAMEQ` / `KNAMPF` files for the
geometry modes that need them.
