# TOT Library Phase L-2: C ABI Foundation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tot 統合シミュレータの C ABI 5 関数（`tot_init / tot_run / tot_get_state / tot_set_param / tot_finalize`）の **stub** を Fortran/C ヘッダレベルで定義し、それぞれが対応する per-module API（trapi/tiapi/fpapi/wrapi/...）に**fan-out するスケルトン**を構築する。シンボル解決可能な状態にして、実体実装は L-3/L-4/L-5 で段階的に肉付けする。

**Architecture:** tot は単独の物理ソルバではなく **オーケストレータ** なので、`tot_api.f90` の各関数は per-module API を順次呼び出す。例: `tot_init()` は内部で `pl_init / eq_init / tr_init / ti_init / fp_init / dp_init / wr_init / wm_init` を呼ぶ。`tot_run()` は基本的に **TR がドライバ** として時間発展を進める想定（既存 `totmenu` の慣習踏襲）。`tot_state_t` は per-module state（`tr_state_t`, `ti_state_t`, `fp_state_t`, ...）を入れ子で持つ。L-2 のスコープでは「ヘッダと stub が揃い、`libtotapi.so` 相当のオブジェクトファイルがコンパイル成功する」ところまで。

**Tech Stack:** Fortran 90 (`ISO_C_BINDING`), C ヘッダ (`tot_api.h`), gfortran。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 3-4（C ABI シグネチャ）を tot に拡張。

**前提条件:** L-0 / L-1 完了。**個別モジュールの C ABI（`tr_api.f90`, `tr_api.h`, `ti_api.f90`, `fp_api.f90`, `wr_api.f90`, `wrx_api.f90`）が L-2 以前に各モジュールの Phase L-2 で完成している必要がある**。L-2 段階で個別 API が無い場合は「stub 内で個別 API を呼ぶ行を `! TODO` コメントにする」フォールバックを用意。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `tot/tot_state.f90` | 新規 | `tot_state_c` 型（C 互換 BIND(C)）。per-module state を入れ子で保持 |
| `tot/tot_api.f90` | 新規 | C ABI 5 関数の Fortran 側スタブ。`BIND(C, NAME=...)` 付き |
| `tot/tot_api.h` | 新規 | 上記 5 関数 + `tot_state_t` 構造体の C ヘッダ |
| `tot/Makefile` | 修正 | 新規 `totapi-stubs` ターゲットを追加（デフォルトの `tot` ターゲットには含めない）。`ifeq ($(TR_API_READY),1)` で TR-L-2 完了時のみ stub をコンパイルする条件化も併用 |
| `tot/tests/c_abi/test_abi.c` | 新規 | C から `tot_init/tot_finalize` を呼んで戻り値を検査する最小ユニットテスト |
| `tot/tests/c_abi/Makefile` | 新規 | テストビルド（`gcc test_abi.c -o test_abi -L../.. -ltotapi`） |

**方針:**
- L-2 の段階では `tot_run` は単に `tr_run` を呼ぶだけの最小実装。WR/FP/TI 連動は L-3/L-6 で実装。
- `tot_get_state` も TR の state だけ埋めて、TI/FP は presence flag のみ（L-0 の dump 方針と整合）。
- `tot_set_param` は **L-2 では常に `ierr=1`（unimplemented）**を返す stub。本実装は L-3。
- 物理的に意味のある呼び出しは L-6 のテストで初めて検証する。L-2 はあくまで **シンボル/型/リンクの土台**。
- **依存分離:** `tot_state.f90` / `tot_api.f90` は TR Phase L-2 (`tr_state`, `tr_api`) に強く依存する。これらをデフォルト `tot` ターゲットの `SRCS` に含めると **TR-L-2 が未完成のとき既存 `tot` バイナリのビルドが壊れる**。これを避けるため:
  - L-2 では別ターゲット `totapi-stubs` を新設し、デフォルト `make tot` には含めない（`make totapi-stubs` で明示的にビルド）。
  - 加えて `ifeq ($(TR_API_READY),1)` ガードを置き、TR-L-2 完了が確認できた段階で初めて自動ビルドに昇格できるようにする（TR-L-2 完了時に `make TR_API_READY=1 totapi-stubs` を呼べる）。

---

## Task 1: 作業用ブランチ作成と前提条件チェック

**Files:** なし

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop && git pull
git checkout -b feature/tot-library-l2-c-abi-foundation
```

- [ ] **Step 2: per-module API の有無を確認**

Run:
```bash
ls /home/k-yoshimi/program/task/tr/tr_api.f90 \
   /home/k-yoshimi/program/task/tr/tr_api.h \
   /home/k-yoshimi/program/task/ti/ti_api.f90 \
   /home/k-yoshimi/program/task/fp/fp_api.f90 \
   /home/k-yoshimi/program/task/wr/wr_api.f90 \
   /home/k-yoshimi/program/task/wrx/wrx_api.f90 \
   2>&1 | head -10
```
Expected: 全て存在する場合は本格 fan-out 実装可能。一部欠けていれば、その関数呼び出しは `! TODO L-? requires <module>_api` コメントで stub のみ書く。

- [ ] **Step 3: L-0 と L-1 の baseline テストが PASS**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。

- [ ] **Step 4: 初期コミット**

Run:
```bash
git commit --allow-empty -m "chore(tot): start L-2 C ABI foundation"
```

---

## Task 2: `tot/tot_state.f90` を新規作成

**Files:**
- Create: `tot/tot_state.f90`

**目的:** Python/C から見たときの「tot 全体の state」を 1 つの BIND(C) 構造体として定義。per-module state は入れ子で持つ。

- [ ] **Step 1: 新規作成**

作成: `tot/tot_state.f90`

```fortran
! tot_state.f90
!
! C-compatible state container for the integrated tot simulator.
! Composed of per-module sub-states (TR, TI, FP, WR) plus a presence
! bitmap so callers can detect which modules have been initialized.
!
! Schema is intentionally fixed-size (matches per-module *_state_c types)
! to keep the C ABI simple. Upper bounds follow the per-module specs.

MODULE tot_state
  USE, INTRINSIC :: ISO_C_BINDING
  ! Per-module C-state types are USE-imported from each module's *_api.
  ! If any per-module API is not yet available, comment out the USE
  ! and replace the corresponding component with a placeholder INTEGER.
  USE tr_state, ONLY: tr_state_c
  ! USE ti_state, ONLY: ti_state_c   ! enable when ti_api is ready
  ! USE fp_state, ONLY: fp_state_c   ! enable when fp_api is ready
  ! USE wr_state, ONLY: wr_state_c   ! enable when wr_api is ready
  IMPLICIT NONE
  PUBLIC

  TYPE, BIND(C) :: tot_state_c
     INTEGER(C_INT) :: tr_present
     INTEGER(C_INT) :: ti_present
     INTEGER(C_INT) :: fp_present
     INTEGER(C_INT) :: wr_present
     ! Per-module sub-states. tr_state_c is currently the only one.
     ! Placeholders for the others until their *_api.f90 is built.
     TYPE(tr_state_c) :: tr
     INTEGER(C_INT)   :: ti_placeholder   ! replaced by TYPE(ti_state_c) at L-3 if ready
     INTEGER(C_INT)   :: fp_placeholder
     INTEGER(C_INT)   :: wr_placeholder
  END TYPE tot_state_c

END MODULE tot_state
```

注: `tr_state_c` がまだ無い段階では、`tr_state` の USE をコメントアウトし `tr_state_c` を `INTEGER(C_INT) :: tr_placeholder` に差し替える。

- [ ] **Step 2: ビルドテスト（このファイル単体だけコンパイル）**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make tot_state.o 2>&1 | tail -10
```

`tot_state.o` が必要なら Makefile 修正は Task 4。ここでは構文確認だけ。`tr_state` モジュールの解決に問題があれば `MODINCLUDE` の `-I../tr/$(MOD)` を確認（既存 Makefile に含まれているはず）。

- [ ] **Step 3: コミット**

Run:
```bash
git add tot/tot_state.f90
git commit -m "feat(tot): add tot_state.f90 (C-compatible composite state)"
```

---

## Task 3: `tot/tot_api.f90` を新規作成（5 関数の stub）

**Files:**
- Create: `tot/tot_api.f90`

- [ ] **Step 1: 新規作成**

作成: `tot/tot_api.f90`

```fortran
! tot_api.f90
!
! C ABI for the integrated tot simulator. Fans out to per-module APIs.
!
! API:
!   tot_init()              - call pl/eq/tr/ti/fp/dp/wr/wm init in order
!   tot_run(ntmax)          - advance the integrated system NTMAX TR steps
!                             (TR drives time; per-step coupling done in L-6)
!   tot_get_state(state)    - copy current state into tot_state_c
!   tot_set_param(name, v)  - dispatch to per-module param setters (L-3)
!   tot_finalize()          - finalize all initialized modules
!
! Error codes: 0=OK, 1=invalid param, 2=not initialized, 3=calc failed.

MODULE tot_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE tot_state, ONLY: tot_state_c
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tot_init, tot_run, tot_get_state, tot_set_param, tot_finalize

  ! Module-local lifecycle bookkeeping.
  LOGICAL, SAVE :: initialized = .FALSE.

CONTAINS

  !-------------------------------------------------------------------
  FUNCTION tot_init() RESULT(ierr) BIND(C, NAME="tot_init")
    USE plinit,   ONLY: pl_init
    USE equnit,   ONLY: eq_init
    USE trcomm,   ONLY: open_trcomm
    USE trinit,   ONLY: tr_init
    USE ticomm,   ONLY: open_ticomm_parm
    USE tiinit,   ONLY: ti_init
    ! NOTE: tot/totmain.f90:24 USEs `fpcomm_parm` (not `fpcomm`) and the
    ! corresponding `CALL open_fpcomm_parm` is commented out (totmain.f90:38
    ! reads `!  CALL open_fpcomm_parm`). Mirror that here: do NOT USE the
    ! `fpcomm` module just for this symbol, and do NOT issue the call.
    USE fpinit,   ONLY: fp_init
    USE dpinit,   ONLY: dp_init
    USE wrcomm,   ONLY: open_wrcomm_parm
    USE wrinit,   ONLY: wr_init
    USE wminit,   ONLY: wm_init
    INTEGER(C_INT) :: ierr

    ierr = 0
    IF (initialized) THEN
       ierr = 0          ! idempotent: re-init is a no-op
       RETURN
    END IF

    ! Open module-private comm areas (matches totmain.f90 sequence).
    ! Note: `open_fpcomm_parm` is intentionally NOT called — totmain.f90:38
    ! has it commented out (`!  CALL open_fpcomm_parm`), and we keep the
    ! C ABI behaviorally identical to the menu-driven binary at L-2.
    CALL open_trcomm
    CALL open_ticomm_parm
!   CALL open_fpcomm_parm   ! disabled to match totmain.f90:38
    CALL open_wrcomm_parm

    ! Per-module init in the order used by totmain.f90.
    CALL pl_init
    CALL eq_init
    CALL tr_init
    CALL dp_init
    CALL wr_init
    CALL wm_init
    CALL fp_init
    CALL ti_init

    initialized = .TRUE.
  END FUNCTION tot_init

  !-------------------------------------------------------------------
  FUNCTION tot_run(ntmax) RESULT(ierr) BIND(C, NAME="tot_run")
    ! L-2 stub: drive only TR. Per-module coupling (TR<->FP, TR<->WR)
    ! is wired in L-6 once the test scaffolding can detect drift.
    USE tr_api, ONLY: tr_run   ! requires tr Phase L-2 complete
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax
    INTEGER(C_INT) :: ierr

    ierr = 0
    IF (.NOT. initialized) THEN
       ierr = 2; RETURN
    END IF
    IF (ntmax < 0) THEN
       ierr = 1; RETURN
    END IF
    ierr = tr_run(ntmax)
  END FUNCTION tot_run

  !-------------------------------------------------------------------
  FUNCTION tot_get_state(state) RESULT(ierr) BIND(C, NAME="tot_get_state")
    USE tr_api, ONLY: tr_get_state
    TYPE(tot_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER(C_INT) :: tr_ierr

    ierr = 0
    IF (.NOT. initialized) THEN
       ierr = 2; RETURN
    END IF

    ! Always populate per-module presence flags first.
    state%tr_present = 1   ! tr_init is always called by tot_init
    state%ti_present = 1
    state%fp_present = 1
    state%wr_present = 1
    state%ti_placeholder = 0
    state%fp_placeholder = 0
    state%wr_placeholder = 0

    tr_ierr = tr_get_state(state%tr)
    IF (tr_ierr /= 0) ierr = tr_ierr
  END FUNCTION tot_get_state

  !-------------------------------------------------------------------
  FUNCTION tot_set_param(name, value) RESULT(ierr) BIND(C, NAME="tot_set_param")
    ! L-2 stub: dispatch table is implemented in L-3 (tot_param_registry).
    ! Always returns "invalid param" until L-3 lands.
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    INTEGER :: dummy_len

    dummy_len = 0   ! suppress unused-arg warning
    IF (value == 0.0_C_DOUBLE) dummy_len = 0
    ierr = 1
  END FUNCTION tot_set_param

  !-------------------------------------------------------------------
  FUNCTION tot_finalize() RESULT(ierr) BIND(C, NAME="tot_finalize")
    USE tr_api, ONLY: tr_finalize
    INTEGER(C_INT) :: ierr
    INTEGER(C_INT) :: tr_ierr

    ierr = 0
    IF (.NOT. initialized) THEN
       ierr = 0; RETURN     ! idempotent
    END IF
    tr_ierr = tr_finalize()
    IF (tr_ierr /= 0) ierr = tr_ierr
    initialized = .FALSE.
  END FUNCTION tot_finalize

END MODULE tot_api
```

**注:** per-module API (`tr_api`, etc.) が無い場合の対応:
- `tr_api` USE 行をコメントアウト → `tot_run`/`tot_get_state`/`tot_finalize` 内の TR 呼び出しを `! TODO requires tr_api` のコメントに置換し、`ierr = 0` 直返しにする。

- [ ] **Step 2: 単体コンパイル**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make tot_state.o tot_api.o 2>&1 | tail -15
```
Expected: 両方コンパイル成功。`tr_api` mod が見つからないエラーが出る場合は Step 1 のフォールバックに従う。

- [ ] **Step 3: コミット**

Run:
```bash
git add tot/tot_api.f90
git commit -m "feat(tot): add tot_api.f90 (C ABI 5-function stub)"
```

---

## Task 4: `tot/Makefile` に独立 stub ターゲットを追加

**Files:**
- Modify: `tot/Makefile`

**重要:** `tot_state.f90` は `USE tr_state` で TR Phase L-2 (`tr/tr_state.f90`) に hard depend する。これをデフォルトの `tot` ターゲットの `SRCS` に入れると、TR-L-2 が未完成な develop で `make tot` が壊れる。L-2 では **「明示的に呼んだときだけビルドされる stub ターゲット」** として独立化する。

- [ ] **Step 1: stub 専用ターゲットを追加（デフォルト `tot` には含めない）**

`tot/Makefile` の SRCS ブロックを以下に修正:

変更前（L-1 で入れたコメント込み）:
```makefile
SRCS_CORE = totregress.f90
SRCS_MENU = totmenu.f90
SRCS      = $(SRCS_CORE) $(SRCS_MENU)
```

変更後:
```makefile
SRCS_CORE = totregress.f90
SRCS_MENU = totmenu.f90
# SRCS_API は tot_state/tot_api で構成され、TR Phase L-2 (tr_state, tr_api) に
# 強く依存する。SRCS には入れず、専用 `totapi-stubs` ターゲットでだけビルドする。
SRCS_API  = tot_state.f90 tot_api.f90
SRCS      = $(SRCS_CORE) $(SRCS_MENU)
OBJS_API  = $(SRCS_API:.f90=.o)

# Conditional auto-include: when TR Phase L-2 is complete, callers can pass
# TR_API_READY=1 to fold the API objects into the default tot build.
ifeq ($(TR_API_READY),1)
SRCS += $(SRCS_API)
endif

# Standalone stub-build entry point (always available; manual invocation).
# Use:  make totapi-stubs
.PHONY: totapi-stubs
totapi-stubs: $(OBJS_API)
```

- [ ] **Step 2: 既存 `tot` バイナリビルドが壊れないことを確認（stub 抜きビルド）**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make clean && make tot 2>&1 | tail -10
ls -la tot
```
Expected: `tot` バイナリ生成成功。`tot_state.o`/`tot_api.o` は **コンパイルされない**（依然 TR-L-2 が無い develop でも壊れないことを保証）。`tot` バイナリ動作は L-1 から不変。

- [ ] **Step 2b: TR-L-2 が完了している場合のみ stub をビルドする**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
ls /home/k-yoshimi/program/task/tr/tr_state.f90 /home/k-yoshimi/program/task/tr/tr_api.f90 2>&1 | head -5
# 上記が両方存在すれば stub ビルド可能:
make totapi-stubs 2>&1 | tail -10
ls -la tot_state.o tot_api.o 2>&1 | head
```
Expected: `tr_state.o` がリンク可能なら `tot_state.o`/`tot_api.o` が生成される。未完成ならスキップ（L-2 完了基準は「`make totapi-stubs` が TR-L-2 ありで成功する」）。

- [ ] **Step 3: 既存テストが PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。L-1 と数値完全一致。

- [ ] **Step 4: コミット**

Run:
```bash
git add tot/Makefile
git commit -m "build(tot): add SRCS_API objects to default build"
```

---

## Task 5: `tot/tot_api.h` を作成

**Files:**
- Create: `tot/tot_api.h`

- [ ] **Step 1: 新規作成**

作成: `tot/tot_api.h`

```c
/*
 * tot_api.h — C ABI for the integrated tot simulator.
 *
 * Lifecycle:
 *   tot_init()             - initialize all per-module states
 *   tot_run(ntmax)         - advance ntmax TR steps (drives integrated system)
 *   tot_get_state(state*)  - snapshot current integrated state
 *   tot_set_param(name, v) - set parameter (L-3 implementation)
 *   tot_finalize()         - finalize all per-module states
 *
 * Error codes:
 *   0 = success
 *   1 = invalid parameter / invalid argument
 *   2 = not initialized
 *   3 = calculation failed (per-module error propagated)
 */

#ifndef TOT_API_H
#define TOT_API_H

#include "tr_api.h"
/* #include "ti_api.h"  -- enable when ti_api is ready */
/* #include "fp_api.h" */
/* #include "wr_api.h" */

typedef struct {
    int tr_present;
    int ti_present;
    int fp_present;
    int wr_present;
    tr_state_t tr;
    int ti_placeholder;   /* replaced by ti_state_t when ti_api lands */
    int fp_placeholder;
    int wr_placeholder;
} tot_state_t;

int tot_init(void);
int tot_run(int ntmax);
int tot_get_state(tot_state_t* state);
int tot_set_param(const char* name, double value);
int tot_finalize(void);

#endif  /* TOT_API_H */
```

- [ ] **Step 2: ヘッダの構文確認（C コンパイラで preprocessor を回す）**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
gcc -E -I. -I../tr tot_api.h 2>&1 | tail -20
```
Expected: 構文エラー無し。tr_api.h が見つからない場合はパスを調整。

- [ ] **Step 3: コミット**

Run:
```bash
git add tot/tot_api.h
git commit -m "feat(tot): add tot_api.h C header"
```

---

## Task 6: 最小 C ABI ユニットテスト追加

**Files:**
- Create: `tot/tests/c_abi/test_abi.c`
- Create: `tot/tests/c_abi/Makefile`

**目的:** L-2 段階では `libtotapi.so` がまだないので、Fortran object 群を直接アーカイブ化してリンクする最小テストを書く。

- [ ] **Step 1: テスト本体を新規作成**

作成: `tot/tests/c_abi/test_abi.c`

```c
/*
 * test_abi.c — minimal smoke test for tot C ABI symbols.
 *
 * At Phase L-2 the runtime behavior of tot_init/tot_finalize depends on
 * many side effects (MPI init, file opens) we don't want to drag into a
 * unit test. We therefore only verify symbol resolution and that the
 * trivial stubs return their documented codes.
 */
#include <stdio.h>
#include <assert.h>
#include "tot_api.h"

int main(void) {
    /* tot_set_param is a stub at L-2: must return 1 (invalid param). */
    int rc = tot_set_param("ANY", 0.0);
    assert(rc == 1 && "tot_set_param L-2 stub must return 1");

    /* Finalize when uninitialized: idempotent (returns 0). */
    rc = tot_finalize();
    assert(rc == 0 && "tot_finalize on uninitialized state must be 0");

    printf("test_abi: PASS (L-2 symbol resolution + stub behavior)\n");
    return 0;
}
```

- [ ] **Step 2: テスト用 Makefile を新規作成**

作成: `tot/tests/c_abi/Makefile`

```makefile
# Minimal C ABI smoke test for tot Phase L-2.
#
# Links the tot_api object directly (no shared library yet).
# libtotapi.so build is in L-4.

TOT_DIR = ../..
TR_DIR  = ../../../tr

CC      = gcc
FC      = gfortran
CFLAGS  = -O0 -g -I$(TOT_DIR) -I$(TR_DIR)
LDFLAGS = -L$(TOT_DIR) -L$(TR_DIR)

OBJS = $(TOT_DIR)/tot_state.o $(TOT_DIR)/tot_api.o

# Per-module objects used by tot_api stubs. Adjust as more *_api modules land.
DEPS = $(TR_DIR)/tr_state.o $(TR_DIR)/tr_api.o $(TR_DIR)/libtr2.a

test_abi: test_abi.c $(OBJS)
	$(CC) $(CFLAGS) test_abi.c $(OBJS) $(DEPS) -lgfortran -lm -o $@

run: test_abi
	./test_abi

clean:
	rm -f test_abi *.o
```

- [ ] **Step 3: テストをビルド実行**

Run:
```bash
cd /home/k-yoshimi/program/task/tot/tests/c_abi
make run 2>&1 | tail -10
```
Expected: `test_abi: PASS (L-2 symbol resolution + stub behavior)` が表示される。

リンクエラー（undefined reference to `tr_run`等）が出る場合:
- per-module API が未完成 → `tot_api.f90` の対応 USE をコメントアウトして再ビルド
- libtr2.a への依存が足りない → `DEPS` に他の `.a` を追加（`libpl.a`, `libeq.a` など）

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/tests/c_abi/
git commit -m "test(tot): add minimal C ABI smoke test"
```

---

## Task 7: 既存 tot バイナリと tot regression テストの不変性を最終確認

**Files:** なし

- [ ] **Step 1: 通常ビルド + 全 tot テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/tot && make clean && make tot 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。L-0/L-1 baseline と数値完全一致。

- [ ] **Step 2: 全モジュール回帰テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: tot 系含む全テスト FAIL ゼロ。

- [ ] **Step 3: 最終コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "test(tot): L-2 verification complete (baseline unchanged)"
```

---

## Verification (Phase L-2 完了基準)

- [ ] `tot/tot_state.f90`, `tot/tot_api.f90`, `tot/tot_api.h` が新規追加されている。
- [ ] `tot/Makefile` に `totapi-stubs` ターゲットが追加され、`make totapi-stubs` で `tot_state.o`, `tot_api.o` が生成される（**デフォルト `make tot` には含まれない**）。
- [ ] デフォルトの `make tot` が TR-L-2 未完成な develop でも引き続き成功する（L-2 stub の追加で既存ビルドが壊れていないこと）。
- [ ] `tot/tests/c_abi/test_abi` が PASS する（C から `tot_set_param`/`tot_finalize` のシンボルが解決され、stub 戻り値も期待通り）。
- [ ] 通常 `tot` バイナリの動作と tot regression テストが L-0/L-1 と数値完全一致。
- [ ] per-module API が利用可能な範囲で `tot_init`/`tot_run`/`tot_get_state`/`tot_finalize` が fan-out している（未利用な部分は明示的に TODO コメント）。

---

## Dependencies & Fallback

**前提:**
- L-0 / L-1 完了。
- 個別モジュール (`tr`, `ti`, `fp`, `wr`, `wrx`) の Phase L-2（C ABI foundation）が完成していると **fan-out が完全**になる。一部未完成でも stub のまま L-2 を完了できる。

**産出物:** L-3 (param registry)、L-4 (`libtotapi.so` ビルド)、L-5 (Python ラッパ) に必要な型・関数シグネチャ・C ヘッダが整う。

**Fallback:**
- per-module C ABI が未完成な場合 → 該当モジュールへの fan-out 行を `! TODO L-? requires <module>_api` でコメント化、`ierr = 0` を返す stub に置換。test_abi は引き続き PASS する。
- `tr_state_c` 構造体サイズが per-モジュール側で大きすぎて C 側でメモリ確保エラー → `tot_state_c` を pointer ベースの API（`tot_get_state(int* tr_present, tr_state_t** tr_out)` 等）に切り替えるリファクタを L-4 で検討。
- BIND(C) シンボル名が他ライブラリと衝突 → `BIND(C, NAME="task_tot_init")` のように prefix を加える（その場合は `tot_api.h` も同期）。

---

## Out of scope（次フェーズ送り）

- 実際の param 設定動作（`tot_set_param` の dispatch table） → L-3
- shared library `libtotapi.so` のビルド → L-4
- Python ラッパからの呼び出し検証 → L-5
- per-step 結合計算（TR<->FP<->WR の coupling） → L-6
