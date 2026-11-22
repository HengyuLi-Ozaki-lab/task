# equlib: TASK/EQU, the free-boundary equilibrium code, from Python

`equlib` is the ctypes wrapper of `equ/libequapi.so`, the library interface of
EQU (`equ/`, M. Azumi's free-boundary solver). It follows `eqlib` (EQ's wrapper).
Design: `docs/superpowers/specs/2026-11-22-equ-library-design.md`; the C
interface: `equ/equ_api.h`; architecture: `docs/equ-library/architecture.md`.

| | |
|---|---|
| Library | `equ/libequapi.so` (`make -C equ libequapi.so`) |
| Lookup | explicit path, `EQULIB_PATH`, `<repo>/equ/libequapi.so` |
| Inputs | an `&EQU` namelist file (`read_parm`) and/or `set_param` by name |
| Coil data | the file `KNAMCOIL` names (relative to the working directory) |
| Run | mode 1: the program's `R`; mode 0: its first step (`equ_prof`) |
| Output | `get_state`, `get_psi_rz`, `write_geqdsk` |

## Installation

Build bpsd beside the checkout and `make.header` as for the other modules, then

```bash
make -C equ libequapi.so
export PYTHONPATH=$PWD/python
```

## Quick start

```python
from equlib import Equ

with Equ() as equ:                  # equ_init: EQU's defaults (the JT-60U case)
    equ.read_parm("equparm")        # e.g. equ/example/equparm.quest, as 'equparm'
    print(equ.validate())           # [] when the run may start
    equ.run()                       # mode 1, the program's R
    st = equ.get_state()
    print(st.ip, st.q_axis, st.fct_converged)
    equ.write_geqdsk("quest.geqdsk")
```

`python python/equlib/examples/quickstart.py` runs the QUEST example this way.

## API

| Method | What it does | Errors |
|---|---|---|
| `Equ(lib_path=None)` | load the library, `equ_init`; one live instance per process | `EqulibInitError`, `EqulibAbiError`, `FileNotFoundError` |
| `read_parm(path)` | read an `&EQU` namelist file; names it does not give keep their values; a failed read is undone | `EqulibInvalidParamError` |
| `set_param(name, value)` | `NAME` or `NAME[i]`, the index as Fortran declares it | `EqulibInvalidParamError` |
| `set_param_str(name, value)` | `DEVICE`, `DEVNAM`, `TITLE`, `KNAMCOIL` | `EqulibInvalidParamError` |
| `set_params(dict or pairs)` | several, in order; a `str` value goes to `set_param_str`; not transactional | as above |
| `validate()` | every check of the inputs; a list of `EquDiag(param, code, message)` | -- |
| `run(mode=1)` | mode 1 the program's `R`, mode 0 its first step; refuses with `validate`'s checks | `EqulibInvalidParamError`, `EqulibNotImplementedError`, `EqulibCalculationFailedError` |
| `get_state()` | `EquState` of the last run | `EqulibInvalidParamError` before a run |
| `get_psi_rz()` | psi(R, Z) as numpy `[i_r, i_z]` | as above |
| `write_geqdsk(path, overwrite=False)` | EQU's G-EQDSK writer (the program's `E`); a path over 80 characters is written from its directory | `EqulibInvalidParamError`, `EqulibCalculationFailedError` |
| `last_error()`, `reset()`, `close()` | the library's last reason; `equ_init` again; `equ_finalize` | -- |

## Parameters

The names of the `&EQU` namelist (`eqnlin`, `equ/equinit.f90`); the MCP server's
`describe_parameters` lists them with types, groups, defaults and descriptions.
Arrays: `IVAC`, `NCOIL`, `CVAC`, `CVACST`, `CVACWG`, `CVACT` are `[0..18]`;
`RVAC`, `ZVAC` `[0..30]`; `ICP`, `CP`, `IEQOUT` `[1..10]`. A bare array name, a
subscript on a scalar and a fraction for an integer are refused. `NR` and `NZ` are
`2**k+1` (3, 5, ..., 129, 257): EQU's Buneman solver needs it. `IVP`, `IVTAB`,
`IVGRP`, `JEQRD`, `IEQWT`, `JEQWT` (and the dummies `EQFILE`, `RWAL`, `ZWAL`) are
accepted by `read_parm` but nothing reads them: `set_param` refuses them.

Each run starts from the inputs as set: the solver overwrites some of them
(`RMAJ`, `RPLA`, `ELIP`, `TRIG`, the box, the markers, `KNAMCOIL`), and the
library restores them before the next run or set. After a run, `validate`, a refused set
and a failed `read_parm` leave the run's result in place; a set that succeeds drops it.

## EquState

`nr`, `nz`, `nv`, `nsu`; `scalars` (`mode`, `fct_steps`, `fct_converged`,
`xpoint_status`, `erreq`, `raxis`, `zaxis`, `psi_axis`, `rsep`, `zsep`, `psi_sep`,
`ip` [MA], `ip_target` [MA], `rbt` [T m], `beta_t`, `beta_s`, `beta_j`, `li`,
`q_axis`, `q_surf`, `q95`, `qqj`, `rmaj`, `rpla`, `elip`, `trig`, `el95`,
`volume`); `cvac` (groups 0..18); `rg`, `zg`; `profiles` on the flux surfaces
(`psi`, `psit`, `pressure` [Pa], `q`, `f` = R B_t, `vol`, `rminor`, `rcentre`,
`kappa`, `delta`); the boundary `rsu`, `zsu`. `state.q_axis` and `state.pressure`
read through. `to_dict()` gives upper-case keys.

## What to know

- **The FCT loop.** In both examples the last FCT loop ends at `IEQMAX` without
  meeting `EEQMAX` (`fct_converged` is 0, `erreq` 0.2 to 0.6). The program does not
  treat that as a failure, and neither does the library: look at the state.
- **G-EQDSK pressure is in MPa.** EQU's writer gives `pres` and `pprime` in MPa,
  not Pa (`prv` holds MPa); `write_geqdsk` writes the program's file unchanged. The
  state's `pressure` is in Pa.
- **One instance per process.** Use one process per parallel run.
- **Not in this version:** the program's `C` (the mock TR step), EQU in TOT and
  the mono image, coil data as arrays, `EQUSAVE`'s binary file.

## Tests

```bash
make -C equ libequapi.so equ_nogr
PYTHONPATH=python:python/mcp-servers python -m pytest python/equlib \
    --forked --timeout=120 --timeout-method=signal
```

`test_program_parity.py` compares the library's G-EQDSK with the program
`equ_nogr`'s (the program linked without graphics) on QUEST and ITER#1, every
number within 1e-10; it runs wherever both are built.
