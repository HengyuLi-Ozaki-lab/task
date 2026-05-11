# Setting Input Parameters

`wr` uses the same standard 5-function ABI as `tr`, so input parameters
are configured in just two ways: `set_params` and `set_param` (there is
no string-parameter API).

## Method A — scalars (`set_params`)

```python
wr.set_params(RR=3.0, RA=1.2, BB=3.0, NSMAX=1,
              RF=170.0e9,            # frequency [Hz]
              RPI=3.5, ZPI=0.0,      # launch position
              NRAYMAX=1)             # number of rays
```

## Method B — array elements (`set_param`)

For multi-ray runs, give each ray's initial conditions through array
parameters.

```python
wr.set_param("NRAYMAX", 5)            # 5 rays
for i in range(1, 6):
    wr.set_param(f"RFIN[{i}]", 170.0e9)    # frequency of ray i
    wr.set_param(f"RPIN[{i}]", 3.5)         # launch R
    wr.set_param(f"ZPIN[{i}]", 0.1*(i-3))   # launch Z (shifted)
    wr.set_param(f"RKRIN[{i}]", 1.0)        # initial wave-number
    wr.set_param(f"PHIIN[{i}]", 0.0)        # toroidal angle
```

The `*IN`-suffixed arrays carry "per-ray initial conditions"; the
suffix-less scalars (`RF`, `RPI`, ...) are for the single-ray case
(`NRAYMAX=1`).

## Single-ray vs. multi-ray

### Single ray (`NRAYMAX=1`)

```python
wr.set_params(RR=3.0, BB=3.0)
wr.set_param("RF", 170e9)         # use the scalar version
wr.set_param("RPI", 3.5)
wr.run(nray_request=1)
```

### Multi-ray (`NRAYMAX>1`)

```python
wr.set_params(RR=3.0, BB=3.0, NRAYMAX=5)
for i in range(1, 6):
    wr.set_param(f"RFIN[{i}]", 170e9)
    wr.set_param(f"RPIN[{i}]", 3.5)
    wr.set_param(f"ZPIN[{i}]", -0.1 + 0.05*(i-1))   # spread along Z
wr.run(nray_request=5)
```

## About string parameters

`wr` has **no string parameters**. Equilibrium data (`KNAMEQ`) is passed
in through the `pl_*` modules and is therefore not set on `wr` itself.

## Pre-validation (`validate`)

```{important}
`wr` does not currently implement a `validate()` API. Out-of-range values
are caught immediately at `set_param` time; ray-trace failures surface as
`WrlibRunError` from `run()`.
```

## Typical configurations

### ECRH/ECCD (170 GHz, ITER-like)

```python
wr.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
wr.set_param("RF", 170.0e9)
wr.set_param("RPI", 8.0)               # launch from outboard
wr.set_param("ZPI", 0.0)
wr.set_param("MODELP[1]", 4)           # electron-cyclotron resonance mode
wr.run(nray_request=1)
```

### LH (3.7 GHz)

```python
wr.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
wr.set_param("RF", 3.7e9)
wr.set_param("RNZI", 1.8)              # parallel refractive index (key for LH efficiency)
wr.run(nray_request=1)
```

### Multi-ray beam approximation (5 rays)

```python
wr.set_params(RR=6.2, BB=5.3, NRAYMAX=5)
for i in range(1, 6):
    wr.set_param(f"RFIN[{i}]", 170e9)
    wr.set_param(f"RPIN[{i}]", 8.0)
    wr.set_param(f"ZPIN[{i}]", -0.1 + 0.05*(i-1))   # beam spread
wr.run(nray_request=5)
```
