# Appendix: Input ↔ Output Correspondence

This appendix summarises how the outputs in `TrState` move when
input parameters change. We restrict ourselves to **(1) algebraic
relationships** and **(2) qualitative trends widely accepted as
physical scaling**. Quantities whose result changes substantially
with the choice of transport model (`MDLKAI` etc.) require
case-by-case simulations and are not covered here
(see {doc}`appendix-mdlkai`).

```{admonition} Legend
:class: note

- **↑**: output increases when input increases (monotonic increase)
- **↓**: output decreases when input increases (monotonic decrease)
- **=**: equal to / directly determined by the input
- **⊕**: turning the input on adds a new term
- **~**: roughly holds (higher-order effects can flip the sign)
```

## 1. Algebraic / direct relations

Things determined for certain without running the simulation.

| Input | Output | Relation | Note |
|---|---|---|---|
| `DT` × `NTMAX` | `T` (time) | `T = DT × NTMAX` | final time when `run` finishes |
| `NSMAX` | `state.nsmax` | `nsmax = NSMAX` | second-axis size of the output arrays |
| `RIPS = RIPE` | plasma current | `Ip = RIPS` for all time (steady) | with different values, linear ramp |
| `RIPS ≠ RIPE` | plasma current | `RIPS` at t=0, `RIPE` at end, linear interpolation | — |
| `MODELG = 3` | required input | `KNAMEQ` file must exist | otherwise `validate()` in {doc}`parameter-setting` reports `FILE_MISSING` |
| `MDLNB = 0` | NBI inputs | `PNBR0`, `PNBRW`, `PNBENG`, `PNBRTG` all ignored | — |
| `MDLEC = 0` | ECRF inputs | `PECCD`, `PECR0`, `PECRW`, `PECNPR` ignored | — |
| `MDLLH = 0` | LH inputs | `PLHCD`, `PLHR0`, `PLHRW`, `PLHNPR`, `PLHTOT` ignored | — |
| `MDLIC = 0` | ICRF inputs | `PICCD`, `PICR0`, `PICRW`, `PICNPR` ignored | — |
| `MDLPEL = 0` | pellet | no pellet particle source | — |
| `MDLNF = 0` | fusion | no DT / DHe³ reactions → no α-particle heating | — |
| `MDLIMP = 0` | impurities | `PNC` ignored, `ZEFF0 ≈ 1` | pure hydrogen plasma approximation |

## 2. Known physical scaling trends

Qualitative trends widely accepted in the research community. The
absolute value depends on the model, but the direction is largely
model-independent.

### 2.1 Geometry / device (`RR`, `RA`, `RKAP`, `BB`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `RR` ↑ | `WPT` | ↑ | plasma volume $V \propto R \cdot a^2$ |
| `RA` ↑ | `WPT` | ↑↑ | $V \propto R \cdot a^2$ — `RA` matters more |
| `RKAP` ↑ (elongation) | `WPT` | ↑ | volume $\propto \kappa$, plus higher density limit due to better stability |
| `BB` ↑ | `BETA0`, `BETAA` | ↓ | $\beta = 2\mu_0 p / B^2$ |
| `BB` ↑ | `Q0`, `QP` | ↑ | $q \propto B / I_p$ |
| `BB` ↑ | `TAUE1`, `TAUE2` | ~↑ | most scaling laws give $\tau_E \propto B^{0.15{\sim}0.3}$ |

### 2.2 Plasma current (`RIPS`, `RIPE`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `RIPS` ↑ | `AJT` (total current) | = | direct |
| `RIPS` ↑ | `Q0`, `QP` (all $q$) | ↓ | $q \propto B / I_p$ |
| `RIPS` ↑ | `RQ1` (radius of $q=1$ surface) | ↑ | the whole $q$ profile drops, pushing $q=1$ outward |
| `RIPS` ↑ | `BETAN` (normalised $\beta$) | ↓ | $\beta_N = \beta_A / (I_p/(aB))$ — denominator grows |
| `RIPS` ↑ | `TAUE1`, `TAUE2` | ~↑ | scaling laws give $\tau_E \propto I_p^{0.7{\sim}0.9}$ |
| `RIPS` ↑ | `ALI` (internal inductance) | ~↓ | tendency for the current profile to flatten |

### 2.3 Initial density / temperature profile (`PN[i]`, `PT[i]`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `PN[i]` ↑ (axis density) | `WPT` | ↑ | $W \propto \int n T\, dV$ |
| `PN[i]` ↑ | `BETA0`, `BETAA` | ↑ | $\beta \propto p = nT$ |
| `PN[i]` ↑ | `TAUE1` | ~↑ | scaling laws give $\tau_E \propto n^{0.4{\sim}0.5}$ |
| `PT[i]` ↑ (axis temperature) | `WPT` | ↑ | same as above |
| `PT[i]` ↑ | `BETA*` | ↑ | $\beta \propto p$ |
| `PT[i]` ↑ | `TAUE1`, `TAUE2` | ~↓ | higher temperature tends to increase transport |
| `PNS[i]` ↑ (edge density) | density profile | flatten | core–edge gap shrinks → smaller gradient |
| `PTS[i]` ↑ (edge temperature) | `WPT` | ↑ | edge temperature pedestal raised |
| `PROFN1` ↑ | density profile | flatter centre | the exponent in $(1-\rho^{P_1})^{P_2}$ steepens |
| `PROFN2` ↑ | density profile | sharper outer | same as above |

### 2.4 Heating systems (`MDLNB`, `MDLEC`, `MDLLH`, `MDLIC`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `MDLNB ≥ 1` (NBI ON) | `WPT` | ⊕↑ | external heating power added |
| `MDLNB ≥ 1` | `AJT` | ⊕↑ | NB-driven current adds to total |
| `MDLNB ≥ 1` | `TAUE1` | ~↓ | power degradation: $\tau_E \propto P^{-0.5{\sim}-0.7}$ |
| `PNBENG` ↑ | NB driven current | ↑ | higher beam energy → better CD efficiency |
| `MDLEC ≥ 1` (ECRF ON) | `WPT`, $T_e$ profile | ⊕↑ | local electron heating |
| `MDLLH ≥ 1` (LH ON) | `AJT` | ⊕↑ | LH current drive |
| `MDLLH ≥ 1`, `PLHTOT` ↑ | `WPT` | ⊕↑ | proportional to input power |
| `MDLIC ≥ 1` (ICRF ON) | $T_i$ profile | ⊕↑ | local ion heating |
| `PNBR0`, `PECR0` toward axis | profile peaking | ↑ | temperature gradient steepens at the heating location |

### 2.5 Simple scale of the transport coefficients (`CK0`, `CK1`)

These act directly when `MDLKAI` is a constant-coefficient model
(`0`–`9`).

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `CK0` ↑ (electron χ coefficient) | $T_e$ profile | flatten | larger diffusivity |
| `CK0` ↑ | `WPT` | ↓ | $T_e$ drops |
| `CK0` ↑ | `TAUE1`, `TAUE2` | ↓ | $\tau_E \propto 1/\chi$ |
| `CK1` ↑ (ion χ coefficient) | $T_i$ profile | flatten | same as above |
| `CK1` ↑ | `BETAN` | ↓ | $T_i$ drops |

### 2.6 Impurities (`MDLIMP`, `PNC`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `MDLIMP ≥ 1`, `PNC` ↑ | `ZEFF0` | ↑ | $Z_\text{eff} = \sum Z_i^2 n_i / n_e$ |
| `MDLIMP ≥ 1`, `PNC` ↑ | radiative loss (`PRADT`, ...) | ↑ | bremsstrahlung / line radiation from high-Z impurities |
| `MDLIMP ≥ 1`, `PNC` ↑ | `WPT` | ↓ | energy loss due to higher radiation |

### 2.7 Fusion (`MDLNF`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `MDLNF ≥ 1` (DT ON) | `WPT` | ⊕↑ | α-particle heating (3.5 MeV per reaction) |
| `MDLNF ∈ {2, 4, 6}` | `PN[2]`, `PN[3]` (D, T) | ↓ | DT burn consumes D and T |
| `MDLNF ∈ {2, 4, 6}` | `PN[4]` (He) | ↑ | α-particle accumulation |

## How to use

When you want to push a particular output toward a target value, use
the table above to estimate "which input to move". Examples:

- **To raise `BETAN`**: raise `PN`/`PT`, or lower `BB`, or lower
  `Ip` (but lowering `BB` too far hurts stability, and lowering
  `Ip` too far raises `q` — both create new problems).
- **To extend `TAUE1`**: raise `Ip`, `B`, `n`; conversely keep the
  heating power `P` modest (power degradation).
- **To see the breakdown of `AJT`**: switch `MDLNB`, `MDLLH`,
  `MDLEC` while sweeping `MDLJBS`.

For a quantitative sensitivity (e.g. how much `WPT` rises when `RR`
increases by 10 %), run a simulation — the `tr_sweep` framework
exists for exactly that purpose
(see Layer 4 in {doc}`testing`).
