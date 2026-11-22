# TR scenarios through the library: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ITER01 under `MODELG=9`, with its three stages, runs through `trlib`, `totlib` and `tr_mcp` and gives the
product `tr2`'s numbers; its fusion power and power balance are readable; EQ failures and NaN inside the loop come
back as errors instead of ending the process or going unseen.

**Spec:** task-web-client `docs/superpowers/specs/2026-10-29-tr-scenarios-through-library-design.md` (#96, issue #95),
"the spec" below. The author chose this route on 2026-11-16: the spec as written, its four decisions on the
recommended options (an explicit `tr_continue`; scalars by name; `eq:` names in `tr_set_param`; stop on EQ failure
and NaN in library mode only). K. Yoshimi reviews the pull requests themselves; no interface confirmation is asked
before them.

**Architecture:** the work lands as three fork pull requests in the spec's order:

1. errors and P1;
2. outputs by name;
3. run control.

Each PR is on its own branch, stacked on the one before. `tr2`'s output stays bit-for-bit what it is today. Every
change of the time loop is gated on a library-mode flag that only `tr_init` sets, and the one formula change
(`DIPDT`) is the same number in `tr2`.

**Tech stack:** Fortran 2008 (gfortran 15 on macOS, 13 on CI), the C ABI in `tr/tr_api.h` and `tot/tot_api.h`, Python
ctypes wrappers (`python/trlib`, `python/totlib`), the FastMCP server `python/mcp-servers/tr_mcp`, pytest with
`--forked`.

---

## Where this differs from the spec's section 6, and why

- **Base: the product line, not the upstream merge-base.**
  - `MODELG=9` as `tr2` runs it today exists only on `kyoshimi-develop`. The TR–EQ q-solver coupling of
    `fa9dd493` (group B) is in upstream PR #226, which has been open since 2026-07-12. So are the product's
    `tr/trloop.f90` and `tr/trmetric.f90` (`git diff 98a40d11 origin/kyoshimi-develop -- tr/trloop.f90 tr/trmetric.f90`).
  - The acceptance numbers (RESULTS §5) come from that code.
  - All three branches therefore start from `origin/kyoshimi-develop` (`dee378ce`) and carry the label
    `product-only`, with one row in `docs/product-line/upstream-status.md` (fork `AGENTS.md` rule 4).
  - Their upstream pull requests are a re-cut after #226 merges. That is the TASK merge session's and the author's
    call; this plan does not open them.
- **Two commits of #226's head are taken first.**
  - These are #228 findings 3 and 4:
    - `0dd157d4` (MODELG=9 adopts the equilibrium in every preparation);
    - `6a804077` (a failed q-scaling fails the run; `eq_calc` gains its optional `IERR`).
  - They are cherry-picked with `-x` onto the branch of PR 1 as `39bb9728` and `4f500ea1`. The CHANGELOG conflicts
    were resolved to the product's file, as #226's own `d8b6e4de` holds those entries back.
  - They do part of the spec's section 4. Without finding 3, any second preparation in one lifecycle under
    `MODELG=9` gives a wrong state, and the run-control tests prepare more than once.
- **Registry names go to plato-cpc's branch too.**
  - The plato-cpc session adds TR registry names on `feat/tr-registry-plato`, which is product-only from
    `dee378ce`.
  - Task 1's names commit is handed to it as a `git format-patch` file in the shared notes folder, after its A+B
    commit (`plato-registry-names.md` there).
  - Whichever of the two PRs merges second rebases and drops the duplicate.
- **One addition the spec lacks: TR's radial mesh `NRMAX` in the registry.** The task's numerical checks need it
  (mesh convergence of TR).

## Conventions for every task

- **Clone:** `~/task-web-scratch/iter-heating/lib/task`, with pinned bpsd beside it as `../bpsd` (`fb8414fe`). Remotes:
  `origin` is the fork, `upstream` is `k-yoshimi/task`.
- **Branches:**
  - PR 1: `feat/tr-library-errors`, from `origin/kyoshimi-develop`;
  - PR 2: `feat/tr-library-outputs`, from PR 1's head;
  - PR 3: `feat/tr-library-continue`, from PR 2's head.
- **Build** (macOS; the conda env's `AR` is a missing cross `ar`, so it is overridden):
  ```bash
  cd ~/task-web-scratch/iter-heating/lib
  export PATH=/opt/homebrew/bin:/usr/bin:/bin FC=/opt/homebrew/bin/gfortran AR=/usr/bin/ar RANLIB=/usr/bin/ranlib
  /Users/lihengyu/Research_Project/MS10/TASK/task-web/.claude/worktrees/iter-heating-workflow-d71f07/scripts/build_fortran.sh "$PWD/task" "$PWD/bpsd"
  # after an edit: one module (GNU make 3.81 compares whole seconds: sleep 1.2; touch <src>; sleep 1.2 first)
  make -C task/tr libtrapi.so      # TR
  make -C task/eq libeqapi.so      # EQ
  make -C task/tot libtotapi.so libtotapi_mono.so   # TOT and mono (they embed TR and EQ: rebuild after TR/EQ edits)
  make -C task/tr libs && make -C task/tr tr2       # the product tr2 (non-PIC objects)
  ```
- **Tests**, from the clone root in conda env `task`:
  ```bash
  PYTHONPATH=python:python/mcp-servers python -m pytest python/ --forked --timeout=120 --timeout-method=signal -q
  ```
  - Record the baseline once before Task 1 (`pass/skip/xfail` counts).
  - Set `MONO_LIB_PATH` and `TOTLIB_PATH` to the clone's `tot/libtotapi_mono.so` and `tot/libtotapi.so` for the full
    suite.
- **Tests are written to fail first.** "Before the change" means the new test files copied into a build at the
  branch's base, run, and deleted.
- **Forked tests:**
  - No `subTest`: one test per case.
  - A case that can hang or `STOP` inside Fortran runs in `subprocess.run([...], timeout=...)`, not in the forked
    child.
  - Check `ps` for orphans after a hang.
- **Never** `pkill`/`killall`; kill by explicit PID. Every model entry point in a test is stubbed; these tests call
  only the Fortran libraries and `tr2`.
- **Commits:**
  - Commit by pathspec.
  - Message bodies say what was measured.
  - End with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - No `git stash`.
- **The pre-push gate**, per PR:
  - local pytest with the CI flags;
  - a code review (`superpowers:code-reviewer` agent);
  - a Codex review (`codex exec -m gpt-6-astra -s read-only -C <clone> ... < /dev/null`);
  - HIGH and MED findings fixed or answered;
  - then `touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"`.
  - Every amend needs a new marker and a new review.
  - Install the hook once from a `kyoshimi-develop` worktree (`scripts/install-hooks.sh`).
- **Line citations** in comments and docs: run `follow_lines` once per base after edits (the fork-workflow notes).
  Append new routines at the END of a module.

## File map

| File | PR | Change |
|---|---|---|
| `tr/tr_param_registry.f90` | 1, 3 | NTEQIT, TPRST, NRMAX cases and `value_refused` entries (1); control list, structural counter, `tr_param_class` (3) |
| `tr/trfailure.f90` (new) | 1 | library-mode flag and the last-failure record |
| `tr/Makefile`, `tot/Makefile` | 1, 3 | `trfailure.o`; `eq_param_registry.o` in `libtrapi.so` (1) |
| `tr/tr_api.f90`, `tr/tr_api.h` | 1, 2, 3 | `eq:` routing, `tr_last_error` (1); scalar table (2); `tr_continue`, `tr_param_class` (3) |
| `tr/trloop.f90` | 1, 3 | failures returned in library mode (1); `DIPDT` over this call (3) |
| `tr/trmetric.f90` | 1 | the q-scaling's failure recorded as `EQ_FAILED` |
| `eq/eqcalq.f90` | 1 | `zminmax` at the edge of `YA` sets `IERR` |
| `tot/tot_api.f90`, `tot/tot_api.h` | 2, 3 | `tot_get_scalar` (2), `tot_continue` (3) |
| `python/trlib/{_ffi,trlib,errors,state}.py` | 1, 2, 3 | `.failure`, `scalars`/`get_scalar`, `continue_run`/`param_class` |
| `python/totlib/{_ffi,totlib}.py` | 2, 3 | `get_scalar`, `continue_run` |
| `python/mcp-servers/tr_mcp/server.py` | 1, 2, 3 | names and `eq:` passthrough, failure record (1); scalars in the state and schema (2); `continue_run` tool, class in `describe_parameters` (3) |
| `test_run/{test_definitions.conf,run_tests.sh,inputs,baselines}` | 3 | equivalence case `tr_iter01_m9` |
| `python/trlib/tests/test_*` (new files per task) | 1, 2, 3 | below |
| `README`s, `docs/sphinx` (en, ja), `CHANGELOG.md`, `docs/product-line/upstream-status.md` | 1, 2, 3 | per PR |

---

### Task 1: NTEQIT, TPRST, NRMAX in the registry; `eq:` names through `tr_set_param` (PR 1)

**Files:**
- Modify: `tr/tr_param_registry.f90` (CASEs near `MDLST` and `NTSTEP`; `value_refused`'s integer list)
- Modify: `tr/tr_api.f90` (`tr_api_set_param`, `tr_api_set_param_str`: `eq:` prefix)
- Modify: `tr/Makefile` (link `../eq/<pic objdir>/eq_param_registry.o` into `libtrapi.so` only; mono must not get it
  twice)
- Modify: `python/mcp-servers/tr_mcp/server.py` (declarations; `eq:` names passed through)
- Modify: `python/trlib/README.md` (registry table)
- Test: `python/trlib/tests/test_registry_modelg9_names.py` (new)

The names commit (registry, server, README and the NTEQIT/TPRST/NRMAX tests) is its own commit, so that it can be
handed to plato-cpc. `eq:` is a second commit.

- [ ] **Step 1: Write the failing tests**

```python
"""NTEQIT, TPRST and TR's NRMAX through the registry; eq: names through tr_set_param."""
import math
import pytest
from trlib import Trlib, TrlibParamError

pytestmark = pytest.mark.forked

def _lib():
    return Trlib()

def test_nteqit_is_settable():
    with _lib() as t:
        t.set_param("NTEQIT", 50)

def test_nteqit_negative_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("NTEQIT", -1)

def test_tprst_is_settable():
    with _lib() as t:
        t.set_param("TPRST", 0.5)

def test_tprst_zero_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("TPRST", 0.0)

def test_nrmax_set_before_the_first_run_gives_that_mesh():
    with _lib() as t:
        t.set_param("NRMAX", 30)
        t.run(1)
        assert t.get_state().nrmax == 30

def test_nrmax_above_the_state_bound_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("NRMAX", 501)   # TR_MAX_NRMAX = 500 (tr/tr_api.h)

def test_nrmax_below_the_minimum_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("NRMAX", NRMAX_MIN - 1)   # NRMAX_MIN: measured in Step 3, written here as a literal

def test_eq_rb_is_settable_through_tr():
    with _lib() as t:
        t.set_param("eq:RB", 2.1)
        t.set_param("eq:NSGMAX", 128)

def test_unknown_eq_name_is_refused():
    with _lib() as t, pytest.raises(TrlibParamError):
        t.set_param("eq:NOSUCHNAME", 1.0)

def test_an_eq_set_prepares_tr_again():
    # MODELG=3 tr_tst2-like defaults; the point is the restart, not the physics
    with _lib() as t:
        t.run(2)
        nt_before = t.get_state().nt
        t.set_param("eq:RB", 2.1)
        t.run(1)
        assert t.get_state().nt == 1 and nt_before == 2
```

Also add `NTEQIT` and `NRMAX` to the integer list that `python/trlib/tests/test_param_values.py` holds to
`value_refused`. That test reads the CASEs from the source; it fails until Step 4.

- [ ] **Step 2: Run them to see them fail**

Run: `PYTHONPATH=python:python/mcp-servers python -m pytest python/trlib/tests/test_registry_modelg9_names.py python/trlib/tests/test_param_values.py --forked -q`

Expected: the NTEQIT/TPRST/NRMAX/eq: cases FAIL with `TrlibParamError` (unknown name).

- [ ] **Step 3: Measure NRMAX's minimum and write it into the test**

- Set NRMAX = 2 … 10 on the `tr_init` defaults, each in a process of its own (`subprocess.run(..., timeout=60)`):
  `t.set_param("NRMAX", n); t.run(5)`.
- The minimum is the smallest n for which every larger n up to 10 runs and gives a finite `WPT` and `Q0`.
- Write the measured numbers into the commit body, and the minimum into `NRMAX_MIN` in the test.
- Write it into `plato-registry-names.md` in the shared notes folder too: plato-cpc uses NRMAX for its mesh check.

- [ ] **Step 4: Implement the names**

In `tr_param_set_impl`, beside `NTSTEP` and `MDLST`:

```fortran
    CASE ("NTEQIT")
       IF (value < 0.0_rkind) THEN; ierr = 1; ELSE; NTEQIT = INT(value); END IF
    CASE ("TPRST")
       IF (.NOT. value > 0.0_rkind) THEN; ierr = 1; ELSE; TPRST = value; END IF
    CASE ("NRMAX")
       ! TR's radial mesh. ALLOCATE_TRCOMM re-allocates when it changes before a
       ! preparation (tr/trcomm.f90); the state carries at most TR_MAX_NRMAX
       ! surfaces (tr/tr_api.h).
       IF (value < REAL(NRMAX_MIN, rkind) .OR. value > REAL(TR_MAX_NRMAX, rkind)) THEN
          ierr = 1
       ELSE
          NRMAX = INT(value)
       END IF
```

- `NRMAX_MIN` is a named constant in the module, set to the Step 3 measurement; `TR_MAX_NRMAX` comes from
  `tr_state`.
- Add `NTEQIT`, `TPRST` and `NRMAX` to the module's `USE trcomm, ONLY:` list.
- Add `"NTEQIT"` and `"NRMAX"` to `value_refused`'s integer CASE.
- In `tr_mcp/server.py` the `NRMAX` group is `plasma`, beside `NSMAX`, as `tr_mcp` has no `mesh` group (agreed with
  plato-cpc to follow its branch's choice; if its branch adds `mesh`, use that):

```python
    "NTEQIT": {"type": "int",   "group": "time",    "description": "EQ re-solve interval in steps under MODELG=9 (0 = never)"},
    "TPRST":  {"type": "float", "group": "modules", "description": "sawtooth period [s]"},
    "NRMAX":  {"type": "int",   "group": "plasma",  "description": "TR radial mesh points"},
```

- [ ] **Step 5: Run the names tests; commit the names commit**

Run the two files from Step 2: the NTEQIT, TPRST and NRMAX cases and `test_param_values.py` PASS; the `eq:` cases
still FAIL.

```bash
git add tr/tr_param_registry.f90 python/mcp-servers/tr_mcp/server.py python/trlib/README.md \
        python/trlib/tests/test_param_values.py python/trlib/tests/test_registry_modelg9_names.py
git commit   # "feat(tr): NTEQIT, TPRST and TR's NRMAX in the registry" (the eq: tests are added in the next commit:
             # move them out of this file for this commit, back in the next)
```

- [ ] **Step 6: Hand the names commit to plato-cpc** (only after its A+B hash is in `plato-registry-names.md`)

```bash
git fetch ~/task-web-scratch/plato-nclass/task feat/tr-registry-plato:refs/remotes/plato/feat-tr-registry-plato   # read only
git worktree add --detach ../plato-apply plato/feat-tr-registry-plato
cd ../plato-apply && git cherry-pick <names commit>   # resolve against its CASE lists, build, run Step 2's names tests
git format-patch -1 -o "/Users/lihengyu/Library/Application Support/Claude/side-session-notes/local_2fe367ea-8a36-471f-95df-7448a0adea65"
```

Write the patch's file name into `plato-registry-names.md`; remove the worktree.

- [ ] **Step 7: Implement `eq:` routing**

In `tr_api_set_param`, after the C string is converted to `fname` and before the registry is called:

```fortran
    IF (LEN_TRIM(fname) > 3) THEN
       IF (fname(1:3) == 'eq:') THEN
          CALL eq_param_set(fname(4:LEN_TRIM(fname)), value, rc)
          IF (rc /= 0) THEN
             ierr = TR_ERR_INVALID
          ELSE
             CALL tr_param_note_external_set()   ! TR prepares again before its next run
             ierr = TR_OK
          END IF
          RETURN
       END IF
    END IF
```

- Do the same in `tr_api_set_param_str` with `eq_param_set_str`.
- `tr_param_note_external_set` is a new public routine at the end of `tr_param_registry` that advances
  `g_generation`.
- Link: add `eq_param_registry.o` (PIC) to `OBJ_LIBTRAPI`, following `tot/Makefile:91` and `:268-269`.
  - Check that `make -C tot libtotapi_mono.so` still links with no duplicate symbol. If it does not, mono takes TR's
    API objects without it.
  - Check: `nm -gU tr/libtrapi.so | grep eq_param_registry`.
- `tr_mcp`: a name that starts with `eq:` is passed to the library as is, with no local declaration check. The
  library refuses unknown names. `describe_parameters` gains one line that says so.

- [ ] **Step 8: Run the Task's tests and the TR suite; commit**

Run: `PYTHONPATH=python:python/mcp-servers python -m pytest python/trlib python/mcp-servers/tr_mcp python/totlib --forked --timeout=120 --timeout-method=signal -q`

Expected: everything that passed at the baseline passes, and the new tests pass.

Commit: `feat(tr): eq: names through tr_set_param, so MODELG=9 sets EQ's wall and grid`.

---

### Task 2: EQ: an extremum at the edge of the contour sets IERR (PR 1)

**Files:**
- Modify: `eq/eqcalq.f90` (the three `zminmax` call pairs in `EQCALQP` and `EQCALQV`)
- Test: `python/eqlib/tests/test_contour_extremum_edge.py` (new)

The spec's risk comes first: does an index at the edge (1 or the last point) occur on a healthy equilibrium?

- **The first caller** (`EQCALQP`, the traced field line). The extremes are searched from N = 2, with
  `NZMINR = NZMAXR = 1` before the loop. Index 1 is left only when no point is below (above) the axis: a degenerate
  contour.
- **The other two** (`EQCALQV`, the poloidal grid NTH = 1 … NTHMAX+1, θ = 2π(NTH−1)/NTHMAX). Index 1 and the last
  index are θ = 0, the outboard midplane, at the axis height. Before this task, `NZMINR`/`NZMAXR` are not reset
  there at all.

- [ ] **Step 1: Measure**
  - Add a temporary `WRITE(6,'(A,3I6)') 'ZMM ', NZMINR, NZMAXR, <last index>` before each `zminmax` pair.
  - Build EQ and TR, and run:
    - the EQ baselines `eq_iter01`, `eq_tst2` and the analytic default;
    - `tr2` on `~/task-web-scratch/iter-heating/ref-dee378ce/n50/tr.in` (with its `eqparm`), in the background,
      about 10 min at -O0.
  - Count the lines whose index is 1 or the last.
  - Expected: none on these healthy runs. If there are any, the guard uses the wrap-around neighbour (point
    NTHMAX on the closed grid) for that caller instead of failing, and the commit body says so.
  - Remove the WRITEs.

- [ ] **Step 2: Write the failing test**

```python
"""An equilibrium whose contour extremum sits at the edge of YA fails with IERR; the process lives."""
import subprocess, sys, textwrap
import pytest

CHILD = textwrap.dedent('''
    from trlib import Trlib, TrlibRunError
    t = Trlib()
    t.set_param("MODELG", 9); t.set_param("RIPS", 100.0); t.set_param("RIPE", 100.0)
    try:
        t.run(0)
        print("RC 0")
    except TrlibRunError as e:
        print("RC CALC_FAILED")
''')

def test_unsolvable_modelg9_fails_without_ending_the_process():
    p = subprocess.run([sys.executable, "-c", CHILD], capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC CALC_FAILED" in p.stdout
```

Also add one case per caller, built from the Step 1 measurement: an input whose index reaches the edge (for
`EQCALQP`, the RA = 2.0 default case named in `6a804077`'s message, which ended at the `zminmax` read in a checked
build), asserting `RC CALC_FAILED` and exit 0.

- [ ] **Step 3: Run it to see it fail**

On the base: the child ends at the run-time check (index 0 of `ya`), so `returncode != 0` and the test FAILS.

- [ ] **Step 4: Implement**

Before each pair, with `NLAST` the pair's last filled index (`NA` in `EQCALQP`, `NTHMAX+1` in `EQCALQV`):

```fortran
         IF(NZMINR.LE.1 .OR. NZMINR.GE.NLAST .OR. &
            NZMAXR.LE.1 .OR. NZMAXR.GE.NLAST) THEN
            WRITE(6,'(A,3I6)') 'XX EQCALQ: contour extremum at the edge: ', NZMINR, NZMAXR, NLAST
            IERR=110
            RETURN
         ENDIF
         call zminmax(YA,NZMINR,ZMIN,ZMINR)
         call zminmax(YA,NZMAXR,ZMAX,ZMAXR)
```

- In `EQCALQV`, set `NZMINR = 1` and `NZMAXR = 1` before each search loop (they were left from the previous
  surface).
- `110` must be unused by EQ: grep `IERR *= *1[0-9][0-9]` in `eq/` first and take a free number.
- Check that `EQCALQ` returns `EQCALQP`'s and `EQCALQV`'s `IERR`, and that `eq_calc(ierr)` passes it on (from
  `6a804077`).

- [ ] **Step 5: Run the EQ and TR suites and the EQ baselines; commit**

Expected:
- the new tests pass;
- `python/eqlib/tests/test_equivalence.py` and the TR equivalence tests unchanged (Linux-only ones skip on macOS);
- the `tr2` §5 run on `n50` gives the same 89 printed lines as `ref-dee378ce/n50/out.txt`
  (`python ~/task-web-scratch/iter-heating/ref-dee378ce/extract.py`).

Commit: `fix(eq): a contour extremum at the edge of YA fails EQCALQ, where it read outside the array`.

---

### Task 3: library mode, failures in the loop, `tr_last_error` (PR 1)

**Files:**
- Create: `tr/trfailure.f90`
- Modify: `tr/Makefile` (source lists of `tr2` and `libtrapi.so`, dependencies), `tot/Makefile` (mono)
- Modify: `tr/trloop.f90`, `tr/trmetric.f90`, `tr/trexec.f90` (only where `tr_exec` returns `TRCHCK`'s status: record
  `TR_CHECK`)
- Modify: `tr/tr_api.f90`, `tr/tr_api.h` (`tr_last_error`; flag set in `tr_init`; the record cleared at each
  `tr_run`)
- Modify: `python/trlib/_ffi.py`, `python/trlib/errors.py`, `python/trlib/trlib.py`,
  `python/mcp-servers/tr_mcp/server.py`
- Test: `python/trlib/tests/test_loop_failures.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
"""Library mode: an EQ failure or NaN inside the loop returns an error with a record; the process lives."""
import subprocess, sys, textwrap
import pytest

def _child(body):
    code = "from trlib import Trlib, TrlibRunError\n" + textwrap.dedent(body)
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=600)

ITER_M9 = '''
t = Trlib()
for k, v in dict(MODELG=9, RR=6.2, RA=2.0, RKAP=1.7, RDLT=0.33, BB=5.3, NSMAX=4, DT=0.02).items():
    t.set_param(k, v)
t.set_param("eq:RB", 2.1); t.set_param("eq:NSGMAX", 128)
'''

def test_modelg9_with_eq_defaults_fails_with_eq_failed():
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9)
        try:
            t.run(1); print("RC 0")
        except TrlibRunError as e:
            print("RC", e.failure.kind, e.failure.code, e.failure.nt)
    ''')
    assert p.returncode == 0, p.stderr[-2000:]
    assert "RC EQ_FAILED" in p.stdout

def test_flat_9ma_with_nteqit_50_stops_before_25_s():
    # spec section 4: NTEQIT=50, 9 MA flat -> AXIS NOT FOUND, state NaN from 20 s in tr2
    p = _child(ITER_M9 + '''
t.set_param("NTEQIT", 50); t.set_param("RIPS", 9.0); t.set_param("RIPE", 9.0)
try:
    t.run(1250); print("RC 0")       # 25 s at DT 0.02
except TrlibRunError as e:
    print("RC", e.failure.kind, e.failure.time)
''')
    assert p.returncode == 0, p.stderr[-2000:]
    kind, time = p.stdout.split("RC ")[1].split()
    assert kind in ("EQ_FAILED", "NONFINITE") and float(time) < 25.0

def test_last_error_is_cleared_by_a_good_run():
    p = _child('''
        t = Trlib()
        t.set_param("MODELG", 9)
        try: t.run(1)
        except TrlibRunError: pass
        t.set_param("MODELG", 2); t.run(2)
        print("KIND", t.last_error().kind)
    ''')
    assert "KIND NONE" in p.stdout
```

That `tr2` never sets library mode, and so prints what it printed, is checked in Step 5 by running it, not by a pytest.

Add one `tr_mcp` test: a `run` whose library call fails returns the record (`kind`, `code`, `nt`, `time`) in its
error payload.

- [ ] **Step 2: Run them to see them fail**

- On the branch after Task 2, the first test gets `CALC_FAILED` without a record: `AttributeError: failure`.
- The second runs to the end: `RC 0`.

- [ ] **Step 3: Implement `tr/trfailure.f90`**

```fortran
! trfailure.f90 -- library mode and the last failure of a TR run (libtrapi only sets the flag)
MODULE trfailure
  USE bpsd_kinds, ONLY: rkind
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_library_mode, tr_failure_clear, tr_failure_record, tr_failure_get
  PUBLIC :: TRF_NONE, TRF_EQ_FAILED, TRF_NONFINITE, TRF_TR_CHECK, TRF_PREP_FAILED, TRF_REFUSED, TRF_OTHER
  INTEGER, PARAMETER :: TRF_NONE = 0, TRF_EQ_FAILED = 1, TRF_NONFINITE = 2, TRF_TR_CHECK = 3, &
                        TRF_PREP_FAILED = 4, TRF_REFUSED = 5, TRF_OTHER = 6
  LOGICAL, SAVE :: tr_library_mode = .FALSE.      ! set by tr_init (tr_api.f90) only; tr2 never sets it
  INTEGER, SAVE :: g_kind = TRF_NONE, g_code = 0, g_nt = 0
  REAL(rkind), SAVE :: g_time = 0.0_rkind
  CHARACTER(LEN=96), SAVE :: g_detail = ''
CONTAINS
  SUBROUTINE tr_failure_clear()
    g_kind = TRF_NONE; g_code = 0; g_nt = 0; g_time = 0.0_rkind; g_detail = ''
  END SUBROUTINE tr_failure_clear
  ! The first failure of a run is kept: a later one is its consequence.
  SUBROUTINE tr_failure_record(kind, code, nt, time, detail)
    INTEGER, INTENT(IN) :: kind, code, nt
    REAL(rkind), INTENT(IN) :: time
    CHARACTER(LEN=*), INTENT(IN) :: detail
    IF (g_kind /= TRF_NONE) RETURN
    g_kind = kind; g_code = code; g_nt = nt; g_time = time; g_detail = detail
  END SUBROUTINE tr_failure_record
  SUBROUTINE tr_failure_get(kind, code, nt, time, detail)
    INTEGER, INTENT(OUT) :: kind, code, nt
    REAL(rkind), INTENT(OUT) :: time
    CHARACTER(LEN=*), INTENT(OUT) :: detail
    kind = g_kind; code = g_code; nt = g_nt; time = g_time; detail = g_detail
  END SUBROUTINE tr_failure_get
END MODULE trfailure
```

Add it to `SRCS_CORE` (it is used by `trloop`, `trmetric` and `trexec`) and to the dependency lines, so `tr2`, the
`.so` and mono all build it. `make -C tr tr2 libtrapi.so` and `make -C tot libtotapi_mono.so` must link.

- [ ] **Step 4: Implement the loop, the metric and the API**

`tr/trloop.f90`, the periodic re-solve:

```fortran
            IF(modelg.eq.9) THEN
               IF(tr_library_mode) THEN
                  call eq_calc(ierr)
                  IF(ierr.NE.0) THEN
                     CALL tr_failure_record(TRF_EQ_FAILED, ierr, NT, T, 'eq_calc in tr_loop (NTEQIT)')
                     GOTO 9000
                  ENDIF
               ELSE
                  call eq_calc          ! tr2: as before, the outcome is not tested
               ENDIF
```

After the step's `tr_eval(NT,IERR)` (library mode only), a finite check on `Q0`, `WPT` and the central temperature of
every species:

```fortran
      IF(tr_library_mode) THEN
         IF(.NOT.(ieee_is_finite(Q0) .AND. ieee_is_finite(WPT) .AND. &
                  ALL(ieee_is_finite(RT(1,1:NSMAX))))) THEN
            CALL tr_failure_record(TRF_NONFINITE, 0, NT, T, 'Q0, WPT or a central temperature')
            IERR=-3
            GOTO 9000
         ENDIF
      ENDIF
```

- Add `T`, `WPT`, `RT`, `NSMAX` to the `USE TRCOMM` list, and `USE trfailure` and
  `USE, INTRINSIC :: ieee_arithmetic, ONLY: ieee_is_finite`.
- `GOTO 9000` keeps the loop's end-of-call bookkeeping (`RIPS=RIPE`, the regression dump), as every existing failure
  path does.

`tr/trmetric.f90`: each `ierr /= 0` exit that `6a804077` added records
`TRF_EQ_FAILED, ierr, 0, T, 'tr_set_metric q-scaling, iteration <n>'` (the message it already writes).

`tr/trexec.f90`: where `TRCHCK` (negative temperature or density) sets `IERR`, record `TRF_TR_CHECK` with that code
(recording is harmless in `tr2`: nothing reads it there).

`tr/tr_api.f90`:
- `tr_api_init` sets `tr_library_mode = .TRUE.`;
- `tr_api_run` calls `tr_failure_clear()` on entry, and on a `tr_prep` failure records `TRF_PREP_FAILED` (unless
  something more specific was recorded);
- a new entry point appended at the end of the module:

```fortran
  FUNCTION tr_api_last_error(e) RESULT(ierr) BIND(C, NAME="tr_last_error")
    TYPE(tr_diag_entry_c), INTENT(OUT) :: e
    INTEGER(C_INT) :: ierr
    INTEGER :: kind, code, nt
    REAL(rkind) :: time
    CHARACTER(LEN=96) :: detail
    CHARACTER(LEN=TR_DIAG_PARAM_LEN) :: pname
    CHARACTER(LEN=TR_DIAG_MSG_LEN) :: msg
    CALL tr_failure_get(kind, code, nt, time, detail)
    SELECT CASE (kind)
    CASE (TRF_NONE);        pname = 'NONE'
    CASE (TRF_EQ_FAILED);   pname = 'EQ_FAILED'
    CASE (TRF_NONFINITE);   pname = 'NONFINITE'
    CASE (TRF_TR_CHECK);    pname = 'TR_CHECK'
    CASE (TRF_PREP_FAILED); pname = 'PREP_FAILED'
    CASE (TRF_REFUSED);     pname = 'REFUSED'
    CASE DEFAULT;           pname = 'OTHER'
    END SELECT
    WRITE(msg, '(A,I0,A,ES14.7,A,A)') 'nt=', nt, ' t=', time, ' s: ', TRIM(detail)
    CALL fill_diag_entry(e, pname, INT(code, C_INT), msg)   ! the helper tr_validate's push_diag uses; factor it out if it is internal
    ierr = TR_OK
  END FUNCTION tr_api_last_error
```

`tr/tr_api.h`:

```c
/* The last failure of tr_run (and tr_continue), or param "NONE".
   param: EQ_FAILED, NONFINITE, TR_CHECK, PREP_FAILED, REFUSED or OTHER; code: the Fortran IERR;
   msg: "nt=<step> t=<time> s: <what failed>". Cleared at the start of every tr_run. */
int tr_last_error(tr_diag_entry_t* e);
```

Python:
- `_ffi.py` declares `tr_last_error`.
- `errors.py` adds `TrFailure` (a frozen dataclass: `kind`, `code`, `nt`, `time`, `detail`) and `TrlibRunError`
  gains a `failure` attribute (`None` by default).
- `Trlib.run` fills it on ierr 3 by calling `tr_last_error`; `Trlib.last_error()` returns it.
- `tr_mcp`'s `run` and `run_and_get_state` put the record in the error they return.

- [ ] **Step 5: Run; check `tr2`; commit**

- Run the suite (Conventions); the new tests pass.
- Build `tr2` and run the §5 input `n50`: `diff` against `~/task-web-scratch/iter-heating/ref-dee378ce/n50/out.txt`
  shows no difference in the 89 printed lines (`extract.py`).
- `tr2`'s output must be unchanged bit for bit; the Linux tr baselines check it again in CI.

Commit: `feat(tr): in library mode an EQ failure or NaN in the loop ends the run with a record (tr_last_error)`.

---

### Task 4: PR 1 delivered

**Files:** `CHANGELOG.md` (Added / Changed / Fixed), `python/trlib/README.md`, `docs/sphinx/{en,ja}/` (the TR API page:
`tr_last_error`, the `eq:` names, NTEQIT/TPRST/NRMAX), `docs/product-line/upstream-status.md` (a row for this group;
its own commit, naming the hashes; a second commit because it needs the first ones' hashes).

- [ ] **Step 1:** the full suite with `MONO_LIB_PATH`/`TOTLIB_PATH` set, after a full rebuild (Conventions). Write the
  counts against the baseline into the PR body.
- [ ] **Step 2:** mutation check of each new refusal and failure path. A scratch `mutate.py` replaces one condition,
  rebuilds one module and runs the task's test file; each mutation must be seen to fail.
- [ ] **Step 3:** the gate (Conventions): code review and Codex review on the whole branch; fix; re-review; marker.
- [ ] **Step 4:** push `feat/tr-library-errors` to `origin`. Open the PR:

```bash
gh pr create -R HengyuLi-Ozaki-lab/task --base kyoshimi-develop --head feat/tr-library-errors --label product-only \
  --title "TR library: MODELG=9 errors and names (#96 PR 1 of 3)" --body-file <body>
```

The body has:
- the spec link and the author's decisions;
- why it is product-only (#226);
- the two cherry-picks;
- what was measured;
- the counts and the mutations;
- the four spec decisions as questions;
- a paragraph addressed to `@k-yoshimi` asking for the review of the C interface and the registry (the author's
  request of 2026-11-16).

  Requested reviewers on the fork must be collaborators, so the mention is the request.
- The author merges, with a merge commit and four checks green. Do not merge.

---

### Task 5: outputs by name (PR 2, delivered in the same task)

**Files:**
- Modify: `tr/tr_api.f90` (appended: the table and three entry points), `tr/tr_api.h`
- Modify: `tot/tot_api.f90`, `tot/tot_api.h` (`tot_get_scalar("tr:<name>")`)
- Modify: `python/trlib/{_ffi,state,trlib}.py`, `python/totlib/{_ffi,totlib}.py`, `python/mcp-servers/tr_mcp/server.py`
- Test: `python/trlib/tests/test_scalars_by_name.py`, `python/mcp-servers/tr_mcp/tests/test_scalar_schema.py` (new)

The table, with each unit read from `tr/trrslt_globals.f90` (lines 192–366 at the base) before it is final:

| Name | Source | Unit |
|---|---|---|
| T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, TAUE1, TAUE2, ZEFF0, ALI, RQ1, AJRFT | the state struct's scalars | as `tr_state_t` |
| PNFT | `trrslt_globals.f90:194` | MW (alpha; P_fus = 5 PNFT for D–T) |
| QF | `:366`, 5 PNFT / (POHT + PNBT + PRFST + PEXST) | — |
| PINT | `:323`, POHT + PNBT + PRFST + PNFT + PEXST (alpha included) | MW |
| POHT, PNBT | `:192`, `:193` | MW |
| PRFST, PEXST | `:317`, `:316` | MW |
| PRLT, POUT | `:229`, `:324` | MW |
| AJOHT, AJNBT, AJBST | `:246`, `:236`, `:241` | MA |
| RIP | boundary current (trcomm) | MA |
| VLOOP | `:348` | V |
| WPDOT | `:335` | MW (MJ/s) |
| H98Y2, TAUE98 | `:362`, `:360` | —, s |

- [ ] **Step 1: Write the failing tests**

```python
import math, pytest
from trlib import Trlib, TrlibParamError
pytestmark = pytest.mark.forked

def test_every_enumerated_scalar_is_finite_after_steps():
    with Trlib() as t:
        t.run(20)                       # defaults; group N gives the globals of the last step
        names = t.scalar_names()
        assert len(names) == 31 and len(set(names)) == 31
        for n in names:
            assert math.isfinite(t.get_scalar(n)), n

def test_qf_matches_its_formula():
    with Trlib() as t:
        t.run(20)
        g = t.get_scalar
        denom = g("POHT") + g("PNBT") + g("PRFST") + g("PEXST")
        assert g("QF") == pytest.approx(5.0 * g("PNFT") / denom, rel=1e-12)

def test_struct_scalars_agree_with_the_table():
    with Trlib() as t:
        t.run(20)
        s = t.get_state()
        for n in ("T", "WPT", "AJT", "Q0", "AJRFT"):
            assert t.get_scalar(n) == getattr(s, n)

def test_unknown_scalar_is_refused():
    with Trlib() as t, pytest.raises(TrlibParamError):
        t.get_scalar("NOSUCH")

def test_state_carries_the_scalars_and_to_dict_is_unchanged():
    with Trlib() as t:
        t.run(5)
        s = t.get_state()
        assert set(s.scalars) == set(t.scalar_names())
        assert "PNFT" not in s.to_dict()      # baselines compare to_dict at 1e-10 (G4)
```

`test_scalar_schema.py`: every name `Trlib.scalar_names()` returns has an entry in `tr_mcp`'s state schema.

Add one `totlib` test: `Tot.get_scalar("tr:PNFT")` equals the `trlib` value for the same `tr:` inputs run through
mono.

- [ ] **Step 2: Run them to see them fail** (`AttributeError: scalar_names`).
- [ ] **Step 3: Implement.**
  - Fortran: an `N_SCALARS = 31` name array and one `SELECT CASE` routine `scalar_value(name, v, found)`, appended
    to `tr_api.f90`, and three entry points:

```fortran
  FUNCTION tr_api_scalar_count() RESULT(n) BIND(C, NAME="tr_scalar_count")
  FUNCTION tr_api_scalar_name(i, buf, buflen) RESULT(ierr) BIND(C, NAME="tr_scalar_name")   ! 1-based; TR_ERR_INVALID past the end or for a short buffer
  FUNCTION tr_api_get_scalar(name, value) RESULT(ierr) BIND(C, NAME="tr_get_scalar")        ! TR_ERR_NOT_INIT before tr_init; TR_ERR_INVALID for an unknown name
```

  - `tr_api.h` gets the three prototypes from the spec's section 3 with these return codes.
  - Python:
    - `Trlib.scalar_names()`, `Trlib.get_scalar(name)`;
    - `TrState.scalars` (a dict filled by `get_state`), not in `to_dict()`;
    - `tr_mcp`'s `get_state` returns `scalars`, and `describe_state_schema` lists each with its unit and meaning;
    - TOT: `tot_get_scalar(name, value)` strips `tr:` and calls `tr_get_scalar`; `Tot.get_scalar`.
- [ ] **Step 4: Run them to see them pass**, then the full suite.
- [ ] **Step 5: Commit, deliver:**
  - CHANGELOG, README and sphinx pages;
  - the gate;
  - branch `feat/tr-library-outputs` from PR 1's head. Its PR is opened after PR 1 merges, with
    `--base kyoshimi-develop`, or as a stacked PR whose base is `feat/tr-library-errors`, retargeted to
    `kyoshimi-develop` before anyone merges it (a stacked PR merged first lands in the lower branch);
  - the same `@k-yoshimi` paragraph.

---

### Task 6: parameter classes, `tr_continue`, `DIPDT` over the call (PR 3)

**Files:**
- Modify: `tr/tr_param_registry.f90` (control list, structural counter, last structural name, `tr_param_class`)
- Modify: `tr/tr_api.f90`, `tr/tr_api.h` (`tr_continue`, `tr_param_class`; the failed-state flag)
- Modify: `tr/trloop.f90:43` (the `DIPDT` line)
- Test: `python/trlib/tests/test_continue.py`, `python/trlib/tests/test_continue_vs_tr2.py` (new)

- [ ] **Step 1: Write the failing tests** (`test_continue.py`)

```python
import pytest
from trlib import Trlib, TrlibParamError
pytestmark = pytest.mark.forked

def test_continue_carries_t_and_nt_after_a_control_set():
    with Trlib() as t:
        t.run(10)
        s0 = t.get_state()
        t.set_param("PECTOT", 1.0)
        t.continue_run(10)
        s1 = t.get_state()
        assert s1.nt == s0.nt + 10 and s1.T > s0.T

def test_continue_refuses_after_a_structural_set_and_names_it():
    with Trlib() as t:
        t.run(10)
        t.set_param("RR", 3.0)
        with pytest.raises(TrlibParamError) as e:
            t.continue_run(5)
        assert t.last_error().kind == "REFUSED" and "RR" in t.last_error().detail

def test_continue_needs_a_prepared_state():
    with Trlib() as t, pytest.raises(TrlibParamError):
        t.continue_run(1)

def test_param_class():
    with Trlib() as t:
        assert t.param_class("RIPE") == 1 and t.param_class("PNBTOT") == 1
        assert t.param_class("RR") == 0 and t.param_class("eq:RB") == 0
        assert t.param_class("NOSUCH") == -1

def test_two_calls_ramp_to_each_ripe():
    with Trlib() as t:
        t.set_param("RIPS", 1.0); t.set_param("RIPE", 2.0)
        t.run(10)
        assert t.get_scalar("RIP") == pytest.approx(2.0, rel=1e-12)
        t.set_param("RIPE", 3.0)
        t.continue_run(20)
        assert t.get_scalar("RIP") == pytest.approx(3.0, rel=1e-12)

def test_a_later_run_with_nothing_set_continues():
    with Trlib() as t:
        t.run(5); t.set_param("PECTOT", 1.0); t.continue_run(5)
        t.run(5)
        assert t.get_state().nt == 15
```

`test_continue_vs_tr2.py`:
- Skip when `tr/tr2` is not built; it runs on macOS here and is recorded in the PR.
- For each control parameter (`RIPE`, `PNBTOT`, `PICTOT`, `PECTOT`, `PLHTOT`, `TPRST`, and `NTEQIT` under the
  ITER `MODELG=9` input), write a two-stage `tr2` input:
  - the base namelist, `r`;
  - the change, `c`, `q`.
- Run it with `TR_REGRESS_DUMP=1` in a temporary directory (`subprocess.run`, timeout 300). Then run the API:
  `run(n1)`, set, `continue_run(n2)`.
- Compare the dump with `TrState.to_dict()` through `test_run/scripts/compare_metrics.py` at 1e-10.
- One test per parameter. Segment lengths are multiples of `NTEQIT` and `NTSTEP` (the spec's `NT` phase note).

- [ ] **Step 2: Run to see them fail** (`AttributeError: continue_run`).

- [ ] **Step 3: Implement the registry**

```fortran
  INTEGER, SAVE :: g_structural = 0
  CHARACTER(LEN=32), SAVE :: g_last_structural = ''
  ...
  ! A control parameter takes effect at the next step of a running case (tr_continue).
  ! A name is here only when test_continue_vs_tr2.py shows tr_continue equals tr2's C for it.
  LOGICAL FUNCTION is_control(b)
    CHARACTER(LEN=*), INTENT(IN) :: b
    SELECT CASE (TRIM(b))
    CASE ("RIPE", "PNBTOT", "PICTOT", "PECTOT", "PLHTOT", "NTEQIT", "TPRST")
       is_control = .TRUE.
    CASE DEFAULT
       is_control = .FALSE.
    END SELECT
  END FUNCTION is_control
```

- In `tr_param_set` and `tr_param_set_str`, on success: `g_generation += 1`, and if `.NOT. is_control(base name)`
  then `g_structural += 1; g_last_structural = name`.
- `tr_param_note_external_set` (Task 1) counts as structural with the `eq:` name.
- Public: `tr_param_structural_generation()`, `tr_param_last_structural()`.
- `tr_param_class(name)`:
  - 1 for `is_control`;
  - 0 for an `eq:` name or a name the setter knows;
  - −1 otherwise.
- The known names come from a `PARAMETER` list of the setter's CASE names (scalar and array bases). A test reads the
  CASEs from the source and holds the list to them, as `test_param_values.py` does for `value_refused`.

- [ ] **Step 4: Implement the API and `DIPDT`**

`tr_api.f90`: the module keeps `g_prep_structural` (set beside `g_prep_generation` after every `tr_prep`) and
`g_failed`:
- set when `tr_prep` or `tr_loop` fails in `tr_run` or `tr_continue`;
- cleared after a successful `tr_prep`.

```fortran
  FUNCTION tr_api_continue(nsteps) RESULT(ierr) BIND(C, NAME="tr_continue")
    INTEGER(C_INT), VALUE, INTENT(IN) :: nsteps
    INTEGER(C_INT) :: ierr
    INTEGER :: ntmax_save, calc_ierr
    IF (.NOT. g_initialized) THEN; ierr = TR_ERR_NOT_INIT; RETURN; END IF
    CALL tr_failure_clear()
    IF (nsteps < 0) THEN; ierr = TR_ERR_INVALID; RETURN; END IF
    IF (.NOT. g_prepared) THEN
       CALL refuse('no prepared case: tr_run prepares one')
       RETURN
    END IF
    IF (g_failed) THEN
       CALL refuse('the last run failed: tr_run prepares the case again')
       RETURN
    END IF
    IF (g_prep_structural /= tr_param_structural_generation()) THEN
       CALL refuse('structural parameter '//TRIM(tr_param_last_structural())//' set since the preparation')
       RETURN
    END IF
    g_prep_generation = tr_param_generation()     ! the control sets are taken in
    ntmax_save = NTMAX
    NTMAX      = NT + nsteps
    CALL tr_loop(calc_ierr)
    NTMAX      = ntmax_save
    IF (calc_ierr /= 0) THEN
       g_failed = .TRUE.
       ierr = TR_ERR_CALC_FAILED
       RETURN
    END IF
    ierr = TR_OK
  CONTAINS
    SUBROUTINE refuse(why)
      CHARACTER(LEN=*), INTENT(IN) :: why
      CALL tr_failure_record(TRF_REFUSED, 0, NT, T, why)
      WRITE(6, '(A)') 'XX tr_continue: '//why
      ierr = TR_ERR_INVALID
    END SUBROUTINE refuse
  END FUNCTION tr_api_continue

  FUNCTION tr_api_param_class(name) RESULT(cls) BIND(C, NAME="tr_param_class")   ! 1 control, 0 structural, -1 unknown
```

- `tr_run` stays as it is, except that it sets `g_failed` and `g_prep_structural`. After a failure, a `tr_run` with
  nothing set continues as before; `tr_continue` refuses until a preparation. The interface documentation says so.

`tr/trloop.f90:43`:

```fortran
         IF(NTMAX.GT.NT) DIPDT=(RIPE-RIPS)/(DBLE(NTMAX-NT)*DT)
```

In `tr2` this is the same number: `NT = 0` at the loop's start after `R` (`tr/trprep.f90:144`) and after `C`
(`tr/trmenu.f90:87`), and the loop leaves at `NT.GE.NTMAX` before this line. The C header documents that `NT` counts
on across calls while `tr2`'s `C` resets it.

- [ ] **Step 5: Run; commit**

- `test_continue.py` passes, and `test_continue_vs_tr2.py` passes at 1e-10 for every parameter. A parameter that
  does not match leaves the control list, and the commit says why.
- Every TR test passes; `tr2` on `n50` is unchanged (`extract.py`).

Commit: `feat(tr): tr_continue and parameter classes; the current ramp is taken over the call`.

---

### Task 7: TOT, Python, MCP; the `tr_iter01_m9` equivalence case; acceptance (PR 3)

**Files:**
- Modify: `tot/tot_api.f90`, `tot/tot_api.h` (`tot_continue(nsteps)` calls `tr_api_continue`; TOT runs only TR, as
  `tot_run` does)
- Modify: `python/trlib/trlib.py` (`continue_run`, `param_class`), `python/totlib/totlib.py` (`continue_run`)
- Modify: `python/mcp-servers/tr_mcp/server.py` (a `continue_run` tool; `describe_parameters` shows each name's class)
- Create: `test_run/inputs/tr_iter01_m9.in` (tr.ITER01 with `modelg=9`, `NTEQIT=0`, the ITER geometry, the three
  stages `r` / `c` / `c` with the GSAF prologue lines that `run_tests.sh` expects for tr cases),
  `test_run/inputs/tr_iter01_m9.eqparm` (`&eq RR=6.2 RA=2.0 RKAP=1.7 RDLT=0.33 RB=2.1 BB=5.3 RIP=2.0 NSGMAX=128 &end`)
- Modify: `test_run/run_tests.sh` (copy `inputs/<case>.eqparm` to `eqparm` for `tr` cases too, as it does for `tot`),
  `test_run/test_definitions.conf`
- Create: `test_run/baselines/tr_iter01_m9/` (from the regen workflow, below)
- Modify: `python/trlib/tests/test_equivalence.py` (the case: `run(1500)`, set, `continue_run(2000)`, set,
  `continue_run(6500)`)
- Test: `python/mcp-servers/tr_mcp/tests/test_continue_tool.py`, a `totlib` continue test

- [ ] **Step 1: Write the failing tests:**
  - the MCP tool test: `continue_run` after a control set advances `nt`, and after a structural set returns the
    refusal with its record;
  - the `totlib` test: `Tot.continue_run` equals `Trlib.continue_run` on the same `tr:` inputs, in mono;
  - the equivalence case (skips without its baseline).
- [ ] **Step 2: Implement** the three layers as above.
- [ ] **Step 3: The baseline.**
  - Push a branch `regen/tr-iter01-m9` (PR 3's head) to `origin`. `regen-baselines.yml` runs on `push` to
    `regen/**` and builds `tr2` on Linux.
  - Take `test_run/baselines/tr_iter01_m9/` from its artifact, commit it on PR 3's branch, and delete the regen
    branch.
  - The equivalence test then runs on Linux CI at 1e-10.
- [ ] **Step 4: Acceptance, once, recorded in the PR.**
  - Through `trlib`, the three stages at `NTEQIT=50` (`DT=0.02`, `run(1500)`; then `RIPE=9`, `PNBTOT=25`,
    `PICTOT=5`, `PECTOT=20`, `continue_run(2000)`; then `continue_run(6500)`), with `eq:RB 2.1` and `eq:NSGMAX 128`.
    It must give:
    - RIP 7.0 MA at 30 s and 9.0 MA at 70 s;
    - Q0 1.652 / 1.242 / 1.095 / 0.632 at 35 / 70 / 90 / 190 s;
    - WPT 87.01 MJ at 190 s.
  - At `NTEQIT=0`: WPT 84.47 MJ, Q0 0.603 at 190 s.
  - Read Q0 at 35 and 90 s by cutting the continue calls at those times (RIPE interpolated before each piece).
  - Compare with `~/task-web-scratch/iter-heating/ref-dee378ce/{n50,n0}/out.txt` (the product `tr2` at
    `dee378ce`).
- [ ] **Step 5:** the full suite; commit.

---

### Task 8: PR 3 delivered

- [ ] CHANGELOG, READMEs, sphinx (en, ja): `tr_continue`, classes, the `NT` phase note, `tot_continue`, the MCP tool.
- [ ] The `upstream-status.md` row of the group (one row for the three PRs, updated by each).
- [ ] The gate.
- [ ] Push `feat/tr-library-continue`, open its PR with `--base kyoshimi-develop` once PR 2 has merged (or stacked,
  as in Task 5), with the acceptance table, and the `@k-yoshimi` paragraph.
- [ ] After the author merges: tell task-web's `iter-heating` work that the interface is on the product line. The
  `deps.lock` bump is task-web's, after plato-cpc's PR, and only one bump PR is open at a time.

## Self-review against the spec

- **§1 parameters:** NTEQIT and TPRST are in Task 1, with `eq:` routing and classes (Task 6). The class shows in
  `describe_parameters` (Task 7).
- **§2 run control:** `tr_continue` and its refusals are in Task 6. The structural counter and `tr_run` unchanged
  are Task 6. `DIPDT` is Task 6. The `NT` phase note is in Task 6's header comment and Task 8's docs. TOT, Python
  and MCP are Task 7.
- **§3 outputs:** the table, units, `AJT`/`RIP` and `TrState.scalars` are in Task 5. The schema test and
  `tot_get_scalar` are Task 5.
- **§4 errors:**
  - `eq_calc`'s `IERR` is the cherry-pick `4f500ea1`;
  - the `zminmax` edge is Task 2;
  - library mode, the loop and the q-scaling are Task 3, and so is `tr_last_error` with `.failure` and the MCP
    payload.
- **§5 tests:**
  - unit tests: Tasks 1, 3, 5 and 6;
  - the per-parameter comparison with `tr2`: Task 6;
  - the equivalence case: Task 7;
  - acceptance: Task 7.
- **§6 delivery:** three PRs in order (Tasks 4, 5 and 8). Product-only instead of two PRs per change, for the reason
  at the top. The Kyoto-line report of the TASK developers' files (`trloop`, `equnit`, `eqcalq`, `trmetric`) goes in
  each PR body for the author to forward.

## Findings during execution (2026-11-17)

Found while delivering PR 1; they change later tasks (Tasks 5 to 8), the `deps.lock` bump and the second spec.

### F1. bpsd overruns its spline after a larger grid (fixed upstream-side: k-yoshimi/bpsd#7)

- **The bug:** bpsd sized the spline only at the first get.
- **Where it shows:** under MODELG 9, NRPMAX changes between NTEQIT re-solves. In the §5 run it alternates between 47
  and 48; the first put is 48, so that run never overran.
- **The fixes:**
  - in bpsd, status 2 or 3 now adjusts the spline (k-yoshimi/bpsd#7);
  - in TASK, `eq_bpsd_put` sizes its arrays again when EQ's grid changes (PR 1).
- **Interim:** plato-cpc's fork PR #22 refuses a TR NRMAX different from the process's first preparation (`61ff3cdf`).
  That guard comes off in a separate commit once the pinned bpsd has #7. The TR-NRMAX regrid tests are skipped until
  then.
- **The EQ-grid regrid tests** are gated on `TRLIB_BPSD_REGRID_FIX=1`.
- **task-web's `deps.lock` bump moves bpsd** to the merge commit of #7.

### F2. Splitting a run into several calls is not seamless

Probe: `~/task-web-scratch/iter-heating/chunk-probe/`. It compares one `tr_run(N)` with chunked calls that add up to N:

| Case | Largest relative difference |
|---|---|
| MODELG 2 defaults | 1e-13 (roundoff) |
| MODELG 9 ITER, 7 MA flat, NTEQIT 0 | 5e-9 |
| Same, NTEQIT 50, chunks aligned to 50 | 1e-9 |
| Same, NTEQIT 50, chunks of 70 | 4.5e-8 |
| Near an EQ failure (flat 9 MA, heated) | Q0 differs by 0.4 % |

Every call begins with a prologue (`tr_eval`, `RIP=RIPS`, `DIPDT`, `tr_bpsd_get`). `tr2`'s `C` has the same prologue.
Consequences:

- **Task 6.**
  - `tr_continue` must equal `tr2`'s `C` at the same cut points (the spec's test, 1e-10). That holds by construction
    if `tr_continue` runs the same `tr_loop`.
  - Do NOT promise that k chunks equal one call.
  - Add a test that measures the chunk difference on the ITER MODELG 9 case and documents it (e.g. relative difference
    < 1e-7 on WPT and Q0 for aligned chunks), so that a regression in the prologue shows up.
  - Optional, and only if it is cheap and `tr2`-neutral: find which prologue statement causes the 1e-9. Report it; do
    not change it in this PR without the TASK developers.
- **task-web (second spec).** The scenario runner cuts segments only at schedule breakpoints: a ramp knot, a heating
  event, a stage. That is what `tr2` does. It does not cut at the recording interval. The time series comes from F3.
  The numerical checks of step 3 add one case: the same scenario with an extra breakpoint that changes nothing,
  showing the effect of a cut.

### F2, extended (Task 5/5b review, 2026-11-17)

A cut that falls on an NTEQIT re-solve changes the history row right after it. In the parent build the numbers are
the same. Measured:

| Case | Row after the cut | One call | Run in chunks |
|---|---|---|---|
| NTEQIT 50, chunks of 100 | WPDOT at T = 2.04 | 0.874 | 0.746 |
| NTEQIT 50, chunks of 100 | WPDOT at T = 8.04 | 0.400 | 0.255 (36 % lower) |
| Chunks of 70 | WPDOT at T = 7.04 | 0.447 | 0.292 |

The one-call run carries the spike that the metric change of the re-solve puts into WPT; the chunked run does not, because
after a cut its first TRGLOB re-anchors WPPRE/TPRE on the re-solved WPT.

TAUE2 changes by up to 3 %, and H98Y2 with it.

- **Cause.** A call's first TRGLOB runs at the same T after `eq_calc` and re-anchors WPPRE/TPRE on the re-solved WPT
  (`tr/trrslt_globals.f90:332-338`).
- **Not affected.** State: the evolved profiles do not change.
- **Consequences:**
  - task-web's steady test takes dW/dt from the WPT series over its window, not from WPDOT.
  - Task 6's history test (one call against `run` + `continue_run`) excludes or bounds WPDOT, TAUE2 and H98Y2 on the
    row after a cut.
  - **Option for PR 3** (library mode only, outputs only): a call that continues keeps WPPRE/TPRE, as the last-step
    branch does at `tr/trexec.f90:447-453`. This makes the diagnostics seamless. Propose it to the TASK developers in
    the PR body.
  - `tr2`'s `C` still writes the history row of the step at each cut a second time. A history compared against `tr2`
    drops one row per cut.

### F3. New Task 5b (PR 2): the run's history by name

TR records a time history every `NGTSTP` steps (default 2):
- `GT(NGT)` holds the time and `GVT(NGT, 1:NCTM=110)` the globals, in single precision (`GUCLIP`);
- they are written in `tr/trrslt_globals.f90` from line 427;
- the arrays have `NTM = 10001` rows (`tr/trcom0.f90:12`). Recording stops silently when they are full.

Export it so that a client gets the whole trajectory without cutting the run.

**C interface:**

```c
int tr_history_length(void);                                      /* rows recorded so far (NGT) */
int tr_history_count(void);                                       /* number of named columns */
int tr_history_name(int i, char* buf, int buflen);                /* 1-based; TR_ERR_INVALID past the end */
int tr_history_get(const char* name, double* buf, int n, int* got);  /* copies min(n, NGT) rows, T included as "T" */
```

**The named columns.** Read the column map from `trrslt_globals.f90` lines 431-549, and check each against the code
there. A curated list: T (`GT`), WPT, Q0, RIP, the central Te/Ti (TS0), TAUE1/TAUE2, BETAN, PNFT, PINT, POHT, PNBT,
the RF/EC/IC powers, PRLT, POUT, AJT, AJOHT, AJNBT, AJBST, VLOOP, WPDOT, QF, and the central and average density.
Every listed name gets a test that its last row equals the final scalar of PR 2's table to single precision (rel
1e-6).

**Other points:**
- `NGT` and the arrays start again at `tr_prep` (check that `tr_prep` resets `NGT`). `tr_continue` appends.
- `tr_history_full()`, or a flag in the length call, says when `NGT` reached `NTM`.
- Python: `Trlib.history(names=None) -> dict[str, numpy.ndarray]`. `tr_mcp`: a `get_history` tool.
- **Tests:**
  - the length grows by `nsteps/NGTSTP` per call;
  - the history equals across one call and `run` + `continue_run`, up to F2's difference;
  - the last row agrees with the final scalars;
  - a full buffer is reported.
- **task-web** sets `NGTSTP` so that the scenario's steps / NGTSTP < 10001.

### F3, the fourth Codex round (2026-11-22, after the merge of the product line `8a9f5e98`)

Six findings at P2 and two at P3, each measured before it was answered:

- **The failed iterate of a `TRCHCK` failure was a row.** `tr_exec` records it for `tr2`'s graphics (`DT` 100 s: a row at
  800 s with `TE0` 3.7e6 after that step's own row; at `NGTSTP` 3 a row off the cadence). Not recorded in library mode.
- **Under `MODELG` 9 the row of a step that ends with an EQ re-solve holds the `Q0` of before it.** `tr_loop` records the
  step, re-solves, and recomputes `Q0` (`tr_bpsd_get`, `TRCALC`): 6.6e-5 relative in the test case, the other 29 shared
  names agree. Documented and tested; the record before the re-solve is `tr_loop`'s choice (a consistent snapshot).
- **`tr_run(0)` evaluates no step**, so after a preparation what it sets is new (`T` 0, `RIP` = `RIPS`, `Q0`) and what
  only a step computes (the powers, `WPT`) is the run before's. Documented and tested, not refused: `get_state` after
  `run(0)` is how the initial profiles are read. (The fifth round's wording fix; evaluating the prepared state in
  `run(0)` was considered and not done: `TRCALC` injects the `PELTIM` pellet on every call within half a step of it
  (`tr/trcalc.f90`), so a second call at t = 0 would inject it twice.)
- **`GVT` columns 89 to 88 + 4 `NGPST` are also `TRATOTN`'s sawtooth record** once `MDLST` /= 0 and `T` >= `TSST`. `TSST`
  is not a library parameter (1e9 s), so in library mode the record never starts; a test pins that.
- **Descriptions:** `PNFT` is alpha and proton together for D-He3 (`MDLNF` 5, 6) and `QF` a D-T gain; `RIP` is the
  equilibrium's boundary current under `MODELG` 3, 5 and 8.
- **Tests:** the `tot` reference reads used `trlib`'s own library, not the image `Tot` loaded (`TOTLIB_PATH` = the mono
  image failed them); the skip markers ignored `TRLIB_PATH` (all 126 tests skipped with the library only there).

The fifth round (on `c9e7b464`), four P2 and five P3: a step `tr_loop` finds not finite was left in the history (`DT`
1e6 s: a row of NaN; now taken back), a failed preparation left the run before's rows (`MODEL_PNF` with `MDLNF`; now no
rows), `tr_mcp`'s `run_and_get_state` with `ntmax` 0 showed the call before's results (now `T` only), the `run(0)`
wording above, `RIP` under `MDLUF` 1 and 3, the schema of a library older than the scalar table, and three test defects
(a relative library path resolved after the fixture `chdir`: 29 tests failed; the `tot` skip markers; the status row).

### F4. task-web side of the bump (for the second spec and the `deps.lock` bump)

- **Runs that now fail.** In library mode, MODELG 0, 4 or 25, and RIPS = 0, now fail with NONFINITE at nt 1. Before,
  they returned RC 0 with NaN scalars, which task-web's `non_finite` flag (#133) caught. So
  `tests/unit/test_tr_param_limits.py:250` and the assistant's `non_finite` tool descriptions change with the bump.
- **`tr_last_error`.** A failing run now carries the record (`kind`, `code`, `nt`, `time`). task-web's bridge maps it
  into the job's error.
- **Rows to add.** The `deps.lock` bump takes lib-hardening, #22, PR 1-3 and bpsd at #7.

### F5. PR 1's gate review (2026-11-17): what the plan said and what is true

- **`tr2` is not unchanged by PR 1.** The plan and the first drafts said "library mode only" and "`tr2` unchanged". The
  #228 cherry-pick `23541105` makes `tr_set_metric` fail without a library-mode gate, so `tr2`'s `R` stops at
  `trmenu.f90:74` where it used to run (`RIPS` 0.81 and 0.84 in that commit's table), and a second `R` in one `tr2`
  session under `MODELG` 9 changes too (`7656ebbe`, a fix). Both are #226's own commits. `tr2`'s output is unchanged
  on a single healthy `R`.
- **`eq:` names reached the bpsd#7 overrun with no guard**, and some did nothing (`eq:RR`, `eq:RA`, `eq:RKAP`,
  `eq:RDLT`, `eq:BB`, `eq:RIP` under `MODELG` 9; `eq:KNAMEQ` always). They are refused at set time now; every `eq:`
  name is refused after the process's first preparation attempt, until the pinned bpsd has #7.
- **`REFUSED` is reserved** for `tr_continue` (PR 3); nothing records it.
- **EQ's reason** (`EQ_ERRMSG`) is appended to an `EQ_FAILED` record's detail; `libtrapi.so` has no `eq_last_error`.
- **The `eq:` guard closes one route to the bpsd#7 overrun, not all.** Measured on an unpatched bpsd: `MODELG` 9 with
  `RA` 0.5 in one lifecycle, then `RA` 1.0 (or the default) in the next, fails with `EQ_FAILED` 103 at q-scaling
  iteration 2, with no `eq:` name set and TR's `NRMAX` unchanged. EQ's plasma point count (`NRPMAX`) depends on `RA`,
  `RB` and the solved axis and edge, and it moves between `NTEQIT` re-solves inside one run (47 and 48 in `tr.ITER01`
  with `MODELG` 9). TOT's `eq:` dispatcher (`dispatch_eq` in `tot/tot_param_registry.f90`) calls `eq_param_set`
  directly, so the guard does not apply in `totlib` or the mono build. **The protection against the overrun is bpsd#7
  itself:** task-web's `deps.lock` bump that brings PR 1 must also move bpsd to #7's merge commit; if #7 is not merged
  by then, the bump waits.
- **EQ's reason is cleared** with the failure record (`tr_failure_clear`), so a later lifecycle's record does not carry
  an earlier run's `EQ_ERRMSG`.
