# Registered Input Parameters

`ti/ti_param_registry.f90` registers a total of **77 `CASE` entries**.
The names match the Fortran `/TI/` namelist. Defaults are set in
`ti/tiinit.f90`.

## Required and recommended parameters

`ti` runs with defaults out of the box, but for physically meaningful
results the following overrides are recommended.

### Required (conditional)

`ti` has no string parameters and does not require external files such
as `KNAMEQ`. **Strictly speaking, no parameter is mandatory.**

### Strongly recommended (defaults are too generic)

| Name | Default | Suggested override (ITER scenario) |
|---|---|---|
| `RR`     | 3.0 m  | 6.2 m |
| `RA`     | 1.2 m  | 2.0 m |
| `BB`     | 3.0 T  | 5.3 T |
| `RIP`    | 3.0 MA | 15.0 MA |
| `NSMAX`  | 2     | depends on the analysis (2–8) |
| `DT`     | 0.01 s | depends on the simulated duration |
| `NTMAX`  | 100    | same |

### Additional flags when including heating physics

| Name | Value | Effect |
|---|---|---|
| `MODEL_NB` | 1 | NBI heating ON |
| `MODEL_EC` | 1 | ECRF ON |
| `MODEL_NC` | 1 | NCLASS neoclassical transport ON (cannot be combined with other models) |

### Recommended workflow

```python
from tilib import Tilib

with Tilib() as ti:
    # 1. Device parameters
    ti.set_params(RR=6.2, RA=2.0, BB=5.3, RIP=15.0,
                  NSMAX=2,
                  DT=0.01, NTMAX=100)

    # 2. (Optional) heating model
    ti.set_param("MODEL_NB", 1)

    # 3. ti has no validate(); rely on set_param errors to catch mistakes
    try:
        ti.run(ntmax=10)
    except Exception as e:
        print(f"Run failed: {e}")
        raise

    state = ti.get_state()
```

---

## 1. Geometry / device

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `RR`    | double | 3.0 | m | Plasma major radius |
| `RA`    | double | 1.2 | m | Plasma minor radius |
| `RKAP`  | double | 1.5 | — | Elongation |
| `RDLT`  | double | 0.0 | — | Triangularity |
| `BB`    | double | 3.0 | T | Toroidal field |
| `RIP`   | double | 3.0 | MA | Plasma current |

## 2. Plasma composition

`ti` provides a rich set of per-species attribute arrays so that ions,
impurities, and fast ions can be managed by charge state.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `NSMAX`     | int          | 2   | — | Number of main species |
| `PA[i]`     | double[NSMM] | (per species) | — | Mass number |
| `PZ[i]`     | double[NSMM] | (per species) | — | Charge number |
| `PN[i]`     | double[NSMM] | (per species) | 10²⁰ m⁻³ | Initial axis number density |
| `PNS[i]`    | double[NSMM] | (per species) | 10²⁰ m⁻³ | Initial boundary number density |
| `PT[i]`     | double[NSMM] | (per species) | keV | Initial axis temperature |
| `PTPR[i]`   | double[NSMM] | -- | keV | Parallel temperature |
| `PTPP[i]`   | double[NSMM] | -- | keV | Perpendicular temperature |
| `PTS[i]`    | double[NSMM] | (per species) | keV | Initial boundary temperature |
| `PU[i]`     | double[NSMM] | 0.0 | m/s | Toroidal flow velocity |
| `PUS[i]`    | double[NSMM] | 0.0 | m/s | Boundary toroidal flow |
| `NPA[i]`    | int[NSMM] | -- | — | Mass number per species (integer) |
| `ID_NS[i]`  | int[NSMM] | -- | — | Species ID |
| `NZMIN_NS[i]` | int[NSMM] | -- | — | Minimum charge state |
| `NZMAX_NS[i]` | int[NSMM] | -- | — | Maximum charge state |
| `NZINI_NS[i]` | int[NSMM] | -- | — | Initial charge state |

## 3. Profile shape (per species)

Unlike `tr`, `ti` lets you specify **profile-shape exponents per
species**.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `PROFN1[i]` | double[NSMM] | 2.0 | Density profile exponent 1 for species `i` |
| `PROFN2[i]` | double[NSMM] | 0.5 | Density profile exponent 2 for species `i` |
| `PROFT1[i]` | double[NSMM] | 2.0 | Temperature profile exponent 1 for species `i` |
| `PROFT2[i]` | double[NSMM] | 1.0 | Temperature profile exponent 2 for species `i` |
| `PROFU1[i]` | double[NSMM] | 2.0 | Flow velocity exponent 1 for species `i` |
| `PROFU2[i]` | double[NSMM] | 1.0 | Flow velocity exponent 2 for species `i` |
| `PROFJ1`   | double | 2.0 | Current profile exponent 1 |
| `PROFJ2`   | double | 1.0 | Current profile exponent 2 |
| `MODEL_PROF`  | int switch | 0 | Source of profile data |
| `MODEL_NPROF` | int switch | 0 | Density-profile selector |

## 4. Time evolution / iteration

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `DT`       | double | 0.01 | s | Time step width |
| `NRMAX`    | int    | 50   | — | Number of radial mesh points |
| `NTMAX`    | int    | 100  | — | Number of time steps |
| `NTSTEP`   | int    | 10   | — | Snapshot interval |
| `NGTSTEP`  | int    | 2    | — | Time-evolution graph interval |
| `NGRSTEP`  | int    | 100  | — | Profile graph interval |
| `MAXLOOP`  | int    | 100  | — | Maximum inner-iteration count |
| `EPSLOOP`  | double | 1e-6 | — | Inner-iteration convergence tolerance |
| `EPSMAT`   | double | 1e-8 | — | Matrix-solver convergence tolerance |
| `MATTYPE`  | int switch | 0 | — | Matrix-solver type |

## 5. Boundary conditions

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MODEL_BND`  | int switch | 0 | Boundary-condition model |
| `BND_VALUE`  | double | -- | Boundary value |

## 6. Diffusion / convection

| Name | Type | Default | Meaning |
|---|---|---|---|
| `DN0`   | double | 0.1 | Density diffusion coefficient (reference) |
| `DT0`   | double | 1.0 | Temperature diffusion coefficient (reference) |
| `DU0`   | double | 0.1 | Flow-velocity diffusion coefficient |
| `VDN0`  | double | 0.0 | Density pinch velocity |
| `VDT0`  | double | 0.0 | Temperature pinch velocity |
| `VDU0`  | double | 0.0 | Flow-velocity pinch velocity |
| `DR0`   | double | 1.0 | Radial coefficient (reference) |
| `DRS`   | double | 1.0 | Radial coefficient (edge) |
| `DN0_NS[i]`  | double[NSMM] | per species | `DN0` for species `i` |
| `DT0_NS[i]`  | double[NSMM] | per species | `DT0` for species `i` |
| `DU0_NS[i]`  | double[NSMM] | per species | `DU0` for species `i` |
| `VDN0_NS[i]` | double[NSMM] | per species | `VDN0` for species `i` |
| `VDT0_NS[i]` | double[NSMM] | per species | `VDT0` for species `i` |
| `VDU0_NS[i]` | double[NSMM] | per species | `VDU0` for species `i` |

## 7. Module switches (`MODEL_*`)

A defining feature of `ti` is that **18+ `MODEL_*` switches** turn
physics modules ON/OFF.

### Equilibrium / initialization

| Name | Default | Meaning |
|---|---|---|
| `MODEL_EQB` | 0 | Equilibrium boundary model |
| `MODEL_EQN` | 0 | Equilibrium density model |
| `MODEL_EQT` | 0 | Equilibrium temperature model |
| `MODEL_EQU` | 0 | Equilibrium flow-velocity model |

### Transport models

| Name | Default | Meaning |
|---|---|---|
| `MODEL_KAI` | 31 | Turbulent thermal transport (same as `MDLKAI` in `tr`; default = CDBM) |
| `MODEL_DRR` | 3  | Particle-diffusion model (same as `MDLAD` in `tr`) |
| `MODEL_VR`  | 3  | Heat-pinch model (same as `MDLAVK` in `tr`) |
| `MODEL_NC`  | 0  | NCLASS neoclassical transport |

### Heating / current drive

| Name | Default | Meaning |
|---|---|---|
| `MODEL_NB`   | 0 | NBI heating |
| `MODEL_EC`   | 0 | ECRF heating |
| `MODEL_LH`   | 0 | LHRF heating |
| `MODEL_IC`   | 0 | ICRF heating |
| `MODEL_CD`   | 0 | Current drive (general) |
| `MODEL_SYNC` | 0 | Synchrotron radiation |

### Particle sources / wall

| Name | Default | Meaning |
|---|---|---|
| `MODEL_NF`  | 0 | Fusion reactions |
| `MODEL_PEL` | 0 | Pellet injection |
| `MODEL_PSC` | 0 | Particle source |

### Operating mode (`MODELG`, `MODELQ`)

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MODELG` | int | 2 | Geometry model (same as in `tr`/`eq`; default = analytic toroidal) |
| `MODELQ` | int | 0 | Safety-factor model |

```{note}
The allowed values of `MODEL_KAI` are the same enumeration as `MDLKAI`
in `tr`. For the full list of models, see the transport-model appendix
in the `tr` module (`docs/sphinx/modules/tr/en/appendix-mdlkai.md`).
```

```{warning}
Do not combine `MODEL_NC=1` (NCLASS) with `MODEL_DRR` or `MODEL_VR`.
NCLASS computes neoclassical coefficients itself, leading to
double-counting ({doc}`faq` Q5).
```
