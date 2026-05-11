# Setting Input Parameters

`fp` uses the same 6-function ABI as `eq`, with three ways to set
parameters: scalar, array, and **string**.

## Method A — scalars (`set_params`)

```python
fp.set_params(RR=3.0, BB=3.0, NSMAX=1,
              NPMAX=50, NTHMAX=25, NRMAX=20,
              DELT=0.001, NTMAX=100,
              MODELE=1)
```

## Method B — array elements (`set_param`)

```python
fp.set_param("PA[1]", 2.0)        # mass number for species 1
fp.set_param("PZ[1]", 1.0)        # charge
fp.set_param("NS_NSA[1]", 2)      # NSA[1] maps to NSMAX[2]
```

## Method C — string parameter (`set_param_str`)

`fp` lets you set the **`KNAMEQ`** (equilibrium-data file name) via a
string.

```python
fp.set_param_str("KNAMEQ", "eqdata.ITER01")
```

`fp` inherits `KNAMEQ` from the `pl_*` modules internally; use this
method only when you need to override that value.

## Pre-validation (`validate`)

```{important}
`fp` does not currently implement a `validate()` API. Range violations
are caught immediately at `set_param` time (`FplibInvalidParamError`);
physical-consistency violations are caught at `run()` time
(`FplibCalcFailedError`).
```

## Common configuration patterns

### Fast-ion distribution under NBI

```python
fp.set_params(NSMAX=2, NSAMAX=2, NSBMAX=2,
              NPMAX=100, NTHMAX=50,        # high resolution
              MODEL_NBI=1)                  # turn on NBI source
```

### Wave-driven electron acceleration

```python
fp.set_params(NSMAX=1,
              MODELE=1,                     # electrons only
              MODEL_WAVE=1,                 # wave drive ON
              PABS_LH=1.0)                  # LH absorbed power [MW]
```

### Equilibrium from an external file

```python
fp.set_param("MODELG", 3)                   # EQDSK mode
fp.set_param_str("KNAMEQ", "eqdata.ITER01") # equilibrium data
```
