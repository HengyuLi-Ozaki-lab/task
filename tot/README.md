# TASK/TOT — Integrated Transport Simulator Orchestrator

`tot` is the integrated front-end that composes the per-physics modules
(`pl, eq, tr, ti, fp, dp, wr, wm`) into a single interactive simulator.
The current `totmain.f90` is intentionally thin: it initializes each
module, parses its namelist, and dispatches to `tot_menu` which routes
the user to the per-module menus.

## Build

```sh
make                                   # standard tot binary (interactive, with graphics)
make EXTRA_DEFS=-DTOT_NO_GRAPHICS      # tot binary without GSOPEN/GSCLOS calls
```

The `TOT_NO_GRAPHICS` preprocessor guard is the foundation for the
upcoming Phase L-4 (`libtotapi.so`) build, which links against the PIC
versions of per-module libraries and excludes graphics dependencies.

Note: with `TOT_NO_GRAPHICS` defined, the source no longer calls
`GSOPEN` / `GSCLOS`, but `LIBS` still references `libgrf.a` so the link
succeeds. Actually dropping the graphics library from the link is
deferred to Phase L-4.

## Regression tests (Phase L-0)

`totregress.f90` writes `tot_regress.dat` when run with
`TOT_REGRESS_DUMP=1`. See `test_run/README.md` and
`docs/superpowers/plans/2026-04-18-tot-library-L0-baseline.md`.

## Library-ization roadmap (Phase L)

| Phase | Status | Description |
|-------|--------|-------------|
| L-0   | done   | Integrated regression baselines |
| L-1   | done   | Graphics call guarded by preprocessor flag |
| L-2   | TODO   | `tot_state.f90`, `tot_api.f90` C-ABI stubs |
| L-3   | TODO   | `tot_param_registry.f90` (union of submodule namelist) |
| L-4   | TODO   | `libtotapi.so` shared library build |
| L-5   | TODO   | Python wrapper `python/totlib/` |
| L-6   | TODO   | 4-layer integrated tests |
| L-7   | TODO   | Parameter-optimization workflow |

See specs in `docs/superpowers/specs/`.
