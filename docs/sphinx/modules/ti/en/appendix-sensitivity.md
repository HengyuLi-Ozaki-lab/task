# Appendix: Input ↔ Output Correspondence

This appendix summarizes the `ti` input → output correspondence,
restricted to **(1) algebraic, deterministic relationships** and **(2)
qualitative trends well established by physics scaling**. Quantities
that depend strongly on the choice of transport model (`MODEL_KAI`,
etc.) are not covered here, since they require dedicated simulations.

```{admonition} Legend
:class: note

- **↑**: increasing the input increases the output (monotonic increase)
- **↓**: increasing the input decreases the output (monotonic decrease)
- **=**: equals the input / determined directly
- **⊕**: turning the input ON adds an extra term
- **~**: holds approximately (higher-order effects may reverse it)
```

## 1. Algebraic / direct relationships

| Input | Affected output | Relation | Notes |
|---|---|---|---|
| `DT × NTMAX` | `state.scalars["T"]` | = | Final time |
| `NSMAX` | `state.nsmax` | = | Number of species in TICOMM |
| `NRMAX` | `state.nrmax` | = | Number of radial mesh points |
| `MODEL_NB = 0` | NBI-related output | all 0 | No heating |
| `MODEL_EC = 0` | ECRF-related output | all 0 | — |
| `MODEL_LH = 0` | LHRF-related output | all 0 | — |
| `MODEL_IC = 0` | ICRF-related output | all 0 | — |
| `MODEL_NF = 0` | Fusion reactions | none | DT, DHe³ disabled |
| `MODEL_NC = 0` | NCLASS | none | Standard transport models take precedence |
| `EPSLOOP / EPSMAT` | Iteration accuracy | ↓ → accuracy ↑, time ↑ | Directly affects compute cost |

## 2. Known physics-scaling trends

### 2.1 Device parameters (`RR`, `RA`, `BB`, `RIP`)

| Input | Affected output | Direction | Physical basis |
|---|---|---|---|
| `RR` ↑ | `state.BETA` (volume-averaged) | ↑ | Volume $V \propto R \cdot a^2$, stored E proportional |
| `RA` ↑ | `state.BETA` | ↑↑ | $V \propto R \cdot a^2$ |
| `BB` ↑ | `state.BETA` | ↓ | $\beta \propto p / B^2$ |
| `BB` ↑ | `state.RQP` (q profile) | ↑ | $q \propto B / I_p$ |
| `RIP` ↑ | `state.RJP` (current density) | ↑ | Total current grows |
| `RIP` ↑ | `state.RQP` | ↓ | $q \propto B / I_p$ — denominator grows |

### 2.2 Initial density / temperature profiles (`PN[i]`, `PT[i]`)

| Input | Affected output | Direction | Physical basis |
|---|---|---|---|
| `PN[i]` ↑ | `state.RNA` near the axis | ↑ | Direct setting |
| `PN[i]` ↑ | `state.BETA` | ↑ | $\beta \propto nT$ |
| `PT[i]` ↑ | `state.RTA` near the axis | ↑ | Direct setting |
| `PT[i]` ↑ | `state.BETA` | ↑ | $\beta \propto nT$ |
| `PNS[i]` ↑ (edge) | Profile shape | flatten | Center-edge contrast shrinks |
| `PROFN1[i]` ↑ | Center of profile becomes flatter | — | Higher exponent in $(1-\rho^P)^Q$ |

### 2.3 Heating (`MODEL_NB`, `MODEL_EC`, …)

| Input | Affected output | Direction | Physical basis |
|---|---|---|---|
| `MODEL_NB ≥ 1` | `state.RTA` (temperature) | ⊕↑ | External heating power added |
| `MODEL_NB ≥ 1` | `state.RJP` (current) | ⊕↑ | NB-driven current |
| `MODEL_EC ≥ 1` | `state.RTA` (electrons) | ⊕↑ | Local electron heating |
| `MODEL_LH ≥ 1` | `state.RJP` | ⊕↑ | LH current drive |
| `MODEL_IC ≥ 1` | `state.RTA` (ions) | ⊕↑ | Local ion heating |

### 2.4 Transport models (`MODEL_KAI`, `MODEL_DRR`, `MODEL_VR`)

| Input | Affected output | Direction | Physical basis |
|---|---|---|---|
| `MODEL_KAI` (large χ) | `state.RTA` profile | flatten | Higher diffusivity |
| `MODEL_NC = 1` (NCLASS ON) | `state.ZEFF` | ~ | Improved consistency with impurities |

For the meaning of each `MODEL_KAI` value, see the transport-model
appendix in the `tr` module
(`docs/sphinx/modules/tr/en/appendix-mdlkai.md`) — `ti` and `tr` use
the same enumeration.

### 2.5 Impurities (`MODEL_PSC`, `PNC`-family)

| Input | Affected output | Direction | Physical basis |
|---|---|---|---|
| Impurity source ON | `state.ZEFF` | ↑ | $Z_\text{eff} = \sum Z_i^2 n_i / n_e$ |
| Impurity source ON | `state.RTA` (temperature) | ↓ | Energy lost via radiation |

### 2.6 Iteration control (`MAXLOOP`, `EPSLOOP`)

| Input | Affected output | Direction | Physical basis |
|---|---|---|---|
| `EPSLOOP` ↓ (stricter) | `state.scalars["residual_loop_max"]` | ↓ | Iterates to a smaller residual |
| `EPSLOOP` ↓ | `state.scalars_int["icount_loop_max"]` | ↑ | More iterations needed |
| `MAXLOOP` ↑ | Probability of convergence | ↑ | More likely to finish under hard conditions |

## How to use this table

When you want to push a particular output toward a target value, use
this table to pick the most promising input to vary.

- **Want to raise temperature** → set `MODEL_NB=1` to enable NBI, or
  raise `PT[i]`
- **Want a more peaked current** → set `MODEL_LH=1` to enable LH
  current drive
- **Want a high-fidelity transport calculation with NCLASS** → set
  `MODEL_NC=1` (you must also set `MODEL_DRR` and `MODEL_VR` to 0;
  see {doc}`faq` Q5)

For quantitative sensitivity, run actual simulations — the
`tilib_sweep` framework is available ({doc}`testing` Layer 4).
