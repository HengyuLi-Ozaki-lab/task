# Appendix: `MDLKAI` Transport Model Details

`MDLKAI` is the integer switch that selects the turbulent
heat-transport model. Each value picks a different physics model.
The default is `MDLKAI=31` (CDBM F(s,α,κq)).

The values are defined in the comments at `tr/trinit.f90:211-276`,
and this page is a complete transcription. We organise the families
by section, and at the end we provide the full mapping table for all
41 values.

## 0–9: CONSTANT COEFFICIENT

The simplest models. They give the diffusion coefficient as an
analytic function. Used as a baseline for physics benchmarking and
numerical tests.

| Value | Functional form |
|---|---|
| 0 | $\chi = C \cdot (1 + A\rho^2)$ |
| 1 | $\chi = C / (1 - A\rho^2)$ |
| 2 | $\chi = C \cdot (\partial T_i/\partial\rho)^B / (1 - A\rho^2)$ |
| 3 | $\chi = C \cdot (\partial T_i/\partial\rho)^B \cdot T_i^C$ |

$C$ is a constant coefficient (`CK0`, `CK1`); $\rho$ is the
normalised radius.

## 10–19: DRIFT WAVE (+ITG +ETG)

Drift-wave family of turbulence models. Based on ITG (Ion Temperature
Gradient) and ETG (Electron Temperature Gradient) instabilities. The
parameter $\eta_c$ is the threshold for $\eta = L_n/L_T$.

| Value | Model |
|---|---|
| 10 | $\eta_c = 1$ |
| 11 | $\eta_c = 1$, suppression $1/(1+\exp(\cdot))$ |
| 12 | $\eta_c = 1$, $1/(1+\exp) \cdot q$ |
| 13 | $\eta_c = 1$, $1/(1+\exp) \cdot (1+q^2)$ |
| 14 | $\eta_c = 1 + 2.5(L_n/R_R - 0.2)$, $1/(1+\exp)$ |
| 15 | $\eta_c = 1$, $1/(1+\exp) \cdot \mathrm{func}(q, \varepsilon, L_n)$ |
| 16 | (15) + ZONAL FLOW effect |

## 20–29: REBU-LALLA

The empirical Rebu-Lalla model.

| Value | Model |
|---|---|
| 20 | Rebu-Lalla model |

## 30–40: CDBM family (Current-Diffusivity-driven Ballooning Mode)

Current-diffusivity-driven ballooning mode. **The default
`MDLKAI=31`** belongs here and is TASK's default analysis model.
Parameters:

- $s$: magnetic shear
- $\alpha$: pressure-gradient parameter
- $\kappa_q$: safety-factor-dependent correction
- $W_{E1}$: ExB shear
- $a/R$: inverse aspect ratio

| Value | Model form |
|---|---|
| 30 | CDBM $1/(1+s)$ |
| **31 (default)** | **CDBM $F(s, \alpha, \kappa_q)$** |
| 32 | CDBM $F(s, \alpha, \kappa_q)/(1 + W_{E1}^2)$ — ExB-shear-suppressed variant |
| 33 | CDBM $F(s, 0, \kappa_q)$ |
| 34 | CDBM $F(s, 0, \kappa_q)/(1 + W_{E1}^2)$ |
| 35 | CDBM $(s-\alpha)^2/(1+s^{2.5})$ |
| 36 | CDBM $(s-\alpha)^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 37 | CDBM $s^2/(1+s^{2.5})$ |
| 38 | CDBM $s^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 39 | CDBM $F_2(s, \alpha, \kappa_q, a/R)$ |
| 40 | CDBM $F_3(s, \alpha, \kappa_q, a/R)/(1+W_{S1}^2)$ |

## 60–64: advanced models

Recently popular first-principles-based transport models.

| Value | Model | Source |
|---|---|---|
| 60 | GLF23 model | Waltz et al. |
| 61 | GLF23 (stability-enhanced version) | improved stability variant |
| 62 | IFS/PPPL model | Kotschenreuther et al. |
| 63 | Weiland model | Weiland group |
| 64 | Modified Weiland model | improved Weiland variant |

## 130–134: CDBM other branch

A CDBM code path implemented independently of the 30s branch. It
goes through different routines such as `tr/trcdbm.f90`.

| Value | Model |
|---|---|
| 130 | CDBM model |
| 131 | CDBM05 model (2005 revision) |
| 132 | CDBM model with ExB shear |
| 134 | CDBM05 model with ExB shear |

```{note}
133 is missing (no definition in the source).
```

## 140–143: Mixed Bohm/gyro-Bohm (mBgB) model

### Physics background

Anomalous transport observed in tokamaks can be roughly described by
two scalings: **Bohm diffusion** and **gyro-Bohm diffusion**.

- **Bohm diffusion** $\chi^\text{Bohm} \propto \rho_s c_s$: scales
  **linearly** in the gyroradius $\rho_s$. A non-local contribution
  spanning the entire plasma, where the edge electron-temperature
  gradient affects core transport. Matters more, relatively, for
  larger machines.
- **gyro-Bohm diffusion**
  $\chi^\text{gB} \propto \rho_s^2 c_s / a$: a local contribution
  scaling as the **square** of the gyroradius. The standard
  expression for ITG / TEM instabilities.

Adding the two **at the same location** is the Mixed Bohm/gyro-Bohm
(mBgB) model. Tuned against JET experimental data, it is also called
the "JETTO transport model" (Erba et al., Nucl. Fusion **38** (1998)
1013).

Concretely, the electron and ion thermal diffusivities are written
as the sums:

$$\chi_e = \chi_e^\text{Bohm} + \chi_e^\text{gB}, \quad \chi_i = \chi_i^\text{Bohm} + \chi_i^\text{gB}$$

The 141–143 variants apply additional ExB-shear or magnetic-shear
suppression on top of this (Pankin/Bateman et al., PPCF **44** (2002)
A495).

### Mapping for `MDLKAI=140..143`

| Value | Model | Physics |
|---|---|---|
| 140 | mBgB (basic) | Plain sum of Bohm + gyro-Bohm. No suppression |
| 141 | mBgB + Tara suppression | Magnetic-shear-dependent suppression by Tara |
| 142 | mBgB + Pacher suppression (ExB) | Pacher's ExB-flow-shear suppression |
| 143 | mBgB + Pacher suppression (ExB + magnetic shear) | 142 + magnetic-shear-dependent term |

### When to use

- Frequently used for simulations of discharges that include the
  L-mode → H-mode transition.
- Has benchmarks on JET / DIII-D / ITER.
- Does not include the ETG (electron temperature gradient) mode, so
  for core electron transport another family (e.g. GLF23 `60–61` or
  mmm) may be needed.

The implementation lives in `tr/mbgb/mixed_Bohm_gyro_Bohm.f`
(Bateman/Pankin/Kritz, Lehigh Univ.).

## 150–151: mmm95 (Multi-Mode Transport Model 1995)

### Physics background

True to the name **Multi-Mode (MM)**, the MMM family **evaluates
several independent instability channels separately and sums them**.
mmm95's channels are:

1. **Weiland model**: drift-wave-family ITG / TEM (Trapped-Electron
   Mode)
2. **Resistive Ballooning** (RB)
3. **Kinetic Ballooning** (KB)

Each produces a diffusivity ($\chi^\text{ig}$ for ITG/TEM,
$\chi^\text{rb}$, $\chi^\text{kb}$), and their linear sum is the
final transport coefficient.

The code was standardised by NTCC (National Transport Code
Collaboration); the version frozen in 1995 is mmm95 (Bateman et al.,
Phys. Plasmas **5** (1998) 1793). It had extensive validation in the
BALDUR transport code at the time, and was widely adopted for the
ITER physics basis.

### Mapping for `MDLKAI=150 / 151`

| Value | Model | ExB suppression |
|---|---|---|
| 150 | mmm95 (Multi-Mode 1995) | no (standard form) |
| 151 | mmm95 + ExB shear stabilization | yes |

The ExB-shear extension (`151`) incorporates background-flow
turbulence suppression in the form $1/(1 + W_{ExB}^2)$.

### When to use

- When you need to use the same model in international benchmarks
  (e.g. ITER design).
- When you want to see the contributions of ITG / TEM / RB / KB
  separately.

The implementation lives in `tr/mmm95/mmm95.f` (Bateman/Kritz,
Lehigh Univ.).

## 160–161: mmm7_1 (Multi-Mode Transport Model 7.1)

### Physics background

The **next generation** of mmm (the successor to mmm95). Internally
it uses Halpern et al.'s 2006–2011 rewrite of the Weiland model
(`w20mod`), which has improved numerical stability and profile
resolution. While mmm95 assumed fixed parameters, mmm7_1 is more
robust for time- and space-dependent analyses.

```{important}
mmm7_1 **does not include the ETG (electron temperature gradient)
mode**. In cases where core electron heat transport is anomalously
large, it can underestimate, so cross-checking with GLF23
(`MDLKAI=60`) is the safe option.
```

### Mapping for `MDLKAI=160 / 161`

| Value | Model | ExB suppression |
|---|---|---|
| 160 | mmm7_1 (Multi-Mode 7.1) | no |
| 161 | mmm7_1 + ExB shear stabilization | yes |

### When to use

- When you want to analyse with the latest Multi-Mode model.
- When you want to compare against mmm95 (`150` / `151`) to see the
  effect of the model update.
- In parameter regimes where ETG is not expected to dominate.

The implementation lives in `tr/libmmm7_1/modmmm7_1.f90` +
`tr/libmmm7_1/w20mod.f90` (Lixiang Luo, F. Halpern et al., Lehigh
Univ.).

## Comparison of the three models

| Aspect | mBgB (140–143) | mmm95 (150–151) | mmm7_1 (160–161) |
|---|---|---|---|
| **Origin** | JET (Erba 1998) | NTCC (Bateman 1998) | NTCC (Halpern 2008–) |
| **Channels** | Bohm + gyro-Bohm | Weiland + RB + KB | Weiland (revised) + RB + KB |
| **ETG mode** | not included | not included | not included |
| **ExB suppression** | 142, 143 (Pacher) | 151 | 161 |
| **Magnetic-shear suppression** | 141, 143 | built-in | built-in |
| **Compute cost** | low | medium | medium–high |
| **Typical use** | Discharges including L/H transition | ITER physics baseline | Latest-generation comparison |
| **Implementation** | `tr/mbgb/` | `tr/mmm95/` | `tr/libmmm7_1/` |

Selection guidelines:

- **JET / mid-size H-mode reproduction**: mBgB (`143` is the
  standard).
- **Match the ITER baseline**: mmm95 (`151`).
- **Re-evaluate with a newer model**: mmm7_1 (`161`).
- **When ETG matters**: none of the above three covers it — consider
  combining with GLF23 (`60`–`61`).

## Which one to pick

- **Default (`MDLKAI=31`)**: CDBM F(s,α,κq). The TASK standard.
  Use this if you want to compare with previous analyses.
- **For international benchmarking**: GLF23 (`60`), mmm95 (`150` /
  `151`), or mmm7_1 (`160` / `161`).
- **For benchmarking**: constant-coefficient (`0`–`3`) to isolate
  the numerical behaviour of the transport equations.
- **To see the effect of ExB shear**: any of `32`, `34`, `36`, `38`,
  `132`, `134`, `142`, `143`, `151`, `161`.

## Full 41-value mapping

For searchability, all values in one table.

| Value | Family | Brief description |
|---|---|---|
| 0  | CONSTANT  | $C(1+A\rho^2)$ |
| 1  | CONSTANT  | $C/(1-A\rho^2)$ |
| 2  | CONSTANT  | $C(\partial T_i/\partial\rho)^B/(1-A\rho^2)$ |
| 3  | CONSTANT  | $C(\partial T_i/\partial\rho)^B T_i^C$ |
| 10 | DRIFT WAVE | $\eta_c=1$ |
| 11 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp)$ |
| 12 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp) \cdot q$ |
| 13 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp) \cdot (1+q^2)$ |
| 14 | DRIFT WAVE | $\eta_c=1+2.5(L_n/R_R-0.2)$, $1/(1+\exp)$ |
| 15 | DRIFT WAVE | $\eta_c=1$, $1/(1+\exp) \cdot \mathrm{func}(q,\varepsilon,L_n)$ |
| 16 | DRIFT WAVE | (15) + zonal flow |
| 20 | REBU-LALLA | Rebu-Lalla model |
| 30 | CDBM      | $1/(1+s)$ |
| **31** | **CDBM (default)** | **$F(s,\alpha,\kappa_q)$** |
| 32 | CDBM      | $F(s,\alpha,\kappa_q)/(1+W_{E1}^2)$ |
| 33 | CDBM      | $F(s,0,\kappa_q)$ |
| 34 | CDBM      | $F(s,0,\kappa_q)/(1+W_{E1}^2)$ |
| 35 | CDBM      | $(s-\alpha)^2/(1+s^{2.5})$ |
| 36 | CDBM      | $(s-\alpha)^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 37 | CDBM      | $s^2/(1+s^{2.5})$ |
| 38 | CDBM      | $s^2/(1+s^{2.5})/(1+W_{E1}^2)$ |
| 39 | CDBM      | $F_2(s,\alpha,\kappa_q,a/R)$ |
| 40 | CDBM      | $F_3(s,\alpha,\kappa_q,a/R)/(1+W_{S1}^2)$ |
| 60 | advanced  | GLF23 |
| 61 | advanced  | GLF23 (stability enhanced) |
| 62 | advanced  | IFS/PPPL |
| 63 | advanced  | Weiland |
| 64 | advanced  | Modified Weiland |
| 130 | CDBM other branch | CDBM |
| 131 | CDBM other branch | CDBM05 |
| 132 | CDBM other branch | CDBM + ExB shear |
| 134 | CDBM other branch | CDBM05 + ExB shear |
| 140 | mBgB     | mixed Bohm/gyro-Bohm |
| 141 | mBgB     | mBgB + Tara suppression |
| 142 | mBgB     | mBgB + Pacher (ExB) |
| 143 | mBgB     | mBgB + Pacher (ExB + shear) |
| 150 | mmm95    | mmm95 (no ExB) |
| 151 | mmm95    | mmm95 (with ExB) |
| 160 | mmm7_1   | mmm7_1 (no ExB) |
| 161 | mmm7_1   | mmm7_1 (with ExB) |

(Missing values: 4–9, 17–19, 21–29, 41–59, 65–129, 133, 135–139,
144–149, 152–159, 162–. Specifying these triggers `STOP` on the
Fortran side or falls back to the default model — implementation-
dependent, so do not use them.)
