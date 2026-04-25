# `ti` — 統合輸送

```{admonition} この章で学ぶこと
:class: tip

TASK/TI (**統合輸送** モジュール: 輸送 + 補助物理 (NBI, EC, LH, IC,
核融合, 不純物, 新古典) を統合) を Python から呼ぶ `tilib` の使い方を
学びます. 共有ライブラリのビルド, 最短 hello-world, 77 個の登録
パラメータと 18+ の MODEL_* スイッチ, FAQ, テストまでカバーします.
```

## 概要 — `ti` は何をする

**TASK/TI** はトカマクの **時間発展する 1-D 統合プラズマシミュレーション**
を行うモジュールです. `tr` (純粋輸送) を発展させ, 以下を統合します:

- **輸送**: 乱流 + 新古典 (`MODEL_KAI`, `MODEL_NC`)
- **加熱・電流駆動**: NBI, ECRF, LHRF, ICRF (`MODEL_NB`, `MODEL_EC`,
  `MODEL_LH`, `MODEL_IC`, `MODEL_CD`)
- **粒子源**: 燃料補給, ペレット, 壁/SOL (`MODEL_PSC`, `MODEL_PEL`)
- **核融合**: DT/DHe³ 反応 + α 加熱 (`MODEL_NF`)
- **シンクロトロン放射**: (`MODEL_SYNC`)
- **不純物**: 多電離度モデル (`ID_NS`, `NZMIN_NS`, `NZMAX_NS` 配列)

得られる主な量:

- `RNA[nr][nsa]`, `RTA[nr][nsa]` — active species 別の密度・温度プロファイル
- `RUA[nr][nsa]` — トロイダル流速プロファイル
- `RBP[nr]`, `RQP[nr]`, `RJP[nr]` — ポロイダル磁場 / q / 電流
- `ZEFF[nr]`, `BETA[nr]` — 実効電荷, β プロファイル
- スカラー: `T` (時刻), 反復残差・カウンタ

## 使い方ガイド

```{toctree}
:maxdepth: 1

build
hello-world
parameters
parameter-setting
state
context-manager
faq
```

## リファレンス

```{toctree}
:maxdepth: 1

quickstart
api-reference
```

## 内部情報

```{toctree}
:maxdepth: 1

design
mcp
testing
```

## 付録

```{toctree}
:maxdepth: 1

appendix-sensitivity
```

## 読みすすめ方

初めて触る場合は次の順序がおすすめです:

1. {doc}`build` — 共有ライブラリをビルドし, `import tilib` できるようにする
2. {doc}`hello-world` — 5 行でプラズマを進める最短例
3. {doc}`parameters` — 77 個のパラメータと 18+ の MODEL_* スイッチ
4. {doc}`parameter-setting` — パラメータ指定の方法
5. {doc}`state` — `ti.get_state()` で取れる出力 (8 種のプロファイル)
6. {doc}`context-manager` — `with` 文の意味と落とし穴
7. {doc}`quickstart` — 実行可能 notebook で一連の流れを体験

困ったときは {doc}`faq` を. API の完全仕様は {doc}`api-reference`.
入力 ↔ 出力の対応関係は {doc}`appendix-sensitivity` へ.

## `tr` との違い (要約)

| | `tr` (純粋輸送) | `ti` (統合輸送) |
|---|---|---|
| **物理範囲** | 単純な 1D 輸送 | 輸送 + 補助物理を統合 |
| **C ABI** | 5 + `set_param_str` + `validate` | 5 (拡張なし) |
| **登録パラメータ数** | ~30 | **77** |
| **MODEL_* スイッチ数** | ~10 | **18+** |
| **出力スカラー数** | 13 (BETAN, TAUE 等) | 2 + 2 整数 (収束診断中心) |
| **プロファイル数** | 4 (RN, RT, AJ, QP) | 8 (RNA, RTA, RUA, RBP, RQP, RJP, ZEFF, BETA) |
| **species 軸** | NSMAX | active `nsa_max` |
| **典型用途** | 輸送モデル比較ベンチマーク | 実験再現シミュレーション |
