# TASK Plasma Library

Welcome to the portal for the TASK family of plasma-physics modules,
re-packaged as in-process shared libraries with thin `ctypes`-based
Python wrappers.

```{note}
This Sphinx manual supersedes the standalone LaTeX document at
`docs/manual/task-library-manual.tex`, which is now frozen at its 2026-04
snapshot. New changes land here.
```

## Modules

::::{grid} 2 3 3 4
:gutter: 3

:::{grid-item-card} **tr** — Transport
:link: ../../tr/en/index.html

1-D radial transport simulation for tokamaks. Evolves density,
temperature, current and equilibrium profiles.
**Status:** full chapter
:::

:::{grid-item-card} **eq** — Equilibrium
:link: ../../eq/en/index.html

MHD equilibrium solver. Reads EQDSK or analytic profiles, returns
ψ-surface geometry and derived scalars.
**Status:** full chapter
:::

:::{grid-item-card} **ti** — Transport-Integrated
:link: ../../ti/en/index.html

Integrated transport interface coupling `tr` with auxiliary physics.
**Status:** placeholder
:::

:::{grid-item-card} **fp** — Fokker-Planck
:link: ../../fp/en/index.html

Fast-ion / energetic-particle distribution solver.
**Status:** placeholder
:::

:::{grid-item-card} **wr** — Wave Ray
:link: ../../wr/en/index.html

Geometric-optics ray tracing for RF heating / current drive.
**Status:** placeholder
:::

:::{grid-item-card} **wrx** — Wave Ray Extended
:link: ../../wrx/en/index.html

Beam-tracing extension of `wr`.
**Status:** placeholder
:::

:::{grid-item-card} **tot** — Orchestrator
:link: ../../tot/en/index.html

Composes runs across all modules (`eq` → `tr` / `ti` / `fp` / `wr` / `wrx`).
**Status:** placeholder
:::

::::

## Foundation

```{toctree}
:maxdepth: 2
:caption: Foundation

common/architecture
```

## Audience

This manual is written for researchers and engineers who want to call the
TASK modules from Python (or directly through the C ABI). Readers are
assumed to be comfortable with Python and plasma-physics terminology, but
no prior exposure to the legacy `tr2` / interactive menu workflow is required.

## Indices

* {ref}`genindex`
* {ref}`modindex`
