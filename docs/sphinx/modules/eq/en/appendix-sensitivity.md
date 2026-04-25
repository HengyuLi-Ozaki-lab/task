# Appendix: Input ↔ Output Correspondence

This appendix summarises how the `EqState` outputs change as you vary
the input parameters. It covers only **(1) algebraically determined
relationships** and **(2) qualitative trends widely accepted as
physical scaling**. Quantities that depend on detailed profile shape
(higher-order effects of `PP*`, `PJ*`, `FF*`) and that you only know
after solving are not covered here.

```{admonition} Legend
:class: note

- **↑**: increasing the input increases the output (monotonically increasing)
- **↓**: increasing the input decreases the output (monotonically decreasing)
- **=**: equal to / directly determined by the input
- **~**: roughly true (higher-order effects may reverse it)
```

## 1. Algebraic / direct relationships

These are determined without solving the equilibrium.

| Input | Output | Relation | Note |
|---|---|---|---|
| `RIP` | `state.scalars["ripx"]` | ≈ | `ripx` is the total current after the solver converges; usually equal to `RIP` (mismatch ⇒ unconverged) |
| `RGMIN`, `RGMAX` | `state.rg` (R-grid extent) | = | the interval `[RGMIN, RGMAX]` is divided into `nrgmax` points |
| `ZGMIN`, `ZGMAX` | `state.zg` (Z-grid extent) | = | same |
| `NRGMAX` | `state.nrgmax` | = | number of R-grid points |
| `NZGMAX` | `state.nzgmax` | = | number of Z-grid points |
| `NPSMAX` | `state.npsmax` | = | number of ψ-surface samples |
| `NRMAX`, `NTHMAX` | `state.nrmax`, `state.nthmax` | = | resolution of the ψ mesh |
| `MODELG ∈ {3, 5, 8}` | required input | the file referenced by `KNAMEQ` must exist | `validate` returns `FILE_MISSING` |
| `MODELG = 2` | `KNAMEQ` ignored | — | analytic toroidal path does not use it |

## 2. Trends known as physical scaling

Qualitative trends that are widely accepted in the research community.

### 2.1 Device parameters (`RR`, `RA`, `RKAP`, `RDLT`, `BB`, `RIP`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `RR` ↑ | `pvol` (volume) | ↑ | $V \propto R \cdot a^2$ |
| `RR` ↑ | `raxis` | ↑ | the device centre shifts outward |
| `RR` ↑ | `qaxis` | ↑ | $q \propto B/(I \cdot R^{-1})$ — major-radius effect |
| `RA` ↑ | `pvol` | ↑↑ | $V \propto R \cdot a^2$ — `RA` has stronger leverage |
| `RA` ↑ | `qsurf` | ~↓ | surface $q \propto B \cdot a / (R \cdot I)$ — $a$ ↑ |
| `RKAP` ↑ (elongation) | `pvol` | ↑ | volume $\propto \kappa$ |
| `RKAP` ↑ | `betat`, `betap` | ~↑ | shape-related stability improvement |
| `RDLT` ↑ (triangularity) | higher-order surface distortion | — | first-order effect on scalars is small |
| `BB` ↑ | `betat`, `betap` | ↓ | $\beta = 2\mu_0 \langle p \rangle / B^2$ |
| `BB` ↑ | `qaxis`, `qsurf` | ↑ | $q \propto B / I$ |
| `RIP` ↑ | `qaxis`, `qsurf` | ↓ | $q \propto B / I$ — denominator increases |
| `RIP` ↑ | `betap` | ↑ | $\beta_p \propto p / B_p^2 \propto p R / I^2$ — model-dependent in detail |

### 2.2 Safety-factor constraints (`Q0`, `QA`, `QMIN`)

These act directly when `MDLEQF=4` (supplied profiles: $P, q$).

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `Q0` (supplied central q) | `state.scalars["qaxis"]` | ≈ | solved to match |
| `QA` (supplied surface q) | `state.scalars["qsurf"]` | ≈ | same |
| `QMIN` (reversed shear) | minimum of the `qqps` profile | = | minimum q of a reversed-shear configuration |

### 2.3 Pressure profile (`PP0`, `PP1`, `PP2`, `PROFP*`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `PP0` ↑ (main amplitude) | `state.ppps` (pressure profile) | ↑ | $p$ near the axis rises directly |
| `PP0` ↑ | `betat`, `betap` | ↑ | $\beta \propto \langle p \rangle$ |
| `PP1` ↑ (secondary) | `state.ppps` near the centre | ↑ | added centre-peaking |
| `PP2` ↑ (ITB component) | profile peaking | ↑ | added only inside the ITB |
| `PROFP0` ↑ | profile shape | flatter centre | exponent of $(1-\psi^{P_R})^{P_{P0}}$ increases |

### 2.4 Current profile (`PJ0`, `PJ1`, `PJ2`, `PROFJ*`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `PJ0` ↑ (main) | $j(\psi)$ profile | ↑ | central current density rises |
| `PJ0` ↑ | `qaxis` | ↓ | central current ↑ ⇒ central $q$ ↓ |
| `PJ0` ↑ | `state.scalars["ripx"]` | ↑ | the integral of the total current rises |
| `PROFJ0` ↑ | $j$ profile | centre-concentrated | flattens by exponent |

### 2.5 Mesh resolution (`NSGMAX`, `NRGMAX`, `NPSMAX`, …)

Higher mesh resolution **approaches the true answer**, at the cost of
longer compute time.

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `NSGMAX` ↑ | precision of the equilibrium solution | ↑ | Grad-Shafranov convergence |
| `NRGMAX`, `NZGMAX` ↑ | resolution in the R-Z plane | ↑ | plotting precision |
| `NPSMAX` ↑ | resolution of ψ-surface profiles | ↑ | more sample points in `state.psips` etc. |
| `NRMAX`, `NTHMAX` ↑ | flux-coordinate resolution | ↑ | precision of higher-order analyses |

In practice, the defaults are sufficient for many cases.

### 2.6 Iteration control (`EPSEQ`, `NLPMAX`)

| Input | Mainly affected output | Direction | Physical basis |
|---|---|---|---|
| `EPSEQ` ↓ (tighter tolerance) | solution precision | ↑ | iteration is more strict |
| `EPSEQ` ↓ | compute time | ↑ | more iterations |
| `EPSEQ` too small | `EqlibCalculationFailedError` | — | error if the iteration does not converge within `NLPMAX` |
| `NLPMAX` ↑ | likelihood of convergence | ↑ | rescues unconverged cases |

### 2.7 Mode switches (`MODELG`, `MDLEQF`)

| Input | Effect |
|---|---|
| `MODELG=2` (analytic) | `KNAMEQ` not needed; solves with built-in profiles |
| `MODELG=3` (TASK/EQ) | `KNAMEQ` required; reads a TASK-native equilibrium |
| `MODELG=5` (EQDSK) | `KNAMEQ` required; G-EQDSK standard format |
| `MDLEQF=0` (default) | supply $P, J_\text{tor}, T, V_\varphi$ + $I_p$ |
| `MDLEQF=1` | supply $P, F$ + $I_p$ — high-energy regime studies |
| `MDLEQF=4` | supply $P, q$ — for directly specifying the q profile |

## How to use this table

Use the table to guess "which input to move" when you want to push a
specific output toward a target value. Examples:

- **Raise `betat`** → raise `PP*` or lower `BB` (but lowering `BB`
  too far can drive `qaxis<1` and trigger MHD instability concerns)
- **Raise `qaxis`** → raise `BB` or lower `RIP` (the total current is
  set indirectly through `PJ0` etc.)
- **Match the magnetic-axis position `raxis` to an ITER reference
  value** → tune the combination of `RR`, `RKAP`, `RDLT`
- **Grad-Shafranov fails to converge** → relax `EPSEQ`, raise
  `NLPMAX`, or use physically reasonable initial profiles

For quantitative sensitivity (e.g. by what percentage does `pvol`
rise when `RR` is raised by 10 %), run a simulation. The
`eqlib_sweep` framework exists for exactly that purpose
({doc}`testing` Layer 4).
