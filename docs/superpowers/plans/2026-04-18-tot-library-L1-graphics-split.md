# TOT Library Phase L-1: グラフィクス分離（最小化アプローチ） 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** tot ライブラリ化に向けて「グラフィクス（GS*）依存を実行時にバイパスできる仕組み」を最小コードで導入する。tot 本体の構造は維持し、ライブラリ化フェーズ (L-4) で graphics 抜きの shared library をビルドできる土台を作る。

**Architecture:** tot の構造的特徴は **「totmain.f90 が GSOPEN/GSCLOS を呼び、totmenu.f90 は各サブモジュールの menu に dispatch するだけ」** という極めてシンプルな構成である。tot 自体には graphics ルーチンは無く、グラフィクスは各サブモジュール（tr/eq/...）の menu 内に閉じ込められている。したがって **tr のような「graphics ファイル群を分離する」という大規模な作業は不要**。代わりに本フェーズでは: (a) `totmain.f90` の GSOPEN/GSCLOS をコンパイル時スイッチで無効化できるラッパに置き換える、(b) `tot/Makefile` に `SRCS_CORE` / `SRCS_MENU` の論理分離（コメントベース）を入れて L-2 以降の Makefile 改修の起点を作る、の 2 点に絞る。

**Tech Stack:** Fortran 90 preprocessor (`#ifdef NO_GRAPHICS` / `#ifndef`) または equivalent な `IF (use_graphics) THEN` ランタイム分岐, gfortran (`-cpp` フラグ), 既存 tot/Makefile。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md`（A.4 Graphics 設計決定: 別モジュール化）。tot は分離対象ファイル数がゼロのため、設計趣旨を「ランタイム/コンパイル時切り替え」に翻訳して適用する。

**前提条件:** L-0 完了。`tot_demo2014_short` と `tot_ht6m_short` の回帰テストが PASS している。

---

## Why graphics-split as a sub-phase is mostly N/A for tot

`tr/Makefile` では `SRCS_GRAPHICS = trgout.f90 trgrar.f90 trgrat.f90 trgrap.f90 trgrae.f90 trgrad.f90 trgram.f90 trgsub.f90 trg2d.f90` の **9 ファイル** を分離する作業が必要だった。しかし tot は:

- `tot/totmain.f90`: 80 行強。`GSOPEN`/`GSCLOS` を 2 か所呼ぶのみ。
- `tot/totmenu.f90`: 70 行弱。各モジュールの `*_menu` を呼ぶ dispatcher のみ。
- tot 専用の graphics ルーチンは **存在しない**。

したがって「ファイル分離」という意味の graphics-split は **N/A**。代わりに L-1 では:

1. `GSOPEN`/`GSCLOS` 呼び出しに `#ifndef TOT_NO_GRAPHICS` のガードを入れる
2. `tot/Makefile` に `SRCS_CORE` / `SRCS_MENU` のコメントブロック分離を入れる
3. `tot_no_graphics` 簡易ビルド検証（preprocessor フラグで `tot` バイナリがリンクできるか確認）

の 3 点だけ実施する。実際に「graphics ライブラリを引かない shared library」を作るのは L-4。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `tot/totmain.f90` | 修正 | `GSOPEN`/`GSCLOS` を `#ifndef TOT_NO_GRAPHICS` ガード内に配置 |
| `tot/Makefile` | 修正 | `SRCS_CORE` / `SRCS_MENU` のコメント分離、`tot_no_graphics` ターゲット追加（オプション） |
| `tot/README.md` | 新規 | tot のグラフィクス方針と将来 L-4 のリンク戦略を文書化 |
| `test_run/test_definitions.conf` | 修正なし | （既存 `tot_*` ケースをそのまま流用） |

**方針:**
- 既存 `tot` バイナリの動作は **完全不変**（preprocessor マクロ無指定時）。
- `TOT_NO_GRAPHICS` を define したビルドでは `GSOPEN`/`GSCLOS` を呼ばないが、`tot` バイナリ自体は依然として menu 起動可能（無理に lib 化はしない）。
- L-2 で `tot_api.f90` を作るときは「`TOT_NO_GRAPHICS` を define した上で graphics シンボル（GSOPEN 等）に依存しない」状態を再利用する。

---

## Task 1: 作業用ブランチ作成と L-0 baseline 確認

**Files:** なし

- [ ] **Step 1: ブランチ作成**

Run:
```bash
cd /home/k-yoshimi/program/task
git checkout develop
git pull
git checkout -b feature/tot-library-l1-graphics-split
```

- [ ] **Step 2: L-0 の baseline テストが PASS することを再確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。

PASS しない場合は L-0 が未完了 / 環境問題。先に解消する。

- [ ] **Step 3: 初期コミット（マーカー）**

Run:
```bash
git commit --allow-empty -m "chore(tot): start L-1 graphics-split sub-phase"
```

---

## Task 2: tot のグラフィクス依存箇所を棚卸しする

**Files:** 調査のみ

- [ ] **Step 1: tot 配下の GS* / 描画呼び出しを列挙**

Run:
```bash
grep -n "GSOPEN\|GSCLOS\|GS[A-Z]" /home/k-yoshimi/program/task/tot/*.f90
```
Expected: `totmain.f90:45: CALL GSOPEN` と `totmain.f90:75: CALL GSCLOS` の 2 か所のみが見つかる。

- [ ] **Step 2: tot 配下に他に graphics 依存がないか確認**

Run:
```bash
grep -rn "PGFA\|GFRAME\|GTEXT" /home/k-yoshimi/program/task/tot/ 2>&1 | head
```
Expected: ヒットなし（tot は GS の薄いラッパしか持たない）。

- [ ] **Step 3: 棚卸し結果を本 plan に追記する commit を打つ**

Run:
```bash
git commit --allow-empty -m "docs(tot): inventory graphics dependencies (GSOPEN/GSCLOS only in totmain)"
```

---

## Task 3: `totmain.f90` に preprocessor ガードを追加

**Files:**
- Modify: `tot/totmain.f90`

**目的:** `TOT_NO_GRAPHICS` を define したビルドで `GSOPEN`/`GSCLOS` をスキップ。define なしでは挙動完全不変。

- [ ] **Step 1: 失敗するテスト準備（事前に L-0 baseline が変わらないことだけ確認できる体制）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short
echo "baseline pass status: $?"
```
Expected: PASS（exit=0）。

- [ ] **Step 2: `tot/totmain.f90` の GSOPEN/GSCLOS にガードを入れる**

`tot/totmain.f90` の以下 2 か所を修正:

変更前（GSOPEN 周辺、~45 行付近）:
```fortran
  IF(nrank.EQ.0) THEN
     WRITE(6,*) '##### /TASK/TOT  2019/02/25 #####'
     CALL GSOPEN
     OPEN(7,STATUS='SCRATCH',FORM='FORMATTED')
  ENDIF
```

変更後:
```fortran
  IF(nrank.EQ.0) THEN
     WRITE(6,*) '##### /TASK/TOT  2019/02/25 #####'
#ifndef TOT_NO_GRAPHICS
     CALL GSOPEN
#endif
     OPEN(7,STATUS='SCRATCH',FORM='FORMATTED')
  ENDIF
```

変更前（GSCLOS 周辺、~75 行付近）:
```fortran
  IF(nrank.EQ.0) THEN
     CALL GSCLOS
     CLOSE(7)
  END IF
```

変更後:
```fortran
  IF(nrank.EQ.0) THEN
#ifndef TOT_NO_GRAPHICS
     CALL GSCLOS
#endif
     CLOSE(7)
  END IF
```

- [ ] **Step 3: preprocessor を有効化するため Makefile に `-cpp` を加える**

`tot/Makefile` の totmain ビルドルール周辺を確認:

Run:
```bash
grep -n "FCFREE\|FCFIXED\|cpp\|fpp" /home/k-yoshimi/program/task/tot/Makefile /home/k-yoshimi/program/task/make.header 2>&1 | head -10
```

`make.header` で既に `FCFREE` に preprocessor が組み込まれていればそのまま使える（`gfortran` のデフォルト .F90 拡張子なら有効）。`.f90` 拡張のままでも `-cpp` を付ければ良い。

- [ ] **Step 4: `tot/Makefile` の `.f90.o` ルールに `-cpp` を追加**

変更前:
```makefile
.f90.o :
	$(FCFREE) $(FFLAGS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
```

変更後:
```makefile
.f90.o :
	$(FCFREE) $(FFLAGS) -cpp $(EXTRA_DEFS) -c $< -o $@ $(MODDIR) $(MODINCLUDE)
```

`EXTRA_DEFS` は通常空。`make EXTRA_DEFS=-DTOT_NO_GRAPHICS` のように外部から指定。

- [ ] **Step 5: 通常ビルドで挙動不変を確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make clean && make tot 2>&1 | tail -5
ls -la tot
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: ビルド成功、2/2 PASS。L-0 baseline と数値一致。

- [ ] **Step 6: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/totmain.f90 tot/Makefile
git commit -m "feat(tot): guard GSOPEN/GSCLOS with TOT_NO_GRAPHICS preprocessor"
```

---

## Task 4: `TOT_NO_GRAPHICS` ビルドが通ることを検証

**Files:** なし（ビルド検証）

- [ ] **Step 1: `EXTRA_DEFS=-DTOT_NO_GRAPHICS` でリビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make clean
make tot EXTRA_DEFS=-DTOT_NO_GRAPHICS 2>&1 | tail -10
ls -la tot
```
Expected: ビルド成功。`tot` バイナリが新規生成。

注: 現段階では `LIBS` に `libgrf.a` 等のグラフィクスライブラリを含めたままなので、リンク時には GSOPEN シンボルは依然として解決される。実際にライブラリから graphics を外すのは L-4。L-1 では「ソース側で呼び出さない」状態を確立するのが目的。

- [ ] **Step 2: NO_GRAPHICS ビルドでも従来テストが通る（dump 機構は影響を受けない）**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。

なお `gs` ファイルは生成されなくなるが、`tot_regress.dat` の中身は同一。L-0 の許容誤差 `1e-10` 内で一致する。

- [ ] **Step 3: 通常ビルドに戻して pass 確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make clean && make tot 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short
```
Expected: PASS（通常ビルドで baseline と一致）。

- [ ] **Step 4: コミット（NO_GRAPHICS ビルド成功を記録）**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "test(tot): verify TOT_NO_GRAPHICS build succeeds and regression passes"
```

---

## Task 5: `tot/Makefile` に `SRCS_CORE` / `SRCS_MENU` の論理分離コメントを入れる

**Files:**
- Modify: `tot/Makefile`

**目的:** L-2/L-4 で `tot_api.f90` を追加する際に、どのソースが「ライブラリにも入れる core」「menu バイナリだけが必要」かを分かりやすくする。実際の SRCS 変数は分けず、コメントだけで意図を残す（最小変更原則）。

- [ ] **Step 1: コメント分離を入れる**

`tot/Makefile` の `SRCS = totmenu.f90 totregress.f90` 行の周辺を以下に変更:

変更前:
```makefile
SRCS = totmenu.f90 totregress.f90
```

変更後:
```makefile
# Source layout (logical groups; SRCS still single list for now):
#   SRCS_CORE  : files needed by both `tot` binary and future libtotapi.so
#                (regression dump goes here so library users can also dump).
#   SRCS_MENU  : interactive dispatcher only used by `tot` binary.
#   SRCS_API   : added in L-2 (tot_state.f90, tot_api.f90, tot_param_registry.f90).
SRCS_CORE = totregress.f90
SRCS_MENU = totmenu.f90
SRCS      = $(SRCS_CORE) $(SRCS_MENU)
```

- [ ] **Step 2: ビルドが壊れていないか確認**

Run:
```bash
cd /home/k-yoshimi/program/task/tot
make clean && make tot 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tot_demo2014_short tot_ht6m_short
```
Expected: 2/2 PASS。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/Makefile
git commit -m "build(tot): introduce SRCS_CORE/SRCS_MENU logical split (comment-level)"
```

---

## Task 6: `tot/README.md` を作成して L-1 方針を文書化

**Files:**
- Create: `tot/README.md`

- [ ] **Step 1: README 新規作成**

作成: `tot/README.md`

```markdown
# TASK/TOT — Integrated Transport Simulator Orchestrator

`tot` is the integrated front-end that composes the per-physics modules
(`pl, eq, tr, ti, fp, dp, wr, wm`) into a single interactive simulator.
The current `totmain.f90` is intentionally thin: it initializes each
module, parses its namelist, and dispatches to `tot_menu` which routes
the user to the per-module menus.

## Build

```sh
make            # standard tot binary (interactive, with graphics)
make EXTRA_DEFS=-DTOT_NO_GRAPHICS   # tot binary without GSOPEN/GSCLOS calls
```

The `TOT_NO_GRAPHICS` preprocessor guard is the foundation for the
upcoming Phase L-4 (`libtotapi.so`) build, which links against the PIC
versions of per-module libraries and excludes graphics dependencies.

## Regression tests (Phase L-0)

`totregress.f90` writes `tot_regress.dat` when run with
`TOT_REGRESS_DUMP=1`. See `test_run/README.md` and
`docs/superpowers/plans/2026-04-18-tot-library-L0-baseline.md`.

## Library-ization roadmap (Phase L)

| Phase | Status | Description |
|-------|--------|-------------|
| L-0   | done   | Integrated regression baselines |
| L-1   | (this) | Graphics call guarded by preprocessor flag |
| L-2   | TODO   | `tot_state.f90`, `tot_api.f90` C-ABI stubs |
| L-3   | TODO   | `tot_param_registry.f90` (union of submodule namelist) |
| L-4   | TODO   | `libtotapi.so` shared library build |
| L-5   | TODO   | Python wrapper `python/totlib/` |
| L-6   | TODO   | 4-layer integrated tests |
| L-7   | TODO   | Parameter-optimization workflow |

See specs in `docs/superpowers/specs/`.
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add tot/README.md
git commit -m "docs(tot): add README documenting build modes and L-roadmap"
```

---

## Verification (Phase L-1 完了基準)

- [ ] `tot/totmain.f90` の `GSOPEN`/`GSCLOS` が `#ifndef TOT_NO_GRAPHICS` でガードされている。
- [ ] `make tot`（通常ビルド）で挙動完全不変、L-0 baseline と数値一致。
- [ ] `make tot EXTRA_DEFS=-DTOT_NO_GRAPHICS` でビルドが通る。
- [ ] `tot/Makefile` に `SRCS_CORE` / `SRCS_MENU` の論理分離コメントが入っている。
- [ ] `tot/README.md` で L-1 方針と L-roadmap が文書化されている。
- [ ] `./run_tests.sh tot_demo2014_short tot_ht6m_short` が両ビルドモードで PASS。

---

## Dependencies & Fallback

**前提:** L-0 完了。

**産出物:** L-2 以降が `tot_api.f90` をビルドする際の「graphics 抜きビルド」が可能であることを保証。

**Fallback:**
- preprocessor `#ifndef` が gfortran の `.f90` 拡張で動かない場合 → ファイル拡張子を `totmain.F90` に rename（gfortran は `.F90` で自動的に preprocessor を有効化）。
- `-cpp` フラグが既存 `make.header` のフラグと競合する場合 → `tot/Makefile` の `.f90.o` ルールでだけ `-cpp` を追加（局所化）。
- `EXTRA_DEFS` 経由のフラグ伝播が想定通りでない場合 → `tot/Makefile` 内に `TOTMAIN_DEFS = -DTOT_NO_GRAPHICS` をオプトイン変数として用意。

---

## Out of scope（次フェーズ送り）

- 実際に `libgrf.a` をリンクから外す → L-4
- `tot_no_graphics_lib` の Makefile ターゲット追加 → L-4
- per-module の graphics 分離検証 → 各 per-module phase
