# Registered Input Parameters

`fp/fp_param_registry.f90` registers all **55** `CASE` entries. The
names match the Fortran `/FP/` namelist.

## Required and recommended parameters

### Required (conditionally)

| Condition | Required parameter | Reason |
|---|---|---|
| `MODELG ∈ {3, 5, 8}` | **`KNAMEQ`** (string) | Equilibrium-data file. Set via `set_param_str`. |
| `MODELG = 2` (default) | — | Analytic toroidal geometry; nothing required. |

### Strongly recommended

Because `fp` works on a 5D grid, the **resolution parameters** directly
control output quality.

| Name | Default | Recommended override |
|---|---|---|
| `RR`     | 3.0 m | Per device |
| `RA`     | 1.2 m | Same |
| `BB`     | 3.0 T | Same |
| `RIP`    | 3.0 MA | Same |
| `NSMAX`  | (1) | Number of species in the analysis |
| `NSAMAX` | (1) | Number of active species |
| `NPMAX`  | 50  | 80–200 (depending on accuracy needs) |
| `NTHMAX` | 25  | 50–100 |
| `DELT`   | 0.001 s | ~0.0001 for fast-ion analysis |

### Recommended workflow

```python
from fplib import Fplib

with Fplib() as fp:
    # 1. Device parameters
    fp.set_params(RR=6.2, RA=2.0, BB=5.3, RIP=15.0)

    # 2. 5D grid resolution
    fp.set_params(NSMAX=2, NSAMAX=2, NSBMAX=2,
                  NPMAX=100, NTHMAX=50, NRMAX=20,
                  DELT=0.0005, NTMAX=50)

    # 3. (optional) Via EQDSK
    # fp.set_param("MODELG", 3)
    # fp.set_param_str("KNAMEQ", "eqdata.ITER01")

    fp.run(ntmax=10)
    state = fp.get_state()
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
| `BB`    | double | 3.0 | T | Toroidal magnetic field |
| `RIP`   | double | 3.0 | MA | Plasma current |

## 2. Phase-space dimensions (5D grid)

The distinctive part of `fp`. Compute cost scales with the product of
these.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `NRMAX`  | int | 20 | Number of radial mesh points |
| `NPMAX`  | int | 50 | Number of momentum-space mesh points |
| `NTHMAX` | int | 25 | Number of pitch-angle mesh points |
| `NTMAX`  | int | 100 | Number of time steps |
| `NAVMAX` | int | 100 | Number of averaging steps |

```{note}
Memory consumption is approximately
$N_R \times N_P \times N_\theta \times N_{SA} \times 80$ bytes
(summed over the main internal arrays). With
`NPMAX=200, NTHMAX=100, NRMAX=50, NSAMAX=2` this is about 1.6 GB.
```

## 3. Plasma composition

| Name | Type | Meaning |
|---|---|---|
| `NSMAX`     | int | Total number of species |
| `NSAMAX`    | int | **active species** — the number of species whose distribution functions are solved |
| `NSBMAX`    | int | **bulk species** — the number of species used as collision partners |
| `NS_NSA[i]` | int[] | Maps active species `i` onto an entry of `NSMAX` |
| `NS_NSB[i]` | int[] | Maps bulk species `i` onto an entry of `NSMAX` |
| `PA[i]`     | double[] | Mass number |
| `PZ[i]`     | double[] | Charge number |
| `PN[i]`     | double[] | On-axis initial number density [10²⁰ m⁻³] |
| `PNS[i]`    | double[] | Boundary initial number density |
| `PT[i]`     | double[] | On-axis initial temperature [keV] (Maxwellian-equivalent) |
| `PTPR[i]`   | double[] | Parallel temperature |
| `PTPP[i]`   | double[] | Perpendicular temperature |
| `PTS[i]`    | double[] | Boundary initial temperature |
| `PMAX[i]`   | double[] | Maximum momentum for species i (in normalised units) |

## 4. Time evolution / iteration

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `DELT`   | double | 0.001 | s | Time-step size |
| `EPSFP`  | double | 1e-6 | — | Inner-iteration convergence criterion |
| `LMAXFP` | int    | 100  | — | Maximum number of inner iterations |

## 5. Radial domain

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `R1`    | double | 0.0 | — | Inner boundary (normalised radius) |
| `DELR1` | double | 0.05 | — | Mesh spacing |
| `RMIN`  | double | 0.0 | — | Minimum of the computational range |
| `RMAX`  | double | 1.0 | — | Maximum of the computational range |

## 6. Physical parameters

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `E0`    | double | 0.0 | V/m | Inductive electric field on axis |
| `ZEFF`  | double | 1.0 | — | Effective charge (background plasma) |

## 7. Wave heating

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `PABS_EC` | double | 0.0 | MW | ECRF absorbed power |
| `PABS_LH` | double | 0.0 | MW | LHRF absorbed power |
| `PABS_FW` | double | 0.0 | MW | Fast-wave absorbed power |
| `PABS_WR` | double | 0.0 | MW | From ray tracing |
| `PABS_WM` | double | 0.0 | MW | From full-wave |
| `RF_WM`   | double | 0.0 | Hz | Full-wave frequency |

## 8. Mode switches

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MODELG` | int | 2 | Geometry model (2: analytic, 3: TASK/EQ, 5: EQDSK) |
| `MODELE` | int | 1 | Energy operator (1: linear, 2: relativistic) |
| `MODELR` | int | — | Radial-direction model |
| `MODELS` | int | 0 | Particle-source model |
| `MODELD` | int | — | Diffusion model |
| `MODELC` | int | 0 | Collision model |
| `MODELW` | int | 0 | Wave model |

## 9. Physical sub-module switches (`MODEL_*`)

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MODEL_NBI`     | int | 0 | NBI particle source |
| `MODEL_WAVE`    | int | 0 | Wave drive (LH, FW, etc.) |
| `MODEL_DISRUPT` | int | 0 | Disruption (runaway) mode |
| `MODEL_BS`      | int | 0 | Bootstrap-current contribution |
| `MODEL_LOSS`    | int | 0 | Loss processes |
| `MODEL_SYNCH`   | int | 0 | Synchrotron radiation |
| `MODEL_FOW`     | int | 0 | Finite-orbit-width effect |

## 10. String parameters (via `set_param_str`)

| Name | Type | Default | Meaning |
|---|---|---|---|
| `KNAMEQ` | CHARACTER(80) | (inherited from `pl_init`) | Equilibrium-data file name |

```python
fp.set_param_str("KNAMEQ", "eqdata.ITER01")
```
