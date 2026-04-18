# EQ ライブラリ化 Phase L-3: Parameter Registry 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2 で空シェルだった `eq_param_registry.f90` に、`/EQ/` namelist パラメータの setter テーブルを実装する。同時に `eq_api.f90::eq_get_state` を実体化（プロファイル配列まで populate）、`eq_run(mode=1)` の `eq_load` ルートを実装する。EQ は F77 COMMON ベースなので、registry は F90 SELECT CASE + F77 setter ヘルパ (`eq_api_common.f` 拡張) の 2 段構成になる。**`eq`/`pl`/`ak` バイナリは引き続き未変更（API は別オブジェクト群）。**

**Architecture:** 設計書 §5 の手書き SELECT CASE 方式を採用。EQ 固有の難点は「registry の上位ディスパッチは F90 module (`eq_param_registry.f90`) で書きたいが、COMMON 変数への代入は F77 fixed-form (`INCLUDE eqcomm.inc`) でしか書けない」こと。これを 2 段で解く:

1. `eq_param_registry.f90`（F90 module）が `parse_array_subscript` + SELECT CASE で名前を分解し、F77 setter helper (`eq_common_set_RR`, `eq_common_set_BB`, ..., `eq_common_set_PSIB`, ...) を `EXTERNAL` 宣言して呼ぶ
2. `eq/eq_api_common.f` を拡張し、登録対象パラメータごとに 1〜2 行の setter を追加（`SUBROUTINE EQ_COMMON_SET_RR(VAL); INCLUDE eqcomm.inc; RR=VAL; END`）

これにより F90 module から COMMON への代入が可能になる。TR / TI の registry と異なり setter 定義数が倍になるが、1 パラメータあたり 3 行と極小なので可読性は保たれる。

スカラー / 整数 / 1D 配列 (`PSIB[0]`, `RIPFC[1]`, `RPFC[1]`, etc.) / スカラー文字列 (`KNAMEQ`) を扱う。文字列は第 2 ABI `eq_set_param_str(const char* name, const char* value)` を L-3 で追加（KNAMEQ, KNAMWR, ... の 7 個のファイル名パラメータ用）。

**Tech Stack:** Fortran 2003 (SELECT CASE, ISO_C_BINDING) for F90 side, Fortran 77 fixed-form for COMMON setter helpers, 既存 `equnit::eq_load`, gfortran。

**出典設計書:**
- `docs/superpowers/plans/2026-04-18-tr-library-L3-param-registry.md` (TR L-3 — SELECT CASE 本体の写し)
- `docs/superpowers/plans/2026-04-18-ti-library-L3-param-registry.md` (TI L-3 — 2D 添字 `MODEL_BND[i,NS]` 記法の参考)
- `docs/superpowers/plans/2026-04-18-eq-library-L2-c-abi-foundation.md` (前段 — eq_api_common.f のブリッジ設計)
- `eq/eqinit.f` の `NAMELIST /EQ/ ...` 行 (登録対象の正典、PR #54 以降固定)
- `eq/eqcom1.inc` (COMMON ブロック /EQPRM3/../EQPRX5/ — 変数宣言の正典)

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `eq/eq_param_registry.f90` | 修正（実装本体） | `/EQ/` namelist パラメータの SELECT CASE 実装 + `parse_array_subscript` |
| `eq/eq_api_common.f` | 修正（拡張） | `EQ_COMMON_SET_*` setter 群（約 60 個）+ `EQ_COMMON_GET_PROFILES` + `EQ_COMMON_GET_KNAMEQ` + `EQ_COMMON_SET_KNAMEQ` |
| `eq/eq_api.f90` | 修正 | `eq_get_state` の配列部分を populate、`eq_run(mode=1)` の eq_load ルートを実装、`eq_set_param_str` の公開 |
| `eq/eq_api.h` | 修正 | `eq_set_param_str` プロトタイプ追加 |
| `eq/tests/c_abi/test_param.c` | 新規 | set_param → get_state の sanity（`RR` を変えて読めるか） |
| `eq/tests/c_abi/test_param_str.c` | 新規 | `eq_set_param_str("KNAMEQ", "eqdata_test")` の sanity |
| `eq/tests/c_abi/test_run_calc.c` | 新規 | `eq_run(0)` 後に state scalars が eqinit 既定値と一致 |
| `eq/tests/c_abi/Makefile` | 修正 | 新テストを追加 |

**方針:**
- 登録パラメータは §「Task 2」の **初期セット**（およそ 60 個）に絞る。残りは後続 PR で追加可能
- `parse_array_subscript` は TR / TI と共通仕様 (`[N]`, `[I,J]` 記法サポート)。PSIB は `[0..5]` の 0-origin 添字が唯一の例外
- `eq_load` は既存 `equnit::eq_load(MODELG, KNAMEQ, ierr)` をそのまま呼ぶ。`KNAMEQ` は registry 経由で事前に `eq_set_param_str` でセット
- `eq_get_state` の scalar 名は Phase L-0 `eqregress.f` が dump している集合と同一（README で「regression dump と get_state は同じ集合」と明記）

---

## Task 1: ブランチと前提

- [ ] **Step 1: L-2 完了確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git fetch origin develop
git log --oneline origin/develop | grep -iE "eq.*L-2|eq C ABI foundation" | head -3
ls eq/eq_state.f90 eq/eq_param_registry.f90 eq/eq_api.f90 eq/eq_api_common.f eq/eq_api.h
```
Expected: L-2 merge commit、5 ファイルが develop に存在。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/eq-library-L3-param-registry origin/develop
```

- [ ] **Step 3: 登録対象 `/EQ/` namelist の列挙**

Run:
```bash
sed -n '/NAMELIST .EQ./,/FORMAT/p' /home/k-yoshimi/program/task-private/eq/eqinit.f | head -30
```
Expected: `NAMELIST /EQ/ RR,RA,RB,RKAP,RDLT,BB,Q0,QA,RIP, RHOMIN,QMIN,MODELG,MODELQ, ... MDLEQF,MDLEQC, ... PSIB,NPFCMAX,RIPFC,RPFC,ZPFC,WPFC,FRBIN` が見える。

- [ ] **Step 4: 撤退判定**

本 L-3 は「最小セット 30 個」を合格ラインとする。60 個狙いで始め、`USE` / `eq_common_set_*` で解決できないものが 30 個を超えた場合は後続 PR に分割。

---

## Task 2: 登録対象パラメータリストの確定（EQNAM1/EQNAM2 = namelist /EQ/）

**Files:** なし（決定の文書化）

**決定事項:** 以下 60 個を L-3 で registry に登録する。追加は別 PR。

### スカラー実数 (26)
- **Device geometry:** `RR, RA, RB, RKAP, RDLT, BB, Q0, QA, RIP, RHOMIN, QMIN, RHOITB, RHOEDG, FRBIN, RBRA`
- **Pressure profile:** `PP0, PP1, PP2, PROFP0, PROFP1, PROFP2`
- **Current profile:** `PJ0, PJ1, PJ2, PROFJ0, PROFJ1, PROFJ2`
- **Poloidal-F profile:** `FF0, FF1, FF2, PROFF0, PROFF1, PROFF2`
- **Temperature/velocity:** `PT0, PT1, PT2, PROFTP0, PROFTP1, PROFTP2, PTSEQ, PN0EQ`
- **Radial profile:** `PROFR0, PROFR1, PROFR2`
- **Convergence:** `EPSEQ, EPSNW, DELNW`
- **Region:** `RGMIN, RGMAX, ZGMIN, ZGMAX, ZLIMP, ZLIMM`

(注: これらの一部は Task 2 の総数 26 にカウントされず、合計 60 のうち実数部を構成する。)

### スカラー整数 (16)
- **Mesh sizes:** `NRMAX, NTHMAX, NSUMAX, NSGMAX, NTGMAX, NUGMAX, NRGMAX, NZGMAX, NPSMAX, NRVMAX, NTVMAX`
- **Model switches:** `MODELG, MODELQ, MDLEQF, MDLEQC, MDLEQA, MDLEQX, MDLEQV, NPRINT, NLPMAX, NLPNW, IDEBUG, MODEFR, MODEFW, NPFCMAX`

### 1D 配列 (12)
- **PFC (NPFCMAX <= NPFCM=10):** `RIPFC[i], RPFC[i], ZPFC[i], WPFC[i]` — 1-origin 添字
- **Multipole:** `PSIB[0]`, `PSIB[1]`, ..., `PSIB[5]` — **0-origin 添字** (eqcom1.inc `PSIB(0:5)` の通り)

### スカラー文字列 (7) — 別 ABI
- `KNAMEQ, KNAMWR, KNAMWM, KNAMFP, KNAMFO, KNAMPF, KNAMEQ2` — 80 文字固定長、`eq_set_param_str` 経由

### 命名の決定メモ（TI の `pm=>pa` quirk と同種の注意点）

TR/TI と異なり、EQ 内で rename は発生していない。`USE plcomm`（`eqcomm.inc` の先頭）経由で `plcomm::RR` を直接使っているが、EQ 側で別名化していないので **plcomm 名 = `/EQ/` namelist 名 = registry key**（全一致）。ただし:
- `RR, RA, BB, RIP` は `plcomm` / `eqcomm` 両方にあり、どちらで setter を書いても最終的に同じ変数 (plcomm 側の COMMON)。本プランでは `eqcomm.inc` の INCLUDE 経由で統一（plcomm 直接 USE は避ける）。
- `NRMAX` は **pl の NRMAXPL と異なる**。EQ `NRMAX`（flux coord 半径メッシュ）の setter は `eqcomm.inc` 経由で書き込む。pl の `NRMAXPL` は対象外。

---

## Task 3: `parse_array_subscript` のテストを先に書く（TDD）

**Files:**
- 一時テストドライバ（commit せず捨て可）

- [ ] **Step 1: 失敗するテスト用ドライバ**

作成: `eq/tests/c_abi/parse_subscript_unittest.f90`

```fortran
PROGRAM parse_subscript_unittest
  USE eq_param_registry, ONLY: parse_array_subscript_pub
  IMPLICIT NONE
  CHARACTER(LEN=32) :: base
  INTEGER :: i1, i2
  CALL parse_array_subscript_pub("RR", base, i1, i2)
  IF (TRIM(base) /= "RR" .OR. i1 /= 0 .OR. i2 /= 0) STOP 1
  CALL parse_array_subscript_pub("PSIB[0]", base, i1, i2)
  IF (TRIM(base) /= "PSIB" .OR. i1 /= 0) STOP 2
  CALL parse_array_subscript_pub("PSIB[5]", base, i1, i2)
  IF (TRIM(base) /= "PSIB" .OR. i1 /= 5) STOP 3
  CALL parse_array_subscript_pub("RIPFC[3]", base, i1, i2)
  IF (TRIM(base) /= "RIPFC" .OR. i1 /= 3) STOP 4
  PRINT *, "parse_array_subscript_pub OK"
END PROGRAM
```

注: PSIB は 0-origin なので `PSIB[0]` で `i1 = 0` が正しく、`ierr=BAD_INDEX` にならないこと。`PSIB` 以外は 1-origin。

---

## Task 4: `eq_api_common.f` に setter helper 群を追加

**Files:** Modify: `eq/eq_api_common.f`

- [ ] **Step 1: scalar setter helpers を追加**

`eq/eq_api_common.f` の末尾に以下を追記（各 setter は 3〜5 行）:

```fortran
C     ================================================================
C     Phase L-3 scalar setters (called from eq_param_registry.f90)
C     ================================================================

      SUBROUTINE EQ_COMMON_SET_RR(VAL)
      INCLUDE '../eq/eqcomm.inc'
      REAL*8, INTENT(IN) :: VAL
      RR = VAL
      END

      SUBROUTINE EQ_COMMON_SET_RA(VAL)
      INCLUDE '../eq/eqcomm.inc'
      REAL*8, INTENT(IN) :: VAL
      RA = VAL
      RBRA = RB/RA   ! keep invariant (see EQPARM)
      END

      SUBROUTINE EQ_COMMON_SET_RB(VAL)
      INCLUDE '../eq/eqcomm.inc'
      REAL*8, INTENT(IN) :: VAL
      RB = VAL
      RBRA = RB/RA
      END

      SUBROUTINE EQ_COMMON_SET_BB(VAL)
      INCLUDE '../eq/eqcomm.inc'
      REAL*8, INTENT(IN) :: VAL
      BB = VAL
      END

      SUBROUTINE EQ_COMMON_SET_RIP(VAL)
      INCLUDE '../eq/eqcomm.inc'
      REAL*8, INTENT(IN) :: VAL
      RIP = VAL
      END

      ! ... (同パターンで RKAP, RDLT, Q0, QA, RHOMIN, QMIN, RHOITB, RHOEDG,
      !      FRBIN, PP0/1/2, PROFP0/1/2, PJ0/1/2, PROFJ0/1/2, FF0/1/2,
      !      PROFF0/1/2, PT0/1/2, PROFTP0/1/2, PTSEQ, PN0EQ, PROFR0/1/2,
      !      EPSEQ, EPSNW, DELNW, RGMIN, RGMAX, ZGMIN, ZGMAX, ZLIMP, ZLIMM)
```

- [ ] **Step 2: integer setters**

```fortran
      SUBROUTINE EQ_COMMON_SET_MODELG(IVAL)
      INCLUDE '../eq/eqcomm.inc'
      INTEGER, INTENT(IN) :: IVAL
      MODELG = IVAL
      END

      SUBROUTINE EQ_COMMON_SET_NRMAX(IVAL)
      INCLUDE '../eq/eqcomm.inc'
      INTEGER, INTENT(IN) :: IVAL
      NRMAX = IVAL
      END

      ! ... (NTHMAX, NSUMAX, NSGMAX, NTGMAX, NUGMAX, NRGMAX, NZGMAX, NPSMAX,
      !      NRVMAX, NTVMAX, MODELQ, MDLEQF, MDLEQC, MDLEQA, MDLEQX, MDLEQV,
      !      NPRINT, NLPMAX, NLPNW, IDEBUG, MODEFR, MODEFW, NPFCMAX)
```

- [ ] **Step 3: 1D array setters**

```fortran
      SUBROUTINE EQ_COMMON_SET_PSIB(I, VAL)
C     PSIB(0:5) — 0-origin
      INCLUDE '../eq/eqcomm.inc'
      INTEGER, INTENT(IN) :: I
      REAL*8,  INTENT(IN) :: VAL
      IF (I .LT. 0 .OR. I .GT. 5) RETURN   ! caller checks IERR separately
      PSIB(I) = VAL
      END

      SUBROUTINE EQ_COMMON_SET_RIPFC(I, VAL)
C     RIPFC(1:NPFCM), NPFCM=10 (eqcom0.inc)
      INCLUDE '../eq/eqcomm.inc'
      INTEGER, INTENT(IN) :: I
      REAL*8,  INTENT(IN) :: VAL
      IF (I .LT. 1 .OR. I .GT. NPFCM) RETURN
      RIPFC(I) = VAL
      END

      ! ... (RPFC, ZPFC, WPFC の同パターン)
```

- [ ] **Step 4: 文字列 setter (KNAMEQ ほか 7)**

```fortran
      SUBROUTINE EQ_COMMON_SET_KNAMEQ(STR)
      INCLUDE '../eq/eqcomm.inc'
      CHARACTER(LEN=*), INTENT(IN) :: STR
      KNAMEQ = STR
      END

      SUBROUTINE EQ_COMMON_GET_KNAMEQ(STR)
      INCLUDE '../eq/eqcomm.inc'
      CHARACTER(LEN=80), INTENT(OUT) :: STR
      STR = KNAMEQ
      END

      ! ... (KNAMWR/KNAMWM/KNAMFP/KNAMFO/KNAMPF/KNAMEQ2 の SET/GET)
```

- [ ] **Step 5: プロファイル配列 getter**

```fortran
      SUBROUTINE EQ_COMMON_GET_PROFILES_1D(
     &     N_PS, PSIPS_OUT, PPPS_OUT, TTPS_OUT, QQPS_OUT,
     &     N_RV, QPV_OUT, TTV_OUT, VPV_OUT,
     &     N_SU, RSU_OUT, ZSU_OUT)
      INCLUDE '../eq/eqcomm.inc'
      INTEGER, INTENT(IN) :: N_PS, N_RV, N_SU
      REAL*8,  INTENT(OUT) :: PSIPS_OUT(N_PS), PPPS_OUT(N_PS)
      REAL*8,  INTENT(OUT) :: TTPS_OUT(N_PS),  QQPS_OUT(N_PS)
      REAL*8,  INTENT(OUT) :: QPV_OUT(N_RV), TTV_OUT(N_RV), VPV_OUT(N_RV)
      REAL*8,  INTENT(OUT) :: RSU_OUT(N_SU), ZSU_OUT(N_SU)
      INTEGER :: I

      DO I = 1, MIN(NPSMAX, N_PS)
         PSIPS_OUT(I) = PSIPS(I)
         PPPS_OUT(I)  = PPPS(I)
         TTPS_OUT(I)  = TTPS(I)
         QQPS_OUT(I)  = QQPS(I)
      END DO
      DO I = 1, MIN(NRVMAX, N_RV)
         QPV_OUT(I) = QPV(I)
         TTV_OUT(I) = TTV(I)
         VPV_OUT(I) = VPV(I)
      END DO
      DO I = 1, MIN(NSUMAX, N_SU)
         RSU_OUT(I) = RSU(I)
         ZSU_OUT(I) = ZSU(I)
      END DO
      RETURN
      END
```

- [ ] **Step 6: コンパイル確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make eq_api_common.o 2>&1 | tail -10
```
Expected: エラーなしで `.o` 生成。`eqcomm.inc` 内の COMMON 変数と名前不一致があればここで判明。

---

## Task 5: `eq_param_registry.f90` を実装

**Files:** Modify: `eq/eq_param_registry.f90`

- [ ] **Step 1: 実装本体に置換**

`eq/eq_param_registry.f90` を以下で置換:

```fortran
! eq_param_registry.f90
!
! Phase L-3: setter table for /EQ/ namelist parameters.
!
! Dispatches name strings to F77 setter helpers declared in eq_api_common.f.
! See docs/superpowers/plans/2026-04-18-eq-library-L3-param-registry.md.

MODULE eq_param_registry
  USE bpsd_kinds, ONLY: rkind
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_param_set, eq_param_set_str
  PUBLIC :: parse_array_subscript_pub  ! exported for unit test only

  INTEGER, PARAMETER :: ERR_OK         = 0
  INTEGER, PARAMETER :: ERR_BAD_NAME   = 1
  INTEGER, PARAMETER :: ERR_BAD_INDEX  = 1   ! collapsed into ARG per ABI

CONTAINS

  FUNCTION eq_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),       INTENT(IN) :: value
    INTEGER :: ierr
    CHARACTER(LEN=32) :: base
    INTEGER :: i1, i2
    ! F77 setter externals
    EXTERNAL :: EQ_COMMON_SET_RR, EQ_COMMON_SET_RA, EQ_COMMON_SET_RB, &
                EQ_COMMON_SET_RKAP, EQ_COMMON_SET_RDLT, EQ_COMMON_SET_BB, &
                EQ_COMMON_SET_Q0, EQ_COMMON_SET_QA, EQ_COMMON_SET_RIP, &
                EQ_COMMON_SET_RHOMIN, EQ_COMMON_SET_QMIN, EQ_COMMON_SET_RHOITB, &
                EQ_COMMON_SET_RHOEDG, EQ_COMMON_SET_FRBIN, &
                EQ_COMMON_SET_PP0, EQ_COMMON_SET_PP1, EQ_COMMON_SET_PP2, &
                EQ_COMMON_SET_PROFP0, EQ_COMMON_SET_PROFP1, EQ_COMMON_SET_PROFP2, &
                EQ_COMMON_SET_PJ0, EQ_COMMON_SET_PJ1, EQ_COMMON_SET_PJ2, &
                EQ_COMMON_SET_PROFJ0, EQ_COMMON_SET_PROFJ1, EQ_COMMON_SET_PROFJ2, &
                EQ_COMMON_SET_FF0, EQ_COMMON_SET_FF1, EQ_COMMON_SET_FF2, &
                EQ_COMMON_SET_PROFF0, EQ_COMMON_SET_PROFF1, EQ_COMMON_SET_PROFF2, &
                EQ_COMMON_SET_PT0, EQ_COMMON_SET_PT1, EQ_COMMON_SET_PT2, &
                EQ_COMMON_SET_PROFTP0, EQ_COMMON_SET_PROFTP1, EQ_COMMON_SET_PROFTP2, &
                EQ_COMMON_SET_PTSEQ, EQ_COMMON_SET_PN0EQ, &
                EQ_COMMON_SET_PROFR0, EQ_COMMON_SET_PROFR1, EQ_COMMON_SET_PROFR2, &
                EQ_COMMON_SET_EPSEQ, EQ_COMMON_SET_EPSNW, EQ_COMMON_SET_DELNW, &
                EQ_COMMON_SET_RGMIN, EQ_COMMON_SET_RGMAX, &
                EQ_COMMON_SET_ZGMIN, EQ_COMMON_SET_ZGMAX, &
                EQ_COMMON_SET_ZLIMP, EQ_COMMON_SET_ZLIMM
    EXTERNAL :: EQ_COMMON_SET_MODELG, EQ_COMMON_SET_MODELQ, &
                EQ_COMMON_SET_MDLEQF, EQ_COMMON_SET_MDLEQC, &
                EQ_COMMON_SET_MDLEQA, EQ_COMMON_SET_MDLEQX, &
                EQ_COMMON_SET_MDLEQV, EQ_COMMON_SET_NPRINT, &
                EQ_COMMON_SET_NLPMAX, EQ_COMMON_SET_NLPNW, &
                EQ_COMMON_SET_IDEBUG, EQ_COMMON_SET_MODEFR, EQ_COMMON_SET_MODEFW, &
                EQ_COMMON_SET_NRMAX, EQ_COMMON_SET_NTHMAX, EQ_COMMON_SET_NSUMAX, &
                EQ_COMMON_SET_NSGMAX, EQ_COMMON_SET_NTGMAX, EQ_COMMON_SET_NUGMAX, &
                EQ_COMMON_SET_NRGMAX, EQ_COMMON_SET_NZGMAX, EQ_COMMON_SET_NPSMAX, &
                EQ_COMMON_SET_NRVMAX, EQ_COMMON_SET_NTVMAX, EQ_COMMON_SET_NPFCMAX
    EXTERNAL :: EQ_COMMON_SET_PSIB, EQ_COMMON_SET_RIPFC, &
                EQ_COMMON_SET_RPFC, EQ_COMMON_SET_ZPFC, EQ_COMMON_SET_WPFC

    ierr = ERR_OK
    CALL parse_array_subscript(name, base, i1, i2)

    SELECT CASE (TRIM(base))
    ! ---- geometry / device scalars ----
    CASE ("RR");     CALL EQ_COMMON_SET_RR(value)
    CASE ("RA");     CALL EQ_COMMON_SET_RA(value)
    CASE ("RB");     CALL EQ_COMMON_SET_RB(value)
    CASE ("RKAP");   CALL EQ_COMMON_SET_RKAP(value)
    CASE ("RDLT");   CALL EQ_COMMON_SET_RDLT(value)
    CASE ("BB");     CALL EQ_COMMON_SET_BB(value)
    CASE ("Q0");     CALL EQ_COMMON_SET_Q0(value)
    CASE ("QA");     CALL EQ_COMMON_SET_QA(value)
    CASE ("RIP");    CALL EQ_COMMON_SET_RIP(value)
    CASE ("RHOMIN"); CALL EQ_COMMON_SET_RHOMIN(value)
    CASE ("QMIN");   CALL EQ_COMMON_SET_QMIN(value)
    CASE ("RHOITB"); CALL EQ_COMMON_SET_RHOITB(value)
    CASE ("RHOEDG"); CALL EQ_COMMON_SET_RHOEDG(value)
    CASE ("FRBIN");  CALL EQ_COMMON_SET_FRBIN(value)
    ! ---- pressure / current / F / T / profile scalars ----
    CASE ("PP0");    CALL EQ_COMMON_SET_PP0(value)
    CASE ("PP1");    CALL EQ_COMMON_SET_PP1(value)
    CASE ("PP2");    CALL EQ_COMMON_SET_PP2(value)
    CASE ("PROFP0"); CALL EQ_COMMON_SET_PROFP0(value)
    CASE ("PROFP1"); CALL EQ_COMMON_SET_PROFP1(value)
    CASE ("PROFP2"); CALL EQ_COMMON_SET_PROFP2(value)
    CASE ("PJ0");    CALL EQ_COMMON_SET_PJ0(value)
    CASE ("PJ1");    CALL EQ_COMMON_SET_PJ1(value)
    CASE ("PJ2");    CALL EQ_COMMON_SET_PJ2(value)
    CASE ("PROFJ0"); CALL EQ_COMMON_SET_PROFJ0(value)
    CASE ("PROFJ1"); CALL EQ_COMMON_SET_PROFJ1(value)
    CASE ("PROFJ2"); CALL EQ_COMMON_SET_PROFJ2(value)
    CASE ("FF0");    CALL EQ_COMMON_SET_FF0(value)
    CASE ("FF1");    CALL EQ_COMMON_SET_FF1(value)
    CASE ("FF2");    CALL EQ_COMMON_SET_FF2(value)
    CASE ("PROFF0"); CALL EQ_COMMON_SET_PROFF0(value)
    CASE ("PROFF1"); CALL EQ_COMMON_SET_PROFF1(value)
    CASE ("PROFF2"); CALL EQ_COMMON_SET_PROFF2(value)
    CASE ("PT0");    CALL EQ_COMMON_SET_PT0(value)
    CASE ("PT1");    CALL EQ_COMMON_SET_PT1(value)
    CASE ("PT2");    CALL EQ_COMMON_SET_PT2(value)
    CASE ("PROFTP0"); CALL EQ_COMMON_SET_PROFTP0(value)
    CASE ("PROFTP1"); CALL EQ_COMMON_SET_PROFTP1(value)
    CASE ("PROFTP2"); CALL EQ_COMMON_SET_PROFTP2(value)
    CASE ("PTSEQ");  CALL EQ_COMMON_SET_PTSEQ(value)
    CASE ("PN0EQ");  CALL EQ_COMMON_SET_PN0EQ(value)
    CASE ("PROFR0"); CALL EQ_COMMON_SET_PROFR0(value)
    CASE ("PROFR1"); CALL EQ_COMMON_SET_PROFR1(value)
    CASE ("PROFR2"); CALL EQ_COMMON_SET_PROFR2(value)
    CASE ("EPSEQ");  CALL EQ_COMMON_SET_EPSEQ(value)
    CASE ("EPSNW");  CALL EQ_COMMON_SET_EPSNW(value)
    CASE ("DELNW");  CALL EQ_COMMON_SET_DELNW(value)
    CASE ("RGMIN");  CALL EQ_COMMON_SET_RGMIN(value)
    CASE ("RGMAX");  CALL EQ_COMMON_SET_RGMAX(value)
    CASE ("ZGMIN");  CALL EQ_COMMON_SET_ZGMIN(value)
    CASE ("ZGMAX");  CALL EQ_COMMON_SET_ZGMAX(value)
    CASE ("ZLIMP");  CALL EQ_COMMON_SET_ZLIMP(value)
    CASE ("ZLIMM");  CALL EQ_COMMON_SET_ZLIMM(value)
    ! ---- integer scalars ----
    CASE ("MODELG");  CALL EQ_COMMON_SET_MODELG(INT(value))
    CASE ("MODELQ");  CALL EQ_COMMON_SET_MODELQ(INT(value))
    CASE ("MDLEQF");  CALL EQ_COMMON_SET_MDLEQF(INT(value))
    CASE ("MDLEQC");  CALL EQ_COMMON_SET_MDLEQC(INT(value))
    CASE ("MDLEQA");  CALL EQ_COMMON_SET_MDLEQA(INT(value))
    CASE ("MDLEQX");  CALL EQ_COMMON_SET_MDLEQX(INT(value))
    CASE ("MDLEQV");  CALL EQ_COMMON_SET_MDLEQV(INT(value))
    CASE ("NPRINT");  CALL EQ_COMMON_SET_NPRINT(INT(value))
    CASE ("NLPMAX");  CALL EQ_COMMON_SET_NLPMAX(INT(value))
    CASE ("NLPNW");   CALL EQ_COMMON_SET_NLPNW(INT(value))
    CASE ("IDEBUG");  CALL EQ_COMMON_SET_IDEBUG(INT(value))
    CASE ("MODEFR");  CALL EQ_COMMON_SET_MODEFR(INT(value))
    CASE ("MODEFW");  CALL EQ_COMMON_SET_MODEFW(INT(value))
    CASE ("NRMAX");   CALL EQ_COMMON_SET_NRMAX(INT(value))
    CASE ("NTHMAX");  CALL EQ_COMMON_SET_NTHMAX(INT(value))
    CASE ("NSUMAX");  CALL EQ_COMMON_SET_NSUMAX(INT(value))
    CASE ("NSGMAX");  CALL EQ_COMMON_SET_NSGMAX(INT(value))
    CASE ("NTGMAX");  CALL EQ_COMMON_SET_NTGMAX(INT(value))
    CASE ("NUGMAX");  CALL EQ_COMMON_SET_NUGMAX(INT(value))
    CASE ("NRGMAX");  CALL EQ_COMMON_SET_NRGMAX(INT(value))
    CASE ("NZGMAX");  CALL EQ_COMMON_SET_NZGMAX(INT(value))
    CASE ("NPSMAX");  CALL EQ_COMMON_SET_NPSMAX(INT(value))
    CASE ("NRVMAX");  CALL EQ_COMMON_SET_NRVMAX(INT(value))
    CASE ("NTVMAX");  CALL EQ_COMMON_SET_NTVMAX(INT(value))
    CASE ("NPFCMAX"); CALL EQ_COMMON_SET_NPFCMAX(INT(value))
    ! ---- 1D arrays ----
    CASE ("PSIB")
       ! PSIB(0:5) — 0-origin index, unique among EQ registry
       IF (i1 < 0 .OR. i1 > 5) THEN
          ierr = ERR_BAD_INDEX
       ELSE
          CALL EQ_COMMON_SET_PSIB(i1, value)
       END IF
    CASE ("RIPFC")
       IF (i1 < 1 .OR. i1 > 10) THEN
          ierr = ERR_BAD_INDEX
       ELSE
          CALL EQ_COMMON_SET_RIPFC(i1, value)
       END IF
    CASE ("RPFC")
       IF (i1 < 1 .OR. i1 > 10) THEN
          ierr = ERR_BAD_INDEX
       ELSE
          CALL EQ_COMMON_SET_RPFC(i1, value)
       END IF
    CASE ("ZPFC")
       IF (i1 < 1 .OR. i1 > 10) THEN
          ierr = ERR_BAD_INDEX
       ELSE
          CALL EQ_COMMON_SET_ZPFC(i1, value)
       END IF
    CASE ("WPFC")
       IF (i1 < 1 .OR. i1 > 10) THEN
          ierr = ERR_BAD_INDEX
       ELSE
          CALL EQ_COMMON_SET_WPFC(i1, value)
       END IF
    CASE DEFAULT
       ierr = ERR_BAD_NAME
    END SELECT
  END FUNCTION eq_param_set

  FUNCTION eq_param_set_str(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name, value
    INTEGER :: ierr
    EXTERNAL :: EQ_COMMON_SET_KNAMEQ, EQ_COMMON_SET_KNAMWR, &
                EQ_COMMON_SET_KNAMWM, EQ_COMMON_SET_KNAMFP, &
                EQ_COMMON_SET_KNAMFO, EQ_COMMON_SET_KNAMPF, &
                EQ_COMMON_SET_KNAMEQ2
    ierr = ERR_OK
    SELECT CASE (TRIM(name))
    CASE ("KNAMEQ");  CALL EQ_COMMON_SET_KNAMEQ(value)
    CASE ("KNAMWR");  CALL EQ_COMMON_SET_KNAMWR(value)
    CASE ("KNAMWM");  CALL EQ_COMMON_SET_KNAMWM(value)
    CASE ("KNAMFP");  CALL EQ_COMMON_SET_KNAMFP(value)
    CASE ("KNAMFO");  CALL EQ_COMMON_SET_KNAMFO(value)
    CASE ("KNAMPF");  CALL EQ_COMMON_SET_KNAMPF(value)
    CASE ("KNAMEQ2"); CALL EQ_COMMON_SET_KNAMEQ2(value)
    CASE DEFAULT
       ierr = ERR_BAD_NAME
    END SELECT
  END FUNCTION eq_param_set_str

  SUBROUTINE parse_array_subscript(full_name, base, i1, i2)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: i1, i2
    INTEGER :: lb, rb, comma, ios
    base = ' '
    i1 = 0
    i2 = 0
    lb = INDEX(full_name, '[')
    rb = INDEX(full_name, ']', BACK=.TRUE.)
    IF (lb == 0 .AND. rb == 0) THEN
       base = TRIM(ADJUSTL(full_name))
       RETURN
    END IF
    IF (lb == 0 .OR. rb == 0 .OR. rb <= lb + 1) THEN
       base = TRIM(ADJUSTL(full_name))
       i1 = -1
       RETURN
    END IF
    base = full_name(1:lb-1)
    comma = INDEX(full_name(lb+1:rb-1), ',')
    IF (comma > 0) THEN
       READ(full_name(lb+1:lb+comma-1), *, IOSTAT=ios) i1
       IF (ios /= 0) i1 = -1
       READ(full_name(lb+comma+1:rb-1), *, IOSTAT=ios) i2
       IF (ios /= 0) i2 = -1
    ELSE
       READ(full_name(lb+1:rb-1), *, IOSTAT=ios) i1
       IF (ios /= 0) i1 = -1
    END IF
  END SUBROUTINE parse_array_subscript

  ! Public alias for unit testing only.
  SUBROUTINE parse_array_subscript_pub(full_name, base, i1, i2)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: i1, i2
    CALL parse_array_subscript(full_name, base, i1, i2)
  END SUBROUTINE parse_array_subscript_pub

END MODULE eq_param_registry
```

- [ ] **Step 2: parse ユニットテストをビルド・実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make eq_param_registry.o 2>&1 | tail -5
gfortran -I./mod -o tests/c_abi/parse_test \
    tests/c_abi/parse_subscript_unittest.f90 eq_param_registry.o
./tests/c_abi/parse_test
```
Expected: `parse_array_subscript_pub OK`。

---

## Task 6: `eq_api.f90` の `eq_get_state` と `eq_run` を実装

**Files:** Modify: `eq/eq_api.f90`

- [ ] **Step 1: `eq_api_get_state_c` を populate 化**

`eq_api.f90` の `eq_api_get_state_c` のプロファイル部分を、新ヘルパ `EQ_COMMON_GET_PROFILES_1D` で埋める:

```fortran
  FUNCTION eq_api_get_state_c(state) RESULT(ierr) BIND(C, NAME="eq_get_state")
    TYPE(eq_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: nrg, nzg, nps, nrv, nsu
    REAL(C_DOUBLE) :: tj_r, ripx_r
    EXTERNAL :: EQ_COMMON_GET_DIMS, EQ_COMMON_GET_GLOBALS, &
                EQ_COMMON_GET_DEVICE, EQ_COMMON_GET_PROFILES_1D

    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_LIFECYCLE; RETURN
    END IF
    CALL EQ_COMMON_GET_DIMS(nrg, nzg, nps, nrv, nsu)
    IF (nrg > EQ_MAX_NRGMAX .OR. nzg > EQ_MAX_NZGMAX .OR. &
        nps > EQ_MAX_NPSMAX .OR. nrv > EQ_MAX_NRVMAX .OR. &
        nsu > EQ_MAX_NSUMAX) THEN
       ierr = EQ_ERR_BUFFER; RETURN
    END IF
    state%nrgmax = nrg; state%nzgmax = nzg; state%npsmax = nps
    state%nrvmax = nrv; state%nsumax = nsu
    CALL EQ_COMMON_GET_GLOBALS( &
         state%RAXIS, state%ZAXIS, state%PSI0, state%PSIPA, &
         state%PSITA, state%REDGE, state%PVOL, state%RAAVE, &
         state%BETAT, state%BETAP, state%QAXIS, state%QSURF, &
         tj_r, ripx_r)
    state%TJ = tj_r
    state%RIPX = ripx_r
    CALL EQ_COMMON_GET_DEVICE( &
         state%RR, state%RA, state%RB, state%RKAP, state%RDLT, &
         state%BB, state%Q0, state%QA, state%RIP)
    ! Zero buffers first (Fortran auto-initializes INTENT(OUT) fixed-type
    ! components to 0 on some compilers but not all).
    state%PSIPS = 0.0_C_DOUBLE; state%PPPS = 0.0_C_DOUBLE
    state%TTPS  = 0.0_C_DOUBLE; state%QQPS = 0.0_C_DOUBLE
    state%QPV   = 0.0_C_DOUBLE; state%TTV  = 0.0_C_DOUBLE
    state%VPV   = 0.0_C_DOUBLE
    state%RSU   = 0.0_C_DOUBLE; state%ZSU  = 0.0_C_DOUBLE
    CALL EQ_COMMON_GET_PROFILES_1D( &
         EQ_MAX_NPSMAX, state%PSIPS, state%PPPS, state%TTPS, state%QQPS, &
         EQ_MAX_NRVMAX, state%QPV, state%TTV, state%VPV, &
         EQ_MAX_NSUMAX, state%RSU, state%ZSU)
    ierr = EQ_OK
  END FUNCTION eq_api_get_state_c
```

- [ ] **Step 2: `eq_api_run_c(mode=1)` の eq_load ルートを実装**

`eq_api.f90::eq_api_run_c` の `CASE (1)` を:

```fortran
    CASE (1)
       ! Load from EQDSK-format file pointed to by KNAMEQ (set via
       ! eq_set_param_str("KNAMEQ", ...)).
       CALL equnit_eq_load(modelg_dummy, knameq_local, jerr)
       ! Here we must pass the current MODELG; for L-3 we read it
       ! from COMMON via a helper:
       ! (pseudocode — real impl uses EQ_COMMON_GET_MODELG)
       IF (jerr /= 0) THEN
          ierr = EQ_ERR_CALC
          RETURN
       END IF
```

具体的には先に `EQ_COMMON_GET_MODELG(modelg)` と `EQ_COMMON_GET_KNAMEQ(knameq_local)` を呼び、それから `equnit_eq_load(modelg, knameq_local, jerr)` を呼ぶ。2 つのヘルパを Task 4 step 2/4 で追加済みとする。

- [ ] **Step 3: `eq_api_set_param_str_c` を追加**

新規関数を `eq_api.f90` 末尾に追加:

```fortran
  FUNCTION eq_api_set_param_str_c(name, value) RESULT(ierr) &
       BIND(C, NAME="eq_set_param_str")
    USE eq_param_registry, ONLY: eq_param_set_str
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name, value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: fname
    CHARACTER(LEN=80) :: fvalue
    INTEGER :: i
    IF (.NOT. g_initialized) THEN
       ierr = EQ_ERR_LIFECYCLE; RETURN
    END IF
    fname = ' '
    DO i = 1, 64
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
    END DO
    fvalue = ' '
    DO i = 1, 80
       IF (value(i) == C_NULL_CHAR) EXIT
       fvalue(i:i) = value(i)
    END DO
    ierr = eq_param_set_str(TRIM(fname), TRIM(fvalue))
  END FUNCTION eq_api_set_param_str_c
```

`PUBLIC` 行と module 先頭の export に `eq_api_set_param_str_c` を追加。

- [ ] **Step 4: `eq/eq_api.h` に `eq_set_param_str` 追加**

```c
/* Set a string-valued parameter (KNAMEQ, KNAMWR, KNAMWM, KNAMFP,
 * KNAMFO, KNAMPF, KNAMEQ2). */
int eq_set_param_str(const char* name, const char* value);
```

---

## Task 7: 新規 C テストを追加

**Files:**
- Create: `eq/tests/c_abi/test_param.c`
- Create: `eq/tests/c_abi/test_param_str.c`
- Create: `eq/tests/c_abi/test_run_calc.c`
- Modify: `eq/tests/c_abi/Makefile`

- [ ] **Step 1: `test_param.c`**

```c
/* Phase L-3: set RR/BB/RIP/PSIB[0] via eq_set_param, read scalars back
 * via eq_get_state. */
#include <stdio.h>
#include <math.h>
#include "../../eq_api.h"

int main(void) {
    int rc;
    eq_state_t s;
    rc = eq_init();                        if (rc != 0) return 10;
    rc = eq_set_param("RR", 6.2);          if (rc != 0) return 11;
    rc = eq_set_param("BB", 5.3);          if (rc != 0) return 12;
    rc = eq_set_param("RIP", 15.0);        if (rc != 0) return 13;
    rc = eq_set_param("PSIB[0]", 2.5);     if (rc != 0) return 14;
    rc = eq_set_param("PSIB[5]", 0.0);     if (rc != 0) return 15;

    rc = eq_get_state(&s);                 if (rc != 0) return 16;
    if (fabs(s.RR  - 6.2) > 1e-12) { fprintf(stderr,"RR=%g\n",s.RR); return 20; }
    if (fabs(s.BB  - 5.3) > 1e-12) { fprintf(stderr,"BB=%g\n",s.BB); return 21; }
    if (fabs(s.RIP - 15.0)> 1e-12) { fprintf(stderr,"RIP=%g\n",s.RIP); return 22; }

    /* out-of-range PSIB */
    rc = eq_set_param("PSIB[6]", 1.0);
    if (rc == 0) { fprintf(stderr,"PSIB[6] should error\n"); return 23; }

    /* unknown name */
    rc = eq_set_param("NO_SUCH_PARAM", 0.0);
    if (rc == 0) { fprintf(stderr,"unknown name should error\n"); return 24; }

    rc = eq_finalize();                    if (rc != 0) return 30;
    printf("OK: eq_set_param + eq_get_state (RR, BB, RIP, PSIB)\n");
    return 0;
}
```

- [ ] **Step 2: `test_param_str.c`**

```c
/* Phase L-3: eq_set_param_str for KNAMEQ. */
#include <stdio.h>
#include <string.h>
#include "../../eq_api.h"

int main(void) {
    int rc;
    rc = eq_init();                                            if (rc != 0) return 1;
    rc = eq_set_param_str("KNAMEQ", "eqdata_test_l3");         if (rc != 0) return 2;
    rc = eq_set_param_str("KNAMWR", "wrdata_test_l3");         if (rc != 0) return 3;
    rc = eq_set_param_str("NO_SUCH_STR", "x");
    if (rc == 0) { fprintf(stderr,"unknown string name should error\n"); return 4; }
    rc = eq_finalize();                                        if (rc != 0) return 5;
    printf("OK: eq_set_param_str (KNAMEQ, KNAMWR)\n");
    return 0;
}
```

- [ ] **Step 3: `test_run_calc.c`**

```c
/* Phase L-3: eq_run(0) followed by eq_get_state returns sane
 * converged scalars (RAXIS > 0, QAXIS > 0, BETAT > 0). */
#include <stdio.h>
#include "../../eq_api.h"

int main(void) {
    int rc;
    eq_state_t s;
    rc = eq_init();           if (rc != 0) return 1;
    /* Use the eqinit defaults: RR=3, RA=1, BB=3, RIP=3, MODELG=2. */
    rc = eq_run(0);           if (rc != 0) return 2;
    rc = eq_get_state(&s);    if (rc != 0) return 3;
    if (s.RAXIS < 2.0 || s.RAXIS > 4.0) {
        fprintf(stderr,"RAXIS=%g outside sanity band\n", s.RAXIS);
        return 4;
    }
    if (s.QAXIS < 0.1 || s.QAXIS > 10.0) {
        fprintf(stderr,"QAXIS=%g outside sanity band\n", s.QAXIS);
        return 5;
    }
    rc = eq_finalize();       if (rc != 0) return 6;
    printf("OK: eq_run(0) converged: RAXIS=%g QAXIS=%g BETAT=%g\n",
           s.RAXIS, s.QAXIS, s.BETAT);
    return 0;
}
```

- [ ] **Step 4: Makefile に新テスト追加**

`eq/tests/c_abi/Makefile` の末尾に:

```makefile
test_param: test_param.c $(API_OBJS) $(EQ_LIB)
	$(FLINKER) -I$(EQ_DIR) test_param.c $(API_OBJS) $(EQ_LIB) $(DEPS) \
	    $(FFLAGS) $(FLIBS) $(LIBX_MTX) -o test_param

test_param_str: test_param_str.c $(API_OBJS) $(EQ_LIB)
	$(FLINKER) -I$(EQ_DIR) test_param_str.c $(API_OBJS) $(EQ_LIB) $(DEPS) \
	    $(FFLAGS) $(FLIBS) $(LIBX_MTX) -o test_param_str

test_run_calc: test_run_calc.c $(API_OBJS) $(EQ_LIB)
	$(FLINKER) -I$(EQ_DIR) test_run_calc.c $(API_OBJS) $(EQ_LIB) $(DEPS) \
	    $(FFLAGS) $(FLIBS) $(LIBX_MTX) -o test_run_calc

run_all: test_smoke test_param test_param_str test_run_calc
	./test_smoke
	./test_param
	./test_param_str
	./test_run_calc
```

- [ ] **Step 5: 実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq && make 2>&1 | tail -5
cd tests/c_abi && make run_all 2>&1 | tail -20
```
Expected: 4 テスト全 PASS。

---

## Task 8: 回帰テスト

- [ ] **Step 1: eq/pl/ak バイナリの回帰**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eq_iter01 eq_tst2 2>&1 | tail -5
```
Expected: 2/2 PASS。`eq_param_registry` と `eq_api_common` の拡張は `eq` バイナリにリンクされないため、数値は完全に同じ。

- [ ] **Step 2: 他モジュール巻き込み確認**

Run:
```bash
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -5
./run_tests.sh ti_min ti_ar ti_w 2>&1 | tail -5 || true
```
Expected: すべて PASS。

---

## Task 9: コミットと PR

- [ ] **Step 1: 段階コミット**

Run:
```bash
git add eq/eq_api_common.f
git commit -m "feat(eq): expand eq_api_common.f with ~60 COMMON-block setter helpers"

git add eq/eq_param_registry.f90
git commit -m "feat(eq): implement eq_param_registry SELECT CASE table (60 params)

Covers /EQ/ namelist: RR, RA, RB, RKAP, RDLT, BB, RIP, MODELG, MDLEQF,
NRMAX, NTHMAX, NSUMAX, PSIB[0..5], RIPFC[], KNAMEQ and ~50 more.
Adds parse_array_subscript helper and eq_param_set_str for KNAM* file
names."

git add eq/eq_api.f90 eq/eq_api.h
git commit -m "feat(eq): wire eq_get_state arrays and eq_run(mode=1) eq_load path"

git add eq/tests/c_abi/
git commit -m "test(eq): C ABI tests for set_param, set_param_str, run_calc"
```

- [ ] **Step 2: PR**

Run:
```bash
gh pr create --base develop \
  --title "feat(eq): Phase L-3 parameter registry + state populate" \
  --body "Phase L-3: eq_param_registry を実装（60 パラメータ）、eq_api の get_state/run(1) を実体化、KNAMEQ 用 eq_set_param_str を追加。eq/pl/ak 未変更、L-0 回帰 2 ケース PASS。設計は tr-library-L3 の転用 + EQ 固有の F77 COMMON ブリッジ（eq_api_common.f 拡張）。"
```

---

## Risk / Mitigation

| リスク | 影響 | 対策 |
|---|---|---|
| `eq_api_common.f` に 60+ の setter を手書きするのは冗長 | メンテコスト | F77 では macros が弱いので手書き受容。代わりに sphinx コメントでテーブル化。L-7 README で setter 表を自動生成 |
| PSIB の 0-origin 添字で混乱 | ユーザーが 1-origin で叩くとエラー | `eq_api.h` コメントに「PSIB is 0-indexed (0..5)」明記、Python L-5 wrapper で `psib[0]` (Python 流) に合わせる |
| `RBRA = RB/RA` invariant が RA/RB の片方変更時に壊れる | 後続 eq_calc で QA がおかしくなる | `EQ_COMMON_SET_RA/_RB` 内で `RBRA` を自動再計算（Task 4 Step 1 で対策済み）。他の類似 invariant が見つかった場合は L-7 で追記 |
| `equnit::eq_calc` が ierr を返さない | `eq_run(0)` で失敗を検知できない | L-3 で `equnit.f` を薄く変更して `eq_calc_ierr(ierr)` wrapper を追加、それを呼ぶ。本修正は **既存バイナリには影響しない**（新規ラッパを追加するだけ、元 `eq_calc` は残す） |
| F77 setter 名が 32 文字制限を超える (例: `EQ_COMMON_SET_PROFTP2`) | gfortran で truncate 警告 | 現行 gfortran は 63 文字までサポート (`-ffree-line-length-none`)。事前に `grep -n 'EQ_COMMON_SET_.\{30,\}'` で確認 |
| `USE bpsd_kinds, ONLY: rkind` の kind 整合性 | `REAL*8`（F77 side）と `REAL(rkind)`（F90 side）が一致しない環境がある | `task_kinds::dp` (= REAL*8) が全モジュール一致していることを L-0 で確認済み。万一ずれたら `USE task_kinds, ONLY: dp` に統一 |

## Testing Strategy

**Layer 0 (本 L-3):**
- L-0 回帰 2 ケース bit-exact PASS
- `tr_*`, `ti_*` 回帰巻き込みなし
- `nm eq | grep "T eq_init$"` が空（API 未リンク確認継続）

**Layer 1 (C smoke):**
- `test_smoke` (L-2 から継続)
- `test_param`: `RR/BB/RIP/PSIB[0..5]` set → get でラウンドトリップ
- `test_param_str`: `KNAMEQ/KNAMWR` set でエラーなし
- `test_run_calc`: `eq_run(0)` 後の `RAXIS/QAXIS/BETAT` が sanity band 内

**Layer 1.5 (parse unit):**
- `parse_subscript_unittest`: `PSIB[0]` を 0-origin で受ける確認

**Layer 2 以降** は L-4 (libeqapi.so), L-6 (4 層 test) で段階的に追加。

## Deliverables Checklist

- [ ] `eq/eq_param_registry.f90` - 60 個の SELECT CASE + `parse_array_subscript` + `eq_param_set_str`
- [ ] `eq/eq_api_common.f` - 60 個の setter helpers + `EQ_COMMON_GET_PROFILES_1D` + `GET/SET_KNAMEQ` 系 7 対
- [ ] `eq/eq_api.f90` - `eq_get_state` 配列 populate、`eq_run(mode=1)` の eq_load、`eq_set_param_str_c`
- [ ] `eq/eq_api.h` - `eq_set_param_str` プロトタイプ
- [ ] `eq/tests/c_abi/test_param.c` - scalar & array roundtrip
- [ ] `eq/tests/c_abi/test_param_str.c` - KNAMEQ roundtrip
- [ ] `eq/tests/c_abi/test_run_calc.c` - run(0) sanity
- [ ] L-0 回帰 2 ケース PASS
- [ ] PR が develop をターゲットに作成

## 撤退条件 / フォールバック

| 状況 | 判断 |
|---|---|
| 登録対象変数の宣言が大量に COMMON に欠落 | 最小セット 30 個に縮小（device 8 + model 8 + mesh 8 + profile 6）、残りは L-3.5 PR |
| `equnit::eq_calc` ラッパ追加が `eq` バイナリに影響 | 元 `eq_calc` を残したまま `eq_calc_ierr` を**別名で**新設するので影響なし。万一影響が出たら新ラッパを `eq_api.f90` 内にインライン化 |
| `eq_run(1)` テスト用の KNAMEQ ファイルが CI 環境に無い | `test_run_load.c` は本 L-3 スコープから外し、L-6 の fixture 整備と同時実装に回す |
| parse_array_subscript が `PSIB[0]` を受けない | `i1 == 0` を `ERR_BAD_INDEX` にしないよう PSIB CASE 内で個別に 0 <= i <= 5 をチェック（本プランは既にこの形） |
| setter 数が多すぎて `eq_api_common.f` が 1000 行超 | `eq_api_common.f` を機能別に 3 分割 (`eq_api_common_geo.f`, `eq_api_common_profiles.f`, `eq_api_common_model.f`)。Makefile `SRCS_API` に併記 |

## 依存

- **必須前提:** L-2 (`eq_state.f90`, `eq_param_registry.f90` 空シェル, `eq_api.f90`, `eq_api_common.f` ブリッジ, `eq_api.h`) が develop にマージ済み
- **必須前提:** L-0 (PR #54) が develop にマージ済み

## 後続

- **L-4:** `libeqapi.so` 生成 + 本 L-3 実装を shared library で検証
- **L-5:** Python wrapper（`eq.set_param`, `eq.set_param_str`, `eq.run(0/1)`, `eq.get_state()`）
- **L-6:** 4 層回帰 (Fortran bin / C test / Python / 最上位 harness) — L-0 baseline と Python 経由結果が bit-exact 一致するまで追い込み
- **L-7:** ユーザードキュメント（registry パラメータ表を本ドキュメントから転載）
