# Fortran Design

The `ti` library wraps the same physics kernel as the existing `tix2`
binary (`ticalc.f90`, `ticoef.f90`, `tinclass.f90`, and roughly 20
other `.f90` sources) with a thin C-ABI entry layer (`ti_api.f90`) to
form `libtiapi.so`. The 3-layer common design is described in the
{ref}`Common Architecture <portal:common-architecture>` chapter.

## Entry layer (`ti_api.f90`)

Five functions are callable from C — the standard pattern. Unlike
`eq`, there is no extension as a 6th ABI function.

| C symbol | Fortran side | Role |
|---|---|---|
| `ti_init`       | `ti_api_init`       | `pl_init` → `eq_init` → `ti_init` (internal) — initializes TICOMM |
| `ti_set_param`  | `ti_api_set_param`  | Delegates to `ti_param_registry::ti_param_set` |
| `ti_run`        | `ti_api_run`        | Time-step advance, includes the inner iteration solver (`MAXLOOP`) |
| `ti_get_state`  | `ti_api_get_state`  | Copies TICOMM scalars and profiles into the C struct |
| `ti_finalize`   | `ti_api_finalize`   | `DEALLOCATE` + flag reset |

All are `BIND(C, NAME="ti_xxx")`, fixing the C-ABI symbol names.

```{note}
`ti` does not currently provide `ti_set_param_str` or `ti_validate`.
String parameters are unnecessary by design (equilibrium data flow
through `pl_*`); a validate API is planned in issue #143.
```

## Parameter registry (`ti_param_registry.f90`)

Exposes 77 `CASE` entries via the same `SELECT CASE` layout as `tr`.
`ti`-specific traits:

- **Many array parameters**: `PROFN1[i]`, `PROFN2[i]`, `DT0_NS[i]`, …
  — per-species parameters are abundant (the `_NS` suffix on arrays).
- **18+ `MODEL_*` switches**: more finely subdivided than `tr`'s `MDL*`.
- **`NRMAX` is runtime-mutable**: in `tr` it was fixed; in `ti` you can
  change it at runtime via `set_param("NRMAX", n)`.

## Library source layout

The roughly 20 `ti/*.f90` sources by role:

| Group | Main files | Role |
|---|---|---|
| **API layer** | `ti_api.f90`, `ti_param_registry.f90`, `ti_state.f90` | C ABI entry |
| **Main loop** | `timain.f90`, `tiexec.f90`, `tiprep.f90` | Time-evolution control |
| **Physics** | `ticalc.f90`, `ticoef.f90`, `ticdbm.f90`, `tinclass.f90` | Transport coefficients, neoclassical, CDBM |
| **Common module** | `ticomm.f90` | Global state (TICOMM) |
| **Particle sources / atomic** | `tiadas.f90`, `tisource.f90` | Impurity atomic processes, particle sources |
| **I/O** | `tiparm.f90`, `tirecord.f90`, `tigout.f90` | Namelist, result recording, plotting |
| **Interactive menu** | `timenu.f90` | Used only by the `tix2` CLI |
| **Regression** | `tiregress.f90` | Phase 0 baseline output |
| **Graphics** | `ti_graphics_stubs.f90` | Stubbed in the library build |
| **Initialization** | `tiinit.f90` | Default-value setup |

## Design differences from `tr`

| | `tr` | `ti` |
|---|---|---|
| **C ABI functions** | 5 + `set_param_str` (after PR #172) + `validate` | 5 (no extensions) |
| **`NRMAX`** | fixed | runtime-mutable (`set_param`) |
| **Species management** | `NSMAX` only | two tiers — `NSMAX` + active `NSA_MAX` |
| **Number of model switches** | ~10 (`MDL*`) | 18+ (`MODEL_*`) |
| **Module dependencies** | `pl`, `eq`, `bpsd`, `mtxp` | `pl`, `eq`, `bpsd`, `mtxp` (same) |

## PIC build dependencies

```
libtiapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (referenced under MODEL_EQ* modes)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## See also

- [`docs/ti-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/ti-library/architecture.md)
- {ref}`Common Architecture <portal:common-architecture>`
- `ti/ti_api.h` — C ABI header
- `ti/ti_api.f90` — Fortran-side entry layer
- `ti/ti_param_registry.f90` — parameter registry
