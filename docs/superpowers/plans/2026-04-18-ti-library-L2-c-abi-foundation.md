# TI Library Phase L-2: C ABI Foundation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TI モジュールに C ABI の土台を導入する。`ti_state.f90`（C 互換 state struct 定義）と `ti_api.f90`（5 関数の **stub** 実装）を新設し、対応する C ヘッダ `ti_api.h` を追加する。実装は最小限の wrapper として既存 ti サブルーチン（`ti_init`, `ti_exec` など）に委譲する。L-3 以降で `ti_set_param` を本実装し、L-4 で shared library を作る。

**Architecture:** TR の C ABI 設計（`tr/tr_api.f90` 5 関数: `tr_init/tr_run/tr_get_state/tr_set_param/tr_finalize`）を ti に転用。命名規則は `ti_*`、state 構造体は `ti_state_t`（NRMAX/nsa_max を反映、impurity transport の量を含む）。本フェーズでは **既存 ti 実行バイナリ `ti` への影響ゼロ**（新ファイル追加と Makefile への 1 ターゲット追加のみ）。

**Tech Stack:** Fortran 90 + ISO_C_BINDING, C ヘッダ。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` 4 章 (C ABI シグネチャ) を ti に転用。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `ti/ti_state.f90` | 新規 | `ti_state_c` 構造体（C 互換）の定義 |
| `ti/ti_api.f90` | 新規 | C ABI 5 関数（`ti_init/ti_run/ti_get_state/ti_set_param/ti_finalize`）の wrapper、本フェーズでは `ti_set_param` のみ stub（常に -1 を返す） |
| `ti/ti_api.h` | 新規 | 上記 5 関数の C 言語プロトタイプ + `ti_state_t` typedef |
| `ti/Makefile` | 修正 | `SRCS_API = ti_state.f90 ti_api.f90` を追加。**まだ libti.a / ti バイナリには含めない**（本フェーズでは独立コンパイル確認のみ） |
| `ti/tests/c_abi/test_compile.c` | 新規 | `ti_api.h` を `#include` してコンパイルが通ることだけ確認する最小 C ファイル |
| `ti/tests/c_abi/Makefile` | 新規 | 上記 .c をコンパイル + 実行する最小 Makefile |

**スコープ外（後の L-3/L-4 で実装）:**
- `ti_set_param` の本実装（L-3 で `ti_param_registry.f90` 経由）
- `libtiapi.so` 生成（L-4）
- リンクテスト全般（L-4）

---

## Task 1: 前提確認

**Files:**
- なし

- [ ] **Step 1: ブランチ作成と L-1 マージ確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin
git checkout -b feature/ti-library-L2-c-abi-foundation origin/develop
grep "SRCS_CORE\|SRCS_GRAPHICS" /home/k-yoshimi/program/task/ti/Makefile | head -5
```
Expected: develop に L-1 の `SRCS_CORE/GRAPHICS/MENU` 分割が入っている。新ブランチに居る。

- [ ] **Step 1b: 依存モジュール `plinit` / `equnit` / `tiinit` の存在を verify**

`ti_api.f90` で `USE plinit, ONLY: pl_init` / `USE equnit, ONLY: eq_init` / `USE tiinit, ONLY: ti_init` を呼ぶため、対応する `MODULE` 定義が実在することを確認する。

Run:
```bash
grep -ln "^[[:space:]]*MODULE plinit\b" /home/k-yoshimi/program/task/pl/ -r
grep -ln "^[[:space:]]*MODULE equnit\b" /home/k-yoshimi/program/task/eq/ -r
grep -n "USE plinit\|USE equnit\|USE tiinit" /home/k-yoshimi/program/task/ti/timain.f90
```
Expected:
- `pl/plinit.f90` に `MODULE plinit` がある（既存 `ti/timain.f90:12` の `USE plinit, ONLY: pl_init` が解決できているはず）。
- `eq/equnit.f` に `MODULE equnit` がある（拡張子 `.f` の固定形式）。
- `ti/timain.f90` の USE 行（`USE plinit,ONLY: pl_init` / `USE equnit,ONLY: eq_init` / `USE tiinit,ONLY: ti_init`）が表示される。

**フォールバック (どれかが欠けていた場合):**
- `plinit` が無い場合: `pl/plload.f90` 等を grep して `pl_init` を提供している実モジュール名を探し、`ti_api.f90` の USE 行を実モジュール名に置換する。
- `equnit` が無い場合: `eq/eqinit.f`, `eq/eqcalc.f` などから `eq_init` の MODULE を探して置換。
- `tiinit` のサブルーチン名が `ti_init` 以外（例: `init_ti`）の場合: 名前衝突回避が二重に必要 → `ti_api.f90` で `USE tiinit, ONLY: ti_init_internal => <real_name>` の rename を導入。
- どれも実在しない極端な場合: `ti/timain.f90` の実 USE 行を移植する（同じ初期化シーケンスを再現）。

- [ ] **Step 2: L-0 回帰テストが PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh ti_min ti_ar ti_w
```
Expected: ビルド OK、3/3 PASS。

- [ ] **Step 3: 空コミット**

Run:
```bash
git commit --allow-empty -m "chore(ti): start L-2 C ABI foundation"
```

---

## Task 2: `ti_state.f90` を新設

**Files:**
- Create: `ti/ti_state.f90`

**目的:** C 互換の `ti_state_c` を ISO_C_BINDING で定義する。固定サイズ配列とし、上限を `TI_MAX_NRMAX=200`, `TI_MAX_NSA_MAX=20` に設定（不純物多価数イオンを多めに見て NSM=100 から 20 に絞る。実 ti 入力では nsa_max <= 50 程度で収まる想定）。

- [ ] **Step 1: 新規ファイル作成**

作成: `ti/ti_state.f90`

```fortran
! ti_state.f90
!
! C-compatible state struct for the TI library API.
! Fixed-size arrays for simplicity; runtime nrmax/nsa_max must be <= the maxima.

MODULE ti_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE

  INTEGER(C_INT), PARAMETER :: TI_MAX_NRMAX   = 200
  INTEGER(C_INT), PARAMETER :: TI_MAX_NSA_MAX = 20

  ! Mirror of the (NSA,NR) profile arrays in ticomm.
  ! Indexing in C: state.RNA[NR][NSA] (row-major). Fortran writer flattens
  ! using DO NR / DO NSA matching this layout.
  TYPE, BIND(C) :: ti_state_c
     INTEGER(C_INT) :: nt
     INTEGER(C_INT) :: nrmax
     INTEGER(C_INT) :: nsa_max
     INTEGER(C_INT) :: nsmax
     REAL(C_DOUBLE) :: T
     REAL(C_DOUBLE) :: residual_loop_max
     INTEGER(C_INT) :: icount_loop_max
     INTEGER(C_INT) :: icount_mat_max
     ! per-(NR,NSA) profiles
     REAL(C_DOUBLE) :: RNA(TI_MAX_NSA_MAX, TI_MAX_NRMAX)
     REAL(C_DOUBLE) :: RTA(TI_MAX_NSA_MAX, TI_MAX_NRMAX)
     REAL(C_DOUBLE) :: RUA(TI_MAX_NSA_MAX, TI_MAX_NRMAX)
     ! per-NR scalars
     REAL(C_DOUBLE) :: RBP(TI_MAX_NRMAX)
     REAL(C_DOUBLE) :: RQP(TI_MAX_NRMAX)
     REAL(C_DOUBLE) :: RJP(TI_MAX_NRMAX)
     REAL(C_DOUBLE) :: ZEFF(TI_MAX_NRMAX)
     REAL(C_DOUBLE) :: BETA(TI_MAX_NRMAX)
     REAL(C_DOUBLE) :: BETAP(TI_MAX_NRMAX)
  END TYPE ti_state_c

END MODULE ti_state
```

- [ ] **Step 2: 単体コンパイルが通ることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
gfortran -c ti_state.f90 -J./mod -o /tmp/ti_state.o 2>&1 | tail -5
ls /tmp/ti_state.o /home/k-yoshimi/program/task/ti/mod/ti_state.mod
```
Expected: `.o` と `.mod` が生成される。エラーなし。

- [ ] **Step 3: コミット**

Run:
```bash
git add ti/ti_state.f90
git commit -m "feat(ti): add ti_state.f90 with C-compatible state struct"
```

---

## Task 3: `ti_api.f90` 5 関数 stub を新設

**Files:**
- Create: `ti/ti_api.f90`

**目的:** 5 関数の C ABI を **wrapper** として実装する:
- `ti_init` — 既存の `pl_init`, `eq_init`, `ti_init` (tiinit.f90 の方) を呼ぶ
- `ti_run` — 既存の `ti_prep` + `ti_exec` を呼ぶ
- `ti_get_state` — `ticomm` 変数を `ti_state_c` にコピー
- `ti_set_param` — **stub**（常に `-1`、L-3 で `ti_param_registry` 経由実装）
- `ti_finalize` — 既存の `deallocate_ticomm` を呼ぶ

注意: 内部 `ti_init` (tiinit.f90 の subroutine) と本 ABI の `ti_init` (本ファイル) は名前が衝突する。回避策として ABI 関数は `BIND(C, NAME="ti_init")` で C シンボル名を `ti_init` に固定し、Fortran 内部名は `ti_init_c` とする（C から呼ぶ際は `ti_init` のまま）。

- [ ] **Step 1: 新規ファイル作成**

作成: `ti/ti_api.f90`

```fortran
! ti_api.f90
!
! C ABI for the TI library. 5 functions exposed as `ti_*` C symbols.
! Body is a thin wrapper around existing ti_* subroutines (ti_init in tiinit.f90,
! ti_prep, ti_exec, etc.) so that runtime semantics match the standalone `ti`
! binary exactly.
!
! ti_set_param is a stub in this phase (always returns 1 = invalid param).
! It will be backed by ti_param_registry in Phase L-3.

MODULE ti_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE ti_state, ONLY: ti_state_c, TI_MAX_NRMAX, TI_MAX_NSA_MAX
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: ti_init_c, ti_run_c, ti_get_state_c, ti_set_param_c, ti_finalize_c

  ! Module-level lifecycle state.
  ! `g_initialized` is set by ti_init_c, cleared by ti_finalize_c.
  ! `g_prepped`     is set by the first ti_run_c (after ti_prep), cleared by
  !                 ti_finalize_c so that the NEXT ti_init_c/ti_run_c cycle
  !                 re-runs ti_prep. This is critical for L-6 sweep tests
  !                 (per-cell `with Tilib():` blocks) — see fallback table.
  INTEGER, SAVE :: g_initialized = 0
  INTEGER, SAVE :: g_prepped     = 0

CONTAINS

  FUNCTION ti_init_c() RESULT(ierr) BIND(C, NAME="ti_init")
    USE plinit, ONLY: pl_init
    USE equnit, ONLY: eq_init
    USE tiinit, ONLY: ti_init      ! existing internal init
    INTEGER(C_INT) :: ierr
    ierr = 0
    CALL pl_init
    CALL eq_init
    CALL ti_init                   ! sets defaults, allocates nothing yet
    g_initialized = 1
    g_prepped     = 0              ! force re-prep on the next ti_run_c
  END FUNCTION ti_init_c

  FUNCTION ti_run_c(ntmax_arg) RESULT(ierr) BIND(C, NAME="ti_run")
    USE ticomm_parm, ONLY: NTMAX
    USE tiprep, ONLY: ti_prep
    USE tiexec, ONLY: ti_exec
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax_arg
    INTEGER(C_INT) :: ierr
    INTEGER :: jerr

    ierr = 0
    IF (g_initialized == 0) THEN
       ierr = 2                    ! lifecycle violation (call ti_init first)
       RETURN
    END IF
    NTMAX = ntmax_arg
    IF (g_prepped == 0) THEN
       CALL ti_prep(jerr)
       IF (jerr /= 0) THEN
          ierr = 3
          RETURN
       END IF
       g_prepped = 1
    END IF
    CALL ti_exec(jerr)
    IF (jerr /= 0) ierr = 3
  END FUNCTION ti_run_c

  FUNCTION ti_get_state_c(state) RESULT(ierr) BIND(C, NAME="ti_get_state")
    USE ticomm, ONLY: NRMAX, NSMAX, nsa_max, NT, T, &
                       residual_loop_max, icount_loop_max, icount_mat_max, &
                       RNA, RTA, RUA, RBP, RQP, RJP, ZEFF, BETA, BETAP
    TYPE(ti_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: NR, NSA

    ierr = 0
    IF (NRMAX > TI_MAX_NRMAX) THEN
       ierr = 4
       RETURN
    END IF
    IF (nsa_max > TI_MAX_NSA_MAX) THEN
       ierr = 4
       RETURN
    END IF

    state%nt                = NT
    state%nrmax             = NRMAX
    state%nsa_max           = nsa_max
    state%nsmax             = NSMAX
    state%T                 = T
    state%residual_loop_max = residual_loop_max
    state%icount_loop_max   = icount_loop_max
    state%icount_mat_max    = icount_mat_max

    state%RNA = 0.0_C_DOUBLE
    state%RTA = 0.0_C_DOUBLE
    state%RUA = 0.0_C_DOUBLE
    state%RBP = 0.0_C_DOUBLE
    state%RQP = 0.0_C_DOUBLE
    state%RJP = 0.0_C_DOUBLE
    state%ZEFF = 0.0_C_DOUBLE
    state%BETA = 0.0_C_DOUBLE
    state%BETAP = 0.0_C_DOUBLE

    DO NR = 1, NRMAX
       DO NSA = 1, nsa_max
          state%RNA(NSA, NR) = RNA(NSA, NR)
          state%RTA(NSA, NR) = RTA(NSA, NR)
          state%RUA(NSA, NR) = RUA(NSA, NR)
       END DO
       state%RBP(NR)   = RBP(NR)
       state%RQP(NR)   = RQP(NR)
       state%RJP(NR)   = RJP(NR)
       state%ZEFF(NR)  = ZEFF(NR)
       state%BETA(NR)  = BETA(NR)
       state%BETAP(NR) = BETAP(NR)
    END DO
  END FUNCTION ti_get_state_c

  FUNCTION ti_set_param_c(name, value) RESULT(ierr) BIND(C, NAME="ti_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! Stub: not implemented in L-2. Backed by ti_param_registry in L-3.
    ! Suppress unused-variable warnings.
    IF (name(1) == C_NULL_CHAR) CONTINUE
    IF (value /= value) CONTINUE
    ierr = 1   ! invalid parameter
  END FUNCTION ti_set_param_c

  FUNCTION ti_finalize_c() RESULT(ierr) BIND(C, NAME="ti_finalize")
    USE ticomm, ONLY: deallocate_ticomm
    INTEGER(C_INT) :: ierr
    ierr = 0
    CALL deallocate_ticomm
    g_initialized = 0
    g_prepped     = 0              ! ensure next init->run cycle re-preps
  END FUNCTION ti_finalize_c

END MODULE ti_api
```

注: `deallocate_ticomm` の名前は `ticomm.f90` を確認して合わせる（Step 2 で確認）。`ticomm.f90:361` に `SUBROUTINE deallocate_ticomm` が存在することは確認済（worktree state 2026-04-18 時点）。

注 2 (L-6 連携): 上記の **module-level `g_prepped` リセット** は、L-6 で実装する `test_sweep.py` の per-cell `with Tilib():` パターンに不可欠。`SAVE` 変数を関数内に閉じ込めると `ti_finalize_c` 経由でリセットできず、2 セル目以降で `ti_prep` がスキップされて `RNA/RTA/RUA` が ALLOCATE されない不具合になる。

- [ ] **Step 2: deallocate_ticomm の正確な名前を確認**

Run:
```bash
grep -n "SUBROUTINE deallocate\|SUBROUTINE allocate_ticomm\|SUBROUTINE deallocate_ticomm" \
    /home/k-yoshimi/program/task/ti/ticomm.f90
```
Expected: `deallocate_ticomm` または類似名が見える。異なる場合は `ti_finalize_c` 内の呼び出しを実名に合わせて修正。

- [ ] **Step 3: 単体コンパイル確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
gfortran -c ti_api.f90 -J./mod -I./mod -I../pl/mod -I../eq/mod -I../../bpsd/mod \
    -o /tmp/ti_api.o 2>&1 | tail -10
ls /tmp/ti_api.o /home/k-yoshimi/program/task/ti/mod/ti_api.mod
```
Expected: コンパイル成功。`.o` と `.mod` が生成される。

依存 module の `.mod` が無いと言われた場合は事前に `make libti.a` を実行して mod ファイルを生成しておく。

- [ ] **Step 4: コミット**

Run:
```bash
git add ti/ti_api.f90
git commit -m "feat(ti): add ti_api.f90 with 5-function C ABI (ti_set_param stub)"
```

---

## Task 4: `ti_api.h` を新設

**Files:**
- Create: `ti/ti_api.h`

- [ ] **Step 1: ヘッダ作成**

作成: `ti/ti_api.h`

```c
/*
 * ti_api.h — C interface for the TI library.
 *
 * Layout note: Fortran writes profile arrays as state.RNA(NSA, NR), so
 * from C the access is state->RNA[NR][NSA] when the struct is interpreted
 * as a flat row-major buffer. NR and NSA are 0-indexed in C (the Fortran
 * side already wrote into 0..NRMAX-1 / 0..nsa_max-1 slots).
 */
#ifndef TI_API_H
#define TI_API_H

#define TI_MAX_NRMAX   200
#define TI_MAX_NSA_MAX 20

typedef struct {
    int nt;
    int nrmax;
    int nsa_max;
    int nsmax;
    double T;
    double residual_loop_max;
    int icount_loop_max;
    int icount_mat_max;
    double RNA[TI_MAX_NRMAX][TI_MAX_NSA_MAX];
    double RTA[TI_MAX_NRMAX][TI_MAX_NSA_MAX];
    double RUA[TI_MAX_NRMAX][TI_MAX_NSA_MAX];
    double RBP[TI_MAX_NRMAX];
    double RQP[TI_MAX_NRMAX];
    double RJP[TI_MAX_NRMAX];
    double ZEFF[TI_MAX_NRMAX];
    double BETA[TI_MAX_NRMAX];
    double BETAP[TI_MAX_NRMAX];
} ti_state_t;

#ifdef __cplusplus
extern "C" {
#endif

/* Initialize TI internal state (calls pl_init / eq_init / ti_init internally). */
int ti_init(void);

/* Run NTMAX time steps. Calls ti_prep on first call, then ti_exec each call. */
int ti_run(int ntmax);

/* Copy current ticomm values into *state. Returns 4 if NRMAX/nsa_max exceed
 * compile-time maxima. */
int ti_get_state(ti_state_t* state);

/* Set a single named parameter. STUB in L-2 (always returns 1). */
int ti_set_param(const char* name, double value);

/* Free allocations (calls deallocate_ticomm). */
int ti_finalize(void);

#ifdef __cplusplus
}
#endif

#endif /* TI_API_H */
```

- [ ] **Step 2: ヘッダの C 構文チェック（プリプロセス + 構文）**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
gcc -E ti_api.h -o /tmp/ti_api.h.E
echo 'int main(void){ return 0; }' | gcc -include /home/k-yoshimi/program/task/ti/ti_api.h -x c - -o /tmp/ti_api_smoke 2>&1 | tail -5
ls /tmp/ti_api_smoke
```
Expected: コンパイルが通り `/tmp/ti_api_smoke` が生成される。

- [ ] **Step 3: コミット**

Run:
```bash
git add ti/ti_api.h
git commit -m "feat(ti): add ti_api.h C header with ti_state_t and 5 prototypes"
```

---

## Task 5: 最小 C テスト `tests/c_abi/` を追加

**Files:**
- Create: `ti/tests/c_abi/test_compile.c`
- Create: `ti/tests/c_abi/Makefile`

**目的:** 本フェーズでは link は行わず、ヘッダがコンパイル可能であること、`ti_state_t` のサイズが期待通り（`TI_MAX_NRMAX * TI_MAX_NSA_MAX * sizeof(double) * 3 +` 等）であることを確認する。L-4 で実 `libtiapi.so` ができたらリンクテストに昇格する。

- [ ] **Step 1: ディレクトリ作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/ti/tests/c_abi
```

- [ ] **Step 2: test_compile.c 作成**

作成: `ti/tests/c_abi/test_compile.c`

```c
/*
 * test_compile.c — L-2 smoke: header compiles, struct sizes are sane,
 * function pointers can be declared. Does NOT link against libtiapi.so
 * (that's L-4).
 */
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
#include "ti_api.h"

int main(void) {
    /* sanity sizes */
    assert(sizeof(ti_state_t) > 0);
    assert(TI_MAX_NRMAX == 200);
    assert(TI_MAX_NSA_MAX == 20);

    /* function pointer compatibility (no link required) */
    int (*p_init)(void)                            = NULL;
    int (*p_run)(int)                              = NULL;
    int (*p_get_state)(ti_state_t*)                = NULL;
    int (*p_set_param)(const char*, double)        = NULL;
    int (*p_finalize)(void)                        = NULL;
    (void)p_init; (void)p_run; (void)p_get_state; (void)p_set_param; (void)p_finalize;

    printf("OK: ti_api.h compiles, sizeof(ti_state_t)=%zu bytes\n",
           sizeof(ti_state_t));
    return 0;
}
```

- [ ] **Step 3: tests/c_abi/Makefile 作成**

作成: `ti/tests/c_abi/Makefile`

```makefile
# L-2 smoke: compile-only test for ti_api.h.
TI_DIR := $(abspath $(CURDIR)/../..)
CFLAGS := -Wall -Wextra -O0 -I$(TI_DIR)

.PHONY: test clean

test: test_compile
	./test_compile

test_compile: test_compile.c $(TI_DIR)/ti_api.h
	$(CC) $(CFLAGS) test_compile.c -o test_compile

clean:
	rm -f test_compile
```

- [ ] **Step 4: テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task/ti/tests/c_abi
make test
```
Expected: `OK: ti_api.h compiles, sizeof(ti_state_t)=NNNN bytes`。

- [ ] **Step 5: コミット**

Run:
```bash
git add ti/tests/c_abi/test_compile.c ti/tests/c_abi/Makefile
git commit -m "test(ti): add L-2 C ABI compile smoke test"
```

---

## Task 6: Makefile に `SRCS_API` を導入（既存ビルド未影響）

**Files:**
- Modify: `ti/Makefile`

**目的:** `SRCS_API = ti_state.f90 ti_api.f90` を新設し、`api-objs` ターゲットでこれだけをコンパイルできるようにする。L-3 までは libti.a / ti バイナリには含めない。L-4 で `libtiapi.so` のソースとして使う。

- [ ] **Step 1: SRCS_API を追加**

`ti/Makefile` の SRCS 定義部に以下を追加（L-1 の `SRCS_MENU= timenu.f90` の直後）:

```
# C-ABI sources for libtiapi.so. NOT included in `ti` binary or libti.a until L-4.
SRCS_API= ti_state.f90 ti_api.f90

OBJS_API= $(SRCS_API:.f90=.o)
```

- [ ] **Step 2: api-objs phony ターゲットを追加**

`ti/Makefile` の `srcs-core-list:` の付近に以下を追加:

```
.PHONY: api-objs

api-objs: $(OBJS_API)

ti_state.o : ti_state.f90
ti_api.o   : ti_api.f90 ti_state.f90 ticomm.f90 tiinit.f90 tiprep.f90 tiexec.f90
```

- [ ] **Step 3: api-objs だけビルドできることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make libs        # ensure dependent .mod are present (pl, eq, etc.)
make ticomm.o tiinit.o tiprep.o tiexec.o   # ensure ti's own .mod files are present
make api-objs 2>&1 | tail -5
ls ti_state.o ti_api.o
```
Expected: `ti_state.o` と `ti_api.o` が生成される。エラーなし。

- [ ] **Step 4: 既存 `ti` バイナリは影響を受けないことを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make clean
make 2>&1 | tail -10
ls ti libti.a
ar t libti.a | grep -E "ti_state|ti_api"
```
Expected:
- `ti` と `libti.a` が引き続き生成される。
- `libti.a` に `ti_state.o` / `ti_api.o` は **含まれない** (L-2 では libti.a 未統合)。

- [ ] **Step 5: L-0 回帰テスト PASS 確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh ti_min ti_ar ti_w
```
Expected: 3/3 PASS。既存挙動完全不変。

- [ ] **Step 6: コミット**

Run:
```bash
git add ti/Makefile
git commit -m "build(ti): add SRCS_API and api-objs target (libtiapi.so prep)"
```

---

## Task 7: PR 作成

- [ ] **Step 1: 変更ファイルの最終確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: 新規 6 ファイル (`ti_state.f90`, `ti_api.f90`, `ti_api.h`, `tests/c_abi/test_compile.c`, `tests/c_abi/Makefile`)、修正 1 ファイル (`ti/Makefile`)。

- [ ] **Step 2: push と PR**

Run:
```bash
git push -u origin feature/ti-library-L2-c-abi-foundation
gh pr create --base develop \
  --title "feat(ti): add C ABI foundation (ti_state, ti_api stub) (L-2)" \
  --body "Phase L-2: scaffolding for libtiapi.so. ti_set_param is a stub (L-3 implements it). ti binary unchanged; L-0 regression tests pass 3/3."
```

---

## Dependencies

- 前段階: L-1 マージ済み (`SRCS_CORE/GRAPHICS/MENU` 分離)。
- 後段階: L-3 が `ti_set_param` 本実装、L-4 が `libtiapi.so` リンク。

## Fallback

| 障害 | 対処 |
|---|---|
| `ti_init` 名衝突がコンパイラで解消されない | Fortran 内部関数名を `ti_init_c` に固定（本計画通り）し `BIND(C, NAME="ti_init")` で C シンボルだけ揃える。それでもダメなら C 側を `tilib_init` 等にリネーム |
| `deallocate_ticomm` が無い | 確認済: `ticomm.f90:361 SUBROUTINE deallocate_ticomm` が存在。万一実環境で renamed されていた場合は `grep -n "deallocate_ticomm\|deallocate.ticomm" ti/ticomm.f90` で実名を確認して置換。代替: `ALLOCATABLE` 個別の `IF(ALLOCATED) DEALLOCATE` を `ti_finalize_c` 内で順次実行 |
| `equnit` モジュールが無い | 確認済: `eq/equnit.f` (固定形式) に `MODULE equnit` が定義されており、`ti/timain.f90:13` の `USE equnit, ONLY: eq_init` と整合。万一見当たらなければ `grep -lr "MODULE equnit\|SUBROUTINE eq_init" eq/` で実モジュールを探して USE 行を修正 |
| `plinit` モジュールが無い | 確認済: `pl/plinit.f90` に `MODULE plinit` あり。`pl_init` も同モジュール内 PUBLIC |
| `ti_run` 2 回目以降が `ti_prep` をスキップする | 本計画は module-level `g_prepped` を `ti_finalize_c` でリセット済（L-6 sweep 対策）。万一 `g_prepped` でなく関数内 `SAVE` を残す場合は、L-6 で per-cell `with Tilib():` テストが落ちるので注意 |
| ti_state_t が大きすぎる | `TI_MAX_NRMAX` を 100 に下げる、または将来 dynamic API に切り替え |
