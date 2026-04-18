# TOT Library Phase L-4: `libtotapi.so` Shared Library Build 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2/L-3 で実装した tot C ABI を **`libtotapi.so` 共有ライブラリ** としてビルドし、Python (L-5) や任意の C/Julia/MATLAB クライアントから dlopen 可能にする。`libtrapi.so / libtiapi.so / libfpapi.so / libwrapi.so / libwmapi.so / libplapi.so` に依存し、graphics は除外、`TOT_NO_GRAPHICS` 構成でリンク。

**Architecture:** tot は単一 PROGRAM ではなく per-module library を「束ねる」だけなので、`libtotapi.so` のソースは `tot_state.f90 + tot_param_registry.f90 + tot_api.f90` の 3 つだけ。リンク対象として既存 per-module の PIC 版 `lib*api.so` を `-l` リンクする。`tot` 標準バイナリは引き続き従来どおり `libtr2.a / libfp.a / ...` の static 版でリンクするので、PIC 版と static 版が共存する状態になる。

**Tech Stack:** Make, gfortran (`-fPIC -shared`), `ldd` でリンク検証, 既存 per-module `lib*api.so`。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 7（ビルドシステム）を tot 用に拡張。

**前提条件:** L-0..L-3 完了 + **個別モジュールの Phase L-4 が完成済みで `lib<x>api.so` がビルドされている**こと（trapi/tiapi/fpapi/wrapi/wmapi/plapi）。EQ は static `libeq.a` を PIC リビルドして `libeq_pic.a` として組み込む。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `tot/Makefile` | 修正 | `libtotapi.so` ターゲット追加、PIC ビルドルール追加 |
| `tot/mod_pic/` | 新規（生成） | PIC ビルド時の .mod ディレクトリ |
| `eq/Makefile` | 修正 | `libeq_pic.a` ターゲット追加（EQ は library 化していないため static で組み込む） |
| `tot/tests/c_abi/Makefile` | 修正 | `-L../.. -ltotapi` でリンクするテストを追加 |
| `tot/tests/c_abi/test_abi_so.c` | 新規 | `dlopen("libtotapi.so")` でシンボル解決確認 |

**方針:**
- `libtotapi.so` は **graphics を除外**してビルド（`TOT_NO_GRAPHICS` define）。
- 既存 `tot` バイナリ（static link、graphics あり）は **完全に温存**。
- `RPATH` を `$ORIGIN/../tr:$ORIGIN/../ti:...` に設定し、`tot/libtotapi.so` を別ディレクトリから dlopen しても per-module の `.so` を見つけられるように。
- L-4 の検証は「`ldd libtotapi.so` で全シンボル解決」「`test_abi_so` が PASS」までで、物理的計算結果検証は L-6 の Layer 1 等価性テスト。

---

## Task 1: 作業用ブランチ作成と前提確認

**Files:** なし

- [ ] **Step 1: ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop && git pull
git checkout -b feature/tot-library-l4-shared-lib-build
```

- [ ] **Step 2: per-module の PIC 版 `.so` 存在確認**

Run:
```bash
ls /home/k-yoshimi/program/task/tr/libtrapi.so \
   /home/k-yoshimi/program/task/ti/libtiapi.so \
   /home/k-yoshimi/program/task/fp/libfpapi.so \
   /home/k-yoshimi/program/task/wr/libwrapi.so \
   /home/k-yoshimi/program/task/wm/libwmapi.so \
   /home/k-yoshimi/program/task/pl/libplapi.so \
   2>&1
```
Expected: 全て存在。無ければ各モジュールの Phase L-4 を先に完了する。

- [ ] **Step 3: L-3 baseline 確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh tot_demo2014_short tot_ht6m_short
cd /home/k-yoshimi/program/task/tot/tests/c_abi && make run
```
Expected: 全 PASS。

- [ ] **Step 4: 初期コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(tot): start L-4 shared library build"
```

---

## Task 2: EQ の PIC 版 static library `libeq_pic.a` を追加

**Files:**
- Modify: `eq/Makefile`

**目的:** EQ は F77 + .inc include で Phase 0 段階では非ライブラリ化。tot の `.so` 中に EQ シンボルを取り込むため、PIC でリビルドした static archive を用意する。

- [ ] **Step 1: `eq/Makefile` を確認**

Run:
```bash
head -40 /home/k-yoshimi/program/task/eq/Makefile
```

- [ ] **Step 2: PIC ターゲット追加**

`eq/Makefile` に以下を追加（既存 `libeq.a` ターゲットの直後）:

```makefile
# PIC build for inclusion in libtotapi.so / libtrapi.so consumers.
OBJ_EQ_PIC = $(SRCS:.f=.pic.o)

%.pic.o: %.f
	$(FCFIXED) $(FFLAGS) -fPIC -c $< -o $@ $(MODDIR_PIC) $(MODINCLUDE)

libeq_pic.a: $(OBJ_EQ_PIC)
	$(AR) rcs libeq_pic.a $(OBJ_EQ_PIC)
```

`MODDIR_PIC = -Jmod_pic -I./mod_pic` を冒頭で定義。

- [ ] **Step 3: ビルドテスト**

Run:
```bash
cd /home/k-yoshimi/program/task/eq
mkdir -p mod_pic
make libeq_pic.a 2>&1 | tail -10
ls -la libeq_pic.a
```
Expected: `libeq_pic.a` が生成される。

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add eq/Makefile
git commit -m "build(eq): add PIC-rebuilt libeq_pic.a target for shared-lib consumers"
```

---

## Task 3: `tot/Makefile` に PIC ビルドルールと `libtotapi.so` ターゲットを追加

**Files:**
- Modify: `tot/Makefile`

- [ ] **Step 1: PIC 関連定義を追加**

`tot/Makefile` の冒頭付近（既存 `MODINCLUDE` の直後）に以下を追加:

```makefile
# ----- PIC build configuration (libtotapi.so) ----------------------
MOD_PIC      = mod_pic
MODDIR_PIC   = -J$(MOD_PIC) -I$(MOD_PIC)
MODINCLUDE_PIC = -I$(MOD_PIC) \
                 -I../tr/mod_pic -I../ti/mod_pic -I../fp/mod_pic \
                 -I../wr/mod_pic -I../wm/mod_pic -I../pl/mod_pic \
                 -I../dp/$(MOD) -I../eq/mod_pic \
                 -I../mtxp/$(MOD) -I../lib/$(MOD) -I../../bpsd/$(MOD)

# Sources to include in libtotapi.so (no graphics, no menu).
SRCS_LIB = $(SRCS_API) $(SRCS_CORE)
OBJ_LIB_PIC = $(SRCS_LIB:.f90=.pic.o)

# Per-module shared libraries we link against.
LIB_PER_MODULE = -L../tr -ltrapi \
                 -L../ti -ltiapi \
                 -L../fp -lfpapi \
                 -L../wr -lwrapi \
                 -L../wm -lwmapi \
                 -L../pl -lplapi

# EQ is bundled as PIC static archive (still F77 era).
LIB_EQ_PIC = ../eq/libeq_pic.a

# Other infrastructure libraries (assumed available as static; rebuild PIC if not).
LIB_INFRA_PIC = ../lib/libmds.a ../lib/libtask.a ../../bpsd/libbpsd.a \
                ../adpost/lib-adpost.a ../open-adas/adf11/adf11-lib/lib-adf11.a
```

- [ ] **Step 2: PIC コンパイルルール追加**

`tot/Makefile` の `.f90.o:` ルールの直後に追加:

```makefile
# Pattern rule for PIC build (used only by libtotapi.so).
%.pic.o: %.f90
	$(FCFREE) $(FFLAGS) -fPIC -cpp -DTOT_NO_GRAPHICS -c $< -o $@ \
	    $(MODDIR_PIC) $(MODINCLUDE_PIC)
```

- [ ] **Step 3: `libtotapi.so` ターゲット追加**

`tot/Makefile` の `tot:` ターゲット直後に追加:

```makefile
# Shared library target for in-process Python / C / Julia consumers.
libtotapi.so: $(LIB_MTX) | mod_pic_dir
	$(MAKE) $(OBJ_LIB_PIC)
	$(FC) -shared -fPIC -Wl,-soname,libtotapi.so \
	    $(OBJ_LIB_PIC) \
	    $(LIB_PER_MODULE) \
	    $(LIB_EQ_PIC) \
	    $(LIB_INFRA_PIC) \
	    $(FLIBS) $(LIBX_MTX) \
	    -Wl,-rpath,'$$ORIGIN/../tr:$$ORIGIN/../ti:$$ORIGIN/../fp:$$ORIGIN/../wr:$$ORIGIN/../wm:$$ORIGIN/../pl' \
	    -o libtotapi.so

mod_pic_dir:
	mkdir -p $(MOD_PIC)
```

- [ ] **Step 4: clean ターゲットに PIC 成果物を追加**

変更前:
```makefile
clean:
	-rm -f core a.out *.o *.mod ./*~ *.a $(MOD)/*.mod
```

変更後:
```makefile
clean:
	-rm -f core a.out *.o *.pic.o *.mod ./*~ *.a *.so $(MOD)/*.mod $(MOD_PIC)/*.mod
	-rmdir $(MOD_PIC) 2>/dev/null || true
```

- [ ] **Step 5: ビルド試行**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make libtotapi.so 2>&1 | tail -20
ls -la libtotapi.so
```
Expected: `libtotapi.so` が生成される。

ビルドエラー対処:
- "Cannot find -ltrapi" → per-module の `.so` パスを確認、`tr/Makefile` で `libtrapi.so` がビルドされているか
- "undefined reference to `mtx_initialize`" → `LIBX_MTX` の中身を確認、PIC 版 mtx ライブラリ (`libmtxp_pic.so`) が必要かも
- modパス解決 → `MODINCLUDE_PIC` の `-I` を per-module の正しい mod_pic に向ける

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/Makefile
git commit -m "build(tot): add libtotapi.so shared library target with PIC rules"
```

---

## Task 4: `libtotapi.so` のシンボル解決を ldd / nm で確認

**Files:** なし（検証のみ）

- [ ] **Step 1: 未解決シンボル確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
ldd -r libtotapi.so 2>&1 | tail -20
```
Expected: `undefined symbol` の行がゼロ（あっても `libgrf` 由来の GS* シンボルは出ないはず — TOT_NO_GRAPHICS で除外したので）。

未解決があれば該当ライブラリを `LIB_INFRA_PIC` か `LIB_PER_MODULE` に追加。

- [ ] **Step 2: 公開シンボルを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
nm -D libtotapi.so | grep -E "^[0-9a-f]+ T tot_" | sort
```
Expected: `tot_init`, `tot_run`, `tot_get_state`, `tot_set_param`, `tot_finalize` の 5 シンボルが見える。

- [ ] **Step 3: 依存ライブラリ参照確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
ldd libtotapi.so | head -20
```
Expected: `libtrapi.so`, `libtiapi.so`, ... が解決される。

- [ ] **Step 4: 検証コミット**

Run:
```bash
git commit --allow-empty -m "test(tot): verify libtotapi.so symbol resolution"
```

---

## Task 5: dlopen 経由のテスト `test_abi_so.c` を作成

**Files:**
- Create: `tot/tests/c_abi/test_abi_so.c`
- Modify: `tot/tests/c_abi/Makefile`

- [ ] **Step 1: dlopen テスト本体を作成**

作成: `tot/tests/c_abi/test_abi_so.c`

```c
/*
 * test_abi_so.c — verify libtotapi.so loads and exports the C ABI.
 *
 * Build:  see Makefile target test_abi_so
 * Run:    LD_LIBRARY_PATH includes the tot/, tr/, ti/, fp/, ... dirs.
 */
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
#include <dlfcn.h>

typedef int (*fn_void_int)(void);
typedef int (*fn_int_int)(int);
typedef int (*fn_str_dbl_int)(const char*, double);

int main(void) {
    void* h = dlopen("libtotapi.so", RTLD_NOW);
    if (!h) {
        fprintf(stderr, "dlopen failed: %s\n", dlerror());
        return 1;
    }

    fn_void_int    tot_init     = (fn_void_int)   dlsym(h, "tot_init");
    fn_int_int     tot_run      = (fn_int_int)    dlsym(h, "tot_run");
    fn_str_dbl_int tot_set      = (fn_str_dbl_int)dlsym(h, "tot_set_param");
    fn_void_int    tot_finalize = (fn_void_int)   dlsym(h, "tot_finalize");

    assert(tot_init     && "tot_init symbol not exported");
    assert(tot_run      && "tot_run symbol not exported");
    assert(tot_set      && "tot_set_param symbol not exported");
    assert(tot_finalize && "tot_finalize symbol not exported");

    int rc = tot_init();
    assert(rc == 0 && "tot_init must succeed");

    rc = tot_set_param("ZZ.UNKNOWN", 0.0);
    assert(rc == 1 && "unknown prefix must return 1 via .so");

    rc = tot_finalize();
    assert(rc == 0 && "tot_finalize must succeed via .so");

    dlclose(h);
    printf("test_abi_so: PASS\n");
    return 0;
}
```

- [ ] **Step 2: テスト Makefile に dlopen ターゲット追加**

`tot/tests/c_abi/Makefile` に追記:

```makefile
test_abi_so: test_abi_so.c
	$(CC) $(CFLAGS) test_abi_so.c -ldl -o $@

run_so: test_abi_so
	LD_LIBRARY_PATH=$(TOT_DIR):$(TR_DIR):$(TI_DIR):$(FP_DIR):$(WR_DIR):$(WM_DIR):$(PL_DIR):$$LD_LIBRARY_PATH \
	    ./test_abi_so
```

- [ ] **Step 3: ビルド + 実行**

Run:
```bash
cd /home/k-yoshimi/program/task/tot/tests/c_abi
make test_abi_so 2>&1 | tail
make run_so 2>&1 | tail
```
Expected: `test_abi_so: PASS`。

エラー対処:
- "cannot open shared object file" → `LD_LIBRARY_PATH` を再確認、もしくは `tot/Makefile` の RPATH 設定 (`-Wl,-rpath,$ORIGIN/...`) を直す
- assertion failure → L-3 のテストが PASS しているはず、ABI 整合性を `nm` で再確認

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/tests/c_abi/test_abi_so.c tot/tests/c_abi/Makefile
git commit -m "test(tot): add dlopen-based test for libtotapi.so"
```

---

## Task 6: `make tot` がまだ動くことを確認（既存バイナリ温存）

**Files:** なし

- [ ] **Step 1: 通常 tot バイナリのビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make tot 2>&1 | tail
ls -la tot libtotapi.so
```
Expected: 両方存在する。

- [ ] **Step 2: 通常テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。L-3 と完全一致。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "test(tot): verify standalone tot binary unchanged"
```

---

## Task 7: README とビルドドキュメント更新

**Files:**
- Modify: `tot/README.md`

- [ ] **Step 1: README 更新**

`tot/README.md` の Build セクションを以下に置換:

```markdown
## Build

```sh
make                    # standard tot binary (interactive, with graphics)
make EXTRA_DEFS=-DTOT_NO_GRAPHICS   # tot binary without graphics calls
make libtotapi.so       # shared library for in-process Python/C consumers
```

`libtotapi.so` requires the per-module shared libraries (`libtrapi.so`,
`libtiapi.so`, `libfpapi.so`, `libwrapi.so`, `libwmapi.so`, `libplapi.so`)
to be built first, plus `libeq_pic.a` (PIC archive for the F77 EQ module).

To use `libtotapi.so` from another directory, ensure `LD_LIBRARY_PATH`
includes both `tot/` and the per-module directories, or rely on the
embedded `RPATH` (set to `$ORIGIN/../tr:$ORIGIN/../ti:...`).
```

- [ ] **Step 2: コミット**

Run:
```bash
git add tot/README.md
git commit -m "docs(tot): document libtotapi.so build and runtime path"
```

---

## Verification (Phase L-4 完了基準)

- [ ] `tot/libtotapi.so` が生成され、`ldd -r` で未解決シンボルなし。
- [ ] `nm -D libtotapi.so` で `tot_init/run/get_state/set_param/finalize` 5 シンボル全て公開。
- [ ] `tot/tests/c_abi/test_abi_so` が PASS。
- [ ] 既存 `tot` バイナリと tot regression テスト（L-0/L-1/L-2/L-3）に変化なし。
- [ ] `eq/libeq_pic.a` が PIC でビルドできる。

---

## Dependencies & Fallback

**前提:** L-2/L-3 + 個別モジュールの Phase L-4 完了。

**産出物:** L-5 (Python ラッパ)、L-6 (4 層テスト)、L-7 (パラメータ最適化) の前提となる `libtotapi.so`。

**Fallback:**
- per-module の `.so` が無い → 該当モジュールの Phase L-4 を先行する。あるいは `libtotapi.so` のリンクから一部 per-module を一時的に外し、tot 側 `tot_api.f90` の対応 fan-out を `! TODO` に置換した縮小版 `.so` をビルド。
- EQ の PIC リビルドが失敗 → `eq` を `--whole-archive` で組み込む案 (`-Wl,--whole-archive ../eq/libeq.a -Wl,--no-whole-archive`)、ただし非 PIC オブジェクトでは shared library に入れられないため最終的に PIC 化が必要。
- `libgfortran.so` の混在で undefined reference → `gfortran -shared` ではなく `gcc -shared -lgfortran` で明示リンク。
- `RPATH` `$ORIGIN` が動かない（古い ldso）→ `LD_LIBRARY_PATH` を README に明記し、テストはそちらで通す。

---

## Out of scope（次フェーズ送り）

- Python ラッパ実装 → L-5
- 数値等価性検証（`tot` バイナリと `libtotapi.so` 経由の結果一致） → L-6 Layer 1
- Windows / macOS 対応 → 別 phase（Linux x86_64 のみサポート）
- multi-instance / thread-safe 対応 → 既知の制限として明文化
