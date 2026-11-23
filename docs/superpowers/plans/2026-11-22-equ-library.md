# EQU library interface — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** `equ/libequapi.so`, `python/equlib`, `python/mcp-servers/equ_mcp` as specified in
`docs/superpowers/specs/2026-11-22-equ-library-design.md` (approved by the author 2026-11-22), with the
library's G-EQDSK equal to the program's to 1e-10 on QUEST and ITER#1.

**Architecture:** EQ's layering (Fortran API module with `BIND(C)` exports, a hand-written registry, a
fixed-layout state struct, a ctypes wrapper, a FastMCP server). EQU's kernel stays shared with the program; the
only kernel changes are the error returns of spec §9.2, active in library mode only.

**Tech stack:** gfortran (13.3 on CI, 15 on macOS), GNU make, C (gcc/clang) for the C checks, Python 3.11/3.13,
ctypes, numpy, `mcp` (FastMCP), pytest with `--forked --timeout=120 --timeout-method=signal`.

**Where:** clone `~/task-web-scratch/equ-api/task`, branch `feat/equ-library-interface` (from
`origin/kyoshimi-develop` `ee8a6af5`). Build environment for every `make` on this Mac:

```bash
E="env -u AR -u LD -u NM -u RANLIB -u CC -u CFLAGS -u CPPFLAGS -u LDFLAGS PATH=/opt/homebrew/bin:/usr/bin:/bin"
```

Test command (repo root, conda env `task`):

```bash
PYTHONPATH=python:python/mcp-servers EQULIB_PATH=$PWD/equ/libequapi.so \
  python -m pytest python/equlib python/mcp-servers/equ_mcp --forked --timeout=120 --timeout-method=signal -q
```

GNU make 3.81 compares whole seconds: after editing a source, `sleep 1.2` before `make`, and check the `.o` is
newer than the source.

---

## File map

| File | Responsibility |
|---|---|
| `equ/equ_status.f90` (new) | `equ_status_mod`: library-mode flag, failure flag and message, `equ_fail`, `equ_failed`, `equ_status_clear` |
| `equ/equinit.f90`, `equ/equsub.f90`, `equ/equ_eqdsk.f90` (edit) | the four `STOP`s and the coil `OPEN` through `equ_fail`; failure checks after calls; unit 21 closed on error |
| `equ/equ_state.f90` (new) | `equ_state_c`, `equ_diag_entry_c`, capacities, `EQU_STATE_ABI_VERSION`, diag codes |
| `equ/equ_param_registry.f90` (new) | `equ_param_set`, `equ_param_set_str`, `value_refused`, `parse_array_subscript`, `equ_param_is_unused` |
| `equ/equ_image.f90` (new) | `equ_image_mod`: the parameter image (save from / restore to the `&EQU` variables) and the reset of the non-namelist state (spec §5, §9.3) |
| `equ/equ_api.f90` (new) | module `equ_api`: the `BIND(C)` entry points; run steps; validate; G-EQDSK |
| `equ/equ_api.h` (new) | the C header |
| `equ/equ_static_stubs.f90` (new) | no-op GSAF entries for `equ_nogr` |
| `equ/tests/c_abi/test_run_so.c`, `test_negative.c` (new) | C checks |
| `equ/Makefile` (edit, additions) | `SRCS` += `equ_status.f90`; PIC tree; `bpsd_pic`; `libequapi.so`; `equ_api_check_so`, `equ_api_check_all`, `libequapi_inspect`; `equ_nogr` |
| `python/equlib/{__init__,_ffi,equlib,state,errors}.py`, `README.md`, `examples/quickstart.py` | wrapper |
| `python/equlib/tests/*.py`, `python/equlib/tests/_geqdsk.py` | tests and a G-EQDSK number reader |
| `python/mcp-servers/equ_mcp/{__init__,server}.py`, `pyproject.toml`, `README.md`, `tests/*.py` | MCP server |
| `python/tests/test_fd_isolation.py` (edit) | `equ_mcp` in `SERVERS` |
| `.github/workflows/python-tests.yml`, `clean-tree-build.yml` (edit) | CI |
| `.gitignore` (edit) | build artefacts |
| `docs/equ-library/architecture.md`, `docs/sphinx/modules/equ/{en,ja}/*`, `docs/sphinx/Makefile`, portal (new/edit) | documents |
| `CHANGELOG.md`, `docs/product-line/upstream-status.md` (edit, last commit) | ledgers |

---

### Task 0: the suite before the branch

- [ ] **0.1** In the clone at `origin/kyoshimi-develop` (the branch adds nothing yet): build all seven libraries
and mono as `task-library-fork-workflow` describes, run the whole suite with the CI flags, `MONO_LIB_PATH`
unset, and record passed / skipped / xfailed counts in the notes folder. This is the count Task 8 compares with.

### Task 1: Makefile additions, `equ_nogr`, and the comparison harness

**Files:** modify `equ/Makefile`, `.gitignore`; create `equ/equ_static_stubs.f90`,
`python/equlib/__init__.py` (empty docstring module for now), `python/equlib/tests/__init__.py`,
`python/equlib/tests/_geqdsk.py`, `python/equlib/tests/_program.py`, `python/equlib/tests/test_program_self.py`.

- [ ] **1.1 Measure what `equ_nogr` must stub.** Link the program with no GSAF and read the undefined symbols:

```bash
cd equ && $E make libequ.a obj/equcomm.o obj/equmain.o
$E /opt/homebrew/bin/gfortran obj/equmain.o obj/equcomm.o libequ.a ../pl/libpl.a ../lib/libtask.a \
   ../lib/libgrf.a ../../bpsd/libbpsd.a -o /dev/null 2>&1 | grep -o '"_[a-z0-9_]*"' | sort -u
```

Expected: the GSAF names (`_gsopen_`, `_gsclos_`, `_pages_`, `_pagee_`, `_move2d_`, `_draw2d_`, `_setrgb_`,
`_gtext2d_`, …). The stub file defines exactly that set, each as an empty `SUBROUTINE NAME` with assumed
arguments ignored (gfortran accepts a no-argument definition for calls with arguments only across separate
compilation, which is how `eq/eq_static_stubs.f90` works; copy its form). `GUCLIP` and `NGULEN` are functions:
copy their bodies from `eq/eq_static_stubs.f90:43-53`.

- [ ] **1.2 Add the targets** (append to `equ/Makefile`, nothing existing changes):

```make
# --- No-graphics program for the library comparison (equ_nogr) ---
equ_nogr: $(OBJC) libs libequ.a $(OBJDIR)/equmain.o $(OBJDIR)/equ_static_stubs.o
	$(FLINKER) $(OBJDIR)/equmain.o $(OBJC) $(OBJDIR)/equ_static_stubs.o $(LIBS) -o $@ $(FFLAGS) $(LIBX_MTX)
```

`FLINKER` is not in task-web's generated `make.header`; add `FLINKER ?= $(FCFREE)` at the top of the additions
(only when unset). Add `equ/equ`, `equ/equ_nogr`, `equ/libequapi.so`, `equ/obj/pic/`, `equ/mod_pic/`,
`equ/tests/c_abi/*.o` and the C test binaries to `.gitignore` (pattern of the eq block at `.gitignore:145-151`).

- [ ] **1.3 `_geqdsk.py`: read every number of a G-EQDSK file.** The writer's format is `(6a8,3i4)` then
`(5e16.9)` blocks, with `2020` and an integer pair line for the boundary. Read the header line's last three
integers, then split the rest with a regular expression for Fortran reals (`E16.9` fields run together when
negative: `0.1E+01-0.2E+00`), keeping integers of the boundary-count line as numbers:

```python
import re
_NUM = re.compile(r"[-+]?\d*\.\d+(?:[EeDd][-+]?\d+)?|[-+]?\d+")

def read_numbers(path):
    with open(path) as f:
        head = f.readline()
        body = f.read()
    ints = [int(x) for x in head[48:].split()]
    nums = [float(x.replace("D", "E").replace("d", "e")) for x in _NUM.findall(body)]
    return ints, nums

def assert_same(path_a, path_b, rtol=1e-10, atol=1e-300):
    ia, na = read_numbers(path_a)
    ib, nb = read_numbers(path_b)
    assert ia == ib, (ia, ib)
    assert len(na) == len(nb), (len(na), len(nb))
    for k, (x, y) in enumerate(zip(na, nb)):
        assert abs(x - y) <= max(atol, rtol * max(abs(x), abs(y))), (k, x, y)
```

- [ ] **1.4 `_program.py`: run `equ_nogr` on a case in a temporary directory.**

```python
import os, shutil, subprocess
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
EXAMPLE = REPO / "equ" / "example"
CASES = {
    "quest":  ("equparm.quest", "coildata.quest", "coildata"),
    "iter01": ("equparm.ITER#1", "coildata.ITER#1", "coildata.ITER#1"),
}

def stage(case, workdir):
    parm, coil, coil_as = CASES[case]
    shutil.copy(EXAMPLE / parm, Path(workdir) / "equparm")
    shutil.copy(EXAMPLE / coil, Path(workdir) / coil_as)
    return Path(workdir) / "equparm"

def program_geqdsk(case, workdir, out="prog.geqdsk"):
    exe = REPO / "equ" / "equ_nogr"
    stage(case, workdir)
    r = subprocess.run([str(exe)], cwd=workdir, input=f"R\nE\n{out}\nQ\n",
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    return Path(workdir) / out
```

(`equ_nogr`'s stub `GSOPEN` reads nothing, so stdin starts with `R`.)

- [ ] **1.5 `test_program_self.py`: the harness against itself** (two program runs in two directories give the
same file; the reader sees 257 × 257 and the expected number count). Run it; expect PASS. This is the baseline
every later task keeps green.

- [ ] **1.6 Build check:** `$E make -C equ equ` still builds the GSAF program (with `FLIBS` as before) and
`equ_nogr` builds without GSAF. Commit: `build(equ): equ_nogr, the program without graphics, for the library comparison`.

### Task 2: the error returns and the second-run state (spec §9.2, §9.3)

**Files:** create `equ/equ_status.f90`; modify `equ/equinit.f90` (`eqflin`), `equ/equsub.f90` (`eqerr`,
`eqlin`, `eqtrc` and the callers listed in 2.3), `equ/equ_eqdsk.f90`, `equ/Makefile` (`SRCS`, dependencies).

- [ ] **2.1 `equ_status.f90`:**

```fortran
! equ_status.f90
! Failure record of EQU's solver. Outside library mode equ_fail stops,
! as the code did before; equ_init of the library interface sets
! library mode, and equ_fail then records the failure and returns.
MODULE equ_status_mod
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: equ_library_mode, equ_fail, equ_failed, equ_status_clear, equ_status_message
  LOGICAL, SAVE :: equ_library_mode = .FALSE.
  LOGICAL, SAVE :: failed = .FALSE.
  CHARACTER(LEN=256), SAVE :: message = ' '
CONTAINS
  SUBROUTINE equ_fail(msg)
    CHARACTER(LEN=*), INTENT(IN) :: msg
    WRITE(6,'(A)') TRIM(msg)
    IF (.NOT. equ_library_mode) STOP
    IF (.NOT. failed) message = msg
    failed = .TRUE.
  END SUBROUTINE equ_fail
  LOGICAL FUNCTION equ_failed()
    equ_failed = failed
  END FUNCTION equ_failed
  SUBROUTINE equ_status_clear
    failed = .FALSE.
    message = ' '
  END SUBROUTINE equ_status_clear
  FUNCTION equ_status_message() RESULT(m)
    CHARACTER(LEN=256) :: m
    m = message
  END FUNCTION equ_status_message
END MODULE equ_status_mod
```

The program's text before each `STOP` is kept as the message (`' stop at eqtrc : s1*s2*s3*s4=0 '` and so on), so
its unit-6 output is unchanged.

- [ ] **2.2 The four sites and the coil open.** `equsub.f90:803-804`: `call equ_fail('===error stop===')`,
`return`. `:1296-1297`, `:1314-1315`, `:2320-2321`: the same with their own text. `equinit.f90:449-450`:

```fortran
         if(nid.ne.5) then
            open(nid,FILE=knamcoil,STATUS='OLD',FORM='FORMATTED',IOSTAT=ios)
            if(ios.ne.0) then
               call equ_fail('XX eqflin: cannot open the coil file '//trim(knamcoil))
               ierr=7
               return
            endif
         endif
```

and `close(nid)` before each `ierr=8`/`ierr=9` return. `equ_eqdsk.f90:137-152`: `CLOSE(neqdsk)` before each
error `RETURN`.

- [ ] **2.3 The checks after calls.** After every call of `eqtrc`, `eqerr`, `eqlin`, and of any routine that
(transitively) calls them, inside `eqequ`, `eqlin`, `eqlim`, `eqout`, `eqrcu`, `eqsep`, `eqvac`, `eqeqv`, `eqset`,
`eqfct`: `if(equ_failed()) return`. The call sites are `equsub.f90:602, 638, 642, 646, 650, 654, 655, 667, 672,
675, 692, 1258, 1287, 1310, 1324, 1407, 1428, 1482, 1535, 1818, 2065, 2072, 2105, 2219, 2594, 2645, 2646, 2693,
2694`, `equset.f90:34-67`, `equfct.f90:29-69` (re-list with `grep -n "call eq" equ/*.f90` after editing, because
lines move). Each routine gets `use equ_status_mod, only: equ_failed, equ_fail`.

- [ ] **2.4 Check that the program is unchanged** (a development check, not a CI test): keep a copy of Task 1's
`equ_nogr` as `~/task-web-scratch/equ-api/ref/equ_nogr_task1`; after the edits run both on QUEST and ITER#1 with
`_program.py`'s stdin and compare the files with `_geqdsk.assert_same` from a one-off Python call; expect the
same text (`cmp` exit 0).

- [ ] **2.5** `make -C equ equ` and `equ_nogr` build; commit: `fix(equ): the process-ending statements on the solve path go through equ_fail (stops as before outside library mode)`.

### Task 3: C ABI, registry, image, state, C checks

**Files:** create `equ/equ_state.f90`, `equ/equ_param_registry.f90`, `equ/equ_image.f90`, `equ/equ_api.f90`,
`equ/equ_api.h`, `equ/tests/c_abi/test_run_so.c`, `equ/tests/c_abi/test_negative.c`; modify `equ/Makefile`.

- [ ] **3.1 `equ_api.h`** — the declarations of spec §4, the enum, the diag codes and lengths (EQ's 64/128), and
`equ_state_t` field by field in the order of 3.2.

- [ ] **3.2 `equ_state.f90`** — `EQU_STATE_ABI_VERSION = 1`; capacities `EQU_MAX_NR = 257`, `EQU_MAX_NZ = 257`,
`EQU_MAX_NV = 101`, `EQU_MAX_NSU = 1542`, `EQU_NCV = 19`; `TYPE, BIND(C) :: equ_state_c` with, in this order:
`INTEGER(C_INT) nr, nz, nv, nsu, mode, fct_steps, fct_converged, xpoint_status`; `REAL(C_DOUBLE) erreq, raxis,
zaxis, psi_axis, rsep, zsep, psi_sep, ip, ip_target, rbt, beta_t, beta_s, beta_j, li, q_axis, q_surf, q95, qqj,
rmaj, rpla, elip, trig, el95, volume`; `cvac(EQU_NCV)`; `rg(EQU_MAX_NR)`, `zg(EQU_MAX_NZ)`; profiles
`psi, psit, pressure, q, f, vol, rminor, rcentre, kappa, delta` each `(EQU_MAX_NV)`; `rsu(EQU_MAX_NSU)`,
`zsu(EQU_MAX_NSU)`. `equ_diag_entry_c` as `eq_diag_entry_c`.

- [ ] **3.3 `equ_param_registry.f90`** — copy `parse_array_subscript` and the finite/integer guard of
`eq/eq_param_registry.f90:255-371`. One `CASE` per name of spec §6.3, assigning the module variable of
`equcomm.f90` (`par_mod`, `geo_mod`, `eqv_mod`, `equ_mod`, `vac_mod`, `cnt_mod`, `aaa_mod`; `KNAMCOIL` in
`eqinit_mod`). Arrays check `idx` against `LBOUND`/`UBOUND` of the variable. Integers: `INT(value)` after the
guard. `equ_param_is_unused(b)` is true for `IVP IVTAB IVGRP JEQRD IEQWT JEQWT EQFILE RWAL ZWAL`; `equ_param_set`
returns `ierr = 2` for them (the API maps it to `EQU_ERR_INVALID` with "unused by EQU" in `equ_last_error`).

- [ ] **3.4 `equ_image.f90`** — `TYPE equ_image_t` holding a copy of every `&EQU` variable (the list of `eqnlin`,
`equinit.f90:398-412`), `image_save()`, `image_restore()`, and `reset_run_state()` that sets `iad = 0`,
`ieq = 0`, `iod = 0`, `time = 0`, `itime = 0`, `iread = 0`, `btol = 0`, zeroes `rcoil`, `zcoil`, `ccoil` of groups
5 to 18, `svac`, and puts an empty `plasmaf` into bpsd (`plasmaf%nrmax = 0; CALL bpsd_put_plasmaf(...)`, or
whatever the bpsd API offers for a reset; read `bpsd/bpsd_plasmaf.f90` first). The `eqadj` `DATA` locals and the
`equpl_mod`/`trpl_mod` flags are handled in 3.9 if the second-run test shows they matter.

- [ ] **3.5 `equ_api.f90`** — module `equ_api`, EQ's skeleton (`eq/eq_api.f90:49-146, 226-345, 486-515,
905-950`) with:
  - `equ_api_init`: `ft05=5; ft06=6; out=0; CALL flxtab; CALL eqinit; CALL trpl_init`,
    `equ_library_mode = .TRUE.`, `reset_run_state`, `image_save`, flags, `equ_status_clear`.
  - `equ_api_read_parm(path)`: C path → `CHARACTER(1024)`; restore the image if dirty; `OPEN(NEWUNIT=u, ...,
    STATUS='OLD', IOSTAT=ios)`; `CALL eqnlin(u, ist, ierr)`; `CLOSE(u)`; on success `image_save`.
  - `equ_api_set_param`, `equ_api_set_param_str`: restore if dirty, registry, `image_save`.
  - `equ_api_validate`: spec §8 (one `push_diag` per finding, EQ's helper).
  - `equ_api_run(mode)`: mode checks; restore the image if dirty; `reset_run_state`; `equ_status_clear`;
    validate (refuse on the first diagnostic); then the steps of spec §5 with `ierr` and `equ_failed()` checked
    after each; mark dirty after the first step (inputs are about to be overwritten); on success
    `g_has_equilibrium = .TRUE.`, record `mode`.
  - `equ_api_get_state`: zero, check init, fill from the modules (3.2's mapping; `pressure = prv * 1e6`).
  - `equ_api_get_psi_rz(nr, nz, psi)`: lifecycle, equilibrium present, sizes equal; copy `psi(ir+nr*(iz-1))`.
  - `equ_api_write_geqdsk(path, overwrite)`: equilibrium present; path non-blank, ≤ 80; `KNAMEQ = path`;
    `MODEFW = 0` or `3`; `CALL equ_eqdsk_write(ierr)`; `INQUIRE` size > 0.
  - `equ_api_last_error`, `equ_api_finalize`, `equ_api_state_abi_version`, `equ_api_state_size`,
    `c_str_overflows` (EQ's).

- [ ] **3.6 Makefile:** `SRCS_CORE = $(filter-out equgout.f90 equmenu.f90 equ_convert.f90 equunit.f90,$(SRCS))`;
`SRCS_API = equ_state.f90 equ_param_registry.f90 equ_image.f90 equ_api.f90`; the PIC rules, `bpsd_pic` block and
`libs_pic_prereq` copied from `eq/Makefile:157-188, 334-446` with `eq` → `equ` in names; `libequapi.so` from
`eq/Makefile:471-488` (`equcomm.f90` is in `SRCC`, not `SRCS`: include `$(OBJDIR_PIC)/equcomm.o` explicitly and
make every PIC object depend on it); `equ_api_check_so` and `equ_api_check_all` from `eq/Makefile:508-556`
(dlopen drivers only; no static driver).

- [ ] **3.7 C checks.** `test_run_so.c`: dlopen `EQULIB_PATH`, dlsym all thirteen entry points (91 if one is
missing), layout check (92/93), then in a temporary directory with the QUEST files: `equ_init`,
`equ_read_parm("equparm")`, `equ_run(1)`, `equ_get_state` (`nr == 257`, `fct_steps > 0`), `equ_write_geqdsk`,
`equ_finalize`; exit 1..9 by step. `test_negative.c`: every call before init returns 2; unknown name, bare
`IVAC`, `IVAC[19]`, `CP[0]`, `NR` = NaN, a 70-character name → 1; `equ_run(-1)` → 1, `equ_run(2)` → 4;
`equ_write_geqdsk` before a run → 1; `equ_get_psi_rz` with wrong sizes → 1; `KNAMCOIL = "no-such-file"` then
`equ_run(1)` → 1 (validate refuses) and the process is alive; double finalize → 0; layout version.

- [ ] **3.8** Build `make -C equ libequapi.so equ_api_check_all`; expect both drivers OK. Commit:
`feat(equ): the C interface (libequapi.so): init, read_parm, set_param, validate, run, state, G-EQDSK`.

- [ ] **3.9 Second run.** Python test in Task 4 (`test_repeat_run.py`) decides whether 3.4 is enough; any extra
reset found there comes back here as its own commit.

### Task 4: `equlib`

**Files:** `python/equlib/__init__.py`, `_ffi.py`, `errors.py`, `state.py`, `equlib.py`, `README.md`,
`examples/quickstart.py`; tests `test_ffi.py`, `test_param_values.py`, `test_validate.py`, `test_read_parm.py`,
`test_run_errors.py`, `test_geqdsk_write.py`, `test_get_psi_rz.py`, `test_repeat_run.py`,
`test_program_parity.py`, `test_stop_sites.py`.

- [ ] **4.1 `errors.py`, `_ffi.py`, `state.py`, `equlib.py`** — EQ's files with `eq` → `equ`, the struct of 3.2 in
`EquStateC._fields_`, prototypes for the thirteen functions, `check_state_layout(prefix="equ")`, lookup
`EQULIB_PATH` → `<repo>/equ/libequapi.so`, no `MONO_LIB_PATH`. `Equ` methods of spec §11.

- [ ] **4.2 Tests first, each run to fail against a stubbed expectation, then pass:**
  - `test_program_parity.py`: for `quest` and `iter01`: program file (Task 1 harness) vs library file through
    `read_parm`, and vs library file through `set_params` of the same namelist (parsed with a small reader for
    `&EQU` files in the test: `NAME = v, v, ...` and `NAME(i) = v`). `assert_same(rtol=1e-10)`.
  - `test_repeat_run.py`: run, run → equal state; case A then case B → equals B fresh; set after run → equals
    init + set + run.
  - `test_validate.py`: one test per diagnostic of spec §8, each with the input that triggers it and the name
    and code reported; a clean QUEST validates to `[]`.
  - `test_read_parm.py`: missing file, a file with a bad value, a file naming an unknown variable → errors with
    text; read then set overrides; set then read overrides only the named.
  - `test_param_values.py`: EQ's checks (`python/eqlib/tests/test_param_values.py:71-189`) against
    `equ_param_registry.f90` and the MCP table: integer list = integer `CASE`s, every `CASE` is in the MCP
    registry and the reverse, array bounds.
  - `test_run_errors.py`: run before read; mode −1 and 2; missing coil file (validate and run); a coil file with
    fewer lines than `NCOIL` asks.
  - `test_geqdsk_write.py`: refusals (before run, blank, > 80 characters, existing without overwrite), overwrite
    works, the file is non-empty.
  - `test_get_psi_rz.py`: equals the G-EQDSK `psirz` block to 1e-10 relative (the writer prints 9 digits: compare
    within 1e-9 relative there, and say so in the test).
  - `test_stop_sites.py`: lists the `stop` statements of `equ/*.f90` with their line and asserts the set equals the
    known list outside the library's path (so a new one on the path is seen), and drives one former site from an
    input if one is found that reaches it (`eqtrc` with a box too small for the plasma is the candidate: find the
    input by trying `ZWMX` shrinking on QUEST; if none in ten tries reaches a site, the test of the mechanism is
    the C-level one in 3.7 and this test says so).
  - Mutation: each validation check removed in turn (scratch script, `make -C equ libequapi.so`, run
    `test_validate.py`) must fail its test.

- [ ] **4.3 README** (EQ's sections), `examples/quickstart.py` (`--dry-run` as EQ's). Commit:
`feat(equlib): the Python wrapper of libequapi.so, with the comparison against the program`.

### Task 5: `equ_mcp`

- [ ] **5.1** `server.py` from `python/mcp-servers/eq_mcp/server.py` with the tools of spec §12;
`PARAMETER_REGISTRY` (type, group, unit, description, default from `eqinit`) for every registry name;
`STATE_SCHEMA`; `read_parm`; `write_geqdsk(path, overwrite=False)`.
- [ ] **5.2** Tests: `test_server.py` (shape, schema, handlers on a mock), `test_fd_isolation.py` (the six cases of
`python/mcp-servers/fd_isolation_cases.py`), `test_stdio_geqdsk.py` (a `python -m equ_mcp.server` subprocess over
`stdio_client`: `init`, `read_parm`, `run`, `write_geqdsk`, file exists). Add `equ_mcp` to
`python/tests/test_fd_isolation.py` `SERVERS`.
- [ ] **5.3** `pyproject.toml` (EQ's, console script `equ-mcp`), `README.md`. Commit:
`feat(equ_mcp): the MCP server for EQU`.

### Task 6: CI

- [ ] **6.1** `python-tests.yml` pytest job: `equ` into the `.so` loop before `tot`, into the `_api_check_so`
loop, and `make -C equ equ_nogr` after the PIC support libraries; mono job: comment only. `clean-tree-build.yml`:
`equ` in the matrix. Run `python -m pytest python/repo_tests` (ruleset and workflow tests). Commit:
`ci: build and test libequapi.so and equ_nogr`.

### Task 7: documents and ledgers (last; rule R9)

- [ ] **7.1** `docs/equ-library/architecture.md`; Sphinx `modules/equ/{en,ja}/` (`index`, `quickstart`,
`parameters`, `state`, `mcp`, `conf.py` importing `conf_common`); `MODULES` in `docs/sphinx/Makefile`; portal card.
- [ ] **7.2** `CHANGELOG.md` `## [Unreleased]` → `### Added`: **EQU library interface** line;
`docs/product-line/upstream-status.md` row (product-only; re-cut after k-yoshimi/task#226; conflicts expected in
`python-tests.yml`, `clean-tree-build.yml`, `CHANGELOG.md`). Commit: `docs(equ): architecture, Sphinx pages, changelog`.

### Task 8: the gate (no push without the author)

- [ ] **8.1** The whole suite with the CI flags on this Mac (all seven libraries + `equ`; `MONO_LIB_PATH` unset),
compare with the count before the branch (Task 0 run on `origin/kyoshimi-develop`).
- [ ] **8.2** `scripts/install-hooks.sh` from a `kyoshimi-develop` worktree; code review (`superpowers:code-reviewer`)
and, with the author's OK for the paid call, Codex (`codex exec -m gpt-6.2-astra -c model_reasoning_effort=xhigh
--sandbox read-only`); findings HIGH/MED to the author; fixes; marker.
- [ ] **8.3** Ask the author for the push and the fork PR text (label `product-only`).
