# FAQ — `ti` 固有

## Q1. `ti` と `tr` の違いは?

`tr` は **単純な 1D 輸送方程式ソルバ** で, 最小限のパラメータで動きます.
`ti` は **輸送 + 補助物理 (NBI / EC / LH / IC / 核融合 / 不純物 / ペレット)
を統合したフルパッケージ** で, モデルスイッチが大量にあります.

| | `tr` | `ti` |
|---|---|---|
| 主目的 | 純粋な輸送ベンチマーク | 実験を再現する統合シミュレーション |
| 登録パラメータ数 | ~30 | 77 |
| MODEL_* スイッチ | NBI/EC/LH/IC, JBS のみ | 18 種以上 |
| プロファイル出力 | RN, RT, AJ, QP | RNA, RTA, RUA, RBP, RQP, RJP, ZEFF, BETA |

新規プロジェクトで「TASK で実験を再現したい」なら `ti` を選ぶのが普通です.

## Q2. `Tilib()` と `Trlib()` を同時に作れる?

**作れません**. 両方が共通のプラズマ状態 (`pl_*` モジュール) を握るので
シングルトン違反になります. 順次なら OK:

```python
with Trlib() as tr:
    ...
# tr_finalize 後
with Tilib() as ti:
    ...
```

## Q3. `validate()` メソッドが見つからない

`ti` は現時点で `validate()` API を実装していません ({doc}`parameter-setting`
の冒頭注意参照). 値域違反は `set_param` 時の即時エラー (`TilibParamError`),
物理整合性違反は `run()` 時の `TilibRunError` で検出します.

## Q4. `MODEL_*` スイッチが多すぎてどれを設定すべきか分からない

最低限は **既定値のままで動く** ように設計されています. 既定で輸送のみ
ON, 加熱・粒子源系は全 OFF です. 個別に有効化:

- `MODEL_NB=1` → NBI ON
- `MODEL_EC=1` → ECRF ON
- `MODEL_LH=1` → LHRF ON
- `MODEL_IC=1` → ICRF ON
- `MODEL_NF=1` → 核融合 ON
- `MODEL_NC=1` → NCLASS (新古典輸送) ON

詳細は {doc}`parameters` の「モジュール切替」セクション.

## Q5. NCLASS を有効にしたら結果がおかしくなった

`MODEL_NC=1` (NCLASS) を有効にすると, NCLASS が新古典輸送係数を全部
計算するため, それと矛盾するモデル (`MODEL_DRR`, `MODEL_VR` 等) を
有効にしていると結果がおかしくなります. NCLASS と他の輸送モデルを
**併用しない** ようにしてください.

## Q6. 反復が収束しない (`MAXLOOP` 到達)

時間ステップ `DT` が大きすぎるか, パラメータの整合性が悪い可能性が
あります. 対処:

1. `DT` を 1/10 にする (例: 0.01 → 0.001)
2. `MAXLOOP` を増やす (既定 100 → 1000)
3. `EPSLOOP` を緩める (既定 1e-6 → 1e-4)
4. プロファイル指数 (`PROFN1`, `PROFN2` など) が物理的に妥当か確認

## Q7. 結果が `tix2` (CLI 版) と一致しない

回帰テスト `tilib_equivalence` を実行して Phase 0 ベースラインとの
差分を確認してください.

```bash
bash test_run/run_tests.sh tilib_equivalence
```

tolerance は `1e-10`. 許容値以上ずれる場合は登録漏れのパラメータがある
可能性が高いです.
