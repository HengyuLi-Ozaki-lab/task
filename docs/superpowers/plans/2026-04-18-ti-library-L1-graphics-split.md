# TI Library Phase L-1: Graphics Separation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ti/` モジュールの Makefile を CORE / GRAPHICS / MENU の 3 グループに分離し、`tigout.f90` を core ビルドから外せる状態にする（後の L-4 で `libtiapi.so` を作る際、graphics リンクを避けるため）。既存 `ti` 実行バイナリは従来通り全モジュールを含めてビルドされ、挙動・数値結果は完全に不変。

**Architecture:** Makefile の `SRCS` 単一定義を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` の 3 つに分け、`SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` という形に書き換える。Fortran ソースには一切手を入れない。L-0 で確立した回帰テストでビルド・数値の不変を毎ステップ検証する。

**Tech Stack:** GNU Make, Fortran 90 (ソース無変更)。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` (4.4 Graphics 質問の決定 (d) 別モジュール化、 9. サブフェーズ計画 L-1)。

---

## File Structure

このフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `ti/Makefile` | 修正 | `SRCS` を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` の 3 グループに分離 |

その他のファイル（`.f90` 含む）には一切変更を加えない。

---

## Task 1: 前提確認（L-0 完了とビルド可能性）

**Files:**
- なし

- [ ] **Step 1: L-0 がマージ済みでブランチ起点が develop にあることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin
git log --oneline origin/develop -5
git checkout -b feature/ti-library-L1-graphics-split origin/develop
```
Expected: `develop` HEAD に L-0 のコミット（`test(ti): commit initial regression baselines (ti_min, ti_ar, ti_w)` 等）が見える。新ブランチに切り替わる。

- [ ] **Step 2: 現在の ti/Makefile SRCS 行を読む**

Run:
```bash
grep -n "^SRCS\|^OBJS" /home/k-yoshimi/program/task/ti/Makefile
sed -n '29,45p' /home/k-yoshimi/program/task/ti/Makefile
```
Expected: 既存 `SRCS=` 定義（`ticomm.f90 tiadas.f90 ... timenu.f90`）が見える。L-0 で追加された `tiregress.f90` も含まれている。

- [ ] **Step 3: L-0 のテストが PASS することを確認（ベースライン保護）**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh ti_min ti_ar ti_w
```
Expected: ti ビルド OK、3 ケースすべて PASS。

- [ ] **Step 4: 空コミット**

Run:
```bash
git commit --allow-empty -m "chore(ti): start L-1 graphics split scaffolding"
```

---

## Task 2: 各 .f90 ファイルの責務を分類

**Files:**
- なし（調査のみ）

- [ ] **Step 1: 各ソースの種別を確認**

Run:
```bash
ls /home/k-yoshimi/program/task/ti/*.f90
grep -l "^MODULE \|^PROGRAM " /home/k-yoshimi/program/task/ti/*.f90
```
Expected: 14 個の `.f90` ファイルとそれぞれが定義する MODULE/PROGRAM を把握。

- [ ] **Step 2: 分類を以下に固定**

本計画で確定する分類:

**SRCS_CORE** (libtiapi.so の対象、graphics と menu 以外):
- `ticomm.f90` — 共通変数 (ticomm_parm + ticomm)
- `tiadas.f90` — ADAS interface
- `tiinit.f90` — 初期化
- `tiparm.f90` — namelist parser
- `ticoef.f90` — 係数計算
- `tisource.f90` — ソース項
- `ticalc.f90` — 計算ルーチン
- `tirecord.f90` — 結果保存
- `tiprep.f90` — 計算前処理
- `tiregress.f90` — L-0 で追加した regression dump（env-guarded）
- `tiexec.f90` — メインループ実行

**SRCS_CORE 候補に含めない（理由: 現行 `ti/Makefile` の `SRCS` 未登録）:**
- `tinclass.f90` — NCLASS interface。ファイルは存在するが現行ビルドでは使われていない（実機 `grep "SRCS" ti/Makefile` で確認済: `SRCS= ticomm.f90 tiadas.f90 tiinit.f90 tiparm.f90 ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 tiprep.f90 tiexec.f90 tigout.f90 timenu.f90`）。L-1 のスコープ（graphics 分離）では追加しない。将来 `MODEL_NC` 等で必要になった時点で別 PR で `SRCS_CORE` に追加。
- `ticdbm.f90` — CDBM model interface。同上の理由で除外。

**SRCS_GRAPHICS** (libtiapi.so から除外):
- `tigout.f90` — GSAF/GSCLOS 等の描画

**SRCS_MENU** (libtiapi.so から除外):
- `timenu.f90` — 対話メニュー (READ(5,...))

- [ ] **Step 3: tinclass / ticdbm が現行 SRCS にあるか確認（除外判定の追認）**

Run:
```bash
grep "tinclass\|ticdbm" /home/k-yoshimi/program/task/ti/Makefile
```
Expected: ヒット **無し**（現行 `SRCS=` には含まれていない）。本計画でも `SRCS_CORE` から外す方針を維持。

将来含めることになった場合（L-3+ で `MODEL_NC` 系を有効化したい等）は、別 PR で `SRCS_CORE` に追加し、依存 lib（NCLASS の static lib）のリンクと PIC 化（L-4 で `_pic.a` 必要）を併せて行う。

- [ ] **Step 4: 分類を plan に固定したことをメモコミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git commit --allow-empty -m "docs(ti): lock L-1 file classification (CORE/GRAPHICS/MENU)"
```

---

## Task 3: Makefile を 3 グループに分割

**Files:**
- Modify: `ti/Makefile`

- [ ] **Step 1: 既存 SRCS 定義を新形式に書き換える**

`ti/Makefile` の以下のブロック（L-0 後想定）:
```
SRCS=   ticomm.f90 tiadas.f90 \
	tiinit.f90 tiparm.f90 \
	ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
        tiprep.f90 tiregress.f90 tiexec.f90 \
        tigout.f90 timenu.f90
```
を以下に置換:

```
# Core sources: included in both `ti` binary and (later) libtiapi.so.
# Graphics and menu are split out so libtiapi.so can be built without them.
SRCS_CORE=   ticomm.f90 tiadas.f90 \
	tiinit.f90 tiparm.f90 \
	ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 \
        tiprep.f90 tiregress.f90 tiexec.f90

SRCS_GRAPHICS= tigout.f90

SRCS_MENU=     timenu.f90

SRCS=$(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)
```

注: `SRCS=$(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` の連結により、`OBJS=$(SRCS:.f90=.o)` は引き続き全 .o を生成する（既存 `ti` バイナリのリンクには影響なし）。

- [ ] **Step 2: ビルドして既存バイナリが従来通り作られることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make clean
make 2>&1 | tail -10
ls -la ti libti.a
```
Expected: `ti` と `libti.a` が生成される。`tigout.o` も `libti.a` に含まれる（`ar t libti.a | grep tigout.o` で確認可）。

- [ ] **Step 3: ar の中身に全 .o があることを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
ar t libti.a | sort
```
Expected: `ticomm.o`, `tiexec.o`, `tigout.o`, `timenu.o`, `tiregress.o` 等、全ファイルが含まれる。

- [ ] **Step 4: L-0 回帰テストが PASS することを確認**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh ti_min ti_ar ti_w
```
Expected: 3/3 PASS。Makefile 編集が数値挙動に影響していないことを確認。

- [ ] **Step 5: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add ti/Makefile
git commit -m "refactor(ti): split Makefile SRCS into CORE/GRAPHICS/MENU groups"
```

---

## Task 4: ダミーターゲット `srcs-core-list` を追加して将来の libtiapi.so に備える

**Files:**
- Modify: `ti/Makefile`

**目的:** L-4 で `libtiapi.so` を追加するときに「core ソース一覧を確認するヘルパ」が必要。phony target で簡単に出せるようにする。これは新規ターゲットで、既存ビルドには無影響。

- [ ] **Step 1: phony helper を追加**

`ti/Makefile` の `clean :` ターゲットの直前に以下を追加:

```
.PHONY: srcs-core-list srcs-graphics-list srcs-menu-list

srcs-core-list:
	@echo $(SRCS_CORE)

srcs-graphics-list:
	@echo $(SRCS_GRAPHICS)

srcs-menu-list:
	@echo $(SRCS_MENU)
```

- [ ] **Step 2: 動作確認**

Run:
```bash
cd /home/k-yoshimi/program/task/ti
make srcs-core-list
make srcs-graphics-list
make srcs-menu-list
```
Expected:
- core: `ticomm.f90 tiadas.f90 tiinit.f90 tiparm.f90 ticoef.f90 tisource.f90 ticalc.f90 tirecord.f90 tiprep.f90 tiregress.f90 tiexec.f90`
- graphics: `tigout.f90`
- menu: `timenu.f90`

- [ ] **Step 3: コミット**

Run:
```bash
git add ti/Makefile
git commit -m "build(ti): add srcs-{core,graphics,menu}-list phony targets"
```

---

## Task 5: 最終回帰確認と PR

**Files:**
- なし

- [ ] **Step 1: clean ビルド + 全テスト**

Run:
```bash
cd /home/k-yoshimi/program/task/ti && make clean && make 2>&1 | tail -5
cd /home/k-yoshimi/program/task/test_run && ./run_tests.sh
```
Expected: ti ビルド OK、全テスト PASS。

- [ ] **Step 2: 変更ファイルの最終確認**

Run:
```bash
git diff --stat origin/develop..HEAD
```
Expected: `ti/Makefile` のみが modified、`.f90` ファイルは無変更。

- [ ] **Step 3: push と PR**

Run:
```bash
git push -u origin feature/ti-library-L1-graphics-split
gh pr create --base develop \
  --title "refactor(ti): split Makefile into CORE/GRAPHICS/MENU groups (L-1)" \
  --body "Phase L-1: Makefile-only refactor preparing for L-4 libtiapi.so. No Fortran changes, no behavior change. Verified by L-0 regression tests (3/3 PASS)."
```

---

## Dependencies

- 前段階: L-0 マージ済み (`tiregress.f90` と 3 baseline が `develop` に存在)。
- 後段階: L-2/L-3/L-4 が `SRCS_CORE` を参照する。

## Fallback

| 障害 | 対処 |
|---|---|
| `make clean && make` で OBJS 不足エラー | `SRCS=$(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` の連結が正しく `OBJS:=$(SRCS:.f90=.o)` を生成しているか確認。Make の `:=` vs `=` の違いに注意 |
| 数値結果が変わる（あり得ない想定） | Makefile 順序変化でリンク順が変わった可能性。`SRCS_CORE` 内のファイル順序を旧 `SRCS` と完全一致させる |
| ti binary がリンクできなくなる | `LIBS=libti.a ...` のリンク順を変更していないか確認。本計画では `LIBS` には触らない |
