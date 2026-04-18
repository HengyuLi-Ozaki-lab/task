# WR ライブラリ化 Phase L-4: Shared Library Build (`libwrapi.so`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-3 までで揃った C ABI を実際に Python から `dlopen` できる形にする。`wr/Makefile` に `libwrapi.so` ターゲットを追加し、`SRCS_LIB = $(SRCS_CORE) $(SRCS_API)` を `-fPIC` 付きで再ビルドし、依存ライブラリ (`libdp_pic.a`, `libpl_pic.a`, `libtask_pic.a`, `libbpsd_pic.a` など) も PIC 再ビルドする。

**Architecture:** TR の Phase L-4 と同じ「PIC リビルド方式（案 a）」を採用。`obj_pic/`, `mod_pic/` を別ディレクトリにして `-fPIC` ビルドを既存の `-fPIE` なしビルドと共存させる。`libwrapi.so` は graphics 抜き、menu 抜き、`wr_api/wr_state/wr_param_registry` のみ公開。失敗時のフォールバックとして「案 b: 直接ソース統合」「案 c: `-Wl,--whole-archive`」を準備。

**Tech Stack:** GNU Make, gfortran (`-fPIC`, `-shared`), 既存依存ライブラリ群 (eq, dp, pl, lib, mtxp, bpsd)。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 7（ビルドシステム）と Phase L-4。

---

## 依存ライブラリと PIC 化の影響範囲

`wr/Makefile` の現状リンク順:
```
LIBS = libwr.a  ../dp/libdp.a ../eq/libeq.a ../pl/libpl.a \
       ../lib/libtask.a ../lib/libgrf.a ../../bpsd/libbpsd.a
```

`libwrapi.so` で必要になるもの (graphics 抜き = `libgrf.a` 不要、`libgrf` 経由のシンボルが core に潜んでいないか L-2 のスモークテストで検証済み):

| ライブラリ | パス | 既存 PIC ビルド? | 本フェーズの作業 |
|---|---|---|---|
| `libwr_api.a` | `wr/libwrapi_pic.a`（中間） | なし | `SRCS_LIB` を `-fPIC` でビルドして新規生成 |
| `libdp.a` → `libdp_pic.a` | `dp/` | なし | `dp/Makefile` に PIC ターゲット追加 |
| `libeq.a` → `libeq_pic.a` | `eq/` | なし（または TR L-4 で追加済み） | TR L-4 と共有可能なら再利用、無ければ追加 |
| `libpl.a` → `libpl_pic.a` | `pl/` | なし（または TR L-4 で追加済み） | 同上 |
| `libtask.a` → `libtask_pic.a` | `lib/` | なし（または TR L-4 で追加済み） | 同上 |
| `libbpsd.a` → `libbpsd_pic.a` | `../bpsd/` | なし（または TR L-4 で追加済み） | 同上 |
| `libmtx_*` | `mtxp/` | mtxp 内部で PIC 対応している場合あり | `make.mtxp` を点検し必要なら追加 |

**重要:** TR L-4 が先にマージされている場合、`eq/libeq_pic.a, pl/libpl_pic.a, lib/libtask_pic.a, ../bpsd/libbpsd_pic.a` が既に存在する可能性が高い。**まず `git log --oneline develop -- eq/Makefile pl/Makefile lib/Makefile` で TR L-4 の有無を確認**し、既存なら再利用する。新規追加の場合は TR L-4 で追加されたパターンを真似る。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wr/Makefile` | 修正 | `libwrapi.so` ターゲット、PIC オブジェクトディレクトリ `obj_pic/` と mod ディレクトリ `mod_pic/`、`SRCS_LIB`, PIC 用ビルドルール |
| `dp/Makefile` | 修正（既に PIC 対応済みなら追加なし） | `libdp_pic.a` ターゲットを追加 |
| `eq/Makefile` | 修正（同上） | `libeq_pic.a` ターゲット |
| `pl/Makefile` | 修正（同上） | `libpl_pic.a` ターゲット |
| `lib/Makefile` | 修正（同上） | `libtask_pic.a` ターゲット |
| `../bpsd/Makefile` | 修正（同上） | `libbpsd_pic.a` ターゲット |
| `wr/tests/c_abi/Makefile` | 修正 | `libwrapi.so` 経由でリンクする版テスト `test_abi_so` を追加 |

**方針:**
- 既存 `wr` バイナリのビルド（`libwr.a` ベース）は完全に温存。
- `libwrapi.so` は別 build path (`obj_pic/`, `mod_pic/`)。
- TR L-4 で同じ依存ライブラリの PIC 化を済ませている場合は、新規追加せず既存ターゲットを使う。

---

## Task 1: ブランチ作成 + TR L-4 状況確認

**Files:** なし

- [ ] **Step 1: develop 最新 + ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L4-shared-lib
```

- [ ] **Step 2: TR L-4 (`libtrapi.so`) が develop に merge されているかチェック**

Run:
```bash
cd /home/k-yoshimi/program/task
git log --oneline develop -- tr/Makefile | head -5
ls -la tr/libtrapi.so 2>&1 | head -1
ls -la dp/libdp_pic.a pl/libpl_pic.a lib/libtask_pic.a ../bpsd/libbpsd_pic.a 2>&1
grep -n "libdp_pic\|libpl_pic\|libtask_pic\|libbpsd_pic\|fPIC" /home/k-yoshimi/program/task/dp/Makefile /home/k-yoshimi/program/task/pl/Makefile /home/k-yoshimi/program/task/lib/Makefile /home/k-yoshimi/program/task/../bpsd/Makefile 2>&1 | head -30
```
Expected:
- `tr/libtrapi.so` が既にあれば、依存ライブラリの PIC 化も完了している → Task 4-7 を skip 可能。
- 無ければ、本フェーズで dp/eq/pl/lib/bpsd の PIC ターゲットを追加する。

- [ ] **Step 3: マーカーコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wr): start Phase L-4 libwrapi.so build"
```

---

## Task 2: WR の PIC ビルドルールを Makefile に追加

**Files:**
- Modify: `wr/Makefile`

- [ ] **Step 1: PIC オブジェクトディレクトリを作成**

Run:
```bash
mkdir -p /home/k-yoshimi/program/task/wr/obj_pic /home/k-yoshimi/program/task/wr/mod_pic
```

- [ ] **Step 2: Makefile に PIC ルールと libwrapi.so ターゲットを追加**

Modify `/home/k-yoshimi/program/task/wr/Makefile`. Append at the end (after existing rules):

```make
# ============================================================
# Phase L-4: libwrapi.so (Python/C-callable shared library)
# ============================================================

OBJDIR_PIC = ./obj_pic
MOD_PIC    = ./mod_pic
PICFLAGS   = -fPIC

MODINCLUDE_PIC = -I./$(MOD_PIC) -I../pl/mod_pic -I../dp/mod_pic -I../eq/mod_pic \
                 -I../lib/mod_pic -I../mtxp/mod_pic -I../../bpsd/mod_pic

# Source set for the library (graphics + menu intentionally excluded).
SRCS_LIB  = $(SRCS_CORE) $(SRCS_API)
OBJS_PIC  = $(addprefix $(OBJDIR_PIC)/, $(SRCS_LIB:.f90=.o))

# PIC build rules (separate object dir so that the regular wr build is unaffected).
$(OBJDIR_PIC)/%.o: %.f90 | $(OBJDIR_PIC) $(MOD_PIC)
	$(FCFREE) $(FFLAGS) $(PICFLAGS) -c $< -o $@ -J$(MOD_PIC) $(MODINCLUDE_PIC)

$(OBJDIR_PIC):
	mkdir -p $(OBJDIR_PIC)

$(MOD_PIC):
	mkdir -p $(MOD_PIC)

# PIC dependency stubs (delegated to sister modules).
../dp/libdp_pic.a:
	(cd ../dp; make libdp_pic.a)
../eq/libeq_pic.a:
	(cd ../eq; make libeq_pic.a)
../pl/libpl_pic.a:
	(cd ../pl; make libpl_pic.a)
../lib/libtask_pic.a:
	(cd ../lib; make libtask_pic.a)
../../bpsd/libbpsd_pic.a:
	(cd ../../bpsd; make libbpsd_pic.a)

LIBS_PIC = ../dp/libdp_pic.a ../eq/libeq_pic.a ../pl/libpl_pic.a \
           ../lib/libtask_pic.a ../../bpsd/libbpsd_pic.a

libwrapi.so: $(OBJS_PIC) $(LIBS_PIC)
	$(FC) -shared $(PICFLAGS) $(OBJS_PIC) \
	    -Wl,--start-group $(LIBS_PIC) -Wl,--end-group \
	    $(LIB_MTX) $(FLIBS) -o $@

libwrapi: libwrapi.so

clean-pic:
	-rm -rf $(OBJDIR_PIC) $(MOD_PIC) libwrapi.so

.PHONY: libwrapi clean-pic
```

注: `LIB_MTX` は既存 Makefile 上部の `mtxp/make.mtxp` 経由で定義されている。MPI なしビルドであれば `LIB_MTX` が空、または `LIB_MTX_BND` 等で内部解決される。

- [ ] **Step 3: WR 単体（依存抜き）で PIC オブジェクトが作れるか確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make $(make -p 2>&1 | grep -E "^OBJS_PIC" | head -1 | awk -F= '{print $2}') 2>&1 | tail -10
ls obj_pic/ 2>&1 | head -10
```
Expected: `wrcomm.o, wrinit.o, ..., wr_api.o, wr_state.o, wr_param_registry.o` 等が `obj_pic/` に作られる。

依存 `.mod` が `pl/mod_pic` 等にまだ無い場合は、Task 3-7 を先に進めてから戻る。

- [ ] **Step 4: コミット（依存ビルドはまだ）**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/Makefile
git commit -m "build(wr): add PIC build rules and libwrapi.so target (deps TBD)"
```

---

## Task 3: 依存ライブラリの PIC 化（または既存再利用）

各依存 Makefile に対し、TR L-4 で既に PIC 対応済みなら **何もしない**、未対応ならパターン追加する。

**ガイドラインのテンプレ** (例: `dp/Makefile`):

```make
# --- Phase L-4: PIC objects for shared libraries (libdp_pic.a) ---

OBJDIR_PIC = ./obj_pic
MOD_PIC    = ./mod_pic

OBJS_PIC = $(addprefix $(OBJDIR_PIC)/, $(SRCS:.f90=.o))

$(OBJDIR_PIC)/%.o: %.f90 | $(OBJDIR_PIC) $(MOD_PIC)
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -J$(MOD_PIC) -I./$(MOD_PIC) \
	    -I../pl/mod_pic -I../../bpsd/mod_pic

$(OBJDIR_PIC):
	mkdir -p $(OBJDIR_PIC)

$(MOD_PIC):
	mkdir -p $(MOD_PIC)

libdp_pic.a: $(OBJS_PIC)
	$(AR) rcs $@ $(OBJS_PIC)

clean-pic:
	-rm -rf $(OBJDIR_PIC) $(MOD_PIC) libdp_pic.a

.PHONY: clean-pic
```

`-I` の依存はモジュールごとに調整（`pl` は `bpsd` のみ、`eq` は `pl` と `bpsd`、`dp` は `pl` と `bpsd`、`lib` は依存なしか `bpsd` のみ等）。

- [ ] **Step 1: TR L-4 が既に各 Makefile に PIC ターゲットを追加しているか再確認**

Run:
```bash
for d in dp eq pl lib; do
  echo "=== $d ==="
  grep -E "libdp_pic|libeq_pic|libpl_pic|libtask_pic|fPIC" /home/k-yoshimi/program/task/$d/Makefile | head -3
done
echo "=== bpsd ==="
grep -E "libbpsd_pic|fPIC" /home/k-yoshimi/program/task/../bpsd/Makefile | head -3
```

- [ ] **Step 2: 既存の場合 → Step 4 へ。未対応の場合は Step 3 で各 Makefile に追加**

各 Makefile に上記テンプレを (依存方向に応じて `-I`/`USE` ライブラリを調整して) 追加する:

- `../bpsd/Makefile`: 依存なし（テンプレから `-I../pl/mod_pic -I../../bpsd/mod_pic` を削除）
- `lib/Makefile`: 依存最小（`-I../../bpsd/mod_pic` のみ）
- `pl/Makefile`: `-I../../bpsd/mod_pic`
- `eq/Makefile`: `-I../pl/mod_pic -I../../bpsd/mod_pic`
- `dp/Makefile`: `-I../pl/mod_pic -I../../bpsd/mod_pic`

各 Makefile への追加は別コミットに分ける（後で revert しやすくするため）:

```bash
cd /home/k-yoshimi/program/task
git add ../bpsd/Makefile && git commit -m "build(bpsd): add libbpsd_pic.a PIC target"
git add lib/Makefile && git commit -m "build(lib): add libtask_pic.a PIC target"
git add pl/Makefile && git commit -m "build(pl): add libpl_pic.a PIC target"
git add eq/Makefile && git commit -m "build(eq): add libeq_pic.a PIC target"
git add dp/Makefile && git commit -m "build(dp): add libdp_pic.a PIC target"
```

- [ ] **Step 3: 個別ビルドテスト**

Run:
```bash
for d in ../bpsd lib pl eq dp; do
  echo "=== $d ==="
  cd /home/k-yoshimi/program/task/$d
  make libbpsd_pic.a 2>&1 | tail -3 || \
    make lib$(basename $d)_pic.a 2>&1 | tail -3 || \
    make libtask_pic.a 2>&1 | tail -3
done
```
Expected: 各 `lib*_pic.a` が生成される。

- [ ] **Step 4: 既に PIC が存在 (TR L-4 由来) ならスキップして Task 4 へ**

---

## Task 4: `libwrapi.so` をビルド

**Files:** なし（ビルドのみ）

- [ ] **Step 1: 全依存を含めてビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make libwrapi.so 2>&1 | tail -30
ls -la libwrapi.so
```
Expected: `libwrapi.so` が生成される（数 MB）。

リンク時に `gscls_, gsopen_, gtmark_` 等の GSAF シンボル未定義エラーが出る場合 → `wr_api.f90 → wrcomm` 経由で `wrgout` を引っ張っていないか確認。`wrgout` は `SRCS_GRAPHICS` にあるので `OBJS_PIC` には入らないはずだが、`wrcomm` が間接的に `plgout` を `USE` しているとここで詰まる。詰まったら `wrcomm.f90` の `USE` を点検。

未定義のままどうしても解決しない場合の最終手段:
```make
libwrapi.so: $(OBJS_PIC) $(LIBS_PIC)
	$(FC) -shared $(PICFLAGS) -Wl,--unresolved-symbols=ignore-in-shared-libs \
	    $(OBJS_PIC) ...
```
（ただし呼び出し時に load failure するリスクがあるので、最初は試さない）

- [ ] **Step 2: シンボル確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
nm -D libwrapi.so | grep -E " T (wr_init|wr_run|wr_set_param|wr_get_state|wr_finalize)\b"
ldd libwrapi.so | head -10
```
Expected:
- 5 つの C シンボルが `T` (defined text) として見える。
- `ldd` で循環依存や `not found` が無い。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/Makefile
git commit -m "build(wr): produce libwrapi.so with PIC dependencies"
```

---

## Task 5: `libwrapi.so` 経由の C テスト

**Files:**
- Create: `wr/tests/c_abi/test_abi_so.c`
- Modify: `wr/tests/c_abi/Makefile`

- [ ] **Step 1: dlopen ベースのテスト作成**

Create `/home/k-yoshimi/program/task/wr/tests/c_abi/test_abi_so.c`:
```c
/* test_abi_so.c
 *
 * Phase L-4 test: load libwrapi.so via dlopen, resolve the 5 ABI functions,
 * and run a minimal init→set_param→run→get_state→finalize cycle.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include "../../wr_api.h"

typedef int (*fn_void_int)(void);
typedef int (*fn_int_int)(int);
typedef int (*fn_str_dbl)(const char*, double);
typedef int (*fn_state)(wr_state_t*);

static int fail = 0;
#define EXPECT_OK(call) do { int r = (call); if (r != 0) {  \
    fprintf(stderr, "FAIL %s:%d: %s -> %d\n", __FILE__, __LINE__, #call, r); fail++; } } while (0)

int main(int argc, char** argv) {
    const char* sopath = (argc > 1) ? argv[1] : "../../libwrapi.so";
    void* h = dlopen(sopath, RTLD_NOW | RTLD_LOCAL);
    if (!h) { fprintf(stderr, "dlopen %s: %s\n", sopath, dlerror()); return 2; }

    fn_void_int wr_init     = (fn_void_int) dlsym(h, "wr_init");
    fn_int_int  wr_run      = (fn_int_int)  dlsym(h, "wr_run");
    fn_str_dbl  wr_set_param= (fn_str_dbl)  dlsym(h, "wr_set_param");
    fn_state    wr_get_state= (fn_state)    dlsym(h, "wr_get_state");
    fn_void_int wr_finalize = (fn_void_int) dlsym(h, "wr_finalize");
    if (!wr_init || !wr_run || !wr_set_param || !wr_get_state || !wr_finalize) {
        fprintf(stderr, "dlsym: %s\n", dlerror()); return 3;
    }

    EXPECT_OK(wr_init());
    /* Set up a tiny analytic-geometry case (mirrors wr_iter_lhcd.in). */
    EXPECT_OK(wr_set_param("MODELG", 2.0));
    EXPECT_OK(wr_set_param("RR", 6.2));
    EXPECT_OK(wr_set_param("RA", 2.0));
    EXPECT_OK(wr_set_param("BB", 5.3));
    EXPECT_OK(wr_set_param("NSMAX", 2.0));
    EXPECT_OK(wr_set_param("PA[1]", 2.0));   EXPECT_OK(wr_set_param("PA[2]", 1.0));
    EXPECT_OK(wr_set_param("PZ[1]", 1.0));   EXPECT_OK(wr_set_param("PZ[2]", -1.0));
    EXPECT_OK(wr_set_param("PN[1]", 1.0));   EXPECT_OK(wr_set_param("PN[2]", 1.0));
    EXPECT_OK(wr_set_param("PNS[1]", 0.1));  EXPECT_OK(wr_set_param("PNS[2]", 0.1));
    EXPECT_OK(wr_set_param("PTPR[1]",10.0)); EXPECT_OK(wr_set_param("PTPR[2]",10.0));
    EXPECT_OK(wr_set_param("PTPP[1]",10.0)); EXPECT_OK(wr_set_param("PTPP[2]",10.0));
    EXPECT_OK(wr_set_param("PTS[1]", 0.5));  EXPECT_OK(wr_set_param("PTS[2]", 0.5));
    EXPECT_OK(wr_set_param("NRAYMAX", 1.0));
    EXPECT_OK(wr_set_param("NSTPMAX", 1000.0));
    EXPECT_OK(wr_set_param("MDLWRI", 101.0));
    EXPECT_OK(wr_set_param("MDLWRQ", 0.0));
    EXPECT_OK(wr_set_param("SMAX", 5.0));
    EXPECT_OK(wr_set_param("DELS", 0.05));
    EXPECT_OK(wr_set_param("RFIN[1]", 5.0e3));
    EXPECT_OK(wr_set_param("RPIN[1]", 8.0));
    EXPECT_OK(wr_set_param("ZPIN[1]", 0.0));
    EXPECT_OK(wr_set_param("PHIIN[1]",0.0));
    EXPECT_OK(wr_set_param("ANGZIN[1]", 0.0));
    EXPECT_OK(wr_set_param("ANGPHIN[1]", 30.0));
    EXPECT_OK(wr_set_param("UUIN[1]", 1.0));
    EXPECT_OK(wr_set_param("MODEWIN[1]", 1.0));

    EXPECT_OK(wr_run(0));

    wr_state_t st;
    EXPECT_OK(wr_get_state(&st));
    fprintf(stdout, "OK got state: nraymax=%d nrsmax=%d nrlmax=%d pwrmax_rs=%g\n",
            st.nraymax, st.nrsmax, st.nrlmax, st.pwrmax_rs);

    EXPECT_OK(wr_finalize());
    dlclose(h);
    return fail ? 1 : 0;
}
```

- [ ] **Step 2: Makefile に dlopen テスト用ターゲット追加**

Modify `/home/k-yoshimi/program/task/wr/tests/c_abi/Makefile`. Append:
```make
test_abi_so: test_abi_so.c
	$(CC) $(CFLAGS) test_abi_so.c -ldl -o $@

run-so: test_abi_so
	./test_abi_so $(WR_DIR)/libwrapi.so
```

Update `clean`:
```
clean:
	-rm -f test_abi_stub test_param_set test_abi_so
```

- [ ] **Step 3: ビルド + 実行**

Run:
```bash
cd /home/k-yoshimi/program/task/wr/tests/c_abi
make test_abi_so 2>&1 | tail -5
./test_abi_so /home/k-yoshimi/program/task/wr/libwrapi.so
echo "exit=$?"
```
Expected:
- ビルド成功。
- 実行で `OK got state: nraymax=1 nrsmax=... pwrmax_rs=...` が表示される。
- exit 0。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/tests/c_abi/test_abi_so.c wr/tests/c_abi/Makefile
git commit -m "test(wr): add dlopen-based libwrapi.so smoke test"
```

---

## Task 6: 既存 `wr` バイナリと回帰テストの再確認

- [ ] **Step 1: 既存 wr バイナリビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make clean && make 2>&1 | tail -5
```
Expected: `wr` バイナリ生成成功（PIC 経路は別ディレクトリなので影響しないはず）。

- [ ] **Step 2: 全テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 全件 PASS。

---

## 完了基準

- [ ] `wr/libwrapi.so` が生成される
- [ ] `nm -D libwrapi.so` で `wr_init/wr_run/wr_set_param/wr_get_state/wr_finalize` が表示される
- [ ] `wr/tests/c_abi/test_abi_so` で dlopen + init→run→get_state→finalize サイクルが PASS
- [ ] 既存 `wr` バイナリと WR/TR/EQ/TX 回帰テストに影響なし
- [ ] 必要な依存 `.a_pic` が揃っている（既存の TR L-4 を再利用 or 新規追加）

## 撤退条件

- 案 a (PIC リビルド) が失敗:
  - 案 c (`-Wl,--whole-archive`) を試す: `libwrapi.so` ビルド時に `-Wl,--whole-archive ../dp/libdp.a -Wl,--no-whole-archive` のように非 PIC `.a` を埋め込む（コンパイラの古い gfortran で失敗の可能性）
  - 案 b (ソース統合): `wr/libwrapi.so` ビルド時に依存ライブラリのソースを直接 `-fPIC` 付きでコンパイルし `.o` を直接リンク。Makefile が肥大化するが PIC 移植性問題を回避

- mtxp の MPI 依存で詰まる: `LIB_MTX_BND`（MPI なし）に固定し、`make.mtxp` で `LIB_MTX = $(LIB_MTX_BND)` に設定して進む

- ldd で `not found` が出る: `LD_LIBRARY_PATH` を設定するか、Python 側で `ctypes.CDLL("/abs/path/to/libwrapi.so")` で絶対パス指定（L-5 でデフォルト動作にする）

## 依存

- 前提: L-3 完了（`wr_param_registry.f90` が存在し、`wr_set_param_c` が実装されている）
- 後続: L-5 (Python ラッパ) が `libwrapi.so` を `ctypes.CDLL` で読み込む
