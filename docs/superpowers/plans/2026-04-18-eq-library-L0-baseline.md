# EQ ライブラリ化 Phase L-0: Baseline 確立（As-Built）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** EQ モジュールの数値回帰ベースラインを PR #54 で確立済み。本ドキュメントは **as-built 振り返り** として、既に develop（merge 前）または L-1 ブランチ上に存在する L-0 成果物 (`eq/eqregress.f`, `test_run/baselines/eq_iter01/`, `test_run/baselines/eq_tst2/`, `test_run/scripts/extract_eq_metrics.py`, `compare_metrics.py` の EQ 対応) の構造を文書化し、L-2 以降のフェーズが前提とする「数値 bit-safe ガードレール」を明示する。新たなコード変更は行わない（retrospective documentation）。

**Architecture:** TR L-0 (`trregress.f90`) と同設計を F77 fixed-form に移植。`eq/eqregress.f` は `eqcomm.inc` を include して COMMON 経由でスカラー + プロファイル配列を拾い、`eq_regress.dat` を単一テキストファイルとして書き出す。`test_run/baselines/eq_{iter01,tst2}/metrics.json` はチェックポイント（`PSI0`, `PSIPA`, `RAXIS`, `ZAXIS`, `Q0`, `QA`, `BETAT`, `BETAP`, `VPOL`, `RIP`, 配列ハッシュ）をホストし、`compare_metrics.py --dim eq` で tol `1e-10` 比較される。

**Tech Stack:** Fortran 77 fixed-form (`eqregress.f`), Python 3 stdlib (`extract_eq_metrics.py`, `compare_metrics.py`), Bash (`run_tests.sh`), gfortran 既存ビルド、既存 `eq/eq` バイナリ。

**出典:**
- PR #54 (as-built L-0 implementation — eq dump module + 2 baselines + extractor + `--dim eq`)
- `docs/superpowers/plans/2026-04-18-tr-library-L0-baseline.md` (TR L-0 の対応版、同設計の写し)
- `docs/superpowers/specs/2026-04-17-tr-library-design.md` §9 (L-0 行) の設計原則
- `eq/eqinit.f` の `/EQ/` namelist（ベースライン metrics が拾う変数集合の正典）

---

## As-Built File Structure

PR #54 で追加された成果物:

| ファイル | 種別 | 役割 |
|---|---|---|
| `eq/eqregress.f` | F77 fixed-form | `eq_regress.dat` ダンプ用 subroutine。`eqcomm.inc` 経由で COMMON を読み、`EQCALC` 完了後に呼ばれる |
| `eq/Makefile` | 修正 | `SRCS` に `eqregress.f` を追加 |
| `eq/eqmain.f`（または `equnit.f`） | 修正 | `CALL EQREGRESS_DUMP` を `EQCALC` / `EQLOAD` の直後に挿入（`EQ_REGRESS=1` 環境変数時のみ） |
| `test_run/baselines/eq_iter01/metrics.json` | 新規 | ITER ベース入力 `eq_iter01.in` のリファレンス |
| `test_run/baselines/eq_iter01/eq_iter01.in` | 新規 | namelist fixture |
| `test_run/baselines/eq_tst2/metrics.json` | 新規 | 2 ケース目の短時間 fixture |
| `test_run/baselines/eq_tst2/eq_tst2.in` | 新規 | namelist fixture |
| `test_run/scripts/extract_eq_metrics.py` | 新規 | `eq_regress.dat` → `metrics.json` 変換器 |
| `test_run/scripts/compare_metrics.py` | 修正 | `--dim eq` 対応（プロファイル配列サイズと tol はモジュール依存で `1e-10` を採用） |
| `test_run/scripts/run_tests.sh` | 修正（予定） | `eq_*` ケース追加 |

**方針（as-built から抽出）:**
- `eqregress.f` は **既存コード非侵襲**。`EQ_REGRESS=1` の場合のみ `eq_regress.dat` を `$(pwd)` に作成し、未セットなら no-op。
- `eq_regress.dat` のスキーマは平文 key=value + array blocks（TR と同じ）。バイナリ形式は採用しない（diff 容易性優先）。
- 2 ケース (`eq_iter01`, `eq_tst2`) の採用理由: (a) `iter01` は現実的トカマク (MODELG=2, MDLEQF=0), (b) `tst2` は `eqmain.f` の既存テストケース系譜（短時間 CI 向け）。3 ケース目 (`eq_eqdsk`) は L-0 段階では見送り（EQDSK ファイル依存のため fixture サイズが肥大化）。
- TR と同様に **graphics を呼ばない非対話パス** を通ること。namelist 内で `NPRINT=0`、メニュー入力は `MODE=1` (file-based) を使う。

---

## As-Built ダンプ対象（`eq_regress.dat` の schema）

PR #54 時点で `eqregress.f` が書き出す項目（`eqcom1.inc` の COMMON を参照）:

### グローバル収束スカラー（EQGLB1..EQGLB6）
- `RAXIS`, `ZAXIS` (磁気軸座標)
- `PSI0`, `PSIPA`, `PSITA`, `REDGE` (フラックス normalization)
- `PVOL`, `RAAVE`, `BETAT`, `BETAP`, `QAXIS`, `QSURF`
- `TJ`, `PSIITB`, `IDCALV` (ITB / 収束フラグ)
- `RRC`, `RIPX`, `RBRA` (補助)
- `RXPNT1, ZXPNT1, PSIXPNT1, RXPNT2, ZXPNT2, PSIXPNT2, NXPOINT` (X 点)

### 入力パラメータ（同一シードで reproduce 確認）
- `RR, RA, RB, RKAP, RDLT, BB, Q0, QA, RIP` (geometry / device)
- `PP0, PP1, PP2, PROFP0, PROFP1, PROFP2` (pressure profile)
- `PJ0, PJ1, PJ2, PROFJ0, PROFJ1, PROFJ2` (current density profile)
- `FF0, FF1, FF2, PROFF0, PROFF1, PROFF2` (poloidal F profile)
- `NRMAX, NTHMAX, NSUMAX, NSGMAX, NTGMAX, NUGMAX` (mesh)
- `MDLEQF, MDLEQC, MDLEQA, MDLEQX, MDLEQV, MODELG, MODELQ` (model switches)

### プロファイル配列（縮約後ハッシュ + 端点値）
- `PSIPS(NPSMAX)`, `PPPS(NPSMAX)`, `TTPS(NPSMAX)`, `QQPS(NPSMAX)` (flux-surface quantities)
- `PSIPV(NRVMAX)`, `QPV(NRVMAX)`, `TTV(NRVMAX)`, `VPV(NRVMAX)` (averaged quantities)
- `RSU(NSUMAX+1), ZSU(NSUMAX+1)` (boundary surface)
- `PSIRZ(NRGMAX,NZGMAX)` は SHA-256 (raw bytes) のみ（フルダンプは 4 MB 級で回帰 diff に不向き）

**tolerance:** 全 scalar / 1D array は絶対誤差 `1e-10`、2D array はハッシュ完全一致。

---

## Task 1 (as-built): ダンプルーチン `eqregress.f`（retrospective audit）

**Files:** Audit only — already present in PR #54.

- [ ] **Step 1: 既存 `eq/eqregress.f` のエントリポイントを確認**

Run:
```bash
cd /home/k-yoshimi/program/task-private
grep -n "SUBROUTINE EQREGRESS_DUMP\|subroutine eqregress_dump" eq/eqregress.f
```
Expected: `SUBROUTINE EQREGRESS_DUMP(IERR)` が 1 つ。INCLUDE 文で `../eq/eqcomm.inc` を取り込んでいる。

- [ ] **Step 2: `EQ_REGRESS` 環境変数ガードを確認**

Run:
```bash
grep -n "EQ_REGRESS\|getenv" eq/eqregress.f
```
Expected: `CALL GETENV('EQ_REGRESS', kval)` の後 `IF (LEN_TRIM(kval)==0) RETURN` ガード。

- [ ] **Step 3: 呼び出し箇所の確認**

Run:
```bash
grep -n "EQREGRESS_DUMP\|eqregress_dump" eq/*.f eq/*.f90
```
Expected: `eq/eqmain.f` または `eq/equnit.f::eq_calc` の末尾で `CALL EQREGRESS_DUMP(IERR)`。EQ の主計算 (`EQCALC`, `EQCALQ`, 必要なら `EQLOAD` パス) 完了直後。

---

## Task 2 (as-built): Baseline fixtures（retrospective audit）

**Files:** Audit only — already present in PR #54.

- [ ] **Step 1: 2 ケースの namelist 入力**

Run:
```bash
cat test_run/baselines/eq_iter01/eq_iter01.in
cat test_run/baselines/eq_tst2/eq_tst2.in
```
Expected: `&EQ ... &END` 形式。`NPRINT=0`、`MODELG=2`、`MDLEQF=0` 程度の設定。

- [ ] **Step 2: `metrics.json` フォーマット**

Run:
```bash
python3 -c "import json; j=json.load(open('test_run/baselines/eq_iter01/metrics.json')); print(sorted(j.keys())[:20])"
```
Expected: `RR, RA, BB, RIP, RAXIS, ZAXIS, PSI0, PSIPA, Q0, QAXIS, QSURF, BETAT, BETAP, NRMAX, NTHMAX, PSIPS__hash, PSIRZ__hash, ...` などがキーに並ぶ。

---

## Task 3 (as-built): Python tool chain（retrospective audit）

**Files:** Audit only — already present in PR #54.

- [ ] **Step 1: `extract_eq_metrics.py` の入出力**

Run:
```bash
head -40 test_run/scripts/extract_eq_metrics.py
```
Expected: `argparse` で `input` (.dat) と `--output` (.json) を取り、`eq_regress.dat` の key=value + `BEGIN_ARRAY <NAME> <N>` セクションをパースする。

- [ ] **Step 2: `compare_metrics.py` の `--dim eq` 分岐**

Run:
```bash
grep -n "dim.*eq\|\"eq\"\|'eq'" test_run/scripts/compare_metrics.py
```
Expected: `DIM_TOLERANCES = { "tr": 1e-10, "eq": 1e-10, "ti": 1e-10, ... }` などの dict にエントリ追加、および EQ 専用無視キー（空想または `PSIRZ__timestamp` のような非決定要素）の除外ロジック。

---

## Task 4 (as-built): `run_tests.sh` との統合

**Files:** Audit only — already present in PR #54.

- [ ] **Step 1: eq ケース登録**

Run:
```bash
grep -n "eq_iter01\|eq_tst2\|eq_" test_run/scripts/run_tests.sh
```
Expected: `case "$TEST_CASE" in eq_*) MODULE=eq; BIN=eq/eq; DIM=eq ;; esac` などの分岐で eq ケースを dispatch。

- [ ] **Step 2: 実行コマンド確認**

run_tests.sh は以下を行う:
```bash
cd $(baseline_dir)
EQ_REGRESS=1 ../../../eq/eq < $(test).in > run.log 2>&1
python3 ../../scripts/extract_eq_metrics.py eq_regress.dat -o /tmp/$(test).metrics.json
python3 ../../scripts/compare_metrics.py --dim eq /tmp/$(test).metrics.json $(baseline)/metrics.json
```
Expected: 2 ケース全 PASS（tol `1e-10`）。

---

## Task 5: Retrospective report commit（ドキュメントのみ）

**Files:**
- このプラン自体（`docs/superpowers/plans/2026-04-18-eq-library-L0-baseline.md`）

- [ ] **Step 1: プランをコミット**

本ファイルは **コードなしのドキュメント PR** として develop に入れる。PR 本文要旨:
> As-built record of eq L-0 baseline (PR #54). No source changes; locks in the regression ground truth that L-2 (C ABI), L-3 (registry), L-4 (shared lib), L-5 (Python), L-6 (4-layer tests), L-7 (docs) all depend on.

---

## 受け入れ基準（as-built）

- [ ] `eq/eqregress.f` が存在し、`EQ_REGRESS=1` のときだけ `eq_regress.dat` を出力
- [ ] `test_run/baselines/eq_iter01/metrics.json`, `test_run/baselines/eq_tst2/metrics.json` の 2 セット
- [ ] `test_run/scripts/extract_eq_metrics.py` が `eq_regress.dat` → `metrics.json` を変換
- [ ] `test_run/scripts/compare_metrics.py --dim eq` で tol `1e-10` 比較
- [ ] `./run_tests.sh eq_iter01 eq_tst2` → 2/2 PASS

## 撤退条件 / フォールバック

| 状況 | 判断 |
|---|---|
| `eq_tst2` が数値的に不安定（別入力案を要検討） | fixture を `eq_tst2` → `eq_short` に rename、`NTVMAX` を下げた別 case に差し替え。本 L-0 retrospective ではスコープ外 |
| `PSIRZ__hash` が環境依存で揺れる | `-fno-fast-math`, `-mfpmath=sse` を `FFLAGS` に追加し PR #54 側で既に固定済み。要確認 |
| PR #54 がまだ develop に未 merge | 本 retrospective プランは PR #54 と同時／後にマージ。L-2 以降のプランは PR #54 依存としてマーク |

## 依存

- なし（本 L-0 はベースライン確立フェーズ）
- 下流: L-1 (Makefile split、既に別 PR でプラン済 `eq-library-L1-makefile-split.md`), L-2, L-3, L-4, L-5, L-6, L-7 の全フェーズが本 L-0 を必須前提にする

---

## 注釈: TR L-0 との設計差異

| 項目 | TR | EQ |
|---|---|---|
| ダンプ実装ファイル | `tr/trregress.f90` (free-form F90, `USE trcomm`) | `eq/eqregress.f` (fixed-form F77, `INCLUDE eqcomm.inc`) |
| 変数取得 | F90 `USE` 経由 | F77 COMMON 経由（EQ は module 化未完了のため） |
| ベースラインケース数 | 3 (`tr_iter01`, `tr_m0904`, `tr_tst2`) | 2 (`eq_iter01`, `eq_tst2`) — EQDSK ケースは L-1 以降に延期 |
| tolerance | `1e-10` | `1e-10` (同一) |
| ダンプ呼び出し位置 | `tr_loop` 完了直後 | `EQCALC` または `EQLOAD` 完了直後 |
| 2D 大配列 | なし (TR は 1D radial profiles のみ) | `PSIRZ(NRGM,NZGM)` は SHA-256 ハッシュのみ（フルダンプ回避） |

この差異は L-2 以降で「EQ 固有の F77 COMMON access」をどう C ABI に橋渡しするかという課題に直結する（L-3 plan 参照）。
