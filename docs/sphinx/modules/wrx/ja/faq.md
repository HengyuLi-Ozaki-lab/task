# FAQ — `wrx` 固有

## Q1. `wrx` は何をするモジュール?

`wrx` (Wave Ray eXtended) は **beam tracing** ソルバで, `wr` (geometric optics)
の拡張版です. 各レイに **ビーム形状情報** (曲率テンソル, 幅, 位相) を
持たせ, 集束ビームの伝搬を **解析的に展開** します.

主な用途:

- **集束 ECRH ビーム** (ITER の Upper/Equatorial Launcher など)
- **LH ビーム** の高精度解析
- **gyrotron ビーム** の焦点追跡

## Q2. `wr` とどう使い分ける?

| 目的 | 推奨 |
|---|---|
| ECRH/ECCD の概算 (ピーク位置だけ知りたい) | `wr` |
| ECRH の集束ビームで吸収プロファイル精度が必要 | **`wrx`** |
| 多数レイでビーム広がりを近似 | `wr` (NRAYMAX=10–50) |
| 単一レイでビームを正確に追跡 | **`wrx`** |
| 計算時間を最小にしたい | `wr` |
| 物理的に正確な beam tracing | **`wrx`** |

迷ったら **まず `wr` で十分** — 結果が荒すぎたら `wrx` を検討.

## Q3. `NRAYMAX=1` で十分な結果が出るのか?

**はい**. `wrx` の肝は, 1 本のレイでビーム形状を追跡できることです.
複数レイが必要なのは:

- 物理的に分離された複数ビーム (upper + lower launcher 等)
- 異なる周波数の混在
- 波動モード (O/X モード) の比較

単純な集束ビーム 1 個なら `NRAYMAX=1` で OK.

## Q4. `RBRADAIN`, `RCURVAIN` の決め方

- **`RBRADAIN[i]`**: ビームの 1/e² 幅 [m]. ECRH gyrotron は典型的に
  2–5 cm, LH coupler は 10–30 cm くらい.
- **`RCURVAIN[i]`**: 曲率半径 [m]. 正で発散, 負で集束. 集束光学系の
  焦点距離 (focal length) に対応します. 発散してほしければ大きい正値
  (例: 1000) を設定.

詳細は装置の光学系仕様を参照.

## Q5. 結果が `wr` と一致しない

wrx は beam tracing で物理的に `wr` と違うモデルなので **一致しないのが
正常** です. 近いパラメータで比較するには:

- `wrx` で `RBRADAIN=0.001` (ほぼ 0 幅) にすると `wr` に近い結果
- `wr` で `NRAYMAX=50` くらいで beam 近似すると `wrx` に近づく

完全一致は期待できません.

## Q6. 結果が `wrx2` (CLI 版) と一致しない

回帰テスト `wrxlib_equivalence` を実行:

```bash
bash test_run/run_tests.sh wrxlib_equivalence
```

tolerance は `1e-10`. 許容値以上ずれる場合は登録漏れのパラメータを確認.

## Q7. レイが途中で止まる / パワーが 0

`wr` と同じ原因の多く:

- `NSTPMAX` 不足
- カットオフに到達
- 共鳴 (吸収点) に到達しない入射条件

ただし `wrx` では **ビームが発散しすぎて計算不能になる** ケースも追加で
あります. `RCURVAIN` (曲率) を変えて発散を抑えてください.

## Q8. `wr` と `wrx` のテストは両方走らせるべき?

各モジュールには独立した等価性テスト (`wrlib_equivalence`,
`wrxlib_equivalence`) があるので両方走らせます. CI では並列実行される
ため時間は大きく変わりません.
