# Setting Input Parameters

There are four ways.

## Method A — scalars (`set_params`)

You can set many scalars at once via Python keyword arguments.

```python
tr.set_params(RR=7.5, RA=2.0, BB=5.3, DT=0.05, NTMAX=200)
```

## Method B — array elements (`set_param`)

Keyword arguments cannot contain `[` or `]`, so array elements go
through `set_param`. Indices are **1-origin** (start from 1).

```python
tr.set_param("PN[1]", 1.0)   # density of species 1
tr.set_param("PN[2]", 1.0)   # species 2
tr.set_param("CDW[12]", 0.5) # 12th element of the CDW array
```

## Method C — string parameters (`set_param_str`)

TR has string parameters such as the equilibrium-data filename
`KNAMEQ`. These are set through a dedicated API.

```python
tr.set_param_str("KNAMEQ", "eqdata.ITER01")
```

## Method D — pre-run validation (`validate`)

```{admonition} New feature (PR #172)
:class: important

`validate()` is an API that batch-checks parameters before they are
passed to `run()`. It returns a list of diagnostic dataclasses
covering out-of-range values, inconsistencies, missing files, and so
on. Calling it after parameter setup but before `run()` is the
recommended workflow.
```

```python
from trlib import Trlib, TrDiagCode

with Trlib() as tr:
    tr.set_params(RR=3.0, BB=3.0, NSMAX=2)
    tr.set_param_str("KNAMEQ", "eqdata.missing")  # file does not exist

    diags = tr.validate()
    for d in diags:
        print(f"[{TrDiagCode(d.code).name}] {d.param}: {d.message}")
    if diags:
        raise SystemExit("fix the diagnostics before running")

    tr.run(ntmax=10)
```

Diagnostic codes:

| Code | Meaning |
|---|---|
| `OUT_OF_RANGE`           | value outside the allowed range |
| `INCONSISTENT_PAIR`      | inconsistency between related parameters |
| `OUT_OF_RANGE_AFTER_DEP` | out of range after dependent parameters are evaluated |
| `FILE_MISSING`           | a referenced file does not exist (e.g. `KNAMEQ`) |
| `MISSING_REQUIRED`       | a required parameter is unset |
