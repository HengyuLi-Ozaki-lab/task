# 入力パラメータの指定方法

`wr` は `tr` と同じ標準 5 関数 ABI なので, 指定方法は `set_params` /
`set_param` の 2 通りです (文字列パラメータ専用 API は持ちません).

## 方法 A — スカラー (`set_params`)

```python
wr.set_params(RR=3.0, RA=1.2, BB=3.0, NSMAX=1,
              RF=170.0e9,            # 周波数 [Hz]
              RPI=3.5, ZPI=0.0,      # 入射位置
              NRAYMAX=1)             # レイ数
```

## 方法 B — 配列要素 (`set_param`)

複数レイを使う場合, 各レイの初期条件は配列パラメータで指定します.

```python
wr.set_param("NRAYMAX", 5)            # 5 本のレイ
for i in range(1, 6):
    wr.set_param(f"RFIN[{i}]", 170.0e9)    # i 番目レイの周波数
    wr.set_param(f"RPIN[{i}]", 3.5)         # 入射 R
    wr.set_param(f"ZPIN[{i}]", 0.1*(i-3))   # 入射 Z (シフト)
    wr.set_param(f"RKRIN[{i}]", 1.0)        # 初期波数
    wr.set_param(f"PHIIN[{i}]", 0.0)        # トロイダル角
```

`*IN` サフィックス付きの配列が「各レイの初期条件」, サフィックスなしの
スカラー (`RF`, `RPI`, ...) は `NRAYMAX=1` のときの単一レイ用です.

## 単一レイ vs 複数レイの使い分け

### 単一レイ (`NRAYMAX=1`)

```python
wr.set_params(RR=3.0, BB=3.0)
wr.set_param("RF", 170e9)         # スカラー版を使用
wr.set_param("RPI", 3.5)
wr.run(nray_request=1)
```

### 複数レイ (`NRAYMAX>1`)

```python
wr.set_params(RR=3.0, BB=3.0, NRAYMAX=5)
for i in range(1, 6):
    wr.set_param(f"RFIN[{i}]", 170e9)
    wr.set_param(f"RPIN[{i}]", 3.5)
    wr.set_param(f"ZPIN[{i}]", -0.1 + 0.05*(i-1))   # Z 方向に分散
wr.run(nray_request=5)
```

## 文字列パラメータについて

`wr` は **文字列パラメータを持ちません**. 平衡データ (`KNAMEQ`) は `pl_*`
モジュール経由で渡されるため, `wr` 自身からは設定しません.

## 事前検証 (`validate`)

```{important}
`wr` は現時点で `validate()` API を実装していません. 値域違反は
`set_param` 時の即時エラー, レイトレース失敗は `run()` 時の
`WrlibRunError` で検出します.
```

## 設定パターンの典型例

### ECRH/ECCD (170 GHz, ITER 想定)

```python
wr.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
wr.set_param("RF", 170.0e9)
wr.set_param("RPI", 8.0)               # 外側からの入射
wr.set_param("ZPI", 0.0)
wr.set_param("MODELP[1]", 4)           # 電子サイクロトロン共鳴モード
wr.run(nray_request=1)
```

### LH (3.7 GHz)

```python
wr.set_params(RR=6.2, RA=2.0, BB=5.3, NSMAX=2)
wr.set_param("RF", 3.7e9)
wr.set_param("RNZI", 1.8)              # 平行屈折率 (LH の効率に重要)
wr.run(nray_request=1)
```

### Multi-ray ビーム近似 (5 本)

```python
wr.set_params(RR=6.2, BB=5.3, NRAYMAX=5)
for i in range(1, 6):
    wr.set_param(f"RFIN[{i}]", 170e9)
    wr.set_param(f"RPIN[{i}]", 8.0)
    wr.set_param(f"ZPIN[{i}]", -0.1 + 0.05*(i-1))   # ビーム広がり
wr.run(nray_request=5)
```
