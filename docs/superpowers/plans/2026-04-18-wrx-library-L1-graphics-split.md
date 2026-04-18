# WRX Library-ization Phase L-1: Graphics Separation 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `wrx/` モジュールの Makefile を **`SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` の 3 グループに分離**し、後続 L-4 で `libwrxapi.so` を構築する際に graphics 依存（`libgrf`, X11, GS, plgout）を排除可能にする。本フェーズではコード自体は触らず Makefile のみ変更し、既存 `wrx/wr` バイナリの数値結果が L-0 の baseline と完全一致することを CI で確認する。

**Architecture:** L-0 で作成した `wrx/Makefile` の `SRCS = ...` 1 つの定義を `SRCS_CORE`, `SRCS_GRAPHICS`, `SRCS_MENU`, `SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` の 4 行に分割する。`wrgout.f90` は graphics 専用（`USE plgout`、`libgrf` 経由の GSAF/GSCLOS 描画依存）。`wrmenu.f90` は対話 UI でグラフィックも呼び出すので menu。残り（17 ファイル）が core。**新規ファイルは作らない**、既存ファイルへのコード変更もない、Makefile の整理だけ。

**Tech Stack:** GNU Make, gfortran. 既存 build chain のみ。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §7.1（SRCS_CORE / SRCS_GRAPHICS / SRCS_MENU 分離）を wrx に適用。

**WRX 固有の注意:** `wr/` と `wrx/` は同じ `wrgout.f90` ファイル名を持つが**中身は別**（wrx は wr に対し追加の WRGRF11A/B 等を持つ）。本フェーズでも他モジュール (`wr/`) には触らない。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `wrx/Makefile` | 修正 | `SRCS` を `SRCS_CORE`, `SRCS_GRAPHICS`, `SRCS_MENU` に 3 分割。`SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` で従来 ALL を維持 |

**方針:** L-1 では Makefile 1 ファイル のみ変更。本フェーズの最終出力は L-0 の baseline と数値完全一致。

---

## Task 1: ブランチ準備とビルド事前確認

- [ ] **Step 1: フェーズ用ブランチ**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git checkout develop
git pull
git checkout -b feature/wrx-library-L1-graphics-split
```

- [ ] **Step 2: 現状の SRCS を確認**

Run:
```bash
grep -n "^SRCS" /home/k-yoshimi/program/task-private/wrx/Makefile
```
Expected: `SRCS = wrcomm.f90 wrinit.f90 wrparm.f90 wrprep.f90 wrview.f90 \ ... wrxregress.f90 \ wrmenu.f90` の 1 ブロック。L-0 で `wrxregress.f90` が追加されている。

- [ ] **Step 3: build 動作確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/wrx && make 2>&1 | tail -5
```
Expected: `wrx/wr` が生成される。エラーなし。

---

## Task 2: 各ファイルの graphics 依存を確認

- [ ] **Step 1: graphics ライブラリ参照を grep**

Run:
```bash
cd /home/k-yoshimi/program/task-private/wrx
grep -lE "USE\s+(plgout|libgrf)|GSAF|GSCLOS|GSOPEN|PAGES|CALL\s+PAGES" *.f90
```
Expected: `wrgout.f90` (主)、`wrmenu.f90` (経由) が出る可能性。core 17 ファイルには graphics 依存なし。

- [ ] **Step 2: 結果を分類メモ**

| ファイル | 分類 | 理由 |
|---|---|---|
| `wrcomm.f90` | core | データ定義 |
| `wrinit.f90` | core | 初期値 |
| `wrparm.f90` | core | namelist parser |
| `wrprep.f90` | core | 計算前準備 |
| `wrview.f90` | core | パラメータ表示（stdout のみ） |
| `wrsub.f90` | core | サブルーチン |
| `wrsetup.f90` | core | ray セットアップ |
| `wrcalpwr.f90` | core | パワー計算（`USE libgrf` あるが計算用 utility のみ。要確認） |
| `wrfdrv.f90` | core | ODE 駆動 |
| `wroxb.f90` | core | OXB モード変換 |
| `wrexecr.f90` | core | ray 実行 |
| `wrexecb.f90` | core | beam 実行 |
| `wrexec.f90` | core | exec dispatch |
| `wrfile.f90` | core | save/load (ファイル I/O のみ) |
| `wrxregress.f90` | core | regression dump (L-0 で追加) |
| `wrgout.f90` | **graphics** | 描画 |
| `wrmenu.f90` | **menu** | 対話 UI、graphics と core を両方呼ぶ |

注: `wrcalpwr.f90` の `USE libgrf` は要確認。もし libgrf を実際に呼んでいなければ core に残す（USE のみで未使用変数なら graphics に移す必要なし）。

- [ ] **Step 3: `wrcalpwr.f90` の libgrf 呼出を確認**

Run:
```bash
grep -nE "CALL\s+(GRF|grf)|\bGSAF\b|\bGSPLOT\b" /home/k-yoshimi/program/task-private/wrx/wrcalpwr.f90 | head
```
Expected: 何もマッチしないなら core 維持で問題なし。マッチしたら graphics に分類するか、L-1 では USE 句を `ONLY:` で削るリファクタを別 PR に分ける（ユーザ制約「最小コード変更」を遵守）。

---

## Task 3: Makefile を 3 グループに分割

- [ ] **Step 1: Edit `wrx/Makefile`**

`SRCS = ...` ブロックを以下に置換:
```make
SRCS_CORE = wrcomm.f90 wrinit.f90 wrparm.f90 wrprep.f90 wrview.f90 \
            wrsub.f90 \
            wrsetup.f90 wrcalpwr.f90 wrfdrv.f90 wroxb.f90 \
            wrexecr.f90 wrexecb.f90 \
            wrexec.f90 \
            wrfile.f90 \
            wrxregress.f90

SRCS_GRAPHICS = wrgout.f90

SRCS_MENU = wrmenu.f90

SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)
```

`SRCS_CORE` の最後を `wrxregress.f90`、graphics は `wrgout.f90` のみ、menu は `wrmenu.f90` のみ。これで `OBJS = $(addprefix $(OBJDIR)/, $(SRCS:.f90=.o))` は変わらず動く。

- [ ] **Step 2: `wr` ターゲットが従来通り全 OBJS を含むことを確認**

`wr` のターゲット行はそのまま:
```make
wr : $(LIB_MTX) $(LIBS) $(OBJDIR)/wrmain.o
	$(FLINKER) $(OBJDIR)/wrmain.o $(LIBS) -o $@ $(FFLAGS) $(FLIBS) $(LIBX_MTX)
```
`$(LIBS)` には `libwr.a` が含まれ、`libwr.a` は `$(OBJS)` から作られる。`$(OBJS) = SRCS_CORE + SRCS_GRAPHICS + SRCS_MENU` のため変化なし。

---

## Task 4: clean ビルドで動作確認

- [ ] **Step 1: clean & rebuild**

Run:
```bash
cd /home/k-yoshimi/program/task-private/wrx
make veryclean
make 2>&1 | tail -10
ls -la wr
```
Expected: 全ファイル再ビルドされ `wrx/wr` 生成。エラーなし。

- [ ] **Step 2: L-0 baseline と数値一致確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private/test_run
rm -rf test_output/wrx_*
./run_tests.sh wrx_iter01 wrx_jt60 wrx_demo
```
Expected: 3 ケースとも PASS（L-0 baseline 完全一致）。

- [ ] **Step 3: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task-private
git add wrx/Makefile
git commit -m "refactor(wrx): split Makefile SRCS into core/graphics/menu groups"
```

---

## Verification Checklist

- [ ] `wrx/Makefile` に `SRCS_CORE`, `SRCS_GRAPHICS`, `SRCS_MENU` の 3 定義がある
- [ ] `SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` で従来 ALL を維持
- [ ] `wrx/wr` バイナリが従来通り build される
- [ ] WRX 3 baseline テストが全て PASS（数値完全一致）
- [ ] TR 既存 baseline が壊れていない

## Dependencies

- L-0 完了（`wrxregress.f90` と 3 baseline が存在）

## Fallback

- `wrcalpwr.f90` の `USE libgrf` が実際に graphics 呼出を含む場合: graphics 分類に移すか、`USE libgrf, ONLY: <unused-symbol>` を取り除く小修正を本フェーズに追加（ユーザ制約「最小変更」内）。判断は Task 2 Step 3 の grep 結果による。

## Out of Scope

- ファイル本体の `USE` 文整理（必要最小限のみ; 大きな refactor はしない）
- L-2 以降の C ABI、libwrxapi.so 構築
