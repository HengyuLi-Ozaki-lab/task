# FP ライブラリ化 Phase L-3: パラメータレジストリ実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2 で stub のままだった `fp_set_param(name, value)` を、`fp_param_registry.f90` 経由で `fpcomm_parm` の namelist 変数（`/FP/`）に書き込めるようにする。Python 側からスカラーや配列インデクス記法 `PN[1]` で fp の主要パラメータを動的に変更できる土台。

**Architecture:** TR Phase L 設計 (`tr_library-design.md` セクション 5) を fp 用に転用:

```
fp_set_param(name, value)               [fp_api.f90]
   │
   ▼
fp_param_set(name, value) -> ierr        [fp_param_registry.f90]
   │
   ├── parse_array_subscript("PN[2]")    [補助 SUBROUTINE]
   │
   └── SELECT CASE (TRIM(base))
       CASE ("RR");    RR = value
       CASE ("BB");    BB = value
       CASE ("PN");    PN(idx) = value
       ...
       CASE DEFAULT;   ierr = 1
```

**Tech Stack:** Fortran 90 (`SELECT CASE`)、`fpcomm_parm` モジュール（fp の namelist 全変数を保持）、L-2 で導入した `fp_api.f90`。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 5。

---

## Module Survey: `&FP/` namelist の主要パラメータ

`fp/fpparm.f90:60-108` の `NAMELIST /FP/` には 110+ 変数が登録されている。L-3 では **頻用パラメータ約 25 個** を最初に登録し、CASE 追加でいつでも拡張できる構造にする。

優先度別の登録対象:

| カテゴリ | 変数 | 型 | 形 |
|---|---|---|---|
| **幾何** | `RR, RA, RB, RKAP, RDLT, BB, RIP` | real(rkind) | scalar |
| **モデルスイッチ (scalar int)** | `MODELG, MODELE, MODELR, MODELC, MODELW, MODELS, MODELD` | integer | scalar (※ MODELC/W は配列。後述) |
| **メッシュ** | `NRMAX, NPMAX, NTHMAX, NTMAX, NAVMAX` | integer | scalar |
| **species 数** | `NSMAX, NSAMAX, NSBMAX` | integer | scalar |
| **species mapping** | `NS_NSA, NS_NSB` | integer | array (NSM) |
| **species 物理量** | `PA, PZ, PN, PNS, PTPR, PTPP, PTS` | real | array (NSM) |
| **時間発展** | `DELT, EPSFP, LMAXFP` | real / integer | scalar |
| **エネルギー / radial** | `PMAX, R1, DELR1, RMIN, RMAX, E0, ZEFF` | real | scalar (※ PMAX は array (NSM)) |
| **波加熱** | `PABS_EC, PABS_LH, PABS_FW, PABS_WR, PABS_WM, RF_WM` | real | scalar |
| **MODEL config (scalar int)** | `MODEL_NBI, MODEL_WAVE, MODEL_DISRUPT, MODEL_BS, MODEL_LOSS, MODEL_SYNCH, MODEL_FOW` | integer | scalar |

**配列パラメータの記法:** TR と同じく Python 側で `set_param("PN[1]", 0.7)`、Fortran 側で 1-origin。

**CASE table の最小セット (L-3 完了基準):** 上表の **25 個** を実装する。それ以上は後続 PR で追加（追加コストは Fortran 1 行）。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `fp/fp_param_registry.f90` | 新規 | `MODULE fp_param_registry`、`fp_param_set(name, value) RESULT(ierr)`、`parse_array_subscript` ヘルパ |
| `fp/fp_api.f90` | 修正 | `fp_set_param_c` を stub から `fp_param_set` 呼び出しに差し替え |
| `fp/Makefile` | 修正 | `SRCS_API` に `fp_param_registry.f90` を追加、依存ルール追加 |
| `fp/tests/registry/test_param_registry.f90` | 新規 | Fortran 直 driver で `fp_param_set` の単体動作を検証 |
| `fp/tests/registry/Makefile` | 新規 | テスト driver のビルド/実行 |

---

## Task 1: 作業ブランチ + L-2 完了確認

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git checkout -b feature/fp-library-L3-param-registry origin/develop
cd fp && make 2>&1 | tail -3
make fp_api_check 2>&1 | tail -5
```
Expected: 既存 fp ビルド + L-2 の `fp_api_check` 両方 OK。

- [ ] **Step 2: L-0 ベースラインが green（出発点固定）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 全 PASS。

---

## Task 2: `fp_param_registry.f90` を新規作成

**Files:**
- Create: `fp/fp_param_registry.f90`

- [ ] **Step 1: `fpcomm_parm` で公開されている対象変数を grep 確認**

Run:
```bash
grep -nE "^[[:space:]]+(integer|INTEGER|real|REAL|complex|COMPLEX).*::.*\b(RR|RA|BB|RKAP|RDLT|RIP|NSMAX|NRMAX|NPMAX|NTHMAX|NTMAX|DELT|PMAX|EPSFP|LMAXFP|PN\b|PT\b|PTPR|PTPP|PTS|PNS|PA\b|PZ\b|MODELC|MODELW|MODELE|MODELR|MODELG|MODEL_NBI|MODEL_WAVE|PABS_EC|PABS_WR|PABS_WM)\b" /home/k-yoshimi/program/task/fp/fpcomm.f90 | head -40
```
Expected: ほぼ全変数が `fpcomm_parm`（または `plcomm_parm` 経由）で宣言されている。型と shape を確認。

- [ ] **Step 2: ファイル作成**

作成: `fp/fp_param_registry.f90`

```fortran
! fp_param_registry.f90
!
! Phase L-3: name -> fpcomm_parm setter table for FP library API.
! Called from fp_api.f90 :: fp_set_param.
!
! Adding a parameter is a one-liner in the SELECT CASE block below.
! Array parameters use 1-origin indices via "NAME[idx]" syntax (e.g. PN[2]).

MODULE fp_param_registry
  USE fpcomm_parm
  IMPLICIT NONE
  PRIVATE
  PUBLIC :: fp_param_set

CONTAINS

  FUNCTION fp_param_set(name, value) RESULT(ierr)
    CHARACTER(LEN=*), INTENT(IN) :: name
    REAL(rkind),       INTENT(IN) :: value
    INTEGER :: ierr
    INTEGER :: idx
    CHARACTER(LEN=64) :: base

    ierr = 0
    CALL parse_array_subscript(name, base, idx)

    SELECT CASE (TRIM(base))

    ! ----- geometry (scalar real) -----
    CASE ("RR");      RR    = value
    CASE ("RA");      RA    = value
    CASE ("RB");      RB    = value
    CASE ("RKAP");    RKAP  = value
    CASE ("RDLT");    RDLT  = value
    CASE ("BB");      BB    = value
    CASE ("RIP");     RIP   = value

    ! ----- mesh (scalar int) -----
    CASE ("NRMAX");   NRMAX  = NINT(value)
    CASE ("NPMAX");   NPMAX  = NINT(value)
    CASE ("NTHMAX");  NTHMAX = NINT(value)
    CASE ("NTMAX");   NTMAX  = NINT(value)
    CASE ("NAVMAX");  NAVMAX = NINT(value)

    ! ----- species count -----
    CASE ("NSMAX");   NSMAX  = NINT(value)
    CASE ("NSAMAX");  NSAMAX = NINT(value)
    CASE ("NSBMAX");  NSBMAX = NINT(value)

    ! ----- species mapping (1-origin, NSM-bound) -----
    CASE ("NS_NSA")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       NS_NSA(idx) = NINT(value)
    CASE ("NS_NSB")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       NS_NSB(idx) = NINT(value)

    ! ----- species real arrays (1-origin) -----
    CASE ("PA")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PA(idx)  = value
    CASE ("PZ")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PZ(idx)  = value
    CASE ("PN")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PN(idx)  = value
    CASE ("PNS")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PNS(idx) = value
    CASE ("PTPR")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PTPR(idx) = value
    CASE ("PTPP")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PTPP(idx) = value
    CASE ("PTS")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PTS(idx)  = value

    ! ----- time evolution -----
    CASE ("DELT");   DELT   = value
    CASE ("EPSFP");  EPSFP  = value
    CASE ("LMAXFP"); LMAXFP = NINT(value)

    ! ----- energy / radial mesh -----
    CASE ("PMAX")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       PMAX(idx) = value
    CASE ("R1");     R1    = value
    CASE ("DELR1");  DELR1 = value
    CASE ("RMIN");   RMIN  = value
    CASE ("RMAX");   RMAX  = value
    CASE ("E0");     E0    = value
    CASE ("ZEFF");   ZEFF  = value

    ! ----- wave heating -----
    CASE ("PABS_EC"); PABS_EC = value
    CASE ("PABS_LH"); PABS_LH = value
    CASE ("PABS_FW"); PABS_FW = value
    CASE ("PABS_WR"); PABS_WR = value
    CASE ("PABS_WM"); PABS_WM = value
    CASE ("RF_WM");   RF_WM   = value

    ! ----- model switches (scalar int) -----
    CASE ("MODELG"); MODELG = NINT(value)
    CASE ("MODELE"); MODELE = NINT(value)
    CASE ("MODELR"); MODELR = NINT(value)
    CASE ("MODELS"); MODELS = NINT(value)
    CASE ("MODELD"); MODELD = NINT(value)
    CASE ("MODEL_NBI");      MODEL_NBI      = NINT(value)
    CASE ("MODEL_WAVE");     MODEL_WAVE     = NINT(value)
    CASE ("MODEL_DISRUPT");  MODEL_DISRUPT  = NINT(value)
    CASE ("MODEL_BS");       MODEL_BS       = NINT(value)
    CASE ("MODEL_LOSS");     MODEL_LOSS     = NINT(value)
    CASE ("MODEL_SYNCH");    MODEL_SYNCH    = NINT(value)

    ! ----- model switches (per-species int arrays) -----
    CASE ("MODELC")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       MODELC(idx) = NINT(value)
    CASE ("MODELW")
       IF (idx < 1 .OR. idx > NSM) THEN; ierr = 2; RETURN; END IF
       MODELW(idx) = NINT(value)

    CASE DEFAULT
       ierr = 1
    END SELECT
  END FUNCTION fp_param_set

  ! Parse "NAME[idx]" -> base="NAME", idx=N. "NAME" alone -> idx=0.
  SUBROUTINE parse_array_subscript(full_name, base, idx)
    CHARACTER(LEN=*), INTENT(IN)  :: full_name
    CHARACTER(LEN=*), INTENT(OUT) :: base
    INTEGER,          INTENT(OUT) :: idx

    INTEGER :: i_open, i_close, ios

    base = ''
    idx  = 0
    i_open  = INDEX(full_name, '[')
    i_close = INDEX(full_name, ']', BACK=.TRUE.)
    IF (i_open == 0 .AND. i_close == 0) THEN
       base = full_name
       RETURN
    END IF
    IF (i_open == 0 .OR. i_close == 0 .OR. i_close <= i_open + 1) THEN
       base = full_name   ! malformed -> let CASE DEFAULT reject
       RETURN
    END IF
    base = full_name(1 : i_open - 1)
    READ(full_name(i_open + 1 : i_close - 1), *, IOSTAT=ios) idx
    IF (ios /= 0) idx = -1
  END SUBROUTINE parse_array_subscript

END MODULE fp_param_registry
```

エラーコード: `ierr = 0` OK、`1` unknown name、`2` index out of range。

- [ ] **Step 3: 単独コンパイル**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make obj/fpcomm.o 2>&1 | tail -3
gfortran -c fp_param_registry.f90 -o obj/fp_param_registry.o -Imod -I../pl/mod -I../dp/mod -Jmod
ls -la obj/fp_param_registry.o
```
Expected: エラーなしで `.o` 生成。

CASE 文中で `MODEL_FOW` など `fpcomm_parm` に存在しない変数を入れていると compile error になる。当該行を削除して再試行。

---

## Task 3: `fp_api.f90` の `fp_set_param_c` を本実装に差し替え

**Files:**
- Modify: `fp/fp_api.f90`

- [ ] **Step 1: 失敗するテストを書く（Fortran 単体テスト driver）**

作成: `fp/tests/registry/test_param_registry.f90`

```fortran
! fp/tests/registry/test_param_registry.f90
!
! Direct Fortran test for fp_param_set. Does NOT exercise the C ABI;
! that comes in L-6 layer 2.

PROGRAM test_param_registry
  USE fpcomm_parm
  USE fpinit, ONLY: fp_init
  USE fp_param_registry, ONLY: fp_param_set
  USE plinit, ONLY: pl_init
  IMPLICIT NONE

  INTEGER :: ierr, fail
  fail = 0

  CALL pl_init
  CALL fp_init

  ! 1. scalar real
  ierr = fp_param_set("RR", 7.5d0)
  IF (ierr /= 0 .OR. RR /= 7.5d0) THEN
     WRITE(6,*) "FAIL: set RR (ierr=", ierr, "RR=", RR, ")"; fail = fail + 1
  END IF

  ! 2. scalar int
  ierr = fp_param_set("NTMAX", 42.d0)
  IF (ierr /= 0 .OR. NTMAX /= 42) THEN
     WRITE(6,*) "FAIL: set NTMAX (ierr=", ierr, "NTMAX=", NTMAX, ")"; fail = fail + 1
  END IF

  ! 3. array element
  ierr = fp_param_set("PN[2]", 0.345d0)
  IF (ierr /= 0 .OR. PN(2) /= 0.345d0) THEN
     WRITE(6,*) "FAIL: set PN[2] (ierr=", ierr, "PN(2)=", PN(2), ")"; fail = fail + 1
  END IF

  ! 4. unknown parameter rejected
  ierr = fp_param_set("UNKNOWN_FOO", 1.d0)
  IF (ierr /= 1) THEN
     WRITE(6,*) "FAIL: unknown parameter not rejected (ierr=", ierr, ")"; fail = fail + 1
  END IF

  ! 5. out-of-range index rejected
  ierr = fp_param_set("PN[999]", 1.d0)
  IF (ierr /= 2) THEN
     WRITE(6,*) "FAIL: out-of-range PN[999] not rejected (ierr=", ierr, ")"; fail = fail + 1
  END IF

  ! 6. malformed name accepted as unknown (ierr=1)
  ierr = fp_param_set("PN[", 1.d0)
  IF (ierr /= 1) THEN
     WRITE(6,*) "FAIL: malformed PN[ not rejected (ierr=", ierr, ")"; fail = fail + 1
  END IF

  IF (fail == 0) THEN
     WRITE(6,*) "OK: all fp_param_set unit tests passed"
     STOP 0
  ELSE
     WRITE(6,*) "FAIL count =", fail
     STOP 1
  END IF
END PROGRAM test_param_registry
```

- [ ] **Step 2: テスト driver 用 Makefile**

作成: `fp/tests/registry/Makefile`

```makefile
# Phase L-3 unit test for fp_param_registry.
# Builds against the real fp libs in ../../

include ../../../make.header

FFLAGS = $(OFLAGS)

FP_DIR  = ../..
MODINC  = -I$(FP_DIR)/mod -I$(FP_DIR)/../pl/mod -I$(FP_DIR)/../dp/mod \
          -I$(FP_DIR)/../eq/mod -I$(FP_DIR)/../ob/mod \
          -I$(FP_DIR)/../lib/mod -I$(FP_DIR)/../mtxp/mod \
          -I$(FP_DIR)/../../bpsd/mod

OBJS_REG = $(FP_DIR)/obj/fp_param_registry.o

LIBS = $(FP_DIR)/libfp.a $(FP_DIR)/../ob/libob.a $(FP_DIR)/../pl/libpl.a \
       $(FP_DIR)/../eq/libeq.a $(FP_DIR)/../dp/libdp.a \
       $(FP_DIR)/../lib/libgrf.a $(FP_DIR)/../lib/libtask.a \
       $(FP_DIR)/../../bpsd/libbpsd.a

test_param_registry: test_param_registry.f90 $(OBJS_REG) $(LIBS)
	$(FCFREE) $(FFLAGS) test_param_registry.f90 $(OBJS_REG) $(LIBS) \
	    -o test_param_registry $(FFLAGS) $(MODINC) $(FLIBS)

.PHONY: check
check: test_param_registry
	./test_param_registry

.PHONY: clean
clean:
	-rm -f test_param_registry
```

- [ ] **Step 3: テスト失敗を確認（fp_api がまだ stub のまま）**

L-3 ではテストは fp_param_set を直接呼ぶので、現状 stub のままでも build は通り、PASS してしまう可能性がある。重要なのは **fp_param_registry.o がリンクできること**。

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make obj/fp_param_registry.o 2>&1 | tail -3
cd tests/registry
make check 2>&1 | tail -10
```
Expected: 6 個のテストが OK、`OK: all fp_param_set unit tests passed`。

リンクで未解決シンボルが出たら `LIBS` に必要な `.a` を追加。

- [ ] **Step 4: `fp/fp_api.f90` の `fp_set_param_c` を実装に差し替え**

`fp/fp_api.f90` の `fp_set_param_c` 関数を以下に置換:

```fortran
  FUNCTION fp_set_param_c(name, value) RESULT(ierr) BIND(C, NAME="fp_set_param")
    USE fp_param_registry, ONLY: fp_param_set
    USE fpcomm,           ONLY: rkind
    CHARACTER(KIND=C_CHAR), DIMENSION(*), INTENT(IN) :: name
    REAL(C_DOUBLE), VALUE, INTENT(IN) :: value
    INTEGER(C_INT) :: ierr
    CHARACTER(LEN=64) :: f_name
    INTEGER :: i, n
    INTEGER :: rerr

    ! Convert C string -> Fortran string (truncate at first NUL or 64 chars).
    f_name = ' '
    n = 0
    DO i = 1, LEN(f_name)
       IF (name(i) == C_NULL_CHAR) EXIT
       f_name(i:i) = name(i)
       n = i
    END DO

    rerr = fp_param_set(TRIM(f_name(1:n)), REAL(value, KIND=rkind))
    SELECT CASE (rerr)
    CASE (0); ierr = FP_OK
    CASE (1); ierr = FP_ERR_INVALID
    CASE (2); ierr = FP_ERR_INVALID
    CASE DEFAULT; ierr = FP_ERR_INVALID
    END SELECT
  END FUNCTION fp_set_param_c
```

注: `C_NULL_CHAR` は `ISO_C_BINDING` から既に USE 済み。`rkind` を `fpcomm` から取得。

- [ ] **Step 5: Makefile に登録**

`fp/Makefile` の `SRCS_API` を更新:

```makefile
SRCS_API = fp_state.f90 fp_param_registry.f90 fp_api.f90
```

依存記述に追記:

```makefile
$(OBJDIR)/fp_param_registry.o : fp_param_registry.f90 fpcomm.f90
$(OBJDIR)/fp_api.o            : fp_api.f90 fp_state.f90 fp_param_registry.f90 \
                                fpcomm.f90 fpinit.f90 fpprep.f90 fploop.f90
```

- [ ] **Step 6: `fp_api_check` を再走**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make fp_api_check 2>&1 | tail -10
```
Expected: 全 OK。

- [ ] **Step 7: 単体テスト再実行**

Run:
```bash
cd /home/k-yoshimi/program/task/fp/tests/registry
make clean && make check 2>&1 | tail -10
```
Expected: 全 6 PASS。

- [ ] **Step 8: 既存 fp バイナリの数値が変わっていないこと**

Run:
```bash
cd /home/k-yoshimi/program/task/fp && make 2>&1 | tail -3
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 全 PASS。

- [ ] **Step 9: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add fp/fp_param_registry.f90 fp/fp_api.f90 fp/Makefile \
        fp/tests/registry/test_param_registry.f90 fp/tests/registry/Makefile
git commit -m "feat(fp): implement fp_param_set with name->fpcomm setter table"
```

---

## Task 4: README に L-3 メモ追加

- [ ] **Step 1: `test_run/README.md` の FP セクションに追記**

```markdown
### FP parameter registry (Phase L-3)

Direct Fortran unit test:

    cd fp/tests/registry && make check

Currently registered parameters (~25): see fp/fp_param_registry.f90.
Adding a new parameter is a one-line `CASE` addition.
Array params use 1-origin "NAME[idx]" syntax (e.g. PN[2], MODELW[1]).
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add test_run/README.md
git commit -m "docs(fp): note L-3 parameter registry usage"
```

---

## 受け入れ基準

- [ ] `fp/fp_param_registry.f90` が存在し、25 個以上の namelist 変数を CASE で受け付ける。
- [ ] `cd fp/tests/registry && make check` で 6 個のテストが PASS。
- [ ] `cd fp && make fp_api_check` が PASS。
- [ ] `fp_iter01/jt60/dt1` の 3 ケースが L-0 ベースラインと一致（fp 既存バイナリは無変更）。
- [ ] TR 既存テスト全 PASS。
- [ ] `fp_set_param("UNKNOWN_FOO", 1.0)` が `1` (FP_ERR_INVALID) を返す。

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| `fpcomm_parm` の宣言と SELECT CASE が型不整合 (`PN` の shape など) | 当該変数を一旦削除し、最小 10 個 (`RR/BB/NSMAX/NTMAX/DELT/PN[]/PT[]/MODELW[]/MODELC[]/EPSFP`) で受け入れ基準を満たす |
| `fp/tests/registry/Makefile` のリンクで未解決シンボル (mtxp 等) | `LIBS` に `$(LIB_MTX)` を追加、`include $(FP_DIR)/../mtxp/make.mtxp` を冒頭に挿入 |
| L-3 単独で 2 週超 | 最小 10 個で merge し、追加変数は L-4/L-5 期間中に sub-PR で増やす |

## 依存

- 上流: L-2 (fp_api foundation) マージ済み
- 後続: L-4 (libfpapi.so build) — 本 PR の `fp_param_registry.o` を共有 lib に含める
