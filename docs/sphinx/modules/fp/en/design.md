# Fortran Design

`fp` solves the **Fokker-Planck equation** on a 5D phase space
(position × momentum × pitch angle × species × time). The library wraps
the same physics kernel as the existing `fpx2` binary (about 51 `.f90`
sources: `fpcalc.f90`, `fpcalw.f90`, `fpbounce.f90`, …) with a thin
C-ABI entry layer (`fp_api.f90`) to produce `libfpapi.so`.

## Entry layer (`fp_api.f90`)

There are **6** C-callable functions (the same extended ABI as `eq`).

| C symbol | Fortran side | Role |
|---|---|---|
| `fp_init`           | `fp_api_init`           | `pl_init` → `eq_init` → `fp_init` (internal) initialises FPCOMM |
| `fp_set_param`      | `fp_api_set_param`      | Delegates to `fp_param_registry::fp_param_set` |
| `fp_set_param_str`  | `fp_api_set_param_str`  | String version (`KNAMEQ`) |
| `fp_run`            | `fp_api_run`            | Time-stepping. 5D-grid discretisation + iterative solver |
| `fp_get_state`      | `fp_api_get_state`      | Copies moment quantities into the C struct |
| `fp_finalize`       | `fp_api_finalize`       | Releases the large arrays |

```{note}
`fp` does not yet have an `fp_validate`. To be added under issue #143.
```

## Parameter registry (`fp_param_registry.f90`)

Registers 55 `CASE` entries. The `fp`-specific groups are:

- **5D grid dimensions**: `NRMAX`, `NPMAX`, `NTHMAX`, `NSAMAX`, `NSBMAX`
- **Phase-space bounds**: `PMAX[i]` (per-species maximum momentum)
- **Physics switches**: `MODELE` (relativistic mode), `MODELS`
  (particle source), `MODELC` (collisions), `MODELW` (waves)

`KNAMEQ` is set via `fp_param_set_str`. It is inherited from `pl_init`
internally, so call this only when you want to override that value.

## Source-tree layout

The roughly 51 `fp/*.f90` sources by role:

| Group | Main files | Role |
|---|---|---|
| **API layer** | `fp_api.f90`, `fp_param_registry.f90`, `fp_state.f90` | C ABI entry |
| **Main solver** | `fpcalc.f90`, `fpcalcn.f90`, `fpcalcnr.f90`, `fpsetn.f90` | Discretisation of the Fokker-Planck equation |
| **Collision term** | `fpcalc*.f90` (variants), `fpcoul.f90`, `fpcoulw.f90` | Coulomb-collision operator |
| **Wave term** | `fpcalw.f90`, `fpcalwm.f90`, `fpcaltp.f90` | Wave diffusion tensor |
| **Particle source** | `fpsource.f90`, `fpnbi.f90` | NBI, fusion, etc. sources |
| **Boundary conditions** | `fpbounce.f90`, `fpbroadcast.f90` | Bounce averaging, boundary handling |
| **Equilibrium data** | `cdbm.f90`, `cdbmfp.f90` | Equilibrium ingestion via CDBM |
| **Common modules** | `fpcomm.f90` (estimated), related `_mod.f90` | Global state |
| **I/O** | `fpparm.f90`, `fpfile.f90` (estimated) | namelist, result archiving |
| **Interactive menu** | `fpmenu.f90` (estimated) | `fpx2` CLI only |
| **Regression** | `fpregress.f90` (estimated) | Phase 0 baseline |
| **Graphics** | `fp_graphics_stubs.f90` | Stubbed in the library build |

## Compute cost and memory

`fp` memory is dominated by the **product of the 5D arrays**:

```
memory ≈ NRMAX × NPMAX × NTHMAX × NSAMAX × 8 bytes × (≈10 5D arrays)
```

Examples: `NRMAX=50, NPMAX=100, NTHMAX=50, NSAMAX=2` → about 200 MB.
`NPMAX=200, NTHMAX=100` (high resolution) → about 1.6 GB.

Time complexity is `O(NRMAX × NPMAX × NTHMAX × LMAXFP)` per time step.

## PIC build dependencies

```
libfpapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (used when MODELG=3)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## References

- [`docs/fp-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/fp-library/architecture.md)
- [Common architecture](../../../portal/en/common/architecture.md)
- `fp/fp_api.h` — C ABI header
- `fp/fp_api.f90` — Fortran-side entry
- `fp/fp_param_registry.f90` — parameter registry
