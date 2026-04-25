# `fp` — Fokker-Planck

```{admonition} What you'll learn
:class: tip

How to use `fplib`, the Python wrapper that calls TASK/FP (the
**Fokker-Planck** solver: it solves for the particle distribution
function on a 5D phase space) from Python. The chapter covers building
the shared library, a minimal hello-world, the 55 registered parameters,
moment outputs, the `KNAMEQ` string parameter, and the four-layer test
suite.
```

## Overview — what `fp` does

**TASK/FP** is a solver for the **Fokker-Planck equation** in tokamak
plasmas. Unlike the fluid equations of `tr` / `ti` (which evolve
temperature and density), `fp` **discretises the particle distribution
function $f(r, p, \theta, t)$ itself on a 5D phase space** and evolves
it in time.

Typical applications:

- Detailed analysis of **NBI-driven fast ions** (cases where the
  Maxwellian assumption breaks down)
- Electron distribution distortion and current-drive efficiency under
  **wave drive** (LH, ECCD)
- Slowing-down of **fusion alpha particles**
- Acceleration of **runaway electrons** during disruptions

Main outputs (moments):

- `RNT[isa][nr]` — particle-density profile (per active species)
- `RWT[isa][nr]` — energy-density profile
- `RTT[isa][nr]` — average-temperature profile
- `RJT[isa][nr]` — current-density profile
- `RPCT[isa][nr]` — collisional power exchange
- `RPWT[isa][nr]` — wave-heating power exchange
- Scalar: `timefp` (simulation time)

## User guide

```{toctree}
:maxdepth: 1

build
hello-world
parameters
parameter-setting
state
context-manager
faq
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
mcp
testing
```

## Appendix

```{toctree}
:maxdepth: 1

appendix-sensitivity
```

## Suggested reading order

1. {doc}`build` — build the shared library
2. {doc}`hello-world` — the smallest 5D-grid setup
3. {doc}`parameters` — the complete list of 55 parameters
4. {doc}`parameter-setting` — scalar / array / string (`KNAMEQ`) entry
5. {doc}`state` — the moment outputs explained
6. {doc}`context-manager` — why memory management matters

When you get stuck, see {doc}`faq`. The full API is in
{doc}`api-reference`. The input ↔ output correspondence is summarised
in {doc}`appendix-sensitivity`.

## Differences from `tr`/`ti` (summary)

| | `tr` (pure transport) | `ti` (integrated transport) | `fp` (Fokker-Planck) |
|---|---|---|---|
| **Equations** | Fluid (Maxwellian assumption) | Fluid + auxiliary physics | **Distribution function in 5D** |
| **C ABI** | 5 + str + validate | 5 | 6 (with str) |
| **Phase space** | 1D (radial) | 1D (radial) | **5D** (r, p, θ, species, t) |
| **Memory** | Low | Medium | **High** |
| **Use case** | Transport-model comparison | Experimental reproduction | Detailed analysis of non-thermal distributions |
