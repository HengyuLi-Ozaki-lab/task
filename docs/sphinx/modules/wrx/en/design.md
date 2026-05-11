# Fortran Design

`wrx` is the **extended** version of `wr` (geometric optics) that adds
**beam tracing**. It places a thin C-ABI entry layer (`wrx_api.f90`) on
top of the same physics kernel as the `wrx2` binary (about 27 `.f90`
sources) to produce `libwrxapi.so`.

## Entry layer (`wrx_api.f90`)

The C-callable surface is **5 functions** (the standard pattern).

| C symbol | Fortran side | Role |
|---|---|---|
| `wrx_init`       | `wrx_api_init`       | Initialize WRXCOMM via `pl_init` → `eq_init` → `wrx_init` |
| `wrx_set_param`  | `wrx_api_set_param`  | Delegate to `wrx_param_registry::wrx_param_set` |
| `wrx_run`        | `wrx_api_run`        | Run beam tracing; track the beam shape on each ray |
| `wrx_get_state`  | `wrx_api_get_state`  | Copy ray results + profiles into the C struct |
| `wrx_finalize`   | `wrx_api_finalize`   | Release ray + beam-shape buffers |

## What `wrx_run` does

Similar to `wr_run(nray_request)`, but each ray is integrated together
with a **beam-shape tensor**.

1. Pull `NRAYMAX` rays
2. Set initial conditions for each ray (position + wave-number + power +
   **curvature** `RCURVAIN` + **width** `RBRADAIN`)
3. Integrate the ray equation; in parallel evolve the beam-shape tensor:
   - Propagation of the curvature $\partial^2 \phi / \partial x^2$
   - Propagation of the beam width
4. Compute power absorption at each step (taking the beam cross-section
   into account)
5. Stopping conditions (`UUMIN` reached, leaving the computational
   domain, maximum step count)

## Parameter registry (`wrx_param_registry.f90`)

70 `CASE` entries. wrx-specific traits:

- **Beam-shape arrays**: `RCURVAIN[i]`, `RCURVBIN[i]`, `RBRADAIN[i]`,
  `RBRADBIN[i]` — define curvature and width of each ray.
- **`NSAMAX_WR`**: the active-species count, kept for `wr` compatibility.
- Single-ray scalars (`RF`, `RPI`, ...) are not as exhaustive as in `wr`
  — the array form is assumed.

## Library source organization

Rough role classification of the ~27 `wrx/*.f90` files (file names are
estimated):

| Group | Main files | Role |
|---|---|---|
| **API layer** | `wrx_api.f90`, `wrx_param_registry.f90`, `wrx_state.f90` | C-ABI entry |
| **Main solver** | `wrxcalc.f90`, `wrxexec.f90` | Ray integration + beam-shape evolution |
| **Beam shape** | `wrxbeam.f90` (estimated) | Time evolution of curvature/width tensors |
| **Wave equation** | `wrxdisp.f90` (estimated) | Refractive-index tensor (possibly shared with wr) |
| **Damping** | `wrxdamp.f90` (estimated) | Cyclotron damping, Landau damping |
| **Common module** | `wrxcomm.f90` | Global state (WRXCOMM) |
| **I/O** | `wrxparm.f90`, `wrxfile.f90` (estimated) | Namelist, result logging |
| **Interactive menu** | `wrxmenu.f90` (estimated) | Specific to the `wrx2` CLI |
| **Regression** | `wrxregress.f90` (estimated) | Phase-0 baselines |
| **Graphics** | `wrx_graphics_stubs.f90` | Stubbed in the library build |

## Implementation differences from `wr`

| | `wr` | `wrx` |
|---|---|---|
| **Per-ray state variables** | position + wave-number + power (≈20 double/step) | position + wave-number + power + **curvature + width** (≈40 double/step) |
| **Compute cost (N rays)** | O(N × NSTPMAX) | O(N × NSTPMAX) (constant factor ≈ 2×) |
| **Absorption model** | point source | **Gaussian cross-section** integral |
| **Rays needed for the same physical accuracy** | 10–50 | **1** (or a few) |

## Memory consumption

```
Ray trajectory (wrx): NRAYMAX × NSTPMAX × (20–40 double) × 8 bytes
Beam-shape data:       NRAYMAX × NSTPMAX × (10–20 double) × 8 bytes
```

For `NRAYMAX=1, NSTPMAX=10000` this is roughly 3–4 MB. The advantage of
`wrx` is that physical accuracy is higher while memory stays comparable
to `wr`.

## PIC build dependencies

```
libwrxapi.so
├── lib/lib*_pic.a
├── pl/libplcomm_pic.a
├── eq/libeqcomm_pic.a   (used when MODELG=3)
├── mtxp/libmtxp_pic.a
└── bpsd/libbpsd_pic.a
```

## References

- [`docs/wrx-library/architecture.md`](https://github.com/k-yoshimi/task/blob/develop/docs/wrx-library/architecture.md)
- [Common Architecture](../../../portal/en/common/architecture.md)
- `wrx/wrx_api.h` — C-ABI header
- `wrx/wrx_api.f90` — Fortran entry layer
- `wrx/wrx_param_registry.f90` — parameter registry
- The `wr` module design page (`docs/sphinx/modules/wr/en/design.md`) —
  shared physical background
