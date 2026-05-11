# Registered Input Parameters

`wrx/wrx_param_registry.f90` registers a total of **70** `CASE` entries —
fewer than `wr` (103) because `wrx` can track a beam with a single ray and
therefore omits some of the multi-ray `*IN` arrays.

## Required and recommended parameters

### Required

`wrx` has no parameter that is unconditionally required. That said, the
**wave conditions** (frequency `RFIN[1]`, launch point `RPIN[1]`,
`ZPIN[1]`, initial wave-number `RKRIN[1]`) need meaningful values.

### Strongly recommended (ITER ECRH scenario)

| Name | Recommended value | Notes |
|---|---|---|
| `RR`     | 6.2 m | Major radius of the device |
| `BB`     | 5.3 T | Toroidal field |
| `RFIN[1]` | 170e9 Hz | ECRH frequency (second harmonic) |
| `RPIN[1]` | 8.5 m | Upper-launcher launch point |
| `ZPIN[1]` | 1.5 m | (same) |
| `NRAYMAX` | 1 | A single ray is enough for `wrx` |
| `RBRADAIN[1]` | 0.02 m | Beam width (1/e²) |
| `RCURVAIN[1]` | 200 m | Focal length |

### Recommended workflow

```python
from wrxlib import Wrxlib

with Wrxlib() as wrx:
    # 1. device
    wrx.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)

    # 2. beam conditions (single ray)
    wrx.set_param("NRAYMAX", 1)
    wrx.set_param("RFIN[1]", 170.0e9)
    wrx.set_param("RPIN[1]", 8.5)
    wrx.set_param("ZPIN[1]", 1.5)
    wrx.set_param("RCURVAIN[1]", 200.0)
    wrx.set_param("RBRADAIN[1]", 0.02)

    # 3. run
    wrx.run(nray_request=1)
    state = wrx.get_state()

    print(f"Total absorbed power: {state.scalars['pwr_tot']:.4e}")
```

---

## 1. Geometry / device

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `RR`    | double | 3.0 | m | Plasma major radius |
| `RA`    | double | 1.2 | m | Plasma minor radius |
| `RB`    | double | 1.4 | m | Wall minor radius |
| `RKAP`  | double | 1.0 | — | Elongation |
| `RDLT`  | double | 0.0 | — | Triangularity |
| `BB`    | double | 3.0 | T | Toroidal field |
| `Q0`    | double | 1.0 | — | Central q |
| `QA`    | double | 3.0 | — | Edge q |
| `RIP`   | double | 3.0 | MA | Plasma current |

## 2. Plasma composition

| Name | Type | Meaning |
|---|---|---|
| `NSMAX`    | int | Number of species |
| `NSAMAX_WR`| int | Active species (`wr`-compatible) |
| `PA[i]`    | double[] | Mass number |
| `PZ[i]`    | double[] | Charge number |
| `PN[i]`    | double[] | On-axis density |
| `PNS[i]`   | double[] | Edge density |
| `PTPR[i]`  | double[] | Parallel temperature |
| `PTPP[i]`  | double[] | Perpendicular temperature |
| `PTS[i]`   | double[] | Edge temperature |

## 3. Profiles

| Name | Type | Meaning |
|---|---|---|
| `PROFJ`   | double | Current-profile exponent |
| `PROFN1[i]`, `PROFN2[i]` | double[] | Density-profile exponents |
| `PROFT1[i]`, `PROFT2[i]` | double[] | Temperature-profile exponents |

## 4. Ray initial conditions (`*IN` arrays)

`wrx` uses the array form even for a single ray.

| Name | Type | Unit | Meaning |
|---|---|---|---|
| `RFIN[i]`     | double[] | Hz | Frequency |
| `RPIN[i]`     | double[] | m | Launch R |
| `ZPIN[i]`     | double[] | m | Launch Z |
| `PHIIN[i]`    | double[] | rad | Toroidal angle |
| `RKRIN[i]`    | double[] | — | Initial k_R |
| `RNZIN[i]`    | double[] | — | $N_\parallel$ |
| `RNPHIIN[i]`  | double[] | — | $N_\varphi$ |
| `ANGZIN[i]`   | double[] | deg | Launch angle (Z) |
| `ANGPHIN[i]`  | double[] | deg | Launch angle (φ) |
| `UUIN[i]`     | double[] | — | Initial power |

## 5. Beam shape (specific to beam tracing)

A group of parameters unique to `wrx`. They specify the focused-beam
geometry.

| Name | Type | Unit | Meaning |
|---|---|---|---|
| `RCURVAIN[i]` | double[] | m | Major-axis radius of curvature (positive: diverging, negative: focusing) |
| `RCURVBIN[i]` | double[] | m | Minor-axis radius of curvature |
| `RBRADAIN[i]` | double[] | m | Major-axis beam radius (1/e² width) |
| `RBRADBIN[i]` | double[] | m | Minor-axis beam radius |
| `MODEWIN[i]`  | int[]    | — | Wave mode of ray i (1: O, 2: X) |

## 6. Computation control

| Name | Type | Default | Meaning |
|---|---|---|---|
| `NRAYMAX` | int | 1 | Number of rays |
| `NSTPMAX` | int | 10000 | Maximum steps per ray |
| `NRSMAX`  | int | -- | Minor-radius profile sample count |
| `NRLMAX`  | int | -- | Major-radius profile sample count |
| `LMAXNW`  | int | -- | Maximum Newton iterations |

## 7. Numerical-integration parameters

| Name | Type | Meaning |
|---|---|---|
| `SMAX`   | double | Maximum ray-path length |
| `DELS`   | double | Step size |
| `EPSRAY` | double | Convergence criterion for ray integration |
| `DELRAY` | double | Computation step |
| `DELDER` | double | Numerical-derivative step |
| `DELKR`  | double | k_R derivative step |
| `EPSNW`  | double | Newton-method convergence criterion |
| `UUMIN`  | double | Minimum-residual-power threshold |

## 8. Operating modes

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MODELG`    | int | 2 | Geometry model |
| `MODELQ`    | int | 0 | q-profile control |
| `MODELP[i]` | int[] | -- | Wave model for species i |
| `MODELV[i]` | int[] | -- | Velocity-distribution model for species i |
| `NCMIN[i]`  | int[] | -- | Minimum resonance order |
| `NCMAX[i]`  | int[] | -- | Maximum resonance order |
| `MDLWRI`    | int | -- | wrx input mode |
| `MDLWRG`    | int | -- | wrx graph mode |
| `MDLWRP`    | int | -- | wrx output mode |
| `MDLWRQ`    | int | -- | wrx quality mode |
| `MDLWRW`    | int | -- | wrx wave mode |
