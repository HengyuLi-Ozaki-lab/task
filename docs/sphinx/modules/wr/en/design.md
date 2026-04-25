# Fortran Design

`wr` is a **geometric-optics ray-tracing** solver. `libwrapi.so` is built
by layering a thin C-ABI entry layer (`wr_api.f90`) on top of the same
physics kernel as the existing `wrx2` binary (about 20 `.f90` source
files).

## Entry layer (`wr_api.f90`)

There are **5 functions** callable from C (the standard pattern).

| C symbol | Fortran side | Role |
|---|---|---|
| `wr_init`           | `wr_api_init`           | initialises WRCOMM via `pl_init` → `eq_init` → internal `wr_init` |
| `wr_set_param`      | `wr_api_set_param`      | delegates to `wr_param_registry::wr_param_set` |
| `wr_run`            | `wr_api_run`            | traces `nray_request` rays in parallel |
| `wr_get_state`      | `wr_api_get_state`      | copies ray trajectories + profiles into the C struct |
| `wr_finalize`       | `wr_api_finalize`       | frees ray buffers + resets flags |

```{note}
`wr` implements neither `set_param_str` nor `validate`. String parameters
are inherited via `pl_*`; range checks are limited to the immediate
rejection performed at `set_param` time.
```

## How `wr_run(nray_request)` works

Unlike the time-stepping `run(ntmax)` of `tr` / `ti` / `fp`, `wr_run`
performs a **spatial ray integration**.

1. Pick `nray_request` rays (capped at `NRAYMAX`)
2. Set each ray's initial conditions (position + wave-vector + power)
3. Integrate the ray equation (Hamiltonian:
   $\dot{\vec{x}} = \partial H/\partial \vec{k}$,
   $\dot{\vec{k}} = -\partial H/\partial \vec{x}$) up to `NSTPMAX` steps
4. At each step, compute power absorption and reduce the residual power
   `UU`
5. Stop when `UU < UUMIN` or the ray leaves the domain
6. Sum the contributions of all rays radially → `pwr_nrs[]`, `pwr_nrl[]`

## Parameter registry (`wr_param_registry.f90`)

Registers 103 `CASE` entries. `wr`-specific features:

- **Per-ray initial-condition arrays**: the `*IN` family (`RFIN[i]`,
  `RPIN[i]`, `ZPIN[i]`, ...)
- **Beam-shape inputs**: `RCURVA*`, `RBRADA*` for curvature and width
  (Gaussian approximation)
- **Resonance-order selection**: `NCMIN[i]`, `NCMAX[i]` for the range of
  electron-cyclotron harmonics

## Library source layout

The roughly 20 `wr/*.f90` files, by role:

| Group | Main files (estimated) | Role |
|---|---|---|
| **API layer** | `wr_api.f90`, `wr_param_registry.f90`, `wr_state.f90` | C ABI entry |
| **Main solver** | `wrcalc.f90`, `wrexec.f90` | main ray-integration loop |
| **Wave equation** | `wrdisp.f90` (estimated), related | refractive-index tensor / dispersion |
| **Damping** | `wrdamp.f90` (estimated) | cyclotron and Landau damping |
| **Common module** | `wrcomm.f90` | global state (WRCOMM) |
| **I/O** | `wrparm.f90`, `wrfile.f90` (estimated) | namelist, result recording |
| **Interactive menu** | `wrmenu.f90` (estimated) | exclusive to the `wrx2` CLI |
| **Regression** | `wrregress.f90` (estimated) | Phase 0 baseline |
| **Graphics** | `wr_graphics_stubs.f90` | stubbed in the library build |

## Relationship between `wr` and `wrx`

`wr` (geometric optics) and `wrx` (extended / beam tracing) are
**separate C ABIs** producing separate `.so` files, but they share much
source:

- `wr`: each ray is an infinitesimal beam. Beam spread is approximated
  with `NRAYMAX` rays
- `wrx`: each ray carries beam-shape information (curvature, width)
  expanded analytically

For details see the `wrx` module pages
(`docs/sphinx/modules/wrx/en/index.md`).

## Memory consumption

Main buffers:

```
ray trajectories: NRAYMAX × NSTPMAX × NRAY_EQ × 8 bytes
radial profiles : (NRSMAX + NRLMAX) × 8 bytes × a few
```

`NRAYMAX=10, NSTPMAX=10000, NRAY_EQ=20` is about 16 MB. Smaller than
`tr` / `fp`, but with many rays and high resolution it can reach
hundreds of MB.

## PIC-build dependencies

```
libwrapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (used when MODELG=3)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## See also

- [`docs/wr-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/wr-library/architecture.md)
- {ref}`Common Architecture <portal:common-architecture>`
- `wr/wr_api.h` — C ABI header
- `wr/wr_api.f90` — Fortran-side entry
- `wr/wr_param_registry.f90` — parameter registry
