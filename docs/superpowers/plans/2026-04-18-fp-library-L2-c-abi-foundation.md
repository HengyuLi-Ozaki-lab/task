# FP ライブラリ化 Phase L-2: C ABI 基盤（fp_state / fp_api / fp_api.h）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `fp/` に C ABI の最小骨格を 3 ファイル（`fp_state.f90`, `fp_api.f90`, `fp_api.h`）として追加する。実装は **stub 主体**（`fp_init/fp_run/fp_get_state/fp_set_param/fp_finalize` の 5 関数を `bind(c)` で公開し、内部から既存 `fp_init`, `fp_prep`, `fp_loop` 等を呼び出す）。`fp_set_param` は L-3 まではダミー実装で `ierr=1` を返してもよい。L-2 単体では `fp` バイナリの数値結果は不変、`make` で `fp_api.f90` がコンパイル通過することが必須要件。

**Architecture:** TR Phase L 設計 (`tr_library-design.md` セクション 4.1, 4.2) を fp 用に転用:

```
PROGRAM fp (fpmain.f90)             [既存]
  └─ fp_menu                          [既存、graphics + 対話シーケンス]

MODULE fp_api (fp_api.f90)          [新規: C ABI 5 関数]
  ├─ fp_init   → 既存 pl_init / fp_init / open_fpcomm_parm
  ├─ fp_run    → 既存 fp_prep + fp_loop
  ├─ fp_set_param → L-3 で実装、L-2 では ierr=1 stub
  ├─ fp_get_state → fp_state_c に fpcomm の代表値をコピー
  └─ fp_finalize → fp_deallocate
```

5 関数全て `INTEGER(C_INT)` 戻り値、`bind(c, name="fp_*")` で公開。

**命名規約 — Fortran PUBLIC vs C シンボル:**

Fortran 側では `fp_init_c, fp_run_c, fp_set_param_c, fp_get_state_c, fp_finalize_c`（`_c` サフィックス付き）として PUBLIC 公開する一方、C ABI 上は `BIND(C, NAME="fp_init")` 等で `_c` を取った素のシンボル名を export する。これは:

- Fortran 内では「C ABI 用関数」と分かるよう `_c` サフィックスで識別
- C ヘッダ / C コードからは素の `fp_init` を呼ぶ（ヘッダの prototype と一致）
- リンク時には `BIND(C, NAME=...)` 指定により素の名前で解決される

L-3 以降で `nm -D libfpapi.so | grep ' T fp_'` を確認するとき、表示されるのは `fp_init` 等（`_c` 抜き）になる点に注意。

**Tech Stack:** Fortran 2003 (`ISO_C_BINDING`)、既存 fp ビルドシステム、回帰テスト（`fp_iter01/jt60/dt1` の bit-exact 維持）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 4.1, 4.2, 4.3。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `fp/fp_state.f90` | 新規 | `MODULE fp_state` に `TYPE, BIND(C) :: fp_state_c` を定義（C struct 互換）|
| `fp/fp_api.f90` | 新規 | `MODULE fp_api` に 5 つの `bind(c)` 関数を実装（`fp_set_param` は L-2 で stub）|
| `fp/fp_api.h` | 新規 | C ヘッダ（`fp_state_t` typedef、5 プロトタイプ、エラーコード定数）|
| `fp/Makefile` | 修正 | `SRCS_API = fp_state.f90 fp_api.f90` を追加。`SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` のままで `fp` バイナリは API を含めない（L-4 で `libfpapi.so` リンク用にだけ使う）。ただし「ビルド可能性」を保証するため、`fp_api.o` 単体の compile rule は OBJS から外して別ターゲット `fp_api_check` で確認できるようにする |
| `fp/tests/c_abi/test_abi_smoke.c` | 新規 | C ABI ヘッダが C コードからインクルードできること、シンボル `fp_init` 等の定義が `bind(c)` 命名どおりに用意できているかを **コンパイル時のみ** 検証（リンクは L-4 で行う）|
| `fp/tests/c_abi/Makefile` | 新規 | `gcc -c test_abi_smoke.c -I..` だけ走らせる軽量テスト |

---

## Task 1: 作業ブランチ作成と L-1 完了確認

- [ ] **Step 1: L-1 マージ済みを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | head -10
```
Expected: L-0/L-1 のマージコミットが見える。

- [ ] **Step 2: L-2 ブランチ**

Run:
```bash
git checkout -b feature/fp-library-L2-c-abi-foundation origin/develop
```

- [ ] **Step 3: L-1 状態の `fp` がビルドでき、回帰 3 ケースが PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/fp && make 2>&1 | tail -3
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh fp_iter01 fp_jt60 fp_dt1 | tail -10
```
Expected: 3 ケース PASS。

---

## Task 2: `fp/fp_state.f90` を作成（C 互換 struct）

**Files:**
- Create: `fp/fp_state.f90`

- [ ] **Step 1: dump 対象（L-0 で確定済み）と整合した struct 設計を決定**

L-0 で fp が dump する scalar/profile（`NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2, TIMEFP` + `RNT/RWT/RTT/RJT/RPCT/RPWT(NR,NSA,NTG2)`）を C struct に転写する。プロファイルは固定サイズ配列を使う:

- `FP_MAX_NRMAX = 100`（fp 入力で典型 NRMAX <= 50。`fp.inITER` で 40、`fp.injt60` で 11、余裕を持たせる）
- `FP_MAX_NSAMAX = 8`（`NSM=8` が plcomm 上限）

メモリ目安: profile 6 fields × 100 × 8 = 4800 doubles = 38.4 KB。十分軽量。

- [ ] **Step 2: ファイル作成**

作成: `fp/fp_state.f90`

```fortran
! fp_state.f90
!
! C-interoperable state struct for FP library API (Phase L-2).
! Mirrors fp_regress.dat fields used in Phase L-0 baselines.

MODULE fp_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: fp_state_c
  PUBLIC :: FP_MAX_NRMAX, FP_MAX_NSAMAX

  INTEGER(C_INT), PARAMETER :: FP_MAX_NRMAX  = 100
  INTEGER(C_INT), PARAMETER :: FP_MAX_NSAMAX = 8

  TYPE, BIND(C) :: fp_state_c
     INTEGER(C_INT) :: nrmax
     INTEGER(C_INT) :: nsamax
     INTEGER(C_INT) :: npmax
     INTEGER(C_INT) :: nthmax
     INTEGER(C_INT) :: ntg2
     REAL(C_DOUBLE) :: timefp

     ! profile arrays: shape [FP_MAX_NRMAX, FP_MAX_NSAMAX]
     ! actual data only valid for indices [1..nrmax, 1..nsamax]
     REAL(C_DOUBLE) :: RNT (FP_MAX_NRMAX, FP_MAX_NSAMAX)
     REAL(C_DOUBLE) :: RWT (FP_MAX_NRMAX, FP_MAX_NSAMAX)
     REAL(C_DOUBLE) :: RTT (FP_MAX_NRMAX, FP_MAX_NSAMAX)
     REAL(C_DOUBLE) :: RJT (FP_MAX_NRMAX, FP_MAX_NSAMAX)
     REAL(C_DOUBLE) :: RPCT(FP_MAX_NRMAX, FP_MAX_NSAMAX)
     REAL(C_DOUBLE) :: RPWT(FP_MAX_NRMAX, FP_MAX_NSAMAX)
  END TYPE fp_state_c

END MODULE fp_state
```

- [ ] **Step 3: 単独コンパイル確認**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
gfortran -c fp_state.f90 -o /tmp/fp_state.o -J/tmp
ls -la /tmp/fp_state.o
```
Expected: エラーなし、`.o` が出力される。

---

## Task 3: `fp/fp_api.f90` を作成（5 関数 stub）

**Files:**
- Create: `fp/fp_api.f90`

L-2 では:
- `fp_init` → `pl_init + eq_init + ob_init + fp_init` を呼ぶ（ただし MPI 初期化は呼び出し側に任せる暫定方針。L-4 で再評価）
- `fp_run(ntmax_arg)` → `fp_prep(ierr); IF(ierr /= 0) RETURN; NTMAX = ntmax_arg; CALL fp_loop`
- `fp_get_state` → fpcomm の現値を `fp_state_c` にコピー（NRMAX <= FP_MAX_NRMAX チェック）
- `fp_set_param` → L-2 では `ierr=1` を返す stub（L-3 で本実装）
- `fp_finalize` → 既存の `fp_deallocate`（あれば）を呼ぶ

- [ ] **Step 1: 既存 `fp_init` の signature と必要 USE を再確認**

Run:
```bash
grep -n "SUBROUTINE fp_init\|MODULE fpinit\|MODULE fpprep\|SUBROUTINE fp_prep\|MODULE fploop\|SUBROUTINE FP_LOOP" /home/k-yoshimi/program/task/fp/*.f90
```
Expected: `fp_init` は引数なし、`fp_prep(ierr)`、`fp_loop` は引数なし。

- [ ] **Step 2: ファイル作成**

作成: `fp/fp_api.f90`

```fortran
! fp_api.f90
!
! C ABI for FP library (Phase L-2 stub; L-3 will populate fp_set_param).
!
! Functions (all returning INTEGER(C_INT) error code; 0=OK):
!   fp_init     : initialize PL/EQ/OB/FP modules
!   fp_run(N)   : run NTMAX = N timesteps via existing fp_prep + fp_loop
!   fp_set_param: STUB in L-2 (returns 1=invalid). Implemented in L-3.
!   fp_get_state: copy current fpcomm state into fp_state_c
!   fp_finalize : release fp allocations

MODULE fp_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE fp_state, ONLY: fp_state_c, FP_MAX_NRMAX, FP_MAX_NSAMAX
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: fp_init_c, fp_run_c, fp_set_param_c, fp_get_state_c, fp_finalize_c

  INTEGER, PARAMETER :: FP_OK              = 0
  INTEGER, PARAMETER :: FP_ERR_INVALID     = 1
  INTEGER, PARAMETER :: FP_ERR_NOT_INIT    = 2
  INTEGER, PARAMETER :: FP_ERR_CALC_FAIL   = 3
  INTEGER, PARAMETER :: FP_ERR_OVERFLOW    = 4

  LOGICAL, SAVE :: g_initialized = .FALSE.

CONTAINS

  FUNCTION fp_init_c() RESULT(ierr) BIND(C, NAME="fp_init")
    USE plinit, ONLY: pl_init
    USE equnit, ONLY: eq_init
    USE obinit, ONLY: ob_init
    USE fpinit, ONLY: fp_init
    INTEGER(C_INT) :: ierr

    ierr = FP_OK
    CALL pl_init
    CALL eq_init
    CALL ob_init
    CALL fp_init
    g_initialized = .TRUE.
  END FUNCTION fp_init_c

  FUNCTION fp_run_c(ntmax_arg) RESULT(ierr) BIND(C, NAME="fp_run")
    USE fpcomm, ONLY: NTMAX
    USE fpprep, ONLY: fp_prep
    USE fploop, ONLY: fp_loop
    INTEGER(C_INT), VALUE, INTENT(IN) :: ntmax_arg
    INTEGER(C_INT) :: ierr
    INTEGER :: ierr_local

    IF (.NOT. g_initialized) THEN
       ierr = FP_ERR_NOT_INIT; RETURN
    END IF

    NTMAX = ntmax_arg
    CALL fp_prep(ierr_local)
    IF (ierr_local /= 0) THEN
       ierr = FP_ERR_CALC_FAIL; RETURN
    END IF
    CALL fp_loop
    ierr = FP_OK
  END FUNCTION fp_run_c

  FUNCTION fp_set_param_c(name, value) RESULT(ierr) BIND(C, NAME="fp_set_param")
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! L-2 stub: parameter table not implemented yet (L-3 fills this in via
    ! fp_param_registry). Return INVALID for any parameter to fail loud.
    ierr = FP_ERR_INVALID
  END FUNCTION fp_set_param_c

  FUNCTION fp_get_state_c(state) RESULT(ierr) BIND(C, NAME="fp_get_state")
    USE fpcomm, ONLY: NRMAX, NSAMAX, NPMAX, NTHMAX, NTG2, TIMEFP, &
                      RNT, RWT, RTT, RJT, RPCT, RPWT
    TYPE(fp_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: nr, nsa, ntg_last

    IF (.NOT. g_initialized) THEN
       ierr = FP_ERR_NOT_INIT; RETURN
    END IF
    IF (NRMAX > FP_MAX_NRMAX .OR. NSAMAX > FP_MAX_NSAMAX) THEN
       ierr = FP_ERR_OVERFLOW; RETURN
    END IF

    state%nrmax  = NRMAX
    state%nsamax = NSAMAX
    state%npmax  = NPMAX
    state%nthmax = NTHMAX
    state%ntg2   = NTG2
    state%timefp = TIMEFP

    ! initialize trailing slots to zero for determinism
    state%RNT  = 0.0_C_DOUBLE
    state%RWT  = 0.0_C_DOUBLE
    state%RTT  = 0.0_C_DOUBLE
    state%RJT  = 0.0_C_DOUBLE
    state%RPCT = 0.0_C_DOUBLE
    state%RPWT = 0.0_C_DOUBLE

    ntg_last = MAX(NTG2, 1)
    DO nsa = 1, NSAMAX
       DO nr = 1, NRMAX
          state%RNT (nr, nsa) = RNT (nr, nsa, ntg_last)
          state%RWT (nr, nsa) = RWT (nr, nsa, ntg_last)
          state%RTT (nr, nsa) = RTT (nr, nsa, ntg_last)
          state%RJT (nr, nsa) = RJT (nr, nsa, ntg_last)
          state%RPCT(nr, nsa) = RPCT(nr, nsa, ntg_last)
          state%RPWT(nr, nsa) = RPWT(nr, nsa, ntg_last)
       END DO
    END DO

    ierr = FP_OK
  END FUNCTION fp_get_state_c

  FUNCTION fp_finalize_c() RESULT(ierr) BIND(C, NAME="fp_finalize")
    INTEGER(C_INT) :: ierr
    ! L-2 stub: no explicit deallocation. fpcomm uses module ALLOCATABLE arrays
    ! that are freed on process exit. L-4 will revisit if shared-lib reuse needs
    ! a clean fp_deallocate call.
    g_initialized = .FALSE.
    ierr = FP_OK
  END FUNCTION fp_finalize_c

END MODULE fp_api
```

注: `fp_deallocate` の呼び出しは L-2 では入れない（既存 fp バイナリ動作不変を最優先）。L-4 で `libfpapi.so` の reuse シナリオが固まってから判断。

**USE chain の事前確認（重要）:**

`fp_api.f90` が `USE fpprep, ONLY: fp_prep` を行うと、`fpprep.f90` の以下の transitive USE が芋づる式に解決される必要がある:

```
fpprep
  ├── fpcomm, fpinit, fpsave, fpcoef, fpcalw, fpbounce
  ├── equnit, fpmpi, libmpi
  ├── fpcaleind     ← MODULE は fp/fpcale.f90 内に定義（独立 .f90 ではない）
  ├── fpdisrupt, fplib, libmtx, plprof
  └── fpbroadcast, fpwrin, fpwmin, fpreadeg
```

ファイル名は `fpcale.f90` だが、その中で `MODULE fpcaleind` が定義されている。`grep -n "MODULE fpcaleind" fp/fpcale.f90` で確認可能。

事前検証コマンド:
```bash
grep -nE "^[[:space:]]+USE[[:space:]]+" /home/k-yoshimi/program/task/fp/fpprep.f90
grep -n "MODULE fpcaleind" /home/k-yoshimi/program/task/fp/*.f90
```
Expected: `fpcale.f90:6:      MODULE fpcaleind` が見つかる。

**フォールバック方針:** もし `fp_api.f90` の compile で transitive USE 解決に失敗した場合（例: `mod_pic` ディレクトリの `.mod` 不整合）、Step 3 では `fp_run_c` を一時的に `ierr = FP_ERR_NOT_INIT` を返す stub に縮退し、L-3 の `fp_param_registry.f90` 実装と並行して fp_run の実体実装を後追いする。「ビルドが通る最小構成」を優先（受け入れ基準: `make fp_api_check` が 0 終了するだけ）。

- [ ] **Step 3: 単独コンパイル確認**

L-2 では `fp_api.o` を `OBJS` に含めずビルドだけ確認したい。手動で:

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make obj/fpcomm.o obj/fpinit.o obj/fpparm.o obj/fpprep.o obj/fploop.o 2>&1 | tail -3
gfortran -c fp_state.f90 -o obj/fp_state.o -Imod -Jmod
gfortran -c fp_api.f90  -o obj/fp_api.o   -Imod -I../pl/mod -I../eq/mod -I../ob/mod -Jmod
ls -la obj/fp_api.o
```
Expected: エラーなしで `obj/fp_api.o` 生成。USE chain（pl_init, eq_init, ob_init, fp_init, fp_prep, fp_loop, fpcomm）が解決できる必要がある。

USE できないモジュール（例: `equnit`）がある場合: `fp/Makefile` の `MODINCLUDE` を確認し、`-I../eq/mod` を追加。`fpprep` が `fpcaleind`（`fpcale.f90` 内）を transitive に USE するため、`fp/fpcale.f90` も先にビルドされている必要がある（`make` の通常ターゲットで自動的に解決される）。

---

## Task 4: `fp/fp_api.h` を作成

**Files:**
- Create: `fp/fp_api.h`

- [ ] **Step 1: ファイル作成**

作成: `fp/fp_api.h`

```c
#ifndef FP_API_H
#define FP_API_H

/* TASK/FP library C API (Phase L-2 foundation).
 *
 * All functions return an error code (0 = OK).
 * Profile arrays are fixed-size for ABI simplicity; runtime nrmax/nsamax
 * are stored in the struct and must be <= FP_MAX_NRMAX/NSAMAX.
 */

#define FP_MAX_NRMAX  100
#define FP_MAX_NSAMAX 8

/* Error codes (must match fp_api.f90 PARAMETERs) */
#define FP_OK            0
#define FP_ERR_INVALID   1
#define FP_ERR_NOT_INIT  2
#define FP_ERR_CALC_FAIL 3
#define FP_ERR_OVERFLOW  4

typedef struct {
    int    nrmax;
    int    nsamax;
    int    npmax;
    int    nthmax;
    int    ntg2;
    double timefp;
    /* Note: Fortran lays these out as [FP_MAX_NRMAX][FP_MAX_NSAMAX] in
     * column-major; from C use [nsa-1][nr-1] indexing on the flattened
     * pointer if you copy out. Valid range: [1..nrmax, 1..nsamax]. */
    double RNT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RWT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RTT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RJT [FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RPCT[FP_MAX_NSAMAX][FP_MAX_NRMAX];
    double RPWT[FP_MAX_NSAMAX][FP_MAX_NRMAX];
} fp_state_t;

#ifdef __cplusplus
extern "C" {
#endif

int fp_init(void);
int fp_run(int ntmax);
int fp_set_param(const char* name, double value);
int fp_get_state(fp_state_t* state);
int fp_finalize(void);

#ifdef __cplusplus
}
#endif

#endif /* FP_API_H */
```

注: Fortran の `(FP_MAX_NRMAX, FP_MAX_NSAMAX)` 配列を C で表現する場合、column-major のため C 側では `[FP_MAX_NSAMAX][FP_MAX_NRMAX]` の順で見える（先頭次元が「速い」）。ヘッダのコメントに明記。

---

## Task 5: `fp/Makefile` に `SRCS_API` を追加（compile-only target）

**Files:**
- Modify: `fp/Makefile`

L-2 では `fp_api.o` は `fp` バイナリのリンクには含めない。だが Makefile レベルで「ビルド可能な target がある」ことを保証する。

- [ ] **Step 1: `SRCS_API` 変数と `fp_api_check` ターゲットを追加**

L-1 で導入した `SRCS_CORE / SRCS_GRAPHICS / SRCS_MENU` ブロックの直後に追記:

```makefile
# --- C ABI sources (used by libfpapi.so in L-4; not linked into `fp` binary) ---
SRCS_API = fp_state.f90 fp_api.f90

OBJS_API = $(addprefix $(OBJDIR)/, $(SRCS_API:.f90=.o))

# fp_api_check: compile-only sanity target for L-2 (no link).
fp_api_check: $(OBJS) $(OBJS_API)
	@echo "fp_api compiled OK (L-2 stub)"
```

加えて Makefile の依存記述ブロック（136 行目の `$(OBJDIR)/fpwrite.o` のあたり）に:

```makefile
$(OBJDIR)/fp_state.o : fp_state.f90
$(OBJDIR)/fp_api.o   : fp_api.f90 fp_state.f90 fpcomm.f90 fpinit.f90 \
                       fpprep.f90 fploop.f90
```

- [ ] **Step 2: `fp_api_check` ターゲットを実行**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make fp_api_check 2>&1 | tail -10
```
Expected: 既存 `OBJS` と `OBJS_API` がビルドされ、最後に `fp_api compiled OK (L-2 stub)` が表示される。エラーなし。

USE chain で `equnit, plinit, obinit` が見つからない場合、`fp/Makefile` の MODINCLUDE に `-I../eq/mod -I../pl/mod -I../ob/mod` が既にあることを確認（21-24 行目）。

- [ ] **Step 3: `fp` 通常ビルドが影響を受けないことを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make veryclean
make 2>&1 | tail -5
ls -la fp
```
Expected: `fp` バイナリ生成、エラーなし。`OBJS_API` は `fp` のリンクには使われないため通常 `make` には影響しない。

- [ ] **Step 4: 回帰 3 ケース PASS（数値不変）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 全 PASS。

---

## Task 6: C ヘッダの compile-only smoke test

**Files:**
- Create: `fp/tests/c_abi/test_abi_smoke.c`
- Create: `fp/tests/c_abi/Makefile`

L-2 ではリンクは確認しない（L-4 で行う）。ヘッダが C コードでパース可能であることだけ検証する。

- [ ] **Step 1: Smoke テスト C ファイル**

作成: `fp/tests/c_abi/test_abi_smoke.c`

```c
/* fp/tests/c_abi/test_abi_smoke.c
 *
 * Phase L-2 smoke test: just verify fp_api.h parses cleanly and
 * the function prototypes / struct layout look right.
 * No linking is attempted here; that is L-4's job.
 */

#include <stdio.h>
#include <stddef.h>
#include "fp_api.h"

int main(void) {
    fp_state_t s;
    /* zero init */
    s.nrmax = 0;
    s.nsamax = 0;
    s.timefp = 0.0;

    /* ABI sanity: profile fields must be 6 distinct arrays. */
    (void)&s.RNT;
    (void)&s.RWT;
    (void)&s.RTT;
    (void)&s.RJT;
    (void)&s.RPCT;
    (void)&s.RPWT;

    /* Function pointer compatibility check (no call). */
    int (*pf_init)(void)                              = fp_init;
    int (*pf_run)(int)                                = fp_run;
    int (*pf_set)(const char*, double)                = fp_set_param;
    int (*pf_get)(fp_state_t*)                        = fp_get_state;
    int (*pf_fin)(void)                               = fp_finalize;
    (void)pf_init; (void)pf_run; (void)pf_set; (void)pf_get; (void)pf_fin;

    printf("fp_api.h parsed OK; sizeof(fp_state_t) = %zu bytes\n",
           sizeof(fp_state_t));
    return 0;
}
```

- [ ] **Step 2: テスト用 Makefile**

作成: `fp/tests/c_abi/Makefile`

```makefile
# Phase L-2 smoke: compile-only check that fp_api.h parses with gcc.
# Does NOT attempt to link; that is L-4 (libfpapi.so).

CC      ?= gcc
CFLAGS  ?= -Wall -Wextra -O0

test_abi_smoke.o: test_abi_smoke.c ../../fp_api.h
	$(CC) $(CFLAGS) -I../.. -c test_abi_smoke.c -o test_abi_smoke.o

.PHONY: check
check: test_abi_smoke.o
	@echo "L-2 smoke OK: fp_api.h compiles under gcc"

.PHONY: clean
clean:
	-rm -f test_abi_smoke.o
```

- [ ] **Step 3: 走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task/fp/tests/c_abi
make check 2>&1
```
Expected: `L-2 smoke OK: fp_api.h compiles under gcc`。

警告（特に `-Wunused-function`）が出ても一旦許容。エラーなしで `.o` が生成されれば OK。

---

## Task 7: 回帰テストへの組み込み（compile-only）

**Files:**
- Modify: `test_run/test_definitions.conf` — 任意。compile-only テストは run_tests.sh の現フレームワークに馴染まないため、**README に手順を残すだけ** とする。

- [ ] **Step 1: `test_run/README.md` の FP セクション末尾に追記**

```markdown
### FP C ABI smoke (Phase L-2)

To verify the C header & 5-function ABI compile cleanly (no link):

    cd fp && make fp_api_check
    cd fp/tests/c_abi && make check

These are run manually until L-4 wires `libfpapi.so` into the test runner.
```

- [ ] **Step 2: コミット（全変更まとめて）**

Run:
```bash
cd /home/k-yoshimi/program/task
git add fp/fp_state.f90 fp/fp_api.f90 fp/fp_api.h fp/Makefile \
        fp/tests/c_abi/test_abi_smoke.c fp/tests/c_abi/Makefile \
        test_run/README.md
git commit -m "feat(fp): add C ABI foundation (fp_state, fp_api stub, fp_api.h)"
```

---

## 受け入れ基準

- [ ] `fp/fp_state.f90`, `fp/fp_api.f90`, `fp/fp_api.h` が存在し、`make fp_api_check` で 0 終了する。
- [ ] `cd fp/tests/c_abi && make check` で 0 終了する。
- [ ] `fp` 通常ビルド（`make veryclean && make`）が成功し、L-0 ベースライン（`fp_iter01/jt60/dt1`）と bit-exact 一致する。
- [ ] TR 既存テストが回帰しない。
- [ ] `fp_set_param` は L-2 では常に `1` を返す stub であり、後続 L-3 で実装される旨が `fp_api.f90` のコメントに明記されている。

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| `fp_api.f90` の USE chain（`equnit, obinit, plinit, fpprep, fploop`）で循環 / 未解決モジュール | `fp_api.f90` に必要最低限の USE だけ残し、`fp_run_c` の中身を一時的に `ierr=FP_ERR_NOT_INIT` の stub にして「ビルド通過 + L-3 で本実装」へ縮退 |
| `fpprep` 経由で USE される `fpcaleind` の `.mod` が見つからない | `fpcaleind` MODULE は `fp/fpcale.f90` 内に定義されている（独立 .f90 ではない）。通常 `make` で `fp/fpcale.f90` 由来の `fpcale.o` + `fpcaleind.mod` が `obj/` / `mod/` に生成されるはず。先に `make obj/fpcale.o` を実行してから fp_api をビルド |
| `fp_state_c` の固定サイズが大きすぎてスタックあふれを心配される | `FP_MAX_NRMAX = 50` に減らす（実入力で十分）|
| `gcc -c` で `fp_api.h` の `[FP_MAX_NSAMAX][FP_MAX_NRMAX]` レイアウトが C99 規約と齟齬 | C99 配列宣言に変更、または `double *RNT;` ポインタ + サイズパラメータの外部 API に切り替えて L-3 で再評価 |
| `fp_api_check` を Makefile の `all:` ターゲットに含めるべきか | L-2 では含めない（独立ターゲット）。L-4 で `all: libs fp libfpapi.so` に含める |

## 依存

- 上流: L-0 (回帰基盤)、L-1 (Makefile SRCS 分離) が両方マージ済み
- 後続: L-3（`fp_param_registry.f90` で `fp_set_param` を本実装）
