# Phase L-2: C ABI Foundation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** C ABI 5 関数 (`tr_init`, `tr_run`, `tr_set_param`, `tr_get_state`, `tr_finalize`) のスケルトンと、tr_state 構造体（Fortran 側 / C 側）を新設する。中身は最小実装：`tr_init/tr_finalize` だけは実際に既存 ALLOCATE_TRCOMM/DEALLOCATE_TRCOMM を呼んで動かし、他は固定値（`ierr=0`）を返すスタブとする。**`tr2` バイナリの構成・数値結果は変えない。**

**Architecture:** 設計書 §3 のモジュール責務分離に従い、3 つの新規 Fortran モジュール (`tr_state.f90`, `tr_param_registry.f90`, `tr_api.f90`) と 1 つの C ヘッダ (`tr_api.h`) を `tr/` 直下に追加する。Phase L-1 の `SRCS_CORE` には含めず、新たに `SRCS_API` make 変数として独立に管理し、`tr2` ターゲットからは外す（`tr2` は graphics + menu を含むまま、API オブジェクトはまだリンクしない）。

**Tech Stack:** Fortran 2003 `ISO_C_BINDING`, gfortran, GNU Make, 既存 TRCOMM とその ALLOCATE/DEALLOCATE ルーチン。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §3 (アーキテクチャ図), §4 (C ABI シグネチャ), §9 (L-2 行)。

---

## File Structure

このサブフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `tr/tr_state.f90` | 新規 | `tr_state_c` 派生型（C 互換、固定サイズ配列）。中身は ZEROS。 |
| `tr/tr_param_registry.f90` | 新規 | `tr_param_set` 関数の **空シェル**（常に ierr=1=invalid を返す）。L-3 で本実装。 |
| `tr/tr_api.f90` | 新規 | `bind(c)` 5 関数。init/finalize は既存ルーチン呼び出し、他はスタブ。 |
| `tr/tr_api.h` | 新規 | C ヘッダ（設計書 §4.2 をそのまま貼る） |
| `tr/Makefile` | 修正 | `SRCS_API` を新設、コンパイル対象に追加（リンクはまだ tr2 に組み込まない） |
| `tr/tests/c_abi/test_smoke.c` | 新規 | C から `tr_init`/`tr_finalize` を 1 サイクル呼ぶ最小スモーク |
| `tr/tests/c_abi/Makefile` | 新規 | C スモークのビルド・実行ルール（libtrapi 依存しない、直接 .o リンク） |

**方針:**
- 新規 3 Fortran ファイルは「**増やすだけ**」「**既存ファイルを書き換えない**」が大原則。
- `tr_api.f90` の `tr_init` 実装は、既存 `trinit.f90` の中で呼ばれている初期化サブルーチン群（例: `ALLOCATE_TRCOMM`、`tr_init` ラッパ）をそのまま `CALL` する。新しい初期化フローを書かない。
- `tr_run` は L-2 では「`ntmax` を受け取って `ierr=0` を返すだけ」のスタブ。実装本体は L-3 後半か L-4 で導入。
- C スモークテストは「init→finalize で SIGSEGV しない」だけを確認する。**数値の正しさは Layer 1 (L-6) でやる。**

---

## Task 1: ブランチ作成と前提確認

**Files:**
- なし

- [ ] **Step 1: L-1 完了済みを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | grep -i "phase l-1\|tr-library-phase-l1" | head -3
grep -n "^SRCS_CORE\|^SRCS_GRAPHICS\|^SRCS_MENU" tr/Makefile
```
Expected: L-1 merge commit が見える、Makefile に 3 グループの SRCS が定義済み。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/tr-library-phase-l2 origin/develop
```

- [ ] **Step 3: 既存の TRCOMM init/finalize 入口を特定**

Run:
```bash
grep -rn "ALLOCATE_TRCOMM\|DEALLOCATE_TRCOMM\|SUBROUTINE.*tr_init\b" tr/ | head -20
```
Expected: `trcomm.f90` または `trinit.f90` に `ALLOCATE_TRCOMM` の SUBROUTINE 定義、`trinit.f90` に `tr_init`（既存）が存在することを確認。`tr_api.f90` ではこれらを `USE`/`CALL` する。

注意: 既存に `tr_init` という名前のサブルーチンがある場合は、新 API 関数名と衝突する。`bind(c, name="tr_init")` の C 側名前は維持し、Fortran 側関数名は `tr_init_c` 等に改名して衝突を避ける（Step 後段で確認）。

---

## Task 2: `tr_state.f90` を新規作成

**Files:**
- Create: `tr/tr_state.f90`

- [ ] **Step 1: ファイル作成**

作成: `tr/tr_state.f90`

```fortran
! tr_state.f90
!
! C-interoperable state struct for the TR library API.
! Mirrors tr_api.h::tr_state_t exactly. Fixed-size arrays per §4.2 of
! docs/superpowers/specs/2026-04-17-tr-library-design.md.
!
! Phase L-2: definition only. Population happens in tr_api::tr_get_state (L-3+).

MODULE tr_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_state_c, TR_MAX_NRMAX, TR_MAX_NSMAX

  INTEGER(C_INT), PARAMETER :: TR_MAX_NRMAX = 500
  INTEGER(C_INT), PARAMETER :: TR_MAX_NSMAX = 8

  TYPE, BIND(C) :: tr_state_c
     INTEGER(C_INT)  :: nt
     INTEGER(C_INT)  :: nrmax
     INTEGER(C_INT)  :: nsmax
     REAL(C_DOUBLE)  :: T
     REAL(C_DOUBLE)  :: WPT
     REAL(C_DOUBLE)  :: AJT
     REAL(C_DOUBLE)  :: Q0
     REAL(C_DOUBLE)  :: BETA0
     REAL(C_DOUBLE)  :: BETAP0
     REAL(C_DOUBLE)  :: BETAA
     REAL(C_DOUBLE)  :: BETAN
     REAL(C_DOUBLE)  :: TAUE1
     REAL(C_DOUBLE)  :: TAUE2
     REAL(C_DOUBLE)  :: ZEFF0
     REAL(C_DOUBLE)  :: ALI
     REAL(C_DOUBLE)  :: RQ1
     REAL(C_DOUBLE)  :: RN(TR_MAX_NSMAX, TR_MAX_NRMAX)
     REAL(C_DOUBLE)  :: RT(TR_MAX_NSMAX, TR_MAX_NRMAX)
     REAL(C_DOUBLE)  :: AJ(TR_MAX_NRMAX)
     REAL(C_DOUBLE)  :: QP(TR_MAX_NRMAX)
  END TYPE tr_state_c
END MODULE tr_state
```

注: C 側は `RN[NRMAX][NSMAX]` 行優先、Fortran 側は `RN(NSMAX, NRMAX)` 列優先で**メモリレイアウトが一致**する（§4.2 のコメントの通り）。L-6 Layer 1 で順序を実走確認する。

---

## Task 3: `tr_param_registry.f90` を空シェルとして作成

**Files:**
- Create: `tr/tr_param_registry.f90`

- [ ] **Step 1: ファイル作成（中身は L-3 で実装）**

作成: `tr/tr_param_registry.f90`

```fortran
! tr_param_registry.f90
!
! Phase L-2: empty shell. Returns ierr=1 (invalid name) for any input.
! Phase L-3 fills in the SELECT CASE table for namelist parameters.

MODULE tr_param_registry
  USE trcomm, ONLY: rkind
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_param_set

CONTAINS

  FUNCTION tr_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),      INTENT(IN) :: value
    INTEGER :: ierr
    ! Phase L-2 stub. L-3 will implement SELECT CASE on namelist names.
    ierr = 1   ! invalid parameter name (always)
    ! prevent unused-argument warnings
    IF (LEN_TRIM(name) < 0) ierr = 1
    IF (value /= value)     ierr = 1
  END FUNCTION tr_param_set

END MODULE tr_param_registry
```

注: `USE trcomm, ONLY: rkind` だけで十分（実装は L-3）。

---

## Task 4: `tr_api.f90` を作成（bind(c) 5 関数のスタブ）

**Files:**
- Create: `tr/tr_api.f90`

- [ ] **Step 1: ファイル作成**

作成: `tr/tr_api.f90`

```fortran
! tr_api.f90
!
! C ABI entry points for libtrapi.so.
! Phase L-2 minimal scaffolding:
!   - tr_init / tr_finalize : delegate to existing TRCOMM ALLOCATE/DEALLOCATE.
!   - tr_run / tr_get_state / tr_set_param : stubs returning ierr=0
!     (or via the empty registry). Real bodies arrive in L-3 / L-4.
!
! See docs/superpowers/specs/2026-04-17-tr-library-design.md §4.

MODULE tr_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE tr_state,           ONLY: tr_state_c
  USE tr_param_registry,  ONLY: tr_param_set
  USE trcomm,             ONLY: ALLOCATE_TRCOMM, DEALLOCATE_TRCOMM
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: tr_api_init, tr_api_run, tr_api_get_state, &
            tr_api_set_param, tr_api_finalize

  LOGICAL, SAVE :: g_initialized = .FALSE.

CONTAINS

  FUNCTION tr_api_init() RESULT(ierr) BIND(C, NAME="tr_init")
    INTEGER(C_INT) :: ierr
    INTEGER :: stat
    IF (g_initialized) THEN
       ierr = 0
       RETURN
    END IF
    CALL ALLOCATE_TRCOMM(stat)
    IF (stat /= 0) THEN
       ierr = 3   ! calculation/initialization failed
       RETURN
    END IF
    g_initialized = .TRUE.
    ierr = 0
  END FUNCTION tr_api_init

  FUNCTION tr_api_run(ntmax) RESULT(ierr) BIND(C, NAME="tr_run")
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax
    INTEGER(C_INT) :: ierr
    IF (.NOT. g_initialized) THEN
       ierr = 2   ! not initialized
       RETURN
    END IF
    ! L-2 stub: do nothing. L-4 will call tr_loop with NTMAX overridden.
    IF (ntmax < 0) THEN
       ierr = 1
    ELSE
       ierr = 0
    END IF
  END FUNCTION tr_api_run

  FUNCTION tr_api_get_state(state) RESULT(ierr) BIND(C, NAME="tr_get_state")
    TYPE(tr_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF
    ! L-2 stub: zero out the struct. L-3 will populate from TRCOMM.
    state%nt    = 0
    state%nrmax = 0
    state%nsmax = 0
    state%T     = 0.0_C_DOUBLE
    state%WPT   = 0.0_C_DOUBLE
    state%AJT   = 0.0_C_DOUBLE
    state%Q0    = 0.0_C_DOUBLE
    state%BETA0 = 0.0_C_DOUBLE
    state%BETAP0= 0.0_C_DOUBLE
    state%BETAA = 0.0_C_DOUBLE
    state%BETAN = 0.0_C_DOUBLE
    state%TAUE1 = 0.0_C_DOUBLE
    state%TAUE2 = 0.0_C_DOUBLE
    state%ZEFF0 = 0.0_C_DOUBLE
    state%ALI   = 0.0_C_DOUBLE
    state%RQ1   = 0.0_C_DOUBLE
    state%RN    = 0.0_C_DOUBLE
    state%RT    = 0.0_C_DOUBLE
    state%AJ    = 0.0_C_DOUBLE
    state%QP    = 0.0_C_DOUBLE
    ierr = 0
  END FUNCTION tr_api_get_state

  FUNCTION tr_api_set_param(name, value) RESULT(ierr) BIND(C, NAME="tr_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: fname
    INTEGER :: i
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF
    ! Convert NUL-terminated C string to Fortran string.
    fname = ' '
    DO i = 1, 64
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
    END DO
    ierr = tr_param_set(TRIM(fname), value)
  END FUNCTION tr_api_set_param

  FUNCTION tr_api_finalize() RESULT(ierr) BIND(C, NAME="tr_finalize")
    INTEGER(C_INT) :: ierr
    IF (.NOT. g_initialized) THEN
       ierr = 0
       RETURN
    END IF
    CALL DEALLOCATE_TRCOMM()
    g_initialized = .FALSE.
    ierr = 0
  END FUNCTION tr_api_finalize

END MODULE tr_api
```

注:
- 関数の Fortran 名は `tr_api_*`、C 側公開名は `bind(c, name="tr_*")` で固定（既存 `tr_init` サブルーチンとの名前衝突回避）。
- `ALLOCATE_TRCOMM` の引数シグネチャは Phase 0 修正後のもの（`stat` 引数を持つ）を仮定。シグネチャが異なる場合は L-2 の Step 1 で確認し、適合させる。

---

## Task 5: `tr_api.h` を作成

**Files:**
- Create: `tr/tr_api.h`

- [ ] **Step 1: 設計書 §4.2 のヘッダをそのまま貼る**

作成: `tr/tr_api.h`

```c
#ifndef TR_API_H
#define TR_API_H

#ifdef __cplusplus
extern "C" {
#endif

/* See docs/superpowers/specs/2026-04-17-tr-library-design.md §4.2.
 * Memory note: in C, RN[NRMAX][NSMAX] is row-major; in Fortran the
 * matching declaration is RN(NSMAX, NRMAX) (column-major). Layouts
 * agree, but only RN[0..nrmax-1][0..nsmax-1] are valid runtime values. */
#define TR_MAX_NRMAX 500
#define TR_MAX_NSMAX 8

typedef struct {
    int nt, nrmax, nsmax;
    double T, WPT, AJT, Q0, BETA0, BETAP0, BETAA, BETAN;
    double TAUE1, TAUE2, ZEFF0, ALI, RQ1;
    double RN[TR_MAX_NRMAX][TR_MAX_NSMAX];
    double RT[TR_MAX_NRMAX][TR_MAX_NSMAX];
    double AJ[TR_MAX_NRMAX];
    double QP[TR_MAX_NRMAX];
} tr_state_t;

int tr_init(void);
int tr_run(int ntmax);
int tr_set_param(const char* name, double value);
int tr_get_state(tr_state_t* state);
int tr_finalize(void);

#ifdef __cplusplus
}
#endif

#endif /* TR_API_H */
```

---

## Task 6: Makefile に SRCS_API を追加

**Files:**
- Modify: `tr/Makefile`

- [ ] **Step 1: SRCS_API 定義と OBJ_API 派生変数を追加**

`tr/Makefile` の `SRCS_MENU=trmenu.f90` の **直後** に以下を追加:

```makefile
# C ABI sources (Phase L-2+). Compiled but not linked into tr2.
# Linked into libtrapi.so by Phase L-4.
SRCS_API=tr_state.f90 tr_param_registry.f90 tr_api.f90
```

そして `OBJS=$(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))` の **直後** に:

```makefile
OBJ_API=$(addprefix $(OBJDIR)/, $(SRCS_API:.f90=.o))
```

注（review #9 反映）: `tr/Makefile` の **`SRCM=trcom0.f90 trcom1.f90 trcomm.f90 trbpsd.f90`** （4 ファイル）は L-2 では一切触らない。これらは TRCOMM 中核モジュール群で `tr_api` モジュールが `USE trcomm` 経由で参照する。新設の `SRCS_API` も `SRCM` には混ぜない（モジュール責務分離のため、API モジュールは独立変数で管理）。

**`tr/trbpsd-mod.f90` について:** リポジトリには `tr/trbpsd.f90`（`SRCM` に含まれる）と `tr/trbpsd-mod.f90`（`SRCM` 等いずれの make 変数にも含まれない）が併存する。確認:
```bash
grep "^SRCM=" tr/Makefile
ls tr/trbpsd*.f90
grep -lE "trbpsd_mod|trbpsd-mod" tr/*.f90 | head
```
Expected: `SRCM` には `trbpsd.f90` のみ。`trbpsd-mod.f90` は孤立ファイル（既存 `tr2` ビルドにも使われていない可能性が高い）。

**方針:** L-2 では `trbpsd-mod.f90` を `SRCS_API` にも `SRCM` にも追加しない。L-4 で `libtrapi.so` リンク時に `tr_api` から未解決シンボルが出たら（あるいは Phase 0 で `tr2` に必要だったことが判明したら）、そのとき初めて `SRCM` への追加を別タスクで議論する。本 L-2 サブフェーズの観察結論として「`trbpsd-mod.f90` は現行ビルド未使用、`libtrapi.so` でも除外」を本 plan に明記。

- [ ] **Step 2: `all` ターゲットに API オブジェクトのビルドを追加（リンクは行わない）**

既存:
```makefile
all: libs tr2
```
を:
```makefile
all: libs tr2 $(OBJ_API)
```
に変更。これで `tr_state.o`, `tr_param_registry.o`, `tr_api.o` が `tr/obj/` に生成されるが、`tr2` のリンクには含まれない。

- [ ] **Step 3: clean ビルドして tr2 が変わらないこと、API .o が出ることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
(cd tr && make clean && make 2>&1 | tail -10)
ls tr/obj/tr_state.o tr/obj/tr_param_registry.o tr/obj/tr_api.o
nm tr/tr2 | grep -E "^[0-9a-f]+ T tr_init$|^[0-9a-f]+ T tr_run$" | head
```
Expected:
- `tr2` が生成され、エラーなし。
- 3 つの API .o ファイルが存在する。
- `nm tr/tr2` には `T tr_init`/`T tr_run` の C シンボルは **含まれない**（リンクしていないため）。これにより既存 `tr2` の挙動が変わらないことが保証される。

---

## Task 7: C スモークテストを追加

**Files:**
- Create: `tr/tests/c_abi/test_smoke.c`
- Create: `tr/tests/c_abi/Makefile`

- [ ] **Step 1: スモークテスト C ソース**

作成: `tr/tests/c_abi/test_smoke.c`

```c
/* Phase L-2 smoke: just call tr_init then tr_finalize. No numerics yet.
 * Verifies link & ALLOCATE/DEALLOCATE_TRCOMM cycle from the C side. */
#include <stdio.h>
#include <stdlib.h>
#include "../../tr_api.h"

int main(void) {
    int rc;
    rc = tr_init();
    if (rc != 0) { fprintf(stderr, "tr_init failed: %d\n", rc); return 1; }
    rc = tr_run(0);          /* L-2 stub no-op */
    if (rc != 0) { fprintf(stderr, "tr_run(0) failed: %d\n", rc); return 1; }
    rc = tr_finalize();
    if (rc != 0) { fprintf(stderr, "tr_finalize failed: %d\n", rc); return 1; }
    printf("OK: init/run/finalize cycle returned 0\n");
    return 0;
}
```

- [ ] **Step 2: ビルド用 Makefile**

作成: `tr/tests/c_abi/Makefile`

```makefile
# Phase L-2 smoke test. Links the API objects and dependencies directly
# (libtrapi.so does not exist yet; arrives in L-4).

include ../../../make.header

TR_OBJDIR=../../obj
API_OBJS=$(TR_OBJDIR)/tr_state.o $(TR_OBJDIR)/tr_param_registry.o $(TR_OBJDIR)/tr_api.o
TR_LIB=../../libtr2.a
DEPS=../../../eq/libeq.a ../../../pl/libpl.a ../../../lib/libmds.a \
     ../../../lib/libtask.a ../../../lib/libgrf.a ../../../bpsd/libbpsd.a

test_smoke: test_smoke.c $(API_OBJS) $(TR_LIB)
	$(CC) -I../.. test_smoke.c $(API_OBJS) $(TR_LIB) $(DEPS) \
	     $(FLIBS) -o test_smoke

run: test_smoke
	./test_smoke

clean:
	-rm -f test_smoke
```

- [ ] **Step 3: スモーク実行**

Run:
```bash
cd /home/k-yoshimi/program/task/tr/tests/c_abi
make run 2>&1 | tail -10
```
Expected: `OK: init/run/finalize cycle returned 0`。

注: リンクが gfortran ランタイムで失敗する場合は `$(FLINKER)` を C ドライバとして使う方式に切り替える（`tr/Makefile` の `FLINKER` を流用）。`make.header` に `CC` が定義されていない場合も同様に `FLINKER` 化する。

- [ ] **Step 4: 失敗時の撤退**

リンクが解決できない場合、L-4 の libtrapi.so 生成と同時にスモークを動かす設計に変更する（`Makefile` をコメントアウトしておき、`test_smoke.c` だけ commit、L-4 で復活）。L-2 全体は止めない。

---

## Task 8: Phase 0 回帰テストで tr2 不変を確認

**Files:**
- なし

- [ ] **Step 1: 回帰 3 ケース PASS**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -10
```
Expected: 3/3 PASS（API オブジェクトを追加しても tr2 はリンクしないため、数値は完全に同じ）。

---

## Task 9: コミットと PR

**Files:**
- なし

- [ ] **Step 1: 段階的コミット**

Run:
```bash
git add tr/tr_state.f90 tr/tr_param_registry.f90 tr/tr_api.f90 tr/tr_api.h
git commit -m "feat(tr): add C ABI scaffolding (tr_state, tr_param_registry, tr_api)"

git add tr/Makefile
git commit -m "build(tr): compile C ABI objects (no libtrapi.so yet)"

git add tr/tests/c_abi/
git commit -m "test(tr): add C ABI smoke test for init/run/finalize"
```

- [ ] **Step 2: PR 作成**

Run:
```bash
gh pr create --base develop --title "feat(tr): Phase L-2 C ABI foundation (stubs + smoke)" \
  --body "Phase L-2: C ABI 5 関数のスケルトン、tr_state_c 構造体、tr_api.h、C スモークを追加。tr2 バイナリには新規シンボルをリンクせず、回帰 3 ケースは引き続き PASS。設計書 §3, §4。"
```

---

## 撤退条件 / フォールバック

| 状況 | 判断 |
|---|---|
| `ALLOCATE_TRCOMM` のシグネチャが想定と違う | ラッパサブルーチンを `trinit.f90` に追加するのではなく、`tr_api.f90` 内で対処（最小変更原則） |
| C スモークがリンクできない | C スモーク Makefile を一旦削除し、L-4 の libtrapi.so 完成後に Layer 2 として実装 |
| 回帰テストが FAIL | Makefile の `all:` 変更を revert（API .o を all から外す）して原因切り分け |

## 受け入れ基準

- [ ] 4 つの新規ファイル (`tr_state.f90`, `tr_param_registry.f90`, `tr_api.f90`, `tr_api.h`) が存在
- [ ] `make -C tr` で 3 つの API オブジェクトが生成
- [ ] `nm tr/tr2 | grep tr_init$` で **何も出ない**（tr2 に未リンク）
- [ ] 回帰 3 ケース PASS
- [ ] C スモーク `tr/tests/c_abi/test_smoke` が exit 0（撤退時を除く）

## 依存

- L-1 完了（`SRCS_CORE` 等が定義済み）
