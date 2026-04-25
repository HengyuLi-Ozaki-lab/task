# 付録: 入力パラメータと出力の対応

`tot` の入出力対応をまとめます. **(1) 代数的に決まる関係** と **(2) 物理
スケーリング** に限定します. tot は他モジュールの寄せ集めなので, 詳細な
感度はそれぞれの `appendix-sensitivity.md` を参照してください.

```{admonition} 凡例
:class: note

- **↑**: 入力を増やすと出力も増える
- **↓**: 入力を増やすと出力は減る
- **=**: 入力に等しい / 直接決まる
- **〜**: 概ね成り立つ
```

## 1. 代数的・直接的に決まる関係

| 入力 | 主に影響する出力 | 関係 | 備考 |
|---|---|---|---|
| `tr:DT × tr:NTMAX` | `state.scalars["T"]` | = | 最終時刻 |
| `tr:NSMAX` | `state.nsmax` | = | tr の粒子種数 |
| `Tot()` 成功時 | `state.<mod>_present` | = 1 | 各サブモジュール正常 init |
| サブモジュール失敗 | `state.<mod>_present` | = 0 | 該当プレフィックス使用不可 |

## 2. 物理スケーリングとして既知の傾向

`tot` の出力は基本的に **`tr` 経由で取得** されるため, `tr` の感度がそのまま
適用されます. 詳細は `tr` モジュールの sensitivity 付録
(`docs/sphinx/modules/tr/ja/appendix-sensitivity.md`) を参照.

### 2.1 装置パラメータ (`eq:RR`, `eq:BB`, ...)

`eq` プレフィックスで装置を変えると, 平衡が変わって `tr` の磁気面情報が
変わり, 結果として `state.scalars` 全部が変わります.

| 入力 | 主に影響する出力 | 方向 | 備考 |
|---|---|---|---|
| `eq:RR` ↑ | `state.scalars["WPT"]` | ↑ | 体積比例 (`tr` と同じ) |
| `eq:BB` ↑ | `state.scalars["BETAN"]` | ↓ | $\beta \propto 1/B^2$ |
| `eq:RIP` ↑ | `state.scalars["Q0"]`, `Q[surf]` | ↓ | $q \propto B/I$ |

### 2.2 加熱モジュール統合の効果

`tot` の特徴は **加熱が動的に統合される** こと.

| 入力 | 主に影響する出力 | 方向 | 物理的根拠 |
|---|---|---|---|
| `tr:MDLNB = 1` (NBI ON) | `state.scalars["WPT"]` | ⊕↑ | 加熱パワー追加 (tr 内で計算) |
| `wr:RF`, `wr:RPI` 設定 | `state.scalars["WPT"]` | ⊕↑ | レイトレース結果が tr に流れる |
| `fp:MODEL_NBI = 1` (fp NBI 解析) | `state.scalars["AJT"]` (NB 駆動) | ⊕↑ | fp の Fokker-Planck 結果が tr に流れる |

### 2.3 連携の有無で結果が変わる

| 動作モード | 効果 |
|---|---|
| **eq + tr のみ** (wr/fp 不使用) | `tr` 単独と同じ結果 |
| **eq + tr + wr** | RF 加熱が動的に反映される |
| **eq + tr + wr + fp** | RF 加熱 + 高速イオン分布が反映される |

サブモジュールを増やすと **物理的精度は上がるが計算コストも上がる** ので,
目的に合わせて選びます.

## 各モジュールの詳細感度

`tot` 経由でも各モジュールの基本的な物理は変わらないので, 詳細は以下を
参照:

- `tr` の入出力対応: `docs/sphinx/modules/tr/ja/appendix-sensitivity.md`
- `eq` の入出力対応: `docs/sphinx/modules/eq/ja/appendix-sensitivity.md`
- `ti` の入出力対応: `docs/sphinx/modules/ti/ja/appendix-sensitivity.md`
- `fp` の入出力対応: `docs/sphinx/modules/fp/ja/appendix-sensitivity.md`
- `wr` の入出力対応: `docs/sphinx/modules/wr/ja/appendix-sensitivity.md`
- `wrx` の入出力対応: `docs/sphinx/modules/wrx/ja/appendix-sensitivity.md`

## 使い方

`tot` で出力を狙った値にしたいときの目安:

- **BETAN を上げたい** → `tr:` の `PN`, `PT` を上げる, または `eq:BB` を下げる
  (詳細は tr の sensitivity 付録参照)
- **RF 加熱の効果を比較したい** → `wr:` のレイトレース ON/OFF を切替
- **高速イオン解析を入れたい** → `fp:` パラメータを設定すると自動で fp が
  実行される

定量的な感度はシミュレーションを走らせて確認 — `totlib_sweep` (Layer 4)
の枠組みが利用できます.
