# L-7b-i External Driven Current Scalar — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the L-7a skeleton coupling (`PLHCD` as MA-magnitude carrier) with a physically meaningful `EXTERNAL_DRIVEN_I` scalar [MA] injected via Gaussian profile into AJRF, plus AJRFT C ABI exposure for integration verification, plus `tr_api_validate` extension for the `RW=0 + I!=0` misconfiguration case.

**Architecture:** Add 3 scalars to `tr/trcomm_param.f90` (`EXTERNAL_DRIVEN_I/R0/RW`); register in `tr_param_registry.f90`; default in `trinit.f90`; inject Gaussian additively into `AJRF(NR)` in `trprf.f90`'s `TRPWRF` (default I=0 → no-op → backward compat). Expose `AJRFT` (already computed in trrslt_globals) via `tr_api_get_state` + `tr_state_c` struct + C header. Update Python `pipeline.py` `COUPLING_RULES` to use `EXTERNAL_DRIVEN_I`. Single PR, 3 commit, feature branch flow per handoff 2026-05-02 §C.

**Tech Stack:** Fortran (gfortran, free-form F90), Python 3.10+ (ctypes), pytest with `--forked --timeout=120 --timeout-method=signal`. macOS local build needs `make -C tot tot GFLIBS=""` override (Linux CI defaults to empty).

**Spec:** `docs/superpowers/specs/2026-05-02-l7b-i-external-driven-i-design.md` (commit 26c2bc44)

**PR phases (= 3 commit boundaries):**
- Phase 1 — Commit 1: Fortran scalar add + AJRFT C ABI exposure + Python state.py mapping
- Phase 2 — Commit 2: pipeline.py rewrite + existing test_pipeline*.py update
- Phase 3 — Commit 3: New test_external_driven_i.py + README updates
- Phase 4 — Pre-push gate (CLAUDE.md): pytest sweep, reviewer agents (parallel), REVIEW_OK marker, feature branch push, PR open

---

## Phase 0 — Setup feature branch

### Task 0.1: Create feature branch

**Files:** none (git only)

- [ ] **Step 1: Verify clean working tree on chore branch**

```bash
git status
```

Expected: only untracked files from handoff list (`.worktrees/`, `docs/doc-design/`, `docs/slides/`, `python/mcp-servers/tr_mcp/setup_cli.py`, etc.). No modified tracked files.

- [ ] **Step 2: Verify chore branch tip matches handoff**

```bash
git log --oneline -3
```

Expected first line: `26c2bc44 docs(spec): add L-7b-i external driven current scalar design`

- [ ] **Step 3: Create and switch to feature branch**

```bash
git checkout -b claude/2026-05-02-l7b-i-external-driven-i
```

Expected: `Switched to a new branch 'claude/2026-05-02-l7b-i-external-driven-i'`

---

## Phase 1 — Fortran scalar add + AJRFT C ABI exposure

**Goal of phase:** introduce 3 new scalars and AJRFT exposure, with default I=0 → AJRF unchanged → all existing tests pass at 1e-10. End of phase: `make -C tr libtrapi.so` succeeds and existing trlib tests pass.

### Task 1.1: Declare 3 scalars in trcomm_param.f90

**Files:**
- Modify: `tr/trcomm_param.f90`

- [ ] **Step 1: Read existing PLHCD declaration block to confirm pattern**

```bash
sed -n '32,42p' tr/trcomm_param.f90
```

Expected lines include:

```fortran
  REAL(rkind)   :: &
       TPRST, PBSCD, &
       PNBTOT, ..., PLHCD, PLHTOE, PLHNPR, ...
```

- [ ] **Step 2: Add 3 new scalars to the model parameters block**

Append a new declaration block right before `INTEGER:: number_of_pellet_repeat` (line 42 area). Use the Edit tool to add after line 41 (which is `ELMWID, ELMDUR`):

```fortran
       ELMWID, ELMDUR, &
! L-7b-i: external user-supplied driven current (Gaussian profile, MA).
! Distinct from PLHCD/PECCD/PICCD: bypasses TRCDEF efficiency model — the
! given current is injected directly with a Gaussian radial shape rather
! than computed from RF wave power × efficiency.
       EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_R0, EXTERNAL_DRIVEN_RW
```

(Alternative: add a new `REAL(rkind) :: EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_R0, EXTERNAL_DRIVEN_RW` block after line 41. Either works; choose whatever the existing file style preserves. Use Edit tool, not Write.)

- [ ] **Step 3: Verify file still parses (syntax sanity)**

```bash
grep -nE "EXTERNAL_DRIVEN_I|EXTERNAL_DRIVEN_R0|EXTERNAL_DRIVEN_RW" tr/trcomm_param.f90
```

Expected: 3 hits (one per scalar, in your inserted block).

- [ ] **Step 4: Commit (will be amended into final commit 1 later, but commit incrementally)**

```bash
git add tr/trcomm_param.f90
git commit -m "tr: declare EXTERNAL_DRIVEN_I/R0/RW scalars (L-7b-i)"
```

### Task 1.2: Set defaults in trinit.f90

**Files:**
- Modify: `tr/trinit.f90` around line 502 (between IC block end and CURRENT DRIVE PARAMETERS block start)

- [ ] **Step 1: Read context around insertion point**

```bash
sed -n '498,508p' tr/trinit.f90
```

Expected: lines showing `PICCD = 0.D0`, `MDLIC = 0` (line 502), then comment block `==== CURRENT DRIVE PARAMETERS ====` (line 504).

- [ ] **Step 2: Insert new "EXTERNAL DRIVEN CURRENT" block**

Use Edit tool to add after line 502 (after `MDLIC = 0`) and before line 504:

```fortran

!     ==== EXTERNAL DRIVEN CURRENT (L-7b-i) ====

!        EXTERNAL_DRIVEN_I  : USER-SUPPLIED TOTAL DRIVEN CURRENT (MA)
!        EXTERNAL_DRIVEN_R0 : GAUSSIAN PROFILE CENTER (NORMALIZED RHO)
!        EXTERNAL_DRIVEN_RW : GAUSSIAN PROFILE WIDTH  (NORMALIZED RHO)

      EXTERNAL_DRIVEN_I  = 0.D0
      EXTERNAL_DRIVEN_R0 = 0.D0
      EXTERNAL_DRIVEN_RW = 0.3D0
```

- [ ] **Step 3: Verify defaults are present**

```bash
grep -nE "EXTERNAL_DRIVEN_(I|R0|RW)\s*=" tr/trinit.f90
```

Expected: 3 hits.

- [ ] **Step 4: Commit**

```bash
git add tr/trinit.f90
git commit -m "tr: default EXTERNAL_DRIVEN_I=0, R0=0, RW=0.3 (L-7b-i)"
```

### Task 1.3: Add 3 CASEs to tr_param_registry.f90

**Files:**
- Modify: `tr/tr_param_registry.f90`

- [ ] **Step 1: Read USE clause and PLHCD CASE for context**

```bash
grep -n "PLHCD" tr/tr_param_registry.f90
```

Expected: 2 hits — one in USE statement (line 55), one as `CASE ("PLHCD"); PLHCD = value` (line 159).

- [ ] **Step 2: Add 3 new symbols to USE clause**

Edit the USE clause (line 50-65 area). Find the line containing `PLHCD,` and add 3 new symbols on a continuation line. Example: change

```fortran
       PLHCD, PLHR0, PLHRW, PLHNPR, PLHTOT, &
```

to

```fortran
       PLHCD, PLHR0, PLHRW, PLHNPR, PLHTOT, &
       EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_R0, EXTERNAL_DRIVEN_RW, &
```

(Keep the trailing `&` and ensure the next line still chains correctly. Use Edit tool, not Write.)

- [ ] **Step 3: Add 3 CASEs after `CASE ("PLHCD")` line 159**

Find line 159 (`CASE ("PLHCD"); PLHCD = value`) and add 3 lines below it:

```fortran
    CASE ("PLHCD");  PLHCD  = value
    CASE ("EXTERNAL_DRIVEN_I");  EXTERNAL_DRIVEN_I  = value
    CASE ("EXTERNAL_DRIVEN_R0"); EXTERNAL_DRIVEN_R0 = value
    CASE ("EXTERNAL_DRIVEN_RW"); EXTERNAL_DRIVEN_RW = value
```

- [ ] **Step 4: Verify both USE and CASE are present**

```bash
grep -nE "EXTERNAL_DRIVEN_I|EXTERNAL_DRIVEN_R0|EXTERNAL_DRIVEN_RW" tr/tr_param_registry.f90
```

Expected: 6 hits (3 in USE, 3 in CASE).

- [ ] **Step 5: Commit**

```bash
git add tr/tr_param_registry.f90
git commit -m "tr: register EXTERNAL_DRIVEN_I/R0/RW in tr_param_set (L-7b-i)"
```

### Task 1.4: Build libtrapi.so to verify Fortran additions compile

**Files:** none (build only)

- [ ] **Step 1: Build tr static + shared libs**

```bash
make -C tr clean 2>&1 | tail -5
make -C tr libtrapi.so 2>&1 | tail -20
```

Expected: build succeeds, no errors. The new symbols compile cleanly.

- [ ] **Step 2: Sanity check libtrapi.so symbol presence**

```bash
nm tr/libtrapi.so 2>/dev/null | grep -i "tr_set_param" | head
```

Expected: `tr_set_param` symbol present (= the registry path is exported). EXTERNAL_DRIVEN_* are reached via this symbol; no separate symbols.

- [ ] **Step 3: Run existing trlib tests to confirm no regression**

```bash
PYTHONPATH=python python3 -m pytest --timeout=60 python/trlib/tests/ 2>&1 | tail -3
```

Expected: all existing tests PASS (we haven't changed semantics; default I=0).

### Task 1.5: Inject Gaussian into AJRF in trprf.f90

**Files:**
- Modify: `tr/trprf.f90` (USE clause line 9-11, TRPWRF subroutine body around line 124)

- [ ] **Step 1: Read TRPWRF subroutine declaration block to find local var insertion point**

```bash
sed -n '5,30p' tr/trprf.f90
```

Note: USE clause starts at line 9. Local variables likely declared just before the executable code.

- [ ] **Step 2: Add 4 symbols to USE clause**

Edit the USE clause to add `DSRHO`, `RM`, and 3 EXTERNAL_DRIVEN_* (DVRHO already in). Example: append at the end:

```fortran
      USE TRCOMM, ONLY : AJRF, AJRFV, AME, DR, DVRHO, EPSRHO, NRMAX, PECCD, PECNPR, PECR0, PECRW, PECTOE, PECTOT, PICCD, &
     &                   PICNPR, PICR0, PICRW, PICTOE, PICTOT, PLHCD, PLHNPR, PLHR0, PLHRW, PLHTOE, PLHTOT, PRF, PRFV,   &
     &                   ..., RA, &
     &                   RM, DSRHO, EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_R0, EXTERNAL_DRIVEN_RW
```

(Read existing USE first to get the exact symbol list and continuation style.)

- [ ] **Step 3: Add SUM_EXT local variable**

In the subroutine declaration block (after USE, before executables), find an existing `REAL(rkind) ::` declaration line for locals and add:

```fortran
      REAL(rkind) :: SUM_EXT
```

Or extend an existing declaration block.

- [ ] **Step 4: Add Gaussian injection block at end of AJRF DO loop**

Find the end of the existing `DO NR = 1, NRMAX ... AJRF(NR) = ... ENDDO` block (line ~124-125). After the `ENDDO`, add:

```fortran
! ----- L-7b-i: external driven current (scalar API, Gaussian profile) -----
! AJRFT [MA] = SUM(AJRF * DSRHO * DR) / 1.D6  (per trrslt_globals.f90:240)
! Choose AJ_ext(NR) such that SUM(AJ_ext * DSRHO * DR) = EXTERNAL_DRIVEN_I * 1.D6 [A]
! → Total contribution to AJRFT becomes EXTERNAL_DRIVEN_I [MA] exactly.
!
! Outer guard: skip when I=0 (default → no-op, backward compatible) OR when
! RW<=0 (silent: tr_api_validate surfaces this misconfiguration via OUT_OF_RANGE).
      IF (EXTERNAL_DRIVEN_I /= 0.D0 .AND. EXTERNAL_DRIVEN_RW > 0.D0) THEN
         SUM_EXT = 0.D0
         DO NR = 1, NRMAX
            SUM_EXT = SUM_EXT + DEXP(-((RM(NR) - EXTERNAL_DRIVEN_R0) &
                                       / EXTERNAL_DRIVEN_RW)**2) &
                                * DSRHO(NR) * DR
         END DO
         ! Inner guard: numerical safety net for extreme RW pushing the
         ! Gaussian entirely outside the plasma.
         IF (SUM_EXT > 0.D0) THEN
            DO NR = 1, NRMAX
               AJRF(NR) = AJRF(NR) + EXTERNAL_DRIVEN_I * 1.D6 &
                          * DEXP(-((RM(NR) - EXTERNAL_DRIVEN_R0) &
                                   / EXTERNAL_DRIVEN_RW)**2) &
                          / SUM_EXT
            END DO
         END IF
      END IF
```

- [ ] **Step 5: Build to verify compilation**

```bash
make -C tr libtrapi.so 2>&1 | tail -10
```

Expected: builds. If you get "Symbol RM unresolved" or similar, you missed adding RM to the USE clause — go back to step 2.

- [ ] **Step 6: Verify default-zero backward compat**

```bash
PYTHONPATH=python python3 -m pytest --timeout=60 python/trlib/tests/ 2>&1 | tail -3
```

Expected: all PASS at the same numeric values as before (since EXTERNAL_DRIVEN_I=0 default → block skipped).

- [ ] **Step 7: Commit**

```bash
git add tr/trprf.f90
git commit -m "tr: inject EXTERNAL_DRIVEN_I via Gaussian into AJRF (L-7b-i)"
```

### Task 1.6: Add AJRFT to tr_state_c struct

**Files:**
- Modify: `tr/tr_state.f90` (struct end at line ~67)

- [ ] **Step 1: Read struct end block to confirm insertion point**

```bash
sed -n '60,70p' tr/tr_state.f90
```

Expected last lines: `REAL(C_DOUBLE) :: AJ(TR_MAX_NRMAX)`, `REAL(C_DOUBLE) :: QP(TR_MAX_NRMAX)`, `END TYPE tr_state_c`.

- [ ] **Step 2: Add AJRFT field at struct end (just before END TYPE tr_state_c)**

Edit to insert before `END TYPE tr_state_c`:

```fortran
     REAL(C_DOUBLE)  :: QP(TR_MAX_NRMAX)
     ! L-7b-i: total RF + external driven current [MA] (sum into AJRFT global,
     ! includes the new EXTERNAL_DRIVEN_I contribution from trprf).
     REAL(C_DOUBLE)  :: AJRFT
  END TYPE tr_state_c
```

- [ ] **Step 3: Verify struct field added**

```bash
grep -A2 "AJ(TR_MAX_NRMAX)" tr/tr_state.f90 | head -8
```

Expected: shows AJ → QP → comment → AJRFT → END TYPE.

- [ ] **Step 4: Commit**

```bash
git add tr/tr_state.f90
git commit -m "tr: add AJRFT to tr_state_c struct (L-7b-i)"
```

### Task 1.7: Sync C header tr_api.h

**Files:**
- Modify: `tr/tr_api.h` (struct end around line 43)

- [ ] **Step 1: Read C struct definition**

```bash
sed -n '35,45p' tr/tr_api.h
```

Expected: `typedef struct { ... double AJ[...]; double QP[...]; } tr_state_t;`

- [ ] **Step 2: Add `double AJRFT;` at struct end (before `} tr_state_t;`)**

Use Edit to insert:

```c
    double AJ[TR_MAX_NRMAX];
    double QP[TR_MAX_NRMAX];
    /* L-7b-i: total RF + external driven current [MA]. Mirrors AJRFT in
       tr_state_c; offset must match. */
    double AJRFT;
} tr_state_t;
```

- [ ] **Step 3: Verify header parses (compile any small consumer)**

```bash
make -C tr clean && make -C tr libtrapi.so 2>&1 | tail -5
```

Expected: build succeeds. Any C drivers that include tr_api.h will pick up the new field at the END (no offset changes for existing fields).

- [ ] **Step 4: Commit**

```bash
git add tr/tr_api.h
git commit -m "tr: add AJRFT to tr_state_t C header (L-7b-i)"
```

### Task 1.8: Wire AJRFT into tr_api_get_state + add validate check

**Files:**
- Modify: `tr/tr_api.f90` (USE clause line 33-37, get_state body line 217-303, validate body line 381-465)

- [ ] **Step 1: Add AJRFT and EXTERNAL_DRIVEN_* to USE clause**

Edit USE statement (line 33-37). Add `AJRFT` after `RQ1`. Add `EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_RW` to the bottom of the USE list:

```fortran
  USE trcomm,   ONLY: rkind, &
       NRMAX, NSMAX, NT, T, NTMAX, MODELG, KNAMEQ, &
       WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN, &
       TAUE1, TAUE2, ZEFF0, ALI, RQ1, RN, RT, AJ, QP, &
       AJRFT, &
       EXTERNAL_DRIVEN_I, EXTERNAL_DRIVEN_RW, &
       ALLOCATE_TRCOMM, DEALLOCATE_TRCOMM
```

- [ ] **Step 2: Add zero-init for state%AJRFT in tr_api_get_state**

Find the zero-init block (line ~262-279, where `state%nt = 0` etc. live). Add:

```fortran
    state%RQ1    = 0.0_C_DOUBLE
    state%AJRFT  = 0.0_C_DOUBLE      ! L-7b-i
    state%RN     = 0.0_C_DOUBLE
```

- [ ] **Step 3: Add populate for state%AJRFT in tr_api_get_state**

Find the populate block (line ~295-310). Add after `state%RQ1 = RQ1`:

```fortran
    state%RQ1    = RQ1
    state%AJRFT  = AJRFT             ! L-7b-i: includes EXTERNAL_DRIVEN_I contribution
```

- [ ] **Step 4: Add validate check in tr_api_validate**

Find the existing FILE_MISSING KNAMEQ check (line ~407-412). Add after the END IF of that check:

```fortran
       IF (LEN_TRIM(KNAMEQ) == 0) THEN
          CALL push_diag("KNAMEQ", TR_DIAG_FILE_MISSING, &
               "MODELG=3/5/7/8 requires non-blank KNAMEQ (eq/VMEC file)")
       END IF
    END IF

    ! ---- OUT_OF_RANGE: EXTERNAL_DRIVEN_I requires positive width. -------
    ! Non-zero I with non-positive RW would silently normalize to zero in
    ! trprf, leaving AJRF unchanged. Surface this so callers know their
    ! setting was no-op rather than physically applied.
    IF (EXTERNAL_DRIVEN_I /= 0.D0 .AND. EXTERNAL_DRIVEN_RW <= 0.D0) THEN
       CALL push_diag("EXTERNAL_DRIVEN_RW", TR_DIAG_OUT_OF_RANGE, &
            "non-positive width with non-zero EXTERNAL_DRIVEN_I; profile cannot be normalized (silent no-op)")
    END IF
```

- [ ] **Step 5: Build + verify compilation**

```bash
make -C tr libtrapi.so 2>&1 | tail -10
```

Expected: builds. If you get "AJRFT not declared" → check trrslt_globals.f90 imports it into trcomm correctly (it should, via trcomm_globals).

- [ ] **Step 6: Verify existing trlib tests still PASS**

```bash
PYTHONPATH=python python3 -m pytest --timeout=60 python/trlib/tests/ 2>&1 | tail -3
```

Expected: all PASS. Any failure here means the C ABI struct mismatch — verify tr_api.h struct field order EXACTLY matches tr_state.f90.

- [ ] **Step 7: Commit**

```bash
git add tr/tr_api.f90
git commit -m "tr: expose AJRFT via tr_api_get_state + validate EXTERNAL_DRIVEN_RW (L-7b-i)"
```

### Task 1.9: Add AJRFT to Python state.py

**Files:**
- Modify: `python/trlib/state.py`

- [ ] **Step 1: Read state.py to find scalars dict construction**

```bash
grep -n "scalars\|AJT\|RQ1" python/trlib/state.py | head -20
```

Expected: see how the dict gets keys like AJT, RQ1, etc. Likely a `_FIELDS` tuple or explicit dict build in `from_c()`.

- [ ] **Step 2: Add AJRFT to the scalar field list**

Locate the field list (e.g., a tuple `_SCALAR_FIELDS = ("nt", "nrmax", "nsmax", "T", "WPT", "AJT", ..., "RQ1")`) and append `"AJRFT"`:

```python
_SCALAR_FIELDS = (
    "nt", "nrmax", "nsmax", "T", "WPT", "AJT", "Q0",
    "BETA0", "BETAP0", "BETAA", "BETAN",
    "TAUE1", "TAUE2", "ZEFF0", "ALI", "RQ1",
    "AJRFT",   # L-7b-i
)
```

(Exact location depends on existing code structure — adapt to whatever pattern is used.)

- [ ] **Step 3: Verify Python wrapper picks up AJRFT**

```bash
PYTHONPATH=python python3 -c "
from trlib import Trlib
tr = Trlib()
tr.set_param('RR', 8.5)
tr.set_param('RA', 2.0)
tr.run(ntmax=1)
state = tr.get_state()
print('AJRFT in scalars:', 'AJRFT' in state.scalars)
print('AJRFT value:', state.scalars.get('AJRFT'))
tr.close()
"
```

Expected: `AJRFT in scalars: True`, `AJRFT value: 0.0` (since EXTERNAL_DRIVEN_I=0 default).

- [ ] **Step 4: Commit**

```bash
git add python/trlib/state.py
git commit -m "trlib: expose AJRFT in TrState.scalars (L-7b-i)"
```

### Task 1.10: Verify trlib has validate() wrapper, add if missing

**Files:**
- Possibly modify: `python/trlib/trlib.py` (or wherever the Trlib class lives)

- [ ] **Step 1: Check if `validate()` method exists on Trlib**

```bash
grep -n "def validate\|tr_validate" python/trlib/trlib.py python/trlib/_ffi.py 2>&1 | head
```

If 0 results → method missing, proceed to Step 2. If hits found → skip to Step 4 (already implemented).

- [ ] **Step 2: Add validate() method to Trlib (if missing)**

Pattern to follow: existing `set_param`, `run`, `get_state` methods. Add to Trlib class:

```python
def validate(self):
    """Call tr_validate; return list of TrDiagEntry dataclasses.
    
    Empty list = no issues. Each entry: (param: str, code: str, msg: str).
    Code is mapped to enum names (OUT_OF_RANGE, FILE_MISSING, etc.).
    """
    from .state import TrDiagEntry
    DIAG_CAP = 16
    diag_array = (TrDiagEntryC * DIAG_CAP)()
    ndiag = ctypes.c_int(0)
    rc = self._lib.tr_validate(diag_array, DIAG_CAP, ctypes.byref(ndiag))
    # rc=0 (TR_OK) = clean, rc=1 (TR_ERR_INVALID) = ndiag>=1 with payload
    if rc not in (0, 1):
        raise TrlibError(f"tr_validate: ierr={rc}")
    return [TrDiagEntry.from_c(diag_array[i]) for i in range(ndiag.value)]
```

`TrDiagEntryC` ctypes Structure mirroring `tr_diag_entry_t` (param: 64-byte char array, code: int, msg: 128-byte char array). Add to `_ffi.py` or `state.py`.

`TrDiagEntry` dataclass with `from_c()` classmethod that decodes the ctypes Structure.

- [ ] **Step 3: Build/test wrapper**

```bash
PYTHONPATH=python python3 -c "
from trlib import Trlib
tr = Trlib()
tr.set_param('RR', 8.5)
print('validate result:', tr.validate())
tr.close()
"
```

Expected: `validate result: []` (empty list, no diagnostics).

- [ ] **Step 4: Commit (if changes made)**

```bash
git add python/trlib/
git commit -m "trlib: add validate() wrapper for tr_api_validate (L-7b-i)"
```

(Skip if validate() already existed.)

### Task 1.11: Squash Phase 1 commits into Commit 1

**Files:** none (git rebase)

- [ ] **Step 1: List Phase 1 commits**

```bash
git log --oneline chore/pre-push-hook-worktree-compat..HEAD
```

Expected: ~7 commits (Tasks 1.1, 1.2, 1.3, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10).

- [ ] **Step 2: Squash via interactive rebase**

```bash
git reset --soft chore/pre-push-hook-worktree-compat
git status
```

Expected: all Phase 1 file changes are staged.

- [ ] **Step 3: Create Commit 1**

```bash
git commit -m "$(cat <<'EOF'
tr+totlib: add EXTERNAL_DRIVEN_I scalar (Fortran + AJRFT C ABI exposure)

Adds 3 new scalars to tr/trcomm_param.f90: EXTERNAL_DRIVEN_I [MA],
EXTERNAL_DRIVEN_R0 (Gaussian center, normalized rho), EXTERNAL_DRIVEN_RW
(Gaussian width, normalized rho). Defaults: 0/0/0.3 (no-op when I=0).

Registered in tr_param_registry.f90 (3 CASEs + USE import). Injected
additively into AJRF(NR) in trprf.f90's TRPWRF via Gaussian profile
normalized so the integral matches EXTERNAL_DRIVEN_I [MA] exactly
(verified: AJRFT [MA] = SUM(AJRF * DSRHO) * DR / 1e6 per trrslt_globals).

Two-stage guard in trprf: outer (I!=0 .AND. RW>0) for default no-op +
silent-skip-on-zero-width, inner (SUM_EXT>0) for extreme RW edge case.
tr_api_validate surfaces RW<=0 + I!=0 as OUT_OF_RANGE diagnostic.

AJRFT exposed via tr_state_c (Fortran) + tr_api.h (C struct, end-of-struct
to preserve existing field offsets) + python/trlib/state.py mapping.
trlib wrapper validate() method ensured (added if missing).

Backward compat: EXTERNAL_DRIVEN_I=0 default → trprf injection block
skipped → AJRF unchanged → existing Layer 1 baselines (demo2014, ht6m)
must continue to PASS at 1e-10. PLHCD logic untouched (still LH-only,
not used for orchestrator coupling after this PR).

Spec: docs/superpowers/specs/2026-05-02-l7b-i-external-driven-i-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Verify only one commit added**

```bash
git log --oneline -3
```

Expected: top commit is the new squashed one; HEAD~1 is `26c2bc44 docs(spec): ...`.

---

## Phase 2 — Pipeline rewrite + existing test updates

**Goal of phase:** Switch the Python `pipeline.py` COUPLING_RULES from skeleton (PLHCD) to physical (EXTERNAL_DRIVEN_I), and update all existing tests that referenced PLHCD assertions. End of phase: existing test_pipeline*.py PASS with new dst_param.

### Task 2.1: Rewrite COUPLING_RULES in pipeline.py

**Files:**
- Modify: `python/totlib/pipeline.py` (CouplingRule definition area, line ~218-240)

- [ ] **Step 1: Read existing rule + skeleton caveat block**

```bash
sed -n '210,245p' python/totlib/pipeline.py
```

Note exact line numbers and surrounding context.

- [ ] **Step 2: Delete skeleton caveat comment block**

Use Edit tool. Find and remove the 5-line comment block:

```python
# tr's PLHCD is dimensionless, so this is a skeleton coupling — physical
# fidelity (a proper EXTERNAL_DRIVEN_I scalar) is L-7b's scope.
```

(Match exact lines from file.)

- [ ] **Step 3: Update CouplingRule dst_param + doc**

Edit the rule:

```python
COUPLING_RULES: Dict[Tuple[str, str], List[CouplingRule]] = {
    ("fp", "tr"): [
        CouplingRule(
            src_state_key=lambda state, params: compute_rjt_volint(
                state,
                R0=params["tr:RR"],
                a=params["tr:RA"],
            ),
            dst_param="EXTERNAL_DRIVEN_I",   # was "PLHCD" (L-7a R3 skeleton)
            transform=lambda v: v * 1e-6,    # Amperes → MA
            doc="fp driven current (RJT volume integral, A) -> tr EXTERNAL_DRIVEN_I (MA)",
        ),
    ],
}
```

- [ ] **Step 4: Verify no remaining PLHCD references in pipeline.py**

```bash
grep -n "PLHCD\|skeleton" python/totlib/pipeline.py
```

Expected: 0 hits.

- [ ] **Step 5: Commit**

```bash
git add python/totlib/pipeline.py
git commit -m "pipeline: switch fp→tr coupling from PLHCD to EXTERNAL_DRIVEN_I (L-7b-i)"
```

### Task 2.2: Update test_pipeline.py PLHCD assertions

**Files:**
- Modify: `python/totlib/tests/test_pipeline.py` (lines 403, 419, 457, 459 per spec)

- [ ] **Step 1: Find all PLHCD references in test files**

```bash
grep -n "PLHCD" python/totlib/tests/test_pipeline.py python/totlib/tests/test_pipeline_equiv.py python/totlib/tests/test_pipeline_registry.py 2>&1
```

Expected hits per spec §7.1:
- test_pipeline.py:403 (CouplingRule dst_param in mock setup)
- test_pipeline.py:419 (assert_any_call)
- test_pipeline.py:457-459 (comment + dst_param assertion)
- test_pipeline_equiv.py:9-12 (skeleton notes), 87-88 (set_param call)
- test_pipeline_registry.py: dst_param assertion

- [ ] **Step 2: Update test_pipeline.py mock setup (line ~403)**

Replace `dst_param="PLHCD"` with `dst_param="EXTERNAL_DRIVEN_I"` in the mock CouplingRule setup.

- [ ] **Step 3: Update test_pipeline.py assertion (line ~419)**

Change `tr_inst.set_param.assert_any_call("PLHCD", 0.62)` to `tr_inst.set_param.assert_any_call("EXTERNAL_DRIVEN_I", 0.62)`.

- [ ] **Step 4: Update test_pipeline.py comment + assertion (line ~457-459)**

```python
# R3 confirmed: PNBCD is NOT registered in tr_param_registry.f90; use PLHCD
assert rule.dst_param == "PLHCD"
```

becomes:

```python
# L-7b-i: physical EXTERNAL_DRIVEN_I scalar (was PLHCD skeleton from L-7a R3)
assert rule.dst_param == "EXTERNAL_DRIVEN_I"
```

- [ ] **Step 5: Run test_pipeline.py to verify**

```bash
PYTHONPATH=python python3 -m pytest --timeout=60 python/totlib/tests/test_pipeline.py 2>&1 | tail -3
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add python/totlib/tests/test_pipeline.py
git commit -m "test_pipeline: update PLHCD assertions to EXTERNAL_DRIVEN_I (L-7b-i)"
```

### Task 2.3: Update test_pipeline_equiv.py

**Files:**
- Modify: `python/totlib/tests/test_pipeline_equiv.py`

- [ ] **Step 1: Read current PLHCD/skeleton references**

```bash
sed -n '1,20p' python/totlib/tests/test_pipeline_equiv.py
sed -n '80,95p' python/totlib/tests/test_pipeline_equiv.py
```

- [ ] **Step 2: Remove skeleton notes from docstring (lines 9-12)**

Delete (or rewrite) the 4-line block:

```python
Note (skeleton coupling): tr's PLHCD is dimensionless (per R3), so the
test verifies API plumbing equivalence: pattern X and Y feed the same
PLHCD inputs to tr and identical tr final scalars. Physical fidelity
...
```

Replace with:

```python
L-7b-i: physical EXTERNAL_DRIVEN_I [MA] coupling. Pattern X (direct call)
and pattern Y (TotPipeline.run_pipeline) push the same EXTERNAL_DRIVEN_I
value to tr; the test verifies their tr final scalars match at 1e-10.
```

- [ ] **Step 3: Update set_param call (line ~87-88)**

```python
# R3 confirmed: PNBCD is unregistered; PLHCD is the chosen skeleton param.
tr.set_param("PLHCD", rjt_volint * 1e-6)
```

becomes:

```python
# L-7b-i: physical injection via EXTERNAL_DRIVEN_I [MA] (Gaussian profile in tr).
tr.set_param("EXTERNAL_DRIVEN_I", rjt_volint * 1e-6)
```

- [ ] **Step 4: Run equivalence test**

```bash
PYTHONPATH=python python3 -m pytest --timeout=120 python/totlib/tests/test_pipeline_equiv.py 2>&1 | tail -5
```

Expected: PASS at 1e-10. The dst_param change doesn't break X≡Y equivalence (same scalar value flows through both paths). Final state values WILL differ from L-7a (physical injection vs no-op skeleton), but that's expected; test only compares X and Y.

- [ ] **Step 5: Commit**

```bash
git add python/totlib/tests/test_pipeline_equiv.py
git commit -m "test_pipeline_equiv: update PLHCD path to EXTERNAL_DRIVEN_I (L-7b-i)"
```

### Task 2.4: Update test_pipeline_registry.py

**Files:**
- Modify: `python/totlib/tests/test_pipeline_registry.py`

- [ ] **Step 1: Find PLHCD references**

```bash
grep -n "PLHCD" python/totlib/tests/test_pipeline_registry.py
```

- [ ] **Step 2: Update each `dst_param == "PLHCD"` assertion to `EXTERNAL_DRIVEN_I`**

Use Edit tool for each occurrence.

- [ ] **Step 3: Verify**

```bash
PYTHONPATH=python python3 -m pytest --timeout=60 python/totlib/tests/test_pipeline_registry.py 2>&1 | tail -3
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add python/totlib/tests/test_pipeline_registry.py
git commit -m "test_pipeline_registry: update PLHCD assertions (L-7b-i)"
```

### Task 2.5: Run full pipeline test sweep + Layer 1 regression

**Files:** none (test only)

- [ ] **Step 1: Run all pipeline-related tests**

```bash
PYTHONPATH=python python3 -m pytest --timeout=120 \
    python/totlib/tests/test_pipeline*.py 2>&1 | tail -3
```

Expected: all PASS.

- [ ] **Step 2: Run Layer 1 equivalence (most important regression check)**

```bash
PYTHONPATH=python python3 -m pytest --timeout=120 python/totlib/tests/test_equivalence.py 2>&1 | tail -3
```

Expected: 2 passed (demo2014 + ht6m). This proves EXTERNAL_DRIVEN_I=0 default keeps tr behavior unchanged at 1e-10.

### Task 2.6: Squash Phase 2 commits into Commit 2

**Files:** none (git rebase)

- [ ] **Step 1: List Phase 2 commits**

```bash
git log --oneline HEAD~5..HEAD
```

Expected: 4-5 commits (Tasks 2.1-2.4).

- [ ] **Step 2: Squash via soft reset to Commit 1**

Find the SHA of Commit 1 (top of Phase 1 squash) — call it `<C1>`.

```bash
git reset --soft <C1>
git status
```

Expected: all Phase 2 file changes are staged.

- [ ] **Step 3: Create Commit 2**

```bash
git commit -m "$(cat <<'EOF'
pipeline: replace PLHCD skeleton with EXTERNAL_DRIVEN_I (L-7b-i)

Switches python/totlib/pipeline.py COUPLING_RULES[("fp","tr")] from
the L-7a skeleton (PLHCD as MA-magnitude carrier) to the physically
meaningful EXTERNAL_DRIVEN_I scalar [MA] introduced in the previous
commit. transform stays * 1e-6 (Amperes → MA); dst_param string
changes; doc string is updated; the 5-line "skeleton coupling caveat"
comment block is removed.

Existing pipeline tests (test_pipeline.py / test_pipeline_equiv.py /
test_pipeline_registry.py) updated to assert against the new dst_param.
Pattern X (direct) and pattern Y (run_pipeline) equivalence at 1e-10
is preserved; the test logic is unchanged, only the scalar name.

Layer 1 equivalence (test_equivalence.py: demo2014 + ht6m) continues
to PASS at 1e-10 — EXTERNAL_DRIVEN_I=0 default leaves tr behavior
identical to before this series.

Spec: docs/superpowers/specs/2026-05-02-l7b-i-external-driven-i-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Verify**

```bash
git log --oneline -4
```

Expected top 2: Commit 2 (pipeline), Commit 1 (Fortran).

---

## Phase 3 — New tests + README updates (Commit 3)

**Goal of phase:** verify EXTERNAL_DRIVEN_I behaves correctly (default no-op, AJT change, integration math, validate diag) via 5 new test cases. Update README docs.

### Task 3.1: Create test_external_driven_i.py

**Files:**
- Create: `python/trlib/tests/test_external_driven_i.py`

- [ ] **Step 1: Find existing trlib test file conventions**

```bash
ls python/trlib/tests/ && head -30 python/trlib/tests/test_*.py 2>&1 | head -50
```

Note import patterns, fixture conventions.

- [ ] **Step 2: Write the test file**

```python
"""L-7b-i: External driven current scalar (EXTERNAL_DRIVEN_I) verification.

Tests:
  - default (un-set) and explicit 0.0 produce identical state at 1e-10
  - I=1.0 MA changes AJT measurably (downstream effect proof)
  - AJRFT integrates to EXTERNAL_DRIVEN_I (math correctness)
  - 3 scalars round-trip through set_param (registry coverage)
  - tr_api_validate surfaces RW<=0 + I!=0 as OUT_OF_RANGE diagnostic

Spec: docs/superpowers/specs/2026-05-02-l7b-i-external-driven-i-design.md
"""
import math

import pytest

from trlib import Trlib


# ITER-like fixture (from L-7a R1-b ITER fixture). Stable across
# repeated init/finalize cycles per R1-b verification.
ITER_FIXTURE = {
    "RR":     8.5,
    "RA":     2.0,
    "RKAP":   1.7,
    "BB":     5.3,
    "NSMAX":  2,
    "DT":     0.1,
    "NTSTEP": 10,
    # Density / temperature profile arrays — set per index.
    # If trlib's set_param doesn't support the "PN[1]" notation, fall
    # back to bulk fixtures from python/trlib/examples/quickstart.py.
}
PN_PT_FIXTURE = [
    ("PN[1]",  1.0),
    ("PN[2]",  1.0),
    ("PT[1]",  1.5),
    ("PT[2]",  1.5),
]


def _new_tr_with_fixture(extra_params=None):
    """Construct a Trlib(), apply ITER_FIXTURE + PN/PT, plus optional extras.

    Returns the live handle; caller is responsible for tr.run() and tr.close().
    """
    tr = Trlib()
    for k, v in ITER_FIXTURE.items():
        tr.set_param(k, v)
    for k, v in PN_PT_FIXTURE:
        tr.set_param(k, v)
    if extra_params:
        for k, v in extra_params.items():
            tr.set_param(k, v)
    return tr


def _run_and_get_scalars(extra_params=None):
    tr = _new_tr_with_fixture(extra_params)
    tr.run(ntmax=1)
    state = tr.get_state()
    scalars = dict(state.scalars)
    tr.close()
    return scalars


def test_external_driven_i_default_is_noop():
    """Default (un-set) and explicit 0.0 set produce identical scalars."""
    s_default = _run_and_get_scalars()
    s_zero    = _run_and_get_scalars({"EXTERNAL_DRIVEN_I": 0.0})
    for k in s_default:
        assert math.isclose(s_default[k], s_zero[k],
                            rel_tol=1e-10, abs_tol=1e-15), \
            f"default vs explicit-zero diverged at {k}: {s_default[k]} vs {s_zero[k]}"


def test_external_driven_i_changes_ajt():
    """I=1.0 MA changes AJT measurably from the default-zero baseline."""
    s_zero = _run_and_get_scalars()
    s_one  = _run_and_get_scalars({"EXTERNAL_DRIVEN_I": 1.0})
    delta = abs(s_one["AJT"] - s_zero["AJT"])
    assert delta > 0.5, \
        f"AJT shift too small ({delta:.4f}); expected >0.5 MA shift " \
        f"from EXTERNAL_DRIVEN_I=1.0. Default AJT={s_zero['AJT']:.4f}, " \
        f"with-drive AJT={s_one['AJT']:.4f}"


def test_external_driven_i_integrates_to_total():
    """AJRFT (= integrated total) matches the requested EXTERNAL_DRIVEN_I.
    
    Default (I=0): AJRFT = 0 (no RF current drive setup either).
    I=1.0 MA: AJRFT ≈ 1.0 MA (transport back-reaction in 1 step is small;
    rel_tol=1e-3 is conservative).
    """
    s_zero = _run_and_get_scalars()
    s_one  = _run_and_get_scalars({"EXTERNAL_DRIVEN_I": 1.0})
    # Default: AJRFT should be 0 (no PLH/PEC/PIC driven current configured)
    assert math.isclose(s_zero["AJRFT"], 0.0, abs_tol=1e-12), \
        f"default AJRFT not zero: {s_zero['AJRFT']}"
    # With drive: AJRFT should match injected I within transport coupling tol
    assert math.isclose(s_one["AJRFT"], 1.0, rel_tol=1e-3, abs_tol=1e-6), \
        f"AJRFT={s_one['AJRFT']:.6f} did not match injected I=1.0 MA"


def test_external_driven_r0_rw_round_trip():
    """All 3 EXTERNAL_DRIVEN_* scalars are accepted by set_param.
    
    Catches missing CASE entries in tr_param_registry.f90.
    """
    tr = _new_tr_with_fixture({
        "EXTERNAL_DRIVEN_I":  0.5,
        "EXTERNAL_DRIVEN_R0": 0.2,
        "EXTERNAL_DRIVEN_RW": 0.4,
    })
    tr.run(ntmax=1)   # exception-free run = registry CASE coverage
    tr.close()


def test_external_driven_validate_zero_width():
    """RW=0 + I!=0 surfaces as OUT_OF_RANGE in tr_api_validate."""
    tr = _new_tr_with_fixture({
        "EXTERNAL_DRIVEN_I":  1.0,
        "EXTERNAL_DRIVEN_RW": 0.0,    # invalid: would silent-zero in trprf
    })
    diags = tr.validate()
    matched = [d for d in diags
               if d.param == "EXTERNAL_DRIVEN_RW" and "OUT_OF_RANGE" in str(d.code)]
    assert matched, \
        f"expected OUT_OF_RANGE diagnostic for EXTERNAL_DRIVEN_RW, got: {diags}"
    tr.close()
```

- [ ] **Step 3: Run new tests one at a time**

```bash
PYTHONPATH=python python3 -m pytest --timeout=60 -v \
    python/trlib/tests/test_external_driven_i.py 2>&1 | tail -20
```

Expected: 5 passed. If `test_external_driven_i_integrates_to_total` fails with `rel_tol=1e-3` too tight, relax to `rel_tol=1e-2` (some transport back-reaction in 1 step). If `test_external_driven_validate_zero_width` fails with "validate not callable", revisit Task 1.10.

- [ ] **Step 4: Iterate on tolerance / fixture if needed**

If `PN[1]` notation isn't supported by current trlib, replace `PN_PT_FIXTURE` with the bulk-fixture pattern from `python/trlib/examples/quickstart.py`.

- [ ] **Step 5: Commit**

```bash
git add python/trlib/tests/test_external_driven_i.py
git commit -m "test: external driven current verification (5 cases) (L-7b-i)"
```

### Task 3.2: Update python/totlib/README.md

**Files:**
- Modify: `python/totlib/README.md` (line ~290-299)

- [ ] **Step 1: Read existing skeleton caveat block**

```bash
sed -n '285,305p' python/totlib/README.md
```

- [ ] **Step 2: Replace skeleton block with EXTERNAL_DRIVEN_I description**

Use Edit tool. Replace lines describing PLHCD skeleton with:

```markdown
- `fp → tr`: fp's RJT volume integral [A] → tr's `EXTERNAL_DRIVEN_I` [MA]

The fp side computes the total driven current via `compute_rjt_volint(state, R0, a)`
(volume integral of `RJT[NSA][NR]` over the plasma cross-section). The result
[A] is converted to MA (`× 1e-6`) and pushed into tr's `EXTERNAL_DRIVEN_I`
scalar. tr then injects that current into the transport equation via a
Gaussian radial profile (`EXTERNAL_DRIVEN_R0`, `EXTERNAL_DRIVEN_RW` defaults
0.0 / 0.3 — axis-peaked, width 30% of minor radius). The Gaussian is
normalized so the integral of AJRF's external contribution exactly equals
`EXTERNAL_DRIVEN_I [MA]`.

Verify the injected total via `tr.get_state().scalars["AJRFT"]` (= total
RF + external driven current [MA], includes the EXTERNAL_DRIVEN_I term).
```

(Adjust to match surrounding markdown style.)

- [ ] **Step 3: Verify no PLHCD or "skeleton" references remain in README**

```bash
grep -in "plhcd\|skeleton" python/totlib/README.md
```

Expected: 0 hits (or only references to L-7a as historical context if you keep that).

- [ ] **Step 4: Commit**

```bash
git add python/totlib/README.md
git commit -m "docs(totlib): replace PLHCD skeleton with EXTERNAL_DRIVEN_I (L-7b-i)"
```

### Task 3.3: Add "External driven current" section to python/trlib/README.md

**Files:**
- Modify: `python/trlib/README.md`

- [ ] **Step 1: Read README structure to find logical insertion point**

```bash
grep -n "^##" python/trlib/README.md
```

Insertion point: after the existing "Parameters" or "Set Param" section, before the "State" section.

- [ ] **Step 2: Add new section**

```markdown
## External driven current (L-7b-i)

For pipelines where another module computes a total driven current
(e.g. fp's RJT volume integral) and tr should consume it, set:

| Param                    | Unit              | Default | Meaning                                |
|--------------------------|-------------------|---------|----------------------------------------|
| `EXTERNAL_DRIVEN_I`      | MA                | 0.0     | Total externally-driven current        |
| `EXTERNAL_DRIVEN_R0`     | normalized rho    | 0.0     | Gaussian profile center (axis-peaked)  |
| `EXTERNAL_DRIVEN_RW`     | normalized rho    | 0.3     | Gaussian profile width                 |

Default `EXTERNAL_DRIVEN_I = 0.0` means no external drive (no-op,
backward compatible — existing tr regression baselines are unaffected).

Example:

```python
from trlib import Trlib

tr = Trlib()
tr.set_param("RR", 8.5); tr.set_param("RA", 2.0)
# ... other parameters ...
tr.set_param("EXTERNAL_DRIVEN_I",  1.0)   # 1 MA externally driven
tr.set_param("EXTERNAL_DRIVEN_R0", 0.0)
tr.set_param("EXTERNAL_DRIVEN_RW", 0.3)
tr.run(ntmax=10)
state = tr.get_state()
print("AJRFT:", state.scalars["AJRFT"])   # ≈ 1.0 (matches injected I)
print("AJT:",   state.scalars["AJT"])     # changed from default by ~ I
tr.close()
```

The injected current is added to `AJRF(NR)` in `trprf.f90`'s `TRPWRF`
via a Gaussian profile, normalized so `SUM(AJ_ext * DSRHO * DR) / 1e6
== EXTERNAL_DRIVEN_I [MA]` exactly. Consumed by the standard transport
equation (no special wiring needed downstream).

Validation: `tr.validate()` returns an `OUT_OF_RANGE` diagnostic if you
set `EXTERNAL_DRIVEN_I != 0` together with `EXTERNAL_DRIVEN_RW <= 0`
(which would silently no-op in trprf otherwise).
```

- [ ] **Step 3: Commit**

```bash
git add python/trlib/README.md
git commit -m "docs(trlib): add 'External driven current' README section (L-7b-i)"
```

### Task 3.4: Squash Phase 3 commits into Commit 3

**Files:** none (git rebase)

- [ ] **Step 1: List Phase 3 commits**

```bash
git log --oneline HEAD~3..HEAD
```

Expected: 3 commits (Tasks 3.1, 3.2, 3.3).

- [ ] **Step 2: Squash via soft reset to Commit 2**

```bash
git reset --soft <C2>
git status
```

Expected: all Phase 3 file changes staged.

- [ ] **Step 3: Create Commit 3**

```bash
git commit -m "$(cat <<'EOF'
test+docs: external driven current verification + skeleton caveat removal

Adds 5 new test cases under python/trlib/tests/test_external_driven_i.py:

  - default (un-set) ≡ explicit 0.0 at 1e-10 (no-op proof)
  - I=1.0 MA changes AJT by >0.5 MA (downstream effect proof)
  - AJRFT ≈ 1.0 MA when I=1.0 (Gaussian normalization correctness)
  - 3 scalars round-trip through set_param (registry CASE coverage)
  - validate() surfaces RW=0 + I!=0 as OUT_OF_RANGE

Updates python/totlib/README.md (replaces PLHCD skeleton section with
physical EXTERNAL_DRIVEN_I description) and adds a new "External driven
current" section to python/trlib/README.md with usage example +
parameter table + validation note.

Spec: docs/superpowers/specs/2026-05-02-l7b-i-external-driven-i-design.md

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Verify final commit list**

```bash
git log --oneline -4
```

Expected: 3 commits (Phase 3, 2, 1) + handoff/spec base.

---

## Phase 4 — Pre-push gate + PR open

**Goal of phase:** CLAUDE.md pre-push gate (local pytest, 2 reviewers in parallel, marker, push, PR).

### Task 4.1: Final local pytest sweep

**Files:** none (test only)

- [ ] **Step 1: Run canonical CI test set**

```bash
PYTHONPATH=python python3 -m pytest --timeout=120 --timeout-method=signal \
    python/totlib/tests/ python/trlib/tests/ python/mcp-servers/tot_mcp/tests/ \
    2>&1 | grep -E "^=+.*(passed|failed)" | tail -3
```

Expected: 211 passed (206 existing + 5 new). 1 fail OK if it's the unrelated Python 3.10 ExceptionGroup test (per handoff §残タスク低優先).

- [ ] **Step 2: Specifically verify Layer 1 baseline regression**

```bash
PYTHONPATH=python python3 -m pytest --timeout=120 \
    python/totlib/tests/test_equivalence.py 2>&1 | tail -3
```

Expected: `2 passed`. This is the key backward-compat gate.

- [ ] **Step 3: If any unexpected failure, debug before proceeding**

DO NOT push if anything else fails. Re-read the failing test, reproduce, fix, re-commit. Pre-push gate exists for a reason.

### Task 4.2: Run 2 reviewer agents in parallel

**Files:** none (Agent calls)

- [ ] **Step 1: Run in-house code-reviewer + Codex independent reviewer in PARALLEL (single message, both Agent calls)**

In-house prompt sketch:

```
Review the diff in /Users/k-yoshimi/Dropbox/cursor/task on branch
claude/2026-05-02-l7b-i-external-driven-i. Run `git diff
chore/pre-push-hook-worktree-compat..HEAD` to see the 3 commits:

1. tr+totlib: Fortran scalar add + AJRFT C ABI exposure (commit 1)
2. pipeline: PLHCD → EXTERNAL_DRIVEN_I (commit 2)
3. test+docs: 5 new test cases + README updates (commit 3)

Spec: docs/superpowers/specs/2026-05-02-l7b-i-external-driven-i-design.md

Background: replaces L-7a skeleton coupling with physically meaningful
external driven current scalar. Default I=0 → AJRF unchanged → Layer 1
baseline (demo2014, ht6m) PASS. Verified locally: 211 passed.

Focus on: (1) Fortran USE clause correctness, (2) tr_state struct
layout vs tr_api.h C header sync, (3) Gaussian normalization math in
trprf injection, (4) test fixture compatibility (PN[1] notation), (5)
backward compat invariants. Report HIGH/MED in <400 words.
```

Codex prompt: similar, framed as "independent second-opinion review,
catch what in-house might miss (especially cross-cutting code quality
and edge cases in Fortran/C struct interop)".

- [ ] **Step 2: Address HIGH/MED findings**

For each HIGH/MED:
- Make a fix commit on top of Commit 3 (do NOT amend Commit 3 — CLAUDE.md says "Always create NEW commits rather than amending")
- Re-run pytest
- If diff is significant, re-run reviewers (cumulative diff)

### Task 4.3: Write REVIEW_OK marker + push

**Files:** none

- [ ] **Step 1: Mark current HEAD as reviewed**

```bash
touch "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
ls "$(git rev-parse --git-common-dir)/REVIEW_OK_$(git rev-parse HEAD)"
```

Expected: marker file exists for HEAD SHA.

- [ ] **Step 2: Push feature branch to origin**

```bash
git push -u origin claude/2026-05-02-l7b-i-external-driven-i 2>&1 | tail -5
```

Expected: `pre-push: review marker present — OK`. Push succeeds.

If pre-push hook complains about marker missing, you skipped Step 1 — go back.

### Task 4.4: Open PR

**Files:** none (gh)

- [ ] **Step 1: Create PR via gh**

```bash
env -u GITHUB_TOKEN gh pr create \
    --base chore/pre-push-hook-worktree-compat \
    --title "tr+totlib: physical EXTERNAL_DRIVEN_I scalar (L-7b-i)" \
    --body "$(cat <<'EOF'
## Summary

Replaces the L-7a skeleton coupling (PLHCD as MA-magnitude carrier) with
a physically meaningful EXTERNAL_DRIVEN_I scalar [MA] injected via Gaussian
profile into AJRF, plus AJRFT C ABI exposure for integration verification,
plus tr_api_validate extension for the RW=0+I!=0 misconfiguration case.

3 commits:
1. **Fortran + C ABI** (`tr+totlib: add EXTERNAL_DRIVEN_I scalar (Fortran + AJRFT C ABI exposure)`)
2. **Python pipeline** (`pipeline: replace PLHCD skeleton with EXTERNAL_DRIVEN_I (L-7b-i)`)
3. **Tests + docs** (`test+docs: external driven current verification + skeleton caveat removal`)

Spec: `docs/superpowers/specs/2026-05-02-l7b-i-external-driven-i-design.md`

## Test plan

- [x] Layer 1 equivalence (demo2014 + ht6m) PASS at 1e-10 — backward compat gate
- [x] All existing pipeline tests PASS with new dst_param
- [x] 5 new test cases PASS (default no-op / AJT change / AJRFT integration / round-trip / validate diag)
- [x] In-house code-reviewer: HIGH/MED resolved
- [x] Codex independent reviewer: HIGH/MED resolved
- [x] CLAUDE.md pre-push gate complete (REVIEW_OK marker for final SHA)

## L-7b-i scope confirmation

In scope (this PR):
- 3 new scalars (`EXTERNAL_DRIVEN_I`, `EXTERNAL_DRIVEN_R0`, `EXTERNAL_DRIVEN_RW`)
- AJRFT exposure via tr_state_c + tr_api.h
- tr_api_validate extension for RW=0 misconfiguration
- pipeline.py COUPLING_RULES rewrite
- 5 new test cases + README updates

Out of scope (L-7b follow-ups):
- L-7b-ii: BPSD broker profile coupling (wr → fp/tr, eq → tr)
- L-7b-iii: Declarative `tot.couple(src, dst)` API
- L-7b-iv: Per-module state aggregation (`Tot.get_state().fp_scalars` etc.)
- AJOHT/AJBST/AJNBT additional exposure (deferred to L-7b-iv)

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)" 2>&1 | tail -5
```

Expected: PR URL printed.

- [ ] **Step 2: Note the PR URL for the user**

Print the URL so the user can check CI status.

### Task 4.5: Wait for CI + Bugbot

**Files:** none (monitoring)

- [ ] **Step 1: Check CI status periodically (don't poll tightly)**

```bash
env -u GITHUB_TOKEN gh pr view --json statusCheckRollup,number 2>&1 | head
```

If green: proceed to Step 2.
If red: read the failing job, reproduce locally, fix, push fix commit, re-mark + re-push.

- [ ] **Step 2: Check Bugbot status (will be SKIPPED for CI-only changes per handoff §D, but still wait if it triggers)**

If Bugbot leaves comments → respond per CLAUDE.md feedback_bugbot_wait.md (re-review with both agents on the fix diff).

- [ ] **Step 3: Merge (squash) when all checks COMPLETED**

```bash
env -u GITHUB_TOKEN gh pr merge --squash --delete-branch 2>&1 | tail -3
```

NEVER use `--admin` or `--no-verify`. Wait for CI even if it takes hours.

---

## Spec coverage check

| Spec section | Implementation task |
|---|---|
| §5.1 trcomm_param declarations | Task 1.1 |
| §5.2 trinit defaults | Task 1.2 |
| §5.3 tr_param_registry CASEs | Task 1.3 |
| §5.4 trprf Gaussian injection | Task 1.5 |
| §5.5 tr_state_c struct field | Task 1.6 |
| §5.6 tr_api.h C header sync | Task 1.7 |
| §5.7 tr_api_get_state populate + validate | Task 1.8 |
| §6.1 pipeline.py rewrite | Task 2.1 |
| §6.2 skeleton caveat removal | Task 2.1 |
| §6.3 trlib state.py mapping | Task 1.9 |
| §6.4 trlib validate() wrapper | Task 1.10 |
| §7.1 existing test PLHCD updates | Tasks 2.2-2.4 |
| §7.2 new test_external_driven_i.py | Task 3.1 |
| §7.3 AJRFT integration test | Task 3.1 (test_external_driven_i_integrates_to_total) |
| §7.4 Layer 1 regression | Task 4.1 Step 2 |
| §7.5 pipeline equivalence | Task 2.5 |
| §8 documentation updates | Tasks 3.2 (totlib README), 3.3 (trlib README) |
| §9 error handling | Task 1.5 (trprf 2-stage guard) + Task 1.8 (validate) |
| §10 DoD | covered across all tasks |
| §11 PR strategy + pre-push gate | Phase 4 |
| §12 Risk register | (mitigations applied per task) |
| §13 L-7b follow-ups | mentioned in PR description (Task 4.4) |

All spec sections are implemented in this plan. ✓

---

## Notes for the executor

- **Frequent commits**: each task commits incrementally. Phase 1.11 / 2.6 / 3.4 then squash into the 3 PR-target commits.
- **TDD discipline**: for the new test file (Task 3.1), write the test first, run it (expect FAIL because tr doesn't have the new behavior wired locally yet — wait, it should be wired by end of Phase 1; so all tests should PASS on first run).
  - The TDD cycle here is between phases: Phase 1 changes the Fortran/Python plumbing, Phase 3 verifies with new tests. Tests are added AFTER plumbing because we need libtrapi.so rebuilt and pipeline.py updated first.
  - If you want strict TDD: write the new tests in Phase 0.5 (between Phase 0 and 1), confirm they fail, then proceed to Phase 1. The tests will start passing as you complete each Phase 1 task.
- **macOS gotcha**: if `make -C tr` fails on macOS, try `make -C tr GFLIBS=""` (per handoff §環境セットアップ).
- **Build artifacts NOT in git**: `tr/libtrapi.so` is gitignored (handoff "手元のみ"). Don't commit it.
- **Layer 1 is the gate**: if `test_equivalence.py` fails after Phase 1, the EXTERNAL_DRIVEN_I default-zero invariant is broken — check trprf guard logic first.
