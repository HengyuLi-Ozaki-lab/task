# Phase L-4: libtrapi.so ビルド 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tr/libtrapi.so` を `SRCS_CORE + SRCS_API` から PIC ビルドで生成する。依存ライブラリ（eq, pl, lib, mtxp, bpsd）にも `libXX_pic.a` ターゲットを追加して PIC オブジェクトを取り揃える。**`tr2` バイナリの構成・数値結果は変えない。**

**Architecture:** 設計書 §7 の方針 (a) **PIC 付き再ビルド** を採用。各依存ライブラリの Makefile に `libXX_pic.a` 追加ターゲットと PIC コンパイルルール (`obj/pic/%.o`) を 5〜10 行追加する。`tr/Makefile` に `libtrapi.so` ターゲットと `OBJ_LIB_PIC` 変数を追加する。フォールバック (b ソース統合 / c whole-archive) は §7.4 表に従う。

**Tech Stack:** GNU Make, gfortran `-fPIC -shared`, ld, ar, 既存の各依存 Makefile（`eq/Makefile`, `pl/Makefile`, `lib/Makefile`, `mtxp/Makefile`, `../bpsd/Makefile`）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §7 (ビルドシステム), §7.4 (フォールバック), §A.11 (PIC 採用根拠), §10 (リスク)。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `eq/Makefile` | 修正 | `libeq_pic.a` ターゲット追加（5〜10 行） |
| `pl/Makefile` | 修正 | `libpl_pic.a` ターゲット追加 |
| `lib/Makefile` | 修正 | `libmds_pic.a`, `libtask_pic.a`, `libgrf_pic.a` 追加 |
| `mtxp/Makefile` | 修正 | mtx 系の PIC 版（必要に応じて） |
| `../bpsd/Makefile` | 修正 | `libbpsd_pic.a` 追加 |
| `tr/Makefile` | 修正 | `OBJ_LIB_PIC`、`libtrapi.so` ターゲット、`mod_pic/` ディレクトリ |
| `tr/tests/c_abi/Makefile` | 修正 | `libtrapi.so` 経由のリンクオプション追加 |

**方針:**
- 既存 `libXX.a` ターゲットは **そのまま温存**。`libXX_pic.a` は **追加** のみ。
- PIC オブジェクトは `obj/pic/` 等の専用ディレクトリに置き、既存 `obj/` と分離。modfile も `mod_pic/` に分ける。
- 既存開発者の `make` ワークフロー（`make` でフルビルド、`make clean` で全消去）を変えない。`libtrapi.so` のビルドは追加コマンド（例: `make libtrapi.so`）で発火。
- ステップごとに「既存 `tr2` の build & 回帰テストが通ること」を確認することで、副作用ゼロを担保。

---

## Task 1: ブランチと前提

- [ ] **Step 1: L-3 完了確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | grep -i "phase l-3" | head -3
```
Expected: L-3 merge commit。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/tr-library-phase-l4 origin/develop
```

- [ ] **Step 3: 既存 PIC 設定の探索**

Run:
```bash
grep -nE "fPIC|libtrapi|libXX_pic" eq/Makefile pl/Makefile lib/Makefile mtxp/Makefile ../bpsd/Makefile tr/Makefile 2>&1 | head -30
```
Expected: ほとんどヒットしない（PIC 対応未実装）。`mtxp/Makefile` に部分的な PIC 痕跡があれば流用可能。

---

## Task 2: 依存ライブラリに `libXX_pic.a` ターゲットを追加

**Files:**
- Modify: `eq/Makefile`, `pl/Makefile`, `lib/Makefile`, `../bpsd/Makefile`

各 Makefile に同じパターンを追加するため、まず 1 つ (`eq`) で動かし、コピペで他に展開する。

- [ ] **Step 1: `eq/Makefile` に PIC ターゲットを追加**

末尾に以下を追記:

```makefile
# --- PIC build (for libtrapi.so, Phase L-4) ---
OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)

OBJ_EQ_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS:.f=.o))

$(OBJDIR_PIC)/%.o: %.f
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFIXED) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@

$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@

libeq_pic.a: $(OBJ_EQ_PIC)
	$(AR) rcs libeq_pic.a $(OBJ_EQ_PIC)

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) libeq_pic.a
```

注:
- `SRCS` 変数は `eq/Makefile` の既存 SRCS 一覧（fixed-form `.f` ファイル群）。`SRCS:.f=.o` で .f → .o 拡張子変換。`.f90` ソースが混在する場合は `OBJ_EQ_PIC` を 2 行に分けて両方扱う。
- `MODDIR_PIC` は既存 `mod/` と衝突しないよう `mod_pic/` を新設。
- 既存 `libeq.a` ターゲットや `clean` ターゲットは **触らない**。

- [ ] **Step 2: 動作確認**

Run:
```bash
cd /home/k-yoshimi/program/task/eq
make libeq_pic.a 2>&1 | tail -10
ls libeq_pic.a obj/pic/ | head -5
file libeq_pic.a
```
Expected: `libeq_pic.a` が生成、`obj/pic/*.o` が PIC でコンパイル済み（`readelf -h obj/pic/eqcalc.o | grep Type` で `REL` 確認）。

- [ ] **Step 3: 同パターンを `pl/Makefile`, `lib/Makefile`, `../bpsd/Makefile` に展開**

- `pl/Makefile`: 同じテンプレート、ターゲット `libpl_pic.a`、対象 SRCS は `pl/Makefile` の既存定義に合わせる。
- `lib/Makefile`: ターゲット 3 つ `libmds_pic.a`, `libtask_pic.a`, `libgrf_pic.a`。各々 SRCS_MDS / SRCS_TASK / SRCS_GRF 相当。`libgrf_pic.a` は graphics 出力に使うため libtrapi では不要だが、依存解決上ビルドしておく（最終リンクで除外）。
- `../bpsd/Makefile`: ターゲット `libbpsd_pic.a`。

各々ビルド確認:
```bash
(cd pl && make libpl_pic.a 2>&1 | tail -3)
(cd lib && make libmds_pic.a libtask_pic.a 2>&1 | tail -3)
(cd ../bpsd && make libbpsd_pic.a 2>&1 | tail -3)
```
Expected: 全て成功、`*_pic.a` ファイル生成。

- [ ] **Step 4: 既存 `make`（非 PIC）が壊れていないことを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
(cd eq && make clean && make 2>&1 | tail -3)
(cd pl && make clean && make 2>&1 | tail -3)
```
Expected: 既存 `libeq.a`, `libpl.a` が問題なく再生成。

- [ ] **Step 5: コミット**

Run:
```bash
git add eq/Makefile pl/Makefile lib/Makefile ../bpsd/Makefile
git commit -m "build: add PIC variants (libXX_pic.a) for libtrapi.so

Adds opt-in PIC targets to eq/pl/lib/bpsd Makefiles. Existing
libXX.a targets and clean rules are unchanged."
```

---

## Task 3: `tr/Makefile` に `libtrapi.so` ターゲット

**Files:**
- Modify: `tr/Makefile`

- [ ] **Step 1: PIC コンパイルルールと OBJ_LIB_PIC 追加**

`tr/Makefile` の既存コンパイルルールの直後（`MODINCLUDE=` の前後）に追加:

```makefile
# --- PIC build (Phase L-4) ---
OBJDIR_PIC=obj/pic
MODDIR_PIC=mod_pic
PIC_FLAGS=-fPIC -J$(MODDIR_PIC) -I$(MODDIR_PIC)
MODINCLUDE_PIC= -I./$(MODDIR_PIC) -I../pl/mod_pic -I../eq/mod_pic \
                -I../lib/mod_pic -I../mtxp/mod_pic \
                -I../../bpsd/mod_pic

$(OBJDIR_PIC)/%.o: %.f90
	@mkdir -p $(OBJDIR_PIC) $(MODDIR_PIC)
	$(FCFREE) $(FFLAGS) $(PIC_FLAGS) -c $< -o $@ $(MODINCLUDE_PIC)

# Sources linked into libtrapi.so: SRCM (TRCOMM modules) + SRCS_CORE + SRCS_API.
# Excludes SRCS_GRAPHICS and SRCS_MENU.
SRCS_LIB=$(SRCM) $(SRCS_CORE) $(SRCS_API)
OBJ_LIB_PIC=$(addprefix $(OBJDIR_PIC)/, $(SRCS_LIB:.f90=.o))

LIBS_PIC=../eq/libeq_pic.a ../pl/libpl_pic.a \
         ../lib/libmds_pic.a ../lib/libtask_pic.a \
         ../../bpsd/libbpsd_pic.a

libtrapi.so: $(OBJ_LIB_PIC) $(LIBS_PIC)
	$(FC) -shared -fPIC \
	    -Wl,-soname,libtrapi.so \
	    $(OBJ_LIB_PIC) \
	    -Wl,--start-group $(LIBS_PIC) -Wl,--end-group \
	    $(FLIBS) $(LIBX_MTX) \
	    -o libtrapi.so

# Build PIC deps on demand
../eq/libeq_pic.a:
	(cd ../eq; make libeq_pic.a)
../pl/libpl_pic.a:
	(cd ../pl; make libpl_pic.a)
../lib/libmds_pic.a:
	(cd ../lib; make libmds_pic.a)
../lib/libtask_pic.a:
	(cd ../lib; make libtask_pic.a)
../../bpsd/libbpsd_pic.a:
	(cd ../../bpsd; make libbpsd_pic.a)

clean_pic:
	-rm -rf $(OBJDIR_PIC) $(MODDIR_PIC) libtrapi.so
```

注:
- `SRCS_LIB = $(SRCM) $(SRCS_CORE) $(SRCS_API)` で graphics/menu を除外。
- `--start-group / --end-group` で循環依存を解決（gfortran + ld の標準パターン）。
- `mtxp` の PIC 対応は本サブフェーズでは保留（既存 `LIBX_MTX` で間に合うか L-4 Step 3 で確認）。必要なら mtxp 用の `*_pic.a` を別タスクで追加。

- [ ] **Step 2: ビルド試行**

Run:
```bash
cd /home/k-yoshimi/program/task/tr
make libtrapi.so 2>&1 | tee /tmp/libtrapi_build.log | tail -30
ls -la libtrapi.so
file libtrapi.so
nm -D libtrapi.so | grep -E "^[0-9a-f]+ T tr_(init|run|set_param|get_state|finalize)$"
```
Expected:
- `libtrapi.so` が生成。
- `file libtrapi.so` で `ELF 64-bit LSB shared object`。
- `nm -D` で 5 つの C シンボル `tr_init/tr_run/tr_set_param/tr_get_state/tr_finalize` がエクスポートされている。

- [ ] **Step 3: PIC リビルド失敗時のフォールバック**

設計書 §7.4 に従い、以下の順で試行:

| 試行 | 内容 | 切替方法 |
|---|---|---|
| (a) PIC rebuild | 上記 Step 2 | デフォルト |
| (c) `-Wl,--whole-archive` | 既存 `.a` をそのまま使う | `LIBS_PIC=../eq/libeq.a ...` に置換、リンク行を `-Wl,--whole-archive $(LIBS) -Wl,--no-whole-archive` に変更 |
| (b) ソース直結合 | 依存ソースをコピーして `tr/` で PIC ビルド | 緊急避難。`tr/lib_inline/` を作って必要な .f を symlink |

判断基準: PIC リンクで `relocation R_X86_64_32 against ... can not be used when making a shared object` エラーが出たら (a) NG。`-fPIC` 抜けの再ビルド漏れを最初に疑い、対応 Makefile を修正。

- [ ] **Step 4: 既存 `tr2` ビルドを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tr
make clean && make 2>&1 | tail -3
ls tr2 libtrapi.so
```
Expected: `make` のデフォルトターゲット `all` で `tr2` のみ生成。`libtrapi.so` は別途明示ターゲットとして要求した時のみビルド。
（`all` に `libtrapi.so` を含めるかは要相談。L-4 では含めない方針: 既存 `make` 行動を変えない）

---

## Task 4: 回帰テスト

- [ ] **Step 1: tr2 の数値が変わっていないこと**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -5
```
Expected: 3/3 PASS。Makefile 変更は既存 `tr2` のリンク経路に一切手を入れていないため不変。

- [ ] **Step 2: libtrapi.so の C スモーク**

L-2/L-3 の C スモークを `libtrapi.so` 経由のリンクに切り替える。

`tr/tests/c_abi/Makefile` に追加:

```makefile
TRLIB_SO=../../libtrapi.so

test_smoke_so: test_smoke.c $(TRLIB_SO)
	$(CC) -I../.. test_smoke.c -L../.. -ltrapi -Wl,-rpath,../.. -o test_smoke_so

run_so: test_smoke_so
	./test_smoke_so
```

Run:
```bash
cd /home/k-yoshimi/program/task/tr
make libtrapi.so 2>&1 | tail -3
cd tests/c_abi
make run_so 2>&1 | tail -5
```
Expected: `OK: init/run/finalize cycle returned 0`。

---

## Task 5: コミットと PR

- [ ] **Step 1: 段階コミット**

Run:
```bash
git add tr/Makefile
git commit -m "build(tr): add libtrapi.so target (PIC, graphics excluded)"

git add tr/tests/c_abi/Makefile
git commit -m "test(tr): C smoke linked against libtrapi.so"
```

注: Task 2 のコミットは既に存在（依存 Makefile 群）。

- [ ] **Step 2: PR**

Run:
```bash
gh pr create --base develop --title "build(tr): Phase L-4 libtrapi.so via PIC rebuild" \
  --body "Phase L-4: libtrapi.so を PIC ビルドで生成、依存に libXX_pic.a を追加。tr2 と数値結果は不変。設計書 §7。フォールバックは §7.4 を参照。"
```

---

## 撤退条件 / フォールバック

設計書 §7.4 表に従う:

| 試行 | 失敗内容 | 次の手 |
|---|---|---|
| (a) PIC rebuild | `R_X86_64_32` 再配置エラー | -fPIC 漏れを探す。残れば (c) へ |
| (c) whole-archive | `multiple definition` 等 | (b) ソース統合へ |
| (b) ソース直結合 | gfortran モジュール解決失敗 | mtxp/bpsd 等の問題は本サブを保留して別 PR で議論 |

**最低受け入れ:** いずれかの方式で `libtrapi.so` ができ、C シンボル 5 つがエクスポートされていること。

## 受け入れ基準

- [ ] `tr/libtrapi.so` が生成される
- [ ] `nm -D libtrapi.so` で `tr_init/tr_run/tr_set_param/tr_get_state/tr_finalize` 5 シンボルがエクスポート
- [ ] `tr2` のビルドが従来通り動き、数値が回帰 3 ケースで一致
- [ ] C スモーク（`.so` 経由）が PASS
- [ ] 既存 `make clean` 後の `make` で副作用なく `tr2` が再生成

## 依存

- L-3 完了
