# 入力パラメータの指定方法

`wrx` は `wr` と同じ標準 5 関数 ABI なので, 指定方法は `set_params` /
`set_param` の 2 通りです. 文字列パラメータ専用 API は持ちません.

## 方法 A — スカラー (`set_params`)

```python
wrx.set_params(RR=3.0, RA=1.2, BB=3.0, NSMAX=1,
               NRAYMAX=1, NSTPMAX=10000,
               MODELG=2)
```

## 方法 B — 配列要素 (`set_param`)

レイ入射条件は **すべて配列パラメータ** で指定します (`wr` の `*IN` 配列と
同じ構造).

```python
wrx.set_param("NRAYMAX", 3)
for i in range(1, 4):
    wrx.set_param(f"RFIN[{i}]", 170.0e9)           # 周波数
    wrx.set_param(f"RPIN[{i}]", 3.5)                # 入射 R
    wrx.set_param(f"ZPIN[{i}]", 0.1*(i-2))          # 入射 Z (シフト)
    wrx.set_param(f"RKRIN[{i}]", 1.0)               # 初期波数
```

## `wr` との配列形式の違い

`wr` は **単一レイ用** (`RF`, `RPI` 等) と **複数レイ用** (`RFIN`, `RPIN`)
の両方を持ちますが, `wrx` は **複数レイ配列のみ** を使います. `NRAYMAX=1`
でも必ず `RFIN[1]`, `RPIN[1]` のように配列経由で指定してください.

```python
# wr の書き方 (NRAYMAX=1 で単一レイ)
wr.set_param("RF", 170e9)          # OK
wr.set_param("RPI", 3.5)           # OK

# wrx の書き方 (必ず配列)
wrx.set_param("RFIN[1]", 170e9)    # OK (単一レイでも配列形式)
wrx.set_param("RPIN[1]", 3.5)
# wrx.set_param("RF", 170e9)       # ← これは動かない場合あり
```

## ビーム形状の指定

`wrx` の醍醐味は **ビーム曲率・幅** の指定です.

```python
wrx.set_param("RCURVAIN[1]", 100.0)    # 主軸の曲率半径 [m]
wrx.set_param("RCURVBIN[1]", 100.0)    # 副軸の曲率半径
wrx.set_param("RBRADAIN[1]", 0.05)      # 主軸のビーム半径 (1/e² 幅) [m]
wrx.set_param("RBRADBIN[1]", 0.05)      # 副軸のビーム半径
```

これらを指定すると, 単一レイでも **有限幅 Gaussian ビーム** として
伝搬を計算します.

## 文字列パラメータについて

`wrx` は **文字列パラメータを持ちません**. `KNAMEQ` は `pl_*` 経由で継承.

## 事前検証 (`validate`)

```{important}
`wrx` は現時点で `validate()` API を実装していません. 値域違反は
`set_param` 時の即時エラー (`WrxlibParamError`), ビーム計算失敗は
`run()` 時の `WrxlibRunError` で検出します.
```

## 設定パターンの典型例

### 集束 ECRH ビーム (ITER Upper Launcher 想定)

```python
wrx.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
wrx.set_param("NRAYMAX", 1)
wrx.set_param("RFIN[1]", 170.0e9)
wrx.set_param("RPIN[1]", 8.5)
wrx.set_param("ZPIN[1]", 1.5)
wrx.set_param("ANGPHIN[1]", 20.0)        # トロイダル入射角 [deg]
wrx.set_param("RCURVAIN[1]", 200.0)      # 集束光学系の焦点距離
wrx.set_param("RBRADAIN[1]", 0.02)       # 2 cm ビーム幅
wrx.run(nray_request=1)
```

### 複数ビーム (multi-launcher)

```python
wrx.set_params(RR=6.2, BB=5.3, NRAYMAX=4)
for i in range(1, 5):
    wrx.set_param(f"RFIN[{i}]", 170e9)
    wrx.set_param(f"RPIN[{i}]", 8.5)
    wrx.set_param(f"ZPIN[{i}]", -0.5 + 0.3*(i-1))   # Z 方向に並べる
    wrx.set_param(f"RBRADAIN[{i}]", 0.02)
wrx.run(nray_request=4)
```
