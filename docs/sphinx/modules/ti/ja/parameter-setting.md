# 入力パラメータの指定方法

`ti` は `tr` と同じ標準 5 関数 ABI なので, 指定方法は `set_params` /
`set_param` の 2 通りです (文字列パラメータ専用 API は持ちません).

## 方法 A — スカラー (`set_params`)

Python のキーワード引数で一括指定できます.

```python
ti.set_params(RR=3.0, RA=1.2, BB=3.0, NSMAX=2,
              DT=0.01, NTMAX=100,
              MODEL_KAI=31, MODEL_NB=1)
```

## 方法 B — 配列要素 (`set_param`)

キーワード引数には `[` `]` が使えないので, 配列要素は `set_param` を
使います. **1-origin** (1 始まり) です.

```python
ti.set_param("PN[1]", 1.0)         # 1 番目の粒子種の密度
ti.set_param("PT[2]", 1.5)         # 2 番目の中心温度
ti.set_param("PROFN1[1]", 2.0)     # プロファイル形状指数 (粒子種別)
ti.set_param("ID_NS[3]", 4)        # 種別 ID (整数だが double 渡しで OK)
```

## 文字列パラメータについて

`ti` は **文字列パラメータを持ちません** (eq の `KNAMEQ` のような専用 API
は不要). 平衡データを使う場合は `pl_*` (プラズマ共通) 経由で渡されるため,
`ti` 自身からは設定しません.

## 事前検証 (`validate`)

```{important}
`ti` は現時点で `validate()` API を実装していません. 値域チェックは
`set_param` 時の即時リジェクト (`TilibParamError`) と `run()` 時の物理
チェックのみです. 大量パラメータを動かす場合は `try/except` で囲んで
ください.
```

## 設定パターンの典型例

### 最低限の輸送計算

```python
ti.set_params(RR=3.0, RA=1.2, BB=3.0, RIP=3.0, NSMAX=2,
              DT=0.01, NTMAX=100)
```

### NBI を入れる

```python
ti.set_params(RR=3.0, BB=3.0, NSMAX=2,
              MODEL_NB=1)        # NBI モデル ON
```

### 輸送モデルを変える

```python
ti.set_params(RR=3.0, BB=3.0, NSMAX=2,
              MODEL_KAI=140)     # mBgB に切替 (既定は 31 = CDBM)
```

### 種別の電荷状態を細かく指定

```python
ti.set_param("ID_NS[3]", 6)        # 種 3 はカーボン (Z=6)
ti.set_param("NZMIN_NS[3]", 1)     # 最小電離度 +1
ti.set_param("NZMAX_NS[3]", 6)     # 最大電離度 +6
```
