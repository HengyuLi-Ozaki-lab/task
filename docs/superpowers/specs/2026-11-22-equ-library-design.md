# TASK/EQU library interface — design

Status: approved by the author on 2026-11-22; updated with what the implementation found (sections 6.1, 7, 8,
9.2, 9.3; marked *found in implementation*). Branch `feat/equ-library-interface` (product line).

EQU is TASK's free-boundary equilibrium code (M. Azumi; `equ/`). Today it runs only as the interactive program
`equ`. This document specifies a library interface for it in the pattern of EQ's and TR's (the TR design
`2026-04-17-tr-library-design.md`, `docs/eq-library/architecture.md`): a C ABI in a shared library
`equ/libequapi.so`, a Python wrapper `python/equlib/`, and a stdio MCP server `python/mcp-servers/equ_mcp/`.

Line citations are at the product line `ee8a6af5`; `equ/` there is byte-identical to `equ/` on upstream PR
k-yoshimi/task#226 (`898b2bc5`, tree `79690aeb`).

## 1. Purpose and scope

### 1.1 Purpose

A caller (Python, a C driver, an MCP client, later TASK Web Client) can set EQU's inputs, compute a free-boundary
equilibrium, read its result and write it as a G-EQDSK file, without the menu, without graphics, without
standard input, and without the process ending on bad input.

The first user is the PLATO case of the CPC paper: the paper's EQU–TR runs cannot be reproduced through the
platform today because EQU has no library interface.

### 1.2 Scope

- Lifecycle: `init`, `finalize`.
- Inputs: `read_parm` (an `&EQU` namelist file), `set_param`, `set_param_str` (and `set_params` in Python and
  MCP), with a registry of the `&EQU` names. Coil data comes from the file `KNAMCOIL` names.
- `validate`: every check in one batch before the run; `run` refuses with the same checks.
- `run` in two modes: mode 1 is the menu's `R` command; mode 0 is its first step alone (section 5).
- Output: `get_state` (a fixed-layout C struct), `get_psi_rz`, `write_geqdsk`, `last_error`.
- The Fortran changes the interface needs to be safe (section 9): error returns in place of the process-ending
  statements on the library's path, and a reset of the state a second run reads.
- Tests at four layers, including the equality of the library's G-EQDSK with the program's (section 14); CI;
  documents.

### 1.3 Not in scope (later phases or other tasks)

- **EQU–TR coupling.** The menu's `C` command (`tr_exec`: the mock "TOPICS-TR" step of `equtr*.f90`), and any
  coupling of EQU with `tr` or `trx`. A later phase.
- **EQU in TOT and in `libtotapi_mono.so`.** `pl/noequlib.f` defines a module `equunit_mod`, the same name as
  `equ/equunit.f90`, and `tot/Makefile:33` links it. A later phase decides the seam.
- Coil data as arrays through the interface (an `equ_set_coil` call). The file is the only route for now.
- `EQUSAVE` (the menu's `S`, a TASK/EQ-style binary file): it has two defects (section 19) and G-EQDSK is the
  interchange format; not exported.
- Graphics (`G`), the CSV coil table (`Z`, `equ_convert.f90`), the menu's namelist line input.
- Committed reference results under `test_run/baselines/` (`regen-baselines.yml` with an `equ_*` case): a
  follow-up pull request, with the author's approval of the regeneration.
- An EQU module in TASK Web Client (a separate task-web task) and the installers that copy the wrappers.
- Any change of EQU's equations, defaults or iteration (rule R8: those are questions for the lead first;
  section 20).

### 1.4 Constraints

- The library never reads standard input and never ends the process: a stdio MCP server owns stdin and stdout
  (compare task-web issue #202, `MODEFR`). It may write to unit 6; the MCP server moves fd 1 to stderr as EQ's
  does (`python/_fd_isolation.py`).
- Upstream's direction: validation in one batch before the run (k-yoshimi/task#143); every library-reachable
  `STOP` becomes an error return (#142).
- The program `equ` and the target `libequ.a` keep their behaviour: the Makefile changes only add variables and
  targets (no change in the structure of existing ones; module independence, #300, is K. Yoshimi's).
- On valid input, the library's mode-1 result equals the program's `R` to 1e-10.

## 2. What EQU is today

- Program flow (`equmain.f90:10-29`): `gsopen` (GSAF; prompts on stdin for a display type), `OPEN(7,SCRATCH)`,
  `equ_init` (units, `flxtab`, `eqinit` = JT-60U defaults), `tr_init`, `equ_parm(1,'equparm')` (the `&EQU`
  namelist from the file `equparm`), then the menu loop on stdin (`eqmenu`).
- `R` (`equmenu.f90:42-47`) = `equ_prof` → `tr_prof` → `equ_calc`:
  1. `equ_prof` (`equunit.f90:58-73`): `eqflin` reads the coil file (unit 18), `eqchek` checks and derives the
     inputs, `eqgrd` builds the R–Z grid, `eqset` runs the Solovev start, the setup loop (`eqequ`, at most
     `MSETUP` steps) and 10 FCT steps, then `eqout`, `eqpl_init`, `eqpl_prof` (bpsd). It drops every `ierr`.
  2. `tr_prof` (`equtrunit.f90:28-39`): `trset` turns the pressure into an analytic density and a temperature on
     a TR grid; `trpl_put` puts them into bpsd's `plasmaf`.
  3. `equ_calc` (`equunit.f90:77-89`): `eqpl_get` takes `plasmaf` back and rebuilds the adiabatic invariants,
     `eqfct` (at most `IEQMAX` FCT steps), `eqout`, `eqpl_put` (bpsd `equ1D`, `metric1D`, `plasmaf`).
  Without step 2, step 3 indexes `sit(0)` (`equpl.f90:182`): a bounds abort under `-fcheck=all`.
- `E` (`equmenu.f90:93`) = `equ_eqdsk_write` (`equ_eqdsk.f90:10-158`): G-EQDSK on unit 21 through
  `FWOPEN(21,KNAMEQ,1,MODEFW,'EQ')`; pl's default `MODEFW = 5` prompts for the file name on stdin.
- Measured on macOS (gfortran 15, `-O0 -fcheck=all`), 2026-11-22, `R` then `E`:

  | Case | setup error | after `eqset`'s 10 FCT steps | after `equ_calc`'s FCT | time |
  |---|---|---|---|---|
  | QUEST (`equparm.quest`, `coildata.quest`) | 6.0e-8 | 5.7e-1 | 2.8e-1 (20 steps, `IEQMAX` reached) | 6.5 s |
  | ITER#1 (`equparm.ITER#1`, `coildata.ITER#1`) | 9.9e-8 | 4.8e-2 | 1.8e-1 | 7.4 s |

  Both write a 257 × 257 G-EQDSK (13,720 lines, `E16.9`).
- No routine of `eq/` is called; `../eq/libeq.a` in `equ/Makefile` is not needed by any symbol. EQU uses `pl`
  (`plcomm`: `KNAMEQ`, `MODEFW`, `pl_allocate_ns`), `lib` (`libfio`, `libspl1d`, `libkio`, and `libgrf` for
  graphics), `bpsd`, and links `mtxp` without using it.

## 3. Architecture

| Layer | Artefact | Note |
|---|---|---|
| Fortran kernel | `equ/equ*.f90` (unchanged except section 9); new `equ/equ_status.f90` (section 9.2), added to `SRCS` | shared with the program |
| C ABI | `equ/equ_api.h`; `equ/equ_api.f90` (module `equ_api`, functions `equ_api_*` exported `BIND(C, NAME='equ_*')`); `equ/equ_state.f90` (the `BIND(C)` state type); `equ/equ_param_registry.f90` | EQ's layout and naming |
| Shared library | `equ/libequapi.so` (`make -C equ libequapi.so`) | links `pl`, `lib`, `bpsd` PIC archives; no graphics |
| C checks | `equ/tests/c_abi/test_run_so.c`, `test_negative.c` (both through dlopen); targets `equ_api_check_so`, `equ_api_check_all` | EQ's dlopen drivers |
| Program for comparison | `equ/equ_nogr` (`make -C equ equ_nogr`): the program linked with `equ/equ_static_stubs.f90` instead of GSAF | new target; `equ` itself unchanged |
| Python | `python/equlib/`: `_ffi.py`, `equlib.py` (`Equ`), `state.py` (`EquState`), `errors.py`, `README.md`, `examples/`, `tests/` | library path `EQULIB_PATH` |
| MCP | `python/mcp-servers/equ_mcp/`: `server.py` (FastMCP `task-equ`), `pyproject.toml`, `README.md`, `tests/` | |

The library calls EQU's routines in the order `equ_prof`, `tr_prof` and `equ_calc` call them, checking each
status, rather than calling those three: `equunit_mod` uses `eqgout_mod` (graphics), and `equ_prof` drops its
statuses. The comparison test (section 14) holds the library to the program's order.

## 4. C ABI

```c
/* equ/equ_api.h */
#define EQU_STATE_ABI_VERSION 1
enum equ_error { EQU_OK = 0, EQU_ERR_INVALID = 1, EQU_ERR_NOT_INIT = 2,
                 EQU_ERR_CALC_FAILED = 3, EQU_ERR_NOT_IMPL = 4 };

int    equ_init(void);
int    equ_read_parm(const char *path);
int    equ_set_param(const char *name, double value);
int    equ_set_param_str(const char *name, const char *value);
int    equ_validate(equ_diag_entry_t *diags, int cap, int *ndiag);
int    equ_run(int mode);
int    equ_get_state(equ_state_t *state);
int    equ_get_psi_rz(int nr, int nz, double *psi);   /* psi[iz*nr + ir], C order */
int    equ_write_geqdsk(const char *path, int overwrite);
int    equ_last_error(char *buf, int buflen);
int    equ_finalize(void);
int    equ_state_abi_version(void);
size_t equ_state_size(void);
```

- The codes and their Python exceptions are EQ's (`EqlibInvalidParamError` and so on, named `Equlib…`).
  Every function but the two layout queries returns `EQU_ERR_NOT_INIT` before `equ_init`, before any other
  check.
- `equ_last_error` copies the message of the last failure (at most `buflen-1` characters, NUL-terminated), as
  `eq_last_error`. Every failure of `read_parm`, `run` and `write_geqdsk` sets it.
- `equ_diag_entry_t` and the diagnostic codes are EQ's (`OUT_OF_RANGE`, `INCONSISTENT_PAIR`,
  `OUT_OF_RANGE_AFTER_DEP`, `FILE_MISSING`, `MISSING_REQUIRED`); `equ_validate` returns `EQU_OK` with
  `*ndiag = 0`, or `EQU_ERR_INVALID` with the entries (counting past `cap`).
- Names: at most 63 characters; string values at most 80 (the longest `CHARACTER` of `&EQU`); a longer one is
  refused, not cut. Paths for `read_parm` and `write_geqdsk`: at most 1023 characters.
- `equ_get_psi_rz` is `BIND(C)` and checks the lifecycle and that `(nr, nz)` equal the state's (EQ exports its
  counterpart as a name-mangled helper without checks; EQU does not copy that).
- Lifecycle: `equ_init` always resets (EQ's behaviour, not TR's no-op): the defaults of `eqinit`, plus the state
  of section 9.3. `equ_finalize` clears the flags and the message and never fails.

## 5. Run modes

| Mode | Steps | Equals |
|---|---|---|
| 1 | `eqflin`, `eqchek`, `eqgrd`, `eqset`, `eqout`, `eqpl_init`, `eqpl_prof`; `trset`, `trpl_init`, `trpl_put`; `eqpl_get`, `eqfct`, `eqout`, `eqpl_put` | the menu's `R`; the G-EQDSK comparison uses this mode |
| 0 | the first seven steps (the menu's `equ_prof`) | the equilibrium before the bpsd round trip |
| other | refused: negative → `EQU_ERR_INVALID`; above 1 → `EQU_ERR_NOT_IMPL` | |

- `run` first applies the checks of `validate` and refuses with `EQU_ERR_INVALID` and the first diagnostic in the
  message (TR's pattern).
- An FCT loop that ends at `IEQMAX` without meeting `EEQMAX` is not a failure, as in the program: the state
  carries the FCT step count, the convergence flag (`ieq < 0` in `eqchk`, `equfct.f90:227`) and `erreq`, so a
  caller can see it. Whether it should fail is a question for the lead (section 20).
- **Each run starts from the inputs as the caller set them.** The solver overwrites some of its inputs (`eqout`
  sets `RMAJ`, `RPLA`, `ELIP`, `TRIG`; `eqchek` enlarges `RWMN`, `RWMX`, `ZWMX` and swaps `CVAC` and `CVACST`;
  `eqsol` changes `BTV` and `ZPLA`; `eqflin` sets `KNAMCOIL = 'done'`; `eqadj` moves `RVAC`, `ZVAC`). The
  library keeps an image of every `&EQU` variable as last set by `init`, `read_parm` or `set_param`; `run`, and a
  `set_param` or `read_parm` after a run, first restore the image. So `init`, sets, `run`, `run` gives two equal
  results, and a set after a run changes the input, not the value the solver left. The program's second `R`
  differs (it starts from the overwritten values); the comparison is for a first run.
- After a run, `validate`, a refused `set_param`, a failed `read_parm` leave the run's values in place
  (*found in review*): they swap the inputs in for their time (`image_swap`); a set or read that succeeds starts
  new inputs and drops the result.

## 6. Parameters

### 6.1 Three routes, one image

- `equ_read_parm(path)` opens the file itself (`NEWUNIT`, `IOSTAT`) and reads it with EQU's own namelist reader
  `eqnlin` (`equinit.f90:396-427`), the routine the program's start-up read reaches through `task_parm`. It does
  not go through `task_parm` (its file name is cut at 80 characters and an error leaves unit 25 open). Errors:
  missing file, read error and end of file are `EQU_ERR_INVALID` with the `IOSTAT` text in the message.
  Variables the file does not name keep their values; `read_parm` after `set_param` overrides only what the file
  names.
- `equ_set_param(name, value)` and `equ_set_param_str(name, value)`: the registry, a hand-written `SELECT CASE`
  as EQ's (`eq/eq_param_registry.f90`), with EQ's refusals: malformed subscript, unknown name, a value that is
  not finite, an integer outside `-HUGE(0)..HUGE(0)`, an array index outside the declared bounds; and two EQ does
  not make: a subscript on a scalar, a fraction for an integer.
- `set_params` (Python, MCP): a loop over `set_param`/`set_param_str`, non-transactional, as EQ's.

### 6.2 Array names and origin

`NAME[i]`, the index as declared in Fortran: `IVAC`, `CVAC`, `NCOIL`, `CVACST`, `CVACWG`, `CVACT` are `0:18`;
`RVAC`, `ZVAC` are `0:30`; `ICP`, `CP`, `IEQOUT` are `1:10`. A bare array name is refused. The 0-origin coil
arrays follow EQU's own declaration (as EQ's `PSIB`); the documents say so at each.

### 6.3 The registry (from `eqnlin`, `equinit.f90:398-412`)

| Group | Names |
|---|---|
| device | `DEVICE` (str 8), `DEVNAM` (str 8), `TITLE` (str 70) |
| mesh | `NR`, `NZ`, `NV`, `NSUMAX`, `IUDSYM`, `RWMN`, `RWMX`, `ZWMX` |
| plasma | `BTV` (R·B_t [T m]), `TCUR` (I_p [MA]), `RMAJ`, `RPLA`, `ZPLA`, `ELIP`, `TRIG`, `ELIPUP`, `TRIGUP`, `YH`, `YD`, `QAXI`, `QSUR`, `XXLI` |
| profile | `ICP[1..10]`, `CP[1..10]` |
| coils | `KNAMCOIL` (str 80), `IVAC[0..18]`, `NCOIL[0..18]`, `CVAC[0..18]`, `CVACST[0..18]`, `CVACWG[0..18]`, `CVACT[0..18]`, `ISVAC` |
| boundary | `MSFX`, `RVAC[0..30]`, `ZVAC[0..30]`, `ISEP`, `DSEP`, `ILIMT`, `IVBND`, `RLOOP`, `ZLOOP` |
| convergence | `MSETUP`, `ESETUP`, `IEQMAX`, `EEQMAX`, `IODMAX`, `EODMAX`, `IADMAX`, `EADMAX`, `BAVMAX`, `BAVMIN` |
| output | `IEQOUT[1..10]`, `IEQRD` |

- Names the namelist accepts but nothing reads (`IVP`, `IVTAB`, `IVGRP`, `JEQRD`, `IEQWT`, `JEQWT`, and the
  dummies `EQFILE`, `RWAL`, `ZWAL`) are refused by `set_param` with a message saying they are unused;
  `read_parm` accepts them as the program does.
- `CVACT` is used only by `C`, which is out of scope; it is registered because the namelist has it, and
  `describe_parameters` says it has no effect on `run`.
- The metadata (type, group, unit, description, default) lives in the MCP server's `PARAMETER_REGISTRY`, as EQ's;
  a test parses `equ_param_registry.f90` and checks that the registry, the MCP table and the integer list agree.

### 6.4 Coil data

The file `KNAMCOIL` names, in `eqflin`'s format (`equinit.f90:448-474`): for each group `n = 1..18` with
`NCOIL(n) > 0`, one header line and `NCOIL(n)` lines of `(3d10.3)`: R [m], Z [m], weight; then, if `ILIMT > 0`,
one header line and `ILIMT` lines of `(2d10.3)` limiter points. Groups are matched by order. A relative path is
taken from the working directory, as in the program. `KNAMCOIL = 'done'` keeps the coils already in memory
(after `init`, eqinit's JT-60U set). The default `'init'` names no file: `validate` reports it.

## 7. State (`equ_state_t`, `EQU_STATE_ABI_VERSION = 1`)

A fixed-layout struct, valid part `1..n`, the rest zero (EQ's rule and EQ's #246 layout check:
`equ_state_abi_version`, `equ_state_size`, and `_ffi.py` refuses a library whose layout differs). Capacities from
`equcomm.f90`: `EQU_MAX_NR = EQU_MAX_NZ = 257`, `EQU_MAX_NV = 101`, `EQU_MAX_NSU = 1542`, `EQU_NCV = 19`.

| Part | Fields (code variable) |
|---|---|
| counts | `nr`, `nz`, `nv`, `nsu`; `mode` of the run |
| convergence | `fct_steps` (abs of `ieq`), `fct_converged` (`ieq < 0`), `erreq`: the last FCT loop of the run (mode 1: `equ_calc`'s; mode 0: the 10 steps `eqset` runs, which it labels "check of equilibrium accuracy through ode", `equset.f90:62-67`) |
| axis | `raxis`, `zaxis`, `psi_axis` (`saxis`) |
| separatrix | `xpoint_status` (`iisep`: > 0 found; the code's negative failure codes kept), `rsep`, `zsep` (`rg(irsep)`, `zg(izsep)` when found), `psi_sep` (`psep`) |
| scalars | `ip` (`ttcu` [MA], computed), `ip_target` (`tcur` [MA]), `rbt` (`btv` [T m]), `beta_t` (`beta`), `beta_s` (`bets`), `beta_j` (`betj`), `li` (`zzli`), `q_axis` (`qqv(1)`: *found in implementation*, the variable `qaxis` is set again after `eqout`'s print by the `eqaxi` of its `eqsep`), `q_surf`, `q95`, `qqj`, `rmaj`, `rpla`, `elip`, `trig`, `el95`, `volume` (`vlv(nv)`) |
| coils | `cvac[0..18]` (the fitted and fixed currents, in the code's unit) |
| grid | `rg[nr]`, `zg[nz]` |
| profiles on `nv` surfaces (1 = axis) | `psi` (`siv`), `psit` (`hiv`), `pressure` (`prv`, converted to Pa), `q` (`qqv`), `f` (`rbv`, R·B_t), `vol` (`vlv`), `rminor` (`rpv`), `rcentre` (`rtv`), `kappa` (`elv`), `delta` (`dlv`) |
| boundary | `rsu[nsu]`, `zsu[nsu]` (open polygon, as `eqtrc` leaves it) |

- Units are the code's, named in `describe_state_schema` per field, with one conversion: `prv` holds MPa after
  `eqout` (`equsub.f90:1443, 1469`); the state gives Pa. The β fields are as `eqout` prints them (percent).
- `get_state` before a successful run returns `EQU_OK` with the struct zeroed and `nr = 0` (EQ's behaviour);
  Python's `get_state` raises instead.
- `betp`, the upper and lower κ and δ and `asp` are locals of `eqout` and lost when it returns: not in version 1.

## 8. Validation (one batch, shared with `run`)

Read-only; each entry names the parameter and the reason. The list, in three kinds:

- **Bounds the arrays need** (each a bounds abort today): `3 ≤ NV ≤ 101` (`eqout` prints `rbv(nv-2)`),
  `NSUMAX ≤ 1542`, `MSFX ≥ −29` (a positive `MSFX` is lowered by `eqchek` to 17, or 9 when symmetric, and is not
  refused), `0 ≤ NCOIL(n) ≤ 100`, `0 ≤ ILIMT ≤ 100`, `IVBND = 0` (it counts vacuum boundary points `RVBND`,
  `ZVBND` that no input sets). `NR` and `NZ` are `2**k + 1` in 3..257 (*found in review*: the Buneman solver of
  `eqgrd`/`eqpde` halves both directions; another value gives a wrong psi without an error); `eqchek` lowers a
  value above 257 without a word (`equinit.f90:533-535`), the library refuses it.
- **What `eqchek` refuses** (`equinit.f90:527-778`), reported before the run instead of after the coil file is
  read: `IEQRD ≠ 0` (its `ierr` 1); `NR·NZ·NV = 0` (2); more fitted coil groups (`IVAC(i) ≥ 0`) than marker points
  (3), with `MSFX` as `eqchek` leaves it (lowered when positive), taken from `eqchek` itself (below).
- **Marker points** (*found in implementation*, corrected in two reviews): every marker `(RVAC(k), ZVAC(k))`,
  k = 0..|MSFX|, inside the box as `eqchek` leaves it, and that box's inner edge > 0. When nothing above is reported,
  the library runs `eqflin` and `eqchek` on a copy of the inputs (`eqchek_preview`: the stash, the Solovev
  constants and `nivac`, the coil and limiter arrays are put back) and checks what they leave: the markers given
  (`MSFX ≤ 0`; `RMAJ`, `RPLA` taken from them) or generated from the shape (`MSFX > 0`), and the box widened to
  `RMAJ ∓ 1.2 RPLA`, `|Z| < 1.2 ELIP RPLA`. QUEST with `ZWMX = 0.6` indexed `svac` at -177 in `eqadj0`; the
  defaults with `ELIPUP = 1.5` or `ZPLA = 0.4` generate markers above the box.
- **Files and choices**: `KNAMCOIL` names an existing file unless `'done'`; the file holds the groups and lines
  `NCOIL` and `ILIMT` ask for (a read-only scan with `IOSTAT`); `RWMN > 0`, `RWMX > RWMN`, `ZWMX > 0`;
  `ICP(1)` one of the values `eqpfds` and `eqequ` handle (±1, ±2, ±9, ±11); `ISVAC` 0 or 1; `ISEP` −4 to 4 (the
  code uses its sign);
  `IEQMAX`, `MSETUP`, `IODMAX`, `IADMAX` ≥ 0.

A value the code accepts but the physics may not (for example a coil far outside the box) is not refused: that
is the lead's to decide. The internal `WRITE`s of real numbers into messages use `IOSTAT` (EQ's
`eq_api_validate` pattern); `itoa`'s `I0` into 16 characters cannot fail.

## 9. Process safety

### 9.1 Standard input and output

- Never called by the library: `gsopen`, `eqmenu`/`task_klin`, `task_parm` mode 0, `eqgout`.
- `write_geqdsk` sets `MODEFW` to 0 (`overwrite` true) or 3 (refuse an existing file) and `KNAMEQ` to the path
  before `equ_eqdsk_write`, so `FWOPEN` never prompts; the C entry point refuses a path over 80 characters
  (`KNAMEQ`'s length), and `equlib` writes such a path from its directory under its base name.
- The library does not use unit 7 (the program's scratch unit for namelist lines) and opens its files with
  `NEWUNIT`.
- Unit 6 stays as it is (the solver prints its progress); the MCP server isolates fd 1.

### 9.2 Process-ending statements on the library's path: the Fortran changes

| Site | Today | Change |
|---|---|---|
| `equinit.f90:449-450` (`eqflin`) | `OPEN` of the coil file without `IOSTAT`: a missing file ends the process with a runtime error | `IOSTAT`; a failure goes through `equ_fail` (below); unit 18 closed on every error return |
| `equsub.f90:803-804` (`eqerr`, called from `eqtrc`) | `STOP` | `equ_fail` |
| `equsub.f90:1296-1297`, `1314-1315` (`eqlin`) | `STOP` (`irst = nr-1`; more than 20 failed traces) | `equ_fail` |
| `equsub.f90:2320-2321` (`eqtrc`) | `STOP` (`s1*s2*s3*s4 = 0`) | `equ_fail` |
| callers of `eqtrc`/`eqlin` up to `eqset` and `eqfct` (`eqequ`, `eqlin`, `eqout`, `eqrcu`, `eqsep`, …) | carry on | return when a failure is recorded (one test after each call) |
| `equ_eqdsk.f90:137-152` | error paths return with unit 21 open | close it |
| `eqtrc`, where it stores a contour point (*found in implementation*) | a contour longer than `isrzdm` (half of it when `IUDSYM = 1`) indexed past `zrsu` (QUEST with `RVAC(0) = 0.2`) | refuse the next point through `equ_fail`; the bound leaves room for `eqequ`'s read of `rsu(nsu+2)` |
| `eqout`, the flux-loop value `psloop` (*found in review*) | `(RLOOP, ZLOOP)` off the grid indexed `psi` out of bounds (QUEST with `ZWMX = 0.9` and the JT-60U default point) | computed only on the grid, else 0; `psloop` is read nowhere, so no result changes |

- A new module `equ_status_mod` holds a library-mode flag (false by default), a failure flag and a message.
  `equ_fail(msg)` writes the message to unit 6; outside library mode it then stops, as the code does today, so
  the program behaves as before in every case and `equmenu.f90` is not changed. In library mode (set by
  `equ_init`, TR's pattern) it records the failure and returns; the callers return in turn and the library
  returns `EQU_ERR_CALC_FAILED` with the message.
- On valid input nothing changes: the comparison test (section 14) runs the program and the library on the same
  inputs after the change.
- The remaining `STOP`s of `equ/` are outside the library's path (`eqdsk0`, `eqinp`/`eqrest`, `trsvq`,
  `equ_convert.f90`, the program's end); a test lists them with their line so a new one on the path is seen.
- Aborts the bounds checks catch (`eqaxi`/`eqlin` walks, `eqind` at the box edge) are not all preventable
  before the run; `validate` closes those that follow from the inputs. A run that still reaches one ends the
  process, as for EQ and TR; the tests run `--forked`.

### 9.3 A second run in one process

`eqinit` does not reset: `iad`, `ieq`, `iod`, `time`, `itime`, `iread`, `RVAC`/`ZVAC`, the coil filaments of
groups 5 to 18, `svac` of groups without filaments, `btol` (read at `equsub.f90:2134`, never set), the
`SAVE`/`DATA` locals of `eqadj` and `eqadj0`, the init flags of `equpl_mod` and `trpl_mod`, and bpsd's
`plasmaf` (which `eqpl_prof` reads on a second run), and (*found in implementation*, by restoring each module
variable to its value before a first run in turn) the profile `rbv`: with `ICP(2) = 2` the setup loop of `eqequ`
starts from it, so a second QUEST run moved 7,013 numbers by about 1e-9. `equ_init` and `run` reset what the library can reach;
where a reset needs a Fortran change (a `SAVE` local), it is a listed change of the same kind as 9.2. The test:
two runs in one process, and a run after another case, give the result of a fresh process to 1e-10.

### 9.4 Graphics

The library's objects are `SRCS` minus `equgout.f90`, `equmenu.f90`, `equ_convert.f90` and `equunit.f90` (which
uses `eqgout_mod`); none of the rest references GSAF or `libgrf` (`nm -u`). No graphics stubs are linked into
the library. `equ_nogr` (the comparison program) links `equ/equ_static_stubs.f90`: no-op GSAF entries for the
symbols `libgrf`, `equgout.f90` and `equ_convert.f90` reference (`GSOPEN` without its prompt among them).

## 10. Writing G-EQDSK

`equ_write_geqdsk(path, overwrite)` calls `equ_eqdsk_write` after a successful run, and checks afterwards that a
non-empty file exists. Refused: no equilibrium (`EQU_ERR_INVALID`), a blank or too long path, an existing file
without `overwrite`. The file is the program's, number for number, with its properties: title blank, `current` =
the input `TCUR` × 1e6, `sibry` = 0, `pres` and `pprime` in MPa (section 20), the boundary an open polygon,
`limitr = ILIMT`.

## 11. Python wrapper `equlib`

- `Equ` (context manager; one live instance per process, as EQ's): `read_parm(path)`, `set_param`,
  `set_param_str`, `set_params`, `validate() -> list`, `run(mode=1)`, `get_state() -> EquState`,
  `get_psi_rz() -> numpy array [i_r, i_z]`, `write_geqdsk(path, overwrite=False)`, `last_error()`, `close()`.
- `EquState`: a dataclass; `to_dict()` with upper-case keys, JSON-serialisable.
- Errors: `EqulibError` and `EqulibInvalidParamError`, `EqulibNotInitializedError`,
  `EqulibCalculationFailedError`, `EqulibNotImplementedError`, `EqulibInitError`, `EqulibAbiError`;
  a failed call appends `last_error()` to the message.
- Library lookup: explicit path, `EQULIB_PATH`, `<repo>/equ/libequapi.so`; `RTLD_LAZY`; the layout check of
  `python/_abi_check.py` (`prefix="equ"`). `MONO_LIB_PATH` is not honoured (EQU is not in the mono image).

## 12. MCP server `equ_mcp` (`task-equ`)

Tools: `init`, `read_parm`, `set_param`, `set_param_str`, `set_params`, `validate`, `run`, `get_state`,
`get_psi_rz`, `write_geqdsk`, `finalize`, `describe_parameters`, `describe_state_schema`, `run_and_get_state`.
EQ's patterns: one process-wide `Equ`; `_fd_isolation.install()` in `main()` only; `ToolError` with the library's
message; `write_geqdsk` refuses an existing path unless `overwrite`; `run_and_get_state` re-initialises first.
Relative paths are taken from the server's working directory, which the README says how to set.

## 13. Build

`equ/Makefile`, additions only:
- `SRCS_CORE` (the library's sources, section 9.4), a PIC object tree `obj/pic`, `mod_pic`, as `eq/Makefile`;
- `libequapi.so`: `SRCS_CORE` + `equ_status.f90` + `equ_state.f90` + `equ_param_registry.f90` + `equ_api.f90`,
  linked with `../pl/libpl_pic.a`, `../lib/libtask_pic.a` and its own PIC build of bpsd (`make -C equ bpsd_pic`,
  as eq and tr do), without `$(FLIBS)` (EQ's link line, `eq/Makefile:471-488`); one-line build from a clean tree
  through order-only prerequisites (#230);
- `equ_api_check_so`, `equ_api_check_all`, `libequapi_inspect`;
- `equ_nogr`: the program, linked from the same PIC archives (and `../lib/libgrf_pic.a`) with
  `equ_static_stubs.f90` in place of GSAF, so the pytest job builds it without the non-PIC libraries;
- `.gitignore`: `equ/equ`, `equ/equ_nogr`, `equ/libequapi.so`, the PIC trees.

No new `../` path beyond those the module already has (`../pl`, `../lib`, `../../bpsd`), so the build stays
inside #300's direction.

## 14. Tests

| Layer | What | Where |
|---|---|---|
| C ABI | lifecycle, pre-init refusals, unknown and malformed names, refusals of each run mode, layout queries, re-init, use after finalize; a missing coil file returns an error and the process lives | `equ/tests/c_abi/*.c`, run by `equ_api_check_all` (in CI) |
| Python | FFI and layout; registry against the Fortran `CASE` list and the MCP table; each validation entry (one test per entry, each seen to fail by mutation); `read_parm` errors; run refusals; the four former `STOP`s reached from crafted inputs where an input reaches them; `write_geqdsk` refusals and overwrite; `get_psi_rz` equals the G-EQDSK's `psirz`; second run and run-after-another-case equal a fresh process | `python/equlib/tests/` |
| Comparison (1e-10) | QUEST and ITER#1 from `equ/example`: the program `equ_nogr` (`R`, `E`, path, `Q` on its stdin) against the library's mode 1, through `read_parm` and through `set_param` replaying the same namelist; every number of the two G-EQDSK files equal within 1e-10 relative (in practice the same text). Same machine, so it runs on macOS and Linux | `python/equlib/tests/test_program_parity.py` |
| MCP | registry shape and schema, handlers, bulk sets, the six shared fd-isolation cases, a stdio subprocess that writes a G-EQDSK | `python/mcp-servers/equ_mcp/tests/` |

- Fixtures: the example files of `equ/example`, read in place (copied into a temporary directory per test,
  because `KNAMCOIL` is relative).
- Timing: a run takes about 7 s at `-O0`; the suite adds about 3 minutes to a pytest job (its limit is 20).
- `equ_mcp` joins `SERVERS` in `python/tests/test_fd_isolation.py`.

## 15. CI

In `.github/workflows/python-tests.yml`'s pytest job: `equ` in the `.so` loop (before `tot`), in the
`_api_check_so` loop, the build of `equ_nogr` and `equ_api_check_all`; the tests are collected by `pytest python/`. `equ` in
`clean-tree-build.yml`'s matrix. The mono job's module list is unchanged (EQU is not in the mono image) and its
comment says why. No job is added or renamed, so the ruleset is unchanged.

## 16. Documents

`docs/equ-library/architecture.md` (EQ's structure); `python/equlib/README.md`;
`python/mcp-servers/equ_mcp/README.md`; Sphinx `docs/sphinx/modules/equ/{en,ja}/` with `index`, `quickstart`,
`parameters`, `state`, `mcp`, added to `MODULES` and the portal; `CHANGELOG.md` (an `EQU library` section);
`docs/product-line/upstream-status.md` (a row: product-only until #226 merges, then the re-cut).

## 17. Base, branches and route (the author's decision of 2026-11-22: option a)

- Branch `feat/equ-library-interface` from `origin/kyoshimi-develop`; fork pull request into `kyoshimi-develop`
  with the label `product-only`, because `develop` still has the old fixed-form `equ/`.
- After #226 merges: the same commits cherry-picked onto `develop` for the upstream pull request. `equ/` is then
  the same tree on both lines, so the Fortran and the new files apply cleanly; expected conflicts are
  `python-tests.yml`, `clean-tree-build.yml` and `CHANGELOG.md` (measured when it is cut). That pull request
  waits for a free place under the cap of six open upstream pull requests.
- The EQU files are a new lane (`equ/equ_api.*`, `equ/equ_state.f90`, `equ/equ_param_registry.f90`,
  `python/equlib/`, `python/mcp-servers/equ_mcp/`); this work touches no file of the EQ or TR lane.

## 18. Order of work (one pull request, commits in this order)

1. Makefile additions and `equ_nogr`, with the comparison test against itself (the baseline of everything after).
2. The Fortran changes of section 9.2 and 9.3, each with its test; the comparison still equal.
3. C ABI, registry, state, validate, run, G-EQDSK, C checks.
4. `equlib` and its tests, the comparison test against the library.
5. `equ_mcp` and its tests.
6. CI.
7. Documents, `CHANGELOG.md`, `upstream-status.md` (last, rule R9).

## 19. Risks and findings

| Item | Effect | Handling |
|---|---|---|
| FCT does not meet `EEQMAX` in either example | a caller may take an unconverged result | state fields; question to the lead |
| G-EQDSK `pres`/`pprime` in MPa, not Pa | an EQU G-EQDSK loaded into EQ (`MODELG` 5) or TR has a pressure 1e6 too small | documented; question to the lead before any change of the program's output |
| `EQUSAVE`: `RIP = tcu·1e-6`; `PSI0` operator precedence (`equfile.f90:60`) | its binary would be wrong | not exported; reported |
| `eqlim` with `ILIMT > 0` reads uninitialised locals (`equsub.f90:1191-1192`, `1238-1239`) | results with a limiter are undefined | not refused (the code takes the input); documented, and a question to the lead |
| debug lines `@@@ point 1..10` in `equsub.f90` read `rsu(nsu+1)`, `rsu(nsu+2)` | a bounds abort when `nsu` reaches the array end; uninitialised reads | reported (k-yoshimi/task#228 item); not changed here unless a test hits it |
| `trpl_init` puts species with mass and charge 0 (`fmass`, `fchrg` never set) | bpsd consumers would see them | none consume them in this scope; reported |
| Re-entrancy hazards not all visible by reading | a second run differs | the second-run test |
| Kyoto `work` tree moves `equ/` to `eq/eq-free` | a later rename merge | the files move with it; nothing to do now |

## 20. Questions for others (none blocks this work)

- **The lead (Prof. Fukuyama), as questions, not changes:** whether `equ_calc`'s FCT result with
  `erreq` 0.2–0.6 against `EEQMAX` 1e-3 is the intended result of `R`; whether G-EQDSK pressure should be in Pa;
  the limiter branch of `eqlim`.
- **K. Yoshimi:** the C interface (PLAN D3: he reviews C interfaces). A short proposal (sections 4 to 7) can go
  to him once the fork pull request is up, in the next batch note (rule R10).

## 21. Acceptance

1. `make -C equ libequapi.so` from a clean tree; `equ_api_check_all` passes; `nm` shows only `equ_*` entry points
   added.
2. `python -m pytest python/equlib python/mcp-servers/equ_mcp --forked --timeout=120 --timeout-method=signal`
   passes on macOS and in CI; the comparison test runs (no skip) in both pytest jobs, read from the log.
3. The program `equ` builds and behaves as before (`R`, `E` on both examples give the same file as before the
   change).
4. The four required checks green on the fork pull request.
5. Documents and the `CHANGELOG.md` line; the `upstream-status.md` row.
