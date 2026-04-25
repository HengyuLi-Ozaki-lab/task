# 入力パラメータの指定方法

`fp` は `eq` と同じ 6 関数 ABI で, スカラー / 配列 / **文字列** の 3 通りの
指定方法があります.

## 方法 A — スカラー (`set_params`)

```python
fp.set_params(RR=3.0, BB=3.0, NSMAX=1,
              NPMAX=50, NTHMAX=25, NRMAX=20,
              DELT=0.001, NTMAX=100,
              MODELE=1)
```

## 方法 B — 配列要素 (`set_param`)

```python
fp.set_param("PA[1]", 2.0)        # 1 番目の粒子種の質量数
fp.set_param("PZ[1]", 1.0)        # 電荷
fp.set_param("NS_NSA[1]", 2)      # NSA[1] が NSMAX[2] にマップ
```

## 方法 C — 文字列パラメータ (`set_param_str`)

`fp` は **`KNAMEQ`** (平衡データファイル名) を文字列で指定できます.

```python
fp.set_param_str("KNAMEQ", "eqdata.ITER01")
```

`fp` は内部で `pl_*` モジュールから `KNAMEQ` を継承しますが, これを
上書きしたい場合に使います.

## 事前検証 (`validate`)

```{important}
`fp` は現時点で `validate()` API を実装していません. 値域違反は `set_param`
時の即時エラー (`FplibInvalidParamError`), 物理整合性違反は `run()` 時の
`FplibCalcFailedError` で検出します.
```

## 設定パターンの典型例

### NBI 注入の高速イオン分布

```python
fp.set_params(NSMAX=2, NSAMAX=2, NSBMAX=2,
              NPMAX=100, NTHMAX=50,        # 高解像度
              MODEL_NBI=1)                  # NBI 粒子源 ON
```

### 波動による電子加速

```python
fp.set_params(NSMAX=1,
              MODELE=1,                     # 電子のみ
              MODEL_WAVE=1,                 # 波動駆動 ON
              PABS_LH=1.0)                  # LH 波の吸収パワー [MW]
```

### 平衡データを別ファイルから

```python
fp.set_param("MODELG", 3)                   # EQDSK モード
fp.set_param_str("KNAMEQ", "eqdata.ITER01") # 平衡データ
```
