# Appendix: Input ↔ Output Correspondence

This appendix summarises the input → output relationships in `fp`. It
is restricted to **(1) algebraically determined relations** and
**(2) physical scalings**.

```{admonition} Legend
:class: note

- **↑**: Increasing the input increases the output.
- **↓**: Increasing the input decreases the output.
- **=**: Equal to / directly determined by the input.
- **⊕**: Turning the input on adds an extra term.
- **~**: Holds approximately (higher-order effects can reverse the trend).
```

## 1. Algebraic / direct relations

| Input | Output mainly affected | Relation | Notes |
|---|---|---|---|
| `DELT × NTMAX` | `state.timefp` | = | Final time |
| `NRMAX`, `NPMAX`, `NTHMAX` | Grid resolution + memory consumption | = | 5D grid |
| `NSAMAX` | `state.nsamax` | = | Number of active species |
| `MODEL_NBI = 0` | NBI source | none | — |
| `MODEL_WAVE = 0` | Wave-drive term | none | — |
| `MODEL_DISRUPT = 0` | Runaway | none | Steady state |
| `MODELE = 1` (non-relativistic) | Energy operator | linear | Errors at high particle energies |
| `EPSFP / LMAXFP` | Iterative accuracy | ↓ raises accuracy, ↑ raises cost | — |

## 2. Known physical-scaling tendencies

### 2.1 Grid resolution

| Input | Output mainly affected | Direction | Physical reason |
|---|---|---|---|
| `NPMAX` ↑ | Distribution-tail resolution | ↑ | Fast-particle tails become visible |
| `NPMAX` ↑ | Memory and run time | ↑↑ | Proportional to 5D-array size |
| `NTHMAX` ↑ | Resolution of pitch-angle structure | ↑ | Beam peaks, wave resonances |
| `NRMAX` ↑ | Radial-profile accuracy | ↑ | Usually 50 or fewer is enough |
| `DELT` ↓ | Time-integration accuracy | ↑ | Captures sharp initial transients |

### 2.2 Physical parameters

| Input | Output mainly affected | Direction | Physical reason |
|---|---|---|---|
| `BB` ↑ | `state.RJT` (current density) | ~ | Stronger magnetic confinement |
| `RIP` ↑ | `state.RJT` normalisation | ↑ | Total current rises |
| `ZEFF` ↑ | `state.RPCT` (collisional power) | ↑ | $\nu_{ee}, \nu_{ei} \propto Z_\text{eff}$ |
| `E0` (inductive E-field) ↑ | `state.RJT` runaway contribution | ↑ | Acceleration term ∝ E |
| `PT[i]` ↑ (initial temperature) | `state.RTT` initial value | ↑ | Set directly |

### 2.3 Heating and particle sources

| Input | Output mainly affected | Direction | Physical reason |
|---|---|---|---|
| `MODEL_NBI ≥ 1` | `state.RNT` fast ions | ⊕↑ | NBI source ON |
| `MODEL_NBI ≥ 1` | `state.RWT` high-energy component | ⊕↑ | Beam energy added |
| `MODEL_WAVE ≥ 1`, `PABS_LH` ↑ | `state.RPWT` (LH contribution) | ⊕↑ | Wave-heating term |
| `MODEL_WAVE ≥ 1`, `PABS_LH` ↑ | `state.RJT` (LH drive) | ⊕↑ | LH current drive |
| `MODEL_WAVE ≥ 1`, `PABS_EC` ↑ | `state.RPWT` (EC contribution) | ⊕↑ | Electron-cyclotron heating |

### 2.4 Collisions and losses

| Input | Output mainly affected | Direction | Physical reason |
|---|---|---|---|
| `NSBMAX` ↑ (number of bulk species) | `state.RPCT` (collisional power) | ↑ | More collision partners |
| `MODEL_LOSS ≥ 1` | `state.RNT` (particle density) | ↓ | Particle-loss term |
| `MODEL_SYNCH ≥ 1` | `state.RPCT` (radiation) | ↓ | Synchrotron-radiation losses |

### 2.5 Iteration control

| Input | Output mainly affected | Direction | Notes |
|---|---|---|---|
| `EPSFP` ↓ | Iterative accuracy | ↑ | Stricter convergence criterion |
| `LMAXFP` ↑ | Likelihood of converging | ↑ | Maximum allowed iterations |

## How to use this table

When tuning a target output:

- **Current-drive efficiency** → enable LH drive with `MODEL_WAVE=1,
  PABS_LH > 0`, then read `state.RJT`.
- **Fast-ion buildup under NBI** → set `MODEL_NBI=1`, time-step, and
  watch `state.RNT[isa]` and `state.RWT[isa]`.
- **Runaway-electron generation** → set `MODEL_DISRUPT=1` and raise
  `E0`.
- **Avoid memory errors** → keep `NPMAX`, `NTHMAX` modest
  ({doc}`faq` Q7).

For quantitative sensitivity, run the simulation — see the
`fplib_sweep` framework.
