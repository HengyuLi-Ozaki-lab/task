# WRX Library-ization Phase L-2: C ABI Foundation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** WRX を `bind(c)` 経由で外部から呼べる C ABI を **Fortran 側 stub と C ヘッダ** として導入する。実装は本フェーズでは "init / finalize / get_state の最小スケルトン"（`wrx_run` と `wrx_set_param` は L-3 で完成）。本フェーズの完了基準は「Fortran モジュールがビルド可能で、`bind(c)` 5 関数のシンボルが `nm` で見える」こと。

**Architecture:** `wrx/wrx_state.f90`（C 互換構造体 `wrx_state_c` 定義）、`wrx/wrx_api.f90`（5 関数の `bind(c)` stub、`wrx_init/wrx_finalize` のみ実体実装、`wrx_run/wrx_set_param/wrx_get_state` は ierr=0 でスケルトン返し）、`wrx/wrx_api.h`（C ヘッダ）の 3 ファイル新規。**既存 Fortran ファイルには触らない**。

**Critical: シンボル衝突回避** — `wr/` モジュールも将来同じパターンで `wr_api.f90` を作る可能性があるため、本 wrx 用 ABI 関数は **必ず `wrx_` プレフィックス**（`wr_` 不可）。`bind(c, name="wrx_init")` の name 引数を明示し、Fortran 側関数名と C シンボル名を一致させる。

**Tech Stack:** Fortran 90 + ISO_C_BINDING、gfortran、GNU Make。Python ラッパや shared library は L-4/L-5 の責務、本フェーズでは扱わない。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §4.1, §4.2, §4.3 を wrx に翻案。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wrx/wrx_state.f90` | 新規 | `MODULE wrx_state` に `TYPE, BIND(C) :: wrx_state_c` を定義（C 互換 POD struct） |
| `wrx/wrx_api.f90` | 新規 | `MODULE wrx_api` に 5 関数 `wrx_init/wrx_run/wrx_get_state/wrx_set_param/wrx_finalize` の `bind(c)` 宣言。L-2 では init/finalize のみ実装 |
| `wrx/wrx_api.h` | 新規 | C ヘッダ。`wrx_state_t` typedef + 5 関数の extern 宣言 |
| `wrx/Makefile` | 修正 | `SRCS_CORE` に `wrx_state.f90` と `wrx_api.f90` を追加（順序: state → api） |

---

## Task 1: ブランチ準備と現状確認

- [ ] **Step 1: ブランチ作成**
```bash
cd /home/k-yoshimi/program/task-private
git checkout develop && git pull
git checkout -b feature/wrx-library-L2-c-abi-foundation
```

- [ ] **Step 2: L-0/L-1 完了状況確認**
```bash
ls /home/k-yoshimi/program/task-private/wrx/wrxregress.f90
grep -n "SRCS_CORE\|SRCS_GRAPHICS\|SRCS_MENU" /home/k-yoshimi/program/task-private/wrx/Makefile
```
Expected: L-0 の dump file が存在、L-1 の SRCS 3 分割が出来ている。

---

## Task 2: `wrx_state.f90` 新規作成

**Files:**
- Create: `wrx/wrx_state.f90`

- [ ] **Step 1: ファイル作成**

Create: `wrx/wrx_state.f90`

```fortran
! wrx_state.f90
!
! C-interoperable state struct for the WRX library API (Phase L-2).
!
! Upper bounds:
!   WRX_MAX_NRAYMAX = 100  (matches NRAYM in wrcomm_parm)
!   WRX_MAX_NSAMAX  = 8    (matches NSM upper bound used by wr/dp)
!
! Actual runtime sizes are in nraymax/nsamax fields of the struct
! and must be <= these compile-time bounds.

MODULE wrx_state
  USE, INTRINSIC :: ISO_C_BINDING
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wrx_state_c, WRX_MAX_NRAYMAX, WRX_MAX_NSAMAX

  INTEGER(C_INT), PARAMETER :: WRX_MAX_NRAYMAX = 100
  INTEGER(C_INT), PARAMETER :: WRX_MAX_NSAMAX  = 8

  TYPE, BIND(C) :: wrx_state_c
     INTEGER(C_INT) :: nraymax
     INTEGER(C_INT) :: nstpmax
     INTEGER(C_INT) :: nsamax
     INTEGER(C_INT) :: nsmax
     INTEGER(C_INT) :: modelg
     INTEGER(C_INT) :: mdlwrq
     REAL(C_DOUBLE) :: pwr_tot
     INTEGER(C_INT) :: nstpmax_nray(WRX_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwr_nray(WRX_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pwr_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pwr_nsa_nray(WRX_MAX_NSAMAX, WRX_MAX_NRAYMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rs_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pwrmax_rs_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pos_pwrmax_rl_nsa(WRX_MAX_NSAMAX)
     REAL(C_DOUBLE) :: pwrmax_rl_nsa(WRX_MAX_NSAMAX)
  END TYPE wrx_state_c
END MODULE wrx_state
```

---

## Task 3: `wrx_api.f90` stub 作成

**Files:**
- Create: `wrx/wrx_api.f90`

- [ ] **Step 1: ファイル作成（init/finalize は実装、他 3 関数は L-3 用 stub）**

Create: `wrx/wrx_api.f90`

```fortran
! wrx_api.f90
!
! C ABI for WRX library (Phase L-2: foundation).
!
! Public functions (all bind(c)):
!   wrx_init       - allocate WRX state, run wr_init/dp_init/pl_init/eq_init
!   wrx_run        - (L-3 stub) execute ray tracing
!   wrx_set_param  - (L-3 stub) set namelist parameter by name
!   wrx_get_state  - (L-3 stub) copy WRX state into struct
!   wrx_finalize   - deallocate WRX state
!
! Error codes:
!   0 = OK
!   1 = invalid parameter
!   2 = not initialized
!   3 = calculation failed
!   4 = not implemented yet (L-2 stubs return this for run/set_param/get_state)

MODULE wrx_api
  USE, INTRINSIC :: ISO_C_BINDING
  USE wrx_state, ONLY: wrx_state_c
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wrx_init, wrx_run, wrx_get_state, wrx_set_param, wrx_finalize

  LOGICAL, SAVE :: g_initialized = .FALSE.

CONTAINS

  FUNCTION wrx_init() BIND(C, NAME="wrx_init") RESULT(ierr)
    USE plinit, ONLY: pl_init
    USE dpinit, ONLY: dp_init
    USE wrinit, ONLY: wr_init
    INTEGER(C_INT) :: ierr
    EXTERNAL EQINIT
    ierr = 0
    IF (g_initialized) THEN
       ierr = 0
       RETURN
    END IF
    CALL pl_init
    CALL EQINIT
    CALL dp_init
    CALL wr_init
    g_initialized = .TRUE.
  END FUNCTION wrx_init

  FUNCTION wrx_run(nstpmax_arg) BIND(C, NAME="wrx_run") RESULT(ierr)
    INTEGER(C_INT), VALUE, INTENT(IN) :: nstpmax_arg
    INTEGER(C_INT) :: ierr
    ! L-2 stub: return "not implemented" until L-3 wires wr_prep/wr_setup/wr_exec.
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF
    ierr = 4   ! not implemented yet
  END FUNCTION wrx_run

  FUNCTION wrx_set_param(name, value) BIND(C, NAME="wrx_set_param") RESULT(ierr)
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    ! L-2 stub: L-3 wires this into wrx_param_registry.
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF
    ierr = 4   ! not implemented yet
  END FUNCTION wrx_set_param

  FUNCTION wrx_get_state(state) BIND(C, NAME="wrx_get_state") RESULT(ierr)
    TYPE(wrx_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    ! L-2 stub: zero-fill struct so callers can detect "not yet populated".
    state%nraymax = 0
    state%nstpmax = 0
    state%nsamax  = 0
    state%nsmax   = 0
    state%modelg  = 0
    state%mdlwrq  = 0
    state%pwr_tot = 0.0_C_DOUBLE
    state%nstpmax_nray = 0
    state%pwr_nray     = 0.0_C_DOUBLE
    state%pwr_nsa      = 0.0_C_DOUBLE
    state%pwr_nsa_nray = 0.0_C_DOUBLE
    state%pos_pwrmax_rs_nsa = 0.0_C_DOUBLE
    state%pwrmax_rs_nsa     = 0.0_C_DOUBLE
    state%pos_pwrmax_rl_nsa = 0.0_C_DOUBLE
    state%pwrmax_rl_nsa     = 0.0_C_DOUBLE
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF
    ierr = 4   ! L-3 will populate from wrcomm
  END FUNCTION wrx_get_state

  FUNCTION wrx_finalize() BIND(C, NAME="wrx_finalize") RESULT(ierr)
    USE wrcomm, ONLY: wr_deallocate
    INTEGER(C_INT) :: ierr
    ierr = 0
    IF (.NOT. g_initialized) RETURN
    ! Defensive: only call deallocate if WRX was actually run (allocations done).
    ! In L-2 stub mode wr_allocate is never called, so wr_deallocate may fail.
    ! Wrap in BLOCK with no-op to keep ABI clean.
    g_initialized = .FALSE.
  END FUNCTION wrx_finalize

END MODULE wrx_api
```

注: L-2 では `wr_deallocate` は実際には呼ばない（`wr_allocate` も呼んでいないため）。L-3 で `wrx_run` が `wr_allocate` を呼ぶようになったら `wrx_finalize` で `wr_deallocate` を有効化。

---

## Task 4: C ヘッダ `wrx_api.h` 作成

**Files:**
- Create: `wrx/wrx_api.h`

- [ ] **Step 1: ファイル作成**

Create: `wrx/wrx_api.h`

```c
#ifndef WRX_API_H
#define WRX_API_H

/* TASK/WRX library C ABI (Phase L-2 foundation).
 *
 * Upper bounds for fixed-size struct:
 *   WRX_MAX_NRAYMAX = 100  (matches NRAYM in wrcomm_parm)
 *   WRX_MAX_NSAMAX  = 8    (matches NSM in pl/plcomm)
 * Actual runtime nraymax/nsamax must be <= these.
 */

#define WRX_MAX_NRAYMAX 100
#define WRX_MAX_NSAMAX  8

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int    nraymax;
    int    nstpmax;
    int    nsamax;
    int    nsmax;
    int    modelg;
    int    mdlwrq;
    double pwr_tot;
    int    nstpmax_nray[WRX_MAX_NRAYMAX];
    double pwr_nray[WRX_MAX_NRAYMAX];
    double pwr_nsa[WRX_MAX_NSAMAX];
    double pwr_nsa_nray[WRX_MAX_NRAYMAX][WRX_MAX_NSAMAX]; /* Fortran column-major */
    double pos_pwrmax_rs_nsa[WRX_MAX_NSAMAX];
    double pwrmax_rs_nsa[WRX_MAX_NSAMAX];
    double pos_pwrmax_rl_nsa[WRX_MAX_NSAMAX];
    double pwrmax_rl_nsa[WRX_MAX_NSAMAX];
} wrx_state_t;

/* Error codes:
 *   0 = OK, 1 = invalid param, 2 = not initialized,
 *   3 = calculation failed, 4 = not implemented yet
 */
int wrx_init(void);
int wrx_run(int nstpmax);
int wrx_set_param(const char* name, double value);
int wrx_get_state(wrx_state_t* state);
int wrx_finalize(void);

#ifdef __cplusplus
}
#endif

#endif /* WRX_API_H */
```

注: 2 次元配列のメモリレイアウトは Fortran column-major。C 側で `state.pwr_nsa_nray[nray][nsa]` でアクセスすることに注意（Fortran `(nsa, nray)` と C `[nray][nsa]` が同じメモリ）。

---

## Task 5: Makefile に SRCS 追加

**Files:**
- Modify: `wrx/Makefile`

- [ ] **Step 1: SRCS_CORE に追加**

`SRCS_CORE` の末尾を以下に変更（`wrxregress.f90` の後ろに追加）:
```make
SRCS_CORE = wrcomm.f90 wrinit.f90 wrparm.f90 wrprep.f90 wrview.f90 \
            wrsub.f90 \
            wrsetup.f90 wrcalpwr.f90 wrfdrv.f90 wroxb.f90 \
            wrexecr.f90 wrexecb.f90 \
            wrexec.f90 \
            wrfile.f90 \
            wrxregress.f90 \
            wrx_state.f90 wrx_api.f90
```

- [ ] **Step 2: 依存セクションに追記**

Makefile 末尾の依存セクションに追加:
```make
$(OBJDIR)/wrx_state.o: wrx_state.f90
$(OBJDIR)/wrx_api.o:   wrx_api.f90 wrx_state.f90 $(WRCOMM) \
                       ../pl/plinit.f90 ../dp/dpinit.f90 wrinit.f90
```

---

## Task 6: ビルドと nm でシンボル確認

- [ ] **Step 1: clean & rebuild**
```bash
cd /home/k-yoshimi/program/task-private/wrx
make veryclean
make 2>&1 | tail -15
ls -la wr libwr.a
```
Expected: `libwr.a` と `wr` が生成。`wrx_state.f90`, `wrx_api.f90` のコンパイル成功。

- [ ] **Step 2: bind(c) シンボル確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/wrx
nm libwr.a 2>/dev/null | grep -E " T (wrx_init|wrx_run|wrx_get_state|wrx_set_param|wrx_finalize)$"
```
Expected: 5 行表示（5 つの `wrx_*` シンボルが Text セクションに存在）。

- [ ] **Step 3: シンボル衝突なし確認**

Run:
```bash
nm libwr.a 2>/dev/null | grep -E " T wr_(init|run|get_state|set_param|finalize)$"
```
Expected: マッチなし（誤って `wr_` プレフィックスのシンボルを公開していないこと）。

---

## Task 7: 既存数値結果が L-0 baseline と一致することを確認

- [ ] **Step 1: 全 WRX baseline テスト**
```bash
cd /home/k-yoshimi/program/task-private/test_run
rm -rf test_output/wrx_*
./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo
```
Expected: 3 ケースとも PASS。L-2 で stub 追加したのみで実行パスは触っていない。

- [ ] **Step 2: コミット**
```bash
cd /home/k-yoshimi/program/task-private
git add wrx/wrx_state.f90 wrx/wrx_api.f90 wrx/wrx_api.h wrx/Makefile
git commit -m "feat(wrx): add C ABI foundation (wrx_state.f90, wrx_api.f90 stubs, wrx_api.h)"
```

---

## Verification Checklist

- [ ] `wrx/wrx_state.f90` の `wrx_state_c` 構造体が `BIND(C)` 付きで定義されている
- [ ] `wrx/wrx_api.f90` の 5 関数すべてが `BIND(C, NAME="wrx_*")` 宣言で公開されている
- [ ] `wrx/wrx_api.h` の C 構造体・関数宣言と Fortran 側が一致
- [ ] `nm libwr.a | grep wrx_` で 5 シンボル全部見える
- [ ] 既存 `wrx/wr` バイナリが build 成功
- [ ] WRX 3 baseline が PASS（数値変化なし）
- [ ] `nm` 結果に `wr_init`, `wr_run` 等の wr_-prefix シンボル流出なし

## Dependencies

- L-1 完了（Makefile SRCS 3 分割済み）

## Fallback

- `wrx_init` で `pl_init`/`dp_init`/`wr_init`/`EQINIT` の呼出順が wrx の従来 main (`wrmain.f90`) と異なると初期化失敗。`wrmain.f90` の順序をそのままコピーすれば良い（コピー済み）。
- `wr_deallocate` を呼ぶと未 allocate 状態でエラー → L-2 では呼ばない（コメントで明示）。L-3 で `wrx_run` を実装した時点で再有効化。

## Out of Scope

- `wrx_run`, `wrx_set_param`, `wrx_get_state` の実体実装（L-3）
- `libwrxapi.so` build（L-4）
- Python ラッパ（L-5）
- mtx_initialize/mtx_finalize の扱い（L-3 で検討、現状は wrmain でのみ呼ぶため wrx_init では省略）
