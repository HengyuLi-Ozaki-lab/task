# TASK/EQU library interface — architecture

EQU (`equ/`, M. Azumi's free-boundary equilibrium code) runs as the interactive
program `equ`. This interface lets Python, a C driver or an MCP client run it
without the menu, graphics or standard input, and without the process ending on
the failures it knows of. It follows EQ's (`docs/eq-library/architecture.md`).
Design and decisions: `docs/superpowers/specs/2026-11-22-equ-library-design.md`;
plan: `docs/superpowers/plans/2026-11-22-equ-library.md`.

## Layers

| Layer | Artefact | Purpose |
|---|---|---|
| Fortran kernel | `equ/equ*.f90` | the solver, shared with the program |
| Failure record | `equ/equ_status.f90` | `equ_fail`: stops outside library mode, records and returns inside it |
| C ABI | `equ/equ_api.h`; `equ/equ_api.f90`, `equ_state.f90`, `equ_param_registry.f90`, `equ_image.f90` | 13 entry points, the state struct, the registry, the input image |
| Shared library | `equ/libequapi.so` | `make -C equ libequapi.so` |
| C checks | `equ/tests/c_abi/test_run_so.c`, `test_negative.c` | `make -C equ equ_api_check_all` |
| Program for comparison | `equ/equ_nogr` | the program linked with no-op GSAF entries (`equ_static_stubs.f90`) |
| Python | `python/equlib/` | `Equ`, `EquState`, errors |
| MCP | `python/mcp-servers/equ_mcp/` | FastMCP server `task-equ` |

```
python/equlib (ctypes)        C driver (equ_api.h)        MCP client
        |                            |                        |
        +------------+---------------+              python/mcp-servers/equ_mcp
                     |                                        |
              equ/libequapi.so  <-----------------------------+
              equ_api.f90: init, read_parm, set_param[_str], validate,
                           run, get_state, get_psi_rz, write_geqdsk, ...
              equ_image.f90: the inputs as set; the run-state reset
              equ_param_registry.f90: NAME / NAME[i] -> &EQU variable
                     |
              EQU's routines (SRCS without equgout, equmenu, equ_convert,
              equunit), pl, lib, bpsd -- no graphics
```

## C ABI

`equ/equ_api.h` declares `equ_init`, `equ_read_parm`, `equ_set_param`,
`equ_set_param_str`, `equ_validate`, `equ_run`, `equ_get_state`, `equ_get_psi_rz`,
`equ_write_geqdsk`, `equ_last_error`, `equ_finalize`, `equ_state_abi_version`,
`equ_state_size`. Return codes are EQ's: 0 OK, 1 invalid, 2 not initialised,
3 calculation failed, 4 not implemented. The diagnostic record of `equ_validate`
is EQ's.

## The run

`equ_run(1)` calls the steps of the menu's `R` in their order, checking each status:

| Program routine | Steps |
|---|---|
| `equ_prof` (`equunit.f90`) | `eqflin` (the coil file), `eqchek`, `eqgrd`, `eqset` (Solovev start, setup loop, 10 FCT steps), `eqout`, `eqpl_init`, `eqpl_prof` |
| `tr_prof` (`equtrunit.f90`) | `trset`, `trpl_init`, `trpl_put` (the mock TR interface's profiles into bpsd) |
| `equ_calc` (`equunit.f90`) | `eqpl_get`, `eqfct` (`IEQMAX` FCT steps), `eqout`, `eqpl_put` |

`equ_run(0)` stops after `equ_prof`. The checks of `equ_validate` run first.

## Process safety

- **Standard input.** The library calls nothing that reads it (`gsopen`, the menu,
  `task_parm` mode 0, `eqgout`). `equ_write_geqdsk` sets `MODEFW` to 0 or 3 and
  `KNAMEQ` before EQU's writer, so `FWOPEN` does not prompt.
- **Process-ending statements.** The four `STOP`s on the path of `R` (`eqerr`,
  `eqlin` twice, `eqtrc`) and a missing coil file go through `equ_fail`; `eqtrc`
  also refuses a contour longer than its arrays. Outside library mode `equ_fail`
  stops, so the program is unchanged. The other `STOP`s of `equ/` are off the
  library's path (`python/equlib/tests/test_stop_sites.py` holds that list).
- **Checks before the run.** Array bounds (`NR`, `NZ` = 2**k+1 for the Buneman
  solver, `NV` >= 3), what `eqchek` refuses, the box, the profile and switch
  values, marker points inside the box as `eqchek` widens it, the coil file
  (exists, holds what `NCOIL` and `ILIMT` ask for).
- **Off-grid reads.** `eqout` computes the unused flux-loop value `psloop` only
  when `(RLOOP, ZLOOP)` is on the grid.
- **Unit 6.** The solver prints its progress; the MCP server moves fd 1 to stderr.

## Each run starts from the inputs as set

`equ_image.f90` keeps every `&EQU` variable as last set by `init`, `read_parm` or
`set_param`, and restores it before a run and before a set that follows a run
(the solver overwrites `RMAJ`, `RPLA`, `ELIP`, `TRIG`, the box, the markers,
`CVAC`/`CVACST`, `KNAMCOIL`). Before each run it resets what a run reads and
`eqinit` does not set: the iteration counters, `iread`, `btol`, the vacuum field
`svac`, the profile `rbv` (with `ICP(2) = 2` the setup loop starts from it), and
bpsd's `plasmaf`. `equ_init` also zeroes the marker points and coil groups 5..18.
Measured: a second run, a run after another case and a run after a set equal a
fresh process's (`test_repeat_run.py`). After a run, `validate`, a refused set
and a failed read swap the inputs in for their time and leave the run's values
(`image_swap`; `test_after_run.py`).

## The state

`equ_state_t` (fixed layout, `EQU_STATE_ABI_VERSION = 1`, EQ's #246 rule for
changes): counts, the run's mode, the last FCT loop's steps, convergence flag and
error, axis, X point, current (computed and target), beta, li, q (on axis as
`qqv(1)`, as `eqout` prints it), shape, volume, the coil currents, the grid, ten
profiles on the flux surfaces (pressure in Pa) and the boundary.

## Tests

| Layer | Where | What |
|---|---|---|
| C | `equ/tests/c_abi/` | QUEST through dlopen; 36 refusal cases |
| Comparison | `python/equlib/tests/test_program_parity.py` | the library's G-EQDSK equals `equ_nogr`'s on QUEST and ITER#1, every number within 1e-10, through `read_parm` and through `set_params` |
| Python | `python/equlib/tests/` | each validation check (each seen to fail when removed), the registry against the namelist, errors, the second run, G-EQDSK, psi |
| MCP | `python/mcp-servers/equ_mcp/tests/` | registry, schema, handlers, fd isolation, QUEST over stdio |

Committed reference results under `test_run/baselines/` are a later step: they
need an `equ_*` case in `regen-baselines.yml`.

## Known limitations

- One instance per process (Fortran module state).
- Not in this version: the menu's `C` (the mock TR step) and EQU–TR coupling; EQU
  in TOT and in `libtotapi_mono.so` (`pl/noequlib.f` defines a module named as
  `equ/equunit.f90`'s, and tot links it); coil data as arrays; `EQUSAVE`.
- EQU's G-EQDSK writes `pres` and `pprime` in MPa; the library writes the
  program's file unchanged. The FCT loop of both examples ends at `IEQMAX` without
  meeting `EEQMAX`; the state reports it, the run does not fail. Both are
  questions for the code's lead.
