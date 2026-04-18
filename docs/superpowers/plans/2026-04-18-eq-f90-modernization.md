# eq モジュール F77 → F90 現代化 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `eq/*.f` 固定形式 F77 ソース (~23 ファイル) を自由形式 F90 に段階的に現代化し、COMMON ブロック群を F90 モジュールに置き換える。最終目標は Phase L 系 (library-ization) を安定して進められる土台作り。現代化前後で **数値出力が完全に一致** (L-0 ベースライン参照) することを必須とする。

**Architecture:** ボトムアップ 4 フェーズで進める。先に孤立した低リスクファイルを自由形式化して手順を確立し、次に `eqcom*.inc` を F90 モジュール化、続いて MED/HIGH 段の COMMON 依存の強いファイルを置換する。各フェーズで回帰テスト 全 PASS を checkpoint とする。

**Tech Stack:** Fortran 90 (自由形式, MODULE, INTENT, ALLOCATE), gfortran `-ffree-form` / `-std=f2008`, 既存の `make.header` / `FCFREE`, L-0 で整備した `./run_tests.sh eq_*` 回帰スイート、1e-13 RMS tolerance。

**出典:** `eq/Makefile` (31 ソース構成), `eq/eqcom{0..5}.inc` (COMMON 宣言), 既存 F90 参考実装 `equcom.f90`, `equread.f90`, `eqlib.f90`。tr モジュールの modernization 系譜 (`docs/superpowers/plans/2026-04-17-tr-phase2-*.md` など) も方針参考。

---

## ファイル分類 (修正難度)

| 段階 | ファイル | COMMON 数 | 行数目安 | 備考 |
|---|---|---|---|---|
| LOW | `newton.f` | 0 | <200 | Newton 反復ユーティリティ |
| LOW | `invematrix.f` | 0 | <200 | 行列反転 |
| LOW | `eqgsub.f` | 0-1 | ~300 | グラフ補助 (L-1 で既に graphics 側) |
| LOW | `eqgetp.f` | 1 (読み取り) | ~250 | パラメータ取得ヘルパ |
| MED | `eqinit.f` | 2 | ~400 | 初期化 |
| MED | `eqmenu.f` | 2 | ~500 | 対話メニュー (graphics) |
| MED | `eqcalv.f` | 2 | ~400 | 体積積分 |
| MED | `eqfunc.f` | 2-3 | ~450 | 補助関数群 |
| MED | `eqintf.f` | 2 | ~350 | インタフェース |
| MED | `eqgout.f` | 2 | ~500 | graphics メイン (L-1 で分離済み) |
| MED | `eqrppl.f` | 2 | ~300 | リップル計算 |
| MED | `equnit.f` | 1 | ~200 | 単位変換 |
| MED | `equintf.f` | 2 | ~350 | equread 用 interface |
| HIGH | `eqsub.f` | 4-5 | ~800 | 中核サブ群 |
| HIGH | `eqcalq.f` | 3-4 | ~700 | Q 計算 (スプライン依存) |
| HIGH | `eqsplf.f` | 3 | ~600 | スプライン生成 |
| HIGH | `eq-eqdsk.f` | 3 | ~600 | EQDSK 入出力 |
| HIGH | `eq-qst.f` | 3 | ~550 | QST 入出力 |
| HIGH | `eqfile.f` | 3 | ~700 | ファイル I/O ディスパッチャ |
| HIGH | `eqbpsd.f` | 3 | ~500 | BPSD インタフェース |
| HIGH | `eqcalc.f` | 4-5 | ~900 | 主計算ドライバ |

## COMMON ブロック構造 (`eqcom{0..5}.inc`)

| include | 内容 | 主な変数 |
|---|---|---|
| `eqcom0.inc` | グリッド定数 | `NRGM=513`, `NZGM=513`, `NRM=1001`, `NTHM=2049` |
| `eqcom1.inc` | グローバル状態 | `RG`, `ZG`, `PSIRZ`, `PSIPS`, `PPPS`, `TTPS`, `RAXIS`, `ZAXIS` |
| `eqcom2.inc` | メッシュ / 右辺 | `PSI`, `DELPSI`, `PP`, `TT`, `HJT`, `RHO`, `PSIST`, `HJTST` |
| `eqcom3.inc` | 1D スプライン状態 | `RPS`, `ZPS`, `DRPSI`, `DZPSI`, Boozer 座標, ripple |
| `eqcom4.inc` | TR ソルバ状態 | (外部参照のみ; eq/ 内では軽い) |
| `eqcom5.inc` | 行列ソルバ | (`eqcalx.f` 専用; 本体 SRCS には含まれない) |

合計: ~70 COMMON ブロック / 400+ 変数。

---

## Phase F-1: COMMON → MODULE 変換

### Task F-1-1: `eqcom0_mod` の作成
- [ ] `eq/eqcom0_mod.f90` を新規作成 (`PARAMETER :: NRGM=513`, 等)
- [ ] `eqcom0.inc` 参照ファイルの中から 1 つ (例: `newton.f`) を F90 化して `USE eqcom0_mod` で置換し、**L-0 回帰 PASS** を確認

### Task F-1-2: `eqcom1_mod`, `eqcom2_mod`, `eqcom3_mod` の作成
- [ ] 各 COMMON を `MODULE eqcomN_mod` で `SAVE` 属性付き変数として宣言
- [ ] `ALLOCATABLE` は Phase F-4 で導入 (この段階では固定サイズ維持)
- [ ] **include と module を並行共存可能にする過渡期 Makefile ルール** を用意

### Task F-1-3: bootstrap 検証プログラム
- [ ] `eq/tests/eq_commontest.f90` を作成: 全 module を USE して初期値を整合チェック
- [ ] 既存 `eq` 実行と初期値一致を確認

## Phase F-2: LOW tier 自由形式化

### Task F-2-1: `newton.f`, `invematrix.f` の自由形式化
- [ ] `.f` → `.f90` リネーム + 自由形式 (`&` 継続, column-1 comment `!`)
- [ ] COMMON 参照無いため、変更は純粋に syntactic
- [ ] `./run_tests.sh eq_*` 全 PASS

### Task F-2-2: `eqgetp.f`, `eqgsub.f` の自由形式化
- [ ] 同上
- [ ] graphics 側 (`eqgsub.f`) は L-1 分離済みの `SRCS_GRAPHICS` に含まれるため、Makefile のリストも合わせて更新

## Phase F-3: MED tier 自由形式化 (USE module 化)

各ファイルを順次自由形式化し、`INCLUDE 'eqcomN.inc'` を `USE eqcomN_mod` に置換。

依存が浅い順: `eqinit` → `equnit` → `equintf` → `eqrppl` → `eqcalv` → `eqfunc` → `eqintf` → `eqmenu` → `eqgout`

- [ ] 各ファイルで段階的に変換し、変換ごとに L-0 回帰 PASS を確認
- [ ] `IMPLICIT NONE` を各ルーチンに追加
- [ ] `INTENT(IN/OUT/INOUT)` を argument に付与
- [ ] `DOUBLE PRECISION` → `REAL(KIND=dp)` へ段階的に移行 (optional; dp は `task_kind` module で集約)

## Phase F-4: HIGH tier 自由形式化 (critical path)

依存順: `eqsplf` → `eqsub` → `eq-eqdsk` → `eq-qst` → `eqfile` → `eqbpsd` → `eqcalc` → `eqcalq`

- [ ] `eqsplf.f` 自由形式化 — スプライン生成は後段の `eqcalq` で参照される
- [ ] `eqsub.f` 自由形式化 — 最も COMMON 依存が重い
- [ ] `eq-eqdsk.f`, `eq-qst.f` — file I/O 順序依存を変えない
- [ ] `eqfile.f` — `EXTERNAL` 代わりに `PROCEDURE POINTER` 化
- [ ] `eqbpsd.f` — BPSD 側 interface を保持
- [ ] `eqcalc.f`, `eqcalq.f` — 最後に置換、numeric drift なしを確認

---

## Risks & Mitigations

| リスク | 影響 | Mitigation |
|---|---|---|
| COMMON 初期化順序の差 | 初期値ドリフト → 数値結果不一致 | bootstrap 検証プログラム (F-1-3) を各フェーズ冒頭で実行 |
| スプライン依存グラフ | `eqcalq` が `eqsplf` より先に走ると NaN | F-4 では `eqsplf` を先に変換し、Makefile 依存で順序保証 |
| `eqfile.f` の I/O シーケンス | ファイル順序に敏感なフォーマットが崩れる | I/O 関連は `MODULE` 内 `PROCEDURE` に包んで外形維持 |
| F77 外部関数 (newton など) が F90 module 側から呼べなくなる | リンクエラー | `INTERFACE` 宣言を `equintf.f90` 系に集約 |
| `-std=f2008` の警告大量発生 | レビュー困難 | フェーズごとに `-std=f2008 -Wall` を clean にしてからマージ |

---

## Testing Strategy

- 各タスクの完了条件は **`./run_tests.sh eq_*` 全 PASS** かつ `compare_metrics.py --tolerance 1e-13` PASS (L-0 で整備済み)。
- `eq_commontest.f90` は Phase F-1 で初期値確認用、以降の phase でも COMMON→MODULE 境界で走らせる。
- CI でまず LOW tier 自動ビルドを固定、MED/HIGH tier は手動トリガ (長時間) とする。

## Deliverables

- [ ] `eq/eqcom{0..5}_mod.f90` (6 本) — Phase F-1
- [ ] `eq/tests/eq_commontest.f90` — Phase F-1
- [ ] `eq/*.f90` (23 本 ± graphics 含む全体) — Phase F-2..F-4
- [ ] `eq/Makefile` 更新 (`.f90` ルール統一、include 削除) — 各フェーズ
- [ ] docs: `docs/superpowers/plans/2026-04-18-eq-f90-modernization-phaseN-report.md` を各フェーズ終了時に残す

---

## 前提条件

- **eq L-0 完了**: 回帰スイート (`eq_*`) とベースラインが develop に merge 済みであること。
- 本計画はコード変更を含むため、L-0 完了後に **個別フェーズ F-1..F-4 を別 PR で** 順次実装する。

## 見積 (目安)

| Phase | 期間 | PR 数 |
|---|---|---|
| F-1 (MODULE 化) | 1-2 週 | 2-3 |
| F-2 (LOW) | 3-5 日 | 1-2 |
| F-3 (MED) | 3-4 週 | 5-7 |
| F-4 (HIGH) | 4-6 週 | 6-8 |

総計 8-12 週、14-20 PR 程度。
