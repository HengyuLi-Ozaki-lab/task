# Registered Input Parameters

This page lists, by logical group, the parameters registered in
`tr/tr_param_registry.f90`. The names match the Fortran `/TR/`
namelist. Entries whose type is "double array" use the
`set_param("NAME[i]", value)` syntax with **1-origin** indexing.
Defaults are those set in `tr/trinit.f90::tr_init`; values not
overridden explicitly take the default.

## Required and recommended parameters

Most parameters have defaults, so a minimal configuration can call
`run()` without setting anything. However some are **required under
specific conditions**, and others **should be overridden if you want
physically meaningful results**.

### Required (conditional)

| Condition | Required parameter | Reason |
|---|---|---|
| `MODELG ∈ {3, 5, 7, 8}` | **`KNAMEQ`** (string) | Equilibrium-data filename. If unset, `tr_validate()` returns a `FILE_MISSING` diagnostic and `tr_prep` fails inside `run()` |

`KNAMEQ` is set via `set_param_str`:

```python
tr.set_param("MODELG", 3)
tr.set_param_str("KNAMEQ", "eqdata.ITER01")
```

If `MODELG=2` (analytic toroidal geometry, the default), no file is
needed, so **strictly speaking nothing is mandatory**.

### Strongly recommended (defaults are too generic)

The defaults are dummy values for a generic small tokamak. If your
target device is fixed, you should override at least the following.

| Name | Default | Recommended override (ITER example) |
|---|---|---|
| `RR`     | 3.0 m  | 6.2 m |
| `RA`     | 1.2 m  | 2.0 m |
| `BB`     | 3.0 T  | 5.3 T |
| `RIPS`   | 3.0 MA | 15.0 MA |
| `RIPE`   | 3.0 MA | 15.0 MA |
| `NSMAX`  | 2 (e + D) | depends on the analysis |
| `DT`     | 0.01 s | depends on the time scale of the result |
| `NTMAX`  | 100    | depends on the time scale of the result |

### Usually leave alone (defaults are fine)

The following are essentially fine at default. Turn them on only when
you specifically need that physics.

- Heating systems (everything except `MDLNB=1` is OFF by default;
  `MDLEC`/`MDLLH`/`MDLIC=0`)
- Fusion (`MDLNF=0`)
- Impurities (`MDLIMP=0`)
- Internal numerical settings (`EPSLTR`, `LMAXTR`, `NGTSTP`, `NGRSTP`)
- Profile shape (`PROFN1=2.0`, `PROFN2=0.5`)

### Recommended workflow

```python
from trlib import Trlib, TrDiagCode

with Trlib() as tr:
    # 1. things to always set
    tr.set_params(RR=6.2, RA=2.0, BB=5.3,
                  RIPS=15.0, RIPE=15.0,
                  DT=0.01, NTMAX=100)

    # 2. if you set MODELG=3, KNAMEQ is required
    # tr.set_param("MODELG", 3)
    # tr.set_param_str("KNAMEQ", "eqdata.ITER01")

    # 3. after setup, call validate before run
    diags = tr.validate()
    for d in diags:
        print(f"[{TrDiagCode(d.code).name}] {d.param}: {d.message}")
    if diags:
        raise SystemExit("fix the diagnostics before running")

    tr.run(ntmax=10)
    state = tr.get_state()
```

`validate()` checks **unset required parameters**, **out-of-range
values**, and **missing files** in one pass, so calling it just
before `run()` is the safe pattern (see method D in
{doc}`parameter-setting`).

## 1. Geometry / device

The parameters that fix the plasma's spatial shape and field
strength. The minimum you should set before starting a simulation is
the trio `RR`, `RA`, `BB`.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `RR`     | double | 3.0 | m | plasma major radius |
| `RA`     | double | 1.2 | m | plasma minor radius |
| `RKAP`   | double | 1.5 | — | poloidal cross-section elongation |
| `RDLT`   | double | 0.0 | — | poloidal cross-section triangularity |
| `BB`     | double | 3.0 | T | toroidal field on plasma axis |
| `PHIA`   | double | 0.0 | Wb | total toroidal flux (placeholder for UFILE input) |
| `MODELG` | int switch | 2 | — | equilibrium / geometry model selector |

Allowed values of `MODELG`:

| Value | Behaviour |
|---|---|
| 2 (default) | TOROIDAL GEOMETRY — analytic toroidal geometry |
| 3        | READ TASK/EQ FILE — read equilibrium data named by `KNAMEQ` |
| 5        | READ EQDSK FILE |
| 9        | CALCULATE TASK/EQ — solve TASK/EQ on the fly |

## 2. Plasma current

The plasma current ramps linearly from `RIPS` to `RIPE`. For
steady-state runs set both equal.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `RIPS` | double | 3.0 | MA | plasma current at simulation start |
| `RIPE` | double | 3.0 | MA | plasma current at simulation end |

## 3. Plasma composition

The species array is declared with `NSMM=100`, but the registry
restricts `NSMAX ∈ [2, 8]` (`NSMAX=1` triggers a divide-by-zero in
`tr_prof_impurity`, and the Fortran-side `STOP` would abort the host
process). By convention NS=1 is the electrons; NS=2 onward are ion
species.

| Name | Type | Default (NS=2 D ion) | Unit | Meaning |
|---|---|---|---|---|
| `NSMAX`   | int          | 2   | — | number of main species (1 ≤ NS ≤ NSMAX) |
| `PA[i]`   | double[NSMM] | 2   | — | mass number of species `i` |
| `PZ[i]`   | double[NSMM] | 1   | — | charge number of species `i` |
| `PN[i]`   | double[NSMM] | 0.5 | 10²⁰ m⁻³ | initial axial number density of species `i` |
| `PNS[i]`  | double[NSMM] | 0.05 | 10²⁰ m⁻³ | initial edge (surface) number density of species `i` |
| `PT[i]`   | double[NSMM] | 1.5 | keV | initial axial temperature of species `i` |
| `PTS[i]`  | double[NSMM] | 0.05 | keV | initial edge (surface) temperature of species `i` |

The default species layout (`trinit.f90`):

| NS | Species | PA | PZ | PN | PT |
|---|---|---|---|---|---|
| 1 | electron | 5.446×10⁻⁴ (AME/AMM) | -1 | 0.5 | 1.5 |
| 2 | D     | 2  | 1 | 0.5 | 1.5 |
| 3 | T     | 3  | 1 | 0   | 1.5 |
| 4 | He    | 4  | 2 | 0   | 1.5 |
| 5 | C (low ionization) | 12 | 2 | 0 | 0 |
| 6 | C (high ionization) | 12 | 4 | 0 | 0 |

## 4. Initial profile shape

The initial density / temperature profiles are given by:

$$X(\rho) = (X_0 - X_S)\,(1 - \rho^{\text{PROFN1}})^{\text{PROFN2}} + X_S$$

where $X_0$ = `PN[i]` or `PT[i]` (axis) and $X_S$ = `PNS[i]` or
`PTS[i]` (edge).

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `PROFN1` | double | 2.0 | — | inner-shape exponent |
| `PROFN2` | double | 0.5 | — | outer-shape exponent |

## 5. Impurity

Controls injection of carbon (C) and iron (Fe) impurities.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MDLIMP` | int switch | 0 | impurity model selector |
| `PNC`    | double     | 0.0 | carbon density coefficient (relative to ITER physics guideline) |

Allowed values of `MDLIMP`:

| Value | Behaviour |
|---|---|
| 0 (default) | no impurities (`PNC` / `PNFE` unused) |
| 1 | impurity density at the ITER physics guideline ×1.0 |
| 2 | use `PNC` as a factor: `ANC = PNC·ANE` |
| 3 | case 1 + Te-dependent electron density via `PZC` / `PZFE` |
| 4 | case 2 + Te-dependent electron density via `PZC` / `PZFE` |

## 6. Time evolution

`DT × NTMAX` is the actual simulation time [s]. The default is
0.01 × 100 = 1 s.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `DT`     | double | 0.01  | s | time step size |
| `NTMAX`  | int    | 100   | — | total number of time steps |
| `NTSTEP` | int    | 10    | — | snapshot print interval (in steps) |
| `EPSLTR` | double | 0.001 | — | convergence criterion for inner iterations |
| `LMAXTR` | int    | 10    | — | maximum number of inner iterations |
| `NGTSTP` | int    | 2     | — | save interval for time-evolution graphs |
| `NGRSTP` | int    | 100   | — | save interval for radial-profile graphs |

## 7. Transport model

Heat- and particle-transport coefficients and model selector. `MDLKAI`
in particular has many options; see the table below for representative
values. `CDW` has 8 elements (1-origin) and is consulted by Drift-Wave
family models.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MDLKAI` | int switch | 31  | turbulent heat-transport model selector |
| `MDLETA` | int switch | 3   | resistivity model |
| `MDLAD`  | int switch | 3   | particle-diffusion model |
| `MDLAVK` | int switch | 3   | thermal-pinch model |
| `CDW[i]` | double[8]  | 0.04 | Drift-Wave model coefficients (i=1..8) |
| `CHP`    | double     | 0.0 | semi-empirical correction coefficient |
| `CK0`    | double     | 12.0 | electron χ coefficient |
| `CK1`    | double     | 12.0 | ion χ coefficient |
| `CDH`    | double     | 1.0 | turbulent heat-diffusivity sum weight ($\chi_s = \mathtt{CDH}\cdot\chi_\mathrm{turb} + \mathtt{CNH}\cdot\chi_\mathrm{NCLASS}$) |
| `CNH`    | double     | 1.0 | neoclassical heat-diffusivity sum weight (same sum) |

Selectable transport models for `MDLKAI` (representative values;
families are organized in groups of 10):

| Range | Family | Representative values |
|---|---|---|
| 0–9    | CONSTANT COEFFICIENT | 0: constant, 2: $\propto(\partial T_i/\partial\rho)^B$ |
| 10–19  | DRIFT WAVE (+ITG +ETG) | 10: $\eta_c=1$, 16: 15+zonal flow |
| 20–29  | REBU-LALLA | 20: Rebu-Lalla |
| 30–40  | **CDBM family** | **31 (default): CDBM F(s,α,κq)**, 32: +ExB shear |
| 60–64  | advanced models | 60: GLF23, 62: IFS/PPPL, 63: Weiland |
| 130–134 | CDBM other branch | 131: CDBM05, 132: +ExB shear |
| 140–143 | Mixed Bohm/gyro-Bohm | 140: mBgB, 143: mBgB+Pacher |
| 150–151 | mmm95 | 150: no ExB, 151: with ExB |
| 160–161 | mmm7_1 (no ETG) | 160: no ExB, 161: with ExB |

Per-model details and the full 41-value mapping table are in
{doc}`appendix-mdlkai`.

`MDLETA` (resistivity model):

| Value | Model |
|---|---|
| 1 | Hinton and Hazeltine |
| 2 | Hirshman, Hawryluk |
| 3 (default) | Sauter |
| 4 | Hirshman, Sigmar |
| other | CLASSICAL |

`MDLAD` (particle diffusion):

| Value | Model |
|---|---|
| 1 | constant D + inward pinch AV0 |
| 2 | turbulence + pinch AV0 |
| 3 (default) | Hinton and Hazeltine |
| 4 | Hinton and Hazeltine + turbulence |
| other | no particle transport |

`MDLAVK` (thermal pinch):

| Value | Model |
|---|---|
| 1 | arbitrary amplitude |
| 2 | arbitrary amplitude + pressure-dependent |
| 3 (default) | Hinton and Hazeltine |
| other | no thermal pinch |

## 8. Module switches

These turn the heating, current-drive, and particle-source submodules
on or off. By default only NBI (`MDLNB=1`), pellet (`MDLPEL=1`), and
the bootstrap-current Sauter model (`MDLJBS=5`) are active.

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MDLNB`  | int switch | 1 | NBI (neutral beam) heating model |
| `MDLEC`  | int switch | 0 | ECRF (electron cyclotron) heating |
| `MDLLH`  | int switch | 0 | LHRF (lower-hybrid wave) heating |
| `MDLIC`  | int switch | 0 | ICRF (ion cyclotron) heating |
| `MDLPEL` | int switch | 1 | pellet-injection model |
| `MDLJBS` | int switch | 5 | bootstrap-current model |
| `MDLST`  | int switch | 0 | sawtooth model |
| `MDLNF`  | int switch | 0 | fusion-reaction model |
| `MDLUF`  | int switch | 0 | UFILE (experimental data) reader model |

`MDLNB`:

| Value | Behaviour |
|---|---|
| 0 | OFF |
| 1 (default) | GAUSSIAN (no particle source) |
| 2 | GAUSSIAN |
| 3 | PENCIL BEAM (no particle source) |
| 4 | PENCIL BEAM |

`MDLPEL`:

| Value | Model |
|---|---|
| 0 | OFF |
| 1 (default) | GAUSSIAN |
| 2 | Nakamura |
| 3 | Ho |

`MDLJBS`:

| Value | Model |
|---|---|
| 1–3 | Hinton and Hazeltine |
| 4   | Hirshman, Sigmar |
| 5 (default) | Sauter |
| other | Hinton and Hazeltine |

`MDLNF`:

| Value | Reaction |
|---|---|
| 0 (default) | OFF |
| 1 | DT (no particle source) |
| 2 | DT (with particle source) |
| 3 | DT + NB beam component (no particle source) |
| 4 | DT + NB beam component (with particle source) |
| 5 | DHe³ (no particle source) |
| 6 | DHe³ (with particle source) |

`MDLST`: 0 (OFF, default) / 1 (ON).

`MDLUF`:

| Value | Meaning |
|---|---|
| 0 (default) | UFILE not used |
| 1 | time evolution |
| 2 | steady state |
| 3 | comparison with TOPICS |

```{note}
The enumerations of `MDLEC` / `MDLLH` / `MDLIC` are not commented in
the Fortran source and are not listed here. Default 0 is OFF.
For non-zero behaviour, consult `tr/trpnb.f90` and the related wave
calculation code directly.
```

## 9. NBI (Neutral Beam Injection)

Active when `MDLNB ≥ 1`. The deposited power follows a Gaussian
distribution centred at radius `PNBR0` with width `PNBRW`.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `PNBR0`  | double | 0.0  | m | radial centre of power deposition |
| `PNBRW`  | double | 0.5  | m | radial width of power deposition |
| `PNBENG` | double | 80.0 | keV | beam energy |
| `PNBRTG` | double | 3.0  | m | tangency radius (used when `MDLNB=3` / `4`) |

## 10. ICRF (Ion Cyclotron Range of Frequencies)

Active when `MDLIC ≠ 0`.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `PICCD`  | double | 0.0 | — | current-drive coefficient |
| `PICR0`  | double | 0.0 | m | radial centre of power deposition |
| `PICRW`  | double | 0.5 | m | radial width of power deposition |
| `PICNPR` | double | 2.0 | — | parallel refractive index $N_\parallel$ |
| `PICTOT` | double | 0.0 | MW | total ICRF input power |

## 11. ECRF (Electron Cyclotron Range of Frequencies)

Active when `MDLEC ≠ 0`.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `PECCD`  | double | 0.0 | — | current-drive coefficient |
| `PECR0`  | double | 0.0 | m | radial centre of power deposition |
| `PECRW`  | double | 0.2 | m | radial width of power deposition |
| `PECNPR` | double | 0.0 | — | parallel refractive index $N_\parallel$ |
| `PECTOT` | double | 0.0 | MW | total ECRF input power |

## 12. LH (Lower Hybrid Range)

Active when `MDLLH ≠ 0`.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `PLHCD`  | double | 0.0 (in practice) | — | current-drive coefficient |
| `PLHR0`  | double | 0.0 | m | radial centre of power deposition |
| `PLHRW`  | double | 0.2 | m | radial width of power deposition |
| `PLHNPR` | double | 2.0 | — | parallel refractive index $N_\parallel$ |
| `PLHTOT` | double | 0.0 | MW | total LHRF input power |

```{note}
`PLHCD` is not explicitly initialised in `tr/trinit.f90`. It depends
on Fortran's implicit default for module variables, so a value of
exactly 0.0 is not strictly guaranteed. Setting
`tr.set_param("PLHCD", 0.0)` explicitly is the safe option.
```

## 13. Strings

| Name | Type | Default | Meaning |
|---|---|---|---|
| `KNAMEQ` | CHARACTER(80) | `'eqdata'` | equilibrium-data filename loaded when `MODELG=3` |

This is set via **`set_param_str`**, not `set_param`.

```python
tr.set_param_str("KNAMEQ", "eqdata.ITER01")
```
