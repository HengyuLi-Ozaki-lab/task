# 入力パラメータの指定方法

4 通りあります.

## 方法 A — スカラー (`set_param`)

`tr` と違い, `eq` の `set_params(**kwargs)` はスカラー専用 (位置引数で
mapping を受ける形もサポート, 下記 B 参照). 通常は 1 つずつ
`set_param("NAME", value)`:

```python
eq.set_param("RR", 6.5)
eq.set_param("MODELG", 3)      # int は double で渡して OK
eq.set_param("RIPFC[1]", 0.5)  # PF コイル電流 (1-origin, 1..10)
```

```{admonition} `PSIB` だけは 0-origin
:class: warning

Fortran 宣言が `REAL(KIND=8) :: PSIB(0:5)` で 0 から始まるため, 添字も
`PSIB[0]` 〜 `PSIB[5]` です. 添字無しの裸の `"PSIB"` はレジストリで
明示的に拒否されます (`EqlibInvalidParamError`). 他の 1-D 配列
(`RIPFC`, `RPFC`, `ZPFC`, `WPFC`) は 1-origin です.
```

## 方法 B — 一括 dict / kwargs (`set_params`)

```python
eq.set_params(RR=6.5, BB=5.3, MODELG=3)       # kwargs 形式
eq.set_params({"RR": 6.5, "BB": 5.3})          # 位置引数 mapping 形式
```

## 方法 C — 文字列パラメータ (`set_param_str`)

EQDSK 系ファイル名は `CHARACTER(LEN=80)` で, **専用 API** が必須です.
`set_param` には渡せません.

```python
eq.set_param_str("KNAMEQ",  "eqdata.ITER01")
eq.set_param_str("KNAMWR",  "wrdata.dat")
```

対応するキーは **7 個**:
`KNAMEQ`, `KNAMEQ2`, `KNAMWR`, `KNAMWM`, `KNAMFP`, `KNAMFO`, `KNAMPF`.

## 方法 D — 事前検証 (`validate`)

```{admonition} 新機能 (PR #164)
:class: important

`validate()` はパラメータを `run()` に渡す前に一括検査する API です.
グリッド寸法の整合性, ファイル不在などを診断 dataclass のリストで
返します. パラメータ設定後, `run()` の前に呼ぶのが推奨フローです.
```

```python
from eqlib import Eq, EqDiagCode

with Eq() as eq:
    eq.set_params(RR=6.5, BB=5.3, RIP=1.5, MODELG=3)
    eq.set_param_str("KNAMEQ", "eqdata.missing")  # 存在しないファイル

    diags = eq.validate()
    for d in diags:
        print(f"[{EqDiagCode(d.code).name}] {d.param}: {d.message}")
    if diags:
        raise SystemExit("fix the diagnostics before running")

    eq.run()
```

診断コードは `tr` と共通の 5 種類:

| コード | 意味 |
|---|---|
| `OUT_OF_RANGE`           | 値が許容範囲外 |
| `INCONSISTENT_PAIR`      | 関連パラメータ対の不整合 |
| `OUT_OF_RANGE_AFTER_DEP` | 依存パラメータ評価後の範囲逸脱 |
| `FILE_MISSING`           | 指定されたファイルが存在しない (`KNAMEQ` など) |
| `MISSING_REQUIRED`       | 必須パラメータが未設定 |

`eq_validate` は **10 個のグリッド寸法** (`NSGMAX`, `NTGMAX`, `NUGMAX`,
`NRGMAX`, `NZGMAX`, `NPSMAX`, `NRMAX`, `NTHMAX`, `NSUMAX`, `NRVMAX`) と,
必要な幾何モードでの `KNAMEQ` / `KNAMPF` ファイル存在をチェックします.
