# WR ライブラリ化 Phase L-2: C ABI Foundation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** WR モジュールに C ABI の足場として `wr_state.f90`、`wr_api.f90` (stub)、`wr_api.h` を新設する。L-2 の段階では `wr_set_param` は未実装だが、`wr_init / wr_run / wr_get_state / wr_finalize` の 4 関数は最低限動く（既存 `wr_init/wr_setup/wr_exec` を呼ぶ thin wrapper）。

**Architecture:** TR の Phase L-2 と同じ 5 関数 C ABI 設計を WR にミラーリング。ただし WR は時間発展ループを持たず ray tracing 1 回で終わるため、`wr_run` の引数は `nray_request` (= override 後に走らせる ray の本数。0 なら namelist の `NRAYMAX` を尊重) とし、内部で `wr_setup → wr_exec` を呼び出す。`wr_state_t` は L-0 dump で扱った量と同じセット（per-ray `RAYS_END` と minor/major profile）を固定サイズ配列で公開。`wr_param_registry` は L-3 で別途実装するため、本フェーズの `wr_set_param` は「常に `ierr=99` (not implemented)」を返す stub。Makefile は L-1 の `SRCS_CORE` に新規 `SRCS_API` を加える形だが、本フェーズではまだ `libwrapi.so` 自体は作らず（L-4）、`libwr.a` に組み込むだけ。

**Tech Stack:** Fortran 90 (`ISO_C_BINDING`, `BIND(C)`), C ヘッダ (固定サイズ配列), make。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 4 (C ABI) と Phase L-2。

---

## モジュール調査サマリ

L-2 で使う既存 WR 内部 API:

| 既存関数 | モジュール | 引数 | 役割 |
|---|---|---|---|
| `wr_init` | `wrinit` | なし | namelist デフォルト値設定 |
| `wr_parm(MODE,KIN,IERR)` | `wrparm` | `MODE=2` で line input | namelist 読み込み |
| `wr_allocate` | `wrcomm` | なし | `RAYS, RAYIN, *_NRAY` 等を ALLOCATE |
| `wr_setup(ierr)` | `wrsetup` | `out: ierr` | ray/beam セットアップ |
| `wr_exec(nstat,ierr)` | `wrexec` | `out: nstat, ierr` | 実行 + L-0 dump |
| `wr_deallocate` | `wrcomm` | なし | DEALLOCATE 群 |

`PROGRAM wr` の流れ (`wrmain.f90` 参照):
```
mtx_initialize → GSOPEN → pl_init → EQINIT → dp_init → wr_init
  → OPEN(7,SCRATCH) → wr_parm(1,'wrparm',IERR)  ← namelist file 読み込み
  → wr_menu → CLOSE(7) → GSCLOS → mtx_finalize
```

L-2 ではこのうち **graphics 系 (`GSOPEN/GSCLOS`) と `wr_menu` を排除**、`mtx_initialize/finalize` は MPI なしのシングルプロセスならスキップ可能（`pl_init/dp_init/wr_init` は呼ぶ）。`wr_parm` 経由ではなく、L-3 完成までは「init 直後の default 値で `wr_setup → wr_exec` を呼ぶ」だけの最小限フローでテスト。

WR の状態量上限は (L-0 dump 経験から):
- `WR_MAX_NRAYMAX = 100` （`wrcomm.f90` の `NRAYM=100` パラメータと一致）
- `WR_MAX_NRSMAX = 200` （標準 100、余裕 ×2）
- `WR_MAX_NRLMAX = 400` （標準 200、余裕 ×2）

メモリ占有: `100 × 8 + 100 × 8 + 200 × 2 × 8 + 400 × 2 × 8 = 11.2 KB`、十分小さい。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wr/wr_state.f90` | 新規 | `MODULE wr_state`：`TYPE, BIND(C) :: wr_state_c` を定義（C ヘッダの `wr_state_t` と一対一対応） |
| `wr/wr_api.f90` | 新規 | `MODULE wr_api`：5 つの `BIND(C)` 関数。L-2 では `wr_set_param` は stub |
| `wr/wr_api.h` | 新規 | C ヘッダ：`wr_state_t` struct と 5 関数プロトタイプ |
| `wr/Makefile` | 修正 | `SRCS_API = wr_state.f90 wr_api.f90` を追加し、`libwr.a` に組み込み |
| `wr/tests/c_abi/test_abi_stub.c` | 新規 | C 言語の最小スモークテスト（`wr_init → wr_run → wr_get_state → wr_finalize`） |
| `wr/tests/c_abi/Makefile` | 新規 | C テスト用 Makefile（`libwr.a` + 依存 `.a` を直接リンク） |

**方針:**
- ソースは additive のみ（既存ファイル無修正）。
- `wr_api.f90` は thin wrapper：L-3 完了後に `wr_set_param` を実装するため、本フェーズではコメントで明示しつつ stub を返す。
- C テストは「init/finalize サイクルがクラッシュしない」「`wr_get_state` が dimensions を返す」だけの最小限 smoke test。L-6 で本格化。

---

## Task 1: ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L2-c-abi
```

- [ ] **Step 2: L-1 の `SRCS_CORE` 等の Makefile 構造が存在することを確認**

Run:
```bash
grep -n "SRCS_CORE\|SRCS_GRAPHICS\|SRCS_MENU" /home/k-yoshimi/program/task/wr/Makefile
```
Expected: 3 グループが定義されている（L-1 完了状態）。

- [ ] **Step 3: マーカーコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wr): start Phase L-2 C ABI foundation"
```

---

## Task 2: `wr/wr_state.f90` を新規作成

**Files:**
- Create: `wr/wr_state.f90`

- [ ] **Step 1: モジュール作成**

Create `/home/k-yoshimi/program/task/wr/wr_state.f90`:
```fortran
! wr_state.f90
!
! C-interoperable state struct definition for the WR library API.
! Mirrors wr_api.h::wr_state_t.

MODULE wr_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PUBLIC

  ! Upper bounds (must match wr_api.h)
  INTEGER(C_INT), PARAMETER :: WR_MAX_NRAYMAX = 100
  INTEGER(C_INT), PARAMETER :: WR_MAX_NRSMAX  = 200
  INTEGER(C_INT), PARAMETER :: WR_MAX_NRLMAX  = 400

  TYPE, BIND(C) :: wr_state_c
     ! Dimensions (actual runtime values; <= WR_MAX_*)
     INTEGER(C_INT) :: nraymax
     INTEGER(C_INT) :: nrsmax
     INTEGER(C_INT) :: nrlmax
     ! Global peak power location/value
     REAL(C_DOUBLE) :: pos_pwrmax_rs
     REAL(C_DOUBLE) :: pwrmax_rs
     REAL(C_DOUBLE) :: pos_pwrmax_rl
     REAL(C_DOUBLE) :: pwrmax_rl
     ! Per-ray scalars: NSTP_END(j), pwr peak (rs/rl) per ray, end-state RAYS(0:NEQ,end,j) with NEQ=8 ⇒ 9 elements
     INTEGER(C_INT) :: nstp_end(WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rs_nray(WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwrmax_rs_nray(WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rl_nray(WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwrmax_rl_nray(WR_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: rays_end(0:8, WR_MAX_NRAYMAX)   ! mirrors WR_MAX_NRAY_EQ-1 = NEQ
     ! Profiles (zero-padded beyond actual dim)
     REAL(C_DOUBLE) :: pos_nrs(WR_MAX_NRSMAX)
     REAL(C_DOUBLE) :: pwr_nrs(WR_MAX_NRSMAX)
     REAL(C_DOUBLE) :: pos_nrl(WR_MAX_NRLMAX)
     REAL(C_DOUBLE) :: pwr_nrl(WR_MAX_NRLMAX)
  END TYPE wr_state_c

END MODULE wr_state
```

- [ ] **Step 2: コンパイルチェック（単体）**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
gfortran -c -g -O3 -std=legacy wr_state.f90 -J./mod -o /tmp/wr_state_check.o 2>&1 | tail -10
echo "exit=$?"
ls -la /tmp/wr_state_check.o
```
Expected: コンパイル成功、`/tmp/wr_state_check.o` が出来る。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/wr_state.f90
git commit -m "feat(wr): add wr_state.f90 with C-interoperable wr_state_c type"
```

---

## Task 3: `wr/wr_api.h` を新規作成

**Files:**
- Create: `wr/wr_api.h`

- [ ] **Step 1: ヘッダ作成**

Create `/home/k-yoshimi/program/task/wr/wr_api.h`:
```c
#ifndef WR_API_H
#define WR_API_H

/* TASK/WR library C ABI (Phase L-2 stub).
 *
 * Upper bounds for the fixed-size state struct.
 * Actual runtime nraymax/nrsmax/nrlmax are state.nraymax/state.nrsmax/state.nrlmax
 * and must be <= these.
 *
 * WR_MAX_NRAYMAX must equal NRAYM in wrcomm.f90 (currently 100).
 */
#define WR_MAX_NRAYMAX 100
#define WR_MAX_NRSMAX  200
#define WR_MAX_NRLMAX  400
/* WR_MAX_NRAY_EQ must equal NEQ+1 in wrcomm.f90 (NEQ=8 ⇒ 9). */
#define WR_MAX_NRAY_EQ 9

typedef struct {
    int    nraymax, nrsmax, nrlmax;
    double pos_pwrmax_rs, pwrmax_rs, pos_pwrmax_rl, pwrmax_rl;
    int    nstp_end           [WR_MAX_NRAYMAX];
    double pos_pwrmax_rs_nray [WR_MAX_NRAYMAX];
    double pwrmax_rs_nray     [WR_MAX_NRAYMAX];
    double pos_pwrmax_rl_nray [WR_MAX_NRAYMAX];
    double pwrmax_rl_nray     [WR_MAX_NRAYMAX];
    double rays_end           [WR_MAX_NRAYMAX][WR_MAX_NRAY_EQ]; /* Fortran rays_end(0:NEQ, j); NEQ=8 ⇒ 9 elements */
    double pos_nrs            [WR_MAX_NRSMAX];
    double pwr_nrs            [WR_MAX_NRSMAX];
    double pos_nrl            [WR_MAX_NRLMAX];
    double pwr_nrl            [WR_MAX_NRLMAX];
} wr_state_t;

/* Return codes:
 *   0 = OK
 *   1 = invalid parameter name (set_param)
 *   2 = not initialized
 *   3 = calculation failed
 *  99 = not implemented (Phase L-2 stub)
 */
int wr_init(void);
int wr_run(int nray_request);
int wr_set_param(const char* name, double value);
int wr_get_state(wr_state_t* state);
int wr_finalize(void);

#endif /* WR_API_H */
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/wr_api.h
git commit -m "feat(wr): add wr_api.h C header (5-function ABI, Phase L-2 stub)"
```

---

## Task 4: `wr/wr_api.f90` を新規作成（stub 実装）

**Files:**
- Create: `wr/wr_api.f90`

- [ ] **Step 1: モジュール作成**

Create `/home/k-yoshimi/program/task/wr/wr_api.f90`:
```fortran
! wr_api.f90
!
! C ABI wrapper for TASK/WR (Phase L-2 stub).
!
! Provides 5 BIND(C) functions:
!   wr_init       — initialize WR + dependencies (pl_init, dp_init, wr_init)
!   wr_run        — run wr_setup + wr_exec for ray tracing
!   wr_set_param  — STUB (Phase L-3 will implement)
!   wr_get_state  — copy WR globals into wr_state_c
!   wr_finalize   — wr_deallocate

MODULE wr_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE wr_state, ONLY: wr_state_c, &
                      WR_MAX_NRAYMAX, WR_MAX_NRSMAX, WR_MAX_NRLMAX
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wr_init_c, wr_run_c, wr_set_param_c, wr_get_state_c, wr_finalize_c

  LOGICAL, SAVE :: g_initialized = .FALSE.
  LOGICAL, SAVE :: g_executed    = .FALSE.

CONTAINS

  FUNCTION wr_init_c() RESULT(ierr) BIND(C, NAME="wr_init")
    USE plinit, ONLY: pl_init
    USE dpinit, ONLY: dp_init
    USE wrinit, ONLY: wr_init
    INTEGER(C_INT) :: ierr
    EXTERNAL EQINIT

    ierr = 0
    IF (g_initialized) THEN
       ierr = 0  ! idempotent re-init returns OK; state retained
       RETURN
    END IF
    CALL pl_init
    CALL EQINIT
    CALL dp_init
    CALL wr_init   ! note: same name as this wrapper; resolved by USE rename below
    g_initialized = .TRUE.
    g_executed    = .FALSE.
  END FUNCTION wr_init_c

  FUNCTION wr_run_c(nray_request) RESULT(ierr) BIND(C, NAME="wr_run")
    USE wrcomm,  ONLY: NRAYMAX, wr_allocate
    USE wrsetup, ONLY: wr_setup
    USE wrexec,  ONLY: wr_exec
    INTEGER(C_INT), VALUE, INTENT(IN) :: nray_request
    INTEGER(C_INT) :: ierr
    INTEGER :: setup_ierr, exec_ierr, nstat

    ierr = 0
    IF (.NOT. g_initialized) THEN
       ierr = 2; RETURN
    END IF

    ! Honor caller's NRAYMAX request if positive; else keep namelist value.
    IF (nray_request > 0) THEN
       NRAYMAX = nray_request
    END IF

    CALL wr_allocate
    CALL wr_setup(setup_ierr)
    IF (setup_ierr /= 0) THEN
       ierr = 3; RETURN
    END IF
    CALL wr_exec(nstat, exec_ierr)
    IF (exec_ierr /= 0) THEN
       ierr = 3; RETURN
    END IF
    g_executed = .TRUE.
  END FUNCTION wr_run_c

  FUNCTION wr_set_param_c(name, value) RESULT(ierr) BIND(C, NAME="wr_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! Phase L-2 stub: real implementation lands in L-3 (wr_param_registry).
    ! Suppress unused warnings:
    IF (.FALSE.) THEN
       ierr = INT(value, C_INT)
       ierr = ICHAR(name(1))
    END IF
    ierr = 99
  END FUNCTION wr_set_param_c

  FUNCTION wr_get_state_c(state) RESULT(ierr) BIND(C, NAME="wr_get_state")
    USE wrcomm, ONLY: NEQ, NRAYMAX, NRSMAX, NRLMAX, &
                      NSTPMAX_NRAY, RAYS, &
                      pos_nrs, pwr_nrs, pos_nrl, pwr_nrl, &
                      pos_pwrmax_rs, pwrmax_rs, pos_pwrmax_rl, pwrmax_rl, &
                      pos_pwrmax_rs_nray, pwrmax_rs_nray, &
                      pos_pwrmax_rl_nray, pwrmax_rl_nray
    TYPE(wr_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: j, k

    ierr = 0
    IF (.NOT. g_executed) THEN
       ierr = 2; RETURN
    END IF

    IF (NRAYMAX > WR_MAX_NRAYMAX .OR. &
        NRSMAX  > WR_MAX_NRSMAX  .OR. &
        NRLMAX  > WR_MAX_NRLMAX) THEN
       ierr = 3; RETURN
    END IF

    ! Defensive: profile / per-ray arrays must have been allocated by wr_calc_pwr.
    ! If not (caller bug, e.g. wr_run failed silently), bail out with ierr=3
    ! rather than hitting a Fortran runtime error on the unallocated reads below.
    IF (.NOT. ALLOCATED(NSTPMAX_NRAY)) THEN; ierr = 3; RETURN; END IF
    IF (.NOT. ALLOCATED(RAYS))         THEN; ierr = 3; RETURN; END IF
    IF (.NOT. ALLOCATED(pos_nrs))      THEN; ierr = 3; RETURN; END IF
    IF (.NOT. ALLOCATED(pwr_nrs))      THEN; ierr = 3; RETURN; END IF
    IF (.NOT. ALLOCATED(pos_nrl))      THEN; ierr = 3; RETURN; END IF
    IF (.NOT. ALLOCATED(pwr_nrl))      THEN; ierr = 3; RETURN; END IF

    state%nraymax = NRAYMAX
    state%nrsmax  = NRSMAX
    state%nrlmax  = NRLMAX
    state%pos_pwrmax_rs = pos_pwrmax_rs
    state%pwrmax_rs     = pwrmax_rs
    state%pos_pwrmax_rl = pos_pwrmax_rl
    state%pwrmax_rl     = pwrmax_rl

    ! zero-fill, then copy active range
    state%nstp_end           = 0
    state%pos_pwrmax_rs_nray = 0.0_C_DOUBLE
    state%pwrmax_rs_nray     = 0.0_C_DOUBLE
    state%pos_pwrmax_rl_nray = 0.0_C_DOUBLE
    state%pwrmax_rl_nray     = 0.0_C_DOUBLE
    state%rays_end           = 0.0_C_DOUBLE
    DO j = 1, NRAYMAX
       state%nstp_end(j)           = NSTPMAX_NRAY(j)
       state%pos_pwrmax_rs_nray(j) = pos_pwrmax_rs_nray(j)
       state%pwrmax_rs_nray(j)     = pwrmax_rs_nray(j)
       state%pos_pwrmax_rl_nray(j) = pos_pwrmax_rl_nray(j)
       state%pwrmax_rl_nray(j)     = pwrmax_rl_nray(j)
       DO k = 0, NEQ   ! NEQ=8 ⇒ 9 iterations matching RAYS(0:NEQ,...) first dim
          state%rays_end(k, j) = RAYS(k, NSTPMAX_NRAY(j), j)
       END DO
    END DO

    state%pos_nrs = 0.0_C_DOUBLE
    state%pwr_nrs = 0.0_C_DOUBLE
    DO j = 1, NRSMAX
       state%pos_nrs(j) = pos_nrs(j)
       state%pwr_nrs(j) = pwr_nrs(j)
    END DO

    state%pos_nrl = 0.0_C_DOUBLE
    state%pwr_nrl = 0.0_C_DOUBLE
    DO j = 1, NRLMAX
       state%pos_nrl(j) = pos_nrl(j)
       state%pwr_nrl(j) = pwr_nrl(j)
    END DO
  END FUNCTION wr_get_state_c

  FUNCTION wr_finalize_c() RESULT(ierr) BIND(C, NAME="wr_finalize")
    USE wrcomm, ONLY: wr_deallocate
    INTEGER(C_INT) :: ierr

    ierr = 0
    IF (g_executed) THEN
       CALL wr_deallocate
    END IF
    g_initialized = .FALSE.
    g_executed    = .FALSE.
  END FUNCTION wr_finalize_c

END MODULE wr_api
```

注: 内部関数名 `wr_init_c` と既存サブルーチン `wr_init` (in module `wrinit`) の名前衝突を避けるため、wrapper 側は `wr_init_c` とし、`BIND(C, NAME="wr_init")` で C 側名前空間にだけ `wr_init` を露出させる。

- [ ] **Step 2: 単体コンパイルチェック**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
gfortran -c -g -O3 -std=legacy \
    -I./mod -I../pl/mod -I../dp/mod -I../eq/mod -I../lib/mod -I../mtxp/mod -I../../bpsd/mod \
    -J./mod wr_state.f90 -o /tmp/wr_state_check.o
gfortran -c -g -O3 -std=legacy \
    -I./mod -I../pl/mod -I../dp/mod -I../eq/mod -I../lib/mod -I../mtxp/mod -I../../bpsd/mod \
    -J./mod wr_api.f90 -o /tmp/wr_api_check.o 2>&1 | tail -20
echo "exit=$?"
```
Expected: 両方コンパイル成功。エラーなし。

`USE` の名前衝突や ALLOCATABLE のアクセス可否で問題が出たら、`wrcomm` の `PUBLIC` 範囲を確認し、必要なら `wr_api.f90` の `USE wrcomm, ONLY:` リストを調整。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/wr_api.f90
git commit -m "feat(wr): add wr_api.f90 with 5-function C ABI (Phase L-2 stub)"
```

---

## Task 5: `wr/Makefile` に `SRCS_API` を追加

**Files:**
- Modify: `wr/Makefile`

- [ ] **Step 1: SRCS_API グループを追加**

Modify `/home/k-yoshimi/program/task/wr/Makefile`. Locate the source group block (created in L-1):

Old:
```
# --- Source groups (Phase L-1 split) ---
# SRCS_CORE: pure computation; will be reused for libwrapi.so in Phase L-4.
# SRCS_GRAPHICS: GSAF-based plot output; excluded from libwrapi.so.
# SRCS_MENU: interactive stdin menu; excluded from libwrapi.so.
#
# When Phase L-4 lands, libwrapi.so will be built from:
#   SRCS_LIB = $(SRCS_CORE) $(SRCS_API)
# where SRCS_API = wr_state.f90 wr_param_registry.f90 wr_api.f90
# (no graphics, no menu).
SRCS_CORE = wrcomm.f90 wrinit.f90 wrparm.f90 wrview.f90 \
            wrsub.f90 \
            wrsetupr.f90 wrexecr.f90 wrsetupb.f90 wrexecb.f90 \
            wrsetup.f90 wrregress.f90 wrexec.f90 \
            wrfile.f90

SRCS_GRAPHICS = wrgout.f90

SRCS_MENU = wrmenu.f90

SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)
```

New:
```
# --- Source groups (Phase L-1/L-2 split) ---
# SRCS_CORE: pure computation; reused for libwrapi.so in Phase L-4.
# SRCS_GRAPHICS: GSAF-based plot output; excluded from libwrapi.so.
# SRCS_MENU: interactive stdin menu; excluded from libwrapi.so.
# SRCS_API: C ABI bindings; included in both libwr.a and (future) libwrapi.so.
#
# Phase L-4 will build libwrapi.so from:
#   SRCS_LIB = $(SRCS_CORE) $(SRCS_API)
SRCS_CORE = wrcomm.f90 wrinit.f90 wrparm.f90 wrview.f90 \
            wrsub.f90 \
            wrsetupr.f90 wrexecr.f90 wrsetupb.f90 wrexecb.f90 \
            wrsetup.f90 wrregress.f90 wrexec.f90 \
            wrfile.f90

SRCS_GRAPHICS = wrgout.f90

SRCS_MENU = wrmenu.f90

SRCS_API = wr_state.f90 wr_api.f90

SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU) $(SRCS_API)
```

And add explicit dependency lines near the bottom (after the existing `$(OBJDIR)/wrexec.o:` rule):

```
$(OBJDIR)/wr_state.o: wr_state.f90
$(OBJDIR)/wr_api.o:   wr_api.f90 wr_state.f90 $(WRCOMM) wrinit.f90 wrsetup.f90 wrexec.f90
```

- [ ] **Step 2: フルビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make clean && make 2>&1 | tail -15
```
Expected: 
- `wr_state.f90` と `wr_api.f90` が `obj/wr_state.o` / `obj/wr_api.o` としてコンパイルされる。
- `libwr.a` に新 .o が含まれる。
- `wr` バイナリも正常リンク。

- [ ] **Step 3: シンボル確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
nm libwr.a | grep -E " T (wr_init|wr_run|wr_set_param|wr_get_state|wr_finalize)\b"
```
Expected: 5 つの C シンボル `wr_init, wr_run, wr_set_param, wr_get_state, wr_finalize` が見える。

- [ ] **Step 4: 既存 wr バイナリと回帰テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh wr_iter_lhcd wr_test001 wr_tst2_ec
```
Expected: 3 ケースとも PASS（C ABI を追加しただけで既存 wr の挙動は不変）。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/Makefile
git commit -m "build(wr): wire SRCS_API (wr_state.f90, wr_api.f90) into libwr.a"
```

---

## Task 6: 最小限の C スモークテストを追加

**Files:**
- Create: `wr/tests/c_abi/test_abi_stub.c`
- Create: `wr/tests/c_abi/Makefile`

- [ ] **Step 1: テストディレクトリと C ソース作成**

Create `/home/k-yoshimi/program/task/wr/tests/c_abi/test_abi_stub.c`:
```c
/* test_abi_stub.c
 *
 * Phase L-2 smoke test for the WR C ABI:
 *   1. wr_init() should return 0 on first call.
 *   2. wr_set_param() should return 99 (not implemented).
 *   3. wr_get_state() before wr_run() should return 2 (not initialized/executed).
 *   4. wr_finalize() should return 0.
 *
 * We deliberately do NOT call wr_run() here because L-2 has no parameter
 * setting yet; L-6 will exercise the full init→run→get_state cycle.
 */
#include <stdio.h>
#include <stdlib.h>
#include "../../wr_api.h"

static int fail = 0;
#define EXPECT(expr, want) do {                                    \
    int got = (expr);                                              \
    if (got != (want)) {                                           \
        fprintf(stderr, "FAIL %s:%d: %s = %d, want %d\n",          \
                __FILE__, __LINE__, #expr, got, (want));           \
        fail++;                                                    \
    } else {                                                       \
        fprintf(stdout, "OK   %s = %d\n", #expr, got);             \
    }                                                              \
} while (0)

int main(void) {
    EXPECT(wr_init(), 0);
    EXPECT(wr_init(), 0);                       /* idempotent */
    EXPECT(wr_set_param("RR", 6.2), 99);        /* L-2 stub */

    wr_state_t state;
    EXPECT(wr_get_state(&state), 2);            /* not executed yet */

    EXPECT(wr_finalize(), 0);
    return fail ? 1 : 0;
}
```

- [ ] **Step 2: テスト用 Makefile を作成**

Create `/home/k-yoshimi/program/task/wr/tests/c_abi/Makefile`:
```make
# Minimal Makefile for the WR C ABI smoke test (Phase L-2).
# Links libwr.a + dependencies as a static blob; no shared library yet.

include ../../../make.header
include ../../../mtxp/make.mtxp

WR_DIR  = ../..
TASK    = ../../..

WR_LIB  = $(WR_DIR)/libwr.a
DEPS    = $(WR_DIR)/../dp/libdp.a \
          $(WR_DIR)/../eq/libeq.a \
          $(WR_DIR)/../pl/libpl.a \
          $(WR_DIR)/../lib/libtask.a \
          $(WR_DIR)/../lib/libgrf.a \
          $(WR_DIR)/../../bpsd/libbpsd.a

CFLAGS  = -O2 -Wall

test_abi_stub: test_abi_stub.c $(WR_LIB)
	$(CC) $(CFLAGS) test_abi_stub.c $(WR_LIB) $(DEPS) $(LIB_MTX) $(LIBX_MTX) \
	    $(FLIBS) -lm -o $@

run: test_abi_stub
	./test_abi_stub

clean:
	-rm -f test_abi_stub
```

注: WR の通常 wr バイナリは `wrgout` 経由で GSAF (グラフィクス) シンボルにもリンクするが、stub テストは graphics を呼ばないため、`-Wl,--allow-shlib-undefined` 等が必要なら出してから対処（gfortran のリンクで通常は問題ないはず）。

- [ ] **Step 3: ビルドと実行**

Run:
```bash
cd /home/k-yoshimi/program/task/wr/tests/c_abi
make 2>&1 | tail -20
./test_abi_stub
echo "exit=$?"
```
Expected:
- ビルド成功（リンクで未定義シンボルが出ないこと）。
- 実行で `OK ...` 行が複数、最後に exit 0。

リンクで GSAF (`gscls_, gsopen_` 等) の未定義シンボルが出る場合は `wr_api.f90` 経由では `wrgout.f90` を引っ張らないはずだが、念のため `nm libwr.a | grep gscls` で `wrgout.o` が混入していないか確認。混入していれば一旦 `wr_api` テスト用の薄い `libwrapi_stub.a` を Makefile に追加する（L-4 の前倒し）。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/tests/c_abi/test_abi_stub.c wr/tests/c_abi/Makefile
git commit -m "test(wr): add C ABI smoke test (Phase L-2)"
```

---

## Task 7: 受け入れチェック

**Files:** なし

- [ ] **Step 1: 全シンボル / 既存テスト / 新スモークテストを一度に検証**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
nm libwr.a | grep -E " T (wr_init|wr_run|wr_set_param|wr_get_state|wr_finalize)\b" | sort
cd tests/c_abi && ./test_abi_stub
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected:
- 5 つの C シンボルが listed。
- C スモークテスト exit 0。
- 既存 + WR L-0 回帰 全件 PASS。

---

## 完了基準

- [ ] `wr/wr_state.f90` が追加され、`wr_state_c` 型を export
- [ ] `wr/wr_api.f90` が追加され、5 つの `BIND(C)` 関数を export
- [ ] `wr/wr_api.h` が C ヘッダとして整備されている
- [ ] `libwr.a` から `wr_init/wr_run/wr_set_param/wr_get_state/wr_finalize` の C シンボルが見える
- [ ] C スモークテスト `wr/tests/c_abi/test_abi_stub` が通る
- [ ] 既存 WR/TR/EQ/TX 回帰テスト全件 PASS

## 撤退条件

- `wr_api.f90` のリンクで `pl_init/dp_init/wr_init/wr_setup/wr_exec` が未定義になる場合 → `USE` リストの `ONLY:` 句を見直し、必要なら module の `PUBLIC` 宣言を確認
- `wrgout.f90` のグラフィクスシンボルが C テストに引っ張られる場合 → L-4 の前倒しで `libwr_core.a` を分離（本フェーズの撤退ではなく追加タスク）

## 依存

- 前提: L-1 完了（`SRCS_CORE/SRCS_GRAPHICS/SRCS_MENU` 分離済み）
- 後続: L-3 (`wr_set_param` の実装) で `wr_param_registry.f90` を追加して stub を置き換える
