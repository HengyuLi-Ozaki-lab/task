# FP ライブラリ化 Phase L-4: 共有ライブラリ libfpapi.so ビルド 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-1〜L-3 で揃った `SRCS_CORE + SRCS_API` を **PIC ビルド** し、`fp/libfpapi.so` を生成する。Python の `ctypes` がロード可能な `.so`（`fp_init / fp_run / fp_set_param / fp_get_state / fp_finalize` シンボルが見える）を作る。既存の `fp` バイナリは温存する。

**Architecture:** TR Phase L 設計 (`tr_library-design.md` セクション 7) を fp 用に転用:

```
fp/Makefile
├── all: libs fp                          [既存]
└── libfpapi.so: $(OBJS_PIC_CORE) $(OBJS_PIC_API)
       $(FC) -shared -fPIC ... -o libfpapi.so

依存ライブラリ（PIC 対応版）
├── ../../bpsd/libbpsd_pic.a              [新規 target]
├── ../lib/libtask_pic.a                  [新規 target]
├── ../lib/libgrf_pic.a                   [graphics 不要なら省略可]
├── ../mtxp/libmtxp_pic.a                 [新規 target]
├── ../pl/libpl_pic.a                     [新規 target]
├── ../eq/libeq_pic.a                     [新規 target]
├── ../dp/libdp_pic.a                     [新規 target]
└── ../ob/libob_pic.a                     [新規 target]
```

各依存ライブラリの Makefile に `lib*_pic.a` ターゲットと `obj/pic/*.o` ルールを 5-10 行追加。`fpgout/fpgsub/fpcont/fpfout` (= `SRCS_GRAPHICS`) と `fpmenu` は **`libfpapi.so` には含めない**（graphics 依存を排除）。

**Tech Stack:** gfortran (`-fPIC -shared`)、Make、L-3 までで作成した Fortran ソース。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 7.1, 7.2, 7.3, 7.4。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `fp/Makefile` | 修正 | `OBJS_PIC_CORE`, `OBJS_PIC_API` の生成ルール、`libfpapi.so` ターゲット追加 |
| `../bpsd/Makefile` | 修正 | `libbpsd_pic.a` ターゲットと `obj/pic/*.o` ルール追加 |
| `lib/Makefile` | 修正 | `libtask_pic.a` (graphics-free) ターゲット追加 |
| `mtxp/Makefile` | 修正 | `libmtxp_pic.a` ターゲット追加 |
| `pl/Makefile` | 修正 | `libpl_pic.a` ターゲット追加 |
| `eq/Makefile` | 修正 | `libeq_pic.a` ターゲット追加 |
| `dp/Makefile` | 修正 | `libdp_pic.a` ターゲット追加 |
| `ob/Makefile` | 修正 | `libob_pic.a` ターゲット追加 |
| `fp/tests/c_abi/test_abi_link.c` | 新規 | `libfpapi.so` をロードして `fp_init` を直呼び出し|
| `fp/tests/c_abi/Makefile` | 修正 | `test_abi_link` ターゲット追加 |
| `test_run/README.md` | 修正 | `make libfpapi.so` の手順を追記 |

**graphics-free でいいか？** TR 設計では graphics 部品を `libtrapi.so` に **含めない**。fp も同様 — `fpgout/fpgsub/fpcont/fpfout` は SRCS_GRAPHICS に切り出してあるので除外できる。`libgrf_pic.a`（GSAF graphics）も不要。

---

## Task 1: ブランチ + 起点確認

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git checkout -b feature/fp-library-L4-shared-lib origin/develop
```

- [ ] **Step 2: L-3 ステートで build & test**

Run:
```bash
cd /home/k-yoshimi/program/task/fp && make 2>&1 | tail -3
make fp_api_check 2>&1 | tail -5
cd tests/registry && make check 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 既存 fp バイナリ + L-3 単体テスト + L-0 回帰 3 ケース全 PASS。

---

## Task 2: 依存ライブラリの PIC 版を順次追加

各 Makefile に同形の追加を行う。順序: `bpsd → lib → mtxp → pl → dp → eq → ob`（fp の依存順に従う）。

### Task 2.1: `../../bpsd/Makefile`

- [ ] **Step 1: 既存 `libbpsd.a` ルールを確認**

Run:
```bash
grep -n "libbpsd\.a\|^OBJ\|^SRC" /home/k-yoshimi/program/task/../bpsd/Makefile | head -20
```

- [ ] **Step 2: `libbpsd_pic.a` ターゲットを追加**

`../bpsd/Makefile` の末尾近く（`libbpsd.a` ルールの直後）に:

```makefile
# --- PIC build for shared-library use (fp Phase L-4) ---
OBJDIR_PIC = obj/pic
OBJS_PIC = $(addprefix $(OBJDIR_PIC)/, $(SRCS:.f90=.o))

$(OBJDIR_PIC)/%.o : %.f90 | $(OBJDIR_PIC)
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic -Imod_pic

$(OBJDIR_PIC):
	mkdir -p $(OBJDIR_PIC)
	mkdir -p mod_pic

libbpsd_pic.a: $(OBJS_PIC)
	$(LD) $(LDFLAGS) libbpsd_pic.a $(OBJS_PIC)
```

注: `bpsd` の `SRCS` 変数名と `OBJDIR` 変数名は実 Makefile に合わせる。`$(SRCS)` ではなく個別ファイル名のリストかもしれない。

- [ ] **Step 3: ビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/../bpsd
make libbpsd_pic.a 2>&1 | tail -10
ls -la libbpsd_pic.a
```
Expected: エラーなし、`libbpsd_pic.a` が生成される。

### Task 2.2: `lib/Makefile`

- [ ] **Step 1: graphics-free な `libtask` 部分を抽出**

Run:
```bash
grep -n "^SRCS\|^libtask\|^libgrf" /home/k-yoshimi/program/task/lib/Makefile | head -10
```
Expected: `libtask.a` の SRCS と `libgrf.a` の SRCS が分かれていることを確認。

- [ ] **Step 2: `libtask_pic.a` ターゲット追加**

`lib/Makefile` の末尾に同形パターンで `libtask_pic.a` を追加（Task 2.1 と同様）。`libgrf.a` 側は `libfpapi.so` には不要なため触らない（必要なら後で `libgrf_pic.a` も追加可能）。

- [ ] **Step 3: ビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/lib
make libtask_pic.a 2>&1 | tail -5
ls -la libtask_pic.a
```

### Task 2.3-2.7: `mtxp, pl, dp, eq, ob` の Makefile

各々で同じパターンを追加:

```makefile
OBJDIR_PIC = obj/pic
OBJS_PIC = $(addprefix $(OBJDIR_PIC)/, $(SRCS:.f90=.o))

$(OBJDIR_PIC)/%.o : %.f90 | $(OBJDIR_PIC)
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic -Imod_pic \
	    -I../<deps>/mod_pic -I../../bpsd/mod_pic

$(OBJDIR_PIC):
	mkdir -p $(OBJDIR_PIC) mod_pic

lib<name>_pic.a: $(OBJS_PIC)
	$(LD) $(LDFLAGS) lib<name>_pic.a $(OBJS_PIC)
```

`<deps>` 部は依存先の `mod_pic` を `-I` で参照（pl は bpsd だけ、eq は pl + bpsd、dp は pl + bpsd、ob は pl + eq + dp + bpsd）。

- [ ] **Step 1-5: 各々のディレクトリでビルド確認**

Run:
```bash
cd /home/k-yoshimi/program/task/mtxp && make libmtxp_pic.a 2>&1 | tail -3
cd /home/k-yoshimi/program/task/pl   && make libpl_pic.a   2>&1 | tail -3
cd /home/k-yoshimi/program/task/dp   && make libdp_pic.a   2>&1 | tail -3
cd /home/k-yoshimi/program/task/eq   && make libeq_pic.a   2>&1 | tail -3
cd /home/k-yoshimi/program/task/ob   && make libob_pic.a   2>&1 | tail -3
ls /home/k-yoshimi/program/task/{pl,dp,eq,ob,mtxp}/lib*_pic.a /home/k-yoshimi/program/task/../bpsd/libbpsd_pic.a
```
Expected: 全 `.a` ファイル生成。

- [ ] **Step 6: コミット（依存 PIC ライブラリ群、まとめて 1 PR 内 1 commit）**

Run:
```bash
cd /home/k-yoshimi/program/task
git add ../bpsd/Makefile lib/Makefile mtxp/Makefile pl/Makefile dp/Makefile eq/Makefile ob/Makefile
git commit -m "build: add PIC library targets in deps for libfpapi.so"
```

---

## Task 3: `fp/Makefile` に `libfpapi.so` ターゲット追加

**Files:**
- Modify: `fp/Makefile`

- [ ] **Step 1: PIC 版 OBJ パターンを追加**

`fp/Makefile` の `SRCS_API` ブロック直後に:

```makefile
# --- PIC build for libfpapi.so (Phase L-4) ---
OBJDIR_PIC      = ./obj/pic
OBJS_PIC_CORE   = $(addprefix $(OBJDIR_PIC)/, $(SRCS_CORE:.f90=.o))
OBJS_PIC_API    = $(addprefix $(OBJDIR_PIC)/, $(SRCS_API:.f90=.o))

MODINCLUDE_PIC = -I./mod_pic -I../ob/mod_pic \
                 -I../dp/mod_pic -I../pl/mod_pic -I../eq/mod_pic \
                 -I../lib/mod_pic -I../mtxp/mod_pic \
                 -I../../bpsd/mod_pic

$(OBJDIR_PIC)/%.o : %.f90 | $(OBJDIR_PIC)
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic $(MODINCLUDE_PIC)

$(OBJDIR_PIC):
	mkdir -p $(OBJDIR_PIC) mod_pic

LIBS_PIC = ../ob/libob_pic.a ../pl/libpl_pic.a ../eq/libeq_pic.a \
           ../dp/libdp_pic.a ../lib/libtask_pic.a \
           ../mtxp/libmtxp_pic.a ../../bpsd/libbpsd_pic.a

libfpapi.so: $(OBJS_PIC_CORE) $(OBJS_PIC_API) $(LIBS_PIC)
	$(FC) -shared -fPIC \
	    $(OBJS_PIC_CORE) $(OBJS_PIC_API) \
	    $(LIBS_PIC) \
	    $(LIB_MTX) $(FLIBS) \
	    -o libfpapi.so
```

注: `$(LIB_MTX)` は `mtxp/make.mtxp` で定義されている既定値（band solver 等）。fp の対話シナリオで使われているのと同じものを共有。`$(FLIBS)` は `make.header` のリンカフラグ。

- [ ] **Step 2: `libs_pic` ターゲット（依存 PIC を一括ビルド）**

`fp/Makefile` の `libs:` ターゲット直下に:

```makefile
libs_pic:
	(cd ../../bpsd; make libbpsd_pic.a)
	(cd ../lib;    make libtask_pic.a)
	(cd ../mtxp;   make libmtxp_pic.a)
	(cd ../pl;     make libpl_pic.a)
	(cd ../dp;     make libdp_pic.a)
	(cd ../eq;     make libeq_pic.a)
	(cd ../ob;     make libob_pic.a)
```

- [ ] **Step 3: ビルド試行**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make libs_pic 2>&1 | tail -10
make libfpapi.so 2>&1 | tail -20
ls -la libfpapi.so
```
Expected: `libfpapi.so` が生成される。サイズは数 MB 程度。

- [ ] **Step 4: シンボル検証**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
nm -D libfpapi.so | grep -E " T (fp_init|fp_run|fp_set_param|fp_get_state|fp_finalize)$"
```
Expected: 5 シンボル全てが `T`（global text）として export されている。

- [ ] **Step 5: 不要なシンボル衝突チェック**

Run:
```bash
ldd /home/k-yoshimi/program/task/fp/libfpapi.so 2>&1 | head
nm -D /home/k-yoshimi/program/task/fp/libfpapi.so | grep -i "graphic\|gscls\|gsopen" | head -3
```
Expected: GSAF graphics シンボルは含まれない (`fp_menu` も除外しているため対話依存はゼロ)。

---

## Task 4: C リンク smoke test

**Files:**
- Create: `fp/tests/c_abi/test_abi_link.c`
- Modify: `fp/tests/c_abi/Makefile`

L-2 では compile-only smoke だった。L-4 では `libfpapi.so` をリンクして `fp_init` を実呼び出しする。

- [ ] **Step 1: テスト C プログラム**

作成: `fp/tests/c_abi/test_abi_link.c`

```c
/* Phase L-4 link smoke test for libfpapi.so. */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fp_api.h"

int main(void) {
    int rc;
    fp_state_t st;

    rc = fp_init();
    if (rc != FP_OK) {
        fprintf(stderr, "fp_init failed: %d\n", rc);
        return 1;
    }

    /* set a known parameter (L-3 fp_param_set must accept it) */
    rc = fp_set_param("RR", 6.5);
    if (rc != FP_OK) {
        fprintf(stderr, "fp_set_param(RR) failed: %d\n", rc);
        return 2;
    }

    /* unknown parameter must return INVALID */
    rc = fp_set_param("NO_SUCH_VAR", 1.0);
    if (rc != FP_ERR_INVALID) {
        fprintf(stderr, "expected INVALID for unknown, got %d\n", rc);
        return 3;
    }

    /* get_state before run is allowed (state may be partly zero) */
    memset(&st, 0, sizeof(st));
    rc = fp_get_state(&st);
    if (rc != FP_OK) {
        fprintf(stderr, "fp_get_state failed: %d\n", rc);
        return 4;
    }
    printf("nrmax=%d nsamax=%d timefp=%g\n",
           st.nrmax, st.nsamax, st.timefp);

    rc = fp_finalize();
    if (rc != FP_OK) {
        fprintf(stderr, "fp_finalize failed: %d\n", rc);
        return 5;
    }

    printf("L-4 link smoke OK\n");
    return 0;
}
```

- [ ] **Step 2: Makefile に link target を追加**

`fp/tests/c_abi/Makefile` に追記:

```makefile
# --- L-4 link smoke (requires fp/libfpapi.so) ---
FP_LIB_DIR ?= ../..
LDFLAGS_FPAPI = -L$(FP_LIB_DIR) -Wl,-rpath,$(abspath $(FP_LIB_DIR)) -lfpapi -lgfortran -lm

test_abi_link: test_abi_link.c $(FP_LIB_DIR)/libfpapi.so $(FP_LIB_DIR)/fp_api.h
	$(CC) $(CFLAGS) -I$(FP_LIB_DIR) test_abi_link.c $(LDFLAGS_FPAPI) -o test_abi_link

.PHONY: link_check
link_check: test_abi_link
	./test_abi_link

clean:
	-rm -f test_abi_smoke.o test_abi_link
```

`-Wl,-rpath` を使うことで実行時に `fp/libfpapi.so` を自動ロードできる（`LD_LIBRARY_PATH` 不要）。

- [ ] **Step 3: 走らせる**

Run:
```bash
cd /home/k-yoshimi/program/task/fp/tests/c_abi
make link_check 2>&1
```
Expected: `L-4 link smoke OK` の最終行。`nrmax=...` の出力（fp_init 直後なので 0 でも OK）。

- [ ] **Step 4: 全テスト再走（回帰確認）**

Run:
```bash
cd /home/k-yoshimi/program/task/fp && make veryclean && make
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 全 PASS。`fp` バイナリは依然不変。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add fp/Makefile fp/tests/c_abi/test_abi_link.c fp/tests/c_abi/Makefile
git commit -m "feat(fp): add libfpapi.so target + C link smoke test"
```

---

## Task 5: README 更新

- [ ] **Step 1: `test_run/README.md` の FP セクション末尾に追記**

```markdown
### FP shared library libfpapi.so (Phase L-4)

Build:

    cd fp && make libs_pic && make libfpapi.so

Verify symbols:

    nm -D fp/libfpapi.so | grep ' T fp_'

C link smoke test:

    cd fp/tests/c_abi && make link_check

`libfpapi.so` excludes graphics (`fpgout, fpgsub, fpcont, fpfout`)
and `fpmenu` to keep the surface minimal for ctypes use in L-5.
```

- [ ] **Step 2: コミット**

```bash
cd /home/k-yoshimi/program/task
git add test_run/README.md
git commit -m "docs(fp): document libfpapi.so build and link smoke"
```

---

## 受け入れ基準

- [ ] `fp/libfpapi.so` が `make libfpapi.so` で生成される（5 つの依存 `lib*_pic.a` が先にビルドされる）。
- [ ] `nm -D fp/libfpapi.so | grep ' T fp_'` で `fp_init/fp_run/fp_set_param/fp_get_state/fp_finalize` の 5 シンボルが見える。
- [ ] `cd fp/tests/c_abi && make link_check` で `L-4 link smoke OK` を出力。
- [ ] `fp` バイナリの `make veryclean && make` が成功し、`fp_iter01/jt60/dt1` ベースラインと bit-exact 一致。
- [ ] TR 既存テスト全 PASS（無関係な依存 lib に副作用なし）。

## 撤退条件 / フォールバック

| 状況 | 対応（出典: tr_library-design.md 7.4 節） |
|---|---|
| **PIC リビルド (案 a) が一部 lib で動かない** | フォールバック (b): 該当 lib のソースを `libfpapi.so` に直接統合。具体的には `fp/Makefile` で `$(addprefix obj/pic/,$(SRCS_OF_FAILING_LIB:.f90=.o))` を `libfpapi.so` の依存に追加 |
| **`-Wl,--whole-archive` 案 (c)** | (b) より優先したい場合に試す。`libpl_pic.a` 等 `.a` を `--whole-archive` で囲む |
| **`mtxp` の MUMPS/PETSc バックエンドが PIC でビルドできない** | デフォルト `LIB_MTX_BND` (band solver) に固定し、それだけ PIC 化。MUMPS/PETSc は L-4 スコープ外 |
| **GSAF (`libgrf`) の参照が `fpprep.f90` 等から漏れて入ってくる** | 該当箇所を `#ifdef NO_GRAPHICS` でくくる **のではなく**、SRCS_CORE から除外して L-4 のスコープを再評価。最悪 `libgrf_pic.a` も追加 |
| **rpath が動かず実行時にロードできない** | `LD_LIBRARY_PATH=fp/ ./test_abi_link` で回避し、README に明記 |
| **L-4 が 1 ヶ月超** | 撤退して L-5 を Python ctypes ではなく f2py 経由に切替（仕様変更）|

## 依存

- 上流: L-3 (fp_param_registry) マージ済み
- 後続: L-5 (Python ラッパ) — 本 PR でできた `libfpapi.so` を ctypes でロード
