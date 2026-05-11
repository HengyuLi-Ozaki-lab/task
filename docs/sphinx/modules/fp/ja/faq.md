# FAQ — `fp` 固有

## Q1. `fp` は何をするモジュール?

`fp` は **Fokker-Planck 方程式ソルバ** で, 粒子分布関数 $f(r, p, \theta, t)$
の時間発展を解きます. `tr` / `ti` のような流体方程式 (温度・密度の発展)
ではなく, **5D 位相空間** (位置 1D × 運動量 1D × ピッチ角 1D × 種別 ×
時間) を直接解きます.

主な用途:

- **NBI 起源高速イオン**の分布計算 (温度モーメントだけでは見えない
  非熱化テール)
- **波動駆動** (LH, ECCD) による電子分布変形
- **核融合 α 粒子**の減速過程
- **disruption 時のランナウェイ電子**の加速

## Q2. `tr`/`ti` で温度を計算するのと何が違う?

`tr`/`ti` は分布関数を **Maxwellian と仮定** して温度・密度のモーメント
だけを発展させます. 高速イオンや波動駆動など **非熱平衡分布** が重要な
場面では Maxwell 仮定が破綻するので, fp が必要になります.

具体例:

| 場面 | tr/ti でも OK | fp が必要 |
|---|---|---|
| 通常の輸送計算 (Te, Ti プロファイル) | ✓ | — |
| NBI 加熱の絶対値見積もり | (近似) ✓ | より精密 |
| ECCD / LHCD の電流駆動効率 | ✗ | ✓ |
| 高速イオンの分布関数形 | ✗ | ✓ |
| ランナウェイ電子の解析 | ✗ | ✓ |

## Q3. `NPMAX`, `NTHMAX` をどう決める?

運動量空間とピッチ角空間の解像度です. 既定では `NPMAX=50`, `NTHMAX=25`
程度が想定されます.

- **小さすぎる** → 分布関数の鋭い構造 (ビームピーク, 共鳴ピーク) を
  解像できない
- **大きすぎる** → メモリ消費 (×NPMAX × NTHMAX × NRMAX × NSAMAX) と
  計算時間が膨大に

経験則: NBI 解析なら `NPMAX≥80`, `NTHMAX≥50` 推奨.

## Q4. `NSMAX`, `NSAMAX`, `NSBMAX` の違い

| 名前 | 意味 |
|---|---|
| `NSMAX` | 全粒子種数 (TR/TI と同じ) |
| `NSAMAX` | **active species** — 分布関数を解く粒子の数 |
| `NSBMAX` | **bulk species** — 衝突項のターゲットとなる粒子 |

`NSAMAX = 1` で電子のみ解いて `NSBMAX = 2` でイオンを衝突相手に, など
の使い分けができます.

## Q5. `MODELE` / `MODELS` などのスイッチ

`MODELE` (Energy operator):

- 1 (既定): 線形 Fokker-Planck
- 2: 相対論的 Fokker-Planck

`MODELS` (Source operator):

- 0: 粒子源なし
- 1: NBI 粒子源 (`MODEL_NBI=1` 必須)
- 他

詳細は `fp/fpinit.f90` のコメントブロック参照.

## Q6. 結果が `fpx2` (CLI 版) と一致しない

回帰テスト `fplib_equivalence` を実行:

```bash
bash test_run/run_tests.sh fplib_equivalence
```

tolerance は `1e-10`. 許容値以上ずれる場合は登録漏れのパラメータがある
可能性があります.

## Q7. メモリエラー / SIGABRT が出る

5D グリッドが大きすぎる可能性が高いです. 概算:

```
RAM ≈ NRMAX × NPMAX × NTHMAX × NSAMAX × 8 bytes × (~10 配列)
```

`NRMAX=50, NPMAX=100, NTHMAX=50, NSAMAX=2` で約 40 MB × 10 = 400 MB.
これに加えて `LMAXFP` 反復のための一時配列もあります. 32GB マシンでも
`NPMAX=200` くらいまでが現実的ライン.

`Fplib()` インスタンスは 1 プロセス 1 個までで, `with` を抜けたら必ず
解放しましょう.
