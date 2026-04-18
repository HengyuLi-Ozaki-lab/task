# EQ ライブラリ化 Phase L-4: Shared Library Build (`libeqapi.so`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-1 で分離した `SRCS_CORE` と L-2/L-3 で追加する C ABI (`eq_api.f90`, `eq_state.f90`, `eq_param_registry.f90`) を中核に、graphics/menu を除外した position-independent shared library `eq/libeqapi.so` を生成する。既存の `eq`, `pl`, `ak` バイナリの **数値結果とバイト列は完全に不変**。

**Architecture:** TR の L-4 と同じ方針 (a) PIC リビルド方式を採用。`obj/pic/` と `mod_pic/` を **非 PIC build (`obj/`, `mod/`) と並列に** 配置し、`-fPIC -J mod_pic` で再コンパイル。依存ライブラリ (`bpsd/pl/lib/mtxp`) も in-tree で PIC リビルド（bpsd は `../../bpsd` 外部ソースを `obj/pic/bpsd/` に再コンパイル、TR L-4 と同じ戦略）。GSAF graphics (PAGES/PAGEE/GUCLIP/GDEFIN 等) は `eq_graphics_stubs.f90` を追加して no-op 化し、非 PIC libgsp/libg3d を一切リンクしない。リンク行は `--start-group/--end-group` で循環依存を解決、`-Wl,-soname,libeqapi.so` を付ける。

**Tech Stack:** GNU Make, gfortran (`-fPIC`, `-shared`, `-J`, `-soname`), `ld` (start-group/end-group), `ar`, `nm`, `dlopen` via `test_run_so.c`.

**出典:**
- `docs/superpowers/specs/2026-04-17-tr-library-design.md` §7 (ビルドシステム), §7.4 (PIC フォールバック), §A.4 (graphics 扱い), §A.11 (PIC 採用根拠)
- canonical: `tr/Makefile` L-4 block (lines 227–424)、`tr/tr_graphics_stubs.f90`
- 依存 plan: `docs/superpowers/plans/2026-04-18-tr-library-L4-shared-lib-build.md`、`docs/superpowers/plans/2026-04-18-ti-library-L4-shared-lib-build.md`、`docs/superpowers/plans/2026-04-18-wr-library-L4-shared-lib-build.md`

---

## Prerequisites

| Phase | 状況 | 目的 |
|---|---|---|
| **L-0** | マージ済み | baseline fixtures (`eq_*` 回帰テスト) が green |
| **L-1** plan | merge 済み / draft 修正待ち | `eq/Makefile` の `SRCS_CORE`/`SRCS_GRAPHICS`/`SRCS_MENU` 3 分割 |
| **L-2** plan | 未マージ | `eq_api.f90` (`eq_init/eq_run/eq_set_param/eq_get_state/eq_finalize`) + `eq_state.f90` (`eq_state_t` / `eq_get_state_impl`) + `eq/eq_api.h` |
| **L-3** plan | 未マージ | `eq_param_registry.f90` (scalar + 配列サブスクリプト `[i]`/`[i,j]` parser) |
| **f90 modernization** | in-progress | `.f` fixed-form → `.f90` free-form への段階的移行（本 L-4 は fixed/free 混在でも動くように書く） |

Reference: L-0 ✅、L-1 ✅ plan、L-2 plan、L-3 plan の順にマージされた develop を起点とする。

---

## 依存関係と PIC 化の影響範囲

`eq/Makefile` の現行 `eq` バイナリリンク順（概略）:

```
OBJS = $(SRCS_CORE:.f->.o) $(SRCS_GRAPHICS:.f->.o) $(SRCS_MENU:.f->.o)
LIBS = ../pl/libpl.a ../lib/libtask.a ../lib/libgrf.a ../lib/libmds.a \
       ../../bpsd/libbpsd.a $(FLIBS)
```

`libeqapi.so` で必要な依存（graphics 抜き = `libgrf.a` 除外、`libmds.a` は MDSplus が `nomdsplus.f` で無効なので除外可、`FLIBS` から GFLIBS/LIBLA/MDSLIB を落とす）:

| ライブラリ | パス | PIC 版 | 本フェーズの作業 |
|---|---|---|---|
| `libeq.a` 相当 (SRCS_CORE + SRCS_API) | `eq/` (本体) | → `eq/libeqapi.so` 中核 | `OBJ_CORE_PIC` + `OBJ_API_PIC` を直接 .so にリンク |
| `libpl.a` → `libpl_pic.a` | `pl/` | TR/TI/WR L-4 で作成済み or 新規 | なければ `pl/Makefile` に追加 |
| `libtask_pic.a` | `lib/` | TR/TI/WR L-4 で作成済み or 新規 | なければ `lib/Makefile` に追加 |
| `libmds_pic.a` | `lib/` | 同上 | 使わない予定だが依存解決のため PIC 化しておく |
| `libbpsd_pic.a` | `../bpsd/` | **外部ソース** | TR L-4 と同じく in-tree `obj/pic/bpsd/` に再ビルド |
| `libmtxnompi_pic.o`, `libmtxbnd_pic.o` | `mtxp/` | TR L-4 で作成済み or 新規 | なければ `mtxp/Makefile` に追加 |

**重要:** TR L-4 (merged) が `eq/libeq_pic.a` を既に追加している場合、そのターゲットは **そのまま再利用せず**、本 L-4 ではリンクしない（`SRCS_CORE` + `SRCS_API` を直接 `.o` で詰む方針＝TR L-4 Makefile 参照 line 379–383 同様）。理由: eq 自身が .so の中核なので、自身を `libeq_pic.a` として archive に詰めて `--whole-archive` するより、`.o` を直接リストしたほうが graphics 除外の可視性が高い。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `eq/Makefile` | 修正 | `libeqapi.so` ターゲット、`OBJDIR_PIC=obj/pic`、`MODDIR_PIC=mod_pic`、PIC コンパイルルール、bpsd in-tree rebuild、`eq_api_check_so` ターゲット、`libeqapi_inspect` ターゲット |
| `eq/eq_graphics_stubs.f90` | 新規 | GSAF no-op stubs (`PAGES`, `PAGEE`, `GUCLIP`, `GUDATE`, `GUTIME`, `GUFLSH`, `GDEFIN`, `GFRAME` 等)。`GUCLIP` のみ `REAL(X)` の cast を実装 |
| `eq/tests/c_abi/test_run_so.c` | 新規 | dlopen ベースの動作確認テスト（libeqapi.so を load し 5 関数を resolve、フルサイクル実行） |
| `pl/Makefile` | 修正（TR/TI/WR L-4 マージ済みならスキップ） | `libpl_pic.a` ターゲット追加 |
| `lib/Makefile` | 修正（同上） | `libtask_pic.a`, `libmds_pic.a` ターゲット追加 |
| `mtxp/Makefile` | 修正（同上） | `libmtxnompi_pic.o`, `libmtxbnd_pic.o` ターゲット追加 |

**方針:**
- 既存 `eq`, `pl`, `ak` バイナリのビルド (`obj/`, `mod/`, `libeq.a` 関連) は **完全に温存**。ターゲット `all` に `libeqapi.so` は **含めない**（既存 `make` 行動を変えない）。
- `libeqapi.so` は `make libeqapi.so` で明示 build。
- `eq_graphics_stubs.f90` は **libeqapi.so にしかリンクされない**（`OBJ_GR_STUBS_PIC` として `obj/pic/` 専用）。既存 `eq` バイナリは本物の `libgsp`/`libg3d` を引き続き使う。

---

## Task 1: ブランチと前提確認

- [ ] **Step 1: L-3 plan merge 確認と worktree**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git fetch origin develop
git log --oneline origin/develop | grep -iE "eq.*L-[0-3]|eq.*phase" | head -10
ls eq/eq_api.f90 eq/eq_state.f90 eq/eq_param_registry.f90 eq/eq_api.h 2>&1
```
Expected: L-1/L-2/L-3 が develop にマージ済み、4 ファイルが存在。未マージなら L-3 plan のブランチを base にする。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/eq-library-L4-shared-lib origin/develop
```

- [ ] **Step 3: 既存 PIC 対応の確認（TR/TI/WR L-4 が済んでいる可能性）**

Run:
```bash
for f in pl/Makefile lib/Makefile mtxp/Makefile; do
  echo "=== $f ==="
  grep -nE "libpl_pic|libtask_pic|libmds_pic|libmtxnompi_pic|libmtxbnd_pic|fPIC|obj_pic|obj/pic" $f | head -5
done
```
Expected: TR L-4 merge 後ならヒットする。ヒットしなければ本 L-4 で追加。

- [ ] **Step 4: L-0 回帰テストが green な状態から始める**

Run:
```bash
(cd eq && make 2>&1 | tail -3)
(cd test_run && ./run_tests.sh eq_* 2>&1 | tail -5)
```
Expected: eq バイナリ build OK、eq_* 回帰テスト PASS。

- [ ] **Step 5: マーカーコミット**

Run:
```bash
git commit --allow-empty -m "chore(eq): start Phase L-4 libeqapi.so build"
```

---

## Task 2: `eq_graphics_stubs.f90` を追加

**Files:**
- Create: `eq/eq_graphics_stubs.f90`

L-4 では `libeqapi.so` が GSAF (PAGES/PAGEE/GUCLIP/GDEFIN/GFRAME/MOVE/DRAW 等) を **一切呼ばない**ように `SRCS_GRAPHICS` を除外しているが、**CORE の一部ルーチンが GUCLIP を間接参照する可能性**を考慮し、かつ dlopen 時に unresolved symbol を出さないように以下の stub を用意する。

- [ ] **Step 1: 現状の CORE 側 GSAF 参照を grep で確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
for sym in PAGES PAGEE GUCLIP GUDATE GUTIME GUFLSH GDEFIN GFRAME MOVE DRAW SETCHS SETLIN SETFNT; do
  echo "--- $sym ---"
  grep -l "CALL $sym\|= $sym(" equcom.f90 equread.f90 eqlib.f90 eqinit.f eqcalc.f eqcalq.f eqcalv.f \
      eqsub.f eqfunc.f eqintf.f eqsplf.f equintf.f eq-eqdsk.f eq-qst.f eqgetp.f \
      newton.f invematrix.f equnit.f eqrppl.f eqbpsd.f 2>/dev/null | head -3
done
```
Expected: 大部分はヒットしないが、`equread.f90` が潜在的に `GUCLIP` を referencing する可能性あり（L-1 plan 注釈参照）。ヒットした最小セットだけ stub にする。

- [ ] **Step 2: `eq/eq_graphics_stubs.f90` 新規作成**

Create `/home/k-yoshimi/program/task-private/eq/eq_graphics_stubs.f90`:

```fortran
! eq_graphics_stubs.f90
!
! Phase L-4: minimal no-op stand-ins for the GSAF / grafix entry points
! that eq's SRCS_CORE references at run-time even though libeqapi.so
! excludes all real graphics output.
!
! Background: libgsp / libg3d (the real GSAF implementations) are
! distributed as non-PIC static archives and cannot be linked into a
! PIC shared object. libeqapi.so therefore provides these symbols as
! no-ops so that dlopen() succeeds and any code path that happens to
! reach a plotting hook returns silently. None of them are exercised
! by eq_init -> eq_run -> eq_get_state -> eq_finalize, so the no-op
! behaviour is safe. If a future caller needs real plots the right
! answer is to add a libeqgrf_pic.a (see design doc §A.4) rather
! than to extend these stubs.
!
! GUCLIP is the one exception: equread / eqgetp may cast REAL(8) ->
! REAL(4) via GUCLIP for time-series storage, so we implement the
! actual cast, matching tr_graphics_stubs.f90.

REAL FUNCTION GUCLIP(X)
  IMPLICIT NONE
  DOUBLE PRECISION, INTENT(IN) :: X
  GUCLIP = REAL(X)
END FUNCTION GUCLIP

SUBROUTINE PAGES
  IMPLICIT NONE
END SUBROUTINE PAGES

SUBROUTINE PAGEE
  IMPLICIT NONE
END SUBROUTINE PAGEE

SUBROUTINE GUDATE(KK)
  IMPLICIT NONE
  CHARACTER(LEN=*), INTENT(OUT) :: KK
  KK = ' '
END SUBROUTINE GUDATE

SUBROUTINE GUTIME(KK)
  IMPLICIT NONE
  CHARACTER(LEN=*), INTENT(OUT) :: KK
  KK = ' '
END SUBROUTINE GUTIME

SUBROUTINE GUFLSH
  IMPLICIT NONE
END SUBROUTINE GUFLSH

SUBROUTINE GDEFIN(IX1, IX2, IY1, IY2, XL, XR, YB, YT)
  IMPLICIT NONE
  REAL, INTENT(IN) :: IX1, IX2, IY1, IY2, XL, XR, YB, YT
END SUBROUTINE GDEFIN

SUBROUTINE GFRAME
  IMPLICIT NONE
END SUBROUTINE GFRAME

SUBROUTINE MOVE(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE MOVE

SUBROUTINE DRAW(X, Y)
  IMPLICIT NONE
  REAL, INTENT(IN) :: X, Y
END SUBROUTINE DRAW

SUBROUTINE SETCHS(H, A)
  IMPLICIT NONE
  REAL, INTENT(IN) :: H, A
END SUBROUTINE SETCHS

SUBROUTINE SETLIN(IPAT, INO, ICOL)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: IPAT, INO, ICOL
END SUBROUTINE SETLIN

SUBROUTINE SETFNT(IFONT)
  IMPLICIT NONE
  INTEGER, INTENT(IN) :: IFONT
END SUBROUTINE SETFNT
```

注:
- **GUCLIP 以外は no-op** で十分。
- Task 2 Step 1 で grep して実際には参照されていない stub は削除してもよいが、将来 SRCS_CORE に後から graphics 依存が混入した際の保険として残す。
- `eq_graphics_stubs.f90` は **SRCS にも SRCS_CORE にも含めない**。PIC ビルド専用で `OBJ_GR_STUBS_PIC` として `libeqapi.so` にのみリンク。

- [ ] **Step 3: コミット**

Run:
```bash
git add eq/eq_graphics_stubs.f90
git commit -m "feat(eq): add eq_graphics_stubs.f90 (GSAF no-ops for libeqapi.so)"
```

---

## Task 3: 依存ライブラリの PIC ターゲット追加（必要時のみ）

Task 1 Step 3 で確認済みの状態に応じて:

- TR/TI/WR L-4 でどれか一つでもマージ済み → `pl/libpl_pic.a`, `lib/libtask_pic.a`, `lib/libmds_pic.a`, `mtxp/libmtxnompi_pic.o`, `mtxp/libmtxbnd_pic.o` が既に存在 → **本タスクをスキップ**。
- マージなし → 以下を適用。

- [ ] **Step 1: `pl/Makefile` に `libpl_pic.a` ターゲット追加**

TR L-4 と同じテンプレート（`pl/Makefile` 末尾に追記）:

```makefile
# --- Phase L-4 PIC build (for libeqapi.so / libtrapi.so / ...) ---
OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)
MODINCLUDE_PIC= -I./$(MODDIR_PIC) -I../../bpsd/mod_pic

OBJS_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS:.f90=.o))

$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)
$(OBJDIR_PIC)/%.o: %.f
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFIXED) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

libpl_pic.a: $(OBJS_PIC)
	$(AR) rcs $@ $(OBJS_PIC)

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) libpl_pic.a
.PHONY: clean_pic
```

- [ ] **Step 2: `lib/Makefile` に `libtask_pic.a`, `libmds_pic.a` 追加**

同テンプレート。lib/ の SRCS 変数名が違う場合（`SRCS_TASK`, `SRCS_MDS` など）に合わせて調整。

- [ ] **Step 3: `mtxp/Makefile` に PIC .o ターゲット追加**

mtxp は archive ではなく single .o (`libmtxnompi.o`, `libmtxbnd.o`) として扱われる流儀。既存の非 PIC ビルドの隣に `-fPIC` で同名 suffix `_pic` を追加。TR L-4 の `tr/Makefile` line 362–365 参照。

- [ ] **Step 4: ビルドと確認**

Run:
```bash
(cd pl && make libpl_pic.a 2>&1 | tail -3 && ls libpl_pic.a)
(cd lib && make libtask_pic.a libmds_pic.a 2>&1 | tail -3 && ls lib*_pic.a)
(cd mtxp && make libmtxnompi_pic.o libmtxbnd_pic.o 2>&1 | tail -3 && ls lib*_pic.o)
```
Expected: 5 ファイル生成。readelf で PIC (`REL`) 確認:
```bash
readelf -h pl/obj/pic/plcom.o | grep Type  # "REL (Relocatable file)"
```

- [ ] **Step 5: 既存非 PIC ビルドが壊れていないこと**

Run:
```bash
(cd pl && make clean && make 2>&1 | tail -3)
(cd lib && make clean && make 2>&1 | tail -3)
```

- [ ] **Step 6: コミット**

Run:
```bash
git add pl/Makefile lib/Makefile mtxp/Makefile
git commit -m "build(pl,lib,mtxp): add PIC variants for shared library links"
```

---

## Task 4: `eq/Makefile` に PIC build tree と `libeqapi.so` ターゲット

**Files:**
- Modify: `eq/Makefile`

- [ ] **Step 1: PIC コンパイルルールと bpsd in-tree rebuild を追記**

`eq/Makefile` 末尾（既存 `clean`, `distclean` の後ろ）に、TR L-4 の同ブロック（`tr/Makefile` lines 227–383）を **eq 向けに翻訳して** 追記。以下テンプレート:

```makefile
# =====================================================================
# Phase L-4: libeqapi.so shared library build
#
# Builds a position-independent shared object that exposes the 5 C ABI
# entry points (eq_init, eq_run, eq_set_param, eq_get_state,
# eq_finalize) by linking SRCS_CORE + SRCS_API (plus eq_graphics_stubs)
# against PIC rebuilds of bpsd / pl / lib / mtxp.
#
# The PIC build is a *separate* tree at obj/pic/ + mod_pic/ so the
# existing non-PIC eq / pl / ak build is unaffected. bpsd sources live
# in ../../bpsd/ (outside this worktree); we rebuild them in-tree as
# obj/pic/bpsd/*.o (same strategy as tr/Makefile).
# =====================================================================

OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)
MODINCLUDE_PIC= -I./$(MODDIR_PIC) -I../pl/mod_pic -I../lib/mod_pic \
                -I../mtxp/mod_pic

# Pattern rules
$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(@D) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)
$(OBJDIR_PIC)/%.o: %.f
	@mkdir -p $(@D) $(MODDIR_PIC)
	$(FCFIXED) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

# --- bpsd in-tree PIC rebuild (mirrors tr/Makefile L-4) ---
BPSD_SRC=../../bpsd
OBJBPSD_PIC=$(OBJDIR_PIC)/bpsd/bpsd_kinds.o \
            $(OBJDIR_PIC)/bpsd/bpsd_constants.o \
            $(OBJDIR_PIC)/bpsd/bpsd_flags.o \
            $(OBJDIR_PIC)/bpsd/bpsd_libchar.o \
            $(OBJDIR_PIC)/bpsd/bpsd_libfio.o \
            $(OBJDIR_PIC)/bpsd/bpsd_libspl.o \
            $(OBJDIR_PIC)/bpsd/bpsd_types.o \
            $(OBJDIR_PIC)/bpsd/bpsd_types_internal.o \
            $(OBJDIR_PIC)/bpsd/bpsd_subs.o \
            $(OBJDIR_PIC)/bpsd/bpsd_shot.o \
            $(OBJDIR_PIC)/bpsd/bpsd_device.o \
            $(OBJDIR_PIC)/bpsd/bpsd_species.o \
            $(OBJDIR_PIC)/bpsd/bpsd_equ1D.o \
            $(OBJDIR_PIC)/bpsd/bpsd_metric1D.o \
            $(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o \
            $(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o \
            $(OBJDIR_PIC)/bpsd/bpsd_trsource.o \
            $(OBJDIR_PIC)/bpsd/bpsd_base.o

$(OBJDIR_PIC)/bpsd/%.o: $(BPSD_SRC)/%.f90
	@mkdir -p $(@D) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

# bpsd dependency order (copied verbatim from tr/Makefile lines 306-322)
$(OBJDIR_PIC)/bpsd/bpsd_constants.o:       $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_flags.o:            $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libchar.o:          $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libfio.o:           $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_libspl.o:           $(OBJDIR_PIC)/bpsd/bpsd_kinds.o
$(OBJDIR_PIC)/bpsd/bpsd_types.o:            $(OBJDIR_PIC)/bpsd/bpsd_kinds.o $(OBJDIR_PIC)/bpsd/bpsd_constants.o
$(OBJDIR_PIC)/bpsd/bpsd_types_internal.o:   $(OBJDIR_PIC)/bpsd/bpsd_types.o
$(OBJDIR_PIC)/bpsd/bpsd_subs.o:             $(OBJDIR_PIC)/bpsd/bpsd_types_internal.o $(OBJDIR_PIC)/bpsd/bpsd_libchar.o $(OBJDIR_PIC)/bpsd/bpsd_libfio.o $(OBJDIR_PIC)/bpsd/bpsd_libspl.o $(OBJDIR_PIC)/bpsd/bpsd_flags.o
$(OBJDIR_PIC)/bpsd/bpsd_shot.o:             $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_device.o:           $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_species.o:          $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_equ1D.o:            $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_metric1D.o:         $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o:          $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o:         $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_trsource.o:         $(OBJDIR_PIC)/bpsd/bpsd_subs.o
$(OBJDIR_PIC)/bpsd/bpsd_base.o:             $(OBJDIR_PIC)/bpsd/bpsd_shot.o $(OBJDIR_PIC)/bpsd/bpsd_device.o $(OBJDIR_PIC)/bpsd/bpsd_species.o $(OBJDIR_PIC)/bpsd/bpsd_equ1D.o $(OBJDIR_PIC)/bpsd/bpsd_metric1D.o $(OBJDIR_PIC)/bpsd/bpsd_plasmaf.o $(OBJDIR_PIC)/bpsd/bpsd_trmatrix.o $(OBJDIR_PIC)/bpsd/bpsd_trsource.o

.PHONY: bpsd_pic
bpsd_pic: $(OBJBPSD_PIC)

# --- Object sets for libeqapi.so ---
# SRCS_CORE is defined by L-1. SRCS_API is defined by L-2 (eq_api.f90,
# eq_state.f90, eq_param_registry.f90). SRCS_GRAPHICS and SRCS_MENU
# are excluded.
OBJ_CORE_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_CORE:.f=.o))
# Convert any .f90 suffix too (SRCS_CORE mixes .f and .f90)
OBJ_CORE_PIC:=$(OBJ_CORE_PIC:.f90=.o)
OBJ_API_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_API:.f90=.o))

# Graphics stubs that satisfy GUCLIP/PAGES/... without dragging in
# non-PIC libgsp/libg3d. PIC-only; never linked into the eq binary.
SRCS_GR_STUBS=eq_graphics_stubs.f90
OBJ_GR_STUBS_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_GR_STUBS:.f90=.o))

OBJ_LIBEQAPI= $(OBJ_CORE_PIC) $(OBJ_API_PIC) $(OBJ_GR_STUBS_PIC)

# Dependent PIC archives / objects.
LIBS_PIC=../pl/libpl_pic.a ../lib/libtask_pic.a ../lib/libmds_pic.a
LIBMTX_PIC=../mtxp/libmtxnompi_pic.o ../mtxp/libmtxbnd_pic.o

# Build dependent PIC libs on demand.
../pl/libpl_pic.a:
	(cd ../pl; $(MAKE) libpl_pic.a)
../lib/libtask_pic.a:
	(cd ../lib; $(MAKE) libtask_pic.a)
../lib/libmds_pic.a:
	(cd ../lib; $(MAKE) libmds_pic.a)
../mtxp/libmtxnompi_pic.o:
	(cd ../mtxp; $(MAKE) libmtxnompi_pic.o)
../mtxp/libmtxbnd_pic.o:
	(cd ../mtxp; $(MAKE) libmtxbnd_pic.o)

# --- The shared library itself ---
# gfortran drives the link so libgfortran is pulled in automatically.
# --start-group / --end-group resolves any cyclic references.
# We deliberately drop $(FLIBS) from the link: FLIBS pulls in non-PIC
# graphics archives (libg3d/libgsp/libgdp) via GFLIBS. libeqapi.so
# excludes SRCS_GRAPHICS so none of the gsaf calls are reachable;
# leaving GFLIBS in triggers R_X86_64_PC32 relocation errors when ld
# tries to copy non-PIC .text from libg3d.a into the .so.
libeqapi.so: $(OBJ_LIBEQAPI) $(OBJBPSD_PIC) $(LIBS_PIC) $(LIBMTX_PIC)
	$(FCFREE) -shared -fPIC -Wl,-soname,libeqapi.so \
	    $(OBJ_LIBEQAPI) $(OBJBPSD_PIC) $(LIBMTX_PIC) \
	    -Wl,--start-group $(LIBS_PIC) -Wl,--end-group \
	    -o libeqapi.so

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) libeqapi.so
	-rm -f $(EQ_API_SO_O) $(EQ_API_SO_BIN)

.PHONY: libeqapi_inspect
libeqapi_inspect: libeqapi.so
	@echo "=== file ==="
	@file libeqapi.so
	@echo "=== ldd ==="
	@ldd libeqapi.so
	@echo "=== exported eq_* symbols ==="
	@nm -D libeqapi.so | grep ' T eq_' || true
	@echo "=== undefined symbols (count) ==="
	@nm -D libeqapi.so | grep ' U ' | wc -l
	@echo "=== non-libc/gfortran undefined ==="
	@nm -D libeqapi.so | grep ' U ' | grep -vE '@(GLIBC|GCC|GFORTRAN)' | head -40
```

注記:
- `SRCS_CORE` が `.f` 主体で一部 `.f90` (equcom.f90, equread.f90, eqlib.f90) なので、`OBJ_CORE_PIC` は 2 段 substitution (`:.f=.o` → `:.f90=.o`) が必要。
- `FLIBS` 除外は TR L-4 と同じ理由。`libgsp/libg3d/libgdp` は non-PIC archive で `libeqapi.so` にリンクすると `R_X86_64_PC32` エラー。
- `eq_api.f90` が `USE equ_params` 等 SRCS_CORE の module を USE するため、`OBJ_CORE_PIC` は `OBJ_API_PIC` より先にリストする（pattern rule の依存順で足りるはずだが、link order も念のため揃える）。

- [ ] **Step 2: libeqapi.so をビルド試行**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make libeqapi.so 2>&1 | tee /tmp/libeqapi-build.log | tail -40
ls -la libeqapi.so
file libeqapi.so
```
Expected: `libeqapi.so` が生成、`ELF 64-bit LSB shared object`。

失敗パターン:
- `R_X86_64_PC32` → `FLIBS` を link から除外できていない / `GFLIBS` が混じっている
- `undefined reference to GUCLIP` → `OBJ_GR_STUBS_PIC` がリンク行から抜けている
- `module bpsd_kinds not found` → `MODINCLUDE_PIC` の `-I../../bpsd/mod_pic` が足りていない（bpsd in-tree なら `-I./mod_pic` で見える）

- [ ] **Step 3: エクスポートシンボル確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make libeqapi_inspect 2>&1 | tee /tmp/libeqapi-inspect.log
nm -D libeqapi.so | grep -E " T (eq_init|eq_run|eq_set_param|eq_get_state|eq_finalize)$"
```
Expected: 5 つの C シンボルが `T` (defined text) として表示。

- [ ] **Step 4: 既存 eq バイナリが byte-identical であること**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
md5sum eq pl ak > /tmp/eq-md5-before.txt
make clean && make 2>&1 | tail -3
md5sum eq pl ak > /tmp/eq-md5-after.txt
diff /tmp/eq-md5-before.txt /tmp/eq-md5-after.txt
```
Expected: `diff` の出力なし（= bit-exact）。

注: 正確なバイナリ一致は gfortran のバージョン/flags 依存 timestamps で乱れる場合がある。少なくとも L-0 回帰テスト（数値一致）は PASS すること。

- [ ] **Step 5: 回帰テスト**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
./run_tests.sh eq_* tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -10
```
Expected: 全 PASS。

- [ ] **Step 6: コミット**

Run:
```bash
git add eq/Makefile
git commit -m "build(eq): add libeqapi.so target with PIC rebuild of bpsd/pl/lib/mtxp"
```

---

## Task 5: dlopen テスト `eq_api_check_so`

**Files:**
- Create: `eq/tests/c_abi/test_run_so.c`
- Modify: `eq/Makefile`（`eq_api_check_so` ターゲット追加）

- [ ] **Step 1: `test_run_so.c` を作成**

Create `/home/k-yoshimi/program/task-private/eq/tests/c_abi/test_run_so.c`:

```c
/*
 * test_run_so.c — Phase L-4 dlopen smoke test for libeqapi.so.
 *
 * Dynamically loads libeqapi.so (via EQLIB_PATH env or default path),
 * resolves the 5 ABI symbols, runs a minimal
 *   eq_init -> eq_set_param -> eq_run -> eq_get_state -> eq_finalize
 * cycle, and asserts each return value is 0. This exercises the .so
 * exactly like the L-5 Python ctypes wrapper will.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include "eq_api.h"

typedef int (*fn_void_int)(void);
typedef int (*fn_int_int)(int);
typedef int (*fn_str_dbl)(const char*, double);
typedef int (*fn_state)(eq_state_t*);

static int fail = 0;
#define EXPECT_OK(call) do { int r = (call); \
    if (r != 0) { fprintf(stderr, "FAIL %s:%d: %s -> %d\n", \
        __FILE__, __LINE__, #call, r); fail++; } } while (0)

int main(int argc, char** argv) {
    const char* sopath = getenv("EQLIB_PATH");
    if (!sopath) sopath = (argc > 1) ? argv[1] : "./libeqapi.so";

    void* h = dlopen(sopath, RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        fprintf(stderr, "dlopen %s: %s\n", sopath, dlerror());
        return 2;
    }

    fn_void_int eq_init     = (fn_void_int) dlsym(h, "eq_init");
    fn_int_int  eq_run      = (fn_int_int)  dlsym(h, "eq_run");
    fn_str_dbl  eq_set_param= (fn_str_dbl)  dlsym(h, "eq_set_param");
    fn_state    eq_get_state= (fn_state)    dlsym(h, "eq_get_state");
    fn_void_int eq_finalize = (fn_void_int) dlsym(h, "eq_finalize");
    if (!eq_init || !eq_run || !eq_set_param || !eq_get_state || !eq_finalize) {
        fprintf(stderr, "dlsym: %s\n", dlerror());
        return 3;
    }

    EXPECT_OK(eq_init());
    /* Minimal analytic case (MDLEQF=0, RR=3.0, BB=3.0, RIP=1.0). */
    EXPECT_OK(eq_set_param("MDLEQF", 0.0));
    EXPECT_OK(eq_set_param("RR",     3.0));
    EXPECT_OK(eq_set_param("BB",     3.0));
    EXPECT_OK(eq_set_param("RIP",    1.0));
    EXPECT_OK(eq_set_param("NRGMAX", 65.0));
    EXPECT_OK(eq_set_param("NZGMAX", 65.0));
    EXPECT_OK(eq_set_param("NPSMAX", 65.0));

    EXPECT_OK(eq_run(0));

    eq_state_t st;
    EXPECT_OK(eq_get_state(&st));
    fprintf(stdout, "OK: nrgmax=%d nzgmax=%d npsmax=%d raxis=%g zaxis=%g qaxis=%g\n",
            st.nrgmax, st.nzgmax, st.npsmax, st.raxis, st.zaxis, st.qaxis);

    EXPECT_OK(eq_finalize());
    dlclose(h);
    return fail ? 1 : 0;
}
```

- [ ] **Step 2: `eq/Makefile` に `eq_api_check_so` ターゲットを追加**

Append to `eq/Makefile`:

```makefile
# ---------------------------------------------------------------------
# Phase L-4: eq_api_check_so
# Dynamically loads libeqapi.so via dlopen() and runs the full cycle.
# ---------------------------------------------------------------------
EQ_API_SMOKE_DIR=tests/c_abi
EQ_API_SO_C=$(EQ_API_SMOKE_DIR)/test_run_so.c
EQ_API_SO_O=$(EQ_API_SMOKE_DIR)/test_run_so.o
EQ_API_SO_BIN=$(EQ_API_SMOKE_DIR)/test_run_so

$(EQ_API_SO_O): $(EQ_API_SO_C) eq_api.h
	$(CC) $(CFLAGS_API) -I. -c -o $(EQ_API_SO_O) $(EQ_API_SO_C)

$(EQ_API_SO_BIN): $(EQ_API_SO_O)
	$(CC) -o $(EQ_API_SO_BIN) $(EQ_API_SO_O) -ldl

.PHONY: eq_api_check_so
eq_api_check_so: libeqapi.so $(EQ_API_SO_BIN)
	@echo "Phase L-4 eq_api_check_so: dlopen libeqapi.so + full cycle ..."
	@EQLIB_PATH=$(CURDIR)/libeqapi.so $(EQ_API_SO_BIN)
	@echo "Phase L-4 eq_api_check_so OK"
```

注: `CFLAGS_API` は L-2 plan で既に定義されている想定（`-I../eq` などの header path）。存在しなければ `CFLAGS` で代用。

- [ ] **Step 3: ビルド + 実行**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make eq_api_check_so 2>&1 | tail -15
```
Expected:
```
Phase L-4 eq_api_check_so: dlopen libeqapi.so + full cycle ...
OK: nrgmax=65 nzgmax=65 npsmax=65 raxis=... zaxis=... qaxis=...
Phase L-4 eq_api_check_so OK
```

- [ ] **Step 4: コミット**

Run:
```bash
git add eq/tests/c_abi/test_run_so.c eq/Makefile
git commit -m "test(eq): add eq_api_check_so dlopen-based smoke test"
```

---

## Task 6: 回帰テストと PR

- [ ] **Step 1: 既存 eq バイナリと L-0 回帰**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq && make clean && make 2>&1 | tail -3
(cd test_run && ./run_tests.sh eq_* tr_iter01 tr_m0904 tr_tst2 wr_* ti_* 2>&1 | tail -10)
```
Expected: 全 PASS。

- [ ] **Step 2: libeqapi.so ビルドが make clean 後も再現すること**

Run:
```bash
cd /home/k-yoshimi/program/task-private/eq
make clean_pic
make libeqapi.so 2>&1 | tail -5
make eq_api_check_so 2>&1 | tail -5
```
Expected: fresh ビルドから eq_api_check_so が PASS。

- [ ] **Step 3: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: 修正は `eq/Makefile` + `pl/Makefile` + `lib/Makefile` + `mtxp/Makefile`（TR/TI/WR L-4 未マージ時のみ）、新規は `eq/eq_graphics_stubs.f90` + `eq/tests/c_abi/test_run_so.c`。

- [ ] **Step 4: push と PR**

Run:
```bash
git push -u origin feature/eq-library-L4-shared-lib
gh pr create --base develop \
  --title "build(eq): Phase L-4 libeqapi.so via PIC rebuild" \
  --body "Phase L-4: generates libeqapi.so via PIC rebuild of SRCS_CORE+SRCS_API and bpsd/pl/lib/mtxp dependencies. eq_graphics_stubs.f90 provides GSAF no-ops. eq_api_check_so dlopen smoke test included. Existing eq/pl/ak binaries and L-0 regression unchanged. Design spec §7."
```

---

## Risk / Mitigation

| リスク | 影響 | 緩和策 |
|---|---|---|
| `R_X86_64_PC32` relocation error | .so ビルド失敗 | `FLIBS` から GFLIBS/LIBLA/MDSLIB を落とす（TR L-4 line 372–378 参照）。`libgsp`/`libg3d` は PIC 化せず引数から除外 |
| `equread.f90` が GUCLIP 以外の GSAF symbol を参照 | dlopen 時 undefined symbol | `eq_graphics_stubs.f90` に Task 2 Step 1 grep で見つかった symbol を追加 |
| bpsd の in-tree rebuild が `module not found` で失敗 | .so ビルド失敗 | TR L-4 の `OBJBPSD_PIC` 依存順を verbatim コピー（bpsd_kinds → constants → ... → base） |
| mtxp の MUMPS 依存で詰まる | .so ビルド失敗 | `libmtxnompi_pic.o`（MPI なし）と `libmtxbnd_pic.o`（MUMPS なし）のみリンクし、MUMPS/MPI symbol は参照しない |
| 既存 eq バイナリが byte-identical でない | L-0 回帰失敗 | 既存 `obj/`, `mod/`, `libeq.a` ターゲットを一切変更せず、`obj/pic/`, `mod_pic/` のみ新設 |
| `eq_graphics_stubs.f90` と `libgsp` の symbol 名衝突 | 既存 eq バイナリの link で multiple definition | stub は **SRCS に含めない**。PIC ビルド専用で `libeqapi.so` にのみ入る |
| gfortran の実装依存で `_` suffix が付く | dlsym で symbol 見つからず | `eq_api.f90` が `BIND(C, NAME="eq_init")` 等で明示命名する（L-2 plan 要件） |
| `SRCS_CORE` に fixed/free 混在 | PIC ルール漏れ | pattern rule を `%.o: %.f` と `%.o: %.f90` の 2 本用意（Task 4 Step 1） |

### フォールバック（設計書 §7.4）

| 試行 | 失敗内容 | 次の手 |
|---|---|---|
| (a) PIC rebuild | 本計画主軸 | デフォルト |
| (c) `-Wl,--whole-archive` 非 PIC | (a) 失敗時 | `LIBS_PIC` を `../pl/libpl.a` 等非 PIC に置換し `--whole-archive` でリンク（gfortran 古バージョンで失敗しやすい） |
| (b) ソース直統合 | (c) も失敗時 | 依存ソースを `eq/Makefile` に直接コピーして PIC ビルド。最終手段 |

---

## Testing Strategy

| レベル | テスト | 期待 |
|---|---|---|
| Fortran build | `make libeqapi.so` | ELF 64-bit LSB shared object が生成 |
| Symbol check | `make libeqapi_inspect` | `eq_init/eq_run/eq_set_param/eq_get_state/eq_finalize` 5 T シンボル。non-libc/gfortran undefined が 0 |
| C dlopen | `make eq_api_check_so` | フルサイクル return 0、`nrgmax/zaxis/qaxis` 正常値 |
| 既存バイナリ非破壊 | `make clean && make; md5sum eq pl ak` | L-0 baseline と同じ |
| 回帰 | `test_run/run_tests.sh eq_* tr_iter01 tr_m0904 tr_tst2` | 全 PASS |
| Fresh rebuild | `make clean_pic && make eq_api_check_so` | 空から PASS |

L-5 Python ctypes layer は本 L-4 成果物を前提とする。L-6 で 4 層テスト（Baseline / L-2 C / L-4 .so / L-5 Python）を統合検証。

---

## Deliverables

- [ ] `eq/libeqapi.so` が `make libeqapi.so` で生成される
- [ ] `nm -D libeqapi.so` で 5 C シンボル (`eq_init/eq_run/eq_set_param/eq_get_state/eq_finalize`) が `T` として表示
- [ ] `eq/eq_graphics_stubs.f90` が追加され、`libeqapi.so` にのみリンクされる
- [ ] `eq/tests/c_abi/test_run_so.c` + `eq_api_check_so` ターゲットで dlopen フルサイクル PASS
- [ ] `obj/pic/` と `mod_pic/` が非 PIC build (`obj/`, `mod/`) と並列に存在
- [ ] bpsd が in-tree (`obj/pic/bpsd/*.o`) で PIC リビルドされる
- [ ] `pl/libpl_pic.a`, `lib/libtask_pic.a`, `lib/libmds_pic.a`, `mtxp/libmtxnompi_pic.o`, `mtxp/libmtxbnd_pic.o` が生成可能（TR/TI/WR L-4 未マージ時のみ追加）
- [ ] 既存 `eq`, `pl`, `ak` バイナリのビルドが壊れていない（byte-identical が理想、最悪でも L-0 回帰 PASS）
- [ ] L-0 回帰テスト (`eq_*`, `tr_iter01/m0904/tst2`) 全 PASS
- [ ] `make clean_pic` で PIC tree のみクリーンアップ可能

## 依存

- 前段階: L-1 (SRCS 分割) ✅、L-2 (C ABI) plan、L-3 (param registry) plan
- 後段階: L-5 (`python/eqlib/` ctypes wrapper) が `libeqapi.so` を `ctypes.CDLL` で読み込む
