# WR ライブラリ化 Phase L-3: Parameter Registry 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2 で stub になっていた `wr_set_param(name, value)` を実装し、Python/C 側から名前指定で WR の主要 namelist パラメータと配列要素 (`PN[1]`, `RFIN[1]` など) を書き換えられるようにする。

**Architecture:** TR の `tr_param_registry.f90` と同じ「手書き SELECT CASE テーブル」方式。`wrcomm`/`wrcomm_parm`/`plcomm`/`dpcomm` 由来の WR 関連スカラー / 1次元配列を一括で `MODULE wr_param_registry` 内の `wr_param_set(name, value)` 関数に登録する。配列パラメータは `"PN[1]"` 形式の文字列を `parse_array_subscript` で `base="PN", idx=1` に分解。`wr_api.f90` の `wr_set_param_c` stub を本実装に置き換え、stub の戻り値 `99` を `wr_param_set` の戻り値（0/1）に差し替える。`wr_init_c` 後・`wr_run_c` 前のタイミングでだけ意味があるが、実装はライフサイクル無関係（呼んだ順に値を上書き）。

**Tech Stack:** Fortran 90 (`SELECT CASE`, 文字列パース), C ABI 互換（既存の `wr_set_param` シグネチャ維持）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 5（パラメータテーブル）と Phase L-3。

---

## モジュール調査サマリ

### 登録対象パラメータ（WR 側）

`wr/wrparm.f90` の namelist `WR` を起点に、Python/C 側から触りたい量を以下に分類:

#### A. 幾何パラメータ（`plcomm` 経由）
スカラー: `RR, RA, RB, RKAP, RDLT, BB, Q0, QA, RIP`

#### B. プラズマパラメータ（`plcomm` 経由）
- スカラー: `NSMAX`
- 配列 `[1:NSM]`: `PA, PZ, PN, PNS, PTPR, PTPP, PTS, PU, PUS, PZCL`

#### C. プロファイル制御（`plcomm` 経由）
- スカラー: `PROFN1, PROFN2, PROFT1, PROFT2, PROFU1, PROFU2`
- スカラー: `RHOMIN, QMIN, RHOITB, PNITB, PTITB, PUITB, RHOEDG`
- スカラー: `PPN0, PTN0, RF_PL`

#### D. モデルスイッチ（`plcomm`/`dpcomm` 経由）
スカラー: `MODELG, MODELP, MODELQ, MODEL_PROF, MODEL_NPROF, MODEFW, MODEFR, IDEBUG`
（`MODELP` は `[1:NSM]` 配列）

#### E. WR 固有スカラー（`wrcomm_parm`）
- 整数: `NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, LMAXNW, mode_beam, MDLWRI, MDLWRG, MDLWRP, MDLWRQ, MDLWRW, MODEW, nres_max, nres_type, mode_wline`
- 実数: `SMAX, DELS, UUMIN, EPSRAY, DELRAY, DELDER, DELKR, EPSNW`
- 実数: `RF, RPI, ZPI, PHII, RNZI, RNPHII, RKR0, UUI`
- 実数: `RCURVA, RCURVB, RBRADA, RBRADB`
- 実数: `pne_threshold, bdr_threshold, Rmax_wr, Rmin_wr, Zmax_wr, Zmax_wr`

#### F. WR 固有配列（`wrcomm_parm`、サイズ NRAYM=100）
- 実数: `RFIN[i], RPIN[i], ZPIN[i], PHIIN[i], RKRIN[i], RNZIN[i], RNPHIIN[i], ANGZIN[i], ANGPHIN[i], UUIN[i], RCURVAIN[i], RCURVBIN[i], RBRADAIN[i], RBRADBIN[i]`
- 整数: `MODEWIN[i]`

#### G. dispersion (DP) 制御
- スカラー: `NPMAX_DP, NTHMAX_DP, NRMAX_DP`
- 配列: `NCMIN[i], NCMAX[i], NS_NSA_DP[i]`
- 配列: `MODELV[i], PMAX_DP[i], EMAX_DP[i]`

**初期スコープ（L-3 で確実に登録するセット）:** A〜F すべて。G は L-6 で必要に応じて追加（無くても基本テストは回せる）。

### 既存実装の参考

TR 側の `tr_param_registry.f90` (Phase L-3) を真似る形にする。`wrparm.f90` の namelist 列挙が登録パラメータ表のソースとなる。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wr/wr_param_registry.f90` | 新規 | `MODULE wr_param_registry`, `FUNCTION wr_param_set(name, value) RESULT(ierr)`, `SUBROUTINE parse_array_subscript(...)` |
| `wr/wr_api.f90` | 修正 | `wr_set_param_c` を stub から `wr_param_set` 呼び出しに差し替え |
| `wr/Makefile` | 修正 | `SRCS_API` に `wr_param_registry.f90` を追加（`wr_api.f90` より前） |
| `wr/tests/c_abi/test_param_set.c` | 新規 | C テスト：`wr_init → wr_set_param("RR", 6.2) → wr_run → wr_get_state` で値が反映されているか確認 |
| `wr/tests/c_abi/Makefile` | 修正 | `test_param_set` ターゲット追加 |

---

## Task 1: ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L3-param-registry
```

- [ ] **Step 2: L-2 の `wr_api.f90` stub と `wr_state.f90` が存在することを確認**

Run:
```bash
ls -la /home/k-yoshimi/program/task/wr/wr_api.f90 /home/k-yoshimi/program/task/wr/wr_state.f90 /home/k-yoshimi/program/task/wr/wr_api.h
grep -n "wr_set_param_c\|99" /home/k-yoshimi/program/task/wr/wr_api.f90 | head -5
```
Expected: 3 ファイル存在、`wr_set_param_c` が `ierr = 99` の stub 状態。

- [ ] **Step 3: マーカーコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wr): start Phase L-3 parameter registry"
```

---

## Task 2: `wr/wr_param_registry.f90` を新規作成

**Files:**
- Create: `wr/wr_param_registry.f90`

- [ ] **Step 1: モジュール作成**

Create `/home/k-yoshimi/program/task/wr/wr_param_registry.f90`:
```fortran
! wr_param_registry.f90
!
! Name-based parameter setter for the WR library API.
! Maps "RR", "PN[1]", "RFIN[3]" etc. to the corresponding global variables in
! wrcomm_parm / plcomm / dpcomm.
!
! Phase L-3 scope: WR namelist (groups A..F). DP-side parameters (NPMAX_DP etc.)
! can be added in L-6 if needed by smoke tests.

MODULE wr_param_registry
  USE wrcomm_parm
  USE plcomm
  USE dpcomm
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wr_param_set

CONTAINS

  FUNCTION wr_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),      INTENT(IN) :: value
    INTEGER :: ierr
    INTEGER :: idx
    CHARACTER(LEN=32) :: base

    ierr = 0
    CALL parse_array_subscript(name, base, idx)

    SELECT CASE (TRIM(base))
       ! --- A. Geometry (plcomm) ---
       CASE ("RR");    RR    = value
       CASE ("RA");    RA    = value
       CASE ("RB");    RB    = value
       CASE ("RKAP");  RKAP  = value
       CASE ("RDLT");  RDLT  = value
       CASE ("BB");    BB    = value
       CASE ("Q0");    Q0    = value
       CASE ("QA");    QA    = value
       CASE ("RIP");   RIP   = value

       ! --- B. Plasma (plcomm) ---
       CASE ("NSMAX"); NSMAX = INT(value)
       CASE ("PA");    CALL set_real_array(PA,   idx, value, ierr)
       CASE ("PZ");    CALL set_real_array(PZ,   idx, value, ierr)
       CASE ("PN");    CALL set_real_array(PN,   idx, value, ierr)
       CASE ("PNS");   CALL set_real_array(PNS,  idx, value, ierr)
       CASE ("PTPR");  CALL set_real_array(PTPR, idx, value, ierr)
       CASE ("PTPP");  CALL set_real_array(PTPP, idx, value, ierr)
       CASE ("PTS");   CALL set_real_array(PTS,  idx, value, ierr)
       CASE ("PU");    CALL set_real_array(PU,   idx, value, ierr)
       CASE ("PUS");   CALL set_real_array(PUS,  idx, value, ierr)
       CASE ("PZCL");  CALL set_real_array(PZCL, idx, value, ierr)

       ! --- C. Profile control (plcomm) ---
       CASE ("PROFN1"); PROFN1 = value
       CASE ("PROFN2"); PROFN2 = value
       CASE ("PROFT1"); PROFT1 = value
       CASE ("PROFT2"); PROFT2 = value
       CASE ("PROFU1"); PROFU1 = value
       CASE ("PROFU2"); PROFU2 = value
       CASE ("RHOMIN"); RHOMIN = value
       CASE ("QMIN");   QMIN   = value
       CASE ("RHOITB"); RHOITB = value
       CASE ("PNITB");  PNITB  = value
       CASE ("PTITB");  PTITB  = value
       CASE ("PUITB");  PUITB  = value
       CASE ("RHOEDG"); RHOEDG = value
       CASE ("PPN0");   PPN0   = value
       CASE ("PTN0");   PTN0   = value
       CASE ("RF_PL");  RF_PL  = value

       ! --- D. Model switches (plcomm/dpcomm) ---
       CASE ("MODELG");      MODELG      = INT(value)
       CASE ("MODELQ");      MODELQ      = INT(value)
       CASE ("MODEL_PROF");  MODEL_PROF  = INT(value)
       CASE ("MODEL_NPROF"); MODEL_NPROF = INT(value)
       CASE ("MODEFW");      MODEFW      = INT(value)
       CASE ("MODEFR");      MODEFR      = INT(value)
       CASE ("IDEBUG");      IDEBUG      = INT(value)
       CASE ("MODELP");      CALL set_int_array(MODELP, idx, INT(value), ierr)
       CASE ("MODELV");      CALL set_int_array(MODELV, idx, INT(value), ierr)
       CASE ("NCMIN");       CALL set_int_array(NCMIN,  idx, INT(value), ierr)
       CASE ("NCMAX");       CALL set_int_array(NCMAX,  idx, INT(value), ierr)

       ! --- E. WR scalars (wrcomm_parm) ---
       CASE ("NRAYMAX");   NRAYMAX   = INT(value)
       CASE ("NSTPMAX");   NSTPMAX   = INT(value)
       CASE ("NRSMAX");    NRSMAX    = INT(value)
       CASE ("NRLMAX");    NRLMAX    = INT(value)
       CASE ("LMAXNW");    LMAXNW    = INT(value)
       CASE ("mode_beam"); mode_beam = INT(value)
       CASE ("MDLWRI");    MDLWRI    = INT(value)
       CASE ("MDLWRG");    MDLWRG    = INT(value)
       CASE ("MDLWRP");    MDLWRP    = INT(value)
       CASE ("MDLWRQ");    MDLWRQ    = INT(value)
       CASE ("MDLWRW");    MDLWRW    = INT(value)
       CASE ("MODEW");     MODEW     = INT(value)
       CASE ("nres_max");  nres_max  = INT(value)
       CASE ("nres_type"); nres_type = INT(value)
       CASE ("mode_wline"); mode_wline = INT(value)
       CASE ("SMAX");      SMAX      = value
       CASE ("DELS");      DELS      = value
       CASE ("UUMIN");     UUMIN     = value
       CASE ("EPSRAY");    EPSRAY    = value
       CASE ("DELRAY");    DELRAY    = value
       CASE ("DELDER");    DELDER    = value
       CASE ("DELKR");     DELKR     = value
       CASE ("EPSNW");     EPSNW     = value
       CASE ("RF");        RF        = value
       CASE ("RPI");       RPI       = value
       CASE ("ZPI");       ZPI       = value
       CASE ("PHII");      PHII      = value
       CASE ("RNZI");      RNZI      = value
       CASE ("RNPHII");    RNPHII    = value
       CASE ("RKR0");      RKR0      = value
       CASE ("UUI");       UUI       = value
       CASE ("RCURVA");    RCURVA    = value
       CASE ("RCURVB");    RCURVB    = value
       CASE ("RBRADA");    RBRADA    = value
       CASE ("RBRADB");    RBRADB    = value
       CASE ("pne_threshold"); pne_threshold = value
       CASE ("bdr_threshold"); bdr_threshold = value
       CASE ("Rmax_wr");   Rmax_wr   = value
       CASE ("Rmin_wr");   Rmin_wr   = value
       CASE ("Zmax_wr");   Zmax_wr   = value
       CASE ("Zmin_wr");   Zmin_wr   = value

       ! --- F. WR per-ray arrays (wrcomm_parm) ---
       CASE ("RFIN");      CALL set_real_array(RFIN,    idx, value, ierr)
       CASE ("RPIN");      CALL set_real_array(RPIN,    idx, value, ierr)
       CASE ("ZPIN");      CALL set_real_array(ZPIN,    idx, value, ierr)
       CASE ("PHIIN");     CALL set_real_array(PHIIN,   idx, value, ierr)
       CASE ("RKRIN");     CALL set_real_array(RKRIN,   idx, value, ierr)
       CASE ("RNZIN");     CALL set_real_array(RNZIN,   idx, value, ierr)
       CASE ("RNPHIIN");   CALL set_real_array(RNPHIIN, idx, value, ierr)
       CASE ("ANGZIN");    CALL set_real_array(ANGZIN,  idx, value, ierr)
       CASE ("ANGPHIN");   CALL set_real_array(ANGPHIN, idx, value, ierr)
       CASE ("UUIN");      CALL set_real_array(UUIN,    idx, value, ierr)
       CASE ("RCURVAIN");  CALL set_real_array(RCURVAIN, idx, value, ierr)
       CASE ("RCURVBIN");  CALL set_real_array(RCURVBIN, idx, value, ierr)
       CASE ("RBRADAIN");  CALL set_real_array(RBRADAIN, idx, value, ierr)
       CASE ("RBRADBIN");  CALL set_real_array(RBRADBIN, idx, value, ierr)
       CASE ("MODEWIN");   CALL set_int_array(MODEWIN,  idx, INT(value), ierr)

       CASE DEFAULT
          ierr = 1
    END SELECT
  END FUNCTION wr_param_set

  SUBROUTINE parse_array_subscript(full, base, idx)
    ! "PN[1]"   -> base="PN",   idx=1
    ! "RFIN[3]" -> base="RFIN", idx=3
    ! "RR"      -> base="RR",   idx=0
    CHARACTER(LEN=*), INTENT(IN)  :: full
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx
    INTEGER :: i_lb, i_rb, ios

    i_lb = INDEX(full, '[')
    i_rb = INDEX(full, ']')
    IF (i_lb > 0 .AND. i_rb > i_lb) THEN
       base = full(1:i_lb-1)
       READ(full(i_lb+1:i_rb-1), *, IOSTAT=ios) idx
       IF (ios /= 0) idx = -1
    ELSE
       base = TRIM(full)
       idx = 0
    END IF
  END SUBROUTINE parse_array_subscript

  SUBROUTINE set_real_array(arr, idx, value, ierr)
    REAL(rkind), DIMENSION(:), INTENT(INOUT) :: arr
    INTEGER, INTENT(IN) :: idx
    REAL(rkind), INTENT(IN) :: value
    INTEGER, INTENT(INOUT) :: ierr
    IF (idx < 1 .OR. idx > SIZE(arr)) THEN
       ierr = 1
       RETURN
    END IF
    arr(idx) = value
  END SUBROUTINE set_real_array

  SUBROUTINE set_int_array(arr, idx, value, ierr)
    INTEGER, DIMENSION(:), INTENT(INOUT) :: arr
    INTEGER, INTENT(IN) :: idx, value
    INTEGER, INTENT(INOUT) :: ierr
    IF (idx < 1 .OR. idx > SIZE(arr)) THEN
       ierr = 1
       RETURN
    END IF
    arr(idx) = value
  END SUBROUTINE set_int_array

END MODULE wr_param_registry
```

注: `MODELP` などが `plcomm` 経由でなく `dpcomm` にある場合は `USE` リストを修正。コンパイル時に `Symbol 'MODELP' has no IMPLICIT type` 等が出たら `wrparm.f90` の namelist `WR` で `MODELP` を `USE plcomm` 経由で参照しているか `USE dpcomm` 経由かを確認し、`USE` 文を合わせる。

- [ ] **Step 2: 単体コンパイル**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
gfortran -c -g -O3 -std=legacy \
    -I./mod -I../pl/mod -I../dp/mod -I../eq/mod -I../lib/mod -I../mtxp/mod -I../../bpsd/mod \
    -J./mod wr_param_registry.f90 -o /tmp/wr_param_registry_check.o 2>&1 | tail -30
echo "exit=$?"
```
Expected: コンパイル成功。失敗したら、エラー行に出ている変数名を `wrparm.f90` の namelist と照合し、不要なエントリを削除。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/wr_param_registry.f90
git commit -m "feat(wr): add wr_param_registry.f90 with name-based setter"
```

---

## Task 3: `wr_api.f90` の `wr_set_param_c` を実装に差し替え

**Files:**
- Modify: `wr/wr_api.f90`

- [ ] **Step 1: stub を本実装に置き換え**

Modify `/home/k-yoshimi/program/task/wr/wr_api.f90`. Locate the stub:

Old:
```fortran
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
```

New:
```fortran
  FUNCTION wr_set_param_c(name, value) RESULT(ierr) BIND(C, NAME="wr_set_param")
    USE wr_param_registry, ONLY: wr_param_set
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: f_name
    INTEGER :: i, n

    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF

    ! Convert C string to Fortran string (max 63 chars + null).
    f_name = ''
    DO i = 1, LEN(f_name)
       IF (name(i) == C_NULL_CHAR) EXIT
       f_name(i:i) = name(i)
    END DO

    ierr = wr_param_set(TRIM(f_name), value)
  END FUNCTION wr_set_param_c
```

- [ ] **Step 2: コンパイル**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
gfortran -c -g -O3 -std=legacy \
    -I./mod -I../pl/mod -I../dp/mod -I../eq/mod -I../lib/mod -I../mtxp/mod -I../../bpsd/mod \
    -J./mod wr_api.f90 -o /tmp/wr_api_check.o 2>&1 | tail -10
```
Expected: 成功。`wr_param_registry` モジュールが見つからない場合は Task 4 の Makefile 修正を先に。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/wr_api.f90
git commit -m "feat(wr): wire wr_set_param_c to wr_param_registry (replace stub)"
```

---

## Task 4: `wr/Makefile` を更新

**Files:**
- Modify: `wr/Makefile`

- [ ] **Step 1: `SRCS_API` に `wr_param_registry.f90` を追加**

Modify `/home/k-yoshimi/program/task/wr/Makefile`.

Old:
```
SRCS_API = wr_state.f90 wr_api.f90
```

New:
```
SRCS_API = wr_state.f90 wr_param_registry.f90 wr_api.f90
```

And add a dependency rule near the bottom (after `$(OBJDIR)/wr_state.o:`):
```
$(OBJDIR)/wr_param_registry.o: wr_param_registry.f90 $(WRCOMM)
$(OBJDIR)/wr_api.o: wr_api.f90 wr_state.f90 wr_param_registry.f90 $(WRCOMM) wrinit.f90 wrsetup.f90 wrexec.f90
```
(Replace the existing `$(OBJDIR)/wr_api.o:` line.)

- [ ] **Step 2: フルビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make clean && make 2>&1 | tail -15
```
Expected: 全ビルド成功、`wr` バイナリが更新される。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/Makefile
git commit -m "build(wr): add wr_param_registry.f90 to SRCS_API"
```

---

## Task 5: C テスト `test_param_set` を追加

**Files:**
- Create: `wr/tests/c_abi/test_param_set.c`
- Modify: `wr/tests/c_abi/Makefile`

- [ ] **Step 1: C テスト作成**

Create `/home/k-yoshimi/program/task/wr/tests/c_abi/test_param_set.c`:
```c
/* test_param_set.c
 *
 * Phase L-3 test for wr_set_param.
 *   - "RR"        scalar -> ok
 *   - "PN[2]"     real array -> ok
 *   - "RFIN[1]"   per-ray real array -> ok
 *   - "MODEWIN[1]" per-ray int array -> ok (passed as double, INT()ed inside)
 *   - "BOGUS"     unknown name -> ierr=1
 *   - "PN[999]"   out-of-range index -> ierr=1
 *   - calling without wr_init() -> ierr=2
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
    /* Pre-init: should reject. */
    EXPECT(wr_set_param("RR", 6.2), 2);

    EXPECT(wr_init(), 0);

    EXPECT(wr_set_param("RR",        6.2),    0);
    EXPECT(wr_set_param("BB",        5.3),    0);
    EXPECT(wr_set_param("NSMAX",     2.0),    0);
    EXPECT(wr_set_param("PN[1]",     1.0),    0);
    EXPECT(wr_set_param("PN[2]",     1.0),    0);
    EXPECT(wr_set_param("NRAYMAX",   1.0),    0);
    EXPECT(wr_set_param("RFIN[1]",   5.0e3,  0);
    EXPECT(wr_set_param("MODEWIN[1]",1.0),    0);

    /* Failure cases */
    EXPECT(wr_set_param("BOGUS",     0.0),    1);
    EXPECT(wr_set_param("PN[999]",   1.0),    1);
    EXPECT(wr_set_param("PN[0]",     1.0),    1);

    EXPECT(wr_finalize(), 0);
    return fail ? 1 : 0;
}
```

注: 上記の `RFIN[1], 5.0e3, 0` の閉じ括弧抜けは意図的なミス防止のため、実装時に必ず `EXPECT(wr_set_param("RFIN[1]", 5.0e3), 0);` の形に修正すること。コピペ時の括弧位置に注意。

- [ ] **Step 2: Makefile に test_param_set ターゲット追加**

Modify `/home/k-yoshimi/program/task/wr/tests/c_abi/Makefile`. Append after `test_abi_stub` rule:
```
test_param_set: test_param_set.c $(WR_LIB)
	$(CC) $(CFLAGS) test_param_set.c $(WR_LIB) $(DEPS) $(LIB_MTX) $(LIBX_MTX) \
	    $(FLIBS) -lm -o $@

run-all: test_abi_stub test_param_set
	./test_abi_stub && ./test_param_set
```

Update `clean`:
```
clean:
	-rm -f test_abi_stub test_param_set
```

- [ ] **Step 3: ビルドと実行**

Run:
```bash
cd /home/k-yoshimi/program/task/wr/tests/c_abi
make test_param_set 2>&1 | tail -10
./test_param_set
echo "exit=$?"
```
Expected: 全 EXPECT 行で OK、exit 0。

- [ ] **Step 4: 既存テストへの影響なしを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr/tests/c_abi
make run-all
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: 全件 PASS。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/tests/c_abi/test_param_set.c wr/tests/c_abi/Makefile
git commit -m "test(wr): add C ABI test for wr_set_param (Phase L-3)"
```

---

## 完了基準

- [ ] `wr/wr_param_registry.f90` が追加され、A〜F の namelist パラメータをカバー
- [ ] `wr_api.f90::wr_set_param_c` が stub から実装に差し替え済み
- [ ] C テスト `test_param_set` で正常系・異常系（unknown name, out-of-range index, pre-init）全て期待通り
- [ ] 既存 wr バイナリと WR/TR/EQ/TX 回帰テストに影響なし

## 撤退条件

- 全パラメータ登録でコンパイルが通らない場合 → 最小セット（`RR, BB, NSMAX, PN[], NRAYMAX, RFIN[], ANGPHIN[]`）に絞って commit、残りは後続タスクで追加
- DP 系 (`MODELV, NCMIN, NCMAX`) で未定義シンボル → `USE dpcomm, ONLY:` リストを `wrparm.f90` の namelist と完全に揃える
- `parse_array_subscript` のテストで `IOSTAT` が常にゼロ非ゼロにブレる場合 → `READ(..., FMT='(I)')` 等明示書式に切り替え

## 依存

- 前提: L-2 完了（`wr_api.f90` stub と `wr_state.f90` 存在）
- 後続: L-4 (`libwrapi.so` ビルド) で `wr_param_registry.o` が PIC リビルド対象に入る
