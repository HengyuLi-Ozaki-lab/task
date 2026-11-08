# 入力パラメータの指定方法

4 通りあります.

## 方法 A — スカラー (`set_params`)

Python のキーワード引数で一括指定できます.

```python
tr.set_params(RR=7.5, RA=2.0, BB=5.3, DT=0.05, NTMAX=200)
```

## 方法 B — 配列要素 (`set_param`)

キーワード引数には `[` `]` が使えないので, 配列要素は `set_param` を
使います. **1-origin** (1 始まり) です.

```python
tr.set_param("PN[1]", 1.0)   # 1 番目の粒子種の密度
tr.set_param("PN[2]", 1.0)   # 2 番目
tr.set_param("CDW[12]", 0.5) # 配列 CDW の 12 番目
```

## 方法 C — 文字列パラメータ (`set_param_str`)

TR には平衡データファイル名 `KNAMEQ` など文字列パラメータがあります.
これは専用 API で与えます.

```python
tr.set_param_str("KNAMEQ", "eqdata.ITER01")
```

## 方法 D — 事前検証 (`validate`)

```{admonition} 新機能 (PR #172)
:class: important

`validate()` はパラメータを `run()` に渡す前に一括検査する API です.
値域逸脱, 整合性違反, ファイル不在などを診断 dataclass のリストで
返します. パラメータ設定後, `run()` の前に呼ぶのが推奨フローです.
```

```python
from trlib import Trlib, TrDiagCode

with Trlib() as tr:
    tr.set_params(RR=3.0, BB=3.0, NSMAX=2)
    tr.set_param_str("KNAMEQ", "eqdata.missing")  # 存在しないファイル

    diags = tr.validate()
    for d in diags:
        print(f"[{TrDiagCode(d.code).name}] {d.param}: {d.message}")
    if diags:
        raise SystemExit("fix the diagnostics before running")

    tr.run(ntmax=10)
```

診断コードの一覧:

| コード | 意味 |
|---|---|
| `OUT_OF_RANGE`           | 値が許容範囲外 |
| `INCONSISTENT_PAIR`      | 関連パラメータ対の不整合 |
| `OUT_OF_RANGE_AFTER_DEP` | 依存パラメータ評価後の範囲逸脱 |
| `FILE_MISSING`           | 指定されたファイルが存在しない (`KNAMEQ` など) |
| `MISSING_REQUIRED`       | 必須パラメータが未設定 |

現在行われる検査: `NSMAX` がコンパイル時上限を超える (`OUT_OF_RANGE`),
`MODELG` 3/5/7/8 で `KNAMEQ` が空 (`FILE_MISSING`),
`EXTERNAL_DRIVEN_I != 0` かつ `EXTERNAL_DRIVEN_RW <= 0` (`OUT_OF_RANGE`),
および UFILE モード以外 (`MDLUF` が 1/2/3 でない) のとき active な粒子種
`1..NSMAX` の namelist プロファイル: `PN`/`PNS` が負, 両方 0, 非有限,
または `PT`/`PTS` が 0 以下の場合に `PN[ns]` / `PT[ns]` / `PTS[ns]` として
報告 (両方 0 は `OUT_OF_RANGE_AFTER_DEP`, それ以外は `OUT_OF_RANGE`).
輸送ステップがこれらで割るため, 実行すると NaN になるからです (#189).
`run()` も `tr_prep` 前に同じ条件で拒否 (`TrlibParamError`) し, コンパイル時
上限を超える `NSMAX` も拒否するので, fixture の粒子種数を超えて `NSMAX`
を上げる場合は追加種の `PN[ns]`, `PNS[ns]`, `PT[ns]`, `PTS[ns]` を設定して
ください.
