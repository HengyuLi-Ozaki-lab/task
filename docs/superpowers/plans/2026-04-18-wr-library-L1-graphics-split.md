# WR ライブラリ化 Phase L-1: Graphics 分離 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** WR 本体のソースを「コア計算」「グラフィクス」「メニュー」の 3 グループに **Makefile レベルだけで分離** し、後続の L-2 以降で `libwrapi.so` をビルドする際に graphics 依存を簡単に外せるようにする。

**Architecture:** ソースファイルそのものは触らない（`wrgout.f90` の中身は不変、`wrmenu.f90` も不変）。`wr/Makefile` の `SRCS = ...` を `SRCS_CORE / SRCS_GRAPHICS / SRCS_MENU` の 3 つに分割し、`SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` という形に書き換えるのみ。`libwr.a` のリンク内容は完全に変わらず、`wr` バイナリ・既存 namelist 入力・回帰テスト dump も完全に同一結果。L-2 以降で `SRCS_LIB = $(SRCS_CORE) $(SRCS_API)` の形でグラフィクス抜きセットを作るための「足場」。

**Tech Stack:** Make のみ。Fortran ソースは無変更。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` セクション 7.1（Graphics 分離）と Phase L-1。

---

## モジュール調査サマリ

`wr/` 全 15 ファイル + `wrmain.f90`（PROGRAM）を以下に分類:

### SRCS_CORE — Phase L-2 以降の `libwrapi.so` に組み込む計算コア (12 ファイル)

| ファイル | 行数 | 責務 | グラフィクス依存? |
|---|---|---|---|
| `wrcomm.f90`     | 138  | グローバル状態 (`wrcomm_parm`, `wrcomm`)、ALLOCATE 群 | なし |
| `wrinit.f90`     | 186  | デフォルト値 (`WR_INIT`) | なし |
| `wrparm.f90`     | 187  | namelist `WR` 読み込み (`wr_parm`, `wrnlin`, `wr_chek`) | なし (`USE equnit` のみ) |
| `wrview.f90`     | 53   | パラメータ表示 (`WR_VIEW`)：stdout のみ | なし |
| `wrsub.f90`      | 23k  | dispersion 周りの低レベルユーティリティ | なし |
| `wrsetupr.f90`   | 246  | ray セットアップ (`wr_setup_rays`, `WRSETUP`) | なし |
| `wrsetupb.f90`   | 6.1k | beam セットアップ | なし |
| `wrsetup.f90`    | 24   | 上記 2 つを mode_beam で振り分け | なし |
| `wrexecr.f90`    | 37k  | ray tracing 本体 + `wr_calc_pwr` | `USE libgrf` のみ（コアは数値計算）|
| `wrexecb.f90`    | 23k  | beam tracing 本体 | なし |
| `wrexec.f90`     | 38   | ray/beam ディスパッチ + L-0 dump フック | なし |
| `wrregress.f90`  | 新規 | L-0 で追加した dump | なし |
| `wrfile.f90`     | 5.7k | バイナリ save/load | なし |

### SRCS_GRAPHICS — `wr` バイナリにのみリンク、`libwrapi.so` からは除外 (1 ファイル)

| ファイル | 行数 | 責務 | 依存 |
|---|---|---|---|
| `wrgout.f90` | 90k | `WR_GOUT`, `WRGRF1..7`, `WRGRFB1..4`, `WRGRF11A/B`（GSAF 依存） | `USE plgout`, GSAF symbols |

### SRCS_MENU — 対話メニュー、`wr` バイナリにのみリンク (1 ファイル)

| ファイル | 行数 | 責務 |
|---|---|---|
| `wrmenu.f90` | 87 | `WR_MENU`：`wr_setup → wr_exec → wr_gout → wr_save/load` を stdin で起動 |

### PROGRAM (Makefile の `wr` ターゲットのみ)

| ファイル | 用途 |
|---|---|
| `wrmain.f90` | `PROGRAM wr` エントリポイント — `libwr.a` には含めず、`wr` バイナリリンク時にだけ追加 |

注: `wrgout.f90` 内で `wr_calc_pwr` 由来のデータ（`pos_nrs/pwr_nrs` 等）を参照する箇所はあるが、依存方向は `wrgout → wrcomm → wr_calc_pwr` であり、`wr_calc_pwr`（コア側）は `wrgout` に依存しない。Step 4 で `wrcalc_pwr` 内の `USE libgrf` の使い道を確認し、必要なら下流タスクで切り出す（本 Phase ではノータッチ）。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wr/Makefile` | 修正 | `SRCS` を 3 グループに分割（中身は同一）|

**方針:**
- ソース変更は **0 ファイル**。
- Makefile のみで「カテゴリ表示」を導入する。
- `libwr.a` のオブジェクト構成と `wr` バイナリのリンク内容は完全保持。
- 既存の dependency rule（`$(OBJDIR)/wrexec.o:` 等）は触らない。

---

## Task 1: ブランチ作成と現状ビルドの確認

**Files:** なし

- [ ] **Step 1: develop の最新を取得して Phase L-1 ブランチを作る**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull origin develop
git checkout -b feature/wr-library-L1-graphics-split
```
Expected: ブランチ作成成功。L-0 が既に develop に merge 済みであること（HEAD が L-0 commit を含む）。

- [ ] **Step 2: 現状の wr ビルド成果物を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make 2>&1 | tail -5
ls -la libwr.a wr
nm libwr.a | grep -E "T (wr_setup|wr_exec|wr_init|wr_gout|wr_menu)" | sort > /tmp/wr_libwr_symbols_before.txt
wc -l /tmp/wr_libwr_symbols_before.txt
```
Expected:
- `wr` バイナリと `libwr.a` が生成される。
- シンボル一覧が `/tmp/wr_libwr_symbols_before.txt` に保存される（後でリグレッション照合に使う）。

- [ ] **Step 3: L-0 の回帰テストが緑であることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh wr_iter_lhcd wr_test001 wr_tst2_ec
```
Expected: 3 ケースとも PASS。

- [ ] **Step 4: マーカーコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "chore(wr): start Phase L-1 graphics split scaffolding"
```

---

## Task 2: `wr/Makefile` の `SRCS` を 3 グループに分割

**Files:**
- Modify: `wr/Makefile`

- [ ] **Step 1: 現在の `SRCS` 定義を確認**

Run:
```bash
grep -n "^SRCS\|^OBJS\|^all\|^libwr.a\|^wr :" /home/k-yoshimi/program/task/wr/Makefile
```
Expected: 行 37-44 付近に SRCS 定義が見える。

- [ ] **Step 2: `SRCS` を 3 グループに分割**

Modify `/home/k-yoshimi/program/task/wr/Makefile`.

注: 以下の `Old` ブロックは **L-0 マージ後の Makefile** の状態を表す（L-0 で
`wrregress.f90` が `wrsetup.f90` と `wrexec.f90` の間に追加されている前提）。
もし grep 結果と一致しない場合は L-0 が正しく適用されていない可能性が高いので、
そこで作業を停止して L-0 をやり直すこと。

Old (L-0 適用後の状態; lines 37-44 付近):
```
SRCS = wrcomm.f90 wrinit.f90 wrparm.f90 wrview.f90 \
       wrsub.f90 \
       wrsetupr.f90 wrexecr.f90 wrsetupb.f90 wrexecb.f90 \
       wrsetup.f90 wrregress.f90 wrexec.f90 \
       wrgout.f90 wrfile.f90 \
       wrmenu.f90

OBJS = $(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))
```

New:
```
# --- Source groups (Phase L-1 split) ---
# SRCS_CORE: pure computation; will be reused for libwrapi.so in Phase L-4.
# SRCS_GRAPHICS: GSAF-based plot output; excluded from libwrapi.so.
# SRCS_MENU: interactive stdin menu; excluded from libwrapi.so.
SRCS_CORE = wrcomm.f90 wrinit.f90 wrparm.f90 wrview.f90 \
            wrsub.f90 \
            wrsetupr.f90 wrexecr.f90 wrsetupb.f90 wrexecb.f90 \
            wrsetup.f90 wrregress.f90 wrexec.f90 \
            wrfile.f90

SRCS_GRAPHICS = wrgout.f90

SRCS_MENU = wrmenu.f90

SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)

OBJS = $(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))
```

- [ ] **Step 3: ビルドして既存と完全に同じ成果物が出来ることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make clean && make 2>&1 | tail -10
ls -la libwr.a wr
nm libwr.a | grep -E "T (wr_setup|wr_exec|wr_init|wr_gout|wr_menu)" | sort > /tmp/wr_libwr_symbols_after.txt
diff /tmp/wr_libwr_symbols_before.txt /tmp/wr_libwr_symbols_after.txt
echo "diff exit=$?"
```
Expected: 
- ビルド成功。
- diff の出力が空、`exit=0`。`libwr.a` のシンボル構成が完全に同じ。

- [ ] **Step 4: 回帰テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh wr_iter_lhcd wr_test001 wr_tst2_ec
```
Expected: 3 ケースとも PASS（数値も完全一致）。

- [ ] **Step 5: 既存 TR/EQ/TX への副作用ゼロ確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh
```
Expected: 全件 PASS。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/Makefile
git commit -m "refactor(wr): split SRCS into CORE/GRAPHICS/MENU groups (Makefile only)"
```

---

## Task 3: 分離が機能していることを Makefile レベルで再確認

**Files:** なし（検証のみ）

- [ ] **Step 1: Make 変数として 3 グループが取得できることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make -p 2>&1 | grep -E "^SRCS_(CORE|GRAPHICS|MENU)\s*:?=" | head -10
```
Expected: 3 つの `SRCS_*` 定義が make の variable database に出る。

- [ ] **Step 2: `SRCS_CORE` のみで個別ビルドできることを軽く検証**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make $(echo $(make -p 2>&1 | grep -E "^SRCS_CORE" | head -1 | awk -F= '{print $2}') | sed 's/\.f90/.o/g; s/^/obj\//; s/ / obj\//g')
echo "exit=$?"
```
Expected: `SRCS_CORE` 中の各 .o がビルド済み（既に Task 2 でビルド済みなので "Nothing to be done"）。

注: このステップはあくまで「Makefile が変数を正しく拾うか」の確認用。失敗しても次タスクに影響しない。

- [ ] **Step 3: コミット不要（検証のみ）**

---

## Task 4: 後続フェーズへの引き継ぎコメントを Makefile に明記

**Files:**
- Modify: `wr/Makefile`

- [ ] **Step 1: ヘッダコメントに L-2 以降への意図を追記**

Modify `/home/k-yoshimi/program/task/wr/Makefile`. Locate the line right above `SRCS_CORE = ...`:

Old:
```
# --- Source groups (Phase L-1 split) ---
# SRCS_CORE: pure computation; will be reused for libwrapi.so in Phase L-4.
# SRCS_GRAPHICS: GSAF-based plot output; excluded from libwrapi.so.
# SRCS_MENU: interactive stdin menu; excluded from libwrapi.so.
```

New:
```
# --- Source groups (Phase L-1 split) ---
# SRCS_CORE: pure computation; will be reused for libwrapi.so in Phase L-4.
# SRCS_GRAPHICS: GSAF-based plot output; excluded from libwrapi.so.
# SRCS_MENU: interactive stdin menu; excluded from libwrapi.so.
#
# When Phase L-4 lands, libwrapi.so will be built from:
#   SRCS_LIB = $(SRCS_CORE) $(SRCS_API)
# where SRCS_API = wr_state.f90 wr_param_registry.f90 wr_api.f90
# (no graphics, no menu).
```

- [ ] **Step 2: ビルドして変化なしを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/wr
make 2>&1 | tail -3
```
Expected: "Nothing to be done" もしくは Makefile 解釈のみ。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add wr/Makefile
git commit -m "docs(wr): annotate SRCS groups with Phase L-4 wiring intent"
```

---

## 完了基準

- [ ] `wr/Makefile` の `SRCS` が `SRCS_CORE`, `SRCS_GRAPHICS`, `SRCS_MENU` の 3 グループに分割されている
- [ ] `libwr.a` と `wr` バイナリの内容が分割前と完全に同じ（`nm` シンボル一致）
- [ ] WR 回帰テスト 3 ケースが PASS
- [ ] 既存 TR/EQ/TX テストに回帰なし
- [ ] L-4 で `SRCS_LIB = $(SRCS_CORE) $(SRCS_API)` が書きやすい状態になっている

## 撤退条件

- `nm` でシンボル差分が出る場合 → SRCS の分割で順序が変わったかを疑い、`SRCS_CORE` の並びを既存と一致させる
- 並び依存が解消できない場合 → 一旦 `SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` の順を旧 SRCS と完全同一にする

## 依存

- 前提: L-0 完了（`wrregress.f90` が `SRCS_CORE` に含まれていること）
- 後続: L-2 (`SRCS_API` を新設し、`SRCS_LIB = $(SRCS_CORE) $(SRCS_API)` を追加) の前提
