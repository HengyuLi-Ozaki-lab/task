# FP ライブラリ化 Phase L-1: Graphics 分離 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `fp/Makefile` の `SRCS=` を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` の 3 つに論理分割し、後続 L-2..L-4 で graphics を含まない `libfpapi.so` を作れる準備を整える。既存の `fp` バイナリの数値出力は L-0 ベースラインと完全一致を保つ。

**Architecture:** 既存の `fp/Makefile` で 1 つになっている `SRCS=` を 3 グループに分ける。`fp` バイナリのリンク対象は従来通り全グループ（`$(SRCS_CORE) + $(SRCS_GRAPHICS) + $(SRCS_MENU)`）。L-2 以降で `libfpapi.so` が `$(SRCS_CORE) + $(SRCS_API)` だけを使うことを可能にする土台。コードへの変更は **Makefile のみ**、Fortran ソースは触らない。

**Tech Stack:** Make（`fp/Makefile`）、回帰テスト（L-0 で確立した `./run_tests.sh fp_*`）。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` 7.1 節（"既存 tr2 ターゲット」と graphics 分離方針）、A.4 節（質問 4 の回答）。

---

## Module Survey: fp/ における graphics サブシステム

`fp/Makefile` を読んだ上で、各ファイルを 3 カテゴリに分類した:

| カテゴリ | ファイル | 行数目安 | 役割 |
|---|---|---|---|
| **GRAPHICS** | `fpgout.f90` | 2029 | グラフ出力ルート (`fp_gout`) |
|              | `fpgsub.f90` | 438 | グラフ補助 |
|              | `fpcont.f90` | - | コンタ図 |
|              | `fpfout.f90` | - | ファイル出力（plot 寄り） |
| **MENU**     | `fpmenu.f90` | 136 | 対話メニュー (`fp_menu`)、`USE fpgout` するため graphics に強く依存 |
| **MAIN_PROG**| `fpmain.f90` | 60 | `PROGRAM fp` のエントリ |
| **CORE**     | 上記以外の 41 ファイル | 約 18,000 | 計算本体（`fpcomm, fpinit, fpparm, fpprep, fpcoef, fpcalc*, fpsave, fpexec, fploop, fplib, fpmpi, fpdisrupt, fpregress, ...`）|

**graphics と menu を一緒にするか、別グループにするか**: TR の `tr_library-design.md` 7.1 節に従い 3 分割（CORE / GRAPHICS / MENU）。`fpmenu.f90` は graphics を `USE` するが、L-4 ライブラリ化時には menu も除外して `fp_api.f90` を main 相当に置くため、独立グループのほうが扱いやすい。

**L-1 はあくまで Makefile 上の論理分離だけ**で、Fortran 側で `USE fpgout` を `#ifdef` 等で外したりはしない。`fp` バイナリのビルド成果物は不変。

---

## File Structure

| ファイル | 種別 | 責務 |
|---|---|---|
| `fp/Makefile` | 修正 | `SRCS=` を `SRCS_CORE` / `SRCS_GRAPHICS` / `SRCS_MENU` に 3 分割し、`SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` で再合成 |

それ以外のファイル変更なし。

---

## Task 1: 作業ブランチ作成と L-0 完了確認

**Files:** なし

- [ ] **Step 1: L-0 が develop にマージ済みか確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | head -10
```
Expected: L-0 のマージコミットが見える、または L-0 PR がマージ予定。

- [ ] **Step 2: L-1 ブランチを develop から切る**

Run:
```bash
git checkout -b feature/fp-library-L1-graphics-split origin/develop
```

- [ ] **Step 3: L-0 の fp 回帰 3 ケースが green であることを確認（出発点を固定）**

Run:
```bash
cd /home/k-yoshimi/program/task/fp && make 2>&1 | tail -3
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1 2>&1 | tail -10
```
Expected: 3 ケース全 PASS（L-0 の baselines と一致）。fail なら L-1 開始前に L-0 の修正に戻る。

---

## Task 2: 失敗するテスト（差分検証）を準備

**Files:** なし（手元で fp_regress.dat を保存）

L-1 の本変更は Makefile のみで Fortran は触らないため、ビルド成果物が bit-exact になることを期待する。これを「失敗するテスト」として、変更前の dump をスナップショットしておき、変更後と diff する。

- [ ] **Step 1: 変更前の fp_regress.dat 3 件をスナップショット**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
mkdir -p /tmp/fp_l1_snapshot
for case in fp_iter01 fp_jt60 fp_dt1; do
  cp "test_output/$case/fp_regress.dat" "/tmp/fp_l1_snapshot/${case}.dat"
done
ls -la /tmp/fp_l1_snapshot/
```
Expected: 3 ファイルが保存される。

- [ ] **Step 2: 変更後に diff = 0 であることを期待する確認スクリプト用意（メモのみ、実装はしない）**

確認手順:
```bash
for case in fp_iter01 fp_jt60 fp_dt1; do
  diff "/tmp/fp_l1_snapshot/${case}.dat" "test_output/$case/fp_regress.dat"
done
```
Expected at end: 全部 exit 0。

---

## Task 3: `fp/Makefile` の SRCS 分割

**Files:**
- Modify: `fp/Makefile`

- [ ] **Step 1: 現行 `SRCS=` ブロックを把握**

Run:
```bash
sed -n '30,45p' /home/k-yoshimi/program/task/fp/Makefile
```
Expected: 31-41 行目に
```
SRCS =  fpcomm.f90 fpinit.f90 fpparm.f90 \
	fpmpi.f90 fpbroadcast.f90 fplib.f90 \
	fpexec.f90 fpreadeg.f90 fpsave.f90 fpwrite.f90 \
	fpcaltp.f90 fpcalte.f90 fpcaldeff.f90 fpcalchieff.f90 \
	fpwmin.f90 fpwrin.f90 fpcalwm.f90 fpcalwr.f90 fpcalw.f90 \
	fpcalcn.f90 fpcalcnr.f90 fpcalc.f90 fpnfrr.f90 fpnflg.f90  \
	cdbmfp.f90 \
	fpcalr.f90 fpreadsv.f90 fpoutdata.f90 fpcoef.f90 fpcale.f90 \
	fpbounce.f90 fpcalj.f90 fpdisrupt.f90 fpprep.f90 fploop.f90 \
	fpcont.f90 fpfout.f90 fpgsub.f90 fpgout.f90 fpfile.f90 \
	fpregress.f90 \
	fpmenu.f90
```
が見つかる（L-0 で `fpregress.f90` を加えた状態）。

- [ ] **Step 2: 3 グループに分割した形に書き換え**

`fp/Makefile` の現行 `SRCS = ...` 全体を以下に置換:

```makefile
# --- core (Fokker-Planck physics + I/O, no graphics, no menu) ---
SRCS_CORE = fpcomm.f90 fpinit.f90 fpparm.f90 \
	fpmpi.f90 fpbroadcast.f90 fplib.f90 \
	fpexec.f90 fpreadeg.f90 fpsave.f90 fpwrite.f90 \
	fpcaltp.f90 fpcalte.f90 fpcaldeff.f90 fpcalchieff.f90 \
	fpwmin.f90 fpwrin.f90 fpcalwm.f90 fpcalwr.f90 fpcalw.f90 \
	fpcalcn.f90 fpcalcnr.f90 fpcalc.f90 fpnfrr.f90 fpnflg.f90 \
	cdbmfp.f90 \
	fpcalr.f90 fpreadsv.f90 fpoutdata.f90 fpcoef.f90 fpcale.f90 \
	fpbounce.f90 fpcalj.f90 fpdisrupt.f90 fpprep.f90 fploop.f90 \
	fpfile.f90 fpregress.f90

# --- graphics (plotting, contour, plot-oriented file output) ---
SRCS_GRAPHICS = fpcont.f90 fpfout.f90 fpgsub.f90 fpgout.f90

# --- interactive menu driver (depends on graphics) ---
SRCS_MENU = fpmenu.f90

# --- final SRCS for the existing `fp` binary (unchanged behaviour) ---
SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)
```

注意点:
- `fpregress.f90` は CORE に入れる（環境変数ガード dump で graphics に依存しない）。
- `fpmain.f90` は元から `SRCS=` に含まれていない（リンク時に `$(OBJDIR)/fpmain.o` を別途指定）ので変更不要。
- `cdbm.f90` は `$(SRCS:.f90=.o)` に入っていない可能性が高い（OBJS 計算時に評価される）。L-1 では CORE/GRAPHICS の境界判定のみ行う。`cdbm.f90` の扱いは L-2 で再評価。
- 並び順は元の `SRCS=` の登場順を保つ（`fpcomm` 最先頭、依存解決順を維持）。

- [ ] **Step 3: ビルド**

Run:
```bash
cd /home/k-yoshimi/program/task/fp
make veryclean
make 2>&1 | tail -10
ls -la fp
```
Expected: エラーなしで `fp` バイナリが再生成。

- [ ] **Step 4: 全 fp 回帰テストを通す**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh fp_iter01 fp_jt60 fp_dt1
```
Expected: 3 ケース全 PASS。

- [ ] **Step 5: dump bit-exact 検証**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
for case in fp_iter01 fp_jt60 fp_dt1; do
  echo "=== $case ==="
  diff "/tmp/fp_l1_snapshot/${case}.dat" "test_output/$case/fp_regress.dat"
done
echo "all diffs exit 0?"
```
Expected: 全 diff 出力空（completely bit-exact）。

差異が 1 行でも出る場合は **撤退条件**: Makefile 順序変更により compile order が変わって浮動小数点演算の順番が変わった可能性。Step 2 のグループ分けの並び順を、元の `SRCS=` と完全一致させ直す（`SRCS_CORE = ...; SRCS_GRAPHICS = fpcont.f90 fpfout.f90 fpgsub.f90 fpgout.f90` の挿入位置を `fpfile.f90` の前に戻す等）。

- [ ] **Step 6: TR 既存テストが回帰しないこと**

Run:
```bash
cd /home/k-yoshimi/program/task/test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2
```
Expected: 全 PASS。

- [ ] **Step 7: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add fp/Makefile
git commit -m "build(fp): split SRCS into CORE/GRAPHICS/MENU groups (no behavior change)"
```

---

## Task 4: README/changelog（任意、5 分以内）

**Files:**
- Modify: `fp/changelog`（既存ファイル）

- [ ] **Step 1: 1 行追記**

`fp/changelog` の末尾に追加:

```
2026-04-XX  Phase L-1: Makefile SRCS split into CORE / GRAPHICS / MENU
            (preparation for libfpapi.so; no behavior change).
```

- [ ] **Step 2: コミット**

Run:
```bash
cd /home/k-yoshimi/program/task
git add fp/changelog
git commit -m "docs(fp): note L-1 SRCS split in changelog"
```

---

## 受け入れ基準

- [ ] `fp/Makefile` の `SRCS_CORE`, `SRCS_GRAPHICS`, `SRCS_MENU` 変数が存在し、`SRCS = $(SRCS_CORE) $(SRCS_GRAPHICS) $(SRCS_MENU)` で結合されている。
- [ ] `make veryclean && make` で `fp` バイナリが再生成される。
- [ ] `fp_iter01, fp_jt60, fp_dt1` の dump (`fp_regress.dat`) が L-0 ベースラインと **bit-exact** 一致（diff 出力空）。
- [ ] `tr_iter01, tr_m0904, tr_tst2` も全 PASS（巻き込み事故なし）。

## 撤退条件 / フォールバック

| 状況 | 対応 |
|---|---|
| Step 5 で diff が出る（順序変更で数値が変わる） | 並び順を元に戻し、3 グループに「論理ラベルだけ」付ける形に変える |
| `fpfile.f90` を CORE/GRAPHICS どちらに入れるべきか判断つかない | デフォルト CORE（既存の `OBJDIR/fpfile.o` 依存に graphics モジュールへの USE は無いため）。L-2 でビルド試行時に graphics 依存が見つかれば GRAPHICS に移す |
| L-1 単独で 1 週超 | Makefile 分割のみで commit、後続 README は別 PR で |

## 依存

- 上流: L-0 マージ済み（fp 回帰 3 ケースが develop で green）
- 後続: L-2（C ABI foundation）は本 PR マージ後に着手
