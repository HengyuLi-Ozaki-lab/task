# `tr` — Transport

```{admonition} What you'll learn
:class: tip

How to call TASK/TR (1-D tokamak transport simulation) from Python via
the `trlib` library. We cover building the shared library, the minimal
hello-world (5 lines), the four ways to set parameters (scalar / array /
string / `validate()`), the FAQ, and how to run the regression tests.
```

## What `tr` does

**TASK/TR** performs **1-D (radial) transport simulations** for tokamaks
and spherical tokamaks. It tracks how the radial profile of the plasma
evolves in time, solving the particle-number, temperature, current, and
magnetic-equilibrium balance self-consistently.

Representative output quantities:

- `RN[i][j]` — density of species $j$ at radial point $i$
- `RT[i][j]` — temperature, same indexing
- `AJ[i]`    — current-density profile
- `QP[i]`    — safety-factor $q$ profile
- Scalars: `T` (time), `WPT` (stored energy), `Q0` (axis $q$),
  `BETAN` ($\beta_N$), and 9 more — 13 in total

For Fortran-side design and parameter-registry details see
[Common Architecture](../../../portal/en/common/architecture.md) and
`docs/tr-library/architecture.md`.

## User guide

```{toctree}
:maxdepth: 1

physics-overview
build
hello-world
parameters
parameter-setting
input-files
state
context-manager
faq
applications
tutorials
```

## Reference

```{toctree}
:maxdepth: 1

quickstart
api-reference
```

## Internals

```{toctree}
:maxdepth: 1

design
extending-tr
mcp
testing
```

## Appendix

```{toctree}
:maxdepth: 1

appendix-mdlkai
appendix-sensitivity
limitations-and-references
numerical-stability-and-diagnostics
```

## Suggested reading order

If this is your first encounter with `tr`, the recommended path is:

1. {doc}`build` — build the shared library so `import trlib` works
2. {doc}`hello-world` — the 5-line minimum example that advances a plasma
3. {doc}`parameters` — what input parameters exist (full registered list)
4. {doc}`parameter-setting` — the four ways to set inputs (scalar / array / string / `validate`)
5. {doc}`state` — the output parameters and physical quantities you can read from `tr.get_state()`
6. {doc}`context-manager` — what `with` means and the gotchas around it
7. {doc}`quickstart` — an executable notebook that walks through the whole flow

When stuck, see {doc}`faq`. The full API spec is at {doc}`api-reference`.
For deeper material, see {doc}`appendix-mdlkai` (transport-model details)
and {doc}`appendix-sensitivity` (input ↔ output correspondence).
