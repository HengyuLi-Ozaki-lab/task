# TI Library Phase L-3: Parameter Registry 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2 で stub だった `ti_set_param` を本実装する。`ti/ti_param_registry.f90` を新設し、ti namelist `/TI/`（`tiparm.f90` 参照）の主要パラメータを名前→ticomm 変数の setter テーブルとして登録する。`PT[1]` のような配列添字記法もサポートする。

**Architecture:** 設計は TR の `tr_param_registry` と同型（手書き SELECT CASE テーブル + `parse_array_subscript` ヘルパ）。`ti_api.f90:ti_set_param_c` は `ti_param_registry::ti_param_set` に丸投げするだけ。本フェーズでも `libtiapi.so` 自体はまだ作らない（L-4）。

**Tech Stack:** Fortran 90 + ISO_C_BINDING。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` 5 章 (パラメータテーブル機構) を ti に転用。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `ti/ti_param_registry.f90` | 新規 | 名前 → ticomm 変数の setter テーブル + `parse_array_subscript` |
| `ti/ti_api.f90` | 修正 | `ti_set_param_c` の中で `ti_param_set` を呼ぶ実装に差し替え |
| `ti/Makefile` | 修正 | `SRCS_API` に `ti_param_registry.f90` を追加し、`ti_api.o` の依存に追加 |
| `ti/tests/c_abi/test_param_registry.f90` | 新規 | Fortran 側からだけで registry の動作を検証する単体テスト（main プログラム） |
| `ti/tests/c_abi/Makefile` | 修正 | `test_param_registry` ターゲット追加 |

**スコープ外:**
- C 側からの実 link テスト（L-4）
- Python 側からのテスト（L-5/L-6）

---

## Task 1: 前提確認

**Files:**
- なし

- [ ] **Step 1: ブランチ作成と L-2 マージ確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin
git checkout -b feature/ti-library-L3-param-registry origin/develop
ls /home/k-yoshimi/program/task/ti/ti_state.f90 /home/k-yoshimi/program/task/ti/ti_api.f90 /home/k-yoshimi/program/task/ti/ti_api.h
```
Expected: L-2 で追加されたファイルが develop に存在する。新ブランチに居る。

- [ ] **Step 2: tiparm.f90 の `NAMELIST /TI/` 一覧を抽出**

Run:
```bash
sed -n '/NAMELIST .TI./,/^$/p' /home/k-yoshimi/program/task/ti/tiparm.f90 | head -60
```
Expected: 登録対象候補となる namelist 変数群が表示される。

- [ ] **Step 3: L-0 回帰テスト確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make 2>&1 | tail -3
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh ti_min ti_ar ti_w
```
Expected: 3/3 PASS。

- [ ] **Step 4: 空コミット**

Run:
```bash
git commit --allow-empty -m "chore(ti): start L-3 param registry"
```

---

## Task 2: 登録対象パラメータの最終リスト固定

**Files:**
- なし（決定の文書化）

**決定事項（本計画で確定）:**

ti namelist の中から以下のパラメータを L-3 で registry に登録する（30〜35 個程度）。残りは将来必要になった時点で追加。

**幾何 (scalar real):**
- `RR, RA, RKAP, RDLT, BB, RIP`

**プラズマ種数 (scalar int):**
- `NSMAX`

**プラズマ種別配列 (1D real, 添字 NS):**
- `PA[NS]` (atomic mass; ti コードは `pm=>pa` リネームで `pm` と呼んでいるが、registry では **plcomm 真名 `PA` を C ABI 名としても採用** する。下記「PA / pm 命名の決定」参照)
- `PZ[NS], PN[NS], PNS[NS], PT[NS], PTS[NS], PU[NS], PUS[NS]`

**プラズマ種別配列 (1D int, 添字 NS):**
- `NPA[NS], ID_NS[NS], NZMIN_NS[NS], NZMAX_NS[NS], NZINI_NS[NS]`

**PA / pm 命名の決定（plcomm rename quirk）:**

`ti/ticomm.f90:5` は `USE plcomm, pm=>pa` で **pa を pm にリネーム** して取り込んでいる（既存 ti コード内では `pm(NS)` と書く）。一方 `plcomm.f90:64` の真名は `PA(NSM)`（atomic mass）。

L-3 registry では混乱を避けるため、**真名 `PA` を 1 つだけ正式 C ABI 名として登録** する（`ti.set_param("PA[1]", 39.95)` で Ar の atomic mass を設定）。`pm` は登録しない。

理由:
1. plcomm 自体は `PA` を export する。`USE plcomm, ONLY: PM` はリンク時に `No such entity in module plcomm` エラーになる。
2. ti 内コードの `pm` はあくまで USE-rename された **ローカル名**。registry を `USE plcomm` から構築する以上、真名 `PA` でアクセスするのが自然。
3. ユーザー向け C ABI で 2 つの別名（PA と PM）を併存させると混乱する。L-7 の README で「ti namelist の `PM` は内部 alias、registry では `PA` を使う」と明記する。

互換性が必要な場合の選択肢: `CASE("PA", "PM"); PA(i1) = value` と 2 つの CASE で同一 setter にマップする（実装は容易、ただし上記理由で本計画では PA のみ採用）。

**時間発展 (scalar):**
- `DT, NRMAX, NTMAX, NTSTEP, NGTSTEP, NGRSTEP, MAXLOOP, EPSLOOP, EPSMAT, MATTYPE`

**輸送モデルスイッチ (scalar int):**
- `MODELG, MODELQ, MODEL_PROF, MODEL_NPROF, MODEL_KAI, MODEL_DRR, MODEL_VR, MODEL_NC`

**境界条件 (2D, MODEL_BND[i,NS] / BND_VALUE[i,NS]):**
- `MODEL_BND[i,NS]`, `BND_VALUE[i,NS]` — 添字 i,NS の 2D。L-3 では `"MODEL_BND[1,3]"` 記法でサポート

注: `RR, RA, ...` などは `plcomm` 由来。ti は `USE plcomm,pm=>pa` 経由で参照しているので、`USE plcomm, ONLY: ...` 経由で setter を作る必要あり。

- [ ] **Step 1: 上記決定をコミット**

Run:
```bash
git commit --allow-empty -m "docs(ti): lock L-3 parameter registry initial set (~35 params)"
```

---

## Task 3: `ti_param_registry.f90` を新設（失敗するテスト先行）

**Files:**
- Create: `ti/tests/c_abi/test_param_registry.f90`
- Create: `ti/tests/c_abi/Makefile` (modify, add target)

- [ ] **Step 1: Fortran 単体テスト（registry 直接呼び出し）を書く**

作成: `ti/tests/c_abi/test_param_registry.f90`

```fortran
! test_param_registry.f90
!
! Direct Fortran-side smoke test for ti_param_registry.
! Doesn't go through C ABI; just exercises the SELECT CASE coverage.

PROGRAM test_param_registry
  USE plinit, ONLY: pl_init
  USE equnit, ONLY: eq_init
  USE tiinit, ONLY: ti_init
  USE ti_param_registry, ONLY: ti_param_set
  ! NOTE: plcomm exposes PA (atomic mass) under its true name. The ti codebase
  ! renames it to `pm` via `USE plcomm, pm=>pa` but the rename is not
  ! re-exported; we verify the registry setter by reading PA directly here.
  USE plcomm, ONLY: RR, RA, BB, NSMAX, PN, PNS, PA
  USE ticomm_parm, ONLY: DT, NTMAX, MODEL_KAI
  IMPLICIT NONE
  INTEGER :: ierr
  INTEGER :: failures
  REAL(KIND=8), PARAMETER :: TOL = 1.0D-15

  CALL pl_init
  CALL eq_init
  CALL ti_init

  failures = 0

  ! scalar real
  ierr = ti_param_set("RR", 6.2D0)
  IF (ierr /= 0)               CALL fail("RR set returned non-zero")
  IF (ABS(RR - 6.2D0) > TOL)   CALL fail("RR not updated")

  ierr = ti_param_set("BB", 5.3D0)
  IF (ierr /= 0)               CALL fail("BB set returned non-zero")
  IF (ABS(BB - 5.3D0) > TOL)   CALL fail("BB not updated")

  ierr = ti_param_set("DT", 1.0D-3)
  IF (ierr /= 0)               CALL fail("DT set returned non-zero")
  IF (ABS(DT - 1.0D-3) > TOL)  CALL fail("DT not updated")

  ! scalar int
  ierr = ti_param_set("NSMAX", 3.0D0)
  IF (ierr /= 0)               CALL fail("NSMAX set returned non-zero")
  IF (NSMAX /= 3)              CALL fail("NSMAX not updated")

  ierr = ti_param_set("NTMAX", 50.0D0)
  IF (ierr /= 0)               CALL fail("NTMAX set returned non-zero")
  IF (NTMAX /= 50)             CALL fail("NTMAX not updated")

  ierr = ti_param_set("MODEL_KAI", 1.0D0)
  IF (ierr /= 0)               CALL fail("MODEL_KAI set returned non-zero")
  IF (MODEL_KAI /= 1)          CALL fail("MODEL_KAI not updated")

  ! array real (1D)
  ierr = ti_param_set("PN[1]", 0.7D0)
  IF (ierr /= 0)                  CALL fail("PN[1] set returned non-zero")
  IF (ABS(PN(1) - 0.7D0) > TOL)   CALL fail("PN(1) not updated")

  ierr = ti_param_set("PNS[2]", 0.05D0)
  IF (ierr /= 0)                  CALL fail("PNS[2] set returned non-zero")
  IF (ABS(PNS(2) - 0.05D0) > TOL) CALL fail("PNS(2) not updated")

  ! Atomic mass via true plcomm name `PA`. This is the ti-library-canonical
  ! name; the ticomm rename `pm=>pa` does not apply to the C ABI.
  ierr = ti_param_set("PA[3]", 39.95D0)
  IF (ierr /= 0)                    CALL fail("PA[3] set returned non-zero")
  IF (ABS(PA(3) - 39.95D0) > TOL)   CALL fail("PA(3) not updated")

  ! invalid name
  ierr = ti_param_set("NO_SUCH_PARAM", 1.0D0)
  IF (ierr == 0) CALL fail("unknown name should return non-zero ierr")

  ! out-of-range index
  ierr = ti_param_set("PN[0]", 0.1D0)
  IF (ierr == 0) CALL fail("index 0 should return non-zero ierr")

  IF (failures > 0) THEN
     WRITE(*,'(A,I0,A)') "FAIL: ", failures, " checks failed"
     STOP 1
  END IF
  WRITE(*,*) "OK: ti_param_registry passes all smoke checks"

CONTAINS
  SUBROUTINE fail(msg)
    CHARACTER(LEN=*), INTENT(IN) :: msg
    failures = failures + 1
    WRITE(*,'(A,A)') "  FAIL: ", msg
  END SUBROUTINE fail
END PROGRAM test_param_registry
```

- [ ] **Step 2: tests/c_abi/Makefile に test_param_registry ターゲットを追加**

`ti/tests/c_abi/Makefile` に以下のターゲットを追加（既存 `test:` の前に挿入し、`test:` を `test: test_compile test_param_registry`「両方実行」に変更）:

```makefile
TI_DIR := $(abspath $(CURDIR)/../..)
TASK_TOP := $(abspath $(CURDIR)/../../..)
include $(TASK_TOP)/make.header
include $(TASK_TOP)/mtxp/make.mtxp

LIB_MTX=$(LIB_MTX_MUMPS)
LIBX_MTX=$(LIBX_MTX_MUMPS)

CFLAGS  := -Wall -Wextra -O0 -I$(TI_DIR)
TI_LIBS := $(TI_DIR)/libti.a \
           $(TASK_TOP)/adpost/lib-adpost.a \
           $(TASK_TOP)/open-adas/adf11/adf11-lib/lib-adf11.a \
           $(TASK_TOP)/eq/libeq.a \
           $(TASK_TOP)/pl/libpl.a \
           $(TASK_TOP)/lib/libtask.a \
           $(TASK_TOP)/lib/libgrf.a \
           $(TASK_TOP)/../bpsd/libbpsd.a

MODINCLUDE := -I$(TI_DIR)/$(MOD) -I$(TASK_TOP)/eq/$(MOD) -I$(TASK_TOP)/pl/$(MOD) \
              -I$(TASK_TOP)/lib/$(MOD) -I$(TASK_TOP)/../bpsd/$(MOD)

.PHONY: test test_compile_run test_param_registry_run clean

test: test_compile_run test_param_registry_run

test_compile_run: test_compile
	./test_compile

test_param_registry_run: test_param_registry
	./test_param_registry

test_compile: test_compile.c $(TI_DIR)/ti_api.h
	$(CC) $(CFLAGS) test_compile.c -o test_compile

test_param_registry: test_param_registry.f90 $(TI_DIR)/libti.a
	$(FCFREE) $(OFLAGS) $(MODINCLUDE) test_param_registry.f90 \
	    $(TI_LIBS) -o test_param_registry $(FLIBS) $(LIBX_MTX)

clean:
	rm -f test_compile test_param_registry
```

注: include path 等は環境によって異なるため、`make.header` から取れない変数があれば実値に置換する。

- [ ] **Step 3: テスト実行（まだ ti_param_registry.f90 が無いので失敗する）**

Run:
```bash
cd /home/k-yoshimi/program/task/ti/tests/c_abi
make test_param_registry 2>&1 | tail -10
```
Expected: コンパイルエラー (`Cannot open module file 'ti_param_registry.mod'`)。

- [ ] **Step 4: コミット**

Run:
```bash
git add ti/tests/c_abi/test_param_registry.f90 ti/tests/c_abi/Makefile
git commit -m "test(ti): add Fortran-side smoke test for ti_param_registry (failing)"
```

---

## Task 4: `ti_param_registry.f90` を実装

**Files:**
- Create: `ti/ti_param_registry.f90`

- [ ] **Step 1: 新規ファイル作成**

作成: `ti/ti_param_registry.f90`

```fortran
! ti_param_registry.f90
!
! Hand-written name-to-ticomm setter table for ti_set_param.
! Supports scalar names ("RR") and 1D/2D array subscripts ("PN[1]", "MODEL_BND[1,3]").

MODULE ti_param_registry
  ! NOTE: `plcomm` defines the atomic-mass array as `PA(NSM)`. `ti/ticomm.f90`
  ! does `USE plcomm, pm=>pa` so internal ti code refers to it as `pm`, but
  ! that rename is local and does NOT re-export. We therefore USE plcomm
  ! WITHOUT the rename here and expose `PA` (the true name) as the C ABI key.
  ! `KID_NS` is character-valued and not settable through the float-only
  ! ti_set_param ABI; keep it imported anyway for completeness / future
  ! ti_set_string_param extension, but no SELECT CASE entry below.
  USE plcomm,    ONLY: RR, RA, RKAP, RDLT, BB, RIP, &
                       NSMAX, PA, PZ, PN, PNS, PTPR, PTPP, PTS, PU, PUS, &
                       NPA, ID_NS, KID_NS, &
                       MODELG, MODELQ, MODEL_PROF, MODEL_NPROF, &
                       PROFN1, PROFN2, PROFT1, PROFT2, PROFU1, PROFU2
  USE ticomm_parm, ONLY: rkind, &
                         NZMIN_NS, NZMAX_NS, NZINI_NS, &
                         PT, MODEL_BND, BND_VALUE, &
                         DT, NRMAX, NTMAX, NTSTEP, NGTSTEP, NGRSTEP, &
                         MAXLOOP, EPSLOOP, EPSMAT, MATTYPE, &
                         MODEL_EQB, MODEL_EQN, MODEL_EQT, MODEL_EQU, &
                         MODEL_KAI, MODEL_DRR, MODEL_VR, MODEL_NC, &
                         MODEL_NF, MODEL_NB, MODEL_EC, MODEL_LH, MODEL_IC, &
                         MODEL_CD, MODEL_SYNC, MODEL_PEL, MODEL_PSC, &
                         PROFJ1, PROFJ2
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: ti_param_set

  INTEGER, PARAMETER :: ERR_OK             = 0
  INTEGER, PARAMETER :: ERR_UNKNOWN_NAME   = 1
  INTEGER, PARAMETER :: ERR_BAD_INDEX      = 2

CONTAINS

  FUNCTION ti_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),       INTENT(IN) :: value
    INTEGER :: ierr
    CHARACTER(LEN=64) :: base
    INTEGER :: i1, i2

    CALL parse_subscript(name, base, i1, i2)
    ierr = ERR_OK

    SELECT CASE (TRIM(base))
    ! ---- geometry / device (plcomm scalars) ----
    CASE ("RR");           RR    = value
    CASE ("RA");           RA    = value
    CASE ("RKAP");         RKAP  = value
    CASE ("RDLT");         RDLT  = value
    CASE ("BB");           BB    = value
    CASE ("RIP");          RIP   = value

    ! ---- profile shape (plcomm scalars) ----
    CASE ("PROFN1");       PROFN1 = value
    CASE ("PROFN2");       PROFN2 = value
    CASE ("PROFT1");       PROFT1 = value
    CASE ("PROFT2");       PROFT2 = value
    CASE ("PROFU1");       PROFU1 = value
    CASE ("PROFU2");       PROFU2 = value

    ! ---- model switches (plcomm) ----
    CASE ("MODELG");       MODELG       = INT(value)
    CASE ("MODELQ");       MODELQ       = INT(value)
    CASE ("MODEL_PROF");   MODEL_PROF   = INT(value)
    CASE ("MODEL_NPROF");  MODEL_NPROF  = INT(value)

    ! ---- plasma scalar int ----
    CASE ("NSMAX");        NSMAX        = INT(value)

    ! ---- 1D arrays indexed by NS (plcomm) ----
    ! PA = atomic mass (plcomm true name). ti namelist calls this "PM" via
    ! the `pm=>pa` rename in ticomm_parm; here we expose only PA. See the
    ! "PA / pm 命名の決定" note above for rationale.
    CASE ("PA");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PA(i1)   = value; END IF
    CASE ("PZ");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PZ(i1)   = value; END IF
    CASE ("PN");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PN(i1)   = value; END IF
    CASE ("PNS");  IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PNS(i1)  = value; END IF
    CASE ("PT");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PT(i1)   = value; END IF
    CASE ("PTPR"); IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PTPR(i1) = value; END IF
    CASE ("PTPP"); IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PTPP(i1) = value; END IF
    CASE ("PTS");  IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PTS(i1)  = value; END IF
    CASE ("PU");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PU(i1)   = value; END IF
    CASE ("PUS");  IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; PUS(i1)  = value; END IF

    ! ---- 1D int arrays indexed by NS ----
    CASE ("NPA");        IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; NPA(i1)        = INT(value); END IF
    CASE ("ID_NS");      IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; ID_NS(i1)      = INT(value); END IF
    CASE ("NZMIN_NS");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; NZMIN_NS(i1)   = INT(value); END IF
    CASE ("NZMAX_NS");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; NZMAX_NS(i1)   = INT(value); END IF
    CASE ("NZINI_NS");   IF (i1 < 1) THEN; ierr=ERR_BAD_INDEX; ELSE; NZINI_NS(i1)   = INT(value); END IF

    ! ---- 2D arrays indexed by (i, NS) ----
    CASE ("MODEL_BND"); IF (i1 < 1 .OR. i2 < 1) THEN; ierr=ERR_BAD_INDEX; &
                                                ELSE; MODEL_BND(i1,i2) = INT(value); END IF
    CASE ("BND_VALUE"); IF (i1 < 1 .OR. i2 < 1) THEN; ierr=ERR_BAD_INDEX; &
                                                ELSE; BND_VALUE(i1,i2) = value; END IF

    ! ---- time evolution (ticomm_parm) ----
    CASE ("DT");           DT       = value
    CASE ("NRMAX");        NRMAX    = INT(value)
    CASE ("NTMAX");        NTMAX    = INT(value)
    CASE ("NTSTEP");       NTSTEP   = INT(value)
    CASE ("NGTSTEP");      NGTSTEP  = INT(value)
    CASE ("NGRSTEP");      NGRSTEP  = INT(value)
    CASE ("MAXLOOP");      MAXLOOP  = INT(value)
    CASE ("EPSLOOP");      EPSLOOP  = value
    CASE ("EPSMAT");       EPSMAT   = value
    CASE ("MATTYPE");      MATTYPE  = INT(value)
    CASE ("PROFJ1");       PROFJ1   = value
    CASE ("PROFJ2");       PROFJ2   = value

    ! ---- transport / source switches ----
    CASE ("MODEL_EQB");    MODEL_EQB    = INT(value)
    CASE ("MODEL_EQN");    MODEL_EQN    = INT(value)
    CASE ("MODEL_EQT");    MODEL_EQT    = INT(value)
    CASE ("MODEL_EQU");    MODEL_EQU    = INT(value)
    CASE ("MODEL_KAI");    MODEL_KAI    = INT(value)
    CASE ("MODEL_DRR");    MODEL_DRR    = INT(value)
    CASE ("MODEL_VR");     MODEL_VR     = INT(value)
    CASE ("MODEL_NC");     MODEL_NC     = INT(value)
    CASE ("MODEL_NF");     MODEL_NF     = INT(value)
    CASE ("MODEL_NB");     MODEL_NB     = INT(value)
    CASE ("MODEL_EC");     MODEL_EC     = INT(value)
    CASE ("MODEL_LH");     MODEL_LH     = INT(value)
    CASE ("MODEL_IC");     MODEL_IC     = INT(value)
    CASE ("MODEL_CD");     MODEL_CD     = INT(value)
    CASE ("MODEL_SYNC");   MODEL_SYNC   = INT(value)
    CASE ("MODEL_PEL");    MODEL_PEL    = INT(value)
    CASE ("MODEL_PSC");    MODEL_PSC    = INT(value)

    CASE DEFAULT
       ierr = ERR_UNKNOWN_NAME
    END SELECT
  END FUNCTION ti_param_set

  ! Parse "BASE", "BASE[i]", or "BASE[i,j]" into base + indices.
  ! i / j default to 0 when absent.
  SUBROUTINE parse_subscript(full_name, base, i1, i2)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,           INTENT(OUT) :: i1, i2
    INTEGER :: lb, rb, comma, ios

    base = full_name
    i1 = 0
    i2 = 0
    lb = INDEX(full_name, "[")
    rb = INDEX(full_name, "]", BACK=.TRUE.)
    IF (lb > 0 .AND. rb > lb) THEN
       base = full_name(1:lb-1)
       comma = INDEX(full_name(lb+1:rb-1), ",")
       IF (comma > 0) THEN
          READ(full_name(lb+1:lb+comma-1), *, IOSTAT=ios) i1
          IF (ios /= 0) i1 = -1
          READ(full_name(lb+comma+1:rb-1), *, IOSTAT=ios) i2
          IF (ios /= 0) i2 = -1
       ELSE
          READ(full_name(lb+1:rb-1), *, IOSTAT=ios) i1
          IF (ios /= 0) i1 = -1
       END IF
    END IF
  END SUBROUTINE parse_subscript

END MODULE ti_param_registry
```

注: 上記の `USE plcomm, ONLY: ...` リストのうち、実際の `plcomm` モジュールに存在しないシンボルがあった場合（例: `model_prof` が小文字のみ）はビルドエラーで判明する。Step 3 で確認の上、リスト調整。

- [ ] **Step 2: Makefile の SRCS_API に追加**

`ti/Makefile` の以下を変更:
```
SRCS_API= ti_state.f90 ti_api.f90
```
を以下に変更:
```
SRCS_API= ti_state.f90 ti_param_registry.f90 ti_api.f90
```

そして依存定義に追加:
```
ti_param_registry.o : ti_param_registry.f90 ticomm.f90
ti_api.o : ti_api.f90 ti_state.f90 ti_param_registry.f90 ticomm.f90 tiinit.f90 tiprep.f90 tiexec.f90
```

- [ ] **Step 3: API オブジェクトをビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make api-objs 2>&1 | tail -10
ls ti_param_registry.o
```
Expected: `ti_param_registry.o` が生成される。`USE plcomm, ONLY:` のシンボルがない場合はエラーが出るので、出たシンボルを registry の `USE` 文から削除して再試行。

- [ ] **Step 4: コミット**

Run:
```bash
git add ti/ti_param_registry.f90 ti/Makefile
git commit -m "feat(ti): add ti_param_registry.f90 with ~35 scalar/array setters"
```

---

## Task 5: `ti_api.f90:ti_set_param_c` を本実装に差し替え

**Files:**
- Modify: `ti/ti_api.f90`

- [ ] **Step 1: stub を本実装に置換**

`ti/ti_api.f90` の `ti_set_param_c` 関数を以下に置換:

```fortran
  FUNCTION ti_set_param_c(name, value) RESULT(ierr) BIND(C, NAME="ti_set_param")
    USE ti_param_registry, ONLY: ti_param_set
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: fname
    INTEGER :: i

    fname = ' '
    DO i = 1, LEN(fname)
       IF (name(i) == C_NULL_CHAR) EXIT
       fname(i:i) = name(i)
    END DO

    ierr = ti_param_set(TRIM(fname), value)
  END FUNCTION ti_set_param_c
```

`USE` 文をモジュール先頭の方ではなく function 内 USE で書くのは、Fortran 標準として有効（既存 `tr_api` も同パターン）。

- [ ] **Step 2: ビルド確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make api-objs 2>&1 | tail -10
```
Expected: `ti_api.o` が再ビルドされる。エラーなし。

- [ ] **Step 3: Fortran 単体テスト実行**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make 2>&1 | tail -5   # libti.a 必要
cd /home/k-yoshimi/program/task/ti/tests/c_abi
make test_param_registry 2>&1 | tail -10
./test_param_registry
```
Expected: `OK: ti_param_registry passes all smoke checks`、exit 0。

失敗した場合（典型的には `USE plcomm` で plcomm に無いシンボルを参照している、`PT` の所属モジュール違いなど）、エラーメッセージに従い `ti_param_registry.f90` の `USE` 文と SELECT CASE エントリを修正。

- [ ] **Step 4: コミット**

Run:
```bash
git add ti/ti_api.f90
git commit -m "feat(ti): wire ti_set_param to ti_param_registry (no longer stub)"
```

---

## Task 6: 全 ti テストの最終確認 + PR

**Files:**
- なし

- [ ] **Step 1: 既存 ti バイナリと L-0 回帰テストが PASS すること**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make clean && make 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: 全テスト PASS（ti L-3 は ti binary に直接影響しないため、L-0 baseline は完全一致）。

- [ ] **Step 2: c_abi テスト 2 種が PASS すること**

Run:
```bash
cd /home/k-yoshimi/program/task/ti/tests/c_abi
make test
```
Expected: `test_compile` と `test_param_registry` の両方が PASS。

- [ ] **Step 3: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: 新規 `ti_param_registry.f90` + `tests/c_abi/test_param_registry.f90`、修正 `ti_api.f90` + `Makefile` + `tests/c_abi/Makefile`。

- [ ] **Step 4: push と PR**

Run:
```bash
git push -u origin feature/ti-library-L3-param-registry
gh pr create --base develop \
  --title "feat(ti): implement ti_param_registry (L-3)" \
  --body "Phase L-3: ti_set_param now backed by ti_param_registry with ~35 scalar/array setters covering geometry, plasma, time, model switches, and 2D MODEL_BND/BND_VALUE. Verified by Fortran-side smoke test and L-0 regression (PASS)."
```

---

## Dependencies

- 前段階: L-2 マージ済み (`ti_state.f90`, `ti_api.f90` stub)。
- 後段階: L-4 で libtiapi.so にリンクされ、L-5 から Python 経由で叩かれる。

## Fallback

| 障害 | 対処 |
|---|---|
| `USE plcomm, ONLY: PROFN1` 等で「No such entity」エラー | 該当シンボルが本当に plcomm に無い → registry から削除して initial set を縮小 |
| `USE plcomm, ONLY: PM` で「No such entity」エラー | 既知の quirk: plcomm の真名は `PA`（`ticomm_parm` の `USE plcomm, pm=>pa` は re-export しない）。本計画は `PA` で登録する方針。万一 `PM` エイリアスも公開したければ `CASE ("PA", "PM"); PA(i1) = value` と 2 つのキーを 1 setter にマップする |
| `PT` の参照元モジュール不整合 | 確認済: `PT(NSM)` は `ticomm_parm` 側（`ticomm.f90:32`）で宣言されている。`USE ticomm_parm, ONLY: PT` で正しく取れる。これは `plcomm` 側には存在しない |
| `parse_subscript` が一部の入力で誤動作 | `IOSTAT` でエラー時 `i1=-1` を返す現実装で十分。L-3 では基本ケースだけサポートし、複雑な記法は L-5 wrapper 側で吸収 |
| Fortran スモークテストのリンクで未解決シンボル | tests/c_abi/Makefile の `TI_LIBS` に必要な lib を追記、または `mtxp/libmtxp.a` を加える |
