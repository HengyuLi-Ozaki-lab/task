# `equ` — Free-boundary equilibrium

```{admonition} What you'll learn
:class: tip

How to run TASK/EQU, M. Azumi's **free-boundary** MHD equilibrium code, from
Python (`equlib`), C (`equ/equ_api.h`) or an MCP client (`equ_mcp`), and get its
equilibrium as a state, as psi(R, Z) and as a G-EQDSK file.
```

## What `equ` does

EQU solves the free-boundary equilibrium of a tokamak with coils: the plasma
boundary follows from the coil currents (fixed or fitted to marker points), the
pressure and current profiles. Its inputs are the `&EQU` namelist and a coil file;
it runs as the interactive program `equ`. The library interface runs the same code:

- **`run(mode=1)`** — the program's `R` command: the setup solve, the mock TR
  interface's profiles through bpsd, the FCT solve. Its G-EQDSK equals the program's
  (`R` then `E`) to 1e-10 on the examples.
- **`run(mode=0)`** — the first step of `R` alone (`equ_prof`).

```{note}
`equ` is not `eq`. `eq` (TASK/EQ) solves the fixed-boundary equilibrium or loads
one from a file; `equ` computes the boundary from the coils. An `equ` G-EQDSK can be
loaded into `eq` (`MODELG=5`), with two caveats: EQU writes the pressure in MPa
(see [State](state.md)), and `eq` takes at most 1343 boundary points (`NSUM`)
where EQU's contour arrays hold 1542 (`isrzdm`): loading a file with more fails
(`EQ_ERR_CALC_FAILED`; IERR 9 in EQ's reader).
```

```{toctree}
:maxdepth: 1

quickstart
parameters
state
mcp
```

The design and its decisions: `docs/superpowers/specs/2026-11-22-equ-library-design.md`;
the architecture: `docs/equ-library/architecture.md`.
