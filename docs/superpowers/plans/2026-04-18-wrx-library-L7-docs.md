# WRX ライブラリ化 Phase L-7: ドキュメント・使用例実装計画

**位置:** `docs/superpowers/plans/2026-04-18-wrx-library-L7-docs.md`
**実装スパン:** 数日
**前提:** L-6 完了（4 層テスト全 PASS）
**目標:** `wrxlib` の正式ドキュメント・使用例 notebook を整備し、Phase L 完了とする。

## 成果物

```
python/wrxlib/
├── README.md            # 本体（L-5 雛形を拡張）
├── docs/
│   ├── api_reference.md    # 5 関数 C ABI + Python class の完全仕様
│   ├── parameters.md        # 登録 namelist パラメータ一覧（L-3 由来）
│   └── troubleshooting.md   # 既知問題・FAQ
└── examples/
    ├── 01_quickstart.ipynb         # 最初の起動・ray の可視化
    ├── 02_param_sweep.ipynb        # NRAYMAX × PWAVE スイープ
    └── 03_compare_with_native.ipynb # wrxlib vs 既存 wrx バイナリ等価性確認
```

## Task 1: `python/wrxlib/README.md` 本体

L-5 で作った雛形を拡張。以下を含む:

1. **概要**: wrx は何をするか・wr との違い（拡張版である点）
2. **インストール**: `cd python/wrxlib && pip install -e .` の手順（pyproject.toml が必要なら追加）
3. **クイックスタート**: 5 行で動く例（init→run→get_state→finalize）
4. **API 概要**: 主要 class/method の表
5. **環境変数**: `WRX_LIB_PATH` （`libwrxapi.so` カスタム位置）
6. **既知の制限**: GIL 並列、symbol 衝突回避、`wrlib` との独立性
7. **リンク**: 各 docs ファイルと examples notebook へ

完了基準:
- [ ] README が L-5 雛形を完全に置き換え
- [ ] 5 行 quickstart がコピペで動く（doctest 風）

## Task 2: `docs/api_reference.md`

C ABI 5 関数（`wrx_init` / `wrx_run` / `wrx_get_state` / `wrx_set_param` / `wrx_finalize`）の：
- シグネチャ
- 引数の意味と単位
- 戻り値（`wrx_error_code` enum）
- 呼び出し順序の制約（init→run→...→finalize）

Python `WrxLib` class の：
- 各 method のシグネチャ・raise する例外
- `__enter__/__exit__` の context manager 利用パターン

完了基準:
- [ ] 5 関数 + 5 method 全部が記載
- [ ] L-2 の `wrx_api.h` ヘッダコメントと内容一致

## Task 3: `docs/parameters.md`

L-3 で登録した namelist パラメータ一覧を表で記載:

| 名称 | 型 | デフォルト | 範囲 | 単位 | 説明 |
|---|---|---|---|---|---|
| NRAYMAX | int | 1 | 1〜MAX | - | 追跡するレイ本数 |
| ... | ... | ... | ... | ... | ... |

L-3 の `wrx_param_registry.f90` 実装と必ず同期させる（差分検出スクリプトを CI に入れることを検討）。

完了基準:
- [ ] L-3 で登録した全 param が掲載
- [ ] L-3 ソースとの差分チェック（簡易 grep スクリプト）

## Task 4: `docs/troubleshooting.md`

想定される問題と対処:
1. `OSError: libwrxapi.so not found` → `WRX_LIB_PATH` 設定
2. `WrxError: NOT_INITIALIZED` → init 順序ミス・`finalize` 後の操作
3. `wrlib` と同時 import で SEGV → symbol scope 問題（wrx と wr が同じ symbol を持つケースがあれば、L-4 設計を見直し）
4. sweep 中の数値非再現性 → global state リセット漏れ（L-3 で確認）
5. PETSc/MPI 依存ライブラリ未ロード → `LD_LIBRARY_PATH` 設定

完了基準:
- [ ] 上記 5 項目以上を記載
- [ ] 各項目に対処コマンドあり

## Task 5: `examples/01_quickstart.ipynb`

Jupyter notebook で以下を実行:
1. `from wrxlib import WrxLib`
2. `with WrxLib() as wrx:` で初期化
3. `wrx.set_param('NRAYMAX', 8)`
4. `wrx.run()`
5. `wrx.get_state('rays_r', size=...)` 等を取得
6. matplotlib で ray の R-Z 平面投影をプロット

完了基準:
- [ ] notebook が clean kernel で end-to-end 実行 PASS
- [ ] プロットが生成される

## Task 6: `examples/02_param_sweep.ipynb`

Layer 4 の sweep をリッチに可視化:
1. NRAYMAX × PWAVE の 5×5 grid
2. 各点で `pwr_profile` を取得
3. heatmap / 3D surface で表示

完了基準:
- [ ] 25 ケース全 successful
- [ ] heatmap が描画される

## Task 7: `examples/03_compare_with_native.ipynb`

`wrxlib` 経由結果と既存 `wrx` バイナリ結果を直接比較:
1. 同じ入力ケースで両方走らせる
2. `metrics.json` 同士を `compare_metrics.py` で比較
3. 残差プロット表示

完了基準:
- [ ] tolerance `1e-10` 以内で一致
- [ ] 残差プロットがほぼゼロ

## Task 8: 横断ドキュメント更新

- `docs/superpowers/specs/2026-04-17-tr-library-design.md` に「sister 作業: wrx」へのリンクを追記
- リポジトリ root `README.md` に `python/wrxlib` パッケージの概要を追記
- `CHANGELOG.md`（あれば）に Phase L-7 完了を記載

## 完了基準（フェーズ全体）
- [ ] README + 3 docs + 3 notebook が全部 commit され develop に merge
- [ ] notebook 全 3 件が clean kernel で再実行成功
- [ ] CI に notebook 実行スモーク追加（`jupyter nbconvert --execute --to notebook`）

## 撤退条件
- notebook 実行が CI で flaky → CI 対象から外し、手動実行のみとする
- API 仕様が L-2 から大きく変動 → L-2 を再オープンせず、ドキュメントを最新に追従させる

## 依存
- L-6 完了（テスト全層 PASS）
- L-3 のパラメータリスト確定
- 既存 `python/` ディレクトリ規約（あれば）に準拠

## Phase L 完了宣言
本サブフェーズ完了をもって、wrx モジュールの Phase L (library-ization) を完了とする。`tr` と並列に Python から呼び出せる `wrxlib` が利用可能となり、整数化・パラメータ最適化（tot Phase L-7）への接続準備が整う。
