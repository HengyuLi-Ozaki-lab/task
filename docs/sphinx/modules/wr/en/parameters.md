# Registered Input Parameters

`wr/wr_param_registry.f90` registers all **103** `CASE` entries. The
names match the Fortran `/WR/` namelist. This is the largest registry
of any module (because ray initial conditions need fine-grained control).

## Required and recommended parameters

### Required

`wr` has **no explicitly required parameters such as `KNAMEQ`**. However,
to actually trace a ray you must supply meaningful **wave conditions**
(frequency + launch point + initial wave-vector).

### Strongly recommended (effectively required)

| Name | Default | Recommended override (ITER ECRH example) |
|---|---|---|
| `RR`     | 3.0 m | 6.2 m |
| `BB`     | 3.0 T | 5.3 T |
| `RF`     | -- | 170e9 Hz (ECRH) or 3.7e9 (LH) |
| `RPI`    | -- | 8.0 m (ITER outboard launch) |
| `ZPI`    | -- | 0.0 m (mid-plane launch) |
| `RKR0`   | -- | 1.0 (normalised wave-number) |
| `RNZI`   | -- | parallel refractive index $N_\parallel$ |
| `NRAYMAX` | 1 | 5 etc. for beam approximation |

### Recommended workflow

```python
from wrlib import Wrlib

with Wrlib() as wr:
    # 1. Device parameters
    wr.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)

    # 2. Wave conditions
    wr.set_params(RF=170.0e9,                # 170 GHz ECRH
                  RPI=8.0, ZPI=0.0,           # launch point
                  RKR0=1.0,                   # initial wave-number
                  NRAYMAX=1)                  # single ray

    # 3. Run the ray trace
    wr.run(nray_request=1)
    state = wr.get_state()

    print(f"peak R = {state.scalars['pos_pwrmax_rs']:.3f}")
    print(f"peak value = {state.scalars['pwrmax_rs']:.4e}")
```

---

## 1. Geometry / device

| Name | Type | Default | Unit | Meaning |
|---|---|---|---|---|
| `RR`    | double | 3.0 | m | plasma major radius |
| `RA`    | double | 1.2 | m | plasma minor radius |
| `RB`    | double | 1.4 | m | wall minor radius |
| `RKAP`  | double | 1.0 | — | elongation |
| `RDLT`  | double | 0.0 | — | triangularity |
| `BB`    | double | 3.0 | T | toroidal field |
| `Q0`    | double | 1.0 | — | central q |
| `QA`    | double | 3.0 | — | edge q |
| `RIP`   | double | 3.0 | MA | plasma current |

## 2. Plasma composition

| Name | Type | Meaning |
|---|---|---|
| `NSMAX`     | int | number of species |
| `PA[i]`     | double[] | mass number |
| `PZ[i]`     | double[] | charge number |
| `PN[i]`     | double[] | on-axis density [10²⁰ m⁻³] |
| `PNS[i]`    | double[] | edge density |
| `PT[i]`     | double[] | on-axis temperature [keV] |
| `PTPR[i]`   | double[] | parallel temperature |
| `PTPP[i]`   | double[] | perpendicular temperature |
| `PTS[i]`    | double[] | edge temperature |
| `PU[i]`     | double[] | on-axis flow velocity |
| `PUS[i]`    | double[] | edge flow velocity |
| `PZCL[i]`   | double[] | collision frequency |

## 3. Profile shape (per species)

| Name | Type | Meaning |
|---|---|---|
| `PROFN1[i]` | double[] | density profile exponent 1 of species i |
| `PROFN2[i]` | double[] | density profile exponent 2 |
| `PROFT1[i]` | double[] | temperature profile exponent 1 |
| `PROFT2[i]` | double[] | temperature profile exponent 2 |
| `PROFU1[i]` | double[] | flow profile exponent 1 |
| `PROFU2[i]` | double[] | flow profile exponent 2 |
| `MODEL_PROF`  | int | profile source selector |
| `MODEL_NPROF` | int | density-profile switch |

## 4. ITB profile (Internal Transport Barrier)

| Name | Type | Meaning |
|---|---|---|
| `RHOITB[i]` | double[] | ITB normalised radius |
| `PNITB[i]`  | double[] | density inside ITB |
| `PTITB[i]`  | double[] | temperature inside ITB |
| `PUITB[i]`  | double[] | flow velocity inside ITB |

## 5. Neutrals / SOL

| Name | Type | Meaning |
|---|---|---|
| `RHOMIN` | double | normalised radius of $q_\mathrm{min}$ |
| `QMIN`   | double | minimum q |
| `RHOEDG` | double | normalised radius of plasma edge |
| `PPN0`   | double | neutral density (pressure) |
| `PTN0`   | double | neutral temperature |

## 6. Single-ray launch conditions

Used when `NRAYMAX=1`. For multi-ray cases use the `*IN` arrays in §7.

| Name | Type | Unit | Meaning |
|---|---|---|---|
| `RF`      | double | Hz | wave frequency |
| `RPI`     | double | m | launch point R |
| `ZPI`     | double | m | launch point Z |
| `PHII`    | double | rad | toroidal angle of launch |
| `RNZI`    | double | — | parallel refractive index $N_\parallel$ |
| `RNPHII`  | double | — | toroidal refractive index $N_\varphi$ |
| `RKR0`    | double | — | initial R-direction wave-number |
| `UUI`     | double | — | initial power (normalised, default 1.0) |
| `RCURVA`  | double | m | beam curvature radius (major axis) |
| `RCURVB`  | double | m | beam curvature radius (minor axis) |
| `RBRADA`  | double | m | beam radius (major axis) |
| `RBRADB`  | double | m | beam radius (minor axis) |

## 7. Multi-ray launch conditions (`*IN` arrays)

Specify per-ray initial conditions (1-origin) when `NRAYMAX>1`.

| Name | Type | Meaning |
|---|---|---|
| `RFIN[i]`     | double[] | frequency of ray i |
| `RPIN[i]`     | double[] | launch R of ray i |
| `ZPIN[i]`     | double[] | launch Z |
| `PHIIN[i]`    | double[] | toroidal angle |
| `RKRIN[i]`    | double[] | initial $k_R$ |
| `RNZIN[i]`    | double[] | $N_\parallel$ |
| `RNPHIIN[i]`  | double[] | $N_\varphi$ |
| `ANGZIN[i]`   | double[] | launch angle (Z direction) |
| `ANGPHIN[i]`  | double[] | launch angle (φ direction) |
| `UUIN[i]`     | double[] | initial power |
| `RCURVAIN[i]` | double[] | curvature radius A |
| `RCURVBIN[i]` | double[] | curvature radius B |
| `RBRADAIN[i]` | double[] | beam radius A |
| `RBRADBIN[i]` | double[] | beam radius B |
| `MODEWIN[i]`  | int[]    | wave mode of ray i |

## 8. Computation domain / resolution

| Name | Type | Default | Meaning |
|---|---|---|---|
| `Rmax_wr` | double | -- | maximum R of the domain |
| `Rmin_wr` | double | -- | minimum R of the domain |
| `Zmax_wr` | double | -- | maximum Z |
| `Zmin_wr` | double | -- | minimum Z |
| `NRAYMAX` | int | 1 | number of rays |
| `NSTPMAX` | int | 10000 | maximum steps per ray |
| `NRSMAX`  | int | -- | radial profile points |
| `NRLMAX`  | int | -- | major-radius profile points |
| `LMAXNW`  | int | -- | maximum Newton iterations |

## 9. Numerical integration

| Name | Type | Default | Meaning |
|---|---|---|---|
| `SMAX`   | double | -- | maximum ray-path length |
| `DELS`   | double | -- | ray-path step size |
| `EPSRAY` | double | -- | ray-integration tolerance |
| `DELRAY` | double | -- | ray-calculation step |
| `DELDER` | double | -- | numerical-derivative step |
| `DELKR`  | double | -- | $k_R$ derivative step |
| `EPSNW`  | double | -- | Newton tolerance |
| `UUMIN`  | double | -- | minimum residual-power threshold (stop below this) |

## 10. Resonance / thresholds

| Name | Type | Default | Meaning |
|---|---|---|---|
| `nres_max`     | int | -- | maximum resonance order |
| `nres_type`    | int | -- | resonance type |
| `pne_threshold` | double | -- | cutoff threshold |
| `bdr_threshold` | double | -- | boundary threshold |

## 11. Mode switches

| Name | Type | Default | Meaning |
|---|---|---|---|
| `MODELG`     | int | 2 | geometry model (same as `tr`/`eq`) |
| `MODELQ`     | int | 0 | q-profile control |
| `MODEFW`     | int | 0 | wave model (W-related) |
| `MODEFR`     | int | 0 | radial model |
| `IDEBUG`     | int | 0 | debug output |
| `MODELP[i]`  | int[] | -- | wave model of species i |
| `MODELV[i]`  | int[] | -- | velocity-distribution model of species i |
| `NCMIN[i]`   | int[] | -- | minimum resonance order |
| `NCMAX[i]`   | int[] | -- | maximum resonance order |
| `mode_beam`  | int | 0 | beam / pencil switch |
| `MDLWRI`     | int | -- | wr input mode |
| `MDLWRG`     | int | -- | wr graph mode |
| `MDLWRP`     | int | -- | wr output mode |
| `MDLWRQ`     | int | -- | wr quality mode |
| `MDLWRW`     | int | -- | wr wave mode |
| `MODEW`      | int | 0 | wave-polarisation mode |
| `mode_wline` | int | 0 | wave-line mode |
| `RF_PL`      | double | -- | plasma frequency (internal reference) |
