# EQ validate group (tw#188, tw#214 part 2, tw#217 part 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** EQAXIS's failure message names the bound the axis crossed and, inside the solve, the iteration and the
axis's path; `validate()` flags an analytic solve whose grid `RR -/+ RB` reaches R <= 0. No result changes.

**Architecture:** Fortran only in `eq/` (`eqcom1_mod.f90` gains `EQ_NLOOP`, `eqcalc.f90`'s EQLOOP maintains it,
`eqsub.f90`'s EQAXIS composes the message, `eq_api.f90`'s `eq_api_validate` gains one check); tests in
`python/eqlib/tests/` and `python/mcp-servers/eq_mcp/tests/`; docs. Spec:
`docs/superpowers/specs/2026-11-24-eq-validate-group-design.md`.

**Tech Stack:** gfortran 15 (macOS) / 13 (CI), GNU make, Python 3 (conda env `task`: pytest, pytest-forked,
pytest-timeout), Sphinx 7.4 (the scratch venv).

## Conventions for every task

- Clone: `~/task-web-scratch/equ-api/task`, branch `fix/eq-validate-group` (from `kyoshimi-develop` `44a0d010`).
  Scratch tools: `~/task-web-scratch/equ-api/tools/`. Logs: `~/task-web-scratch/equ-api/`.
- Build prefix (call it `$B`): `env -u AR -u LD -u NM -u RANLIB -u CC -u CFLAGS -u CPPFLAGS -u LDFLAGS PATH=/opt/homebrew/bin:/usr/bin:/bin`.
- EQ only: `$B make -C eq libeqapi.so`. GNU make 3.81 compares whole seconds: after an edit wait 1.2 s, `touch` the
  source, wait 1.2 s, build, and check that the `.o` is newer than the source. `eqcom1_mod.f90` is a module: after
  changing it rebuild every library from clean (Task 7), never trust an incremental build for the full suite.
- Tests: `cd <clone> && env -u MONO_LIB_PATH PYTHONPATH=python:python/mcp-servers /opt/anaconda3/envs/task/bin/python -m pytest <paths> --forked --timeout=120 --timeout-method=signal -q -p no:cacheprovider`.
- One test per case (no `subTest`: a failing one passes under `--forked`). Never `pkill`/`killall`; no `git stash`.
- Commit by pathspec, message ending `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Nothing is pushed
  without the author's go-ahead.

## Files

| File | Change |
|---|---|
| `eq/eqcom1_mod.f90` | `INTEGER :: EQ_NLOOP = 0` beside `EQ_ERRMSG`, with its comment |
| `eq/eqcalc.f90` | EQLOOP: `EQ_NLOOP = NLOOP` at the top of each iteration, `EQ_NLOOP = 0` on every way out |
| `eq/eqsub.f90` | EQAXIS: the bound crossed, the distance, the in-loop form |
| `eq/eq_api.f90` | `eq_api_validate`: the R <= 0 check, the helper `f3`, the header and box comments |
| `python/eqlib/tests/test_validate.py` | class `TestEqValidateGridReachesRZero` |
| `python/eqlib/tests/test_load_errors.py` | the message tests (bound, distance, iteration) |
| `python/mcp-servers/eq_mcp/tests/test_server.py` | one integration test through `handle_validate` |
| `docs/sphinx/modules/eq/{en,ja}/parameter-setting.md`, `faq.md`, `design.md` | the new check; the path failure's message |
| `CHANGELOG.md` | an entry under `## [Unreleased]` |
| `docs/product-line/upstream-status.md` | row AG (last commit, after merging `kyoshimi-develop`) |

---

### Task 1: Measure the results before any change

**Files:** Create: `~/task-web-scratch/equ-api/tools/eqgroup_digest.py` (scratch, not committed).

- [ ] **Step 1: Write the digest tool**

```python
"""Every state scalar and the grid's extent of a set of EQ cases, one process
per case, for the before/after comparison of the EQ validate group.
Usage: eqgroup_digest.py <clone> <out.json>"""
import json, os, subprocess, sys
clone, out = sys.argv[1], sys.argv[2]
CASES = {
    "defaults": {},
    "mdleqf10": {"MDLEQF": 10},
    **{f"mdleqf10_rdlt{r:+.1f}": {"MDLEQF": 10, "RDLT": r} for r in (-0.4, -0.2, 0.2, 0.4)},
    "plato_rb1.2": {"RR": 0.7, "RA": 0.18, "RKAP": 1.9, "RDLT": 0.4, "BB": 0.3, "RIP": 0.04},
    "plato_rb0.216": {"RR": 0.7, "RA": 0.18, "RKAP": 1.9, "RDLT": 0.4, "BB": 0.3, "RIP": 0.04, "RB": 0.216},
    "plato_rb0.7": {"RR": 0.7, "RA": 0.18, "RKAP": 1.9, "RDLT": 0.4, "BB": 0.3, "RIP": 0.04, "RB": 0.7},
    "iter_like": {"RR": 6.2, "RA": 2.0, "RB": 2.4, "RKAP": 1.7, "RDLT": 0.33, "BB": 5.3, "RIP": 15.0},
}
CHILD = r"""
import json, os, sys
sys.path.insert(0, os.path.join(sys.argv[1], "python"))
from eqlib import Eq
params = json.loads(sys.argv[2])
with Eq(os.path.join(sys.argv[1], "eq", "libeqapi.so")) as eq:
    eq.set_params(MODELG=2, **params)
    eq.run(0)
    st = eq.get_state()
    print(json.dumps({"scalars": {k: repr(v) for k, v in sorted(st.scalars.items())},
                      "rg": [repr(st.rg[0]), repr(st.rg[st.nrgmax - 1])]}))
"""
res = {}
for name, params in CASES.items():
    r = subprocess.run([sys.executable, "-I", "-c", CHILD, clone, json.dumps(params)],
                       capture_output=True, text=True, timeout=300)
    res[name] = json.loads(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else {"error": r.stderr[-500:]}
json.dump(res, open(out, "w"), indent=1, sort_keys=True)
print(len(res), "cases;", sum("error" in v for v in res.values()), "errors")
```

The file-load case (TST-2, `MODELG` 3) is covered by `test_load_errors.py`'s existing value checks.

- [ ] **Step 2: Run it on the unchanged build**

Run: `cd ~/task-web-scratch/equ-api && /opt/anaconda3/envs/task/bin/python -I tools/eqgroup_digest.py ~/task-web-scratch/equ-api/task runs/eqgroup-before.json`
Expected: `10 cases; 0 errors`.

---

### Task 2: validate(): failing tests for a grid that reaches R <= 0

**Files:** Modify: `python/eqlib/tests/test_validate.py` (a new class after `TestEqValidateWallGate`).

- [ ] **Step 1: Add the class**

```python
_PLATO = dict(MODELG=2.0, RR=0.7, RA=0.18, RKAP=1.9, RDLT=0.4, BB=0.3, RIP=0.04)


@unittest.skipUnless(
    DEFAULT_SO.exists(),
    f"libeqapi.so not built at {DEFAULT_SO}; run `make -C eq libeqapi.so`",
)
class TestEqValidateGridReachesRZero(unittest.TestCase):
    """An analytic solve tabulates psi on RR -/+ RB (EQTORZ, eq/eqcalc.f90),
    whatever MDLEQF: with RB >= RR that grid reaches R <= 0, the run goes on,
    and its result depends on RB (tw#217: PLATO's QSURF 5.646 with the
    default RB 1.2, 6.471 with RB = 1.2 RA). validate() flags it on RB,
    INCONSISTENT_PAIR; a file load brings its own grid."""

    @staticmethod
    def _rb(diags):
        return [(d.param, d.code, d.message) for d in diags if d.param == "RB"]

    def test_the_default_wall_of_a_small_device_is_flagged_and_the_run_still_completes(self) -> None:
        diags, err, state = TestEqValidateBoxGate._validate_then_run(**_PLATO)
        self.assertEqual(self._rb(diags), [(
            "RB", EqDiagCode.INCONSISTENT_PAIR,
            "RR -/+ RB = [-0.500, 1.900] reaches R <= 0 (RB=1.200 >= RR=0.700): "
            "set RB below RR (e.g. RB = 1.2*RA)")])
        self.assertIsNone(err)                       # validate() changes no run
        self.assertAlmostEqual(state.scalars["qsurf"], 5.646440769840485, places=9)

    def test_a_wall_of_1_2_ra_is_clean(self) -> None:
        diags, err, _ = TestEqValidateBoxGate._validate_then_run(**_PLATO, RB=0.216)
        self.assertEqual(diags, [])
        self.assertIsNone(err)

    def test_a_wall_equal_to_rr_is_flagged(self) -> None:
        with Eq() as eq:
            eq.set_params(**_PLATO, RB=0.7)
            rb = self._rb(eq.validate())
        self.assertEqual([(p, c) for p, c, _ in rb], [("RB", EqDiagCode.INCONSISTENT_PAIR)])
        self.assertIn("[0.000, 1.400] reaches R <= 0", rb[0][2])

    def test_a_wall_just_inside_rr_is_clean(self) -> None:
        with Eq() as eq:
            eq.set_params(**_PLATO, RB=0.6999)
            self.assertEqual(eq.validate(), [])

    def test_with_mdleqf_10_the_grid_is_checked_too(self) -> None:
        with Eq() as eq:
            eq.set_params(**_PLATO, MDLEQF=10.0, RGMIN=0.4, RGMAX=1.0, ZGMIN=-0.5, ZGMAX=0.5)
            self.assertEqual([(p, c) for p, c, _ in self._rb(eq.validate())],
                             [("RB", EqDiagCode.INCONSISTENT_PAIR)])

    def test_no_file_format_is_checked(self) -> None:
        for modelg in (3.0, 5.0, 8.0, 9.0, 15.0, 25.0):
            with Eq() as eq:
                eq.set_params(**{**_PLATO, "MODELG": modelg})
                self.assertEqual(self._rb(eq.validate()), [], f"MODELG={modelg}")

    def test_an_unprintable_wall_falls_back_to_a_static_message(self) -> None:
        with Eq() as eq:
            eq.set_params(MODELG=2.0, RB=1.0e30)
            rb = self._rb(eq.validate())
        self.assertEqual([(p, c) for p, c, _ in rb], [("RB", EqDiagCode.INCONSISTENT_PAIR)])
        self.assertIn("reaches R <= 0", rb[0][2])
        self.assertIn("values unprintable", rb[0][2])
```

- [ ] **Step 2: Run and see them fail**

Run: the test command on `python/eqlib/tests/test_validate.py -k GridReachesRZero`.
Expected: `test_a_wall_of_1_2_ra_is_clean`, `test_a_wall_just_inside_rr_is_clean` and
`test_no_file_format_is_checked` pass; the four others FAIL (no `RB` diagnostic today).

---

### Task 3: validate(): the check

**Files:** Modify: `eq/eq_api.f90` (`eq_api_validate`, after the `RB < RA` block; its `CONTAINS` part; the header
comment).

- [ ] **Step 1: The check, after `CALL push_diag("RB", EQ_DIAG_INCONSISTENT_PAIR, msgbuf)` / `END IF` of `RB < RA`**

```fortran
    ! ---- INCONSISTENT_PAIR: the psi grid RR -/+ RB reaches R <= 0 in an
    !      analytic solve (task-web-client #217). EQTORZ tabulates psi on
    !      RR -/+ RB for every analytic solve, whatever MDLEQF (the box
    !      RGMIN..ZGMAX is not that grid, see below). With RB >= RR the grid
    !      takes R <= 0, the run goes on, and the result depends on RB:
    !      measured 2026-11-24 at 44a0d010, PLATO (RR 0.7, RA 0.18, RKAP 1.9,
    !      RDLT 0.4) with the default RB 1.2 (grid -0.5..1.9): QSURF 5.646,
    !      PVOL 0.7848; RB 0.216 (1.2 RA): 6.471, 0.8102; RB 0.7 (= RR, the
    !      first point at R = 0): 6.052, 0.7997. A file load brings its own
    !      grid and is not checked.
    IF (analytic .AND. RR - RB <= 0.D0) THEN
       WRITE(msgbuf, '(9A)', IOSTAT=ios) &
            "RR -/+ RB = [", TRIM(f3(RR - RB)), ", ", TRIM(f3(RR + RB)), &
            "] reaches R <= 0 (RB=", TRIM(f3(RB)), " >= RR=", TRIM(f3(RR)), &
            "): set RB below RR (e.g. RB = 1.2*RA)"
       IF (ios /= 0) msgbuf = &
            "RR -/+ RB reaches R <= 0 (RB >= RR): set RB below RR (e.g. RB = 1.2*RA; values unprintable)"
       CALL push_diag("RB", EQ_DIAG_INCONSISTENT_PAIR, msgbuf)
    END IF
```

- [ ] **Step 2: The helper, appended at the end of `eq_api_validate`'s `CONTAINS` part (after `push_oor`)**

```fortran
    ! A value as F0.3 with its leading zero (gfortran writes 0.7 as ".700"),
    ! for the R <= 0 check's message; "*" if it does not fit.
    FUNCTION f3(x) RESULT(s)
      REAL(rkind), INTENT(IN) :: x
      CHARACTER(LEN=48) :: s
      INTEGER :: k
      WRITE(s, '(F0.3)', IOSTAT=k) x
      IF (k /= 0) THEN
         s = '*'
         RETURN
      END IF
      s = ADJUSTL(s)
      IF (s(1:1) == '.') THEN
         s = '0' // s
      ELSE IF (s(1:2) == '-.') THEN
         s = '-0' // s(2:)
      END IF
    END FUNCTION f3
```

- [ ] **Step 3: The header comment's `INCONSISTENT_PAIR` line**

Replace

```fortran
  !   INCONSISTENT_PAIR      : wall radius RB < minor radius RA, for an
  !                   analytic solve (the solver can abort or give a
  !                   wrong equilibrium).
```

with

```fortran
  !   INCONSISTENT_PAIR      : wall radius RB < minor radius RA, for an
  !                   analytic solve (the solver can abort or give a
  !                   wrong equilibrium); RB >= RR, whose grid RR -/+ RB
  !                   reaches R <= 0 (the result depends on RB).
```

and in the long comment at the box checks, after "Not seen before the run: an axis that leaves the box as it moves
(RDLT=0.4 with RGMIN=RR fails, ierr=103), and a Z bound inside the axis's rounding (ZGMIN=-1e-14 fails).", add:
`!      EQAXIS's message says which bound the axis crossed, by how much,` and
`!      and in which iteration of the solve (task-web-client #188, #214).`

- [ ] **Step 4: Build and run Task 2's tests**

Run: `$B make -C eq libeqapi.so` (check `eq/obj/pic/eq_api.o` is newer than `eq/eq_api.f90`), then the test command on
`python/eqlib/tests/test_validate.py`.
Expected: the whole file passes (the new class's 7 and the existing ones).

- [ ] **Step 5: Mutations, each seen to fail**

With a scratch copy of `eq/eq_api.f90` (`cp eq/eq_api.f90 /private/tmp/claude-501/-Users-lihengyu-Research-Project-MS10-TASK-task-web--claude-worktrees-great-goodall-ac7c77/c80430a8-f8d4-4593-b853-eb31ea1b195b/scratchpad/equ/eq_api.f90.orig`), for each of
(a) `RR - RB <= 0.D0` -> `RR - RB < 0.D0`, (b) `IF (analytic .AND. RR - RB <= 0.D0)` -> `IF (.FALSE.)`,
(c) `IF (s(1:1) == '.') THEN` -> `IF (.FALSE.) THEN`: wait 1.2 s, edit, wait 1.2 s, build, run the class; expected
(a) `test_a_wall_equal_to_rr_is_flagged` fails, (b) four fail, (c) `..._still_completes` and
`test_a_wall_equal_to_rr_is_flagged` fail. Restore from the copy after each, rebuild, and confirm `git diff eq/` shows
only the intended change.

- [ ] **Step 6: Commit**

```bash
git add eq/eq_api.f90 python/eqlib/tests/test_validate.py
git commit -m "fix(eq): validate() flags an analytic grid RR -/+ RB that reaches R <= 0 (task-web-client #217)" \
  -m "Body: the PLATO measurement (QSURF 5.646 / 6.471 / 6.052), the message, the three mutations seen to fail." \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The same finding through the EQ MCP server

**Files:** Modify: `python/mcp-servers/eq_mcp/tests/test_server.py` (class `TestIntegration`, after
`test_validate_wall_inside_plasma_with_mdleqf_10_adds_the_extent_check`).

- [ ] **Step 1: Add the test**

```python
    def test_validate_names_a_grid_that_reaches_r_0(self) -> None:
        """A small device with the default wall RB=1.2 >= RR=0.7: the
        analytic grid RR -/+ RB reaches R <= 0 (tw#217), reported on RB as
        INCONSISTENT_PAIR (code 2)."""
        srv.handle_init()
        srv.handle_set_params({"MODELG": 2, "RR": 0.7, "RA": 0.18, "RKAP": 1.9,
                               "RDLT": 0.4, "BB": 0.3, "RIP": 0.04})
        diags = srv.handle_validate()
        self.assertEqual([(d["param"], d["code"]) for d in diags], [("RB", 2)], diags)
        self.assertIn("reaches R <= 0", diags[0]["message"])
```

- [ ] **Step 2: Run it**

Run: the test command on `python/mcp-servers/eq_mcp/tests/test_server.py -k grid_that_reaches`.
Expected: PASS (Task 3's build). If the keys of a diagnostic dict differ, read `handle_validate` and use its keys.

- [ ] **Step 3: Commit** `git add python/mcp-servers/eq_mcp/tests/test_server.py` with
"test(eq_mcp): validate names a grid that reaches R <= 0 (task-web-client #217)".

---

### Task 5: EQAXIS's message: failing tests

**Files:** Modify: `python/eqlib/tests/test_load_errors.py` (after `test_an_analytic_solve_whose_axis_leaves_the_box_says_so`).

- [ ] **Step 1: Add the tests**

```python
import re

_IN_LOOP = re.compile(
    r"^EQAXIS: in iteration (\d+) of the solve the magnetic axis search ended at "
    r"\(R, Z\) = \((-?\d+\.\d{4}), (-?\d+\.\d{4})\), (\d\.\dE[-+]\d\d) below RGMIN = (\d+\.\d{4}): "
    r"the axis moves from \(RR, 0\) as the solve goes on, and the box \(MDLEQF >= 10\) "
    r"must hold its path \(ierr=103\)$")


def _analytic_failure(**params):
    with eqlib.Eq() as e:
        e.set_params(MODELG=2, **params)
        with pytest.raises(eqlib.EqlibCalculationFailedError) as err:
            e.run(0)
        return str(err.value), e.last_error()


def test_an_axis_that_triangularity_moves_out_of_the_box_names_the_iteration():
    # tw#188: RR = RGMIN + 0.03 at RDLT 0.4; the axis starts inside and leaves on the way.
    message, last = _analytic_failure(MDLEQF=10, RDLT=0.4, RGMIN=2.97)
    m = _IN_LOOP.match(last)
    assert m, last
    assert int(m.group(1)) >= 2
    assert m.group(5) == "2.9700"
    assert float(m.group(4)) == pytest.approx(2.97 - float(m.group(2)), abs=1e-4)
    assert len(last) <= 255 and "unprintable" not in last
    assert message.endswith(last)


def test_an_axis_that_ends_inside_but_leaves_on_the_way_names_the_iteration():
    # tw#188: at RDLT 0.2 the axis ends at 3.0219 with the default box, yet RGMIN 3.0 fails.
    _, last = _analytic_failure(MDLEQF=10, RDLT=0.2, RGMIN=3.0)
    m = _IN_LOOP.match(last)
    assert m and int(m.group(1)) >= 2 and m.group(5) == "3.0000", last


def test_an_axis_within_rounding_of_zgmax_0_says_by_how_much():
    # tw#214: the axis ends about 1e-12 above ZGMAX = 0; F16.4 prints both as 0.0000.
    _, last = _analytic_failure(MDLEQF=10, ZGMAX=0.0)
    m = re.search(r"\(R, Z\) = \(\d+\.\d{4}, -?0\.0000\)(?:, (\d\.\dE[-+]\d\d) above ZGMAX)?", last)
    assert m, last
    if "in iteration" in last:
        assert "above ZGMAX = 0.0000:" in last, last
    else:
        assert m.group(1) is not None, last
        assert "ZGMIN..ZGMAX = [-2.0000, 0.0000] that MDLEQF >= 10 holds the axis to (ierr=103)" in last
    assert 0.0 < float(re.search(r"(\d\.\dE[-+]\d\d) above ZGMAX", last).group(1)) < 1e-6
```

And add to the two existing tests one line each:
in `test_a_load_whose_axis_lies_outside_the_box_says_so`: `assert ", 1.1E+00 below RGMIN, outside the box" in message`
(TST-2's axis about 0.39 m against RGMIN 1.5: read the actual value in Step 2's failure output and write the digits
it shows, two significant digits);
in `test_an_analytic_solve_whose_axis_leaves_the_box_says_so`: `assert "), 1.0E-03 below RGMIN, outside the box" in message`.

- [ ] **Step 2: Run and see them fail**

Run: the test command on `python/eqlib/tests/test_load_errors.py`.
Expected: the three new tests and the two extended ones FAIL (today's message has no clause and no iteration); the
rest pass.

---

### Task 6: EQAXIS's message: the implementation

**Files:** Modify: `eq/eqcom1_mod.f90`, `eq/eqcalc.f90` (EQLOOP), `eq/eqsub.f90` (EQAXIS).

- [ ] **Step 1: `eq/eqcom1_mod.f90`**, after `CHARACTER(LEN=256) :: EQ_ERRMSG = ' '`, with its comment lines added to
the block above:

```fortran
  !   EQ_NLOOP: the iteration of EQLOOP running (1..NLPMAX), 0 outside
  !     it; EQLOOP sets it and puts it back to 0 on every way out, and
  !     EQAXIS reads it for its message (task-web-client #188).
  INTEGER :: EQ_NLOOP = 0
```

- [ ] **Step 2: EQLOOP (`eq/eqcalc.f90`)**

```fortran
      DO NLOOP=1,NLPMAX
         EQ_NLOOP=NLOOP
         CALL EQBAND
         CALL EQRHSV(IERR)
         IF(IERR.NE.0) THEN
            EQ_NLOOP=0
            RETURN
         ENDIF
```

and `EQ_NLOOP=0` before the `RETURN` of the convergence branch (`IF(SUML.LT.EPSEQ) THEN ... RETURN`) and right after
`ENDDO` (before the `NLPMAX` message).

- [ ] **Step 3: EQAXIS (`eq/eqsub.f90`)**: declarations after `CHARACTER(LEN=16) :: KV(6)`:

```fortran
      CHARACTER(LEN=8)  :: KBN(4)
      CHARACTER(LEN=16) :: KD, KBV, KN
      CHARACTER(LEN=24) :: KBE
      CHARACTER(LEN=48) :: KC
      INTEGER :: IB, IOSD
      REAL(rkind) :: DB, BV
```

and replace the message part, from `WRITE(KV,'(F16.4)') RAXIS,ZAXIS,RMIN,RMAX,ZMIN,ZMAX` through the
`IF(IOS.NE.0) EQ_ERRMSG= ...` fallback, with:

```fortran
!        The bound the point crossed and by how much (task-web-client
!        #214: at ZGMAX = 0 the axis ends about 1e-12 above it, which
!        F16.4 prints as 0.0000), and inside EQLOOP the iteration
!        (EQ_NLOOP, #188): from the second on the axis is the solve's,
!        which moves from (RR, 0), so the window must hold its path.
         IF(MDLEQF.LT.10) THEN
            KBN(1)='RR-RB'
            KBN(2)='RR+RB'
            KBN(3)='-RKAP*RB'
            KBN(4)='RKAP*RB'
         ELSE
            KBN(1)='RGMIN'
            KBN(2)='RGMAX'
            KBN(3)='ZGMIN'
            KBN(4)='ZGMAX'
         ENDIF
         IB=0
         IF(RAXIS.LT.RMIN) THEN
            IB=1
            DB=RMIN-RAXIS
            BV=RMIN
         ELSE IF(RAXIS.GT.RMAX) THEN
            IB=2
            DB=RAXIS-RMAX
            BV=RMAX
         ELSE IF(ZAXIS.LT.ZMIN) THEN
            IB=3
            DB=ZMIN-ZAXIS
            BV=ZMIN
         ELSE IF(ZAXIS.GT.ZMAX) THEN
            IB=4
            DB=ZAXIS-ZMAX
            BV=ZMAX
         ENDIF
         KC=' '
         KBE=' '
         IF(IB.GT.0) THEN
            WRITE(KD,'(ES8.1)',IOSTAT=IOSD) DB
            IF(IOSD.EQ.0) WRITE(KBV,'(F16.4)',IOSTAT=IOSD) BV
            IF(IOSD.EQ.0) THEN
               IF(MOD(IB,2).EQ.1) THEN
                  KC=', '//TRIM(ADJUSTL(KD))//' below '//TRIM(KBN(IB))
               ELSE
                  KC=', '//TRIM(ADJUSTL(KD))//' above '//TRIM(KBN(IB))
               ENDIF
               KBE=' = '//TRIM(ADJUSTL(KBV))
            ENDIF
         ENDIF
         WRITE(KV,'(F16.4)') RAXIS,ZAXIS,RMIN,RMAX,ZMIN,ZMAX
         WRITE(KN,'(I0)') EQ_NLOOP
         IF(EQ_NLOOP.GE.2.AND.MDLEQF.GE.10) THEN
            WRITE(EQ_ERRMSG,'(16A)',IOSTAT=IOS) &
                 'EQAXIS: in iteration ',TRIM(KN), &
                 ' of the solve the magnetic axis search ended at (R, Z) = (', &
                 TRIM(ADJUSTL(KV(1))),', ',TRIM(ADJUSTL(KV(2))),')', &
                 TRIM(KC),TRIM(KBE), &
                 ': the axis moves from (RR, 0) as the solve goes on,'// &
                 ' and the box (MDLEQF >= 10) must hold its path', &
                 ' (ierr=103)'
         ELSE IF(EQ_NLOOP.GE.2) THEN
            WRITE(EQ_ERRMSG,'(16A)',IOSTAT=IOS) &
                 'EQAXIS: in iteration ',TRIM(KN), &
                 ' of the solve the magnetic axis search ended at (R, Z) = (', &
                 TRIM(ADJUSTL(KV(1))),', ',TRIM(ADJUSTL(KV(2))),')', &
                 TRIM(KC),TRIM(KBE), &
                 ', outside RR -/+ RB, -/+ RKAP*RB (MDLEQF < 10)', &
                 ' (ierr=103)'
         ELSE IF(MDLEQF.LT.10) THEN
            WRITE(EQ_ERRMSG,'(16A)',IOSTAT=IOS) &
                 'EQAXIS: the search for the magnetic axis ended at'// &
                 ' (R, Z) = (',TRIM(ADJUSTL(KV(1))),', ', &
                 TRIM(ADJUSTL(KV(2))),')',TRIM(KC),', outside RR -/+ RB = [', &
                 TRIM(ADJUSTL(KV(3))),', ',TRIM(ADJUSTL(KV(4))), &
                 '], -/+ RKAP*RB = [',TRIM(ADJUSTL(KV(5))),', ', &
                 TRIM(ADJUSTL(KV(6))),'] (MDLEQF < 10) (ierr=103)'
         ELSE
            WRITE(EQ_ERRMSG,'(16A)',IOSTAT=IOS) &
                 'EQAXIS: the search for the magnetic axis ended at'// &
                 ' (R, Z) = (',TRIM(ADJUSTL(KV(1))),', ', &
                 TRIM(ADJUSTL(KV(2))),')',TRIM(KC),', outside the box'// &
                 ' RGMIN..RGMAX = [',TRIM(ADJUSTL(KV(3))),', ', &
                 TRIM(ADJUSTL(KV(4))),'], ZGMIN..ZGMAX = [', &
                 TRIM(ADJUSTL(KV(5))),', ',TRIM(ADJUSTL(KV(6))), &
                 '] that MDLEQF >= 10 holds the axis to (ierr=103)'
         ENDIF
         IF(IOS.NE.0) EQ_ERRMSG= &
              'EQAXIS: the search for the magnetic axis ended outside'// &
              ' the window it is held to (values unprintable) (ierr=103)'
```

Every `WRITE` has `(16A)`, at least its items (11, 11, 15 and 15 as written): more items than `A`s would revert the
format to a second record, an `IOSTAT` error at run time that only shows as the fallback message. `USE eqcom1_mod` is already in EQAXIS; `rkind` comes from `plcomm`. Keep
`WRITE(6,'(2A)') '   ',TRIM(EQ_ERRMSG)`, `IERR=103` and `RETURN` after it.

- [ ] **Step 4: Build and run Task 5's tests**

Run: `$B make -C eq libeqapi.so` (check `eqsub.o`, `eqcalc.o` and `eqcom1_mod.o` are newer than their sources), then
the test command on `python/eqlib/tests/test_load_errors.py python/eqlib/tests/test_validate.py`.
Expected: all pass. If the TST-2 clause's digits differ from Step 5.1's guess, write the measured digits.

- [ ] **Step 5: A case for `MDLEQF < 10` in the loop**

Try, one process each, `MDLEQF=0` with `RB` in (0.2, 0.3, 0.5) and `RA` 1.0 (wall inside the plasma), and
`Q0=-1, QA=3, MDLEQF=4`; print `last_error()`. If one fails with ierr=103 in iteration >= 2, add a test that it
matches the `MDLEQF < 10` in-loop form; if none does, record "no input found for the MDLEQF < 10 in-loop form" in the
commit message and the pull request (the form is reviewed, not tested).

- [ ] **Step 6: Mutations, each seen to fail**

(a) `IF(EQ_NLOOP.GE.2.AND.MDLEQF.GE.10) THEN` -> `IF(.FALSE.) THEN`: the two iteration tests fail;
(b) in EQLOOP delete `EQ_NLOOP=NLOOP`: the two iteration tests fail;
(c) swap `' below '` and `' above '`: the clause tests fail;
(d) in EQLOOP delete the `EQ_NLOOP=0` after `ENDDO` and before the convergence `RETURN`: run
`test_a_load_whose_axis_lies_outside_the_box_says_so` after a solve in the same process. If no test fails, add one:
`run(0)` of the defaults, then a `MODELG=3` TST-2 load with `MDLEQF=10` in the same `Eq`; its message must be the
box form (no "in iteration").
Restore and rebuild after each.

- [ ] **Step 7: Commit**

```bash
git add eq/eqcom1_mod.f90 eq/eqcalc.f90 eq/eqsub.f90 python/eqlib/tests/test_load_errors.py
git commit -m "fix(eq): EQAXIS says which bound the axis crossed, by how much, and in which iteration (task-web-client #188, #214)" \
  -m "Body: the four forms and their longest lengths (244, 196, 242, 211), TR's 222-character record, the mutations seen to fail, what Step 5 found for MDLEQF < 10." \
  -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Rebuild everything and compare the results

- [ ] **Step 1: Clean rebuild of all seven libraries, EQU and the C checks** (background, ~4 min)

```bash
cd ~/task-web-scratch/equ-api/task && ( $B FC=/opt/homebrew/bin/gfortran bash -c 'set -e; for m in eq tr fp ti wr wrx tot equ pl dp ob; do make -C $m clean_pic >/dev/null 2>&1 || true; done; ~/Research_Project/MS10/TASK/task-web/.claude/worktrees/great-goodall-ac7c77/scripts/build_fortran.sh "$PWD" ~/task-web-scratch/equ-api/bpsd; make -C pl libpl_pic.a; make -C dp libdp_pic.a; make -C ob libob_pic.a; make -C open-adas/adf11/adf11-lib lib-adf11_pic.a; make -C adpost lib-adpost_pic.a; for m in ti wr wrx; do make -C $m bpsd_pic; make -C $m lib${m}api.so; done; make -C tot libtotapi.so; make -C tot libtotapi_mono.so; make -C equ libequapi.so equ_nogr; make -C equ equ_api_check_all; make -C eq eq_api_check_so' > ../build-eqgroup.log 2>&1; echo "exit $?" >> ../build-eqgroup.log )
```

Expected: `exit 0`; `eq_api_check_so` OK.

- [ ] **Step 2: The results after**

Run: `/opt/anaconda3/envs/task/bin/python -I tools/eqgroup_digest.py ~/task-web-scratch/equ-api/task runs/eqgroup-after.json`
then `diff runs/eqgroup-before.json runs/eqgroup-after.json`.
Expected: no difference (every scalar's `repr` and the grid ends identical).

---

### Task 8: Documents

**Files:** `docs/sphinx/modules/eq/en/parameter-setting.md` and `ja/parameter-setting.md`, `faq.md` (en, ja),
`design.md` (en, ja), `CHANGELOG.md`.

- [ ] **Step 1: `parameter-setting.md` (en)**: after the bullet "- the wall encloses the plasma: `RB >= RA`
(`INCONSISTENT_PAIR`);" add "- the grid `RR -/+ RB` stays at R > 0: `RB < RR` (`INCONSISTENT_PAIR`; with `RB >= RR`
the run goes on, and its result depends on `RB`);". In "Two failures are not seen before the run: the axis moves
during the solve (...)", add after that sentence: "When the axis leaves the box, the run's error says which bound it
crossed, by how much, and, from the second iteration of the solve on, in which iteration." The same two changes in
`ja/parameter-setting.md` (Japanese: 「- グリッド `RR -/+ RB` が R > 0 に収まる: `RB < RR` (`INCONSISTENT_PAIR`; `RB >= RR` でも実行は進むが, 結果が `RB` に依存する);」 and 「磁軸が箱の外に出たとき, 実行のエラーは越えた境界とその量, 解法の 2 回目以降の反復ではその反復回数を示す.」).
- [ ] **Step 2: `faq.md` Q5 (en)**: "a wall inside the plasma" -> "a wall inside the plasma or a grid reaching R <= 0";
ja likewise (read the ja sentence and add 「, R <= 0 に達するグリッド」 after its wall item).
- [ ] **Step 3: `design.md` (en, ja)**: in the `eq_validate` row, "the wall" -> "the wall and its grid (`RB >= RA`,
`RB < RR`)" (ja: the same in its row).
- [ ] **Step 4: CHANGELOG**: under `## [Unreleased]` / `### Fixed`, an entry:

```markdown
- **EQ: the axis search's message and a grid that reaches R <= 0** (task-web-client #188, #214, #217). When the magnetic
  axis leaves its window, `eq_last_error` says which bound it crossed and by how much (`1.0E-12 above ZGMAX`: at
  `ZGMAX = 0` both used to print as `0.0000`) and, from the solve's second iteration on, in which iteration, with the
  reason (the axis moves from `(RR, 0)` as the solve goes on, so with `MDLEQF >= 10` the box must hold its path).
  `validate()` reports, on `RB` as `INCONSISTENT_PAIR`, an analytic solve whose grid `RR -/+ RB` reaches R <= 0
  (`RB >= RR`: PLATO with the default wall). No result changes (ten cases bit-identical before and after).
```

- [ ] **Step 5: Build the pages**: `cd docs/sphinx && for l in en ja; do ~/task-web-scratch/equ-api/sphinx-venv/bin/sphinx-build -q -b html modules/eq/$l /private/tmp/claude-501/-Users-lihengyu-Research-Project-MS10-TASK-task-web--claude-worktrees-great-goodall-ac7c77/c80430a8-f8d4-4593-b853-eb31ea1b195b/scratchpad/equ/_build/eq/$l; done`.
Expected: no warning but the existing `_static` one.
- [ ] **Step 6: Commit** the six pages and the CHANGELOG: "docs(eq): validate()'s grid check and the axis search's
message (task-web-client #188, #214, #217)".

---

### Task 9: The full suite, the reviews, the merge and the ledger row

- [ ] **Step 1: Full suite** (background, ~10 min) with the CI flags:
`env -u MONO_LIB_PATH PYTHONPATH=python:python/mcp-servers /opt/anaconda3/envs/task/bin/python -m pytest python/ test_run/scripts/tests --forked --timeout=120 --timeout-method=signal --tb=short -ra --maxfail=50 -p no:cacheprovider -q > ../full-suite-eqgroup.log 2>&1`.
Expected: 0 failed; the passed count is the base's (2970 at `09386579`'s code, plus #38's merge) plus the new tests.
A test elsewhere that asserted `validate() == []` for an analytic case with `RB >= RR`, or today's EQAXIS wording,
fails here: read it, and change the test only if its input really has `RB >= RR` (say so in the commit).
- [ ] **Step 2: In-house review** (`superpowers:code-reviewer`, read-only brief) of `git diff 44a0d010..HEAD`; fix
HIGH/MED, rerun what they touch.
- [ ] **Step 3: Codex review** only with the author's OK (paid): `codex exec -m gpt-6.2-astra -c model_reasoning_effort=xhigh --sandbox read-only < prompt`.
- [ ] **Step 4: Merge `kyoshimi-develop`** if it moved (`git fetch origin; git merge --no-ff origin/kyoshimi-develop`),
rebuild what changed, rerun the suite if Fortran or Python changed.
- [ ] **Step 5: Row AG** of `docs/product-line/upstream-status.md` (next free letter after the last row: check), its
heading list, the paragraph on open pull requests and the summary count; product-only as cut; the questions for the
lead (RB following RA). Commit last.
- [ ] **Step 6: Push and open the pull request** with the author's go-ahead: marker
`touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"`, `git push -u origin fix/eq-validate-group`,
`gh pr create -R HengyuLi-Ozaki-lab/task --base kyoshimi-develop --head fix/eq-validate-group --label product-only`;
bind it; the CI line after the run.
