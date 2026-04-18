---
name: module-library-ization
description: "Use when adding a Phase L-style library / Python wrapper / MCP server to a new TASK Fortran module. Covers L-0 baseline through L-7 docs, optional F90 modernization (F-1..F-5), and MCP server creation. Adapted from successfully library-ized tr/fp/ti/wr/wrx/eq modules."
---

# Module Library-ization (TASK Fortran)

Recipe for converting a TASK Fortran module (e.g. `tr`, `fp`, `ti`, `wr`,
`wrx`, `eq`) into a numerically-equivalent shared library + Python
wrapper + MCP server, **without disturbing the existing CLI binary**.

This skill captures the methodology that produced PR #12 .. #79
(see `references/completed-modules.md`).

## When to use

- A new TASK Fortran module needs a `lib<X>api.so` C ABI for embedding,
  scripting, sweeps, or LLM control.
- A module already has a CLI but you want a programmatic Python entry
  point with regression-test guarantees.
- You want to expose a module as an MCP tool to LLM clients.

Do **not** use this skill for:
- Pure refactors with no library output (use a normal feature plan).
- Brand-new Fortran modules without an existing CLI baseline (you have
  no oracle to regress against).

## Three orthogonal phase tracks

```
Phase L (library-ization, REQUIRED)         Phase F (F90 modernize, OPTIONAL)
   L-0 baseline (regression dump)              F-1 COMMON -> MODULE w/ shim
   L-1 Makefile split                          F-2 LOW tier .f -> .f90
   L-2 C ABI foundation (stubs)                F-3 MED tier (INCLUDE shims)
   L-3 parameter registry                      F-4 HIGH tier (file I/O, drivers)
   L-4 shared library (.so)                    F-5 shim removal + grep-clean
   L-5 Python wrapper
   L-6 4-layer tests                       MCP track (after L-7)
   L-7 docs (README, examples, arch.md)        MCP-1 server.py + pyproject
                                               MCP-2 plot tool extensions
```

Phase F is **independent of Phase L** — they touch different files (F
edits the legacy COMMON includes, L only adds new files in the module
dir + a Makefile entry). They can run in parallel branches.

The MCP track requires L-5 (Python wrapper) to exist.

## Vocabulary used in this skill

Throughout this document, `<MODULE>` (lowercase) is the new module name
(`tr`, `fp`, `ti`, `wr`, `wrx`, `eq`, ...). `<MOD>` is uppercase
(`TR`, `FP`, ...). `<X>` is shorthand for either when context makes
the case obvious.

## Checklist (top-level)

You MUST complete each block in order, with a merged PR per phase
before starting the next:

1. **Pre-flight** — Read the design doc, identify baseline cases, draft
   the Phase L-0 spec.
2. **L-0 baseline** — env-guarded dump module + 2+ baseline fixtures
   under `test_run/baselines/<MODULE>_<case>/` with deterministic SHA.
3. **L-1 Makefile split** — `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU`
   with byte-identical original binary.
4. **L-2 C ABI foundation** — `<MODULE>_state.f90`,
   `<MODULE>_param_registry.f90` (shell), `<MODULE>_api.f90` (5
   BIND(C) functions returning `4 = NOT_IMPL`), `<MODULE>_api.h`,
   `<module>_api_check` smoke test.
5. **L-3 parameter registry** — populate the SELECT CASE table,
   wire `<module>_init` / `<module>_run(mode=1)` /
   `<module>_get_state` to the real Fortran kernel.
6. **L-4 shared library** — `obj/pic/` PIC build, in-tree bpsd PIC
   rebuild, graphics stubs, `lib<module>api.so`, dlopen smoke.
7. **L-5 Python wrapper** — `python/<module>lib/` (ctypes `_ffi.py`,
   high-level `<module>lib.py`, `state.py` dataclass, `errors.py`).
8. **L-6 4-layer tests** — equivalence (vs L-0), C ABI negative,
   Python wrapper reinforcement, sweep/NaN guards.
9. **L-7 docs** — `python/<module>lib/README.md`, examples/,
   `docs/<module>-library/architecture.md`, `CHANGELOG`.
10. **(optional) Phase F-1..F-5** — modernize fixed-form `.f` files
    that the new library will load; can run in parallel with L.
11. **(optional) MCP server** — `python/mcp-servers/<module>_mcp/`
    with FastMCP, 9 standard tools, beginner Japanese README.

Each phase below has: Goal / Prereqs / Files / Verify / Pitfalls /
Reference PR. See `references/completed-modules.md` for the full PR
matrix per module.

---

## Pre-flight: choose baseline cases

Before writing any code, pick 2-3 representative input fixtures
("baseline cases") that the new library will reproduce bit-safe to
1e-10. Use the existing CLI (`<module>/<module>` binary or
`task <subcommand>`) to confirm they run cleanly in non-interactive
mode (`MODE=1` / file-based input, `NPRINT=0`).

Pattern (from completed modules):

| Module | Cases (test_run/baselines/) | Notes |
|--------|------------------------------|-------|
| tr     | tr_iter01, tr_tst2, tr_m0904 | 3 cases, ITER-class + short CI |
| fp     | fp_iter01, fp_dt1, fp_jt60   | 3 cases |
| ti     | ti_*                         | 2-3 cases |
| wr     | wr_iter_lhcd, wr_test001, wr_tst2_ec | 3 cases |
| wrx    | wrx_iter01, wrx_jt60, wrx_demo | 3 cases |
| eq     | eq_iter01, eq_tst2           | 2 cases (EQDSK-dep deferred) |

Pick at least one **realistic** (e.g. ITER) and one **fast** (CI <30 s).

---

## Phase L-0: baseline (env-guarded Fortran dump)

**Goal:** Establish numerical ground truth that every later phase will
preserve. Define the "if `<module>` regresses by 1 ULP on these cases,
fail" guarantee.

**Prerequisites:** none — this is the first phase.

**Files created:**

```
<module>/<module>regress.f90        (or .f if module is fixed-form)
<module>/Makefile                   (modified — add <module>regress to SRCS)
<module>/<module>main.f             (modified — call dumper after solve)
test_run/baselines/<module>_<caseA>/{metrics.json, <case>.in}
test_run/baselines/<module>_<caseB>/{metrics.json, <case>.in}
test_run/scripts/extract_<module>_metrics.py
test_run/scripts/compare_metrics.py    (modified — add --dim <module>)
test_run/scripts/check_regression.sh   (modified — add <module>_*) case branch)
```

The dump module is **env-guarded**: it runs only when
`<MOD>_REGRESS_DUMP=1` (or `<MOD>_REGRESS=1`, follow per-module
convention). Normal interactive runs are completely unaffected.

See `templates/Xregress.f90.template` for the canonical structure.

**Verification:**

```bash
# 1. Build with the dump module
make -C <module> clean && make -C <module>

# 2. Run a baseline case 3 times; SHA-256 must match all three runs
cd test_run/baselines/<module>_<caseA>
for i in 1 2 3; do
  <MOD>_REGRESS_DUMP=1 ../../../<module>/<module> < <case>.in > /dev/null
  sha256sum <module>_regress.dat
done

# 3. extract -> compare against checked-in metrics.json
python3 ../../scripts/extract_<module>_metrics.py <module>_regress.dat > new.json
python3 ../../scripts/compare_metrics.py --dim <module> --tol 1e-10 \
  ../../baselines/<module>_<caseA>/metrics.json new.json

# 4. Full regression sweep
test_run/scripts/check_regression.sh <module>_<caseA> <module>_<caseB>
```

**Pitfalls:**
- Dump format must use `1PE24.16` (16-digit signed exponent). Lower
  precision will spuriously fail the 1e-10 tolerance.
- Use `STATUS='REPLACE'` on OPEN — repeated runs in the same dir must
  overwrite, not append.
- For modules with stochastic loops (Monte Carlo), seed the RNG
  explicitly in the baseline `.in` file.
- 2D arrays larger than ~1 MB: dump SHA-256 of the raw bytes only,
  not the full array.

**Reference PRs:**
- TR: PR #15 (wr was first), tr was unmerged seed pattern
- FP: PR #13
- TI: PR #12
- WR: PR #15
- WRX: PR #16
- EQ: PR #54

---

## Phase L-1: Makefile graphics split

**Goal:** Separate the module's source list into `SRCS_CORE` (numerics
only, no graphics or menu loop), `SRCS_GRAPHICS` (GSAF / X11 calls),
and `SRCS_MENU` (interactive prompts). Original CLI binary must be
**byte-identical** before vs after this PR.

**Prerequisites:** L-0 merged.

**Files modified:**

```
<module>/Makefile        (add SRCS_CORE / SRCS_GRAPHICS / SRCS_MENU)
```

Pattern:

```make
SRCS_CORE     = <module>init.f <module>loop.f90 <module>calc.f90 ...
SRCS_GRAPHICS = <module>fout.f90 <module>grfp.f90 ...
SRCS_MENU     = <module>menu.f <module>parm.f
SRCS          = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU) <module>main.f
```

This split is purely categorical at L-1 — the CLI binary still links
all three groups. The split unlocks L-4 where `lib<module>api.so` will
link only `SRCS_CORE` + graphics stubs.

**Verification:**

```bash
# Byte-identical original binary before/after
make -C <module> clean && make -C <module>
sha256sum <module>/<module>          # capture pre-PR

git checkout <pr-branch>
make -C <module> clean && make -C <module>
sha256sum <module>/<module>          # MUST equal pre-PR
```

**Pitfalls:**
- Don't reorder source files within `SRCS_CORE` — Fortran module
  dependency order matters; reordering can break the build.
- If a file straddles core+graphics, leave it in `SRCS_CORE` and
  stub the graphics symbol in L-4 instead of splitting the file.

**Reference PRs:**
- TR: #21
- FP: #26
- TI: #22
- WR: #24
- WRX: #25
- EQ: #65

---

## Phase L-2: C ABI foundation (stubs)

**Goal:** Define the public C ABI (5 functions + state struct + 5 error
codes), build the foundation Fortran files, and add a `_api_check`
smoke test that verifies all 5 symbols return `NOT_IMPL` (=4). No real
numerics yet — that lands in L-3.

**Prerequisites:** L-1 merged.

**Files created:**

```
<module>/<module>_state.f90              -- BIND(C) struct, layout-mirror of <X>_api.h
<module>/<module>_param_registry.f90     -- SHELL only (returns INVALID for now)
<module>/<module>_api.f90                -- 5 BIND(C) functions, all stubs
<module>/<module>_api.h                  -- C header with state struct + 5 prototypes
<module>/Makefile                        -- modified, add <module>_api_check target
<module>/<module>_api_check.c            -- tiny C driver that calls all 5 + asserts NOT_IMPL
```

**Five C ABI functions (mandatory contract):**

```c
int <module>_init(void);
int <module>_run(int n);
int <module>_set_param(const char *name, double value);
int <module>_set_param_str(const char *name, const char *value);
int <module>_get_state(<module>_state_t *state);
int <module>_finalize(void);
```

**Five error codes (mandatory contract):**

```c
enum <module>_error {
    <MOD>_OK              = 0,
    <MOD>_ERR_INVALID     = 1,  /* invalid name or value */
    <MOD>_ERR_NOT_INIT    = 2,  /* init() not called yet */
    <MOD>_ERR_CALC_FAILED = 3,  /* calc/init failed      */
    <MOD>_ERR_NOT_IMPL    = 4   /* L-2 stub return       */
};
```

**Name collision pattern (CRITICAL).** Most TASK modules already have a
SUBROUTINE `<module>_init` in `<module>init.f` — colliding with our new
public symbol. Resolve via USE-rename + `BIND(C, NAME=...)`:

```fortran
USE <module>init, ONLY: <module>init_fortran => <module>_init
...
FUNCTION <module>_api_init() RESULT(ierr) BIND(C, NAME="<module>_init")
   ...
   CALL <module>init_fortran        ! invokes the legacy SUBROUTINE
END FUNCTION
```

See `templates/X_api.f90.template` for the full pattern.

**Verification:**

```bash
make -C <module> <module>_api_check
./<module>/<module>_api_check        # all 5 symbols print "ierr=4 (NOT_IMPL)"
```

**Pitfalls:**
- The `<module>_state_t` C struct and `<module>_state_c` Fortran TYPE
  MUST have identical field order, types, and sizes. C arrays are
  row-major, Fortran is column-major; declare matching arrays as
  `RN(NSMAX, NRMAX)` in Fortran and `RN[NRMAX][NSMAX]` in C — the
  byte layout matches.
- Use `INTEGER(C_INT)` and `REAL(C_DOUBLE)` for everything.
  `INTEGER(C_LONG)` portability is poor.
- `<module>_api_check` must be a non-test target so `make` users don't
  pull in C++ test deps; just plain `gcc <module>_api_check.c -L. -l<module>api`.

**Reference PRs:**
- TR: #27
- FP: #29
- TI: #28
- WR: #30
- WRX: #31
- EQ: #70

---

## Phase L-3: parameter registry + real C ABI wiring

**Goal:** Replace the `NOT_IMPL` stubs with real bodies. Build the
SELECT CASE dispatch table that maps namelist parameter names to TRCOMM
(or equivalent) variables. Make `init()` allocate, `set_param()` set,
`run(n)` step, `get_state()` populate.

**Prerequisites:** L-2 merged.

**Files modified:**

```
<module>/<module>_param_registry.f90    -- 40-60 entry SELECT CASE
<module>/<module>_api.f90               -- bodies replace stubs
<module>/Makefile                       -- (no change usually)
```

**Registry checklist:**

- Identify the namelist groups in `<module>parm.f` / `<module>init.f`.
- Add SELECT CASE entries grouped by physics category (geometry,
  plasma scalars, time evolution, transport switches, model switches,
  heating/CD).
- For arrays (e.g. `PA(1:NSMAX)`), accept `"PA[1]"` syntax via
  `parse_array_subscript(name, base, idx)`. **Default `idx = -1`**
  to reject bare names like `"PA"` instead of silently writing `PA(1)`
  or `PA(0)`.
- Strings (KNAMEQ, MODELN, etc.) get a separate entry point:
  `<module>_param_set_str("KNAMEQ", "eqdata.ITER01")`.
- Keep the registry itself decoupled from the C ABI — `<module>_api.f90`
  calls `<module>_param_set` after C-string conversion.

See `templates/X_param_registry.f90.template`.

**Verification:**

```bash
# Build
make -C <module>

# Smoke
./<module>/<module>_api_check         # now returns 0 instead of 4

# (Best effort) call init -> set_param("RR", 6.2) -> run(10) -> get_state
# from a tiny C harness; check QP[0] differs from default.
```

**Pitfalls:**
- **Default idx = -1 sentinel.** Without it, `set_param("PA", 0.0)`
  silently writes `PA(0)` or whatever array(0) is — undefined behavior.
  Bugbot will catch this; reject bare-name array writes explicitly.
- `INT(value)` for INTEGER namelist vars — but reject if `value` is not
  representable (e.g. NaN, > INT_MAX).
- After `<MOD>_init` you usually need a `<MOD>_prep` (ALLOCATE) step.
  Track the lifecycle with two flags: `g_initialized` and `g_prepared`.
- `<module>_run(n)` should restore the original `NTMAX` after the loop
  so successive `run()` calls don't accumulate side-effects.

**Reference PRs:**
- TR: #33
- FP: #37
- TI: #34
- WR: #36
- WRX: #38
- EQ: #78

---

## Phase L-4: shared library build

**Goal:** Produce `<module>/lib<module>api.so` linking the PIC variants
of all module dependencies, with graphics symbols stubbed. Verify with
a `dlopen()` smoke test.

**Prerequisites:** L-3 merged.

**Files created/modified:**

```
<module>/Makefile                       -- new lib<module>api.so target
<module>/obj/pic/                       -- separate PIC build tree
<module>/mod_pic/                       -- separate PIC mod tree
<module>/<module>_graphics_stubs.f90    -- no-op subroutines for GSAF symbols
<module>/<module>_api_check_so.c        -- dlopen smoke test
bpsd/Makefile                           -- add libbpsd_pic.a target (in-tree rebuild)
```

**Build pattern:**

```make
PIC_OBJ_DIR = obj/pic
PIC_MOD_DIR = mod_pic
PIC_FFLAGS  = $(FFLAGS) -fPIC -J$(PIC_MOD_DIR)

$(PIC_OBJ_DIR)/%.o: %.f90 | $(PIC_OBJ_DIR) $(PIC_MOD_DIR)
	$(FC) $(PIC_FFLAGS) -c $< -o $@

lib<module>api.so: $(PIC_CORE_OBJS) $(PIC_STUBS_OBJS) $(PIC_DEPS)
	$(FC) -shared -o $@ \
	      -Wl,--start-group \
	      $(PIC_CORE_OBJS) $(PIC_STUBS_OBJS) \
	      ../lib/libplfile_pic.a ../pl/libplcomm_pic.a \
	      ../eq/libeq_pic.a ../bpsd/libbpsd_pic.a ... \
	      -Wl,--end-group \
	      -Wl,--unresolved-symbols=ignore-in-shared-libs \
	      $(LDFLAGS)
```

**Three loader-level tricks (all required):**

1. `-Wl,--start-group ... --end-group` — the linker re-scans archives
   inside the group, resolving the cross-archive cycles common in
   TASK's PIC tree.
2. `-Wl,--unresolved-symbols=ignore-in-shared-libs` — graphics-only
   symbols (GSAF: `viewgtlist_`, etc.) are reachable only from code
   paths the C ABI never invokes. The linker would otherwise refuse
   to produce the `.so`.
3. Python wrapper opens with `RTLD_LAZY` (mode=1) so any residual
   undefined symbol is resolved at first use, not at `dlopen`. Since
   the C ABI never calls those symbols, lazy binding is safe.

**Verification:**

```bash
make -C <module> lib<module>api.so
make -C <module> <module>_api_check_so
./<module>/<module>_api_check_so          # exits 0; loads the .so via dlopen

# Inspect: should show 6 exported symbols (init/run/set_param/set_param_str/get_state/finalize)
nm -D --defined-only <module>/lib<module>api.so | grep ' T <module>_'
```

**Pitfalls:**
- bpsd's vendored `Makefile` doesn't build a PIC archive by default.
  Add a `libbpsd_pic.a` target that compiles `*.f90` with `-fPIC` into
  `obj/pic/` and `ar`s them. **Do not** install the PIC artefacts into
  the standard `obj/` tree; you'll break the non-PIC `tr2` build.
- mod files: each PIC build needs `-J<dir>` pointing at `mod_pic/`,
  separate from the non-PIC `mod/` dir. Otherwise mod files clobber.
- For modules with `libgrf::grd1d` or similar **module procedures**
  reachable from `<module>_run` (not just file I/O), you cannot
  link-time stub them — see the **wrx-specific** note: gate
  `<module>.run()` behind a runtime env var (`WRX_RUN_OK=1`) and
  document the limitation in L-7.

**Reference PRs:**
- TR: #35
- FP: #43
- TI: #41 (initial), #66 (retroactive fix)
- WR: #42
- WRX: #52
- EQ: (in flight on `feature/eq-library-L4-shared-lib`)

---

## Phase L-5: Python wrapper (ctypes + dataclass)

**Goal:** Idiomatic Python interface over `lib<module>api.so`. Three
files: low-level `_ffi.py` (ctypes), `state.py` (dataclass mirror of
`<module>_state_t`), and `<module>lib.py` (high-level class with
context manager and structured exceptions).

**Prerequisites:** L-4 merged.

**Files created:**

```
python/<module>lib/__init__.py
python/<module>lib/_ffi.py            -- ctypes bindings, RTLD_LAZY dlopen
python/<module>lib/<module>lib.py     -- high-level class
python/<module>lib/state.py           -- @dataclass <Module>State, to_dict()
python/<module>lib/errors.py          -- exception hierarchy
python/<module>lib/__init__.py        -- re-exports
```

**Library path lookup (mandatory order):**

```
1. explicit `path` argument to load_library()
2. <MOD>LIB_PATH environment variable
3. <repo>/<module>/lib<module>api.so   (L-4 build location)
4. <repo>/lib/lib<module>api.so        (future install location)
```

**Exception hierarchy (mandatory):**

```python
class <Module>libError(Exception): pass
class <Module>libInitError(<Module>libError): pass        # rc=2 NOT_INIT
class <Module>libParamError(<Module>libError): pass       # rc=1 INVALID
class <Module>libRunError(<Module>libError): pass         # rc=3 CALC_FAILED
class <Module>libStateError(<Module>libError): pass       # get_state failed
class <Module>libNotImplementedError(<Module>libError): pass  # rc=4
```

Plus a `raise_for_rc(rc, context)` helper.

**Context manager pattern:**

```python
with <Module>lib() as t:
    t.set_param("RR", 6.2)
    t.run(10)
    s = t.get_state()
    print(s.WPT)
# finalize() called automatically on exit
```

See `templates/_ffi.py.template`.

**Verification:**

```bash
cd python && python3 -c "
import <module>lib
with <module>lib.<Module>lib() as t:
    t.set_param('RR', 6.2); t.run(5)
    print(t.get_state().to_dict())
"
```

**Pitfalls:**
- `RTLD_LAZY = 1` on Linux. `getattr(ctypes, 'RTLD_LAZY', 1)` for
  cross-platform fallback.
- The repo root is `Path(__file__).resolve().parents[2]` from
  `python/<module>lib/_ffi.py`. Off-by-one if you forget the
  `python/` parent.
- `set_param_str` may be missing from older `.so` builds — attach it
  in `_apply_prototypes` inside a `try: ... except AttributeError: pass`
  block; raise on first use instead of import time.
- Don't make numpy a hard dep. Use `try: import numpy` and degrade
  to plain lists in `state.to_dict()`.

**Reference PRs:**
- TR: #44
- FP: #55
- TI: #47
- WR: #46
- WRX: #59
- EQ: (in flight)

---

## Phase L-6: 4-layer test suite

**Goal:** Lock in correctness with four independent test layers, each
catching a different failure mode.

**Prerequisites:** L-5 merged.

**Files created:**

```
python/<module>lib/tests/test_equivalence.py        -- L1: vs L-0 baselines
python/<module>lib/tests/test_<module>lib.py        -- L3: wrapper unit tests
python/<module>lib/tests/test_sweep.py              -- L4: 3x3 sweep + NaN/Inf guards
python/<module>lib/tests/fixtures/<module>_<case>_params.py   -- per case
<module>/<module>_api_check_all.c                   -- L2: negative C ABI tests
<module>/Makefile                                   -- <module>_api_check_all target
```

**The four layers:**

| Layer | What | Tolerance |
|-------|------|-----------|
| 1. Equivalence  | Python wrapper reproduces L-0 baseline `metrics.json` | 1e-10 |
| 2. C ABI        | C harness exercises bad inputs: NULL, unknown name, out-of-range idx, init-not-called | rc match |
| 3. Wrapper unit | Python `<Module>lib` smoke + reinforcement | shape/type |
| 4. Sweep        | 3x3 parameter grid (e.g. RR x BB), assert no NaN/Inf | finite |

**Fixtures pattern (Layer 1):**

```python
# fixtures/<module>_<case>_params.py
PARAMS = {"RR": 6.2, "RA": 2.0, "BB": 5.3, ...}        # via set_param
STR_PARAMS = {"KNAMEQ": "eqdata.ITER01"}               # via set_param_str
NTMAX = 10
UNREGISTERED_KEYS = ["MDLNF", "MDLUF"]                  # tracked, not yet wired
```

`UNREGISTERED_KEYS` is the bridge between L-3 (which may ship with a
partial registry) and L-6: list every namelist key the fixture
**would** pass if it were wired. Tests SKIP those, but the list is
visible in code review and tracked for follow-up PRs.

**Verification:**

```bash
cd python/<module>lib && pytest -v
make -C <module> <module>_api_check_all && ./<module>/<module>_api_check_all
```

**Pitfalls:**
- Layer 1 must call exactly the same params the baseline `.in` file
  uses, in the same order. Order matters when later params depend on
  array dims (e.g. set NSMAX before PA[1..NSMAX]).
- Sweep test: skip parameter combos that the registry rejects
  (`<MOD>_ERR_INVALID`); don't fail.
- For wrx, gate `<module>.run()` behind `WRX_RUN_OK=1` env (the
  `libgrf::grd1d` link-time issue) and add a SKIP marker.

**Reference PRs:**
- TR: #53, #63 (registry extension follow-up)
- FP: #56
- TI: #57
- WR: #60
- WRX: #67
- EQ: (in flight)

---

## Phase L-7: documentation

**Goal:** Make the library usable by someone who doesn't know the
codebase. Beginner-friendly Japanese (です・ます調) README, a runnable
quickstart, an architecture diagram.

**Prerequisites:** L-6 merged.

**Files created:**

```
python/<module>lib/README.md                  -- Japanese, beginner-friendly
python/<module>lib/examples/quickstart.py     -- 30 LoC, prints state
python/<module>lib/examples/parameter_sweep.py -- 50 LoC, 3x3 sweep
python/<module>lib/examples/state_dump.py     -- supports --dry-run
docs/<module>-library/architecture.md         -- diagram + layering table
CHANGELOG.md (root)                           -- entry under "Unreleased"
```

**Examples must support `--dry-run`** so the docs CI can run them
without needing the `.so` built. Checking `if "--dry-run" in sys.argv:`
and exiting 0 before the dlopen suffices.

**Verification:**

```bash
# README renders cleanly
python3 -m markdown python/<module>lib/README.md > /dev/null

# Examples are syntactically valid
python3 -m py_compile python/<module>lib/examples/*.py

# Example runs with --dry-run
python3 python/<module>lib/examples/quickstart.py --dry-run
```

**Pitfalls:**
- Don't use emojis in checked-in docs unless the repo style uses
  them. TASK docs are emoji-free.
- The architecture.md "system diagram" is ASCII art — keep it under
  80 columns so it renders in PR diffs.
- Link the architecture doc from the module's `README.md`.

**Reference PRs:**
- TR: #62
- FP: #68
- TI: #64
- WR: #69
- WRX: (in flight)
- EQ: (in flight)

---

## Phase F (optional): F77 -> F90 modernization

Independent track. Touches `<module>com{0..N}.inc` and individual
`.f` source files. Can run in parallel with Phase L.

### F-1: COMMON -> MODULE migration with shim

**Goal:** Wrap each `<module>comN.inc` COMMON-block file in a Fortran
MODULE (`<module>comN_mod.f90`). Keep the `.inc` as a thin shim that
USEs the new module so legacy callers keep working.

**Files:**

```
<module>/<module>com0_mod.f90 .. <module>comN_mod.f90    -- new MODULEs
<module>/<module>com{c,m,q,x}.inc                        -- modified to USE the *_mod
<module>/<module>_commontest.f90                         -- bootstrap
<module>/Makefile                                        -- COMMON cmake target wires *_mod.o
```

**Shim policy:** The `.inc` files stay byte-compatible with their
historical COMMON declarations so untouched legacy callers compile
without edits. Each `.inc` becomes:

```fortran
! eqcomm.inc (shim)
USE eqcom0_mod
USE eqcom1_mod
! ... (re-export everything callers expect)
```

**Reference PR:** EQ F-1 = PR #71

### F-2: LOW tier .f -> .f90 conversion

**Goal:** Convert files with no COMMON dependencies (read-only or
isolated subroutines) from F77 fixed-form to F90 free-form. Pure
syntactic conversion; no logic changes.

**Pattern:**
- `*.f` -> `*.f90`
- `C` comments -> `!`
- Continuation cards (column 6) -> `&` line continuation
- Remove `INCLUDE 'eqcomm.inc'` if unused

**Reference PR:** EQ F-2 = PR #79

### F-3 / F-4: MED / HIGH tier conversion

Same idea, escalating risk:
- **F-3 MED:** Files using `INCLUDE` shims (still wrapped). Validate
  the include shim still resolves through `*_mod.f90`.
- **F-4 HIGH:** Critical-path files (`<module>main.f`, file I/O,
  calculation drivers). Run full L-0 regression after each commit.

### F-5: shim removal + grep-clean

**Goal:** Delete the `.inc` shims. Rewrite every `INCLUDE 'eqcomm.inc'`
as `USE eqcom0_mod, ONLY: ...` (or just `USE`). Grep must show zero
references to the old `.inc` files anywhere in the tree.

**Verification:** `grep -r 'eqcomm.inc' .` returns no hits;
`make -C <module>` succeeds; L-0 regression passes.

---

## MCP server track (after L-7)

### MCP-1: FastMCP server with 9 standard tools

**Goal:** Expose the L-7 Python wrapper as an MCP tool set so LLM
clients (Claude Desktop, etc.) can drive the module.

**Prerequisites:** L-7 merged.

**Files:**

```
python/mcp-servers/<module>_mcp/__init__.py
python/mcp-servers/<module>_mcp/server.py
python/mcp-servers/<module>_mcp/pyproject.toml
python/mcp-servers/<module>_mcp/README.md      -- Japanese, beginner
python/mcp-servers/<module>_mcp/tests/test_tools.py
```

**Nine standard tools (mandatory):**

```python
@mcp.tool()
def init() -> dict: ...
@mcp.tool()
def set_param(name: str, value: SupportedValue) -> dict: ...
@mcp.tool()
def set_params(params: dict[str, SupportedValue]) -> dict: ...
@mcp.tool()
def run(n_steps: int = 1) -> dict: ...
@mcp.tool()
def get_state() -> dict: ...
@mcp.tool()
def finalize() -> dict: ...
@mcp.tool()
def describe_parameters() -> dict: ...      # static metadata of registry
@mcp.tool()
def describe_state_schema() -> dict: ...    # static metadata of state struct
@mcp.tool()
def run_and_get_state(n_steps: int = 1) -> dict: ...   # convenience combo
```

**pyproject.toml — flat layout pattern (CRITICAL):**

```toml
# pyproject.toml lives INSIDE the package dir (flat layout). find_packages()
# fails — must declare explicitly.
[tool.setuptools]
packages = ["<module>_mcp"]

[tool.setuptools.package-dir]
"<module>_mcp" = "."
```

`[project.scripts]` exposes the console entry:

```toml
[project.scripts]
<module>-mcp = "<module>_mcp.server:main"
```

**Verification:**

```bash
cd python/mcp-servers/<module>_mcp
pip install -e .
python -m <module>_mcp.server         # starts FastMCP on stdio
pytest tests/
```

**Pitfalls:**
- Don't bundle MCP SDK in install_requires unless the env genuinely
  has it. `try: from mcp.server.fastmcp import FastMCP / except` lets
  the file pass `py_compile` without the SDK.
- Map `<Module>libError` subclasses to `ToolError` with a
  human-readable message; the LLM can usually recover (e.g. "you
  forgot to call init first").
- One library handle per process — `lib<module>api.so` holds Fortran
  COMMON-block singleton state. Re-`init()` should close & reopen.

**Reference PRs:**
- TR: #72 (reference impl)
- TI: #74
- FP: #77
- WR: #76
- WRX: #75
- EQ: (not yet)

### MCP-2 (later): plot tool extension

After a visualization layer (matplotlib) lands, extend the MCP server:

```python
@mcp.tool()
def plot(varname: str, format: str = "png") -> dict:
    """Returns {'base64_png': '...'}"""
@mcp.tool()
def plot_sweep(varname: str, sweep_param: str, values: list[float]) -> dict: ...
@mcp.tool()
def plot_available() -> list[str]:    # discoverable plot menu
```

The plot byte payload is base64 inside the JSON response so the LLM
can attach it to chat directly.

---

## Common patterns and anti-patterns

See `references/pitfalls.md` for the full list. Key points:

1. **Sandbox bash denial.** Some agents lose Bash mid-task. Use
   `isolation: "worktree"` and instruct the agent to write files only
   if Bash is needed; the parent rescues git operations.
2. **Cache stale PRs.** GitHub mergeability cache can flag CONFLICTING
   incorrectly. Recovery: clean branch off develop, copy files, push,
   new PR. Close the old PR.
3. **Bugbot policy.** Always wait for `Cursor Bugbot` check `COMPLETED`
   before merging. Never `--admin` bypass. After fix push, post
   `@cursor review` to retrigger.
4. **Conflict resolution.** When `Makefile` or `test_definitions.conf`
   conflicts, merge both sections (e.g. preserve `trlib_*` AND
   `tilib_*` AND `fplib_*` entries side-by-side).
5. **wrx-specific.** `wrcalpwr.f90` calls `libgrf::grd1d` (a module
   procedure) that can't be link-time stubbed; gate `wrx.run()` behind
   `WRX_RUN_OK=1` env and document.

---

## Per-module status snapshot

See `references/completed-modules.md` for the full PR matrix. As of
2026-04-18:

| Module | L-0 | L-1 | L-2 | L-3 | L-4 | L-5 | L-6 | L-7 | F | MCP |
|--------|-----|-----|-----|-----|-----|-----|-----|-----|---|-----|
| tr     | done | #21 | #27 | #33 | #35 | #44 | #53/#63 | #62 | n/a | #72 |
| ti     | #12 | #22 | #28 | #34 | #41/#66 | #47 | #57 | #64 | n/a | #74 |
| fp     | #13 | #26 | #29 | #37 | #43 | #55 | #56 | #68 | n/a | #77 |
| wr     | #15 | #24 | #30 | #36 | #42 | #46 | #60 | #69 | n/a | #76 |
| wrx    | #16 | #25 | #31 | #38 | #52 | #59 | #67 | inflight | n/a | #75 |
| eq     | #54 | #65 | #70 | #78 | inflight | inflight | inflight | inflight | F-1 #71 / F-2 #79 | not yet |

---

## After completing a phase

For each phase PR:

1. CI green (build + L-0 regression on the affected module).
2. `Cursor Bugbot` check `COMPLETED` (not pending). If review found
   issues, fix in the same branch, push, post `@cursor review` to
   retrigger.
3. Squash-merge into `develop`. Do NOT merge into `master`.
4. Delete the feature branch after merge.

## Pointers

- Skill files: `docs/superpowers/skills/module-library-ization/`
- Templates: `templates/X_state.f90.template`,
  `templates/X_api.f90.template`, `templates/X_api.h.template`,
  `templates/X_param_registry.f90.template`,
  `templates/_ffi.py.template`
- References: `references/completed-modules.md`,
  `references/error-codes.md`, `references/pitfalls.md`
- Design doc: `docs/superpowers/specs/2026-04-17-tr-library-design.md`
  (reference for the very first module; later modules followed it)
- User manual (LaTeX/PDF): `docs/manual/task-library-manual.{tex,pdf}`
