# P1 — TRX/tr Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `tr` the single canonical transport module by hand-porting bpsi `trx`'s newer fusion physics (the `model_pnf` multi-reaction framework + supporting modules) into the kyoshimi-modernized, module-split, C-ABI/MCP-bearing `tr`, then archiving `trx` and `trm` — preserving every existing result bit-for-bit (`model_pnf=0` default ⇒ inert) and validating the *new* fusion paths against a 1e-10 reference captured from the bpsi `trx` executable.

> **Editorial note (Task 7, after the fact).** The "1e-10" in the Goal above,
> in the Architecture line below, in the file table, and in Task 2's heading
> did not survive contact with the measurement. The reference captures are
> sound and are committed, but kyoshimi `tr` does not match them at 1e-10 and
> the reason is outside fusion: the two forks differ in the transport step
> (identical to rounding at `NTMAX=0`, separating from the first step). Task 7
> validates the fusion *differential* instead. Read Task 7's editorial note
> before acting on any 1e-10 gate in this document;
> `test_run/baselines/tr_fus_dt_hot/SOURCE.md` is authoritative throughout.

**Architecture:** Test-oracle-first. We (1) build a 1e-10 reference from bpsi `trx` by porting the existing `trregress.f90` dumper into it, then (2) port physics into kyoshimi `tr` in inert-then-active order: collision modules → fusion data model (default off) → `libnf` → `trpnf`/dispatch → enable `model_pnf=1..4` against the reference. Every structural step is gated by "existing `tr` regression unchanged at 1e-10"; every new-physics step is gated by "matches bpsi-`trx` at 1e-10". The kyoshimi `tr` `trcomm.f90` is split into 6 sub-modules, so bpsi's monolithic `trcomm` declarations must be routed into the correct sub-module.

**Tech Stack:** Fortran 90 (free-form `.f90`, MODULE, ALLOCATABLE), `gfortran-mp-15 -ffree-form`, the `tr/Makefile` targets `tr2` / `libtrapi.so` / `tr_api_check_all`, the `test_run/` 1e-10 harness (`run_tests.sh`, `trregress.f90` env-guarded dump `TR_REGRESS_DUMP=1`, `extract_tr_metrics.py`, `compare_metrics.py`), `tr_param_registry.f90` (C-ABI param dispatch), `python/trlib` + `tr_mcp`.

**Sources (verified live 2026-06-15):** bpsi `trx` files via `git -C task show bpsi/develop:trx/<f>`; kyoshimi `tr/` worktree; the design spec `docs/superpowers/specs/2026-06-15-task-merge-f90-design.md`; the TR Phase-0 harness plan `docs/superpowers/plans/2026-04-17-tr-refactoring-phase0.md`.

**Key preconditions established by recon:**
- kyoshimi `tr` fusion is the **old scalar `MDLNF`** path (`trpnf.f90` `TRNFDT`/`TRNFDHe3` writing 1-D `SNF(NR)`/`PNF(NR)` with hardcoded species 2,3; `trcalc.f90:132 SELECT CASE(MDLNF)`). It has **zero** `model_pnf`/`libnf`/`nnfmax`/`SNF_NSNNFNR`. (This preconception said fusion must be a *replace/upgrade*; **RECORDED DECISIONS #2 overturned it** — `model_pnf` is added *additively* and the legacy `MDLNF` path is kept.)
- CYTRAN is **already ported** (`tr/cytran/{cytran_mod.f90,tr_cytran_mod.f90}`, wired, `trcalc.f90:19,101`) → **no work**.
- TGLF (`trtglf.f90`) needs the external GACODE TGLF library (`tglf_interface`/`tglf_run`), **absent from both trees** → **deferred** (§Deferred).
- Adding a `.f90` to `SRCS_CORE` (`tr/Makefile:34-48`) auto-includes it in both `libtr2.a` and `libtrapi.so` (via `OBJ_CORE_PIC`) — no other src-list edit needed.

---

## RECORDED DECISIONS (Task 1 complete, 2026-06-30)

Task 1 recon done. Findings + decisions that REVISE the plan below:

1. **[CORRECTS a plan precondition] Existing inputs run with fusion ON.** `tr_m0904.in` and
   `tr_iter01.in` both set `MDLNF=1` (NSMAX=4, e/D/T/He4) — the old scalar DT path IS exercised by 2 of
   the 3 core baselines. The plan's "inputs leave fusion off ⇒ default-off model_pnf keeps baselines
   bit-identical" premise was FALSE.
2. **STRATEGY = Option A (owner-decided): KEEP the old `MDLNF`/`SIGMAM`/`TRNFDT` DT path; ADD `model_pnf`
   as a NEW *additive* multi-reaction path (default off).** Justification (verified numerically): the new
   `libnf` `svnf_dt` reaction-rate table is the SAME analytic fit as the old `SIGMAM` (`svnf_dt` is in cm³/s, `SIGMAM` in m³/s; the % agreement is after the cm³/s→m³/s conversion), just tabulated to
   2 sig figs — at the table points they agree to 0.03–1.2%. CORRECTION (codex review): `libnf` splines
   the RAW ⟨σv⟩ vs `log10(T)` (`SPL1D`), NOT log-log, so at core/fusion temps T≳5 keV it stays within ~1–2% of `SIGMAM` but
   between the low-T edge points (T≲3 keV, where ⟨σv⟩ is negligible and no fusion occurs) the raw-value
   spline overshoots strongly (≫100% at 1–2 keV) — immaterial to fusion power. So migrating existing DT
   cases to `model_pnf` gains ZERO physics at the core (the analytic `MDLNF` is actually smoother). `model_pnf`'s real value is the MULTI-REACTION capability (DD/DHe3/TT/THe3 = model_pnf 2/3/4)
   that `MDLNF` lacks — which is purely additive.
   ⇒ **Task 6 is REVISED: do NOT retire the `MDLNF` `SELECT CASE`.** Add `CALL tr_pnf` as an additive
   branch gated by `model_pnf>0` (the two paths coexist; `model_pnf=0` default ⇒ existing baselines
   bit-for-bit unchanged, guaranteed). This makes every "regression unchanged at 1e-10" gate trivially
   satisfied for the structural tasks.
3. **[Task 1 Step 4] FTAUE/FTAUI reconcile: use `AMM`.** kyoshimi `trcomm_const.f90:19` has `AMM`
   (=1.672621637D-27) but NOT `AMP`; adopt bpsi's guarded form with `AMM`.
   **CORRECTION (Task 3 as-built): `AMM` and bpsd's `AMP` are NO LONGER the same number.**
   `../bpsd/bpsd_constants.f90:39` (the sibling repo; `tr/Makefile` compiles it via `BPSD_SRC=../../bpsd`, and
   `pl/plcomm.f90:36` re-exports it) now carries the CODATA-2018 `AMP = 1.67262192369E-27`, a relative
   difference of ~1.7e-7 from `AMM`. Using `AMP` shifts `FTAUI` by ~8.6e-8 and breaks the 1e-10
   baselines, so `AMM` is mandatory. Likewise bpsi's `PZ(NS_D)` cannot be pasted verbatim — kyoshimi
   `tr` defines no `NS_D`; `PZ(2)` is the numerically identical form for the e/D/T/He4 ordering.
   ⇒ **Consequence for Task 2:** bpsi `trx` cannot serve as a 1e-10 oracle for any FTAUI-dependent
   quantity (bootstrap `AJBS` → `AJ` → `QP`) unless its `AMP` is reconciled to `AMM` in the capture build.
4. **[Validation-env] `run_tests.sh` is unusable locally** (macOS `bash 3.2` lacks `declare -A`). Use the
   **pytest equivalence path** (`python/trlib/tests/test_equivalence.py`, drives `libtrapi.so`) as the
   local 1e-10 gate, plus **CI** (`python-tests.yml`) as the authoritative gate. Build with
   `make -C tr tr2 libtrapi.so`.
5. bpsi `trx` keeps `MDLNF` in its namelist echo but drives fusion via `CALL tr_pnf` (trcalc.f90:128) —
   consistent with policy A. `task/` checkout is on `develop` with the `bpsi` remote ⇒ the Task 2
   reference oracle (build bpsi `trx`) is feasible when the model_pnf paths need validating.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `task/trx/trregress.f90` | Create (copy) | Port the dumper into bpsi `trx` to capture the 1e-10 reference |
| `task/trx/trloop.f90` | Modify | Add the dump hook (reference-capture only; not merged to canonical) |
| `task-kyoshimi/test_run/inputs/tr_fus_dt.in` | Create | DT-fusion (`model_pnf=1`) regression input |
| `task-kyoshimi/test_run/baselines/tr_fus_dt/metrics.json` | Create (generated) | 1e-10 reference from bpsi `trx` |
| `task-kyoshimi/tr/trcoll.f90` | Create | MODULE `trcoll`: `coulomb_log`, `FTAUE`, `FTAUI` (extracted from `trcalc`) |
| `task-kyoshimi/tr/trlib.f90` | Create | MODULE `trlib`: `COULOG`, `HY` |
| `task-kyoshimi/tr/trcalc.f90` | Modify | Remove inline collision functions; `USE trcoll`/`trlib`; add `CALL tr_pnf` gated by `model_pnf>0` **(Option A — keep the `MDLNF` `SELECT CASE`, do NOT replace it; see RECORDED DECISIONS)** |
| `task-kyoshimi/tr/trcomm_param.f90` | Modify | Add `model_pnf`, `nnfmax`, `NNFM`, reaction-source dims |
| `task-kyoshimi/tr/trcomm_profile.f90` | Modify | Add radial fusion/source arrays `SNF_*`/`PNF_*`/`SNFNN_*`/`TAUF`/`AJNB_NSNNBNR`/`PEC_/PLH_/PIC_NSN*` + allocate/dealloc |
| `task-kyoshimi/tr/trcomm_globals.f90` | Modify | Add `ANF0,TF0,ANFAV,TFAV,WFT` + allocate/dealloc |
| `task-kyoshimi/tr/libnf.f90` | Create (port) | MODULE `libnf`: reaction tables, `set_usigmav_nf`, `sigmav_nf` |
| `task-kyoshimi/tr/trpnf.f90` | Extend | **Add** `tr_prep_pnf`/`tr_pnf` generic loop; **keep** `TRNFDT`/`TRNFDHe3` (Option A — the retained `MDLNF SELECT CASE` calls them) |
| `task-kyoshimi/tr/trprep.f90` | Modify | Insert `set_usigmav_nf`→`NFMAX`→allocate→`tr_prep_pnf` sequence |
| `task-kyoshimi/tr/trexec.f90` | Modify | Fast-ion fusion matrix rows over `NNBMAX+NNF` |
| `task-kyoshimi/tr/trparm.f90` + `tr_param_registry.f90` | Modify | Register `model_pnf`,`nnfmax` (default 0) |
| `task-kyoshimi/tr/Makefile` | Modify | Add `trcoll.f90`,`trlib.f90`,`libnf.f90` to `SRCS_CORE` + dep rules |
| `task-kyoshimi/archive/trx/`, `archive/trm/` | Create (move) | Archive the retired variants |

---

## Task 1: Pre-flight verification & decisions

**Files:** none (read-only); record decisions in this plan / a scratch note.

- [x] **Step 1: Confirm bpsi `trx`'s `MDLNF` disposition** (does `trx` keep, remove, or map `MDLNF` alongside `model_pnf`?)

Run:
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task
git show bpsi/develop:trx/trcalc.f90 | grep -nE 'MDLNF|model_pnf|CALL tr_pnf'
git show bpsi/develop:trx/trpnf.f90 | grep -nE 'MDLNF|TRNFDT|tr_pnf|model_nnf'
git show bpsi/develop:trx/trparm.f90 | grep -nE 'MDLNF|model_pnf'
```
Expected: `trx` uses `CALL tr_pnf` / `model_pnf` and no longer the `MDLNF SELECT CASE`. **Record** whether `MDLNF` remains a namelist key in `trx` (it governs the decision in Step 3).

- [x] **Step 2: Confirm existing tr regression inputs leave fusion OFF**

Run:
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
grep -iE 'MDLNF' tr/trinit.f90 test_run/inputs/tr_iter01.in test_run/inputs/tr_m0904.in test_run/inputs/tr_tst2.in
```
Expected: `tr/trinit.f90` sets `MDLNF=0` default and none of the three inputs override it to >0. This guarantees that introducing `model_pnf` with default 0 keeps the three existing baselines bit-identical. If any input sets `MDLNF>0`, flag it — that case's baseline must be regenerated against bpsi `trx`.

- [x] **Step 3: Decide the `MDLNF`→`model_pnf` namelist policy** (record in this plan)

Two options; pick per Step-1 finding and the no-NAMELIST-change constraint:
- **(A, CHOSEN — see RECORDED DECISIONS #2) Keep `MDLNF` as the authoritative legacy DT path; add `model_pnf` (default 0) as an *additive* multi-reaction path.** When `model_pnf=0` the legacy `MDLNF` path runs **exactly as-is — no remapping, no behaviour change** — so existing inputs and the three baselines stay bit-for-bit identical. Preserves all existing input files.
- **(B) Mirror bpsi `trx` exactly** (whatever Step 1 shows). If `trx` dropped `MDLNF`, dropping it here would break old inputs — only choose if Fukuyama confirms no production input uses `MDLNF>0`.

- [x] **Step 4: Decide the `FTAUE`/`FTAUI` behavioral reconcile** (record in this plan)

bpsi `trcoll` differs from kyoshimi `trcalc` inline:

| function | kyoshimi `tr/trcalc.f90` | bpsi `trx/trcoll.f90` |
|---|---|---|
| `FTAUE` | `PZ(2)`, **no** `ABS(ANIL)` guard, `USE ...AME...` | `PZ(NS_D)`, `IF(ABS(ANIL).LE.1.D-8) FTAUE=1.D8`, `coulomb_log(1,2,..)` |
| `FTAUI` | `AMM` | `AMP`, `IF(ABS(ANIL).LE.1.D-8) FTAUI=1.D8` |

Decision: **adopt bpsi's guard, but keep kyoshimi's `AMM` and `PZ(2)`** (see RECORDED DECISIONS #3 — as-built). `NS_D` does not exist in kyoshimi `tr` and `PZ(2)` is its numerically identical form; `AMP` is **NOT** equal to `AMM` any more (bpsd moved to CODATA-2018). The guard is the only behavioural delta, and it is inert for `ANIL>1e-8`. **Confirm which constant exists in kyoshimi `TRCOMM`**:
```bash
grep -rnE '\bAMP\b|\bAMM\b' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trcom0.f90 /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trcomm_*.f90
```
Only `AMM` exists (`trcomm_const.f90:19`). Port FTAUI using `AMM`. **Do not substitute bpsd's `AMP`** — the two differ by ~1.7e-7 (CODATA-2006 vs 2018), which shifts `FTAUI` by ~8.6e-8 and breaks the 1e-10 baselines.

- [x] **Step 5: Capture a clean pre-port regression baseline run**

Run (must already have `tr/tr2` built; if not, `make -C tr tr2`):
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run
./run_tests.sh tr_m0904 && ./run_tests.sh tr_iter01 && ./run_tests.sh tr_tst2
```
Expected: each prints `CLOSED` and `OK: metrics match within tol=1e-10`. This is the green baseline every structural task must preserve. **Do not proceed if any case is red before porting.**

- [x] **Step 6: Commit the decisions**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add docs/superpowers/plans/2026-06-15-trx-tr-consolidation.md
git commit -m "docs(tr): record P1 trx->tr port decisions (MDLNF policy, FTAUE/FTAUI reconcile)"
```

---

## Task 2: Build the 1e-10 bpsi-`trx` reference oracle

> **DONE (as-built, 2026-07-10).** Commit `e8837d92`. Artefacts:
> `test_run/baselines/tr_fus_dt/{metrics.json,SOURCE.md}`, `test_run/inputs/tr_fus_dt.in`
> (force-added — root `.gitignore` has `*.in`), `test_run/test_definitions.conf`.
> Capture branch `ref/trx-regress-capture` @ bpsi `fa9dd493`, in the isolated worktree
> `task-trx-ref/` — **never merged**, and `task/` was never touched (Step 1 as written
> would have switched a dirty tree; it was replaced by `git worktree add`).
>
> Two things this task discovered that the plan did not anticipate:
> 1. **Constant reconciliation is mandatory.** bpsi `trx` takes `AEE`/`AME`/`AMP` from
>    `bpsd_constants` (CODATA-2018) via `plcomm`; kyoshimi `tr` uses the older values in
>    `trcomm_const` and never touches `plcomm`. All three differ by ~1e-7. The capture
>    branch shadows them in `trx`'s `trcomm_parm` (+ a three-site `libnf` patch, since
>    `libnf` reads `AMP` straight from `bpsd_constants`). `PI`/`VC`/`RMU0`/`EPS0` are
>    bit-identical between the trees and are left alone. See `SOURCE.md`.
> 2. **The case must be well-conditioned or the tolerance is meaningless.** The first
>    capture used `NTMAX=20`. A perturbation probe (`PN(1)` ±1e-12 relative, read every
>    `metrics.json` entry) measured an amplification of **2.8e11** there — O(1) scalars
>    `BETAP0`/`Q0`/`WPT` move by 1.4–28 %, so plain FP rounding (1e-16) yields ~1e-5 of
>    noise, five orders **above** the 1e-10 tolerance. Amplification is ~1e2 up to
>    `NTMAX=10` and jumps to ~4e11 at `NTMAX=12` (a discrete branch flip; profiles stay
>    physical). **The baseline is captured at `NTMAX=5`**, where amplification over the
>    whole of `metrics.json` is 76.5 (rounding → 7.7e-15, a 13000x margin) while
>    `model_pnf=1` vs `=0` still separate by 2.2e-4 in `WPT` (~2e6x the tolerance; the largest signal is `BETA0` at 1.6e-1, ~1.6e9x).
>
> **Task 7 must re-run the perturbation probe** if it ever changes `NTMAX`, and should
> confirm cross-host (Mac↔Linux, gfortran-15↔13.2) reproducibility before treating a
> mismatch as a port bug.

**Editorial note (Task 7, after the fact).** The figures in the quoted review
do not survive the five oracle corrections listed in
`test_run/baselines/tr_fus_dt_hot/SOURCE.md`; that file is authoritative. The
amplification of 76.5 was a product of the 1e6 reaction-rate error and is 1.00
once it is fixed. Task 7 did re-run the probe on the corrected binaries at the
same `NTMAX=5`: 1.00 for the 1 keV deck, 2.32 for the 10 keV deck that
replaced it as the primary oracle. Cross-host reproducibility is still
unconfirmed.

**Files:**
- Create: `task/trx/trregress.f90` (copy of the kyoshimi dumper)
- Modify: `task/trx/trloop.f90`, `task/trx/Makefile`
- Create: `task-kyoshimi/test_run/inputs/tr_fus_dt.in`, `task-kyoshimi/test_run/baselines/tr_fus_dt/metrics.json`

> These edits live on a throwaway branch in `task/` (the github-baseline checkout) used only to emit the reference dump. They are **not** merged into the canonical `tr`.

- [x] **Step 1: Create a reference-capture branch in the `task/` checkout**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task
git checkout -b ref/trx-regress-capture bpsi/develop
```

- [x] **Step 2: Copy the dumper into `trx`**
```bash
cp /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trregress.f90 \
   /Users/lihengyu/Research_Project/MS10/TASK/task/trx/trregress.f90
```
(`trx`'s `TRCOMM` exposes every ONLY-symbol the dumper needs — `NRMAX,NSMAX,NT,T,WPT,AJT,AJRFT,Q0,BETA0,BETAP0,BETAA,BETAN,TAUE1,TAUE2,ZEFF0,ALI,RQ1,RN,RT,AJ,QP` — verified in `trx/trrslt.f90 SUBROUTINE TRGLOB`.)

- [x] **Step 3: Add `trregress.f90` to the `trx` Makefile source list**

In `task/trx/Makefile`, find the `SRCS=` block (the line group containing `trrslt.f90`) and append ` trregress.f90` to it. Verify:
```bash
grep -n 'trregress' /Users/lihengyu/Research_Project/MS10/TASK/task/trx/Makefile
```
Expected: `trregress.f90` appears in `SRCS`.

- [x] **Step 4: Add the dump hook to `trx/trloop.f90`**

After the existing `USE` block (~line 22) add:
```fortran
      USE trregress, ONLY : tr_regress_dump_if_enabled
```
Immediately before the `RETURN` at the `9000 CONTINUE` end (~line 84-85) add:
```fortran
      CALL tr_regress_dump_if_enabled   ! reference capture (env-guarded)
```

- [x] **Step 5: Build the reference `trx` binary**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task/trx && make tr2
```
Expected: clean build producing `trx/tr2`. (Fix any `USE`/symbol issue before continuing — the dump only links what `TRGLOB` already computes.)

- [x] **Step 6: Create the DT-fusion regression input**

Create `task-kyoshimi/test_run/inputs/tr_fus_dt.in` as a `TRMENU` stdin script identical in geometry to `tr_m0904.in` (analytic `modelg=2`, self-contained, no eq dependency) **plus** a deuterium+tritium+alpha species set and `model_pnf=1`. Base it on `tr_m0904.in`; in its `&TR` namelist set: `NSMAX=4` with `PA=2.0,3.0,4.0,...`, `PZ=1.0,1.0,2.0,...` (e,D,T,He4 ordering matching `tr_prep_ns`), `model_pnf=1`, and a short `NTMAX`. **`NTMAX=5` (as built).** Do **not** use `NTMAX>=12`: the case is ill-conditioned there (see the as-built note above). `PA`/`PZ` are left at `trinit`'s NSMAX=4 defaults rather than set explicitly. Read `tr_m0904.in` first to copy its exact menu framing:
```bash
cat /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run/inputs/tr_m0904.in
```

- [x] **Step 7: Emit the bpsi-`trx` reference dump for the DT case**

The bpsi `trx` namelist uses `model_pnf`; run `trx/tr2` on the same physical input (translate the menu/namelist to `trx`'s `in/` format if keys differ — `trx` already supports `model_pnf`):
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task/trx
env TR_REGRESS_DUMP=1 ./tr2 < /path/to/trx-format-dt-input > /tmp/trx_dt.log
ls -l tr_regress.dat
```
Expected: `tr_regress.dat` written in `1PE24.16` format. (`trx`'s menu/namelist may need the keys spelled as in `trx/in/test01.in`; read that file to match.)

- [x] **Step 8: Convert the dump to the baseline JSON and store it**
```bash
mkdir -p /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run/baselines/tr_fus_dt
python3 /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run/scripts/extract_tr_metrics.py \
  /Users/lihengyu/Research_Project/MS10/TASK/task/trx/tr_regress.dat \
  > /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run/baselines/tr_fus_dt/metrics.json
head -5 /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run/baselines/tr_fus_dt/metrics.json
```
Expected: valid JSON with `NT`, `NRMAX`, `NSMAX`, `scalars`, `profile`. Add a `baselines/tr_fus_dt/SOURCE.md` noting "generated from bpsi/develop:trx @ <sha> via ref/trx-regress-capture, model_pnf=1 DT".

- [x] **Step 9: Register the new case in the harness**

In `task-kyoshimi/test_run/test_definitions.conf`, after the `tr_tst2` line add:
```
tr_fus_dt:tr:@inputs/tr_fus_dt.in:none:120:DT fusion (model_pnf=1) vs bpsi trx reference
```

- [x] **Step 10: Commit the oracle**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add test_run/inputs/tr_fus_dt.in test_run/baselines/tr_fus_dt/ test_run/test_definitions.conf
git commit -m "test(tr): add DT-fusion 1e-10 reference baseline captured from bpsi trx"
```
(The `task/` `ref/trx-regress-capture` branch is left as-is for re-capture of model_pnf=2/3/4 baselines later; it is never merged.)

---

## Task 3: Extract collision functions into `trcoll` + `trlib` modules

> **DONE (as-built, 2026-07-10).** Commits `2baa7948` (pure move) + `b795c9e6` (guard).
> Deviations forced by the code, all verified:
> - `COULOG`/`FTAUE`/`FTAUI` were **bare external** functions with **12 + 8 + 11 live call sites
>   across 9 files** (plus 4 for `HY`), not just `trcalc.f90`. Every caller bound them via a local `REAL(rkind)` declaration, so
>   each needed a `USE` **and** surgical removal of the name from a shared declaration line.
> - `HY` (external, in `trpnb.f90`) moved into `trlib` too, otherwise `trlib`'s `HY` and the external
>   `HY` would coexist as two silently-divergent live bodies (module mangling `__trlib_MOD_hy` never
>   collides with the external `hy_`, so the linker would NOT catch it).
> - `trcoll` exports `FTAUE`/`FTAUI` only and `USE trlib, ONLY : COULOG`. bpsi ships *both* lowercase
>   `coulomb_log` and uppercase `COULOG` with identical bodies; only one is kept.
> - `AMM` (not `AMP`) and `PZ(2)` (not `PZ(NS_D)`) — see RECORDED DECISIONS #3.
> - Makefile: `trlib.f90 trcoll.f90` **prepended to `SRCS_CORE`** (the earliest consumers are
>   `trcoef_turbulence`/`trcoef_resistivity`, and the PIC/`libtrapi.so` build has no per-file dep
>   rules, so list order is its only ordering guarantee); consumer object rules gained `.o`
>   prerequisites so `make -j` cannot race on `trlib.mod`/`trcoll.mod`.
> - Step 7's `run_tests.sh` is unusable locally (RECORDED DECISIONS #4). Gate used instead:
>   `pytest python/trlib/tests/test_equivalence.py --forked` → *1 passed, 1 xfailed* (unchanged), plus
>   a `tr_m0904` `TR_REGRESS_DUMP` dump that is **byte-identical** pre vs post (sha256 `56d09887…`).

**Files:**
- Create: `task-kyoshimi/tr/trcoll.f90`, `task-kyoshimi/tr/trlib.f90`
- Modify: `task-kyoshimi/tr/trcalc.f90` (remove inline funcs lines 1314-1391; `USE` the modules), `task-kyoshimi/tr/Makefile`

- [x] **Step 1: Create `tr/trcoll.f90` as a MODULE** (wrap bpsi's bare functions; apply the Step-4 reconcile decision)
```fortran
MODULE trcoll
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: coulomb_log, FTAUE, FTAUI
CONTAINS
! --- paste bpsi trx/trcoll.f90 bodies of coulomb_log, FTAUE, FTAUI here ---
! --- adopt the guard, but keep kyoshimi's PZ(2) and AMM (RECORDED DECISIONS #3) ---
END MODULE trcoll
```
Get the exact bodies:
```bash
git -C /Users/lihengyu/Research_Project/MS10/TASK/task show bpsi/develop:trx/trcoll.f90
```
Move the kyoshimi bodies between `CONTAINS` and `END MODULE`, keeping their `USE TRCOMM, ONLY: ...` lines. `AMM` and `PZ(2)` are **mandatory** (not conditional): kyoshimi `tr` has no `NS_D`, and bpsd's `AMP` is no longer equal to `AMM`. Only the `ABS(ANIL)` guard is taken from bpsi.

- [x] **Step 2: Create `tr/trlib.f90` as MODULE `trlib`** (`COULOG`, `HY`)
```bash
git -C /Users/lihengyu/Research_Project/MS10/TASK/task show bpsi/develop:trx/trlib.f90 \
  > /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trlib.f90
```
(bpsi `trx/trlib.f90` is already `MODULE trlib` with `PUBLIC COULOG, HY` — copy verbatim.)

- [x] **Step 3: Remove the inline collision functions from `trcalc.f90`**

Delete `FUNCTION COULOG` (lines 1314-1336), `FUNCTION FTAUE` (1346-1370), `FUNCTION FTAUI` (1374-1391) from `task-kyoshimi/tr/trcalc.f90`. Verify they are gone:
```bash
grep -nE 'FUNCTION (COULOG|FTAUE|FTAUI)' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trcalc.f90
```
Expected: no matches.

- [x] **Step 4: Wire the `USE` in `SUBROUTINE TRAJBS`**

In `tr/trcalc.f90 SUBROUTINE TRAJBS`, remove the local declaration `REAL(rkind):: FTAUE, FTAUI` (~line 820) and add to its `USE` block:
```fortran
      USE trcoll, ONLY : FTAUE, FTAUI
```
(The call sites at ~860-863 and ~945-948 stay unchanged.) If `COULOG` is referenced elsewhere in `trcalc`, add `USE trlib, ONLY : COULOG` there too.

- [x] **Step 5: Add the modules to the Makefile**

In `task-kyoshimi/tr/Makefile`, append `trcoll.f90 trlib.f90` to `SRCS_CORE` (the `trmdlt.f90` group on line ~46). Add dependency rules in the 505-541 block:
```make
$(OBJDIR)/trcoll.o : trcoll.f90 trcomm.f90
$(OBJDIR)/trlib.o  : trlib.f90 trcomm.f90
$(OBJDIR)/trcalc.o : trcalc.f90 trcomm.f90 trcoll.f90 trlib.f90 tr_cytran_mod.f90
```
(Do NOT add `-I../trlib` — kyoshimi `tr` has no `../trlib` dir; `trcoll`/`trlib` only `USE TRCOMM`.)

- [x] **Step 6: Build (static + shared)**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr
make tr2 && make libtrapi.so
```
Expected: clean build of both `tr2` and `libtrapi.so`.

- [x] **Step 7: Run the existing regression — must be UNCHANGED at 1e-10**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run
./run_tests.sh tr_m0904 && ./run_tests.sh tr_iter01 && ./run_tests.sh tr_tst2
```
Expected: all three `CLOSED` + `OK: metrics match within tol=1e-10`. (The collision math is unchanged for `ANIL>1e-8`, so the bootstrap-current path `TRAJBS` must reproduce the baseline exactly. If a case drifts, the guard/`NS_D`/`AMP` reconcile changed a number — investigate before continuing.)

- [x] **Step 8: Commit**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add tr/trcoll.f90 tr/trlib.f90 tr/trcalc.f90 tr/Makefile
git commit -m "refactor(tr): extract COULOG/FTAUE/FTAUI into trcoll+trlib modules (ported from trx)"
```

---

## Task 4: Add the fusion data model to the split `trcomm` (default OFF)

**Files:** Modify `task-kyoshimi/tr/trcomm_param.f90`, `trcomm_profile.f90`, `trcomm_globals.f90`, `trcomm.f90` (allocate driver).

> Route bpsi's monolithic `trcomm` fusion declarations into the correct kyoshimi sub-module. With `model_pnf=0`/`nnfmax=0` these arrays stay size-0 and inert.

- [ ] **Step 1: Add fusion control + dims to `trcomm_param.f90`**

In `MODULE trcomm_param` add (near the existing source-count integers `NNBMAX,NECMAX,...`):
```fortran
      INTEGER:: model_pnf            ! fusion reaction-set selector (0=off)
      INTEGER:: nnfmax               ! number of active fusion reactions
      INTEGER,PARAMETER:: NNFM=4     ! max fusion sources (bpsi trx)
```
Reference bpsi decls:
```bash
git -C /Users/lihengyu/Research_Project/MS10/TASK/task show bpsi/develop:trx/trcomm.f90 | grep -nE 'model_pnf|NNFM|nnfmax'
```

- [ ] **Step 2: Add radial fusion/source arrays to `trcomm_profile.f90`**

In `MODULE trcomm_profile`, alongside the `RN/RT/RU`, `PNB/SNB/PNF/SNF` block, declare (verbatim shapes from bpsi `trx/trcomm.f90`):
```fortran
      INTEGER,DIMENSION(:),ALLOCATABLE :: model_nnf, ns1_nnf, ns2_nnf, nsp_nnf
      REAL(rkind),DIMENSION(:),ALLOCATABLE :: wgt_nnf, eng_nnf, enn_nnf, ENF_NNF
      REAL(rkind),DIMENSION(:,:,:),ALLOCATABLE :: SNF_NSNNFNR, PNF_NSNNFNR, PNFIN_NSNNFNR, PNFCL_NSNNFNR
      REAL(rkind),DIMENSION(:,:),ALLOCATABLE :: SNF_NSNR, PNF_NSNR, PNFIN_NSNR, PNFCL_NSNR
      REAL(rkind),DIMENSION(:,:),ALLOCATABLE :: SNF_NNFNR, PNF_NNFNR, SNFNN_NNFNR, PNFNN_NNFNR
      REAL(rkind),DIMENSION(:),ALLOCATABLE :: SNFNN_NNF, PNFNN_NNF, SNFNN_NR, PNFNN_NR
      REAL(rkind),DIMENSION(:,:),ALLOCATABLE :: TAUF                      ! (NNF,NR)
      REAL(rkind),DIMENSION(:,:,:),ALLOCATABLE :: AJNB_NSNNBNR            ! (NS,NNB,NR)
      REAL(rkind),DIMENSION(:,:,:),ALLOCATABLE :: PEC_NSNECNR, PLH_NSNLHNR, PIC_NSNICNR
```

- [ ] **Step 3: Add fusion totals to `trcomm_globals.f90`**

In `MODULE trcomm_globals`:
```fortran
      REAL(rkind),DIMENSION(:),ALLOCATABLE :: ANF0, TF0, ANFAV, TFAV, WFT  ! (NFM)
```

- [ ] **Step 4: Allocate the new arrays (guarded) in the allocate driver**

In `task-kyoshimi/tr/trcomm.f90` `SUBROUTINE ALLOCATE_TRCOMM` (lines 35-94), after the existing `allocate_trcomm_profile`/`allocate_trcomm_globals` calls (or inside those routines in `trcomm_profile.f90:137-461` / `trcomm_globals.f90`), add — mirroring bpsi `trx/trcomm.f90 allocate_trcomm`:
```fortran
      NFMAX = NNBMAX + NNFMAX
      IF(NFMAX.GT.0) ALLOCATE(ANF0(NFMAX),TF0(NFMAX),ANFAV(NFMAX),TFAV(NFMAX),WFT(NFMAX))
      IF(NNFMAX.GT.0) THEN
         ALLOCATE(model_nnf(NNFMAX),ns1_nnf(NNFMAX),ns2_nnf(NNFMAX),nsp_nnf(NNFMAX))
         ALLOCATE(wgt_nnf(NNFMAX),eng_nnf(NNFMAX),enn_nnf(NNFMAX),ENF_NNF(NNFMAX))
         ALLOCATE(SNF_NSNNFNR(NSMAX,NNFMAX,NRMAX),PNF_NSNNFNR(NSMAX,NNFMAX,NRMAX), &
                  PNFIN_NSNNFNR(NSMAX,NNFMAX,NRMAX),PNFCL_NSNNFNR(NSMAX,NNFMAX,NRMAX))
         ALLOCATE(SNF_NSNR(NSMAX,NRMAX),PNF_NSNR(NSMAX,NRMAX),PNFIN_NSNR(NSMAX,NRMAX),PNFCL_NSNR(NSMAX,NRMAX))
         ALLOCATE(SNF_NNFNR(NNFMAX,NRMAX),PNF_NNFNR(NNFMAX,NRMAX),SNFNN_NNFNR(NNFMAX,NRMAX),PNFNN_NNFNR(NNFMAX,NRMAX))
         ALLOCATE(SNFNN_NNF(NNFMAX),PNFNN_NNF(NNFMAX),SNFNN_NR(NRMAX),PNFNN_NR(NRMAX),TAUF(NNFMAX,NRMAX))
      END IF
      IF(NNBMAX.GT.0) ALLOCATE(AJNB_NSNNBNR(NSMAX,NNBMAX,NRMAX))
      IF(NECMAX.GT.0) ALLOCATE(PEC_NSNECNR(NSMAX,NECMAX,NRMAX))
      IF(NLHMAX.GT.0) ALLOCATE(PLH_NSNLHNR(NSMAX,NLHMAX,NRMAX))
      IF(NICMAX.GT.0) ALLOCATE(PIC_NSNICNR(NSMAX,NICMAX,NRMAX))
```
Follow the defensive zero-init convention (`SNF_NSNNFNR(:,:,:) = 0.D0` etc.) used by `trcomm_mtx`/`globals` to avoid `libtrapi.so` heap-reuse NaNs. Add a `nnfmax_save` reallocation guard mirroring bpsi.

- [ ] **Step 5: Mirror DEALLOCATE + guarded DEALLOCATE_ERR**

Add matching `DEALLOCATE(...)` for every array above in `deallocate_trcomm_profile`/`deallocate_trcomm_globals`, and `IF(ALLOCATED(x)) DEALLOCATE(x)` in the `deallocate_err_*` routines (compare bpsi `DEALLOCATE_TRCOMM`/`DEALLOCATE_ERR_TRCOMM`).

- [ ] **Step 6: Set defaults `model_pnf=0`, `nnfmax=0` in `trinit.f90`**

In `task-kyoshimi/tr/trinit.f90`, near the existing `MDLNF=0` default, add:
```fortran
      model_pnf = 0
      nnfmax    = 0
```

- [ ] **Step 7: Add Makefile dep edges for the touched modules** (no new sources yet)

The split-module objects already rebuild on `.f90` change; confirm `make` re-compiles them:
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr && make tr2 && make libtrapi.so
```
Expected: clean build (no executable physics added yet — only data + zero-size allocs).

- [ ] **Step 8: Regression must be UNCHANGED**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run
./run_tests.sh tr_m0904 && ./run_tests.sh tr_iter01 && ./run_tests.sh tr_tst2
```
Expected: all `OK ... 1e-10`. (`nnfmax=0` ⇒ no fusion arrays allocated ⇒ inert.)

- [ ] **Step 9: Commit**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add tr/trcomm_param.f90 tr/trcomm_profile.f90 tr/trcomm_globals.f90 tr/trcomm.f90 tr/trinit.f90
git commit -m "feat(tr): add model_pnf fusion data model to split trcomm (inert, default off)"
```

---

## Task 5: Port `libnf.f90` (fusion reaction tables + reactivity)

**Files:** Create `task-kyoshimi/tr/libnf.f90`; Modify `task-kyoshimi/tr/Makefile`.

- [ ] **Step 1: Copy `libnf.f90` from bpsi `trx`**
```bash
git -C /Users/lihengyu/Research_Project/MS10/TASK/task show bpsi/develop:trx/libnf.f90 \
  > /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/libnf.f90
```

- [ ] **Step 2: Adapt `USE trcomm` references to the split modules**

`libnf`'s `set_usigmav_nf` does `USE trcomm` for `model_pnf,nnfmax,RKEV` and the `NS_*` species ids. In kyoshimi, `RKEV` lives in `trcomm_const`/`trcom0`, `model_pnf`/`nnfmax` in `trcomm_param`, and `NS_D/NS_T/NS_He4/NS_H/NS_He3/NS_He5` come from `plcomm`. The umbrella `MODULE TRCOMM` re-exports the sub-modules, so the simplest correct change is to keep `USE TRCOMM` (the umbrella) where it resolves all of these. Verify the umbrella re-exports `model_pnf`/`nnfmax`/`NS_*`:
```bash
grep -nE 'model_pnf|nnfmax|NS_D|NS_He4' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trcomm.f90
grep -nE 'NS_D|NS_He4|NS_He5' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/pl/plcomm.f90
```
If the umbrella does not re-export `NS_*`, add `USE plcomm, ONLY : NS_e,NS_D,NS_T,NS_He4,NS_He3,NS_H,NS_He5` to `set_usigmav_nf`. Keep `USE libspl1d` / `USE libde` as-is (those libs exist in `lib/`). **DROP `USE bpsd_constants`.** ⚠ The oracle contract (`test_run/baselines/tr_fus_dt/SOURCE.md`, "Contract for Tasks 4-6") requires the ported `libnf` to take its constants from kyoshimi `TRCOMM` (=`trcomm_const`, CODATA-2006). bpsi's `libnf` reads `AMP` straight from `bpsd_constants` for the DT reduced mass (`pm_local = PA(...)*AMP`); keeping that import pulls the CODATA-2018 `AMP`, lands ~1.7e-7 off the reference, and makes Task 7's 1e-10 gate fail. Use `AMM` from `TRCOMM`.

- [ ] **Step 3: Add `libnf.f90` to the Makefile**

Append `libnf.f90` to `SRCS_CORE` (line ~46 group), and add dep rules:
```make
$(OBJDIR)/libnf.o : libnf.f90 trcomm.f90
```
Place `libnf.f90` so it compiles after `trcomm.f90` (SRCM is built before SRCS_CORE, so ordering within SRCS_CORE is fine; the dep rule enforces the `.mod`).

- [ ] **Step 4: Build (still inert — nothing calls `set_usigmav_nf` yet)**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr && make tr2 && make libtrapi.so
```
Expected: clean build. Resolve any missing-symbol from the `USE` adaptation (Step 2) before continuing.

- [ ] **Step 5: Regression unchanged**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run
./run_tests.sh tr_m0904 && ./run_tests.sh tr_iter01 && ./run_tests.sh tr_tst2
```
Expected: all `OK ... 1e-10`.

- [ ] **Step 6: Commit**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add tr/libnf.f90 tr/Makefile
git commit -m "feat(tr): port libnf fusion reaction tables from trx (unwired)"
```

---

## Task 6: Rewrite `trpnf.f90` (generic `tr_pnf`) and wire dispatch

> **⚠ OVERRIDDEN by RECORDED DECISIONS (Option A).** Do **NOT** retire the `MDLNF` `SELECT CASE`.
> In Step 3, ADD `CALL tr_pnf` as an *additive* branch **gated by `model_pnf>0`**, alongside the kept
> `MDLNF` path (the old 1‑D `SNF(NR)` path stays for `MDLNF>0`). The "retire/replace MDLNF" wording in
> the Files line, Step 3, and the Step‑4 commit message below is **superseded** — the two fusion paths
> coexist and `model_pnf=0` default keeps the 3 existing baselines bit‑for‑bit.

**Files:** Rewrite `task-kyoshimi/tr/trpnf.f90`; Modify `trprep.f90`, `trcalc.f90`, `trexec.f90`; per RECORDED DECISIONS (Option A), **keep** `MDLNF` and add `model_pnf` additively (do **not** retire).

- [ ] **Step 1: Extend `trpnf.f90` with bpsi `trx`'s `tr_prep_pnf` + `tr_pnf` (additive; keep `TRNFDT`/`TRNFDHe3`)**
```bash
git -C /Users/lihengyu/Research_Project/MS10/TASK/task show bpsi/develop:trx/trpnf.f90 \
  > /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trpnf.f90
```
Then adapt its `USE TRCOMM`/`USE libnf`/`USE trlib` lines if the split umbrella needs explicit `ONLY` lists (build will tell you). This **adds** the generic `nnf=1..nnfmax` loop (gated by `model_pnf>0`) writing `SNF_NSNNFNR`/`PNF_NSNNFNR`/`SNFNN_NNFNR` and `TAUF`. **Do NOT delete `TRNFDT`/`TRNFDHe3`** — Option A keeps the `MDLNF SELECT CASE`, which calls them, and `tr_m0904`/`tr_iter01` run `MDLNF=1`.

- [ ] **Step 2: Insert the prep sequence in `trprep.f90`**

In `task-kyoshimi/tr/trprep.f90 SUBROUTINE tr_prep`, add `USE libnf, ONLY: set_usigmav_nf` and `USE trpnf, ONLY: tr_prep_pnf`, and order the calls (mirroring bpsi `trx/trprep.f90`):
```fortran
      CALL tr_prep_ns                 ! resolves NS_* from PA/PZ  (must precede set_usigmav_nf)
      CALL set_usigmav_nf             ! sets nnfmax from model_pnf, builds reaction tables
      NFMAX = NNBMAX + NNFMAX
      CALL allocate_trcomm(ierr)      ! (existing call — now sizes fusion arrays)
      ...
      CALL tr_prep_pnf                ! fills ns1_nnf/ns2_nnf/nsp_nnf/wgt/eng/enn from libnf
```
Check the current order:
```bash
grep -nE 'tr_prep_ns|allocate_trcomm|tr_prep_pnf|set_usigmav_nf|CALL tr_prof' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trprep.f90
```
Ensure `set_usigmav_nf` runs **after** `tr_prep_ns` (needs `NS_*`) and **before** `allocate_trcomm` (needs `nnfmax`).

- [ ] **Step 3: Add `CALL tr_pnf` gated by `model_pnf>0` in `trcalc.f90` (Option A — additive; do NOT retire `MDLNF`)**

> **OVERRIDE (see RECORDED DECISIONS #2, Option A):** the original "replace the `MDLNF` `SELECT CASE`
> with `CALL tr_pnf`" wording is **superseded**. `model_pnf` is an **additive** path (default off); the
> legacy `MDLNF`/`SIGMAM` DT path is **kept bit-for-bit** so the three fusion-ON baselines stay green.

In `task-kyoshimi/tr/trcalc.f90` (around line 132, the `SELECT CASE(MDLNF)` block that currently selects `TRNFDT`/`TRNFDHe3`), **add the `model_pnf>0` dispatch alongside the existing `MDLNF` block** (per Task-1 Step-3 policy, Option A):
- Add `USE trpnf, ONLY : tr_pnf` to the subroutine's `USE` block.
- Insert `CALL tr_pnf` **inside an `IF(model_pnf>0) THEN` guard** before the source-assembly that builds `SSIN`/`PIN` (~line 135-185).
- **Only in the `model_pnf>0` branch**, read the reduced `SNF_NSNR(NS,NR)`/`PNFCL_NSNR(NS,NR)` (mirror bpsi `trx/trcalc.f90` lines ~135-185; get them with `git show bpsi/develop:trx/trcalc.f90`). The legacy `MDLNF` branch keeps reading the old 1-D `SNF(NR)`/`PNF(NR)` **unchanged**.
- **Option A (decided):** the `MDLNF>0 .AND. model_pnf==0` path stays exactly as-is — no remapping, no behaviour change — so `SSIN` is still populated for legacy inputs and the three fusion-ON baselines hold bit-for-bit.

- [ ] **Step 4: Add the fast-ion fusion rows in `trexec.f90`**

In `task-kyoshimi/tr/trexec.f90 SUBROUTINE TRMTRX`, add the fast-ion fusion equation rows over `NNBMAX+NNF` (mirror bpsi `trx/trexec.f90` lines 571/646/723):
```fortran
      Y(NNBMAX+NNF,NR) = (1.D0 - PRV/TAUF(NNF,NR))*YV(NNBMAX+NNF,NR) &
                       + PNF_NSNNFNR(NSP_NNF(NNF),NNF,NR)*DT/(RKEV*1.D20)
```
Confirm the target uses the same `NNBMAX+NNF` fast-ion row indexing (`NFMAX` rows):
```bash
grep -nE 'NNBMAX|NFMAX|NNB,NR|fast' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trexec.f90 | head
```

- [ ] **Step 5: Update Makefile dep edges**
```make
$(OBJDIR)/trpnf.o  : trpnf.f90 libnf.f90 trcomm.f90 trlib.f90
$(OBJDIR)/trprep.o : trprep.f90 trcomm.f90 libnf.f90 trpnf.f90
$(OBJDIR)/trexec.o : trexec.f90 trcomm.f90
```

- [ ] **Step 6: Build**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr && make tr2 && make libtrapi.so
```
Expected: clean build.

- [ ] **Step 7: Regression UNCHANGED with `model_pnf=0`** (the wiring must be inert when off)
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run
./run_tests.sh tr_m0904 && ./run_tests.sh tr_iter01 && ./run_tests.sh tr_tst2
```
Expected: all `OK ... 1e-10`. (If a case drifts, `tr_pnf` is writing into the source vectors even when `nnfmax=0` — guard it with `IF(NNFMAX.GT.0)`.)

- [ ] **Step 8: Commit**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add tr/trpnf.f90 tr/trprep.f90 tr/trcalc.f90 tr/trexec.f90 tr/Makefile
git commit -m "feat(tr): wire additive model_pnf fusion dispatch (tr_prep_pnf/tr_pnf/TRMTRX), default off; MDLNF path kept (Option A)"
```

---

## Task 7: Enable & validate DT fusion against the bpsi-`trx` reference

**Files:** none new (uses the `tr_fus_dt` case from Task 2).

**Editorial note (after the fact).** The four steps below are kept as written,
but three of their expectations do not survive what Task 7 measured. Read this
first; `test_run/baselines/tr_fus_dt_hot/SOURCE.md` is authoritative.

- **`tr_fus_dt` is no longer the case to drive.** A 10 keV variant,
  `tr_fus_dt_hot`, replaced it as the primary oracle: fusion signal rel `WPT`
  1.11e-3 against this deck's 6.2e-9. This deck is retained as a weak
  companion.
- **1e-10 is not reachable, and not for a fusion reason.** Step 1's "OK:
  metrics match within tol=1e-10" does not happen: 308 of 514 fields exceed it
  on this deck. The residual is a transport-layer difference between the two
  forks -- at `NTMAX=0` the two codes agree to rounding on this deck (499 of
  514 value fields bit-identical, worst 5.0e-16; 510 of 514 and 5.7e-16 on the
  10 keV deck) and diverge from the first step. So Step 2's four suspects, all
  fusion-side, are the wrong places to look; that list was written before the
  cause was located. What Task 7 validates instead is the *differential*
  (`model_pnf=1` minus `=0`, taken in each code and compared), pinned by
  `test_model_pnf_dispatch.py::test_fusion_differential_matches_the_trx_reference`.
- **Step 3 cannot be done as written.** `tr` carries one fusion fast-ion slot,
  so `model_pnf>=2` evaluates its reaction set but publishes nothing --
  `test_model_pnf_ge_2_stays_diagnostic_only` pins that gate. There is no
  `model_pnf=2,3,4` solve to drive to 1e-10 until `NFM` is widened.
- The `cd .../task-kyoshimi/test_run` paths are stale: the work is in
  `task-p1-libnf`, and `task-kyoshimi` has no `tr_fus_dt` baseline. And
  `run_tests.sh` needs `declare -A`, so it does not run on this Mac's bash 3.2
  at all -- the figures above were measured by driving `tr/tr2` directly.

- [ ] **Step 1: Run the DT-fusion case — expect RED first if anything is mis-wired**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run
./run_tests.sh tr_fus_dt
```
Expected eventually: `CLOSED` + `OK: metrics match within tol=1e-10`. On mismatch, `compare_metrics.py` prints the first ≤50 drifting keys with `rel_err` — that names the exact `TRCOMM` scalar/profile (e.g. `WPT`, `SNF`-derived) that diverges from bpsi `trx`.

- [ ] **Step 2: Debug to 1e-10** (iterate). Common causes, in order: species-id resolution (`NS_D/NS_T/NS_He4` order in the input), the `model_pnf` CASE table in `set_usigmav_nf` (must be byte-faithful to bpsi), the spline build (`SPL1D` over `usvnf_dt`), and the `SSIN`/`PIN` reduction (`SNF_NSNR` sign/species mapping). Re-`make tr2` and re-run after each fix.

- [ ] **Step 3: Capture & validate `model_pnf=2,3,4` references** (DD, DHe3, full set)

For each, on the `task/` `ref/trx-regress-capture` branch, run `trx/tr2` with the corresponding `model_pnf` input under `TR_REGRESS_DUMP=1`, extract to `baselines/tr_fus_<m>/metrics.json`, add a `test_definitions.conf` row, then run the kyoshimi case and drive it to 1e-10. (Repeat Task 2 Steps 7-9 + Task 7 Steps 1-2 per reaction set.)

- [ ] **Step 4: Commit the validated fusion**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add test_run/
git commit -m "test(tr): validate model_pnf=1..4 fusion vs bpsi trx at 1e-10"
```

---

## Task 8: Port species-resolved NBI/RF arrays (if used by merged physics)

**Files:** Modify `task-kyoshimi/tr/trpnb.f90`, `trcalc.f90`, source routines.

- [ ] **Step 1: Determine whether the merged physics actually consumes `AJNB_NSNNBNR`/`PEC_/PLH_/PIC_NSN*`**
```bash
git -C /Users/lihengyu/Research_Project/MS10/TASK/task show bpsi/develop:trx/trpnb.f90 | grep -nE 'AJNB_NSNNBNR|PEC_NSNECNR'
grep -nE 'AJNB|PEC_NSNECNR' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr/trpnb.f90
```
If bpsi `trx` writes these and the kyoshimi `tr` NBI/RF current path differs, port the species-resolved assembly from bpsi `trx/trpnb.f90`/`trcalc.f90`. (Arrays already declared+allocated in Task 4.) If the kyoshimi `tr` NBI path already produces equivalent currents, **skip** — these arrays were declared for completeness and stay inert.

- [ ] **Step 2: If porting, mirror bpsi assembly, rebuild, and re-run all regression**
  (NOT including `tr_fus_dt` / `tr_fus_dt_hot` -- see the gate note below.)
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr && make tr2 && make libtrapi.so
cd ../test_run && ./run_tests.sh tr_m0904 && ./run_tests.sh tr_iter01 && ./run_tests.sh tr_tst2
```
Expected: all `OK ... 1e-10`. `tr_fus_dt` and `tr_fus_dt_hot` are deliberately
NOT in this gate -- both are registered as expected-drift (see the Task 7
editorial note and `test_definitions.conf`), and `run_tests.sh` hard-codes
1e-10 with no tolerance field in the conf format, so including either would
make the gate permanently red with no repair short of editing the harness.

- [ ] **Step 3: Commit (only if Step 1 required a port)**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add tr/trpnb.f90 tr/trcalc.f90
git commit -m "feat(tr): port species-resolved NBI/RF current arrays from trx"
```

---

## Task 9: Expose `model_pnf`/`nnfmax` through the C-ABI / registry / MCP

**Files:** Modify `task-kyoshimi/tr/trparm.f90`, `tr_param_registry.f90`; verify `python/trlib`, `tr_mcp`.

- [ ] **Step 1: Add the namelist keys** to `/TR/` in `tr/trparm.f90` (after `MDLNF` in the `NAMELIST /TR/` line ~64 and the echo lines ~95/145):
```fortran
      ... MDLST, MDLNF, model_pnf, nnfmax, IZERO, MODELG, ...
```

- [ ] **Step 2: Register in `tr_param_registry.f90`** (mirror the `MDLNF` entry at line 141):
```fortran
    CASE ("model_pnf"); model_pnf = INT(value)
    CASE ("nnfmax");    nnfmax    = INT(value)
```
and add `model_pnf, nnfmax` to the `USE trcomm_param` ONLY-list at line ~49.

- [ ] **Step 3: Rebuild the shared lib and run the C-ABI gate**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr
make libtrapi.so && make tr_api_check_all
```
Expected: `Phase L-6 tr_api_check_all OK`.

- [ ] **Step 4: Run the Python FFI / wrapper / equivalence layers**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/test_run
./run_tests.sh trlib_equivalence
# plus the tr c_abi/ffi/wrapper cases defined in test_definitions.conf
grep -E '^tr.*(_c_abi|_ffi|_wrapper)' test_definitions.conf | cut -d: -f1 | while read t; do ./run_tests.sh "$t"; done
```
Expected: all PASS (the libtrapi.so replay matches Phase-0 baselines at 1e-10; new keys default to 0 so prior behavior is preserved).

- [ ] **Step 5: Verify the MCP surface exposes the new params**
```bash
grep -rnE 'model_pnf|nnfmax' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/python/trlib /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/python/mcp-servers/tr_mcp
```
`tr_mcp describe_parameters` derives from the registry, so no MCP code change is needed — confirm `model_pnf`/`nnfmax` appear. Per CLAUDE.md, the remote needs `make libtrapi.so` rebuilt for the new tool surface.

- [ ] **Step 6: Commit**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add tr/trparm.f90 tr/tr_param_registry.f90
git commit -m "feat(tr): expose model_pnf/nnfmax via namelist, param registry, and MCP"
```

---

## Task 10: Archive `trx` and `trm`; final full regression

**Files:** Move `task-kyoshimi/trx/` → `archive/trx/`, `task-kyoshimi/trm/` → `archive/trm/`; Modify top-level `Makefile`.

- [ ] **Step 1: Move the retired variants (preserve history)**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
mkdir -p archive
git mv trx archive/trx
git mv trm archive/trm
```

- [ ] **Step 2: Drop `trx`/`trm` from the top-level Makefile clean targets**

In `task-kyoshimi/Makefile`, remove the `(cd trx; make clean)` / `(cd trm; make clean)` lines (and any `trx`/`trm` from `all:`/`veryclean:`). Verify:
```bash
grep -nE '\btrx\b|\btrm\b' /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/Makefile
```
Expected: no remaining build references (archive/ is not built).

- [ ] **Step 3: Full regression — everything green**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi/tr && make tr2 && make libtrapi.so && make tr_api_check_all
cd ../test_run && ./run_tests.sh tr_m0904 && ./run_tests.sh tr_iter01 && ./run_tests.sh tr_tst2 && ./run_tests.sh trlib_equivalence
```
Expected: all `CLOSED` + `OK ... 1e-10` + `tr_api_check_all OK`. `tr_fus_dt`
and `tr_fus_dt_hot` are excluded for the reason in the Task 7 editorial note;
`tr_fus_dt_hot`'s guard is
`test_model_pnf_dispatch.py::test_fusion_differential_matches_the_trx_reference`,
which the pytest job already runs.  `tr_fus_dt` has **no** automated guard --
nothing in `python/` reads `test_run/baselines/tr_fus_dt/`.  It is retained as
documentation of the weak-signal case, not as a test.

- [ ] **Step 4: Commit**
```bash
cd /Users/lihengyu/Research_Project/MS10/TASK/task-kyoshimi
git add -A
git commit -m "refactor(tr): archive trx and trm; tr is now the canonical transport module"
```

- [ ] **Step 5: Push to the user's fork (per the design's never-push-upstream rule)**
```bash
git push myfork kyoshimi-develop
```
(Then sync + smoke-test the remote per CLAUDE.md: `ssh li@163.220.179.127 'cd /home/li/task/task-kyoshimi && git pull myfork kyoshimi-develop && cd tr && make libtrapi.so'`, then restart the remote dev server.)

---

## Deferred (documented, not in P1 core)

- **`trtglf.f90` (TGLF):** blocked — needs the external GACODE TGLF library (`tglf_interface` module, `tglf_run`), absent from both trees. Port only after bundling/installing GACODE TGLF and adding its lib to `tr/Makefile LIBS` + `-I` for `tglf_interface.mod`. Track as a separate task.
- **`trsigmavnf.f90` (`sigmav_DTmm`):** legacy alternative reactivity path, NOT in bpsi `trx/Makefile SRCS`, not wired into `tr_pnf`. Port only if a model needs it.
- **`trm`'s `trfixed.f90` (fixed-profile mode):** optional capability. Port as a `tr` mode only if the fixed-profile workflow is wanted; otherwise it stays archived.

---

## Self-Review notes (spec coverage)

- Spec P1 "hand-port set" → Tasks 3 (trcoll/trlib), 5 (libnf), 6 (trpnf/dispatch), 8 (NBI/RF arrays); CYTRAN already done (no task); TGLF/trsigmavnf/trfixed → Deferred. ✓
- Spec P1 "fold tr's plcomm consolidation" → covered by reusing the umbrella `TRCOMM`/`plcomm` re-export in Tasks 5-6 (`NS_*`, `model_pnf` resolution); the broader plcomm de-dup of `RR/RA/BB` is P2 and intentionally NOT pulled in here to keep P1 fusion-focused. (If desired in P1, add as a Task 6.5 — but the spec assigns the systematic dedup to P2.)
- Spec P1 verification ("unported paths 1e-10 vs current tr; ported paths 1e-10 vs bpsi trx") → Tasks 3/4/5/6 Step "regression UNCHANGED" + Tasks 2/7 "vs bpsi trx reference". ✓
- Spec "archive trx/trm" → Task 10. ✓
- Spec "C-ABI/MCP refresh" → Task 9. ✓
