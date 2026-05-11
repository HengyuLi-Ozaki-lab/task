# Setting Input Parameters

`ti` uses the same standard 5-function ABI as `tr`, so there are two
ways to set parameters: `set_params` and `set_param` (there is no
dedicated string-parameter API).

## Method A — scalars (`set_params`)

You can set many parameters in one call via Python keyword arguments.

```python
ti.set_params(RR=3.0, RA=1.2, BB=3.0, NSMAX=2,
              DT=0.01, NTMAX=100,
              MODEL_KAI=31, MODEL_NB=1)
```

## Method B — array elements (`set_param`)

Keyword arguments cannot contain `[` or `]`, so for array elements use
`set_param`. Indices are **1-origin**.

```python
ti.set_param("PN[1]", 1.0)         # density of the 1st species
ti.set_param("PT[2]", 1.5)         # central temperature of the 2nd species
ti.set_param("PROFN1[1]", 2.0)     # profile-shape exponent (per species)
ti.set_param("ID_NS[3]", 4)        # species ID (integers can be passed as double)
```

## About string parameters

`ti` has **no string parameters** (no dedicated API like `eq`'s
`KNAMEQ` is needed). Equilibrium data are passed via `pl_*` (plasma
common), so they are not set from `ti` directly.

## Pre-run validation (`validate`)

```{important}
`ti` does not currently implement a `validate()` API. Range checks are
performed only as immediate rejections in `set_param`
(`TilibParamError`) and as physics checks during `run()`. When sweeping
many parameters, wrap the call in `try/except`.
```

## Typical usage patterns

### Minimal transport calculation

```python
ti.set_params(RR=3.0, RA=1.2, BB=3.0, RIP=3.0, NSMAX=2,
              DT=0.01, NTMAX=100)
```

### Adding NBI

```python
ti.set_params(RR=3.0, BB=3.0, NSMAX=2,
              MODEL_NB=1)        # NBI model ON
```

### Switching transport models

```python
ti.set_params(RR=3.0, BB=3.0, NSMAX=2,
              MODEL_KAI=140)     # switch to mBgB (default is 31 = CDBM)
```

### Specifying charge states per species

```python
ti.set_param("ID_NS[3]", 6)        # species 3 is carbon (Z=6)
ti.set_param("NZMIN_NS[3]", 1)     # minimum charge state +1
ti.set_param("NZMAX_NS[3]", 6)     # maximum charge state +6
```
