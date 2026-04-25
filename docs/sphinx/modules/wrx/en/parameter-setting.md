# Setting Input Parameters

`wrx` uses the same standard 5-function ABI as `wr`, so there are exactly
two ways to set inputs: `set_params` and `set_param`. There is no
dedicated string-parameter API.

## Method A — scalars (`set_params`)

```python
wrx.set_params(RR=3.0, RA=1.2, BB=3.0, NSMAX=1,
               NRAYMAX=1, NSTPMAX=10000,
               MODELG=2)
```

## Method B — array elements (`set_param`)

Ray launch conditions are **all array parameters** (the same structure as
the `*IN` arrays in `wr`).

```python
wrx.set_param("NRAYMAX", 3)
for i in range(1, 4):
    wrx.set_param(f"RFIN[{i}]", 170.0e9)           # frequency
    wrx.set_param(f"RPIN[{i}]", 3.5)                # launch R
    wrx.set_param(f"ZPIN[{i}]", 0.1*(i-2))          # launch Z (offset)
    wrx.set_param(f"RKRIN[{i}]", 1.0)               # initial wave number
```

## Difference from `wr` for the array form

`wr` provides both **single-ray** parameters (`RF`, `RPI`, ...) and
**multi-ray** arrays (`RFIN`, `RPIN`, ...), but `wrx` only uses the
**multi-ray array form**. Even when `NRAYMAX=1`, you must use the array
form `RFIN[1]`, `RPIN[1]`, etc.

```python
# wr style (single ray with NRAYMAX=1)
wr.set_param("RF", 170e9)          # OK
wr.set_param("RPI", 3.5)           # OK

# wrx style (always arrays)
wrx.set_param("RFIN[1]", 170e9)    # OK (array form even for a single ray)
wrx.set_param("RPIN[1]", 3.5)
# wrx.set_param("RF", 170e9)       # may not work
```

## Specifying the beam shape

The defining feature of `wrx` is specifying **beam curvature and width**.

```python
wrx.set_param("RCURVAIN[1]", 100.0)    # major-axis radius of curvature [m]
wrx.set_param("RCURVBIN[1]", 100.0)    # minor-axis radius of curvature
wrx.set_param("RBRADAIN[1]", 0.05)      # major-axis beam radius (1/e² width) [m]
wrx.set_param("RBRADBIN[1]", 0.05)      # minor-axis beam radius
```

With these specified, propagation is computed as a **finite-width Gaussian
beam** even for a single ray.

## On string parameters

`wrx` has **no string parameters**. `KNAMEQ` is inherited via `pl_*`.

## Pre-validation (`validate`)

```{important}
`wrx` does not currently implement a `validate()` API. Out-of-range values
raise immediately at `set_param` time (`WrxlibParamError`); beam-tracing
failures are detected at `run()` time as `WrxlibRunError`.
```

## Typical setting patterns

### Focused ECRH beam (ITER Upper Launcher scenario)

```python
wrx.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
wrx.set_param("NRAYMAX", 1)
wrx.set_param("RFIN[1]", 170.0e9)
wrx.set_param("RPIN[1]", 8.5)
wrx.set_param("ZPIN[1]", 1.5)
wrx.set_param("ANGPHIN[1]", 20.0)        # toroidal launch angle [deg]
wrx.set_param("RCURVAIN[1]", 200.0)      # focal length of the focusing optics
wrx.set_param("RBRADAIN[1]", 0.02)       # 2 cm beam width
wrx.run(nray_request=1)
```

### Multiple beams (multi-launcher)

```python
wrx.set_params(RR=6.2, BB=5.3, NRAYMAX=4)
for i in range(1, 5):
    wrx.set_param(f"RFIN[{i}]", 170e9)
    wrx.set_param(f"RPIN[{i}]", 8.5)
    wrx.set_param(f"ZPIN[{i}]", -0.5 + 0.3*(i-1))   # array along Z
    wrx.set_param(f"RBRADAIN[{i}]", 0.02)
wrx.run(nray_request=4)
```
