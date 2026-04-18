# Phase L-1: Graphics 分離 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `tr/Makefile` 内の `SRCS` を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` の 3 グループに分離し、後段の L-4 で graphics を除外した shared library を組めるよう前準備する。**`tr2` バイナリの構成・数値結果は一切変えない。**

**Architecture:** 既存の `SRCS` 変数の中身を 3 つの make 変数に分割するだけの「カット&ペースト」リファクタ。`SRCS = $(SRCM) $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` という形で再合成して、`OBJS` 以下の派生変数や `tr2` ターゲットの定義は触らない。Fortran ソース・モジュール依存関係には一切手を入れない。

**Tech Stack:** GNU Make, gfortran, 既存 `tr/Makefile`、Phase 0 の `test_run/` 回帰テスト基盤。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §7.1 (Makefile 改修案), §9 (L-1), §A.4 (Graphics 別モジュール化採用根拠)。

---

## File Structure

このサブフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `tr/Makefile` | 修正 | `SRCS` を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` に分割 |

**方針:**
- 変更は `tr/Makefile` の SRCS 定義部のみ（行数で 10 行以内）。
- `OBJS` の合成、`libtr2.a` ターゲット、`tr2` ターゲット、コンパイルルールはいずれも未変更。
- Fortran ソースファイルそのものは触らない。
- 「最小変更原則」: 既存開発者が `git diff` を見て一目で意味が分かる差分にすること。リネーム・並び替え・コメント追加は別 PR にしない。

---

## Task 1: ブランチ作成と前提確認

**Files:**
- なし

- [ ] **Step 1: L-0 完了済みを確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | grep -i "phase l-0\|tr-library-phase-l0" | head -3
```
Expected: L-0 の merge commit が見える。無ければ L-0 を先に終えること（撤退）。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/tr-library-phase-l1 origin/develop
```

- [ ] **Step 3: 現状の SRCS 行を控える**

Run:
```bash
sed -n '27,40p' tr/Makefile
```
Expected: `SRCS=trinit.f90 ...` から `trloop.f90 trmenu.f90` までの複数行が表示される（設計書 §7.1 のリスト）。

---

## Task 2: SRCS を 3 グループに分割

**Files:**
- Modify: `tr/Makefile` (SRCS 定義部のみ)

- [ ] **Step 1: `tr/Makefile` の SRCS 定義を以下に置換**

変更前（現状、Phase 0 で `trregress.f90` を追加済み）:
```makefile
SRCS=trinit.f90 trparm.f90 trview.f90 \
     trmetric.f90 trprof.f90 trprep.f90 \
     trufsub.f90 tr_ufile_task.f90 tr_ufile_topics.f90 trufile.f90 \
     trfile.f90 trhelp.f90 \
     trexec.f90 trcalc.f90 \
     tradat.f90 trcdbm.f90 trmodels.f90 trcoef.f90 tritg.f90 \
     trrslt.f90 trpnb.f90 trprf.f90 trpnf.f90 trpel.f90 trpsc.f90 trmdlt.f90 \
     trgout.f90 trgrar.f90 trgrat.f90 trgrap.f90 trgrae.f90 \
     trgrad.f90 trgram.f90 trgsub.f90 trfout.f90 trregress.f90 \
     trloop.f90 trmenu.f90
```

変更後（3 グループに分割し、`SRCS` を再合成）:
```makefile
# Core computation sources (no graphics, no interactive menu).
# This subset will be linked into libtrapi.so in Phase L-4.
SRCS_CORE=trinit.f90 trparm.f90 trview.f90 \
     trmetric.f90 trprof.f90 trprep.f90 \
     trufsub.f90 tr_ufile_task.f90 tr_ufile_topics.f90 trufile.f90 \
     trfile.f90 trhelp.f90 \
     trexec.f90 trcalc.f90 \
     tradat.f90 trcdbm.f90 trmodels.f90 trcoef.f90 tritg.f90 \
     trrslt.f90 trpnb.f90 trprf.f90 trpnf.f90 trpel.f90 trpsc.f90 trmdlt.f90 \
     trfout.f90 trregress.f90 \
     trloop.f90

# Graphics sources (gsaf/grafix dependent). Excluded from libtrapi.so.
SRCS_GRAPHICS=trgout.f90 trgrar.f90 trgrat.f90 trgrap.f90 trgrae.f90 \
     trgrad.f90 trgram.f90 trgsub.f90

# Interactive menu (only used by the tr2 binary).
SRCS_MENU=trmenu.f90

SRCS=$(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)
```

注:
- `trgout.f90` は `SRCS_CORE` から除外し `SRCS_GRAPHICS` に移動した（`trgout` は名前通り graphics 出力）。`trfout.f90` は file output なので CORE 側に残す。
- `trloop.f90` は `trregress` を `USE` する核計算ループなので CORE。
- `OBJS=$(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))` 行は変更不要（再合成された `SRCS` を見れば従来と同じ並び）。

### `SRC2D` / `SRC3S` についての注記（review #9 反映）

`tr/Makefile` には `SRCS` とは別に **`SRC2D=trg2d.f90` と `SRC3S=trg3d.f90`**（変数名は `SRC3D` ではなく **`SRC3S`**）が独立して定義されており、それぞれ `OBJ2D`, `OBJ3D` を生成して `tr2` 以外の補助ターゲット（2D/3D グラフィクス変種）にリンクされる。本 L-1 の `SRCS` 三分割では `SRC2D`/`SRC3S` には**一切手を加えない**（既存定義のまま残す）。

確認コマンド:
```bash
grep -nE "^SRC2D|^SRC3S|^OBJ2D|^OBJ3D" tr/Makefile
```
Expected: `SRC2D=trg2d.f90`、`SRC3S=trg3d.f90`、および `OBJ2D=$(addprefix $(OBJDIR)/, $(SRC2D:.f90=.o))`、`OBJ3D=$(addprefix $(OBJDIR)/, $(SRC3D:.f90=.o))` がそのまま見えること（`OBJ3D` 側は `SRC3D` を参照しているが現状の Makefile 通り — 既存の挙動に合わせて touch しない）。

**Phase L-4 への引き継ぎ（PIC 取り扱い方針）:**

- `trg2d.f90` / `trg3d.f90` は graphics 専用なので **`libtrapi.so` には含めない**（`SRCS_GRAPHICS` 同様の扱い）。L-4 の `SRCS_LIB = $(SRCM) $(SRCS_CORE) $(SRCS_API)` に `SRC2D` / `SRC3S` は加えない。
- ただしこの 2 ファイルの PIC ビルドが `tr2`（および 2D/3D 補助ターゲット）の挙動に副作用を与えてはならない。`obj/` (非 PIC) と `obj/pic/` (PIC) は L-4 で別ディレクトリに分けるため衝突しない。
- L-4 で graphics 系を PIC 対応するかどうかは **保留**：libtrapi.so のエンドユーザは Python から graphics を叩かないため、`SRC2D`/`SRC3S` の PIC 化は不要。将来 graphics も .so 化する場合は別 PR で `SRCS_GRAPHICS` および `SRC2D`/`SRC3S` をまとめて `libtrgrf_pic.a` にする方針を採る（設計書 §A.4）。
- L-4 の hand-off チェックリストに「`SRC2D` / `SRC3S` は libtrapi.so に含めない」を明記すること（L-4 plan の Task 3 注記に追記済み）。

- [ ] **Step 2: 並び順保存の確認**

Run:
```bash
make -C tr -np 2>/dev/null | grep -m1 "^SRCS = " | tr ' ' '\n' | head -50
```
Expected: 元 `SRCS` と同じ順序（`trinit.f90 trparm.f90 ... trgout.f90 trgrar.f90 ... trmenu.f90`）。`trgout.f90` の位置だけ「core 部の末尾」から「graphics 部の先頭」に動くため、最終並びは: `... trregress.f90 trloop.f90 trgout.f90 ... trgsub.f90 trmenu.f90` となる。

ここで「`trgout.f90` の Fortran module 依存関係が変わるかどうか」を念のため確認:
```bash
grep -n "USE " tr/trgout.f90 | head -10
grep -n "USE.*trgout\|USE trgout" tr/*.f90
```
Expected: `trgout` を `USE` するファイルが `trloop` 等の core ソースに存在しないこと。あれば core 内に戻すか、`trgout` の依存を別途整理する PR を立てる（その場合 L-1 は撤退）。

---

## Task 3: ビルドと回帰テスト

**Files:**
- なし

- [ ] **Step 1: clean ビルド**

Run:
```bash
cd /home/k-yoshimi/program/task
(cd tr && make clean && make 2>&1 | tail -8)
```
Expected: `tr2` が再生成、エラーなし。

- [ ] **Step 2: 回帰テスト 3 ケース PASS**

Run:
```bash
cd test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tail -10
```
Expected: 3/3 PASS（Phase 0 baseline と完全一致）。

- [ ] **Step 3: 失敗時の撤退判断**

万が一 FAIL したら（compile/link が core/graphics の境界で壊れた場合）、Step 1 の Makefile 変更を `git checkout -- tr/Makefile` で戻し、L-1 を中止して原因を別 PR で議論する。

---

## Task 4: コミットと PR

**Files:**
- なし

- [ ] **Step 1: コミット**

Run:
```bash
git add tr/Makefile
git commit -m "build(tr): split SRCS into CORE/GRAPHICS/MENU groups

Pure Makefile refactor. The composed SRCS variable contains the same
files as before, so tr2 build artifacts and numerical output are
unchanged. Sets up Phase L-4 to link libtrapi.so from SRCS_CORE only."
```

- [ ] **Step 2: PR 作成**

Run:
```bash
gh pr create --base develop --title "build(tr): Phase L-1 split SRCS into CORE/GRAPHICS/MENU" \
  --body "Phase L-1: Graphics 分離。Makefile の SRCS を 3 グループに分けるだけのリファクタで、tr2 の構成・数値結果は変更しません。設計書 §7.1, §A.4。回帰 3 ケース PASS。"
```

---

## 撤退条件 / フォールバック

| 状況 | 判断 |
|---|---|
| `trgout` を core ソースが `USE` している | 当該依存を解消する別 PR を先行させ、L-1 を保留 |
| 回帰テストが FAIL | Makefile 変更を revert、L-1 を中止 |
| Make の並列ビルドで不整合 | `make -j1` で再現確認、`SRCS` 順序を厳密に既存と同一化 |

## 受け入れ基準

- [ ] `tr2` バイナリが従来通り生成される
- [ ] 回帰 3 ケース PASS（tol `1e-10`）
- [ ] `tr/Makefile` の差分は SRCS 定義部のみ
- [ ] PR が develop に merge 可能

## 依存

- L-0 完了
