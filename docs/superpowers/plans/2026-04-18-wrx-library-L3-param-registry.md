# WRX Library-ization Phase L-3: Parameter Registry + Run/GetState 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2 stub だった `wrx_run`、`wrx_set_param`、`wrx_get_state` を実装する。namelist 由来の主要パラメータを「名前 → wrcomm 変数」の **手書き SELECT CASE テーブル** で受け取れる `wrx_param_registry.f90` を新設し、`wrx_run` から `wr_prep → wr_allocate → wr_setup → wr_exec` を呼び出す。`wrx_get_state` は `wrcomm` の値を `wrx_state_c` 構造体にコピー。

**Architecture:** 新規 `wrx/wrx_param_registry.f90` に `FUNCTION wrx_param_set(name, value) RESULT(ierr)` を 1 つだけ public で持つ。SELECT CASE で wrcomm/plcomm/dpcomm/wrcomm_parm の各変数に書き込む。配列パラメータは `"PN[1]"` 形式 (1-origin)。`wrx_api.f90` の 3 関数を更新し、`wrx_param_registry` を呼び、`wrcomm.wr_allocate` 経由で計算実行。**新規ファイルは 1 つ、既存 `wrx_api.f90` のみ修正、wrcomm/wrexec 等の既存ファイルは触らない**。

**Tech Stack:** Fortran 90 + ISO_C_BINDING、SELECT CASE、`TRIM()` ベース文字列マッチ。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §5（パラメータテーブル機構）を wrx に翻案。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wrx/wrx_param_registry.f90` | 新規 | `MODULE wrx_param_registry` に `wrx_param_set(name, value)` を実装。SELECT CASE テーブルで wrcomm/plcomm/dpcomm 変数に書き込み。配列は `parse_array_subscript` ヘルパで `"PN[1]"` を base+idx に分解 |
| `wrx/wrx_api.f90` | 修正 | `wrx_set_param` を `wrx_param_set` 呼出に置換、`wrx_run` を `wr_prep/wr_allocate/wr_setup/wr_exec` 呼出に置換、`wrx_get_state` を wrcomm 値コピーに置換 |
| `wrx/Makefile` | 修正 | `SRCS_CORE` に `wrx_param_registry.f90` を追加（順序: state → registry → api） |

---

## Task 1: ブランチ準備

- [ ] **Step 1: ブランチ作成**
```bash
cd /home/k-yoshimi/program/task-private
git checkout develop && git pull
git checkout -b feature/wrx-library-L3-param-registry
```

- [ ] **Step 2: L-2 完了状況確認**
```bash
nm /home/k-yoshimi/program/task-private/wrx/libwr.a 2>/dev/null | grep -E " T wrx_" | head
```
Expected: `wrx_init`, `wrx_run`, ... 5 シンボルが見える。

---

## Task 2: 登録パラメータの最終リスト確定

- [ ] **Step 1: namelist パラメータ一覧を確認**
```bash
grep -A 30 "NAMELIST /WR/" /home/k-yoshimi/program/task-private/wrx/wrparm.f90 | head -50
```
Expected: 大量のパラメータが見える。L-3 では最初に **以下の最小セット (~30 個)** だけ登録する:

**Geometry (plcomm):** `RR, RA, RB, RKAP, RDLT, BB, Q0, QA, RIP`
**Plasma profiles (plcomm):** `NSMAX`, `PA[i]`, `PZ[i]`, `PN[i]`, `PNS[i]`, `PTPR[i]`, `PTPP[i]`, `PTS[i]`
**Profile shape (plcomm):** `PROFN1, PROFN2, PROFT1, PROFT2, PROFJ`
**WRX control (wrcomm_parm):** `NRAYMAX, NSTPMAX, NRSMAX, NRLMAX, LMAXNW, MDLWRI, MDLWRG, MDLWRP, MDLWRQ, MDLWRW`
**Ray init (wrcomm_parm, NRAYM array):** `RFIN[i], RPIN[i], ZPIN[i], PHIIN[i], ANGTIN[i], ANGPIN[i], RNPHIN[i], RNZIN[i], MODEWIN[i], UUIN[i], RBRADAIN[i], RBRADBIN[i]`
**Ray control:** `SMAX, DELS, UUMIN, EPSRAY, DELRAY, DELDER, DELKR, EPSNW, EPSD0, pne_threshold, bdr_threshold`
**Mode (wrcomm_parm):** `mode_beam, mode_wline, mode_fig, model_fdrv, model_fdrv_ds`
**dp/pl integration:** `MODELG, MODELN, MODELQ, NSAMAX_WR`
**dp species:** `MODELP[i], MODELV[i], NCMIN[i], NCMAX[i]`

これらを `SELECT CASE` のラベルとして 1 つずつ記述。L-3 では **エラー時 ierr=1 を返すのみ**で OK; パラメータ追加が必要になれば後続 PR で追加（メンテ容易）。

---

## Task 3: `wrx_param_registry.f90` 新規作成

**Files:**
- Create: `wrx/wrx_param_registry.f90`

- [ ] **Step 1: ファイル作成**

Create: `wrx/wrx_param_registry.f90`

```fortran
! wrx_param_registry.f90
!
! Manual SELECT CASE table mapping namelist parameter names to wrcomm /
! plcomm / dpcomm variables. New parameters: add one CASE clause.
!
! Array indexing: "PN[1]" -> PN(1) (1-origin Fortran convention).

MODULE wrx_param_registry
  USE wrcomm   ! wrcomm_parm + wrcomm + plcomm + dpcomm (via USE chain)
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: wrx_param_set

CONTAINS

  FUNCTION wrx_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind), INTENT(IN) :: value
    INTEGER :: ierr
    CHARACTER(LEN=32) :: base
    INTEGER :: idx

    ierr = 0
    CALL parse_array_subscript(name, base, idx)

    SELECT CASE (TRIM(base))
    ! --- Geometry ---
    CASE ("RR");    RR    = value
    CASE ("RA");    RA    = value
    CASE ("RB");    RB    = value
    CASE ("RKAP");  RKAP  = value
    CASE ("RDLT");  RDLT  = value
    CASE ("BB");    BB    = value
    CASE ("Q0");    Q0    = value
    CASE ("QA");    QA    = value
    CASE ("RIP");   RIP   = value

    ! --- Plasma scalars ---
    CASE ("NSMAX");   NSMAX   = INT(value)
    CASE ("PROFJ");   PROFJ   = value
    CASE ("PROFN1");  PROFN1  = value
    CASE ("PROFN2");  PROFN2  = value
    CASE ("PROFT1");  PROFT1  = value
    CASE ("PROFT2");  PROFT2  = value

    ! --- Plasma arrays (1-origin) ---
    CASE ("PA");    PA(idx)   = value
    CASE ("PZ");    PZ(idx)   = value
    CASE ("PN");    PN(idx)   = value
    CASE ("PNS");   PNS(idx)  = value
    CASE ("PTPR");  PTPR(idx) = value
    CASE ("PTPP");  PTPP(idx) = value
    CASE ("PTS");   PTS(idx)  = value

    ! --- pl/dp integration ---
    CASE ("MODELG"); MODELG  = INT(value)
    CASE ("MODELN"); MODELN  = INT(value)
    CASE ("MODELQ"); MODELQ  = INT(value)
    CASE ("NSAMAX_WR"); NSAMAX_WR = INT(value)
    CASE ("MODELP"); MODELP(idx) = INT(value)
    CASE ("MODELV"); MODELV(idx) = INT(value)
    CASE ("NCMIN");  NCMIN(idx)  = INT(value)
    CASE ("NCMAX");  NCMAX(idx)  = INT(value)

    ! --- WRX control scalars ---
    CASE ("NRAYMAX"); NRAYMAX = INT(value)
    CASE ("NSTPMAX"); NSTPMAX = INT(value)
    CASE ("NRSMAX");  NRSMAX  = INT(value)
    CASE ("NRLMAX");  NRLMAX  = INT(value)
    CASE ("LMAXNW");  LMAXNW  = INT(value)
    CASE ("MDLWRI");  MDLWRI  = INT(value)
    CASE ("MDLWRG");  MDLWRG  = INT(value)
    CASE ("MDLWRP");  MDLWRP  = INT(value)
    CASE ("MDLWRQ");  MDLWRQ  = INT(value)
    CASE ("MDLWRW");  MDLWRW  = INT(value)

    ! --- Ray init arrays (NRAYM = 100 max) ---
    CASE ("RFIN");      RFIN(idx)      = value
    CASE ("RPIN");      RPIN(idx)      = value
    CASE ("ZPIN");      ZPIN(idx)      = value
    CASE ("PHIIN");     PHIIN(idx)     = value
    CASE ("ANGTIN");    ANGTIN(idx)    = value
    CASE ("ANGPIN");    ANGPIN(idx)    = value
    CASE ("RNPHIN");    RNPHIN(idx)    = value
    CASE ("RNZIN");     RNZIN(idx)     = value
    CASE ("MODEWIN");   MODEWIN(idx)   = INT(value)
    CASE ("UUIN");      UUIN(idx)      = value
    CASE ("RBRADAIN");  RBRADAIN(idx)  = value
    CASE ("RBRADBIN");  RBRADBIN(idx)  = value
    CASE ("RCURVAIN");  RCURVAIN(idx)  = value
    CASE ("RCURVBIN");  RCURVBIN(idx)  = value
    CASE ("RNKIN");     RNKIN(idx)     = value

    ! --- Ray control scalars ---
    CASE ("SMAX");           SMAX           = value
    CASE ("DELS");           DELS           = value
    CASE ("UUMIN");          UUMIN          = value
    CASE ("EPSRAY");         EPSRAY         = value
    CASE ("DELRAY");         DELRAY         = value
    CASE ("DELDER");         DELDER         = value
    CASE ("DELKR");          DELKR          = value
    CASE ("EPSNW");          EPSNW          = value
    CASE ("EPSD0");          EPSD0          = value
    CASE ("pne_threshold");  pne_threshold  = value
    CASE ("bdr_threshold");  bdr_threshold  = value

    ! --- Modes ---
    CASE ("mode_beam");      mode_beam      = INT(value)
    CASE ("mode_wline");     mode_wline     = INT(value)
    CASE ("mode_fig");       mode_fig       = INT(value)
    CASE ("model_fdrv");     model_fdrv     = INT(value)
    CASE ("model_fdrv_ds");  model_fdrv_ds  = INT(value)

    CASE DEFAULT
       ierr = 1
    END SELECT
  END FUNCTION wrx_param_set

  SUBROUTINE parse_array_subscript(full_name, base, idx)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx
    INTEGER :: lb, rb, ios

    base = full_name
    idx = 0
    lb = INDEX(full_name, '[')
    IF (lb == 0) RETURN
    rb = INDEX(full_name, ']')
    IF (rb <= lb) RETURN
    base = full_name(1:lb-1)
    READ(full_name(lb+1:rb-1), *, IOSTAT=ios) idx
    IF (ios /= 0) idx = 0
  END SUBROUTINE parse_array_subscript

END MODULE wrx_param_registry
```

注: 一部の変数名（`MODELN`, `MODELQ`, `MODELP`, `MODELV`, `NCMIN`, `NCMAX`, `RIP`, `Q0`, `QA`, `PA`, `PZ`, `PN`, `PNS`, `PTPR`, `PTPP`, `PTS`, `RKAP`, `RDLT`, `RB`, `PROFJ`, `PROFN*`, `PROFT*`）は `plcomm` または `dpcomm_parm` で宣言されており `USE wrcomm` チェーンで間接的に visible。コンパイル失敗があれば `USE plcomm, ONLY: ...` を追加する。

---

## Task 4: `wrx_api.f90` の 3 関数を実装

**Files:**
- Modify: `wrx/wrx_api.f90`

- [ ] **Step 1: `wrx_set_param` 実装**

`wrx_set_param` を以下に置換:
```fortran
  FUNCTION wrx_set_param(name, value) BIND(C, NAME="wrx_set_param") RESULT(ierr)
    USE wrx_param_registry, ONLY: wrx_param_set
    USE wrcomm, ONLY: rkind
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: f_name
    INTEGER :: i
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF
    f_name = ' '
    DO i = 1, LEN(f_name)
       IF (name(i) == C_NULL_CHAR) EXIT
       f_name(i:i) = name(i)
    END DO
    ierr = wrx_param_set(TRIM(f_name), REAL(value, KIND=rkind))
  END FUNCTION wrx_set_param
```

- [ ] **Step 2: `wrx_run` 実装**

`wrx_run` を以下に置換:
```fortran
  FUNCTION wrx_run(nstpmax_arg) BIND(C, NAME="wrx_run") RESULT(ierr)
    USE wrcomm, ONLY: NSTPMAX, wr_allocate
    USE wrprep, ONLY: wr_prep
    USE wrsetup, ONLY: wr_setup
    USE wrexec, ONLY: wr_exec
    INTEGER(C_INT), VALUE, INTENT(IN) :: nstpmax_arg
    INTEGER(C_INT) :: ierr
    INTEGER :: nstat, ierr_local
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF
    IF (nstpmax_arg > 0) NSTPMAX = nstpmax_arg
    CALL wr_prep(ierr_local)
    IF (ierr_local /= 0) THEN
       ierr = 3
       RETURN
    END IF
    CALL wr_allocate
    CALL wr_setup(ierr_local)
    IF (ierr_local /= 0) THEN
       ierr = 3
       RETURN
    END IF
    CALL wr_exec(nstat, ierr_local)
    IF (ierr_local /= 0) THEN
       ierr = 3
       RETURN
    END IF
    ierr = 0
  END FUNCTION wrx_run
```

注: `nstpmax_arg=0` のときは `wrx_set_param("NSTPMAX", ...)` で事前に設定された値を尊重。L-3 では「`wrx_run(0)` で全 ray を 1 回実行」モデル。L-5/L-6 で複数回呼出のセマンティクスを最終決定。

- [ ] **Step 3: `wrx_get_state` 実装**

`wrx_get_state` を以下に置換:
```fortran
  FUNCTION wrx_get_state(state) BIND(C, NAME="wrx_get_state") RESULT(ierr)
    USE wrcomm, ONLY: NRAYMAX, NSTPMAX, NSAMAX_WR, NSMAX, MODELG, MDLWRQ, &
                       pwr_tot, pwr_nray, pwr_nsa, pwr_nsa_nray, &
                       pos_pwrmax_rs_nsa, pwrmax_rs_nsa, &
                       pos_pwrmax_rl_nsa, pwrmax_rl_nsa, NSTPMAX_NRAY
    USE wrx_state, ONLY: WRX_MAX_NRAYMAX, WRX_MAX_NSAMAX
    TYPE(wrx_state_c), INTENT(OUT) :: state
    INTEGER(C_INT) :: ierr
    INTEGER :: nray, nsa, n_r, n_s
    IF (.NOT. g_initialized) THEN
       ierr = 2
       RETURN
    END IF

    n_r = MIN(NRAYMAX, WRX_MAX_NRAYMAX)
    n_s = MIN(NSAMAX_WR, WRX_MAX_NSAMAX)
    IF (NRAYMAX > WRX_MAX_NRAYMAX .OR. NSAMAX_WR > WRX_MAX_NSAMAX) THEN
       ierr = 1   ! exceeds compile-time bound
       RETURN
    END IF

    state%nraymax = NRAYMAX
    state%nstpmax = NSTPMAX
    state%nsamax  = NSAMAX_WR
    state%nsmax   = NSMAX
    state%modelg  = MODELG
    state%mdlwrq  = MDLWRQ
    state%pwr_tot = pwr_tot

    state%nstpmax_nray = 0
    state%pwr_nray     = 0.0_C_DOUBLE
    state%pwr_nsa      = 0.0_C_DOUBLE
    state%pwr_nsa_nray = 0.0_C_DOUBLE
    state%pos_pwrmax_rs_nsa = 0.0_C_DOUBLE
    state%pwrmax_rs_nsa     = 0.0_C_DOUBLE
    state%pos_pwrmax_rl_nsa = 0.0_C_DOUBLE
    state%pwrmax_rl_nsa     = 0.0_C_DOUBLE

    DO nray = 1, n_r
       state%nstpmax_nray(nray) = NSTPMAX_NRAY(nray)
       state%pwr_nray(nray)     = pwr_nray(nray)
    END DO
    DO nsa = 1, n_s
       state%pwr_nsa(nsa)            = pwr_nsa(nsa)
       state%pos_pwrmax_rs_nsa(nsa)  = pos_pwrmax_rs_nsa(nsa)
       state%pwrmax_rs_nsa(nsa)      = pwrmax_rs_nsa(nsa)
       state%pos_pwrmax_rl_nsa(nsa)  = pos_pwrmax_rl_nsa(nsa)
       state%pwrmax_rl_nsa(nsa)      = pwrmax_rl_nsa(nsa)
    END DO
    DO nray = 1, n_r
       DO nsa = 1, n_s
          state%pwr_nsa_nray(nsa, nray) = pwr_nsa_nray(nsa, nray)
       END DO
    END DO

    ierr = 0
  END FUNCTION wrx_get_state
```

- [ ] **Step 4: `wrx_finalize` の `wr_deallocate` を有効化（ALLOCATED ガード付き）**

`wrx_run` を一度も呼ばずに `wrx_finalize` を呼ぶケースが起こり得る（`wrx_init` 直後の `wrx_finalize`、または異常系テストで意図的に skip するケース）。`wr_deallocate` は wrcomm 内部で `DEALLOCATE` を直に並べる素朴実装のため、未 ALLOCATE な配列に対して seg-fault する。`wrx_api` 側で `g_run_called` フラグを導入し、**`wrx_run` が成功した時にだけ `wr_deallocate` を呼ぶ** 形にする（追加で `pwr_nray` の `ALLOCATED` チェックを保険として併用）。

まず module レベル（`g_initialized` の宣言と並べて）:
```fortran
  LOGICAL, SAVE :: g_initialized = .FALSE.
  LOGICAL, SAVE :: g_run_called  = .FALSE.
```

`wrx_run` 成功パスの末尾で `g_run_called = .TRUE.` をセット:
```fortran
    CALL wr_exec(nstat, ierr_local)
    IF (ierr_local /= 0) THEN
       ierr = 3
       RETURN
    END IF
    g_run_called = .TRUE.
    ierr = 0
  END FUNCTION wrx_run
```

`wrx_finalize` を以下に置換:
```fortran
  FUNCTION wrx_finalize() BIND(C, NAME="wrx_finalize") RESULT(ierr)
    USE wrcomm, ONLY: wr_deallocate, pwr_nray
    INTEGER(C_INT) :: ierr
    ierr = 0
    IF (.NOT. g_initialized) RETURN
    ! Only deallocate if wrx_run actually populated the wrcomm allocations.
    ! Belt-and-braces: also probe one canary allocatable (pwr_nray) in case
    ! a future code path bypasses wrx_run but still allocates wrcomm.
    IF (g_run_called .AND. ALLOCATED(pwr_nray)) THEN
       CALL wr_deallocate
    END IF
    g_run_called  = .FALSE.
    g_initialized = .FALSE.
  END FUNCTION wrx_finalize
```

注: `pwr_nray` を canary に選んだ理由は「`wr_allocate` の冒頭で必ず ALLOCATE される配列」だから。canary が変わる場合は `wrcomm.f90` の `wr_allocate` を確認し、最初に ALLOCATE される配列名に追従させる。

---

## Task 5: Makefile に追加

**Files:**
- Modify: `wrx/Makefile`

- [ ] **Step 1: SRCS_CORE に追加**

```make
SRCS_CORE = wrcomm.f90 wrinit.f90 wrparm.f90 wrprep.f90 wrview.f90 \
            wrsub.f90 \
            wrsetup.f90 wrcalpwr.f90 wrfdrv.f90 wroxb.f90 \
            wrexecr.f90 wrexecb.f90 \
            wrexec.f90 \
            wrfile.f90 \
            wrxregress.f90 \
            wrx_state.f90 wrx_param_registry.f90 wrx_api.f90
```

- [ ] **Step 2: 依存追加**

```make
$(OBJDIR)/wrx_param_registry.o: wrx_param_registry.f90 $(WRCOMM)
$(OBJDIR)/wrx_api.o:            wrx_api.f90 wrx_state.f90 wrx_param_registry.f90 \
                                $(WRCOMM) wrprep.f90 wrsetup.f90 wrexec.f90
```

---

## Task 6: ビルドと unit smoke

- [ ] **Step 1: rebuild**
```bash
cd /home/k-yoshimi/program/task-private/wrx
make veryclean && make 2>&1 | tail -15
```
Expected: `wrx_param_registry.o`, `wrx_api.o` のコンパイル成功。

- [ ] **Step 2: bind(c) シンボル再確認**
```bash
nm libwr.a 2>/dev/null | grep -E " T wrx_" | sort
```
Expected: `wrx_init, wrx_run, wrx_get_state, wrx_set_param, wrx_finalize` 5 個。

- [ ] **Step 3: 簡易 C テスト用一時プログラムで smoke 確認**

Create temporary `/tmp/wrx_smoke.c`:
```c
#include <stdio.h>
#include "wrx_api.h"
int main(void) {
    wrx_state_t st;
    int e = wrx_init();
    printf("init=%d\n", e);
    e = wrx_set_param("NRAYMAX", 1.0);
    printf("set NRAYMAX=%d\n", e);
    e = wrx_set_param("NOSUCH", 1.0);
    printf("set NOSUCH=%d (expect 1)\n", e);
    e = wrx_finalize();
    printf("finalize=%d\n", e);
    return 0;
}
```

Run:
```bash
cd /tmp
gfortran -I/home/k-yoshimi/program/task-private/wrx/mod \
    -c /home/k-yoshimi/program/task-private/wrx/wrx_api.f90 -o /dev/null 2>&1 | head -5
# Note: full link with libwr.a + dependencies is L-4's job. L-3 only needs
# successful compilation and nm symbol verification.
```

L-3 で C ABI test を flink できるかは依存ライブラリ (eq, pl, dp, libtask, libgrf, mtxp, bpsd) が PIC でなくても a.out として link できれば良いが、これは L-6 の Layer 2 C ABI test で完全に検証する。**L-3 ではコンパイル成功と nm シンボル可視性のみ確認**。

- [ ] **Step 4: 既存 baseline test PASS**
```bash
cd /home/k-yoshimi/program/task-private/test_run
rm -rf test_output/wrx_*
./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo
```
Expected: 3 ケース PASS。

- [ ] **Step 5: コミット**
```bash
cd /home/k-yoshimi/program/task-private
git add wrx/wrx_param_registry.f90 wrx/wrx_api.f90 wrx/Makefile
git commit -m "feat(wrx): implement wrx_run/set_param/get_state with param registry"
```

---

## Verification Checklist

- [ ] `wrx/wrx_param_registry.f90` に `wrx_param_set` が実装されている
- [ ] 30 個以上のパラメータが `SELECT CASE` に登録されている
- [ ] `parse_array_subscript` が `"PN[1]"` を `base="PN", idx=1` に分解する
- [ ] `wrx_api.f90` の 5 関数すべて実装完了（stub なし）
- [ ] `wrx_get_state` が `NRAYMAX > WRX_MAX_NRAYMAX` のとき ierr=1 を返す
- [ ] `wrx_finalize` が `wr_deallocate` を呼ぶ（`g_run_called` + `ALLOCATED(pwr_nray)` ガード経由のみ）
- [ ] `wrx_init` → `wrx_finalize`（`wrx_run` を呼ばないパス）が seg-fault せず ierr=0 で復帰
- [ ] 既存 WRX baseline 3 ケースが PASS（数値変化なし、wrx_main 経由は影響なし）
- [ ] `nm libwr.a` で 5 シンボル可視

## Dependencies

- L-2 完了（`wrx_state.f90`, `wrx_api.f90` stub, `wrx_api.h` 存在）

## Fallback

| リスク | 緩和策 |
|---|---|
| `USE wrcomm` チェーンで variable not visible | `USE plcomm, ONLY: ...` を `wrx_param_registry.f90` に追加 |
| `wr_deallocate` が `wr_allocate` 未呼出時にクラッシュ | Task 4 Step 4 で導入済みの `g_run_called` フラグと `ALLOCATED(pwr_nray)` ガードで deallocate をスキップ |
| `wr_prep` が EQINIT を要求して fail | `wrx_init` で `EQINIT` を呼んでいるが、`wrx_set_param` で MODELG 等を変えた後は `wr_prep` 内で再 EQINIT が必要かも。L-6 Layer 2 test で確認 |
| 30 個より多くのパラメータが必要 | パラメータ追加は SELECT CASE に 1 行追加するだけ。本フェーズでは 30 個セットで止め、L-5/L-6 で必要に応じ追加 PR |

## Out of Scope

- shared library 構築（L-4）
- Python wrapper（L-5）
- 文字列パラメータ (`KNAMEQ`, `KNAMWR` 等) → 別 API `wrx_set_string_param` を後の PR で追加
- 複数 WRX インスタンスの同時実行（global state のため不可、明文化のみ）
