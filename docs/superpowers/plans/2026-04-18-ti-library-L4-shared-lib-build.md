# TI Library Phase L-4: Shared Library Build (`libtiapi.so`) 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** L-2/L-3 で追加した `ti_state.f90`, `ti_param_registry.f90`, `ti_api.f90` を中核に、graphics/menu を除外した shared library `libtiapi.so` を生成する。依存ライブラリ（`libpl.a`, `libeq.a`, `libtask.a`, `libgrf.a`, `lib-adpost.a`, `lib-adf11.a`, `libbpsd.a`, `mtxp/lib*`）の **PIC 版** を必要に応じて並列ターゲットとして生成する。

**Architecture:** TR の L-4 と同じ戦略。`ti/Makefile` に `libtiapi.so` ターゲットを追加し、`-fPIC` でリビルドした `mod_pic/` 配下の `.o` を集めて `-shared` でリンク。依存 lib に PIC 対応がない場合は本フェーズで `lib*_pic.a` を追加（フォールバック節 7.4 参照）。`ti` バイナリは従来通り温存（影響なし）。

**Tech Stack:** GNU Make, gfortran (`-fPIC`, `-shared`)。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` 7 章 (ビルドシステム), 7.4 (PIC フォールバック)。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `ti/Makefile` | 修正 | `libtiapi.so` ターゲット、PIC ビルドルール (`mod_pic/`)、依存 lib の `_pic.a` 参照 |
| `eq/Makefile` | 修正 | `libeq_pic.a` ターゲット追加 |
| `pl/Makefile` | 修正 | `libpl_pic.a` ターゲット追加 |
| `lib/Makefile` | 修正 | `libtask_pic.a`, `libgrf_pic.a`, `libmds_pic.a` ターゲット追加 |
| `mtxp/Makefile` | 修正 | `lib*_pic.a` ターゲット追加（MUMPS 関連） |
| `adpost/Makefile` | 修正 | `lib-adpost_pic.a` ターゲット追加 |
| `open-adas/adf11/adf11-lib/Makefile` | 修正 | `lib-adf11_pic.a` ターゲット追加 |
| `../bpsd/Makefile` | 修正 | `libbpsd_pic.a` ターゲット追加（リポジトリ外の場合は要確認） |
| `ti/tests/c_abi/test_link.c` | 新規 | `libtiapi.so` をリンクして `ti_init`/`ti_finalize` を呼ぶ最小 link テスト |
| `ti/tests/c_abi/Makefile` | 修正 | `test_link` ターゲット追加 |

**スコープ外:**
- Python wrapper（L-5）
- 4 層テスト（L-6）

---

## Task 1: 前提確認と PIC 対応の事前調査

**Files:**
- なし

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin
git checkout -b feature/ti-library-L4-shared-lib-build origin/develop
```
Expected: develop に L-3 がマージ済み（`ti_param_registry.f90` が存在）。

- [ ] **Step 2: TR 側の libtrapi.so 実装が済んでいる場合は同パターンを参照**

Run:
```bash
ls /home/k-yoshimi/program/task/tr/libtrapi.so 2>/dev/null
grep -n "libtrapi.so\|_pic.a\|mod_pic" /home/k-yoshimi/program/task/tr/Makefile | head -20
```
Expected: TR が L-4 を完了済みなら、`tr/Makefile` の libtrapi.so ターゲットや PIC ルールを丸ごと参考にできる。未完了なら独自に実装。

- [ ] **Step 3: 各依存 lib の Makefile に PIC ターゲットがあるか確認**

Run:
```bash
for d in eq pl lib adpost open-adas/adf11/adf11-lib mtxp; do
  echo "=== $d ==="
  grep -n "_pic\|fPIC" /home/k-yoshimi/program/task/$d/Makefile 2>/dev/null | head -5
done
ls /home/k-yoshimi/program/task/../bpsd/Makefile 2>/dev/null
```
Expected: いずれか（または全て）が PIC 未対応である可能性が高い。本フェーズで追加する。

- [ ] **Step 4: gfortran のバージョンと shared ld 動作の確認**

Run:
```bash
gfortran --version
ld --version | head -1
```
Expected: gfortran 9 以降、ld (GNU/binutils)。

- [ ] **Step 5: 空コミット**

Run:
```bash
git commit --allow-empty -m "chore(ti): start L-4 shared library build"
```

---

## Task 2: 依存ライブラリ各々に PIC ターゲットを追加（順序: 下位から）

**Files:**
- Modify: `../bpsd/Makefile` (リポジトリ内に存在する場合)
- Modify: `lib/Makefile`
- Modify: `eq/Makefile`
- Modify: `pl/Makefile`
- Modify: `mtxp/Makefile`
- Modify: `adpost/Makefile`
- Modify: `open-adas/adf11/adf11-lib/Makefile`

**方針:** 各 Makefile に共通パターンで以下を追加（例として `eq/Makefile`）:

```makefile
# PIC variant for libtiapi.so / libtrapi.so
OBJS_PIC = $(addprefix obj_pic/,$(OBJS))

obj_pic/%.o : %.f90
	@mkdir -p obj_pic mod_pic
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic -I./mod_pic $(MODINCLUDE_PIC)

obj_pic/%.o : %.f
	@mkdir -p obj_pic mod_pic
	$(FCFIXED) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic -I./mod_pic $(MODINCLUDE_PIC)

MODINCLUDE_PIC = $(subst /$(MOD),/mod_pic,$(MODINCLUDE))

libeq_pic.a: $(OBJS_PIC)
	$(AR) rcs $@ $(OBJS_PIC)

.PHONY: libeq_pic
libeq_pic: libeq_pic.a
```

**実施順:** 依存の下位（`bpsd`, `lib`, `mtxp`）から `pl`, `eq`, `adpost`, `open-adas/adf11/adf11-lib` の順で追加し、各ステップで `make lib*_pic.a` が通ることを確認する。

- [ ] **Step 1: bpsd（リポジトリ内に Makefile があれば）に PIC 追加**

Run:
```bash
ls /home/k-yoshimi/program/task/../bpsd/Makefile
cat /home/k-yoshimi/program/task/../bpsd/Makefile | head -40
```
Expected: bpsd の Makefile を確認。`libbpsd.a` ターゲットを参考に `libbpsd_pic.a` を追加。具体的編集は当該 Makefile の構造に合わせる。

リポジトリ外の場合（git submodule や external dep）は本タスクをスキップし、Task 5 で **直接 .o 取り込み（フォールバック b）** に切り替える。

Run（追加できたら）:
```bash
cd /home/k-yoshimi/program/task/../bpsd && make libbpsd_pic.a 2>&1 | tail -5
ls /home/k-yoshimi/program/task/../bpsd/libbpsd_pic.a
```
Expected: `libbpsd_pic.a` が生成される。

コミット:
```bash
git add ../bpsd/Makefile  # ← worktree 配下なら add 可能
git commit -m "build(bpsd): add libbpsd_pic.a target for shared lib"
```

bpsd がリポジトリ外なら以下のメモを残してコミット:
```bash
git commit --allow-empty -m "build(ti): bpsd is external; will use direct .o include in libtiapi.so link"
```

- [ ] **Step 2: lib/ に PIC 追加**

`lib/Makefile` を編集して上記パターンの PIC ターゲットを追加（`libtask_pic.a`, `libgrf_pic.a`, `libmds_pic.a` 各々に対応）。

Run:
```bash
cd /home/k-yoshimi/program/task/lib && make libtask_pic.a libgrf_pic.a libmds_pic.a 2>&1 | tail -5
ls /home/k-yoshimi/program/task/lib/lib*_pic.a
```
Expected: 3 ファイルが生成される。

コミット:
```bash
git add lib/Makefile
git commit -m "build(lib): add libtask_pic.a / libgrf_pic.a / libmds_pic.a targets"
```

- [ ] **Step 3: mtxp/ に PIC 追加**

`mtxp/Makefile` に MUMPS 用 PIC ターゲットを追加。MUMPS 自体は外部 lib なので、ここでは mtxp が生成する `lib*_mumps*.a` 等の PIC 版だけ。

Run:
```bash
cd /home/k-yoshimi/program/task/mtxp && make 2>&1 | tail -5
grep -n "lib.*\.a\b" Makefile | head -10
```
Expected: mtxp が生成する .a ファイル名を把握。それぞれに `_pic.a` 版を追加。

コミット:
```bash
git add mtxp/Makefile
git commit -m "build(mtxp): add PIC variants of MUMPS interface libs"
```

- [ ] **Step 4: pl/ に PIC 追加**

同パターンで `pl/Makefile` に `libpl_pic.a` を追加。

Run:
```bash
cd /home/k-yoshimi/program/task/pl && make libpl_pic.a 2>&1 | tail -5
ls libpl_pic.a
```
Expected: `libpl_pic.a` が生成される。

コミット:
```bash
git add pl/Makefile
git commit -m "build(pl): add libpl_pic.a target"
```

- [ ] **Step 5: eq/ に PIC 追加**

同パターンで `eq/Makefile` に `libeq_pic.a` を追加。

Run:
```bash
cd /home/k-yoshimi/program/task/eq && make libeq_pic.a 2>&1 | tail -5
ls libeq_pic.a
```
Expected: 生成される。

コミット:
```bash
git add eq/Makefile
git commit -m "build(eq): add libeq_pic.a target"
```

- [ ] **Step 6: adpost / open-adas/adf11/adf11-lib に PIC 追加**

同パターン:

Run:
```bash
cd /home/k-yoshimi/program/task/adpost && make lib-adpost_pic.a 2>&1 | tail -5
cd /home/k-yoshimi/program/task/open-adas/adf11/adf11-lib && make lib-adf11_pic.a 2>&1 | tail -5
ls /home/k-yoshimi/program/task/adpost/lib-adpost_pic.a /home/k-yoshimi/program/task/open-adas/adf11/adf11-lib/lib-adf11_pic.a
```
Expected: 両方生成される。

コミット:
```bash
git add adpost/Makefile open-adas/adf11/adf11-lib/Makefile
git commit -m "build(adpost,adas): add PIC variants for libtiapi.so"
```

---

## Task 3: ti 側に PIC ビルドルールと `libtiapi.so` ターゲットを追加

**Files:**
- Modify: `ti/Makefile`

- [ ] **Step 1: PIC ビルドルールと libtiapi.so ターゲットを追加**

`ti/Makefile` の末尾（distclean の前）に以下を追加:

```makefile
# ============================================================================
# Phase L-4: libtiapi.so (shared library)
# ============================================================================
# Sources for libtiapi.so: SRCS_CORE + SRCS_API. Graphics & menu are excluded.
SRCS_LIB = $(SRCS_CORE) $(SRCS_API)
OBJS_LIB_PIC = $(addprefix obj_pic/,$(SRCS_LIB:.f90=.o))

MODINCLUDE_PIC = -I./mod_pic \
                 -I../open-adas/adf11/adf11-lib/mod_pic \
                 -I../adpost/mod_pic -I../eq/mod_pic -I../pl/mod_pic \
                 -I../mtxp/mod_pic -I../lib/mod_pic -I../../bpsd/mod_pic

obj_pic/%.o : %.f90
	@mkdir -p obj_pic mod_pic
	$(FCFREE) $(FFLAGS) -fPIC -c $< -o $@ -Jmod_pic $(MODINCLUDE_PIC)

LIBS_PIC = ../adpost/lib-adpost_pic.a \
           ../open-adas/adf11/adf11-lib/lib-adf11_pic.a \
           ../eq/libeq_pic.a ../pl/libpl_pic.a \
           ../lib/libtask_pic.a ../lib/libgrf_pic.a \
           ../../bpsd/libbpsd_pic.a

.PHONY: libs-pic libtiapi

libs-pic:
	(cd ../../bpsd && $(MAKE) libbpsd_pic.a) || true
	(cd ../lib && $(MAKE) libtask_pic.a libgrf_pic.a)
	(cd ../mtxp && $(MAKE) all)   # if a *_pic target exists, list it here
	(cd ../open-adas/adf11/adf11-lib && $(MAKE) lib-adf11_pic.a)
	(cd ../adpost && $(MAKE) lib-adpost_pic.a)
	(cd ../pl && $(MAKE) libpl_pic.a)
	(cd ../eq && $(MAKE) libeq_pic.a)

libtiapi.so: libs-pic $(OBJS_LIB_PIC)
	$(FC) -shared -fPIC $(OBJS_LIB_PIC) \
	    -Wl,--whole-archive $(LIBS_PIC) -Wl,--no-whole-archive \
	    $(FLIBS) $(LIBX_MTX) -o libtiapi.so

libtiapi: libtiapi.so

.PHONY: clean-pic
clean-pic:
	rm -rf obj_pic mod_pic libtiapi.so
```

`clean:` ターゲットの末尾にも以下を追加:
```
clean : 
	rm -f ./#* ./*~ *.o nclass/*.o itg/*.o glf/*.o cytran/*.o mmm95/*.o mbgb/*.o a.out core *.a *.mod $(MOD)/*.mod
	rm -rf obj_pic mod_pic libtiapi.so
```

注: `--whole-archive` を使うのは、archive 内の全シンボルが shared lib に含まれることを保証するため。これにより Python から ctypes で呼ぶ際にシンボル不足を避けられる。問題が出た場合は外して `--no-undefined` で検証。

- [ ] **Step 2: PIC ビルド試行**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make clean-pic
make libtiapi.so 2>&1 | tee /tmp/libtiapi-build.log | tail -30
ls -la libtiapi.so
```
Expected: `libtiapi.so` が生成される。エラーがあれば `/tmp/libtiapi-build.log` を確認。

典型的失敗:
- `cannot find -leq` → `LIBS_PIC` のパスを絶対化
- 未定義シンボル `mtx_*` → mtxp の PIC lib を `LIBS_PIC` に追加
- `-fPIC` がコンパイラに通らない → ifort 等の場合は `-fpic`（小文字）

- [ ] **Step 3: シンボルが含まれることを確認**

Run:
```bash
nm -D /home/k-yoshimi/program/task/ti/libtiapi.so | grep -E "ti_init|ti_run|ti_get_state|ti_set_param|ti_finalize"
```
Expected: 5 つの関数すべてが `T` シンボル（テキストセクション）として表示される。

- [ ] **Step 4: コミット**

Run:
```bash
git add ti/Makefile
git commit -m "build(ti): add libtiapi.so target with PIC dependency libs"
```

---

## Task 4: C 側 link テスト `test_link.c` を追加

**Files:**
- Create: `ti/tests/c_abi/test_link.c`
- Modify: `ti/tests/c_abi/Makefile`

- [ ] **Step 1: test_link.c を作成**

作成: `ti/tests/c_abi/test_link.c`

```c
/*
 * test_link.c — L-4 link smoke. Loads libtiapi.so via ctypes-equivalent
 * direct linking, calls ti_init / ti_set_param (invalid name) / ti_finalize,
 * checks return codes.
 */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "ti_api.h"

int main(void) {
    int rc;

    rc = ti_init();
    if (rc != 0) {
        fprintf(stderr, "ti_init failed: rc=%d\n", rc);
        return 1;
    }
    printf("ti_init OK\n");

    rc = ti_set_param("RR", 6.2);
    if (rc != 0) {
        fprintf(stderr, "ti_set_param(RR) failed: rc=%d\n", rc);
        return 2;
    }
    printf("ti_set_param(RR=6.2) OK\n");

    rc = ti_set_param("NO_SUCH_PARAM_X", 1.0);
    if (rc == 0) {
        fprintf(stderr, "ti_set_param(unknown) should not return 0\n");
        return 3;
    }
    printf("ti_set_param(unknown) correctly returned %d\n", rc);

    rc = ti_finalize();
    if (rc != 0) {
        fprintf(stderr, "ti_finalize failed: rc=%d\n", rc);
        return 4;
    }
    printf("ti_finalize OK\n");

    printf("OK: ti link smoke passes\n");
    return 0;
}
```

- [ ] **Step 2: Makefile に test_link ターゲットを追加**

`ti/tests/c_abi/Makefile` に以下を追加（既存 `test:` を `test: test_compile_run test_param_registry_run test_link_run` に変更し、ターゲットを追加）:

```makefile
LIBTIAPI := $(TI_DIR)/libtiapi.so

test_link_run: test_link
	LD_LIBRARY_PATH=$(TI_DIR):$$LD_LIBRARY_PATH ./test_link

test_link: test_link.c $(TI_DIR)/ti_api.h $(LIBTIAPI)
	$(CC) $(CFLAGS) test_link.c -L$(TI_DIR) -ltiapi -Wl,-rpath,$(TI_DIR) -o test_link
```

注: `-ltiapi` で `libtiapi.so` を参照。`-Wl,-rpath` で実行時に同じパスから .so を探す（`LD_LIBRARY_PATH` 不要にするため）。

- [ ] **Step 3: link テストをビルド・実行**

Run:
```bash
cd /home/k-yoshimi/program/task/ti/tests/c_abi
make test_link 2>&1 | tail -10
./test_link
```
Expected:
```
ti_init OK
ti_set_param(RR=6.2) OK
ti_set_param(unknown) correctly returned 1
ti_finalize OK
OK: ti link smoke passes
```

失敗パターン:
- `undefined reference to ti_init` → `libtiapi.so` 内のシンボル名が `ti_init` でない可能性。`nm -D libtiapi.so | grep ti_` で実シンボル名を確認
- 実行時 `error while loading shared libraries: libtiapi.so` → rpath が効いていない。`LD_LIBRARY_PATH=$(TI_DIR) ./test_link` を試す
- `Symbol lookup error: undefined symbol: dmumps_` → mtxp の MUMPS lib が PIC リンクできていない。Task 2 Step 3 を再点検

- [ ] **Step 4: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add ti/tests/c_abi/test_link.c ti/tests/c_abi/Makefile
git commit -m "test(ti): add C-side link smoke for libtiapi.so"
```

---

## Task 5: フォールバック準備（PIC 失敗時の代替手段）

**Files:**
- 必要に応じて修正

**目的:** Task 2 で一部の依存 lib が PIC 化困難な場合、以下フォールバックを順に試す（設計書 7.4 節準拠）:

| 案 | 内容 |
|---|---|
| (a) PIC リビルド | 本計画の主軸 |
| (b) ソース直接統合 | 依存 lib のソースを `ti/Makefile` の `OBJS_LIB_PIC` に直接含める |
| (c) `-Wl,--whole-archive` で非 PIC `.a` を使う | リンク時警告は出るが、x86_64 では動くことが多い |

- [ ] **Step 1: 案 a が完走したか判定**

Task 4 Step 3 で test_link が成功 → Task 5 はスキップして Task 6 へ。

- [ ] **Step 2: 失敗していたらフォールバック (c) を試行**

`LIBS_PIC` を非 PIC の元 `.a` に置き換え:
```makefile
LIBS_PIC = ../adpost/lib-adpost.a \
           ../open-adas/adf11/adf11-lib/lib-adf11.a \
           ../eq/libeq.a ../pl/libpl.a \
           ../lib/libtask.a ../lib/libgrf.a \
           ../../bpsd/libbpsd.a
```

`libtiapi.so` ターゲットを以下に変更:
```makefile
libtiapi.so: $(OBJS_LIB_PIC)
	$(FC) -shared -fPIC $(OBJS_LIB_PIC) \
	    -Wl,--whole-archive $(LIBS_PIC) -Wl,--no-whole-archive \
	    $(FLIBS) $(LIBX_MTX) -o libtiapi.so
```

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make clean-pic && make libtiapi.so 2>&1 | tail -10
nm -D libtiapi.so | grep ti_init
```
Expected: 警告（"relocation R_X86_64_..." 等）が出ても OK。`ti_init` シンボルがあれば成功。

問題なければ Task 2 で追加した `_pic.a` ターゲットは温存（将来戻せるよう）。

- [ ] **Step 3: それでもダメなら案 (b) を採用**

依存 lib のソース .f90 を直接 `OBJS_LIB_PIC` に追加する形に Makefile を書き換える。本計画ではこの案の詳細手順は省略（実装時に依存ソースのリストを動的に決定）。

- [ ] **Step 4: 採用したフォールバック案をコミット（必要時のみ）**

Run:
```bash
git add ti/Makefile
git commit -m "build(ti): switch libtiapi.so to fallback (c): whole-archive non-PIC libs"
```

---

## Task 6: 既存 ti バイナリと L-0 回帰テストが PASS することを最終確認

**Files:**
- なし

- [ ] **Step 1: ti バイナリが影響を受けていないこと**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make clean && make 2>&1 | tail -5
ls -la ti libti.a
```
Expected: 従来通り生成される。

- [ ] **Step 2: L-0 回帰テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: 全テスト PASS。

- [ ] **Step 3: c_abi テスト全て PASS**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make libtiapi.so 2>&1 | tail -3
cd /home/k-yoshimi/program/task/ti/tests/c_abi && make test
```
Expected: `test_compile`, `test_param_registry`, `test_link` 全て PASS。

---

## Task 7: PR 作成

- [ ] **Step 1: 変更ファイル確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: 修正は `ti/Makefile` + 各依存の `Makefile`（最大 6〜7 ファイル）、新規は `ti/tests/c_abi/test_link.c`。

- [ ] **Step 2: push と PR**

Run:
```bash
git push -u origin feature/ti-library-L4-shared-lib-build
gh pr create --base develop \
  --title "build(ti): add libtiapi.so shared library (L-4)" \
  --body "Phase L-4: produces libtiapi.so via PIC rebuild of dependent libs (eq/pl/lib/adpost/adas/bpsd). Adds C link smoke test_link. ti binary unchanged; L-0 regression PASS."
```

---

## Dependencies

- 前段階: L-3 マージ済み (`ti_param_registry.f90`)。
- 後段階: L-5 が `libtiapi.so` を Python ctypes でロードする。

## Fallback

| 障害 | 対処 |
|---|---|
| 依存 lib の `_pic.a` がリンクできない | 案 (c) `--whole-archive` 非 PIC、または案 (b) ソース直接統合 |
| `dmumps_` 未定義 | mtxp の MUMPS interface が PIC 化できているか、または `LIBX_MTX` がリンク行に入っているか確認 |
| ifort/PGI コンパイラで `-fPIC` 不可 | `-fpic`（小文字）または `-fPIC` を `OFLAGS` ではなく専用変数に分離 |
| `ti_*` シンボルが `_` 接尾辞で出る | gfortran のデフォルトシンボル装飾。`BIND(C, NAME="ti_init")` で固定化済みのはずだが、`nm` で確認し違えば `BIND` 属性を再点検 |
