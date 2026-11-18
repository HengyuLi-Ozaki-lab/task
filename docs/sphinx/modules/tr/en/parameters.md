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
| `PROFJ1` | double | −2.0 | – | start current profile with `MODELG = 2` (only there): ≤ 0 takes j from the resistivity (j ∝ 1/η, constant E); > 0 takes j ∝ (1 − ρ^\|PROFJ1\|)^\|PROFJ2\| |
| `PROFJ2` | double | 1.0 | – | exponent of that profile (with `PROFJ1` > 0; its absolute value is used) |

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

**Quasi-neutrality.** TR takes the electrons' density equal to the ions'
charge density, `PN[1] = Σ PZ[s]·PN[s]` over `s = 2..NSMAX`, and the same
for `PNS` (`trprof` dilutes the main ions by the impurity model's charge,
which it takes in proportion to the electrons). Nothing makes the namelist
agree: `validate()` reports a difference above 1e-3 of the larger as
`INCONSISTENT_PAIR` on `PN[1]` or `PNS[1]`, and `tr_run` does not refuse it
(task-web-client #200). Measured on TR's defaults, one process per case,
10 steps: ions far below the electrons fail at once (`PN[1] = 0.5` with
`PN[2]` from 0.005 to 0.05: `NEGATIVE TEMPERATURE AT STEP 0`), `PN[2]` = 0.1
and 0.4 complete, and so does `PN[1] = 0.4` with `PN[2] = 0.5`. A
quasi-neutral centre density far below the edge's fails too: `PN[1] = PN[2]`
at 1e-4 (`PN/PNS` = 2e-3) and below ends with `ierr=3`, from 5e-4 (0.01) it
completes. On the TST-2 case (`MDLIMP = 3`), whose impurity charge grows as
the mean density falls, `PN[1] = PN[2] = 0.002` fails in `tr_prep`
(`negative DILUTE`) and 0.005 completes. Beyond the refusal of a zero or
negative centre density (#189, task-web-client #190), no lower bound on a positive centre
density, or on `PN/PNS`, is checked: such a run fails at once, in `tr_prep`
or within its first ten steps.

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
| `NRMAX`  | int    | 50    | — | TR's radial mesh, 3 to 500 (`TR_MAX_NRMAX`). One value per process: `tr_run` refuses an `NRMAX` other than the one of the process's first preparation, until bpsd resizes its splines (k-yoshimi/bpsd#7); a change of the EQ grid also needs `eq_bpsd_put` to size its arrays again |
| `NTEQIT` | int    | 0     | — | step interval of the EQ re-solve under `MODELG = 9` (0 = never) |

A name `eq:NAME` (`eq:RB`, `eq:NRMAX`, ...) in `set_param` is set in EQ's registry, so `MODELG = 9` takes EQ's wall and grid
without `tot`; an unknown one is refused, and the next `run` prepares again. A failed `MODELG = 9` solve ends a library
run with a failure record (`tr_last_error`; see `python/trlib/README.md`).

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
| `CDH`    | double     | 1.0 | turbulent χ sum weight (χ_s = CDH·χ_turb + CNH·χ_NC, χ_NC the neoclassical χ `AKNC`) |
| `CNH`    | double     | 1.0 | neoclassical χ sum weight (same sum) |
| `MDNCLS` | int switch | 0   | 0: the neoclassical models of `MDLAD`, `MDLETA`, `MDLJBS`; else NCLASS for the neoclassical transport (particle and heat), the resistivity (from the first step on; the start profile takes `MDLETA`'s) and the bootstrap current, and `MDLAD`, `MDLAVK` and `MDLJBS` are not used |
| `AD0`    | double     | 0.5 | particle diffusivity: with `MDLAD` 2, 3, 4 and with NCLASS a factor of χ_turb (with `MDDW = 0`, the default); with `MDLAD` 1 a constant D, weighted by mass and charge through `ALP` |
| `AV0`    | double     | 0.0 | turbulent inward pinch factor (`MDLAD` 1, 2 and 4; not with `MDLAD` 3 or NCLASS) |
| `CDP`    | double     | 1.0 | turbulent particle-diffusivity sum weight (D_s = CDP·D_turb + CNP·D_NC; with the default `MDLAD` 3 and with NCLASS, D_turb = AD0·χ_turb) |
| `CNP`    | double     | 1.0 | neoclassical particle-diffusivity sum weight (same sum) |

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
| `TPRST`  | double | 0.1 | sawtooth period [s], > 0 |
| `MDLNF`  | int switch | 0 | fusion-reaction model |
| `MODEL_PNF` | int switch | 0 | multi-reaction fusion model ported from `trx` (see below) |
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

`MODEL_PNF`:

| Value | Reactions | Count | In the solve |
|---|---|---|---|
| 0 (default) | none: `MDLNF` alone decides | 0 | — |
| 1 | DT | 1 | the fusion particle source, the fusion power and the slowing-down time (`SNF`, `PNF`, `TAUF`), in place of `MDLNF`'s |
| 2, 12 | DT, DD | 4 | evaluated, not used |
| 3 | DT, DD, DHe³ | 6 | evaluated, not used |
| 4, 14 | DT, DD, DHe³, TT, THe³ | 13 | evaluated, not used |

The model of `trx` (`tr/libnf.f90`, `tr/trpnf_multi.f90`). `tr_set_param` takes the name `MODEL_PNF`, the `&TR`
namelist `model_pnf`; the MCP server does not declare it yet. A run that sets both `MODEL_PNF` and `MDLNF` is
refused: with one reaction the two would write the same source. Any other value is refused when the run is
prepared. Changed on a prepared case that is not prepared again (the standalone `tr2`'s `L` then `C`; since
upstream #259 every set through the library or `tot` makes the next run prepare again), a nonzero value other
than the prepared one is refused, `MDLNF` set beside a nonzero `MODEL_PNF` is refused, and 0 turns the model off
at once.

It does not replace `MDLNF` yet:

- `MODEL_PNF = 1` passes `SNF`, `PNF` and `TAUF` to the solve and nothing else. `PFIN`, `PFCL` and the fusion slot of
  `RNF` and `RTF` stay zero, as in `trx`: the alpha power fills the fast-ion energy and is not passed to the thermal species, so a D-T
  run is not heated by its alphas as it is with `MDLNF = 1`.
- It reads the reactants from species 2 and 3 and gives the alpha to species 4, as `MDLNF` does, and does not check
  that they are D, T and He⁴.
- Its rates are cubic splines of the logarithm of a table (points at 1, 2, 5, 10, … 1000 keV) over the logarithm
  of the temperature. Its D-T rate agrees with `MDLNF`'s within 5 % from 1 to 5 keV, 1.3 % from 5 to 100 keV, and
  6 % at the table's points from 1 to 500 keV (at the last point, 1000 keV, the table is 1.46 times `MDLNF`'s rate).
- With more than one reaction nothing reaches the solve, because TR has one fusion fast-ion slot.

What was checked: on a 10 keV D-T case the change `MODEL_PNF = 1` makes agrees within 2 % with the change it makes
in `trx`, once five defects of `trx` are corrected and its rate fit is made TR's
(`test_run/baselines/tr_fus_dt_hot/SOURCE.md`). It has not been
compared with a measurement.

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

## 14. Equations solved and the particle source

Which equations TR solves (`TR_EQS_SELECT`, `tr/trprep.f90`) and the Gaussian particle sources of `tr/trpsc.f90`
(a gas puff). The densities move only with `MDLEQN = 1`: a source with `MDLEQN = 0` adds nothing.

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `MDLEQB` | int switch | 1 | – | 1: B_θ (the current profile) evolved; 0: held at the start profile (`PROFJ1`). With `MODELG = 3` TR reloads ψ from the equilibrium every step, so the current never evolves and `MDLEQB` changes nothing there (measured on a PLATO case) |
| `MDLEQN` | int switch | 0 | – | 0: densities held at the start profiles; 1: evolved |
| `MDLEQE` | int switch | 0 | – | with `MDLEQN = 1`: 0 solves the ion densities and takes the electrons from quasi-neutrality; 1 solves both; 2 solves the electrons and takes the bulk ions from quasi-neutrality, only for `NSMAX = 2` with a hydrogen or deuterium species 2 of charge 1, no impurity density (`MDLIMP = 0`, or `MDLIMP` 1–4 with `PNC` = `PNFE` = 0) and no UFILE (`tr/trexec.f90` adds the other species instead of subtracting them) |
| `MDLPSC` | int switch | 0 | – | 0: no particle source; 1: `NPSCMAX` Gaussian sources |
| `NPSCMAX` | int | 1 | – | number of sources, 0..10 (`NPSCM`) |
| `PSCTOT[i]` | double[10] | 0.0 | 10²⁰ s⁻¹ | total rate of source i (its profile is normalised to it over the plasma volume; a source far from every mesh point puts it all where it is nearest) |
| `PSCR0[i]` | double[10] | 0.0 | m | centre of source i, in metres of minor radius (RA·ρ), not in ρ |
| `PSCRW[i]` | double[10] | 0.5 | m | width of source i: S ∝ exp(−((RA·ρ − PSCR0)/PSCRW)²); positive, at least 1e-10 m |
| `NSPSC[i]` | int[10] | 2 | – | ion species source i feeds, 2..NSMAX; the electrons get PZ times as many |

`tr_run` refuses, before the run, and `validate()` reports: `MDLEQB`, `MDLEQN` or `MDLPSC` outside {0, 1}; `MDLEQE`
outside {0, 1, 2}, `MDLEQE` 1 or 2 with `MDLEQN = 0`, and `MDLEQE = 2` outside the case above; and with `MDLPSC = 1`,
`NPSCMAX` outside 0..10, and for each source i ≤ `NPSCMAX` an `NSPSC[i]` outside 2..NSMAX, a `PSCRW[i]` ≤ 0 or
below 1e-10 m, or a `|PSCR0[i]|` above 1e10 m. These indexed an array out of bounds, ended in NaN, ran as another value
without a word, gave wrong densities, or stopped inside `tr_prep` (`MDLEQB = 2`, `MDLEQE` without `MDLEQN`); a
negative width is the same Gaussian as its absolute value and is refused so that the sign means nothing. With a UFILE
(`MDLUF ≠ 0`) `tr_prep` may change NSMAX (`TR_EQS_SELECT` adds carbon when the UFILE has an impurity), so a source
must feed species 2 and `MDLEQE = 2` is refused: a deliberate restriction, since the species are known only in
`tr_prep`.

With NCLASS (`MDNCLS ≠ 0`), `MDLEQE = 1` (both densities solved, no quasi-neutrality) ended a PLATO case with a
negative temperature within 100 steps of 10 µs; `MDLEQE` 0 and 2 run it.
