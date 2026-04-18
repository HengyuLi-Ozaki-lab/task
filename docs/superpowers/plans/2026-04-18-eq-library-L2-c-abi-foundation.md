# EQ ライブラリ化 Phase L-2: C ABI Foundation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** C ABI 5 関数 (`eq_init`, `eq_run`, `eq_set_param`, `eq_get_state`, `eq_finalize`) のスケルトンと、`eq_state` 構造体（Fortran 側 / C 側）を新設する。中身は最小実装：`eq_init/eq_finalize` は既存 `equnit::eq_init` / `equread::alloc_equ(-1)` / `eqbpsd` 初期化を呼んで動かし、`eq_run` は既存の `eq_calc`（自動計算）or `eq_load`（EQDSK ファイル）にディスパッチするラッパとする。`eq_set_param` / `eq_get_state` は L-3 本実装までスタブ。**`eq/eq` / `pl` / `ak` バイナリの構成・数値結果は一切変えない。**

**Architecture:** TR L-2 (`tr/tr_api.f90`, `tr/tr_state.f90`) と同設計。3 つの新規 Fortran モジュール (`eq/eq_state.f90`, `eq/eq_param_registry.f90`, `eq/eq_api.f90`) と 1 つの C ヘッダ (`eq/eq_api.h`) を追加する。L-1 の `SRCS_CORE` には含めず、新たに `SRCS_API` make 変数として独立管理、`eq`/`pl`/`ak` ターゲットからはリンクしない（L-4 で `libeqapi.so` を初めて作る）。

**TR との設計差異 — F77 COMMON ブリッジ:**
EQ の namelist パラメータと計算結果は `eqcomm.inc`（F77 COMMON）経由でアクセスされ、F90 module (`equnit`, `equread`, `eqlib`) からは `USE` できない。このため L-2 では以下のブリッジ戦略を採る:

1. `eq_api.f90`（F90 module）は `USE equnit, ONLY: eq_init, eq_calc, eq_load, eq_parm` で既存エントリを呼ぶ
2. COMMON 変数を読み書きする部分は **F77 fixed-form ヘルパ** (`eq/eq_api_common.f`) に切り出し、INCLUDE `eqcomm.inc` 経由でアクセス
3. `eq_api.f90` からは `EXTERNAL :: eq_api_read_scalars, eq_api_get_nrmax` などで F77 ヘルパを呼ぶ

L-2 ではこのブリッジ ** 最小限**（`eq_api_get_nrmax`, `eq_api_get_nsumax`, `eq_api_copy_state_zeros` だけ）で実装。L-3 で setter 群を追加。

**Tech Stack:** Fortran 2003 `ISO_C_BINDING` (F90 module)、Fortran 77 fixed-form (COMMON ブリッジ)、gfortran、GNU Make、既存 `equnit` モジュール + `eqcomm.inc` COMMON 群。

**出典設計書:**
- `docs/superpowers/plans/2026-04-18-tr-library-L2-c-abi-foundation.md` (直接対応する TR plan、設計の写し)
- `docs/superpowers/plans/2026-04-18-ti-library-L2-c-abi-foundation.md` (第 2 例：rename quirk の扱い方の参考)
- `docs/superpowers/plans/2026-04-18-eq-library-L1-makefile-split.md` (上流、`SRCS_CORE/GRAPHICS/MENU` 分割)
- `docs/superpowers/specs/2026-04-17-tr-library-design.md` §3–4 (C ABI 設計原理を eq に転用)

---

## File Structure

このサブフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `eq/eq_state.f90` | 新規 | `eq_state_c` 派生型（C 互換、固定サイズ配列）。中身は ZEROS |
| `eq/eq_param_registry.f90` | 新規 | `eq_param_set` 関数の **空シェル**（常に ierr=1）。L-3 で本実装 |
| `eq/eq_api.f90` | 新規 | `bind(c)` 5 関数。init/finalize は既存 `equnit` ルーチン呼び出し、他はスタブ |
| `eq/eq_api_common.f` | 新規 | F77 fixed-form ヘルパ（`eqcomm.inc` 経由で COMMON スカラー数値を読み出す。L-2 では `eq_api_get_dims(nrmax, nthmax, nsumax)` と `eq_api_reset` のみ） |
| `eq/eq_api.h` | 新規 | C ヘッダ（`eq_state_t` 構造体 + 5 関数プロトタイプ） |
| `eq/Makefile` | 修正 | `SRCS_API` を新設、コンパイル対象に追加（リンクは `eq`/`pl`/`ak` どのターゲットにも組み込まない） |
| `eq/tests/c_abi/test_smoke.c` | 新規 | C から `eq_init`/`eq_finalize` を 1 サイクル呼ぶ最小スモーク |
| `eq/tests/c_abi/Makefile` | 新規 | C スモークのビルド・実行ルール（`libeqapi.so` 未作成のため直接 .o リンク） |

**方針:**
- 新規 Fortran ファイル 4 本は「**増やすだけ**」「**既存ファイルは Makefile 以外書き換えない**」が大原則
- `eq_api.f90::eq_init` 実装は、`equnit::eq_init` と `equnit::eq_parm` の薄いラッパ（`MODE=2` デフォ namelist + `eqinit` 呼び出し）
- `eq_run` は L-2 では「`MODE=0` → `eq_calc` / `MODE=1` → `eq_load(KNAMEQ)` / `MODE=2` → `eq_jaear` (QST fmt)」を dispatch。実装は既存エントリをそのまま `CALL` で呼ぶだけ
- C スモークテストは「init→run(mode=0)→finalize で SIGSEGV しない」だけを確認（数値正当性は L-6）

---

## Task 1: ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: L-0 (PR #54) と L-1 の完了確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git fetch origin develop
git log --oneline origin/develop | grep -iE "eq.*L-0|eq.*L-1|PR #54|eqregress" | head -5
grep -n "^SRCS_CORE\|^SRCS_GRAPHICS\|^SRCS_MENU" eq/Makefile
ls eq/eqregress.f test_run/baselines/eq_iter01/metrics.json test_run/baselines/eq_tst2/metrics.json 2>&1
```
Expected:
- L-0 (`eqregress.f` + 2 baselines) が develop に merge 済み
- L-1 (`SRCS_CORE/GRAPHICS/MENU` 分割) が develop に merge 済み

どちらか未完了なら本 L-2 は保留。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/eq-library-L2-c-abi-foundation origin/develop
```

- [ ] **Step 3: 既存 `equnit` module エントリを再確認**

Run:
```bash
grep -n "subroutine eq_init\|subroutine eq_calc\|subroutine eq_load\|subroutine eq_parm" eq/equnit.f
```
Expected: `eq_init`, `eq_parm`, `eq_prof`, `eq_calc`, `eq_load`, `eq_gout` の 6 つが公開されている（`equnit.f:7` の `public eq_init,eq_parm,eq_prof,eq_calc,eq_load,eq_gout` 行）。

注意: 既存 `equnit::eq_init` と新 C ABI 関数 `eq_init` の **名前衝突回避** が必要。本プランでは `BIND(C, NAME="eq_init")` で C シンボルを維持しつつ Fortran 側関数名は `eq_api_init_c` とする（TR L-2 Task 1 Step 3 と同じ戦略）。

- [ ] **Step 4: L-0 回帰が PASS することを確認**

Run:
```bash
cd eq && make 2>&1 | tail -5
cd ../test_run && ./run_tests.sh eq_iter01 eq_tst2 2>&1 | tail -5
```
Expected: 2/2 PASS。

---

## Task 2: `eq/eq_state.f90` を新規作成

**Files:** Create: `eq/eq_state.f90`

- [ ] **Step 1: ファイル作成**

作成: `eq/eq_state.f90`

```fortran
! eq_state.f90
!
! C-interoperable state struct for the EQ library API.
! Mirrors eq_api.h::eq_state_t exactly. Fixed-size arrays.
!
! Phase L-2: definition only. Population happens in eq_api::eq_get_state (L-3).
!
! Size choices reflect the LARGEST realistic runs from eqcom0.inc:
!   NRGM = NZGM = 513 (grid)  — cap struct at 257 to balance size vs. coverage
!   NPSM = 513                — cap at 257
!   NRVM = 1001               — cap at 513
!   NTVM = 1025               — not exposed in L-2 state
!   NSUM = 1343               — cap at 1025 (boundary surface)

MODULE eq_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_state_c, EQ_MAX_NRGMAX, EQ_MAX_NZGMAX, &
            EQ_MAX_NPSMAX, EQ_MAX_NRVMAX, EQ_MAX_NSUMAX

  INTEGER(C_INT), PARAMETER :: EQ_MAX_NRGMAX = 257
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NZGMAX = 257
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NPSMAX = 257
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NRVMAX = 513
  INTEGER(C_INT), PARAMETER :: EQ_MAX_NSUMAX = 1025

  TYPE, BIND(C) :: eq_state_c
     ! mesh sizes (runtime <= the maxima above)
     INTEGER(C_INT) :: nrgmax
     INTEGER(C_INT) :: nzgmax
     INTEGER(C_INT) :: npsmax
     INTEGER(C_INT) :: nrvmax
     INTEGER(C_INT) :: nsumax
     ! global scalars (EQGLB1..EQGLB6)
     REAL(C_DOUBLE) :: RAXIS
     REAL(C_DOUBLE) :: ZAXIS
     REAL(C_DOUBLE) :: PSI0
     REAL(C_DOUBLE) :: PSIPA
     REAL(C_DOUBLE) :: PSITA
     REAL(C_DOUBLE) :: REDGE
     REAL(C_DOUBLE) :: PVOL
     REAL(C_DOUBLE) :: RAAVE
     REAL(C_DOUBLE) :: BETAT
     REAL(C_DOUBLE) :: BETAP
     REAL(C_DOUBLE) :: QAXIS
     REAL(C_DOUBLE) :: QSURF
     REAL(C_DOUBLE) :: TJ
     REAL(C_DOUBLE) :: RIPX
     ! device scalars (mirrors of input)
     REAL(C_DOUBLE) :: RR, RA, RB, RKAP, RDLT, BB, Q0, QA, RIP
     ! flux-surface arrays
     REAL(C_DOUBLE) :: PSIPS(EQ_MAX_NPSMAX)
     REAL(C_DOUBLE) :: PPPS(EQ_MAX_NPSMAX)
     REAL(C_DOUBLE) :: TTPS(EQ_MAX_NPSMAX)
     REAL(C_DOUBLE) :: QQPS(EQ_MAX_NPSMAX)
     ! radial-averaged arrays
     REAL(C_DOUBLE) :: QPV(EQ_MAX_NRVMAX)
     REAL(C_DOUBLE) :: TTV(EQ_MAX_NRVMAX)
     REAL(C_DOUBLE) :: VPV(EQ_MAX_NRVMAX)
     ! boundary surface
     REAL(C_DOUBLE) :: RSU(EQ_MAX_NSUMAX)
     REAL(C_DOUBLE) :: ZSU(EQ_MAX_NSUMAX)
  END TYPE eq_state_c

END MODULE eq_state
```

注: `PSIRZ(NRGM,NZGM)` は L-2 state には含めない（`513*513*8B ≈ 2 MB` は構造体に載せるには大きすぎ、パフォーマンス的にも `eq_get_psi_rz_buffer` のような別 API で切り出すのが妥当。L-3 / L-4 で別関数として追加を検討）。

- [ ] **Step 2: 単独コンパイル確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
gfortran -c eq_state.f90 -J./mod -o /tmp/eq_state.o 2>&1 | tail -5
ls /tmp/eq_state.o mod/eq_state.mod
```
Expected: `.o` と `.mod` が生成される。

---

## Task 3: `eq/eq_param_registry.f90` を空シェルとして作成

**Files:** Create: `eq/eq_param_registry.f90`

- [ ] **Step 1: ファイル作成（中身は L-3 で実装）**

作成: `eq/eq_param_registry.f90`

```fortran
! eq_param_registry.f90
!
! Phase L-2: empty shell. Returns ierr=1 (invalid name) for any input.
! Phase L-3 fills in the SELECT CASE table for /EQ/ namelist parameters,
! backed by F77 common-block setters in eq_api_common.f.

MODULE eq_param_registry
  USE bpsd_kinds, ONLY: rkind
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_param_set

CONTAINS

  FUNCTION eq_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),       INTENT(IN) :: value
    INTEGER :: ierr
    ! Phase L-2 stub. L-3 will dispatch SELECT CASE into
    !   CALL eq_common_set_RR(value) / eq_common_set_PN(idx, value) / ...
    ! where the eq_common_set_* helpers live in eq_api_common.f (fixed-form
    ! Fortran with INCLUDE eqcomm.inc to reach the COMMON blocks).
    ierr = 1   ! invalid parameter name (always)
    ! prevent unused-argument warnings
    IF (LEN_TRIM(name) < 0) ierr = 1
    IF (value /= value)     ierr = 1
  END FUNCTION eq_param_set

END MODULE eq_param_registry
```

注: `USE bpsd_kinds, ONLY: rkind`（`equread.f90:3` と同じ kind source）。`equnit` とは USE しない — L-2 ではスタブなので依存はゼロに抑える。

---

## Task 4: `eq/eq_api_common.f` F77 ブリッジヘルパ

**Files:** Create: `eq/eq_api_common.f`

L-2 で必要な最小ヘルパだけ実装:
- `EQ_COMMON_GET_DIMS(NRG, NZG, NPS, NRV, NSU)` — COMMON から mesh サイズを返す
- `EQ_COMMON_RESET_INITIALIZED()` — `eqinit` 的な no-op placeholder

- [ ] **Step 1: ファイル作成**

作成: `eq/eq_api_common.f`

```fortran
C     eq_api_common.f
C
C     Fixed-form F77 bridge between eq_api.f90 (free-form F2003 with
C     ISO_C_BINDING) and the COMMON blocks declared in eqcomm.inc.
C     This file's sole purpose is to reach /EQPRN2/ /EQPRN3/ /EQGLB*/
C     etc. since F90 USE cannot be applied to old-style COMMON.
C
C     Phase L-2 minimal helpers. L-3 adds setters for every registered
C     /EQ/ namelist parameter (eq_common_set_RR, eq_common_set_BB, ...).

      SUBROUTINE EQ_COMMON_GET_DIMS(NRG, NZG, NPS, NRV, NSU)
C     Returns current mesh dimensions from the COMMON blocks.
C     Used by eq_api::eq_get_state to bounds-check against EQ_MAX_*.
      INCLUDE '../eq/eqcomm.inc'
      INTEGER, INTENT(OUT) :: NRG, NZG, NPS, NRV, NSU
      NRG = NRGMAX
      NZG = NZGMAX
      NPS = NPSMAX
      NRV = NRVMAX
      NSU = NSUMAX
      RETURN
      END

      SUBROUTINE EQ_COMMON_GET_GLOBALS(
     &     R_RAXIS, R_ZAXIS, R_PSI0, R_PSIPA, R_PSITA, R_REDGE,
     &     R_PVOL, R_RAAVE, R_BETAT, R_BETAP, R_QAXIS, R_QSURF,
     &     R_TJ, R_RIPX)
C     Returns convergent global quantities after eqcalc/eqload.
      INCLUDE '../eq/eqcomm.inc'
      REAL*8, INTENT(OUT) :: R_RAXIS, R_ZAXIS, R_PSI0, R_PSIPA
      REAL*8, INTENT(OUT) :: R_PSITA, R_REDGE
      REAL*8, INTENT(OUT) :: R_PVOL, R_RAAVE, R_BETAT, R_BETAP
      REAL*8, INTENT(OUT) :: R_QAXIS, R_QSURF
      REAL*8, INTENT(OUT) :: R_TJ, R_RIPX
      R_RAXIS = RAXIS
      R_ZAXIS = ZAXIS
      R_PSI0  = PSI0
      R_PSIPA = PSIPA
      R_PSITA = PSITA
      R_REDGE = REDGE
      R_PVOL  = PVOL
      R_RAAVE = RAAVE
      R_BETAT = BETAT
      R_BETAP = BETAP
      R_QAXIS = QAXIS
      R_QSURF = QSURF
      R_TJ    = TJ
      R_RIPX  = RIPX
      RETURN
      END

      SUBROUTINE EQ_COMMON_GET_DEVICE(
     &     R_RR, R_RA, R_RB, R_RKAP, R_RDLT,
     &     R_BB, R_Q0, R_QA, R_RIP)
      INCLUDE '../eq/eqcomm.inc'
      REAL*8, INTENT(OUT) :: R_RR, R_RA, R_RB, R_RKAP, R_RDLT
      REAL*8, INTENT(OUT) :: R_BB, R_Q0, R_QA, R_RIP
      R_RR = RR
      R_RA = RA
      R_RB = RB
      R_RKAP = RKAP
      R_RDLT = RDLT
      R_BB = BB
      R_Q0 = Q0
      R_QA = QA
      R_RIP = RIP
      RETURN
      END
```

注: `eqcomm.inc` は `USE plcomm` + `IMPLICIT COMPLEX*16(C),REAL*8(...)` + `eqcom0/eqcom1.inc` を取り込む。本ヘルパ subroutine では `INTEGER NRG` は明示宣言済みなので IMPLICIT の影響を受けないが、念のため各 subroutine で `INTEGER` / `REAL*8` を `INTENT(OUT)` 付きで明示。

---

## Task 5: `eq/eq_api.f90` を作成（bind(c) 5 関数のスタブ）

**Files:** Create: `eq/eq_api.f90`

- [ ] **Step 1: ファイル作成**

作成: `eq/eq_api.f90`

```fortran
! eq_api.f90
!
! C ABI entry points for libeqapi.so.
! Phase L-2 minimal scaffolding:
!   - eq_init      : delegate to equnit::eq_init (which calls eqinit).
!   - eq_run(mode) : dispatch to equnit::eq_calc (mode=0) or eq_load (mode=1).
!   - eq_get_state : stub — fills zeros + mesh dims from eq_api_common.
!   - eq_set_param : stub — always returns 1 via empty registry.
!   - eq_finalize  : no-op (eq has no dynamic alloc owned by this API in L-2).
!
! Real bodies for get_state/set_param arrive in L-3.
!
! See docs/superpowers/plans/2026-04-18-eq-library-L2-c-abi-foundation.md.

MODULE eq_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE eq_state,          ONLY: eq_state_c, EQ_MAX_NRGMAX, EQ_MAX_NZGMAX, &
                               EQ_MAX_NPSMAX, EQ_MAX_NRVMAX, EQ_MAX_NSUMAX
  USE eq_param_registry, ONLY: eq_param_set
  USE equnit,            ONLY: equnit_eq_init => eq_init, &
                               equnit_eq_parm => eq_parm, &
                               equnit_eq_calc => eq_calc, &
                               equnit_eq_load => eq_load
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_api_init_c, eq_api_run_c, eq_api_get_state_c, &
            eq_api_set_param_c, eq_api_finalize_c

  LOGICAL, SAVE :: g_initialized = .FALSE.

  ! Error codes (matches tr_api / ti_api convention):
  !   0 : success
  !   1 : invalid argument (bad param name, bad mode, bad index)
  !   2 : lifecycle violation (not initialized, double init, etc.)
  !   3 : calculation failure (eqcalc/eqload returned ierr)
  !   4 : buffer / dimension too small (NRGMAX > EQ_MAX_NRGMAX)

  INTEGER(C_INT), PARAMETER :: EQ_OK            = 0
  INTEGER(C_INT), PARAMETER :: EQ_ERR_ARG       = 1
  INTEGER(C_INT), PARAMETER :: EQ_ERR_LIFECYCLE = 2
  INTEGER(C_INT), PARAMETER :: EQ_ERR_CALC      = 3
  INTEGER(C_INT), PARAMETER :: EQ_ERR_BUFFER    = 4

CONTAINS

  FUNCTION eq_api_init_c() RESULT(ierr) BIND(C, NAME="eq_init")
    INTEGER(C_INT) :: ierr
    IF (g_initialized) THEN
       ierr = EQ_OK
       RETURN
    END IF
    CALL equnit_eq_init()    ! calls eqinit (sets all namelist defaults)
    g_initialized = .TRUE.
    ierr = EQ_OK
  END FUNCTION eq_api_init_c

  FUNCTION eq_api_run_c(mode) RESULT(ierr) BIND(C, NAME="eq_run")
    ! mode = 0 : run EQCALC (analytic profile driven)
    ! mode = 1 : run EQLOAD (read KNAMEQ file)
    ! mode = 2 : reserved for JAEA/QST format (EQJAEAR) — L-3
    INTEGER(C_INT), VALUE, INTENT(IN) :: mode
    INTEGER(C_INT) :: ierr
    INTEGER :: jerr
    CHARACTER(LEN=80) :: knameq_local
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_LIFECYCLE
       RETURN
    END IF
    jerr = 0
    SELECT CASE (mode)
    CASE (0)
       CALL equnit_eq_calc()
       ! equnit::eq_calc has no OUT ierr; it prints on failure. L-3 will
       ! replace this with a wrapper that exposes the inner ierr.
    CASE (1)
       ! KNAMEQ is in COMMON; L-3 reads it through eq_common_get_knameq.
       ! L-2 stub: pass the COMMON default via an eq_api_common helper
       ! (not implemented here) — for now, just error out.
       ierr = EQ_ERR_ARG
       RETURN
    CASE DEFAULT
       ierr = EQ_ERR_ARG
       RETURN
    END SELECT
    ierr = EQ_OK
  END FUNCTION eq_api_run_c

  FUNCTION eq_api_get_state_c(state) RESULT(ierr) BIND(C, NAME="eq_get_state")
    TYPE(eq_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: nrg, nzg, nps, nrv, nsu
    ! F77 helper signatures (declared in eq_api_common.f)
    EXTERNAL :: EQ_COMMON_GET_DIMS, EQ_COMMON_GET_GLOBALS, &
                EQ_COMMON_GET_DEVICE
    REAL(C_DOUBLE) :: tj_r, ripx_r
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_LIFECYCLE
       RETURN
    END IF
    CALL EQ_COMMON_GET_DIMS(nrg, nzg, nps, nrv, nsu)
    IF (nrg > EQ_MAX_NRGMAX .OR. nzg > EQ_MAX_NZGMAX .OR. &
        nps > EQ_MAX_NPSMAX .OR. nrv > EQ_MAX_NRVMAX .OR. &
        nsu > EQ_MAX_NSUMAX) THEN
       ierr = EQ_ERR_BUFFER
       RETURN
    END IF
    state%nrgmax = nrg
    state%nzgmax = nzg
    state%npsmax = nps
    state%nrvmax = nrv
    state%nsumax = nsu
    CALL EQ_COMMON_GET_GLOBALS( &
         state%RAXIS, state%ZAXIS, state%PSI0, state%PSIPA, &
         state%PSITA, state%REDGE, state%PVOL, state%RAAVE, &
         state%BETAT, state%BETAP, state%QAXIS, state%QSURF, &
         tj_r, ripx_r)
    state%TJ   = tj_r
    state%RIPX = ripx_r
    CALL EQ_COMMON_GET_DEVICE( &
         state%RR, state%RA, state%RB, state%RKAP, state%RDLT, &
         state%BB, state%Q0, state%QA, state%RIP)
    ! Zero profile arrays in L-2 (L-3 will populate via EQ_COMMON_GET_PROFILES)
    state%PSIPS = 0.0_C_DOUBLE
    state%PPPS  = 0.0_C_DOUBLE
    state%TTPS  = 0.0_C_DOUBLE
    state%QQPS  = 0.0_C_DOUBLE
    state%QPV   = 0.0_C_DOUBLE
    state%TTV   = 0.0_C_DOUBLE
    state%VPV   = 0.0_C_DOUBLE
    state%RSU   = 0.0_C_DOUBLE
    state%ZSU   = 0.0_C_DOUBLE
    ierr = EQ_OK
  END FUNCTION eq_api_get_state_c

  FUNCTION eq_api_set_param_c(name, value) RESULT(ierr) BIND(C, NAME="eq_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: fname
    INTEGER :: i
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_LIFECYCLE
       RETURN
    END IF
    fname = ' '
    DO i = 1, 64
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
    END DO
    ierr = eq_param_set(TRIM(fname), value)  ! L-2 stub always returns 1
  END FUNCTION eq_api_set_param_c

  FUNCTION eq_api_finalize_c() RESULT(ierr) BIND(C, NAME="eq_finalize")
    INTEGER(C_INT) :: ierr
    ! EQ has no owned dynamic allocations in this API surface (plcomm /
    ! equread manage their own). Flip the lifecycle flag only.
    g_initialized = .FALSE.
    ierr = EQ_OK
  END FUNCTION eq_api_finalize_c

END MODULE eq_api
```

注:
- `USE equnit, ONLY: equnit_eq_init => eq_init` の **rename** は、新 C ABI 関数 `eq_init`（公開名）と `equnit::eq_init`（既存内部名）の Fortran 側衝突を避けるため
- エラーコード 0..4 は TR / TI と統一（`tr_api.f90` と同じ意味）
- L-2 では `eq_api_run_c(1)` は `EQ_ERR_ARG` を返す。L-3 で `EQ_COMMON_GET_KNAMEQ` ヘルパを足し、`equnit_eq_load(MODELG, KNAMEQ, ierr)` 呼び出しを完成させる

---

## Task 6: `eq/eq_api.h` を作成

**Files:** Create: `eq/eq_api.h`

- [ ] **Step 1: ヘッダ作成**

作成: `eq/eq_api.h`

```c
#ifndef EQ_API_H
#define EQ_API_H

#ifdef __cplusplus
extern "C" {
#endif

/* See docs/superpowers/plans/2026-04-18-eq-library-L2-c-abi-foundation.md.
 *
 * Memory note: Fortran column-major and C row-major agree on flat 1D
 * arrays. All arrays here are 1D; 2D PSIRZ is intentionally excluded
 * (too large: 2 MB) and will be exposed via a separate eq_get_psi_rz
 * in a later phase.
 *
 * Error codes returned by all functions:
 *   0 = success
 *   1 = invalid argument (bad name, bad mode, bad index)
 *   2 = lifecycle violation (call eq_init first / already initialized etc.)
 *   3 = calculation failure (eqcalc/eqload internal ierr)
 *   4 = buffer / dimension too small (runtime size > compile-time maximum)
 */

#define EQ_MAX_NRGMAX 257
#define EQ_MAX_NZGMAX 257
#define EQ_MAX_NPSMAX 257
#define EQ_MAX_NRVMAX 513
#define EQ_MAX_NSUMAX 1025

typedef struct {
    int nrgmax, nzgmax, npsmax, nrvmax, nsumax;
    /* global scalars */
    double RAXIS, ZAXIS, PSI0, PSIPA, PSITA, REDGE;
    double PVOL, RAAVE, BETAT, BETAP, QAXIS, QSURF;
    double TJ, RIPX;
    /* device scalars */
    double RR, RA, RB, RKAP, RDLT, BB, Q0, QA, RIP;
    /* flux-surface arrays */
    double PSIPS[EQ_MAX_NPSMAX];
    double PPPS [EQ_MAX_NPSMAX];
    double TTPS [EQ_MAX_NPSMAX];
    double QQPS [EQ_MAX_NPSMAX];
    /* radial-averaged */
    double QPV[EQ_MAX_NRVMAX];
    double TTV[EQ_MAX_NRVMAX];
    double VPV[EQ_MAX_NRVMAX];
    /* boundary */
    double RSU[EQ_MAX_NSUMAX];
    double ZSU[EQ_MAX_NSUMAX];
} eq_state_t;

int eq_init(void);
int eq_run(int mode);          /* 0=eq_calc, 1=eq_load(KNAMEQ), 2=eq_jaear */
int eq_set_param(const char* name, double value);
int eq_get_state(eq_state_t* state);
int eq_finalize(void);

#ifdef __cplusplus
}
#endif

#endif /* EQ_API_H */
```

---

## Task 7: Makefile に SRCS_API を追加

**Files:** Modify: `eq/Makefile`

- [ ] **Step 1: SRCS_API 定義と OBJ_API 派生変数を追加**

`eq/Makefile` の `SRCS_MENU= eqmenu.f`（L-1 で導入済みの行）の直後に挿入:

```makefile
# C ABI sources (Phase L-2+). Compiled but not linked into eq/pl/ak.
# Linked into libeqapi.so by Phase L-4.
SRCS_API = eq_state.f90 eq_param_registry.f90 eq_api.f90 eq_api_common.f
OBJ_API  = $(SRCS_API:.f90=.o)
OBJ_API := $(OBJ_API:.f=.o)
```

- [ ] **Step 2: `all:` に API オブジェクトのビルドを追加（リンクは行わない）**

既存（L-1 の）:
```makefile
all : libs eq
```
を:
```makefile
all : libs eq $(OBJ_API)
```
に変更。

- [ ] **Step 3: 依存定義を追加**

Makefile 末尾に:
```makefile
eq_state.o           : eq_state.f90
eq_param_registry.o  : eq_param_registry.f90
eq_api.o             : eq_api.f90 eq_state.f90 eq_param_registry.f90 equnit.f
eq_api_common.o      : eq_api_common.f eqcomm.inc eqcom0.inc eqcom1.inc
```

- [ ] **Step 4: clean ビルド確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make clean
make 2>&1 | tail -10
ls eq_state.o eq_param_registry.o eq_api.o eq_api_common.o
ls eq pl ak
nm eq | grep -E "^[0-9a-f]+ T eq_init$|^[0-9a-f]+ T eq_run$" | head
```
Expected:
- `eq`, `pl`, `ak` 既存バイナリが生成される
- 4 つの API .o ファイルが存在する
- `nm eq` に `T eq_init`/`T eq_run` の C シンボルは **含まれない**（リンクしていないため）

---

## Task 8: C スモークテストを追加

**Files:**
- Create: `eq/tests/c_abi/test_smoke.c`
- Create: `eq/tests/c_abi/Makefile`

- [ ] **Step 1: スモークテスト C ソース**

作成: `eq/tests/c_abi/test_smoke.c`

```c
/* Phase L-2 smoke: init -> run(mode=0) -> finalize cycle.
 * Verifies link & eqinit-driven defaults from C. No numeric checks.
 */
#include <stdio.h>
#include <stdlib.h>
#include "../../eq_api.h"

int main(void) {
    int rc;
    rc = eq_init();
    if (rc != 0) { fprintf(stderr, "eq_init failed: %d\n", rc); return 1; }

    /* mode=0: analytic-profile eqcalc with default params from eqinit. */
    rc = eq_run(0);
    if (rc != 0) { fprintf(stderr, "eq_run(0) failed: %d\n", rc); return 2; }

    eq_state_t state;
    rc = eq_get_state(&state);
    if (rc != 0) { fprintf(stderr, "eq_get_state failed: %d\n", rc); return 3; }
    if (state.nrgmax <= 0 || state.nrgmax > EQ_MAX_NRGMAX) {
        fprintf(stderr, "bad state.nrgmax=%d\n", state.nrgmax);
        return 4;
    }

    rc = eq_finalize();
    if (rc != 0) { fprintf(stderr, "eq_finalize failed: %d\n", rc); return 5; }
    printf("OK: eq init/run(0)/get_state/finalize cycle returned 0\n");
    return 0;
}
```

- [ ] **Step 2: ビルド用 Makefile**

作成: `eq/tests/c_abi/Makefile`

```makefile
# Phase L-2 smoke test. Links the API objects and dependencies directly
# (libeqapi.so does not exist yet; arrives in L-4).

include ../../../make.header
include ../../../mtxp/make.mtxp
LIB_MTX = $(LIB_MTX_MUMPS)
LIBX_MTX= $(LIBX_MTX_MUMPS)

EQ_DIR     = ../..
API_OBJS   = $(EQ_DIR)/eq_state.o $(EQ_DIR)/eq_param_registry.o \
             $(EQ_DIR)/eq_api.o   $(EQ_DIR)/eq_api_common.o
EQ_LIB     = $(EQ_DIR)/libeq.a
DEPS       = $(EQ_DIR)/../pl/libpl.a \
             $(EQ_DIR)/../lib/libgrf.a \
             $(EQ_DIR)/../lib/libtask.a \
             $(EQ_DIR)/../../bpsd/libbpsd.a

test_smoke: test_smoke.c $(API_OBJS) $(EQ_LIB)
	$(FLINKER) -I$(EQ_DIR) test_smoke.c $(API_OBJS) $(EQ_LIB) $(DEPS) \
	    $(FFLAGS) $(FLIBS) $(LIBX_MTX) -o test_smoke

run: test_smoke
	./test_smoke

clean:
	-rm -f test_smoke
```

注: `$(FLINKER)` を C ドライバとして流用するのは TR L-2 と同じ理由（gfortran runtime が必要）。`$(CC)` で直接リンクすると `undefined reference to _gfortran_*` が多発する。

- [ ] **Step 3: スモーク実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq/tests/c_abi
make run 2>&1 | tail -10
```
Expected: `OK: eq init/run(0)/get_state/finalize cycle returned 0`。

- [ ] **Step 4: 失敗時の撤退**

リンクが解決できない場合、L-4 の `libeqapi.so` 生成と同時にスモークを動かす設計に切り替える（`Makefile` をコメントアウトしておき、`test_smoke.c` だけ commit、L-4 で復活）。L-2 全体は止めない。

---

## Task 9: Phase L-0 回帰テストで eq/pl/ak 不変を確認

**Files:** なし

- [ ] **Step 1: 回帰 2 ケース PASS**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eq_iter01 eq_tst2 2>&1 | tail -10
```
Expected: 2/2 PASS（API オブジェクトを追加しても `eq` はリンクしないため、数値は完全に同じ）。

- [ ] **Step 2: 巻き込み事故チェック（tr / ti / pl 回帰が残っていれば）**

Run:
```bash
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -5
./run_tests.sh ti_min ti_ar ti_w 2>&1 | tail -5 || true
```
Expected: すべて PASS。EQ の Makefile 変更が pl 経由で他モジュールに波及していないか確認。

---

## Task 10: コミットと PR

**Files:** なし

- [ ] **Step 1: 段階的コミット**

Run:
```bash
git add eq/eq_state.f90 eq/eq_param_registry.f90
git commit -m "feat(eq): add C ABI scaffolding modules (state struct + empty registry)"

git add eq/eq_api.f90 eq/eq_api_common.f eq/eq_api.h
git commit -m "feat(eq): add eq_api 5-function ABI + F77 COMMON bridge"

git add eq/Makefile
git commit -m "build(eq): compile SRCS_API objects (no libeqapi.so yet)"

git add eq/tests/c_abi/
git commit -m "test(eq): add C ABI smoke test for init/run(0)/get_state/finalize"
```

- [ ] **Step 2: PR 作成**

Run:
```bash
gh pr create --base develop \
  --title "feat(eq): Phase L-2 C ABI foundation (stubs + smoke)" \
  --body "Phase L-2: C ABI 5 関数のスケルトン、eq_state_c 構造体、eq_api.h、F77 COMMON ブリッジ (eq_api_common.f)、C スモーク追加。eq/pl/ak バイナリには新規シンボルをリンクせず、L-0 回帰 2 ケースは引き続き PASS。設計は tr-library-L2 の写し、EQ 固有の F77 COMMON アクセスは eq_api_common.f 経由でブリッジ。"
```

---

## Risk / Mitigation

| リスク | 影響 | 対策 |
|---|---|---|
| `equnit::eq_init` と新 `eq_init` (C ABI) の名前衝突 | コンパイルエラー | `USE equnit, ONLY: equnit_eq_init => eq_init` で rename。C 側名は `BIND(C, NAME="eq_init")` で維持 |
| `eqcomm.inc` の `USE plcomm` + `IMPLICIT COMPLEX*16/REAL*8` が `eq_api_common.f` で意図せぬ型再定義を起こす | 隠れた型ミス | ヘルパ subroutine 内で `INTEGER`, `REAL*8`, `INTENT(OUT)` を明示宣言。PR レビュー時に全ダミーを点検 |
| `equnit::eq_calc` は `ierr` を返さない | 計算失敗を検知できない | L-2 ではそのまま (EQCALC は失敗時 WRITE(6,...) するのみ)。L-3 で `equnit.f` に小さなラッパ `eq_calc_ierr(ierr)` を増設して解決 |
| PSIRZ (2 MB) を state に含めた場合のスタック overflow | `test_smoke` SIGSEGV | 本 L-2 では struct から除外済み。将来 `eq_get_psi_rz(double* buf, int* nr, int* nz)` の別 API を検討 |
| C スモークテストの gfortran runtime リンク失敗 | CI で FAIL | `$(CC)` ではなく `$(FLINKER)` を driver として使う (TR L-2 と同じ対策) |
| L-1 (SRCS 分割) が未 merge | 本 L-2 がそもそも動かない | Task 1 Step 1 でブロック。`SRCS_CORE` grep 結果が空なら撤退 |

## Testing Strategy

**Layer 0 (本 L-2 の責務):**
- L-0 回帰 2 ケース (`eq_iter01`, `eq_tst2`) bit-exact PASS
- `tr_*`, `ti_*` など他モジュール回帰巻き込み事故なし
- `nm eq | grep "T eq_init$"` が空（C シンボル未リンクの確認）
- 4 API .o ファイルが存在

**Layer 1 (C smoke):**
- `tests/c_abi/test_smoke` が exit 0
- `state.nrgmax`, `state.nrmax`, `state.RR`, `state.BB` などが `eqinit` の default 値と一致
   - `RR=3.0, RA=1.0, BB=3.0, RIP=3.0, NRGMAX=33, NZGMAX=33, NPSMAX=21` (eqinit.f default) を assert できると強い

**Layer 2 以降** は L-3 (param registry), L-4 (libeqapi.so), L-6 (4 層 test harness) で段階的に追加。

## Deliverables Checklist

- [ ] `eq/eq_state.f90` - `eq_state_c` 構造体定義
- [ ] `eq/eq_param_registry.f90` - 空シェル（ierr=1 を返すのみ）
- [ ] `eq/eq_api.f90` - 5 関数 C ABI（init/finalize 実動作、他スタブ）
- [ ] `eq/eq_api_common.f` - F77 COMMON ブリッジ（GET_DIMS / GET_GLOBALS / GET_DEVICE の 3 ヘルパ）
- [ ] `eq/eq_api.h` - C ヘッダ
- [ ] `eq/Makefile` - `SRCS_API` / `OBJ_API` 追加、`all:` 依存追加
- [ ] `eq/tests/c_abi/test_smoke.c` + `Makefile` - C スモーク
- [ ] L-0 回帰 2 ケース PASS
- [ ] `nm eq | grep "T eq_init$"` が空
- [ ] PR が develop をターゲットに作成済み

## 撤退条件 / フォールバック

| 状況 | 判断 |
|---|---|
| `USE equnit, ONLY: equnit_eq_init => eq_init` で rename できない（gfortran バージョン依存） | 新 Fortran 側関数名を `eq_api_lifecycle_init` に変え、`BIND(C, NAME="eq_init")` のみで C 公開。USE rename 不要 |
| `eq_api_common.f` のリンクで `eqcomm.inc` 内 `plcomm` 依存が循環 | `eq_api_common.f` から `USE plcomm` を外し、必要な値だけを引数で受け渡す設計に変更（L-3 で詳細化） |
| C スモーク動かず（ランタイムリンク地獄） | Task 8 Step 4 の通り、Makefile を削除コミット。L-4 以降で復活。本 L-2 は「.o が出来る」「nm で未リンク」だけで合格とする |
| `eq_calc` が namelist を要求し default だけでは動かない | `test_smoke.c` は `eq_run(0)` を外し、init/finalize だけで exit 0 を確認する 最小版にデグレード |
| `EQ_MAX_NRGMAX=257` で運用中の入力 (NRGM=513) が落ちる | 当該ケースは `EQ_ERR_BUFFER` を返すので静かに縮退。本 L-2 では runtime NRGMAX <= 257 のケースだけ回帰対象 |

## 依存

- **必須前提:** L-0 (PR #54, `eqregress.f` + 2 baselines) が develop にマージ済み
- **必須前提:** L-1 (`eq/Makefile` の `SRCS_CORE/GRAPHICS/MENU` 分割) が develop にマージ済み
- **上流モジュール:** `plcomm` (pl/libpl.a), `bpsd_kinds` (bpsd/libbpsd.a), `libmtxp.a` 既存ビルド

## 後続

- **L-3 (`2026-04-18-eq-library-L3-param-registry.md`):** 空シェル registry を実装、`eq_api_common.f` に setter 群を追加
- **L-4:** `libeqapi.so` 生成 + C スモークの完全リンクテスト
- **L-5:** Python wrapper
- **L-6:** 4 層回帰 (Fortran bin / C test / Python / 最上位 harness)
- **L-7:** ユーザードキュメント
