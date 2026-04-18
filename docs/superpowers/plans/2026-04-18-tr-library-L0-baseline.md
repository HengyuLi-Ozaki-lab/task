# Phase L-0: Baseline Confirmation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Phase 1/2 (TRCOMM submodule 化) 完了直後に、既存 `tr2` バイナリの数値挙動が Phase 0 で確立した回帰ベースラインと完全一致することを確認し、L-1 以降のライブラリ化作業に入れる前提を確立する。

**Architecture:** 本サブフェーズはコード変更を一切伴わない確認フェーズ。Phase 0 で導入済みの `test_run/run_tests.sh` + `tr_regress.dat` dump 機構をそのまま使い、3 ケース（`tr_iter01`, `tr_m0904`, `tr_tst2`）で許容誤差 `1e-10` を守れているかをチェックする。差分があれば本フェーズで修正してから L-1 に進む。

**Tech Stack:** Bash (`run_tests.sh`), Python 3 stdlib (`compare_metrics.py`), gfortran 既存ビルド, 既存 `tr/tr2` バイナリ。

**出典設計書:** `docs/superpowers/specs/2026-04-17-tr-library-design.md` §9 (L-0 行) と §1.4 制約。

---

## File Structure

このサブフェーズで作成・変更するファイル:

| ファイル | 種別 | 責務 |
|---|---|---|
| `docs/superpowers/notes/2026-04-18-phase-l0-baseline-report.md` | 新規 | L-0 確認結果の記録（PASS/FAIL、再現コマンド、各ケースの実時間） |

**方針:**
- TR 本体や `test_run/` 配下のコード/設定は **変更しない**。L-0 はあくまで確認フェーズ。
- もし `compare_metrics.py` で FAIL する場合は、Phase 1/2 で混入した数値変動とみなし、本サブフェーズで原因切り分け→修正→再ベースライン化までを行う（その場合のみ `test_run/baselines/` を更新コミットする）。

---

## Task 1: 作業用ブランチ作成と前提確認

**Files:**
- なし（環境準備のみ）

- [ ] **Step 1: develop が Phase 1/2 完了済みか確認**

Run:
```bash
cd /home/k-yoshimi/program/task
git fetch origin develop
git log --oneline origin/develop | head -20
```
Expected: Phase 1 (USE-only restructure) と Phase 2 (TRCOMM submodule 分割) の merge commit が含まれる。含まれない場合は Phase L-0 はまだ実施できない（前提未達）→撤退して Phase 2 完了を待つ。

- [ ] **Step 2: ブランチ作成**

Run:
```bash
git checkout -b feature/tr-library-phase-l0 origin/develop
```
Expected: ブランチ切替成功、`git status` で clean。

- [ ] **Step 3: コンパイラフラグの固定確認**

Run:
```bash
grep -nE "^OFLAGS|^DFLAGS" make.header | head -5
grep -nE "^FFLAGS" tr/Makefile | head -3
```
Expected: `OFLAGS = -g -O3 -m64 -std=legacy` 相当が 1 行だけ有効、`tr/Makefile` で `FFLAGS = $(OFLAGS)` を採用（Phase 0 と同じ条件）。複数の `OFLAGS` がアンコメントされていたら 1 つに固定する。

---

## Task 2: フルビルドと既存テスト一式の実行

**Files:**
- なし（既存 Makefile / `test_run/` を使うのみ）

- [ ] **Step 1: clean ビルド**

Run:
```bash
cd /home/k-yoshimi/program/task
(cd eq && make clean && make 2>&1 | tail -5)
(cd tr && make clean && make 2>&1 | tail -5)
```
Expected: `eq/eq` と `tr/tr2` が再生成される。エラーなし。

- [ ] **Step 2: Phase 0 で登録された TR 回帰テスト 3 ケースを走らせる**

Run:
```bash
cd test_run
./run_tests.sh tr_iter01 tr_m0904 tr_tst2 2>&1 | tee /tmp/phase_l0_run.log
```
Expected: 3 ケースすべて `PASS`。最後に `Summary: 3/3 passed` 等の表示。

- [ ] **Step 3: もし FAIL があれば原因切り分け**

FAIL 時は以下を取得:
```bash
ls -la test_output/tr_iter01/tr_regress.dat test_output/tr_m0904/tr_regress.dat test_output/tr_tst2/tr_regress.dat
diff <(python3 scripts/extract_tr_metrics.py test_output/tr_iter01/tr_regress.dat) baselines/tr_iter01/metrics.json | head -50
```

差分の方向で次のいずれかに進む:
- **小さな数値ノイズ** (≤1e-8): Phase 1/2 で混入した最適化変動。原因 commit を `git bisect` で特定し、PR を分けて修正案を作る。L-0 はそのまま継続不能。
- **大きな差** (>1e-6): Phase 1/2 が物理的に変えてしまっている可能性。L-0 撤退、Phase 2 にバグ報告。

- [ ] **Step 4: 全 PASS だった場合のみ次タスクへ**

Run:
```bash
echo "PASS gate cleared" > /tmp/phase_l0_gate.txt
```

---

## Task 3: 結果レポートをコミット

**Files:**
- Create: `docs/superpowers/notes/2026-04-18-phase-l0-baseline-report.md`

- [ ] **Step 1: ノート用ディレクトリ作成**

Run:
```bash
mkdir -p docs/superpowers/notes
```

- [ ] **Step 2: レポート本文を書き出す**

作成: `docs/superpowers/notes/2026-04-18-phase-l0-baseline-report.md`

```markdown
# Phase L-0 baseline confirmation report

- Date: <YYYY-MM-DD>
- Branch: feature/tr-library-phase-l0
- develop HEAD: <git rev-parse origin/develop>

## Build
- eq: OK / tr: OK
- Compiler: $(gfortran --version | head -1)
- FFLAGS: $(grep -E "^FFLAGS" tr/Makefile)

## Regression
| Case | Result | Wall (s) | Notes |
|---|---|---|---|
| tr_iter01 | PASS | <t> | tol 1e-10 |
| tr_m0904  | PASS | <t> | tol 1e-10 |
| tr_tst2   | PASS | <t> | tol 1e-10 |

## Conclusion
Phase 1/2 後の数値結果は Phase 0 ベースラインと一致。L-1 (Graphics 分離) に着手可能。
```

- [ ] **Step 3: コミット**

Run:
```bash
git add docs/superpowers/notes/2026-04-18-phase-l0-baseline-report.md
git commit -m "docs(tr): record Phase L-0 baseline confirmation"
```

- [ ] **Step 4: PR を作成（develop ターゲット、merge commit）**

Run:
```bash
gh pr create --base develop --title "docs(tr): Phase L-0 baseline confirmation" \
  --body "Phase 1/2 後の回帰テスト全 PASS を確認したレポート（コード変更なし）。設計書 §9 L-0。"
```

---

## 撤退条件 / フォールバック

| 状況 | 判断 |
|---|---|
| Phase 1/2 が未完了 | L-0 を保留、Phase 2 完了を待つ |
| 1 ケースのみ FAIL | 該当ケースの差分を切り分け、Phase 2 側にバグ報告して L-0 ブロック |
| 全ケース小さなノイズ (≤1e-8) | Phase 0 設計書の許容誤差緩和議論を再開（`1e-8` まで許容にする提案 PR を別途出す） |

## 受け入れ基準

- [ ] `tr_iter01`, `tr_m0904`, `tr_tst2` 3 ケース全 PASS（tol `1e-10`）
- [ ] レポートが `docs/superpowers/notes/` にコミットされている
- [ ] PR が develop に merge 済み、または review 中

## 依存

- Phase 0 完了（`trregress.f90`、`run_tests.sh` 拡張、3 ケース baseline）
- Phase 1 完了（`USE only` 化）
- Phase 2 完了（TRCOMM submodule 分割）
