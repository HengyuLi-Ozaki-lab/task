# WRX Library-ization Phase L-4: Shared Library Build (`libwrxapi.so`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-3 で実装した C ABI を含む WRX core を **`libwrxapi.so`** として shared library 化する。`wrgout.f90` (graphics) と `wrmenu.f90` (menu) は除外、`wrmain.f90` も除外。依存ライブラリ (`libeq.a`, `libpl.a`, `libdp.a`, `libtask.a`, `libbpsd.a`, libmtxp) を **PIC 再ビルド**して新しい `libeq_pic.a` 等を作り、それらを束ねて `.so` を生成する。既存 `wrx/wr` バイナリは触らず温存する。

**Architecture:** `wrx/Makefile` に新しいターゲット `libwrxapi.so` を追加。core ファイルを `-fPIC` で再コンパイルし `obj_pic/` に置く。依存ライブラリ側の Makefile (`eq/Makefile`, `pl/Makefile`, `dp/Makefile`, `lib/Makefile`, `mtxp/Makefile`, `../bpsd/Makefile`) に `lib*_pic.a` ターゲットを追加。リンクには `-shared -fPIC` 付き `gfortran -shared` を使い、出力は `wrx/libwrxapi.so`。

**Critical: シンボル衝突回避** — `libwrxapi.so` の公開シンボルは **`wrx_*` のみ** (5 関数) に制限。Fortran モジュール内部のシンボルは ELF symbol scope の制限がないため `wrcomm`, `wr_exec` 等が外部から見えるが、`wr/libwrapi.so` (将来作成可能性) との同時 dlopen は **想定外**（ユーザは wrx か wr のいずれか一方のみ使う）。Python wrapper 側で `RTLD_LOCAL` で dlopen することで衝突回避。

**Tech Stack:** GNU Make、gfortran `-fPIC -shared`、ar/ranlib。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §7（ビルドシステム）、§7.4（PIC ビルド失敗時のフォールバック）。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wrx/Makefile` | 修正 | `libwrxapi.so` ターゲット追加、`obj_pic/`, `mod_pic/` ディレクトリ用 PIC ルール |
| `eq/Makefile` | 修正 | `libeq_pic.a` ターゲット追加 |
| `pl/Makefile` | 修正 | `libpl_pic.a` ターゲット追加 |
| `dp/Makefile` | 修正 | `libdp_pic.a` ターゲット追加 |
| `lib/Makefile` | 修正 | `libtask_pic.a`, `libmds_pic.a` ターゲット追加（`libgrf_pic.a` は wrxlib では不要） |
| `mtxp/Makefile` | 修正 | PIC バリアント追加 |
| `../bpsd/Makefile` | 修正 | `libbpsd_pic.a` ターゲット追加 |

**注意:** これらの修正は他の WRX 関連 PR（`tr/`, `wr/`, `fp/` 等）と競合する可能性。本 PR では **wrx に必要な分のみ** 追加し、既存ターゲットの動作は不変に保つ（add-only）。

---

## Task 1: ブランチ準備、現状の依存関係マップ

- [ ] **Step 1: ブランチ作成**
```bash
cd /home/k-yoshimi/program/task-private
git checkout develop && git pull
git checkout -b feature/wrx-library-L4-shared-lib-build
```

- [ ] **Step 2: 既存 LIBS をマップ**
```bash
grep "^LIBS\|^LIBSPLOT" /home/k-yoshimi/program/task-private/wrx/Makefile
```
Expected:
```
LIBS = libwr.a  ../dp/libdp.a ../eq/libeq.a ../pl/libpl.a \
       ../lib/libtask.a ../lib/libgrf.a ../../bpsd/libbpsd.a
```
これを PIC 版に置換した `LIBS_PIC` を新たに定義。`libgrf` は graphics 用なので wrxlib では除外。

- [ ] **Step 3: `mtxp` の中身を確認**
```bash
ls /home/k-yoshimi/program/task-private/mtxp/*.a 2>/dev/null
grep "^LIB\|^libmtx\|libmpi_dummy\|libmpi" /home/k-yoshimi/program/task-private/mtxp/Makefile | head -10
```
Expected: `libmtx.a` 等が見える。WRX の `LIB_MTX` は通常 `LIB_MTX_NOMPI` または `LIB_MTX_BND`。Phase L-4 では NOMPI 版を採用する。

---

## Task 2: 依存ライブラリ側の `lib*_pic.a` を追加

各依存 Makefile に「PIC オブジェクトディレクトリ + lib*_pic.a ターゲット」を追加する。テンプレート:

- [ ] **Step 1: `eq/Makefile` に追加**

末尾に以下を追加:
```make
# --- PIC variant for shared library use (libwrxapi.so) ---
OBJDIR_PIC = ./obj_pic
MOD_PIC    = mod_pic

$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(OBJDIR_PIC) ./$(MOD_PIC)
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -I./$(MOD_PIC) -J./$(MOD_PIC) \
		-I../pl/$(MOD_PIC) -I../lib/$(MOD_PIC) -I../../bpsd/$(MOD_PIC)

$(OBJDIR_PIC)/%.o: %.f
	@mkdir -p $(OBJDIR_PIC) ./$(MOD_PIC)
	$(FCFIXED) $(FFLAGS) -fPIC -c $< -o $@ -I./$(MOD_PIC) -J./$(MOD_PIC) \
		-I../pl/$(MOD_PIC) -I../lib/$(MOD_PIC) -I../../bpsd/$(MOD_PIC)

OBJS_PIC = $(addprefix $(OBJDIR_PIC)/, $(notdir $(basename $(SRCS)).o))

libeq_pic.a: $(OBJS_PIC)
	$(AR) rcs $@ $(OBJS_PIC)

clean_pic:
	-rm -rf $(OBJDIR_PIC) ./$(MOD_PIC) libeq_pic.a
```
**注:** `$(SRCS)` の参照を確認し、もし複数行にまたがっているなら `OBJS_PIC` の式を合わせる。`eq/Makefile` の SRCS を grep してから合わせる。

- [ ] **Step 2: `pl/Makefile`, `dp/Makefile`, `lib/Makefile`, `mtxp/Makefile`, `../bpsd/Makefile` に同様のブロックを追加**

各 Makefile で:
- 出力 `.a` 名: `libpl_pic.a`, `libdp_pic.a`, `libtask_pic.a`, `lib*mtx*_pic.a`, `libbpsd_pic.a`
- `MODINCLUDE` の `-I` パスは元の `MODINCLUDE` から `mod` → `mod_pic` に置換
- 依存先 lib の MOD パスもすべて `mod_pic` に向ける

`lib/Makefile` には `libtask.a` の SRCS と `libgrf.a` の SRCS が両方あるため、`libtask_pic.a` のみ作る（`libgrf` は graphics 系で wrxlib に不要）。

- [ ] **Step 3: 各 lib_pic.a が個別に build できることを確認**
```bash
cd /home/k-yoshimi/program/task-private/../bpsd && make libbpsd_pic.a 2>&1 | tail -5
cd /home/k-yoshimi/program/task-private/lib    && make libtask_pic.a 2>&1 | tail -5
cd /home/k-yoshimi/program/task-private/pl     && make libpl_pic.a   2>&1 | tail -5
cd /home/k-yoshimi/program/task-private/eq     && make libeq_pic.a   2>&1 | tail -5
cd /home/k-yoshimi/program/task-private/dp     && make libdp_pic.a   2>&1 | tail -5
cd /home/k-yoshimi/program/task-private/mtxp   && make 2>&1 | tail -5  # PIC バリアントの object 群
```
Expected: 各 lib_pic.a が生成される。エラーなし。

**フォールバック:** PIC リビルドで失敗するライブラリがあれば §7.4 のフォールバック (b) ソース直接統合 へ切替: `libwrxapi.so` のリンク行に `lib*.a` の代わりに `*.o` を whole-archive で含める。

- [ ] **Step 4: コミット（依存ライブラリの PIC 対応のみ）**
```bash
cd /home/k-yoshimi/program/task-private
git add eq/Makefile pl/Makefile dp/Makefile lib/Makefile mtxp/Makefile ../bpsd/Makefile
git commit -m "build: add lib*_pic.a targets for shared library consumption"
```

---

## Task 3: `wrx/Makefile` に `libwrxapi.so` ターゲット追加

**Files:**
- Modify: `wrx/Makefile`

- [ ] **Step 1: PIC 用ディレクトリと SRCS_LIB を定義**

`wrx/Makefile` の `SRCS_CORE`, `SRCS_GRAPHICS`, `SRCS_MENU` 定義の直後に追加:
```make
# --- WRX library (libwrxapi.so) sources ---
# Core only (no graphics, no menu, no main).
SRCS_LIB = $(SRCS_CORE)

OBJDIR_PIC = ./obj_pic
MOD_PIC    = mod_pic

OBJS_LIB_PIC = $(addprefix $(OBJDIR_PIC)/, $(SRCS_LIB:.f90=.o))

LIBS_PIC = ../dp/libdp_pic.a ../eq/libeq_pic.a ../pl/libpl_pic.a \
           ../lib/libtask_pic.a ../../bpsd/libbpsd_pic.a

# --- PIC build rule ---
$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(OBJDIR_PIC) ./$(MOD_PIC)
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -I./$(MOD_PIC) -J./$(MOD_PIC) \
		-I../pl/$(MOD_PIC) -I../dp/$(MOD_PIC) -I../eq/$(MOD_PIC) \
		-I../lib/$(MOD_PIC) -I../mtxp/$(MOD_PIC) -I../../bpsd/$(MOD_PIC)
```

- [ ] **Step 2: ターゲット追加**

`all : libs wr` の下に新しいターゲットを追加:
```make
.PHONY: libwrxapi
libwrxapi: libwrxapi.so

libwrxapi.so: $(OBJS_LIB_PIC) $(LIBS_PIC)
	$(FC) -shared -fPIC -o libwrxapi.so \
		$(OBJS_LIB_PIC) $(LIBS_PIC) \
		$(LIB_MTX_NOMPI) $(FLIBS)
```

注: `LIB_MTX_NOMPI` は `mtxp/make.mtxp` で定義される。もし無ければ `mtxp/libmtx_nompi_pic.a` を直接書く。

- [ ] **Step 3: `clean_pic` ターゲット**

```make
clean_pic:
	-rm -rf $(OBJDIR_PIC) ./$(MOD_PIC) libwrxapi.so
```

- [ ] **Step 4: header コピー**

`libwrxapi` ターゲットの後に header をコピーするステップを追加（C 側がリンクする時に使うため）:
```make
libwrxapi.so: $(OBJS_LIB_PIC) $(LIBS_PIC)
	$(FC) -shared -fPIC -o libwrxapi.so \
		$(OBJS_LIB_PIC) $(LIBS_PIC) \
		$(LIB_MTX_NOMPI) $(FLIBS)
	@echo "Built libwrxapi.so. Header at wrx/wrx_api.h"
```

---

## Task 4: ビルドと検証

- [ ] **Step 1: 依存 PIC の事前ビルド**
```bash
cd /home/k-yoshimi/program/task-private/../bpsd && make libbpsd_pic.a
cd /home/k-yoshimi/program/task-private/lib    && make libtask_pic.a
cd /home/k-yoshimi/program/task-private/pl     && make libpl_pic.a
cd /home/k-yoshimi/program/task-private/eq     && make libeq_pic.a
cd /home/k-yoshimi/program/task-private/dp     && make libdp_pic.a
```

- [ ] **Step 2: libwrxapi.so build**
```bash
cd /home/k-yoshimi/program/task-private/wrx
make libwrxapi 2>&1 | tail -20
ls -la libwrxapi.so
```
Expected: `libwrxapi.so` が生成。サイズは数 MB。

- [ ] **Step 3: 公開シンボル確認**
```bash
nm -D /home/k-yoshimi/program/task-private/wrx/libwrxapi.so | grep -E " T wrx_(init|run|set_param|get_state|finalize)$"
```
Expected: 5 シンボルが Text セクションに dynamic symbol として存在。

- [ ] **Step 4: 公開シンボルが `wrx_*` のみ（衝突回避確認）**
```bash
nm -D /home/k-yoshimi/program/task-private/wrx/libwrxapi.so | grep -E " T wr_(init|run|exec)" | head -5
```
Expected: マッチなし（ユーザ指示の通り、`wr_` プレフィックスを ABI として公開していない）。
**注:** Fortran モジュール内部の `wrexec_MOD_wr_exec` 等のシンボルは見えるが、これらは ABI ではなく内部リンケージ。

- [ ] **Step 5: ldd で依存ライブラリ確認**
```bash
ldd /home/k-yoshimi/program/task-private/wrx/libwrxapi.so | head -20
```
Expected: `libgfortran.so`, `libm`, `libc`, `libgcc_s` 等のみ。`libgrf.so` 等 X11/PG 系が含まれていないこと（含まれていたら graphics 分離が不完全）。

- [ ] **Step 6: 簡易 C smoke test**

Create temp `/tmp/wrxlib_smoke.c`:
```c
#include <stdio.h>
#include "wrx_api.h"
int main(void) {
    int e;
    wrx_state_t st;
    e = wrx_init();
    printf("init=%d\n", e);
    e = wrx_set_param("NRAYMAX", 1.0);
    printf("set NRAYMAX=%d\n", e);
    e = wrx_finalize();
    printf("finalize=%d\n", e);
    return 0;
}
```

```bash
cd /tmp
gcc -I/home/k-yoshimi/program/task-private/wrx wrxlib_smoke.c \
    -L/home/k-yoshimi/program/task-private/wrx -lwrxapi \
    -lgfortran -lm -o wrxlib_smoke
LD_LIBRARY_PATH=/home/k-yoshimi/program/task-private/wrx ./wrxlib_smoke
```
Expected:
```
init=0
set NRAYMAX=0
finalize=0
```

`wrx_run` の完全実行 smoke は L-6 Layer 2 で実施（namelist 一括 set_param + run + get_state）。

- [ ] **Step 7: 既存 `wrx/wr` バイナリが従来通り動くことを確認**
```bash
cd /home/k-yoshimi/program/task-private/test_run
rm -rf test_output/wrx_*
./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo
```
Expected: 3 ケース PASS（baseline 一致）。L-4 で PIC ビルドを追加しただけで `wrx/wr` ターゲットは変更なし。

- [ ] **Step 8: コミット**
```bash
cd /home/k-yoshimi/program/task-private
git add wrx/Makefile
git commit -m "feat(wrx): add libwrxapi.so shared library build target"
```

---

## Verification Checklist

- [ ] 依存ライブラリ 5 つ (`libbpsd_pic.a`, `libtask_pic.a`, `libpl_pic.a`, `libeq_pic.a`, `libdp_pic.a`) が build 可能
- [ ] `wrx/libwrxapi.so` が生成される
- [ ] `nm -D libwrxapi.so` で 5 つの `wrx_*` 関数が見える
- [ ] `nm -D libwrxapi.so` に `wr_init`, `wr_run` 等の `wr_` プレフィックスシンボルが**無い**
- [ ] `ldd libwrxapi.so` に X11/PG/libgrf 等 graphics 依存が**無い**
- [ ] C smoke test (`wrx_init` → `wrx_set_param` → `wrx_finalize`) が `0 0 0` を返す
- [ ] 既存 `wrx/wr` バイナリの動作が変わらない
- [ ] WRX 3 baseline test PASS

## Dependencies

- L-3 完了（`wrx_param_registry.f90`, `wrx_api.f90` 実装済み）

## Fallback (PIC リビルドが失敗した場合)

| 試行 | 条件 | フォールバック先 |
|---|---|---|
| (a) 依存 lib_pic.a 個別ビルド | 一部 lib で PIC ビルド失敗 | (b) or (c) |
| (b) ソース直接統合 | (a) 不可 | `libwrxapi.so` のリンク行に依存 lib の `*.o` を直接展開（`-Wl,--whole-archive`） |
| (c) `-Wl,--whole-archive` | (a) 不可 | (b) と同等 |

設計書 §7.4 と同じフォールバック方針。

## Out of Scope

- Python wrapper（L-5）
- 4 層テスト（L-6）
- ドキュメント（L-7）
- インストール (`make install`) 系（CMake 化検討含む。本 PR のスコープ外）
- multiprocessing/threading 安全性（global state による制限を README に明記、L-7）
