# TOT Library Phase L-3: Parameter Registry 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tot_set_param(name, value)` を実装する。tot は per-module namelist の **union** を扱うため、`name` の prefix（`TR.`, `TI.`, `FP.`, `WR.`, `WM.`, `EQ.`, `PL.`）で対応モジュールに dispatch する `tot_param_registry.f90` を新設する。

**Architecture:** `tot_param_registry.f90` は **薄い dispatcher** で、実体の setter は per-module の `tr_param_set / ti_param_set / fp_param_set / wr_param_set / wm_param_set / pl_param_set` に委譲する。tot 自身が独自に namelist 変数を直接書き換えることはしない（これは「既存 namelist 変数は所有モジュールが管理する」原則に従う）。EQ は F77 で `.inc` includes ベースなので、`EQ.RR` のような少数の主要パラメータのみハードコードで設定する補助 setter を tot 側に持つ。

**Tech Stack:** Fortran 90 (`SELECT CASE`, string parsing), 既存 per-module `*_param_set` 関数。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 5（パラメータテーブル機構）を tot に拡張、`name` に prefix を導入。

**前提条件:** L-0 / L-1 / L-2 完了。**個別モジュール（tr, ti, fp, wr, wm, pl）の Phase L-3（パラメータレジストリ）が完成済みで `*_param_set(name, value)` が呼べる**こと。EQ については Phase 0 制約により、限定的なパラメータのみサポート。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `tot/tot_param_registry.f90` | 新規 | prefix dispatcher。`TR.X` → `tr_param_set('X', value)` 等 |
| `tot/tot_api.f90` | 修正 | `tot_set_param` の stub を `tot_param_registry` 呼び出しに置換 |
| `tot/Makefile` | 修正 | `SRCS_API` に `tot_param_registry.f90` を追加 |
| `tot/tot_param_registry_test.f90` | 新規 | parameter dispatcher の Fortran 単体テスト（最小） |
| `tot/tests/c_abi/test_abi.c` | 修正 | `tot_set_param("TR.RR", 6.2)` 等の Pass case を追加 |

**方針:**
- prefix は `<MODULE>.<NAME>` 形式（ピリオド区切り）。array index は `<MODULE>.<NAME>[<idx>]`（例: `TR.PN[1]`）。
- 1-origin インデックス（既存 Fortran 慣習に準拠）。
- 未知 prefix は `ierr=1`、prefix 内で未知 name は per-module の registry が `ierr=1` を返す。
- EQ モジュールは Phase 0 段階では非ライブラリ化（F77 + .inc）。L-3 では `EQ.RR / EQ.RA / EQ.BB / EQ.RIP / EQ.RKAP / EQ.RDLT` の 6 つだけ tot 側に直接ハードコード setter を用意（`equnit` モジュールへの直接代入）。それ以上は L-7 で必要に応じ拡張。

---

## Task 1: 作業用ブランチと前提確認

**Files:** なし

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop && git pull
git checkout -b feature/tot-library-l3-param-registry
```

- [ ] **Step 2: 個別モジュールの param_set 関数の有無を確認**

Run:
```bash
grep -l "FUNCTION.*param_set\|tr_param_set\|ti_param_set\|fp_param_set\|wr_param_set\|wm_param_set\|pl_param_set" \
   /home/k-yoshimi/program/task/tr/*.f90 \
   /home/k-yoshimi/program/task/ti/*.f90 \
   /home/k-yoshimi/program/task/fp/*.f90 \
   /home/k-yoshimi/program/task/wr/*.f90 \
   /home/k-yoshimi/program/task/wm/*.f90 \
   /home/k-yoshimi/program/task/pl/*.f90 \
   2>&1
```
Expected: 各モジュールの param_set ファイルが見つかる。見つからないモジュールは L-3 fan-out を「TODO コメント + `ierr=1`」にする。

- [ ] **Step 3: L-2 baseline 確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
cd /home/k-yoshimi/program/task/tot/tests/c_abi
make run
```
Expected: 全 PASS。

- [ ] **Step 4: 初期コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(tot): start L-3 parameter registry"
```

---

## Task 2: 失敗するテストを先に書く（TDD）

**Files:**
- Modify: `tot/tests/c_abi/test_abi.c`

- [ ] **Step 1: テストケース追加**

`tot/tests/c_abi/test_abi.c` を以下に書き換え:

```c
/*
 * test_abi.c — C ABI smoke test for tot Phase L-3.
 *
 * Verifies that tot_set_param dispatches to per-module setters using
 * the "<MODULE>.<NAME>" naming convention.
 */
#include <stdio.h>
#include <assert.h>
#include "tot_api.h"

int main(void) {
    int rc;

    /* Init must come first for set_param paths that touch state. */
    rc = tot_init();
    assert(rc == 0 && "tot_init must succeed");

    /* Valid TR scalar parameter. */
    rc = tot_set_param("TR.RR", 6.2);
    assert(rc == 0 && "tot_set_param('TR.RR', 6.2) must succeed");

    /* Valid TR array parameter (1-origin). */
    rc = tot_set_param("TR.PN[1]", 0.7);
    assert(rc == 0 && "tot_set_param('TR.PN[1]', 0.7) must succeed");

    /* Unknown prefix. */
    rc = tot_set_param("ZZ.NONE", 0.0);
    assert(rc == 1 && "unknown prefix must return 1");

    /* Unknown name within known prefix. */
    rc = tot_set_param("TR.NOSUCHVAR", 0.0);
    assert(rc == 1 && "unknown name must return 1");

    /* Missing prefix (no '.') -- treated as invalid. */
    rc = tot_set_param("RR", 6.2);
    assert(rc == 1 && "name without prefix must return 1");

    /* EQ partial support. */
    rc = tot_set_param("EQ.RR", 6.2);
    assert(rc == 0 && "EQ.RR must be supported in L-3");

    /* EQ unsupported parameter. */
    rc = tot_set_param("EQ.NOTYET", 0.0);
    assert(rc == 1 && "EQ.NOTYET must return 1 (out of L-3 scope)");

    rc = tot_finalize();
    assert(rc == 0 && "tot_finalize must succeed");

    printf("test_abi: PASS (L-3 dispatcher verified)\n");
    return 0;
}
```

- [ ] **Step 2: ビルドして失敗することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot/tests/c_abi
make clean && make run 2>&1 | tail -20
```
Expected: assertion failure（`tot_set_param('TR.RR', 6.2)` が ierr=1 を返すため）。

- [ ] **Step 3: コミット（failing test を残す）**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/tests/c_abi/test_abi.c
git commit -m "test(tot): add failing tests for L-3 param dispatcher"
```

---

## Task 3: `tot/tot_param_registry.f90` を新規作成

**Files:**
- Create: `tot/tot_param_registry.f90`

- [ ] **Step 1: 新規作成**

作成: `tot/tot_param_registry.f90`

```fortran
! tot_param_registry.f90
!
! Dispatch tot_set_param("<MODULE>.<NAME>", value) to per-module setters.
!
! Naming convention:
!   "<PREFIX>.<NAME>"          scalar         e.g. "TR.RR"
!   "<PREFIX>.<NAME>[<idx>]"   array (1-orig) e.g. "TR.PN[1]"
!
! Supported PREFIX (L-3 scope):
!   TR -> tr_param_set
!   TI -> ti_param_set
!   FP -> fp_param_set
!   WR -> wr_param_set
!   WM -> wm_param_set
!   PL -> pl_param_set
!   EQ -> hardcoded setter (only RR/RA/BB/RIP/RKAP/RDLT) — EQ is F77 + .inc
!
! Returns:
!   0 = success
!   1 = unknown prefix or unknown name
!   3 = per-module setter signaled an error

MODULE tot_param_registry
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tot_param_set

CONTAINS

  FUNCTION tot_param_set(name_c, value) RESULT(ierr)
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name_c
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr

    CHARACTER(LEN=64) :: name_f
    CHARACTER(LEN=8)  :: prefix
    CHARACTER(LEN=56) :: tail
    INTEGER :: dot_pos

    CALL c_string_to_fortran(name_c, name_f)
    dot_pos = INDEX(name_f, '.')
    IF (dot_pos < 2 .OR. dot_pos == LEN_TRIM(name_f)) THEN
       ierr = 1; RETURN
    END IF
    prefix = name_f(1:dot_pos-1)
    tail   = name_f(dot_pos+1:)

    SELECT CASE (TRIM(prefix))
    CASE ('TR'); ierr = dispatch_tr(TRIM(tail), value)
    CASE ('TI'); ierr = dispatch_ti(TRIM(tail), value)
    CASE ('FP'); ierr = dispatch_fp(TRIM(tail), value)
    CASE ('WR'); ierr = dispatch_wr(TRIM(tail), value)
    CASE ('WM'); ierr = dispatch_wm(TRIM(tail), value)
    CASE ('PL'); ierr = dispatch_pl(TRIM(tail), value)
    CASE ('EQ'); ierr = dispatch_eq(TRIM(tail), REAL(value, KIND(1.0D0)))
    CASE DEFAULT; ierr = 1
    END SELECT
  END FUNCTION tot_param_set

  ! ----- per-module dispatchers -------------------------------------

  FUNCTION dispatch_tr(name, value) RESULT(ierr)
    USE tr_param_registry, ONLY: tr_param_set
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(C_DOUBLE), INTENT(IN) :: value
    INTEGER :: ierr
    ierr = tr_param_set(name, REAL(value, KIND(1.0D0)))
    IF (ierr /= 0 .AND. ierr /= 1) ierr = 3
  END FUNCTION dispatch_tr

  FUNCTION dispatch_ti(name, value) RESULT(ierr)
    USE ti_param_registry, ONLY: ti_param_set
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(C_DOUBLE), INTENT(IN) :: value
    INTEGER :: ierr
    ierr = ti_param_set(name, REAL(value, KIND(1.0D0)))
    IF (ierr /= 0 .AND. ierr /= 1) ierr = 3
  END FUNCTION dispatch_ti

  FUNCTION dispatch_fp(name, value) RESULT(ierr)
    USE fp_param_registry, ONLY: fp_param_set
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(C_DOUBLE), INTENT(IN) :: value
    INTEGER :: ierr
    ierr = fp_param_set(name, REAL(value, KIND(1.0D0)))
    IF (ierr /= 0 .AND. ierr /= 1) ierr = 3
  END FUNCTION dispatch_fp

  FUNCTION dispatch_wr(name, value) RESULT(ierr)
    USE wr_param_registry, ONLY: wr_param_set
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(C_DOUBLE), INTENT(IN) :: value
    INTEGER :: ierr
    ierr = wr_param_set(name, REAL(value, KIND(1.0D0)))
    IF (ierr /= 0 .AND. ierr /= 1) ierr = 3
  END FUNCTION dispatch_wr

  FUNCTION dispatch_wm(name, value) RESULT(ierr)
    USE wm_param_registry, ONLY: wm_param_set
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(C_DOUBLE), INTENT(IN) :: value
    INTEGER :: ierr
    ierr = wm_param_set(name, REAL(value, KIND(1.0D0)))
    IF (ierr /= 0 .AND. ierr /= 1) ierr = 3
  END FUNCTION dispatch_wm

  FUNCTION dispatch_pl(name, value) RESULT(ierr)
    USE pl_param_registry, ONLY: pl_param_set
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(C_DOUBLE), INTENT(IN) :: value
    INTEGER :: ierr
    ierr = pl_param_set(name, REAL(value, KIND(1.0D0)))
    IF (ierr /= 0 .AND. ierr /= 1) ierr = 3
  END FUNCTION dispatch_pl

  FUNCTION dispatch_eq(name, value) RESULT(ierr)
    ! EQ is F77 + .inc; we set a small whitelist of geometry/coil scalars
    ! directly through equnit. Full EQ library-ization is a separate phase.
    USE equnit_mod, ONLY: eq_set_geometry   ! see Task 4 for stub if missing
    CHARACTER(LEN=*), INTENT(IN) :: name
    DOUBLE PRECISION, INTENT(IN) :: value
    INTEGER :: ierr
    ierr = 0
    SELECT CASE (TRIM(name))
    CASE ('RR');   CALL eq_set_geometry('RR',   value)
    CASE ('RA');   CALL eq_set_geometry('RA',   value)
    CASE ('BB');   CALL eq_set_geometry('BB',   value)
    CASE ('RIP');  CALL eq_set_geometry('RIP',  value)
    CASE ('RKAP'); CALL eq_set_geometry('RKAP', value)
    CASE ('RDLT'); CALL eq_set_geometry('RDLT', value)
    CASE DEFAULT; ierr = 1
    END SELECT
  END FUNCTION dispatch_eq

  ! ----- helpers ----------------------------------------------------

  SUBROUTINE c_string_to_fortran(c_str, f_str)
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: c_str
    CHARACTER(LEN=*),                     INTENT(OUT) :: f_str
    INTEGER :: i
    f_str = ' '
    DO i = 1, LEN(f_str)
       IF (c_str(i) == C_NULL_CHAR) EXIT
       f_str(i:i) = c_str(i)
    END DO
  END SUBROUTINE c_string_to_fortran

END MODULE tot_param_registry
```

- [ ] **Step 2: `eq_set_geometry` の存在を確認**

Run:
```bash
grep -rn "eq_set_geometry\|SUBROUTINE eqgsetparm" /home/k-yoshimi/program/task/eq/ 2>&1 | head -5
```
Expected: 既存にあれば USE できる。なければ Task 4 で簡易 stub を追加。

- [ ] **Step 3: コミット**

Run:
```bash
git add tot/tot_param_registry.f90
git commit -m "feat(tot): add tot_param_registry.f90 dispatcher"
```

---

## Task 4: 必要なら `eq_set_geometry` の薄いラッパを tot 側に作る

**Files:**
- Create: `tot/eq_geometry_setter.f90` (eq に直接書ける関数が無い場合のみ)

- [ ] **Step 1: 既存 EQ モジュールの geometry setter を再確認**

Run:
```bash
grep -n "RR\s*=\|RA\s*=\|BB\s*=\|RIP\s*=" /home/k-yoshimi/program/task/eq/equnit.f | head
grep -n "MODULE\|SUBROUTINE eq_init" /home/k-yoshimi/program/task/eq/equnit.f | head
```
Expected: equnit.f 内で RR/RA/BB/RIP の参照が見つかる。

- [ ] **Step 2: ラッパを新規作成（eq_set_geometry が無い場合）**

作成: `tot/eq_geometry_setter.f90`

```fortran
! eq_geometry_setter.f90
!
! Thin wrapper allowing tot_param_registry to set a small subset of EQ
! geometry scalars without library-izing the F77 EQ module yet.
! All values are written via the equnit common block / module variable.

MODULE equnit_mod
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: eq_set_geometry

CONTAINS

  SUBROUTINE eq_set_geometry(name, value)
    USE plparm, ONLY: RR, RA, BB, RIP, RKAP, RDLT   ! pl owns geometry by convention
    CHARACTER(LEN=*),    INTENT(IN) :: name
    DOUBLE PRECISION,    INTENT(IN) :: value
    SELECT CASE (TRIM(name))
    CASE ('RR');   RR   = value
    CASE ('RA');   RA   = value
    CASE ('BB');   BB   = value
    CASE ('RIP');  RIP  = value
    CASE ('RKAP'); RKAP = value
    CASE ('RDLT'); RDLT = value
    END SELECT
    ! Note: EQ recomputes geometry on next eq_init / eqcalc call.
    ! Caller is responsible for rerunning eq if needed.
  END SUBROUTINE eq_set_geometry

END MODULE equnit_mod
```

`plparm` が幾何変数の本籍であることを確認 (`grep "RR\|RA\|BB" /home/k-yoshimi/program/task/pl/plparm.f90 | head`)。違えば適切なモジュールに USE 先を置換。

- [ ] **Step 3: コミット**

Run:
```bash
git add tot/eq_geometry_setter.f90
git commit -m "feat(tot): add minimal EQ geometry setter for L-3 (RR/RA/BB/RIP/RKAP/RDLT)"
```

---

## Task 5: `tot_api.f90` の `tot_set_param` を実装に置換

**Files:**
- Modify: `tot/tot_api.f90`

- [ ] **Step 1: stub を置換**

`tot/tot_api.f90` の `tot_set_param` を以下に置換:

変更前:
```fortran
  FUNCTION tot_set_param(name, value) RESULT(ierr) BIND(C, NAME="tot_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    INTEGER :: dummy_len
    dummy_len = 0
    IF (value == 0.0_C_DOUBLE) dummy_len = 0
    ierr = 1
  END FUNCTION tot_set_param
```

変更後:
```fortran
  FUNCTION tot_set_param(name, value) RESULT(ierr) BIND(C, NAME="tot_set_param")
    USE tot_param_registry, ONLY: tot_param_set
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    IF (.NOT. initialized) THEN
       ierr = 2; RETURN
    END IF
    ierr = tot_param_set(name, value)
  END FUNCTION tot_set_param
```

- [ ] **Step 2: コミット**

Run:
```bash
git add tot/tot_api.f90
git commit -m "feat(tot): wire tot_set_param to tot_param_registry dispatcher"
```

---

## Task 6: Makefile 更新

**Files:**
- Modify: `tot/Makefile`

- [ ] **Step 1: SRCS_API 拡張**

変更前:
```makefile
SRCS_API  = tot_state.f90 tot_api.f90
```

変更後:
```makefile
SRCS_API  = tot_state.f90 eq_geometry_setter.f90 tot_param_registry.f90 tot_api.f90
```

注: `eq_geometry_setter.f90` は Task 4 で作った場合のみ含める。

- [ ] **Step 2: コンパイル順序の確認（依存解決）**

Fortran モジュール依存:
- `tot_param_registry` USE `tr_param_registry, ti_param_registry, ..., equnit_mod`
- `tot_api` USE `tot_param_registry`

Make の `.f90.o` ルールが `MODINCLUDE` で他モジュールパスを通しているので、依存解決は OK。

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make clean && make tot 2>&1 | tail -15
```
Expected: ビルド成功。`tot` バイナリ生成。

リンクエラー（undefined `tr_param_set` 等）が出る場合:
- per-module の libapi.a に `*_param_registry.o` が含まれているか確認
- 暫定対応: `tot/Makefile` の `LIBS` に直接 `.o` を追加

- [ ] **Step 3: コミット**

Run:
```bash
git add tot/Makefile
git commit -m "build(tot): add tot_param_registry to SRCS_API"
```

---

## Task 7: C ABI テストを通す

**Files:** なし（既存テストで検証）

- [ ] **Step 1: テスト Makefile の OBJS 更新**

`tot/tests/c_abi/Makefile` の OBJS を以下に拡張:

```makefile
OBJS = $(TOT_DIR)/tot_state.o \
       $(TOT_DIR)/eq_geometry_setter.o \
       $(TOT_DIR)/tot_param_registry.o \
       $(TOT_DIR)/tot_api.o
```

`DEPS` に per-module の `*_param_registry.o` も追加:

```makefile
DEPS = $(TR_DIR)/tr_state.o $(TR_DIR)/tr_param_registry.o $(TR_DIR)/tr_api.o $(TR_DIR)/libtr2.a \
       $(TI_DIR)/ti_param_registry.o $(TI_DIR)/libti.a \
       $(FP_DIR)/fp_param_registry.o $(FP_DIR)/libfp.a \
       $(WR_DIR)/wr_param_registry.o $(WR_DIR)/libwr.a \
       $(WM_DIR)/wm_param_registry.o $(WM_DIR)/libwm.a \
       $(PL_DIR)/pl_param_registry.o $(PL_DIR)/libpl.a \
       $(EQ_DIR)/libeq.a
```

Makefile 冒頭にディレクトリ変数を追加:
```makefile
TI_DIR = ../../../ti
FP_DIR = ../../../fp
WR_DIR = ../../../wr
WM_DIR = ../../../wm
PL_DIR = ../../../pl
EQ_DIR = ../../../eq
```

- [ ] **Step 2: テストビルド + 実行**

Run:
```bash
cd /home/k-yoshimi/program/task/tot/tests/c_abi
make clean && make run 2>&1 | tail -15
```
Expected: `test_abi: PASS (L-3 dispatcher verified)` 表示。

リンクエラー（per-module *_param_registry.o が無い）の場合:
- 該当モジュールの Phase L-3 が未完了 → tot 側 dispatcher 中の対応 USE をコメントアウトし、`dispatch_<x>` 関数を `ierr = 1; RETURN` に書き換え。テスト側もその prefix のケースをスキップ。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/tests/c_abi/Makefile
git commit -m "test(tot): wire L-3 deps into C ABI test build"
```

---

## Task 8: tot regression baseline 不変性を確認

**Files:** なし

- [ ] **Step 1: 通常 tot バイナリの動作確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。L-2 と数値完全一致（`tot_set_param` を呼ばない通常実行は影響を受けない）。

- [ ] **Step 2: 全モジュール回帰テスト**

Run:
```bash
./run_tests.sh
```
Expected: 全テスト FAIL ゼロ。

- [ ] **Step 3: コミット（L-3 完了マーカー）**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "test(tot): L-3 verification complete (baseline unchanged)"
```

---

## Verification (Phase L-3 完了基準)

- [ ] `tot/tot_param_registry.f90` が新規追加され、prefix dispatcher として機能。
- [ ] `tot_set_param("TR.RR", v)` 等が正しく per-module setter に dispatch される。
- [ ] `tot_set_param("EQ.RR", v)` 等の限定 EQ パラメータも動作。
- [ ] 未知 prefix (`ZZ.NONE`) や prefix なし (`RR`) は `ierr=1` を返す。
- [ ] C ABI テストで全 assertion PASS。
- [ ] tot regression baseline (L-0/L-1/L-2) と数値完全一致。

---

## Dependencies & Fallback

**前提:** L-2 完了 + 個別モジュールの Phase L-3 が「動作する `*_param_set` 関数を提供している」こと。

**産出物:** L-5 (Python ラッパ) で `tr.set_param("TR.RR", 6.2)` のような Pythonic な呼び出しが可能になる。L-7（パラメータ最適化）の基礎。

**Fallback:**
- per-module の `*_param_set` が完成していない場合 → 該当 dispatcher を `ierr = 1` に書き換え、L-3 段階では「TR と EQ だけサポート」のように段階的にロールアウト。
- EQ の `eq_set_geometry` で書き換えた変数が `eq_init` のキャッシュをクリアしない場合 → tot 側で `tot_set_param("EQ.*", ...)` 後に EQ 再計算を促すフラグを立てる仕組み（`tot_eq_dirty`）を tot_api 内に追加。L-3 では未対応。
- BIND(C) 文字列受け渡しの長さ問題 → name バッファ 64 文字を 128 文字に拡張する。
- `LEN_TRIM(name_f)` の境界条件不具合（NULL 終端だけの場合）→ `c_string_to_fortran` を堅牢化。

---

## Out of scope（次フェーズ送り）

- shared library `libtotapi.so` ビルド → L-4
- Python ラッパからの dict 一括セット → L-5
- EQ モジュールの完全 library 化 → 別 phase（EQ の F77 → F90 移行が前提）
- `tot_set_string_param` 文字列パラメータ → L-7 で必要なら追加
